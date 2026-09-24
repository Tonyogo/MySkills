---
name: agy-goal
description: Execute an implementation plan or continue/fix tasks using AGY CLI (/goal and continue).
---

# agy-goal

Execute and iterate on implementation plans using **AGY CLI** (`/goal` and `continue`) with a fast, zero-thrashing decision gate.

## Role Definition & Principles

- **Host Agent (Orchestrator)**: Dispatches `agy-goal.sh`, reads the resulting `[DECISION GATE]`, and makes an immediate 1-turn binary decision: declare completion or invoke `continue`.
- **AGY CLI (Worker)**: Autonomous implementation agent. Reads the plan, edits code, runs project tests internally, and fixes failures.

### 🚫 Strict Negative Constraints
- **DO NOT run manual test commands**: Never execute `npm test`, `pytest`, `go test`, `cargo test`, or custom test scripts directly. AGY executes and verifies tests internally.
- **DO NOT manually debug or patch code**: Never open failing source files to debug or write manual fixes. If an issue is reported, summarize it in 1–2 sentences and hand it back to AGY via `continue`.

---

## Commands

Run the runner script from `./agy-goal/scripts/agy-goal.sh` (or your configured skills path).

> [!NOTE]
> 默认单次任务超时时间为 **30 分钟**（可通过环境变量 `AGY_TIMEOUT` 调整，例如 `AGY_TIMEOUT=45m`）。

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

## Fast Decision Gate Workflow

Every time `agy-goal.sh` finishes, inspect the `[DECISION GATE]` block at the end of output:

### Case A: `READY FOR COMPLETION`
- Check `git status` and `git diff` to confirm changes are clean and match the plan.
- Announce completion to the user and suggest commit/push steps.
- **Do NOT run any additional tests.**

### Case B: `ACTION REQUIRED (INCOMPLETE / ERROR)`
- Extract a 1–2 sentence summary of the missing tasks or error from the AGY response.
- Immediately run:
  ```bash
  agy-goal.sh continue "<1-2 sentence issue summary>"
  ```
- **Do NOT attempt to diagnose or fix the error yourself.**

---

## 🛑 Hard Stop & Circuit Breaker

You must **STOP** immediately and escalate to the user if:
1. **Round Limit Exceeded**: You have run `continue` **3 times** and the plan is still not completed.
2. **Identical Error Loop**: The exact same error or test failure persists across **2 consecutive turns**.
3. **Scope Creep / Degradation**: AGY starts modifying unrelated files or introducing new regressions.

**When stopped, report to the user immediately:**
1. Tasks completed successfully so far.
2. The exact blocking error or reason for failure.
3. Proposed options/suggestions, and ask the user how to proceed.
