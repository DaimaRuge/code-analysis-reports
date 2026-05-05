# 《Model Context Protocol Python SDK》技术架构与源码研读报告

> **分析日期**：2026年5月6日  
> **项目来源**：[modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)  
> **语言/生态**：Python ≥ 3.10 · Pydantic · Starlette · anyio  
> **GitHub Stars**：86.3k ⭐ · Forks：9.8k  

---

## 一、项目概述

Model Context Protocol (MCP) 是一个开放协议，旨在让 AI 模型通过标准化的服务器实现，安全地与本地和远程资源交互。Python SDK 是 MCP 协议的官方 Python 实现，支持构建 MCP 客户端和服务器。

### 核心能力

- 🖥️ **服务器构建**：通过装饰器轻松暴露 Tools / Resources / Prompts
- 🔌 **多传输层**：Stdio / SSE / Streamable HTTP / WebSocket
- 🔐 **认证体系**：OAuth 2.1 + RFC 9728 Protected Resource Metadata
- 🧩 **双层 API**：Low-level Server（底层协议控制）+ FastMCP（高级声明式）
- 📦 **结构化输出**：自动序列化 Pydantic / TypedDict / dataclass

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Side                                 │
│   ClientSession → StdioClient / SSIClient / StreamableHTTPClient   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  JSON-RPC 2.0 over ReadStream/WriteStream
┌──────────────────────────────▼──────────────────────────────────────┐
│                         Server Side                                 │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                  MCPServer / Server (FastMCP)                │     │
│  │  • 暴露 Tools / Resources / Prompts                          │     │
│  │  • 管理生命周期 (lifespan)                                    │     │
│  │  • 提供 FastMCP Context 注入                                  │     │
│  └───────────────────────────┬─────────────────────────────────┘     │
│                              │                                       │
│  ┌───────────────────────────▼─────────────────────────────────┐     │
│  │              Low-Level Server (server/lowlevel/)             │     │
│  │  • JSON-RPC 消息分发（on_* handler 注册）                      │     │
│  │  • 协议版本协商                                              │     │
│  │  • 能力声明（capabilities）                                   │     │
│  └───────────────────────────┬─────────────────────────────────┘     │
│                              │                                       │
│  ┌───────────────────────────▼─────────────────────────────────┐     │
│  │                    ServerSession                             │     │
│  │  • 消息路由（Request / Response / Notification）             │     │
│  │  • RequestResponder 生命周期管理                              │     │
│  │  • 进度通知 / 采样 /  elicitation                            │     │
│  └───────────────────────────┬─────────────────────────────────┘     │
│                              │                                       │
│  ┌───────────────────────────▼─────────────────────────────────┐     │
│  │          Transport Layer (传输层)                            │     │
│  │  stdio.py / sse.py / streamable_http.py / websocket.py       │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                  Shared / Types                              │     │
│  │  types/_types.py (1778行) – 全协议类型定义                   │     │
│  │  shared/message.py, session.py, response_router.py           │     │
│  │  shared/experimental/tasks/ – 任务支持                      │     │
│  └─────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、模块结构详解

### 3.1 类型系统 `src/mcp/types/`

`types/_types.py` 约 **1778 行**，是整个 SDK 的协议契约层。

| 重要类型 | 说明 |
|---|---|
| `LATEST_PROTOCOL_VERSION = "2025-11-25"` | 当前最新协议版本 |
| `RequestParams` | 包含 `task`（任务元数据）和 `_meta`（进度令牌） |
| `PaginatedRequestParams` | 支持 cursor 分页 |
| `MCPModel` | 全协议类型的 Pydantic 基类，统一使用 `alias_generator=to_camel` |
| `ProgressToken` | `str \| int`，用于进度通知追踪 |
| `SamplingMessage` | LLM 采样消息结构 |
| 所有 JSON-RPC 类型 | `JSONRPCRequest / JSONRPCResponse / JSONRPCNotification / JSONRPCError` |

### 3.2 传输层 `src/mcp/server/`

| 文件 | 职责 |
|---|---|
| `stdio.py` | 标准 I/O 传输，适合本地 CLI 场景 |
| `sse.py` | Server-Sent Events 传输 |
| `streamable_http.py` | **生产推荐**，支持有状态/无状态模式，Event Store 实现断点续传 |
| `streamable_http_manager.py` | 多会话管理，`StreamableHTTPSessionManager` |
| `websocket.py` | WebSocket 双向传输 |
| `transport_security.py` | TLS / mTLS 中间件 |

