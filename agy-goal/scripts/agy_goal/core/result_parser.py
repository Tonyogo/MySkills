import json
from dataclasses import dataclass
from typing import Optional

@dataclass
class ExecutionResult:
    status: str
    conversation_id: str
    duration_seconds: float
    raw_response: str
    goal_complete: bool
    git_diff_summary: str = ""
    error_message: Optional[str] = None

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
        # Fallback to plain text
        goal_complete = "GOAL_COMPLETE" in stripped
        return ExecutionResult(
            status="SUCCESS" if exit_code == 0 else "ERROR",
            conversation_id="",
            duration_seconds=0.0,
            raw_response=stripped,
            goal_complete=goal_complete,
            error_message=stripped if exit_code != 0 else None,
        )
