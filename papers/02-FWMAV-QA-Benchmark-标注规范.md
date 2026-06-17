# FWMAV-QA Benchmark 标注规范 v1.0

> **目标**：构建 800 题中文测评数据集，作为 BioBridge-GraphRAG 论文 Section 5 的实验基础。
> **完成时间**：2026.06.20–2026.07.31（约 6 周）
> **总工作量**：单人约 80 小时；建议 2-3 人协作
> **最终交付**：JSONL 格式数据集 + 评分脚本 + GitHub release（含 Zenodo DOI）

---

## 1 数据集定位

### 1.1 它是什么
一套用来**测试问答与推荐系统在仿生飞行器领域表现**的"考卷"，包含 800 道题 + 标准答案 + 自动评分代码。

### 1.2 它在论文里的作用
- 论文 Section 5 的**主实验数据**——比 BioBridge 与 6 个基线方法的好坏
- 论文的**第 4 个隐性贡献**——开源后给后续研究者使用
- 你**毕设大论文也复用**——一份数据两次用

### 1.3 它在领域里的稀缺性
现有公开 KGQA 数据集（HotpotQA / MuSiQue / GraphRAG-Bench / Mind the Query）**无一覆盖航空 / MAV / 仿生飞行器**——这是你的差异化卖点。

---

## 2 题目类型与数量分配

### 2.1 三大类（共 800 题）

```
FWMAV-QA Benchmark (800 题)
│
├── A. 知识查询类（KQ, Knowledge Query）         600 题
│   ├── A1. 单跳·定义类                          150 题
│   ├── A2. 单跳·属性类                          150 题
│   ├── A3. 多跳·对比类                          150 题
│   └── A4. 多跳·推理类                          150 题
│
├── B. 方案推荐类（DR, Design Recommendation）   200 题
│   ├── B1. 简单约束（1-2 个性能指标）           100 题
│   └── B2. 复杂约束（3+ 个性能指标 + 任务场景） 100 题
│
└── C. 混合查询类（HQ, Hybrid Query）            包含在 A4 中
        （从生物原型反推工程方案，跨域推理）
```

### 2.2 难度分级

每道题打 **1-3 级难度**：
- **难度 1（基础）**：直接从 KG 单节点属性可答
- **难度 2（中等）**：需 2-3 跳推理或调用 1 个工具
- **难度 3（困难）**：需 4 跳以上 + 多工具协同 / 跨域生物-工程映射

每个子类的难度分布建议 **1:2:1**（基础:中等:困难）。

---

## 3 JSON Schema 定义

### 3.1 知识查询类 schema（A 类）

```json
{
  "id": "kq_001",
  "category": "A1",
  "type": "知识查询·单跳·定义",
  "difficulty": 1,
  "question": "什么是 Strouhal 数？",
  "gold_answer": "Strouhal 数（St）是描述非定常流动周期性的无量纲数，定义为 St = fA/U，其中 f 为扑动频率、A 为扑动幅值、U 为来流速度。扑翼飞行器最优 Strouhal 数通常落在 0.2-0.4 区间。",
  "gold_entities": ["Strouhal 数"],
  "gold_relations": ["定义", "公式", "典型取值范围"],
  "gold_path": ["StrouhalNumber → DEFINED_BY → Formula(St=fA/U) → TYPICAL_RANGE → [0.2,0.4]"],
  "expected_hops": 1,
  "tool_call_required": [],
  "support_docs": [
    {
      "title": "Wing-beat frequency of birds in steady cruising flight",
      "doi": "10.1242/jeb.199.7.1613",
      "snippet": "..."
    }
  ],
  "source": "Pennycuick 1996; Triantafyllou 1991",
  "annotator": "wjl",
  "verified_by": "tongmen_a",
  "annotation_date": "2026-07-05"
}
```

### 3.2 方案推荐类 schema（B 类）