`streamable_http.py` 的核心设计：
- 通过 `MCP_SESSION_ID_HEADER` 实现会话追踪
- 支持 `application/json`（无状态/JSON响应）和 `text/event-stream`（SSE流式）两种模式
- `EventStore` 实现事件持久化，支持重连后恢复

### 3.3 Low-Level Server `src/mcp/server/lowlevel/server.py`（672行）

底层协议引擎，核心职责是**消息分发**。

```python
class Server(Generic[LifespanResultT]):
    def __init__(self, name: str, on_*: Callable):
        # on_list_tools, on_call_tool, on_list_resources...
```

**消息分发流程：**

```
接收 JSON-RPC Message
    → JSONRPCMessage.parse()
    → method string 路由
    → 对应 on_* handler
    → 返回 ServerResult
    → 写入 WriteStream
```

关键设计点：
- 使用 `on_*` 模式注册 handler（handler 可以是协程）
- `NotificationOptions` 控制是否主动发送 `prompts_changed` 等通知
- 默认 lifespan 是空 context，可自定义 lifespan wrapper
- 集成 OpenTelemetry Trace（`otel_span`）用于分布式追踪
- 支持 Starlette ASGI 应用挂载（`app()` 方法）

### 3.4 MCPServer（FastMCP）`src/mcp/server/mcpserver/server.py`（1112行）

FastMCP 是对 Low-Level Server 的**高级封装**，提供声明式 API。

```python
class MCPServer(Generic[LifespanResultT]):
    def __init__(
        self,
        name: str | None = None,
        title: str | None = None,
        tools: list[Tool] | None = None,
        resources: list[Resource] | None = None,
        lifespan: Callable | None = None,
        auth: AuthSettings | None = None,
        # ...
    ):
```

**四大核心管理器：**

| 管理器 | 文件 | 职责 |
|---|---|---|
| `ToolManager` | `mcpserver/tools/tool_manager.py` | `@tool()` 装饰器注册，函数反射提取元数据 |
| `ResourceManager` | `mcpserver/resources/resource_manager.py` | 资源 URI 模板解析，`file://`、`config://` 等 |
| `PromptManager` | `mcpserver/prompts/manager.py` | 提示词模板管理 |
| `Context` | `mcpserver/context.py` | 请求上下文 + 生命周期 context 注入 |

**Settings 配置模式：**

```python
class Settings(BaseSettings, Generic[LifespanResultT]):
    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_file=".env",
        env_nested_delimiter="__",
    )
    debug: bool
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
```

所有配置均可通过环境变量 `MCP_DEBUG=true` 注入，实现了**零代码配置**。

### 3.5 ServerSession `src/mcp/server/session.py`（692行）

会话层核心，负责**请求-响应生命周期管理**：

```python
class RequestResponder(Generic[ReceiveRequestT, SendResultT]):
    """必须作为上下文管理器使用，确保 cancellation scope 正确清理"""
```

**设计模式：异步上下文管理器保障资源释放**

```python
with request_responder as resp:
    await resp.respond(result)
```

- 自动创建/清理 anyio cancellation scope
- 追踪请求完成状态
- 清理 in-flight 请求

### 3.6 认证体系 `src/mcp/server/auth/`

基于 OAuth 2.1，包含两个核心角色：

| 角色 | 说明 |
|---|---|
| **Authorization Server (AS)** | 发行 Bearer Token，处理用户认证 |
| **Resource Server (RS)** | MCP 服务器本身，验证 Token |

**路由设计：**

```
/oauth/authorize    → 授权端点
/oauth/token       → Token 发行
/protected_resource → RFC 9728 元数据端点
```

关键类：
- `OAuthAuthorizationServerProvider` – AS 实现
- `TokenVerifier` – RS 端的 Token 验证协议
- `AuthContextMiddleware` + `BearerAuthBackend` – Starlette 中间件链

### 3.7 任务系统 `src/mcp/shared/experimental/tasks/`

实现 MCP 的**任务增强执行（Task-augmented Execution）**：

