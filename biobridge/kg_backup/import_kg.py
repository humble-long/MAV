#!/usr/bin/env python3
"""把 export_kg.py 导出的 JSONL 重新灌进一个空的 Neo4j 库（换电脑后用）。

用法（新电脑，装好并启动 Neo4j 后）：
    export NEO4J_PASSWORD=xxx
    python3 biobridge/kg_backup/import_kg.py

行为：
    1. 读 nodes.jsonl / rels.jsonl
    2. 用导出时的旧 elementId 作为临时属性 `_import_eid` 建节点，便于关系连线
    3. 建完关系后删除 `_import_eid` 临时属性
默认要求库为空；如需覆盖已有数据，加 --wipe 先清空全库。
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

IN_DIR = Path(__file__).resolve().parent
NODES_FILE = IN_DIR / "nodes.jsonl"
RELS_FILE = IN_DIR / "rels.jsonl"


def _read_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wipe", action="store_true", help="导入前清空整个库（危险）")
    args = ap.parse_args()

    if not NEO4J_PASSWORD:
        raise SystemExit("请先设置环境变量 NEO4J_PASSWORD")
    if not NODES_FILE.exists():
        raise SystemExit(f"找不到 {NODES_FILE}，请先在旧电脑跑 export_kg.py")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as sess:
        if args.wipe:
            sess.run("MATCH (n) DETACH DELETE n")
            print("⚠ 已清空全库")

        existing = sess.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        if existing and not args.wipe:
            raise SystemExit(f"库里已有 {existing} 个节点，非空。确认后加 --wipe 重来。")

        # 唯一约束，加速 MATCH 连线
        sess.run("CREATE INDEX import_eid IF NOT EXISTS FOR (n:_Imported) ON (n._import_eid)")

        n_nodes = 0
        for node in _read_jsonl(NODES_FILE):
            labels = ":".join(["_Imported"] + node["labels"])
            props = dict(node["props"])
            props["_import_eid"] = node["id"]
            sess.run(f"CREATE (n:{labels}) SET n = $props", props=props)
            n_nodes += 1
        print(f"✅ 建了 {n_nodes} 个节点")

        n_rels = 0
        for rel in _read_jsonl(RELS_FILE):
            sess.run(
                f"""
                MATCH (a {{_import_eid:$start}}), (b {{_import_eid:$end}})
                CREATE (a)-[r:`{rel['type']}`]->(b)
                SET r = $props
                """,
                start=rel["start"], end=rel["end"], props=rel["props"],
            )
            n_rels += 1
        print(f"✅ 建了 {n_rels} 条关系")

        # 清理临时标签和属性
        sess.run("MATCH (n:_Imported) REMOVE n:_Imported REMOVE n._import_eid")
        try:
            sess.run("DROP INDEX import_eid IF EXISTS")
        except Exception:
            pass
        print("✅ 已清理临时导入标记，导入完成")

    driver.close()


if __name__ == "__main__":
    main()
