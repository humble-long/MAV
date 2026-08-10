# 面向仿生飞行器设计的大语言模型智能体构建

> 英文题名：Construction of a large language model agent for bionic flapping-wing aircraft design
> 方法名（正文沿用）：BioBridge-GraphRAG（前期开源版本已发 Zenodo DOI，保持可追溯）
> 目标期刊：航空学报
> 本稿：agent 视角重写版 v3 / 2026-07-09

**中图分类号**：V279；TP391　　**文献标识码**：A

---

## 引言

仿生扑翼飞行器（flapping-wing micro air vehicle，FWMAV）通过模拟鸟类、昆虫和蝙蝠等飞行生物的扑翼运动获取升力与推力，兼具尺度小、低速机动能力强、环境适应性好和生物拟态隐蔽等特点，在复杂环境侦察、生态监测、狭小空间巡检和人机协同等任务中具有应用潜力[1-3]。与固定翼和旋翼飞行器相比，扑翼飞行器在非定常气动、柔性结构、驱动传动和控制耦合等方面更为复杂，其概念设计需要综合生物原型、历史样机、任务载荷、续航需求、尺度律和低雷诺数气动特性等多类知识。当前方案构思仍主要依赖"文献检索—经验比对—参数估算—样机验证"的人工迭代流程[4]，存在3个瓶颈：知识来源高度分散、跨样机设计经验难以复用、任务约束到参考方案之间缺乏可解释映射。

知识图谱以实体、关系和属性的形式组织多源异构知识，为检索、推理和解释提供结构化基础。近年来，知识图谱已被应用于飞机电源系统故障诊断[5]、航空电子装备智能诊断[6]和高速飞行器多学科知识分析[7]等航空航天场景，也在工程设计知识复用[8]、生物启发设计[9]和复杂产品案例推理[10]中表现出较强的可解释性。然而，仿生扑翼飞行器的知识组织具有明显特殊性：生物层的体重、翼展、扑频、飞行速度和悬停能力等参数通常以区间或经验范围形式出现，工程层的样机、部件、任务场景和实验性能记录具有系统工程属性，二者之间的核心语义并非简单的"包含"或"引用"，而是"某一工程样机在何种维度上借鉴了某一生物原型"。若仅采用单层产品知识库，难以表达和查询这种跨域仿生映射，面向仿生扑翼飞行器概念设计的专用知识图谱尚未见诸报道。

大语言模型具备较强的自然语言理解与生成能力，为设计知识问答带来了新的交互方式，检索增强生成（retrieval-augmented generation，RAG）通过引入外部知识检索缓解模型幻觉[11]。在此基础上，将大语言模型作为智能体（agent），使其在"思考—行动—观察"循环中自主调用外部工具与知识源，已成为求解复杂推理任务的主流范式：ReAct 将推理轨迹与任务动作交错生成[12]，ToolLLM 使模型掌握大规模真实工具接口[13]。面向知识密集型问答，图检索增强生成（graph retrieval-augmented generation，GraphRAG）以知识图谱提供结构化证据[14]，Think-on-Graph 将大语言模型视为智能体在图谱上执行束搜索、逐步探索关系路径[15]，Plan-on-Graph 进一步引入可自我纠正的自适应规划机制[16]，SymAgent 以神经—符号双模块协同处理图谱不完整性[17]，KAG 面向专业领域融合知识图谱与向量检索[18]；相关综述亦系统梳理了大语言模型与知识图谱的融合范式[19-20]。然而，已有智能体大多面向开放域百科或通用文献问答，其动作空间以通用检索或文本工具为主，在迁移到工程设计问答时缺少3项关键能力：一是缺少承载跨域仿生映射的结构化领域记忆，二是缺少受物理量纲与尺度律约束的数值校验动作，三是缺少在大量历史样机中快速收窄候选方案的规划机制。因此，直接套用通用智能体难以回答"给定载荷与续航目标是否物理可行""为何推荐某一参考样机"这类同时依赖数值判断与方案排序的问题。

在仿生扑翼飞行器智能化研究方面，现有工作多集中于运动学与气动代理模型层面，例如以数据驱动方法预测扑翼时程气动力、优化扑动参数或辅助控制律设计[21]。这类研究面向部件级或参数级优化，而在概念设计阶段的整机方案生成、跨样机对比和知识检索层面，仍缺乏可解释、可追溯、定量化的智能辅助方法。概念设计阶段恰恰对"结构化证据检索、物理约束校验、方案推荐排序"三者兼备的综合能力有迫切需求。

针对上述问题，提出了一种知识图谱增强的仿生飞行器设计问答智能体 BioBridge-GraphRAG。该智能体以生物—工程双层知识图谱作为结构化记忆，以大语言模型作为推理控制器，将候选方案召回、图谱路径检索和物理工具调用统一组织为受领域约束的动作空间，并在"思考—行动—观察"循环中生成可追溯的答案与推荐。与仅依赖大语言模型的问答系统相比，所提智能体强调知识来源可追溯；与传统知识图谱问答相比，能够处理自然语言任务约束并调用物理公式；与纯向量检索增强相比，显式保留实体关系、多跳路径和工程解释。本文主要贡献如下：

