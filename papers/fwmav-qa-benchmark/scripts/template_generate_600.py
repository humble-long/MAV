#!/usr/bin/env python3
"""模板生成 600 道 FWMAV-QA 测评题.

策略：
- 6 类题目（A1/A2/A3/A4/B1/B2）每类 100 道
- 用 KG 真实数据填充模板（避免 LLM 幻觉）
- 答案用 Python 字符串拼接，确保事实与 KG 一致
- 题目分布按难度 1:2:1 (1×25, 2×50, 3×25 per category)

输出：data/generated_600.jsonl + 5 个分类文件
"""

from __future__ import annotations
import json
import random
from datetime import datetime
from pathlib import Path
import os
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")

random.seed(42)  # 可复现

OUTPUT_DIR = Path('/Users/humble/studyProject/MAV/papers/fwmav-qa-benchmark/data')
TODAY = "2026-06-17"


# ========== KG 数据加载 ==========
def load_kg_data():
    """从 Neo4j 加载所需数据."""
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    data = {}
    with driver.session() as sess:
        # FWMAV
        r = sess.run("""
            MATCH (v:FlappingWingVehicle)
            RETURN v.name AS name, properties(v) AS props
        """)
        data['fwmav'] = [{'name': row['name'], **row['props']} for row in r]

        # Organism
        r = sess.run("MATCH (o:Organism) RETURN o.name AS name, properties(o) AS props")
        data['organism'] = [{'name': row['name'], **row['props']} for row in r]

        # Organization
        r = sess.run("MATCH (o:Organization) RETURN o.name AS name")
        data['organization'] = [row['name'] for row in r]

        # DriveMechanism
        r = sess.run("MATCH (d:DriveMechanism) RETURN d.name AS name")
        data['drive'] = [row['name'] for row in r]

        # Application
        r = sess.run("MATCH (a:Application) RETURN a.name AS name")
        data['app'] = [row['name'] for row in r]

        # Equipment（带 category）
        r = sess.run("MATCH (e:Equipment) RETURN e.name AS name, e.category AS cat")
        data['equipment'] = [{'name': row['name'], 'category': row['cat']} for row in r]

        # MIMICS 关系
        r = sess.run("""
            MATCH (v:FlappingWingVehicle)-[m:MIMICS]->(o:Organism)
            RETURN v.name AS v, o.name AS o, m.mimics_dominant_type AS dom, m.mimics_dominant_score AS sc
        """)
        data['mimics'] = [{'v': row['v'], 'o': row['o'], 'dom': row['dom'], 'sc': row['sc']} for row in r]

        # DEVELOPED_BY 关系
        r = sess.run("""
            MATCH (v:FlappingWingVehicle)-[:DEVELOPED_BY]->(o:Organization)
            RETURN v.name AS v, o.name AS o
        """)
        data['dev_by'] = [{'v': row['v'], 'o': row['o']} for row in r]

        # SUITABLE_FOR 关系
        r = sess.run("""
            MATCH (v:FlappingWingVehicle)-[:SUITABLE_FOR]->(a:Application)
            RETURN v.name AS v, a.name AS a
        """)
        data['suitable'] = [{'v': row['v'], 'a': row['a']} for row in r]

        # HAS_DRIVE_MECHANISM
        r = sess.run("""
            MATCH (v:FlappingWingVehicle)-[:HAS_DRIVE_MECHANISM]->(d:DriveMechanism)
            RETURN v.name AS v, d.name AS d
        """)
        data['has_drive'] = [{'v': row['v'], 'd': row['d']} for row in r]
    driver.close()
    return data


# ========== 题目生成器 ==========
def fmt_freq(v):
    """格式化扑频（数字或字符串区间）."""
    if v is None:
        return "未知"
    if isinstance(v, str):
        return v + " Hz"
    return f"{v} Hz"


def fmt_weight(v):
    if v is None: return "未知"
    return f"{v} g"


