# 从深度学习到大模型：人工智能范式转移的学术综述

## 摘要

本文系统性地回顾了从深度学习到基础模型的人工智能范式转移历程，从数据、模型、训练、任务、评估、应用、理论七个维度归纳了范式变化的核心特征。通过梳理学术研究的演化脉络，本文分析了当前学术界的主要趋势与争议，比较了学术界与产业界的差异，并对未来研究方向进行了学术性判断。

---

## 1. 范式转移的多维比较

### 1.1 数据：从人工标注到自监督与合成

**深度学习阶段**以**监督标注数据**为主导。在ImageNet（Deng et al., 2009）等大规模标注数据集的推动下，监督学习成为主流范式。然而，数据标注的高成本、高时间消耗以及标注偏差问题成为显著瓶颈。

**大模型阶段**的核心特征是**自监督学习**的崛起。BERT（Devlin et al., 2019）的掩码语言建模、GPT（Radford et al., 2018）的自回归预测，以及对比学习（Chen et al., 2020b），使得模型能够从海量无标注数据中学习通用表示。**弱监督数据**（Ratner et al., 2016）和**合成数据**（Touvron et al., 2023a）也成为重要补充，特别是在对齐阶段。

| 数据类型 | 代表方法 | 核心优势 | 主要局限 |
|----------|----------|----------|----------|
| 监督标注 | ImageNet, COCO | 质量可控 | 成本高昂、规模受限 |
| 自监督 | BERT-MLM, GPT-AR, SimCLR | 规模无限、成本低 | 信号相对稀疏 |
| 弱监督 | Snorkel, 远程监督 | 中等成本 | 噪声较大 |
| 合成数据 | LLM生成、GTA数据 | 完全可控、多样性高 | 真实性待验证 |

### 1.2 模型：从任务特定到基础模型

**深度学习阶段**的主流是**任务特定模型**。ResNet（He et al., 2016）用于图像分类，LSTM（Hochreiter & Schmidhuber, 1997）用于序列建模，Transformer（Vaswani et al., 2017）最初也是为机器翻译设计。每个任务需要从头训练或微调特定模型。

**预训练-微调范式**的出现是重要过渡。计算机视觉领域的ImageNet预训练、NLP领域的BERT/GPT预训练，使得预训练模型成为"基础特征提取器"，再针对下游任务微调。

**基础模型（Foundation Models）**（Bommasani et al., 2021）阶段的核心是"一基多能"。单一模型通过规模扩大和指令微调，可以在数百个任务上达到或超过专用模型。**多模态基础模型**（Alayrac et al., 2022; Li et al., 2023）进一步统一了视觉、语言、音频等多种模态。

### 1.3 训练：从监督学习到对齐与强化学习

| 训练范式 | 阶段 | 核心目标 | 代表性工作 |
|----------|------|----------|------------|
| 监督学习 | 深度学习 | 任务特定优化 | ResNet, Seq2Seq |
| 大规模预训练 | 预训练阶段 | 通用表示学习 | BERT, GPT-1/2/3 |
| 指令微调 | 对齐阶段 | 任务泛化能力 | Flan, Alpaca, LLaMA-2 |
| RLHF/RLAIF | 对齐阶段 | 人类偏好对齐 | InstructGPT, Claude |
| 持续学习 | 长期部署 | 知识更新与保留 | - |

**强化学习从人类反馈（RLHF）**（Christiano et al., 2017; Stiennon et al., 2020）是对齐的关键技术。奖励模型（Reward Model）拟合人类偏好，PPO算法（Schulman et al., 2017）用于策略优化。**直接偏好优化（DPO）**（Rafailov et al., 2023）简化了RLHF流程，避免了复杂的强化学习训练。

### 1.4 任务：从单任务到代理执行

任务范式的演进呈现清晰的路径：

