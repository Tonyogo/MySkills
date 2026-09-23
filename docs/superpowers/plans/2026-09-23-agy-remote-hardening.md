# agy-remote Hardening and Ergonomics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden `agy-remote` by eliminating target ID arguments from CLI invocations (defaulting to `agy-remote-server`), establishing convention-based remote directory resolution (`/workspace/<project>`), encoding prompts with Base64 to eliminate quoting breakage, and protecting local Git staging.

**Architecture:** Refactor `agy-remote/scripts/agy-remote.sh` to align its CLI 100% with `agy-goal.sh` (`<plan.md>` and `continue`), use `agy-remote-server` as the hardcoded target default (overrideable via `AGY_TARGET`), compute the remote directory dynamically as `/workspace/$(basename $(git rev-parse --show-toplevel))`, encode prompts via Base64 before dispatching through `gt exec`, and update tests and documentation.

**Tech Stack:** Bash, Git, Python 3, Base64

## Global Constraints

- Supported CLI interfaces:
  - `agy-remote.sh <path/to/plan.md>`
  - `agy-remote.sh continue [instructions...]`
  - `agy-remote.sh -h | --help`
  - No `<target_id>` positional parameter allowed in daily commands.
- Defaults:
  - Target ID: `agy-remote-server` (overrideable only via `AGY_TARGET` env var).
  - Remote Directory: `/workspace/${PROJECT_NAME}` (overrideable only via `REMOTE_WORK_DIR` env var).
  - Timeout: `30m` (overrideable via `AGY_TIMEOUT` env var).
- Base64 prompt encoding must prevent shell quote and special character breakage.
- Pre-flight blocks execution on `main` or `master` branch.
- Automated tests must verify all parsing, payload generation, decoding, and directory checks using mock runners.

---

### Task 1: Update CLI Argument Parsing and Target Defaults

**Files:**
- Modify: `agy-remote/tests/test_cli_args.sh`
- Modify: `agy-remote/scripts/agy-remote.sh:12-87`

**Interfaces:**
- Produces: CLI interface in `agy-remote.sh` accepting exclusively `<plan.md>` or `continue [instructions...]`, defaulting `TARGET_ID` to `agy-remote-server`.

- [ ] **Step 1: Write failing CLI tests for the new argument structure**

Update `agy-remote/tests/test_cli_args.sh` to test the new argument parsing:
```bash
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
bash agy-remote/tests/test_cli_args.sh
```
Expected: FAIL (argument mismatch or error parsing with `test.md`).

- [ ] **Step 3: Refactor argument parsing and default target in `agy-remote.sh`**

Modify `agy-remote/scripts/agy-remote.sh`:
- Set `DEFAULT_TARGET="${AGY_TARGET:-agy-remote-server}"`.
- Parse arguments directly without `<target_id>` positional parameter:
```bash
show_help() {
  cat <<'EOF'
Usage:
  agy-remote.sh <path/to/plan.md>            Implement a plan file remotely
  agy-remote.sh continue [instructions...]   Continue remote implementation or supply feedback
  agy-remote.sh -h, --help                   Show this help message

Default Remote Environment:
  Target:    agy-remote-server (override via AGY_TARGET)
  Directory: /workspace/<repo-name> (override via REMOTE_WORK_DIR)
  Timeout:   30m (override via AGY_TIMEOUT)
EOF
}

if [ $# -lt 1 ]; then
  show_help >&2
  echo "[agy-remote] Error: Missing command or plan file." >&2
  exit 1
fi

case "$1" in
  -h|--help|help)
    show_help
    exit 0
    ;;
esac

TARGET_ID="$DEFAULT_TARGET"
ACTION="$1"
shift

INSTRUCTIONS=""
if [ "$ACTION" = "continue" ]; then
  INSTRUCTIONS="$*"
else
  if [ ! -f "$ACTION" ]; then
    echo "[agy-remote] Error: Plan file not found: '$ACTION'." >&2
    exit 1
  fi
fi
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
bash agy-remote/tests/test_cli_args.sh
```
Expected: PASS for all 4 tests.

- [ ] **Step 5: Commit changes**

```bash
git add agy-remote/scripts/agy-remote.sh agy-remote/tests/test_cli_args.sh
git commit -m "feat(agy-remote): default target to agy-remote-server and simplify CLI arguments"
```

