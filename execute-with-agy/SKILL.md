---
name: execute-with-agy
description: Hand off an existing implementation plan to AGY CLI for autonomous execution via /goal or fix issues via /boost, then review via Claude Code.
---

# execute-with-agy

Lightweight skill to orchestrate code implementation and issue fixes using **AGY CLI** (`/goal` and `/boost`).

## Commands

Run the runner script (adjust to `~/.claude/skills/...` if installed globally):

### 1. Implement Plan (`imp`)
Execute a written implementation plan:
```bash
.claude/skills/execute-with-agy/scripts/agy-run.sh imp path/to/plan.md
```
*Prompt passed to AGY:* `/goal Implement Plan @path/to/plan.md`

### 2. Fix Issues (`fix`)
Fix specific bugs or test failures discovered during review:
```bash
.claude/skills/execute-with-agy/scripts/agy-run.sh fix "description of issue to fix"
```
*Prompt passed to AGY:* `/boost Fix description of issue to fix`

---

## Workflow

1. **Implement:** Run `agy-run.sh imp <plan_file>`.
2. **Review:** Inspect the generated changes with `git diff` and run verification tests.
3. **Fix (if needed):** If any issue is found, run `agy-run.sh fix "<issue>"`.
4. **Complete:** Review final Git status/diff and proceed with commit/push/merge.
