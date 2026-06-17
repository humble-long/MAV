#!/usr/bin/env python3
"""P0-2 抽样验证后的修复脚本.

修复内容:
1. KUBeetle-S wingspan_mm: 100 -> 200 (Phan 2019 IJMAV 真实值)
2. PigeonBot 不是扑翼机 -> frequency_hz=null + propulsion_type='propeller' + wing_role='morphing_only'
3. DelFly Nimble 数据源 DOI 改正
4. 12 个 unverified 字段加 unverified 标记
5. Bionic Flying Fox endurance_min 35 偏高，调到 7（FESTO 演示机典型）
6. 联级重跑 P0-3 / P1-1 / P1-2 (单独脚本调用)
"""

from __future__ import annotations
from datetime import datetime
import os
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")


# ============================================================
# 修复 1: KUBeetle-S wingspan
# ============================================================
KUBEETLE_FIX = {
    "name": "KUBeetle-S",
    "updates": {
        "wingspan_mm": 200,
        "p0_2_source": "Phan 2019 IJMAV (DOI: 10.1177/1756829319861371)",
        "wingspan_old_value_was": "100 (incorrect, fixed in 2026-06-17 audit)",
        "speed_max_m_s_unverified": True,
    },
    "remove_keys": ["speed_max_m_s"],  # 完全移除，权威源未发布
}

# ============================================================
# 修复 2: PigeonBot 不是扑翼机
# ============================================================
PIGEONBOT_FIX = {
    "name": "PigeonBot",
    "updates": {
        "propulsion_type": "propeller",
        "wing_role": "morphing_only",
        "is_atypical_fwmav": True,
        "atypical_reason": "Front-mounted propeller for thrust; wings only morph for steering. Retained as morphing-wing edge case for ontology completeness.",
        "p0_2_source": "Chang 2020 Science Robotics (DOI: 10.1126/scirobotics.aay1246)",
        "frequency_hz_old_value_was": "4 (incorrect for propeller-driven; removed)",
        "endurance_min_unverified": True,
        "speed_max_m_s_unverified": True,
    },
    "remove_keys": ["frequency_hz"],
}

# ============================================================
# 修复 3: DelFly Nimble 数据源 DOI
# ============================================================
DELFLY_NIMBLE_FIX = {
    "name": "DelFly Nimble",
    "updates": {
        "p0_2_source": "Karasek 2018 Science (DOI: 10.1126/science.aat0350)",
        "speed_side_m_s_unverified": True,
    },
    "remove_keys": [],
}

# ============================================================
# 修复 4: 其他 unverified 字段标记
# ============================================================
UNVERIFIED_MARKS = {
    "SmartBird": ["speed_m_s_unverified"],
    "BionicOpter": ["endurance_min_unverified", "speed_max_m_s_unverified"],
    "Bionic Flying Fox": [
        "frequency_hz_unverified",
        "speed_max_m_s_unverified",
        "can_hover_unverified",
    ],
    "Nano Hummingbird": ["chord_mm_unverified", "endurance_min_unverified"],
    "RoboRaven": ["speed_max_m_s_unverified"],
}

# ============================================================
# 修复 5: Bionic Flying Fox endurance 35 -> 7 (偏高)
# ============================================================
FLYING_FOX_FIX = {
    "name": "Bionic Flying Fox",
    "updates": {
        "endurance_min": 7,
        "endurance_min_unverified": True,
        "endurance_min_old_value_was": "35 (suspect; FESTO did not publish; comparable demo flyers ~7-8 min)",
        "p0_2_source": "FESTO 2018 technical brief (endurance not officially published; estimated to ~7 min based on comparable FESTO demo platforms)",
    },
    "remove_keys": [],
}


def apply_fix(sess, name: str, updates: dict, remove_keys: list, today: str):
    """对单个 FWMAV 节点应用修复."""
    # 检查存在
    r = sess.run(
        "MATCH (n:FlappingWingVehicle {name:$n}) RETURN count(n) AS c", n=name
    ).single()
    if r["c"] == 0:
        print(f"  ⚠ 节点不存在: {name}")
        return False

    # 加 fix metadata
    payload = dict(updates)
    payload["last_audit_at"] = today
    payload["last_audit_by"] = "P0-2 validation 2026-06-17"

    # 写更新
    if payload:
        sess.run(
            "MATCH (n:FlappingWingVehicle {name:$n}) SET n += $p",
            n=name,
            p=payload,
        )

    # 删除字段（PigeonBot 的 frequency_hz / KUBeetle-S 的 speed_max_m_s）
    for k in remove_keys:
        sess.run(
            f"MATCH (n:FlappingWingVehicle {{name:$n}}) REMOVE n.`{k}`",
            n=name,
        )
    return True


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"开始执行 P0-2 修复... (日期 {today})")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    with driver.session() as sess:
        print("\n--- 修复 1: KUBeetle-S 翼展 ---")
        if apply_fix(sess, **{k: v for k, v in KUBEETLE_FIX.items() if k != "name"}, name=KUBEETLE_FIX["name"], today=today):
            print(f"  ✅ KUBeetle-S: wingspan_mm 100 → 200, removed speed_max_m_s")

        print("\n--- 修复 2: PigeonBot 推进方式 ---")
        if apply_fix(sess, **{k: v for k, v in PIGEONBOT_FIX.items() if k != "name"}, name=PIGEONBOT_FIX["name"], today=today):
            print(f"  ✅ PigeonBot: removed frequency_hz, added propulsion_type=propeller")

        print("\n--- 修复 3: DelFly Nimble DOI ---")
        if apply_fix(sess, **{k: v for k, v in DELFLY_NIMBLE_FIX.items() if k != "name"}, name=DELFLY_NIMBLE_FIX["name"], today=today):
            print(f"  ✅ DelFly Nimble: DOI 修正")

        print("\n--- 修复 4: 其他 unverified 字段标记 ---")
        for name, marks in UNVERIFIED_MARKS.items():
            payload = {m: True for m in marks}
            payload["last_audit_at"] = today
            payload["last_audit_by"] = "P0-2 validation 2026-06-17"
            r = sess.run(
                "MATCH (n:FlappingWingVehicle {name:$n}) RETURN count(n) AS c", n=name
            ).single()
            if r["c"] == 0:
                print(f"  ⚠ 节点不存在: {name}")
                continue
            sess.run(
                "MATCH (n:FlappingWingVehicle {name:$n}) SET n += $p",
                n=name, p=payload,
            )
            print(f"  ✅ {name}: {len(marks)} 个 unverified 标记")

        print("\n--- 修复 5: Bionic Flying Fox endurance ---")
        if apply_fix(sess, **{k: v for k, v in FLYING_FOX_FIX.items() if k != "name"}, name=FLYING_FOX_FIX["name"], today=today):
            print(f"  ✅ Bionic Flying Fox: endurance_min 35 → 7")

    driver.close()
    print("\n=== P0-2 修复完成 ===")
    print("⏭  下一步: 联级重跑 P0-3 / P1-1 / P1-2 (单独脚本)")


if __name__ == "__main__":
    main()
