#!/usr/bin/env python3
"""P0-3: FWMAV 节点属性命名标准化迁移.

策略: "加新字段、保留旧字段"
- 新增 4 个标准字段:
    weight_g_std, endurance_s_std, speed_max_m_s_std, frequency_hz_min/max_std
- 旧字段不删除（保留可追溯）
- 标准化优先级:
    weight: takeoff > total > empty
    endurance: hover_min > min > sec/60
    speed: max_m_s > m_s > forward_m_s > max_km_h/3.6 > flight_speed_m_s
    frequency: 数字直接用; 字符串区间拆 min/max

字段约定:
    weight_g_std            : float
    weight_g_std_kind       : 'takeoff' | 'total' | 'empty'
    endurance_s_std         : float
    endurance_condition_std : 'hover' | 'cruise' | 'mixed'
    speed_max_m_s_std       : float
    frequency_hz_min_std    : float
    frequency_hz_max_std    : float (单值时 = min)
"""

from __future__ import annotations
import re
import sys
from datetime import datetime
import os
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")


def parse_range(value):
    """解析数字或字符串区间 '15-20' / '30~40'，返回 (min, max)."""
    if value is None or value == "":
        return None, None
    if isinstance(value, (int, float)):
        return float(value), float(value)
    s = str(value).strip()
    m = re.match(r"^([\d.]+)\s*[-~～]\s*([\d.]+)$", s)
    if m:
        return float(m.group(1)), float(m.group(2))
    try:
        v = float(s)
        return v, v
    except ValueError:
        return None, None


def to_float_or_mid(value):
    """把数值或区间字符串变成单一浮点（区间取中值）."""
    lo, hi = parse_range(value)
    if lo is None:
        return None
    return (lo + hi) / 2.0


# 旧名兼容
parse_freq = parse_range


def standardize(props: dict) -> dict:
    """根据现有属性产出标准化字段."""
    out = {}

    # ===== weight =====
    for k, kind in [
        ("weight_takeoff_g", "takeoff"),
        ("weight_total_g", "total"),
        ("weight_empty_g", "empty"),
    ]:
        v = to_float_or_mid(props.get(k))
        if v is not None:
            out["weight_g_std"] = v
            out["weight_g_std_kind"] = kind
            break

    # ===== endurance (统一秒) =====
    for k, cond, factor in [
        ("endurance_hover_min", "hover", 60),
        ("endurance_min", "mixed", 60),
        ("endurance_sec", "mixed", 1),
    ]:
        v = to_float_or_mid(props.get(k))
        if v is not None:
            out["endurance_s_std"] = v * factor
            out["endurance_condition_std"] = cond
            break

    # ===== speed_max (统一 m/s) =====
    speed_keys_priority = [
        ("speed_max_m_s", 1.0),
        ("speed_m_s", 1.0),
        ("speed_forward_m_s", 1.0),
        ("flight_speed_m_s", 1.0),
        ("speed_max_km_h", 1.0 / 3.6),
    ]
    for k, factor in speed_keys_priority:
        v = to_float_or_mid(props.get(k))
        if v is not None:
            out["speed_max_m_s_std"] = v * factor
            break

    # ===== frequency (拆 min/max) =====
    fmin, fmax = parse_freq(props.get("frequency_hz"))
    if fmin is not None:
        out["frequency_hz_min_std"] = fmin
        out["frequency_hz_max_std"] = fmax

    return out


def main():
    print("准备标准化 39 个 FWMAV 节点的属性命名...")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    today = datetime.now().strftime("%Y-%m-%d")
    updated = 0

    # 所有可能产生的标准化字段（用于幂等清理）
    STD_FIELDS = [
        "weight_g_std",
        "weight_g_std_kind",
        "endurance_s_std",
        "endurance_condition_std",
        "speed_max_m_s_std",
        "frequency_hz_min_std",
        "frequency_hz_max_std",
    ]

    with driver.session() as sess:
        # 取所有 FWMAV
        res = sess.run("MATCH (n:FlappingWingVehicle) RETURN n.name AS name, properties(n) AS p")
        all_items = [(r["name"], r["p"]) for r in res]

        for name, props in all_items:
            std = standardize(props)

            # 幂等清理：先删除所有旧的标准化字段（哪怕这次不再产出）
            remove_clauses = " ".join(f"REMOVE n.`{k}`" for k in STD_FIELDS)
            sess.run(
                f"MATCH (n:FlappingWingVehicle {{name:$name}}) {remove_clauses}",
                name=name,
            )

            if not std:
                print(f"  ⚠ {name}: 无任何可标准化字段")
                continue

            std["normalized_at"] = today
            sess.run(
                """
                MATCH (n:FlappingWingVehicle {name:$name})
                SET n += $std
                """,
                name=name,
                std=std,
            )
            updated += 1
            n_fields = len([k for k in std if k.endswith("_std")])
            sample = ", ".join(f"{k}={v}" for k, v in list(std.items())[:3] if k != "normalized_at")
            print(f"  ✅ {name}  ({n_fields} std fields)")

    driver.close()

    # 简短自检：把所有 std 字段使用情况打印
    print("\n=== 自检: 标准化字段覆盖率 ===")
    driver2 = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    with driver2.session() as sess:
        for k in [
            "weight_g_std",
            "endurance_s_std",
            "speed_max_m_s_std",
            "frequency_hz_min_std",
        ]:
            res = sess.run(
                f"MATCH (n:FlappingWingVehicle) RETURN count(n) AS total, "
                f"sum(CASE WHEN n.`{k}` IS NOT NULL THEN 1 ELSE 0 END) AS hit"
            )
            r = res.single()
            print(f"  {k}: {r['hit']}/{r['total']} ({r['hit']/r['total']*100:.0f}%)")
    driver2.close()

    print(f"\n=== 完成: {updated} 个节点已标准化 ===")


if __name__ == "__main__":
    main()