```json
{
  "id": "dr_042",
  "category": "B2",
  "type": "方案推荐·复杂约束",
  "difficulty": 3,
  "task_constraints": {
    "endurance_min": 300,
    "endurance_unit": "s",
    "payload_max": 50,
    "payload_unit": "g",
    "mission_type": "outdoor_cruise",
    "wingspan_max": 80,
    "wingspan_unit": "cm"
  },
  "question": "30 km 续航 + 50 g 载重 + 室外巡航任务，推荐参考哪些样机？请按推荐度排序。",
  "gold_recommendations": [
    {
      "rank": 1,
      "vehicle": "DelFly Nimble",
      "match_score": 0.87,
      "reasoning": "续航 9 min 接近目标，载重容差 30 g 可适配，机翼布局成熟"
    },
    {
      "rank": 2,
      "vehicle": "AVITRON",
      "match_score": 0.81,
      "reasoning": "续航略低但室外巡航验证充分"
    },
    {
      "rank": 3,
      "vehicle": "Robird",
      "match_score": 0.76,
      "reasoning": "载重充裕但能耗较高"
    }
  ],
  "expected_recall_top10": ["DelFly Nimble", "AVITRON", "Robird", "Festo SmartBird", "BionicFlyingFox", "..."],
  "tool_call_required": ["hassanalian_weight", "shyy_scaling_law"],
  "support_docs": [
    {"title": "DelFly Nimble specifications", "doi": "10.1109/...", "snippet": "..."}
  ],
  "annotator": "wjl",
  "verified_by": "tongmen_b",
  "annotation_date": "2026-07-12"
}
```

### 3.3 混合查询类 schema（C 类，归入 A4 难度 3）

```json
{
  "id": "kq_452",
  "category": "A4",
  "type": "混合·生物-工程跨域",
  "difficulty": 3,
  "question": "参考蜂鸟原型设计一架续航 30 km 的扑翼机是否可行？给出分析。",
  "gold_answer": "不可行。蜂鸟体重 4 g、翼展 9 cm、扑频 50 Hz，按 Hassanalian 公式估算 30 km 续航需要起飞重量 35 g 以上，约为蜂鸟原型的 8.7 倍。即使按尺度律放大，扑频需降至 ~17 Hz、翼展放大至 ~26 cm，已超出蜂鸟原型的运动学参数边界。建议参考 Festo SmartBird（量级匹配的中型仿生鸟）。",
  "gold_entities": ["Hummingbird", "Nano Hummingbird", "Festo SmartBird"],
  "gold_path": [
    "Hummingbird → MIMICS-scale → Nano Hummingbird (mass=19g)",
    "TaskConstraint(endurance=30km, payload=50g) → hassanalian_weight → 35g",
    "Comparison(Nano Hummingbird, 35g) → mismatch",
    "shyy_scaling_law → suggest larger prototype",
    "Recommendation → Festo SmartBird"
  ],
  "expected_hops": 4,
  "tool_call_required": ["hassanalian_weight", "shyy_scaling_law"],
  "support_docs": ["..."],
  "annotator": "wjl",
  "verified_by": "tongmen_c",
  "annotation_date": "2026-07-18"
}
```

---

## 4 标注流程（4 步法）

### Step 1：题目种子（约 3 天）
- 从 Zotero `小论文-GraphRAG-FWMAV` collection 中选择 30-40 篇文献
- 每篇文献抽 2-3 个潜在问题点（标书签）
- 同时从你毕设的"世界仿生设计图鉴"挑 30-50 个机型作为推荐目标库

### Step 2：题目生成（约 2 周）
- 标注员**根据文献内容人工撰写**问题与答案
- 不能用 ChatGPT 直接生成（避免泄露幻觉）
- 但**可以**用 LLM 协助校对语法、扩展同义改写
- 建议比例：人工 70% + LLM 协助 30%

### Step 3：交叉校验（约 1.5 周）
- 每道题至少 2 人独立标注
- 不一致的题目走第三人仲裁
- 计算 Inter-Annotator Agreement（IAA）：
  - 知识查询类：Cohen's Kappa（答案语义相似度 > 0.8 视为一致）
  - 推荐类：Top-3 列表的 Jaccard 相似度 > 0.6 视为一致
  - **目标 IAA ≥ 0.75**（合格阈值）

### Step 4：自动校验（约 3 天）
- 脚本检查 schema 完整性
- 脚本检查支持文献是否在 Zotero 库中存在
- 脚本检查工具调用类问题的工具列表非空
- 通过率 100% 后冻结数据集

---

## 5 评分规则（实验时怎么用这套数据）

### 5.1 知识查询类指标

| 指标 | 计算方式 | 工具 |
|---|---|---|
| **Hit@k** | gold_entities 至少有 1 个出现在 Top-k 检索结果中即得 1 分 | 自写脚本 |
| **Exact Match (EM)** | 答案与 gold_answer 完全匹配（精确字符串）| 自写脚本 |
| **F1** | token 级 F1 | HuggingFace evaluate |
| **Faithfulness** | 答案中的事实是否被 support_docs 支持 | RAGAS [Zotero: GXZ8QMH4] |
| **Context Recall** | gold support_docs 中被检索到的比例 | RAGAS |
| **Path Accuracy** | 模型推理路径与 gold_path 重合度 | 自写脚本（多跳类专用）|