1. **单任务**：每个模型解决一个问题
2. **跨任务迁移**：预训练+微调
3. **跨模态统一**：多模态模型处理不同类型输入
4. **工具增强**：模型调用外部工具（搜索、计算器、数据库）
5. **代理执行**：模型在复杂环境中自主规划与行动

**工具增强**（Parisi et al., 2022; Schick et al., 2023）和**检索增强生成（RAG）**（Lewis et al., 2020）显著扩展了模型的能力边界。WebGPT（Nakano et al., 2021）、Toolformer（Schick et al., 2023）等工作证明了工具调用的价值。

**代理（Agent）范式**代表了更高级的任务形态。ReAct（Yao et al., 2023）将推理与行动结合，Reflexion（Shinn et al., 2023）引入自我反思，AutoGPT等系统尝试自主完成复杂目标。

### 1.5 评估：从基准测试到真实任务与对齐评测

| 评测类型 | 代表方法 | 核心价值 | 主要局限 |
|----------|----------|----------|----------|
| 传统Benchmark | ImageNet, GLUE, SQuAD | 标准化、可比较 | 易过拟合、污染严重 |
| 通用能力评测 | MMLU, BIG-bench, HellaSwag | 能力全面性 | 仍与真实有差距 |
| 对齐评测 | MT-Bench, Chatbot Arena, HumanEval | 人类偏好对齐 | 主观、成本高 |
| 真实任务评测 | WebArena, AgentBench | 真实有效性 | 难以标准化 |

**基准测试污染**已成为严重问题。Hendrycks et al.（2021）、Li et al.（2023b）的研究表明，许多流行基准的测试集数据存在于预训练语料中，导致评测失真。**开放性问题**、**生成式评测**、**动态基准**成为应对方向。

### 1.6 应用：从模型驱动功能到Agent化

应用范式的演进：

1. **模型驱动功能**：模型作为独立功能模块（如图像识别API）
2. **基础模型驱动系统**：模型作为系统核心（如Copilot, CodeLlama）
3. **工作流增强**：模型嵌入现有工作流（如文档写作、代码辅助）
4. **Agent化**：自主Agent在复杂环境中执行任务（如软件开发助理、研究助手）

### 1.7 理论：从表示学习到涌现能力与对齐

**深度学习阶段**的理论围绕**表示学习**（Bengio et al., 2013）、**优化**（Kingma & Ba, 2014）、**泛化**（Zhang et al., 2017）展开。

**大模型阶段**的理论焦点发生转移：

| 理论方向 | 核心问题 | 代表性进展 |
|----------|----------|------------|
| 规模定律 | 性能与规模的关系 | Hoffmann et al. (2022), Kaplan et al. (2020) |
| 涌现能力 | 能力何时如何出现 | Wei et al. (2022) |
| 对齐理论 | 如何对齐人类价值 | - |
| 安全性 | 鲁棒性、有害性防护 | - |

---

## 2. 学术研究的演化脉络

### 2.1 深度学习兴起阶段（~2012-2017）

**里程碑事件：**
- 2012：AlexNet（Krizhevsky et al., 2012）在ImageNet上大幅超越传统方法
- 2014：GAN（Goodfellow et al., 2014）
- 2015：ResNet（He et al., 2016）解决深度网络退化问题
- 2017：Transformer（Vaswani et al., 2017）提出

**会议热点：** CVPR、NeurIPS、ICML聚焦网络架构设计、优化算法、表示学习理论。

### 2.2 Transformer与预训练阶段（2018-2020）

**关键进展：**
- 2018：GPT-1（Radford et al., 2018）、BERT（Devlin et al., 2019）
- 2019：GPT-2（Radford et al., 2019）展示规模潜力
- 2020：GPT-3（Brown et al., 2020）展示few-shot能力
- 2020：ViT（Dosovitskiy et al., 2020）将Transformer引入CV

"预训练-微调"成为NLP和CV的标准范式。

