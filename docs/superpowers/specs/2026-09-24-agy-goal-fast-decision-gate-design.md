# Design Spec: `agy-goal` Fast Decision Gate & Anti-Thrashing Workflow

- **Date:** 2026-09-24
- **Author:** Claude & liyatao
- **Status:** In Review
- **Topic:** Optimizing `agy-goal` Skill Instructions & Script Output for Instant Binary Decision Making

---

## 1. Motivation & Problem Statement

In the previous design of `agy-goal`, the skill instructions included:
> *"2. Verify: Check `git diff` and run project tests independently."*

This caused host-session agents (e.g., Claude Code) to fall into an anti-pattern:
1. **Inefficient manual testing loop**: After running `agy-goal.sh`, the host agent would repeatedly run project tests (`npm test`, `pytest`, etc.), read stack traces, inspect source files, and attempt manual debugging locally instead of letting AGY handle the implementation.
2. **Context & token thrashing**: The host agent spent numerous tool turns trying to diagnose issues manually, wasting context and tokens.
3. **Ambiguous completion criteria**: Without clear binary cues, agents hesitated on whether to declare the task complete, iterate, or keep testing.

---

## 2. Architecture & Role Separation

To eliminate thrashing, we establish a strict separation between the **Orchestrator** (host-session agent) and the **Worker** (AGY CLI).

```
┌────────────────────────────────────────────────────────┐
│               Host Agent (Orchestrator)                 │
│  - Triggers agy-goal.sh                                │
│  - Inspects [DECISION GATE] and summary output         │
│  - Makes an immediate 1-turn binary decision:          │
│      A. Declare complete and report git actions        │
│      B. Call agy-goal.sh continue "<issue summary>"    │
│  - NEVER runs manual test commands                     │
│  - NEVER attempts manual code debugging                │
└───────────────────────────┬────────────────────────────┘
                            │ Dispatches bash command
                            ▼
┌────────────────────────────────────────────────────────┐
│                  AGY CLI (Worker)                      │
│  - Reads the plan / continue instructions              │
│  - Writes code implementation                          │
│  - Runs project tests autonomously                     │
│  - Fixes test failures and iterates until plan is done │
└────────────────────────────────────────────────────────┘
```

### 2.1 Negative Constraints on Host Agent
- **No Manual Testing**: Strictly prohibited from running `npm test`, `pytest`, `go test`, `cargo test`, or custom test scripts.
- **No Manual Debugging**: Strictly prohibited from opening erroring files to write bug fixes or debug manually. All fixes must be delegated to AGY.

---

## 3. Script Output Enhancement (`agy-goal.sh`)

To give the Orchestrator an unambiguous signal at execution completion, `agy-goal.sh` is updated to include a structured `[DECISION GATE]` block in its post-execution summary.

### 3.1 Gate Output Logic
The runner analyzes:
1. `AGY_EXIT`: Process exit code (0 for clean execution, non-zero for error/timeout).
2. `status`: AGY JSON response status (`COMPLETED` vs others).
3. `response`: Checks if AGY explicitly reported unfinished tasks or errors.

### 3.2 Output Formats

#### Case A: Successful Completion
```text
==================== DECISION GATE ====================
Decision: READY FOR COMPLETION
Action:   Plan executed successfully by AGY.
Next:     Review git diff, then commit and report completion to user.
=======================================================
```

#### Case B: Incomplete Execution or Error
```text
==================== DECISION GATE ====================
Decision: ACTION REQUIRED (INCOMPLETE / ERROR)
Action:   DO NOT run manual tests or debug manually.
Next:     Run: agy-goal.sh continue "<1-2 sentence issue summary>"
=======================================================
```

---

## 4. `SKILL.md` Specification

`agy-goal/SKILL.md` is rewritten to enforce the fast binary decision gate:

1. **Two-Step Execution Loop**:
   - **Step 1**: Execute `agy-goal.sh <plan.md>`.
   - **Step 2**: Inspect `[DECISION GATE]`:
     - If `READY FOR COMPLETION`: Confirm git status/diff, announce completion, suggest commit steps.
     - If `ACTION REQUIRED`: Extract 1–2 sentences summarizing the missing tasks or failure, and immediately run `agy-goal.sh continue "<instructions>"`.

2. **Standard Format for `continue` Instructions**:
   - For remaining tasks: `"Continue remaining tasks in plan: Task 3 (...) and Task 4 (...)."`
   - For reported errors: `"Fix error reported in previous run: <1-sentence error description>."`
   - For timeouts/interrupts: `"Session interrupted before completing Task 2. Please resume and complete it."`

3. **Circuit Breaker Rules**:
   - **Maximum 3 Continue Turns**: If after 3 `continue` invocations the plan is still incomplete, STOP and escalate to the user.
   - **Identical Failure Loop**: If 2 consecutive turns report the exact same failure or zero diff progress, STOP and escalate to the user.
   - **Escalation Report**:
     1. Tasks completed so far.
     2. Exact blocker or error message.
     3. Recommended options for the user.

---

## 5. Verification & Testing Strategy

1. **Unit / Dry-Run Verification**:
   - Test `agy-goal.sh -h` to verify CLI interface stability.
   - Mock AGY execution outputs (both simulated completed JSON and error/incomplete JSON) to verify that `[DECISION GATE]` formats render correctly.
2. **Review of `SKILL.md`**:
   - Verify that all references to running tests independently have been removed.
   - Verify that negative constraints against manual debugging are unambiguous and prominently displayed.
