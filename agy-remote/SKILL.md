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
