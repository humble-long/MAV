"""消融实验跑批脚本.

运行 4 个 + 1（Full）共 5 个变体，全部用相同的 50 题 sample.

输出每个变体一个 jsonl：
- ablation_full_predictions.jsonl
- ablation_no_bilayer_predictions.jsonl
- ablation_no_tools_predictions.jsonl
- ablation_no_tensor_predictions.jsonl
- ablation_no_pathreasoning_predictions.jsonl

使用方式:
    # 跑单个变体
    python3 biobridge/experiments/run_ablation.py --variant no_bilayer
    # 跑全部
    python3 biobridge/experiments/run_ablation.py --variant all
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
from biobridge.agent.react_loop_ablation import (
    react_loop_subset,
    ABLATION_VARIANTS,
)
from biobridge.tools.tool_specs import call_tool


def load_test_set(jsonl_path: Path, n: int, seed: int = 42, sample_per_cat: bool = True) -> list[dict]:
    """与 B1 完全一致的抽样函数（确保 testset 可比）."""
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


def run_tensor_only(question: str) -> dict:
    """w/o 路径推理：只用 tensor_recall + 简单文本格式化的退化变体.

    不调用 LLM，直接从 query 提取约束（粗略），喂给 tensor_recall。
    """
    import re
    args = {"top_k": 10}

    # 简单关键词提取
    if "悬停" in question:
        args["can_hover"] = True

    m = re.search(r'重量[^\d]*(\d+(?:\.\d+)?)\s*g', question)
    if m:
        args["weight_g"] = float(m.group(1))
    m = re.search(r'翼展[^\d]*?(?:不超过|≤|<=|<)?\s*(\d+)\s*(?:mm|毫米)', question)
    if m:
        args["wingspan_mm"] = float(m.group(1))
    m = re.search(r'扑频[^\d]*(\d+(?:\.\d+)?)\s*Hz', question)
    if m:
        args["frequency_hz"] = float(m.group(1))
    m = re.search(r'续航[^\d]*?(\d+(?:\.\d+)?)\s*(?:分钟|min)', question)
    if m:
        args["endurance_s"] = float(m.group(1)) * 60

    if "巡航" in question or "侦察" in question:
        args["mission"] = "task"
    elif "机动" in question or "特技" in question:
        args["mission"] = "maneuver"
    elif "长航时" in question or "悬停" in question:
        args["mission"] = "performance"

    try:
        result = call_tool("tensor_recall", **args)
        candidates = result.get("candidates", [])
        # 格式化为人类可读答案
        if candidates:
            top_names = [c["name"] for c in candidates[:3]]
            answer = (
                f"基于张量分解粗筛，Top-3 候选样机为：" +
                "、".join(f"{c['name']} (sim={c['similarity']:.2f})" for c in candidates[:3]) +
                f"。完整 Top-10 列表：" + "、".join(c["name"] for c in candidates[:10])
            )
        else:
            answer = "（粗筛未返回候选）"
        return {
            "final_answer": answer,
            "iterations": 1,
            "tools_called": ["tensor_recall"],
        }
    except Exception as e:
        return {
            "final_answer": f"（粗筛失败：{type(e).__name__}：{e}）",
            "iterations": 0,
            "tools_called": [],
            "error": str(e),
        }


def run_one_variant(
    variant_key: str,
    test_set: list[dict],
    out_path: Path,
    llm: LLMClient,
    max_iter: int = 6,
):
    spec = ABLATION_VARIANTS[variant_key]
    print("\n" + "=" * 70)
    print(f"  Variant [{variant_key}]: {spec['name']}")
    print(f"  Allowed tools: {spec['allowed_tools']}")
    print("=" * 70)

    is_tensor_only = spec.get("special") == "tensor_only"

    results = []
    total_lat = 0.0
    total_tools = 0

    for i, item in enumerate(test_set, 1):
        try:
            t0 = time.time()
            if is_tensor_only:
                r = run_tensor_only(item["question"])
            else:
                r = react_loop_subset(
                    item["question"],
                    llm=llm,
                    max_iterations=max_iter,
                    allowed_tools=spec["allowed_tools"],
                    extra_system_prompt=spec.get("extra_prompt", ""),
                    verbose=False,
                )
            elapsed = time.time() - t0
            total_lat += elapsed
            n_tools = len(r.get("tools_called", []))
            total_tools += n_tools

            results.append({
                "id": item["id"],
                "category": item.get("category"),
                "difficulty": item.get("difficulty"),
                "question": item["question"],
                "gold_answer": item.get("gold_answer", ""),
                "gold_entities": item.get("gold_entities", []),
                "pred_answer": r.get("final_answer", "") or "",
                "iterations": r.get("iterations", 0),
                "tools_called": r.get("tools_called", []),
                "n_tools": n_tools,
                "latency_s": elapsed,
                "variant": variant_key,
            })
            preview = (r.get("final_answer") or "")[:60].replace("\n", " ")
            print(f"  [{i:3}/{len(test_set)}] {item['id']:14s} {item.get('category')} "
                  f"D={r.get('iterations', 0)} tools={n_tools:2} t={elapsed:5.1f}s  {preview}...")
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
                "iterations": 0,
                "tools_called": [],
                "n_tools": 0,
                "latency_s": 0.0,
                "variant": variant_key,
                "error": f"{type(e).__name__}: {e}",
            })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n  ✓ saved: {out_path}")
    print(f"  Total: {total_lat:.1f}s   Avg: {total_lat/len(test_set):.2f}s/题")
    print(f"  Tool calls: total={total_tools}, avg={total_tools/len(test_set):.1f}/题")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--variant",
        choices=list(ABLATION_VARIANTS.keys()) + ["all"],
        default="all",
    )
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max_iter", type=int, default=6)
    parser.add_argument(
        "--data",
        default=str(ROOT / "papers" / "fwmav-qa-benchmark" / "data" / "fwmav_qa_v2_final.jsonl"),
    )
    parser.add_argument(
        "--out_dir",
        default=str(ROOT / "papers" / "experiment-results"),
    )
    args = parser.parse_args()

    test_set = load_test_set(Path(args.data), n=args.n, seed=args.seed)
    print(f"  Loaded {len(test_set)} test items (seed={args.seed})")
    by_cat = {}
    for it in test_set:
        c = it.get("category", "?")
        by_cat[c] = by_cat.get(c, 0) + 1
    print(f"  Distribution: {dict(sorted(by_cat.items()))}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    llm = LLMClient(mode="auto")
    print(f"  LLM mode: {llm.mode}")

    if args.variant == "all":
        variants_to_run = list(ABLATION_VARIANTS.keys())
    else:
        variants_to_run = [args.variant]

    for v in variants_to_run:
        out_path = out_dir / f"ablation_{v}_predictions.jsonl"
        if out_path.exists():
            print(f"\n  Variant [{v}] output already exists at {out_path}, skipping.")
            print(f"     (delete the file to force re-run)")
            continue
        run_one_variant(v, test_set, out_path, llm, max_iter=args.max_iter)


if __name__ == "__main__":
    main()
