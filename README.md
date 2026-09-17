# 🚀 MySkills - AI 智能体扩展技能库

**MySkills** 是一个面向现代化 AI 编程助手（如 **Claude Code**、**Google Antigravity / AGY** 等）的通用技能（Agent Skills）中枢。

通过遵循统一的技能规范（`SKILL.md` 与渐进式披露机制），本项目封装了跨智能体协同开发、全栈微服务链路追踪、故障自动化诊断等高阶工程能力，让智能体从基础的代码生成工具跃升为具备自主工程实施与系统排障能力的专业结对工程师。

---

## 🧭 技能矩阵一览

| 技能名称 | 核心职责 | 适用场景 | 关键依赖 / 工具 | 文档入口 |
| :--- | :--- | :--- | :--- | :--- |
| **`execute-with-agy`** | **跨 Agent 协同实现**<br>Claude Code 规划/审查 ➔ AGY CLI 自主执行与测试 | 需求/架构计划已由 Superpowers 生成，需转交 AGY 自动写代码、跑测试、修复问题 | `agy` CLI, Bash, Git | [README / SKILL.md](./execute-with-agy/SKILL.md) |
| **`man-system`** | **全栈链路追踪与排障**<br>微前端/网关/核心微服务/MQ 跨层定位 | 业务异常排查（如点击无响应、路由丢失、事务回滚、MQ 掉消息）、服务地图生成 | Python 3, 正则扫描器 | [README / SKILL.md](./man-system/SKILL.md) |

---

## 📦 技能详解

### 1. `execute-with-agy`：Claude Code 与 AGY 协作实现技能

该技能将复杂开发任务划分为**规划**、**实施**与**审查**三个明确边界，由 Claude Code 负责架构规划与验收，AGY CLI 负责自主编写代码并驱动测试闭环：

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

#### 🌟 核心特性
- **三方职责对齐**：
  - **Superpowers / Planner**：决定 *What to build*（需求分解、架构设计、输出 Implementation Plan）。
  - **AGY CLI**：决定 *How to implement*（读写文件、依赖安装、运行测试、自查自纠、符合规范的 Commit）。
  - **Claude Code**：负责 *Independent Review*（对照计划、Git Diff、测试覆盖率进行客观验收）。
- **三态验收标准**：
  - `PASS`：实现完整，测试通过，结束任务。
  - `NEEDS FIX`：提供精确到行和报错的反馈，调用 `--fix` 恢复 AGY 会话进行增量修复。
  - `FAILED`：遇到环境致命阻断或根本性架构分歧，主动升级至用户决策。
- **轻量 Runner 引擎**：
  - 核心脚本 [`scripts/agy-run.sh`](./execute-with-agy/scripts/agy-run.sh) 支持计划文件自动发现（`docs/superpowers/plans/`、`docs/plans/`、`plans/`）、`-y` 非交互自动授权以及轻量级会话 ID 持久化。

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

## 🔌 多平台接入指南

你可以将本仓库中的技能接入到本地常用的 AI 智能体开发环境中：

### 方式一：接入 Claude Code

#### 1. 全局生效（推荐）
将目标技能软链接到 Claude Code 的全局技能配置目录（`~/.claude/skills/`）：

```bash
mkdir -p ~/.claude/skills

# 挂载 execute-with-agy
ln -sfn /path/to/MySkills/execute-with-agy ~/.claude/skills/execute-with-agy

# 挂载 man-system
ln -sfn /path/to/MySkills/man-system ~/.claude/skills/man-system
```

#### 2. 当前工程独享
在你的项目根目录下创建 `.claude/skills/` 并软链接：

```bash
mkdir -p .claude/skills
ln -sfn /path/to/MySkills/execute-with-agy .claude/skills/execute-with-agy
```

---

### 方式二：接入 Google Antigravity (AGY)

Antigravity 原生支持基于目录层级的自动发现与技能渐进式加载（Progressive Disclosure）：

#### 1. 全局配置
软链接到 Antigravity 全局配置目录：

```bash
mkdir -p ~/.gemini/config/skills

# 挂载技能
ln -sfn /path/to/MySkills/execute-with-agy ~/.gemini/config/skills/execute-with-agy
ln -sfn /path/to/MySkills/man-system ~/.gemini/config/skills/man-system
```

#### 2. 工作区专属配置
在你的工程代码库中直接作为工作区技能载入：

```bash
mkdir -p .agents/skills
ln -sfn /path/to/MySkills/execute-with-agy .agents/skills/execute-with-agy
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
