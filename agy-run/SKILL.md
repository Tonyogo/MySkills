---
name: agy-run
description: >-
  Autonomous multi-turn implementation plan runner using AGY CLI (/goal and -c).
  Use this skill whenever the user asks to execute an implementation plan, hand off tasks to AGY,
  continue/resume an ongoing AGY session, or conduct autonomous multi-turn plan review and completion.
---

# agy-run: Autonomous Multi-Turn Plan Runner

Orchestrate end-to-end plan implementation with **AGY CLI** (`/goal` and `-c`) under rigorous, autonomous Agent review.

The skill establishes a closed-loop pair-programming paradigm:
- **Planner**: Specifies *What to build* (Structured Implementation Plan).
- **AGY CLI**: Executes *How to implement* (Autonomous code editing and local testing via `/goal`).
- **Reviewer Agent (Claude Code / Generic Agent)**: Conducts *Independent 4-Gate Review* and drives iterative completion via `continue` until 100% verified.

---

## 📍 Locating the Runner Script

Following the skill discovery pattern, resolve `<SCRIPT_PATH>` using **local workspace priority** with **host global fallback**:

1. **Local Workspace (Priority)**:
   - Current repository: `./agy-run/scripts/agy-run.sh`
   - Claude Code: `./.claude/skills/agy-run/scripts/agy-run.sh`
   - Generic Agent: `./.agent/skills/agy-run/scripts/agy-run.sh` *(or `./.agents/skills/agy-run/scripts/agy-run.sh`)*
2. **Host Agent Global (Fallback)**:
   - Claude Code: `~/.claude/skills/agy-run/scripts/agy-run.sh`
   - Generic Agent: `~/.agent/skills/agy-run/scripts/agy-run.sh`

*(In the instructions below, `<SCRIPT_PATH>` refers to the resolved path above).*

---

## 🛠️ Commands Reference

### 1. Implement Plan (`imp`)
Start autonomous implementation of a written Markdown plan:
```bash
<SCRIPT_PATH> imp <path/to/plan.md>
```
*Prompt passed to AGY:* `/goal Implement Plan @<path/to/plan.md>`

### 2. Continue Plan Execution (`continue`)
Continue the plan to finish remaining tasks or supply targeted feedback:
```bash
# Continue without extra instructions (let AGY self-audit and proceed with remaining tasks):
<SCRIPT_PATH> continue

# Continue with specific defect feedback or instructions:
<SCRIPT_PATH> continue "Task 3 tests failed with AssertionError at line 45; fix and verify."
```
*Resumes the most recent AGY conversation directly via `-c`.*

---

## 🔬 Autonomous Review Loop SOP (For Reviewer Agent)

When tasked with executing a plan via `agy-run`, the Reviewer Agent **must** autonomously drive the full review-and-continue loop following these 4 phases:

```mermaid
flowchart TD
    Start([Receive Plan]) --> CheckPlan{Plan exists on disk?}
    CheckPlan -- No --> HaltPlan[Guide user to write plan first]
    CheckPlan -- Yes --> Imp[Phase 1: Run imp plan.md]
    
    Imp --> Gate[Phase 2: 4-Layer Verification Gate]
    
    Gate --> CheckPass{All 4 Gates Pass?}
    CheckPass -- Yes --> Report[Phase 4: Deliver Structured Final Report]
    
    CheckPass -- No --> CheckRetry{Round <= Max Retries (3~5)?}
    CheckRetry -- Exceeded --> Blocker[Phase 4: Trigger Circuit Breaker & Alert Blocker]
    
    CheckRetry -- Within Limit --> RouteFeedback{Failure Type?}
    RouteFeedback -- Incomplete Only --> ContNoArg[Phase 3: Run continue without args]
    RouteFeedback -- Bug / Test Failure --> ContArg["Phase 3: Run continue <specific error feedback>"]
    
    ContNoArg --> Gate
    ContArg --> Gate
```

