# BioBridge-GraphRAG 论文项目交接文档

> 给下一个 Claude 对话的指引。
> 写于 2026-06-20，基于至 v0.2 草稿的全部上下文。
> **如果你是新来的 Claude：先读完本文档，再决定问用户什么。不要立刻动手。**

---

## 1. TL;DR（60 秒入场）

王嘉龙（用户）是西工大航空学院硕士生，正在写一篇投**航空学报**的中文论文。论文方法叫 **BioBridge-GraphRAG**，是"知识图谱增强的仿生飞行器设计问答智能体"——用 KG 当外部记忆 + LLM 当智能体大脑 + 8 个工具（4 物理 + 3 KG + 1 张量）做 ReAct 推理。

**当前状态**：v0.2 草稿，约 99% 完工。docx 已生成（4.8 MB，9 图 + 7 表 + 4 OMML 公式）。最大缺口是基线少（只有 B1 纯 LLM）和题集只用了 754 题中的 48 题。

**最近的对话节奏**：用户在反复问 "**为什么 / 这是什么 / 我们做的有意义吗**"——你的任务更接近**陪他梳理论文的思路**而不是再写代码。沉得住气，先听他要什么。

---

## 2. 用户画像

| 项 | 详情 |
|---|---|
| 身份 | 西北工业大学航空学院硕士生 |
| 专业 | 仿生扑翼飞行器设计 |
| 工程能力 | Python 熟练；ML/LLM 概念懂但不深 |
| 论文经验 | 这是第一篇 EI 期刊投稿，对学术范式（dev/test 划分、消融实验等）相对生疏 |
| 目标期刊 | **航空学报**（首投）→ CIMS → 系统工程与电子技术 |
| 时间敏感度 | 中等——希望尽快投，但接受先扎实再投 |

---

## 3. 协作偏好（重要）

观察自这一长串对话：

| 偏好 | 具体表现 |
|---|---|
| **要例子，不要术语** | "你能用例子给我讲一下吗"——出现 5+ 次 |
| **要诚实，不要吹牛** | 经常追问"是不是言行不一致" "为什么只跑 48" |
| **要短，不要冗长** | 喜欢 ASCII 图 + 速查表；不喜欢段落式分析 |
| **要决策树，不要选项罗列** | "我推荐 X 因为 Y" 比 "你可以选 A/B/C" 更受欢迎 |
| **不要擅自推进** | 多次说"等一下" "我还没懂"——你要先确认理解再动手 |
| **不喜欢生成新文档** | 除非他明说，不要写 *.md 总结 |
| **中文为主** | 偶尔英文术语保留即可 |

**反例**——他**不喜欢**这种回复：
> "好的！让我深入分析一下您提出的精彩问题。这是一个非常有深度的话题..."

**正例**——他**喜欢**这种：
> "你抓到了一个真实的问题——这是论文当前最大的工程缺口。"
> 然后直接给具体数据 + 权衡 + 推荐。

---

## 4. 不可改的约定

### 4.1 论文标题（已敲定，不要再动）

- **中文**：知识图谱增强的仿生飞行器设计问答智能体（19 字）
- **英文**：A knowledge graph augmented agent for design question answering of bionic flapping-wing aircraft
- **方法名**：BioBridge-GraphRAG（保留——已发 Zenodo DOI）
  - "Bio" 指生物原型层、"Bridge" 指 4 类仿生映射

### 4.2 关键动词措辞

- **正确**："**设计并实现了**一种…智能体"
- **错误**："~~提出了~~一种…智能体"（动词与对象不搭配，已修）

### 4.3 文件同步约定

- **桌面 docx 是 primary**：`/Users/humble/Desktop/biobridge-graphrag-paper.docx`
- **papers/ docx 是 git 副本**：`/Users/humble/studyProject/MAV/papers/biobridge-graphrag-paper.docx`
- 改完桌面后 `cp` 一份到 papers/。改 papers/ 时反向也要同步。
- 用户偶尔会**手动用 Word 编辑桌面版**——动手前 verify 桌面版字节数。

### 4.4 安全约束（绝对红线 —— 不可 commit）

以下凭证是**绝对不能进 git**的（实际值见用户的 `.env` / 环境变量，或私下询问用户）：

| 凭证名 | 用途 | 环境变量 |
|---|---|---|
| Neo4j 密码 | KG 数据库连接 | `NEO4J_PASSWORD` |
| Zotero API key | Zotero MCP server | `ZOTERO_API_KEY` |
| GitHub PAT | gh CLI / 推送 | `GITHUB_TOKEN`（或本地 keychain）|
| 腾讯 qproxy API key | LLM 后端 | `OPENAI_API_KEY` |

