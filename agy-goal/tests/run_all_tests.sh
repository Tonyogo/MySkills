#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Running agy-goal test suite..."
"$SCRIPT_DIR/test_decision_gate.sh"
"$SCRIPT_DIR/test_script_gate_integration.sh"
echo "All tests completed successfully."