```
Request with task metadata
    → CreateTaskResult (立即返回)
    → 后台执行
    → tasks/result 接口获取结果
```

- `InMemoryTaskStore` – 内存任务存储
- `MessageQueue` – 任务消息队列
- `Polling` / `Resolver` – 任务结果解析

---

## 四、装饰器与元编程

### `@tool()` 装饰器工作原理

```python
# 源码位置：mcpserver/tools/tool_manager.py
def add_tool(
    self,
    fn: Callable[..., Any],
    name: str | None = None,
    structured_output: bool | None = None,
) -> Tool:
    tool = Tool.from_function(
        fn,
        name=name,
        structured_output=structured_output,
        # 从函数签名自动提取 annotations / description
    )
```

**函数反射流程：**

1. `inspect.signature(fn)` 提取参数签名
2. Pydantic `TypeAdapter` 将函数签名转换为 JSON Schema
3. 从 docstring 第一行提取 description
4. 从类型注解提取 output schema

### 结构化输出自动分类

```
函数返回类型
    ├── Pydantic BaseModel → structured
    ├── TypedDict → structured
    ├── dataclass（有 type hints）→ structured
    ├── dict[str, T] → structured
    ├── primitive types → wrapped in {"result": value}
    └── 无类型标注 → unstructured
```

---

## 五、关键设计模式

### 5.1 双层 Server 架构

| 层级 | 适用场景 | 控制粒度 |
|---|---|---|
| **FastMCP (MCPServer)** | 大多数 MCP 服务器 | 声明式，装饰器驱动 |
| **Low-Level Server** | 需要完整协议控制 | 手动 handler 注册，完整生命周期管理 |

### 5.2 泛型生命周期类型

```python
class MCPServer(Generic[LifespanResultT]):
    # LifespanResultT 允许自定义上下文类型
    # 在 Context[ServerSession, AppContext] 中使用
```

### 5.3 会话恢复与 Event Store

`streamable_http.py` 的 `EventStore` 实现了 MCP 会话的**幂等恢复机制**：

```
Client 重连（带 session-id）
    → EventStore 查找历史事件
    → 重放未完成的状态变更
    → 继续处理
```

### 5.4 OpenTelemetry 集成

每个请求自动创建 span：

```python
with otel_span(
    name=f"mcp.{method}",
    kind=SpanKind.SERVER,
    attributes={"mcp.method": method, "mcp.session_id": session_id}
):
    # 处理请求
```

---

## 六、协议版本演进

| 版本 | 日期 | 说明 |
|---|---|---|
| `2025-03-26` | 2025-03 | 早期协商默认版本 |
| `2025-11-25` | 2025-11 | 当前最新协议版本 |

服务端假设客户端未指定版本时使用 `DEFAULT_NEGOTIATED_VERSION = "2025-03-26"`。

---

## 七、依赖生态

```
anyio>=4.9              # 跨平台异步 I/O（支持 Windows/macOS/Linux）
httpx>=0.27.1           # HTTP 客户端（支持 HTTP/2）
pydantic>=2.12.0        # 数据验证 + JSON Schema 生成
starlette>=0.27         # ASGI 框架（传输层底层）
sse-starlette>=3.0      # SSE 支持
pydantic-settings>=2.5  # 环境变量驱动配置
opentelemetry-api>=1.28# 分布式追踪
```

---

## 八、总结与洞见

### 架构亮点

1. **协议-传输分离**：传输层（stdio/http/websocket）与协议层完全解耦，可独立替换
2. **声明式优先**：FastMCP 的装饰器模式极大降低了 MCP 服务器开发门槛
3. **渐进式复杂度**：从 `@mcp.tool()` 到 Low-Level Server，提供了复杂度递进的 API 层次
4. **安全优先**：OAuth 2.1 认证体系完整，符合企业安全要求
5. **任务化执行**：后台任务 + 轮询机制支持长时运行操作的异步化

### 潜在关注点

1. **EventStore 内存化**：默认 `InMemoryTaskStore`，多进程部署需要外置存储
2. **TypeScript SDK 对称性**：Python SDK v2 与 TypeScript SDK v2 同步开发中，需关注接口一致性
3. **Structured Output 边界**：unstructured 结果仍有向后兼容需求，可能在 v2 中逐步收紧

---

*报告由 OpenClaw 自动生成 · 2026-05-06*