### Phase 0: Pre-Flight Plan Check
1. Verify that the target implementation plan file exists on disk.
2. If the plan file is missing, **do not** call `agy-run.sh`. Instead, prompt the user or activate a planning workflow (e.g., `superpowers:writing-plans`) to generate a concrete plan first.

### Phase 1: Launch Initial Implementation
Execute the plan via `run_command`:
```bash
<SCRIPT_PATH> imp <path/to/plan.md>
```
Record the initial execution output, duration, and status.

### Phase 2: 4-Layer Verification Gate (Review)
Upon each turn completion, the Reviewer Agent must independently inspect the workspace against **4 mandatory verification gates**:

1. **Gate 1: AGY Execution Health**
   - Check the parsed JSON summary: `Status` must be `SUCCESS` (not `TIMEOUT` or `ERROR`).
   - Confirm no fatal runtime crashes or unhandled script failures occurred.
2. **Gate 2: Plan Task Checklist Compliance**
   - Read `<path/to/plan.md>` and inspect the task checkboxes (`- [x]`).
   - Confirm whether all planned tasks have actually been addressed in the code.
3. **Gate 3: Automated Test & Build Suites**
   - Execute the project's build and test commands (e.g. `npm test`, `pytest`, `cargo test`, `go test`).
   - Ensure 100% of relevant tests pass with zero regressions or compiler errors.
4. **Gate 4: Git Diff & Code Quality Inspection**
   - Inspect `git status` and `git diff`.
   - Verify that all changes adhere to project standards, contain no stray debug statements, and preserve unrelated code/comments.

### Phase 3: Autonomous Feedback & Continue Routing
- **If ALL 4 Gates Pass**: Exit loop and proceed to **Phase 4**.
- **If ANY Gate Fails**:
  1. **Circuit Breaker Check**:
     - Track the current iteration count (Maximum: **3 to 5 rounds**).
     - If the maximum retry count is reached, or if the exact same test error recurs 3 times without progress, **trip the circuit breaker**: stop the loop immediately to prevent runaway token spend and proceed to Phase 4 with a blocker alert.
  2. **Intelligent Continue Dispatching**:
     - **Case A (Incomplete Tasks Only)**: If tests pass but remaining tasks were cut short due to context or timeout, run:
       ```bash
       <SCRIPT_PATH> continue
       ```
     - **Case B (Test Failures, Bugs, or Missed Specs)**: If specific tests failed or defects were identified in Gate 3/4, extract the exact failure snippet (file, line number, error message) and run:
       ```bash
       <SCRIPT_PATH> continue "Gate 3 test failure in <test_name>: <concise error snippet>. Please fix the root cause and ensure all tests pass."
       ```
  3. Return to **Phase 2** after `continue` finishes.

### Phase 4: Final Handover Report
When the loop finishes, format the output to the user as follows:

```markdown
## 🎯 Plan Execution & Verification Report: [Plan Name]

### 1. Execution Summary
- **Total Iterations**: `[X]` turn(s)
- **Final Status**: `[SUCCESS / BLOCKED]`
- **Conversation ID**: `[AGY Session ID]`

### 2. Plan Checklist Compliance
- [x] Task 1: [Description]
- [x] Task 2: [Description]
- ...

### 3. Verification & Test Results
- **Build / Lint**: `[PASS / FAIL]`
- **Test Suite**: `[PASS / FAIL]` (`[X passed, 0 failed]`)
- **Key Validation Output**: `[Brief test summary]`

### 4. Git Changes & Next Steps
- **Branch**: `[current_branch]`
- **Modified Files**: `[X files changed, Y insertions(+), Z deletions(-)]`
- **Suggested Action**: `git add -A && git commit -m "feat: ..."` / `git push`

*(If Circuit Breaker Tripped)*:
> [!WARNING]
> **Execution Halted by Circuit Breaker**:
> - **Repeated Failure / Blocker**: `[Details of recurring error]`
> - **Recommended Manual Intervention**: `[Suggested fix]`
```
