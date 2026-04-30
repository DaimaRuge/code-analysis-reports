# MetaGPT 技术架构与源码研读报告

> 分析日期：2026-04-30 | 项目：FoundationAgents/MetaGPT | ⭐ 66,673 Stars | Python

---

## 一、项目概述

### 1.1 什么是 MetaGPT

MetaGPT 是一个**多智能体框架**，其核心理念是**"Code = SOP(Team)"** —— 将软件公司的标准操作流程（SOP）形式化，并将其应用于由 LLM 驱动的智能体团队中。

MetaGPT 输入**一行需求描述**，输出**完整的软件产品**：包括用户故事、竞品分析、需求文档、数据结构、API 设计、代码、测试文档等。其内部模拟了一个包含产品经理、架构师、工程师、测试工程师等多种角色的虚拟软件公司。

### 1.2 核心数据

| 指标 | 数值 |
|------|------|
| GitHub Stars | 66,673 |
| 语言 | Python (3.9-3.11) |
| 协议 | MIT |
| 主要特性 | 多智能体协作、SOP 驱动、角色扮演、代码生成 |
| 学术引用 | ICLR 2025 Oral (AFlow) |

### 1.3 核心哲学

```
Code = SOP(Team)
```

MetaGPT 认为：代码是团队执行 SOP 的产物。将 SOP 形式化并应用于 LLM 智能体团队，就能让 AI 自动生成完整的软件系统。

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                     Team (团队层)                      │
│   负责管理角色招聘、预算管理、项目启动、异步运行          │
└──────────────────────┬────────────────────────────────┘
                       │ 持有 Environment
                       ▼
┌─────────────────────────────────────────────────────────┐
│            Environment (环境层)                         │
│   消息中枢：.publish_message / .add_roles / .run()     │
│   子类：MGXEnv / SoftwareEnv / WerewolfEnv 等          │
└──────────────────────┬────────────────────────────────┘
                       │ 持有多个 Role
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   Role (角色层)                         │
│   ProductManager / Architect / Engineer / QA 等         │
│   状态机驱动：_think() → _act() 循环                    │
│   消息订阅：watch() 决定接收哪些消息                    │
└──────────────────────┬────────────────────────────────┘
                       │ 执行 Action
                       ▼
┌─────────────────────────────────────────────────────────┐
│                 Action (动作层)                        │
│   WritePRD / WriteCode / WriteTest / DebugError 等      │
│   基于 ActionNode：结构化 LLM 输出解析                    │
└──────────────────────┬────────────────────────────────┘
                       │ 调用 LLM / Tools
                       ▼
┌─────────────────────────────────────────────────────────┐
│          Provider / Tools (基础设施层)                   │
│   OpenAI / Gemini / Anthropic / Ollama 等 LLM           │
│   Browser / Editor / SearchEngine / Translator 等工具    │
└─────────────────────────────────────────────────────────┘
```

### 2.2 核心模块说明

#### Team（团队层）

`Team` 类是整个多智能体系统的入口，负责：
- **hire()** — 将 Role 实例加入团队
- **invest()** — 设置预算上限
- **run_project()** — 接收用户需求并发布初始消息
- **run()** — 异步执行多轮协作直到预算耗尽或轮次用尽

团队内部维护一个 `Environment` 实例，所有消息通过环境进行广播和传递。

```python
class Team(BaseModel):
    env: Optional[Environment] = None
    investment: float = Field(default=10.0)
    idea: str = Field(default="")
    use_mgx: bool = Field(default=True)  # 默认使用 MGX 环境

    async def run(self, n_round=3, idea="", ...):
        while n_round > 0:
            if self.env.is_idle: break
            n_round -= 1
            self._check_balance()
            await self.env.run()
```

#### Environment（环境层）

`Environment` 是多智能体协作的消息中枢，角色之间不直接通信，而是通过环境进行间接通信（发布-订阅模式）。

```python
class Environment(BaseEnvironment):
    # 消息发布：角色调用此方法向环境发送消息
    def publish_message(self, message: Message):
        ...
    
    # 环境运行一轮：让所有活跃角色执行动作
    async def run(self):
        ...
