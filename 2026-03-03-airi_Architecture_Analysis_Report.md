# AIRI: AI 虚拟角色容器系统 技术架构与源码研读报告

**分析日期**: 2026-03-03  
**项目名称**: AIRI (Project AIRI)  
**GitHub 链接**: https://github.com/moeru-ai/airi  
**项目作者**: Moeru AI Team  
**Star 数**: 21,275+ (今日新增 1,425 ⭐)  
**趋势排名**: GitHub TypeScript Trending #1

---

## 一、项目概述与定位

### 1.1 项目愿景

AIRI 是一个**开源的 AI 虚拟角色容器系统**，旨在重新创造类似 Neuro-sama 的数字生命体。与 Character.ai、JanitorAI 等纯聊天平台不同，AIRI 追求让虚拟角色真正"活"在用户的世界中——能够实时语音对话、观察用户的屏幕、一起玩游戏、记住过去的互动。

**核心定位**: "Soul container of AI waifu / virtual characters to bring them into our world"

### 1.2 独特价值主张

| 特性 | 传统 AI 聊天 | AIRI |
|------|-------------|------|
| 交互方式 | 纯文本 | 实时语音 + 视觉 + 游戏 |
| 存在感 | 被动响应 | 主动观察屏幕、参与游戏 |
| 形象展示 | 静态头像 | VRM/Live2D 3D 虚拟形象 |
| 部署方式 | 云端服务 | 完全自托管、本地优先 |
| 平台支持 | Web 为主 | Web + 桌面 + 移动端 |

### 1.3 技术特色

项目从第一天就深度整合 Web 技术栈：
- **WebGPU**: 本地 LLM 推理加速
- **WebAudio**: 实时音频处理
- **Web Workers**: 后台任务处理
- **WebAssembly**: Rust 高性能模块
- **WebSocket**: 实时通信

---

## 二、整体架构设计

### 2.1 架构全景图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用户交互层 (Presentation Layer)                      │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐               │
│  │  Stage Web      │ │ Stage Tamagotchi│ │  Stage Pocket   │               │
│  │  (浏览器/WebView)│ │  (桌面应用)      │ │  (iOS移动端)     │               │
│  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘               │
└───────────┼─────────────────┼─────────────────┼─────────────────────────────┘
            │                 │                 │
            ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          核心运行时层 (Stage Core)                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     @proj-airi/stage-core                           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │Character │ │  Chat    │ │  Audio   │ │  Memory  │ │  Game    │  │   │
│  │  │Orchestr. │ │ Session  │ │ Pipeline │ │  System  │ │  Bridge  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          服务层 (Services)                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ LLM Service │ │ TTS Service │ │ ASR Service │ │  Mods API   │          │
│  │  (OpenAI/   │ │(ElevenLabs/ │ │  (Whisper/  │ │  (MCP/      │          │
│  │   Claude)   │ │  WebGPU)    │ │   WebGPU)   │ │  Plugin)    │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          原生能力层 (Native Layer)                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Tauri / Rust Crates                          │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │   │
│  │  │ Audio Trans. │ │   Audio VAD  │ │  Window Ctrl │ │    MCP     │  │   │
│  │  │   (ORT)      │ │   (ORT)      │ │  (Pass-thru) │ │  Plugin    │  │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Monorepo 结构分析

```
air/
├── apps/                          # 应用层
│   ├── stage-web/                 # Web 版本 (Vite + Vue)
│   ├── stage-tamagotchi/          # 桌面版 (Tauri)
│   ├── stage-pocket/              # iOS 移动端 (Capacitor)
│   ├── server/                    # 后端服务 (Hono + Drizzle)
│   └── component-calling/         # 组件调用示例
│
├── packages/                      # 共享包
│   ├── stage-core/                # 核心运行时
│   ├── stage-ui/                  # UI 组件库
│   ├── ui-transitions/            # 过渡动画
│   ├── ui/                        # 基础 UI 组件
│   └── ...                        # 其他工具包
│
├── crates/                        # Rust 原生模块
│   ├── tauri-plugin-ipc-audio-transcription-ort/  # 语音转文字
│   ├── tauri-plugin-ipc-audio-vad-ort/            # 语音活动检测
│   ├── tauri-plugin-mcp/                          # MCP 协议支持
│   ├── tauri-plugin-rdev/                         # 设备输入控制
│   └── ...
│
├── services/                      # 微服务
├── plugins/                       # 插件系统
├── integrations/                  # 第三方集成
└── docs/                          # 文档站
```

