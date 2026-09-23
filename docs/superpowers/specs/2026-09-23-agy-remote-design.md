# Design Spec: `agy-remote` Skill for Remote Plan Execution

- **Date:** 2026-09-23
- **Author:** Claude & liyatao
- **Status:** Approved
- **Topic:** Remote AGY Implementation Runner (`gt exec` + Git Branch Synchronization)

---

## 1. Overview & Motivation

`agy-goal` provides a streamlined workflow to run implementation plans locally using the AGY CLI (`/goal` and `continue`). However, developers often work in cloud-hosted environments, remote containers, or developer machines where local resources cannot or should not execute the heavy builds, tests, or agent workflows directly.

`agy-remote` is an independent, dedicated skill that wraps remote plan execution over a container-like remote CLI interface (`gt exec <target_id> ...`) with automated Git branch synchronization, preserving local workflow convenience while executing everything in a remote workspace.

---

## 2. Architecture & Design Decisions

### 2.1 Independent Skill (`agy-remote`) vs. Extending `agy-goal`
- **Decision:** Introduce a dedicated `agy-remote` skill instead of bloating `agy-goal`.
- **Rationale:**
  - `agy-goal` remains lightweight, zero-network, and focused exclusively on local execution.
  - `agy-remote` handles cross-environment orchestration (local branch push -> remote container `gt exec` -> remote push -> local pull), isolating network/container failure modes from local workflows.

### 2.2 Directory Structure
```text
./agy-remote/
├── SKILL.md
└── scripts/
    └── agy-remote.sh
```

---

## 3. CLI Ergonomics & Interface

### 3.1 Commands
```bash
# 1. Execute an implementation plan remotely
agy-remote.sh <target_id> <path/to/plan.md>

# 2. Continue remote execution or supply targeted feedback
agy-remote.sh <target_id> continue [optional instructions...]

# 3. Help
agy-remote.sh -h | --help
```

### 3.2 Environment Variables
- `AGY_TARGET`: Optional default target ID. If specified, `<target_id>` can be omitted from CLI arguments:
  ```bash
  export AGY_TARGET=be6147bfc11c
  agy-remote.sh path/to/plan.md
  agy-remote.sh continue "Fix test assertion failure"
  ```
  CLI argument explicitly takes precedence over `AGY_TARGET`.
- `AGY_TIMEOUT`: Execution timeout per run (default: `30m`, configurable, e.g., `45m`).
- `REMOTE_WORK_DIR`: Working directory in the remote container (optional, defaults to remote git repo root or current directory).

---

## 4. Execution Lifecycle & Data Flow

```
[Local Machine]                                       [Remote Container (target_id)]
  │                                                                 │
  ├─ 1. Check branch (block main/master)                            │
  ├─ 2. Auto-commit & push plan/changes to origin                   │
  │     (git push -u origin <branch>)                               │
  │                                                                 │
  ├─ 3. Invoke gt exec ────────────────────────────────────────────>│
  │                                                                 ├─ 3.1 Pull branch (git pull origin <branch>)
  │                                                                 ├─ 3.2 Run agy (/goal @plan.md OR continue)
  │                                                                 ├─ 3.3 Commit remote modifications
  │                                                                 └─ 3.4 Push back to origin (<branch>)
  │                                                                 │
  ├─ 4. Receive gt exec exit code & JSON response <─────────────────┘
  ├─ 5. Sync remote changes locally (git pull origin <branch>)
  ├─ 6. Output status, conversation ID, duration, and git diff stat
  └─ 7. Print suggested next steps
```

### 4.1 Step Details
1. **Local Pre-flight Check**:
   - Detect current branch: `git rev-parse --abbrev-ref HEAD`.
   - Prevent executing directly on `main` or `master` to avoid corrupting shared branches.
   - Stage and commit local plan files if uncommitted, then `git push -u origin <branch>`.
2. **Remote Execution (`gt exec`)**:
   - Packaged into a single remote shell payload:
     - Pull and sync branch: `git fetch origin <branch> && git checkout <branch> && git pull origin <branch>`
     - Execute `agy --mode accept-edits --print-timeout <timeout> --output-format json [-c] -p <prompt>`
     - Commit modified files: `git add -A && git commit -m "feat(agy-remote): update code via agy" && git push origin <branch>`
3. **Local Post-flight Sync & Summary**:
   - Pull remote commits: `git pull origin <branch>`.
   - Parse and display execution summary (conversation ID, duration, status, response).
   - Display `git status --short` and `git diff --stat`.
   - Display next-step suggestions (continue, run local test, or commit/merge).

---

## 5. Error Handling & Circuit Breaker

### 5.1 Pre-flight Validations
- Check existence of `gt` CLI on local machine.
- Verify remote target accessibility via lightweight probe (`gt exec <target_id> echo ok`).
- Ensure local plan file exists before pushing.

### 5.2 Circuit Breaker Rules
Stop and ask for user intervention when:
- **Round Limit Exceeded**: 3 consecutive `continue` turns without plan completion.
- **Identical Error Loop**: Same test failure or compile error across 2 consecutive turns.
- **Network / Container Failure**: `gt exec` connectivity drops or remote repository encounters non-resolvable merge conflict.

When stopped:
1. Print current branch and git commit state.
2. Report the blocking error and failure phase (pre-sync, execution, post-sync).
3. Offer actionable options (manual resolution, retry, or abort).
