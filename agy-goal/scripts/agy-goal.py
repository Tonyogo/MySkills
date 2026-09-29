#!/usr/bin/env python3
"""
agy-goal: Multi-turn runner for AGY plan execution (Local & Remote)
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


# ==============================================================================
# 1. Data Models & Result Parser
# ==============================================================================

@dataclass
class ExecutionResult:
    status: str              # "SUCCESS", "ERROR", "TIMEOUT"
    conversation_id: str
    duration_seconds: float
    raw_response: str
    goal_complete: bool
    git_diff_summary: str = ""
    error_message: Optional[str] = None


def parse_timeout_seconds(timeout_str: str) -> Optional[int]:
    """Parse timeout string (e.g. '20m', '30s', '1h', '600') to integer seconds."""
    if not timeout_str:
        return None
    s = str(timeout_str).strip().lower()
    try:
        if s.endswith("s"):
            return int(s[:-1])
        elif s.endswith("m"):
            return int(s[:-1]) * 60
        elif s.endswith("h"):
            return int(s[:-1]) * 3600
        return int(s)
    except ValueError:
        return None


def parse_agy_output(raw_output: str, exit_code: int = 0) -> ExecutionResult:
    stripped = (raw_output or "").strip()
    if not stripped:
        return ExecutionResult(
            status="SUCCESS" if exit_code == 0 else "ERROR",
            conversation_id="",
            duration_seconds=0.0,
            raw_response="",
            goal_complete=False,
            error_message="Empty output received" if exit_code != 0 else None,
        )

    try:
        data = json.loads(stripped)
        cid = str(data.get("conversation_id", "") or "")
        status = str(data.get("status", "SUCCESS" if exit_code == 0 else "ERROR"))
        duration = float(data.get("duration_seconds", 0.0) or 0.0)
        response_text = str(data.get("response", "") or "").strip()
        goal_complete = "GOAL_COMPLETE" in response_text
        err = None
        if exit_code != 0 and status != "ERROR":
            status = "ERROR"
        if status == "ERROR":
            err = response_text or f"Process exited with code {exit_code}"

        return ExecutionResult(
            status=status,
            conversation_id=cid,
            duration_seconds=duration,
            raw_response=response_text,
            goal_complete=goal_complete,
            error_message=err,
        )
    except Exception:
        goal_complete = "GOAL_COMPLETE" in stripped
        return ExecutionResult(
            status="SUCCESS" if exit_code == 0 else "ERROR",
            conversation_id="",
            duration_seconds=0.0,
            raw_response=stripped,
            goal_complete=goal_complete,
            error_message=stripped if exit_code != 0 else None,
        )


# ==============================================================================
# 2. State Store
# ==============================================================================

@dataclass
class SessionState:
    active: bool = False
    mode: str = "local"
    target: str = ""
    branch: str = ""
    plan_path: str = ""
    round: int = 0
    max_rounds: int = 3
    conversation_id: str = ""
    last_error_signature: str = ""
    consecutive_identical_errors: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0


class StateStore:
    STATE_DIR_NAME = ".agy-goal"
    STATE_FILE_NAME = "state.json"

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.state_dir = self.workspace_root / self.STATE_DIR_NAME
        self.state_file = self.state_dir / self.STATE_FILE_NAME

    def load(self) -> SessionState:
        if not self.state_file.exists():
            return SessionState()
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SessionState(**data)
        except Exception:
            return SessionState()

    def save(self, state: SessionState) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        now = time.time()
        if not state.created_at:
            state.created_at = now
        state.updated_at = now
        temp_file = self.state_dir / f"{self.STATE_FILE_NAME}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(asdict(state), f, indent=2)
        temp_file.replace(self.state_file)

    def clear(self) -> None:
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except OSError:
                pass


# ==============================================================================
# 3. Circuit Breaker
# ==============================================================================

class CircuitBreakerError(Exception):
    def __init__(self, reason: str, escalation_report: str):
        super().__init__(reason)
        self.reason = reason
        self.escalation_report = escalation_report


class CircuitBreaker:
    def __init__(self, max_rounds: int = 3):
        self.max_rounds = max_rounds

    def check_pre_turn(self, state: SessionState) -> None:
        if state.round >= state.max_rounds:
            reason = f"Maximum continue rounds reached ({state.round}/{state.max_rounds})"
            report = self.format_escalation_report(
                state=state,
                reason=reason,
                blocker="Exceeded allowed turn count without reaching <!-- GOAL_COMPLETE -->.",
            )
            raise CircuitBreakerError(reason, report)

    def record_turn(self, state: SessionState, raw_response: str, error_message: Optional[str]) -> None:
        signature = self._compute_error_signature(error_message or raw_response)
        if signature and signature == state.last_error_signature:
            state.consecutive_identical_errors += 1
        else:
            state.last_error_signature = signature
            state.consecutive_identical_errors = 1 if signature else 0

        if state.consecutive_identical_errors >= 2:
            reason = "Identical error loop detected across 2 consecutive turns"
            report = self.format_escalation_report(
                state=state,
                reason=reason,
                blocker=(error_message or raw_response)[:300],
            )
            raise CircuitBreakerError(reason, report)

    def _compute_error_signature(self, text: str) -> str:
        if not text:
            return ""
        normalized = re.sub(r"\s+", " ", text).strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def format_escalation_report(self, state: SessionState, reason: str, blocker: str) -> str:
        lines = [
            "\n" + "=" * 60,
            "🛑 [CIRCUIT BREAKER TRIGGERED - EXECUTION HALTED]",
            "=" * 60,
            f"Reason:           {reason}",
            f"Current Branch:   {state.branch or 'N/A'}",
            f"Target:           {state.mode} ({state.target or 'local'})",
            f"Conversation ID:  {state.conversation_id or 'N/A'}",
            f"Rounds Run:       {state.round} / {state.max_rounds}",
            "",
            "[Blocker Summary]",
            f"{blocker.strip()}",
            "",
            "[Actionable Options for Human Partner]",
            "1. Inspect current branch code and run tests manually to diagnose.",
            '2. Provide specific fix instructions via: ./agy-goal/scripts/agy-goal.py continue "<exact fix>"',
            "3. Reset the active session via: ./agy-goal/scripts/agy-goal.py reset",
            "=" * 60 + "\n",
        ]
        return "\n".join(lines)


# ==============================================================================
# 4. Executor Interface & Workers
# ==============================================================================

class BaseExecutor(ABC):
    @abstractmethod
    def preflight_check(self) -> None:
        pass

    @abstractmethod
    def execute(self, prompt: str, is_continue: bool = False) -> ExecutionResult:
        pass

    @abstractmethod
    def sync_to_local(self) -> None:
        pass


class LocalExecutor(BaseExecutor):
    def __init__(self, workspace_root: Path, timeout: str = "20m"):
        self.workspace_root = workspace_root
        self.timeout = timeout

    def preflight_check(self) -> None:
        if not shutil.which("agy"):
            raise RuntimeError("[agy-goal] Error: 'agy' CLI is not found in PATH.")

    def execute(self, prompt: str, is_continue: bool = False) -> ExecutionResult:
        cmd = [
            "agy",
            "--mode", "accept-edits",
            "--print-timeout", self.timeout,
            "--output-format", "json",
        ]
        if is_continue:
            cmd.append("-c")
        cmd.extend(["-p", prompt])

        timeout_sec = parse_timeout_seconds(self.timeout)

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            raw = proc.stdout if proc.stdout else proc.stderr
            res = parse_agy_output(raw, exit_code=proc.returncode)
            res.git_diff_summary = self._get_git_summary()
            return res
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status="TIMEOUT",
                conversation_id="",
                duration_seconds=0.0,
                raw_response="Local agy execution timed out.",
                goal_complete=False,
                error_message="Local agy execution timed out.",
            )
        except Exception as e:
            return ExecutionResult(
                status="ERROR",
                conversation_id="",
                duration_seconds=0.0,
                raw_response=str(e),
                goal_complete=False,
                error_message=str(e),
            )

    def _get_git_summary(self) -> str:
        try:
            diff = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
            ).stdout.strip()
            return diff
        except Exception:
            return ""

    def sync_to_local(self) -> None:
        pass


class RemoteExecutor(BaseExecutor):
    DIFF_DELIMITER = "---AGY_GIT_DIFF---"

    def __init__(self, workspace_root: Path, target: str, branch: str, timeout: str = "20m"):
        self.workspace_root = workspace_root
        self.target = target
        self.branch = branch
        self.timeout = timeout
        self.repo_name = self.workspace_root.name

    def preflight_check(self) -> None:
        if self.branch in ("main", "master"):
            raise RuntimeError(
                f"[agy-goal] Error: Refusing to run on '{self.branch}' branch.\n"
                "Please create or switch to a feature branch (e.g. git checkout -b feat/my-task)."
            )
        if not shutil.which("gt"):
            raise RuntimeError("[agy-goal] Error: 'gt' CLI tool not found in PATH.")

    def push_initial_branch(self) -> None:
        try:
            st = subprocess.run(["git", "status", "--porcelain"], cwd=str(self.workspace_root), capture_output=True, text=True)
            if st.stdout.strip():
                subprocess.run(["git", "add", "-A"], cwd=str(self.workspace_root), check=True)
                subprocess.run(["git", "commit", "-m", "chore: prepare plan for remote agy execution"], cwd=str(self.workspace_root), check=True)
            subprocess.run(["git", "push", "-u", "origin", self.branch], cwd=str(self.workspace_root), check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"[agy-goal] Failed to push local branch '{self.branch}' to origin: {e}")

    def execute(self, prompt: str, is_continue: bool = False) -> ExecutionResult:
        remote_work_dir = os.environ.get("REMOTE_WORK_DIR", f"/workspace/{self.repo_name}")
        c_flag = "-c " if is_continue else ""

        remote_script = f"""
