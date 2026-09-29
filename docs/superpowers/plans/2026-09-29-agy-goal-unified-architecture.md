# agy-goal Unified Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor and upgrade the `agy-goal` skill from a single local bash script into a modular architecture featuring a Python core engine with an Executor interface (Local and Remote Worker via `gt exec`), state management, circuit breakers, and closed-loop remote verification.

**Architecture:** Python 3 standard library core located in `agy-goal/scripts/agy_goal/` exposing a Work API, Circuit Breaker, Result Parser, and `BaseExecutor` with `LocalExecutor` and `RemoteExecutor`. A POSIX shell script wrapper `agy-goal.sh` preserves 100% backward compatibility for local runs while adding `--remote` and `AGY_TARGET` capabilities.

**Tech Stack:** Python 3.8+ (standard library only: `argparse`, `json`, `subprocess`, `hashlib`, `dataclasses`, `pathlib`, `unittest`), Bash.

**Spec:** `docs/superpowers/specs/2026-09-29-agy-goal-remote-executor-design.md`

## Global Constraints

- Pure Python 3.8+ standard library implementation; no third-party package dependencies (zero `pip install`).
- Remote execution must keep intermediate iterations and testing closed-loop on the remote host via `gt exec`; local `git pull` happens only when `GOAL_COMPLETE` is achieved or when circuit breaker halts.
- Default execution timeout is 20 minutes (`20m` / 1200 seconds).
- Execution on `main` or `master` branch is strictly rejected for remote runs.
- Hard circuit breaker: Maximum 3 `continue` turns per session; identical error hashes across 2 consecutive turns halts execution.
- All tests must run cleanly via `python3 -m unittest` without requiring external test frameworks.

## Review Focus

1. **Empty/Non-JSON response handling**: When `agy` or `gt exec` fails abruptly with empty or unparseable output, Result Parser must degrade gracefully without crashing.
2. **Main/Master branch guard**: Remote worker must refuse to push from `main` or `master` to protect production branches.
3. **Consecutive error signature hashing**: Circuit breaker must correctly detect recurring errors even if whitespace or formatting differs slightly.
4. **Deferred sync guarantee**: Remote worker must not pull commits to local repository during intermediate iterations (`GOAL_COMPLETE: NO`).
5. **State session recovery**: `continue` command without arguments must automatically locate active session, resume the appropriate executor (local or remote), and advance the round counter atomically.

---

### Task 1: Result Parser & Data Models (`core/result_parser.py`)

**Files:**
- Create: `agy-goal/scripts/agy_goal/__init__.py`
- Create: `agy-goal/scripts/agy_goal/core/__init__.py`
- Create: `agy-goal/scripts/agy_goal/core/result_parser.py`
- Test: `agy-goal/tests/test_result_parser.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass
  class ExecutionResult:
      status: str              # "SUCCESS", "ERROR", "TIMEOUT", "MALFORMED"
      conversation_id: str
      duration_seconds: float
      raw_response: str
      goal_complete: bool
      git_diff_summary: str
      error_message: Optional[str] = None

  def parse_agy_output(raw_output: str, exit_code: int = 0) -> ExecutionResult
  ```

- [ ] **Step 1: Write the failing tests for Result Parser**

```python
# agy-goal/tests/test_result_parser.py
import unittest
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from agy_goal.core.result_parser import parse_agy_output, ExecutionResult

class TestResultParser(unittest.TestCase):
    def test_parse_valid_json_with_goal_complete(self):
        sample = '{"conversation_id": "c1", "status": "SUCCESS", "duration_seconds": 12.5, "response": "Done!\\n<!-- GOAL_COMPLETE -->"}'
        res = parse_agy_output(sample, exit_code=0)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.conversation_id, "c1")
        self.assertEqual(res.duration_seconds, 12.5)
        self.assertTrue(res.goal_complete)
        self.assertIn("Done!", res.raw_response)

    def test_parse_valid_json_without_goal_complete(self):
        sample = '{"conversation_id": "c2", "status": "ERROR", "duration_seconds": 5.0, "response": "Failed at test_foo"}'
        res = parse_agy_output(sample, exit_code=1)
        self.assertEqual(res.status, "ERROR")
        self.assertEqual(res.conversation_id, "c2")
        self.assertFalse(res.goal_complete)
        self.assertIn("Failed at test_foo", res.raw_response)

    def test_parse_malformed_json_fallback(self):
        sample = "Internal fatal error: connection refused"
        res = parse_agy_output(sample, exit_code=1)
        self.assertEqual(res.status, "ERROR")
        self.assertFalse(res.goal_complete)
        self.assertIn("Internal fatal error", res.raw_response)

    def test_parse_empty_output(self):
        res = parse_agy_output("", exit_code=1)
        self.assertEqual(res.status, "ERROR")
        self.assertFalse(res.goal_complete)
        self.assertEqual(res.raw_response, "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest agy-goal/tests/test_result_parser.py`
