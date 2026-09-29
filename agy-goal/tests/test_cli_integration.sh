#!/usr/bin/env bash
# agy-goal/tests/test_cli_integration.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$SCRIPT_DIR/scripts/agy-goal.sh"

echo "=== Test 1: CLI Help output ==="
"$BIN" -h | grep -q "usage:" || "$BIN" -h | grep -q "Usage:"
"$BIN" --help | grep -q "agy-goal"
echo "PASS: Help output"

echo "=== Test 2: Missing arguments ==="
OUTPUT="$("$BIN" 2>&1 || true)"
echo "$OUTPUT" | grep -qi "usage:"
echo "PASS: Missing arguments handled"

echo "=== Test 3: Plan file validation ==="
OUTPUT="$("$BIN" nonexistent_plan_file_12345.md 2>&1 || true)"
echo "$OUTPUT" | grep -q "Error: Plan file not found"
echo "PASS: Plan file validation handled"

echo "=== Test 4: Status and Reset commands ==="
"$BIN" reset
STATUS="$("$BIN" status)"
echo "$STATUS" | grep -q "Active:           False"
echo "PASS: Reset and status handled"

echo "=== All CLI integration tests passed! ==="