---

## 三、核心技术栈详解

### 3.1 前端架构 (Vue 3 + TypeScript)

**Store 架构设计** (Pinia-based):

```typescript
// 核心 Store 分层
stores/
├── chat/                    # 聊天相关
│   ├── session-store.ts    # 会话管理
│   ├── conversation-store.ts # 对话历史
│   └── memory-store.ts     # 记忆存储
├── character/
│   ├── orchestrator-store.ts  # 角色编排
│   └── avatar-store.ts        # 形象管理
├── mods/
│   ├── api/                 # Mods API
│   │   ├── channel-server.ts  # 服务器通道
│   │   └── context-bridge.ts  # 上下文桥接
├── settings.ts             # 全局设置
└── ...
```

**关键设计模式**:

1. **Orchestrator 模式**: 角色编排器统一管理多个 AI 角色的状态、对话轮询、情感表达
2. **Context Bridge**: 跨层上下文桥接，连接 Web 层与原生层
3. **Channel Server**: Mods 服务器通道，支持外部插件通过 WebSocket 接入

### 3.2 跨平台架构 (Tauri + Capacitor)

**桌面端 (Tauri)**:

| 组件 | 技术 | 用途 |
|------|------|------|
| 前端 | WebView2/WebKit | Vue 3 UI 渲染 |
| 后端 | Rust | 系统级能力封装 |
| AI 推理 | candle + ONNX Runtime | 本地 LLM/VAD/ASR |
| GPU 加速 | CUDA/Metal | NVIDIA/Apple 芯片加速 |

**移动端 (Capacitor)**:
- iOS 原生 Swift 代码通过 Capacitor 插件桥接
- Web 代码复用率 > 90%
- PWA 支持离线使用

### 3.3 Rust 原生模块

**Crate 架构**:

```rust
// crates/ 目录下的 Tauri 插件

// 1. 音频转录插件 - 基于 ONNX Runtime
#[tauri::command]
async fn transcribe_audio(
    state: State<'_, TranscriptionState>,
    audio_data: Vec<f32>,
) -> Result<String, String> {
    // Whisper 模型本地推理
}

// 2. 语音活动检测 - WebRTC VAD 替代方案
#[tauri::command]
async fn detect_voice_activity(
    state: State<'_, VADState>,
    audio_chunk: Vec<f32>,
) -> Result<bool, String> {
    // Silero VAD 模型
}

// 3. MCP 协议支持 - 模型上下文协议
#[tauri::command]
async fn mcp_invoke_tool(
    tool_name: String,
    params: Value,
) -> Result<Value, String> {
    // 连接外部 MCP 服务器
}
```

### 3.4 后端服务 (Hono + Drizzle)

**技术选型**:
- **框架**: Hono (轻量、边缘友好)
- **ORM**: Drizzle ORM
- **数据库**: PostgreSQL (Railway 部署)
- **认证**: Lucia Auth
- **实时**: WebSocket (Cloudflare Workers)

**API 架构**:

```typescript
// apps/server/src/routes/characters.ts
app.get('/api/characters', async (c) => {
  const user = c.get('user')
  const characters = await characterService.findByUserId(user.id)
  return c.json(characters)
})

// 角色 Schema 设计 (Drizzle)
export const characters = pgTable('characters', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  personality: jsonb('personality'),      // 人格配置
  capabilities: jsonb('capabilities'),    // 能力列表
  avatarModel: jsonb('avatar_model'),     // VRM/Live2D 配置
  memoryConfig: jsonb('memory_config'),   // 记忆系统配置
  llmConfig: jsonb('llm_config'),         // LLM 提供商配置
  ...
})
```

---

## 四、核心系统详解

### 4.1 角色编排系统 (Character Orchestrator)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Character Orchestrator                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Character  │───▶│   Emotion   │───▶│   Action    │        │
│  │   State     │    │   Engine    │    │   Selector  │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                │
│         ▼                  ▼                  ▼                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Memory    │◀───│   LLM Core  │───▶│   Response  │        │
│  │   Layer     │    │  (Router)   │    │  Formatter  │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         ▲                                                    │
│         │         ┌─────────────┐                            │
│         └─────────│  Context    │                            │
│                   │  Builder    │                            │
│                   └─────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**多角色支持**:
- 支持同时加载多个角色
- 角色间可以"感知"彼此存在
- 群聊模式下的角色互动