所有脚本必须用 `os.environ.get(...)`。**不要把任何凭证值写进文件、commit 信息、或回复给用户**。如果发现历史 commit 含凭证，立刻告诉用户，让他 rotate。

---

## 5. 当前状态（v0.2 草稿）

### 5.1 已完工（99%）

| 资产 | 状态 |
|---|---|
| §1 引言 | ✅ v0.2，nature-reviewer P0 已修 |
| §2 KG 构建 | ✅ v0.2，含 Tab.1 |
| §3 路径推理 | ✅ v0.2，含 Algorithm 1 + Tab.2 |
| §4 张量分解 | ✅ v0.2，含 3 公式 |
| §5 实验与分析 | ✅ v0.2，B1 + Full + 4 ablation 数据齐 |
| §6 结论 | ✅ v0.1，4 段 |
| 摘要（中英）| ✅ v0.1，含真实数字 |
| Fig. 1-9 | ✅ 9 张图（drawio 7 张 + matplotlib 2 张）|
| Tab. 1-8 | ✅ 7 表 + 1 消融表 |
| docx 全文 | ✅ 4.8 MB，9 图嵌入 + 7 native table + 4 OMML |
| Excel 实验数据 | ✅ `experiment-results/biobridge-experiments.xlsx`（7 sheet）|
| 实验讲解文档 | ✅ `EXPERIMENTS-EXPLAINED.md`（712 行）|

### 5.2 实验已跑

| 实验 | 题量 | 系统数 | 状态 |
|---|---|---|---|
| 主实验（B1 vs Full）| 48 | 2 | ✅ |
| 创新点级消融 | 48 | 5（Full + 4 ablation）| ✅ |
| E1 R 敏感性 | 5 query | — | ✅ |
| E2 α 敏感性 | 5 query | — | ✅ |
| E3 z-score 对比 | 5 query | — | ✅ |
| §5.7 案例研究 | 3 案例 | 2 | ✅ 但单人评分 |

---

## 6. 已识别的真实漏洞（避免重复发现）

**这一节非常重要——下个 Claude 不要再"发现"一遍这些问题然后告诉用户**。用户已经知道。如果用户问起，告诉他这是已知的、列在这里。

### 6.1 题集利用率漏洞

- **现状**：FWMAV-QA Benchmark 公开了 **754 题**，但实验只用了 **48 题**（6.4%）
- **影响**：审稿人会问"754 是不是只为了好看"
- **改进路径**：A 类扩到全集 374 题（约 17h 跑批）；B 类受 6.2 限制保持 48 题
- **用户反应**：已意识到，未决定何时实施

### 6.2 B 类题 gold_entities 未标注

- **现状**：B 类（B1+B2 共 228 题）`gold_entities` 字段是空的
- **后果**：B 类 Hit@k / Entity Recall **全部为 0**——不是系统不行，是**评测器失灵**
- **当前替代**：Faithfulness Lite + §5.7 案例研究人工 5 分制
- **改进路径**：228 题 × 39 候选 = 8892 次相关度判断，需要 2-3 人协作 1-2 周
- **解锁后**：可计算 NDCG@5，B 类自动评测复活

### 6.3 基线只有 B1（最大工程缺口）

- **现状**：Tab.6/7 的对比基线列只有 B1，B2-B6（VectorRAG / GraphRAG / LightRAG / ToG / HippoRAG）全是 `<待填>`
- **改进推荐**：先补 B2 (VectorRAG) + B5 (ToG) ——一周左右；其余 3 个留修订版
- **用户反应**：上次问起补哪两个时给了选项，他没回答就转去问别的——**他可能没真正想好优先级**

### 6.4 张量超参在测试 query 上调

- **现状**：R=12 / α=0.4 是在 5 个 query 上选的，又在同 5 个 query 上报告——既调超参又当测试集
- **航空学报接受度**：通常宽容（KGQA 圈不严抠 dev/test）
- **顶会会扣分**：如要投顶会需补 dev/test 划分

### 6.5 单人评分

- §5.7 案例研究的 5 分制评分由用户自己打——缺独立专家
- 改进：找 3 名 FWMAV 同学独立打分 + 报 Cohen's kappa

---

## 7. 待办 + 优先级（按用户当前真实状态排）

