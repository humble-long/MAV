"""统一评测脚本：对一个或多个 *_predictions.jsonl 跑 LLM-as-Judge 指标评估，输出对比报告.

使用方式:
    # 评估单个文件
    python3 biobridge/experiments/evaluate.py b1_pure_llm_predictions.jsonl
    # 对比多个变体
    python3 biobridge/experiments/evaluate.py b1_pure_llm ablation_full
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from biobridge.experiments.llm_judge import evaluate_a_metrics
from biobridge.experiments.metrics import evaluate_qa
from biobridge.experiments.b_metrics import evaluate_b_metrics, load_b_gold


def load_predictions(jsonl_path: Path) -> tuple[dict, list]:
    """从 *_predictions.jsonl 解析出 (predictions_dict, gold_items_list)."""
    predictions = {}
    gold_items = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            qid = row["id"]
            predictions[qid] = row.get("pred_answer", "")
            gold_items.append({
                "id": qid,
                "category": row.get("category"),
                "difficulty": row.get("difficulty"),
                "question": row.get("question", ""),
                "gold_answer": row.get("gold_answer", ""),
                "gold_entities": row.get("gold_entities", []),
                "n_tools": row.get("n_tools", 0),
                "iterations": row.get("iterations", 0),
                "latency_s": row.get("latency_s", 0.0),
                "error": row.get("error", ""),
            })
    return predictions, gold_items


def evaluate_file(jsonl_path: Path, b_gold_lookup: dict | None = None,
                  verbose: bool = True) -> dict:
    """对单个 prediction 文件评估.

    A 类：LLM-as-Judge（A2 属性值准确率 / A3 对比完整度 / A4 推理有效性）
    B 类：NDCG@3 (binary) + CSR@3（需提供 b_gold_lookup）
    """
    predictions, gold_items = load_predictions(jsonl_path)

    a_items = [g for g in gold_items if g.get("category") in ("A2", "A3", "A4")]
    b_items = [g for g in gold_items if g.get("category") in ("B1", "B2")]

    # A 类：LLM-as-Judge
    a_preds = {g["id"]: predictions.get(g["id"], "") for g in a_items}
    a_result = evaluate_a_metrics(a_preds, a_items, verbose=verbose)

    # B 类：NDCG@3 + CSR@3
    if b_items and b_gold_lookup:
        b_preds = {g["id"]: predictions.get(g["id"], "") for g in b_items}
        # 仅评测在 b_gold_lookup 中存在的题
        b_subset = {qid: b_gold_lookup[qid] for qid in b_preds if qid in b_gold_lookup}
        b_result = evaluate_b_metrics(b_preds, b_subset, k=3, verbose=verbose)
    else:
        b_result = {"overall": {"n_total": 0, "ndcg_at_3_mean": 0.0,
                                "csr_at_3_n": 0, "csr_at_3_mean": 0.0},
                    "by_category": {}, "per_item": []}

    all_items = a_items + b_items
    n = len(all_items)
    avg_iter = sum(g.get("iterations", 0) for g in all_items) / max(n, 1)
    avg_tools = sum(g.get("n_tools", 0) for g in all_items) / max(n, 1)
    avg_lat = sum(g.get("latency_s", 0) for g in all_items) / max(n, 1)

    return {
        "n_total": n,
        "n_a": len(a_items),
        "n_b": len(b_items),
        "a_metrics": a_result,
        "b_metrics": b_result,
        "avg_iterations": avg_iter,
        "avg_n_tools": avg_tools,
        "avg_latency_s": avg_lat,
    }


def print_summary(name: str, result: dict):
    a = result["a_metrics"]
    ao = a["overall"]

    print(f"\n  ---- {name} (总 {result['n_total']} 题, A {result['n_a']} + B {result['n_b']}) ----")
    print(f"    Avg iterations:  {result.get('avg_iterations', 0):.2f}")
    print(f"    Avg #tools:      {result.get('avg_n_tools', 0):.2f}")
    print(f"    Avg latency (s): {result.get('avg_latency_s', 0):.2f}")

    print(f"\n    --- A 类 LLM-as-Judge (A2+A3+A4, n={ao['n_total']}) ---")
    print(f"      A2 属性值准确率:  {ao['a2_accuracy_mean']:.3f}")
    print(f"      A3 对比完整度:    {ao['a3_completeness_mean']:.3f}")
    print(f"      A4 推理有效性:    {ao['a4_validity_mean']:.3f}")
    print(f"      逐类:")
    for c, m in sorted(a["by_category"].items()):
        print(f"        {c}: n={m['n']:3}  mean={m['mean']:.3f}  min={m['min']:.3f}  max={m['max']:.3f}")

    b = result["b_metrics"]["overall"]
    print(f"\n    --- B 类 (B1+B2, n={result['n_b']}) graded 多指标 ---")
    print(f"      NDCG@3 (graded):  {b.get('ndcg_graded_mean', 0):.3f}")
    print(f"      Recall_strict@3:  {b.get('recall_strict_mean', 0):.3f}  (命中 rel=3)")
    print(f"      Recall_loose@3:   {b.get('recall_loose_mean', 0):.3f}   (命中 rel≥2)")
    print(f"      P@1:              {b.get('p_at_1_mean', 0):.3f}        (第一推荐是 rel=3)")
    by_cat = result["b_metrics"].get("by_category", {})
    for c, m in sorted(by_cat.items()):
        print(f"        {c}: n={m['n']:3}  NDCG={m['ndcg_graded_mean']:.3f}  "
              f"R_strict={m['recall_strict_mean']:.3f}  R_loose={m['recall_loose_mean']:.3f}  "
              f"P@1={m['p_at_1_mean']:.3f}")


def write_report(all_results: dict, out_path: Path):
    lines = ["# FWMAV-QA 评测报告", "",
             "> 自动生成 · LLM-as-Judge 指标",
             "",
             "> A 类：A2 属性值准确率 / A3 对比完整度 / A4 推理有效性",
             "> B 类：待 NDCG/MRR/Recall@10 实现"]

    # A 类
    lines += ["", "## A 类 LLM-as-Judge 对比", "",
              "| 系统 | n | A2 属性值准确率 | A3 对比完整度 | A4 推理有效性 | avg_iter | avg_tools | avg_lat (s) |",
              "|---|---|---|---|---|---|---|---|"]
    for name, result in all_results.items():
        ao = result["a_metrics"]["overall"]
        lines.append(
            f"| {name} | {result['n_a']} | "
            f"{ao['a2_accuracy_mean']:.3f} | {ao['a3_completeness_mean']:.3f} | "
            f"{ao['a4_validity_mean']:.3f} | "
            f"{result.get('avg_iterations', 0):.2f} | {result.get('avg_n_tools', 0):.2f} | "
            f"{result.get('avg_latency_s', 0):.2f} |"
        )

    # By-category
    lines += ["", "## A 类 By-category 详情", ""]
    for name, result in all_results.items():
        lines += [f"### {name}", "",
                  "| Cat | n | mean | min | max |",
                  "|---|---|---|---|---|"]
        for c, m in sorted(result["a_metrics"]["by_category"].items()):
            lines.append(f"| {c} | {m['n']} | {m['mean']:.3f} | {m['min']:.3f} | {m['max']:.3f} |")
        lines.append("")

    lines += ["", "## B 类 graded 多指标对比", "",
              "| 系统 | n_B | NDCG@3 | R_strict@3 | R_loose@3 | P@1 |",
              "|---|---|---|---|---|---|"]
    for name, result in all_results.items():
        b = result["b_metrics"]["overall"]
        lines.append(
            f"| {name} | {result['n_b']} | "
            f"{b.get('ndcg_graded_mean', 0):.3f} | "
            f"{b.get('recall_strict_mean', 0):.3f} | "
            f"{b.get('recall_loose_mean', 0):.3f} | "
            f"{b.get('p_at_1_mean', 0):.3f} |"
        )

    # B 类 by-category
    lines += ["", "## B 类 By-category 详情", ""]
    for name, result in all_results.items():
        lines += [f"### {name}", "",
                  "| Cat | n | NDCG@3 | R_strict@3 | R_loose@3 | P@1 |",
                  "|---|---|---|---|---|---|"]
        for c, m in sorted(result["b_metrics"].get("by_category", {}).items()):
            lines.append(
                f"| {c} | {m['n']} | "
                f"{m['ndcg_graded_mean']:.3f} | "
                f"{m['recall_strict_mean']:.3f} | "
                f"{m['recall_loose_mean']:.3f} | "
                f"{m['p_at_1_mean']:.3f} |"
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  ✓ Report saved: {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+",
                        help="prediction file basenames or full paths")
    parser.add_argument("--results_dir",
                        default=str(ROOT / "papers" / "experiment-results"))
    parser.add_argument("--b_gold",
                        default=str(ROOT / "papers" / "fwmav-qa-benchmark" / "data" / "fwmav_qa_v2_b_graded.jsonl"),
                        help="B 类标注文件（含 graded_relevance）")
    parser.add_argument("--report_out",
                        default=str(ROOT / "papers" / "experiment-results" / "eval_report.md"))
    parser.add_argument("--summary_out",
                        default=str(ROOT / "papers" / "experiment-results" / "eval_summary.json"))
    args = parser.parse_args()

    # 加载 B 类 gold
    b_gold_path = Path(args.b_gold)
    if b_gold_path.exists():
        b_gold_lookup = load_b_gold(b_gold_path)
        print(f"[Eval] 加载 B 类 gold: {len(b_gold_lookup)} 题  ({b_gold_path})")
    else:
        b_gold_lookup = {}
        print(f"[Eval] WARNING: B 类 gold 不存在: {b_gold_path}")

    results_dir = Path(args.results_dir)
    all_results = {}
    for fname in args.files:
        if not fname.endswith(".jsonl"):
            fname = fname + "_predictions.jsonl"
        p = Path(fname)
        if not p.is_absolute():
            p = results_dir / fname
        if not p.exists():
            print(f"  WARN: {p} not found")
            continue
        name = p.stem.replace("_predictions", "")
        result = evaluate_file(p, b_gold_lookup=b_gold_lookup)
        all_results[name] = result
        print_summary(name, result)

    if not all_results:
        print("ERROR: no input files found")
        return

    # Write summary JSON
    summary_path = Path(args.summary_out)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {}
    for name, r in all_results.items():
        serializable[name] = {
            "n_total": r["n_total"],
            "n_a": r["n_a"],
            "n_b": r["n_b"],
            "a_metrics": r["a_metrics"],
            "b_metrics": r["b_metrics"],
            "avg_iterations": r["avg_iterations"],
            "avg_n_tools": r["avg_n_tools"],
            "avg_latency_s": r["avg_latency_s"],
        }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Summary saved: {summary_path}")

    write_report(all_results, Path(args.report_out))


if __name__ == "__main__":
    main()
