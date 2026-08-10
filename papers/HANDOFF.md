# BioBridge-GraphRAG 论文项目交接文档

> 给下一个 Claude 对话的指引。
> 写于 2026-07-02，基于至 v0.2 草稿 + A/B 类全量实验完成 + Mavent v2 prompt 修复的全部上下文。
> **如果你是新来的 Claude：先读完本文档，再决定问用户什么。不要立刻动手。**

---

## 1. TL;DR（60 秒入场）

王嘉龙（用户）是西工大航空学院硕士生，正在写一篇投**航空学报**的中文论文。方法是 **BioBridge-GraphRAG**（代码内改名 Mavent 已讨论但未实施）——KG 增强的仿生飞行器设计 Q&A 智能体，ReAct Agent + 8 tools（4 物理 + 3 KG + 1 tensor recall）。

**这一轮对话核心产出**（2026-06-20 → 2026-07-02）：
- ✅ **KG 升级**：MIMICS 相似度从 4 维扩展到 5 维（Scale/Morphology/Kinematics/Aero/Functional），补 3 个字段（wing_pairs/has_tail/can_glide）
- ✅ **A 类全量实验完成**：5 系统 × 415 题推理 + LLM-as-Judge 评测
- ✅ **Mavent v2 prompt 修复**：修正"信鸽先查生物层"bug，A2 从 0.751 → 0.832
- ✅ **B 类评测体系全新设计**：graded relevance（0-3）自动打分 + 4 指标（NDCG@3 / R_strict / R_loose / P@1）
- ✅ **B 类全量实验完成**：5 系统 × 228 题推理 + 规则评测
- ⏳ **张量消融实验待跑**：现有 48 题旧数据不能用，需要新一轮 5 变体 × 415 题

**结论：主实验数据齐了，只差张量消融。可以开始写论文了。**

---

## 2. 用户画像

| 项 | 详情 |
|---|---|
| 身份 | 西北工业大学航空学院硕士生 |
| 专业 | 仿生扑翼飞行器设计 |
| 工程能力 | Python 熟练；ML/LLM 概念懂但不深 |
| 论文经验 | 第一篇 EI 期刊投稿 |
| 目标期刊 | 航空学报（首投）→ CIMS → 系统工程与电子技术 |
| 时间敏感度 | 中等——希望尽快投，但接受先扎实再投 |

---

## 3. 协作偏好（重要）

| 偏好 | 具体表现 |
|---|---|
| **要例子，不要术语** | "你能用例子给我讲一下吗"——出现 5+ 次 |
| **要诚实，不要吹牛** | 经常追问"是不是言行不一致" |
| **要短，不要冗长** | 喜欢 ASCII 图 + 速查表 |
| **要决策树，不要选项罗列** | "我推荐 X 因为 Y" 比 "你可以选 A/B/C" 更受欢迎 |
| **不要擅自推进** | 多次说"等一下" "我还没懂" |
| **不喜欢生成新文档** | 除非他明说，不要写 *.md 总结 |
| **中文为主** | 偶尔英文术语保留即可 |

**反例**：
> "好的！让我深入分析一下您提出的精彩问题..."

**正例**：
> "你抓到了一个真实的问题——这是论文当前最大的工程缺口。"
> 然后直接给具体数据 + 权衡 + 推荐。

---

## 4. 不可改的约定

### 4.1 论文标题（已敲定）

- **中文**：知识图谱增强的仿生飞行器设计问答智能体（19 字）
- **英文**：A knowledge graph augmented agent for design question answering of bionic flapping-wing aircraft
- **方法名**：BioBridge-GraphRAG（保留——已发 Zenodo DOI）
- **代码内改名 Mavent**：已讨论但**尚未实施**，不要擅自改名

### 4.2 安全约束（绝对红线）

以下凭证**绝对不能进 git**（值已由用户私下提供，放在环境变量中）：

| 凭证名 | 用途 | 环境变量 |
|---|---|---|
| 腾讯 qproxy API key | LLM 后端 | `OPENAI_API_KEY` |
| qproxy base URL | `https://qproxy.gtimg.com/v1` | `OPENAI_BASE_URL` |
| LLM 模型名 | 推理: `deepseek-v4-pro-official` / 评测: `claude-sonnet-4-6` | `OPENAI_MODEL` |
| Neo4j 密码 | KG 数据库连接 | `NEO4J_PASSWORD` |

所有脚本必须用 `os.environ.get(...)`。**不要把任何凭证值写进文件、commit 信息、或回复给用户**。