Expected: FAIL (ModuleNotFoundError: No module named 'agy_goal')

- [ ] **Step 3: Implement minimal Result Parser**

Create `agy-goal/scripts/agy_goal/__init__.py` (empty) and `agy-goal/scripts/agy_goal/core/__init__.py` (empty).
Implement `agy-goal/scripts/agy_goal/core/result_parser.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest agy-goal/tests/test_result_parser.py`
Expected: Ran 4 tests ... OK

- [ ] **Step 5: Commit**

```bash
git add agy-goal/scripts/agy_goal/ agy-goal/tests/test_result_parser.py
git commit -m "feat(agy-goal): implement result parser and execution result data models"
```

---

### Task 2: State Store (`core/state.py`)

**Files:**
- Create: `agy-goal/scripts/agy_goal/core/state.py`
- Test: `agy-goal/tests/test_state_store.py`

**Interfaces:**
- Consumes: Standard Python `dataclasses`, `json`, `pathlib`
- Produces:
  ```python
  @dataclass
  class SessionState:
      active: bool = False
      mode: str = "local"           # "local" | "remote"
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
      def __init__(self, workspace_root: Path)
      def load() -> SessionState
      def save(state: SessionState) -> None
      def clear() -> None
  ```

- [ ] **Step 1: Write failing tests for StateStore**

```python
# agy-goal/tests/test_state_store.py
import unittest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agy_goal.core.state import StateStore, SessionState

class TestStateStore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir)
        self.store = StateStore(self.workspace)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_load_default_when_no_file(self):
        state = self.store.load()
        self.assertFalse(state.active)
        self.assertEqual(state.round, 0)

    def test_save_and_load_roundtrip(self):
        state = SessionState(
            active=True,
            mode="remote",
            target="test-server",
            branch="feat/test",
            round=1,
            conversation_id="conv-123"
        )
        self.store.save(state)
        loaded = self.store.load()
        self.assertTrue(loaded.active)
        self.assertEqual(loaded.mode, "remote")
        self.assertEqual(loaded.target, "test-server")
        self.assertEqual(loaded.conversation_id, "conv-123")
        self.assertEqual(loaded.round, 1)

    def test_clear_state(self):
        state = SessionState(active=True, round=2)
        self.store.save(state)
        self.store.clear()
        reloaded = self.store.load()
        self.assertFalse(reloaded.active)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest agy-goal/tests/test_state_store.py`
Expected: FAIL (ModuleNotFoundError: No module named 'agy_goal.core.state')

- [ ] **Step 3: Implement StateStore**

Implement `agy-goal/scripts/agy_goal/core/state.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest agy-goal/tests/test_state_store.py`
Expected: Ran 3 tests ... OK

- [ ] **Step 5: Commit**

```bash
git add agy-goal/scripts/agy_goal/core/state.py agy-goal/tests/test_state_store.py
git commit -m "feat(agy-goal): implement persistent state store for session tracking"
```

---

### Task 3: Circuit Breaker (`core/circuit_breaker.py`)

**Files:**
- Create: `agy-goal/scripts/agy_goal/core/circuit_breaker.py`
- Test: `agy-goal/tests/test_circuit_breaker.py`

**Interfaces:**
- Consumes: `SessionState`
- Produces:
  ```python
  class CircuitBreakerError(Exception):
      reason: str
      escalation_report: str

  class CircuitBreaker:
      def check_pre_turn(self, state: SessionState) -> None
      def record_turn(self, state: SessionState, raw_response: str, error_message: Optional[str]) -> None
      def format_escalation_report(self, state: SessionState, reason: str, blocker: str) -> str
  ```

