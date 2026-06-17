#!/usr/bin/env python3
"""P1-1: MIMICS 关系细分 + 自动打分.

把现有 50 条 MIMICS 边升级为带 4 类相似度分数的边:
- mimics_aero       : 气动参数相似度 (Reynolds, Strouhal)
- mimics_kinematics : 运动学相似度 (扑频)
- mimics_morphology : 形态学相似度 (展弦比、悬停能力一致性)
- mimics_scale      : 尺度相似度 (重量、翼展)

每个分数 ∈ [0, 1]，越大越相似。
不删除原 MIMICS 边，仅在原边上加属性 + 取 dominant_type.

公式（对数尺度的相对距离）:
    sim_log(a, b) = exp(-|log(a/b)|)

对工程层单值 vs 生物层 [min, max] 区间:
    用最近邻取相对误差，区间内 -> 1.0
"""

from __future__ import annotations
import math
import sys
from datetime import datetime
import os
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")


def sim_log(value, lo, hi):
    """value 与区间 [lo, hi] 的对数相似度.

    - value 在区间内: 1.0
    - value 偏离区间: exp(-|log10(value/最近端点)|)
    - 缺失: None
    """
    if value is None or lo is None or hi is None:
        return None
    if value <= 0 or lo <= 0 or hi <= 0:
        return None
    if lo <= value <= hi:
        return 1.0
    nearest = lo if value < lo else hi
    log_dist = abs(math.log10(value / nearest))
    return math.exp(-log_dist)


def avg_skip_none(values):
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def to_float(v):
    """统一把数值/区间字符串转成 float（区间取中值）.

    None / 空字符串 -> None
    """
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    import re
    m = re.match(r"^([\d.]+)\s*[-~～]\s*([\d.]+)$", s)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    try:
        return float(s)
    except ValueError:
        return None


def compute_similarities(vehicle, organism):
    """计算 4 类相似度.

    Args:
        vehicle: FlappingWingVehicle 节点属性 (含 *_std)
        organism: Organism 节点属性 (含 *_min/*_max)

    Returns:
        dict with keys: mimics_scale, mimics_kinematics, mimics_aero, mimics_morphology
    """
    sims = {}

    # ===== 1. SCALE: 重量 + 翼展 =====
    weight = to_float(vehicle.get("weight_g_std"))
    span = to_float(vehicle.get("wingspan_mm"))  # mm
    org_mass_lo = to_float(organism.get("body_mass_g_min"))
    org_mass_hi = to_float(organism.get("body_mass_g_max"))
    org_span_lo = to_float(organism.get("wingspan_cm_min"))
    org_span_hi = to_float(organism.get("wingspan_cm_max"))

    s_mass = sim_log(weight, org_mass_lo, org_mass_hi)
    # 翼展从 mm 转 cm
    s_span = sim_log(span / 10.0 if span else None, org_span_lo, org_span_hi)
    scale = avg_skip_none([s_mass, s_span])
    if scale is not None:
        sims["mimics_scale"] = round(scale, 3)

    # ===== 2. KINEMATICS: 扑频 =====
    freq = to_float(vehicle.get("frequency_hz_min_std"))
    org_freq_lo = to_float(organism.get("flap_freq_hz_min"))
    org_freq_hi = to_float(organism.get("flap_freq_hz_max"))
    s_freq = sim_log(freq, org_freq_lo, org_freq_hi)
    if s_freq is not None:
        sims["mimics_kinematics"] = round(s_freq, 3)

    # ===== 3. AERO: 速度 (Reynolds 代理) =====
    speed = to_float(vehicle.get("speed_max_m_s_std"))
    org_speed_lo = to_float(organism.get("cruise_speed_m_s_min"))
    org_speed_hi = to_float(organism.get("cruise_speed_m_s_max"))
    s_speed = sim_log(speed, org_speed_lo, org_speed_hi)
    if s_speed is not None:
        sims["mimics_aero"] = round(s_speed, 3)

    # ===== 4. MORPHOLOGY: 悬停能力一致性 =====
    v_hover = vehicle.get("can_hover")
    o_hover = organism.get("can_hover")
    if v_hover is not None and o_hover is not None:
        # 完全一致 = 1.0; 不一致 = 0.0
        sims["mimics_morphology"] = 1.0 if v_hover == o_hover else 0.0

    return sims


def main():
    print("准备升级 MIMICS 关系...")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    today = datetime.now().strftime("%Y-%m-%d")
    updated = 0
    total = 0
    skipped = 0

    with driver.session() as sess:
        # 取所有 MIMICS 边 + 两端节点属性
        res = sess.run(
            """
            MATCH (v:FlappingWingVehicle)-[r:MIMICS]->(o:Organism)
            RETURN
              v.name AS v_name,
              properties(v) AS v_props,
              o.name AS o_name,
              properties(o) AS o_props,
              elementId(r) AS rel_id
            """
        )
        edges = list(res)
        total = len(edges)
        print(f"  共 {total} 条 MIMICS 边")

        for row in edges:
            v_name = row["v_name"]
            o_name = row["o_name"]
            v_props = row["v_props"]
            o_props = row["o_props"]
            rel_id = row["rel_id"]

            sims = compute_similarities(v_props, o_props)

            # 幂等清理：先删除旧的相似度字段
            sess.run(
                """
                MATCH ()-[r:MIMICS]->()
                WHERE elementId(r) = $rid
                REMOVE r.mimics_aero, r.mimics_kinematics, r.mimics_morphology,
                       r.mimics_scale, r.mimics_dominant_type, r.mimics_dominant_score,
                       r.scored_at
                """,
                rid=rel_id,
            )

            if not sims:
                print(f"  ⚠ {v_name} -> {o_name}: 无可计算相似度，跳过")
                skipped += 1
                continue

            # 找出 dominant_type
            dominant = max(sims.items(), key=lambda kv: kv[1])
            sims["mimics_dominant_type"] = dominant[0].replace("mimics_", "")
            sims["mimics_dominant_score"] = round(dominant[1], 3)
            sims["scored_at"] = today

            # 写回 relation 属性
            sess.run(
                """
                MATCH ()-[r:MIMICS]->()
                WHERE elementId(r) = $rid
                SET r += $props
                """,
                rid=rel_id,
                props=sims,
            )
            updated += 1

            score_summary = " | ".join(
                f"{k.replace('mimics_', '')[:4]}:{v}"
                for k, v in sims.items()
                if k.startswith("mimics_") and not k.endswith("type") and not k.endswith("score")
            )
            print(f"  ✅ {v_name} → {o_name}  [{score_summary}]  dom={sims['mimics_dominant_type']}({sims['mimics_dominant_score']})")

    driver.close()

    print(f"\n=== 完成 ===")
    print(f"  Updated: {updated}/{total}")
    print(f"  Skipped: {skipped}")


if __name__ == "__main__":
    main()
