#!/usr/bin/env bash
# ==============================================================================
# agy-remote.sh - Remote runner for AGY plan execution via gt exec
# ==============================================================================

set -euo pipefail

TIMEOUT="${AGY_TIMEOUT:-30m}"
DEFAULT_TARGET="${AGY_TARGET:-}"
REMOTE_DIR="${REMOTE_WORK_DIR:-}"

show_help() {
  cat <<'EOF'
Usage:
  agy-remote.sh <target_id> <path/to/plan.md>            Implement a plan file remotely
  agy-remote.sh <target_id> continue [instructions...]   Continue remote implementation or supply feedback
  agy-remote.sh <path/to/plan.md>                        Implement plan (using $AGY_TARGET)
  agy-remote.sh continue [instructions...]               Continue (using $AGY_TARGET)
  agy-remote.sh -h, --help                               Show this help message

Environment Variables:
  AGY_TARGET       Default target ID/container (allows omitting target_id in CLI)
  AGY_TIMEOUT      Execution timeout (default: 30m)
  REMOTE_WORK_DIR  Remote working directory (default: git root in remote container)
EOF
}

if [ $# -lt 1 ]; then
  show_help >&2
  echo "[agy-remote] Error: Missing target ID or plan file." >&2
  exit 1
fi

case "$1" in
  -h|--help|help)
    show_help
    exit 0
    ;;
esac

TARGET_ID=""
ACTION=""
INSTRUCTIONS=""