- [ ] **Step 1: Write failing tests for CircuitBreaker**

```python
# agy-goal/tests/test_circuit_breaker.py
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agy_goal.core.state import SessionState
from agy_goal.core.circuit_breaker import CircuitBreaker, CircuitBreakerError

class TestCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.cb = CircuitBreaker()

    def test_pre_turn_passes_under_limit(self):
        state = SessionState(active=True, round=2, max_rounds=3)
        # Should not raise
        self.cb.check_pre_turn(state)

    def test_pre_turn_halts_at_max_rounds(self):
        state = SessionState(active=True, round=3, max_rounds=3)
        with self.assertRaises(CircuitBreakerError) as ctx:
            self.cb.check_pre_turn(state)
        self.assertIn("Maximum continue rounds reached (3/3)", ctx.exception.reason)

    def test_identical_error_loop_detection(self):
        state = SessionState(active=True, round=1, max_rounds=3)
        error_msg = "AssertionError: line 42 failed"

        # Turn 1
        self.cb.record_turn(state, raw_response="Some text", error_message=error_msg)
        self.assertEqual(state.consecutive_identical_errors, 1)

        # Turn 2 with identical error
        state.round = 2
        with self.assertRaises(CircuitBreakerError) as ctx:
            self.cb.record_turn(state, raw_response="Some text again", error_message=error_msg)
        self.assertIn("Identical error loop detected", ctx.exception.reason)
        self.assertEqual(state.consecutive_identical_errors, 2)

    def test_reset_consecutive_errors_on_different_output(self):
        state = SessionState(active=True, round=1, max_rounds=3)
        self.cb.record_turn(state, raw_response="Error A", error_message="Error A")
        self.assertEqual(state.consecutive_identical_errors, 1)

        state.round = 2
        self.cb.record_turn(state, raw_response="Error B", error_message="Error B")
        self.assertEqual(state.consecutive_identical_errors, 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest agy-goal/tests/test_circuit_breaker.py`
Expected: FAIL (ModuleNotFoundError: No module named 'agy_goal.core.circuit_breaker')

- [ ] **Step 3: Implement CircuitBreaker**

Implement `agy-goal/scripts/agy_goal/core/circuit_breaker.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest agy-goal/tests/test_circuit_breaker.py`
Expected: Ran 4 tests ... OK

- [ ] **Step 5: Commit**

```bash
git add agy-goal/scripts/agy_goal/core/circuit_breaker.py agy-goal/tests/test_circuit_breaker.py
git commit -m "feat(agy-goal): implement anti-thrashing circuit breaker"
```

---

### Task 4: Base Executor Interface & Local Worker (`executors/base.py`, `executors/local.py`)

**Files:**
- Create: `agy-goal/scripts/agy_goal/executors/__init__.py`
- Create: `agy-goal/scripts/agy_goal/executors/base.py`
- Create: `agy-goal/scripts/agy_goal/executors/local.py`
- Test: `agy-goal/tests/test_local_executor.py`

**Interfaces:**
- Produces:
  ```python
  class BaseExecutor(ABC):
      @abstractmethod
      def preflight_check(self) -> None
      @abstractmethod
      def execute(self, prompt: str, is_continue: bool = False) -> ExecutionResult
      @abstractmethod
      def sync_to_local(self) -> None

  class LocalExecutor(BaseExecutor):
      def __init__(self, workspace_root: Path, timeout: str = "20m")
  ```

- [ ] **Step 1: Write failing tests for LocalExecutor**

