#!/usr/bin/env python3
"""导出整个 Neo4j 图谱到 JSONL（节点 + 关系），用于换电脑迁移。

用法（旧电脑，库正在跑）：
    export NEO4J_PASSWORD=xxx
    python3 biobridge/kg_backup/export_kg.py

产物（提交进 git 即可带到新电脑）：
    biobridge/kg_backup/nodes.jsonl
    biobridge/kg_backup/rels.jsonl

用 elementId 作为节点唯一键；关系记录首尾节点的 elementId + 标签 + 全部属性。
不依赖 APOC 插件，只用 neo4j 官方驱动。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

OUT_DIR = Path(__file__).resolve().parent
NODES_FILE = OUT_DIR / "nodes.jsonl"
RELS_FILE = OUT_DIR / "rels.jsonl"


def _serialize_props(props: dict) -> dict:
    """Neo4j 值大多是 JSON 原生类型；日期/时间等转成字符串兜底。"""
    out = {}
    for k, v in props.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        elif isinstance(v, (list, tuple)):
            out[k] = [x if isinstance(x, (str, int, float, bool)) or x is None else str(x) for x in v]
        else:
            out[k] = str(v)
    return out


def main() -> None:
    if not NEO4J_PASSWORD:
        raise SystemExit("请先设置环境变量 NEO4J_PASSWORD")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    n_nodes = n_rels = 0

    with driver.session() as sess, \
            NODES_FILE.open("w", encoding="utf-8") as nf, \
            RELS_FILE.open("w", encoding="utf-8") as rf:

        for rec in sess.run("MATCH (n) RETURN n"):
            node = rec["n"]
            nf.write(json.dumps({
                "id": node.element_id,
                "labels": sorted(node.labels),
                "props": _serialize_props(dict(node)),
            }, ensure_ascii=False) + "\n")
            n_nodes += 1

        for rec in sess.run("MATCH (a)-[r]->(b) RETURN r, a, b"):
            r = rec["r"]
            rf.write(json.dumps({
                "type": r.type,
                "start": rec["a"].element_id,
                "end": rec["b"].element_id,
                "props": _serialize_props(dict(r)),
            }, ensure_ascii=False) + "\n")
            n_rels += 1

    driver.close()
    print(f"✅ 导出完成：{n_nodes} 节点 -> {NODES_FILE.name}，{n_rels} 关系 -> {RELS_FILE.name}")


if __name__ == "__main__":
    main()
