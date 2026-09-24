# 🚀 MySkills - AI 智能体扩展技能库

**MySkills** 是一个面向 **Claude Code** 以及各类支持 `.agent` 通用技能规范的现代化 AI 编程助手的 Agent Skills 中枢。

通过遵循统一的技能规范（`SKILL.md` 与渐进式披露机制），本项目封装了跨智能体协同开发、全栈微服务链路追踪、故障自动化诊断等高阶工程能力，让智能体从基础的代码生成工具跃升为具备自主工程实施与系统排障能力的专业结对工程师。

---

## 🧭 技能矩阵一览

| 技能名称 | 核心职责 | 适用场景 | 关键依赖 / 工具 | 文档入口 |
| :--- | :--- | :--- | :--- | :--- |
| **`agy-goal`** | **跨 Agent 协同实现**<br>Claude Code / 通用 Agent 规划审查 ➔ AGY CLI 自主执行与测试 | 需求/架构计划已由 Superpowers 生成，转交 AGY 自动编写代码、跑测试并多轮迭代完成 | `agy` CLI, Bash, Git | [README / SKILL.md](./agy-goal/SKILL.md) |
| **`agy-remote`** | **远程容器/主机协同实现**<br>本地规划审查 ➔ `gt exec` 远程容器/主机执行与测试 | 计划已生成，但需在远程容器/机器上执行重型构建与测试，并自动完成 Git 双向同步 | `gt` CLI, `agy` CLI, Bash, Git | [README / SKILL.md](./agy-remote/SKILL.md) |
| **`man-system`** | **全栈链路追踪与排障**<br>微前端/网关/核心微服务/MQ 跨层定位 | 业务异常排查（如点击无响应、路由丢失、事务回滚、MQ 掉消息）、服务地图生成 | Python 3, 正则扫描器 | [README / SKILL.md](./man-system/SKILL.md) |

---

## 📦 技能详解

### 1. `agy-goal`：Claude Code / 通用 Agent 与 AGY 协作实现技能

该技能将复杂开发任务划分为**规划**、**实施**与**审查**三个明确边界，由外部审查 Agent（Claude Code / 通用 Agent）负责架构规划与验收，AGY CLI 负责自主编写代码并驱动测试闭环：

```text
Planning Agent (Superpowers)       AGY (Implementation)       Reviewer Agent (Claude/通用Agent)
      [ What to build ]            [ How to implement ]            [ Verify & Quality ]
             │                              │                               │
      Generate Plan ───────────────────────►│                               │
                                      IMPLEMENT + TEST ────────────────────►│
                                                                       REVIEW DIFF
                                            │                          ┌────┴────┐
                                            │                        PASS     NEEDS FIX
                                            │                          │         │
                                            │◄── Feedback / Continue ──┴─────────┘
                                    CONTINUE + RE-TEST
```

#### 🌟 核心特性
- **三方职责对齐**：
  - **Superpowers / Planner**：决定 *What to build*（需求分解、架构设计、输出 Implementation Plan）。
  - **AGY CLI**：决定 *How to implement*（读写文件、依赖安装、运行测试、自查自纠、符合规范的 Commit）。
  - **Reviewer Agent (Claude Code / 通用 Agent)**：负责 *Independent Review*（执行 4 层门禁验收：执行健康度、Plan 任务勾选、自动化测试运行与 Git Diff 代码审查，自主驱动 continue 闭环）。
- **轻量极简双命令**：
  - **`<plan.md>`**：直接传参执行，利用 AGY 原生 `/goal` 深度实现指定计划文件（固定 20 分钟超时）。
  - **`continue [instructions...]`**：利用 AGY 原生 `-c` 自动续接最近一次会话，支持多轮反馈闭环与自查补全，实现全自主迭代完成。