---

## 5. 当前实验状态（★ 核心）

### 5.1 A 类实验（415 题）✅ 全部完成

**推理阶段**：

| 系统 | 脚本 | 输出 | 延迟 |
|---|---|---|---|
| B1 Pure LLM | `baseline_b1_pure_llm.py` | `b1_pure_llm_predictions.jsonl` | 28.6s/题 |
| B2 VectorRAG | `baseline_b2_vector_rag.py` | `b2_vector_rag_predictions.jsonl` | 21.4s/题 |
| B3 KG-RAG | `baseline_b3_kg_rag.py` | `b3_kg_rag_predictions.jsonl` | 17.9s/题 |
| B4 ToG | `baseline_b4_tog.py` | `b4_tog_predictions.jsonl` | 41.6s/题 |
| **Mavent v2** | `run_biobridge.py` | `biobridge_predictions.jsonl` | 32.2s/题 |

**评测阶段**（LLM-as-Judge，claude-sonnet-4-6 作 judge）：

```
系统            A2查询    A3对比    A4推理    延迟
────────────────────────────────────────────────
B1 Pure LLM    0.269    0.321    0.223    28.6s
B2 VectorRAG   0.835    0.850    0.766    21.4s
B3 KG-RAG      0.845    0.873    0.388    17.9s
B4 ToG         0.771    0.811    0.250    41.6s
Mavent v2      0.832    0.881    0.827★   32.2s
```

**关键发现**：
- **A4 推理是 Mavent 的杀手场景**：0.827 vs 次优 0.766（B2 VecRAG）—— 差距 0.061
- **A2/A3 三家（Mavent/B2/B3）持平**：都在 0.83~0.88 区间
- **B4 ToG 全线垫底**：抽象约束题缺 KG 种子节点，beam search 失效
- **B1 Pure LLM 拒答严重**：141/415（34%）拒答，A4 拒答率高达 48%

### 5.2 B 类实验（228 题）✅ 全部完成

**注意与 A 类的区别**：B 类不用 LLM-as-Judge，用**规则评测 + graded relevance**。

**新数据集**：`papers/fwmav-qa-benchmark/data/fwmav_qa_v2_b_graded.jsonl`
- 每道 B 题给全部 39 个 FWMAV 打 relevance（0-3 分）
- 规则打分脚本：`biobridge/experiments/grade_b_relevance.py`
- rel=3 全部硬约束满足 + 软约束匹配
- rel=2 全部硬约束满足但软约束不匹配
- rel=1 违反 1 个硬约束
- rel=0 违反 2+ 硬约束或严重越界

**指标（4 个）**：
- **NDCG@3 (graded 0-3)**：推荐排序质量
- **Recall_strict@3**：命中 rel=3 样机的比例
- **Recall_loose@3**：命中 rel≥2 样机的比例
- **P@1**：第一推荐是不是 rel=3

**推理阶段**（用 `--data /tmp/b_only.jsonl`，产出到 `*_b_predictions.jsonl`）：

| 系统 | 输出 |
|---|---|
| B1 | `b1_b_predictions.jsonl` |
| B2 | `b2_b_predictions.jsonl` |
| B3 | `b3_b_predictions.jsonl` |
| B4 | `b4_b_predictions.jsonl` |
| Mavent | `biobridge_b_predictions.jsonl` |

**评测结果**：

```
系统            NDCG@3    R_strict  R_loose   P@1     B1_NDCG   B2_NDCG
────────────────────────────────────────────────────────────────────
B1 Pure LLM    0.570    0.513    0.538    0.588    0.689    0.463
B2 VectorRAG   0.839★   0.834★   0.806★   0.829★   0.926    0.760★
B3 KG-RAG      0.508    0.572    0.392    0.605    0.483    0.530
B4 ToG         0.452    0.504    0.365    0.513    0.459    0.445
Mavent         0.696    0.702    0.703    0.640    0.873    0.537
```

**关键发现**：
- **B2 VectorRAG 全面赢** —— 语义向量检索对推荐题极有效
- **Mavent B1 强 (0.873)**，但 B2 弱 (0.537) —— 硬约束多字段过滤不是 ReAct 强项
- **B3/B4 R_loose 远低于 R_strict** —— 推荐过于激进，中间地带覆盖不足

### 5.3 KG 结构（P0-P3 完成）

**P0-P2 之前已完成**（详见 KG-STRUCTURE.md）：当前实测 609 节点 / 622 关系（HANDOFF 初版记 612/625，之后库有微调，以 `biobridge/kg_backup/` 快照为准）。

