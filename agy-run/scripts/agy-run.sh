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
  echo "[agy-run] Error: 'agy' CLI is not found in PATH." >&2
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

  fix)
    if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
      echo "[agy-run] Error: 'fix' requires an issue description." >&2
      echo "Usage: ./scripts/agy-run.sh fix \"description of issue\"" >&2
      exit 1
    fi
    FIX_DESC="$1"
    echo "=== Running AGY Issue Fix ==="
    echo "Fix: $FIX_DESC"
    PROMPT="/boost Fix ${FIX_DESC}"
    ;;

  *)
    echo "[agy-run] Error: Unknown command '$ACTION'." >&2
    show_help >&2
    exit 1
    ;;
esac

CMD=(agy --mode accept-edits --print-timeout 30m --output-format json -p "$PROMPT")

TMP_OUT="$(mktemp -t agy-out.XXXXXX)"
trap 'rm -f "$TMP_OUT"' EXIT

echo "[agy-run] Running AGY..."
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