### 4.2 记忆系统 (Memory System)

**三层记忆架构**:

1. **工作记忆 (Working Memory)**: 当前对话上下文 (Sliding Window)
2. **短期记忆 (Short-term Memory)**: 最近 N 轮对话摘要
3. **长期记忆 (Long-term Memory)**: 向量化存储 + RAG 检索

**技术实现**:
- 浏览器端: DuckDB WASM / pglite (嵌入式 PostgreSQL)
- 服务端: PostgreSQL + pgvector
- 向量嵌入: 使用 embedding 模型将记忆向量化

```typescript
// 记忆存储结构
interface Memory {
  id: string
  content: string                    // 记忆内容
  embedding?: number[]              // 向量表示
  importance: number                // 重要性评分
  createdAt: Date
  accessedAt: Date                  // 最后访问时间
  associations: string[]            // 关联记忆 ID
}

// RAG 检索流程
async function retrieveRelevantMemories(
  query: string,
  characterId: string
): Promise<Memory[]> {
  const queryEmbedding = await embed(query)
  return db.memories
    .where('character_id', '=', characterId)
    .orderBy(cosineDistance('embedding', queryEmbedding))
    .limit(5)
}
```

### 4.3 音频管道 (Audio Pipeline)

**实时语音交互流程**:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Micro   │───▶│   VAD    │───▶│   ASR    │───▶│   LLM    │
│  Input   │    │ (Rust)   │    │(Whisper) │    │  Core    │
└──────────┘    └──────────┘    └──────────┘    └────┬─────┘
                                                      │
┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  Audio   │◀───│   TTS    │◀───│ Response │◀────────┘
│  Output  │    │(WebGPU)  │    │ Formatter│
└──────────┘    └──────────┘    └──────────┘
```

**VAD (语音活动检测)**:
- 使用 Silero VAD 模型
- 通过 ONNX Runtime 在 Rust 层运行
- 支持本地和云端两种模式

**TTS (语音合成)**:
- 主要: ElevenLabs API (高质量)
- 备选: WebGPU 本地合成 (piper/kokoro)
- 支持情感标记注入

### 4.4 游戏集成 (Game Bridge)

**Minecraft 集成**:
- 通过 mineflayer 库创建机器人客户端
- 角色可以"看到"游戏世界、移动、交互
- LLM 通过 function calling 控制游戏行为

**Factorio 集成**:
- 基于 RCON 协议远程控制
- 角色可以观察工厂状态、下达指令

```typescript
// 游戏能力接口
interface GameCapability {
  name: 'minecraft' | 'factorio'
  status: 'connected' | 'disconnected'
  
  // 感知接口
  observe(): Promise<GameState>
  
  // 行动接口
  execute(action: GameAction): Promise<void>
  
  // 事件订阅
  onEvent(handler: (event: GameEvent) => void): void
}
```

---

## 五、UI/UX 架构

### 5.1 设计系统

**主题系统**:
- 动态色彩: 基于 OKLCH 色彩空间
- 色相动画: CSS 变量驱动动态色相偏移
- 暗黑/明亮模式: 完整的 dual-theme 支持

```css
/* 动态色相动画 */
@property --chromatic-hue {
  syntax: '<number>';
  initial-value: 0;
  inherits: true;
}

.dynamic-hue {
  animation: hue-anim 10s linear infinite;
}
```

**组件层次**:

```
@proj-airi/ui           # 基础原子组件 (Button, Input, etc.)
    │
    ▼
@proj-airi/stage-ui     # 业务组件 (ChatBubble, Avatar, etc.)
    │
    ▼