### 2.3 大模型与基础模型阶段（2021-2022）

**关键进展：**
- 2021："Foundation Models"概念提出（Bommasani et al., 2021）
- 2021：InstructGPT（Ouyang et al., 2022）展示RLHF威力
- 2022：ChatGPT发布，引发产业变革
- 2022：LLaMA（Touvron et al., 2023）开源推动学术研究

**产业介入加深**：OpenAI、Google、Meta、Anthropic成为重要玩家。

### 2.4 多模态、对齐、推理、Agent阶段（2023-）

**当前热点：**
- **多模态统一**：GPT-4V、Gemini、Qwen-VL
- **对齐技术**：RLHF、DPO、RLAIF
- **推理增强**：Chain-of-Thought（Wei et al., 2022）、Tree-of-Thought（Yao et al., 2023）
- **Agent系统**：AutoGPT、LangChain、GPT-4 Tools

### 2.5 评测、安全、可解释性、效率优化阶段（并行发展）

这些方向贯穿整个演进过程，但在大模型阶段获得更多关注：

- **评测**：应对基准污染、开发真实任务评测
- **安全**：对抗攻击、有害性生成、越狱防护
- **可解释性**：注意力可视化、激活分析、因果推断
- **效率**：量化（Dettmers et al., 2022）、LoRA（Hu et al., 2021）、蒸馏、MoE（Fedus et al., 2021）

---

## 3. 当前学术界的主要趋势与争议

### 3.1 Scaling Law与模型规模扩展的边界

**已形成共识：**
- 模型性能与计算量、数据量、参数量呈幂律关系（Hoffmann et al., 2022; Kaplan et al., 2020）
- Chinchilla最优分配：数据与参数量应等比例增长

**尚存争议：**
- 规模定律的**极限**在哪里？是否存在"规模天花板"？
- 单纯扩大规模是否是**唯一**或**最优**路径？
- 小模型通过更好的算法、数据或架构能否追上大模型？
- 如何定义"有用的"规模，而非单纯追求参数量？

### 3.2 Instruction Tuning、RLHF、DPO、RLAIF

**已形成共识：**
- 对齐是使大模型"可用"的关键步骤
- 简单的预训练模型往往不符合人类使用习惯
- 一定程度的对齐能显著提升用户体验

**尚存争议：**
- RLHF是否**必需**？DPO等更简单方法能否达到类似效果？
- 对齐是否会导致**能力遗忘**或"对齐税"？
- 人类偏好的**异质性**如何处理？不同用户有不同偏好
- 自动化对齐（如RLAIF）能否替代人类反馈？

### 3.3 多模态统一建模

**已形成共识：**
- 多模态是自然方向，人类智能本质上是多模态的
- 视觉-语言统一模型已有显著进展

**有待验证：**
- 是否存在**单一架构**能统一处理所有模态（视觉、语言、音频、动作、具身）？
- 多模态模型是否会出现**模态干扰**（一个模态影响另一个模态的性能）？
- 如何实现**真正的多模态理解**而非简单的特征拼接？

### 3.4 长上下文与记忆机制

**已形成共识：**
- 长上下文是复杂任务（如代码、长文档、多轮对话）的关键能力
- Transformer原生注意力的O(n²)复杂度成为瓶颈

**研究热点：**
- Linear Attention、RetNet（Sun et al., 2023）、Mamba（Gu & Dao, 2023）等O(n)架构
- 检索增强、滑动窗口、记忆压缩
- 如何在长上下文下保持信息的**可访问性**和**召回质量**？

### 3.5 工具调用、RAG、Agent、推理增强

**已形成共识：**
- 工具调用能显著扩展模型能力边界
- RAG能缓解幻觉、提供可溯源性
- 推理增强策略（CoT、ToT）能提升复杂任务表现