```

#### Role（角色层）

`Role` 是智能体的抽象基类。每个角色拥有：
- **profile** — 角色描述（"Product Manager"）
- **goal** — 角色目标
- **constraints** — 约束条件
- **tools** — 角色可使用的工具列表
- **todo_action** — 当前待执行的动作

角色的核心循环：

```python
# 角色状态机循环
async def run(self):
    while self._is_active():
        await self._observe()     # 1. 观察：读取消息缓冲
        await self._think()       # 2. 思考：决定下一步做什么
        await self._act()         # 3. 执行：执行动作并发布消息
```

**Reaction Mode**（反应模式）控制角色如何选择下一步动作：
- `REACT` — 基于 ReAct 模式（推理+行动）
- `BY_ORDER` — 按固定顺序执行（用于 SOP 流程）
- `PLAN_AND_ACT` — 先计划再执行

```python
class RoleReactMode(str, Enum):
    REACT = "react"
    BY_ORDER = "by_order"
    PLAN_AND_ACT = "plan_and_act"
```

#### Action（动作层）

`Action` 是具体任务的执行单元。每个动作定义了一个明确的目标和执行逻辑。

```python
class Action(SerializationMixin, ContextMixin, BaseModel):
    name: str = ""
    prefix: str = ""       # 附加到 LLM 调用的前缀提示
    desc: str = ""         # 动作描述（供技能管理器使用）
    node: ActionNode = None # 结构化输出节点
    llm_name_or_type: Optional[str] = None  # 指定使用的 LLM
```

动作通过 `ActionNode` 实现结构化输出：

```python
class ActionNode(BaseModel):
    """一个 ActionNode 代表 LLM 输出中的一个结构化字段"""
    instruction: str       # 给 LLM 的指令
    expected_type: Type    # 期望的类型
    schema: str            # JSON Schema 描述
```

#### RoleContext（角色运行时上下文）

每个 Role 在运行时持有一个 `RoleContext`，管理该角色的所有运行时状态：

```python
class RoleContext(BaseModel):
    env: BaseEnvironment       # 环境引用
    msg_buffer: MessageQueue   # 消息缓冲（异步更新）
    memory: Memory             # 短期记忆
    working_memory: Memory      # 工作内存
    state: int                 # 当前状态（状态机）
    todo: Action               # 当前待执行动作
    watch: set[str]            # 订阅的消息标签
    react_mode: RoleReactMode   # 反应模式
    max_react_loop: int         # 最大循环次数
```

---

## 三、核心设计模式

### 3.1 多角色协作模式

MetaGPT 模拟了一个完整的软件公司角色体系：

| 角色 | 主要动作 | 职责 |
|------|----------|------|
| `ProductManager` | WritePRD, PrepareDocuments | 需求分析、市场调研、竞品分析 |
| `Architect` | DesignAPI, WriteDesign | 技术架构设计、API 设计 |
| `Engineer` | WriteCode, RunCode, DebugError | 代码编写与执行 |
| `ProjectManager` | ProjectManagement | 项目进度管理 |
| `QAEngineer` | WriteTest | 测试用例生成与质量保障 |
| `DataAnalyst` | SearchAndSummarize | 数据分析与研究 |

角色的配置通过 YAML/提示词模板实现：

```python
class ProductManager(RoleZero):
    name: str = "Alice"
    profile: str = "Product Manager"
    goal: str = "Create a Product Requirement Document..."
    constraints: str = "utilize the same language as the user"
    instruction: str = PRODUCT_MANAGER_INSTRUCTION  # 详细提示词模板
    tools: list[str] = ["RoleZero", Browser.__name__, Editor.__name__, SearchEnhancedQA.__name__]
    todo_action: str = any_to_name(WritePRD)
```

### 3.2 ActionNode 结构化输出模式

MetaGPT 使用 `ActionNode` 实现 LLM 输出的结构化解析。不同于普通的文本输出，ActionNode 定义了每个字段的预期类型和解析指令：

```python
# 示例：WritePRD 中的 ActionNode 定义
class WritePRDActionNode:
    name: ActionNode
    language: ActionNode
    project_type: ActionNode
    core_functionality: ActionNode
    target_users: ActionNode
    # ...