- **即插即用 Runner 引擎**：
  - 核心脚本 [`scripts/agy-goal.sh`](./agy-goal/scripts/agy-goal.sh) 提供严格的参数校验、执行耗时汇总、20m 超时保护以及自动化的 Git Status、Diff 统计与后续操作引导。

---

### 2. `man-system`：全栈微服务调用链追踪与故障诊断技能

面向大型分布式系统的全栈故障定位专家技能，解决“前端点不动、后端不知道走哪个微服务、异步消息丢失无从查起”等复杂调用链路排障痛点。

```text
UI 点击 ──► 微前端路由 ──► API 网关 ──► 核心微服务 ──► 异步 MQ ──► 消费工作节点
 (Vue/React)     (BFF/Auth)    (Spring/Go)      (Kafka/Rabbit)    (IoT/Worker)
```

#### 🌟 核心特性
- **双模调度器（Intent Dispatcher）**：
  - **索引建图模式（Init / Indexing）**：提供零依赖 Python 扫描器 [`scan_services.py`](./man-system/scripts/scan_services.py)，秒级解析多语言全栈工程目录，生成标准的 5 层服务拓扑地图（`service-map.md`）。
  - **跨层诊断模式（Cross-Layer Analysis）**：针对用户描述的业务异常，执行标准化的 **5 阶段全栈 SOP**（服务定位 ➔ 调用链展开 ➔ 源码模式比对 ➔ 故障核对表自查 ➔ 结构化诊断报告）。
- **常见通信范式手册（Call Patterns）**：
  - 内置微前端 API 路由、HTTP/REST/RPC、gRPC/Protobuf、MQ/PubSub 专属排查清单与失败核对表。

---

### 3. `agy-remote`：远程容器/主机 Plan 执行与 Git 自动化同步技能

当开发环境位于云端容器、独立虚拟机或构建宿主机时，`agy-remote` 默认通过 `gt exec agy-remote-server` 串联远程 `agy` 执行与本地/远端 Git 分支自动双向同步：

```text
[Local Machine]                                       [Remote Container (agy-remote-server)]
  │                                                                 │
  ├─ 1. Check branch (block main/master)                            │
  ├─ 2. Targeted stage & push plan to origin                        │
  │     (git push -u origin <branch>)                               │
  │                                                                 │
  ├─ 3. Invoke gt exec (Base64 prompt payload) ────────────────────>│
  │                                                                 ├─ 3.1 Verify /workspace/<project> exists
  │                                                                 ├─ 3.2 Pull branch (git pull origin <branch>)
  │                                                                 ├─ 3.3 Safely decode Base64 prompt & run agy
  │                                                                 ├─ 3.4 Commit remote modifications
  │                                                                 └─ 3.5 Push back to origin (<branch>)
  │                                                                 │
  ├─ 4. Receive gt exec exit code & JSON response <─────────────────┘
  ├─ 5. Sync remote changes locally (git pull origin <branch>)
  ├─ 6. Output status, conversation ID, duration, and git diff stat
  └─ 7. Print suggested next steps
```

#### 🌟 核心特性
- **极简零参目标与约定式目录**：
  - 命令行完全对齐 `agy-goal`：`agy-remote.sh <plan.md>` 与 `agy-remote.sh continue [instructions...]`，默认目标为 `agy-remote-server`（支持 `AGY_TARGET` 覆盖）。
  - 约定式远端工作目录：基于当前本地 Git 仓库名自动解析为 `/workspace/<project>`（支持 `REMOTE_WORK_DIR` 覆盖），并在容器内执行前严格校验目录存在性。
- **Base64 Prompt 传输防损**：
  - 本地自动将 Prompt 编码为 Base64 传递，远端容器内安全解码执行，彻底杜绝单双引号、反引号及嵌套转义导致的脚本语法报错。
