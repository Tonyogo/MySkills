#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$SCRIPT_DIR/scripts/agy-remote.sh"

echo "=== Test 1: Remote payload script generation ==="
# Mock gt executable to verify the command string passed to it
TMP_BIN_DIR="$(mktemp -d)"
cat <<'EOF' > "$TMP_BIN_DIR/gt"
#!/usr/bin/env bash
echo "MOCK_GT_CALLED: $*"
cat <<'JSON'
{"conversation_id": "conv-123", "status": "COMPLETED", "duration_seconds": 12.5, "response": "Remote tasks completed."}
JSON
EOF
chmod +x "$TMP_BIN_DIR/gt"

TEST_REPO="$(mktemp -d)"
(
  cd "$TEST_REPO"
  git init -b feat/remote-test >/dev/null 2>&1
  git config user.name "Test User"
  git config user.email "test@example.com"
  touch plan.md
  git add plan.md && git commit -m "add plan" >/dev/null 2>&1
  # Mock a remote upstream
  git remote add origin "$TEST_REPO"

  PATH="$TMP_BIN_DIR:$PATH"
  OUTPUT="$("$BIN" test_target plan.md)"
  echo "$OUTPUT" | grep -q "MOCK_GT_CALLED: exec test_target"
  echo "$OUTPUT" | grep -q "Status:          COMPLETED"
  echo "$OUTPUT" | grep -q "Conversation ID: conv-123"
  echo "$OUTPUT" | grep -q "Remote tasks completed."
)
rm -rf "$TMP_BIN_DIR" "$TEST_REPO"
echo "PASS: Remote execution and summary parsing work"
