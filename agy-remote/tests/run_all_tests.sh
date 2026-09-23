#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running agy-remote test suite..."
bash "$TEST_DIR/test_cli_args.sh"
bash "$TEST_DIR/test_remote_payload.sh"
echo "All agy-remote tests passed successfully!"
