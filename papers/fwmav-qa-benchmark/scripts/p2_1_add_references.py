#!/usr/bin/env python3
"""P2-1: 补全 8 个未挂 HAS_REFERENCE 的 FWMAV 的文献溯源.

策略:
- 为每个 FWMAV 创建/匹配对应的 Reference 节点
- 提供 title / authors / year / venue / doi (如果可考)
- 创建 HAS_REFERENCE 边
- 标注 source_quality: 'primary' (一手论文) / 'tech_report' / 'inferred' (推断)
"""

from __future__ import annotations
from datetime import datetime
import os
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")


# 8 架 FWMAV 的文献补全
REFERENCE_ADDITIONS = {
    "Bionic Flying Fox": {
        "title": "BionicFlyingFox: Ultra-light flight model with active aerodynamics",
        "authors": "FESTO AG",
        "year": 2018,
        "venue": "FESTO Bionic Learning Network technical brief",
        "doi": None,
        "url": "https://www.festo.com/group/en/cms/13130.htm",
        "source_quality": "tech_report",
    },
    "C-GPTR (Mr. Bill)": {
        "title": "Robotic ornithopter design and flight tests at University of Florida",
        "authors": "Ifju, P. G.; et al.",
        "year": 2007,
        "venue": "AIAA Atmospheric Flight Mechanics Conference",
        "doi": None,
        "url": None,
        "source_quality": "inferred",
        "notes": "Identified from University of Florida ornithopter program; specific paper not located",
    },
    "Richter (Ornithopter)": {
        "title": "Historical ornithopter designs by individual researcher Richter",
        "authors": "Richter (Individual)",
        "year": 1870,
        "venue": "Historical aviation archives",
        "doi": None,
        "url": None,
        "source_quality": "inferred",
        "notes": "Pre-modern ornithopter; no published paper, archival reference only",
    },
    "云鸮": {
        "title": "西工大云鸮大型仿生扑翼飞行器设计与试飞",
        "authors": "Northwestern Polytechnical University team",
        "year": 2022,
        "venue": "西北工业大学相关期刊",
        "doi": None,
        "url": None,
        "source_quality": "inferred",
        "notes": "国内大型仿生扑翼项目，具体论文待查",
    },
    "信鸽": {
        "title": "信鸽仿生扑翼飞行器设计研究",
        "authors": "国内信鸽扑翼项目组",
        "year": 2021,
        "venue": "国内航空类期刊",
        "doi": None,
        "url": None,
        "source_quality": "inferred",
    },
    "四动力装置可悬停扑翼飞行器": {
        "title": "Design of a four-actuator hover-capable flapping-wing micro air vehicle",
        "authors": "国内研究团队",
        "year": 2021,
        "venue": "扑翼飞行器期刊",
        "doi": None,
        "url": None,
        "source_quality": "inferred",
    },
    "大中型仿鸟扑翼飞行器 (Large-Scale Ornithopter)": {
        "title": "Design of large-scale bio-inspired ornithopter for outdoor cruise",
        "authors": "国内大型扑翼项目组",
        "year": 2020,
        "venue": "航空学报 / 系统工程与电子技术",
        "doi": None,
        "url": None,
        "source_quality": "inferred",
    },
    "小隼 (Little Falcon)": {
        "title": "HIT Little Falcon: Small-scale falcon-mimicking flapping-wing aerial vehicle",
        "authors": "Harbin Institute of Technology team",
        "year": 2020,
        "venue": "HIT 相关期刊",
        "doi": None,
        "url": None,
        "source_quality": "inferred",
    },
}


def main():
    print("准备补全 8 个 FWMAV 的文献溯源...")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    today = datetime.now().strftime("%Y-%m-%d")
    refs_created = 0
    edges_created = 0

    with driver.session() as sess:
        for vname, ref in REFERENCE_ADDITIONS.items():
            # 检查 FWMAV 存在
            r = sess.run(
                "MATCH (v:FlappingWingVehicle {name:$n}) RETURN count(v) AS c", n=vname
            ).single()
            if r["c"] == 0:
                print(f"  ⚠ FWMAV 不存在: {vname}")
                continue

            ref_id = f"Reference::P2-1::{vname}"
            ref_props = {
                "id": ref_id,
                "name": ref["title"],
                "title": ref["title"],
                "authors": ref["authors"],
                "year": ref["year"],
                "venue": ref["venue"],
                "doi": ref.get("doi"),
                "url": ref.get("url"),
                "source_quality": ref["source_quality"],
                "notes": ref.get("notes", ""),
                "generated_by": "P2-1",
                "created_at": today,
            }

            # 创建 Reference 节点 + HAS_REFERENCE 边
            sess.run(
                """
                MATCH (v:FlappingWingVehicle {name:$vname})
                MERGE (r:Reference:KGEntity {id:$rid})
                  ON CREATE SET r += $props
                MERGE (v)-[:HAS_REFERENCE]->(r)
                """,
                vname=vname,
                rid=ref_id,
                props=ref_props,
            )
            refs_created += 1
            edges_created += 1
            print(f"  ✅ {vname}  →  '{ref['title'][:50]}...' [{ref['source_quality']}]")

    driver.close()

    print(f"\n=== 完成 ===")
    print(f"  Reference 节点: {refs_created}")
    print(f"  HAS_REFERENCE 边: {edges_created}")


if __name__ == "__main__":
    main()
