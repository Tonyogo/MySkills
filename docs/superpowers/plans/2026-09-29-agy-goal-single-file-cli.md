# agy-goal Single-File Python CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the `agy-goal` Python multi-module package and shell wrapper into a single, self-contained executable Python script (`agy-goal/scripts/agy-goal.py`) to reduce architectural weight while preserving all core capabilities (Local/Remote Worker via `gt exec`, Circuit Breaker, State Store, and Result Parser).

**Architecture:** Single executable Python script (`agy-goal/scripts/agy-goal.py`) with zero third-party dependencies using Python 3.8+ standard library. Directly invokable with shebang `#!/usr/bin/env python3`. Removes `agy-goal.sh` and the `agy_goal/` multi-file package.

**Tech Stack:** Python 3.8+ (standard library: `argparse`, `json`, `subprocess`, `hashlib`, `dataclasses`, `pathlib`, `unittest`).

**Spec:** `docs/superpowers/specs/2026-09-29-agy-goal-remote-executor-design.md` and approved in-chat simplification design.

## Global Constraints

- Pure Python 3.8+ standard library implementation; no third-party package dependencies (zero `pip install`).
- Script must be directly executable: starts with `#!/usr/bin/env python3` and has executable permissions (`chmod +x`).
- Retain all core functional guarantees:
  - BaseExecutor interface with LocalExecutor and RemoteExecutor.
  - Remote closed-loop verification via `gt exec` (zero local pull noise during intermediate rounds; local pull only upon `GOAL_COMPLETE` or circuit breaker halt).
  - Main/master branch protection on remote runs.
  - Circuit Breaker: maximum 3 continue turns per session; consecutive identical error loop detection; structured escalation reports.
  - Session state tracking in `.agy-goal/state.json`.
- All tests must pass cleanly using `python3 -m unittest`.

## Review Focus

1. **Executable Shebang & Permissions**: `agy-goal.py` must run directly as `./scripts/agy-goal.py` as well as via `python3 ./scripts/agy-goal.py`.
2. **Import Cleanliness**: Since `agy-goal.py` has a hyphen in its filename, test suites importing it as a module must import it dynamically or via a clean helper without syntax errors.
3. **Removal of Shell Wrapper**: Ensure no documentation or tests still reference the deleted `agy-goal.sh`.
4. **Preservation of Remote Delimiter & Git Diff Extraction**: Ensure `---AGY_GIT_DIFF---` parsing and timeout parsing remain intact in the consolidated file.
5. **Session State Compatibility**: Ensure `.agy-goal/state.json` format and lifecycle remain 100% consistent with existing sessions.

---

### Task 1: Create Consolidated `agy-goal/scripts/agy-goal.py`

**Files:**
- Create: `agy-goal/scripts/agy-goal.py`
- Test: `agy-goal/tests/test_single_file_compilation.py`

**Interfaces:**
- Produces:
  - `ExecutionResult`, `parse_timeout_seconds`, `parse_agy_output`
  - `SessionState`, `StateStore`
  - `CircuitBreakerError`, `CircuitBreaker`
  - `BaseExecutor`, `LocalExecutor`, `RemoteExecutor`
  - `WorkAPI`
  - `main()` CLI entrypoint

- [ ] **Step 1: Write a compilation and import test for the single file script**

```python
# agy-goal/tests/test_single_file_compilation.py
import unittest
import importlib.util
from pathlib import Path

class TestSingleFileCompilation(unittest.TestCase):
    def test_script_exists_and_loads(self):
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "agy-goal.py"
        self.assertTrue(script_path.exists(), "agy-goal.py must exist")

        spec = importlib.util.spec_from_file_location("agy_goal_cli", script_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check required classes exist
        self.assertTrue(hasattr(module, "WorkAPI"))
        self.assertTrue(hasattr(module, "CircuitBreaker"))
        self.assertTrue(hasattr(module, "StateStore"))
        self.assertTrue(hasattr(module, "LocalExecutor"))
        self.assertTrue(hasattr(module, "RemoteExecutor"))
        self.assertTrue(hasattr(module, "parse_agy_output"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest agy-goal/tests/test_single_file_compilation.py`
