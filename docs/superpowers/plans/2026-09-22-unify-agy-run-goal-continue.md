# Unify agy-run Concepts to `goal` and `continue` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strictly align all CLI subcommands, error messages, and documentation in `agy-run` to the native concepts `goal` and `continue`, eliminating conflicting terms like `imp` and raw `-c`.

**Architecture:** Refactor `agy-run.sh` to replace `imp` with `goal`, updating help and validation messages. Update `agy-run/SKILL.md` to present a unified conceptual model (`goal` and `continue`) without fragmented terminology.

**Tech Stack:** Bash, Markdown, YAML frontmatter

## Global Constraints

- Supported subcommands: `goal <path/to/plan.md>` and `continue [instructions...]`.
- Subcommand `imp` must be rejected as an unknown command.
- Documentation must not expose raw `-c` or `imp` terms to users.
- Total line count of `agy-run/SKILL.md` must remain under 50 lines.

---

### Task 1: Refactor `agy-run.sh` Subcommand from `imp` to `goal`

**Files:**
- Modify: `agy-run/scripts/agy-run.sh`

**Interfaces:**
- Produces: `agy-run.sh` with subcommands:
  - `agy-run.sh goal <path/to/plan.md>`
  - `agy-run.sh continue [instructions...]`
  - `agy-run.sh -h | --help`

- [ ] **Step 1: Verify current failure of `goal` command**

Run:
```bash
./agy-run/scripts/agy-run.sh goal
```
Expected: `[agy-run] Error: Unknown command 'goal'.`

- [ ] **Step 2: Update `agy-run/scripts/agy-run.sh` to replace `imp` with `goal`**

Modify `agy-run/scripts/agy-run.sh`:
- In `show_help()`: change `imp <path/to/plan.md>` to `goal <path/to/plan.md>` with description `Implement a plan file via /goal`.
- In `case "$ACTION" in`: change `imp)` to `goal)`.
- Update error messages:
  - `echo "[agy-run] Error: 'goal' requires a plan file path." >&2`
  - `echo "Usage: $0 goal path/to/plan.md" >&2`

- [ ] **Step 3: Verify CLI behavior with tests**

Run:
```bash
./agy-run/scripts/agy-run.sh -h | grep "goal <path/to/plan.md>"
./agy-run/scripts/agy-run.sh goal 2>&1 | grep "'goal' requires a plan file path"
./agy-run/scripts/agy-run.sh goal nonexistent.md 2>&1 | grep "Plan file not found"
./agy-run/scripts/agy-run.sh imp 2>&1 | grep "Unknown command 'imp'"
```
Expected: All tests pass with exit code 0/expected error messages.

- [ ] **Step 4: Commit changes to Git**

```bash
git add agy-run/scripts/agy-run.sh
git commit -m "refactor(agy-run): replace imp subcommand with goal"
```

---

### Task 2: Update `agy-run/SKILL.md` to Unify `goal` and `continue`

**Files:**
- Modify: `agy-run/SKILL.md`

**Interfaces:**
- Produces: Streamlined documentation strictly using `goal` and `continue`.

- [ ] **Step 1: Replace content in `agy-run/SKILL.md`**

Update `agy-run/SKILL.md` to:

```markdown
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
```

- [ ] **Step 2: Verify document consistency and constraints**

Run:
```bash
wc -l agy-run/SKILL.md
grep -E "imp|-c" agy-run/SKILL.md || echo "Clean: No obsolete terms found"
```
Expected: Total lines <= 50, and zero instances of `imp` or `-c`.

- [ ] **Step 3: Commit changes to Git**

```bash
git add agy-run/SKILL.md
git commit -m "docs(agy-run): unify skill documentation around goal and continue"
```
