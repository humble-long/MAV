# FWMAV-QA Benchmark

> **目标**：构建 800 题中文测评数据集，用于 BioBridge-GraphRAG 论文 Section 5 的实验。
> **维护**：王嘉龙（西工大航空学院）
> **License**: CC-BY-4.0（数据集）/ MIT（脚本）
> **状态**：v2.0 — 754 题最终数据集（200 手写 + 554 模板生成，已通过校验 + KG 对照 + Subagent 评审）

---

## 标注进度

| Phase | 进度 | 状态 |
|---|---|---|
| Phase 1: 30 题种子 + 规范校准 | 30/30 | ✅ 完成 |
| Phase 2: 扩展到 100 题 + 评审 | 100/100 | ✅ 完成 |
| Phase 2 续: 100→200 + 评审 | 200/200 | ✅ 完成 |
| Phase 3 (混合): +554 模板生成 + 抽样评审 | 754/800 | ✅ 完成 |

754 题分布：
- A1（定义类）111 题（45 手写 + 66 模板）
- A2（属性类）145 题（45 手写 + 100 模板）
- A3（对比类）140 题（40 手写 + 100 模板）
- A4（推理类）130 题（30 手写 + 100 模板）
- B1（简单推荐）108 题（20 手写 + 88 模板）
- B2（复杂推荐）120 题（20 手写 + 100 模板）
- 难度：1×134 / 2×303 / 3×317

## 数据集构成说明（论文中要写）

混合标注策略：
- **手写部分（200 题）**：用作 test split + 部分 valid split，事实精度高（100% 通过 KG 一致性 + Subagent 评审）
- **模板生成部分（554 题）**：用作 train split + 部分 valid split，多样性好，但数据来自 KG 模板填充，存在统计学多样性而非语言学多样性
- 推荐数据划分：test=200 (全部手写) / valid=100 (50 手写 + 50 模板) / train=454 (模板)

## 已知系统性局限（Subagent 评审标记）

1. B2 模板生成题：早期版本（v1）忽略了生物原型约束，已在 v2 修复（用 MIMICS 关系严格匹配）
2. A4 推理题：在极端配置（如 5g + 60min）下电池能量估算不切实际
3. A3 对比题：模板生成的对比答案侧重数值差异，对深层设计差异分析较弱
4. B1/B2 match_score：使用位置分而非真实匹配度计算
5. KG 数据规模天然限制：A1 仅 66 题（67 个核心概念），B1 88 题（KG 满足约束的样机数量）

---

## 文件结构

```
fwmav-qa-benchmark/
├── README.md                         本文件
├── data/
│   ├── seed.jsonl                   v0.2 — 30 题种子（已校验 ✅）
│   ├── batch_wjl_001_a1.jsonl       v0.3 Phase 2 — 22 题 A1 扩展
│   ├── batch_wjl_001_a2.jsonl       v0.3 Phase 2 — 22 题 A2 扩展
│   ├── batch_wjl_001_a3.jsonl       v0.3 Phase 2 — 13 题 A3 扩展
│   ├── batch_wjl_001_a4b1.jsonl     v0.3 Phase 2 — 6+7 题 A4+B1 扩展
│   ├── seed_v2_100.jsonl            v0.3 — 合并后 100 题（已校验 ✅）
│   ├── train.jsonl                  TBD
│   ├── valid.jsonl                  TBD
│   └── test.jsonl                   TBD
├── schemas/
│   ├── kq_schema.json               知识查询类 JSON Schema
│   └── dr_schema.json               方案推荐类 JSON Schema
├── scripts/
│   ├── validate.py                  自动校验脚本
│   ├── score.py                     评分脚本（评估时用）
│   └── kg_cheatsheet.md             KG 节点速查表
└── docs/
    └── annotation_guide.md          标注协作者指南
```

---

## 数据集规模目标

| 类别 | 子类 | 数量 | 难度分布 |
|---|---|---|---|
| A. 知识查询 (KQ) | A1 单跳·定义 | 150 | 1:2:1 |
| | A2 单跳·属性 | 150 | 1:2:1 |
| | A3 多跳·对比 | 150 | 1:2:1 |
| | A4 多跳·推理（含混合）| 150 | 1:2:1 |
| B. 方案推荐 (DR) | B1 简单约束 | 100 | 1:2:1 |
| | B2 复杂约束 | 100 | 1:2:1 |
| **合计** | | **800** | |

---

## 数据划分

- 训练集 (train): 70% = 560 题
- 验证集 (valid): 15% = 120 题
- 测试集 (test): 15% = 120 题（人工严格校验，不公开问题文本直到论文发表）

---

## 引用方式

```bibtex
@dataset{wang2026fwmavqa,
  title  = {FWMAV-QA: A Benchmark Dataset for Question Answering and
            Design Recommendation in Bionic Flapping-Wing MAVs},
  author = {Wang, Jialong},
  year   = {2026},
  url    = {https://github.com/HumbleLong/fwmav-qa-benchmark},
  doi    = {TBD-Zenodo}
}
```

---

## 配套论文

> Wang J L. 基于知识图谱与大语言模型的仿生飞行器智能问答与方案推荐方法[J]. 航空学报, 2027, XX(XX): XXXXXX.