def gen_a1_definition(kg, n=100):
    """A1: 单跳·定义类——基于核心概念列表生成."""
    # 概念库：(术语, 定义文本)
    concepts = [
        ("Strouhal 数", "St = fA/U，扑动幅度与来流速度的比值；扑翼飞行最优区间为 0.2-0.4。"),
        ("雷诺数", "Re = ρUL/μ，惯性力与粘性力之比；仿生扑翼飞行器通常处于 100-100000 的低雷诺数范围。"),
        ("翼载荷", "飞行器重量与机翼面积之比 W/S（N/m² 或 g/cm²），决定了扑动幅度与频率需求。"),
        ("展弦比", "AR = b²/S，机翼细长程度的指标；高展弦比适合长航时滑翔，低展弦比适合高机动飞行。"),
        ("扑动模态", "扑翼机翼的运动形式，主要包括上下扑动 (plunging)、扭转/俯仰 (pitching)、拍打-扭转耦合三种。"),
        ("前缘涡 (LEV)", "机翼前缘形成的螺旋涡结构，是昆虫扑翼产生高升力的关键非定常机制。"),
        ("缩减频率 k", "k = πfc/U，扑动周期与流动时间尺度的比值；反映非定常效应强度。"),
        ("Hassanalian 公式", "Hassanalian 等 2017 年（Meccanica）提出的扑翼飞行器重量分数估算模型，把总重分解为结构、推进、电源、航电+载荷各分数。"),
        ("Shyy 尺度律", "Shyy 等 2013 年基于几何相似假设建立的扑翼飞行器尺度律，例如扑频 f ∝ W^(-1/3)。"),
        ("MIMICS 仿生映射", "知识图谱中扑翼飞行器与生物原型的语义关系，本研究细分为 4 类：MIMICS-aero/kinematics/morphology/scale。"),
        ("曲柄摇杆机构", "由曲柄、连杆、摇杆和机架组成的四杆机构，将电机连续旋转转换为机翼往复扑动。"),
        ("压电致动器", "利用压电材料形变产生位移的执行器，响应频率高（千赫兹）、功率密度高，适合昆虫尺度扑翼。"),
        ("X-Wing 构型", "扑翼飞行器采用 4 个机翼以 X 形排列、相邻翼对反向扑动的布局，代表机型 RoboBee X-Wing。"),
        ("无尾翼扑翼机", "不使用传统尾翼提供俯仰偏航稳定性的扑翼飞行器，靠双翼或四翼差动控制实现姿态稳定。"),
        ("主动扭转", "通过额外的伺服或驱动机构主动控制机翼绕展向轴扭转，实现高气动效率。代表：SmartBird 80% 气动效率。"),
        ("被动扭转", "依赖机翼柔性材料在扑动过程中自然变形产生的扭转，结构简洁、轻量。"),
        ("机翼柔性变形", "扑翼在飞行中由气动力作用产生的非刚性变形，能增强升力、减小阻力、节能。"),
        ("BERT", "Google 2018 提出的双向 Transformer 预训练模型，用于自然语言意图分类。"),
        ("DeepSeek-R1-8b", "DeepSeek 团队 2025 年发布的 8B 参数级开源大模型，本研究选用作为本地 LLM。"),
        ("LLM Agent", "以大语言模型为核心、具备工具调用、多步推理、规划能力的智能体。"),
        ("ReAct 范式", "把推理 (Reasoning) 与行动 (Acting) 交替进行的 LLM Agent 框架，是 BioBridge 创新点 2 的设计基础。"),
        ("Think-on-Graph (ToG)", "ICLR 2024 提出的 LLM × KG 融合范式，让 LLM 在 KG 上做多跳路径搜索式推理。"),
        ("HippoRAG", "结合 KG + LLM + 个性化 PageRank 的检索增强生成方法。"),
        ("RAGAS", "评估 RAG 系统质量的开源框架，包含 Faithfulness、Answer Relevance、Context Precision/Recall 等指标。"),
        ("NDCG@k", "推荐系统评估排序质量的标准指标，衡量 Top-k 推荐的相关性排序，值在 [0, 1] 之间。"),
        ("MRR (Mean Reciprocal Rank)", "推荐评估指标，第一个相关结果的倒数排名的平均。"),
        ("Function Calling", "OpenAI 提出的标准化 LLM 工具调用协议，让 LLM 输出符合 JSON Schema 的结构化调用。"),
        ("Cypher 查询", "Neo4j 图数据库的声明式查询语言。"),
        ("Neo4j", "原生图数据库，使用属性图模型 + Cypher 语言。"),
        ("张量分解 (Tensor Decomposition)", "把高维张量表示为低维因子矩阵或核张量乘积的数学方法，CP 分解和 Tucker 分解最常见。"),
        ("CP 分解", "Canonical Polyadic 分解，把张量近似为外积之和。"),
        ("KGQA", "知识图谱问答任务，把自然语言问题转换为 KG 查询并返回答案。"),
        ("案例推理 (CBR)", "基于历史案例求解新问题的 AI 方法，通过 4R 循环（Retrieve, Reuse, Revise, Retain）。"),
        ("仿生设计 (BID)", "从生物系统提取功能机理并应用于工程设计的方法，强调机理迁移而非形态复制。"),
        ("BiLSTM-CRF", "结合双向 LSTM 和 CRF 的序列标注模型，用于 KG 命名实体识别 (NER)。"),
        ("RAG", "检索增强生成 (Retrieval-Augmented Generation)，让 LLM 检索外部知识后再生成答案。"),
        ("GraphRAG", "结合知识图谱的检索增强生成框架。"),
        ("VectorRAG", "传统的基于向量检索的 RAG，相对于 GraphRAG 多跳能力较弱。"),
        ("Inter-Annotator Agreement", "多人标注一致性度量指标，例如 Cohen's Kappa；BioBridge-QA 要求 IAA ≥ 0.75。"),
        ("Few-shot Prompting", "在 LLM Prompt 中提供少量示例引导模型完成任务，无需微调。"),
        ("Chain-of-Thought (CoT)", "让 LLM 在生成答案前显式输出推理步骤，提升复杂推理能力。"),
        ("意图判别", "把用户问题分类为不同意图（如知识查询 vs 方案推荐），是 BioBridge-GraphRAG 的入口模块。"),
        ("KNN 检索", "在嵌入空间中找最近邻的 K 个点，BioBridge 创新点 3 张量分解粗筛阶段使用。"),
        ("软约束 vs 硬约束", "软约束允许越界（带分数惩罚），硬约束严格不能违反；BioBridge 的方案推荐需明确区分。"),
        ("仿生原型", "扑翼飞行器在 KG 中映射的具体生物对象（如蜂鸟、苍蝇、海鸥）。"),
        ("生物原型层", "BioBridge 双层本体的生物层，存储 23 个生物的体重、扑频、悬停能力等参数。"),
        ("工程层", "BioBridge 双层本体的工程层，存储 39 个 FWMAV 节点的总体参数。"),
        ("仿生映射的 4 类细分", "MIMICS-aero (气动相似)、MIMICS-kinematics (运动学相似)、MIMICS-morphology (形态相似)、MIMICS-scale (尺度相似)。"),
        ("非典型扑翼机", "在 KG 中标注 is_atypical_fwmav=true 的边界案例，例如 PigeonBot 实为螺旋桨推进+morphing 翼。"),
        ("FlappingWingVehicle", "KG 中扑翼飞行器节点类型，39 个实例。"),
        ("Performance 节点", "BioBridge KG 中独立的性能节点（重量、扑频、续航等），共 269 个。"),
        ("HAS_PERFORMANCE 关系", "FlappingWingVehicle 与 Performance 节点之间的关系。"),
        ("EQUIPPED_WITH 关系", "FlappingWingVehicle 与 Equipment 节点的关系，表示载荷/驱动器/传感器装备情况。"),
        ("DEVELOPED_BY 关系", "FlappingWingVehicle 与 Organization 节点的关系，表示研制单位。"),
        ("HAS_DRIVE_MECHANISM 关系", "FlappingWingVehicle 与 DriveMechanism 节点的关系。"),
        ("SUITABLE_FOR 关系", "FlappingWingVehicle 与 Application 节点的关系。"),
        ("HAS_REFERENCE 关系", "FlappingWingVehicle 与 Reference 节点的关系，表示文献溯源。"),
        ("FUNDED_BY 关系", "FlappingWingVehicle 与资助机构的关系，KG 中较稀疏。"),
        ("KGEntity", "BioBridge KG 中所有实体节点共享的根标签，方便统一查询。"),
        ("BiologicalProperty", "Organism 节点的关键属性集合，包括体重区间、翼展区间、扑频区间、悬停能力等。"),
        ("FWMAV-QA Benchmark", "本研究构建的中文测评数据集，含 800 道题，覆盖 6 类题型（A1/A2/A3/A4/B1/B2）。"),
        ("BioBridge-GraphRAG", "本研究提出的图增强检索框架，含 3 个创新点：双层本体、路径推理+工具调用、张量分解推荐。"),
        ("hassanalian_weight 工具", "BioBridge 物理工具之一，基于 Hassanalian 公式估算给定续航与载重的起飞重量。"),
        ("shyy_scaling_law 工具", "BioBridge 物理工具之一，基于 Shyy 尺度律估算给定重量对应的扑频、翼展等参数。"),
        ("strouhal_check 工具", "BioBridge 物理工具之一，校验扑频-扑幅-速度的 Strouhal 数是否在 0.2-0.4 区间。"),
        ("reynolds_check 工具", "BioBridge 物理工具之一，校验雷诺数是否在合理流态范围。"),
    ]

    questions = []
    used = set()
    diff_pool = [1] * 25 + [2] * 50 + [3] * 25
    random.shuffle(diff_pool)

    # 标记哪些是 NLP/KG meta 概念，使用不同题干模板
    NLP_KG_TERMS = {
        'BERT', 'BiLSTM-CRF', 'Function Calling', 'Cypher 查询', 'Neo4j',
        'KGQA', 'BioBridge-GraphRAG', 'GraphRAG', 'VectorRAG', 'RAG',
        'RAGAS', 'NDCG@k', 'MRR (Mean Reciprocal Rank)', 'Inter-Annotator Agreement',
        'Few-shot Prompting', 'Chain-of-Thought (CoT)', 'KNN 检索',
        'LLM Agent', 'ReAct 范式', 'Think-on-Graph (ToG)', 'HippoRAG',
        '张量分解 (Tensor Decomposition)', 'CP 分解', 'DeepSeek-R1-8b',
        '案例推理 (CBR)', '数据增强',
        'FlappingWingVehicle', 'Performance 节点', 'HAS_PERFORMANCE 关系',
        'EQUIPPED_WITH 关系', 'DEVELOPED_BY 关系', 'HAS_DRIVE_MECHANISM 关系',
        'SUITABLE_FOR 关系', 'HAS_REFERENCE 关系', 'FUNDED_BY 关系', 'KGEntity',
        'BiologicalProperty', 'FWMAV-QA Benchmark',
        'hassanalian_weight 工具', 'shyy_scaling_law 工具',
        'strouhal_check 工具', 'reynolds_check 工具',
        '意图判别', '软约束 vs 硬约束',
    }

    for i in range(min(n, len(concepts))):
        term, definition = concepts[i]
        used.add(term)
        diff = diff_pool[i] if i < len(diff_pool) else 2
        qid = f"kq_g_{200 + i + 1:03d}"

        # 根据术语类型选择题干模板
        if term in NLP_KG_TERMS:
            question = f"在 BioBridge-GraphRAG 框架及 FWMAV-QA Benchmark 构建中，什么是 {term}？请简要说明它的定义和作用。"
            source = "BioBridge 系统/工程概念库"
        else:
            question = f"什么是 {term}？请简要说明它在仿生扑翼飞行器领域的含义或应用。"
            source = "FWMAV 领域概念库"

        questions.append({
            "id": qid,
            "category": "A1",
            "type": "知识查询·单跳·定义",
            "difficulty": diff,
            "question": question,
            "gold_answer": f"{term}：{definition}",
            "gold_entities": [term],
            "expected_hops": 1,
            "tool_call_required": [],
            "support_docs": [],
            "source": source,
            "annotator": "wjl-template",
            "annotation_date": TODAY,
            "generated_by": "template-v2",
        })
    return questions


