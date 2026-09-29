import os
import subprocess
from pathlib import Path
from typing import Optional

from agy_goal.core.state import StateStore, SessionState
from agy_goal.core.circuit_breaker import CircuitBreaker, CircuitBreakerError
from agy_goal.executors.local import LocalExecutor
from agy_goal.executors.remote import RemoteExecutor

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

        prompt = f"/goal Implement Plan @{plan_file}"
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

    def _print_summary(self, res) -> None:
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
