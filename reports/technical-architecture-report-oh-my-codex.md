# 技术架构与源码研读报告

## oh-my-codex (OmX) — 多智能体编排层 for OpenAI Codex CLI

> 项目地址: https://github.com/Yeachan-Heo/oh-my-codex  
> Stars: 13,815 | 今日新增: 2,984  
> 语言: TypeScript + Rust  
> License: MIT

---

## 一、项目概述

**oh-my-codex** (简称 OmX) 是一个运行在 OpenAI Codex CLI 之上的**多智能体工作流编排层**。它不替代 Codex，而是为其叠加了更强大的任务路由、工作流模板和运行时状态管理能力。

核心设计理念：
- **$deep-interview** — Socratic 追问式需求澄清
- **$ralplan** — 共识规划（Planner + Architect + Critic 循环）
- **$ralph** — 持续执行与验证循环
- **$team** — 多 Agent 并行协同执行

OmX 拥有与 OpenClaw 的深度集成（`src/openclaw/`），并通过 hooks 系统将 Codex 的会话生命周期与外部通知网关打通。

---

## 二、整体架构

```
┌─────────────────────────────────────────────────┐
│                    omx CLI                      │
│         (src/cli/omx.ts — 入口)                 │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌────────┐  │
│  │  Prompts/   │  │  Skills/     │  │ Agents │  │
│  │  (提示词库)  │  │  (35+技能)   │  │ (角色) │  │
│  └─────────────┘  └──────────────┘  └────────┘  │
├─────────────────────────────────────────────────┤
│           Hook System (src/hooks/)               │
│  KeywordDetector │ SessionHooks │ PromptGuidance  │
│  TaskSizeDetector │ ExploreRouting │ AgentsOverlay │
├─────────────────────────────────────────────────┤
│  ┌──────────┐  ┌───────────┐  ┌───────────────┐  │
│  │ Pipeline │  │  Team/    │  │ MCP Servers   │  │
│  │(编排器)   │  │ (tmux协同) │  │(态/记忆/追踪) │  │
│  └──────────┘  └───────────┘  └───────────────┘  │
├─────────────────────────────────────────────────┤
│   OpenClaw Integration (src/openclaw/)          │
│        Gateway Notifier + Config Reader          │
├─────────────────────────────────────────────────┤
│         Rust Native Crates (crates/)             │
│  omx-explore │ omx-runtime-core │ omx-sparkshell │
└─────────────────────────────────────────────────┘
```

**三层架构：**
1. **感知层** — Hooks 系统：监听会话事件，检测关键词和任务规模
2. **决策层** — Pipeline Orchestrator：路由到相应技能和 Agent 角色
3. **执行层** — Team Runtime (tmux) / MCP Servers：实际运行多 Agent 工作

---

## 三、核心模块详解

### 3.1 入口与配置 (`src/cli/`, `src/config/`)

```
src/cli/
  ├── omx.ts          # CLI 入口，分发 setup/doctor/explore/team 等命令
  ├── setup.ts        # 安装：提示词、skills、AGENTS.md、native 配置
  ├── doctor.ts       # 诊断：验证 omx 环境完整性
  ├── sparkshell.ts   # 轻量 shell 原生验证
  └── session-search.ts  # 跨会话搜索

src/config/
  ├── generator.ts    # 配置生成器（mergeConfig）
  ├── models.ts       # 模型能力定义
  └── mcp-registry.ts # MCP 服务器注册表
```

**配置加载机制：**
- `~/.codex/.omx-config.json` — 主配置
- 支持 `notifications.openclaw` / `custom_webhook_command` / `custom_cli_command` 别名
- `OMX_OPENCLAW=1` 环境变量激活 OpenClaw 集成

### 3.2 Hook 系统 (`src/hooks/`)

这是 OmX 最重要的感知与干预层，所有 `.test.ts` 文件证明其测试驱动开发（TDD）文化。

#### 3.2.1 关键词检测 (`keyword-detector.ts`)