App.vue                 # 应用级组合
```

### 5.2 场景管理

**Stage 概念**: 类似游戏引擎的 Scene 系统

- **IndexScene**: 角色选择/管理
- **StageScene**: 主互动场景 (对话、游戏)
- **SettingsScene**: 配置页面

**页面过渡动画**:
- 使用 StageTransitionGroup 组件
- 基于 Vue Transition 封装
- 支持 page-specific 和 global 两种模式

---

## 六、工程化实践

### 6.1 构建系统

**Turbo + pnpm**:

```json
// turbo.json
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".output/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "test": {
      "dependsOn": ["build"]
    }
  }
}
```

### 6.2 代码质量

**Linting & Formatting**:
- ESLint: @antfu/eslint-config + 自定义规则
- Rust: clippy + rustfmt
- 提交前检查: simple-git-hooks + nano-staged

**类型安全**:
- TypeScript 严格模式
- 全局类型定义共享
- API Schema 与 Drizzle 类型同步

### 6.3 部署架构

**多平台部署**:

| 目标平台 | 技术方案 | CI/CD |
|---------|---------|-------|
| Web | Cloudflare Pages | GitHub Actions |
| Desktop | Tauri + GitHub Releases | release-tamagotchi.yml |
| iOS | Capacitor + TestFlight | Xcode Cloud |
| Server | Railway/Cloudflare Workers | Auto-deploy |

---

## 七、技术亮点与创新

### 7.1 WebGPU 本地推理

项目充分利用 WebGPU 在浏览器中运行 LLM:
- 使用 Transformers.js + ONNX Runtime Web
- 支持 LLaMA、Phi、Qwen 等模型
- 完全离线运行，隐私优先

### 7.2 混合渲染架构

- **Web 层**: Vue 3 负责 UI、动画、布局
- **原生层**: Rust/Tauri 负责高性能计算、系统访问
- **GPU 层**: CUDA/Metal 负责模型推理

### 7.3 插件系统设计

**Mods API** 允许第三方扩展:
- WebSocket 协议通信
- 上下文桥接机制
- 安全沙箱环境

### 7.4 多模态能力

不仅限于文本对话，整合:
- 视觉: 屏幕观察、VRM 表情动画
- 听觉: 实时语音识别/合成
- 触觉: 设备输入/输出控制

---

## 八、学习借鉴点

### 8.1 架构设计

1. **Monorepo 最佳实践**:
   - 清晰的分层: apps/packages/crates
   - 合理的依赖关系
   - Turbo 缓存优化

2. **跨平台代码复用**:
   - 核心业务逻辑抽离到 stage-core
   - 平台特定代码最小化
   - 统一的状态管理

3. **渐进式能力扩展**:
   - 基础版: 纯 Web，云端 API
   - 进阶版: 桌面端，本地推理
   - 完整版: 移动端，完整生态

### 8.2 工程实践

1. **现代前端工具链**:
   - pnpm workspace
   - Vite + Vue 3
   - UnoCSS 原子 CSS
   - Vitest 测试

2. **类型安全**:
   - TypeScript 端到端
   - Schema 驱动开发
   - 共享类型定义

3. **开源协作**:
   - 完善的 CONTRIBUTING.md
   - Crowdin 国际化协作
   - 多语言 README

### 8.3 产品思维

1. **自托管优先**: 用户拥有完全控制权
2. **渐进增强**: 从简单聊天到完整数字生命
3. **社区驱动**: 开放的 Mods API，生态扩展

---

## 九、总结与评价

### 9.1 技术评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | ⭐⭐⭐⭐⭐ | 清晰的分层，合理的抽象 |
| 代码质量 | ⭐⭐⭐⭐⭐ | 类型安全，工程规范 |
| 创新程度 | ⭐⭐⭐⭐⭐ | WebGPU + AI 虚拟角色 |
| 可维护性 | ⭐⭐⭐⭐☆ | Monorepo 复杂度较高 |
| 文档完整 | ⭐⭐⭐⭐⭐ | 多语言文档，DevLog |

### 9.2 适用场景

- **AI 虚拟角色开发**: 参考其架构设计
- **多平台 AI 应用**: 学习跨平台方案
- **本地优先 AI**: WebGPU 本地推理模式
- **实时语音交互**: 音频管道设计

### 9.3 未来展望

项目仍处于快速迭代期 (v0.8.5-beta)，已知 Roadmap:
- 更完善的记忆系统 (Memory Alaya)
- VR/AR 支持 (WebXR)
- 更多游戏集成
- 更强大的 Mods 生态

---

**报告生成时间**: 2026-03-03  
**分析者**: OpenClaw Code Analysis Agent  
**数据来源**: GitHub API、源码阅读、官方文档