| 优先级 | 任务 | 预估时间 | 备注 |
|---|---|---|---|
| ★★★ | **决定下一步主攻什么**（用户当前在思考） | 用户决策 | 不要替他决定 |
| ★★ | 补 B2 VectorRAG（BGE-M3 + FAISS）| 1 天工程 + 0.5h 跑 | 最快的基线 |
| ★★ | 扩 A 类到全集 374 题 | 17h 无人值守 | 与上一项可合并跑 |
| ★★ | 补 B5 ToG | 3-4 天工程 + 1h 跑 | 与图路径推理直接对比 |
| ★ | B 类 gold_entities 标注 | 2-3 人 × 2 周 | 解锁 NDCG@5 |
| ★ | 多 LLM 后端复现（DeepSeek-R1）| 4h | 增强可重现性 |
| ★ | 独立专家 5 分制评分 | 3 人 × 半天 | 解锁 Likert |
| ☆ | Reference 列表替换（[1]-[11] 模板 → 18+ 真实 BibKey）| 1h | 投稿前必做 |
| ☆ | 用 nature-citation skill 转 GB/T 7714 | 30 min | 投稿前必做 |
| ☆ | Algorithm 1 在 docx 里的 code block 排版 | 1-2h | 投稿前必做 |

---

## 8. 关键文件地图

### 8.1 论文文本

```
papers/
  ├── 01-论文大纲-航空学报.md          —— 总大纲，**已含历史归档**
  ├── README.md                        —— 项目入口（先读）
  ├── EXPERIMENTS-EXPLAINED.md         —— 实验全解读 712 行（先读 §1 §11）
  ├── HANDOFF.md                       —— 你正在读
  ├── biobridge-graphrag-paper.docx    —— git 副本（4.8 MB）
  └── sections/
      ├── abstract.md                  —— 摘要中英
      ├── section1-introduction.md
      ├── section2-kg.md
      ├── section3-path-reasoning.md
      ├── section4-tensor.md
      ├── section5-experiments.md      —— 最长，6300 字
      └── section6-conclusion.md
```

### 8.2 实验代码与数据

```
biobridge/
  ├── tools/
  │   ├── physics_tools.py     —— 4 个物理工具
  │   ├── kg_tools.py          —— 3 个 KG 工具
  │   ├── tensor_recall.py     —— 张量分解粗筛
  │   └── tool_specs.py        —— OpenAI Function Calling spec（**先看这个理解全套工具**）
  ├── agent/
  │   ├── llm_client.py        —— 多后端封装
  │   ├── react_loop.py        —— 主推理循环
  │   └── react_loop_ablation.py —— 消融变体（带 allowed_tools 过滤）
  └── experiments/
      ├── metrics.py           —— EM/F1/Hit@k/Faith 实现（**指标定义在这**）
      ├── run_sensitivity.py   —— E1+E2+E3
      ├── baseline_b1_pure_llm.py
      ├── run_biobridge.py
      ├── run_ablation.py      —— 5 变体一次跑完
      └── evaluate.py          —— 统一评测入口

papers/experiment-results/
  ├── eval_summary.json              —— 所有系统指标聚合
  ├── eval_report.md                 —— 人类可读
  ├── b1_pure_llm_predictions.jsonl
  ├── ablation_*_predictions.jsonl   —— 5 个变体预测结果
  ├── e1/e2/e3_*.json                —— 敏感性原始数据
  └── biobridge-experiments.xlsx     —— 7 sheet 数据汇总
```

### 8.3 数据集

```
papers/fwmav-qa-benchmark/
  └── data/
      ├── fwmav_qa_v2_final.jsonl    —— 754 题最终版
      ├── fwmav_qa_v1_754.jsonl      —— v1 历史
      └── batch_wjl_*.jsonl          —— 手写 + 模板生成原始批次
```

### 8.4 docx 批量处理脚本

```
papers/.docx-batch/
  ├── 01-header.json
  ├── 02-clean.json
  ├── 03-body-content.json
  ├── build_body.py / run_body.py    —— resident 模式批处理
  ├── run_figures.py / run_tables.py
  ├── run_format_fixes.py / run_fix_equations.py
  ├── run_56_ablation.py
  └── build_xlsx.py                  —— 生成 biobridge-experiments.xlsx
```

---

## 9. 环境与工具

| 工具 | 用途 | 入口 |
|---|---|---|
| **腾讯 qproxy** | LLM 后端（claude-sonnet-4-6）| `OPENAI_BASE_URL=https://qproxy.gtimg.com/v1` + 环境变量 KEY |
| **officecli** | 改 docx/xlsx | `officecli help <docx\|xlsx>` |
| **draw.io Desktop** | 改 figures（drawio 源文件）| brew 已装 |
| **nature-skills** | 论文写作辅助 | nature-writing / nature-reviewer / nature-figure / nature-citation |
| **drawio Skill** | 生成 drawio 文件 | jgraph/drawio-mcp 官方 |

### LLM 后端调用约定