```typescript
// 优先级系统驱动技能路由
{ keyword: 'ralph',       skill: 'ralph',       priority: 9 }
{ keyword: 'deep-interview', skill: 'deep-interview', priority: 8 }
{ keyword: 'ralplan',      skill: 'ralplan',     priority: 11 }  // 最高
{ keyword: 'team',         skill: 'team',        priority: 8 }
{ keyword: 'autopilot',    skill: 'autopilot',    priority: 10 }
{ keyword: 'ultrawork',    skill: 'ultrawork',   priority: 10 }
```

核心逻辑：
- `recordSkillActivation()` — 写状态文件 `skill-active-state.json`
- **Deep Interview Input Lock** — 访谈期间屏蔽自动批准快捷词（yes/y/proceed 等），防止误触发
- 状态机：`planning → executing → reviewing → completing`

#### 3.2.2 任务规模检测 (`task-size-detector.ts`)

自动判断任务是"小任务"还是"大任务"（heavy），影响是否启动团队模式：
- 扫描文件修改范围、依赖关系、测试数量
- 决定是否需要 `$team` 并行执行

#### 3.2.3 提示词指导 (`prompt-guidance-contract.ts`)

动态向 Codex 注入上下文提示，确保技能按规范执行。包括 fragment 注入、catalog 路由等。

#### 3.2.4 Explore 路由 (`explore-routing.ts`)

当用户需要"只读搜索"时，路由到 `explore` Agent（快速代码库映射），而非完整的 `executor`。

#### 3.2.5 Session Hooks (`session.ts`)

管理 Codex 会话生命周期：
- `session-start` — 初始化 `.omx/` 状态目录
- `session-end` — 保存 planning artifacts
- `session-idle` — 超时检测与 nudge

### 3.3 Agent 系统 (`src/agents/`)

```typescript
// 每个 Agent 有明确的角色定位
const EXECUTOR_AGENT = {
  posture: 'deep-worker',      // vs 'frontier-orchestrator' / 'fast-lane'
  modelClass: 'standard',       // vs 'frontier' / 'fast'
  routingRole: 'executor',       // vs 'leader' / 'specialist'
  tools: 'execution',           // vs 'read-only' / 'analysis' / 'data'
  category: 'build',            // vs 'review' / 'domain' / 'product' / 'coordination'
  reasoningEffort: 'high',      // vs 'low' / 'medium'
};
```

**Agent 角色矩阵：**

| Agent | 职责 | 模式 |
|-------|------|------|
| `explore` | 快速代码库搜索 | fast-lane |
| `analyst` | 需求澄清、验收标准 | frontier-orchestrator |
| `planner` | 任务排序、执行计划 | frontier-orchestrator |
| `architect` | 系统设计、边界接口 | frontier-orchestrator |
| `debugger` | 根因分析、回归隔离 | deep-worker |
| `executor` | 代码实现、重构 | deep-worker |
| `verifier` | 证据验证、测试充分性 | frontier-orchestrator |

### 3.4 Team 系统 (`src/team/`) — 多 Agent 协同核心

Team 是 OmX 最复杂的子系统，通过 **tmux** 实现真正的多进程并行 Agent 协调。

#### 3.4.1 Tmux Session 管理 (`tmux-session.ts`)

```typescript
// 每个 worker 运行在独立的 tmux pane 中
createTeamSession(sessionName, workerCount)  // 创建团队 tmux session
buildWorkerProcessLaunchSpec(worker)         // 构造 worker 启动命令
waitForWorkerReady(worker)                  // 等待 worker 就绪
sendToWorker(stdin/msg)                      // 向 worker 发消息
```

#### 3.4.2 Team Runtime (`runtime.ts`)

团队运行时的核心状态机：

```
team-init → leader-elect → task分配 → worker执行
                                              ↓
                      leader监控 ← idle检测 ← → 任务完成
                                              ↓
                         team-shutdown（所有 worker 优雅退出）
```

关键状态文件（`.omx/team/`）：
- `manifest.json` — 团队元数据（成员、角色）
- `tasks/` — 任务队列，claim/release 机制
- `inbox/` — worker 私有收件箱
- `governance.json` — 团队治理策略（任务大小阈值、仲裁规则）
- `phase-state.json` — 当前阶段（electing/working/shutting_down）

#### 3.4.3 角色路由器 (`role-router.ts`)

