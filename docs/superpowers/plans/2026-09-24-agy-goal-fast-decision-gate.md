# `agy-goal` Fast Decision Gate & Anti-Thrashing Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform `agy-goal` into a fast, binary decision gate workflow that eliminates host-agent test thrashing and enforces immediate completion or continuation.

**Architecture:** Update `agy-goal.sh` to render an explicit `[DECISION GATE]` block in its post-execution output based on AGY exit code and status. Rewrite `agy-goal/SKILL.md` to establish strict negative constraints against manual testing or debugging by the host agent, routing all iterations directly into `continue`.

**Tech Stack:** Bash, Python 3 (JSON parsing & formatting in runner script), Markdown.

**Spec:** `docs/superpowers/specs/2026-09-24-agy-goal-fast-decision-gate-design.md`

## Global Constraints

- CLI syntax for `agy-goal.sh` must remain 100% backward-compatible (`<plan.md>` and `continue [instructions...]`).
- No external dependencies beyond bash, git, and python3 standard library.
- Strict negative constraints on the host agent: zero manual test commands (`npm test`, `pytest`, etc.) and zero manual code patching.
- Explicit circuit breaker: maximum 3 `continue` attempts before mandatory escalation to the human user.

## Review Focus

1. **Non-zero AGY exit with valid JSON**: Ensure `[DECISION GATE]` marks `ACTION REQUIRED` even if JSON contains a status string.
2. **Missing or malformed JSON output**: Ensure parser fallbacks still trigger `ACTION REQUIRED` rather than false `READY FOR COMPLETION`.
3. **Empty or clean status without errors**: Ensure `READY FOR COMPLETION` only renders when exit code is 0 and status is `COMPLETED`.
4. **Preserved git status and diff stat**: Ensure Git diagnostic outputs are maintained alongside the new decision gate block.
5. **No regression in CLI argument validation**: Ensure invalid file paths or missing arguments still exit cleanly with proper error messages.

---

### Task 1: Create Test Suite for `agy-goal.sh` Decision Gate & CLI

**Files:**
- Create: `agy-goal/tests/test_decision_gate.sh`
- Create: `agy-goal/tests/run_all_tests.sh`

**Interfaces:**
- Consumes: `./agy-goal/scripts/agy-goal.sh`
- Produces: Executable test runner scripts validating CLI arguments and decision gate rendering.

- [ ] **Step 1: Write the failing test script**

Create `agy-goal/tests/test_decision_gate.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$SCRIPT_DIR/scripts/agy-goal.sh"

echo "=== Test 1: CLI Help output ==="
"$BIN" -h | grep -q "Usage:"
"$BIN" --help | grep -q "agy-goal.sh <path/to/plan.md>"
echo "PASS: Help output"

echo "=== Test 2: Missing arguments ==="
OUTPUT="$("$BIN" 2>&1 || true)"
echo "$OUTPUT" | grep -q "Usage:"
echo "PASS: Missing arguments handled"

echo "=== Test 3: Plan file validation ==="
OUTPUT="$("$BIN" nonexistent_plan_file_12345.md 2>&1 || true)"
echo "$OUTPUT" | grep -q "Error: Unknown command or plan file not found"
echo "PASS: Plan file validation handled"

echo "=== Test 4: Decision Gate rendering for completed status ==="
TMP_JSON="$(mktemp -t test-comp.XXXXXX.json)"
cat << 'EOF' > "$TMP_JSON"
{
  "conversation_id": "test-cid-123",
  "status": "COMPLETED",
  "duration_seconds": 12.5,
  "response": "All tasks in plan have been implemented and verified."
}
EOF

# Test python decision gate parser directly
PARSER_OUTPUT="$(python3 -c '
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
exit_code = int(sys.argv[2])
status = data.get("status", "UNKNOWN")
is_completed = (exit_code == 0 and status == "COMPLETED")

print("==================== DECISION GATE ====================")
if is_completed:
    print("Decision: READY FOR COMPLETION")
    print("Action:   Plan executed successfully by AGY.")
    print("Next:     Review git diff, then commit and report completion to user.")
else:
    print("Decision: ACTION REQUIRED (INCOMPLETE / ERROR)")
    print("Action:   DO NOT run manual tests or debug manually.")
    print("Next:     Run: agy-goal.sh continue \"<1-2 sentence issue summary>\"")
print("=======================================================")
' "$TMP_JSON" 0)"

rm -f "$TMP_JSON"

echo "$PARSER_OUTPUT" | grep -q "Decision: READY FOR COMPLETION"
echo "$PARSER_OUTPUT" | grep -q "Action:   Plan executed successfully by AGY."
echo "PASS: Completed status generates READY FOR COMPLETION gate"

echo "=== Test 5: Decision Gate rendering for error status ==="
TMP_JSON_ERR="$(mktemp -t test-err.XXXXXX.json)"
cat << 'EOF' > "$TMP_JSON_ERR"
{
  "conversation_id": "test-cid-456",
  "status": "ERROR",
  "duration_seconds": 5.0,
  "response": "Encountered syntax error in auth.js line 12"
}
EOF

PARSER_OUTPUT_ERR="$(python3 -c '
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
exit_code = int(sys.argv[2])
status = data.get("status", "UNKNOWN")
is_completed = (exit_code == 0 and status == "COMPLETED")

print("==================== DECISION GATE ====================")
if is_completed:
    print("Decision: READY FOR COMPLETION")
    print("Action:   Plan executed successfully by AGY.")
    print("Next:     Review git diff, then commit and report completion to user.")
else:
    print("Decision: ACTION REQUIRED (INCOMPLETE / ERROR)")
    print("Action:   DO NOT run manual tests or debug manually.")
    print("Next:     Run: agy-goal.sh continue \"<1-2 sentence issue summary>\"")
print("=======================================================")
' "$TMP_JSON_ERR" 0)"

rm -f "$TMP_JSON_ERR"

echo "$PARSER_OUTPUT_ERR" | grep -q "Decision: ACTION REQUIRED (INCOMPLETE / ERROR)"
echo "$PARSER_OUTPUT_ERR" | grep -q "Action:   DO NOT run manual tests or debug manually."
echo "PASS: Error status generates ACTION REQUIRED gate"

echo "=== All decision gate tests passed! ==="
```