def gen_a2_attribute(kg, n=100):
    """A2: 单跳·属性类——根据 FWMAV 节点属性生成."""
    questions = []
    fwmavs = [v for v in kg['fwmav'] if v.get('wingspan_mm') and v.get('weight_g_std')]
    diff_pool = [1] * 25 + [2] * 50 + [3] * 25
    random.shuffle(diff_pool)

    # 模板 1: 翼展查询
    templates = [
        ('翼展', 'wingspan_mm', 'mm'),
        ('起飞重量/总重', 'weight_g_std', 'g'),
        ('扑频', 'frequency_hz_min_std', 'Hz'),
        ('最大飞行速度', 'speed_max_m_s_std', 'm/s'),
        ('续航', 'endurance_s_std', 's'),
    ]

    idx = 0
    for v in fwmavs:
        if idx >= n: break
        for label, key, unit in templates:
            if idx >= n: break
            val = v.get(key)
            if val is None: continue

            # 处理续航单位转换
            display_val = val
            display_unit = unit
            if key == 'endurance_s_std':
                if val >= 60:
                    display_val = round(val / 60, 1)
                    display_unit = 'min'
                else:
                    display_val = val
                    display_unit = 's'

            qid = f"kq_g_{300 + idx + 1:03d}"
            diff = diff_pool[idx] if idx < len(diff_pool) else 1
            questions.append({
                "id": qid,
                "category": "A2",
                "type": "知识查询·单跳·属性",
                "difficulty": diff,
                "question": f"{v['name']} 的{label}是多少？",
                "gold_answer": f"{v['name']} 的{label}为 {display_val} {display_unit}。",
                "gold_entities": [v['name']],
                "gold_relations": [key],
                "expected_hops": 1,
                "tool_call_required": [],
                "support_docs": [],
                "source": f"KG: {v['name']}.{key}",
                "annotator": "wjl-template",
                "annotation_date": TODAY,
                "generated_by": "template",
            })
            idx += 1

    return questions[:n]


