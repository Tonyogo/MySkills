#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Running Python Unit Tests ==="
python3 "$SCRIPT_DIR/test_agy_goal.py" -v

echo "=== Running CLI Integration Tests ==="
bash "$SCRIPT_DIR/test_cli_integration.sh"

echo "=== Running Decision Gate Mock Tests ==="
bash "$SCRIPT_DIR/test_decision_gate.sh"

echo "All agy-goal tests passed successfully."
