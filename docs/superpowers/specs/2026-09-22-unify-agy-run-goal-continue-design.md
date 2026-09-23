# Design: Unify agy-run Concepts to Native `goal` and `continue`

**Date:** 2026-09-22  
**Status:** Approved  
**Topic:** Aligning CLI subcommands and documentation terminology strictly to `goal` and `continue`, eliminating conflicting terms like `imp`, `/goal`, and `-c`.

---

## 1. Problem & Context

The existing `agy-run` documentation and script exposed conflicting and fragmented terms:
- Plan implementation was called `imp` on the outside, but referred to as `/goal` in descriptions.
- Continuation was called `continue` as a subcommand, but described interchangeably as `-c` and `continue`.

This introduced unnecessary mental overhead and abstraction leaks.

---

## 2. Solution: Strict 1:1 Concept Alignment

Unify all interfaces, documentation, and error messages strictly around two native concepts:
1. **`goal`**: For starting plan execution (replaces `imp`).
2. **`continue`**: For multi-turn continuation and feedback (unifying `-c` and `continue`).

### 2.1 CLI Interface Changes (`agy-run/scripts/agy-run.sh`)
- Replace the `imp` action with `goal`.
- Retain `continue` for session continuation.
- Update help menu, error outputs, and logging to strictly reference `goal` and `continue`.

### 2.2 Documentation Changes (`agy-run/SKILL.md`)
- Update description, command references, and workflow steps to consistently use `goal` and `continue`.
- Remove all references to `imp` and raw `-c` syntax from user-facing text.

---

## 3. Verification Plan

1. Verify `agy-run.sh` CLI:
   - `agy-run.sh -h` displays `goal` and `continue`.
   - `agy-run.sh goal` without args exits with error referencing `goal`.
   - `agy-run.sh imp` is rejected as an unknown command.
   - `agy-run.sh continue` works as expected.
2. Verify `agy-run/SKILL.md`:
   - Text is 100% consistent with `goal` and `continue`.
   - No occurrences of `imp` or raw `-c` in user documentation.