**P3（本轮新增）**：MIMICS 相似度从 4 维扩展到 5 维

补充脚本：`papers/fwmav-qa-benchmark/scripts/p2_3_supplement_wing_props.py`
- 给 39 FWMAV + 23 Organism 加 3 字段：`wing_pairs` / `has_tail` / `can_glide`

打分脚本更新：`papers/fwmav-qa-benchmark/scripts/p1_1_mimics_score.py`
- **旧 4 维**：Scale / Morphology(布尔) / Kinematics / Aero(速度代理)
- **新 5 维**：
  - **Scale**：重量 + 翼展（对数距离）
  - **Morphology**：wing_pairs + has_tail + AR（三合一，Shyy 尺度律推 AR）
  - **Kinematics**：扑频
  - **Aero**：Reynolds 数 + Strouhal 数（弦长≈翼展/4）
  - **Functional**：can_hover + can_glide

**修复效果**：
- 旧 aero 满分率 74%（用速度代理）→ 新 aero 满分率 16%（Re+St 精确）
- 旧 morphology 只有 0/1 → 新 morphology 是连续值，无虚高满分

### 5.5 换电脑 / Neo4j 数据迁移（★ 必看）

**核心坑**：图谱只存在 Neo4j 数据库里，**git 里的 p0/p1/p2 脚本无法从空库重建**——它们是 `MATCH` 已有节点补属性（节点不存在直接跳过），不负责创建原始种子图。所以换电脑不能只靠 clone。

**已做的备份**：整库快照到 `biobridge/kg_backup/`（已进 git）：
- `nodes.jsonl`（609 节点）+ `rels.jsonl`（622 关系）
- `export_kg.py` / `import_kg.py`：APOC-free 全图导出/导入（只用 neo4j 驱动）

**新电脑恢复步骤**：
```bash
git clone https://github.com/humble-long/MAV.git && cd MAV
pip install neo4j
# 装并启动 Neo4j，设好任意新密码
export NEO4J_PASSWORD=<新库密码>
python3 biobridge/kg_backup/import_kg.py     # 空库直接跑；非空需加 --wipe
```
导入用旧 elementId 连关系、再清临时标记，节点/关系/属性与原库一致。密码与数据无关，导入脚本不依赖旧密码。

**更新备份**（以后又改了图谱）：旧电脑 `NEO4J_PASSWORD=<pwd> python3 biobridge/kg_backup/export_kg.py` 重跑一次再 commit 即可。

> 当前旧电脑 Neo4j 密码见环境变量约定（§4.2）；不要写进任何文件或 commit。


### 5.4 Mavent v2 prompt 修复（本轮关键）

**发现的 Bug**：Mavent v1 遇到"信鸽的起飞重量"这类题目，因为 system prompt 说"涉及生物原型必先调 search_organism"，会先查生物层的鸽子（返回 200-500g），而不是查工程样机层的信鸽（280g），答错。

**修复**：`biobridge/agent/llm_client.py` 的 SYSTEM_PROMPT 里改成：
- 遇到具体样机名称必须先调 search_fwmav
- search_organism 只在明确询问生物参数或需要仿生参考时调用

**效果**：Mavent A2 从 0.751 → 0.832，工具调用平均从 6.9 → 5.6/题（不再乱调 organism）

### 5.5 关键 max_tokens 设置（易踩坑）

| 场景 | 变量 | 值 | 原因 |
|---|---|---|---|
| Mavent 推理 | `MAX_OUTPUT_TOKENS` | 8192（默认）| ReAct 需要长思考链 |
| A 类 Judge | `MAX_OUTPUT_TOKENS` | 4096 | claude-sonnet-4-6 输出 JSON |
| B 类标注（annotate_b_relevance）| `max_tokens` 硬编码 1500 | - | claude 有中文双引号问题（已修复） |

**踩坑记录**：minimax-m2.7 是 reasoning model，30000 token 全被 reasoning 阶段吃掉，content 输出为空——**不要用 minimax 作 judge**。

---

## 6. 下一步：待做的工作

### 6.1 张量消融实验 ⏳（论文的关键补充）

**现状**：现有 `ablation_*_predictions.jsonl` 只有 48 题（旧数据，含 A1，用旧 EM/F1 评测）。**不能用于论文**。

**5 个消融变体**（在 `biobridge/agent/react_loop_ablation.py`）：

