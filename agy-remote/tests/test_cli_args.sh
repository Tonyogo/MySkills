#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$SCRIPT_DIR/scripts/agy-remote.sh"

echo "=== Test 1: Help output ==="
"$BIN" -h | grep -q "Usage:"
"$BIN" --help | grep -q "Usage:"
echo "PASS: Help output"

echo "=== Test 2: Missing arguments without AGY_TARGET ==="
OUTPUT="$("$BIN" 2>&1 || true)"
echo "$OUTPUT" | grep -q "Error: Missing target ID or plan file"
echo "PASS: Missing arguments handled"

echo "=== Test 3: Plan file validation ==="
OUTPUT="$("$BIN" dummy_target nonexistent_plan.md 2>&1 || true)"
echo "$OUTPUT" | grep -q "Error: Plan file not found: 'nonexistent_plan.md'"
echo "PASS: Plan file validation handled"

echo "=== Test 4: AGY_TARGET fallback for non-existent plan ==="
OUTPUT="$(AGY_TARGET=dummy_target "$BIN" nonexistent_plan.md 2>&1 || true)"
echo "$OUTPUT" | grep -q "Error: Plan file not found: 'nonexistent_plan.md'"
echo "PASS: AGY_TARGET fallback works"

echo "=== Test 5: Reject execution on main or master branch ==="
TEST_REPO="$(mktemp -d)"
(
  cd "$TEST_REPO"
  git init -b main >/dev/null 2>&1
  git config user.name "Test User"
  git config user.email "test@example.com"
  touch test.md
  git add test.md && git commit -m "init" >/dev/null 2>&1
  OUTPUT="$("$BIN" test_target test.md 2>&1 || true)"
  echo "$OUTPUT" | grep -q "Refusing to run on 'main' or 'master' branch"
)
rm -rf "$TEST_REPO"
echo "PASS: Branch protection works"

