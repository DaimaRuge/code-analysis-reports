# AIRI 技术架构与源码研读报告

**分析日期**: 2026年3月4日  
**项目**: moeru-ai/airi  
**版本**: v0.8.5-beta.3  
**Stars**: 22,059 | **Forks**: 2,066

---

## 一、项目概述

AIRI 是一个自托管的 AI 伴侣项目，灵感来源于 Neuro-sama。它是一个功能丰富的虚拟角色容器，支持实时语音聊天、游戏互动（Minecraft、Factorio）、多平台部署（Web、macOS、Windows）。项目采用现代 Web 技术栈构建，支持纯浏览器运行和本地 GPU 加速推理。

### 核心特性
- **实时语音交互**: WebRTC + Web Audio API 实现低延迟语音对话
- **多模态能力**: 支持 Live2D、VRM 3D 模型、Three.js 渲染
- **本地推理**: 基于 WebGPU 的浏览器内本地 LLM 推理
- **记忆系统**: DuckDB WASM / pglite 纯浏览器数据库支持
- **游戏集成**: Minecraft 和 Factorio 游戏机器人
- **跨平台**: Web 应用 + Tauri 桌面应用

---

## 二、整体架构设计

### 2.1 技术栈分层

```
┌─────────────────────────────────────────────────────────────┐
│                     应用层 (Applications)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  stage-web   │  │stage-tamagotchi│ │ stage-pocket │      │
│  │   (Web App)  │  │  (Desktop)    │  │  (Mobile)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                     包层 (Packages)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   stage-ui   │  │ stage-ui-live2d│ │ stage-ui-three│     │
│  │  (核心UI组件) │  │  (Live2D渲染) │  │ (3D渲染引擎) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ core-character│ │    audio     │  │  pipelines   │      │
│  │ (角色核心逻辑)│  │ (音频处理)   │  │ (管道系统)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                     基础设施层 (Infra)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  server-sdk  │  │  stream-kit  │  │  plugin-sdk  │      │
│  │  (服务端SDK) │  │ (流处理工具) │  │  (插件系统)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                     Rust 原生层 (Crates)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ tauri-plugin │  │  audio-vad   │  │     mcp      │      │
│  │   (Tauri插件)│  │ (语音活动检测)│  │(模型上下文)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 包结构分析

项目采用 **pnpm workspace + Turborepo** 管理，包含 40+ 个包：

| 类别 | 包名 | 功能描述 |
|------|------|----------|
| **UI 核心** | `@proj-airi/stage-ui` | 核心 UI 组件库、状态管理、工具函数 |
| **渲染引擎** | `@proj-airi/stage-ui-live2d` | Live2D 模型渲染支持 |
| | `@proj-airi/stage-ui-three` | Three.js 3D 渲染引擎 |
| **角色系统** | `@proj-airi/core-character` | 角色管道编排（分词、情感、延迟、TTS） |
| **音频处理** | `@proj-airi/audio` | Web Audio API 封装、音频编码 |
| | `@proj-airi/pipelines-audio` | 音频处理管道 |
| **数据存储** | `@proj-airi/drizzle-duckdb-wasm` | DuckDB WASM 数据库封装 |
| | `@proj-airi/duckdb-wasm` | DuckDB WASM 核心 |
| **服务端** | `@proj-airi/server-runtime` | 服务端运行时 |
| | `@proj-airi/server-sdk` | 服务端 SDK |
| | `@proj-airi/server-schema` | 数据模型定义 |
| **插件系统** | `@proj-airi/plugin-protocol` | 插件通信协议 |
| | `@proj-airi/plugin-sdk` | 插件开发 SDK |
| **工具包** | `@proj-airi/stream-kit` | 流处理工具集 |
| | `@proj-airi/ccc` | 通用组件库 |

---

## 三、核心模块详解

### 3.1 角色系统架构 (`core-character`)

```typescript
// 角色状态管理核心 - 基于 Pinia
export const useCharacterStore = defineStore('character', () => {
  // 角色基本信息
  const name = computed(() => activeCard.value?.name ?? '')
  const ownerId = computed(() => activeCard.value?.name ?? 'default')
  
  // 反应系统 - 支持流式处理
  const reactions = ref<CharacterSparkNotifyReaction[]>([])
  const streamingReactions = ref<Map<string, StreamingReactionState>>(new Map())
  
  // 语音运行时集成
  const speechRuntimeStore = useSpeechRuntimeStore()
})
```

**设计亮点**:
1. **流式反应处理**: 支持 LLM 输出的实时流式解析和语音合成
2. **优先级队列**: 支持 `interrupt` (高优先级打断) 和 `queue` (队列等待) 两种行为模式
3. **LLM Marker 解析器**: 自定义文本解析器，支持特殊标记处理（表情、动作等）

### 3.2 音频处理架构 (`audio` + `pipelines-audio`)

```
音频输入 → VAD (语音活动检测) → 转录 (STT) → LLM → TTS → 音频输出
              ↓
         Web Audio API
              ↓
    AudioWorklet (实时处理)
