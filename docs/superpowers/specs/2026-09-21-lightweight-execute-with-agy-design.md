# Design: Lightweight execute-with-agy Skill

**Date:** 2026-09-21  
**Status:** Approved  
**Topic:** Streamlining execute-with-agy to lightweight commands leveraging AGY native capabilities (`/goal` and `/boost`).

---

## 1. Goal & Context

Simplify and streamline the `execute-with-agy` skill and its runner script (`agy-run.sh`). Rather than using heavy prompt wrapping and complex orchestration rules, lean directly on AGY CLI's native commands (`/goal` and `/boost`) with clear, concise English prompts and strict argument validation.

---

## 2. CLI Architecture & Commands (`agy-run.sh`)

The script provides exactly two subcommands: `imp` and `fix`.

### 2.1 Subcommands

1. **`imp <plan_file>`**:
   - **Requirement:** `plan_file` is **mandatory**.
   - **Validation:** Must check that argument exists and the target file actually exists on disk; otherwise exit with a clear error message.
   - **Execution:** Invokes AGY in non-interactive accept-edits mode with auto-approved permissions:
     ```bash
     agy --mode accept-edits --dangerously-skip-permissions -p "/goal Implement Plan @<plan_file>"
     ```
   - Captures and displays execution summary and output.

2. **`fix "<issue_description>"`**:
   - **Requirement:** `<issue_description>` is **mandatory**.
   - **Validation:** Must check that issue description is provided and non-empty.
   - **Execution:** Invokes AGY with `/boost`:
     ```bash
     agy --mode accept-edits --dangerously-skip-permissions -p "/boost Fix <issue_description>"
     ```
   - (Note: No `-c` / `--continue` flag is used).

### 2.2 Post-Execution Output
- Display the execution status and output from AGY.
- If in a Git repository, print a compact Git status summary, diff stats, and standard Git workflow suggestions (commit / push / merge).

---

## 3. Skill Documentation (`SKILL.md`)

Refactor `execute-with-agy/SKILL.md` to be concise:
- Describe the purpose: Delegating plan execution and bug fixing to AGY CLI.
- Provide the exact invocation commands for `imp` and `fix`.
- Keep review / completion verification guidance minimal and practical.

---

## 4. Verification & Testing Plan
- Test `agy-run.sh -h` or invalid commands for clean usage help.
- Test `agy-run.sh imp` without arguments or non-existent file to ensure proper error exit.
- Test `agy-run.sh fix` without arguments to ensure proper error exit.
- Verify `SKILL.md` clarity and brevity.
