# 《DeerFlow 技术架构与源码研读报告》

**分析日期**: 2026年3月24日  
**项目来源**: [bytedance/deer-flow](https://github.com/bytedance/deer-flow)  
**Stars**: 38,704 (今日新增 3,569)  
**Forks**: 4,555  
**分析人**: OpenClaw AI  

---

## 一、项目概述

### 1.1 项目定位

DeerFlow（**D**eep **E**xploration and **E**fficient **R**esearch **Flow）是字节跳动开源的一款**Super Agent Harness**（超级代理框架），基于 LangGraph 和 LangChain 构建。它不是一个简单的聊天机器人，而是一个完整的代理运行时基础设施，赋予 AI 代理实际执行任务的能力。

### 1.2 核心创新点

- **子代理系统（Sub-Agents）**: 主代理可将任务分解并委托给子代理并行执行，最多支持3个并发子代理
- **持久化记忆（Long-Term Memory）**: 跨会话保留用户偏好、工作上下文和知识
- **沙箱执行（Sandbox Execution）**: 每个任务在隔离的 Docker 容器中运行，支持完整的文件系统和命令执行
- **技能系统（Skills System）**: 可扩展的模块化能力，支持自定义技能和工作流
- **多通道支持（IM Channels）**: 原生支持 Feishu、Slack、Telegram 等即时通讯平台

### 1.3 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **Agent Runtime** | LangGraph 1.0.6+ | 多智能体编排框架 |
| **LLM Abstraction** | LangChain 1.2.3+ | LLM 抽象和工具系统 |
| **API Gateway** | FastAPI 0.115.0+ | REST API 服务 |
| **Frontend** | Next.js | React 前端框架 |
| **MCP Integration** | langchain-mcp-adapters | Model Context Protocol |
| **Document Processing** | markitdown | 多格式文档转换 |
| **Web Search** | Tavily, Jina AI, Firecrawl | 网络搜索和爬取 |
| **Sandbox** | agent-sandbox | 沙箱代码执行 |

---

## 二、架构设计详解

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Nginx (Port 2026)                           │
│                    统一反向代理入口点                                │
└───────────────┬──────────────────────┬──────────────────────────────┘
                │                      │
   /api/langgraph/*              /api/* (其他)
                │                      │
                ▼                      ▼
┌────────────────────────┐  ┌──────────────────────────────────────┐
│  LangGraph Server      │  │  Gateway API (Port 8001)             │
│  (Port 2024)           │  │  FastAPI REST                        │
│                        │  │                                      │
│ ┌────────────────────┐ │  │  - Models, MCP, Skills              │
│ │   Lead Agent       │ │  │  - Memory, Uploads                  │
│ │  ┌──────────────┐  │ │  │  - Artifacts, Threads               │
│ │  │  Middleware  │  │ │  └──────────────────────────────────────┘
│ │  │   Chain      │  │ │
│ │  └──────────────┘  │ │
│ │  ┌──────────────┐  │ │
│ │  │    Tools     │  │ │
│ │  └──────────────┘  │ │
│ │  ┌──────────┐      │ │
│ │  │Subagents │      │ │
│ │  └──────────┘      │ │
│ └────────────────────┘ │
└────────────────────────┘
```

### 2.2 分层架构设计

项目采用严格的分层架构，**Harness/App 分离**设计：

```
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Gateway API   │  │  IM Channels    │  │  Frontend       │  │
│  │  (app.gateway)  │  │ (app.channels)  │  │  (Next.js)      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ 导入 deerflow.* (允许)
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Harness Layer (Agent Framework)             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │   Agents    │ │   Tools     │ │   Sandbox   │ │   Skills   │ │
│  │  ┌───────┐  │ │  ┌───────┐  │ │  ┌───────┐  │ │  ┌───────┐ │ │
│  │  │Lead   │  │ │  │MCP    │  │ │  │Local  │  │ │  │Load   │ │ │
│  │  │Agent  │  │ │  │Tools  │  │ │  │Docker │  │ │  │Inject │ │ │
│  │  └───────┘  │ │  └───────┘  │ │  └───────┘  │ │  └───────┘ │ │
│  │  ┌───────┐  │ │  ┌───────┐  │ │  ┌───────┐  │ │  ┌───────┐ │ │
│  │  │Memory │  │ │  │Comm.  │  │ │  │K8s    │  │ │  │Custom │ │ │
│  │  └───────┘  │ │  └───────┘  │ │  └───────┘  │ │  └───────┘ │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**关键原则**: Harness 层永不导入 App 层，App 层可导入 Harness 层。这一边界由 CI 测试 `test_harness_boundary.py` 强制执行。

---

## 三、核心组件源码解析

### 3.1 Lead Agent 系统

**文件位置**: `backend/packages/harness/deerflow/agents/lead_agent/agent.py`

```python
def make_lead_agent(config: RunnableConfig):
    """主代理工厂函数"""
    cfg = config.get("configurable", {})
    
    # 1. 解析运行时配置
    thinking_enabled = cfg.get("thinking_enabled", True)
    reasoning_effort = cfg.get("reasoning_effort", None)
    requested_model_name = cfg.get("model_name") or cfg.get("model")
    is_plan_mode = cfg.get("is_plan_mode", False)
    subagent_enabled = cfg.get("subagent_enabled", False)
    
    # 2. 模型名称解析优先级
    model_name = requested_model_name or agent_model_name  # 请求 > 代理配置 > 全局默认
    
    # 3. 创建 LangChain Agent
    return create_agent(
        model=create_chat_model(name=model_name, thinking_enabled=thinking_enabled),
        tools=get_available_tools(model_name=model_name, subagent_enabled=subagent_enabled),
        middleware=_build_middlewares(config, model_name=model_name),
        system_prompt=apply_prompt_template(subagent_enabled=subagent_enabled),
        state_schema=ThreadState,
    )
```

**设计亮点**:
- 支持动态模型切换（无需重启服务）
- 运行时配置注入（思考模式、子代理开关、计划模式等）
- LangSmith 追踪标签自动注入

### 3.2 中间件链（Middleware Chain）

中间件执行严格顺序，共 **12 个中间件**：

| 序号 | 中间件 | 职责 | 源码位置 |
|------|--------|------|----------|
| 1 | ThreadDataMiddleware | 创建线程隔离目录 | `middlewares/` |
| 2 | UploadsMiddleware | 注入上传文件到上下文 | `middlewares/` |
| 3 | SandboxMiddleware | 获取沙箱环境 | `sandbox/middleware.py` |
| 4 | DanglingToolCallMiddleware | 修补中断的工具调用 | `middlewares/` |
| 5 | GuardrailMiddleware | 工具调用权限控制 | `middlewares/` |
| 6 | SummarizationMiddleware | 上下文摘要（可选） | `create_agent` 注入 |
| 7 | TodoListMiddleware | 任务列表管理（计划模式） | `middlewares/todo_middleware.py` |
| 8 | TitleMiddleware | 自动生成对话标题 | `middlewares/title_middleware.py` |
| 9 | MemoryMiddleware | 异步记忆更新队列 | `middlewares/memory_middleware.py` |
| 10 | ViewImageMiddleware | 视觉模型图像注入 | `middlewares/view_image_middleware.py` |
| 11 | SubagentLimitMiddleware | 限制并发子代理数量 | `middlewares/subagent_limit_middleware.py` |
| 12 | LoopDetectionMiddleware | 检测工具调用循环 | `middlewares/loop_detection_middleware.py` |
| 13 | ClarificationMiddleware | 拦截澄清请求（必须最后） | `middlewares/clarification_middleware.py` |

**关键设计模式**: 每个中间件实现 `AgentMiddleware` 接口，通过 `before_agent()` 和 `after_agent()` 钩子干预执行流程。

### 3.3 ThreadState 状态管理

**文件位置**: `backend/packages/harness/deerflow/agents/thread_state.py`

```python
class ThreadState(AgentState):
    """扩展 LangChain AgentState 的线程状态"""
    sandbox: NotRequired[SandboxState | None]          # 沙箱状态
    thread_data: NotRequired[ThreadDataState | None]   # 线程数据路径
    title: NotRequired[str | None]                     # 对话标题
    artifacts: Annotated[list[str], merge_artifacts]   # 产出物（自动去重）
    todos: NotRequired[list | None]                    # 任务列表
    uploaded_files: NotRequired[list[dict] | None]     # 上传文件
    viewed_images: Annotated[dict, merge_viewed_images] # 已查看图像
```

**Reducer 函数设计**: 使用 `Annotated[Type, reducer]` 模式实现状态合并策略：
- `merge_artifacts`: 列表合并并去重，保留顺序
- `merge_viewed_images`: 字典合并，空字典表示清空

### 3.4 沙箱系统（Sandbox System）

**抽象接口**: `backend/packages/harness/deerflow/sandbox/sandbox.py`

```python
class Sandbox(ABC):
    """沙箱环境抽象基类"""
    
    @abstractmethod
    def execute_command(self, command: str) -> str:
        """执行 bash 命令"""
        
    @abstractmethod
    def read_file(self, path: str) -> str:
        """读取文件内容"""
        
    @abstractmethod
    def list_dir(self, path: str, max_depth=2) -> list[str]:
        """列出目录内容"""
        
    @abstractmethod
    def write_file(self, path: str, content: str, append: bool = False) -> None:
        """写入文件"""
```

**两种实现**:
1. **LocalSandboxProvider**: 本地文件系统执行，适用于开发环境
2. **AioSandboxProvider**: Docker 容器隔离，适用于生产环境

**虚拟路径系统**:
```
Agent 视角路径                    物理路径
/mnt/user-data/workspace    →  backend/.deer-flow/threads/{thread_id}/user-data/workspace
/mnt/user-data/uploads      →  backend/.deer-flow/threads/{thread_id}/user-data/uploads
/mnt/user-data/outputs      →  backend/.deer-flow/threads/{thread_id}/user-data/outputs
/mnt/skills                 →  deer-flow/skills/
```

**工具实现**: `backend/packages/harness/deerflow/sandbox/tools.py`
- `bash`: 命令执行，自动路径转换
- `ls`: 目录列表（树形格式，最大2层深度）
- `read_file`: 文件读取，支持行范围
- `write_file`: 文件写入/追加，自动创建目录
- `str_replace`: 字符串替换（单处或全部）

### 3.5 子代理系统（Subagent System）

**文件位置**: `backend/packages/harness/deerflow/subagents/executor.py`

**架构设计**:
```
┌─────────────────────────────────────────────────────────────────────┐
│                        SubagentExecutor                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  双线程池架构                                                   │  │
│  │  ┌─────────────────────┐    ┌─────────────────────────────┐   │  │
│  │  │ _scheduler_pool     │    │ _execution_pool             │   │  │
│  │  │ (3 workers)         │───▶│ (3 workers)                 │   │  │
│  │  │ 调度任务              │    │ 执行子代理                   │   │  │
│  │  └─────────────────────┘    └─────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  任务状态机                                                    │  │
│  │  PENDING → RUNNING → [COMPLETED | FAILED | TIMED_OUT]         │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  并发控制: MAX_CONCURRENT_SUBAGENTS = 3                        │  │
│  │  超时控制: 15 分钟 (可配置)                                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**执行流程**:
```python
def execute_async(self, task: str, task_id: str | None = None) -> str:
    """异步执行任务"""
    # 1. 创建结果容器
    result = SubagentResult(task_id=task_id, status=SubagentStatus.PENDING)
    
    # 2. 提交到调度线程池
    def run_task():
        # 3. 提交到执行线程池
        execution_future = _execution_pool.submit(self.execute, task, result_holder)
        try:
            # 4. 等待执行结果（带超时）
            exec_result = execution_future.result(timeout=self.config.timeout_seconds)
        except FuturesTimeoutError:
            result.status = SubagentStatus.TIMED_OUT
            
    _scheduler_pool.submit(run_task)
    return task_id
```

**内置子代理类型**:
- **general-purpose**: 全工具集（除 `task` 外）
- **bash**: 命令执行专家

### 3.6 记忆系统（Memory System）

**文件位置**: `backend/packages/harness/deerflow/agents/memory/`

**数据模型**:
```json
{
  "userContext": {
    "workContext": "工作背景信息",
    "personalContext": "个人背景信息",
    "topOfMind": "1-3句核心摘要"
  },
  "history": {
    "recentMonths": "最近几个月摘要",
    "earlierContext": "早期上下文",
    "longTermBackground": "长期背景"
  },
  "facts": [
    {
      "id": "uuid",
      "content": "事实内容",
      "category": "preference|knowledge|context|behavior|goal",
      "confidence": 0.85,
      "createdAt": "timestamp",
      "source": "对话来源"
    }
  ]
}
```

**工作流程**:
```
┌─────────────────────────────────────────────────────────────────────┐
│                        Memory 工作流程                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. MemoryMiddleware.after_agent()                                  │
│     └── 过滤消息（仅保留用户输入 + 最终AI响应）                       │
│     └── 排除工具消息和中间步骤                                       │
│                                                                     │
│  2. 加入 MemoryQueue                                               │
│     └── 防抖机制（默认30秒批处理）                                   │
│     └── 按线程ID去重                                                │
│                                                                     │
│  3. 后台线程处理                                                    │
│     └── 调用 LLM 提取事实和上下文                                    │
│     └── 归一化去重（去除首尾空格后比较）                             │
│                                                                     │
│  4. 原子写入 memory.json                                            │
│     └── 临时文件 + rename 保证原子性                                 │
│     └── mtime 缓存失效机制                                          │
│                                                                     │
│  5. 下次对话注入                                                    │
│     └── 前15个高置信度事实                                          │
│     └── 用户上下文摘要                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.7 MCP 系统集成

**文件位置**: `backend/packages/harness/deerflow/mcp/client.py`

**MCP (Model Context Protocol)** 支持三种传输方式：

| 类型 | 说明 | 配置示例 |
|------|------|----------|
| stdio | 命令行子进程 | `{"type": "stdio", "command": "npx", "args": [...]}` |
| sse | Server-Sent Events | `{"type": "sse", "url": "http://..."}` |
| http | HTTP 请求 | `{"type": "http", "url": "https://..."}` |

**OAuth 支持**: HTTP/SSE 传输支持 OAuth 令牌流程（`client_credentials`、`refresh_token`），自动刷新和注入 Authorization 头。

**懒加载设计**:
```python
def get_cached_mcp_tools():
    """MCP 工具懒加载 + 缓存失效"""
    global _cached_tools, _cached_mtime
    
    current_mtime = os.path.getmtime(config_path)
    if _cached_mtime is None or current_mtime > _cached_mtime:
        # 配置文件变更，重新加载
        _cached_tools = _load_mcp_tools()
        _cached_mtime = current_mtime
    
    return _cached_tools
```

### 3.8 工具系统（Tool System）

**文件位置**: `backend/packages/harness/deerflow/tools/`

**工具组装函数**: `get_available_tools()`

```python
def get_available_tools(groups=None, include_mcp=True, model_name=None, subagent_enabled=False):
    """组装可用工具列表"""
    tools = []
    
    # 1. 配置定义的工具
    tools.extend(_load_config_tools(groups))
    
    # 2. MCP 工具（懒加载）
    if include_mcp:
        tools.extend(get_cached_mcp_tools())
    
    # 3. 内置工具
    tools.extend([
        present_files,      # 展示产出文件
        ask_clarification,  # 请求澄清
        view_image,         # 查看图像（视觉模型）
    ])
    
    # 4. 子代理工具
    if subagent_enabled:
        tools.append(task)  # 委托任务
    
    return tools
```

**社区工具集**:
- **Tavily**: 网络搜索（默认5条结果）
- **Jina AI**: 网页内容提取（4KB限制）
- **Firecrawl**: 网页爬取
- **DuckDuckGo**: 图片搜索

### 3.9 配置系统（Configuration System）

**双文件配置架构**:

| 文件 | 用途 | 格式 |
|------|------|------|
| `config.yaml` | 主配置（模型、沙箱、工具组、记忆等） | YAML |
| `extensions_config.json` | 扩展配置（MCP服务器、技能状态） | JSON |

**环境变量解析**: 配置值以 `$` 开头时自动解析为环境变量
```yaml
models:
  - name: gpt-4
    api_key: $OPENAI_API_KEY  # 从环境变量读取
```

**配置版本控制**:
```python
# config.example.yaml 维护 config_version
# 启动时比较用户配置与示例配置版本
if user_version < example_version:
    logger.warning("配置已过期，请运行 make config-upgrade")
```

**热重载机制**:
```python
_config_cache = None
_last_mtime = 0

def get_app_config():
    global _config_cache, _last_mtime
    path = resolve_config_path()
    mtime = os.path.getmtime(path)
    
    if mtime > _last_mtime:
        _config_cache = AppConfig.from_file(path)
        _last_mtime = mtime
    
    return _config_cache
```

---

## 四、关键设计模式

### 4.1 中间件模式（Middleware Pattern）

DeerFlow 的中间件链是其核心架构模式，灵感来自 Web 框架的中间件设计：

```python
class AgentMiddleware(ABC, Generic[T]):
    """中间件基类"""
    
    def before_agent(self, state: T, runtime: Runtime) -> dict | None:
        """Agent 执行前调用"""
        return None
    
    def after_agent(self, state: T, runtime: Runtime) -> dict | None:
        """Agent 执行后调用"""
        return None
```

**优势**:
- 关注点分离（Separation of Concerns）
- 可插拔架构（中间件可动态启用/禁用）
- 统一的横切关注点处理（日志、权限、缓存等）

### 4.2 Provider 模式（Provider Pattern）

沙箱和模型系统使用 Provider 模式实现可替换的后端：

```python
class SandboxProvider(ABC):
    """沙箱提供者接口"""
    @abstractmethod
    async def acquire(self) -> Sandbox: ...
    
    @abstractmethod
    async def release(self, sandbox: Sandbox) -> None: ...

# 不同实现
class LocalSandboxProvider(SandboxProvider): ...
class AioSandboxProvider(SandboxProvider): ...  # Docker
```

### 4.3 反射解析器（Reflection Resolver）

动态加载配置中指定的类和变量：

```python
# config.yaml
models:
  - use: langchain_openai:ChatOpenAI  # 模块路径:类名

# 解析代码
from deerflow.reflection import resolve_class

model_class = resolve_class("langchain_openai:ChatOpenAI", BaseChatModel)
model = model_class(**config)
```

### 4.4 状态归约器（State Reducer）

LangGraph 使用 Reducer 函数处理并发状态更新：

```python
def merge_artifacts(existing: list | None, new: list | None) -> list:
    """合并并去重产出物列表"""
    if existing is None:
        return new or []
    if new is None:
        return existing
    # 使用 dict.fromkeys 去重同时保持顺序
    return list(dict.fromkeys(existing + new))
```

---

## 五、代码质量与工程实践

### 5.1 测试覆盖

| 测试类别 | 文件数 | 说明 |
|----------|--------|------|
| 单元测试 | 45+ | 覆盖核心模块 |
| 边界测试 | test_harness_boundary.py | 确保分层边界 |
| 回归测试 | test_docker_sandbox_mode_detection.py | Docker 沙箱模式检测 |
| 集成测试 | test_client_live.py | 实时客户端测试 |

**TDD 强制要求**: "Every new feature or bug fix MUST be accompanied by unit tests. No exceptions."

### 5.2 代码规范

- **Linter/Formatter**: ruff
- **行长度**: 240 字符
- **Python 版本**: 3.12+
- **类型提示**: 全类型注解
- **引号**: 双引号
- **缩进**: 4 空格

### 5.3 文档驱动

**CLAUDE.md 强制更新政策**:
> "CRITICAL: Always update README.md and CLAUDE.md after every code change"

每处代码变更必须同步更新：
- `README.md`: 用户面向的变更
- `CLAUDE.md`: 开发面向的变更

---

## 六、性能与扩展性

### 6.1 并发设计

| 组件 | 并发策略 | 限制 |
|------|----------|------|
| 子代理调度 | 线程池 (3 workers) | 无阻塞 |
| 子代理执行 | 线程池 (3 workers) | 最大3并发 |
| 记忆更新 | 后台线程 | 防抖30秒 |
| MCP 工具 | 异步 IO | 连接池 |

### 6.2 资源管理

**线程池隔离**: 调度与执行分离，避免相互阻塞

**超时控制**:
- 子代理: 15 分钟
- 工具调用: 根据工具配置

**缓存策略**:
- MCP 工具: mtime 检测热重载
- 记忆数据: 内存缓存 + 文件监听
- 应用配置: mtime 检测热重载

### 6.3 扩展性设计

**技能系统**:
```
skills/
├── public/          # 公共技能（版本控制）
│   ├── research/
│   ├── data-analysis/
│   └── ...
└── custom/          # 自定义技能（gitignored）
```

**MCP 扩展**: 通过 `extensions_config.json` 动态添加 MCP 服务器

**自定义代理**: 支持通过配置创建专用代理

---

## 七、安全设计

### 7.1 沙箱隔离

- **文件系统隔离**: 每个线程独立的目录
- **执行环境隔离**: Docker 容器隔离（可选）
- **路径白名单**: 虚拟路径系统限制访问范围

### 7.2 工具调用权限

**GuardrailMiddleware**: 可插拔的权限控制

```python
class GuardrailProvider(ABC):
    """权限控制提供者接口"""
    @abstractmethod
    async def evaluate(self, tool_call: ToolCall) -> GuardrailResult: ...
```

内置实现:
- **AllowlistProvider**: 零依赖白名单
- **OAP Providers**: 外部策略服务
- **Custom Providers**: 自定义实现

### 7.3 配置安全

- API 密钥通过环境变量注入
- 配置文件支持 `$ENV_VAR` 语法
- `.env` 文件支持（dotenv）

---

## 八、总结与评价

### 8.1 架构优点

1. **清晰的分层**: Harness/App 分离确保框架代码的纯粹性
2. **可扩展的中间件**: 12 个中间件覆盖所有横切关注点
3. **完整的沙箱**: 真正的执行环境而不仅是工具调用
4. **持久化记忆**: 跨会话的上下文保持，非临时记忆
5. **子代理系统**: 真正的任务分解和并行执行
6. **MCP 生态**: 开放协议支持无限扩展

### 8.2 代码亮点

1. **严格的类型系统**: 全类型注解，Pydantic 模型验证
2. **完善的测试**: 45+ 测试文件，CI 强制执行边界检查
3. **文档同步**: 代码与文档强制同步更新
4. **错误处理**: 优雅的错误转换和日志追踪
5. **并发安全**: 线程锁、原子操作、超时控制

### 8.3 适用场景

- **深度研究**: 多步骤信息收集和综合分析
- **代码生成**: 创建完整项目而不仅是代码片段
- **数据处理**: 复杂的数据管道和分析任务
- **内容创作**: 报告、PPT、网页、多媒体生成
- **自动化工作流**: 与 IM 平台集成的持续对话

### 8.4 学习价值

DeerFlow 是一个优秀的**企业级 AI Agent 架构参考**：
- 展示了如何将 LLM 从"聊天机器人"转变为"执行引擎"
- 提供了完整的 Agent 基础设施设计范式
- 演示了 LangGraph/LangChain 在大规模应用中的最佳实践
- 体现了字节跳动在 AI 工程化方面的深厚积累

---

## 附录：关键文件索引

| 组件 | 文件路径 | 说明 |
|------|----------|------|
| Lead Agent | `backend/packages/harness/deerflow/agents/lead_agent/agent.py` | 主代理工厂 |
| ThreadState | `backend/packages/harness/deerflow/agents/thread_state.py` | 状态定义 |
| Memory | `backend/packages/harness/deerflow/agents/memory/` | 记忆系统目录 |
| Sandbox | `backend/packages/harness/deerflow/sandbox/` | 沙箱系统目录 |
| Subagent | `backend/packages/harness/deerflow/subagents/executor.py` | 子代理执行器 |
| MCP | `backend/packages/harness/deerflow/mcp/client.py` | MCP 客户端 |
| Config | `backend/packages/harness/deerflow/config/app_config.py` | 配置系统 |
| Gateway | `backend/app/gateway/` | FastAPI Gateway |
| Channels | `backend/app/channels/` | IM 通道集成 |

---

*报告完*