set -e
mkdir -p {remote_work_dir}
cd {remote_work_dir}
git fetch origin {self.branch}
git checkout {self.branch}
git pull origin {self.branch}
set +e
agy --mode accept-edits --print-timeout {self.timeout} --output-format json {c_flag}-p "{prompt}" > /tmp/agy_out.json
AGY_EXIT=$?
set -e
git add -A
DIFF_SUMMARY=""
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    git commit -m "feat(agy-remote): update code via agy"
    git push origin {self.branch}
    DIFF_SUMMARY=$(git diff --stat HEAD~1 2>/dev/null || true)
fi
cat /tmp/agy_out.json
echo "{self.DIFF_DELIMITER}"
echo "$DIFF_SUMMARY"
exit $AGY_EXIT
""".strip()

        cmd = ["gt", "exec", self.target, "bash", "-c", remote_script]
        timeout_sec = parse_timeout_seconds(self.timeout)

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            raw = proc.stdout if proc.stdout else proc.stderr
            diff_summary = ""
            if self.DIFF_DELIMITER in (raw or ""):
                json_part, _, diff_summary = raw.partition(self.DIFF_DELIMITER)
                raw = json_part
                diff_summary = diff_summary.strip()
            res = parse_agy_output(raw, exit_code=proc.returncode)
            res.git_diff_summary = diff_summary
            return res
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status="TIMEOUT",
                conversation_id="",
                duration_seconds=0.0,
                raw_response="Remote agy execution timed out.",
                goal_complete=False,
                error_message="Remote agy execution timed out.",
            )
        except Exception as e:
            return ExecutionResult(
                status="ERROR",
                conversation_id="",
                duration_seconds=0.0,
                raw_response=str(e),
                goal_complete=False,
                error_message=str(e),
            )

    def sync_to_local(self) -> None:
        try:
            subprocess.run(
                ["git", "pull", "origin", self.branch],
                cwd=str(self.workspace_root),
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"[agy-goal] Failed to sync remote branch '{self.branch}' to local: {e.stderr or e}")


# ==============================================================================
# 5. Work API & CLI Entrypoint
# ==============================================================================

class WorkAPI:
    def __init__(self, workspace_root: Optional[Path] = None, timeout: str = "20m"):
        self.workspace_root = workspace_root or Path.cwd()
        self.timeout = timeout
        self.state_store = StateStore(self.workspace_root)
        self.circuit_breaker = CircuitBreaker()

    def _get_current_branch(self) -> str:
        try:
            return subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except Exception:
            return "unknown"

    def start_plan(self, plan_path: str, remote_target: Optional[str] = None) -> int:
        plan_file = Path(plan_path)
        if not plan_file.is_absolute():
            plan_file = self.workspace_root / plan_path
        if not plan_file.exists():
            raise FileNotFoundError(f"[agy-goal] Error: Plan file not found: '{plan_path}'.")

        target = remote_target or os.environ.get("AGY_TARGET")
        mode = "remote" if target else "local"
        branch = self._get_current_branch()

        state = SessionState(
            active=True,
            mode=mode,
            target=target or "",
            branch=branch,
            plan_path=str(plan_file),
            round=0,
            max_rounds=3,
        )
        self.state_store.save(state)

        executor = (
            RemoteExecutor(self.workspace_root, target=target, branch=branch, timeout=self.timeout)
            if mode == "remote"
            else LocalExecutor(self.workspace_root, timeout=self.timeout)
        )
        executor.preflight_check()
        if isinstance(executor, RemoteExecutor):
            executor.push_initial_branch()

        try:
            rel_plan = plan_file.relative_to(self.workspace_root)
        except ValueError:
            rel_plan = plan_file

        prompt = f"/goal Implement Plan @{rel_plan}"
        return self._run_and_handle(executor, state, prompt, is_continue=False)

    def continue_plan(self, instructions: str = "") -> int:
        state = self.state_store.load()
        if not state.active:
            raise RuntimeError("[agy-goal] Error: No active agy-goal session found. Please start a plan first.")

        self.circuit_breaker.check_pre_turn(state)
        state.round += 1

        executor = (
            RemoteExecutor(self.workspace_root, target=state.target, branch=state.branch, timeout=self.timeout)
            if state.mode == "remote"
            else LocalExecutor(self.workspace_root, timeout=self.timeout)
        )
        executor.preflight_check()

        if instructions:
            prompt = f"Continue implementing the plan: {instructions}. Finish remaining tasks and ensure tests pass."
        else:
            prompt = "Continue implementing the plan. Check current progress, finish all remaining tasks, and ensure all tests pass."

        return self._run_and_handle(executor, state, prompt, is_continue=True)

    def _run_and_handle(self, executor, state: SessionState, prompt: str, is_continue: bool) -> int:
        try:
            res = executor.execute(prompt, is_continue=is_continue)
            state.conversation_id = res.conversation_id or state.conversation_id
            self.circuit_breaker.record_turn(state, res.raw_response, res.error_message)

            if res.goal_complete:
                state.active = False
                executor.sync_to_local()
                self._print_summary(res)
                self.state_store.save(state)
                return 0

            self._print_summary(res)
            self.state_store.save(state)
            return 1 if res.status == "ERROR" else 0

        except CircuitBreakerError as cb_err:
            executor.sync_to_local()
            print(cb_err.escalation_report)
            state.active = False
            self.state_store.save(state)
            return 10

    def _print_summary(self, res: ExecutionResult) -> None:
        print("\n" + "=" * 60)
        print("Status:         ", res.status)
        if res.conversation_id:
            print("Conversation ID:", res.conversation_id)
        print(f"Duration:        {res.duration_seconds:.1f}s")
        print("Goal Complete:  ", "YES" if res.goal_complete else "NO")
        print("=" * 60 + "\n")
        if res.raw_response:
            print(res.raw_response)

    def sync(self) -> None:
        state = self.state_store.load()
        if state.mode == "remote" and state.target and state.branch:
            RemoteExecutor(self.workspace_root, target=state.target, branch=state.branch).sync_to_local()
            print(f"[agy-goal] Synchronized remote branch '{state.branch}' to local.")
        else:
            print("[agy-goal] Local mode or inactive session; no sync needed.")

    def reset(self) -> None:
        self.state_store.clear()
        print("[agy-goal] Session state cleared.")

    def get_status(self) -> dict:
        state = self.state_store.load()
        return {
            "active": state.active,
            "mode": state.mode,
            "target": state.target,
            "branch": state.branch,
            "round": state.round,
            "max_rounds": state.max_rounds,
            "conversation_id": state.conversation_id,
        }


USAGE_HELP = """usage: agy-goal.py [-h] [--remote REMOTE] {continue,status,sync,reset} ... [plan]

