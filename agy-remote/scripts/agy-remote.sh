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

# Placeholder for downstream execution steps
echo "TARGET: $TARGET_ID, ACTION: $ACTION, TIMEOUT: $TIMEOUT"