```python
import os
from openai import OpenAI
client = OpenAI(
    base_url=os.environ["OPENAI_BASE_URL"],   # qproxy
    api_key=os.environ["OPENAI_API_KEY"],
)
# 模型名：claude-sonnet-4-6
```

---

## 10. 常用命令速查

### 改 docx

```bash
PAPER=/Users/humble/Desktop/biobridge-graphrag-paper.docx

# 找段落
officecli query "$PAPER" 'p:contains("某段开头文字")' --json

# 改段落
officecli set "$PAPER" '/body/p[@paraId=XXXXXXXX]' --prop 'text=新文本'

# 改完同步到 papers/
cp "$PAPER" /Users/humble/studyProject/MAV/papers/biobridge-graphrag-paper.docx
```

### 跑实验

```bash
# 主实验
python biobridge/experiments/baseline_b1_pure_llm.py
python biobridge/experiments/run_biobridge.py

# 消融
python biobridge/experiments/run_ablation.py

# 敏感性
python biobridge/experiments/run_sensitivity.py

# 评测
python biobridge/experiments/evaluate.py
```

### 同步检查

```bash
# 桌面 docx 与 papers/ 字节数应一致
ls -la /Users/humble/Desktop/biobridge-graphrag-paper.docx \
       /Users/humble/studyProject/MAV/papers/biobridge-graphrag-paper.docx
```

---

## 11. 推荐的开场对话

下个 Claude 接手时**第一条回复**建议这样问：

> 我已经读完 HANDOFF.md 和 EXPERIMENTS-EXPLAINED.md。你今天想推进哪一块？
>
> 1. **补基线**（B2 VectorRAG / B5 ToG）—— 上次卡在选哪两个
> 2. **扩题量**（A 类扩到 374 题）—— 与基线可合并跑
> 3. **B 类标注**（解锁 NDCG@5）—— 工程量大需要协作
> 4. **答辩准备**（继续梳理论文逻辑）—— 最近会话的方向
> 5. **投稿前琐事**（references / GB/T 7714 / Algorithm 排版）
> 6. **别的**

**不要主动**：
- 主动跑代码（先确认要跑什么）
- 主动改 docx（先确认要改什么）
- 主动写新 markdown 文档（用户不喜欢冗余文档）
- 主动 commit（每次都要明确确认）

**可以主动**：
- 读已有文件回答问题
- 用例子讲解概念
- 指出潜在问题（但不要重复 §6 已知漏洞）

---

## 12. 最近一次会话讨论焦点（2026-06-19~20）

按时间顺序：

1. **标题统一**：把残留的"基于 KG 与 LLM 的方法"全改成新风格
2. **病句修复**："提出 + 智能体" 改成 "设计并实现"
3. **MathType 安装**：用户问了，但被打断；最终没装（OMML 已够用）
4. **方法名讨论**：用户提出 BioBridge-GraphRAG 是不是该改名 → 决定保留 + 加词源解释
5. **生成 Excel**：用 officecli 生成了 7 sheet 的 `biobridge-experiments.xlsx`
6. **基线讨论**：讨论补 B2/B5，但用户没决定
7. **论文 SCOPE 反思**：用户连续问"我们的论文做了什么"、"为什么需要 KG"、"为什么需要双层本体"、"什么时候走粗筛精排" —— 是在为答辩或 cover letter 做准备
8. **实验逻辑梳理**：讨论了 754 vs 48、gold_entities、为什么需要实验、"B 类不分胜负"的真实含义
9. **指标定义补充**：用户截图问了 5 个指标各自含义 → 需要把 §1.5 速查表加到 EXPERIMENTS-EXPLAINED.md（**未做**）

**最有可能的下一步**：用户继续问概念性问题，或决定开工补基线/扩题量。

---

## 13. 信号灯

| 灯 | 含义 | 出现时怎么办 |
|---|---|---|
| 🔴 用户说 "我还不太懂" / "等一下" | **停下，再讲一次** | 换更具体的例子，不要前进 |
| 🟡 用户说 "是不是…" | **他在质疑** | 诚实回答，不要圆场 |
| 🟢 用户说 "可以补 / 现在做 / 你直接动手" | **可以推进** | 但仍 verify 范围 |
| 🟣 用户长沉默后问技术细节 | **他在准备答辩/写作** | 给他可直接复用的素材（句式、表格、图）|

---

> 写于 2026-06-20。如果三个月后下个对话来接手，先核对：
> 1. docx 字节数（看是否被人手动改过）
> 2. 当前 git branch + uncommitted changes
> 3. 实验数据有无更新
> 4. 是否已投稿（航空学报 / CIMS）
