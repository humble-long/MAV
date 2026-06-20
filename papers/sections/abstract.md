# 摘要 + 关键词

> 草稿 v0.1 / 2026-06-17
> 字数：中文摘要 ~290 字（航空学报要求 ≥ 200），英文摘要对应翻译
> 关键词：7 个（航空学报建议 5–8 个）

---

## 中文摘要（约 290 字）

针对仿生扑翼飞行器概念设计阶段领域知识高度分散、设计经验难以复用以及任务驱动方案生成缺乏系统化方法等问题，设计并实现了一种知识图谱增强的仿生飞行器设计问答智能体 BioBridge-GraphRAG，将知识图谱（KG）作为结构化记忆，并使大语言模型（LLM）作为智能体在图谱上进行多跳推理与物理校验。首先，构建了由生物原型层和工程样机层组成的双层知识图谱（612 节点、625 关系），并定义了气动相似、运动学相似、形态相似、尺度相似 4 类仿生映射关系，实现了生物-工程跨域知识的统一表达；其次，提出了尺度律工具增强的图路径推理框架，将 4 个领域物理工具（重量模型、尺度律预测、Strouhal 数与雷诺数判别）以 OpenAI Function Calling 协议封装为 LLM 可调用接口，使模型在 ReAct 范式下完成知识检索与数值校验的协同推理；进一步，引入基于 3 阶张量 CP 分解的方案候选粗筛方法，结合原始特征与 CP 嵌入空间的混合相似度（α = 0.4）实现毫秒级 Top-K 召回，并与图路径推理协同形成"粗筛—精排"两阶段范式。在自构建的 FWMAV-QA 测评数据集（覆盖 6 类共 754 题）上的实验结果表明，所提方法相较于纯 LLM 基线在多跳推理类问题上的实体召回率由 14% 提升至 62%，整体实体召回率由 0.39 提升至 0.53；时延仅增加约 6%。所提方法可为仿生扑翼飞行器概念设计阶段的快速方案推荐与可解释决策支持提供有效手段。

## 英文摘要（约 280 words）

To address the problems of highly fragmented domain knowledge, the difficulty of reusing design experience, and the lack of a systematic methodology for task-driven design generation in the conceptual design stage of bionic flapping-wing micro air vehicles (FWMAVs), a knowledge-graph-augmented agent for FWMAV design question answering, named BioBridge-GraphRAG, is designed and implemented, in which the knowledge graph (KG) serves as the structured memory and a large language model (LLM) acts as the agent that performs multi-hop reasoning and physical verification on top of the graph. First, a bilayer knowledge graph consisting of a biological-prototype layer and an engineering-vehicle layer (612 nodes and 625 edges) is constructed, in which four classes of bionic mapping relations—aerodynamic similarity, kinematic similarity, morphological similarity, and scale similarity—are defined to enable a unified expression of biology–engineering cross-domain knowledge. Second, a scaling-law tool-augmented graph path reasoning framework is proposed: four domain-specific physical tools (a takeoff-weight model, scaling-law prediction, Strouhal-number and Reynolds-number diagnostics) are encapsulated as LLM-callable interfaces under the OpenAI Function Calling protocol, so that the LLM, operating in the ReAct paradigm, performs the joint reasoning of KG retrieval and numerical verification. Third, a CP-decomposition based candidate-recall method on a 3-mode tensor is introduced, in which a hybrid similarity (α = 0.4) of raw-feature cosine and CP-embedding cosine returns Top-K candidates within milliseconds, working together with the path reasoner to form a recall–rerank two-stage paradigm for design recommendation. On the self-built FWMAV-QA benchmark, which covers six categories with 754 questions in total, experimental results show that the proposed method improves entity recall on multi-hop reasoning questions from 14% to 62% relative to a pure-LLM baseline, raises overall entity recall from 0.39 to 0.53, while the per-question latency increases by only about 6%. The proposed method provides an effective tool for fast design recommendation and explainable decision support in the conceptual design stage of bionic FWMAVs.

---

## 关键词（7 个）

**中文关键词**：
知识图谱；大语言模型；仿生扑翼飞行器；图检索增强生成；张量分解；案例推理；概念设计

**English Keywords**:
Knowledge graph; Large language model; Bionic flapping-wing micro air vehicle; Graph retrieval-augmented generation; Tensor decomposition; Case-based reasoning; Conceptual design

---

## 写作笔记（不进入正文）

### 摘要 5 段式结构
| 段 | 职责 | 中文字数 | 英文 words |
|---|---|---|---|
| 1 | 问题与方法定位 | ~80 | ~70 |
| 2 | 创新点 1：双层本体 | ~70 | ~70 |
| 3 | 创新点 2：工具增强路径推理 | ~60 | ~70 |
| 4 | 创新点 3：张量分解粗筛 | ~50 | ~50 |
| 5 | 实验验证 + 结论 | ~30 | ~40 |
| 合计 | | ~290 | ~280 |

### 关键设计决定

1. **真实数字而非占位 X%**：用 A4 类 Entity Recall 14% → 62%、整体 0.39 → 0.53、时延 +6% 这三组真实测得数据替换大纲中的 X% / Y%。
2. **612 + 625 真实规模**：与 §2 Tab. 1 一致。
3. **R = 12 / α = 0.4**：与 §4 一致；摘要里只点 α 这个最关键的超参（R 影响重构误差但与最终性能弱耦合）。
4. **6 类 754 题**：与 §5.1 Tab. 3 一致。
5. **"FWMAV"全称首次出现给完整定义**：bionic flapping-wing micro air vehicles。
6. **避开"首次/前所未有"**：用"BioBridge-GraphRAG is proposed"，不用"first proposed"。
7. **关键词 7 个**：在大纲基础上加"张量分解"（创新点 3 显式标记），去掉了"扑翼飞行器"（与"仿生扑翼飞行器"重复）。

### Assumptions or missing inputs

- [ ] B1 baseline 已实现，实测数据用上了；B2–B6 没用上但摘要里没提到具体基线名称
- [ ] 4 个消融变体跑完后可考虑在摘要末加一句"消融研究验证了 4 个组件的独立贡献"
- [ ] 中英文严格对应——已对齐
- [ ] BioBridge-GraphRAG 命名首次出现给出英文括注

### 修订记录
- v0.1 (2026-06-17): 初稿，含 B1 vs Full 真实数据
