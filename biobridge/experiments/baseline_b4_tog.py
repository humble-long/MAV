"""B4 Think-on-Graph (ToG) 基线: LLM 在 KG 上 beam search 探索，无物理工具.

实现 ToG (Sun et al., ICLR 2024) 的核心逻辑：
1. 从问题锚定起始实体
2. 每步 LLM 选择候选关系（beam width k）
3. 沿关系遍历到邻居节点
4. LLM 对候选路径打分，保留 top-k
5. 重复到达最大深度或 LLM 判断可回答
6. 综合所有探索路径生成答案

关键区别 vs Mavent: 不调用物理工具 (hassanalian_weight / shyy_scaling_law 等)，
不调用张量分解粗筛 (tensor_recall)。

使用方式:
    python3 biobridge/experiments/baseline_b4_tog.py [--n 415] [--seed 42]
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

TOG_SYSTEM_PROMPT = """你是仿生扑翼飞行器（FWMAV）领域的知识图谱探索专家。
你可以通过关系路径在知识图谱上导航，逐步收集证据来回答问题。

探索规则：
1. 每一步，先思考当前需要什么信息
2. 然后选择一个关系方向来探索
3. 根据探索结果决定下一步

注意：你只能做知识图谱查询，不能使用物理计算工具。
需要用物理公式验证时，请用 KG 中已有的实测参数代替。"""


def _get_driver():
    from neo4j import GraphDatabase
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd = os.environ.get("NEO4J_PASSWORD", "")
    return GraphDatabase.driver(uri, auth=(user, pwd))


def get_relations(entity_name: str) -> list[dict]:
    """获取从某个实体出发的所有可能关系类型和数量."""
    driver = _get_driver()
    with driver.session() as s:
        # Try matching by fuzzy name
        query = """
        MATCH (n)-[r]->(m)
        WHERE n.name CONTAINS $name
        RETURN type(r) AS rel_type, count(m) AS cnt
        UNION
        MATCH (n)-[r]->(m)
        WHERE m.name CONTAINS $name
        RETURN '<-' + type(r) AS rel_type, count(n) AS cnt
        """
        res = s.run(query, name=entity_name)
        rels = []
        for rec in res:
            rels.append({"type": rec["rel_type"], "count": rec["cnt"]})
    driver.close()
    return rels


def traverse(entity_name: str, rel_type: str, limit: int = 10) -> list[dict]:
    """沿指定关系遍历，返回邻居节点."""
    driver = _get_driver()
    # Strip direction prefix
    if rel_type.startswith("<-"):
        rel = rel_type[2:]
        query = """
        MATCH (m)-[r]->(n)
        WHERE n.name CONTAINS $name AND type(r) = $rel
        RETURN m.name AS name, labels(m) AS labels, properties(m) AS props
        LIMIT $limit
        """
    else:
        rel = rel_type
        query = """
        MATCH (n)-[r]->(m)
        WHERE n.name CONTAINS $name AND type(r) = $rel
        RETURN m.name AS name, labels(m) AS labels, properties(m) AS props
        LIMIT $limit
        """
    with driver.session() as s:
        res = s.run(query, name=entity_name, rel=rel, limit=limit)
        nodes = []
        for rec in res:
            nodes.append({
                "name": rec["name"],
                "labels": list(rec["labels"]),
                "props": {k: v for k, v in rec["props"].items()
                         if v is not None and k != "id"},
            })
    driver.close()
    return nodes


def anchor_entities(question: str, llm: LLMClient) -> list[str]:
    """用 LLM 从问题中识别应该在 KG 中查询的起始实体."""
    prompt = (
        "从以下问题中抽取所有应该在知识图谱中查询的实体名称（样机名、生物名、机构名等）。"
        "只输出 JSON 数组，不要输出其他文字。\n\n"
        f"问题：{question}\n\n"
        '输出示例：["DelFly Nimble", "蜂鸟"]'
    )
    messages = [{"role": "user", "content": prompt}]
    resp = llm.chat_with_tools(messages, tools=[])
    raw = resp.get("content", "[]") or "[]"
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:]) if len(lines) > 1 else raw
        if raw.endswith("```"):
            raw = raw[:raw.rfind("```")].strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


def plan_relations(
    question: str,
    current_entity: str,
    explored_summary: str,
    available_relations: list[dict],
    llm: LLMClient,
) -> list[str]:
    """LLM 选择下一步探索哪些关系（ToG 的 relation planning step）."""
    rel_list = "\n".join(
        f"  {r['type']} (有 {r['count']} 个相关节点)"
        for r in available_relations
    )
    prompt = (
        f"【问题】{question}\n\n"
        f"当前焦点实体：{current_entity}\n\n"
        f"已探索的信息：\n{explored_summary if explored_summary else '（尚未开始探索）'}\n\n"
        f"可用的关系类型：\n{rel_list}\n\n"
        "请从可用关系中选择 1-3 个最有帮助的关系类型来探索。"
        "只输出 JSON 数组，不要输出其他文字。\n"
        '示例：["MIMICS", "HAS_PERFORMANCE"]'
    )
    messages = [{"role": "user", "content": prompt}]
    resp = llm.chat_with_tools(messages, tools=[])
    raw = resp.get("content", "[]") or "[]"
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:]) if len(lines) > 1 else raw
        if raw.endswith("```"):
            raw = raw[:raw.rfind("```")].strip()
    try:
        return [r for r in json.loads(raw)
                if any(a['type'] == r for a in available_relations)]
    except (json.JSONDecodeError, TypeError):
        return []


def is_answerable(
    question: str,
    explored_info: str,
    llm: LLMClient,
) -> bool:
    """LLM 判断已收集的信息是否足够回答问题."""
    prompt = (
        f"【问题】{question}\n\n"
        f"已从知识图谱中收集到的信息：\n{explored_info}\n\n"
        "你认为这些信息足够回答上面的问题了吗？回答 YES 或 NO。"
    )
    messages = [{"role": "user", "content": prompt}]
    resp = llm.chat_with_tools(messages, tools=[])
    ans = (resp.get("content") or "").strip().upper()
    return "YES" in ans


def synthesize_answer(
    question: str,
    explored_info: str,
    llm: LLMClient,
) -> str:
    """综合所有探索信息生成最终答案."""
    prompt = (
        f"【问题】{question}\n\n"
        f"从知识图谱探索收集到的信息：\n{explored_info}\n\n"
        "请综合以上信息，给出完整、具体、有数据支撑的答案。"
        "必须引用 KG 中获取的具体数值。"
        "如果信息不完整，诚实说明。"
    )
    messages = [
        {"role": "system", "content": TOG_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    resp = llm.chat_with_tools(messages, tools=[])
    return resp.get("content") or ""


def tog_search(
    question: str,
    llm: LLMClient,
    beam_width: int = 3,
    max_depth: int = 4,
    verbose: bool = False,
) -> dict:
    """ToG beam search 探索。

    Returns dict with answer, explored_paths, steps.
    """
    # Step 1: Anchor entities
    entities = anchor_entities(question, llm)
    if verbose:
        print(f"    锚定实体: {entities}")

    if not entities:
        answer = synthesize_answer(question, "（KG 中未找到相关实体起始点）", llm)
        return {"answer": answer, "paths": [], "steps": 0}

    all_explored = []
    steps = 0

    # Step 2: For each anchor entity, explore
    for entity in entities[:beam_width]:  # limit anchors
        explored = [f"起始实体: {entity}"]

        for depth in range(max_depth):
            # Get available relations
            rels = get_relations(entity)
            if not rels:
                if verbose:
                    print(f"    [{entity}] 无可探索关系，停止")
                break

            # LLM plans which relations to explore
            explored_summary = "\n".join(explored)
            chosen_rels = plan_relations(question, entity, explored_summary, rels, llm)
            steps += 1

            if not chosen_rels:
                if verbose:
                    print(f"    [{entity}] LLM 未选择任何关系")
                break

            # Traverse chosen relations
            new_entities = []
            for rel_type in chosen_rels[:2]:  # limit to 2 relations per step
                nodes = traverse(entity, rel_type, limit=20)
                for node in nodes:
                    # Only keep essential fields to avoid truncation cutting off value
                    essential = {k: node['props'][k] for k in ["metric", "value", "unit", "condition"]
                                 if k in node['props']}
                    explored.append(
                        f"  --[{rel_type}]--> {node['name']} "
                        f"({json.dumps(essential, ensure_ascii=False)})"
                    )
                    new_entities.append(node["name"])

            if verbose:
                print(f"    [{entity}] depth={depth}: {len(chosen_rels)} rels → {len(new_entities)} new entities")

            # Check if answerable
            if is_answerable(question, "\n".join(explored), llm):
                if verbose:
                    print(f"    [{entity}] LLM 判断信息足够，停止探索")
                break

            # Switch focus to first new entity for next depth
            if new_entities:
                entity = new_entities[0]

        all_explored.append("\n".join(explored))

    # Step 3: Synthesize
    answer = synthesize_answer(question, "\n\n".join(all_explored), llm)

    return {
        "answer": answer,
        "explored_summary": all_explored,
        "steps": steps,
    }


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
                        default=str(ROOT / "papers" / "experiment-results" / "b4_tog_predictions.jsonl"))
    parser.add_argument("--beam_width", type=int, default=3)
    parser.add_argument("--max_depth", type=int, default=4)
    args = parser.parse_args()

    neo4j_pwd = os.environ.get("NEO4J_PASSWORD", "")
    if not neo4j_pwd:
        print("ERROR: NEO4J_PASSWORD not set")
        sys.exit(1)

    print("=" * 70)
    print(f"  B4 ToG Baseline: LLM-on-Graph beam search (k={args.beam_width}, D={args.max_depth})")
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
    total_steps = 0
    for i, item in enumerate(test_set, 1):
        try:
            t0 = time.time()
            tog_result = tog_search(
                item["question"],
                llm=llm,
                beam_width=args.beam_width,
                max_depth=args.max_depth,
                verbose=False,
            )
            elapsed = time.time() - t0
            total_lat += elapsed
            total_steps += tog_result.get("steps", 0)

            results.append({
                "id": item["id"],
                "category": item.get("category"),
                "difficulty": item.get("difficulty"),
                "question": item["question"],
                "gold_answer": item.get("gold_answer", ""),
                "gold_entities": item.get("gold_entities", []),
                "pred_answer": tog_result["answer"],
                "tog_steps": tog_result["steps"],
                "latency_s": elapsed,
            })
            preview = tog_result["answer"][:60].replace("\n", " ")
            print(f"  [{i:4}/{len(test_set)}] {item['id']:16s} {item.get('category')} "
                  f"steps={tog_result['steps']:2} t={elapsed:5.1f}s  {preview}...")
        except Exception as e:
            import traceback
            print(f"  [{i}/{len(test_set)}] ERROR on {item['id']}: {type(e).__name__}: {e}")
            traceback.print_exc()
            results.append({
                "id": item["id"],
                "category": item.get("category"),
                "difficulty": item.get("difficulty"),
                "question": item["question"],
                "gold_answer": item.get("gold_answer", ""),
                "gold_entities": item.get("gold_entities", []),
                "pred_answer": "",
                "error": f"{type(e).__name__}: {e}",
                "tog_steps": 0,
                "latency_s": 0.0,
            })

    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    avg_lat = total_lat / len(test_set) if test_set else 0
    avg_steps = total_steps / len(test_set) if test_set else 0
    print(f"\n  ✓ saved: {out_path}")
    print(f"  Total latency: {total_lat:.1f}s  Avg: {avg_lat:.2f}s/题  Avg steps: {avg_steps:.1f}")


if __name__ == "__main__":
    main()