### 5.2 方案推荐类指标

| 指标 | 计算方式 |
|---|---|
| **NDCG@k** (k=3, 5, 10) | 标准 NDCG 公式，relevance 取 gold_recommendations 的 rank 倒数 |
| **MRR** | 第一个正确推荐的倒数排名 |
| **Recall@10** | gold 列表中被召回的比例（衡量粗筛能力）|
| **物理可行性通过率** | 推荐结果用 hassanalian_weight 校验是否合理（自定义指标）|

### 5.3 整体可解释性指标
- **推理路径完整性**：人工 5 分制 Likert 量表
- **文献溯源准确率**：节点 → PDF 段落对齐率（自写脚本 + 人工抽查）

---

## 6 数据集构建分工建议

### 6.1 角色分配（3 人协作示例）
- **王嘉龙（你）**：A 类知识查询 350 题 + 全部 schema 设计 + 评分脚本
- **同门 X**：A 类剩余 250 题 + B 类 100 题
- **同门 Y**：B 类 100 题 + 全数据集交叉校验 + IAA 计算

### 6.2 单人估时
- 每道题平均 6-10 分钟（含查文献、写答案、填 schema）
- 800 题 × 8 分钟 ≈ 107 小时
- 3 人分摊每人约 35-40 小时

### 6.3 实施时间线
| 周 | 工作 |
|---|---|
| Week 1（6.20–6.26）| 标注规范评审 + 题目种子收集 + 工具脚本开发 |
| Week 2-3（6.27–7.10）| A 类 600 题主标注 |
| Week 4（7.11–7.17）| B 类 200 题主标注 |
| Week 5（7.18–7.24）| 交叉校验 + IAA 计算 |
| Week 6（7.25–7.31）| 仲裁修订 + 自动校验 + GitHub release |

---

## 7 自动校验脚本（伪代码）

```python
# fwmav_qa_validate.py
import json, re
from pathlib import Path

REQUIRED_FIELDS_A = {
    "id", "category", "type", "difficulty", "question",
    "gold_answer", "gold_entities", "expected_hops",
    "support_docs", "annotator", "annotation_date"
}
REQUIRED_FIELDS_B = {
    "id", "category", "type", "difficulty", "question",
    "task_constraints", "gold_recommendations",
    "expected_recall_top10", "tool_call_required",
    "annotator", "annotation_date"
}

def validate(item):
    errors = []
    cat = item.get("category", "")
    required = REQUIRED_FIELDS_B if cat.startswith("B") else REQUIRED_FIELDS_A
    missing = required - item.keys()
    if missing:
        errors.append(f"missing: {missing}")
    if not (1 <= item.get("difficulty", 0) <= 3):
        errors.append("difficulty out of range")
    if cat.startswith("B"):
        if len(item.get("gold_recommendations", [])) < 1:
            errors.append("gold_recommendations empty")
        if len(item.get("expected_recall_top10", [])) < 5:
            errors.append("recall_top10 too short")
    return errors

if __name__ == "__main__":
    with open("data/fwmav_qa.jsonl") as f:
        items = [json.loads(line) for line in f]
    bad = [(it["id"], validate(it)) for it in items if validate(it)]
    print(f"Total: {len(items)}, errors: {len(bad)}")
    for itid, errs in bad[:20]:
        print(f"  {itid}: {errs}")
```

---

## 8 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| 800 题工作量超预期 | 中 | 高 | 第 1 周完成 50 题做时间评估，超时则降到 600 题 |
| IAA < 0.75 | 中 | 中 | 标注规范评审会 + 50 题预标注 calibration |
| 推荐类标注主观性大 | 高 | 中 | gold_recommendations 限定为已发表样机；rank 由 3 人独立打分平均 |
| 文献溯源不全 | 中 | 低 | 强制每题至少 1 条 support_docs，否则不录入 |
| 题目泄露给基线 | 低 | 高 | 测试集 15% 严格隔离，标注完不再公开问题文本 |

---

## 9 数据集发布