def gen_a3_compare(kg, n=100):
    """A3: 多跳·对比类——挑两两机型做对比."""
    questions = []
    fwmavs = [v for v in kg['fwmav'] if v.get('wingspan_mm') and v.get('weight_g_std')]
    diff_pool = [1] * 25 + [2] * 50 + [3] * 25
    random.shuffle(diff_pool)

    # 随机生成机型对（避免重复）
    seen_pairs = set()
    idx = 0
    attempts = 0
    while idx < n and attempts < n * 5:
        attempts += 1
        v1, v2 = random.sample(fwmavs, 2)
        pair = tuple(sorted([v1['name'], v2['name']]))
        if pair in seen_pairs: continue
        seen_pairs.add(pair)

        qid = f"kq_g_{400 + idx + 1:03d}"
        diff = diff_pool[idx] if idx < len(diff_pool) else 2

        # 构建对比答案（基于 KG 真实数据）
        def fmt(val, unit):
            return f"{val} {unit}" if val is not None else "未知"

        ans = f"{v1['name']}（翼展 {fmt(v1.get('wingspan_mm'), 'mm')}，重量 {fmt(v1.get('weight_g_std'), 'g')}，扑频 {fmt(v1.get('frequency_hz_min_std'), 'Hz')}，悬停 {v1.get('can_hover', '未知')}）"
        ans += f" vs {v2['name']}（翼展 {fmt(v2.get('wingspan_mm'), 'mm')}，重量 {fmt(v2.get('weight_g_std'), 'g')}，扑频 {fmt(v2.get('frequency_hz_min_std'), 'Hz')}，悬停 {v2.get('can_hover', '未知')}）。"

        # 简单分析
        if v1.get('weight_g_std') and v2.get('weight_g_std'):
            ratio = v1['weight_g_std'] / v2['weight_g_std']
            if ratio > 2 or ratio < 0.5:
                ans += f"两者重量相差约 {max(ratio, 1/ratio):.1f} 倍。"

        questions.append({
            "id": qid,
            "category": "A3",
            "type": "知识查询·多跳·对比",
            "difficulty": diff,
            "question": f"{v1['name']} 和 {v2['name']} 在主要总体参数上有什么差异？",
            "gold_answer": ans,
            "gold_entities": [v1['name'], v2['name']],
            "gold_relations": ["wingspan_mm", "weight_g_std", "frequency_hz_min_std", "can_hover"],
            "gold_path": [f"{v1['name']} attrs", f"{v2['name']} attrs", "compare"],
            "expected_hops": 2,
            "tool_call_required": [],
            "support_docs": [],
            "source": f"KG: 两机型对比",
            "annotator": "wjl-template",
            "annotation_date": TODAY,
            "generated_by": "template",
        })
        idx += 1

    return questions