if [ -n "$DEFAULT_TARGET" ]; then
  # If AGY_TARGET is set, check if $1 is a plan file or continue
  if [ "$1" = "continue" ] || [ -f "$1" ] || [[ "$1" == *.md ]]; then
    TARGET_ID="$DEFAULT_TARGET"
    ACTION="$1"
    shift
    [ "$ACTION" = "continue" ] && INSTRUCTIONS="$*"
  else
    TARGET_ID="$1"
    shift
    if [ $# -lt 1 ]; then
      echo "[agy-remote] Error: Missing command or plan file for target '$TARGET_ID'." >&2
      exit 1
    fi
    ACTION="$1"
    shift
    [ "$ACTION" = "continue" ] && INSTRUCTIONS="$*"
  fi
else
  TARGET_ID="$1"
  shift
  if [ $# -lt 1 ]; then
    echo "[agy-remote] Error: Missing command or plan file for target '$TARGET_ID'." >&2
    exit 1
  fi
  ACTION="$1"
  shift
  [ "$ACTION" = "continue" ] && INSTRUCTIONS="$*"
fi

# Validate target and action
if [ -z "$TARGET_ID" ]; then
  echo "[agy-remote] Error: Target ID must be provided as first argument or via AGY_TARGET." >&2
  exit 1
fi

if [ "$ACTION" != "continue" ]; then
  if [ ! -f "$ACTION" ]; then
    echo "[agy-remote] Error: Plan file not found: '$ACTION'." >&2
    exit 1
  fi
fi

CURRENT_BRANCH=""

check_preflight() {
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[agy-remote] Error: Must be inside a git repository." >&2
    exit 1
  fi

  CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    echo "[agy-remote] Error: Refusing to run on 'main' or 'master' branch." >&2
    echo "Please create or switch to a feature branch (e.g. git checkout -b feat/my-task)." >&2
    exit 1
  fi

  if [ "${AGY_TEST_MOCK:-0}" != "1" ]; then
    if ! command -v gt >/dev/null 2>&1; then
      echo "[agy-remote] Error: 'gt' CLI tool not found in PATH." >&2
      exit 127
    fi

    # Probe target container
    if ! gt exec "$TARGET_ID" echo ok >/dev/null 2>&1; then
      echo "[agy-remote] Error: Unable to connect to target '$TARGET_ID' via gt exec." >&2
      exit 1
    fi
  fi
}

check_preflight

# Push local branch to origin first
if [ "${AGY_TEST_MOCK:-0}" != "1" ]; then
  if [ -n "$(git status --porcelain)" ]; then
    echo "[agy-remote] Staging and committing uncommitted changes on '$CURRENT_BRANCH'..."
    git add -A
    git commit -m "docs/feat(agy-remote): auto-commit before remote execution"
  fi
  echo "[agy-remote] Syncing local branch '$CURRENT_BRANCH' to origin..."
  git push -u origin "$CURRENT_BRANCH"
fi

# Build remote agy prompt
if [ "$ACTION" = "continue" ]; then
  if [ -z "$INSTRUCTIONS" ]; then
    REMOTE_PROMPT="Continue implementing the plan. Check current progress, finish all remaining tasks, and ensure all tests pass."
  else
    REMOTE_PROMPT="Continue implementing the plan: ${INSTRUCTIONS}. Finish remaining tasks and ensure tests pass."
  fi
  AGY_ARGS=(-c -p "$REMOTE_PROMPT")
else
  REMOTE_PROMPT="/goal Implement Plan @${ACTION}"
  AGY_ARGS=(-p "$REMOTE_PROMPT")
fi

ESCAPED_ARGS="$(printf '%q ' "${AGY_ARGS[@]}")"

# Prepare remote execution script
REMOTE_SCRIPT=$(cat <<REMOTE_EOF
set -e
if [ -n "$REMOTE_DIR" ]; then
  cd "$REMOTE_DIR"
fi
git fetch origin "$CURRENT_BRANCH"
git checkout "$CURRENT_BRANCH"
git pull origin "$CURRENT_BRANCH"

agy --mode accept-edits --print-timeout "$TIMEOUT" --output-format json $ESCAPED_ARGS

if [ -n "\$(git status --porcelain)" ]; then
  git add -A
  git commit -m "feat(agy-remote): update code via agy"
  git push origin "$CURRENT_BRANCH"
fi
REMOTE_EOF
)

TMP_OUT="$(mktemp -t agy-remote-out.XXXXXX)"
trap 'rm -f "$TMP_OUT"' EXIT

echo "[agy-remote] Executing on remote target '$TARGET_ID'..."
GT_EXIT=0
gt exec "$TARGET_ID" bash -c "$REMOTE_SCRIPT" > "$TMP_OUT" || GT_EXIT=$?

# Parse JSON output via python3 and output Status, Conversation ID, Duration, and text response.
if [ -s "$TMP_OUT" ]; then
  python3 -c '
import json, sys
try:
    with open(sys.argv[1]) as f:
        raw_content = f.read()
    data = None
    json_start = raw_content.find("{")
    json_end = raw_content.rfind("}")
    if json_start != -1 and json_end != -1 and json_end > json_start:
        prefix = raw_content[:json_start].strip()
        if prefix:
            print(prefix)
        try:
            data = json.loads(raw_content[json_start:json_end+1])
        except Exception:
            pass
    if data:
        cid = data.get("conversation_id", "")
        status = data.get("status", "UNKNOWN")
        duration = data.get("duration_seconds", 0)
        print("\n" + "=" * 60)
        print("Status:          " + str(status))
        if cid:
            print("Conversation ID: " + str(cid))
        print(f"Duration:        {duration:.1f}s")
        print("=" * 60 + "\n")
        print(data.get("response", "").strip())
    else:
        print(raw_content)
except Exception:
    with open(sys.argv[1]) as f:
        print(f.read())
' "$TMP_OUT"
fi

# Locally pull changes
if [ "${AGY_TEST_MOCK:-0}" != "1" ]; then
  echo -e "\n[agy-remote] Pulling remote changes from origin/$CURRENT_BRANCH..."
  git pull origin "$CURRENT_BRANCH" || true
fi

# Display git status and diff stat
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo -e "\n================ Git Status ================"
  git status --short
  echo -e "\n================ Git Diff Stat ============="
  git diff --stat
fi

exit "$GT_EXIT"