Expected: FAIL (agy-goal.py does not exist yet)

- [ ] **Step 3: Implement `agy-goal/scripts/agy-goal.py`**

Consolidate all logic into `agy-goal/scripts/agy-goal.py` with `#!/usr/bin/env python3`:

```python
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


def main():
    parser = argparse.ArgumentParser(
        description="agy-goal: Multi-turn runner for AGY plan execution (Local & Remote)",
        add_help=True,
    )
    subparsers = parser.add_subparsers(dest="command")

    cont_parser = subparsers.add_parser("continue", help="Continue plan implementation or supply feedback")
    cont_parser.add_argument("instructions", nargs="*", help="Optional feedback instructions")

    subparsers.add_parser("status", help="Show active session status")
    subparsers.add_parser("sync", help="Synchronize remote changes to local workspace")
    subparsers.add_parser("reset", help="Clear active session state")

    parser.add_argument("plan", nargs="?", help="Path to implementation plan markdown file")
    parser.add_argument("--remote", help="Remote target ID/node for gt exec")

    args = parser.parse_args()
    api = WorkAPI()

    try:
        if args.command == "continue":
            instructions = " ".join(args.instructions) if args.instructions else ""
            sys.exit(api.continue_plan(instructions))
        elif args.command == "status":
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
        elif args.command == "sync":
            api.sync()
            sys.exit(0)
        elif args.command == "reset":
            api.reset()
            sys.exit(0)
        elif args.plan:
            sys.exit(api.start_plan(args.plan, remote_target=args.remote))
        else:
            parser.print_help()
            sys.exit(1)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```
Make `agy-goal/scripts/agy-goal.py` executable (`chmod +x`).

- [ ] **Step 4: Run compilation test to verify it passes**

Run: `python3 -m unittest agy-goal/tests/test_single_file_compilation.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agy-goal/scripts/agy-goal.py agy-goal/tests/test_single_file_compilation.py
git commit -m "feat(agy-goal): implement single-file Python CLI script"
```

---

### Task 2: Consolidate Unified Test Suite (`tests/test_agy_goal.py`)

**Files:**
- Create: `agy-goal/tests/test_agy_goal.py`
- Test: `agy-goal/tests/test_agy_goal.py`

**Interfaces:**
- Consumes: `agy-goal/scripts/agy-goal.py` (via dynamic import loader)
- Tests:
  - `parse_agy_output`, `parse_timeout_seconds`
  - `StateStore`, `SessionState`
  - `CircuitBreaker`, `CircuitBreakerError`
  - `LocalExecutor` (with mock agy)
  - `RemoteExecutor` (with mock gt)
  - `WorkAPI`

- [ ] **Step 1: Write unified test suite in `test_agy_goal.py`**

