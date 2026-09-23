# agy-remote Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `agy-remote` skill to execute implementation plans on remote containers/hosts via `gt exec` with automated Git branch synchronization and result reporting.

**Architecture:** A bash runner script `agy-remote/scripts/agy-remote.sh` manages local pre-flight Git checks and pushing, invokes a bundled remote shell payload inside `gt exec <target_id>`, syncs returned commits back to the local branch, formats the execution summary, and reports next steps. Accompanied by skill documentation and circuit breaker rules in `agy-remote/SKILL.md`.

**Tech Stack:** Bash, Git, Python 3 (JSON parsing), Markdown (YAML frontmatter)

## Global Constraints

- Supported CLI interfaces:
  - `agy-remote.sh <target_id> <path/to/plan.md>`
  - `agy-remote.sh <target_id> continue [instructions...]`
  - `agy-remote.sh <path/to/plan.md>` (when `AGY_TARGET` env var is set)
  - `agy-remote.sh continue [instructions...]` (when `AGY_TARGET` env var is set)
  - `agy-remote.sh -h | --help`
- Default timeout: `30m` (overrideable via `AGY_TIMEOUT`).
- Pre-flight blocks execution if on `main` or `master` branch.
- Execution payload invokes remote `agy` with `--mode accept-edits --print-timeout "$TIMEOUT" --output-format json`.
- Must verify `gt` executable exists locally.
- Must provide unit/integration tests for CLI parsing, environment handling, and workflow logic with mocked dependencies.

---

### Task 1: CLI Argument Parsing and Target Resolution Unit Tests

**Files:**
- Create: `agy-remote/tests/test_cli_args.sh`
- Create: `agy-remote/scripts/agy-remote.sh`

**Interfaces:**
- Produces: CLI argument parser in `agy-remote.sh` supporting `<target_id> <plan.md>`, `<target_id> continue`, `AGY_TARGET` fallback, and `--help`.

- [x] **Step 1: Write CLI argument parser tests**

Create `agy-remote/tests/test_cli_args.sh`:
```bash
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
```

- [x] **Step 2: Run test to verify it fails**

Run:
```bash
chmod +x agy-remote/tests/test_cli_args.sh || true
bash agy-remote/tests/test_cli_args.sh
```
Expected: FAIL (file `agy-remote/scripts/agy-remote.sh` not found).

- [x] **Step 3: Implement argument and target resolution in `agy-remote.sh`**

Create `agy-remote/scripts/agy-remote.sh`:
```bash
#!/usr/bin/env bash
# ==============================================================================
# agy-remote.sh - Remote runner for AGY plan execution via gt exec
# ==============================================================================

set -euo pipefail

TIMEOUT="${AGY_TIMEOUT:-30m}"
DEFAULT_TARGET="${AGY_TARGET:-}"
REMOTE_DIR="${REMOTE_WORK_DIR:-}"

show_help() {
  cat <<'EOF'
Usage:
  agy-remote.sh <target_id> <path/to/plan.md>            Implement a plan file remotely
  agy-remote.sh <target_id> continue [instructions...]   Continue remote implementation or supply feedback
  agy-remote.sh <path/to/plan.md>                        Implement plan (using $AGY_TARGET)
  agy-remote.sh continue [instructions...]               Continue (using $AGY_TARGET)
  agy-remote.sh -h, --help                               Show this help message

Environment Variables:
  AGY_TARGET       Default target ID/container (allows omitting target_id in CLI)
  AGY_TIMEOUT      Execution timeout (default: 30m)
  REMOTE_WORK_DIR  Remote working directory (default: git root in remote container)
EOF
}

if [ $# -lt 1 ]; then
  show_help >&2
  echo "[agy-remote] Error: Missing target ID or plan file." >&2
  exit 1
fi

case "$1" in
  -h|--help|help)
    show_help
    exit 0
    ;;
esac

TARGET_ID=""
ACTION=""
INSTRUCTIONS=""

if [ -n "$DEFAULT_TARGET" ]; then
  # If AGY_TARGET is set, check if $1 is a plan file or continue
  if [ "$1" = "continue" ] || [ -f "$1" ] || [[ "$1" == *.md ]]; then
    TARGET_ID="$DEFAULT_TARGET"
    ACTION="$1"
    shift
    [ "$ACTION" = "continue" ] && INSTRUCTIONS="$*"
  else
    TARGET_ID="$1"
    shift
    if [ $# -lt 1 ]; then
      echo "[agy-remote] Error: Missing command or plan file for target '$TARGET_ID'." >&2
      exit 1
    fi
    ACTION="$1"
    shift
    [ "$ACTION" = "continue" ] && INSTRUCTIONS="$*"
  fi
else
  TARGET_ID="$1"
  shift
  if [ $# -lt 1 ]; then
    echo "[agy-remote] Error: Missing command or plan file for target '$TARGET_ID'." >&2
    exit 1
  fi
  ACTION="$1"
  shift
  [ "$ACTION" = "continue" ] && INSTRUCTIONS="$*"
fi

# Validate target and action
if [ -z "$TARGET_ID" ]; then
  echo "[agy-remote] Error: Target ID must be provided as first argument or via AGY_TARGET." >&2
  exit 1
fi

if [ "$ACTION" != "continue" ]; then
  if [ ! -f "$ACTION" ]; then
    echo "[agy-remote] Error: Plan file not found: '$ACTION'." >&2
    exit 1
  fi
fi

# Placeholder for downstream execution steps
echo "TARGET: $TARGET_ID, ACTION: $ACTION, TIMEOUT: $TIMEOUT"
```

