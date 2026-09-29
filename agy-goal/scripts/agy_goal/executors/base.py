from abc import ABC, abstractmethod
from typing import Optional
from agy_goal.core.result_parser import ExecutionResult

def parse_timeout_seconds(timeout_str: str) -> Optional[int]:
    """Parse a timeout string (e.g. '20m', '30s', '1h', '600') to seconds."""
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