将任务动态分配给最适合的 Agent 角色：
- 分析任务类型（build/review/coordination）
- 匹配 `routingRole` 和 `modelClass`
- 注入角色专属提示词

#### 3.4.4 任务分配策略 (`allocation-policy.ts`)

- 基于任务规模的头数估算
- 负载均衡（rebalance-policy）
- 动态伸缩（scaling.ts）

#### 3.4.5 Followup Planner (`followup-planner.ts`)

处理"team" / "ralph" 简短后续指令的语义扩展：
```typescript
// 短命令展开为完整 staffing plan
/^team$/i  →  team-executor × 3
/^ralph$/i →  ralph 持久循环
```

### 3.5 Pipeline 编排器 (`src/pipeline/`)

将多个阶段串联为统一流水线：

```typescript
// RALPLAN → Team Exec → Ralph Verify
runPipeline(config: PipelineConfig): Promise<PipelineResult>

createRalplanStage()    // 共识规划阶段
createTeamExecStage()   // 团队执行阶段
createRalphVerifyStage() // 验证阶段
```

支持 `autopilot` 模式的端到端自动化执行。

### 3.6 MCP 服务器 (`src/mcp/`)

Model Context Protocol 服务器，提供有状态工具：

| 服务器 | 功能 |
|--------|------|
| `state-server.ts` | 读写 `.omx/` 状态文件 |
| `memory-server.ts` | 项目级记忆存储 |
| `team-server.ts` | 团队消息队列、dispatch |
| `trace-server.ts` | 执行追踪 |
| `code-intel-server.ts` | 代码智能（符号索引） |

### 3.7 OpenClaw 集成 (`src/openclaw/`) — 关键集成点

这是 OmX 与 OpenClaw 双向打通的桥梁，也是本次分析最具实践价值的内容。

#### 3.7.1 配置读取 (`config.ts`)

```typescript
// 从 ~/.codex/.omx-config.json 读取 notifications.openclaw
getOpenClawConfig(): OpenClawConfig | null
// 激活条件：OMX_OPENCLAW=1 环境变量
```

支持三种配置格式：
1. `notifications.openclaw` — 原生 OpenClaw 配置
2. `notifications.custom_webhook_command` — Webhook 别名
3. `notifications.custom_cli_command` — CLI 别名（兼容旧版）

#### 3.7.2 事件映射 (`types.ts`)

```typescript
type OpenClawHookEvent =
  | "session-start"   // 会话启动
  | "session-end"     // 会话结束
  | "session-idle"    // 会话空闲
  | "ask-user-question" // 询问用户
  | "stop";           // 停止事件
```

每个事件可映射到不同的 Gateway + 指令模板。

#### 3.7.3 Gateway 分发器 (`dispatcher.ts`)

支持两种 Gateway 类型：

**HTTP Gateway：**
```json
{
  "type": "http",
  "url": "https://gateway.example.com/hooks/wake",
  "method": "POST",
  "headers": { "Authorization": "Bearer xxx" },
  "timeout": 10000
}
```

**Command Gateway：**
```json
{
  "type": "command",
  "command": "openclaw gateway wake --event {{event}} --path {{projectPath}}"
}
```

变量插值系统：`{{sessionId}}`, `{{projectPath}}`, `{{prompt}}`, `{{tmuxSession}}`, `{{timestamp}}` 等。

#### 3.7.4 上下文白名单 (`index.ts`)

```typescript
// 只暴露明确允许的字段，防止敏感数据泄漏
function buildWhitelistedContext(context: OpenClawContext): OpenClawContext {
  // 仅包含：sessionId, projectPath, tmuxSession, prompt, contextSummary, reason, question, tmuxTail, replyChannel, replyTarget, replyThread
}
```

**自动 tmux 捕获**：对于 `stop` 和 `session-end` 事件，自动捕获最近 15 行 tmux pane 内容。

### 3.8 Skills 系统 (`skills/`)

35+ 技能目录，每个技能是独立的 `SKILL.md` 文件：