### 9.1 文件结构
```
fwmav-qa-benchmark/
├── README.md
├── LICENSE (CC-BY-4.0)
├── data/
│   ├── train.jsonl       (560 题, 70%)
│   ├── valid.jsonl       (120 题, 15%)
│   └── test.jsonl        (120 题, 15%)
├── schemas/
│   ├── kq_schema.json
│   └── dr_schema.json
├── scripts/
│   ├── validate.py
│   ├── score.py
│   └── ragas_eval.py
└── docs/
    └── annotation_guide.md
```

### 9.2 发布渠道
- **GitHub**：`github.com/HumbleLong/fwmav-qa-benchmark`（公开）
- **Zenodo**：申请 DOI（论文中可引用）
- **HuggingFace Datasets**：方便后续研究者直接 `load_dataset("HumbleLong/fwmav-qa")`

### 9.3 引用方式
论文里：
> "We construct FWMAV-QA, the first benchmark dataset for question answering and design recommendation in bionic flapping-wing MAVs, comprising 600 knowledge queries and 200 design recommendation cases (https://github.com/HumbleLong/fwmav-qa-benchmark)."

---

## 10 第一周立刻可做的事

如果你这周想动手，按这个顺序：

### Day 1（明天）
- [ ] 在 Zotero `小论文-GraphRAG-FWMAV` collection 里标记 30 篇"问题候选"文献（用 tag `qa-source`）
- [ ] 创建 GitHub repo `fwmav-qa-benchmark`（私有，等数据集稳定后再公开）

### Day 2-3
- [ ] 按本规范的 schema 写 **20 道样题**（A1: 5 题, A2: 5 题, A3: 5 题, B1: 5 题）
- [ ] 实现 `validate.py` 自动校验脚本

### Day 4
- [ ] 找 1-2 位同门做"标注规范评审"
- [ ] 用 20 道样题做 IAA calibration（如果 IAA < 0.75 修订规范再试）

### Day 5
- [ ] 招募/确定标注协作者（最好 2-3 人）
- [ ] 把 docs/annotation_guide.md 整理给协作者

### Day 6-7
- [ ] 启动 600 题正式标注，每天 ~30 题
- [ ] 每周一晚上 review 一次进度

---

# 附录 A：常见题目模板（供撰写参考）

## A1. 单跳定义类模板（150 题）

| 模板 | 示例 |
|---|---|
| 什么是 X？ | 什么是雷诺数？ |
| X 是什么意思？ | 翼载荷是什么意思？ |
| X 的定义是什么？ | Strouhal 数的定义是什么？ |
| X 是如何定义的？ | 推进效率因子是如何定义的？ |

## A2. 单跳属性类模板（150 题）

| 模板 | 示例 |
|---|---|
| Festo SmartBird 的翼展是多少？ | （直接查 KG 节点）|
| Nano Hummingbird 由谁研制？ | （查 DEVELOPED_BY 关系）|
| DelFly Nimble 的扑动频率范围是什么？ | （查节点属性）|
| 哪些飞行器使用压电驱动？ | （反向查 EQUIPPED_WITH）|

## A3. 多跳对比类模板（150 题）

| 模板 | 示例 |
|---|---|
| X 和 Y 在 Z 方面有什么区别？ | DelFly Nimble 和 SmartBird 在续航能力上有什么区别？ |
| X 比 Y 在 Z 方面更优的原因？ | 为什么蜂鸟仿生比鸽子仿生更适合悬停？ |
| 列出所有满足条件 C 的 X | 列出所有翼展小于 20 cm 的扑翼机 |

## A4. 多跳推理 + 混合类模板（150 题）

| 模板 | 示例 |
|---|---|
| 参考 X 设计 Y 是否可行？ | 参考蜂鸟设计 30km 续航扑翼机是否可行？ |
| 如果要实现 P 性能，应选择什么 X？ | 如果要实现 5 分钟续航，应选择什么驱动方式？ |
| 给定约束 C，分析方案 S 的可行性 | 给定 50g 载重 + 30km 续航，分析 DelFly 改型是否可行？ |

## B1. 简单约束推荐模板（100 题）

| 模板（任务约束 → 推荐）|
|---|
| 续航 N 分钟以上的扑翼机？|
| 翼展 ≤ X cm 的微型扑翼机？|
| 起飞重量 < Y g 的样机？|

## B2. 复杂约束推荐模板（100 题）

| 模板 |
|---|
| 续航 N + 载重 W + 室外/室内 + 任务类型，推荐参考样机？|
| 仿生 X（生物原型）+ 性能 P + 任务 T，推荐方案？|
