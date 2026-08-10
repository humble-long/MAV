"""B2 VectorRAG 基线: BGE-M3 嵌入 + FAISS 向量检索.

将 KG 中的实体/属性展平为文本 chunk → BGE-M3 嵌入 → FAISS 索引。
查询时检索 Top-10 相似 chunk，注入 LLM prompt，得到答案。

使用方式:
    python3 biobridge/experiments/baseline_b2_vector_rag.py [--n 415] [--seed 42]
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

B2_SYSTEM_PROMPT = """你是仿生扑翼飞行器（FWMAV）领域的专家，请根据提供的参考资料回答用户问题。

要求：
- 用中文回答，严谨、具体
- 必须引用参考资料中的具体数值
- 涉及样机时引用具体名称
- 如果参考资料中没有相关信息，请诚实说明
- 不需要列出参考文献"""


def build_corpus_from_kg(neo4j_uri: str, neo4j_user: str, neo4j_password: str) -> list[dict]:
    """从 Neo4j KG 抽取实体和属性，展平为文本 chunks.

    每个 chunk 是一个 {id, text} dict。
    """
    from neo4j import GraphDatabase

    drv = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    chunks = []

    with drv.session() as s:
        # FWMAV 节点 → 文本 chunk
        r = s.run("""
            MATCH (v:FlappingWingVehicle)
            OPTIONAL MATCH (v)-[:HAS_PERFORMANCE]->(p:Performance)
            OPTIONAL MATCH (v)-[:MIMICS]->(o:Organism)
            OPTIONAL MATCH (v)-[:DEVELOPED_BY]->(org:Organization)
            OPTIONAL MATCH (v)-[:EQUIPPED_WITH]->(e:Equipment)
            OPTIONAL MATCH (v)-[:SUITABLE_FOR]->(a:Application)
            OPTIONAL MATCH (v)-[:HAS_DRIVE_MECHANISM]->(d:DriveMechanism)
            RETURN v,
                   collect(DISTINCT p) AS perfs,
                   collect(DISTINCT o.name) AS organisms,
                   collect(DISTINCT org.name) AS orgs,
                   collect(DISTINCT e.name) AS equipments,
                   collect(DISTINCT a.name) AS apps,
                   collect(DISTINCT d.name) AS drives
        """)

        for rec in r:
            v = dict(rec["v"])
            parts = [f"扑翼飞行器: {v.get('name', '')}"]

            for k in ["weight_g_std", "wingspan_mm", "frequency_hz", "endurance_s_std",
                       "speed_max_m_s_std", "frequency_hz_min_std"]:
                if v.get(k) is not None:
                    label = k.replace("_std", "").replace("_mm", "").replace("_g", "").replace("_s", "").replace("_m_s", "")
                    parts.append(f"  {label}: {v[k]}")

            if v.get("can_hover"):
                parts.append(f"  可悬停: 是")
            if v.get("description"):
                parts.append(f"  描述: {v['description']}")

            if rec["organisms"]:
                parts.append(f"  仿生原型: {', '.join(rec['organisms'])}")
            if rec["orgs"]:
                parts.append(f"  研制单位: {', '.join(rec['orgs'])}")
            if rec["equipments"]:
                parts.append(f"  装备组件: {', '.join(rec['equipments'][:10])}")
            if rec["apps"]:
                parts.append(f"  适用场景: {', '.join(rec['apps'])}")
            if rec["drives"]:
                parts.append(f"  驱动机构: {', '.join(rec['drives'])}")

            chunks.append({"id": v.get("name", ""), "text": "\n".join(parts)})

        # Organism 节点 → 文本 chunk
        r = s.run("""
            MATCH (o:Organism)
            OPTIONAL MATCH (v:FlappingWingVehicle)-[:MIMICS]->(o)
            RETURN o, collect(DISTINCT v.name) AS vehicles
        """)
        for rec in r:
            o = dict(rec["o"])
            parts = [f"生物原型: {o.get('name', '')}"]
            if o.get("scientific_name"):
                parts.append(f"  学名: {o['scientific_name']}")
            for k in ["body_mass_g_min", "body_mass_g_max", "wingspan_cm_min", "wingspan_cm_max",
                       "flap_freq_hz_min", "flap_freq_hz_max", "cruise_speed_m_s_min", "cruise_speed_m_s_max"]:
                if o.get(k) is not None:
                    parts.append(f"  {k}: {o[k]}")
            if o.get("can_hover"):
                parts.append(f"  可悬停: 是")
            if o.get("notes"):
                parts.append(f"  备注: {o['notes']}")
            if rec["vehicles"]:
                parts.append(f"  仿生此原型的飞行器: {', '.join(rec['vehicles'])}")
            chunks.append({"id": o.get("name", ""), "text": "\n".join(parts)})

    drv.close()
    return chunks


def build_or_load_index(chunks: list[dict], index_path: str = None) -> tuple:
    """构建 FAISS 索引（用 BGE-M3 嵌入），或从磁盘加载."""
    import numpy as np
    import faiss
    import torch
    from sentence_transformers import SentenceTransformer

    if index_path is None:
        index_path = str(ROOT / "papers" / "experiment-results" / "vector_rag_index")

    index_file = index_path + ".faiss"
    chunks_file = index_path + ".json"

    if os.path.exists(index_file) and os.path.exists(chunks_file):
        print(f"[VectorRAG] 加载已有索引: {index_file}")
        with open(chunks_file, encoding="utf-8") as f:
            chunks = json.load(f)
        index = faiss.read_index(index_file)
        return chunks, index

    # On Apple Silicon, use MPS; else CPU
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[VectorRAG] 构建 BGE-M3 嵌入（{len(chunks)} chunks, device={device}）...")
    model = SentenceTransformer("BAAI/bge-m3", device=device)
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=16)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner Product (cosine when normalized)
    index.add(embeddings.astype(np.float32))

    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    faiss.write_index(index, index_file)
    with open(chunks_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)

    print(f"[VectorRAG] 索引已保存: {index_file} ({len(chunks)} chunks, dim={dim})")
    return chunks, index


def retrieve(query: str, chunks: list[dict], index, model=None, top_k: int = 10) -> list[dict]:
    """向量检索，返回 top-k chunks。reuse model if provided."""
    import torch
    if model is None:
        from sentence_transformers import SentenceTransformer
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        model = SentenceTransformer("BAAI/bge-m3", device=device)
    q_emb = model.encode([query], normalize_embeddings=True)
    scores, indices = index.search(q_emb.astype("float32"), top_k)
    results = []
    for idx, score in zip(indices[0], scores[0]):
        if idx >= 0 and idx < len(chunks):
            results.append({"chunk": chunks[idx], "score": float(score)})
    return results


def load_test_set(jsonl_path: Path, n: int, seed: int = 42) -> list[dict]:
    """加载测试集，排除 A1."""
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
                        default=str(ROOT / "papers" / "experiment-results" / "b2_vector_rag_predictions.jsonl"))
    args = parser.parse_args()

    # Build/load index
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_pwd = os.environ.get("NEO4J_PASSWORD", "")
    if not neo4j_pwd:
        print("ERROR: NEO4J_PASSWORD not set")
        sys.exit(1)

    print("=" * 70)
    print("  B2 VectorRAG Baseline: BGE-M3 + FAISS")
    print("=" * 70)

    print("\n[1/3] 从 KG 构建文本语料...")
    chunks = build_corpus_from_kg(neo4j_uri, neo4j_user, neo4j_pwd)
    print(f"  {len(chunks)} chunks (FWMAV + Organism)")

    print("\n[2/3] 构建/加载 FAISS 索引...")
    chunks, index = build_or_load_index(chunks)
    print(f"  Index size: {index.ntotal}")

    test_set = load_test_set(Path(args.data), n=args.n, seed=args.seed)
    print(f"\n[3/3] 运行 B2 VectorRAG on {len(test_set)} questions...")

    # Filter to A class only (B class not relevant for VectorRAG)
    test_set = [it for it in test_set if it.get("category", "").startswith(("A", "B"))]
    print(f"  A 类题: {len(test_set)}")

    llm = LLMClient(mode="auto")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    total_lat = 0.0
    for i, item in enumerate(test_set, 1):
        try:
            t0 = time.time()
            question = item["question"]

            # Retrieve top-k chunks
            retrieved = retrieve(question, chunks, index, top_k=10)
            context = "\n\n---\n\n".join(
                f"[{r['chunk']['id']}]\n{r['chunk']['text']}"
                for r in retrieved
            )

            prompt = f"【参考资料】\n{context}\n\n【问题】{question}\n\n请基于参考资料回答。如果参考资料不包含相关信息，请诚实说明并动用你的专业知识。"

            messages = [
                {"role": "system", "content": B2_SYSTEM_PROMPT},
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
                "retrieved_chunks": [r["chunk"]["id"] for r in retrieved],
                "top_score": retrieved[0]["score"] if retrieved else 0,
                "latency_s": elapsed,
            })
            preview = answer[:60].replace("\n", " ")
            print(f"  [{i:4}/{len(test_set)}] {item['id']:16s} {item.get('category')} "
                  f"t={elapsed:5.1f}s  top={retrieved[0]['chunk']['id'][:20] if retrieved else 'N/A'}  {preview}...")
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
                "error": f"{type(e).__name__}: {e}",
                "latency_s": 0.0,
            })

    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n  ✓ saved: {out_path}")
    print(f"  Total latency: {total_lat:.1f}s  Avg: {total_lat/len(test_set):.2f}s/题")


if __name__ == "__main__":
    main()