def gen_a4_reasoning(kg, n=100):
    """A4: 多跳·推理类——基于 MIMICS、约束推理生成."""
    questions = []
    diff_pool = [3] * n

    # 模板 1: "如果想做仿 X 的扑翼机，应该参考 Y"
    biological_to_fwmav = {}
    for m in kg['mimics']:
        biological_to_fwmav.setdefault(m['o'], []).append(m['v'])

    idx = 0
    for biology, vehicles in biological_to_fwmav.items():
        if idx >= n: break
        if len(vehicles) == 0: continue

        org = next((o for o in kg['organism'] if o['name'] == biology), None)
        if org is None or org.get('body_mass_g_min') is None: continue

        qid = f"kq_g_{500 + idx + 1:03d}"
        ans = f"以 {biology}（体重 {org.get('body_mass_g_min', '?')}-{org.get('body_mass_g_max', '?')} g，扑频 {org.get('flap_freq_hz_min', '?')}-{org.get('flap_freq_hz_max', '?')} Hz，悬停 {org.get('can_hover', '未知')}）为仿生原型的扑翼机参考样机：{', '.join(vehicles[:5])}"
        if len(vehicles) > 5:
            ans += f" 等共 {len(vehicles)} 款"
        ans += f"。设计建议：参考生物原型的扑频与重量区间，并结合 Hassanalian 公式与 Shyy 尺度律做工程参数估算。"

        questions.append({
            "id": qid,
            "category": "A4",
            "type": "知识查询·多跳·推理",
            "difficulty": 3,
            "question": f"如果想以 {biology} 为仿生原型设计扑翼机，KG 中有哪些可参考样机？设计建议是什么？",
            "gold_answer": ans,
            "gold_entities": [biology] + vehicles[:5],
            "gold_relations": ["MIMICS"],
            "gold_path": [f"MIMICS->{biology}", "aggregate vehicles", "design suggestion"],
            "expected_hops": 3,
            "tool_call_required": ["hassanalian_weight", "shyy_scaling_law"],
            "support_docs": [],
            "source": f"KG: MIMICS->{biology}",
            "annotator": "wjl-template",
            "annotation_date": TODAY,
            "generated_by": "template",
        })
        idx += 1

    # 模板 2: 重量估算反推
    while idx < n:
        target_w = random.choice([5, 15, 50, 100, 300, 800])
        target_e = random.choice([5, 15, 30, 60])

        # KG 中找接近的样机
        candidates = []
        for v in kg['fwmav']:
            if v.get('weight_g_std') is None: continue
            if abs(v['weight_g_std'] - target_w) / target_w < 0.5:
                candidates.append(v)

        if not candidates:
            idx += 1
            continue

        cand_names = [c['name'] for c in candidates[:3]]
        qid = f"kq_g_{500 + idx + 1:03d}"
        ans = f"按 Hassanalian 重量分数估算 {target_w} g + 续航 {target_e} 分钟：电池能量约 {target_e * 0.2:.1f}-{target_e * 0.3:.1f} Wh，子系统重量分配合理。KG 中接近此重量级的样机：{', '.join(cand_names)}。建议参考其设计但根据具体续航需求调整电池容量。"

        questions.append({
            "id": qid,
            "category": "A4",
            "type": "知识查询·多跳·推理",
            "difficulty": 3,
            "question": f"想做一架重量 {target_w} g、续航 {target_e} 分钟的扑翼机，KG 中有哪些可参考样机？需要做什么调整？",
            "gold_answer": ans,
            "gold_entities": cand_names,
            "gold_relations": ["weight_g_std", "endurance_s_std"],
            "gold_path": ["Hassanalian estimate", "KG search by weight", "propose adjustments"],
            "expected_hops": 4,
            "tool_call_required": ["hassanalian_weight"],
            "support_docs": [{"title": "Methodologies for weight estimation of fixed and flapping wing micro air vehicles", "zotero_key": "FBUQ5TVT"}],
            "source": "KG + Hassanalian",
            "annotator": "wjl-template",
            "annotation_date": TODAY,
            "generated_by": "template",
        })
        idx += 1

    return questions[:n]


