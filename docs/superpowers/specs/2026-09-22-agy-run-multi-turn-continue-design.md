# Design: agy-run Multi-Turn Plan Execution with `continue`

**Date:** 2026-09-22  
**Status:** Approved  
**Topic:** Redesigning `agy-run` skill to support multi-turn plan completion and feedback via `imp` and `continue`, replacing hardcoded fix logic.

---

## 1. Background & Goals

When executing an implementation plan with AGY CLI, single-turn runs often terminate before the full plan is complete, or Claude Code reviewers uncover unaddressed tasks/regressions.

Previous iterations used a rigid `fix` subcommand that assumed fixes only and lacked unified multi-turn workflow support.

This design refocuses `agy-run` entirely on **complete, multi-turn plan execution**:
- Subcommands: `imp <plan_file>` and `continue [instructions...]`.
- Accurate conversation tracking via `.agy-session` storing `conversation_id`.
- Graceful fallback: If `.agy-session` is absent, `continue` falls back to `agy -c` (`--continue`).
- Safe execution: Remove `--dangerously-skip-permissions` to respect existing user permissions.
- Focus: Drive a single plan to 100% completion through iterative turns.

---

## 2. CLI Design (`agy-run.sh`)

### 2.1 Subcommands

1. **`imp <path/to/plan.md>`** (Start new plan execution):
   - **Validation:**
     - `<path/to/plan.md>` is mandatory.
     - Target file must exist on disk; otherwise exit with error.
   - **Command:**
     ```bash
     agy --mode accept-edits --output-format json --print-timeout "${AGY_TIMEOUT:-30m}" -p "/goal Implement Plan @<path/to/plan.md>"
     ```
   - **Session Tracking:**
     - Parses JSON response from AGY to extract `conversation_id`.
     - Writes `conversation_id` into `.agy-session`.
     - Automatically ensures `.agy-session` is listed in Git exclude (`.git/info/exclude`).

2. **`continue [instructions...]`** (Continue execution or provide feedback):
   - **Arguments:**
     - Optional. All remaining arguments are treated as a combined instruction string.
   - **Session Resolution:**
     - Checks `.agy-session` for a valid `conversation_id`.
     - If found: appends `--conversation <id>` to resume the exact session.
     - If not found: falls back to `-c` (`--continue`) to resume the most recent AGY conversation.
   - **Prompt Construction:**
     - If no arguments provided:
       `"Continue implementing the plan. Check current progress, finish all remaining tasks, and ensure all tests pass."`
     - If arguments provided (e.g. `continue "Fix test failure in user_spec"` or `continue "Task 4 is not implemented"`):
       `"Continue implementing the plan: <instructions>. Finish remaining tasks and ensure tests pass."`
   - **Command:**
     ```bash
     agy --mode accept-edits --output-format json --print-timeout "${AGY_TIMEOUT:-30m}" [ --conversation <id> | -c ] -p "<prompt>"
     ```
   - **Session Update:**
     - Updates `.agy-session` with the returned `conversation_id`.

3. **General Options:**
   - `-h`, `--help`, `help`: Display clean usage guide.
   - Any other subcommand: Output error and show usage.

### 2.2 Post-Execution Output & Git Guidance
- Output AGY status (`status`), execution duration (`duration_seconds`), and clean response text.
- If inside a Git repository:
  - Print `git status --short`.
  - Print `git diff --stat`.
  - Print branch-aware suggestions for commit, push, or merge.

---

## 3. Skill Documentation (`agy-run/SKILL.md`)

Update `agy-run/SKILL.md` to reflect the multi-turn paradigm:
- Document the two core commands: `imp` and `continue`.
- Clearly explain the multi-turn lifecycle:
  1. Generate plan (`superpowers:writing-plans`).
  2. Initiate implementation: `agy-run.sh imp <plan.md>`.
  3. Review output and Git diff.
  4. If incomplete or issues exist: `agy-run.sh continue ["details..."]`.
  5. Repeat until 100% verified.
- Remove references to the obsolete `fix` subcommand.

---

## 4. Verification & Testing

1. CLI argument validation tests:
   - `agy-run.sh` without args -> exit 1 with help.
   - `agy-run.sh imp` without file -> exit 1.
   - `agy-run.sh imp nonexistent.md` -> exit 1 with "Plan file not found".
   - `agy-run.sh unknown` -> exit 1.
2. CLI continue fallback tests:
   - When `.agy-session` is missing, `continue` flags `-c`.
   - When `.agy-session` exists, `continue` flags `--conversation <id>`.
3. Verification that `--dangerously-skip-permissions` is not present in invocation.
4. Verification of prompt construction for both default and custom instructions.
