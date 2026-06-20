"""统一评测脚本：对一个或多个 *_predictions.jsonl 跑指标评估，输出对比报告.

使用方式:
    # 评估单个文件
    python3 biobridge/experiments/evaluate.py b1_pure_llm_predictions.jsonl
    # 对比多个变体
    python3 biobridge/experiments/evaluate.py b1_pure_llm ablation_full ablation_no_bilayer
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from biobridge.experiments.metrics import evaluate_qa


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
                "gold_answer": row.get("gold_answer", ""),
                "gold_entities": row.get("gold_entities", []),
                "n_tools": row.get("n_tools", 0),
                "iterations": row.get("iterations", 0),
                "latency_s": row.get("latency_s", 0.0),
            })
    return predictions, gold_items


def evaluate_file(jsonl_path: Path) -> dict:
    """对单个 prediction 文件评估，返回 metrics dict."""
    predictions, gold_items = load_predictions(jsonl_path)
    result = evaluate_qa(predictions, gold_items)
    # 加上系统级统计
    avg_iter = sum(g.get("iterations", 0) for g in gold_items) / max(len(gold_items), 1)
    avg_tools = sum(g.get("n_tools", 0) for g in gold_items) / max(len(gold_items), 1)
    avg_lat = sum(g.get("latency_s", 0) for g in gold_items) / max(len(gold_items), 1)
    result["overall"]["avg_iterations"] = avg_iter
    result["overall"]["avg_n_tools"] = avg_tools
    result["overall"]["avg_latency_s"] = avg_lat
    return result


def print_summary(name: str, result: dict):
    o = result["overall"]
    print(f"\n  ---- {name} (n={o['n_items']}) ----")
    print(f"    EM:                 {o['em']:.3f}")
    print(f"    F1 (char-level):    {o['f1_char']:.3f}")
    print(f"    F1 (jieba):         {o['f1_jieba']:.3f}")
    print(f"    Hit@1:              {o['hit_at_1']:.3f}")
    print(f"    Hit@5:              {o['hit_at_5']:.3f}")
    print(f"    Entity Recall:      {o['entity_recall']:.3f}")
    print(f"    Faithfulness lite:  {o['faithfulness_lite']:.3f}")
    print(f"    Avg iterations:     {o.get('avg_iterations', 0):.2f}")
    print(f"    Avg #tools:         {o.get('avg_n_tools', 0):.2f}")
    print(f"    Avg latency (s):    {o.get('avg_latency_s', 0):.2f}")
    print(f"    By category:")
    for c, m in sorted(result["by_category"].items()):
        print(f"      {c}: n={m['n']:3} EM={m['em']:.2f} F1c={m['f1_char']:.2f} "
              f"H@1={m['hit_at_1']:.2f} H@5={m['hit_at_5']:.2f} "
              f"EntR={m['entity_recall']:.2f} Faith={m['faithfulness_lite']:.2f}")


def write_report(all_results: dict, out_path: Path):
    """写一个 markdown 对比报告."""
    lines = ["# FWMAV-QA 评测报告", "",
             "> 自动生成 · 来源: papers/experiment-results/*_predictions.jsonl", ""]

    # Overall comparison
    lines += ["## Overall 对比", "",
              "| 系统 | n | EM | F1 (char) | F1 (jieba) | Hit@1 | Hit@5 | EntR | Faith | avg_iter | avg_tools | avg_lat (s) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, result in all_results.items():
        o = result["overall"]
        lines.append(
            f"| {name} | {o['n_items']} | "
            f"{o['em']:.3f} | {o['f1_char']:.3f} | {o['f1_jieba']:.3f} | "
            f"{o['hit_at_1']:.3f} | {o['hit_at_5']:.3f} | "
            f"{o['entity_recall']:.3f} | {o['faithfulness_lite']:.3f} | "
            f"{o.get('avg_iterations', 0):.2f} | {o.get('avg_n_tools', 0):.2f} | "
            f"{o.get('avg_latency_s', 0):.2f} |"
        )

    # By-category for each system
    lines += ["", "## By-category 详情", ""]
    for name, result in all_results.items():
        lines += [f"### {name}", "",
                  "| Cat | n | EM | F1 char | Hit@1 | Hit@5 | EntR | Faith |",
                  "|---|---|---|---|---|---|---|---|"]
        for c, m in sorted(result["by_category"].items()):
            lines.append(
                f"| {c} | {m['n']} | {m['em']:.2f} | {m['f1_char']:.2f} | "
                f"{m['hit_at_1']:.2f} | {m['hit_at_5']:.2f} | "
                f"{m['entity_recall']:.2f} | {m['faithfulness_lite']:.2f} |"
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  ✓ Report saved: {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files",
        nargs="+",
        help="prediction file basenames (without .jsonl) or full paths",
    )
    parser.add_argument(
        "--results_dir",
        default=str(ROOT / "papers" / "experiment-results"),
    )
    parser.add_argument(
        "--report_out",
        default=str(ROOT / "papers" / "experiment-results" / "eval_report.md"),
    )
    parser.add_argument(
        "--summary_out",
        default=str(ROOT / "papers" / "experiment-results" / "eval_summary.json"),
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    all_results = {}
    for fname in args.files:
        if not fname.endswith(".jsonl"):
            fname = fname + "_predictions.jsonl" if not fname.endswith(".jsonl") else fname
        p = Path(fname)
        if not p.is_absolute():
            p = results_dir / fname
        if not p.exists():
            # try with _predictions suffix removed
            print(f"  WARN: {p} not found")
            continue
        # Use basename minus _predictions.jsonl as key
        name = p.stem.replace("_predictions", "")
        result = evaluate_file(p)
        all_results[name] = result
        print_summary(name, result)

    if not all_results:
        print("ERROR: no input files found")
        return

    # Write summary JSON
    summary_path = Path(args.summary_out)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {
        name: {
            "overall": r["overall"],
            "by_category": r["by_category"],
        }
        for name, r in all_results.items()
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Summary saved: {summary_path}")

    # Write markdown report
    write_report(all_results, Path(args.report_out))


if __name__ == "__main__":
    main()
