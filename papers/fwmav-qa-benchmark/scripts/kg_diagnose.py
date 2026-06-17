#!/usr/bin/env python3
"""KG 数据完整性诊断脚本.

扫描 Neo4j 中的 FWMAV 知识图谱，输出每个标签下节点的属性缺失情况、
关系挂载情况、属性命名一致性问题，作为补全工作的依据。

依赖:
    pip install neo4j

用法:
    python kg_diagnose.py --output ../papers/kg-diagnostics/diagnose-report.md
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: 请先安装 neo4j: pip install neo4j", file=sys.stderr)
    sys.exit(2)


URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")


# 每类节点期待具备的"关键属性"（用于完整性评分）
KEY_PROPS = {
    "FlappingWingVehicle": [
        "name", "wingspan_mm", "frequency_hz",
        # 重量字段三选一即可
        "weight_total_g|weight_empty_g|weight_takeoff_g",
        "endurance_min|endurance_sec|endurance_hover_min",
        "speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s",
        "can_hover", "description",
    ],
    "Organism": [
        # 当前几乎全部缺失，列出"应该补"的
        "name", "scientific_name",
        "body_mass_g_min", "body_mass_g_max",
        "wingspan_cm_min", "wingspan_cm_max",
        "flap_freq_hz_min", "flap_freq_hz_max",
        "can_hover", "reynolds_min", "reynolds_max",
        "strouhal_min", "strouhal_max",
    ],
    "DriveMechanism": ["name", "category", "description"],
    "Application": ["name", "category"],
    "Organization": ["name", "country", "type"],
    "Reference": ["title", "doi", "year", "authors"],
    "Equipment": ["name", "category"],
}

# 期待每个 FWMAV 节点应连出的关系（粗略检查）
EXPECTED_FWMAV_RELATIONS = [
    "MIMICS",
    "DEVELOPED_BY",
    "HAS_DRIVE_MECHANISM",
    "SUITABLE_FOR",
    "HAS_REFERENCE",
]


def has_any(props: dict, key_spec: str) -> bool:
    """处理 'a|b|c' 形式的"任一存在即可"检查."""
    for key in key_spec.split("|"):
        v = props.get(key)
        if v is not None and v != "":
            return True
    return False


def fmt_missing_keys(props: dict, key_specs: list[str]) -> list[str]:
    return [k for k in key_specs if not has_any(props, k)]


def diagnose(driver) -> dict:
    """跑全部诊断查询，返回结果字典."""
    report = {}

    with driver.session() as sess:
        # 1. 节点统计
        result = sess.run(
            "MATCH (n) WITH labels(n) AS lbl, count(*) AS c RETURN lbl, c ORDER BY c DESC"
        )
        node_counts = [
            {"labels": r["lbl"], "count": r["c"]} for r in result
        ]
        report["node_counts"] = node_counts

        # 2. 各标签下节点的关键属性缺失情况
        per_label_missing = {}
        for label, key_specs in KEY_PROPS.items():
            res = sess.run(
                f"MATCH (n:{label}) RETURN n.name AS name, properties(n) AS props"
            )
            label_data = []
            for r in res:
                missing = fmt_missing_keys(r["props"] or {}, key_specs)
                label_data.append({
                    "name": r["name"] or "<unnamed>",
                    "missing": missing,
                    "completeness": 1 - len(missing) / len(key_specs),
                })
            per_label_missing[label] = label_data
        report["per_label_missing"] = per_label_missing

        # 3. 属性命名一致性 - FWMAV 节点的"重量"字段使用情况
        weight_keys = ["weight_total_g", "weight_empty_g", "weight_takeoff_g"]
        weight_usage = {}
        for k in weight_keys:
            res = sess.run(
                f"MATCH (n:FlappingWingVehicle) WHERE n.{k} IS NOT NULL RETURN count(n) AS c"
            )
            weight_usage[k] = res.single()["c"]
        report["weight_naming_inconsistency"] = weight_usage

        # 4. endurance 字段使用情况
        endurance_keys = ["endurance_min", "endurance_sec", "endurance_hover_min"]
        endurance_usage = {}
        for k in endurance_keys:
            res = sess.run(
                f"MATCH (n:FlappingWingVehicle) WHERE n.{k} IS NOT NULL RETURN count(n) AS c"
            )
            endurance_usage[k] = res.single()["c"]
        report["endurance_naming_inconsistency"] = endurance_usage

        # 5. speed 字段使用情况
        speed_keys = ["speed_max_m_s", "speed_max_km_h", "speed_m_s",
                      "speed_forward_m_s", "speed_side_m_s", "flight_speed_m_s",
                      "climb_speed_m_s"]
        speed_usage = {}
        for k in speed_keys:
            res = sess.run(
                f"MATCH (n:FlappingWingVehicle) WHERE n.{k} IS NOT NULL RETURN count(n) AS c"
            )
            speed_usage[k] = res.single()["c"]
        report["speed_naming_inconsistency"] = speed_usage

        # 6. frequency 数据类型一致性
        res = sess.run(
            "MATCH (n:FlappingWingVehicle) WHERE n.frequency_hz IS NOT NULL "
            "RETURN n.name AS name, n.frequency_hz AS f, "
            "       toString(n.frequency_hz) AS f_str"
        )
        freq_str = []
        freq_num = []
        for r in res:
            f = r["f"]
            if isinstance(f, str):
                freq_str.append({"name": r["name"], "value": f})
            else:
                freq_num.append({"name": r["name"], "value": f})
        report["frequency_type_inconsistency"] = {
            "as_string_count": len(freq_str),
            "as_number_count": len(freq_num),
            "as_string_examples": freq_str[:5],
        }

        # 7. FWMAV 缺关系情况
        res = sess.run(
            """
            MATCH (n:FlappingWingVehicle)
            OPTIONAL MATCH (n)-[r:MIMICS]->()
            WITH n, count(r) AS mimics
            OPTIONAL MATCH (n)-[r:DEVELOPED_BY]->()
            WITH n, mimics, count(r) AS dev
            OPTIONAL MATCH (n)-[r:HAS_DRIVE_MECHANISM]->()
            WITH n, mimics, dev, count(r) AS drv
            OPTIONAL MATCH (n)-[r:SUITABLE_FOR]->()
            WITH n, mimics, dev, drv, count(r) AS app
            OPTIONAL MATCH (n)-[r:HAS_REFERENCE]->()
            RETURN n.name AS name, mimics, dev, drv, app, count(r) AS ref
            ORDER BY name
            """
        )
        fwmav_rels = []
        for r in res:
            fwmav_rels.append({
                "name": r["name"],
                "MIMICS": r["mimics"],
                "DEVELOPED_BY": r["dev"],
                "HAS_DRIVE_MECHANISM": r["drv"],
                "SUITABLE_FOR": r["app"],
                "HAS_REFERENCE": r["ref"],
            })
        report["fwmav_relations"] = fwmav_rels

        # 8. MIMICS 关系上是否带 type / score
        res = sess.run(
            "MATCH ()-[r:MIMICS]->() RETURN keys(r) AS keys LIMIT 5"
        )
        mimics_keys = [r["keys"] for r in res]
        report["mimics_relation_props"] = mimics_keys

        # 9. 关系总数
        res = sess.run(
            "MATCH ()-[r]->() RETURN type(r) AS rt, count(*) AS c ORDER BY c DESC"
        )
        rel_counts = [{"type": r["rt"], "count": r["c"]} for r in res]
        report["rel_counts"] = rel_counts

    return report


def render_markdown(report: dict) -> str:
    md = []
    md.append(f"# FWMAV KG 数据完整性诊断报告\n")
    md.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"> Neo4j: `{URI}`\n")
    md.append("---\n")

    # 1. 节点统计
    md.append("## 1. 节点规模\n")
    md.append("| 标签 | 数量 |")
    md.append("|---|---|")
    for nc in report["node_counts"]:
        labels = "+".join(nc["labels"])
        md.append(f"| {labels} | {nc['count']} |")
    md.append("")

    # 2. 关系统计
    md.append("## 2. 关系规模\n")
    md.append("| 关系类型 | 数量 |")
    md.append("|---|---|")
    for rc in report["rel_counts"]:
        md.append(f"| {rc['type']} | {rc['count']} |")
    md.append("")

    # 3. 属性命名一致性
    md.append("## 3. 属性命名一致性问题（重灾区）\n")
    md.append("### 3.1 重量属性 — 三种命名共存")
    md.append("| 字段 | 使用机型数 |")
    md.append("|---|---|")
    for k, v in report["weight_naming_inconsistency"].items():
        md.append(f"| `{k}` | {v} |")
    md.append("\n**建议**: 统一为 `weight_takeoff_g`（缺失时用 empty + 估算 payload 推算）。\n")

    md.append("### 3.2 续航属性 — 三种单位共存")
    md.append("| 字段 | 使用机型数 |")
    md.append("|---|---|")
    for k, v in report["endurance_naming_inconsistency"].items():
        md.append(f"| `{k}` | {v} |")
    md.append("\n**建议**: 统一为 `endurance_s`（秒）+ `endurance_condition` ∈ {hover, cruise, mixed}。\n")

    md.append("### 3.3 速度属性 — 多种命名共存")
    md.append("| 字段 | 使用机型数 |")
    md.append("|---|---|")
    for k, v in report["speed_naming_inconsistency"].items():
        if v > 0:
            md.append(f"| `{k}` | {v} |")
    md.append("\n**建议**: 统一为 `speed_max_m_s` + `speed_cruise_m_s`。\n")

    md.append("### 3.4 扑频属性 — 数字 vs 字符串混用")
    f_data = report["frequency_type_inconsistency"]
    md.append(f"- 作为 **数字** 存储: {f_data['as_number_count']} 条")
    md.append(f"- 作为 **字符串** 存储: {f_data['as_string_count']} 条（如 \"15-20\"）")
    md.append("- 字符串示例:")
    for ex in f_data["as_string_examples"]:
        md.append(f"    - {ex['name']}: \"{ex['value']}\"")
    md.append("\n**建议**: 把字符串区间拆成 `frequency_hz_min` + `frequency_hz_max`，单值赋 min=max。\n")

    # 4. 各标签下属性完整度
    md.append("## 4. 各标签下属性完整度\n")
    for label, items in report["per_label_missing"].items():
        if not items:
            continue
        avg = sum(it["completeness"] for it in items) / len(items)
        md.append(f"### {label} (共 {len(items)} 个节点，平均完整度 {avg*100:.1f}%)\n")
        md.append("| 节点 | 完整度 | 缺失字段 |")
        md.append("|---|---|---|")
        # 按完整度从低到高排序，先看缺得最严重的
        items_sorted = sorted(items, key=lambda x: x["completeness"])
        for it in items_sorted:
            missing_str = ", ".join(f"`{m}`" for m in it["missing"]) or "—"
            md.append(f"| {it['name']} | {it['completeness']*100:.0f}% | {missing_str} |")
        md.append("")

    # 5. FWMAV 关系挂载情况
    md.append("## 5. FWMAV 节点关系挂载情况\n")
    rels = report["fwmav_relations"]
    md.append("| 飞行器 | MIMICS | DEVELOPED_BY | HAS_DRIVE_MECHANISM | SUITABLE_FOR | HAS_REFERENCE |")
    md.append("|---|---|---|---|---|---|")
    for r in rels:
        cells = []
        for col in ["MIMICS", "DEVELOPED_BY", "HAS_DRIVE_MECHANISM", "SUITABLE_FOR", "HAS_REFERENCE"]:
            val = r[col]
            cell = "✅" if val > 0 else "❌"
            cells.append(f"{cell} ({val})")
        md.append(f"| {r['name']} | {' | '.join(cells)} |")
    md.append("")

    # 6. MIMICS 关系是否细分
    md.append("## 6. MIMICS 关系是否细分\n")
    mk = report["mimics_relation_props"]
    if not mk or all(len(k) == 0 for k in mk):
        md.append("**当前 MIMICS 关系上没有任何属性**——无 type、无 score。")
        md.append("**建议**：升级为带 `similarity_type` (aero/kinematics/morphology/scale) + `similarity_score` 的关系。\n")
    else:
        md.append(f"已有属性: {mk}")
    md.append("")

    # 7. 总体诊断结论
    md.append("## 7. 总体诊断结论\n")
    fwmav_data = report["per_label_missing"].get("FlappingWingVehicle", [])
    fwmav_avg = sum(it["completeness"] for it in fwmav_data) / max(len(fwmav_data), 1)
    organism_data = report["per_label_missing"].get("Organism", [])
    organism_avg = sum(it["completeness"] for it in organism_data) / max(len(organism_data), 1)

    md.append(f"- **FlappingWingVehicle 平均完整度**: {fwmav_avg*100:.1f}%")
    md.append(f"- **Organism 平均完整度**: {organism_avg*100:.1f}%")
    md.append("")
    md.append("**结论**:")
    if organism_avg < 0.3:
        md.append("- 🔴 Organism 节点严重缺失属性，无法支撑创新点 1 的双层本体——**必须先补全生物层数据**。")
    if fwmav_avg < 0.7:
        md.append("- ⚠️ FWMAV 完整度低于 70%，影响创新点 2 工具调用与创新点 3 张量分解。")
    md.append("- ⚠️ 属性命名混乱，标注题目前必须先标准化。")
    md.append("")
    md.append("**下一步建议**: 按 P0 → P1 → P2 顺序补全（详见论文 papers/02-FWMAV-QA-Benchmark-标注规范.md）。")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", "-o",
        default="../papers/kg-diagnostics/diagnose-report.md",
        help="输出 markdown 文件路径（相对脚本所在目录）",
    )
    parser.add_argument("--json", help="同时输出原始 JSON 结果")
    args = parser.parse_args()

    print(f"连接 Neo4j: {URI}")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    try:
        print("跑诊断查询...")
        report = diagnose(driver)
    finally:
        driver.close()

    md = render_markdown(report)
    out_path = (Path(__file__).parent / args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"\n✅ 报告已写入: {out_path}")

    if args.json:
        import json
        json_path = Path(args.json).resolve()
        json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"✅ JSON 已写入: {json_path}")


if __name__ == "__main__":
    main()
