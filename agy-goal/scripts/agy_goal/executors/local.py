import os
import shutil
import subprocess
from pathlib import Path
from agy_goal.executors.base import BaseExecutor, parse_timeout_seconds
from agy_goal.core.result_parser import parse_agy_output, ExecutionResult

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
        # Local execution modifies workspace directly; sync is a no-op
        pass