```python
# agy-goal/tests/test_local_executor.py
import unittest
import tempfile
import shutil
import os
import stat
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agy_goal.executors.local import LocalExecutor

class TestLocalExecutor(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir)
        self.bin_dir = self.workspace / "bin"
        self.bin_dir.mkdir()
        self.old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.bin_dir}:{self.old_path}"

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        shutil.rmtree(self.test_dir)

    def _create_mock_agy(self, output: str, exit_code: int = 0):
        agy_bin = self.bin_dir / "agy"
        with open(agy_bin, "w") as f:
            f.write(f"#!/usr/bin/env bash\ncat << 'EOF'\n{output}\nEOF\nexit {exit_code}\n")
        agy_bin.chmod(agy_bin.stat().st_mode | stat.S_IEXEC)

    def test_preflight_missing_agy(self):
        executor = LocalExecutor(self.workspace)
        # Temporarily clear PATH
        os.environ["PATH"] = ""
        with self.assertRaises(RuntimeError) as ctx:
            executor.preflight_check()
        self.assertIn("not found in PATH", str(ctx.exception))

    def test_execute_success(self):
        mock_resp = '{"conversation_id":"c1","status":"SUCCESS","duration_seconds":1.2,"response":"Done\\n<!-- GOAL_COMPLETE -->"}'
        self._create_mock_agy(mock_resp, exit_code=0)
        executor = LocalExecutor(self.workspace)
        executor.preflight_check()
        res = executor.execute("Implement plan", is_continue=False)
        self.assertEqual(res.status, "SUCCESS")
        self.assertTrue(res.goal_complete)
        self.assertEqual(res.conversation_id, "c1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest agy-goal/tests/test_local_executor.py`
Expected: FAIL (ModuleNotFoundError: No module named 'agy_goal.executors')

- [ ] **Step 3: Implement BaseExecutor and LocalExecutor**

Create `agy-goal/scripts/agy_goal/executors/__init__.py` (empty).
Implement `agy-goal/scripts/agy_goal/executors/base.py`:

```python
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
```

Implement `agy-goal/scripts/agy_goal/executors/local.py`:

```python
import os
import shutil
import subprocess
from pathlib import Path
from agy_goal.executors.base import BaseExecutor
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

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest agy-goal/tests/test_local_executor.py`
Expected: Ran 2 tests ... OK

- [ ] **Step 5: Commit**

```bash
git add agy-goal/scripts/agy_goal/executors/ agy-goal/tests/test_local_executor.py
git commit -m "feat(agy-goal): implement BaseExecutor interface and LocalExecutor"
```

---

### Task 5: Remote Worker via `gt exec` (`executors/remote.py`)

**Files:**
- Create: `agy-goal/scripts/agy_goal/executors/remote.py`
- Test: `agy-goal/tests/test_remote_executor.py`

**Interfaces:**
- Consumes: `BaseExecutor`, `parse_agy_output`, `subprocess`
- Produces:
  ```python
  class RemoteExecutor(BaseExecutor):
      def __init__(self, workspace_root: Path, target: str, branch: str, timeout: str = "20m")
  ```

- [ ] **Step 1: Write failing tests for RemoteExecutor**

```python
# agy-goal/tests/test_remote_executor.py
import unittest
import tempfile
import shutil
import os
import stat
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agy_goal.executors.remote import RemoteExecutor

class TestRemoteExecutor(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir)
        self.bin_dir = self.workspace / "bin"
        self.bin_dir.mkdir()
        self.old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.bin_dir}:{self.old_path}"

    def tearDown(self):
        os.environ["PATH"] = self.old_path
        shutil.rmtree(self.test_dir)

    def _create_mock_gt(self, output: str, exit_code: int = 0):
        gt_bin = self.bin_dir / "gt"
        with open(gt_bin, "w") as f:
            f.write(f"#!/usr/bin/env bash\ncat << 'EOF'\n{output}\nEOF\nexit {exit_code}\n")
        gt_bin.chmod(gt_bin.stat().st_mode | stat.S_IEXEC)

    def test_preflight_blocks_main_branch(self):
        executor = RemoteExecutor(self.workspace, target="server-1", branch="main")
        with self.assertRaises(RuntimeError) as ctx:
            executor.preflight_check()
        self.assertIn("Refusing to run on 'main' or 'master'", str(ctx.exception))

    def test_preflight_missing_gt(self):
        executor = RemoteExecutor(self.workspace, target="server-1", branch="feat/foo")
        os.environ["PATH"] = ""
        with self.assertRaises(RuntimeError) as ctx:
            executor.preflight_check()
        self.assertIn("'gt' CLI tool not found", str(ctx.exception))

    def test_remote_execute_success(self):
        mock_payload = '{"conversation_id":"r1","status":"SUCCESS","duration_seconds":3.0,"response":"Remote Done\\n<!-- GOAL_COMPLETE -->"}'
        self._create_mock_gt(mock_payload, exit_code=0)
        executor = RemoteExecutor(self.workspace, target="server-1", branch="feat/foo")
        executor.preflight_check()
        res = executor.execute("Implement plan", is_continue=False)
        self.assertEqual(res.status, "SUCCESS")
        self.assertTrue(res.goal_complete)
        self.assertEqual(res.conversation_id, "r1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest agy-goal/tests/test_remote_executor.py`
