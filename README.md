# MAV — 基于知识图谱与大语言模型的仿生飞行器智能问答与方案推荐方法

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20726399.svg)](https://doi.org/10.5281/zenodo.20726399)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![License: MIT](https://img.shields.io/badge/Code_License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

> 西北工业大学航空学院 · 控制工程硕士论文研究项目
>
> 论文方向（小论文）：**基于图增强检索的仿生飞行器概念设计智能问答与方案推荐方法**（拟投航空学报）
>
> 框架名：**BioBridge-GraphRAG**

---

## 1. 项目概述

本仓库为硕士研究项目「基于知识图谱与大语言模型的仿生飞行器（FWMAV）智能辅助设计」的开源资料，内容包含：

- **论文大纲**（按航空学报体例展开的中文 SCI Q1 风格大纲）
- **FWMAV-QA Benchmark**：754 题中文测评数据集（200 道人工标注 + 554 道模板生成）
- **知识图谱构建脚本**：从原始 Neo4j KG 出发，逐步补全数据 + 自动打分 MIMICS 仿生映射 + 引入 Performance 节点
- **数据完整性诊断报告 + 抽样验证报告**

## 2. BioBridge-GraphRAG 三大创新点

```
┌─────────────────────────────────────────────────┐
│  创新 1: Bio-Engineering 双层本体                │
│  生物层 (23 Organism) + 工程层 (39 FWMAV)       │
│  + 4 类细分仿生映射 (MIMICS-aero/kin/morph/scale)│
└─────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────┐
│  创新 2: 尺度律工具增强的图路径推理               │
│  LLM 在 KG 上做 ReAct 路径推理 + 调 4 个物理工具 │
│  (Hassanalian / Shyy / Strouhal / Reynolds)     │
│  → 知识问答 + 方案推荐精排                       │
└─────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────┐
│  创新 3: 张量分解的方案候选检索                   │
│  4 阶张量 (FWMAV × Component × Performance × 任务)│
│  CP 分解 + KNN 召回 Top-10 候选 (粗筛)           │
└─────────────────────────────────────────────────┘
```

## 3. 仓库结构

```
.
├── README.md                              本文件
├── LICENSE                                CC-BY-4.0 (数据集) / MIT (代码)
├── .gitignore
└── papers/
    ├── 01-论文大纲-航空学报.md            完整中文大纲（10 章）
    ├── 02-FWMAV-QA-Benchmark-标注规范.md   标注协作规范
    ├── kg-diagnostics/                    KG 诊断 + 升级前后报告
    │   ├── diagnose-report.md
    │   ├── diagnose-report-after-p2.md
    │   ├── p0-p2-summary.md
    │   └── p0-2-validation-report.md
    └── fwmav-qa-benchmark/
        ├── README.md                      数据集 README
        ├── data/                          数据集（jsonl 格式）
        │   ├── seed_v5_200.jsonl          200 道人工标注
        │   ├── generated_600.jsonl        554 道模板生成
        │   └── fwmav_qa_v2_final.jsonl    754 题最终数据集 ⭐
        ├── schemas/                       JSON Schema
        │   ├── kq_schema.json
        │   └── dr_schema.json
        ├── scripts/                       全部 Python 脚本
        │   ├── kg_diagnose.py             KG 完整性诊断
        │   ├── p0_1_enrich_organisms.py   补全 23 个生物原型属性
        │   ├── p0_2_enrich_fwmavs.py      补全 36 个 FWMAV 缺失属性
        │   ├── p0_3_standardize_props.py  属性命名标准化
        │   ├── p1_1_mimics_score.py       MIMICS 自动打分
        │   ├── p1_2_performance_nodes.py  引入 Performance 节点
        │   ├── p2_1_add_references.py     文献溯源补全
        │   ├── p2_2_equipment_categorize.py
        │   ├── validate.py                数据集格式校验
        │   ├── fix_chinese_quotes.py      中文引号自动修复
        │   ├── check_seed_against_kg.py   KG 一致性二次验证
        │   ├── template_generate_600.py   模板生成 600 题
        │   └── p0_2_fix_after_audit.py    抽样审核后的修复
        └── docs/
            └── annotation_guide.md        协作者指南
```

## 4. FWMAV-QA Benchmark 概况

| 类别 | 数量 | 说明 |
|---|---|---|
| **A1** 知识查询·单跳·定义 | 111 | 概念解释类（Strouhal 数、Hassanalian 公式、KGQA 等） |
| **A2** 知识查询·单跳·属性 | 145 | KG 节点属性查询（机型翼展、研制单位等） |
| **A3** 知识查询·多跳·对比 | 140 | 跨样机/跨机构对比 |
| **A4** 知识查询·多跳·推理 | 130 | 任务可行性推理、参考样机推荐推理 |
| **B1** 方案推荐·简单约束 | 108 | 单维度约束的样机推荐 |
| **B2** 方案推荐·复杂约束 | 120 | 多维度复合约束推荐（含生物原型） |
| **合计** | **754** | 难度 1×134 / 2×303 / 3×317 |

**混合标注策略**（与 GraphRAG-Bench, SynthCypher 等同行做法一致）：
- **测试集**：200 道人工标注 + Subagent 多轮评审，事实精度高
- **训练/验证集**：554 道模板生成（KG 数据严格锚定，避免 LLM 幻觉）

## 5. 知识图谱（Neo4j）规模

| 节点类型 | 数量 | 说明 |
|---|---|---|
| FlappingWingVehicle | 39 | 历史样机 |
| Organism | 23 | 生物原型（含完整 8+ 属性） |
| Equipment | 108 | 部件（已分 10 个 category） |
| Application | 54 | 任务场景 |
| DriveMechanism | 44 | 驱动机构 |
| Reference | 39 | 文献溯源（含 8 个补全） |
| Organization | 33 | 研制单位 |
| **Performance** | **272** | 性能节点（独立抽出） |

7 类关系：MIMICS（已细分 4 类 + 自动打分）、HAS_PERFORMANCE、EQUIPPED_WITH、SUITABLE_FOR、HAS_DRIVE_MECHANISM、HAS_REFERENCE、DEVELOPED_BY、FUNDED_BY。

## 6. 复现脚本运行

```bash
# 1. 设置 Neo4j 连接（替换为你的密码）
export NEO4J_PASSWORD="your-password"

# 2. 安装依赖
pip install neo4j jsonschema

# 3. 跑 KG 诊断
python papers/fwmav-qa-benchmark/scripts/kg_diagnose.py

# 4. 校验 754 题数据集
python papers/fwmav-qa-benchmark/scripts/validate.py \
  papers/fwmav-qa-benchmark/data/fwmav_qa_v2_final.jsonl
```

## 7. 引用

如果本研究/数据集对你有帮助，请引用：

```bibtex
@dataset{wang2026fwmavqa,
  title  = {FWMAV-QA: A Benchmark Dataset for Question Answering and Design
            Recommendation in Bionic Flapping-Wing MAVs},
  author = {Wang, Jialong},
  year   = {2026},
  url    = {https://github.com/humble-long/MAV},
  doi    = {10.5281/zenodo.20726399},
  publisher = {Zenodo}
}

@article{wang2026biobridge,
  title  = {基于知识图谱与大语言模型的仿生飞行器智能问答与方案推荐方法},
  author = {王嘉龙 and 宣建林 and 李亮},
  journal= {航空学报},
  year   = {2027},
  note   = {投稿中}
}
```

## 8. 致谢

- 西北工业大学航空学院 · 校内导师 宣建林教授
- 陕西空天动力研究院有限公司 · 校外导师 李亮高工
- 同门标注协作者

## 9. License

- **数据集**（`papers/fwmav-qa-benchmark/data/`）：CC-BY-4.0
- **代码 / 脚本**（`papers/fwmav-qa-benchmark/scripts/`）：MIT
- **论文文档**（`papers/*.md`）：CC-BY-4.0