- [x] **Step 4: Run test to verify it passes**

Run:
```bash
chmod +x agy-remote/scripts/agy-remote.sh
chmod +x agy-remote/tests/test_cli_args.sh
bash agy-remote/tests/test_cli_args.sh
```
Expected: PASS with all 4 tests passing.

- [x] **Step 5: Commit changes**

```bash
git add agy-remote/scripts/agy-remote.sh agy-remote/tests/test_cli_args.sh
git commit -m "feat(agy-remote): implement CLI argument parsing and target resolution"
```

---

### Task 2: Local Pre-flight Git Checks and Target Validation

**Files:**
- Modify: `agy-remote/tests/test_cli_args.sh`
- Modify: `agy-remote/scripts/agy-remote.sh`

**Interfaces:**
- Consumes: `TARGET_ID`, `ACTION`, `INSTRUCTIONS` from Task 1.
- Produces: Pre-flight check functions: `check_local_branch`, `check_dependencies`, `probe_target`.

- [x] **Step 1: Add pre-flight test cases to test script**

Modify `agy-remote/tests/test_cli_args.sh` to add mock testing for pre-flight:
```bash
# Add to agy-remote/tests/test_cli_args.sh:
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
```

- [x] **Step 2: Run test to verify failure**

Run:
```bash
bash agy-remote/tests/test_cli_args.sh
```
Expected: FAIL on Test 5 (branch protection not implemented).

- [x] **Step 3: Implement pre-flight validations in `agy-remote.sh`**

Modify `agy-remote/scripts/agy-remote.sh`:
- Check for `git` inside working tree.
- Check current branch; block if `main` or `master`.
- Check if `gt` is installed (bypassable in test mode via `AGY_TEST_MOCK=1`).
- Auto-stage and commit uncommitted changes on current branch with clear message, then `git push -u origin <branch>`:

```bash
check_preflight() {
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[agy-remote] Error: Must be inside a git repository." >&2
    exit 1
  fi

  CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    echo "[agy-remote] Error: Refusing to run on 'main' or 'master' branch." >&2
    echo "Please create or switch to a feature branch (e.g. git checkout -b feat/my-task)." >&2
    exit 1
  fi

  if [ "${AGY_TEST_MOCK:-0}" != "1" ]; then
    if ! command -v gt >/dev/null 2>&1; then
      echo "[agy-remote] Error: 'gt' CLI tool not found in PATH." >&2
      exit 127
    fi

    # Probe target container
    if ! gt exec "$TARGET_ID" echo ok >/dev/null 2>&1; then
      echo "[agy-remote] Error: Unable to connect to target '$TARGET_ID' via gt exec." >&2
      exit 1
    fi
  fi
}
```

- [x] **Step 4: Run test to verify it passes**

Run:
```bash
bash agy-remote/tests/test_cli_args.sh
```
Expected: PASS with all 5 tests passing.

- [x] **Step 5: Commit changes**

```bash
git add agy-remote/scripts/agy-remote.sh agy-remote/tests/test_cli_args.sh
git commit -m "feat(agy-remote): implement pre-flight git and target checks"
```

---

### Task 3: Remote Shell Payload Construction and Execution (`gt exec`)

**Files:**
- Create: `agy-remote/tests/test_remote_payload.sh`
- Modify: `agy-remote/scripts/agy-remote.sh`

