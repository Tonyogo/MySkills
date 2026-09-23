# Design: Add Circuit Breaker & Human Escalation Rules to agy-run Skill

**Date:** 2026-09-22  
**Status:** Approved  
**Topic:** Preventing runaway loops and unauthorized AI tinkering in `agy-run` by enforcing explicit circuit breaker rules and escalating blockers to the user.

---

## 1. Problem & Context

When AGY CLI encounters stubborn bugs, test failures, or architectural ambiguities across multiple turns, an unconstrained AI agent may continue invoking `continue` blindly. This can result in:
- Wasted tokens and degraded context.
- Unnecessary / unrelated code edits (hallucinatory "fixes" breaking previously working code).
- Masking of fundamental environmental or requirement blockers that actually require human decision.

---

## 2. Solution: Behavioral Circuit Breaker Rules in `SKILL.md`

We keep `agy-run.sh` lightweight without hardcoded counters, and add an explicit, non-negotiable **Hard Stop & Escalation Rules** section to `agy-run/SKILL.md`.

### 2.1 Three Hard Stop Conditions
The agent must immediately cease running `agy-run.sh continue` if any of the following occur:
1. **Turn Limit**: `continue` has been executed **3 times** without reaching full plan completion.
2. **Identical Error Loop**: The exact same error or test failure recurs across **2 consecutive turns**.
3. **Scope Creep / Degradation**: Unrelated files are edited or new test regressions are introduced.

### 2.2 Escalation Protocol
When a hard stop condition is triggered, the AI must not guess or attempt further modifications. It must immediately halt and present a clean report to the user:
- **Completed Work**: What was successfully accomplished.
- **Root Blocker**: The specific error or failure causing the impasse.
- **Recommended Options**: Clear choices or paths forward, requesting the user's decision.

---

## 3. Verification & Acceptance Criteria

1. `agy-run/SKILL.md` is updated with the new `🛑 Hard Stop & Escalation Rules` section.
2. Total document length remains concise (around 50-55 lines).
3. The rules provide crystal-clear guidance on when to stop and what to report to the user.