```python
# agy-goal/tests/test_agy_goal.py
import unittest
import importlib.util
import os
import shutil
import stat
import tempfile
from pathlib import Path

# Dynamically import agy-goal.py
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "agy-goal.py"
spec = importlib.util.spec_from_file_location("agy_goal", SCRIPT_PATH)
agy_goal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agy_goal)

parse_agy_output = agy_goal.parse_agy_output
parse_timeout_seconds = agy_goal.parse_timeout_seconds
StateStore = agy_goal.StateStore
SessionState = agy_goal.SessionState
CircuitBreaker = agy_goal.CircuitBreaker
CircuitBreakerError = agy_goal.CircuitBreakerError
LocalExecutor = agy_goal.LocalExecutor
RemoteExecutor = agy_goal.RemoteExecutor
WorkAPI = agy_goal.WorkAPI


class TestParserAndTimeout(unittest.TestCase):
    def test_parse_timeout_seconds(self):
        self.assertEqual(parse_timeout_seconds("20m"), 1200)
        self.assertEqual(parse_timeout_seconds("30s"), 30)
        self.assertEqual(parse_timeout_seconds("1h"), 3600)
        self.assertEqual(parse_timeout_seconds("500"), 500)
        self.assertIsNone(parse_timeout_seconds("invalid"))

    def test_parse_valid_json_goal_complete(self):
        sample = '{"conversation_id": "c1", "status": "SUCCESS", "duration_seconds": 10.0, "response": "OK\\n<!-- GOAL_COMPLETE -->"}'
        res = parse_agy_output(sample, exit_code=0)
        self.assertEqual(res.status, "SUCCESS")
        self.assertTrue(res.goal_complete)

    def test_parse_empty_and_fallback(self):
        res = parse_agy_output("", exit_code=1)
        self.assertEqual(res.status, "ERROR")
        self.assertFalse(res.goal_complete)


class TestStateStore(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.store = StateStore(Path(self.td))

    def tearDown(self):
        shutil.rmtree(self.td)

    def test_save_and_load(self):
        st = SessionState(active=True, mode="remote", target="test", round=1)
        self.store.save(st)
        loaded = self.store.load()
        self.assertTrue(loaded.active)
        self.assertEqual(loaded.mode, "remote")
        self.assertEqual(loaded.round, 1)


class TestCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.cb = CircuitBreaker(max_rounds=3)

    def test_max_rounds(self):
        st = SessionState(active=True, round=3, max_rounds=3)
        with self.assertRaises(CircuitBreakerError):
            self.cb.check_pre_turn(st)

    def test_stagnation_detection(self):
        st = SessionState(active=True, round=1, max_rounds=3)
        self.cb.record_turn(st, "err1", "err1")
        st.round = 2
        with self.assertRaises(CircuitBreakerError):
            self.cb.record_turn(st, "err1", "err1")


class TestExecutors(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.ws = Path(self.td)
        self.bin_dir = self.ws / "bin"
        self.bin_dir.mkdir()
        self.old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.bin_dir}:{self.old_path}"

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        shutil.rmtree(self.td)

    def _mock_bin(self, name: str, output: str, exit_code: int = 0):
        b = self.bin_dir / name
        b.write_text(f"#!/usr/bin/env bash\ncat << 'EOF'\n{output}\nEOF\nexit {exit_code}\n")
        b.chmod(b.stat().st_mode | stat.S_IEXEC)

    def test_local_executor(self):
        self._mock_bin("agy", '{"conversation_id":"c1","status":"SUCCESS","duration_seconds":1.0,"response":"Done\\n<!-- GOAL_COMPLETE -->"}')
        ex = LocalExecutor(self.ws)
        res = ex.execute("run")
        self.assertTrue(res.goal_complete)

    def test_remote_executor_diff_parsing(self):
        payload = '{"conversation_id":"r1","status":"SUCCESS","duration_seconds":1.0,"response":"Remote\\n<!-- GOAL_COMPLETE -->"}\n---AGY_GIT_DIFF---\n a.py | 1 +\n 1 file changed, 1 insertion(+)'
        self._mock_bin("gt", payload)
        ex = RemoteExecutor(self.ws, target="node", branch="feat/x")
        res = ex.execute("run")
        self.assertTrue(res.goal_complete)
        self.assertIn("1 file changed", res.git_diff_summary)


class TestWorkAPI(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.ws = Path(self.td)
        self.api = WorkAPI(self.ws)

    def tearDown(self):
        shutil.rmtree(self.td)

    def test_relative_plan_prompt(self):
        p_dir = self.ws / "docs"
        p_dir.mkdir()
        plan = p_dir / "p.md"
        plan.write_text("# Plan")
        prompts = []
        self.api._run_and_handle = lambda ex, st, prompt, is_cont: prompts.append(prompt) or 0
        self.api.start_plan(str(plan))
        self.assertEqual(prompts[0], "/goal Implement Plan @docs/p.md")
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python3 -m unittest agy-goal/tests/test_agy_goal.py`
Expected: Ran 9 tests ... OK

- [ ] **Step 3: Commit**

```bash
git add agy-goal/tests/test_agy_goal.py
git commit -m "test(agy-goal): add unified test suite for single-file python CLI"
```

---

### Task 3: Remove Obsolete Multi-Package & Shell Wrapper Files