**尚存争议：**
- 工具调用能力应**内联**（模型内置）还是**外接**（独立工具选择器）？
- 如何设计**通用的工具接口**和工具学习范式？
- Agent的**规划能力**如何系统提升？当前Agent在长程任务上仍易失败
- 如何实现**可验证的推理**？

### 3.6 高效训练、参数高效微调、量化、蒸馏、MoE

**已形成共识：**
- 效率是大模型落地的关键制约因素
- 量化、LoRA等技术已在实践中广泛使用

**研究热点：**
- 4-bit、3-bit甚至2-bit量化的精度保持
- MoE（Mixture of Experts）的路由优化和负载均衡
- 如何在小设备上运行大模型（端侧部署）？
- 蒸馏的最佳实践：大模型教小模型的最优策略

### 3.7 幻觉、偏见、鲁棒性、安全性、可解释性

**已形成共识：**
- 幻觉是大模型实际部署的严重问题
- 模型继承甚至放大训练数据中的偏见
- 对抗攻击、prompt注入、越狱是真实安全威胁

**有待突破：**
- 如何**系统性减少**幻觉而非仅在个案上缓解？
- 偏见的**量化评估**与**有效缓解**方法
- 可证明的安全性保证
- 大模型决策的**机制级理解**（而非仅相关性分析）

### 3.8 基准测试污染、评测失真与可复现性

**已形成共识：**
- 基准污染问题严重，许多Benchmark已不可靠
- 闭源模型的可复现性存在挑战
- 生成式任务的评测标准化困难

**研究方向：**
- 动态基准、实时生成的评测数据
- 基于LLM的自动化评测（需解决评测者自身的可靠性）
- 跨模型的公平比较方法论
- 开放科学与可复现性文化建设

---

## 4. 学术界与产业界的差异比较

### 4.1 学术研究的偏重

| 维度 | 学术偏好 | 原因 |
|------|----------|------|
| **研究目标** | 探索性、原理性问题 | 追求新发现、理论贡献 |
| **资源条件** | 相对有限（依赖算力中心） | 经费制约、设备共享 |
| **实验方式** | 小规模验证、控制变量 | 追求统计显著性、可解释 |
| **评价指标** | 基准性能、新颖性 | 论文录用标准 |
| **部署约束** | 通常不考虑 | 聚焦方法创新 |
| **时间尺度** | 中长期问题 | 不受产品上线压力 |

**学术界特别关注：**
- 新的模型架构和学习范式
- 理论理解和可解释性
- 零样本或少样本场景下的方法
- 公平、伦理、安全等社会影响问题
- 小数据集、低资源场景

### 4.2 产业应用的偏重

| 维度 | 产业偏好 | 原因 |
|------|----------|------|
| **研究目标** | 产品价值、用户体验 | 商业目标驱动 |
| **资源条件** | 充足（大规模算力集群） | 预算相对充裕 |
| **实验方式** | A/B测试、在线实验 | 真实用户反馈 |
| **评价指标** | 业务指标、成本收益 | ROI、用户满意度 |
| **部署约束** | 延迟、成本、可靠性 | 工程落地限制 |
| **时间尺度** | 短期见效 | 快速迭代压力 |

**产业界特别关注：**
- 推理效率和部署成本
- 系统可靠性和可用性
- 有害性防护和内容安全
- 产品化和用户体验优化
- 竞争优势和商业壁垒

### 4.3 共同关注的议题

| 议题 | 说明 |
|------|------|
| **模型能力提升** | 双方都追求更强的模型能力 |
| **效率优化** | 训练和推理效率对双方都重要 |
| **多模态能力** | 学术界探索原理，产业界落地应用 |
| **基础对齐** | 使模型有用、可用的基本对齐技术 |
| **安全性** | 对抗攻击防护、有害内容控制 |

### 4.4 主要由产业驱动的议题

