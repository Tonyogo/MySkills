from abc import ABC, abstractmethod
from agy_goal.core.result_parser import ExecutionResult

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
