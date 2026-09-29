# Design Spec: agy-goal Remote & Local Unified Architecture

- **Date:** 2026-09-29
- **Status:** Approved
- **Topic:** Unified agy-goal Architecture with Local/Remote Executor Interface, Circuit Breaker, and Remote Closed-Loop Verification

---

## 1. Overview & Goals

`agy-goal` allows Claude Code to execute implementation plans via the AGY CLI (`/goal` and `continue`) with autonomous execution and strict anti-thrashing circuit breakers.

Previously, `agy-goal` only supported local command execution through a standalone bash script. This design upgrades `agy-goal` into a modular architecture supporting both local and remote execution environments while preserving a clean, unified CLI experience:

```
                         Claude Code / User
                                │
                          agy-goal Skill
                                │
                                ▼
                       agy-goal CLI Entry
                    (scripts/agy-goal.py / sh)
                                │
               ┌────────────────┴────────────────┐
               │         Core Engine             │
               │                                 │
               │  • Work API (Session & Task)    │
               │  • Circuit Breaker (Anti-loop)  │
               │  • Result Parser (JSON/Markers) │
               │  • State Store (.agy-goal/state)│
               └────────────────┬────────────────┘
                                │
                       Executor Interface
               (Base: Abstract Execution Engine)
                                │
                ┌───────────────┴───────────────┐
                │                               │
        LocalExecutor                    RemoteExecutor
        (Subprocess / agy)              (gt exec / remote agy)
                │                               │
         Local Workspace                 Remote Workspace
                │                               │
          Local Git Repo                 Remote Git Repo
```

### Key Requirements & Constraints
1. **Unified Skill & CLI Entry**: All executions (`local` and `remote`) use the same user-facing command `agy-goal.sh`.
2. **Remote Closed-Loop Verification (Zero Noise)**: During intermediate remote iterations, testing, Git status inspection, and marker verification remain entirely closed-loop on the remote host via `gt exec`. Local repository synchronizes (`git pull`) only upon goal completion or circuit-breaker halt.
3. **Strict Circuit Breaker (Hard Stop)**: Maximum 3 `continue` turns per session, identical error loop detection (2 consecutive identical failures), and mandatory structured escalation reports.
4. **Zero Third-Party Dependencies**: Pure Python 3.8+ standard library implementation with shell wrapper for backward compatibility.

---

## 2. Architecture & Component Decomposition

### 2.1 Directory Structure
```text
agy-goal/
├── SKILL.md                          # Skill guide and agent decision protocol
├── scripts/
│   ├── agy-goal.sh                   # POSIX shell wrapper routing to python3 CLI
│   └── agy_goal/                     # Python core package (standard library only)
│       ├── __init__.py
│       ├── cli.py                    # Argument parsing and command dispatch
│       ├── core/
│       │   ├── __init__.py
│       │   ├── work_api.py           # Work API: high-level session & task lifecycle
│       │   ├── circuit_breaker.py    # Hard limits (rounds <= 3, stagnation detection)
│       │   ├── result_parser.py      # Output parsing (JSON, raw fallback, <!-- GOAL_COMPLETE -->)
│       │   └── state.py              # State manager (.agy-goal/state.json)
│       └── executors/
│           ├── __init__.py
│           ├── base.py               # Executor Interface (Abstract Base Class)
│           ├── local.py              # LocalWorker: local subprocess execution
│           └── remote.py             # RemoteWorker: git push -> gt exec -> remote test/commit
└── tests/
    ├── run_all_tests.sh              # Unified test suite runner
    ├── test_result_parser.py         # Unit tests for result parsing
    ├── test_circuit_breaker.py       # Unit tests for circuit breaker rules
    ├── test_state_store.py           # Unit tests for session state tracking
    ├── test_local_executor.py        # Unit tests for LocalExecutor with mock agy
    ├── test_remote_executor.py       # Unit tests for RemoteExecutor with mock gt
    └── test_cli_integration.sh       # End-to-end CLI behavior and backward compatibility
```

---

## 3. Core Components Specification

### 3.1 Executor Interface (`executors/base.py`)
Both execution modes conform to a common abstract contract:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ExecutionResult:
    status: str              # "SUCCESS", "ERROR", "TIMEOUT", "STAGNANT"
    conversation_id: str     # AGY conversation ID
    duration_seconds: float  # Wall-clock duration
    raw_response: str        # Formatted agent response output
    goal_complete: bool      # True if <!-- GOAL_COMPLETE --> is present
    git_diff_summary: str    # Git diff/log summary from the execution environment
    error_message: Optional[str] = None