Expected: FAIL (ModuleNotFoundError: No module named 'agy_goal.executors.remote')

- [ ] **Step 3: Implement RemoteExecutor**

Implement `agy-goal/scripts/agy_goal/executors/remote.py`:

```python
import os
import shutil
import subprocess
from pathlib import Path
from agy_goal.executors.base import BaseExecutor
from agy_goal.core.result_parser import parse_agy_output, ExecutionResult

class RemoteExecutor(BaseExecutor):
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
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    git commit -m "feat(agy-remote): update code via agy"
    git push origin {self.branch}
fi
cat /tmp/agy_out.json
exit $AGY_EXIT
""".strip()

        cmd = ["gt", "exec", self.target, "bash", "-c", remote_script]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
            )
            raw = proc.stdout if proc.stdout else proc.stderr
            return parse_agy_output(raw, exit_code=proc.returncode)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest agy-goal/tests/test_remote_executor.py`
Expected: Ran 3 tests ... OK

- [ ] **Step 5: Commit**

```bash
git add agy-goal/scripts/agy_goal/executors/remote.py agy-goal/tests/test_remote_executor.py
git commit -m "feat(agy-goal): implement RemoteExecutor with gt exec closed-loop execution"
```

---

### Task 6: Work API & Lifecycle Orchestrator (`core/work_api.py`)

**Files:**
- Create: `agy-goal/scripts/agy_goal/core/work_api.py`
- Test: `agy-goal/tests/test_work_api.py`

**Interfaces:**
- Consumes: `StateStore`, `CircuitBreaker`, `LocalExecutor`, `RemoteExecutor`
- Produces:
  ```python
  class WorkAPI:
      def start_plan(self, plan_path: str, remote_target: Optional[str] = None) -> int
      def continue_plan(self, instructions: str = "") -> int
      def get_status() -> dict
      def sync() -> None
      def reset() -> None
  ```

- [ ] **Step 1: Write failing tests for WorkAPI**

```python
# agy-goal/tests/test_work_api.py
import unittest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from agy_goal.core.work_api import WorkAPI

class TestWorkAPI(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir)
        self.api = WorkAPI(self.workspace)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_status_when_no_session(self):
        status = self.api.get_status()
        self.assertFalse(status["active"])

    def test_reset_clears_session(self):
        state = self.api.state_store.load()
        state.active = True
        self.api.state_store.save(state)
        self.api.reset()
        self.assertFalse(self.api.get_status()["active"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest agy-goal/tests/test_work_api.py`
Expected: FAIL (ModuleNotFoundError: No module named 'agy_goal.core.work_api')

- [ ] **Step 3: Implement WorkAPI**

Implement `agy-goal/scripts/agy_goal/core/work_api.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest agy-goal/tests/test_work_api.py`
Expected: Ran 2 tests ... OK

- [ ] **Step 5: Commit**

```bash
git add agy-goal/scripts/agy_goal/core/work_api.py agy-goal/tests/test_work_api.py
git commit -m "feat(agy-goal): implement WorkAPI lifecycle coordinator"
```

---

### Task 7: CLI Dispatcher, Shell Wrapper & End-to-End Tests (`cli.py`, `agy-goal.sh`)

**Files:**
- Create: `agy-goal/scripts/agy_goal/cli.py`
- Modify: `agy-goal/scripts/agy-goal.sh`
- Test: `agy-goal/tests/test_cli_integration.sh`
- Modify: `agy-goal/tests/run_all_tests.sh`

