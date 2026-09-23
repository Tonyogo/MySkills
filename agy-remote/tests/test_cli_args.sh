#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$SCRIPT_DIR/scripts/agy-remote.sh"

echo "=== Test 1: Help output ==="
"$BIN" -h | grep -q "Usage:"
"$BIN" --help | grep -q "agy-remote.sh <path/to/plan.md>"
echo "PASS: Help output"

echo "=== Test 2: Missing arguments ==="
OUTPUT="$("$BIN" 2>&1 || true)"
echo "$OUTPUT" | grep -q "Error: Missing command or plan file"
echo "PASS: Missing arguments handled"

echo "=== Test 3: Plan file validation ==="
OUTPUT="$("$BIN" nonexistent_plan.md 2>&1 || true)"
echo "$OUTPUT" | grep -q "Error: Plan file not found: 'nonexistent_plan.md'"
echo "PASS: Plan file validation handled"

echo "=== Test 4: Reject execution on main or master branch ==="
TEST_REPO="$(mktemp -d)"
(
  cd "$TEST_REPO"
  git init -b main >/dev/null 2>&1
  git config user.name "Test User"
  git config user.email "test@example.com"
  touch test.md
  git add test.md && git commit -m "init" >/dev/null 2>&1
  OUTPUT="$("$BIN" test.md 2>&1 || true)"
  echo "$OUTPUT" | grep -q "Refusing to run on 'main' or 'master' branch"
)
rm -rf "$TEST_REPO"
echo "PASS: Branch protection works"