| 变体 | 说明 |
|---|---|
| `full` | 完整 Mavent |
| `no_bilayer` | 去掉生物层 |
| `no_tools` | 去掉 4 个物理工具 |
| `no_tensor` | 去掉张量粗筛 |
| `no_pathreasoning` | 只用张量 + 简单格式化 |

**推荐方案**（用户在 6-24 讨论过，倾向选 B）：
- **选 A**：全部 5 变体 × 415 题（12-15 小时）
- **选 B（推荐）**：只跑 no_tensor + no_tools 两个关键变体（5-6 小时），对比 Full 得张量和物理工具的独立贡献

**跑命令模板**（用户还没确认最终方案，等他决定）：
```bash
NEO4J_PASSWORD=<pwd> \
OPENAI_BASE_URL=https://qproxy.gtimg.com/v1 \
OPENAI_API_KEY=<key> \
OPENAI_MODEL=deepseek-v4-pro-official \
python3 -u biobridge/experiments/run_ablation.py --variant no_tensor
```

### 6.2 论文写作

**主实验数据齐了**（A + B），可以开始起草：
- **§4.2 A 类实验**：5 系统 × 3 指标（A2/A3/A4）主表 + A4 单独柱状图
- **§4.3 B 类实验**：5 系统 × 4 指标（NDCG/R_strict/R_loose/P@1）+ B1/B2 分开子表
- **§4.4 消融实验**（等张量消融跑完再写）

**用户曾表达过的写作偏好**：
- 论点 1：A4 推理任务需要工具增强（0.223→0.827 的跳变是最强证据）
- 论点 2：ToG 在扑翼机 QA 上不适合（负面证据也是贡献）
- 论点 3：不同任务需要不同架构（诚实承认 B 类 Mavent 不如 VecRAG）

---

## 7. 已知漏洞（不要再重新发现）

### 7.1 单人评分（案例研究）

案例研究部分若涉及 5 分制打分，由用户自己打，缺独立专家。

### 7.2 Mavent 改名未实施

代码/docs 内所有 BioBridge-GraphRAG 引用尚未统一改名到 Mavent。

### 7.3 张量超参在测试 query 上调（需修）

R=12 / α=0.4 在 5 个 query 上选又在同 5 个 query 上报告——留在论文里的老 caveat。跑消融时可能需要 hold-out。

### 7.4 B2 硬约束题 Mavent 不占优

B2 类多字段联合过滤（"翼展≤250mm+重量≤30g+悬停+相机"），Cypher 一句 WHERE 就能搞定，Mavent ReAct 反而绕路。这个 finding **在论文里应该主动承认**，不要藏。

### 7.5 baseline 脚本已改支持 A+B（已完成）

5 个脚本的过滤条件都改成了 `.startswith(("A", "B"))`——之前只跑 A 类。

---

## 8. 关键文件地图

