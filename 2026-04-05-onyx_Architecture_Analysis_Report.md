# Onyx 开源 AI 平台 — 技术架构与源码研读报告

**项目名称**: [onyx-dot-app/onyx](https://github.com/onyx-dot-app/onyx)
**star**: ~24,000 | **fork**: ~3,200 | **今日新增 star**: 1,200+
**技术栈**: Python (FastAPI) + Next.js 16 (React 19) + PostgreSQL + Vespa + Redis + Celery
**许可证**: MIT (社区版)
**分析日期**: 2026-04-05
**分析人**: OpenClaw Agent

---

## 一、项目定位与核心能力

Onyx（前身 Danswer）是一个开源的企业级 Gen-AI 与智能搜索平台，定位于**LLM 的应用层**，为各类 LLM 提供企业级的 RAG、Agent、Deep Research 能力。

**核心功能矩阵**:

| 功能 | 说明 |
|------|------|
| **Agentic RAG** | 混合索引 + AI Agent 驱动的高质量信息检索 |
| **Deep Research** | 多步骤研究流程，输出深度报告（2026年2月 leaderboard 第一） |
| **Custom Agents** | 支持自定义指令、知识库和 Actions 的 Agent 构建 |
| **Web Search** | 支持 Serper/Google PSE/Brave/SearXNG + 内置爬虫 + Firecrawl/Exa |
| **Code Execution** | 沙箱中执行 Python 代码，进行数据分析、绘图、文件修改 |
| **Voice Mode** | TTS + STT 语音对话 |
| **Image Generation** | 图像生成 |
| **MCP & Actions** | 与外部应用深度集成，支持灵活 Auth |
| **50+ 数据源连接器** | Google Drive, Confluence, Notion, Slack, GitHub, Jira, etc. |
| **多租户** | 企业级多租户隔离架构 |

---

## 二、整体架构总览

```
┌──────────────────────────────────────────────────────┐
│                     Clients                          │
│  Web (Next.js) │ Desktop │ CLI │ Chrome Extension     │
│           │ Widget │ Discord Bot │ Slack Bot          │
└──────────────┬───────────────────────────────────────┘
               │ HTTPS
┌──────────────▼───────────────────────────────────────┐
│           backend/  (FastAPI + Celery)               │
│  ┌─────────────────────────────────────────────────┐  │
│  │  onyx/server/  (REST API + WebSocket Streaming)  │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │  onyx/chat/  (LLM Loop / Tool Call / Streaming) │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  onyx/llm/   │  │ onyx/tools/  │  │  indexing │  │
│  │  (LiteLLM)   │  │ (Tool Runner)│  │ (Pipeline)│  │
│  └──────────────┘  └──────────────┘  └───────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Celery Workers (9种专业 worker 类型)             │  │
│  └─────────────────────────────────────────────────┘  │
└──────────────┬───────────────────────────────────────┘
               │
    ┌──────────┼──────────────┐
    ▼          ▼              ▼
PostgreSQL   Redis        Vespa DB
 (主数据)   (消息队列)    (向量数据库)
```

---

## 三、后端架构详解

### 3.1 技术选型

- **Web 框架**: FastAPI (async, 自动 OpenAPI docs)
- **ORM**: SQLAlchemy (同步 + async 混合)
- **任务队列**: Celery + Redis (9 种专业化 Worker)
- **向量数据库**: Vespa (来自 Yahoo，高性能混合搜索)
- **LLM 抽象层**: LiteLLM (统一接口访问 100+ LLM)
- **全文搜索**: PostgreSQL `pg_vector` / Vespa
- **认证**: OAuth2, SAML, API Key, PAT (Personal Access Token)
- **部署**: Docker Compose / Kubernetes

### 3.2 目录结构

```
backend/
├── alembic/              # 数据库迁移
├── onyx/
│   ├── access/           # 权限访问控制
│   ├── auth/             # 认证 (OAuth, SAML, API Key, PAT)
│   ├── background/       # Celery Beat 调度
│   ├── cache/            # Redis 缓存接口
│   ├── chat/             # 核心聊天处理 ⭐
│   │   ├── llm_loop.py        # LLM 主循环
│   │   ├── llm_step.py       # 单步 LLM 执行
│   │   ├── process_message.py # 消息处理入口
│   │   ├── compression.py    # 上下文压缩
│   │   ├── citation_processor/ # 引文处理
│   │   ├── tool_call_args_streaming.py  # Tool call 流式处理
│   │   └── save_chat.py      # 聊天持久化
│   ├── configs/          # 各类配置 (app_configs, model_configs, chat_configs...)
│   ├── connectors/       # 50+ 数据源连接器 ⭐
│   │   ├── github/, gmail/, notion/, slack/, jira/, ...
│   │   ├── factory.py    # 连接器工厂
│   │   ├── registry.py   # 连接器注册表
│   │   └── connector_runner.py  # 连接器运行器
│   ├── context/          # 搜索上下文管理
│   │   └── search/       # 搜索模型与处理
│   ├── db/               # 数据库模型与操作
│   │   ├── models.py     # SQLAlchemy 模型
│   │   ├── engine/       # 数据库引擎配置
│   │   └── chat/, document/, llm/, user/, ...
│   ├── deep_research/    # 深度研究模块 ⭐
│   │   ├── dr_loop.py    # 研究循环
│   │   └── models.py
│   ├── document_index/   # 文档索引管理
│   ├── file_processing/  # 文件处理 (PDF, HTML, etc.)
│   │   ├── extract_file_text.py
│   │   ├── html_utils.py
│   │   └── unstructured.py
│   ├── file_store/       # 文件存储
│   ├── indexing/         # 索引管道 ⭐
│   │   ├── chunker.py    # 文档分块
│   │   ├── embedder.py   # 向量化
│   │   ├── indexing_pipeline.py  # 完整索引流程
│   │   └── vector_db_insertion.py  # Vespa 写入
│   ├── key_value_store/  # KV 存储
│   ├── kg/               # Knowledge Graph 知识图谱
│   ├── llm/              # LLM 抽象层 ⭐
│   │   ├── factory.py    # LLM 工厂函数
│   │   ├── interfaces.py # LLM 接口定义
│   │   ├── multi_llm.py  # 多模型并行
│   │   ├── litellm_singleton/  # LiteLLM 单例
│   │   └── well_known_providers/  # 已知 provider 常量
│   ├── mcp_server/       # MCP (Model Context Protocol) 服务器
│   ├── natural_language_processing/  # NLP 工具
│   ├── prompts/          # Prompt 模板
│   ├── redis/            # Redis 集成
│   ├── secondary_llm_flows/  # 次级 LLM 流程 (命名/摘要等)
│   ├── server/           # API 路由层 ⭐
│   │   ├── api_key/      # API Key 管理
│   │   ├── query_and_chat/  # 聊天 API ⭐
│   │   │   ├── chat_backend.py
│   │   │   ├── query_backend.py
│   │   │   ├── session_loading.py
│   │   │   ├── placement.py
│   │   │   └── models.py
│   │   ├── documents/    # 文档 API
│   │   ├── manage/       # 管理 API
│   │   ├── features/     # 功能开关
│   │   └── middleware/   # 中间件
│   ├── tools/            # 工具系统 ⭐
│   │   ├── interface.py  # 工具接口
│   │   ├── tool_runner.py  # 工具执行器
│   │   ├── built_in_tools.py  # 内置工具注册
│   │   ├── tool_implementations/  # 工具实现
│   │   │   ├── search/         # 搜索工具
│   │   │   ├── web_search/     # Web 搜索
│   │   │   ├── python/         # Python 执行 (沙箱)
│   │   │   ├── memory/         # 记忆工具
│   │   │   ├── knowledge_graph/  # 知识图谱
│   │   │   ├── file_reader/    # 文件读取
│   │   │   ├── images/         # 图像生成
│   │   │   ├── mcp/            # MCP 工具
│   │   │   └── open_url/       # URL 打开
│   │   └── models.py
│   ├── tracing/          # 分布式追踪
│   ├── voice/             # 语音模式
│   ├── image_gen/         # 图像生成
│   ├── mcp_server/        # MCP Server
│   └── main.py            # FastAPI 应用入口
├── model_server/         # 独立模型服务 (embedding / rerank)
├── ee/                    # Enterprise Edition 扩展
└── requirements/          # 依赖分层 (base, dev, ee)
```

### 3.3 LLM 抽象层 (`onyx/llm/`)

Onyx 的 LLM 层设计非常优雅，采用了**工厂模式 + 接口抽象**：

```python
# onyx/llm/factory.py
def get_default_llm(): ...
def get_llm_for_persona(persona: Persona): ...
def get_llm_token_counter(): ...

# onyx/llm/interfaces.py
class LLM(ABC):
    def chat(...): ...
    def stream_chat(...): ...
    def async_gen(...): ...
```

通过 **LiteLLM** 实现对 100+ LLM 的统一访问：
- OpenAI / Anthropic / Google Gemini
- 开源模型：Ollama, vLLM, LiteLLM, TGI
- OpenRouter, Azure, AWS Bedrock, etc.

### 3.4 聊天处理流程 (`onyx/chat/`)

```
User Message
    │
    ▼
process_message.py
    │
    ▼
gather_stream_full() ──── Multi-Model ──▶ handle_multi_model_stream()
    │
    ▼
llm_loop.py (LLM Loop)
    │
    ├────── (no tool call) ──▶ Emitter (Streaming Response)
    │
    └────── (tool call) ──▶ run_tool_calls()
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
               SearchTool    WebSearchTool   PythonTool
                    │              │              │
                    ▼              ▼              ▼
               Vespa Search   External API   Sandboxed
                    │              │           Exec
                    └──────────────┴──────────────┘
                                   │
                                   ▼
                         ToolResponse
                                   │
                                   ▼
                         CitationProcessor (引文处理)
                                   │
                                   ▼
                         Streaming Final Response
```

**LLM Loop 核心逻辑** (`llm_loop.py`):
```python
class LLMLoop:
    def run(...) -> Generator[Emitter, None, None]:
        # 1. 构建 System Prompt (包含 memory, persona, tools)
        # 2. 调用 LLM (支持 streaming)
        # 3. 提取 Tool Calls
        # 4. 执行 Tool (run_tool_calls)
        # 5. 将 Tool Response 注入下一轮 LLM
        # 6. 重复直到 LLM 不再调用工具
        # 7. 返回最终响应 + 引文
```

### 3.5 索引管道 (`onyx/indexing/`)

```
Document Source
    │
    ▼
ConnectorRunner (从外部抓取)
    │
    ▼
indexing_pipeline.py
    │
    ├─▶ extract_file_text()    # 文本提取
    ├─▶ Chunker (分块 + 添加上下文)
    ├─▶ Embedder (向量化 via model_server)
    └─▶ VectorDB Insertion (Vespa)
           │
           ▼
    PostgreSQL (元数据 + 关系)
```

**分块策略** (`chunker.py`):
- 基于 token 计数的智能分块
- 支持 overlap
- 添加周围上下文 (surrounding context)

### 3.6 数据连接器 (`onyx/connectors/`)

支持 **50+ 数据源**，统一接口：

```python
# onyx/connectors/interfaces.py
class InputConnector(Protocol):
    def poll_source(self, ...): ...  # 增量拉取

class DocumentConnector(Protocol):
    def load_from_state(self, ...): ...  # 从外部加载文档
    def fetch_documents(self, ...): ...   # 批量获取
```

每种连接器都实现了工厂注册：
```python
# registry.py
CONNECTORRegistry = {
    "github": GitHubConnector,
    "gmail": GmailConnector,
    "notion": NotionConnector,
    ...
}
```

### 3.7 Celery Worker 架构 (9种专业 Worker)

| Worker | 职责 | 并发度 |
|--------|------|--------|
| **Primary** | 协调任务、connector 管理、LLM 更新 | 4 threads |
| **Docfetching** | 从外部数据源抓取文档 | 可配置 |
| **Docprocessing** | 文档处理 → 索引管道 | 可配置 |
| **Light** | 快速任务 (Vespa 操作、权限同步) | 高并发 |
| **Heavy** | 资源密集任务 (文档裁剪) | 4 threads |
| **KG Processing** | 知识图谱处理与聚类 | 可配置 |
| **Monitoring** | 系统健康监控 | 1 thread |
| **User File** | 用户文件处理 | 可配置 |
| **Beat** | Celery Beat 调度器 | 单例 |

**优先级队列**: High / Medium / Low

**Beat 定时任务**:
- 每 15s: 索引检查
- 每 20s: Connector 删除检查、Vespa 同步检查
- 每 20s: 裁剪检查
- 每 60s: KG 处理
- 每 5min: 监控任务

### 3.8 深度研究模块 (`onyx/deep_research/`)

```python
# dr_loop.py
class DeepResearchLoop:
    # 多步骤研究循环：
    # 1. 制定研究计划 (Plan)
    # 2. 执行搜索查询
    # 3. 综合信息
    # 4. 迭代优化
    # 5. 生成最终报告
```

---

## 四、前端架构 (`web/`)

- **框架**: Next.js 16.1.7 + React 19.2.4
- **UI**: Tailwind CSS + Radix UI / Shadcn/ui
- **状态管理**: React Context + SWR/Zustand (推测)
- **部署**: Docker

```
web/
├── src/
│   ├── app/           # Next.js App Router
│   ├── components/    # React 组件
│   ├── lib/           # 工具函数
│   └── types/         # TypeScript 类型
├── public/            # 静态资源
└── Dockerfile
```

---

## 五、工具系统深度解析

### 5.1 工具接口设计

```python
# onyx/tools/interface.py
class Tool(ABC):
    name: str
    description: str

    def execute(...) -> ToolResponse:
        """同步执行"""
    
    async def async_execute(...) -> ToolResponse:
        """异步执行"""
```

### 5.2 内置工具实现

| 工具 | 位置 | 功能 |
|------|------|------|
| **SearchTool** | `tool_implementations/search/` | Vespa 混合搜索 |
| **WebSearchTool** | `tool_implementations/web_search/` | 多源 Web 搜索 |
| **PythonTool** | `tool_implementations/python/` | 沙箱 Python 执行 |
| **MemoryTool** | `tool_implementations/memory/` | 用户记忆管理 |
| **KnowledgeGraphTool** | `tool_implementations/knowledge_graph/` | 知识图谱查询 |
| **FileReader** | `tool_implementations/file_reader/` | 读取上传文件 |
| **ImageTool** | `tool_implementations/images/` | DALL-E 等图像生成 |
| **MCPTool** | `tool_implementations/mcp/` | MCP 协议工具 |
| **OpenURL** | `tool_implementations/open_url/` | 打开 URL 获取内容 |

### 5.3 Python 沙箱执行

`PythonTool` 是一个亮点特性，用户可以在聊天中执行 Python 代码：
- 使用隔离的 Python 解释器 (推测使用 `exec` 或容器隔离)
- 支持数据可视化 (matplotlib, seaborn)
- 支持数据分析 (pandas, numpy)
- 返回结构化结果

---

## 六、多租户架构

Onyx 采用**数据库层面的多租户隔离**：

```
PostgreSQL
├── Tenant A (schema: tenant_a)
│   ├── users
│   ├── documents
│   └── ...
├── Tenant B (schema: tenant_b)
│   └── ...
└── Tenant C (schema: tenant_c)
    └── ...
```

通过 `tenant_id` 在所有表上实现行级隔离，中间件自动注入：

```python
# shared_configs/contextvars.py
def get_current_tenant_id() -> str | None:
    return _tenant_id.get()
```

Celery Beat 使用 `DynamicTenantScheduler` 实现多租户任务隔离。

---

## 七、MCP (Model Context Protocol) 支持

```python
# onyx/mcp_server/
# onyx/tools/tool_implementations/mcp/
```

Onyx 实现了 MCP Server，允许：
1. 将 Onyx 作为 MCP Server 供其他 Agent 使用
2. 通过 MCP 协议调用外部工具
3. 灵活的 Auth 选项 (OAuth 等)

---

## 八、部署架构

```
# docker-bake.hcl + docker-compose
┌─────────────┐
│   Nginx     │  (反向代理 + SSL)
└──────┬──────┘
       │
┌──────▼──────┐
│  Next.js    │  Web UI
└──────┬──────┘
       │
┌──────▼──────┐
│  FastAPI    │  API Server (多实例)
└──────┬──────┘
       │
┌──────▼──────┐
│  Celery     │  Background Workers (9种)
│  Workers    │
└──────┬──────┘
       │
┌──────▼──────┐
│  Vespa      │  Vector DB
└─────────────┘
┌─────────────┐
│  PostgreSQL │
└─────────────┘
┌─────────────┐
│    Redis    │  Cache + Celery Broker
└─────────────┘
```

**一键部署**:
```bash
curl -fsSL https://onyx.app/install_onyx.sh | bash
```

---

## 九、源码研读亮点

### 9.1 LLM Loop 的 Tool Call 流式处理

Onyx 实现了在流式响应中实时提取和执行 Tool Call 的能力：

```python
# onyx/chat/tool_call_args_streaming.py
# 特点：
# 1. 不等 LLM 完全返回就开始解析 Tool Call
# 2. Tool Call 参数的 JSON 流式解析
# 3. 先执行 Tool，再将结果注入下一轮
```

### 9.2 上下文压缩机制

```python
# onyx/chat/compression.py
# 当聊天历史过长时，自动压缩：
# 1. 摘要压缩 (LLM 生成摘要)
# 2. 删除低价值消息
# 3. 保留引文和关键信息
```

### 9.3 混合搜索策略

Onyx 不只做向量检索，而是**混合搜索**：
- BM25 (全文) + Vector (语义) + Keyword Boost
- 重排序 (Rerank) 阶段
- 引文匹配

### 9.4 Agentic RAG 流程

```
Query → 路由判断 → (RAG搜索 / Web搜索 / 直接回答)
           ↓
      搜索 → 引文处理 → 答案生成
           ↓ (如果需要多步)
      迭代搜索 → 综合
```

---

## 十、与同类项目对比

| 维度 | Onyx | LangChain | Dify | AnythingLLM |
|------|------|-----------|------|-------------|
| **LLM 支持** | 100+ | 100+ | 50+ | 10+ |
| **连接器数量** | 50+ | 中等 | 100+ | 少 |
| **Deep Research** | ✅ | 需自己搭 | ❌ | ❌ |
| **沙箱代码执行** | ✅ | ❌ | ❌ | ❌ |
| **多租户** | ✅ | 需企业版 | ✅ | ❌ |
| **MIT 许可** | ✅ | ❌ | ❌ | ❌ |
| **架构** | FastAPI + Celery | Python | Go + React | Electron |

**Onyx 的差异化优势**:
1. **企业级多租户** — 开源且完整的多租户实现
2. **Deep Research** — 真正可用的研究代理
3. **沙箱 Python 执行** — 数据分析场景的直接支持
4. **全栈自托管** — 完整的企业数据连接方案

---

## 十一、技术债务与改进建议

1. **依赖复杂度**: `uv.lock` 包含大量依赖，企业安全扫描需重点关注
2. **Celery Worker 状态**: Worker 挂了难以追踪，建议增加更完善的监控
3. **Vespa 运维**: Vespa 不是常见组件，自托管有一定门槛
4. **前端技术栈**: Next.js 16 + React 19 太新，生产环境需谨慎
5. **Schema 迁移**: Alembic 迁移脚本在多租户场景下需要额外测试

---

## 十二、总结

Onyx 是一个**架构极为完整**的开源 AI 平台项目，其设计体现了：

- **清晰的模块边界**: chat / indexing / tools / llm / connectors 各自独立
- **专业的工程化**: Celery 9种 Worker、完整的监控告警、多租户隔离
- **出色的可扩展性**: Connector 注册机制、Tool 接口抽象、MCP 协议
- **务实的功能实现**: 不是 Demo，而是真正可以部署使用的企业级产品

作为曾经是 Danswer 的项目，Onyx 证明了开源社区完全有能力构建与商业产品竞争的企业级 AI 基础设施。其架构对于构建类似 Perplexity / ChatGPT Enterprise 类的产品有极高的参考价值。

---

*本报告由 OpenClaw Agent 自动生成*
*分析时间: 2026-04-05 03:00 (Asia/Shanghai)*