class BaseExecutor(ABC):
    @abstractmethod
    def preflight_check(self) -> None:
        """Validate prerequisites before executing commands."""
        pass

    @abstractmethod
    def execute(self, prompt: str, is_continue: bool = False) -> ExecutionResult:
        """Execute a plan or continue command and return structured result."""
        pass

    @abstractmethod
    def sync_to_local(self) -> None:
        """Synchronize remote changes back to local repository if applicable."""
        pass
```

### 3.2 Local Worker (`executors/local.py`)
- **Execution Mechanism**: Directly runs `agy --mode accept-edits --print-timeout 20m --output-format json [-c] -p <prompt>` locally.
- **Git Inspection**: Runs local `git status --short` and `git diff --stat`.
- **Sync**: No-op (local workspace is already the execution target).

### 3.3 Remote Worker (`executors/remote.py`)
- **Pre-flight Checks**:
  1. Verifies local repository is on a feature branch (rejects `main`/`master`).
  2. Confirms `gt` is installed in `PATH`.
  3. Verifies remote target node is reachable via `gt exec <target> echo ping`.
- **Branch Push & Sync**:
  - Automatically stages uncommitted plan files and pushes current branch to remote: `git push -u origin <branch>`.
- **Remote Execution & Closed-Loop Verification (`gt exec`)**:
  - Remote shell payload performs:
    1. Pull branch inside remote workspace: `git fetch origin <branch> && git checkout <branch> && git pull origin <branch>`.
    2. Run AGY: `agy --mode accept-edits --print-timeout 20m --output-format json [-c] -p <prompt>`.
    3. Commit changes remotely: `git add -A && git commit -m "feat(agy-remote): update code via agy" && git push origin <branch>`.
    4. Extract `git diff --stat HEAD~1` and response JSON into a composite structured response.
- **Sync to Local (`sync_to_local`)**:
  - Pulls remote commits locally via `git pull origin <branch>`.
  - **Invoked ONLY when**:
    - Goal is complete (`goal_complete == True`); OR
    - Circuit breaker triggers a halt (allowing developer inspection).

---

## 4. State Management & Circuit Breaker

### 4.1 State Store (`core/state.py`)
Stored in `.agy-goal/state.json`:
```json
{
  "active": true,
  "mode": "remote",
  "target": "agy-remote-server",
  "branch": "feat/my-feature",
  "round": 1,
  "max_rounds": 3,
  "conversation_id": "mock-1",
  "last_error_signature": "a8f3b2...",
  "consecutive_identical_errors": 0,
  "created_at": 1759132800.0,
  "updated_at": 1759133400.0
}
```

### 4.2 Circuit Breaker Rules (`core/circuit_breaker.py`)
1. **Round Limit**: `round > 3` on `continue` triggers an immediate HALT.
2. **Stagnation / Identical Error**: If the hash of failing test/error messages matches 2 consecutive rounds, trigger an immediate HALT.
3. **Escalation Protocol**:
   - Exit with status code `10`.
   - In Remote mode, execute `sync_to_local()` to ensure local inspection reflects latest remote commits.
   - Print standardized `[CIRCUIT BREAKER TRIGGERED]` block with current progress, blocker, and user options.

---

## 5. CLI Ergonomics & Interface

### 5.1 Commands
```bash
# 1. Start Plan (Local)
agy-goal.sh path/to/plan.md

# 2. Start Plan (Remote)
agy-goal.sh path/to/plan.md --remote <target_id>
# Or via environment variable:
export AGY_TARGET=agy-remote-server
agy-goal.sh path/to/plan.md

# 3. Continue Plan Execution (Auto-detects active session target and round)
agy-goal.sh continue
agy-goal.sh continue "Fix test failure in user_spec: assertion failed at line 42"

# 4. Status & Utility
agy-goal.sh status    # Displays active session, mode, round count, and circuit breaker status
agy-goal.sh sync      # Explicitly pulls latest remote code to local
agy-goal.sh reset     # Clears active session state
agy-goal.sh --help    # Displays help
```

---

## 6. Testing Strategy

1. **Unit Tests**:
   - `test_result_parser.py`: Tests JSON parsing, timeout fallback, markdown responses, and `<!-- GOAL_COMPLETE -->` detection.
   - `test_circuit_breaker.py`: Verifies round limit increments, stagnation triggers, and reset actions.
   - `test_state_store.py`: Tests creation, serialization, updates, and clearing of `.agy-goal/state.json`.
2. **Executor Isolation Tests**:
   - `test_local_executor.py`: Mock `agy` subprocess runner verifying execution flow.
   - `test_remote_executor.py`: Mock `gt` subprocess runner verifying closed-loop execution and deferred `sync_to_local()`.
3. **CLI End-to-End Integration**:
   - `test_cli_integration.sh`: Validates help options, error states, and end-to-end execution flows for both Local and Remote modes.
