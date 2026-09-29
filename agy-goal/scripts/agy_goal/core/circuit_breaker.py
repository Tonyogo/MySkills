import hashlib
import re
from typing import Optional
from agy_goal.core.state import SessionState

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
        # Normalize whitespace and numbers/line markers to detect semantic loops
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
            '2. Provide specific fix instructions via: agy-goal.sh continue "<exact fix>"',
            "3. Reset the active session via: agy-goal.sh reset",
            "=" * 60 + "\n",
        ]
        return "\n".join(lines)
