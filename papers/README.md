# BioBridge-GraphRAG 论文工作目录

> **题目**：知识图谱增强的仿生飞行器设计问答智能体（19 字）
> **英文**：A knowledge graph augmented agent for design question answering of bionic flapping-wing aircraft
> **方法名**：BioBridge-GraphRAG（粗筛 + 精排范式）
> **目标期刊**：航空学报（首投）→ CIMS → 系统工程与电子技术
> **当前状态**：v0.2 草稿（约 99% 完工）
> **生成日期**：2026-06-17

---

## 📂 目录结构与文件导览

### 1. 论文章节（Markdown 草稿）

| 章节 | 文件 | 字数 | 状态 |
|---|---|---|---|
| 摘要 + 关键词中英对照 | `sections/abstract.md` | 290 字 / 280 words | v0.1 |
| §1 引言（5 段） | `sections/section1-introduction.md` | 1660 字 | v0.2 P0 已 review |
| §2 KG 构建（含 Tab. 1） | `sections/section2-kg.md` | 1840 字 | v0.2 P0+P1 已 review |
| §3 路径推理（含 Algo 1 + Tab. 2） | `sections/section3-path-reasoning.md` | 2280 字 | v0.2 P0+P1 已 review |
| §4 张量分解（含 3 公式） | `sections/section4-tensor.md` | 2090 字 | v0.2 P0+P1 已 review |
| §5 实验与分析（含 Tab. 3-7） | `sections/section5-experiments.md` | 6300 字 | v0.2 含 B1 + Full 真实数据 |
| §6 结论 | `sections/section6-conclusion.md` | 850 字 | v0.1 |
| **总计** | | **~15300 字** | **约 14.7 页（≤15 页限制）** |

### 2. 图（9 张）

| 图号 | 内容 | 后端 | 文件 |
|---|---|---|---|
| Fig. 1 | 双层本体示意图 | drawio | `figures/fig1-bilayer-ontology.{drawio,svg,png,pdf}` |
| Fig. 2 | KG 构建流水线 | drawio | `figures/fig2-kg-pipeline.*` |
| Fig. 3 | ReAct 路径推理流程 | drawio | `figures/fig3-path-reasoning-flow.*` |
| Fig. 4 | 知识查询 vs 推荐精排两类应用模式 | drawio | `figures/fig4-application-modes.*` |
| Fig. 5 | 3 阶张量结构 + CP 分解 | drawio | `figures/fig5-tensor-decomposition.*` |
| Fig. 6 | 粗筛—精排两阶段流程 | drawio | `figures/fig6-recall-rerank-pipeline.*` |
| Fig. 7 | CP 秩 R 灵敏性（双 Y 轴）| matplotlib | `figures/fig7-r-sensitivity.*` |
| Fig. 8 | 混合相似度 α 灵敏性 | matplotlib | `figures/fig8-alpha-sensitivity.*` |
| Fig. 9 | 三案例推理路径可视化 | drawio | `figures/fig9-case-study-traces.*` |

**3 套格式齐备**：SVG（投稿首选）/ PDF（备用）/ PNG @ 600dpi（草稿审阅）

drawio 源文件可在 draw.io Desktop 打开编辑；matplotlib 源文件在 `figures/make_figs_*.py`。

### 3. 表（7 张，全部嵌在 `.md` 章节中）

| 表号 | 内容 | 章节 | 数据状态 |
|---|---|---|---|
| Tab. 1 | KG 节点 + 关系组成（612 + 625）| §2.2.3 | ✅ 真实 |
| Tab. 2 | 4 个尺度律物理工具规格 | §3.2.1 | ✅ 真实 |
| Tab. 3 | FWMAV-QA Benchmark 题目构成 | §5.1.2 | ✅ 真实 (754 题) |
| Tab. 4 | 6 个基线方法概览 | §5.3 | ✅ 设计描述 |
| Tab. 5 | z-score 归一化方式对比 | §5.6.1 | ✅ 真实（E3）|
| Tab. 6 | 知识问答主实验（A 类 32 题）| §5.5.2 | ⚠️ B1 + Full 已填，B2-B6 待补 |
| Tab. 7 | 方案推荐主实验（B 类 16 题）| §5.5.3 | ⚠️ 同上 |

---

## 🧪 实验数据清单（已落盘）

### 路径：`experiment-results/`