（1）构建了仿生扑翼飞行器生物—工程双层知识图谱，作为智能体的结构化领域记忆。图谱包含 612 个节点和 625 条关系，并通过 5 类 MIMICS 相似关系刻画生物原型与工程样机之间的尺度、形态、运动学、气动和功能映射。

（2）提出了基于张量分解的方案候选召回方法，作为智能体的规划模块。将样机性能、部件配置和任务场景组织为飞行器—特征—任务三阶张量，通过 CP 分解与混合相似度得到 Top-K 候选，在详细推理前收窄搜索空间。

（3）提出了工具增强的图路径推理方法，作为智能体的推理模块。将重量估算、尺度律预测、Strouhal 数和 Reynolds 数校验封装为可调用的物理工具，与图谱检索共同构成受物理约束的动作空间，使大语言模型在 ReAct 循环中完成多跳推理与数值校验。

（4）构建了 FWMAV-QA 中文测评数据集。数据集共 754 题，覆盖知识定义、属性查询、多实体对比、多跳推理、简单方案推荐和复杂约束推荐 6 类任务，可用于评估仿生扑翼飞行器领域智能问答与方案推荐系统。

---

## 参考文献（引言部分，草稿）

[1] SHYY W, AONO H, CHIMAKURTHI S K, et al. An introduction to flapping wing aerodynamics[M]. Cambridge: Cambridge University Press, 2013.

[2] KEENNON M, KLINGEBIEL K, WON H, et al. Development of the Nano Hummingbird: a tailless flapping wing micro air vehicle[C]//50th AIAA Aerospace Sciences Meeting. Reston: AIAA, 2012.

[3] KARÁSEK M, MUIJRES F T, DE WAGTER C, et al. A tailless aerial robotic flapper reveals that flies use torque coupling in rapid banked turns[J]. Science, 2018, 361(6407): 1089-1094.

[4] HASSANALIAN M, ABDELKEFI A. Methodologies for weight estimation of fixed and flapping wing micro air vehicles[J]. Meccanica, 2017, 52(9): 2047-2068.

[5] 聂同攀, 曾继炎, 程玉杰, 等. 面向飞机电源系统故障诊断的知识图谱构建技术及应用[J]. 航空学报, 2022, 43(8): 625499.

[6] 程玉杰, 胡峥, 高永梅, 等. 知识图谱与大模型融合驱动的航空电子装备故障诊断[J/OL]. 航空学报, doi: 10.7527/S1000-6893.2026.33284.

[7] 安凯, 黄伟, 王振国, 等. AI驱动高速飞行器多学科发展知识图谱分析[J]. 航空学报, 2024(S1): 730566.

[8] SARICA S, SONG B, LOW M Y H, et al. Engineering knowledge graph for keyword discovery in patent search[J]. Advanced Engineering Informatics, 2020, 44: 101105.

[9] CHEN Y, YU S, CHILTON L B, et al. A knowledge graph-based bio-inspired design approach for knowledge retrieval and reasoning[J]. Journal of Engineering Design, 2025, 36(7-9): 1321-1351.

[10] HUANG C, ZHANG Y, YU S, et al. A case-based knowledge graph with reinforcement learning for the intelligent design approach of complex product[J]. Journal of Engineering Design, 2025, 36(7-9): 1451-1478.

[11] LEWIS P, PEREZ E, PIKTUS A, et al. Retrieval-augmented generation for knowledge-intensive NLP tasks[C]//Advances in Neural Information Processing Systems. 2020: 9459-9474.

[12] YAO S, ZHAO J, YU D, et al. ReAct: synergizing reasoning and acting in language models[C]//International Conference on Learning Representations. 2023.

[13] QIN Y, LIANG S, YE Y, et al. ToolLLM: facilitating large language models to master 16000+ real-world APIs[C]//International Conference on Learning Representations. 2024.

[14] EDGE D, TRINH H, CHENG N, et al. From local to global: a graph RAG approach to query-focused summarization[EB/OL]. arXiv:2404.16130, 2024.

[15] SUN J, XU C, TANG L, et al. Think-on-Graph: deep and responsible reasoning of large language model on knowledge graph[C]//International Conference on Learning Representations. 2024.

[16] CHEN L, TONG P, JIN Z, et al. Plan-on-Graph: self-correcting adaptive planning of large language model on knowledge graphs[C]//Advances in Neural Information Processing Systems. 2024.

[17] LIU B, ZHANG J, LIN F, et al. SymAgent: a neural-symbolic self-learning agent framework for complex reasoning over knowledge graphs[C]//Proceedings of the ACM Web Conference. 2025: 98-108.

[18] LIANG L, SUN M, GUI Z, et al. KAG: boosting LLMs in professional domains via knowledge augmented generation[C]//Companion Proceedings of the ACM Web Conference. 2025.

[19] PAN S, LUO L, WANG Y, et al. Unifying large language models and knowledge graphs: a roadmap[J]. IEEE Transactions on Knowledge and Data Engineering, 2024, 36(7): 3580-3599.

[20] PENG B, ZHU Y, LIU Y, et al. Graph retrieval-augmented generation: a survey[J]. ACM Transactions on Information Systems, 2025, 44(2): 1-52.

[21] （待补充：仿生扑翼飞行器数据驱动/深度学习设计相关文献 1-2 篇，用于支撑 P4 论点）
