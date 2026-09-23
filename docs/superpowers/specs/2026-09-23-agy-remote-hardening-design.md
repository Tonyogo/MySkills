# Design Spec: `agy-remote` Hardening & Model-Friendly Ergonomics

- **Date:** 2026-09-23
- **Author:** Claude & liyatao
- **Status:** Approved
- **Topic:** Hardening `agy-remote` (Hardcoded Target Default, Conventional Remote Workspace, Base64 Payload Safety)

---

## 1. Motivation & Problems Solved

In the initial implementation of `agy-remote`, several friction points and reliability risks were identified:
1. **Target ID Hallucination / Parameter Friction**:
   Requiring or expecting an arbitrary container ID (e.g. `be6147bfc11c`) in command invocations caused LLM models to guess, omit, or misplace arguments between target ID and plan files.
2. **Ambiguous Remote Directory**:
   When remote working directory was unspecified, `gt exec` defaulted to container home/root, failing git commands.
3. **Shell Escaping & Prompt Corruption**:
   Passing raw prompts with complex quotes, backticks, or code snippets across multi-layer nested bash strings (`gt exec ... bash -c "..."`) caused shell quote breakage.
4. **Indiscriminate Auto-Commit**:
   Blind `git add -A` risked pushing unrelated local dirty files to the remote repository.

---

## 2. Hardened Architecture & Ergonomics

### 2.1 100% Symmetrical CLI with `agy-goal`
The CLI no longer requires any `<target_id>` argument, matching `agy-goal` exactly:
```bash
# 1. Execute an implementation plan remotely
agy-remote.sh path/to/plan.md

# 2. Continue remote execution or supply targeted feedback
agy-remote.sh continue [optional instructions...]

# 3. Help
agy-remote.sh -h | --help
```

### 2.2 Conventional Defaults
- **Default Target ID**: `agy-remote-server` (overrideable via `AGY_TARGET` if explicitly set).
- **Default Remote Directory**: `/workspace/${PROJECT_NAME}` where `${PROJECT_NAME}` is dynamically derived from `basename $(git rev-parse --show-toplevel)` (overrideable via `REMOTE_WORK_DIR`).
- **Default Timeout**: `30m` (overrideable via `AGY_TIMEOUT`).

---

## 3. Data Flow & Execution Safety

```
[Local Machine]                                           [Remote Container (agy-remote-server)]
  │                                                                     │
  ├─ 1. Branch verification (block main/master)                         │
  ├─ 2. Targeted stage & commit of plan.md (git push origin <branch>)   │
  ├─ 3. Encode PROMPT to Base64 string                                  │
  │                                                                     │
  ├─ 4. Dispatch gt exec ──────────────────────────────────────────────>│
  │                                                                     ├─ 4.1 Check /workspace/<project> exists
  │                                                                     ├─ 4.2 Pull branch (git pull origin <branch>)
  │                                                                     ├─ 4.3 Decode Base64 PROMPT safely
  │                                                                     ├─ 4.4 Run agy (accept-edits, json output)
  │                                                                     ├─ 4.5 Commit changes & push to origin
  │                                                                     │
  ├─ 5. Receive output & pull remote branch locally <───────────────────┘
  └─ 6. Print JSON summary, git status, git diff, and next steps
```

### 3.1 Base64 Prompt Encoding
- Local script:
  ```bash
  ENCODED_PROMPT="$(printf '%s' "$REMOTE_PROMPT" | base64 | tr -d '\r\n')"
  ```
- Remote script decodes safely before passing to `agy`:
  ```bash
  DECODED_PROMPT="$(printf '%s' "$ENCODED_PROMPT" | base64 -d)"
  agy --mode accept-edits --print-timeout "$TIMEOUT" --output-format json -p "$DECODED_PROMPT"
  ```
  This eliminates all quote escaping issues regardless of user input complexity.

### 3.2 Workspace & Remote Directory Defense
- If the remote directory `/workspace/${PROJECT_NAME}` does not exist, the remote script exits immediately with a clear diagnostic message.
- Local commits prioritize staging the plan file or specific modifications rather than blindly pushing unrelated unstaged local files.

---

## 4. Error Handling & Circuit Breaker

- Retain standard hard-stop limits:
  1. 3 consecutive `continue` turns without completion.
  2. Identical error loop across 2 consecutive turns.
  3. Connection failure with `agy-remote-server`.
- On exit, present clean Git status and actionable guidance.
