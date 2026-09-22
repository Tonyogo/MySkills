# agy-run Multi-Turn Plan Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `agy-run.sh` and `agy-run/SKILL.md` to support multi-turn plan completion and feedback via `imp` and `continue`, replacing `fix` and removing `--dangerously-skip-permissions`.

**Architecture:** Update `agy-run.sh` to provide `imp <plan_file>` and `continue [instructions...]` subcommands. Persist `conversation_id` in `.agy-session` upon each run, auto-exclude `.agy-session` from git, and fallback gracefully to `-c` when `.agy-session` is absent. Update `SKILL.md` to guide the multi-turn review-and-continue loop.

**Tech Stack:** Bash, Python 3 (JSON parsing helper), AGY CLI, Git

## Global Constraints

- Subcommands: `imp <plan_file>` and `continue [instructions...]`.
- `imp` requires `plan_file` to exist on disk; otherwise exit with error.
- Remove `--dangerously-skip-permissions` from all AGY invocations.
- `imp` prompt: `/goal Implement Plan @<plan_file>`.
- `continue` without arguments prompt: `"Continue implementing the plan. Check current progress, finish all remaining tasks, and ensure all tests pass."`.
- `continue <instructions>` prompt: `"Continue implementing the plan: <instructions>. Finish remaining tasks and ensure tests pass."`.
- Session management: store `conversation_id` in `.agy-session`. If missing, `continue` falls back to `agy -c`.
- Auto-exclude `.agy-session` in `.git/info/exclude`.
- Remove obsolete `fix` subcommand.

---

### Task 1: Refactor `agy-run.sh` to Support `imp` and `continue` with Session Persistence

**Files:**
- Modify: `agy-run/scripts/agy-run.sh`

**Interfaces:**
- Produces: CLI script `agy-run/scripts/agy-run.sh` with subcommands:
  - `agy-run.sh imp <path/to/plan.md>`
  - `agy-run.sh continue [instructions...]`
  - `agy-run.sh -h | --help`

- [x] **Step 1: Write test commands to verify CLI validation and behavior**

Verify:
1. `agy-run.sh` with no arguments prints usage and exits with code 1.
2. `agy-run.sh imp` with no file prints error and exits with code 1.
3. `agy-run.sh imp non_existent_file.md` prints error and exits with code 1.
4. `agy-run.sh fix` outputs unknown command error and exits with code 1.
5. `agy-run.sh continue` without `.agy-session` falls back to `-c`.
6. `agy-run.sh continue` with `.agy-session` passes `--conversation <id>`.

- [x] **Step 2: Update `agy-run/scripts/agy-run.sh` implementation**

Replace `agy-run/scripts/agy-run.sh` with:

```bash
#!/usr/bin/env bash
# ==============================================================================
# agy-run.sh - Multi-turn runner for AGY plan execution
#
# Commands:
#   imp <plan.md>                - Execute implementation plan via /goal
#   continue [instructions...]   - Continue plan implementation or supply feedback
# ==============================================================================

set -uo pipefail

SESSION_FILE=".agy-session"

show_help() {
  cat <<'EOF'
Usage:
  agy-run.sh imp <path/to/plan.md>            Implement a plan file via /goal
  agy-run.sh continue [instructions...]       Continue plan implementation or supply feedback
  agy-run.sh -h, --help                       Show this help message

Environment:
  AGY_TIMEOUT                                 Execution timeout (default: 30m)
EOF
}

if [ $# -lt 1 ]; then
  show_help >&2
  exit 1
fi

ACTION="$1"
shift

# Check agy CLI
if ! command -v agy >/dev/null 2>&1; then
  echo "[agy-run] Error: 'agy' CLI is not found in PATH." >&2
  exit 127
fi

# Ensure session file is excluded from git if in a git repo
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_DIR="$(git rev-parse --git-dir 2>/dev/null || true)"
  if [ -n "$GIT_DIR" ] && [ -d "$GIT_DIR/info" ]; then
    grep -q "^\.agy-session" "$GIT_DIR/info/exclude" 2>/dev/null || echo ".agy-session" >> "$GIT_DIR/info/exclude"
  fi
fi

PROMPT=""
SESSION_ARGS=()

case "$ACTION" in
  -h|--help|help)
    show_help
    exit 0
    ;;

  imp)
    if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
      echo "[agy-run] Error: 'imp' requires a plan file path." >&2
      echo "Usage: ./scripts/agy-run.sh imp path/to/plan.md" >&2
      exit 1
    fi
    PLAN_FILE="$1"
    if [ ! -f "$PLAN_FILE" ]; then
      echo "[agy-run] Error: Plan file not found: $PLAN_FILE" >&2
      exit 1
    fi
    echo "=== Running AGY Plan Implementation ==="
    echo "Plan: $PLAN_FILE"
    PROMPT="/goal Implement Plan @${PLAN_FILE}"
    ;;

  continue)
    INSTRUCTIONS="$*"
    if [ -f "$SESSION_FILE" ] && [ -s "$SESSION_FILE" ]; then
      CONV_ID="$(head -n 1 "$SESSION_FILE" | tr -d '[:space:]')"
    else
      CONV_ID=""
    fi

    if [ -n "$CONV_ID" ]; then
      echo "=== Continuing AGY Session: $CONV_ID ==="
      SESSION_ARGS+=(--conversation "$CONV_ID")
    else
      echo "=== Continuing AGY Session: (fallback to last conversation -c) ==="
      SESSION_ARGS+=(-c)
    fi

    if [ -z "$INSTRUCTIONS" ]; then
      PROMPT="Continue implementing the plan. Check current progress, finish all remaining tasks, and ensure all tests pass."
    else
      echo "Instructions: $INSTRUCTIONS"
      PROMPT="Continue implementing the plan: ${INSTRUCTIONS}. Finish remaining tasks and ensure tests pass."
    fi
    ;;

  *)
    echo "[agy-run] Error: Unknown command '$ACTION'." >&2
    show_help >&2
    exit 1
    ;;
esac

CMD=(agy --mode accept-edits --print-timeout "${AGY_TIMEOUT:-30m}" --output-format json)
[ ${#SESSION_ARGS[@]} -gt 0 ] && CMD+=("${SESSION_ARGS[@]}")
CMD+=(-p "$PROMPT")

TMP_OUT="$(mktemp -t agy-out.XXXXXX)"
trap 'rm -f "$TMP_OUT"' EXIT

echo "[agy-run] Running AGY..."
AGY_EXIT=0
"${CMD[@]}" > "$TMP_OUT" || AGY_EXIT=$?

# Parse output and save conversation ID
if [ -s "$TMP_OUT" ]; then
  python3 -c '
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    cid = data.get("conversation_id", "")
    if cid:
        with open(sys.argv[2], "w") as sf:
            sf.write(cid + "\n")
    status = data.get("status", "UNKNOWN")
    duration = data.get("duration_seconds", 0)
    print("\n" + "=" * 60)
    print("Status:         ", status)
    if cid:
        print("Conversation ID:", cid)
    print(f"Duration:        {duration:.1f}s")
    print("=" * 60 + "\n")
    print(data.get("response", "").strip())
except Exception:
    with open(sys.argv[1]) as f:
        print(f.read())
' "$TMP_OUT" "$SESSION_FILE"
fi

# Post-Execution Git Summary & Next Steps
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo -e "\n================ Git Status ================"
  git status --short
  echo -e "\n================ Git Diff Stat ============="
  git diff --stat

  CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || echo "")"
  HAS_UNCOMMITTED="$(git status --porcelain 2>/dev/null || true)"

  echo -e "\n================ Suggested Next Steps ================"
  [ -n "$CURRENT_BRANCH" ] && echo "Current Branch: $CURRENT_BRANCH"

  if [ -n "$HAS_UNCOMMITTED" ]; then
    echo "1. Commit changes:   git add -A && git commit -m \"feat: <description>\""
  else
    echo "1. Working tree:     clean (all changes committed)"
  fi

  if [ -n "$CURRENT_BRANCH" ] && [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
    echo "2. Push to remote:   git push -u origin $CURRENT_BRANCH"
    echo "3. Merge to main:    git checkout main && git merge $CURRENT_BRANCH"
  else
    echo "2. Push to remote:   git push"
  fi
  echo -e "======================================================\n"
fi

exit "$AGY_EXIT"
```

- [x] **Step 3: Run verification tests on `agy-run.sh`**

Run:
```bash
./agy-run/scripts/agy-run.sh -h
./agy-run/scripts/agy-run.sh imp 2>&1 | grep "requires a plan file path"
./agy-run/scripts/agy-run.sh imp non_existent_file.md 2>&1 | grep "Plan file not found"
./agy-run/scripts/agy-run.sh fix 2>&1 | grep "Unknown command 'fix'"
```
Expected: All output expected errors and usage info.

- [x] **Step 4: Commit changes**

```bash
git add agy-run/scripts/agy-run.sh
git commit -m "feat(agy-run): support multi-turn plan execution with imp and continue"
```

---

### Task 2: Update `agy-run/SKILL.md` Documentation

**Files:**
- Modify: `agy-run/SKILL.md`

**Interfaces:**
- Produces: Updated documentation in `agy-run/SKILL.md` describing the multi-turn lifecycle.

- [x] **Step 1: Write updated `agy-run/SKILL.md`**

Replace `agy-run/SKILL.md` with:

```markdown
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
*Resumes the exact conversation ID stored in `.agy-session` (or falls back to `-c`).*

---

## Multi-Turn Workflow

1. **Start:** Run `agy-run.sh imp <plan_file>`.
2. **Review:** Inspect the generated changes with `git diff` and check test results.
3. **Continue (if incomplete or bugs found):** Run `agy-run.sh continue ["feedback..."]` to let AGY finish remaining tasks.
4. **Complete:** Once all tasks and tests pass, review the final Git summary and proceed with commit/push.
```

- [x] **Step 2: Verify `SKILL.md` syntax and formatting**

Check rendering and ensure no obsolete `fix` references remain.

- [x] **Step 3: Commit changes**

```bash
git add agy-run/SKILL.md
git commit -m "docs(agy-run): update SKILL.md for multi-turn continue workflow"
```
