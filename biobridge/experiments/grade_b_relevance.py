"""自动给 39 个 FWMAV 打 graded relevance (0-3)，针对每道 B 类题.

输入: papers/fwmav-qa-benchmark/data/fwmav_qa_v2_b_annotated.jsonl
输出: papers/fwmav-qa-benchmark/data/fwmav_qa_v2_b_graded.jsonl

打分规则:
  rel=3  全部硬约束满足 + 软约束匹配（仿生原型/任务类型）
  rel=2  全部硬约束满足，但软约束部分不匹配
  rel=1  违反 1 个硬约束，且越界幅度 ≤ 20%
  rel=0  违反 2+ 硬约束，或严重越界（>20%）

输出 schema:
  每道 B 题增加一个字段:
    "graded_relevance": {
       "vehicle_name_1": 3,
       "vehicle_name_2": 2,
       ...   # 39 个 FWMAV 全部打分
    }
"""

from __future__ import annotations
import json
import os
import re
from pathlib import Path
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_IN  = ROOT / "papers" / "fwmav-qa-benchmark" / "data" / "fwmav_qa_v2_b_annotated.jsonl"
DATA_OUT = ROOT / "papers" / "fwmav-qa-benchmark" / "data" / "fwmav_qa_v2_b_graded.jsonl"

URI = "bolt://localhost:7687"
USER = "neo4j"
PWD = os.environ.get("NEO4J_PASSWORD", "")

# ───────────────────────────────────────────────────────────────
# 1. 从 KG 拉取 FWMAV 节点 + MIMICS 仿生关系
# ───────────────────────────────────────────────────────────────

def load_kg_data() -> tuple[dict, dict]:
    """Returns: ({vehicle_name: props}, {vehicle_name: [organism_names]})"""
    drv = GraphDatabase.driver(URI, auth=(USER, PWD))
    vehicles, mimics = {}, {}
    with drv.session() as s:
        for r in s.run("MATCH (v:FlappingWingVehicle) RETURN v.name AS n, properties(v) AS p"):
            vehicles[r["n"]] = r["p"]
        for r in s.run(
            "MATCH (v:FlappingWingVehicle)-[:MIMICS]->(o:Organism) "
            "RETURN v.name AS vn, collect(o.name) AS orgs"
        ):
            mimics[r["vn"]] = r["orgs"]
    drv.close()
    return vehicles, mimics


# ───────────────────────────────────────────────────────────────
# 2. 字段值提取（统一返回 float 或 None）
# ───────────────────────────────────────────────────────────────

def to_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    m = re.match(r"^([\d.]+)\s*[-~～]\s*([\d.]+)$", s)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    try:
        return float(s)
    except ValueError:
        return None


# ───────────────────────────────────────────────────────────────
# 3. 约束验证逻辑
# ───────────────────────────────────────────────────────────────

# 数值约束 → (KG 字段, 比较方向)，方向 'le' = 实际 ≤ 限值; 'ge' = 实际 ≥ 限值
NUMERIC_RULES = {
    "weight_max_g":          ("weight_g_std",       "le"),
    "weight_min_g":          ("weight_g_std",       "ge"),
    "wingspan_max_mm":       ("wingspan_mm",        "le"),
    "wingspan_min_mm":       ("wingspan_mm",        "ge"),
    "endurance_min_s":       ("endurance_s_std",    "ge"),
    "endurance_max_s":       ("endurance_s_std",    "le"),
    "endurance_min":         ("endurance_s_std",    "ge"),  # 单位也是秒
    "speed_min_m_s":         ("speed_max_m_s_std",  "ge"),
    "speed_max_m_s":         ("speed_max_m_s_std",  "le"),
    "frequency_min_hz":      ("frequency_hz_min_std", "ge"),
    "frequency_max_hz":      ("frequency_hz_min_std", "le"),
    "efficiency_min":        ("efficiency",         "ge"),
}

# 布尔/能力约束：(KG 字段，期望值)
BOOL_RULES = {
    "can_hover":     ("can_hover",   True),
    "is_tailless":   ("has_tail",    False),  # is_tailless=True ↔ has_tail=False
    "needs_camera":  None,  # KG 无字段，跳过
    "untethered":    None,  # KG 无字段，跳过
}

# 严重越界阈值（>20%）
SEVERE_RATIO = 0.20