```
biobridge/experiments/
  ├── baseline_b1_pure_llm.py       —— B1 纯 LLM
  ├── baseline_b2_vector_rag.py     —— B2 VectorRAG + FAISS
  ├── baseline_b3_kg_rag.py         —— B3 KG-RAG（Cypher）
  ├── baseline_b4_tog.py            —— B4 ToG beam search
  ├── run_biobridge.py              —— Mavent 主系统
  ├── run_ablation.py               —— 消融实验（待跑新一轮）
  ├── evaluate.py                   —— 统一评测入口
  ├── llm_judge.py                  —— A 类 LLM-as-Judge（claude-sonnet-4-6）
  ├── b_metrics.py                  —— B 类 4 指标计算（graded NDCG + R_strict + R_loose + P@1）
  ├── grade_b_relevance.py          —— B 类 graded relevance 自动打分
  ├── annotate_b_relevance.py       —— B 类硬约束标注（旧版）
  ├── repair_b_annotation.py        —— annotate 失败样本降级修复
  └── metrics.py                    —— 旧 EM/F1（已废弃）

biobridge/agent/
  ├── llm_client.py                 —— LLM 客户端 + SYSTEM_PROMPT（v2 已修复）
  ├── react_loop.py                 —— ReAct 主循环
  └── react_loop_ablation.py        —— 消融变体 ReAct 变种

biobridge/tools/
  ├── physics_tools.py              —— 4 物理工具
  ├── kg_tools.py                   —— 3 KG 工具（返回 5 维相似度）
  └── tensor_recall.py              —— 张量分解粗筛

papers/fwmav-qa-benchmark/data/
  ├── fwmav_qa_v2_final.jsonl       —— 754 题原始数据集
  ├── fwmav_qa_v2_b_annotated.jsonl —— B 类原 gold + hard_constraints
  └── fwmav_qa_v2_b_graded.jsonl    —— ★ B 类 39 FWMAV × 228 题的 graded relevance

papers/fwmav-qa-benchmark/scripts/
  ├── p1_1_mimics_score.py          —— MIMICS 5 维打分（已更新）
  ├── p2_3_supplement_wing_props.py —— 补 wing_pairs/has_tail/can_glide

papers/experiment-results/
  ├── b1_pure_llm_predictions.jsonl —— A 类 415 题 × 5 系统
  ├── b2_vector_rag_predictions.jsonl
  ├── b3_kg_rag_predictions.jsonl
  ├── b4_tog_predictions.jsonl
  ├── biobridge_predictions.jsonl   —— Mavent v2 A 类结果
  ├── b1_b_predictions.jsonl        —— B 类 228 题 × 5 系统
  ├── b2_b_predictions.jsonl
  ├── b3_b_predictions.jsonl
  ├── b4_b_predictions.jsonl
  ├── biobridge_b_predictions.jsonl
  ├── ablation_*_predictions.jsonl  —— 旧 48 题（不能用）
  ├── vector_rag_index.faiss        —— B2 的 FAISS 索引
  ├── vector_rag_index.json
  ├── eval_summary.json             —— B 类最新评测（覆盖了 A 类的旧摘要）
  └── eval_report.md                —— B 类最新报告

papers/
  ├── HANDOFF.md                    —— 你正在读
  ├── EXPERIMENTS-EXPLAINED.md      —— 实验全解读（可能已过期）
  ├── KG-STRUCTURE.md               —— KG 结构说明
  └── biobridge-graphrag-paper.docx —— git 副本

桌面 docx（primary）:
  /Users/humble/Desktop/biobridge-graphrag-paper.docx
```

---

## 9. LLM 调用配置

**推理时**（跑 baseline / Mavent）：
```bash
export OPENAI_BASE_URL=https://qproxy.gtimg.com/v1
export OPENAI_API_KEY=<qproxy key>
export OPENAI_MODEL=deepseek-v4-pro-official
export MAX_OUTPUT_TOKENS=8192
export NEO4J_PASSWORD=<pwd>
```

**评测时**（跑 evaluate.py）：
```bash
export OPENAI_MODEL=claude-sonnet-4-6      # ← 换成 claude 作 judge
export MAX_OUTPUT_TOKENS=4096
```

**qproxy 特点**（易踩坑）：
- 不支持 `response_format={"type":"json_object"}`
- Claude 系列的 JSON 输出可能被 markdown 包裹（```json...```）——`llm_judge.py` 已用正则提取
- Claude 输出中文引号可能不转义，破坏 JSON——注意
- **不能用 minimax-m2.7 作 judge**（reasoning model，content 空）

---

## 10. 信号灯

| 灯 | 含义 | 怎么办 |
|---|---|---|
| 🔴 用户说 "我还不太懂" / "等一下" | 停下，换例子再讲 | 不要前进 |
| 🟡 用户说 "是不是…" | 他在质疑 | 诚实回答 |
| 🟢 用户说 "可以 / 现在做 / 你直接动手" | 可推进 | 但仍 verify 范围 |
| 🟣 用户长沉默后问技术细节 | 在准备答辩/写作 | 给可直接复用的素材 |

---

## 11. 不要主动做的事

- 不要主动跑代码（先确认要跑什么）
- 不要主动改 docx（先确认要改什么）
- 不要主动写新 markdown 文档
- 不要主动 commit（每次都要确认）
- 不要重复发现 §7 的已知漏洞
- 不要给方法改名 Mavent（尚未实施）
- **不要用 minimax 作 judge**（会全部 score=0）
- **不要用 4 维旧 MIMICS 打分**（已升级到 5 维，别退化）
- **不要跑 baseline 时忘记设 `MAX_OUTPUT_TOKENS`**（Mavent 会被截断，工具调用 JSON 不完整）

---

## 12. 最后一句

**下次对话首先要确认的三件事**：
1. 张量消融实验要跑吗？跑 A 方案（全 5 变体）还是 B 方案（no_tensor + no_tools）？
2. 论文写作从哪里开始？§4 实验章节还是先修 §3 方法？
3. Mavent 是否需要 v3 修复？（B2 类硬约束题的短板可以尝试改进）
