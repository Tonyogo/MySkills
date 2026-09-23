#!/usr/bin/env bash
# ==============================================================================
# agy-remote.sh - Remote runner for AGY plan execution via gt exec
#
# LOCAL RESPONSIBILITIES:
#   1. Ensure feature branch (not main/master)
#   2. Auto-commit & push local changes/plan to origin
#   3. Forward execution to remote target via 'gt exec <target_id>'
#   4. Pull updated code back locally from origin
#   (Local machine does NOT run agy, only git & gt)
# ==============================================================================

set -euo pipefail

TIMEOUT="${AGY_TIMEOUT:-30m}"
DEFAULT_TARGET="${AGY_TARGET:-agy-remote-server}"

show_help() {
  cat <<'EOF'
Usage:
  agy-remote.sh <path/to/plan.md>            Implement a plan file remotely
  agy-remote.sh continue [instructions...]   Continue remote implementation or supply feedback
  agy-remote.sh -h, --help                   Show this help message

Default Remote Environment:
  Target:    agy-remote-server (override via AGY_TARGET)
  Directory: /workspace/<repo-name> (override via REMOTE_WORK_DIR)
  Timeout:   30m (override via AGY_TIMEOUT)
EOF
}

if [ $# -lt 1 ]; then
  show_help >&2
  echo "[agy-remote] Error: Missing command or plan file." >&2
  exit 1
fi

case "$1" in
  -h|--help|help)
    show_help
    exit 0
    ;;
esac

TARGET_ID="$DEFAULT_TARGET"
ACTION="$1"
shift

INSTRUCTIONS=""
if [ "$ACTION" = "continue" ]; then
  INSTRUCTIONS="$*"
else
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

PROJECT_NAME="$(basename "$(git rev-parse --show-toplevel)")"
REMOTE_DIR="${REMOTE_WORK_DIR:-/workspace/${PROJECT_NAME}}"

# Step 1: Local side - stage & commit uncommitted changes (such as plan.md), then push to remote branch
if [ "${AGY_TEST_MOCK:-0}" != "1" ]; then
  if [ -n "$(git status --porcelain)" ]; then
    echo "[agy-remote] Staging and committing local changes on '$CURRENT_BRANCH'..."
    git add -A
    git commit -m "docs/feat(agy-remote): auto-commit before remote execution"
  fi
  echo "[agy-remote] Syncing local branch '$CURRENT_BRANCH' to origin..."
  git push -u origin "$CURRENT_BRANCH"
fi

# Step 2: Build prompt
if [ "$ACTION" = "continue" ]; then
  if [ -z "$INSTRUCTIONS" ]; then
    REMOTE_PROMPT="Continue implementing the plan. Check current progress, finish all remaining tasks, and ensure all tests pass."
  else
    REMOTE_PROMPT="Continue implementing the plan: ${INSTRUCTIONS}. Finish remaining tasks and ensure tests pass."
  fi
  CONTINUE_FLAG="-c"
else
  REMOTE_PROMPT="/goal Implement Plan @${ACTION}"
  CONTINUE_FLAG=""
fi

# Encode prompt to Base64 (single-line, safe from all shell quoting)
ENCODED_PROMPT="$(printf '%s' "$REMOTE_PROMPT" | base64 | tr -d '\r\n')"

# Step 3: Dispatch remote payload via gt exec (all compilation/test/agy execution happens inside the container)
REMOTE_SCRIPT=$(cat <<REMOTE_EOF
set -e
# PROJECT_DIR_CHECK
if [ ! -d "$REMOTE_DIR" ]; then
  echo "[agy-remote] Error: Remote directory '$REMOTE_DIR' does not exist in $TARGET_ID." >&2
  exit 1
fi
cd "$REMOTE_DIR"

git fetch origin "$CURRENT_BRANCH"
git checkout "$CURRENT_BRANCH"
git pull origin "$CURRENT_BRANCH"

DECODED_PROMPT=\$(printf '%s' "$ENCODED_PROMPT" | base64 -d)

if [ -n "$CONTINUE_FLAG" ]; then
  agy --mode accept-edits --print-timeout "$TIMEOUT" --output-format json -c -p "\$DECODED_PROMPT"
else
  agy --mode accept-edits --print-timeout "$TIMEOUT" --output-format json -p "\$DECODED_PROMPT"
fi

if [ -n "\$(git status --porcelain)" ]; then
  git add -A
  git commit -m "feat(agy-remote): update code via remote agy"
  git push origin "$CURRENT_BRANCH"
fi
REMOTE_EOF
)

TMP_OUT="$(mktemp -t agy-remote-out.XXXXXX)"
trap 'rm -f "$TMP_OUT"' EXIT

echo "[agy-remote] Forwarding execution to remote target '$TARGET_ID' via gt exec..."
GT_EXIT=0
gt exec "$TARGET_ID" bash -c "$REMOTE_SCRIPT" > "$TMP_OUT" || GT_EXIT=$?

# Step 4: Parse remote JSON response output
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

# Step 5: Local side - pull back remote changes
if [ "${AGY_TEST_MOCK:-0}" != "1" ]; then
  echo -e "\n[agy-remote] Pulling remote changes from origin/$CURRENT_BRANCH..."
  git pull origin "$CURRENT_BRANCH" || true
fi

# Step 6: Post-Execution Summary
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo -e "\n================ Git Status ================"
  git status --short
  echo -e "\n================ Git Diff Stat ============="
  git diff --stat

  HAS_UNCOMMITTED="$(git status --porcelain 2>/dev/null || true)"

  echo -e "\n================ Suggested Next Steps ================"
  [ -n "$CURRENT_BRANCH" ] && echo "Current Branch: $CURRENT_BRANCH"

  if [ -n "$HAS_UNCOMMITTED" ]; then
    echo "1. Uncommitted changes detected locally:"
    echo "   git add -A && git commit -m \"feat: <description>\""
  else
    echo "1. Working tree:     clean (all changes committed)"
  fi

  echo "2. Iterate or fix:   agy-remote.sh continue \"[optional feedback]\""
  echo "3. Run local tests:  verify independently before merging"
  if [ -n "$CURRENT_BRANCH" ] && [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
    echo "4. Push branch:      git push -u origin $CURRENT_BRANCH"
    echo "5. Merge to main:    git checkout main && git merge $CURRENT_BRANCH"
  else
    echo "4. Push to remote:   git push"
  fi
  echo -e "======================================================\n"
fi

exit "$GT_EXIT"
