#!/usr/bin/env bash
# ==============================================================================
# agy-goal.sh - Multi-turn runner for AGY plan execution
#
# Default Timeout: 30m (configurable via AGY_TIMEOUT environment variable)
#
# Commands:
#   <plan.md>                    - Execute implementation plan via /goal
#   continue [instructions...]   - Continue plan implementation or supply feedback
# ==============================================================================

set -uo pipefail

TIMEOUT="${AGY_TIMEOUT:-30m}"

show_help() {
  cat <<'EOF'
Usage:
  agy-goal.sh <path/to/plan.md>               Implement a plan file via /goal
  agy-goal.sh continue [instructions...]      Continue plan implementation or supply feedback
  agy-goal.sh -h, --help                      Show this help message

Notes:
  - Default execution timeout is 30 minutes. You can override it via AGY_TIMEOUT (e.g. AGY_TIMEOUT=45m).
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
  echo "[agy-goal] Error: 'agy' CLI is not found in PATH." >&2
  exit 127
fi

PROMPT=""
CMD_EXTRA_ARGS=()

case "$ACTION" in
  -h|--help|help)
    show_help
    exit 0
    ;;

  goal)
    echo "[agy-goal] Note: The 'goal' subcommand has been removed for simplicity." >&2
    echo "Usage: $0 <path/to/plan.md>" >&2
    exit 1
    ;;

  continue)
    INSTRUCTIONS="$*"
    echo "=== Continuing Most Recent AGY Session (-c) ==="
    echo "Timeout: $TIMEOUT"
    CMD_EXTRA_ARGS+=(-c)

    if [ -z "$INSTRUCTIONS" ]; then
      PROMPT="Continue implementing the plan. Check current progress, finish all remaining tasks, and ensure all tests pass."
    else
      echo "Instructions: $INSTRUCTIONS"
      PROMPT="Continue implementing the plan: ${INSTRUCTIONS}. Finish remaining tasks and ensure tests pass."
    fi
    ;;

  *)
    # Check if ACTION itself is a plan file
    if [ -f "$ACTION" ]; then
      PLAN_FILE="$ACTION"
      echo "=== Running AGY Plan Implementation ==="
      echo "Plan:    $PLAN_FILE"
      echo "Timeout: $TIMEOUT"
      PROMPT="/goal Implement Plan @${PLAN_FILE}"
    else
      echo "[agy-goal] Error: Unknown command or plan file not found: '$ACTION'." >&2
      show_help >&2
      exit 1
    fi
    ;;
esac

CMD=(agy --mode accept-edits --print-timeout "$TIMEOUT" --output-format json)
[ ${#CMD_EXTRA_ARGS[@]} -gt 0 ] && CMD+=("${CMD_EXTRA_ARGS[@]}")
CMD+=(-p "$PROMPT")

TMP_OUT="$(mktemp -t agy-out.XXXXXX)"
trap 'rm -f "$TMP_OUT"' EXIT

CMD_STR="$(printf '%q ' "${CMD[@]}")"
echo "[agy-goal] Executing: ${CMD_STR% }"
AGY_EXIT=0
"${CMD[@]}" > "$TMP_OUT" || AGY_EXIT=$?

# Parse output and display summary
if [ -s "$TMP_OUT" ]; then
  python3 -c '
import json, sys

exit_code = int(sys.argv[2])
is_completed = False

try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    cid = data.get("conversation_id", "")
    status = data.get("status", "UNKNOWN")
    duration = data.get("duration_seconds", 0)
    print("\n" + "=" * 60)
    print("Status:         ", status)
    if cid:
        print("Conversation ID:", cid)
    print(f"Duration:        {duration:.1f}s")
    print("=" * 60 + "\n")
    print(data.get("response", "").strip())
    
    is_completed = (exit_code == 0 and status == "COMPLETED")
except Exception:
    with open(sys.argv[1]) as f:
        print(f.read())
    is_completed = False

print("\n==================== DECISION GATE ====================")
if is_completed:
    print("Decision: READY FOR COMPLETION")
    print("Action:   Plan executed successfully by AGY.")
    print("Next:     Review git diff, then commit and report completion to user.")
else:
    print("Decision: ACTION REQUIRED (INCOMPLETE / ERROR)")
    print("Action:   DO NOT run manual tests or debug manually.")
    print("Next:     Run: agy-goal.sh continue \"<1-2 sentence issue summary>\"")
print("=======================================================\n")
' "$TMP_OUT" "$AGY_EXIT"
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
