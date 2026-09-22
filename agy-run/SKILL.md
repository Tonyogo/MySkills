---
name: agy-run
description: Hand off an existing implementation plan to AGY CLI for autonomous execution via /goal and iterative multi-turn completion via continue, then review via Claude Code.
---

# agy-run

Lightweight skill to orchestrate autonomous implementation plan execution using **AGY CLI** (`/goal`) with multi-turn completion support.

## Commands

Run the runner script (adjust to `~/.claude/skills/...` if installed globally):

### 1. Implement Plan (`imp`)
Start executing a written implementation plan:
```bash
.claude/skills/agy-run/scripts/agy-run.sh imp path/to/plan.md
```
*Prompt passed to AGY:* `/goal Implement Plan @path/to/plan.md`

### 2. Continue Plan Execution (`continue`)
Continue the plan to complete remaining tasks or provide feedback on issues found during review:
```bash
# Continue without extra instructions:
.claude/skills/agy-run/scripts/agy-run.sh continue

# Continue with specific feedback or remaining task instructions:
.claude/skills/agy-run/scripts/agy-run.sh continue "Task 3 tests are failing; fix the assert issue"
```
*Resumes the most recent AGY conversation via `-c`.*

---

## Multi-Turn Workflow

1. **Start:** Run `agy-run.sh imp <plan_file>`.
2. **Review:** Inspect the generated changes with `git diff` and check test results.
3. **Continue (if incomplete or bugs found):** Run `agy-run.sh continue ["feedback..."]` to let AGY finish remaining tasks.
4. **Complete:** Once all tasks and tests pass, review the final Git summary and proceed with commit/push.