def gen_b1_simple(kg, n=100):
    """B1: 简单约束推荐（单约束）."""
    def safe_num(x):
        try: return float(x) if x is not None else None
        except (TypeError, ValueError): return None

    questions = []
    fwmavs = [v for v in kg['fwmav'] if v.get('weight_g_std')]
    diff_pool = [1] * 25 + [2] * 75
    random.shuffle(diff_pool)

    # 模板：按各种单约束筛选；扩展到 frequency / endurance / can_hover / 仿生原型
    constraints_list = [
        # (约束名, 字段名, 操作, 描述, 阈值列表, 单位)
        ('weight_max_g', 'weight_g_std', 'max', '重量不超过', [5, 10, 15, 20, 25, 30, 50, 100, 200, 300, 500, 800], 'g'),
        ('weight_min_g', 'weight_g_std', 'min', '重量至少', [10, 30, 50, 100, 200, 300, 500, 800], 'g'),
        ('wingspan_max_mm', 'wingspan_mm', 'max', '翼展不超过', [100, 200, 300, 500, 800, 1000, 1500, 2000], 'mm'),
        ('wingspan_min_mm', 'wingspan_mm', 'min', '翼展至少', [200, 500, 800, 1000, 1500, 2000], 'mm'),
        ('frequency_max_hz', 'frequency_hz_min_std', 'max', '扑频不超过', [3, 5, 10, 20, 30, 50, 100], 'Hz'),
        ('frequency_min_hz', 'frequency_hz_min_std', 'min', '扑频至少', [10, 20, 30, 50, 100], 'Hz'),
        ('endurance_min_s', 'endurance_s_std', 'min', '续航至少', [60, 300, 600, 1200, 1800, 3600], 's'),
        ('endurance_max_s', 'endurance_s_std', 'max', '续航不超过', [300, 600, 1800, 3600], 's'),
        ('speed_max_m_s', 'speed_max_m_s_std', 'max', '速度不超过', [3, 5, 8, 10, 15], 'm/s'),
        ('speed_min_m_s', 'speed_max_m_s_std', 'min', '速度至少', [5, 8, 10, 12], 'm/s'),
    ]

    idx = 0
    for cname, key, op, label, thresholds, unit in constraints_list:
        for thresh in thresholds:
            if idx >= n: break

            # 筛选符合的样机
            matched = []
            for v in fwmavs:
                vv = safe_num(v.get(key))
                if vv is None: continue
                if op == 'max' and vv <= thresh: matched.append(v)
                elif op == 'min' and vv >= thresh: matched.append(v)
            if len(matched) < 3: continue
            matched.sort(key=lambda v: abs((safe_num(v.get(key)) or 0) - thresh))

            top3 = matched[:3]
            recall = matched[:min(10, len(matched))]
            recall_names = [m['name'] for m in recall]
            if len(recall_names) < 5:
                # 凑 5 个
                others = [m['name'] for m in fwmavs if m['name'] not in recall_names]
                recall_names = recall_names + others[:5 - len(recall_names)]

            qid = f"dr_g_{600 + idx + 1:03d}"
            diff = diff_pool[idx] if idx < len(diff_pool) else 1

            recs = []
            for rank, t in enumerate(top3, 1):
                val = safe_num(t.get(key))
                recs.append({
                    "rank": rank,
                    "vehicle": t['name'],
                    "match_score": round(0.95 - 0.05 * (rank - 1), 2),
                    "reasoning": f"{label} {thresh} {unit} 约束下匹配良好（实际 {val} {unit}）"
                })

            questions.append({
                "id": qid,
                "category": "B1",
                "type": "方案推荐·简单约束",
                "difficulty": diff,
                "question": f"想做一架{label} {thresh} {unit}的扑翼机，推荐参考哪些样机？",
                "task_constraints": {cname: thresh},
                "gold_recommendations": recs,
                "expected_recall_top10": recall_names[:10],
                "tool_call_required": [],
                "support_docs": [],
                "annotator": "wjl-template",
                "annotation_date": TODAY,
                "generated_by": "template",
            })
            idx += 1

    # can_hover 约束
    for hover_val in [True, False]:
        if idx >= n: break
        matched = [v for v in fwmavs if v.get('can_hover') == hover_val]
        if len(matched) < 3: continue
        top3 = matched[:3]
        recall_names = [m['name'] for m in matched[:10]]
        if len(recall_names) < 5: recall_names = recall_names + [m['name'] for m in fwmavs[:5-len(recall_names)]]
        qid = f"dr_g_{600 + idx + 1:03d}"
        recs = []
        for rank, t in enumerate(top3, 1):
            recs.append({"rank": rank, "vehicle": t['name'], "match_score": round(0.95 - 0.05 * (rank - 1), 2), "reasoning": f"can_hover={hover_val} 匹配"})
        questions.append({
            "id": qid, "category": "B1", "type": "方案推荐·简单约束", "difficulty": 1,
            "question": f"想做一架{'能悬停' if hover_val else '不悬停'}的扑翼机，推荐参考哪些样机？",
            "task_constraints": {"can_hover": hover_val},
            "gold_recommendations": recs, "expected_recall_top10": recall_names[:10],
            "tool_call_required": [], "support_docs": [],
            "annotator": "wjl-template", "annotation_date": TODAY, "generated_by": "template",
        })
        idx += 1

    # 按生物原型
    biology_to_fwmav = {}
    for m in kg['mimics']:
        biology_to_fwmav.setdefault(m['o'], []).append(m['v'])
    for bio, vehicles in biology_to_fwmav.items():
        if idx >= n: break
        if len(vehicles) < 1: continue
        recall_names = vehicles[:10]
        if len(recall_names) < 5: recall_names = recall_names + [v['name'] for v in fwmavs if v['name'] not in recall_names][:5-len(recall_names)]
        recs = []
        for rank, name in enumerate(vehicles[:3], 1):
            recs.append({"rank": rank, "vehicle": name, "match_score": round(0.95 - 0.05 * (rank - 1), 2), "reasoning": f"仿{bio}原型匹配"})
        qid = f"dr_g_{600 + idx + 1:03d}"
        questions.append({
            "id": qid, "category": "B1", "type": "方案推荐·简单约束", "difficulty": 2,
            "question": f"想以{bio}为仿生原型设计扑翼机，推荐参考哪些样机？",
            "task_constraints": {"biological_prototype": bio},
            "gold_recommendations": recs, "expected_recall_top10": recall_names[:10],
            "tool_call_required": [], "support_docs": [],
            "annotator": "wjl-template", "annotation_date": TODAY, "generated_by": "template",
        })
        idx += 1

    return questions[:n]