Usage:
  agy-goal.py <path/to/plan.md> [--remote <target>]   Implement a plan file via /goal
  agy-goal.py continue [instructions...]               Continue plan implementation or supply feedback
  agy-goal.py status                                   Show active session status
  agy-goal.py sync                                     Synchronize remote changes to local workspace
  agy-goal.py reset                                    Clear active session state
  agy-goal.py -h, --help                               Show this help message
"""


def main():
    if len(sys.argv) < 2:
        print(USAGE_HELP, file=sys.stderr)
        sys.exit(1)

    first_arg = sys.argv[1]
    if first_arg in ("-h", "--help", "help"):
        print(USAGE_HELP)
        sys.exit(0)

    api = WorkAPI()

    try:
        if first_arg == "continue":
            instructions = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
            sys.exit(api.continue_plan(instructions))
        elif first_arg == "status":
            st = api.get_status()
            print("Active:          ", st["active"])
            print("Mode:            ", st["mode"])
            if st["target"]:
                print("Target:          ", st["target"])
            print("Branch:          ", st["branch"])
            print(f"Rounds:           {st['round']} / {st['max_rounds']}")
            if st["conversation_id"]:
                print("Conversation ID: ", st["conversation_id"])
            sys.exit(0)
        elif first_arg == "sync":
            api.sync()
            sys.exit(0)
        elif first_arg == "reset":
            api.reset()
            sys.exit(0)
        else:
            plan_parser = argparse.ArgumentParser(
                prog="agy-goal.py",
                description="agy-goal: Multi-turn runner for AGY plan execution (Local & Remote)",
                add_help=True,
            )
            plan_parser.add_argument("plan", help="Path to implementation plan markdown file")
            plan_parser.add_argument("--remote", help="Remote target ID/node for gt exec")
            args = plan_parser.parse_args(sys.argv[1:])
            sys.exit(api.start_plan(args.plan, remote_target=args.remote))
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