```

这种设计确保 LLM 输出可以安全地被解析为 Pydantic 模型，避免了 JSON 解析的不稳定性。

### 3.3 消息订阅机制

角色通过 `watch` 属性订阅感兴趣的消息类型：

```python
class ProductManager(RoleZero):
    def __init__(self, **kwargs):
        # 订阅 UserRequirement 和 PrepareDocuments 消息
        self._watch([UserRequirement, PrepareDocuments])
```

当环境中有新消息时，只有订阅了该消息类型的角色才会将其加入消息缓冲。

### 3.4 SOP（标准操作流程）

MetaGPT 的核心创新是将软件公司的 SOP 形式化并应用到多智能体系统。以产品开发流程为例：

```
用户输入需求
    ↓
ProductManager 撰写 PRD
    ↓
Architect 进行技术设计
    ↓
Engineer 编写代码
    ↓
QAEngineer 编写测试
    ↓
ProjectManager 跟踪进度
```

每个角色按照预设的顺序执行特定动作，确保最终产出的软件具有一致的质量和结构。

---

## 四、关键源码解析

### 4.1 Role._think() 状态机

`Role._think()` 方法决定角色当前应该处于哪个状态：

```python
STATE_TEMPLATE = """Here are your conversation records...
Your previous stage: {previous_state}
Now choose one of the following stages you need to go to:
{states}
Just answer a number between 0-{n_states}...
"""

async def _think(self) -> bool:
    if self.rc.todo is None:
        return False  # 无法继续推理
    prompt = STATE_TEMPLATE.format(
        history=self.rc.memory.get(),
        previous_state=self.rc.state,
        states=self.rc.states,
        n_states=len(self.rc.states) - 1
    )
    # 调用 LLM 选择下一个状态
    rsp = await self.llm.aask(prompt)
    self.rc.state = extract_state_value(rsp)
    return True
```

### 4.2 ActionNode 的 LLM 调用与解析

```python
class ActionNode:
    async def fill(self, context, llm):
        prompt = self.instruction.format(context=context)
        rsp = await llm.aask(prompt)
        # 从 LLM 输出中解析结构化结果
        json_str = extract_content_between_tags(rsp, TAG)
        return self.expected_type.model_validate_json(json_str)
```

### 4.3 Memory 消息存储

```python
class Memory(BaseModel):
    storage: list[SerializeAsAny[Message]] = []
    index: DefaultDict[str, list[Message]] = Field(default_factory=lambda: defaultdict(list))
    
    def add(self, message: Message):
        self.storage.append(message)
        if message.cause_by:
            self.index[message.cause_by].append(message)
    
    def get_by_role(self, role: str) -> list[Message]:
        return [msg for msg in self.storage if msg.role == role]
    
    def try_remember(self, keyword: str) -> list[Message]:
        return [msg for msg in self.storage if keyword in msg.content]
```

### 4.4 Team.run() 异步多轮执行

```python
async def run(self, n_round=3, idea="", ...):
    if idea:
        self.run_project(idea=idea)
    
    while n_round > 0:
        if self.env.is_idle:  # 所有角色空闲则退出
            break
        n_round -= 1
        self._check_balance()  # 检查预算
        await self.env.run()   # 执行一轮
    self.env.archive(auto_archive)
    return self.env.history
```

---

## 五、工具系统

### 5.1 工具注册与执行

MetaGPT 使用 `@register_tool` 装饰器注册工具：

```python
@register_tool(
    tags=["web", "browse"],
    include_functions=["click", "goto", "hover", ...]
)
class Browser:
    async def goto(self, url: str): ...
    async def click(self, selector: str): ...
    async def type_text(self, selector: str, text: str): ...
```

工具通过 `ToolRegistry` 统一管理，角色通过 `tool_execution_map` 动态调用。

### 5.2 核心工具

| 工具 | 用途 |
|------|------|
| `Browser` | 网页浏览、自动化操作 |
| `Editor` | 文件创建、编辑、代码修改 |
| `SearchEnhancedQA` | 互联网搜索与信息检索 |
| `RunCommand` | 执行命令行指令 |
| `Translator` | 多语言翻译 |
| `TextToImage` | 图像生成（DALL-E/SD） |

---

## 六、配置系统

MetaGPT 使用分层配置管理：

```python
# config2.yaml 配置示例
llm:
  api_type: "openai"
  model: "gpt-4"
  
