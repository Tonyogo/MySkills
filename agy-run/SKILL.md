---
name: agy-run
description: Execute an implementation plan or continue/fix tasks using AGY CLI (goal and continue).
---

# agy-run

Execute and iterate on implementation plans using **AGY CLI** (`goal` and `continue`).

## Commands

Run the runner script from `./agy-run/scripts/agy-run.sh` (or your configured skills path):

### 1. Implement Plan (`goal`)
Start executing a written markdown plan:
```bash
agy-run.sh goal path/to/plan.md
```

### 2. Continue Plan Execution (`continue`)
Continue the plan to finish remaining tasks or supply targeted feedback:
```bash
# Continue without extra instructions:
agy-run.sh continue

# Continue with specific feedback or fix instructions:
agy-run.sh continue "Fix test failure in user_spec: assertion failed at line 42"
```

---

## Workflow & Circuit Breaker

1. **Start**: Run `agy-run.sh goal <plan.md>`.
2. **Verify**: Check `git diff` and run project tests independently.
3. **Iterate**: If tasks remain incomplete or tests fail, run `agy-run.sh continue ["feedback"]`.
4. **Complete**: When all tests pass and changes are clean, proceed with Git commit/push.

### 🛑 Hard Stop & Escalation Rules
Do **NOT** guess or repeatedly edit files without progress. You must **STOP** and ask the user for a decision if:
- **Round Limit Exceeded**: You have run `continue` **3 times** and the plan is still not completed.
- **Identical Error Loop**: The exact same error or test failure persists across **2 consecutive turns**.
- **Scope Creep / Degradation**: AGY starts modifying unrelated files or introducing new regressions.

**When stopped, report to the user immediately:**
1. What was completed successfully.
2. The exact blocking error or reason for failure.
3. Proposed options/suggestions, and ask the user how to proceed.
