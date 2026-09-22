#!/usr/bin/env bash
# ==============================================================================
# agy-run.sh - Multi-turn runner for AGY plan execution
#
# Commands:
#   imp <plan.md>                - Execute implementation plan via /goal
#   continue [instructions...]   - Continue plan implementation or supply feedback
# ==============================================================================

set -uo pipefail

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

PROMPT=""
CMD_EXTRA_ARGS=()

case "$ACTION" in
  -h|--help|help)
    show_help
    exit 0
    ;;

  imp)
    if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
      echo "[agy-run] Error: 'imp' requires a plan file path." >&2
      echo "Usage: $0 imp path/to/plan.md" >&2
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
    echo "=== Continuing Most Recent AGY Session (-c) ==="
    CMD_EXTRA_ARGS+=(-c)

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
[ ${#CMD_EXTRA_ARGS[@]} -gt 0 ] && CMD+=("${CMD_EXTRA_ARGS[@]}")
CMD+=(-p "$PROMPT")

TMP_OUT="$(mktemp -t agy-out.XXXXXX)"
trap 'rm -f "$TMP_OUT"' EXIT

CMD_STR="$(printf '%q ' "${CMD[@]}")"
echo "[agy-run] Executing: ${CMD_STR% }"
AGY_EXIT=0
"${CMD[@]}" > "$TMP_OUT" || AGY_EXIT=$?

# Parse output and display summary
if [ -s "$TMP_OUT" ]; then
  python3 -c '
import json, sys
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