browser:
  driver: "playwright"  # 或 selenium

search:
  engine: "googleapi"   # 或 bing/serper/ddg
```

配置文件通过 `metagpt config2.yaml` 初始化，支持多 LLM 提供商（OpenAI/Gemini/Claude/Ollama 等）。

---

## 七、Memory 与持久化

### 7.1 多层记忆架构

```
Working Memory (当前会话)
    ↓ 定期总结
Long-term Memory (跨会话)
    ↓ 经验池
Experience Pool (向量检索)
```

### 7.2 Team 序列化/反序列化

```python
def serialize(self, stg_path: Path):
    team_info_path = stg_path.joinpath("team.json")
    serialized_data = self.model_dump()
    serialized_data["context"] = self.env.context.serialize()
    write_json_file(team_info_path, serialized_data)

@classmethod
def deserialize(cls, stg_path: Path, context: Context = None) -> "Team":
    team_info = read_json_file(stg_path.joinpath("team.json"))
    ctx = context or Context()
    ctx.deserialize(team_info.pop("context", None))
    return Team(**team_info, context=ctx)
```

---

## 八、扩展点与生态

### 8.1 多种环境类型

MetaGPT 不仅支持软件开发场景，还支持：

| 环境 | 说明 |
|------|------|
| `SoftwareEnv` | 软件开发环境（默认） |
| `MGXEnv` | MetaGPT X 产品环境 |
| `WerewolfEnv` | 狼人杀游戏环境 |
| `StanfordTownEnv` | 斯坦福小镇模拟 |
| `AndroidEnv` | 安卓控制环境 |
| `MinecraftEnv` | Minecraft 游戏环境 |

### 8.2 新增的功能模块

MetaGPT 近期引入了 **RoleZero** —— 一个通用动态角色，可以根据指令动态规划行动，无需预定义 SOP。这种设计使 MetaGPT 能够处理更加开放性的任务。

---

## 九、与其他框架的对比

| 特性 | MetaGPT | LangChain | CrewAI | AutoGen |
|------|---------|-----------|--------|---------|
| 多智能体协作 | ✅ SOP 驱动 | ✅ 链式调用 | ✅ 角色扮演 | ✅ 对话协作 |
| 代码生成 | ✅ 完整端到端 | ⚠️ 需要自行组合 | ⚠️ 需要自行组合 | ⚠️ 需要自行组合 |
| 软件公司模拟 | ✅ 独特设计 | ❌ | ❌ | ❌ |
| 状态机 | ✅ 内置 | ⚠️ 需自行实现 | ✅ | ❌ |
| 工具支持 | 丰富（Browser/Editor/Search） | 丰富 | 一般 | 一般 |

---

## 十、架构亮点与局限性

### 10.1 架构亮点

1. **SOP 形式化**：将软件工程最佳实践编码为可执行的多智能体流程
2. **ActionNode 结构化输出**：可靠的 LLM 输出解析机制
3. **消息订阅机制**：灵活的角色间解耦
4. **多层记忆**：支持短期、长期、经验池的多层次记忆
5. **多环境支持**：通用性设计可扩展到游戏、模拟等场景

### 10.2 局限性

1. **预算驱动**：系统依赖预算限制来终止执行，可能导致任务未完成
2. **状态机硬编码**：每个角色需要预定义状态机，扩展需要修改代码
3. **调试困难**：多智能体异步协作使得问题定位复杂
4. **Token 消耗大**：完整流程可能产生大量 LLM 调用

---

## 十一、总结

MetaGPT 是一个设计精巧的多智能体框架，通过将软件公司的 SOP 形式化并应用到 LLM 驱动的智能体团队，实现了从自然语言需求到完整软件产品的端到端自动化。其核心架构由 Team → Environment → Role → Action → Provider/ Tools 构成，层次清晰，职责分明。

**"Code = SOP(Team)"** 这个公式简洁而深刻地抓住了软件工程的核心——高质量的软件来自有序的流程和高能力的团队。MetaGPT 正是将这一思想，通过 LLM + Multi-Agent 技术变为现实。

---

*报告生成时间：2026-04-30 | 分析深度：源码级 | 主要参考版本：main branch*