```

**关键技术**:
- **Web Audio API**: 浏览器原生音频处理
- **AudioWorklet**: 低延迟音频处理线程
- **VAD (Voice Activity Detection)**: 语音活动检测，基于 `@ricky0123/vad-web`
- **STT 支持**: 集成 `@xsai/stream-transcription` 和 HuggingFace Transformers

### 3.3 UI 组件架构 (`stage-ui`)

**组件分层**:
```
src/
├── components/
│   ├── auth/           # 认证相关
│   ├── data-pane/      # 数据面板
│   ├── gadgets/        # 工具组件
│   ├── graphics/       # 图形渲染
│   ├── layouts/        # 布局组件
│   ├── markdown/       # Markdown 渲染
│   ├── modules/        # 功能模块
│   ├── scenarios/      # 场景组件
│   └── widgets/        # 通用小部件
├── composables/        # Vue 组合式函数
├── stores/             # Pinia 状态管理
├── workers/            # Web Workers
└── utils/              # 工具函数
```

**状态管理**:
- `character`: 角色状态、反应系统
- `settings`: 应用设置、模型配置
- `speech-runtime`: 语音运行时状态
- `analytics`: 分析数据

### 3.4 存储架构

**浏览器端存储**:
```typescript
// DuckDB WASM 纯浏览器数据库
@proj-airi/drizzle-duckdb-wasm

// 持久化状态管理 - unstorage + localforage
key features:
- 浏览器内 SQL 数据库
- 向量搜索支持 (pgvector WASM)
- 离线优先架构
```

---

## 四、关键技术决策分析

### 4.1 混合技术栈 (TypeScript + Rust)

**决策**: 核心逻辑用 TypeScript，性能敏感模块用 Rust

| 语言 | 用途 | 优势 |
|------|------|------|
| TypeScript | UI、业务逻辑、AI 管道 | 生态丰富、开发效率高 |
| Rust | Tauri 插件、音频处理、原生集成 | 性能极致、内存安全 |

**Rust 插件列表**:
- `tauri-plugin-ipc-audio-transcription-ort`: ONNX Runtime 音频转录
- `tauri-plugin-ipc-audio-vad-ort`: ONNX Runtime VAD
- `tauri-plugin-mcp`: Model Context Protocol 支持
- `tauri-plugin-rdev`: 全局输入设备监听

### 4.2 Web 优先架构

**决策**: 优先支持浏览器，桌面端作为增强

**优势**:
- 零安装体验
- 跨平台天然支持
- PWA 支持移动端

**桌面增强** (Tauri):
- CUDA/Metal GPU 加速
- 本地模型推理
- 系统集成（全局快捷键、系统托盘）

### 4.3 模块化插件系统

```
插件协议层 (plugin-protocol)
    ↓
插件 SDK (plugin-sdk)
    ↓
具体插件实现
```

**设计原则**:
- 标准化通信协议
- 沙箱化执行环境
- 热插拔支持

---

## 五、源码质量评估

### 5.1 代码组织

✅ **优点**:
- 清晰的 monorepo 结构
- 一致的命名规范
- 完善的类型定义 (TypeScript)
- 细粒度的包拆分

⚠️ **改进空间**:
- 包数量较多，依赖关系复杂
- 部分包之间存在循环依赖风险

### 5.2 工程化实践

**工具链**:
- **构建**: Vite + Turborepo
- **类型检查**: TypeScript 5.9
- **代码规范**: ESLint + @antfu/eslint-config
- **测试**: Vitest
- **CI/CD**: GitHub Actions

**依赖管理**:
- pnpm workspace
- Catalog dependencies (统一管理版本)
- Simple git hooks (代码提交前检查)

### 5.3 性能优化

**已实施**:
- Web Workers 用于后台任务
- WebGPU 加速推理
- 虚拟滚动优化长列表
- 懒加载和代码分割

---

## 六、架构创新点

### 6.1 "Soul Container" 概念

AIRI 不仅是一个聊天机器人，而是一个**灵魂容器**架构：
- 角色配置（性格、记忆、外观）
- 运行时状态（情绪、上下文）
- 可交换的 AI 后端（OpenAI、Claude、本地模型）

### 6.2 多模态实时交互

```
语音输入 → STT → LLM → 情感分析 → TTS + 唇形同步 + 表情动画
                ↓
           视觉识别 ← 屏幕捕获/摄像头
```

### 6.3 纯浏览器 AI 栈

- **推理**: Transformers.js + ONNX Runtime Web
- **向量数据库**: DuckDB WASM + pgvector
- **存储**: IndexedDB + localforage

---

## 七、学习价值与借鉴点

### 7.1 适合学习的方面

1. **Monorepo 管理**: pnpm workspace + Turborepo 最佳实践
2. **Web 音频处理**: Web Audio API + AudioWorklet 深度应用
3. **Vue 3 大型项目**: 组合式函数、状态管理、组件设计
4. **Tauri 集成**: Rust + TypeScript 混合开发模式
5. **AI 应用架构**: LLM 流式处理、管道编排

### 7.2 可复用的模式

```typescript
// 1. 流式处理管道模式
interface IntentHandle {
  writeLiteral(text: string): void
  writeSpecial(special: string): void
  writeFlush(): void
  end(): void
}

// 2. 优先级队列模式
type Priority = 'high' | 'normal' | 'low'
type Behavior = 'interrupt' | 'queue' | 'drop'

// 3. 模块化状态管理
// 按功能域拆分 store，避免单文件过大
```

---

## 八、总结

AIRI 是一个架构精良、技术前沿的开源 AI 伴侣项目。其核心优势在于：

1. **现代化的技术栈**: Vue 3 + TypeScript + Tauri + WebGPU
2. **模块化的架构**: 40+ 个精心设计的包
3. **Web 优先理念**: 浏览器端实现复杂的 AI 交互
4. **活跃的社区**: 22k+ stars，持续迭代

**适合人群**:
- 学习现代前端架构的开发者
- 探索 AI 应用开发的工程师
- 对虚拟角色/数字人感兴趣的技术爱好者

---

**报告生成**: OpenClaw Code Analysis Agent  
**数据来源**: GitHub API + 源码分析  
**分析方法**: 静态代码分析 + 架构模式识别
