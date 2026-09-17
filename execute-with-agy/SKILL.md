---
name: execute-with-agy
description: Hand off an existing implementation plan to AGY CLI for autonomous execution and testing, then independently review and fix via Claude Code.
---

# execute-with-agy

Orchestrate autonomous code implementation and testing with **AGY CLI**, followed by independent verification and iterative review loops in **Claude Code**.

## Core Architecture & Agent Roles

```text
Planning Agent (Superpowers)       AGY (Implementation)       Claude Code (Reviewer)
      [ What to build ]            [ How to implement ]        [ Verify & Quality ]
             │                              │                           │
      Generate Plan ───────────────────────►│                           │
                                      IMPLEMENT + TEST ────────────────►│
                                                                   REVIEW DIFF
                                            │                      ┌────┴────┐
                                            │                    PASS     NEEDS FIX
                                            │                      │         │
                                            │◄── Concrete Feedback ┴─────────┘
                                      FIX + RE-TEST
```

| Agent | Responsibility | Core Question |
| :--- | :--- | :--- |
| **Superpowers / Planner** | Requirements analysis, architecture, implementation plan | *What to build?* |
| **AGY CLI** | Full plan execution, file editing, dependencies, tests, commits | *How to implement?* |
| **Claude Code** | Independent review, acceptance verification, fix orchestration | *Does it meet standards?* |

---

## When to Use

- **Use when** a written implementation plan exists (e.g. in `docs/superpowers/plans/`, `docs/plans/`, or `plans/`) and is ready for execution.
- **Do NOT use** for initial planning or requirements brainstorming (use `superpowers:brainstorming` or `superpowers:writing-plans`).
- **Do NOT use** if no implementation plan exists yet.

---

## Invocation

Run the runner script (adjust to `~/.claude/skills/...` if installed globally):

```bash
# Auto-discover the latest plan:
.claude/skills/execute-with-agy/scripts/agy-run.sh

# Or specify a plan explicitly:
.claude/skills/execute-with-agy/scripts/agy-run.sh path/to/plan.md
```

---

## AGY Implementation Principles

AGY operates as an autonomous implementation engineer, not a rigid command executor. It has full engineering agency to:
- Create, modify, or delete files as required by the plan.
- Install packages and dependencies.
- Run tests, linters, formatters, and debug failures.
- Inspect Git status, inspect diffs, and create commits per project workflow.

**Boundary & Fidelity:**
- Implement the plan; do **not** redesign or draft a new plan.
- If practical repository realities require adjustments, apply the smallest reasonable change and explicitly record deviations in the summary.
- **Core Safety Rule:** Preserve unrelated user modifications that existed prior to the AGY session.

---

## Claude Code Independent Review

**Never treat AGY's summary as proof of completion.** Claude Code must independently inspect the working tree:

```text
Implementation Plan ──► Actual Code ──► Git Diff ──► Test Results ──► Acceptance Criteria
```

### Review Checklist
1. **Completeness:** Are all tasks from the plan fully implemented without omissions?
2. **Fidelity:** Does the implementation follow the plan's architectural intent?
3. **Scope Control:** Are all modifications directly related to the plan (no accidental file bloat)?
4. **Test Verification:** Did tests actually execute, and do they pass cleanly?
5. **Acceptance Criteria:** Are all functional and edge-case requirements satisfied?

---

## Review Outcomes

After inspection, classify the outcome into exactly one of three states:

### 1. `PASS`
- All tasks implemented, tests pass, code meets quality standards.
- **Action:** Present completed results and proactively guide next steps (Superpowers style):
  1. **Summarize Verification:** Report that all plan requirements and tests have passed.
  2. **Prompt Next Steps:** Actively ask the user how they would like to proceed with the Git workflow:
     - **Option 1 (Push to Remote / PR):** Commit remaining changes (if any) and push to remote (`git push -u origin <branch>`).
     - **Option 2 (Local Merge):** Merge the feature branch into the base branch locally (`git checkout main && git merge <branch>`).
     - **Option 3 (Keep Local):** Leave changes as-is in the working tree for manual inspection.
  3. Execute the selected Git operation upon user confirmation.

### 2. `NEEDS FIX`
- Specific bugs, missing plan steps, test failures, or regressions found.
- **Action:** Send actionable, structured feedback back to the existing AGY session:
  ```bash
  .claude/skills/execute-with-agy/scripts/agy-run.sh --fix "Fix the issues identified during review:
  1. <Specific file/line issue or missing requirement>
  2. <Failing test output or behavioral bug>

  Run relevant tests after making fixes. Do not change unrelated functionality."
  ```
  *Always resume the existing AGY session to retain implementation context.*

### 3. `FAILED`
- Fundamental blockers, unrecoverable environment errors, or unresolvable architectural mismatch requiring human decision.
- **Action:** Stop the loop, explain the blocker, and escalate to the user.

---

## Complete Orchestration Loop

```text
[ Plan (.md) ] ──► [ AGY: IMPLEMENT + TEST ] ──► [ Claude Code: REVIEW ]
                              ▲                                │
                              │                           NEEDS FIX
                              └────── [ AGY: FIX ] ◄───────────┘
                                           │
                                         (PASS) ──► DONE
```