**Files:**
- Delete: `agy-goal/scripts/agy_goal/` (entire directory)
- Delete: `agy-goal/scripts/agy-goal.sh`
- Delete obsolete individual test files replaced by `test_agy_goal.py`:
  - `agy-goal/tests/test_circuit_breaker.py`
  - `agy-goal/tests/test_local_executor.py`
  - `agy-goal/tests/test_remote_executor.py`
  - `agy-goal/tests/test_result_parser.py`
  - `agy-goal/tests/test_state_store.py`
  - `agy-goal/tests/test_work_api.py`
  - `agy-goal/tests/test_single_file_compilation.py`
- Modify: `agy-goal/tests/test_cli_integration.sh`
- Modify: `agy-goal/tests/test_decision_gate.sh`
- Modify: `agy-goal/tests/run_all_tests.sh`

- [ ] **Step 1: Update `test_cli_integration.sh` to target `agy-goal.py` directly**

```bash
#!/usr/bin/env bash
# agy-goal/tests/test_cli_integration.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$SCRIPT_DIR/scripts/agy-goal.py"

echo "=== Test 1: CLI Help output ==="
"$BIN" -h | grep -q "usage:"
"$BIN" --help | grep -q "agy-goal"
echo "PASS: Help output"

echo "=== Test 2: Missing arguments ==="
OUTPUT="$("$BIN" 2>&1 || true)"
echo "$OUTPUT" | grep -q "usage:"
echo "PASS: Missing arguments handled"

echo "=== Test 3: Plan file validation ==="
OUTPUT="$("$BIN" nonexistent_plan_file_12345.md 2>&1 || true)"
echo "$OUTPUT" | grep -q "Error: Plan file not found"
echo "PASS: Plan file validation handled"

echo "=== Test 4: Status and Reset commands ==="
"$BIN" reset
STATUS="$("$BIN" status)"
echo "$STATUS" | grep -q "Active:           False"
echo "PASS: Reset and status handled"

echo "=== All CLI integration tests passed! ==="
```

- [ ] **Step 2: Update `test_decision_gate.sh` to target `agy-goal.py` directly**

Update `BIN="$SCRIPT_DIR/scripts/agy-goal.py"` in `agy-goal/tests/test_decision_gate.sh`.

- [ ] **Step 3: Update `run_all_tests.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Running Python Unit Tests ==="
python3 -m unittest "$SCRIPT_DIR/test_agy_goal.py" -v

echo "=== Running CLI Integration Tests ==="
bash "$SCRIPT_DIR/test_cli_integration.sh"

echo "=== Running Decision Gate Mock Tests ==="
bash "$SCRIPT_DIR/test_decision_gate.sh"

echo "All agy-goal tests passed successfully."
```

- [ ] **Step 4: Remove obsolete directory and files**

```bash
rm -rf agy-goal/scripts/agy_goal agy-goal/scripts/agy-goal.sh
rm -f agy-goal/tests/test_circuit_breaker.py \
      agy-goal/tests/test_local_executor.py \
      agy-goal/tests/test_remote_executor.py \
      agy-goal/tests/test_result_parser.py \
      agy-goal/tests/test_state_store.py \
      agy-goal/tests/test_work_api.py \
      agy-goal/tests/test_single_file_compilation.py
```

- [ ] **Step 5: Run `run_all_tests.sh` to ensure all tests pass**

Run: `bash agy-goal/tests/run_all_tests.sh`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add agy-goal/
git commit -m "refactor(agy-goal): remove multi-package directories and update test drivers"
```

---

### Task 4: Update `SKILL.md` Documentation

**Files:**
- Modify: `agy-goal/SKILL.md`

- [ ] **Step 1: Update `agy-goal/SKILL.md` command references**

Replace any remaining references to `agy-goal.sh` with `./agy-goal/scripts/agy-goal.py`:
- `agy-goal.py path/to/plan.md`
- `agy-goal.py path/to/plan.md --remote <target>`
- `agy-goal.py continue [instructions...]`
- `agy-goal.py status`, `agy-goal.py sync`, `agy-goal.py reset`

- [ ] **Step 2: Run test suite to verify everything remains green**

Run: `bash agy-goal/tests/run_all_tests.sh`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add agy-goal/SKILL.md
git commit -m "docs(agy-goal): update SKILL.md for direct agy-goal.py python CLI usage"
```
