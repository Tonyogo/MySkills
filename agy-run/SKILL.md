---
name: agy-run
description: Execute an implementation plan or continue/fix tasks using AGY CLI (/goal and continue).
---

# agy-run

Execute and iterate on implementation plans using **AGY CLI** (`/goal` and `continue`).

## Commands

Run the runner script from `./agy-run/scripts/agy-run.sh` (or your configured skills path):

### 1. Implement Plan (`imp`)
Start executing a written markdown plan:
```bash
agy-run.sh imp path/to/plan.md
```
*Directs AGY via:* `/goal Implement Plan @path/to/plan.md`

### 2. Continue Plan Execution (`continue`)
Continue the plan to finish remaining tasks or supply targeted feedback:
```bash
# Continue without extra instructions:
agy-run.sh continue

# Continue with specific feedback or fix instructions:
agy-run.sh continue "Fix test failure in user_spec: assertion failed at line 42"
```
*Resumes the session directly via `-c`.*

---

## Workflow

1. **Start**: Run `agy-run.sh imp <plan.md>`.
2. **Verify**: Check `git diff` and run project tests.
3. **Continue**: If tasks remain incomplete or tests fail, run `agy-run.sh continue ["feedback"]`.
4. **Complete**: When all tests pass and changes are clean, proceed with Git commit/push.
