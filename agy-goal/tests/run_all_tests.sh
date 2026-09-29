#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Running Python Unit Tests ==="
python3 -m unittest discover -s "$SCRIPT_DIR" -p "test_*.py" -v

echo "=== Running CLI Integration Tests ==="
bash "$SCRIPT_DIR/test_cli_integration.sh"

echo "All agy-goal tests passed successfully."