**Interfaces:**
- Consumes: Validated `TARGET_ID`, `ACTION`, `INSTRUCTIONS`, `CURRENT_BRANCH`, `TIMEOUT`.
- Produces: `run_remote_execution` building and executing the remote script, capturing output, and handling return codes.

- [x] **Step 1: Write remote payload execution tests**

Create `agy-remote/tests/test_remote_payload.sh`:
```bash
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
```

- [x] **Step 2: Run test to verify it fails**

Run:
```bash
chmod +x agy-remote/tests/test_remote_payload.sh
bash agy-remote/tests/test_remote_payload.sh
```
Expected: FAIL (remote payload generation not implemented in `agy-remote.sh`).

- [x] **Step 3: Implement remote execution and summary formatting**

Modify `agy-remote/scripts/agy-remote.sh`:
- Construct remote command for `/goal` or `continue`:
```bash
# Push local branch to origin first
if [ "${AGY_TEST_MOCK:-0}" != "1" ]; then
  echo "[agy-remote] Syncing local branch '$CURRENT_BRANCH' to origin..."
  git push -u origin "$CURRENT_BRANCH"
fi

# Build remote agy prompt
if [ "$ACTION" = "continue" ]; then
  if [ -z "$INSTRUCTIONS" ]; then
    REMOTE_PROMPT="Continue implementing the plan. Check current progress, finish all remaining tasks, and ensure all tests pass."
  else
    REMOTE_PROMPT="Continue implementing the plan: ${INSTRUCTIONS}. Finish remaining tasks and ensure tests pass."
  fi
  AGY_ARGS=(-c -p "$REMOTE_PROMPT")
else
  REMOTE_PROMPT="/goal Implement Plan @${ACTION}"
  AGY_ARGS=(-p "$REMOTE_PROMPT")
fi

# Prepare remote execution script
REMOTE_SCRIPT=$(cat <<REMOTE_EOF
set -e
if [ -n "$REMOTE_DIR" ]; then
  cd "$REMOTE_DIR"
fi
git fetch origin "$CURRENT_BRANCH"
git checkout "$CURRENT_BRANCH"
git pull origin "$CURRENT_BRANCH"

agy --mode accept-edits --print-timeout "$TIMEOUT" --output-format json ${AGY_ARGS[@]}

if [ -n "\$(git status --porcelain)" ]; then
  git add -A
  git commit -m "feat(agy-remote): update code via agy"
  git push origin "$CURRENT_BRANCH"
fi
REMOTE_EOF
)

TMP_OUT="$(mktemp -t agy-remote-out.XXXXXX)"
trap 'rm -f "$TMP_OUT"' EXIT

echo "[agy-remote] Executing on remote target '$TARGET_ID'..."
gt exec "$TARGET_ID" bash -c "$REMOTE_SCRIPT" > "$TMP_OUT"
```
- Parse JSON output via `python3` and output Status, Conversation ID, Duration, and text response.
- Locally pull changes: `git pull origin "$CURRENT_BRANCH"`.
- Display git status and diff stat.

- [x] **Step 4: Run test to verify it passes**

Run:
```bash
bash agy-remote/tests/test_remote_payload.sh
```
Expected: PASS.

- [x] **Step 5: Commit changes**

```bash
git add agy-remote/scripts/agy-remote.sh agy-remote/tests/test_remote_payload.sh
git commit -m "feat(agy-remote): implement remote execution payload and output parsing"
```

---

### Task 4: Post-Execution Summary and Next Steps Reporting

**Files:**
- Modify: `agy-remote/scripts/agy-remote.sh`
- Modify: `agy-remote/tests/test_remote_payload.sh`

**Interfaces:**
- Consumes: Local working tree after `git pull`.
- Produces: Formatted git summary, diff stat, and actionable next steps instructions.

- [x] **Step 1: Add assertions for Git summary and next steps**

Modify `agy-remote/tests/test_remote_payload.sh` to check for:
- `================ Git Status ===============`
- `================ Git Diff Stat =============`
- `================ Suggested Next Steps ===============`

- [x] **Step 2: Run test to verify failure/coverage**

Run:
```bash
bash agy-remote/tests/test_remote_payload.sh
```

- [x] **Step 3: Update `agy-remote.sh` with complete post-execution summary**

Ensure `agy-remote.sh` mirrors `agy-goal.sh`'s clean summary reporting and displays actionable instructions:
- If uncommitted changes exist locally or pull had modifications.
- Commands to continue with `agy-remote.sh <target_id> continue "feedback"`.
- Commands to merge to `main` when finished.

- [x] **Step 4: Run test to verify it passes**