---

### Task 2: Conventional Remote Working Directory Resolution & Validation

**Files:**
- Modify: `agy-remote/scripts/agy-remote.sh`
- Modify: `agy-remote/tests/test_remote_payload.sh`

**Interfaces:**
- Produces: Dynamic calculation of `REMOTE_DIR="/workspace/${PROJECT_NAME}"` and pre-check inside container.

- [ ] **Step 1: Add directory resolution test in `test_remote_payload.sh`**

Modify `agy-remote/tests/test_remote_payload.sh` to assert that the remote script inspects `/workspace/<PROJECT_NAME>`:
```bash
# Add assertion in test_remote_payload.sh:
echo "$OUTPUT" | grep -q "PROJECT_DIR_CHECK"
```

- [ ] **Step 2: Run test to verify failure**

Run:
```bash
bash agy-remote/tests/test_remote_payload.sh
```
Expected: FAIL.

- [ ] **Step 3: Implement dynamic remote directory resolution in `agy-remote.sh`**

In `agy-remote/scripts/agy-remote.sh`:
- Compute project name:
```bash
PROJECT_NAME="$(basename "$(git rev-parse --show-toplevel)")"
REMOTE_DIR="${REMOTE_WORK_DIR:-/workspace/${PROJECT_NAME}}"
```
- In the remote script payload, check that `$REMOTE_DIR` exists before attempting `cd`:
```bash
if [ ! -d "$REMOTE_DIR" ]; then
  echo "[agy-remote] Error: Remote directory '$REMOTE_DIR' does not exist in $TARGET_ID." >&2
  exit 1
fi
cd "$REMOTE_DIR"
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
bash agy-remote/tests/test_remote_payload.sh
```
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add agy-remote/scripts/agy-remote.sh agy-remote/tests/test_remote_payload.sh
git commit -m "feat(agy-remote): add convention-based remote directory resolution and validation"
```

---

### Task 3: Base64 Prompt Encoding and Safe Remote Decoding

**Files:**
- Modify: `agy-remote/scripts/agy-remote.sh`
- Modify: `agy-remote/tests/test_remote_payload.sh`

**Interfaces:**
- Consumes: `REMOTE_PROMPT` containing complex characters (quotes, backticks, newlines).
- Produces: `ENCODED_PROMPT` sent to remote container and safely decoded via Base64.

- [ ] **Step 1: Add test for complex instructions containing quotes and special characters**

In `agy-remote/tests/test_remote_payload.sh`, add a test invoking:
```bash
"$BIN" continue 'Fix NPE in "user.spec": where $val == `nil` && echo "ok"'
```
Verify that the prompt is passed intact without shell breakage.

- [ ] **Step 2: Run test to verify behavior**

Run:
```bash
bash agy-remote/tests/test_remote_payload.sh
```

- [ ] **Step 3: Implement Base64 prompt encoding in `agy-remote.sh`**

Modify `agy-remote/scripts/agy-remote.sh`:
```bash
# Build prompt
if [ "$ACTION" = "continue" ]; then
  if [ -z "$INSTRUCTIONS" ]; then
    REMOTE_PROMPT="Continue implementing the plan. Check current progress, finish all remaining tasks, and ensure all tests pass."
  else
    REMOTE_PROMPT="Continue implementing the plan: ${INSTRUCTIONS}. Finish remaining tasks and ensure tests pass."
  fi
  CONTINUE_FLAG="-c"
else
  REMOTE_PROMPT="/goal Implement Plan @${ACTION}"
  CONTINUE_FLAG=""
fi

# Encode prompt to Base64 (single-line, safe from all shell quoting)
ENCODED_PROMPT="$(printf '%s' "$REMOTE_PROMPT" | base64 | tr -d '\r\n')"

