---
name: agy-goal
description: Use when executing an implementation plan or iterating/fixing tasks via AGY CLI (/goal and continue), locally or remotely.
---

# agy-goal

Execute and iterate on implementation plans using the **AGY CLI** (`/goal` and `continue`) with autonomous local or remote execution, closed-loop remote verification, and strict anti-thrashing circuit breakers.

## Architecture & Role Definition

- **Host Agent (Orchestrator & Verifier)**:
  - Dispatches `agy-goal.sh`.
  - Performs semantic verification from AGY execution summaries and Git diffs.
  - Automatically recovers session context on `continue`.
  - Enforces hard iteration limits and halts execution upon circuit breaker triggers.
- **AGY CLI (Autonomous Worker)**:
  - **Local Mode**: Executes directly in the local workspace via local `agy`.
  - **Remote Mode (`--remote <target>` or `AGY_TARGET`)**: Pushes initial branch to origin, runs autonomous execution, testing, and commits closed-loop on the remote host via `gt exec`, and synchronizes back to local only upon goal completion or circuit breaker halt (zero noise during intermediate turns).

### 🚫 Strict Negative Constraints
- **DO NOT run manual test commands**: Never execute `npm test`, `pytest`, `go test`, `cargo test`, or custom test scripts. All testing is handled autonomously inside AGY.
- **DO NOT manually debug or patch code**: Never open failing source files to debug or write manual fixes. All adjustments must be delegated back to AGY via `continue`.
- **DO NOT execute remote runs on `main` or `master`**: Always create or switch to a feature branch before dispatching remote runs.

---

## Commands

Run the runner script from `./agy-goal/scripts/agy-goal.sh` (or your configured skills path).

> [!NOTE]
> Execution timeout is fixed at **20 minutes**.

### 1. Implement Plan (Local)
Start executing a written markdown plan on the local machine:
```bash
agy-goal.sh path/to/plan.md
```

### 2. Implement Plan (Remote via `gt exec`)
Execute on a remote compute target using `--remote` or the `AGY_TARGET` environment variable:
```bash
# Option A: Command-line flag
agy-goal.sh path/to/plan.md --remote my-worker-node

# Option B: Environment variable
export AGY_TARGET=my-worker-node
agy-goal.sh path/to/plan.md
```
During remote runs:
- Initial plan and workspace changes are committed and pushed to `origin/<branch>`.
- AGY execution, intermediate edits, tests, and commits happen entirely on the remote host.
- Local repository remains clean and pulls (`git pull`) only when `GOAL_COMPLETE` is achieved or if execution halts.

### 3. Continue Plan Execution (`continue`)
Continue the active plan session to finish remaining tasks or supply targeted feedback. Target mode and conversation context are automatically loaded from state:
```bash
# Continue without extra instructions:
agy-goal.sh continue

# Continue with targeted feedback (1-2 sentences):
agy-goal.sh continue "Fix test failure in user_spec: assertion failed at line 42"
```

### 4. Utilities
```bash
# Check current session mode, branch, round count, and status
agy-goal.sh status

# Explicitly pull latest remote changes to local workspace
agy-goal.sh sync

# Clear active session state
agy-goal.sh reset
```

---

## Agent Verification Protocol (1-Turn Decision)

The runner outputs AGY's execution response (Status, Conversation ID, Duration, `Goal Complete` marker, and Response body). After execution completes, evaluate two primary sources of truth:

1. **`Goal Complete` Marker & Response Summary**:
   - **Fast-Path Check**: Check if `Goal Complete: YES` (AGY explicitly emitted `<!-- GOAL_COMPLETE -->`). This is the deterministic handshake indicating AGY completed all planned tasks and tests.
   - If `Goal Complete: NO`, inspect the response summary for incomplete tasks, timeouts, or error messages.
2. **Git Changes (`git status`, `git diff --stat`, or `git log -n 1`)**:
   - Confirm that actual code changes and commits exist and align with the plan.

### Decision Gate:

- **Case A: Goal Achieved (PASS - Fast-Path)**
  - `Goal Complete: YES` (or `<!-- GOAL_COMPLETE -->` present) and Git changes match the plan.
  - **Action**: Declare completion immediately, summarize completed tasks and Git commits, and advise the user on next steps (Commit/Push/PR).
  - **🚫 Rule**: Do NOT run any additional tests.

- **Case B: Incomplete, Error, or Scope Miss (ITERATE)**
  - `Goal Complete: NO`, unfinished tasks remain, tests failed, or expected code changes are absent.
  - **Action**: Extract a 1–2 sentence summary of the exact blocker or unfinished task, and immediately run:
    ```bash
    agy-goal.sh continue "<1-2 sentence issue summary>. Finish remaining tasks until <!-- GOAL_COMPLETE --> is reached."
    ```
  - **🚫 Rule**: Do NOT attempt to fix code manually.

---

## 🛑 Circuit Breaker & Mandatory Escalation

To prevent infinite loops, token waste, and agent thrashing, the core engine enforces built-in circuit breaker rules:

### 1. Stopping Red Lines
- **Maximum 3 Continue Turns**: You may invoke `continue` at most **3 times** per session. Reaching round 3 halts execution with status code 10.
- **Identical Error / Stagnation Loop**: If the SHA-256 signature of failing test/error messages matches across **2 consecutive turns**, execution halts immediately.
- **Production Branch Guard**: Remote execution on `main` or `master` is rejected before any remote commands run.

### 2. Escalation Behavior
When the circuit breaker triggers:
- Any remote changes are automatically pulled locally (`sync_to_local()`) to facilitate inspection.
- A formatted `[CIRCUIT BREAKER TRIGGERED - EXECUTION HALTED]` report is printed with the blocker summary.
- The agent must **NOT** continue automated execution. Report the findings to the human partner with actionable options.