| 文件 | 内容 | 大小 | 用途 |
|---|---|---|---|
| `e1_r_sensitivity.json` | E1 R∈{4-20} 完整数据 + 5 query × 7 R 详细 | 21 KB | §5.6.2 + Fig. 7 数据源 |
| `e2_alpha_sensitivity.json` | E2 α∈{0,0.2,0.4,0.6,0.8,1.0} 完整数据 | 18 KB | §5.6.3 + Fig. 8 数据源 |
| `e3_zscore_compare.json` | E3 per-feature vs global z-score | 5 KB | §5.6.1 Tab. 5 数据源 |
| `sensitivity_summary.md` | E1+E2+E3 汇总 markdown | 1.3 KB | 人类可读 |
| `b1_pure_llm_predictions.jsonl` | B1 baseline 48 题（每题 1 行 JSON）| 76 KB | Tab. 6 / Tab. 7 |
| `ablation_full_predictions.jsonl` | BioBridge-GraphRAG Full 48 题 | 145 KB | Tab. 6 / Tab. 7 |
| `eval_summary.json` | 所有系统指标对比 JSON | 10 KB | nature-reviewer 审阅用 |
| `eval_report.md` | 所有系统指标对比 markdown 报告 | 3 KB | 人类可读 |

### 待跑（已排队，~2 小时后完成）

```
ablation_no_bilayer_predictions.jsonl       w/o 双层本体（禁用生物层）
ablation_no_tools_predictions.jsonl         w/o 物理工具
ablation_no_tensor_predictions.jsonl        w/o 张量分解粗筛
ablation_no_pathreasoning_predictions.jsonl w/o 路径推理（仅粗筛）
```

---

## 💻 代码索引

### 核心实现 `biobridge/`

| 模块 | 文件 | 用途 |
|---|---|---|
| 物理工具集 | `biobridge/tools/physics_tools.py` | 4 个尺度律工具（hassanalian / shyy / strouhal / reynolds） |
| KG 检索工具 | `biobridge/tools/kg_tools.py` | 3 个 KG 工具（search_fwmav / search_organism / query_mimics_path） |
| 张量分解粗筛 | `biobridge/tools/tensor_recall.py` | TensorLy CP 分解 + KNN + 混合相似度 |
| 工具规格汇总 | `biobridge/tools/tool_specs.py` | OpenAI Function Calling JSON Schema + 调度入口 |
| LLM 客户端 | `biobridge/agent/llm_client.py` | OpenAI/DeepSeek/qproxy/mock 多后端封装 |
| ReAct 主循环 | `biobridge/agent/react_loop.py` | 算法 1 实现（与论文 1:1 对齐）|
| 消融变体 ReAct | `biobridge/agent/react_loop_ablation.py` | 工具子集限制版本 |

### 实验脚本 `biobridge/experiments/`

| 脚本 | 用途 |
|---|---|
| `run_sensitivity.py` | E1+E2+E3 张量超参敏感性实验 |
| `metrics.py` | EM / F1 / Hit@k / Entity Recall / Faithfulness 实现 |
| `baseline_b1_pure_llm.py` | B1 纯 LLM 直答 baseline |
| `run_biobridge.py` | BioBridge-GraphRAG Full 主跑 |
| `run_ablation.py` | 4 消融变体 + Full 五合一脚本 |
| `evaluate.py` | 统一评测 + 对比报告生成 |

### Demo `biobridge/demo/`

| 脚本 | 用途 |
|---|---|
| `run_demo.py` | 创新点 2 端到端 demo（3 查询） |
| `run_innov3_demo.py` | 创新点 3 端到端 demo（粗筛 + 精排）|
| `demo_results.json` | 3 demo 完整 trace（§5.7 案例研究数据源） |
| `innov3_demo_results.json` | 创新 3 demo trace |

---

## 🎯 论文 4 大贡献（与代码、数据、图、章节对应）

| 贡献 | 论文章节 | 代码 | 数据 | 图表 |
|---|---|---|---|---|
| 1. 双层本体 + 4 类 MIMICS | §2 | kg_tools | KG 含 612 节点 / 625 边 / 50 MIMICS×4 类分数 | Fig. 1, Tab. 1 |
| 2. 工具增强 ReAct 路径推理 | §3 | physics_tools + react_loop | demo_results.json | Fig. 3, 4, Algo 1, Tab. 2 |
| 3. 张量分解粗筛—精排范式 | §4 | tensor_recall | E1+E2+E3 + tensor_decomp_cache.npz | Fig. 5, 6, 7, 8, Tab. 5 |
| 4. FWMAV-QA Benchmark | §5.1 | fwmav-qa-benchmark/ | 754 题 jsonl + GitHub release + Zenodo DOI | Tab. 3 |

---

## 🔬 实验结果一览（截至 v0.2，B1 + Full 已完成）

### 主实验（48 题，B1 vs BioBridge Full）

