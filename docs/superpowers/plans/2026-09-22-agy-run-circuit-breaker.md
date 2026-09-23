# agy-run Circuit Breaker & Human Escalation Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add non-negotiable circuit breaker rules and human escalation protocols to `agy-run/SKILL.md` to prevent AI runaway loops and ungrounded file edits when multi-turn plan execution fails.

**Architecture:** Update `agy-run/SKILL.md` to introduce explicit hard stop rules (max 3 rounds, identical error loop, scope creep) and a structured escalation protocol directing the AI to halt and request human guidance.

**Tech Stack:** Markdown, YAML frontmatter

## Global Constraints

- Modify `agy-run/SKILL.md` without introducing unnecessary verbosity (total line count kept under 60 lines).
- Rules must specify three hard stop triggers:
  1. Maximum 3 `continue` turns.
  2. Identical error recurring across 2 consecutive turns.
  3. Scope creep or unexpected regressions.
- Escalation format must mandate reporting:
  1. What was completed successfully.
  2. The exact blocking error or failure.
  3. Suggested options and request for user decision.

---

### Task 1: Add Circuit Breaker and Escalation Rules to `agy-run/SKILL.md`

**Files:**
- Modify: `agy-run/SKILL.md`

**Interfaces:**
- Produces: Updated `agy-run/SKILL.md` containing `## Workflow & Circuit Breaker` and `### 🛑 Hard Stop & Escalation Rules`.

- [ ] **Step 1: Inspect current `agy-run/SKILL.md`**

Run:
```bash
wc -l agy-run/SKILL.md
```
Expected: ~39 lines.

- [ ] **Step 2: Update `agy-run/SKILL.md` with circuit breaker and escalation rules**

Update `agy-run/SKILL.md` to:

```markdown
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

## Workflow & Circuit Breaker

1. **Start**: Run `agy-run.sh imp <plan.md>`.
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

- [ ] **Step 3: Verify document constraints**

Run:
```bash
wc -l agy-run/SKILL.md
```
Expected: Around 50-55 lines (< 60 lines).

Verify Markdown formatting and frontmatter validity.

- [ ] **Step 4: Commit changes to Git**

```bash
git add agy-run/SKILL.md
git commit -m "docs(agy-run): add circuit breaker and human escalation rules"
```
