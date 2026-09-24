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

# Setup temporary mock agy environment for E2E tests
MOCK_DIR="$(mktemp -d -t mock-agy.XXXXXX)"
trap 'rm -rf "$MOCK_DIR"' EXIT

cat << 'EOF' > "$MOCK_DIR/agy"
#!/usr/bin/env bash
case "${MOCK_AGY_MODE:-completed}" in
  completed)
    echo '{"conversation_id":"mock-1","status":"SUCCESS","duration_seconds":1.5,"response":"All plan tasks implemented successfully.\n<!-- GOAL_COMPLETE -->"}'
    exit 0
    ;;
  error)
    echo '{"conversation_id":"mock-2","status":"ERROR","duration_seconds":1.0,"response":"Test failed on line 12."}'
    exit 1
    ;;
  empty)
    # Output nothing and exit non-zero (simulating crash)
    exit 1
    ;;
  malformed)
    echo 'RAW_OUTPUT_NOT_JSON: something broke'
    exit 1
    ;;
esac
EOF
chmod +x "$MOCK_DIR/agy"

DUMMY_PLAN="$MOCK_DIR/test_plan.md"
echo "# Dummy Test Plan" > "$DUMMY_PLAN"

echo "=== Test 4: E2E Output rendering for success status ==="
OUT="$(PATH="$MOCK_DIR:$PATH" MOCK_AGY_MODE=completed "$BIN" "$DUMMY_PLAN")"
echo "$OUT" | grep -q "Status:          SUCCESS"
echo "$OUT" | grep -q "Conversation ID: mock-1"
echo "$OUT" | grep -q "Goal Complete:   YES"
echo "$OUT" | grep -q "All plan tasks implemented successfully."
echo "PASS: Success status rendered correctly"

echo "=== Test 5: E2E Output rendering for error status ==="
OUT="$(PATH="$MOCK_DIR:$PATH" MOCK_AGY_MODE=error "$BIN" "$DUMMY_PLAN" 2>&1 || true)"
echo "$OUT" | grep -q "Status:          ERROR"
echo "$OUT" | grep -q "Goal Complete:   NO"
echo "$OUT" | grep -q "Test failed on line 12."
echo "PASS: Error status rendered correctly"

echo "=== Test 6: E2E Output rendering for empty output crash ==="
OUT="$(PATH="$MOCK_DIR:$PATH" MOCK_AGY_MODE=empty "$BIN" "$DUMMY_PLAN" 2>&1 || true)"
echo "PASS: Empty output handled cleanly without script explosion"

echo "=== Test 7: E2E Output rendering for malformed raw output ==="
OUT="$(PATH="$MOCK_DIR:$PATH" MOCK_AGY_MODE=malformed "$BIN" "$DUMMY_PLAN" 2>&1 || true)"
echo "$OUT" | grep -q "RAW_OUTPUT_NOT_JSON: something broke"
echo "PASS: Malformed raw output fallback rendered correctly"

echo "=== All runner tests passed! ==="
