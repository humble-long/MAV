"""BioBridge-GraphRAG 系统评测脚本.

使用 react_loop 在与 B1 baseline 相同的样本集上跑，得到工具增强 + KG 检索 + 张量分解
协同的答案，便于与 baseline 对比。

使用方式:
    python3 biobridge/experiments/run_biobridge.py [--n 50] [--seed 42]
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
from biobridge.agent.react_loop import react_loop


def load_test_set(jsonl_path: Path, n: int, seed: int = 42, sample_per_cat: bool = True) -> list[dict]:
    """与 B1 一致的抽样函数（确保 testset 完全相同）."""
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--data",
        default=str(ROOT / "papers" / "fwmav-qa-benchmark" / "data" / "fwmav_qa_v2_final.jsonl"),
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "papers" / "experiment-results" / "biobridge_predictions.jsonl"),
    )
    parser.add_argument("--max_iter", type=int, default=6)
    args = parser.parse_args()

    print("=" * 70)
    print("  BioBridge-GraphRAG 系统评测")
    print("=" * 70)

    test_set = load_test_set(Path(args.data), n=args.n, seed=args.seed)
    print(f"\n  Sampled {len(test_set)} questions (seed={args.seed})")
    by_cat = {}
    for it in test_set:
        c = it.get("category", "?")
        by_cat[c] = by_cat.get(c, 0) + 1
    print(f"  Distribution: {dict(sorted(by_cat.items()))}")

    print(f"\n  Initializing LLM + ReAct ...")
    llm = LLMClient(mode="auto")
    print(f"  Mode: {llm.mode}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n  Running BioBridge-GraphRAG on {len(test_set)} questions ...\n")
    results = []
    total_lat = 0.0
    total_tools = 0
    for i, item in enumerate(test_set, 1):
        try:
            t0 = time.time()
            result = react_loop(item["question"], llm=llm,
                                max_iterations=args.max_iter, verbose=False)
            elapsed = time.time() - t0
            total_lat += elapsed
            n_tools = len(result.get("tools_called", []))
            total_tools += n_tools
            results.append({
                "id": item["id"],
                "category": item.get("category"),
                "difficulty": item.get("difficulty"),
                "question": item["question"],
                "gold_answer": item.get("gold_answer", ""),
                "gold_entities": item.get("gold_entities", []),
                "pred_answer": result.get("final_answer", "") or "",
                "iterations": result.get("iterations", 0),
                "tools_called": result.get("tools_called", []),
                "n_tools": n_tools,
                "latency_s": elapsed,
            })
            preview = (result.get("final_answer") or "")[:60].replace("\n", " ")
            print(f"  [{i:3}/{len(test_set)}] {item['id']:14s} {item.get('category')} "
                  f"d={item.get('difficulty')} D={result.get('iterations', 0)} "
                  f"tools={n_tools:2} t={elapsed:5.1f}s  {preview}...")
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
                "iterations": 0,
                "tools_called": [],
                "n_tools": 0,
                "latency_s": 0.0,
            })

    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n  ✓ saved: {out_path}")
    print(f"  Total latency: {total_lat:.1f}s   Avg: {total_lat/len(test_set):.2f}s/题")
    print(f"  Total tool calls: {total_tools}   Avg: {total_tools/len(test_set):.1f}/题")

    n_empty = sum(1 for r in results if not r.get("pred_answer"))
    print(f"  Empty answers: {n_empty}/{len(test_set)}")


if __name__ == "__main__":
    main()
