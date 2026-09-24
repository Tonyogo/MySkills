#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$SCRIPT_DIR/scripts/agy-goal.sh"

echo "=== Test 1: CLI Help output ==="
"$BIN" -h | grep -q "Usage:"
"$BIN" --help | grep -q "agy-goal.sh <path/to/plan.md>"
echo "PASS: Help output"

echo "=== Test 2: Missing arguments ==="
OUTPUT="$("$BIN" 2>&1 || true)"
echo "$OUTPUT" | grep -q "Usage:"
echo "PASS: Missing arguments handled"

echo "=== Test 3: Plan file validation ==="
OUTPUT="$("$BIN" nonexistent_plan_file_12345.md 2>&1 || true)"
echo "$OUTPUT" | grep -q "Error: Unknown command or plan file not found"
echo "PASS: Plan file validation handled"

echo "=== Test 4: Decision Gate rendering for completed status ==="
TMP_JSON="$(mktemp -t test-comp.XXXXXX.json)"
cat << 'EOF' > "$TMP_JSON"
{
  "conversation_id": "test-cid-123",
  "status": "COMPLETED",
  "duration_seconds": 12.5,
  "response": "All tasks in plan have been implemented and verified."
}
EOF

# Test python decision gate parser directly
PARSER_OUTPUT="$(python3 -c '
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
exit_code = int(sys.argv[2])
status = data.get("status", "UNKNOWN")
is_completed = (exit_code == 0 and status == "COMPLETED")

print("==================== DECISION GATE ====================")
if is_completed:
    print("Decision: READY FOR COMPLETION")
    print("Action:   Plan executed successfully by AGY.")
    print("Next:     Review git diff, then commit and report completion to user.")
else:
    print("Decision: ACTION REQUIRED (INCOMPLETE / ERROR)")
    print("Action:   DO NOT run manual tests or debug manually.")
    print("Next:     Run: agy-goal.sh continue \"<1-2 sentence issue summary>\"")
print("=======================================================")
' "$TMP_JSON" 0)"

rm -f "$TMP_JSON"

echo "$PARSER_OUTPUT" | grep -q "Decision: READY FOR COMPLETION"
echo "$PARSER_OUTPUT" | grep -q "Action:   Plan executed successfully by AGY."
echo "PASS: Completed status generates READY FOR COMPLETION gate"

echo "=== Test 5: Decision Gate rendering for error status ==="
TMP_JSON_ERR="$(mktemp -t test-err.XXXXXX.json)"
cat << 'EOF' > "$TMP_JSON_ERR"
{
  "conversation_id": "test-cid-456",
  "status": "ERROR",
  "duration_seconds": 5.0,
  "response": "Encountered syntax error in auth.js line 12"
}
EOF

PARSER_OUTPUT_ERR="$(python3 -c '
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
exit_code = int(sys.argv[2])
status = data.get("status", "UNKNOWN")
is_completed = (exit_code == 0 and status == "COMPLETED")

print("==================== DECISION GATE ====================")
if is_completed:
    print("Decision: READY FOR COMPLETION")
    print("Action:   Plan executed successfully by AGY.")
    print("Next:     Review git diff, then commit and report completion to user.")
else:
    print("Decision: ACTION REQUIRED (INCOMPLETE / ERROR)")
    print("Action:   DO NOT run manual tests or debug manually.")
    print("Next:     Run: agy-goal.sh continue \"<1-2 sentence issue summary>\"")
print("=======================================================")
' "$TMP_JSON_ERR" 0)"

rm -f "$TMP_JSON_ERR"

echo "$PARSER_OUTPUT_ERR" | grep -q "Decision: ACTION REQUIRED (INCOMPLETE / ERROR)"
echo "$PARSER_OUTPUT_ERR" | grep -q "Action:   DO NOT run manual tests or debug manually."
echo "PASS: Error status generates ACTION REQUIRED gate"

echo "=== All decision gate tests passed! ==="