Create `agy-goal/tests/run_all_tests.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Running agy-goal test suite..."
"$SCRIPT_DIR/test_decision_gate.sh"
echo "All tests completed successfully."
```

- [ ] **Step 2: Make test scripts executable and run to verify**

Run:
```bash
chmod +x agy-goal/tests/test_decision_gate.sh agy-goal/tests/run_all_tests.sh
./agy-goal/tests/run_all_tests.sh
```
Expected: PASS with "All tests completed successfully."

- [ ] **Step 3: Commit test suite**

```bash
git add agy-goal/tests/
git commit -m "test(agy-goal): add test suite for cli and decision gate logic"
```

---

### Task 2: Implement `[DECISION GATE]` in `agy-goal.sh`

**Files:**
- Modify: `agy-goal/scripts/agy-goal.sh:99-121`

**Interfaces:**
- Consumes: AGY exit code `$AGY_EXIT`, `$TMP_OUT` json file.
- Produces: Printed summary block containing `[DECISION GATE]` with unambiguous instruction for host agent.

- [ ] **Step 1: Write an end-to-end integration test in `agy-goal/tests/test_script_gate_integration.sh`**

Create `agy-goal/tests/test_script_gate_integration.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$SCRIPT_DIR/scripts/agy-goal.sh"

# Check if agy-goal.sh contains DECISION GATE string
echo "=== Check DECISION GATE presence in agy-goal.sh ==="
if grep -q "DECISION GATE" "$BIN"; then
  echo "PASS: DECISION GATE is implemented in agy-goal.sh"
else
  echo "FAIL: DECISION GATE is missing from agy-goal.sh"
  exit 1
fi
```
Make executable: `chmod +x agy-goal/tests/test_script_gate_integration.sh`

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
./agy-goal/tests/test_script_gate_integration.sh
```
Expected: FAIL with "FAIL: DECISION GATE is missing from agy-goal.sh"

- [ ] **Step 3: Update `agy-goal/scripts/agy-goal.sh` to include `[DECISION GATE]`**

Replace lines 99-121 in `agy-goal/scripts/agy-goal.sh` with:
```bash
# Parse output and display summary
if [ -s "$TMP_OUT" ]; then
  python3 -c '
import json, sys

exit_code = int(sys.argv[2])
is_completed = False

try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    cid = data.get("conversation_id", "")
    status = data.get("status", "UNKNOWN")
    duration = data.get("duration_seconds", 0)
    print("\n" + "=" * 60)
    print("Status:         ", status)
    if cid:
        print("Conversation ID:", cid)
    print(f"Duration:        {duration:.1f}s")
    print("=" * 60 + "\n")
    print(data.get("response", "").strip())
    
    is_completed = (exit_code == 0 and status == "COMPLETED")
except Exception:
    with open(sys.argv[1]) as f:
        print(f.read())
    is_completed = False

print("\n==================== DECISION GATE ====================")
if is_completed:
    print("Decision: READY FOR COMPLETION")
    print("Action:   Plan executed successfully by AGY.")
    print("Next:     Review git diff, then commit and report completion to user.")
else:
    print("Decision: ACTION REQUIRED (INCOMPLETE / ERROR)")
    print("Action:   DO NOT run manual tests or debug manually.")
    print("Next:     Run: agy-goal.sh continue \"<1-2 sentence issue summary>\"")
print("=======================================================\n")
' "$TMP_OUT" "$AGY_EXIT"
fi
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
./agy-goal/tests/test_script_gate_integration.sh
./agy-goal/tests/run_all_tests.sh
```
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add agy-goal/scripts/agy-goal.sh agy-goal/tests/test_script_gate_integration.sh
git commit -m "feat(agy-goal): add DECISION GATE block to post-execution summary"
```

---

### Task 3: Rewrite `agy-goal/SKILL.md` with Fast Decision Gate & Negative Constraints

