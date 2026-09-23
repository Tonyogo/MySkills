#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$SCRIPT_DIR/scripts/agy-remote.sh"

TMP_BIN_DIR="$(mktemp -d)"
cat <<'EOF' > "$TMP_BIN_DIR/gt"
#!/usr/bin/env bash
echo "MOCK_GT_CALLED: $*"
cat <<'JSON'
{"conversation_id": "conv-123", "status": "COMPLETED", "duration_seconds": 12.5, "response": "Remote tasks completed."}
JSON
EOF
chmod +x "$TMP_BIN_DIR/gt"

echo "=== Test 1: Remote payload script generation ==="
TEST_REPO="$(mktemp -d)"
(
  cd "$TEST_REPO"
  git init -b feat/remote-test >/dev/null 2>&1
  git config user.name "Test User"
  git config user.email "test@example.com"
  touch plan.md
  git add plan.md && git commit -m "add plan" >/dev/null 2>&1
  git remote add origin "$TEST_REPO"

  PATH="$TMP_BIN_DIR:$PATH"
  OUTPUT="$("$BIN" plan.md)"
  echo "$OUTPUT" | grep -q "MOCK_GT_CALLED: exec agy-remote-server"
  echo "$OUTPUT" | grep -q "PROJECT_DIR_CHECK"
  echo "$OUTPUT" | grep -q "/workspace/$(basename "$TEST_REPO")"
  echo "$OUTPUT" | grep -q "Status:          COMPLETED"
  echo "$OUTPUT" | grep -q "Conversation ID: conv-123"
  echo "$OUTPUT" | grep -q "Remote tasks completed."
  echo "$OUTPUT" | grep -q "================ Git Status ================"
  echo "$OUTPUT" | grep -q "================ Git Diff Stat ============="
  echo "$OUTPUT" | grep -q "================ Suggested Next Steps ================"
)
rm -rf "$TEST_REPO"
echo "PASS: Remote execution and summary parsing work"

echo "=== Test 2: Base64 prompt encoding for complex characters ==="
TEST_REPO2="$(mktemp -d)"
(
  cd "$TEST_REPO2"
  git init -b feat/remote-test-2 >/dev/null 2>&1
  git config user.name "Test User"
  git config user.email "test@example.com"
  touch dummy.txt
  git add dummy.txt && git commit -m "init" >/dev/null 2>&1
  git remote add origin "$TEST_REPO2"

  PATH="$TMP_BIN_DIR:$PATH"
  OUTPUT="$("$BIN" continue 'Fix NPE in "user.spec": where $val == `nil` && echo "ok"')"
  echo "$OUTPUT" | grep -q "MOCK_GT_CALLED: exec agy-remote-server"
  echo "$OUTPUT" | grep -q "base64 -d"
  EXPECTED_PROMPT='Continue implementing the plan: Fix NPE in "user.spec": where $val == `nil` && echo "ok". Finish remaining tasks and ensure tests pass.'
  EXPECTED_B64="$(printf '%s' "$EXPECTED_PROMPT" | base64 | tr -d '\r\n')"
  echo "$OUTPUT" | grep -q "$EXPECTED_B64"
  echo "$OUTPUT" | grep -q "Status:          COMPLETED"
)
rm -rf "$TEST_REPO2"
echo "PASS: Complex prompt encoding works"

rm -rf "$TMP_BIN_DIR"
