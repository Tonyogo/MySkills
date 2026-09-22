# Streamline agy-run Skill Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Streamline `agy-run/SKILL.md` description and body to a lightweight, zero-boilerplate reference under 45 lines.

**Architecture:** Replace the 160-line `agy-run/SKILL.md` containing extensive flowcharts and templates with a concise single-line frontmatter description, an exact command reference for `imp` and `continue`, and a 4-step workflow loop.

**Tech Stack:** Markdown, YAML frontmatter

## Global Constraints

- Frontmatter `description` must be single-line and concise:
  `Execute an implementation plan or continue/fix tasks using AGY CLI (/goal and continue).`
- Subcommands documented must strictly match `agy-run.sh`: `imp <path/to/plan.md>` and `continue [instructions...]`.
- Total line count of `agy-run/SKILL.md` must be under 45 lines.
- No Mermaid diagrams, no verbose 4-gate verification SOPs, and no bulky output report templates.

---

### Task 1: Update `agy-run/SKILL.md` with Streamlined Content

**Files:**
- Modify: `agy-run/SKILL.md`

**Interfaces:**
- Produces: Concise skill documentation `agy-run/SKILL.md` (< 45 lines).

- [ ] **Step 1: Check current line count of `agy-run/SKILL.md`**

Run:
```bash
wc -l agy-run/SKILL.md
```
Expected: ~160 lines.

- [ ] **Step 2: Replace `agy-run/SKILL.md` with streamlined content**

Write the following content to `agy-run/SKILL.md`:

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

## Workflow

1. **Start**: Run `agy-run.sh imp <plan.md>`.
2. **Verify**: Check `git diff` and run project tests.
3. **Continue**: If tasks remain incomplete or tests fail, run `agy-run.sh continue ["feedback"]`.
4. **Complete**: When all tests pass and changes are clean, proceed with Git commit/push.
```

- [ ] **Step 3: Verify line count and format constraints**

Run:
```bash
wc -l agy-run/SKILL.md
```
Expected: Less than 45 lines (around 38 lines).

Also verify that frontmatter parses cleanly and markdown formatting renders properly.

- [ ] **Step 4: Commit changes to Git**

```bash
git add agy-run/SKILL.md
git commit -m "docs(agy-run): streamline SKILL.md to concise reference guide"
```
