---
name: agy-goal
description: Use when executing an implementation plan or iterating/fixing tasks via AGY CLI (/goal and continue).
---

# agy-goal

Execute and iterate on implementation plans using **AGY CLI** (`/goal` and `continue`) with agent-driven semantic verification and strict anti-thrashing circuit breakers.

## Role Definition & Principles

- **Host Agent (Orchestrator & Reviewer)**:
  - Dispatches `agy-goal.sh`.
  - Performs **semantic verification** by reading the execution log and reviewing Git changes.
  - Decides whether the goal is achieved or requires `continue`.
  - Enforces the hard iteration limit and escalates to the user when stuck.
- **AGY CLI (Autonomous Worker)**:
  - Reads the plan, writes code, runs project tests internally, and debugs failures autonomously.

### 🚫 Strict Negative Constraints
- **DO NOT run manual test commands**: Never execute `npm test`, `pytest`, `go test`, `cargo test`, or custom test scripts. All testing is handled autonomously inside AGY.
- **DO NOT manually debug or patch code**: Never open failing source files to debug or write manual fixes. All adjustments must be delegated back to AGY via `continue`.

---

## Commands

Run the runner script from `./agy-goal/scripts/agy-goal.sh` (or your configured skills path).

> [!NOTE]
> Execution timeout is fixed at **20 minutes**.

### 1. Implement Plan
Start executing a written markdown plan:
```bash
agy-goal.sh path/to/plan.md
```

### 2. Continue Plan Execution (`continue`)
Continue the plan to finish remaining tasks or supply targeted feedback:
```bash
# Continue without extra instructions:
agy-goal.sh continue

# Continue with targeted feedback (1-2 sentences):
agy-goal.sh continue "Fix test failure in user_spec: assertion failed at line 42"
```

---

## Agent Verification Protocol (1-Turn Decision)

The script formats and prints AGY's execution response (Status, Conversation ID, Duration, `Goal Complete` marker, and Response body). After execution completes, the host agent evaluates two primary sources of truth:

1. **`Goal Complete` Marker & Response Summary**:
   - **Fast-Path Check**: Check if `Goal Complete: YES` (AGY explicitly printed `<!-- GOAL_COMPLETE -->`). This is the deterministic handshake indicating AGY completed all planned tasks and tests.
   - If `Goal Complete: NO`, check the response summary for incomplete tasks, timeouts, or error messages.
2. **Git Changes (Inspected via `git status`, `git diff --stat`, or `git log -n 1`)**:
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

## 🛑 Circuit Breaker & Mandatory User Escalation

To prevent infinite loops, token waste, and agent thrashing, you must enforce strict stopping criteria:

### 1. Stopping Red Lines
- **Maximum 3 Continue Turns**: You may invoke `continue` at most **3 times** per plan. If the plan is still not completed after round 3, you must STOP immediately. Never initiate a 4th turn.
- **Identical Error / Stagnation Loop**: If the exact same error persists across **2 consecutive turns**, or if Git diff shows zero forward progress, you must STOP immediately.
- **Scope Creep / Degradation**: If AGY modifies completely unrelated directories or introduces regressions, you must STOP immediately.

### 2. Mandatory Human Escalation
When a stop condition is triggered, you are **STRICTLY PROHIBITED** from continuing automated execution or trying to fix it yourself. You must immediately report to the user:

1. **Completed Tasks**: What was completed and committed successfully so far.
2. **Current Blocker**: The exact error message, failing test, or incomplete task.
3. **Reason for Stopping**: (e.g., *"Reached maximum 3 continue attempts"* or *"Identical failure across 2 consecutive turns"*).
4. **Options for User Decision**: Present 2–3 actionable choices and ask the human partner how to proceed (e.g., provide manual guidance, pause for manual inspection, or adjust plan scope).