**Interfaces:**
- Command line arguments:
  ```bash
  agy-goal.sh <plan.md> [--remote <target>]
  agy-goal.sh continue [instructions...]
  agy-goal.sh status
  agy-goal.sh sync
  agy-goal.sh reset
  ```

- [ ] **Step 1: Write integration tests in `test_cli_integration.sh`**

```bash
#!/usr/bin/env bash
# agy-goal/tests/test_cli_integration.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$SCRIPT_DIR/scripts/agy-goal.sh"

echo "=== Test 1: CLI Help output ==="
"$BIN" -h | grep -q "Usage:"
"$BIN" --help | grep -q "agy-goal.sh"
echo "PASS: Help output"

echo "=== Test 2: Missing arguments ==="
OUTPUT="$("$BIN" 2>&1 || true)"
echo "$OUTPUT" | grep -q "Usage:"
echo "PASS: Missing arguments handled"

echo "=== Test 3: Plan file validation ==="
OUTPUT="$("$BIN" nonexistent_plan_file_12345.md 2>&1 || true)"
echo "$OUTPUT" | grep -q "Error: Plan file not found"
echo "PASS: Plan file validation handled"

echo "=== Test 4: Status and Reset commands ==="
"$BIN" reset
STATUS="$("$BIN" status)"
echo "$STATUS" | grep -q "Active: False"
echo "PASS: Reset and status handled"

echo "=== All CLI integration tests passed! ==="
```

- [ ] **Step 2: Implement `cli.py`**

Implement `agy-goal/scripts/agy_goal/cli.py`:

```python
import argparse
import sys
from pathlib import Path
from agy_goal.core.work_api import WorkAPI

def main():
    parser = argparse.ArgumentParser(
        description="agy-goal: Multi-turn runner for AGY plan execution (Local & Remote)",
        add_help=True,
    )
    subparsers = parser.add_subparsers(dest="command")

    # continue subcommand
    cont_parser = subparsers.add_parser("continue", help="Continue plan implementation or supply feedback")
    cont_parser.add_argument("instructions", nargs="*", help="Optional feedback instructions")

    # status subcommand
    subparsers.add_parser("status", help="Show active session status")

    # sync subcommand
    subparsers.add_parser("sync", help="Synchronize remote changes to local workspace")

    # reset subcommand
    subparsers.add_parser("reset", help="Clear active session state")

    # Default plan positional argument or flags
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

- [ ] **Step 3: Update `agy-goal.sh` to wrap `cli.py`**

Update `agy-goal/scripts/agy-goal.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

exec python3 -m agy_goal.cli "$@"
```

- [ ] **Step 4: Update `run_all_tests.sh` to run both unit tests and integration tests**

Update `agy-goal/tests/run_all_tests.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Running Python Unit Tests ==="
python3 -m unittest discover -s "$SCRIPT_DIR" -p "test_*.py" -v

echo "=== Running CLI Integration Tests ==="
bash "$SCRIPT_DIR/test_cli_integration.sh"

echo "All agy-goal tests passed successfully."
```

- [ ] **Step 5: Run all tests and verify PASS**

Run: `bash agy-goal/tests/run_all_tests.sh`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add agy-goal/scripts/agy-goal.sh agy-goal/scripts/agy_goal/cli.py agy-goal/tests/
git commit -m "feat(agy-goal): wire python CLI to shell wrapper and update test suites"
```

---

### Task 8: Update SKILL.md & Clean Obsolete References

**Files:**
- Modify: `agy-goal/SKILL.md`

- [ ] **Step 1: Update `agy-goal/SKILL.md`**

Reflect the new architecture:
1. Explain both Local and Remote execution options (`--remote <target>` and `AGY_TARGET`).
2. Highlight the remote closed-loop verification (zero local sync noise during intermediate turns).
3. Document the Circuit Breaker rules and `status`, `sync`, and `reset` utility commands.

- [ ] **Step 2: Verify skill markdown format**

Check frontmatter and format integrity.

- [ ] **Step 3: Run all test suites one last time**

Run: `bash agy-goal/tests/run_all_tests.sh`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add agy-goal/SKILL.md
git commit -m "docs(agy-goal): update SKILL.md for unified local and remote execution"
```