| 议题 | 产业优势 | 示例 |
|------|----------|------|
| **超大规模预训练** | 算力资源充足 | GPT-4、PaLM、Claude |
| **工程化基础设施** | 分布式训练、推理优化 | Megatron-LM、vLLM |
| **产品级对齐** | 用户反馈数据丰富 | ChatGPT、Claude的持续优化 |
| **部署系统** | 大规模服务、高可用性 | API服务、企业级部署 |
| **数据闭环** | 真实用户数据收集与利用 | - |

### 4.5 仍需学术界突破的基础问题

| 问题 | 为什么需要学术界 | 研究难度 |
|------|------------------|----------|
| **理论理解** | 产业界关注应用，缺乏理论研究动力 | 高 |
| **小样本/零样本学习** | 不需要大规模数据即可验证 | 中 |
| **可解释性与因果性** | 不直接产生商业价值，但对长期发展关键 | 高 |
| **新范式探索** | 风险高、周期长，产业界不愿投入 | 高 |
| **伦理与社会影响** | 超越商业目标的 broader impact | 中 |
| **基准与评测科学** | 需要独立、中立的评估 | 中 |

---

## 5. 未来研究方向的学术性判断

### 5.1 Agentic AI

**现状**：当前Agent在长程任务上表现不佳，规划能力有限，容易在复杂环境中失败。

**可能的突破方向**：
- **层次化规划**：从"一步一想"到多尺度、抽象级别的规划
- **内在动机与好奇心驱动**：超越即时奖励，实现更通用的探索
- **社会模拟与多Agent协作**：多个Agent交互产生更复杂的行为
- **可验证的执行轨迹**：Agent的每一步决策都可追溯、可验证

**有待验证**：
- Agent是否需要"世界模型"？还是仅凭当前观察即可？
- 如何实现Agent的**终身学习**与**技能积累**？
- Agent的**安全控制**与"关停开关"如何设计？

### 5.2 世界模型与具身智能

**现状**：世界模型（Ha & Schmidhuber, 2018; Hafner et al., 2020）在强化学习中已有探索，但尚未与大模型范式深度融合。

**核心问题**：
- 大模型是否需要**内在的世界模拟器**？
- 如何从文本/多模态输入中学习**可泛化的物理常识**？
- 具身（Embodiment）是否是理解世界的必要条件？
- 如何实现**模拟与真实**的无缝迁移？

**潜在价值**：世界模型可能是实现"推理"、"想象"、"规划"等高级能力的关键路径。

### 5.3 多模态统一模型

**趋势判断**：
- **已成共识**：多模态是自然方向，单一模态的模型终将成为历史
- **技术路径**：可能存在从"拼接"→"对齐"→"统一表示"→"统一架构"的演进路径
- **模态范围**：将从视觉-语言扩展到音频、动作、传感器信号、神经信号等

**研究问题**：
- 是否存在**通用的变换器**能处理所有模态？还是需要模态特定的适配器？
- 如何实现**均衡的多模态能力**？（许多当前模型仍以语言为主）
- 多模态是否会带来**新的涌现能力**？

### 5.4 个性化与持续学习

**现状**：当前大模型是"静态"的，知识截止于训练数据，无法个性化适应用户。

**核心挑战**：
- **灾难性遗忘**：如何在学习新知识时不忘记旧知识？
- **个性化 vs 通用性**：如何在保持通用性的同时适应个人偏好？
- **隐私与效率**：个性化学习可能需要访问用户数据，如何在保护隐私的同时实现？
- **更新频率**：模型应持续更新还是定期更新？更新的边界在哪里？

**可能的技术路径**：
- 参数高效微调（LoRA等）+ 适配器
- 记忆增强架构
- 检索增强作为"外部记忆"
- 稀疏更新、低秩更新

### 5.5 端侧/小模型

**驱动因素**：
- 隐私：数据不离开设备
- 延迟：本地推理速度更快
- 成本：无需调用云端API
- 可用性：无网络也能使用