def gen_b2_complex(kg, n=100):
    """B2: 复杂约束推荐（多约束）.

    修复 v2: 严格匹配 biological_prototype（基于 MIMICS 关系）.
    """
    def safe_num(x):
        try: return float(x) if x is not None else None
        except (TypeError, ValueError): return None
    questions = []
    fwmavs = [v for v in kg['fwmav'] if safe_num(v.get('weight_g_std')) and safe_num(v.get('wingspan_mm'))]

    # 构建 仿生原型 → FWMAV 映射（基于 MIMICS 关系）
    bio_to_vehicles = {}
    for m in kg['mimics']:
        bio_to_vehicles.setdefault(m['o'], set()).add(m['v'])

    # 同义/抽象生物的扩展映射（如"鹰"→"金鹰","鸟类"→所有鸟类系）
    bio_aliases = {
        '鹰': ['金鹰', '隼', '鸟类'],   # 鹰是抽象，扩展到 KG 中的具体节点
        '鹰类': ['金鹰', '隼', '鸟类'],
        '猛禽': ['金鹰', '隼', '鸟类'],
    }

    biology_list = list(bio_to_vehicles.keys())  # 只用 KG 中真实存在的生物原型

    idx = 0
    attempts = 0
    while idx < n and attempts < n * 10:
        attempts += 1
        bio = random.choice(biology_list)

        # 拿到该生物对应的 FWMAV 候选
        vehicle_names = bio_to_vehicles.get(bio, set())
        # 扩展同义生物
        for alias_bio, real_bios in bio_aliases.items():
            if bio in real_bios:
                for rb in real_bios:
                    vehicle_names = vehicle_names | bio_to_vehicles.get(rb, set())

        if not vehicle_names: continue

        # 在 vehicle_names 范围内进一步筛约束
        candidate_pool = [v for v in fwmavs if v['name'] in vehicle_names]
        if not candidate_pool: continue

        # 随机生成约束
        # 用候选池的实际范围作为采样依据，提升匹配率
        ws_list = [safe_num(v.get('weight_g_std')) for v in candidate_pool]
        ws_list = [w for w in ws_list if w]
        max_w_seen = max(ws_list) if ws_list else 1000

        w_max = random.choice([
            int(max_w_seen * 1.2), int(max_w_seen * 1.5), int(max_w_seen * 2.0)
        ])
        wingspan_max_mm = random.choice([500, 1000, 2000, 3000])
        endurance_min_s = random.choice([60, 300, 600, 1800])
        # can_hover 仅在生物本身可悬停时设 True
        bio_node = next((o for o in kg['organism'] if o['name'] == bio), None)
        bio_can_hover = bio_node.get('can_hover') if bio_node else None
        can_hover = random.choice([True, False, None]) if bio_can_hover else random.choice([False, None])

        # 找匹配
        matched = []
        for v in candidate_pool:
            w = safe_num(v.get('weight_g_std'))
            ws = safe_num(v.get('wingspan_mm'))
            e = safe_num(v.get('endurance_s_std'))
            if w is None or w > w_max: continue
            if ws is None or ws > wingspan_max_mm: continue
            if e is None or e < endurance_min_s: continue
            if can_hover is not None and v.get('can_hover') != can_hover: continue
            matched.append(v)

        if len(matched) < 1:
            continue

        # 按重量优先排序
        matched.sort(key=lambda v: safe_num(v.get('weight_g_std')) or 0)

        top3 = matched[:3]
        recall_names = [m['name'] for m in matched[:10]]
        # 凑 5
        if len(recall_names) < 5:
            others = [v['name'] for v in candidate_pool if v['name'] not in recall_names]
            recall_names = recall_names + others[:5 - len(recall_names)]
            if len(recall_names) < 5:
                # 再凑生物原型外的
                others2 = [v['name'] for v in fwmavs if v['name'] not in recall_names]
                recall_names = recall_names + others2[:5 - len(recall_names)]

        recs = []
        for rank, t in enumerate(top3, 1):
            w = safe_num(t.get('weight_g_std'))
            ws = safe_num(t.get('wingspan_mm'))
            e = safe_num(t.get('endurance_s_std'))
            recs.append({
                "rank": rank,
                "vehicle": t['name'],
                "match_score": round(0.95 - 0.05 * (rank - 1), 2),
                "reasoning": f"仿{bio}原型（KG 标注 MIMICS）+ 翼展 {ws} mm（≤{wingspan_max_mm}）+ 重量 {w} g（≤{w_max}）+ 续航 {e} s（≥{endurance_min_s}）多约束匹配"
            })

        qid = f"dr_g_{700 + idx + 1:03d}"
        constraints = {
            "biological_prototype": bio,
            "weight_max_g": w_max,
            "wingspan_max_mm": wingspan_max_mm,
            "endurance_min_s": endurance_min_s,
        }
        if can_hover is not None:
            constraints["can_hover"] = can_hover

        questions.append({
            "id": qid,
            "category": "B2",
            "type": "方案推荐·复杂约束",
            "difficulty": 3,
            "question": f"任务约束：仿{bio}原型 + 重量 ≤ {w_max} g + 翼展 ≤ {wingspan_max_mm} mm + 续航 ≥ {endurance_min_s/60:.0f} 分钟" + (f" + 能悬停" if can_hover else "") + "，推荐 Top-3 参考样机。",
            "task_constraints": constraints,
            "gold_recommendations": recs,
            "expected_recall_top10": recall_names[:10],
            "tool_call_required": ["hassanalian_weight"],
            "support_docs": [],
            "annotator": "wjl-template",
            "annotation_date": TODAY,
            "generated_by": "template-v2",
        })
        idx += 1

    return questions[:n]


