#!/usr/bin/env bash
# ==============================================================================
# agy-run.sh - Lightweight runner for Claude Code -> AGY execution
#
# Core responsibilities:
#   1. Resolve implementation plan (auto-discovery or explicit path)
#   2. Execute AGY CLI in non-interactive accept-edits mode
#   3. Persist session ID to enable fix loops (--fix "<feedback>")
#   4. Support -y / auto-permissions
#   5. Show post-execution Git diff & status
# ==============================================================================

set -uo pipefail

SESSION_FILE=".execute-with-agy-session"
PLAN_FILE=""
FIX_PROMPT=""
SKIP_PERMS=false
EXTRA_ARGS=()

# 1. Parse Arguments
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      cat <<'EOF'
Usage:
  agy-run.sh [path/to/plan.md] [options...]
  agy-run.sh --fix "<instructions>"

Options:
  -p, --plan <path>       Specify implementation plan markdown file
  -y, --skip-permissions  Auto-approve AGY tool permissions (--dangerously-skip-permissions)
      --fix "<prompt>"    Resume previous AGY session to apply fixes
  -h, --help              Show this help message

Environment:
  AGY_TIMEOUT             Execution timeout (default: 30m)
EOF
      exit 0
      ;;
    --fix)
      if [ -z "${2:-}" ]; then
        echo "[execute-with-agy] Error: --fix requires feedback text." >&2
        exit 1
      fi
      FIX_PROMPT="$2"
      shift 2
      ;;
    -y|--skip-permissions|--dangerously-skip-permissions)
      SKIP_PERMS=true
      shift
      ;;
    -p|--plan)
      if [ -z "${2:-}" ]; then
        echo "[execute-with-agy] Error: --plan requires a file path." >&2
        exit 1
      fi
      PLAN_FILE="$2"
      shift 2
      ;;
    *)
      if [ -z "$PLAN_FILE" ] && [ -z "$FIX_PROMPT" ] && [[ "$1" != -* ]]; then
        PLAN_FILE="$1"
      else
        EXTRA_ARGS+=("$1")
      fi
      shift
      ;;
  esac
done

# 2. Check agy CLI
if ! command -v agy >/dev/null 2>&1; then
  echo "[execute-with-agy] Error: 'agy' CLI is not found in PATH." >&2
  exit 127
fi

# Exclude session file from git status if inside a repository
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_DIR="$(git rev-parse --git-dir 2>/dev/null || true)"
  if [ -n "$GIT_DIR" ] && [ -d "$GIT_DIR/info" ]; then
    grep -q "^\.execute-with-agy-session" "$GIT_DIR/info/exclude" 2>/dev/null || echo ".execute-with-agy-session" >> "$GIT_DIR/info/exclude"
  fi
fi

# 3. Determine Mode & Prompt
RESUME_ID=""
if [ -n "$FIX_PROMPT" ]; then
  if [ ! -f "$SESSION_FILE" ]; then
    echo "[execute-with-agy] Error: No previous session found in $SESSION_FILE. Cannot fix." >&2
    exit 1
  fi
  RESUME_ID="$(head -n 1 "$SESSION_FILE" | tr -d '[:space:]')"
  echo "=== Resuming AGY Session: $RESUME_ID ==="
  echo "Fix instruction: $FIX_PROMPT"

  PROMPT="$(cat <<EOF
You are continuing the implementation session.

Fix the issues identified during review:
$FIX_PROMPT

Run the relevant tests after making the fixes.
Do not change unrelated functionality.
EOF
)"
else
  # Auto-discover plan if not specified
  if [ -z "$PLAN_FILE" ]; then
    for dir in "docs/superpowers/plans" "docs/plans" "plans"; do
      if [ -d "$dir" ]; then
        PLAN_FILE=$(ls -t "$dir"/*.md 2>/dev/null | head -n 1 || true)
        [ -n "$PLAN_FILE" ] && break
      fi
    done
  fi

  if [ -z "$PLAN_FILE" ] || [ ! -f "$PLAN_FILE" ]; then
    echo "[execute-with-agy] Error: Plan file not found: ${PLAN_FILE:-'(none discovered)'}" >&2
    echo "Usage: ./scripts/agy-run.sh path/to/plan.md" >&2
    exit 1
  fi

  echo "=== Running AGY Implementation ==="
  echo "Plan: $PLAN_FILE"

  PROMPT="$(cat <<EOF
You are the implementation agent.

A separate planning agent has analyzed the repository and created the implementation plan:
@${PLAN_FILE}

Your responsibility is to IMPLEMENT this plan:
1. Inspect the codebase, understand architecture and conventions.
2. Directly implement all planned tasks in the repository.
3. Run required tests and verify fixes.
4. Report completed work, changed files, test outcomes, and any deviations from the plan.

Preserve unrelated user changes that existed before this session.
EOF
)"
fi

# 4. Build AGY Command
CMD=(agy --mode accept-edits --output-format json --print-timeout "${AGY_TIMEOUT:-30m}")
[ "$SKIP_PERMS" = true ] && CMD+=(--dangerously-skip-permissions)
[ -n "$RESUME_ID" ] && CMD+=(--conversation "$RESUME_ID")
[ ${#EXTRA_ARGS[@]} -gt 0 ] && CMD+=("${EXTRA_ARGS[@]}")
CMD+=(-p "$PROMPT")

# 5. Execute AGY
TMP_OUT="$(mktemp -t agy-out.XXXXXX)"
trap 'rm -f "$TMP_OUT"' EXIT

echo "[execute-with-agy] Running AGY..."
AGY_EXIT=0
"${CMD[@]}" > "$TMP_OUT" || AGY_EXIT=$?

# 6. Parse and Display Output
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
    print("Conversation ID:", cid)
    print(f"Duration:        {duration:.1f}s")
    print("=" * 60 + "\n")
    print(data.get("response", "").strip())
except Exception:
    with open(sys.argv[1]) as f:
        print(f.read())
' "$TMP_OUT" "$SESSION_FILE"
fi

# 7. Post-Execution Git Summary & Next Steps
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo -e "\n================ Git Status ================"
  git status --short
  echo -e "\n================ Git Diff Stat ============="
  git diff --stat

  # Branch-aware suggestions
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