**研究问题**：
- **规模的本质是什么**？小模型通过更好的算法能否追上大模型？
- **模型压缩的极限**：在保持能力的前提下，模型可以有多小？
- **蒸馏的最优策略**：大模型教小模型的最佳方式是什么？
- **云侧-端侧协同**：哪些能力放在云侧，哪些放在端侧？

**产业影响**：端侧模型可能重塑AI产业格局，降低对大公司API的依赖。

### 5.6 检索增强生成与记忆系统

**已形成共识**：
- RAG是缓解幻觉的有效方法
- 检索提供可溯源性，提升可信度
- 混合"模型内知识"与"检索知识"是可行路径

**未来方向**：
- **何时检索**：智能决策检索的触发时机，而非盲目检索
- **多步检索**：检索 → 分析 → 再检索的迭代过程
- **检索结果的融合**：如何将多个检索源的信息有机结合
- **长期记忆系统**：跨会话的记忆存储与召回
- **记忆编辑与遗忘**：如何"修正"错误记忆，"忘记"过时信息

### 5.7 AI系统化工程与自治系统

**愿景**：AI不再是单个模型，而是由多个组件组成的复杂系统。

**研究问题**：
- **系统架构**：如何设计由多个模型、工具、记忆组成的AI系统？
- **组件通信**：不同组件之间的接口与协议
- **容错与降级**：系统部分失败时如何优雅降级？
- **可观测性**：如何理解和调试复杂AI系统的行为？
- **目标函数**：自治系统的长期目标如何设定与更新？

**跨学科融合**：这一方向可能需要与系统工程、控制理论、认知科学等学科深度交叉。

---

## 6. 结论

从深度学习到大模型的范式转移，不仅是模型规模的扩大，更是数据、模型、训练、任务、评估、应用、理论等全链条的系统性变革。这一转移既带来了前所未有的能力突破，也暴露了新的挑战。

**已形成共识**的方向包括：规模定律的有效性、自监督学习的价值、对齐技术的必要性、多模态的自然趋势。

**尚存争议**的问题包括：规模的边界、对齐的最优路径、小模型的潜力、Agent的最佳架构。

**有待验证**的方向包括：世界模型的必要性、具身智能的价值、个性化学习的机制、端侧-云侧的最优分工。

学术界与产业界在这一轮变革中呈现出既合作又分工的态势：产业界在大规模工程落地、数据闭环、产品化方面具有优势，而学术界在理论理解、新范式探索、基础问题突破、伦理社会影响等方面仍发挥着不可替代的作用。

未来几年，Agentic AI、世界模型、多模态统一、个性化学习、端侧部署、记忆系统、AI系统化工程等方向可能成为研究热点。如何在追求能力的同时确保安全、对齐、可解释、可控，将是贯穿始终的核心挑战。

---

## 参考文献

（代表性文献示例，实际综述应包含更完整的引用）