def check_numeric(key, value, vehicle):
    """Returns (violated, severe). 数据缺失时 returns (None, None)."""
    if key not in NUMERIC_RULES:
        return None, None
    kg_field, direction = NUMERIC_RULES[key]
    actual = to_float(vehicle.get(kg_field))
    if actual is None or value is None:
        return None, None
    if direction == "le":
        violated = actual > value
        ratio = (actual - value) / max(value, 1e-6)
    else:
        violated = actual < value
        ratio = (value - actual) / max(value, 1e-6)
    return violated, (violated and ratio > SEVERE_RATIO)


def check_bool(key, value, vehicle):
    """Returns (violated, severe). 数据缺失或无规则时 returns (None, None)."""
    if key not in BOOL_RULES or BOOL_RULES[key] is None:
        return None, None
    kg_field, expected_when_true = BOOL_RULES[key]
    actual = vehicle.get(kg_field)
    if actual is None:
        return None, None
    if value is True:
        violated = (actual != expected_when_true)
    else:
        # value is False, 约束是"不需要" → 不构成硬约束（按之前讨论）
        return None, None
    return violated, False  # bool 违反不算严重越界


def check_wing_count(value, vehicle):
    """wing_count=4 时要求 wing_pairs=2，wing_count=2 时要求 wing_pairs=1."""
    wp = vehicle.get("wing_pairs")
    if wp is None or value is None:
        return None, None
    expected_wp = value / 2  # 2 翅膀 = 1 对，4 翅膀 = 2 对
    return (wp != expected_wp), False


def check_drive_mechanism(value, vehicle):
    """drive_mechanism 是字符串约束，看 KG 的 drive_type 是否包含."""
    actual = vehicle.get("drive_type")
    if actual is None or not value:
        return None, None
    actual_l = str(actual).lower()
    value_l = str(value).lower()
    if value_l == "piezoelectric":
        match = "piezo" in actual_l or "压电" in actual
    else:
        match = value_l in actual_l or value in str(actual)
    return (not match), False


def check_biological_prototype(value, vehicle_name, mimics_dict):
    """查 vehicle 是否 MIMICS 到指定的生物原型（包含匹配）."""
    if not value:
        return None
    orgs = mimics_dict.get(vehicle_name, [])
    for o in orgs:
        if value in o or o in value:
            return True
    # 也允许"鸟类/鸟"宽匹配：vehicle 仿生任何鸟都算
    BIRD_FAMILY = {"鸽子", "海鸥", "海鸠 (Guillemot)", "金鹰", "隼", "凤凰", "乌鸦", "鸮", "鸟类", "大型鸟类"}
    INSECT_FAMILY = {"苍蝇", "蜜蜂", "蜻蜓", "蝴蝶", "甲虫", "甲虫 (Beetle)", "独角仙", "昆虫", "昆虫 (布局)"}
    if value in ("鸟类", "鸟"):
        for o in orgs:
            if o in BIRD_FAMILY:
                return True
    if value == "昆虫":
        for o in orgs:
            if o in INSECT_FAMILY:
                return True
    if value == "猛禽":
        for o in orgs:
            if o in {"金鹰", "隼", "鸮"}:
                return True
    return False


def check_mission_type(value, vehicle):
    """mission_type 软约束：基于 vehicle 的 can_hover / flight_modes / description 判断."""
    if not value:
        return None
    v = str(value).lower()
    can_hover = vehicle.get("can_hover", False)
    can_glide = vehicle.get("can_glide", False)
    desc = (str(vehicle.get("description", "")) + " " + str(vehicle.get("flight_modes", ""))).lower()

    if "hover" in v:
        return can_hover is True
    if "cruise" in v or "巡航" in v:
        return can_glide is True or vehicle.get("speed_max_m_s_std", 0) >= 5
    if "maneuver" in v or "机动" in v:
        return can_hover is True  # 机动一般要求悬停级灵活性
    if "indoor" in v or "室内" in v:
        # 室内要求小尺寸
        ws = to_float(vehicle.get("wingspan_mm"))
        return ws is not None and ws <= 400
    if "outdoor" in v or "户外" in v or "recon" in v or "侦察" in v:
        ws = to_float(vehicle.get("wingspan_mm"))
        return ws is not None and ws >= 200
    if "aerial_aquatic" in v or "跨介质" in v:
        return "aquatic" in desc or "水" in str(vehicle.get("description", ""))
    return True  # 未知 mission_type 默认匹配


