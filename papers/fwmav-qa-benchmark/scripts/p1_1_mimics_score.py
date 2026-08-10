#!/usr/bin/env python3
"""P1-1: MIMICS 关系细分 + 自动打分 (v2: 5 维度).

5 个维度:
- mimics_scale      : 尺度相似度      (重量 + 翼展)
- mimics_morphology : 形态/构型相似度  (wing_pairs + has_tail + 展弦比AR)
- mimics_kinematics : 运动学相似度    (扑频)
- mimics_aero       : 气动机制相似度  (Reynolds数 Re + Strouhal数 St)
- mimics_functional : 飞行功能相似度  (can_hover + can_glide)

每个分数 ∈ [0, 1]，越大越相似。不匹配的布尔特征给 0.3 软惩罚，不给 0。
Re 由 speed × chord (≈ wingspan/4) / ν 计算；St 由 freq × chord / speed 计算。
展弦比 AR 由 Shyy 尺度律从质量估算翼面积后导出。
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


def sim_log_pair(a, b):
    """两个单值之间的对数相似度: exp(-|log10(a/b)|)."""
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return math.exp(-abs(math.log10(a / b)))


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
    """计算 5 类相似度.

    Args:
        vehicle:  FlappingWingVehicle 节点属性
        organism: Organism 节点属性

    Returns:
        dict: mimics_scale / mimics_morphology / mimics_kinematics /
              mimics_aero / mimics_functional
    """
    sims = {}
    NU = 1.516e-5  # 运动粘度 m²/s (20°C, 海平面)

    weight   = to_float(vehicle.get("weight_g_std"))
    span_mm  = to_float(vehicle.get("wingspan_mm"))
    freq     = to_float(vehicle.get("frequency_hz_min_std"))
    speed    = to_float(vehicle.get("speed_max_m_s_std"))

    org_mass_lo  = to_float(organism.get("body_mass_g_min"))
    org_mass_hi  = to_float(organism.get("body_mass_g_max"))
    org_span_lo  = to_float(organism.get("wingspan_cm_min"))
    org_span_hi  = to_float(organism.get("wingspan_cm_max"))
    org_freq_lo  = to_float(organism.get("flap_freq_hz_min"))
    org_freq_hi  = to_float(organism.get("flap_freq_hz_max"))
    org_Re_lo    = to_float(organism.get("reynolds_min"))
    org_Re_hi    = to_float(organism.get("reynolds_max"))
    org_St_lo    = to_float(organism.get("strouhal_min"))
    org_St_hi    = to_float(organism.get("strouhal_max"))

    # ── 1. SCALE: 重量 + 翼展 ───────────────────────────────────────
    s_mass = sim_log(weight, org_mass_lo, org_mass_hi)
    s_span = sim_log(span_mm / 10.0 if span_mm else None, org_span_lo, org_span_hi)
    scale  = avg_skip_none([s_mass, s_span])
    if scale is not None:
        sims["mimics_scale"] = round(scale, 3)

    # ── 2. MORPHOLOGY: wing_pairs + has_tail + 展弦比 AR ────────────
    v_wp = vehicle.get("wing_pairs")
    o_wp = organism.get("wing_pairs")
    v_ht = vehicle.get("has_tail")
    o_ht = organism.get("has_tail")

    morph_parts = []
    if v_wp is not None and o_wp is not None:
        morph_parts.append(1.0 if v_wp == o_wp else 0.3)
    if v_ht is not None and o_ht is not None:
        morph_parts.append(1.0 if v_ht == o_ht else 0.3)

    # 展弦比 AR = b² / S，翼面积 S 用 Shyy 尺度律从质量估算
    if weight and span_mm:
        v_AR = (span_mm / 1000.0) ** 2 / (0.16 * (weight / 1000.0) ** (2.0 / 3.0))
        org_mass_mid = avg_skip_none([org_mass_lo, org_mass_hi])
        org_span_mid = avg_skip_none([org_span_lo, org_span_hi])
        if org_mass_mid and org_span_mid and org_mass_mid > 0:
            o_AR = (org_span_mid / 100.0) ** 2 / (0.16 * (org_mass_mid / 1000.0) ** (2.0 / 3.0))
            s_AR = sim_log_pair(v_AR, o_AR)
            if s_AR is not None:
                morph_parts.append(s_AR)

    if morph_parts:
        sims["mimics_morphology"] = round(avg_skip_none(morph_parts), 3)

    # ── 3. KINEMATICS: 扑频 ─────────────────────────────────────────
    s_freq = sim_log(freq, org_freq_lo, org_freq_hi)
    if s_freq is not None:
        sims["mimics_kinematics"] = round(s_freq, 3)

    # ── 4. AERO: Reynolds数 Re + Strouhal数 St ──────────────────────
    # 弦长估算: chord ≈ wingspan / 4
    aero_parts = []
    if speed and span_mm and speed > 0:
        chord_m = (span_mm / 1000.0) / 4.0
        v_Re = speed * chord_m / NU
        s_Re = sim_log(v_Re, org_Re_lo, org_Re_hi)
        if s_Re is not None:
            aero_parts.append(s_Re)
        if freq and freq > 0:
            v_St = freq * chord_m / speed
            s_St = sim_log(v_St, org_St_lo, org_St_hi)
            if s_St is not None:
                aero_parts.append(s_St)
    if aero_parts:
        sims["mimics_aero"] = round(avg_skip_none(aero_parts), 3)

    # ── 5. FUNCTIONAL: can_hover + can_glide ────────────────────────
    v_hover = vehicle.get("can_hover")
    o_hover = organism.get("can_hover")
    v_glide = vehicle.get("can_glide")
    o_glide = organism.get("can_glide")

    func_parts = []
    if v_hover is not None and o_hover is not None:
        func_parts.append(1.0 if v_hover == o_hover else 0.3)
    if v_glide is not None and o_glide is not None:
        func_parts.append(1.0 if v_glide == o_glide else 0.3)
    if func_parts:
        sims["mimics_functional"] = round(avg_skip_none(func_parts), 3)

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
                       r.mimics_scale, r.mimics_functional,
                       r.mimics_dominant_type, r.mimics_dominant_score,
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
                f"{k.replace('mimics_', '')[:5]}:{v}"
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