- **双向 Git 分支自动同步与精准暂存**：
  - 本地预检（拦截误在 `main`/`master` 执行），仅精准暂存与提交当前 Plan 文件，避免污染无关的本地脏工作区。
  - 远程容器自动拉取分支、执行 `agy`、自动 commit 远程变更并 push 回 remote。
  - 本地自动 pull 同步远端最新产出，输出清晰的 Git Status 与 Diff 统计。
- **极速反馈闭环**：
  - 提供 `continue [instructions...]` 子命令，支持无缝传递审查反馈进行多轮自查与修补。
  - 内置熔断保护规则（硬限 3 轮 continue、相同错误连发 2 次即停），防止死循环。

---

## 🔌 多平台接入指南

你可以将本仓库中的技能接入到本地常用的 AI 智能体开发环境中：

### 方式一：接入 Claude Code
适合使用 Claude Code 作为主控 Agent，调用 `agy-goal` 驱动 AGY CLI 编写代码，或调用 `man-system` 进行全栈排障：

#### 1. 全局生效（推荐）
将目标技能软链接到 Claude Code 的全局技能配置目录（`~/.claude/skills/`）：

```bash
mkdir -p ~/.claude/skills

# 挂载技能
ln -sfn /path/to/MySkills/agy-goal ~/.claude/skills/agy-goal
ln -sfn /path/to/MySkills/man-system ~/.claude/skills/man-system
```

#### 2. 当前工程独享
在你的项目根目录下创建 `.claude/skills/` 并软链接：

```bash
mkdir -p .claude/skills
ln -sfn /path/to/MySkills/agy-goal .claude/skills/agy-goal
ln -sfn /path/to/MySkills/man-system .claude/skills/man-system
```

---

### 方式二：接入通用 Agent 环境（`.agent/` 通用目录）
适用于遵循通用 Agent 技能规范的开发环境（如 Antigravity、Codex、Cursor 等）：

> [!NOTE]
> - `man-system`（全栈排障）完全支持各环境原生直接运行。
> - `agy-goal` 专用于外部 Agent（如 Claude Code / 通用 Agent）调度驱动 AGY CLI（在 AGY / Antigravity 原生内部无需挂载 `agy-goal`）。

#### 1. 工作区专属配置（推荐）
在工程代码库根目录下创建 `.agent/skills/`（兼容 `.agents/skills/`）并软链接：

```bash
mkdir -p .agent/skills

# 挂载技能
ln -sfn /path/to/MySkills/agy-goal .agent/skills/agy-goal
ln -sfn /path/to/MySkills/man-system .agent/skills/man-system
```

#### 2. 全局生效
软链接到宿主 Agent 的全局技能配置目录（`~/.agent/skills/`）：

```bash
mkdir -p ~/.agent/skills

# 挂载技能
ln -sfn /path/to/MySkills/agy-goal ~/.agent/skills/agy-goal
ln -sfn /path/to/MySkills/man-system ~/.agent/skills/man-system
```

---

## 🛠️ 新增技能规范

若需为本仓库扩展新的 AI 智能体技能，请遵循以下工程准则：

### 1. 目录结构

```text
MySkills/
├── <skill-name>/
│   ├── SKILL.md              # [必需] 核心技能说明文档（含 YAML Frontmatter）
│   ├── scripts/              # [可选] 可执行脚本与辅助自动化工具
│   └── references/           # [可选] 规则手册、通信规范、架构模板
└── README.md                 # 仓库主介绍文档
```

### 2. `SKILL.md` 编写规范
- **YAML Frontmatter**：必须声明 `name` 与精准的 `description`。`description` 应清晰列明触发词与典型意图，帮助模型实现精准的意图识别与渐进式调度。
- **正向目标驱动**：避免堆砌大量的 `Do NOT` 负向微观限制，赋能智能体正常的工程自主权。
- **精炼可读**：核心调用逻辑与 SOP 保持在 100～150 行以内，技术实现细节下沉至 `scripts/` 中。

---

## 📄 License

[MIT License](LICENSE) © 2026 MySkills Contributors