# ───────────────────────────────────────────────────────────────
# 4. 综合打分
# ───────────────────────────────────────────────────────────────

def score_relevance(task_constraints, vehicle_name, vehicle, mimics_dict) -> int:
    hard_violations = 0
    severe = False
    soft_mismatches = 0

    for key, value in task_constraints.items():
        if key == "endurance_unit":
            continue

        # 数值约束
        if key in NUMERIC_RULES:
            v, sev = check_numeric(key, value, vehicle)
            if v is None:  # 数据缺失，跳过
                continue
            if v:
                hard_violations += 1
                if sev:
                    severe = True
            continue

        # endurance_distance_km：转秒后用 endurance_min_s 逻辑
        if key == "endurance_distance_km":
            speed = to_float(vehicle.get("speed_max_m_s_std"))
            endur = to_float(vehicle.get("endurance_s_std"))
            if speed and endur:
                actual_km = speed * endur / 1000
                if actual_km < value:
                    ratio = (value - actual_km) / value
                    hard_violations += 1
                    if ratio > SEVERE_RATIO:
                        severe = True
            continue

        # payload_max_g：用 weight_empty_g + payload 估算
        if key == "payload_max_g":
            wt = to_float(vehicle.get("weight_g_std"))
            we = to_float(vehicle.get("weight_empty_g"))
            if wt is not None and we is not None:
                capacity = wt - we
                if value > capacity:
                    ratio = (value - capacity) / max(value, 1e-6)
                    hard_violations += 1
                    if ratio > SEVERE_RATIO:
                        severe = True
            continue

        # 布尔
        if key in BOOL_RULES:
            v, sev = check_bool(key, value, vehicle)
            if v is None:
                continue
            if v:
                hard_violations += 1
            continue

        # wing_count
        if key == "wing_count":
            v, _ = check_wing_count(value, vehicle)
            if v:
                hard_violations += 1
            continue

        # drive_mechanism
        if key == "drive_mechanism":
            v, _ = check_drive_mechanism(value, vehicle)
            if v:
                hard_violations += 1
            continue

        # 软约束
        if key == "biological_prototype":
            match = check_biological_prototype(value, vehicle_name, mimics_dict)
            if match is False:
                soft_mismatches += 1
            continue

        if key == "mission_type":
            match = check_mission_type(value, vehicle)
            if match is False:
                soft_mismatches += 1
            continue

        # 其他未识别字段忽略
        continue

    # 打分逻辑
    if severe or hard_violations >= 2:
        return 0
    if hard_violations == 1:
        return 1
    if soft_mismatches > 0:
        return 2
    return 3


# ───────────────────────────────────────────────────────────────
# 5. 主循环
# ───────────────────────────────────────────────────────────────

def main():
    print(f"[Load] KG ...")
    vehicles, mimics = load_kg_data()
    print(f"[Load] {len(vehicles)} FWMAVs, MIMICS: {sum(len(v) for v in mimics.values())} 条")

    print(f"[Load] {DATA_IN}")
    items = []
    with open(DATA_IN, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    n_b = sum(1 for it in items if it.get("category") in ("B1", "B2"))
    print(f"[Load] {len(items)} total, {n_b} B-class")

    print(f"[Score] 对 {n_b} 道 B 题 × {len(vehicles)} FWMAV 打分 ...")
    out_items = []
    for it in items:
        if it.get("category") not in ("B1", "B2"):
            out_items.append(it)
            continue
        tc = it.get("task_constraints", {})
        graded = {}
        for vname, vprops in vehicles.items():
            graded[vname] = score_relevance(tc, vname, vprops, mimics)
        new_it = dict(it)
        new_it["graded_relevance"] = graded
        out_items.append(new_it)

    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_OUT, "w", encoding="utf-8") as f:
        for it in out_items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    print(f"[Done] 输出: {DATA_OUT}")

    # 统计分布
    from collections import Counter
    dist = Counter()
    for it in out_items:
        if it.get("category") in ("B1", "B2"):
            for s in it.get("graded_relevance", {}).values():
                dist[s] += 1
    total = sum(dist.values())
    print(f"\n=== relevance 分布（B 类 × 39 FWMAV = {total} 个 pair）===")
    for k in sorted(dist.keys(), reverse=True):
        print(f"  rel={k}: {dist[k]:5d}  ({dist[k]/total*100:.1f}%)")


if __name__ == "__main__":
    main()
