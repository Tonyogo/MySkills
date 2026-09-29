import os
import shutil
import subprocess
from pathlib import Path
from agy_goal.executors.base import BaseExecutor, parse_timeout_seconds
from agy_goal.core.result_parser import parse_agy_output, ExecutionResult

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
                f"[agy-goal] Error: Refusing to run on 'main' or 'master' branch (current: '{self.branch}').\n"
                "Please create or switch to a feature branch (e.g. git checkout -b feat/my-task)."
            )
        if not shutil.which("gt"):
            raise RuntimeError("[agy-goal] Error: 'gt' CLI tool not found in PATH.")

    def push_initial_branch(self) -> None:
        """Stage uncommitted changes/plan files and push branch to origin."""
        try:
            # Check if there are changes to commit
            st = subprocess.run(["git", "status", "--porcelain"], cwd=str(self.workspace_root), capture_output=True, text=True)
            if st.stdout.strip():
                subprocess.run(["git", "add", "-A"], cwd=str(self.workspace_root), check=True)
                subprocess.run(["git", "commit", "-m", "chore: prepare plan for remote agy execution"], cwd=str(self.workspace_root), check=True)
            # Push upstream
            subprocess.run(["git", "push", "-u", "origin", self.branch], cwd=str(self.workspace_root), check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"[agy-goal] Failed to push local branch '{self.branch}' to origin: {e}")

    def execute(self, prompt: str, is_continue: bool = False) -> ExecutionResult:
        remote_work_dir = os.environ.get("REMOTE_WORK_DIR", f"/workspace/{self.repo_name}")
        c_flag = "-c " if is_continue else ""

        # Compose single remote payload
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
        """Pulls remote changes to local workspace."""
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
