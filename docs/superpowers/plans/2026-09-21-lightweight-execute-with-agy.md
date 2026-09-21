# Lightweight execute-with-agy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Streamline `execute-with-agy` skill and `agy-run.sh` runner into a lightweight, concise tool using AGY's native `/goal` and `/boost` commands with strict argument validation and clean Git guidance.

**Architecture:** Refactor `agy-run.sh` to support only two subcommands (`imp <plan_file>` and `fix "<issue>"`), enforcing required arguments and file existence checks before invoking AGY. Streamline `SKILL.md` to remove boilerplate and document the new workflow concisely.

**Tech Stack:** Bash, Markdown, AGY CLI, Git

## Global Constraints

- Subcommands supported: `imp <plan_file>` and `fix "<issue_description>"`.
- `imp` requires `plan_file` to exist on disk; otherwise exit with error.
- `imp` invokes AGY with: `agy --mode accept-edits --dangerously-skip-permissions -p "/goal Implement Plan @<plan_file>"`.
- `fix` invokes AGY with: `agy --mode accept-edits --dangerously-skip-permissions -p "/boost Fix <issue_description>"`.
- No `-c` / `--continue` argument used in `fix`.
- Output parsing, status summary, and Git status / diff / next-steps suggestions are preserved.
- `SKILL.md` is updated to match the streamlined usage.

---

### Task 1: Refactor `agy-run.sh` to Lightweight `imp` and `fix` Subcommands

**Files:**
- Modify: `execute-with-agy/scripts/agy-run.sh`
- Test: Manual CLI verification of argument parsing, error cases, and help output

**Interfaces:**
- Produces: CLI script `execute-with-agy/scripts/agy-run.sh` supporting:
  - `agy-run.sh imp <plan_file>`
  - `agy-run.sh fix "<issue_description>"`
  - `agy-run.sh -h | --help`

- [ ] **Step 1: Write test script to verify `agy-run.sh` CLI argument behavior**

Create a temporary test script or run bash checks to assert that:
1. Running with `-h` or `--help` prints usage.
2. Running without arguments exits with error.
3. Running `imp` without a plan file exits with error.
4. Running `imp non_existent_file.md` exits with error "Plan file not found".
5. Running `fix` without issue text exits with error.
6. Unknown commands exit with error.

- [ ] **Step 2: Run verification against current `agy-run.sh` to confirm current failure/mismatch**

Run:
```bash
./execute-with-agy/scripts/agy-run.sh imp
```
Expected: Current script fails or misparses `imp` as a plan file.

- [ ] **Step 3: Implement new `agy-run.sh`**

Replace `execute-with-agy/scripts/agy-run.sh` with the streamlined logic:

```bash
#!/usr/bin/env bash
# ==============================================================================
# agy-run.sh - Lightweight runner for AGY execution
#
# Commands:
#   imp <plan.md>      - Execute implementation plan via /goal
#   fix "<issue>"      - Fix issues via /boost
# ==============================================================================

set -uo pipefail

show_help() {
  cat <<'EOF'
Usage:
  agy-run.sh imp <path/to/plan.md>   Implement a plan file via /goal
  agy-run.sh fix "<issue_desc>"      Fix issues via /boost
  agy-run.sh -h, --help              Show this help message

Environment:
  AGY_TIMEOUT                        Execution timeout (default: 30m)
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
  echo "[execute-with-agy] Error: 'agy' CLI is not found in PATH." >&2
  exit 127
fi

PROMPT=""

case "$ACTION" in
  -h|--help|help)
    show_help
    exit 0
    ;;

  imp)
    if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
      echo "[execute-with-agy] Error: 'imp' requires a plan file path." >&2
      echo "Usage: ./scripts/agy-run.sh imp path/to/plan.md" >&2
      exit 1
    fi
    PLAN_FILE="$1"
    if [ ! -f "$PLAN_FILE" ]; then
      echo "[execute-with-agy] Error: Plan file not found: $PLAN_FILE" >&2
      exit 1
    fi
    echo "=== Running AGY Plan Implementation ==="
    echo "Plan: $PLAN_FILE"
    PROMPT="/goal Implement Plan @${PLAN_FILE}"
    ;;

  fix)
    if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
      echo "[execute-with-agy] Error: 'fix' requires an issue description." >&2
      echo "Usage: ./scripts/agy-run.sh fix \"description of issue\"" >&2
      exit 1
    fi
    FIX_DESC="$1"
    echo "=== Running AGY Issue Fix ==="
    echo "Fix: $FIX_DESC"
    PROMPT="/boost Fix ${FIX_DESC}"
    ;;

  *)
    echo "[execute-with-agy] Error: Unknown command '$ACTION'." >&2
    show_help >&2
    exit 1
    ;;
esac

CMD=(agy --mode accept-edits --dangerously-skip-permissions --output-format json --print-timeout "${AGY_TIMEOUT:-30m}" -p "$PROMPT")

TMP_OUT="$(mktemp -t agy-out.XXXXXX)"
trap 'rm -f "$TMP_OUT"' EXIT

echo "[execute-with-agy] Running AGY..."
AGY_EXIT=0
"${CMD[@]}" > "$TMP_OUT" || AGY_EXIT=$?

# Parse and display output
if [ -s "$TMP_OUT" ]; then
  python3 -c '
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    status = data.get("status", "UNKNOWN")
    duration = data.get("duration_seconds", 0)
    print("\n" + "=" * 60)
    print("Status:         ", status)
    print(f"Duration:        {duration:.1f}s")
    print("=" * 60 + "\n")
    print(data.get("response", "").strip())
except Exception:
    with open(sys.argv[1]) as f:
        print(f.read())
' "$TMP_OUT"
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

- [ ] **Step 4: Verify test scenarios pass**

Run verification tests:
```bash
./execute-with-agy/scripts/agy-run.sh -h
./execute-with-agy/scripts/agy-run.sh imp 2>&1 | grep "requires a plan file path"
./execute-with-agy/scripts/agy-run.sh imp nonexistent.md 2>&1 | grep "Plan file not found"
./execute-with-agy/scripts/agy-run.sh fix 2>&1 | grep "requires an issue description"
./execute-with-agy/scripts/agy-run.sh invalid 2>&1 | grep "Unknown command"
```
Expected: All exit cleanly with corresponding error messages.

- [ ] **Step 5: Commit changes**

```bash
git add execute-with-agy/scripts/agy-run.sh
git commit -m "feat(execute-with-agy): streamline agy-run.sh with imp and fix subcommands"
```

---

### Task 2: Streamline `execute-with-agy/SKILL.md`

**Files:**
- Modify: `execute-with-agy/SKILL.md`

**Interfaces:**
- Produces: Concise skill documentation reflecting the new `imp` and `fix` workflows.

- [ ] **Step 1: Draft the concise `SKILL.md` content**

Update `execute-with-agy/SKILL.md` to:

```markdown
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
```

- [ ] **Step 2: Update `execute-with-agy/SKILL.md`**

Write the new content to `execute-with-agy/SKILL.md`.

- [ ] **Step 3: Verify document completeness**

Check that file is clean, links/commands are accurate, and formatting is intact.

- [ ] **Step 4: Commit changes**

```bash
git add execute-with-agy/SKILL.md
git commit -m "docs(execute-with-agy): update SKILL.md to reflect lightweight imp and fix workflow"
```