| 指标 | B1（纯 LLM） | **BioBridge Full** | 提升 |
|---|---|---|---|
| Hit@1 | 0.542 | **0.646** | +10.4 pp |
| Hit@5 | 0.271 | **0.417** | +14.6 pp |
| Entity Recall | 0.389 | **0.528** | **+13.9 pp** |
| Faithfulness Lite | 0.107 | **0.187** | +8.0 pp |
| **A4 多跳推理 EntR** | **0.14** | **0.62** | **+48 pp（4.4 倍）** |
| 平均时延 (s/题) | 30.3 | 32.2 | +6% |
| 平均工具调用 | 0 | 5.5 | — |

### 超参敏感性（E1+E2+E3，已完成）

- **R**：R=12 是重构充分性 + 因子稳健性的均衡点（Top-3 Jaccard 在 R=12 处达 1.0 峰值）
- **α**：α=0.4 最优，α∈[0.2, 0.4] 是稳健区；纯 raw 与纯 CP 均失稳
- **z-score**：per-feature 重构误差 0.39 vs global 0.085；但 per-feature Top-1 一致性远好（论证选择正确）

---

## ⏳ 剩余工作（按优先级）

### 投稿前必做

| 任务 | 状态 | 预估时间 |
|---|---|---|
| 4 个消融变体跑完 → 填入 Tab. 8（§5.6.1 创新点级消融）| 排队中 | 2 小时（无人值守）|
| 8 个 BibKey 引用补到 Zotero（[Yang2018], [Trivedi2022], [Han2024], [Es2024RAGAS], [Chen2024BGE], [Yao2023], [Kossaifi2019], [Jia2021], [Wang2023UniNER], [Triantafyllou1991], [Kolda2009], [OpenAI2023], [Lewis2020], [Pennycuick1996], [Greenewalt1975], [Tennekes2009], [Shyy2013], [Hassanalian2017]，约 18 篇）| 部分待补 | 1 小时 |
| 用 nature-citation skill 转 GB/T 7714 格式 | 待做 | 30 分钟 |
| 全文统一 review（用 nature-reviewer skill）| 待做 | 1 小时 |

### 投稿前 nice-to-have

| 任务 | 备注 |
|---|---|
| 实现 B2–B6 baseline（VectorRAG / GraphRAG / LightRAG / ToG / HippoRAG）| 工程量大；首投后修订时再补 |
| B 类题相关度等级标注（用于 NDCG@5）| 需要 1-2 名同学协助 |
| 多 LLM 后端复现（DeepSeek-R1 离线）| 增强可重现性 |
| §5.5 题目数从 48 扩到 200+ | 增强统计显著性 |

---

## 📝 已知问题

1. **B 类题 Hit@k 恒为 0**——`gold_entities` 字段在 B 类题中未填；这不影响系统对比有效性（FaithfulnessLite 仍能区分），但建议补一轮 B 类题相关度标注以解锁 NDCG。
2. **48 题样本规模有限**——按 6 类各 8 题的分层抽样保证了类别覆盖，但单类内统计稳健性弱；首投后修订时考虑扩到 200+ 题。
3. **B2-B6 5 个基线尚未实现**——这是首投前最大的工程缺口；可在论文修订版中分批补全。

---

## 🔗 配套资源

- GitHub 仓库：[https://github.com/humble-long/MAV](https://github.com/humble-long/MAV)
- Zenodo DOI：[10.5281/zenodo.20726399](https://doi.org/10.5281/zenodo.20726399)（自动归档自 GitHub release v1.0）
- Neo4j KG 数据：随仓库 Cypher 导出
- LLM 推理后端：腾讯 qproxy（claude-sonnet-4-6） / DeepSeek-R1（备选）

---

## 📅 时间线

- 2026-06-16：选题确定（BioBridge-GraphRAG）+ 文献调研入库 22 篇
- 2026-06-16：KG 数据 P0/P1/P2 三阶段升级（39 FWMAV + 23 Organism + 50 MIMICS×4）
- 2026-06-16：FWMAV-QA Benchmark 构建（200 手写 + 554 模板生成 = 754 题）
- 2026-06-16：GitHub + Zenodo 公开
- 2026-06-17：4 创新点代码 demo 验证（含真实 LLM via qproxy）
- 2026-06-17：§1-6 全部初稿 + Fig. 1-9 + Tab. 1-7
- 2026-06-17：E1+E2+E3 + B1 + Full 真实实验数据闭环
- 2026-06-17：消融实验排队中
- **下一步**：消融数据填入 → 投稿前 review → 投航空学报

---

> 本 README 自动总结当前论文工作的全部素材、代码、数据与待办。建议每次 v0.x → v0.x+1 时同步更新。