Run:
```bash
bash agy-remote/tests/test_cli_args.sh
bash agy-remote/tests/test_remote_payload.sh
```
Expected: All tests PASS.

- [x] **Step 5: Commit changes**

```bash
git add agy-remote/scripts/agy-remote.sh agy-remote/tests/test_remote_payload.sh
git commit -m "feat(agy-remote): add git summary and next steps guidance"
```

---

### Task 5: Skill Documentation and Circuit Breaker Rules (`SKILL.md`)

**Files:**
- Create: `agy-remote/SKILL.md`

**Interfaces:**
- Produces: Complete skill manual specifying commands, workflows, environment variables, and circuit breaker hard-stop rules.

- [x] **Step 1: Draft `agy-remote/SKILL.md`**

Create `agy-remote/SKILL.md`:
```markdown
---
name: agy-remote
description: Execute an implementation plan or continue/fix tasks remotely on containers via gt exec with automated Git sync.
---

# agy-remote

Execute and iterate on implementation plans remotely on target containers or developer machines using **gt exec** and **AGY CLI**.

## Commands

Run the runner script from `./agy-remote/scripts/agy-remote.sh` (or your configured skills path).

> [!NOTE]
> 默认单次任务超时时间为 **30 分钟**（可通过环境变量 `AGY_TIMEOUT` 调整，例如 `AGY_TIMEOUT=45m`）。
> 可以通过设置 `AGY_TARGET` 环境变量来设定默认目标 ID，省略每次命令行输入。

### 1. Implement Plan Remotely
Start executing a written markdown plan on the remote target:
```bash
agy-remote.sh <target_id> path/to/plan.md

# If AGY_TARGET is set:
agy-remote.sh path/to/plan.md
```

### 2. Continue Plan Execution (`continue`)
Continue the plan remotely to finish remaining tasks or supply targeted feedback:
```bash
# Continue without extra instructions:
agy-remote.sh <target_id> continue

# Continue with specific feedback or fix instructions:
agy-remote.sh <target_id> continue "Fix test failure in user_spec: assertion failed at line 42"
```

---

## Workflow & Circuit Breaker

1. **Pre-flight**: Ensure you are on a feature branch (not `main`/`master`). The runner pushes your plan to the remote branch.
2. **Execute**: The runner syncs the branch inside `gt exec <target_id>`, runs `agy`, and commits remote code changes back.
3. **Sync**: The runner pulls the remote changes back to your local repository.
4. **Verify**: Check `git diff` and run project tests locally.
5. **Iterate**: If tasks remain incomplete or tests fail, run `agy-remote.sh <target_id> continue ["feedback"]`.

### 🛑 Hard Stop & Escalation Rules
Do **NOT** guess or repeatedly edit files without progress. You must **STOP** and ask the user for a decision if:
- **Round Limit Exceeded**: You have run `continue` **3 times** and the plan is still not completed.
- **Identical Error Loop**: The exact same error or test failure persists across **2 consecutive turns**.
- **Connectivity / Merge Failure**: `gt exec` connectivity drops or Git encounters conflicting states.

**When stopped, report to the user immediately:**
1. What was completed successfully.
2. The exact blocking error or reason for failure.
3. Proposed options/suggestions, and ask the user how to proceed.
```

- [x] **Step 2: Validate documentation completeness and formatting**

Check line count and markdown structure:
```bash
wc -l agy-remote/SKILL.md
```
Expected: Clean, standard markdown under 70 lines.

- [x] **Step 3: Commit changes**

```bash
git add agy-remote/SKILL.md
git commit -m "docs(agy-remote): add skill documentation and circuit breaker rules"
```

---

### Task 6: End-to-End Test Suite Verification

**Files:**
- Modify: `agy-remote/tests/run_all_tests.sh` (create master test runner)

- [x] **Step 1: Create master test runner script**

Create `agy-remote/tests/run_all_tests.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running agy-remote test suite..."
bash "$TEST_DIR/test_cli_args.sh"
bash "$TEST_DIR/test_remote_payload.sh"
echo "All agy-remote tests passed successfully!"
```
```bash
chmod +x agy-remote/tests/run_all_tests.sh
```

- [x] **Step 2: Run all tests**

Run:
```bash
bash agy-remote/tests/run_all_tests.sh
```
Expected: `All agy-remote tests passed successfully!`

- [x] **Step 3: Commit changes**

```bash
git add agy-remote/tests/run_all_tests.sh
git commit -m "test(agy-remote): add end-to-end test suite runner"
```
