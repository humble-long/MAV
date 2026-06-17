#!/usr/bin/env python3
"""自动校验：对种子题中"能直接由 KG 生成答案"的题目，
验证 gold_answer 中的关键数字是否仍与 KG 一致.

只做事实型问答的对照，推理类不在此自动校验.
"""

from __future__ import annotations
import json
import re
import os
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")


# 验证规则: (题目 id, Cypher 查询, 期望从答案中提取的字段, 期望值或正则)
CHECKS = [
    # kq_009: DelFly Nimble 翼展 330 mm
    ("kq_009", "MATCH (v:FlappingWingVehicle {name:'DelFly Nimble'}) RETURN v.wingspan_mm AS x", "x", 330),
    # kq_011: SmartBird 扑频 2-3 Hz
    ("kq_011", "MATCH (v:FlappingWingVehicle {name:'SmartBird'}) RETURN v.frequency_hz AS x", "x", "2-3"),
    # kq_015: RoboBee X-Wing 重量 0.259 g
    ("kq_015", "MATCH (v:FlappingWingVehicle {name:'RoboBee X-Wing'}) RETURN v.weight_total_g AS x", "x", 0.259),
    # kq_015: RoboBee X-Wing 扑频 170 Hz
    ("kq_015", "MATCH (v:FlappingWingVehicle {name:'RoboBee X-Wing'}) RETURN v.frequency_hz AS x", "x", 170),
    # kq_010: Nano Hummingbird 由 AeroVironment 研制
    ("kq_010", "MATCH (v:FlappingWingVehicle {name:'Nano Hummingbird'})-[:DEVELOPED_BY]->(o:Organization) RETURN o.name AS x", "x", "AeroVironment"),
    # kq_012: 悬停飞行器数量 (验证个数, 不验证全集)
    ("kq_012", "MATCH (v:FlappingWingVehicle) WHERE v.can_hover=true RETURN count(v) AS x", "x", 17),
    # kq_018: 鸽子体重 200-500 g
    ("kq_018", "MATCH (o:Organism {name:'鸽子'}) RETURN o.body_mass_g_min AS lo, o.body_mass_g_max AS hi", "lo", 200),
    ("kq_018", "MATCH (o:Organism {name:'鸽子'}) RETURN o.body_mass_g_min AS lo, o.body_mass_g_max AS hi", "hi", 500),
    # kq_018: 蜂鸟扑频 18-80 Hz
    ("kq_018", "MATCH (o:Organism {name:'蜂鸟'}) RETURN o.flap_freq_hz_min AS lo, o.flap_freq_hz_max AS hi", "lo", 18),
    ("kq_018", "MATCH (o:Organism {name:'蜂鸟'}) RETURN o.flap_freq_hz_max AS hi", "hi", 80),
    # kq_027: PigeonBot 是非典型扑翼机
    ("kq_027", "MATCH (v:FlappingWingVehicle {name:'PigeonBot'}) RETURN v.is_atypical_fwmav AS x", "x", True),
    ("kq_027", "MATCH (v:FlappingWingVehicle {name:'PigeonBot'}) RETURN v.propulsion_type AS x", "x", "propeller"),
]


def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    pass_count = 0
    fail_count = 0
    failures = []

    with driver.session() as sess:
        for qid, cypher, field, expected in CHECKS:
            r = sess.run(cypher).single()
            if r is None:
                print(f"  ❌ [{qid}] Cypher 无结果: {cypher[:60]}...")
                fail_count += 1
                failures.append((qid, cypher, expected, "no result"))
                continue
            actual = r[field]
            if actual == expected:
                print(f"  ✅ [{qid}] {field} = {actual}")
                pass_count += 1
            else:
                print(f"  ❌ [{qid}] {field}: expected={expected!r}, actual={actual!r}")
                fail_count += 1
                failures.append((qid, cypher, expected, actual))

    driver.close()
    print(f"\n=== 完成: {pass_count} 通过 / {fail_count} 失败 ===")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
