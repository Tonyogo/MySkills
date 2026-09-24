#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$SCRIPT_DIR/scripts/agy-goal.sh"

# Check if agy-goal.sh contains DECISION GATE string
echo "=== Check DECISION GATE presence in agy-goal.sh ==="
if grep -q "DECISION GATE" "$BIN"; then
  echo "PASS: DECISION GATE is implemented in agy-goal.sh"
else
  echo "FAIL: DECISION GATE is missing from agy-goal.sh"
  exit 1
fi