# Dispatch remote execution payload
REMOTE_SCRIPT=$(cat <<REMOTE_EOF
set -e
if [ ! -d "$REMOTE_DIR" ]; then
  echo "[agy-remote] Error: Remote directory '$REMOTE_DIR' does not exist in $TARGET_ID." >&2
  exit 1
fi
cd "$REMOTE_DIR"

git fetch origin "$CURRENT_BRANCH"
git checkout "$CURRENT_BRANCH"
git pull origin "$CURRENT_BRANCH"

DECODED_PROMPT=\$(printf '%s' "$ENCODED_PROMPT" | base64 -d)

if [ -n "$CONTINUE_FLAG" ]; then
  agy --mode accept-edits --print-timeout "$TIMEOUT" --output-format json -c -p "\$DECODED_PROMPT"
else
  agy --mode accept-edits --print-timeout "$TIMEOUT" --output-format json -p "\$DECODED_PROMPT"
fi

if [ -n "\$(git status --porcelain)" ]; then
  git add -A
  git commit -m "feat(agy-remote): update code via remote agy"
  git push origin "$CURRENT_BRANCH"
fi
REMOTE_EOF
)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
bash agy-remote/tests/test_remote_payload.sh
```
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add agy-remote/scripts/agy-remote.sh agy-remote/tests/test_remote_payload.sh
git commit -m "feat(agy-remote): implement Base64 prompt encoding and remote decoding"
```

---

### Task 4: Targeted Local Staging and Workspace Protection

**Files:**
- Modify: `agy-remote/scripts/agy-remote.sh`
- Modify: `agy-remote/tests/test_remote_payload.sh`

**Interfaces:**
- Produces: Safer local git staging (specifically staging `$ACTION` if it is a plan file, avoiding blind `git add -A`).

- [ ] **Step 1: Write test checking that plan file is staged specifically**

In `agy-remote/tests/test_remote_payload.sh`, verify that when uncommitted `plan.md` is present, it is committed before pushing.

- [ ] **Step 2: Update local staging logic in `agy-remote.sh`**

Modify `agy-remote/scripts/agy-remote.sh`:
```bash
if [ "${AGY_TEST_MOCK:-0}" != "1" ]; then
  if [ "$ACTION" != "continue" ] && [ -f "$ACTION" ]; then
    if git status --porcelain "$ACTION" | grep -q .; then
      echo "[agy-remote] Staging and committing plan file '$ACTION'..."
      git add "$ACTION"
      git commit -m "docs(plan): add or update plan before remote execution"
    fi
  elif [ -n "$(git status --porcelain)" ]; then
    echo "[agy-remote] Note: Local branch has uncommitted changes. Staging before sync..."
    git add -A
    git commit -m "wip(agy-remote): sync local work before continue"
  fi
  echo "[agy-remote] Syncing local branch '$CURRENT_BRANCH' to origin..."
  git push -u origin "$CURRENT_BRANCH"
fi
```

- [ ] **Step 3: Run test to verify it passes**

Run:
```bash
bash agy-remote/tests/run_all_tests.sh
```
Expected: All tests PASS.

- [ ] **Step 4: Commit changes**

```bash
git add agy-remote/scripts/agy-remote.sh agy-remote/tests/test_remote_payload.sh
git commit -m "feat(agy-remote): implement targeted local plan staging"
```

---

### Task 5: Update Documentation (`SKILL.md` & `README.md`)

**Files:**
- Modify: `agy-remote/SKILL.md`
- Modify: `README.md`

**Interfaces:**
- Produces: Updated skill manual and root README reflecting zero-argument target and conventional `/workspace/<project>` directory.

- [ ] **Step 1: Update `agy-remote/SKILL.md`**

Reflect the new command signatures:
```bash
# 1. Implement plan
agy-remote.sh path/to/plan.md

# 2. Continue
agy-remote.sh continue [optional instructions...]
```
Document default `agy-remote-server` and `/workspace/<project>`.

- [ ] **Step 2: Update root `README.md`**

Update `agy-remote` row and details in `README.md`.

- [ ] **Step 3: Verify formatting and line counts**

Run:
```bash
git diff agy-remote/SKILL.md README.md
```

- [ ] **Step 4: Commit changes**

```bash
git add agy-remote/SKILL.md README.md
git commit -m "docs(agy-remote): update documentation for hardened zero-target CLI"
```

---

### Task 6: End-to-End Test Suite Verification

**Files:**
- Modify: `agy-remote/tests/run_all_tests.sh`

- [ ] **Step 1: Run complete test suite**

Run:
```bash
bash agy-remote/tests/run_all_tests.sh
```
Expected: `All agy-remote tests passed successfully!`

- [ ] **Step 2: Verify git working tree is clean**

Run:
```bash
git status
```
Expected: `working tree clean`.