# ========== 主流程 ==========
def main():
    print("加载 KG 数据...")
    kg = load_kg_data()
    print(f"  FWMAV: {len(kg['fwmav'])}")
    print(f"  Organism: {len(kg['organism'])}")
    print(f"  MIMICS: {len(kg['mimics'])}")

    generators = [
        ('a1', gen_a1_definition, 100),
        ('a2', gen_a2_attribute, 100),
        ('a3', gen_a3_compare, 100),
        ('a4', gen_a4_reasoning, 100),
        ('b1', gen_b1_simple, 100),
        ('b2', gen_b2_complex, 100),
    ]

    all_qs = []
    for name, gen, n in generators:
        print(f"\n生成 {name.upper()} ({n} 题)...")
        qs = gen(kg, n)
        print(f"  实际生成: {len(qs)}")
        out_path = OUTPUT_DIR / f'generated_{name}.jsonl'
        with open(out_path, 'w', encoding='utf-8') as f:
            for q in qs:
                f.write(json.dumps(q, ensure_ascii=False) + '\n')
        print(f"  写入: {out_path.name}")
        all_qs.extend(qs)

    # 合并
    out_all = OUTPUT_DIR / 'generated_600.jsonl'
    with open(out_all, 'w', encoding='utf-8') as f:
        for q in all_qs:
            f.write(json.dumps(q, ensure_ascii=False) + '\n')
    print(f"\n=== 总计生成 {len(all_qs)} 题 → {out_all.name} ===")


if __name__ == "__main__":
    main()
