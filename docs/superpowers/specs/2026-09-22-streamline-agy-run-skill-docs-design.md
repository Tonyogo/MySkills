# Design: Streamline agy-run Skill Documentation and Description

**Date:** 2026-09-22  
**Status:** Approved  
**Topic:** Streamlining `agy-run/SKILL.md` description and body to a lightweight, zero-boilerplate reference.

---

## 1. Background & Goals

The `agy-run` skill document currently spans 160 lines, including extensive Mermaid flowcharts, exhaustive 4-gate verification SOPs, path priority hierarchies, and large output templates. This consumes unnecessary context window tokens and dilutes the core usage of the skill.

The goal is to streamline both the frontmatter description and the body of `agy-run/SKILL.md` into a concise, direct guide (~35-40 lines) focused on the core commands (`imp` and `continue`) and their iterative workflow.

---

## 2. Updated Frontmatter & Content Specification

### 2.1 Frontmatter Description
Replace the multi-line description with a concise, single-line trigger:
```yaml
---
name: agy-run
description: Execute an implementation plan or continue/fix tasks using AGY CLI (/goal and continue).
---
```

### 2.2 Document Structure
The document consists of three streamlined sections:
1. **Header & Overview**: 1-2 sentence definition of executing and iterating on plans via AGY CLI.
2. **Commands Reference**:
   - `imp <path/to/plan.md>`: Start plan execution via `/goal Implement Plan @<plan.md>`.
   - `continue [instructions...]`: Continue execution without args, or provide specific feedback/fixes.
3. **Workflow**: A concise 4-step loop:
   - Start (`imp`) -> Verify (diff & tests) -> Continue (if incomplete or bugs) -> Complete (commit/push).

All Mermaid diagrams, complex reporting templates, and redundant path listings are removed.

---

## 3. Verification & Acceptance Criteria

1. `agy-run/SKILL.md` line count is reduced under 45 lines.
2. Skill description is concise and clearly indicates when to trigger.
3. Commands and usage parameters accurately reflect `agy-run.sh` CLI capabilities (`imp` and `continue`).