**Files:**
- Modify: `agy-goal/SKILL.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-09-24-agy-goal-fast-decision-gate-design.md`
- Produces: Clean, authoritative skill specification with zero manual testing instructions.

- [ ] **Step 1: Check existing `SKILL.md` for prohibited patterns**

Run:
```bash
grep -n "run project tests independently" agy-goal/SKILL.md || true
```
Expected: Matches line 38 in current `SKILL.md`.

- [ ] **Step 2: Rewrite `agy-goal/SKILL.md`**

Replace `agy-goal/SKILL.md` with:
```markdown
---
name: agy-goal
description: Execute an implementation plan or continue/fix tasks using AGY CLI (/goal and continue).
---

# agy-goal

Execute and iterate on implementation plans using **AGY CLI** (`/goal` and `continue`) with a fast, zero-thrashing decision gate.

## Role Definition & Principles

- **Host Agent (Orchestrator)**: Dispatches `agy-goal.sh`, reads the resulting `[DECISION GATE]`, and makes an immediate 1-turn binary decision: declare completion or invoke `continue`.
- **AGY CLI (Worker)**: Autonomous implementation agent. Reads the plan, edits code, runs project tests internally, and fixes failures.

### 🚫 Strict Negative Constraints
- **DO NOT run manual test commands**: Never execute `npm test`, `pytest`, `go test`, `cargo test`, or custom test scripts directly. AGY executes and verifies tests internally.
- **DO NOT manually debug or patch code**: Never open failing source files to debug or write manual fixes. If an issue is reported, summarize it in 1–2 sentences and hand it back to AGY via `continue`.

---

## Commands

Run the runner script from `./agy-goal/scripts/agy-goal.sh` (or your configured skills path).

> [!NOTE]
> 默认单次任务超时时间为 **30 分钟**（可通��环境变量 `AGY_TIMEOUT` 调整，例如 `AGY_TIMEOUT=45m`）。

### 1. Implement Plan
Start executing a written markdown plan:
```bash
agy-goal.sh path/to/plan.md
```

### 2. Continue Plan Execution (`continue`)
Continue the plan to finish remaining tasks or supply targeted feedback:
```bash
# Continue without extra instructions:
agy-goal.sh continue

# Continue with targeted feedback (1-2 sentences):
agy-goal.sh continue "Fix test failure in user_spec: assertion failed at line 42"
```

---

## Fast Decision Gate Workflow

Every time `agy-goal.sh` finishes, inspect the `[DECISION GATE]` block at the end of output:

### Case A: `READY FOR COMPLETION`
- Check `git status` and `git diff` to confirm changes are clean and match the plan.
- Announce completion to the user and suggest commit/push steps.
- **Do NOT run any additional tests.**

### Case B: `ACTION REQUIRED (INCOMPLETE / ERROR)`
- Extract a 1–2 sentence summary of the missing tasks or error from the AGY response.
- Immediately run:
  ```bash
  agy-goal.sh continue "<1-2 sentence issue summary>"
  ```
- **Do NOT attempt to diagnose or fix the error yourself.**

---

## 🛑 Hard Stop & Circuit Breaker

You must **STOP** immediately and escalate to the user if:
1. **Round Limit Exceeded**: You have run `continue` **3 times** and the plan is still not completed.
2. **Identical Error Loop**: The exact same error or test failure persists across **2 consecutive turns**.
3. **Scope Creep / Degradation**: AGY starts modifying unrelated files or introducing new regressions.

**When stopped, report to the user immediately:**
1. Tasks completed successfully so far.
2. The exact blocking error or reason for failure.
3. Proposed options/suggestions, and ask the user how to proceed.
```

- [ ] **Step 3: Verify negative constraints and prohibited terms are absent**

Run:
```bash
grep -n "run project tests independently" agy-goal/SKILL.md || echo "VERIFIED: Prohibited phrase removed"
grep -n "Strict Negative Constraints" agy-goal/SKILL.md
grep -n "DECISION GATE" agy-goal/SKILL.md
```
Expected: Prohibited phrase removed, new sections present.

- [ ] **Step 4: Commit changes**

```bash
git add agy-goal/SKILL.md
git commit -m "docs(agy-goal): rewrite SKILL.md with fast decision gate and negative constraints"
```

---

### Task 4: Full Integration Verification & All-Test Execution

**Files:**
- Modify: `agy-goal/tests/run_all_tests.sh`

**Interfaces:**
- Consumes: All tests in `agy-goal/tests/`.
- Produces: Exit code 0 on complete pass.

- [ ] **Step 1: Add integration test to `run_all_tests.sh`**

Update `agy-goal/tests/run_all_tests.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Running agy-goal test suite..."
"$SCRIPT_DIR/test_decision_gate.sh"
"$SCRIPT_DIR/test_script_gate_integration.sh"
echo "All tests completed successfully."
```

- [ ] **Step 2: Run all tests**

Run:
```bash
./agy-goal/tests/run_all_tests.sh
```
Expected: PASS with "All tests completed successfully."

- [ ] **Step 3: Commit final test runner update**

```bash
git add agy-goal/tests/run_all_tests.sh
git commit -m "test(agy-goal): include integration gate test in full test runner"
```
