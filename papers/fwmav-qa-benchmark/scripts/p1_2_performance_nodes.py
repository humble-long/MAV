#!/usr/bin/env python3
"""P1-2: 把 FWMAV 性能数据抽成独立 Performance 节点.

为创新点 3 (4 阶张量分解) 提供 "飞行器 × Performance × condition" 维度.

每个 Performance 节点带:
    metric           : 'weight' / 'wingspan' / 'frequency' / 'speed' / 'endurance' / 'hover'
    value            : float
    unit             : 标准单位
    condition        : 'hover' / 'cruise' / 'mixed' / 'general'
    source_field     : 来自 FWMAV 节点的哪个字段（追溯）

边: (FlappingWingVehicle)-[:HAS_PERFORMANCE]->(Performance)

注意:
    本步骤不删除 FWMAV 节点上的属性（保留以便 Cypher 直查），仅"复制"为节点形式。
"""

from __future__ import annotations
import sys
from datetime import datetime
import os
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")


# 性能字段抽取规则
# (metric_name, unit, condition, source_field, [extra_fields])
PERFORMANCE_RULES = [
    ("weight",    "g",        "general", "weight_g_std"),
    ("wingspan",  "mm",       "general", "wingspan_mm"),
    ("speed_max", "m/s",      "max",     "speed_max_m_s_std"),
    ("frequency_min", "Hz",   "general", "frequency_hz_min_std"),
    ("frequency_max", "Hz",   "general", "frequency_hz_max_std"),
    ("endurance", "s",        None,      "endurance_s_std"),  # condition 取自 endurance_condition_std
    ("hover",     "boolean",  "general", "can_hover"),
]


def main():
    print("准备引入 Performance 节点...")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    today = datetime.now().strftime("%Y-%m-%d")
    perf_created = 0
    edges_created = 0
    fwmav_count = 0

    with driver.session() as sess:
        # 先清掉之前可能存在的旧 Performance 节点（幂等）
        # 但只清掉本脚本生成的（带 generated_by='P1-2'）
        sess.run(
            """
            MATCH (p:Performance {generated_by: 'P1-2'})
            DETACH DELETE p
            """
        )
        print("  清理旧 Performance 节点完成")

        # 取所有 FWMAV
        res = sess.run(
            "MATCH (n:FlappingWingVehicle) RETURN n.name AS name, properties(n) AS p"
        )
        items = [(r["name"], r["p"]) for r in res]
        fwmav_count = len(items)

        for name, props in items:
            n_perf_for_this = 0
            for metric, unit, cond, src in PERFORMANCE_RULES:
                value = props.get(src)
                if value is None or value == "":
                    continue

                # endurance 的 condition 单独处理
                if metric == "endurance":
                    cond = props.get("endurance_condition_std", "mixed")

                # 转 float; hover 例外（保 bool）
                if metric == "hover":
                    val_to_store = bool(value)
                else:
                    try:
                        val_to_store = float(value)
                    except (TypeError, ValueError):
                        # 区间字符串等异常，跳过
                        continue

                # 创建 Performance 节点 + HAS_PERFORMANCE 边
                sess.run(
                    """
                    MATCH (v:FlappingWingVehicle {name:$vname})
                    CREATE (p:Performance:KGEntity {
                        id: $pid,
                        name: $pname,
                        metric: $metric,
                        value: $value,
                        unit: $unit,
                        condition: $cond,
                        source_field: $src,
                        generated_by: 'P1-2',
                        created_at: $today
                    })
                    CREATE (v)-[:HAS_PERFORMANCE]->(p)
                    """,
                    vname=name,
                    pid=f"Performance::{name}::{metric}",
                    pname=f"{name}_{metric}",
                    metric=metric,
                    value=val_to_store,
                    unit=unit,
                    cond=cond,
                    src=src,
                    today=today,
                )
                perf_created += 1
                edges_created += 1
                n_perf_for_this += 1

            print(f"  ✅ {name}: 生成 {n_perf_for_this} 个 Performance 节点")

    driver.close()

    print(f"\n=== 完成 ===")
    print(f"  Performance 节点: {perf_created} 个")
    print(f"  HAS_PERFORMANCE 边: {edges_created} 条")
    print(f"  覆盖 FWMAV: {fwmav_count} 个")


if __name__ == "__main__":
    main()
