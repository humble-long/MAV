"""B3 KG-RAG 基线: 从问题提取实体 → KG 查 1-2 跳邻居 → 转文本喂给 LLM.

单轮检索，LLM 被动接收 KG 片段。与 Mavent（多轮 ReAct + 工具）和 B2（向量检索文档）对比。

使用方式:
    python3 biobridge/experiments/baseline_b3_kg_rag.py [--n 415] [--seed 42]
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from biobridge.agent.llm_client import LLMClient

B3_SYSTEM_PROMPT = """你是仿生扑翼飞行器（FWMAV）领域的专家，请根据提供的知识图谱检索结果回答用户问题。

要求：
- 用中文回答，严谨、具体
- 必须引用知识图谱数据中的具体数值
- 涉及样机时引用具体名称
- 如果知识图谱数据中没有相关信息，请诚实说明"""


def extract_entities_from_question(question: str, llm: LLMClient = None) -> list[str]:
    """用 LLM 从问题中抽取实体名，用于 KG 查询锚点."""
    prompt = (
        "请从以下问题中抽取出所有仿生扑翼飞行器（FWMAV）相关的实体名称"
        "（样机名、生物名、机构名、组件名、概念术语等）。"
        "只输出 JSON 数组，不要输出其他文字。\n\n"
        f"问题：{question}\n\n"
        '输出格式：["实体1", "实体2", ...]'
    )

    messages = [
        {"role": "user", "content": prompt},
    ]
    resp = llm.chat_with_tools(messages, tools=[])
    raw = resp.get("content", "[]") or "[]"

    try:
        # 去掉可能的 markdown 包裹
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:]) if len(lines) > 1 else raw
            if raw.endswith("```"):
                raw = raw[:raw.rfind("```")].strip()
        entities = json.loads(raw)
        return entities if isinstance(entities, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def kg_retrieve(
    entities: list[str],
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    max_hops: int = 2,
    max_nodes: int = 30,
):
    """在 KG 中检索 1-2 跳邻居，返回子图文本。

    Returns:
        str of formatted KG data
    """
    from neo4j import GraphDatabase

    if not entities:
        return "（未从问题中识别出实体，无法查询 KG）"

    drv = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    all_chunks = []

    with drv.session() as s:
        for entity in entities:
            # 尝试按名称匹配任意类型的节点
            query_1hop = """
            MATCH (n)-[r]-(m)
            WHERE n.name CONTAINS $name OR m.name CONTAINS $name
            RETURN DISTINCT n, r, m
            LIMIT $limit
            """
            res = s.run(query_1hop, name=entity, limit=max_nodes)
            if res.peek() is None:
                continue

            lines = [f"=== KG 检索: \"{entity}\" 的关联信息 ==="]

            # 分组：按源节点
            src_nodes = {}
            for rec in res:
                n = dict(rec["n"])
                r_type = type(rec["r"]).__name__
                m = dict(rec["m"])
                n_key = n.get("name", str(id(n)))
                src_nodes.setdefault(n_key, {"node": n, "rels": []})
                src_nodes[n_key]["rels"].append((r_type, m))

            for src_name, data in src_nodes.items():
                n = data["node"]
                n_labels = [l for l in n.get("labels", [])] if "labels" in n else []
                lines.append(f"\n[{', '.join(n_labels) if n_labels else 'Node'}] {n.get('name', '')}")
                # Print key attributes
                for k, v in n.items():
                    if k not in ("name", "labels", "id") and v is not None:
                        lines.append(f"    {k}: {v}")

                for r_type, m in data["rels"]:
                    m_name = m.get("name", "")
                    lines.append(f"  --[{r_type}]--> {m_name}")
                    # Key attributes of target
                    for k, v in m.items():
                        if k not in ("name", "id") and v is not None:
                            lines.append(f"      {k}: {v}")
                    if len(str(m)) > 500:
                        break

            all_chunks.append("\n".join(lines))

    drv.close()

    if not all_chunks:
        return "（KG 中未找到与问题相关的实体信息）"

    return "\n\n".join(all_chunks)


def load_test_set(jsonl_path: Path, n: int, seed: int = 42) -> list[dict]:
    items = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                it = json.loads(line)
                if it.get("category") != "A1":
                    items.append(it)
    random.seed(seed)
    if n >= len(items):
        return items
    random.shuffle(items)
    return items[:n]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=9999)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--data",
                        default=str(ROOT / "papers" / "fwmav-qa-benchmark" / "data" / "fwmav_qa_v2_final.jsonl"))
    parser.add_argument("--out",
                        default=str(ROOT / "papers" / "experiment-results" / "b3_kg_rag_predictions.jsonl"))
    args = parser.parse_args()

    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_pwd = os.environ.get("NEO4J_PASSWORD", "")
    if not neo4j_pwd:
        print("ERROR: NEO4J_PASSWORD not set")
        sys.exit(1)

    print("=" * 70)
    print("  B3 KG-RAG Baseline: Entity Extraction → KG 1-2 Hop → Text → LLM")
    print("=" * 70)

    test_set = load_test_set(Path(args.data), n=args.n, seed=args.seed)
    test_set = [it for it in test_set if it.get("category", "").startswith(("A", "B"))]
    print(f"  A 类题: {len(test_set)}")

    llm = LLMClient(mode="auto")
    print(f"  LLM mode: {llm.mode}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    total_lat = 0.0
    for i, item in enumerate(test_set, 1):
        try:
            t0 = time.time()
            question = item["question"]

            # Step 1: Extract entities from question
            entities = extract_entities_from_question(question, llm)

            # Step 2: KG retrieval
            kg_context = kg_retrieve(entities, neo4j_uri, neo4j_user, neo4j_pwd)

            # Step 3: Ask LLM with KG context
            prompt = f"【知识图谱数据】\n{kg_context}\n\n【问题】{question}\n\n请基于知识图谱数据回答。"

            messages = [
                {"role": "system", "content": B3_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            resp = llm.chat_with_tools(messages, tools=[])
            elapsed = time.time() - t0
            total_lat += elapsed

            answer = resp.get("content") or ""
            results.append({
                "id": item["id"],
                "category": item.get("category"),
                "difficulty": item.get("difficulty"),
                "question": question,
                "gold_answer": item.get("gold_answer", ""),
                "gold_entities": item.get("gold_entities", []),
                "pred_answer": answer,
                "extracted_entities": entities,
                "latency_s": elapsed,
            })
            preview = answer[:60].replace("\n", " ")
            print(f"  [{i:4}/{len(test_set)}] {item['id']:16s} {item.get('category')} "
                  f"ents={entities[:3]} t={elapsed:5.1f}s  {preview}...")
        except Exception as e:
            print(f"  [{i}/{len(test_set)}] ERROR on {item['id']}: {type(e).__name__}: {e}")
            results.append({
                "id": item["id"],
                "category": item.get("category"),
                "difficulty": item.get("difficulty"),
                "question": item["question"],
                "gold_answer": item.get("gold_answer", ""),
                "gold_entities": item.get("gold_entities", []),
                "pred_answer": "",
                "extracted_entities": [],
                "error": f"{type(e).__name__}: {e}",
                "latency_s": 0.0,
            })

    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    avg_lat = total_lat / len(test_set) if test_set else 0
    print(f"\n  ✓ saved: {out_path}")
    print(f"  Total latency: {total_lat:.1f}s  Avg: {avg_lat:.2f}s/题")


if __name__ == "__main__":
    main()