| 技能 | 用途 |
|------|------|
| `deep-interview` | Socratic 需求澄清 |
| `ralplan` | 共识规划 |
| `ralph` | 持续执行循环 |
| `team` | 多 Agent 协同 |
| `autopilot` | 全自主执行 |
| `ultrawork` | 并行加速 |
| `ultraqa` | 持续 QA 循环 |
| `build-fix` | 构建修复 |
| `code-review` | 代码审查 |
| `security-review` | 安全审查 |
| `tdd` | 测试驱动开发 |
| `plan` | 战略规划 |
| `visual-verdict` | 视觉验证 |

每个 SKILL.md 包含：
- `<Purpose>` — 技能目的
- `<Use_When>` / `<Do_Not_Use_When>` — 使用边界
- `<Execution_Policy>` — 执行策略
- `<Steps>` — 详细步骤

### 3.9 Rust 原生模块 (`crates/`)

OmX 的性能关键路径使用 Rust 编写：

| Crate | 用途 |
|-------|------|
| `omx-runtime-core` | 核心运行时引擎（dispatch/mailbox/authority） |
| `omx-runtime` | 运行时包装器 |
| `omx-explore` | 快速代码库探索（原生实现） |
| `omx-sparkshell` | Shell 原生命令执行 |
| `omx-mux` | Tmux 会话复用 |

`omx-runtime-core` 定义了命令和事件名称的二进制协议：
```rust
pub const RUNTIME_COMMAND_NAMES: &[&str] = &[
    "acquire-authority", "renew-authority", "queue-dispatch",
    "mark-notified", "mark-delivered", "mark-failed",
    "request-replay", "capture-snapshot", ...
];
```

---

## 四、关键设计模式

### 4.1 状态机 + 文件系统持久化

OmX 大量使用 `.omx/` 目录下的 JSON 文件作为状态机载体：
- `skill-active-state.json` — 当前激活技能
- `planning-artifacts.json` — 规划产物
- `team/manifest.json` — 团队配置
- `team/tasks/` — 任务队列（claim/release 模式）

这使得状态可以在进程重启后恢复，也便于调试。

### 4.2 Hook 可扩展性

通过 `notify hook` 系统，OmX 将 Codex CLI 的生命周期事件（session-start/end/stop/ask-user-question）转换为外部动作（发 HTTP 请求、执行 CLI 命令、捕获 tmux 状态）。

### 4.3 关键词优先级路由

`keyword-registry.ts` 定义了优先级系统，高优先级关键词（如 `ralplan` p=11）优先于低优先级（`analyze` p=7）被匹配。

### 4.4 Tmux 虚拟化

Team 系统将 tmux 作为多 Agent 虚拟化层，每个 worker 运行在独立 pane 中，通过 stdin/stdout 通信，无需修改 Codex 本身。

### 4.5 白名单安全模型

OpenClaw 集成中的 `buildWhitelistedContext()` 确保只暴露明确声明的字段，防止配置文件中的敏感信息意外泄漏到外部 Gateway。

---

## 五、技术栈总结

| 层次 | 技术 |
|------|------|
| 主语言 | TypeScript (ESM, Node.js 20+) |
| 原生模块 | Rust (via cargo) |
| 协议 | MCP (Model Context Protocol) |
| 会话虚拟化 | tmux |
| 配置格式 | JSON + TOML |
| 验证 | Zod v4, TypeScript strict |
| 测试 | Node.js built-in test runner + c8 coverage |
| 代码风格 | Biome (Biome.json) |
| 构建 | tsc → dist/ |

---

## 六、对 OpenClaw 的意义

OmX 展示了**多 Agent 编排**的一种成熟实现路径：

1. **OpenClaw 可借鉴**：OmX 的 Hook 事件映射 → OpenClaw 的 cron/wake 系统
2. **技能系统**：OmX 的 `skills/SKILL.md` 机制与 OpenClaw 的 skill 系统高度一致
3. **团队协作**：OmX 的 tmux 多 Agent 模式 → 可探索作为 OpenClaw 多节点协作的参考
4. **Gateway 集成**：OmX 的 HTTP/CLI Gateway 分发 → OpenClaw 的 webhook/notification 机制

OmX 证明了在 Codex CLI 这种封闭生态上，通过**文件系统 + Hooks + tmux 虚拟化**可以实现复杂的多 Agent 协调，且保持对宿主系统的零侵入。

---

*报告生成时间：2026-04-04 | 数据来源：oh-my-codex v0.11.12 源码*
