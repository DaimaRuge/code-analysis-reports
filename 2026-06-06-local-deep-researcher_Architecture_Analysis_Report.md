# LangChain Local Deep Researcher 技术架构与源码研读报告

> **生成日期**: 2026-06-06  
> **分析版本**: v0.0.1 (main分支, 提交: 2026-04-21)  
> **仓库**: https://github.com/langchain-ai/local-deep-researcher  
> **Stars**: 9,206 | **Forks**: 963 | **License**: MIT

---

## 一、项目概述与定位

Local Deep Researcher 是一个**完全本地化的网络研究与报告写作助手**，由 LangChain 官方团队开发。它的核心愿景是让任何开发者都能在自己的机器上运行一个具备深度研究能力的 AI 智能体，而无需依赖云端 API（除可选的搜索服务外）。

**灵感来源**: 基于 [IterDRAG](https://arxiv.org/html/2410.04343v1) 论文的迭代式检索增强生成思想。IterDRAG 的核心是将复杂查询分解为子查询，逐个检索文档、回答子查询，然后基于第二个子查询的检索结果继续构建答案。本项目将其转化为可执行的 LangGraph 工作流。

**核心能力**：
- 接受用户研究主题 → 生成搜索查询 → 执行网络搜索 → 总结搜索结果 → 反思知识缺口 → 生成新的搜索查询 → 循环迭代 → 输出最终研究报告

---

## 二、系统架构全景图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        用户交互层 (LangGraph Studio)                 │
│                      https://smith.langchain.com/studio              │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       LangGraph 状态图引擎                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ START        │──│generate_query│──│ web_research │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                              │                     │
│                    ┌─────────────────────────┘                     │
│                    ▼                                               │
│         ┌──────────────┐  ┌──────────────────┐  ┌──────────┐     │
│  ┌──────│summarize_srcs│──│ reflect_on_summary │──│ 条件路由 │     │
│  │      └──────────────┘  └──────────────────┘  └────┬─────┘     │
│  │                              ▲                     │            │
│  │                              │  loop_count ≤ max  │ no         │
│  │                              └────────────────────┘            │
│  │                              yes                                │
│  ▼                                                                 │
│ ┌──────────────┐                                                   │
│ │finalize_summary│─────────────────────────────────────── END     │
│ └──────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         基础设施层                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  Ollama  │  │ LMStudio │  │  Tavily  │  │DuckDuckGo│          │
│  │  (LLM)   │  │  (LLM)   │  │(Search) │  │(Search)  │          │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘          │
│  ┌──────────┐  ┌──────────┐                                        │
│  │Perplexity│  │ SearXNG  │  ← 可选的搜索服务提供商                 │
│  │(Search)  │  │(Search)  │                                        │
│  └──────────┘  └──────────┘                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心架构设计

### 3.1 状态图 (StateGraph) 工作流设计

本项目是 **LangGraph 架构范式的典范实现**。整个研究流程被建模为一个有向状态图，每个节点都是一个纯函数，状态通过 `SummaryState` dataclass 传递。

```python
# 状态图构建 (graph.py)
builder = StateGraph(
    SummaryState,
    input=SummaryStateInput,
    output=SummaryStateOutput,
    config_schema=Configuration,
)
builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("summarize_sources", summarize_sources)
builder.add_node("reflect_on_summary", reflect_on_summary)
builder.add_node("finalize_summary", finalize_summary)

builder.add_edge(START, "generate_query")
builder.add_edge("generate_query", "web_research")
builder.add_edge("web_research", "summarize_sources")
builder.add_edge("summarize_sources", "reflect_on_summary")
builder.add_conditional_edges("reflect_on_summary", route_research)
builder.add_edge("finalize_summary", END)

graph = builder.compile()
```

**关键设计决策**:
- **输入/输出/状态分离**: `SummaryStateInput` 只包含 `research_topic`，`SummaryStateOutput` 只包含 `running_summary`，而 `SummaryState` 包含完整中间状态。这实现了清晰的数据契约。
- **条件路由**: `route_research` 函数基于 `research_loop_count` 和 `max_web_research_loops` 决定是继续研究还是终止。这是实现**迭代循环**的核心机制。

### 3.2 状态管理 (Accumulator Pattern)

```python
@dataclass(kw_only=True)
class SummaryState:
    research_topic: str
    search_query: str
    web_research_results: Annotated[list, operator.add]  # 累加器模式!
    sources_gathered: Annotated[list, operator.add]      # 累加器模式!
    research_loop_count: int
    running_summary: str
```

**累加器模式 (Accumulator Pattern)** 是本架构的精髓：
- `Annotated[list, operator.add]` 告诉 LangGraph 当节点返回列表时，不要替换而是**追加**到现有列表中。
- 这意味着每次 `web_research` 节点的结果都会累积到 `web_research_results` 中，每次搜索的源都会累积到 `sources_gathered` 中。
- 这种设计天然支持迭代式研究：每一轮的新发现都叠加到已有发现之上。

### 3.3 配置系统 (三级配置优先级)

```python
class Configuration(BaseModel):
    max_web_research_loops: int = 3
    local_llm: str = "llama3.2"
    llm_provider: Literal["ollama", "lmstudio"] = "ollama"
    search_api: Literal["perplexity", "tavily", "duckduckgo", "searxng"] = "duckduckgo"
    # ... 其他字段

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None):
        # 优先级: 环境变量 > LangGraph UI配置 > 默认值
        raw_values = {
            name: os.environ.get(name.upper(), configurable.get(name))
            for name in cls.model_fields.keys()
        }
```

**配置优先级** (从高到低):
1. **环境变量** (`.env` 文件): `MAX_WEB_RESEARCH_LOOPS=5`
2. **LangGraph UI 配置**: 用户在 Studio 界面中调整的参数
3. **代码默认值**: `Configuration` 类中的 `Field(default=...)`

**设计优点**:
- 使用 Pydantic 进行类型校验，配置错误在启动时就能发现
- 使用 `Literal` 类型限制 LLM 提供商和搜索 API 的取值范围，防止配置错误
- 统一的 `from_runnable_config` 工厂方法确保所有节点以相同方式获取配置

---

## 四、核心模块详解

### 4.1 查询生成节点 (generate_query)

**职责**: 将研究主题转化为优化的搜索查询。

**架构亮点**:
- **双重结构化输出策略**: 支持 JSON mode 和 Tool calling 两种模式，通过 `generate_search_query_with_structured_output` 统一抽象。
- **Prompt 工程**: 使用 `query_writer_instructions` 模板，包含当前日期、研究主题、示例输出格式，以及 JSON mode / Tool calling 的格式指令。

```python
# 统一的结构化输出辅助函数
def generate_search_query_with_structured_output(configurable, messages, tool_class, 
                                                  fallback_query, tool_query_field, json_query_field):
    if configurable.use_tool_calling:
        llm = get_llm(configurable).bind_tools([tool_class])
        # 解析 tool_call 结果...
    else:
        llm = get_llm(configurable)  # JSON mode (format="json")
        # 解析 JSON 结果...
```

**容错设计**: 如果 JSON 解析失败或 Tool calling 没有返回结果，使用 fallback query（`f"Tell me more about {topic}"`）。这确保即使在模型输出格式异常时，系统也能继续运行。

### 4.2 网络研究节点 (web_research)

**职责**: 执行实际的网络搜索。

**策略模式 (Strategy Pattern)**: 通过 `search_api` 配置选择不同的搜索后端：

| 搜索 API | 特点 | 是否需要 API Key |
|---------|------|----------------|
| DuckDuckGo | 免费，无需认证，默认选择 | 否 |
| Tavily | 高质量 AI 搜索，支持 raw_content | 是 |
| Perplexity | 强大的 sonar-pro 模型，自带引用 | 是 |
| SearXNG | 自托管，隐私友好 | 否（需自托管） |

**统一接口设计**: 所有搜索函数返回相同的格式：`{"results": [{"title": ..., "url": ..., "content": ..., "raw_content": ...}]}`

**Traceability**: 使用 `@traceable` 装饰器（LangSmith），所有搜索调用都会被追踪和记录，便于调试和优化。

### 4.3 总结节点 (summarize_sources)

**职责**: 将最新的搜索结果整合到现有总结中。

**增量式总结策略**:
- 如果已有 `running_summary`，则提示模型"更新现有总结"
- 如果这是第一次，则提示模型"创建新总结"
- 使用 XML 标签（`<Existing Summary>`、`<New Context>`）帮助模型区分已有内容和新内容

**关键提示词设计**:
```python
# 增量更新提示
"Update the Existing Summary with the New Context on this topic"

# 要求
"If it's related to existing points, integrate it into the relevant paragraph"
"If it's entirely new but relevant, add a new paragraph with a smooth transition"
"If it's not relevant to the user topic, skip it"
```

### 4.4 反思节点 (reflect_on_summary)

**职责**: 分析当前总结，识别知识缺口，生成后续搜索查询。

这是**实现深度研究的关键节点**。它让系统能够自我评估，主动发现需要更多信息的地方，而不是盲目执行固定次数的搜索。

**反思 Prompt 设计**:
```
1. Identify knowledge gaps or areas that need deeper exploration
2. Generate a follow-up question that would help expand your understanding
3. Focus on technical details, implementation specifics, or emerging trends
```

### 4.5 路由决策 (route_research)

```python
def route_research(state, config) -> Literal["finalize_summary", "web_research"]:
    if state.research_loop_count <= configurable.max_web_research_loops:
        return "web_research"  # 继续循环
    else:
        return "finalize_summary"  # 终止循环
```

注意：条件使用 `<=` 而不是 `<`，这意味着如果 `max_web_research_loops=3`，系统会执行 4 轮研究（loop_count 0→1→2→3）。

---

## 五、设计模式与架构原则

### 5.1 设计模式汇总

| 模式 | 应用位置 | 目的 |
|------|---------|------|
| **状态模式 (State Pattern)** | `StateGraph` | 管理研究流程的状态转换 |
| **累加器模式 (Accumulator)** | `Annotated[list, operator.add]` | 累积多轮搜索结果 |
| **策略模式 (Strategy Pattern)** | `search_api` / `llm_provider` | 切换搜索后端和 LLM 提供商 |
| **工厂模式 (Factory Pattern)** | `get_llm()` | 根据配置创建 LLM 实例 |
| **模板方法模式 (Template Method)** | `generate_search_query_with_structured_output` | 统一 JSON/Tool 调用流程 |
| **依赖注入 (Dependency Injection)** | `RunnableConfig` | 将配置注入到节点函数 |

### 5.2 架构原则

**1. 单一职责原则 (SRP)**
每个节点只做一件事：
- `generate_query`: 只生成查询
- `web_research`: 只执行搜索
- `summarize_sources`: 只更新总结
- `reflect_on_summary`: 只生成反思和后续查询

**2. 开闭原则 (OCP)**
- 添加新的搜索后端：只需在 `utils.py` 添加新函数并在 `web_research` 节点添加分支
- 添加新的 LLM 提供商：只需在 `get_llm()` 添加新分支和对应的 Chat 类
- 不需要修改现有代码的核心逻辑

**3. 可观测性内建 (Observability by Design)**
- `@traceable` 装饰器：所有搜索调用自动追踪
- LangSmith 集成：完整的研究流程可视化
- 详细的 `print()` 日志：JSON 解析失败、搜索错误等关键事件都有日志

---

## 六、依赖管理与部署架构

### 6.1 依赖树

```
ollama-deep-researcher
├── langgraph >= 1.1.0          # 状态图引擎
├── langchain-community >= 0.4.0 # 社区工具 (SearXNG)
├── tavily-python >= 0.7.23     # Tavily 搜索
├── langchain-ollama >= 1.0.0   # Ollama 集成
├── duckduckgo-search >= 7.3.0 # DuckDuckGo 搜索
├── langchain-openai >= 1.1.14  # OpenAI 兼容 API (LMStudio)
├── openai >= 2.31.0            # OpenAI 客户端
├── httpx >= 0.28.1             # HTTP 客户端 (全文抓取)
├── markdownify >= 0.11.0       # HTML → Markdown 转换
└── python-dotenv == 1.2.2      # 环境变量加载
```

### 6.2 部署选项

| 方式 | 适用场景 | 命令 |
|------|---------|------|
| **本地开发** | 开发调试 | `uvx --from "langgraph-cli[inmem]" langgraph dev` |
| **Docker** | 生产部署 | `docker build -t local-deep-researcher . && docker run -p 2024:2024 ...` |
| **LangGraph Cloud** | 托管部署 | 参见 Module 6 of LangChain Academy |

### 6.3 Docker 架构

```dockerfile
FROM python:3.11-slim
# 安装系统依赖 + uv 包管理器
# 复制代码
# 默认暴露 2024 端口 (LangGraph dev server)
# CMD: uvx --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --host 0.0.0.0
```

**注意**: Docker 镜像**不包含 Ollama**，需要单独运行 Ollama 服务并配置 `OLLAMA_BASE_URL` 指向外部服务。

---

## 七、代码质量与工程实践

### 7.1 代码规范

- **Ruff**: 使用 `E, F, I, D, D401, T201, UP` 规则集，Google 风格 docstring 约定
- **类型提示**: 全面使用类型提示，包括 `Literal`, `Annotated`, `Optional`, `Union`
- **Pydantic**: 配置和数据模型使用 Pydantic 进行校验

### 7.2 文档质量

每个函数都有完整的 Google 风格 docstring，包含：
- 功能描述
- 参数说明（类型、含义、默认值）
- 返回值说明
- 示例（`utils.py` 中的 `get_config_value` 甚至包含 doctests）
- 异常说明

### 7.3 错误处理

- **搜索失败**: 返回空结果 `{"results": []}` 而不是抛异常，让研究流程继续
- **JSON 解析失败**: 使用 fallback query，并打印原始响应供调试
- **HTTP 请求**: 使用 `httpx` 的 10 秒超时，避免挂起
- **全文抓取**: 失败时返回 `None` 并打印警告，不影响主流程

---

## 八、扩展性分析

### 8.1 如何添加新的搜索后端

1. 在 `utils.py` 添加新的搜索函数（遵循统一返回格式）
2. 在 `SearchAPI` enum 添加新值
3. 在 `web_research` 节点添加 elif 分支
4. 在 `Configuration` 的 `search_api` 字段更新 Literal 类型

**示例**: 添加 Bing Search 支持，预计修改 3 个文件，约 20 行代码。

### 8.2 如何添加新的 LLM 提供商

1. 创建新的 Chat 类（继承 `ChatOpenAI` 或实现 `BaseChatModel`）
2. 在 `get_llm()` 添加分支
3. 在 `Configuration` 的 `llm_provider` 字段更新 Literal 类型

### 8.3 如何修改研究流程

- 添加新节点：定义新函数 → `builder.add_node()` → 在适当位置添加边
- 修改循环条件：调整 `route_research` 函数或添加新的状态判断
- 并行搜索：修改 `web_research` 节点同时调用多个搜索 API，然后合并结果

---

## 九、源码研读心得

### 9.1 架构亮点

1. **LangGraph 的优雅**: 整个复杂的研究流程被简洁地表达为 5 个节点和几条边。状态图的可视化能力让非技术人员也能理解系统逻辑。

2. **本地优先的设计哲学**: 默认使用 DuckDuckGo（无需 API Key）和 Ollama（本地运行），让用户零成本启动。付费服务（Tavily, Perplexity）作为可选增强。

3. **结构化输出的双重保障**: 同时支持 JSON mode 和 Tool calling，并处理模型不兼容的情况（如 `gpt-oss` 不支持 JSON mode）。

4. **迭代式研究的智能**: 不是简单的"搜索 N 次"，而是每次搜索后都有反思步骤，主动发现知识缺口。这模拟了人类研究员的工作方式。

### 9.2 改进建议

1. **并行搜索**: 当前搜索是串行的，如果配置多个搜索 API，可以并行执行然后合并结果。

2. **源质量控制**: 当前没有对源的权威性进行评估（如域名可信度），容易引入低质量信息。

3. **总结长度控制**: 随着循环次数增加，总结会越来越长，可能超出 LLM 上下文窗口。需要添加总结压缩机制。

4. **测试覆盖**: 当前没有看到测试文件，建议为核心节点（特别是搜索和格式化逻辑）添加单元测试。

5. **流式输出**: 最终总结目前是整块返回，可以改为流式输出，提升用户体验。

---

## 十、总结

Local Deep Researcher 是 **LangGraph 架构范式的教科书级示例**。它展示了如何：
- 用状态图建模复杂的工作流程
- 用累加器模式处理迭代式数据积累
- 用策略模式实现多后端切换
- 用三级配置系统实现灵活部署
- 在保持代码简洁的同时实现深度研究能力

对于希望构建基于 LLM 的自动化工作流的开发者，这是一个极佳的参考实现。其代码量（约 700 行 Python）与功能复杂度（迭代式研究、多后端支持、结构化输出）的比例展现了优秀的架构设计能力。

---

*报告生成时间: 2026-06-06 03:00 CST*  
*分析工具: OpenClaw AI Agent*  
*数据来源: GitHub API + 源码静态分析*
