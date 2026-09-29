import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

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