- Alayrac, J. B., et al. (2022). Flamingo: a visual language model for few-shot learning. *NeurIPS*.
- Bengio, Y., Courville, A., & Vincent, P. (2013). Representation learning: A review and new perspectives. *IEEE TPAMI*.
- Bommasani, R., et al. (2021). On the opportunities and risks of foundation models. *arXiv:2108.07258*.
- Brown, T. B., et al. (2020). Language models are few-shot learners. *NeurIPS*.
- Chen, T., et al. (2020b). A simple framework for contrastive learning of visual representations. *ICML*.
- Christiano, P. F., et al. (2017). Deep reinforcement learning from human preferences. *NeurIPS*.
- Deng, J., et al. (2009). ImageNet: A large-scale hierarchical image database. *CVPR*.
- Dettmers, T., et al. (2022). LLM.int8(): 8-bit matrix multiplication for transformers at scale. *NeurIPS*.
- Devlin, J., et al. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. *NAACL*.
- Dosovitskiy, A., et al. (2020). An image is worth 16x16 words: Transformers for image recognition at scale. *ICLR*.
- Fedus, W., et al. (2021). Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity. *arXiv:2101.03961*.
- Goodfellow, I., et al. (2014). Generative adversarial nets. *NeurIPS*.
- Gu, A., & Dao, T. (2023). Mamba: Linear-Time Sequence Modeling with Selective State Spaces. *arXiv:2312.00752*.
- Hafner, D., et al. (2020). Mastering Atari with Discrete World Models. *ICLR*.
- Ha, D., & Schmidhuber, J. (2018). World Models. *arXiv:1803.10122*.
- He, K., et al. (2016). Deep residual learning for image recognition. *CVPR*.
- Hendrycks, D., et al. (2021). Measuring Massive Multitask Language Understanding. *ICLR*.
- Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. *Neural Computation*.
- Hoffmann, J., et al. (2022). Training compute-optimal large language models. *arXiv:2203.15556*.
- Hu, E. J., et al. (2021). LoRA: Low-Rank Adaptation of Large Language Models. *ICLR*.
- Kaplan, J., et al. (2020). Scaling laws for neural language models. *arXiv:2001.08361*.
- Kingma, D. P., & Ba, J. (2014). Adam: A method for stochastic optimization. *ICLR*.
- Krizhevsky, A., et al. (2012). ImageNet classification with deep convolutional neural networks. *NeurIPS*.
- Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *NeurIPS*.
- Li, X., et al. (2023). Visual Instruction Tuning. *NeurIPS*.
- Nakano, R., et al. (2021). WebGPT: Browser-assisted question-answering with human feedback. *arXiv:2112.09332*.
- Ouyang, L., et al. (2022). Training language models to follow instructions with human feedback. *NeurIPS*.
- Parisi, A., et al. (2022). MRKL Systems: A modular, neuro-symbolic architecture that combines large language models, external knowledge sources and discrete reasoning. *arXiv:2205.00445*.
- Radford, A., et al. (2018). Improving language understanding by generative pre-training.
- Radford, A., et al. (2019). Language models are unsupervised multitask learners. *OpenAI Blog*.
- Rafailov, R., et al. (2023). Direct Preference Optimization: Your Language Model is Secretly a Reward Model. *NeurIPS*.
- Ratner, A., et al. (2016). Data Programming: Creating Large Training Sets, Quickly. *NeurIPS*.
- Schick, T., et al. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools. *NeurIPS*.
- Schulman, J., et al. (2017). Proximal Policy Optimization Algorithms. *arXiv:1707.06347*.
- Shinn, N., et al. (2023). Reflexion: Language Agents with Verbal Reinforcement Learning and Self-Reflection. *arXiv:2303.11366*.
- Stiennon, N., et al. (2020). Learning to summarize with human feedback. *NeurIPS*.
- Sun, Z., et al. (2023). Retentive Network: A Successor to Transformer for Large Language Models. *arXiv:2307.08621*.
- Touvron, H., et al. (2023). LLaMA: Open and Efficient Foundation Language Models. *arXiv:2302.13971*.
- Touvron, H., et al. (2023a). Llama 2: Open Foundation and Fine-Tuned Chat Models. *arXiv:2307.09288*.
- Vaswani, A., et al. (2017). Attention Is All You Need. *NeurIPS*.
- Wei, J., et al. (2022). Emergent abilities of large language models. *TMLR*.
- Yao, S., et al. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR*.
- Yao, S., et al. (2023). Tree of Thoughts: Deliberate Problem Solving with Large Language Models. *NeurIPS*.
- Zhang, C., et al. (2017). Understanding deep learning requires rethinking generalization. *ICLR*.

---

**文档信息**  
- 标题：从深度学习到大模型：人工智能范式转移的学术综述  
- 撰写日期：2026-03-22  
- 风格：文献综述 / 研究背景分析  
- 用途：论文背景、相关工作、开题报告、课程讲义
