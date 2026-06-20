"""B1 Baseline: 纯 LLM 直答（无任何工具/检索）.

输入: FWMAV-QA jsonl item
输出: LLM 给出的答案文本

只用 LLMClient 不带 tools 调用，最简单的 baseline。

使用方式:
    python3 biobridge/experiments/baseline_b1_pure_llm.py [--n 50] [--out path]
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import random
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from biobridge.agent.llm_client import LLMClient


B1_SYSTEM_PROMPT = """你是仿生扑翼飞行器（FWMAV）领域的专家，请回答用户的问题。

要求：
- 用中文回答，严谨、具体、有数据支撑
- 涉及计算时给出具体数值
- 涉及样机时引用具体名称（如 DelFly Nimble、Festo SmartBird 等）
- 不要回避问题，直接给出你的最佳判断
- 不需要列出参考文献"""


def load_test_set(jsonl_path: Path, n: int, seed: int = 42, sample_per_cat: bool = True) -> list[dict]:
    """从 fwmav_qa_v2_final.jsonl 抽样 n 条；按类别均衡抽样."""
    items = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    random.seed(seed)
    if not sample_per_cat:
        random.shuffle(items)
        return items[:n]

    # 按 6 类均衡抽样
    by_cat = {}
    for it in items:
        c = it.get("category", "?")
        by_cat.setdefault(c, []).append(it)

    n_per_cat = max(1, n // len(by_cat))
    sampled = []
    for c, cat_items in by_cat.items():
        random.shuffle(cat_items)
        sampled.extend(cat_items[:n_per_cat])

    random.shuffle(sampled)
    return sampled[:n]


def query_pure_llm(llm: LLMClient, question: str) -> dict:
    """单题查询，返回 {answer, latency_s}."""
    start = time.time()
    messages = [
        {"role": "system", "content": B1_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    # 不带 tools
    resp = llm.chat_with_tools(messages, tools=[])
    elapsed = time.time() - start
    return {
        "answer": resp.get("content") or "",
        "latency_s": elapsed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50, help="样本数")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--data",
        default=str(ROOT / "papers" / "fwmav-qa-benchmark" / "data" / "fwmav_qa_v2_final.jsonl"),
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "papers" / "experiment-results" / "b1_pure_llm_predictions.jsonl"),
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  B1 Baseline: 纯 LLM 直答")
    print("=" * 70)

    print(f"\n  Loading test set from {args.data} ...")
    test_set = load_test_set(Path(args.data), n=args.n, seed=args.seed)
    print(f"  Sampled {len(test_set)} questions")
    by_cat = {}
    for it in test_set:
        c = it.get("category", "?")
        by_cat[c] = by_cat.get(c, 0) + 1
    print(f"  Distribution: {dict(sorted(by_cat.items()))}")

    print(f"\n  Initializing LLM client ...")
    llm = LLMClient(mode="auto")
    print(f"  Mode: {llm.mode}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n  Running B1 on {len(test_set)} questions ...\n")
    results = []
    total_latency = 0.0
    for i, item in enumerate(test_set, 1):
        try:
            r = query_pure_llm(llm, item["question"])
            total_latency += r["latency_s"]
            results.append({
                "id": item["id"],
                "category": item.get("category"),
                "difficulty": item.get("difficulty"),
                "question": item["question"],
                "gold_answer": item.get("gold_answer", ""),
                "gold_entities": item.get("gold_entities", []),
                "pred_answer": r["answer"],
                "latency_s": r["latency_s"],
            })
            preview = r["answer"][:60].replace("\n", " ")
            print(f"  [{i:3}/{len(test_set)}] {item['id']:14s} {item.get('category')} "
                  f"d={item.get('difficulty')} t={r['latency_s']:5.2f}s  {preview}...")
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
    print(f"  Total latency: {total_latency:.1f}s   Avg: {total_latency/len(test_set):.2f}s/题")

    n_empty = sum(1 for r in results if not r.get("pred_answer"))
    print(f"  Empty answers: {n_empty}/{len(test_set)}")


if __name__ == "__main__":
    main()
