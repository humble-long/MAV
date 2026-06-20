"""E1+E2+E3: 张量分解超参敏感性实验.

E1 R sensitivity:    CP 分解秩 R ∈ {4,6,8,10,12,16,20} 对重构误差 + 检索一致性的影响
E2 α sensitivity:    混合相似度 α ∈ {0,0.2,0.4,0.6,0.8,1.0} 对检索 Top-K 一致性的影响
E3 z-score 对比:     per-feature 标准化 vs 全局标准化 对重构误差 + 检索质量

输出:
- experiment-results/e1_r_sensitivity.json
- experiment-results/e2_alpha_sensitivity.json
- experiment-results/e3_zscore_compare.json
- experiment-results/sensitivity_summary.md (人类可读总结)

参考 query: 5 个代表性任务约束（涵盖小型悬停 / 中型长航 / 昆虫 / 仿鸟 / 多约束）
"""

from __future__ import annotations
import sys
import os
import json
from pathlib import Path

import numpy as np
import tensorly as tl
from tensorly.decomposition import parafac

# Insert project root (one level above biobridge/) so `from biobridge.* import ...` works
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from biobridge.tools.tensor_recall import (
    build_tensor,
    decompose_tensor,
    tensor_recall,
    constraints_to_query_vector,
    EQUIPMENT_DIMS,
    PERFORMANCE_DIMS,
    MISSION_DIMS,
)


REFERENCE_QUERIES = [
    {
        "name": "小型悬停",
        "args": {"weight_g": 30, "endurance_s": 900, "can_hover": True, "mission": "performance"},
    },
    {
        "name": "中型长航时巡航",
        "args": {"weight_g": 300, "endurance_s": 1800, "can_hover": False, "mission": "task"},
    },
    {
        "name": "昆虫尺度极致小型化",
        "args": {"weight_g": 0.5, "wingspan_mm": 35, "frequency_hz": 170, "mission": "research"},
    },
    {
        "name": "仿鸟侦察",
        "args": {"weight_g": 100, "wingspan_mm": 400, "speed_max_m_s": 12, "mission": "task"},
    },
    {
        "name": "多约束概念探索",
        "args": {"weight_g": 50, "wingspan_mm": 250, "endurance_s": 600, "can_hover": False, "mission": "performance"},
    },
]

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "papers" / "experiment-results"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def spearman_rank_corr(rank_a: list[str], rank_b: list[str]) -> float:
    """Compute Spearman rank correlation between two ordered candidate lists.

    Both lists should have the same items (same Top-K cap). For items in only
    one list, we assign them rank = K (penalty position). Returns value in [-1, 1].
    """
    union = list(set(rank_a) | set(rank_b))
    K = max(len(rank_a), len(rank_b))
    if len(union) < 2 or K < 2:
        return 0.0
    pos_a = {n: i for i, n in enumerate(rank_a)}
    pos_b = {n: i for i, n in enumerate(rank_b)}
    n = len(union)
    d2 = 0.0
    for c in union:
        ra = pos_a.get(c, K)  # missing → ranked at K (penalty)
        rb = pos_b.get(c, K)
        d2 += (ra - rb) ** 2
    rho = 1.0 - 6 * d2 / (n * (n * n - 1))
    return max(-1.0, min(1.0, rho))


def topk_intersection(rank_a: list[str], rank_b: list[str], k: int) -> float:
    """Top-K Jaccard / intersection size / k."""
    sa = set(rank_a[:k])
    sb = set(rank_b[:k])
    return len(sa & sb) / k if k > 0 else 0.0


def get_top_candidates(decomp, query_args, top_k=10, alpha=0.4):
    res = tensor_recall(decomp, top_k=top_k, embedding_weight=alpha, **query_args)
    return [c["name"] for c in res["candidates"]]


# ============================================================================
# E1: R sensitivity
# ============================================================================
def run_e1_r_sensitivity():
    print("=" * 70)
    print("  E1: CP 分解秩 R sensitivity")
    print("=" * 70)

    R_values = [4, 6, 8, 10, 12, 16, 20]
    print(f"  Building base tensor...")
    td = build_tensor()
    print(f"  Tensor shape: {td['shape']}")

    results = {"R_values": R_values, "queries": [], "summary": {}}
    rec_errs = []
    decomps = {}

    for R in R_values:
        print(f"\n  CP decomp with R={R} ...")
        decomp = decompose_tensor(td, rank=R, random_state=42)
        rec_errs.append(decomp["reconstruction_error"])
        decomps[R] = decomp
        print(f"    rec_err = {decomp['reconstruction_error']:.4f}")

    # 用 R=12 作为 reference
    ref_decomp = decomps[12]
    ref_topks = {q["name"]: get_top_candidates(ref_decomp, q["args"]) for q in REFERENCE_QUERIES}

    # 每个 query 在不同 R 下的 Top-10 与 R=12 的一致性
    for q in REFERENCE_QUERIES:
        q_result = {"name": q["name"], "args": q["args"], "by_R": {}}
        ref_top = ref_topks[q["name"]]
        for R in R_values:
            cur_top = get_top_candidates(decomps[R], q["args"])
            q_result["by_R"][R] = {
                "top10": cur_top,
                "spearman_vs_R12": spearman_rank_corr(cur_top, ref_top),
                "top1_match": 1.0 if (cur_top and ref_top and cur_top[0] == ref_top[0]) else 0.0,
                "top3_jaccard": topk_intersection(cur_top, ref_top, 3),
                "top5_jaccard": topk_intersection(cur_top, ref_top, 5),
            }
        results["queries"].append(q_result)

    # 汇总
    summary = {}
    for R in R_values:
        spearmans = [q["by_R"][R]["spearman_vs_R12"] for q in results["queries"]]
        top3_js = [q["by_R"][R]["top3_jaccard"] for q in results["queries"]]
        top5_js = [q["by_R"][R]["top5_jaccard"] for q in results["queries"]]
        top1s = [q["by_R"][R]["top1_match"] for q in results["queries"]]
        summary[R] = {
            "rec_err": rec_errs[R_values.index(R)],
            "spearman_mean_vs_R12": float(np.mean(spearmans)),
            "spearman_std_vs_R12": float(np.std(spearmans)),
            "top1_match_rate_vs_R12": float(np.mean(top1s)),
            "top3_jaccard_mean": float(np.mean(top3_js)),
            "top5_jaccard_mean": float(np.mean(top5_js)),
        }

    results["summary"] = summary

    out_path = OUT_DIR / "e1_r_sensitivity.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  ✓ saved: {out_path}")

    print("\n  ----  E1 SUMMARY  ----")
    print(f"  {'R':>4} {'rec_err':>10} {'spearman':>12} {'top1':>8} {'top3 jacc':>12} {'top5 jacc':>12}")
    for R in R_values:
        s = summary[R]
        print(f"  {R:>4} {s['rec_err']:>10.4f} {s['spearman_mean_vs_R12']:>12.3f} "
              f"{s['top1_match_rate_vs_R12']:>8.2f} {s['top3_jaccard_mean']:>12.3f} {s['top5_jaccard_mean']:>12.3f}")

    return results, td


# ============================================================================
# E2: α sensitivity
# ============================================================================
def run_e2_alpha_sensitivity(td):
    print("\n" + "=" * 70)
    print("  E2: 混合相似度 α sensitivity (R fixed = 12)")
    print("=" * 70)

    alphas = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    decomp = decompose_tensor(td, rank=12, random_state=42)
    print(f"  Base decomp rec_err = {decomp['reconstruction_error']:.4f}")

    # 用 α=0.4 作为 reference
    ref_topks = {q["name"]: get_top_candidates(decomp, q["args"], alpha=0.4) for q in REFERENCE_QUERIES}

    results = {"alphas": alphas, "queries": [], "summary": {}}

    for q in REFERENCE_QUERIES:
        q_result = {"name": q["name"], "args": q["args"], "by_alpha": {}}
        ref_top = ref_topks[q["name"]]
        for alpha in alphas:
            cur_top = get_top_candidates(decomp, q["args"], alpha=alpha)
            q_result["by_alpha"][alpha] = {
                "top10": cur_top,
                "spearman_vs_a04": spearman_rank_corr(cur_top, ref_top),
                "top1_match": 1.0 if (cur_top and ref_top and cur_top[0] == ref_top[0]) else 0.0,
                "top3_jaccard": topk_intersection(cur_top, ref_top, 3),
                "top5_jaccard": topk_intersection(cur_top, ref_top, 5),
            }
        results["queries"].append(q_result)

    summary = {}
    for alpha in alphas:
        spearmans = [q["by_alpha"][alpha]["spearman_vs_a04"] for q in results["queries"]]
        top3_js = [q["by_alpha"][alpha]["top3_jaccard"] for q in results["queries"]]
        top5_js = [q["by_alpha"][alpha]["top5_jaccard"] for q in results["queries"]]
        top1s = [q["by_alpha"][alpha]["top1_match"] for q in results["queries"]]
        summary[alpha] = {
            "spearman_mean_vs_a04": float(np.mean(spearmans)),
            "spearman_std_vs_a04": float(np.std(spearmans)),
            "top1_match_rate_vs_a04": float(np.mean(top1s)),
            "top3_jaccard_mean": float(np.mean(top3_js)),
            "top5_jaccard_mean": float(np.mean(top5_js)),
        }

    results["summary"] = summary

    out_path = OUT_DIR / "e2_alpha_sensitivity.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  ✓ saved: {out_path}")

    print("\n  ----  E2 SUMMARY  ----")
    print(f"  {'α':>4} {'spearman':>12} {'top1':>8} {'top3 jacc':>12} {'top5 jacc':>12}")
    for alpha in alphas:
        s = summary[alpha]
        print(f"  {alpha:>4.1f} {s['spearman_mean_vs_a04']:>12.3f} "
              f"{s['top1_match_rate_vs_a04']:>8.2f} {s['top3_jaccard_mean']:>12.3f} {s['top5_jaccard_mean']:>12.3f}")

    return results


# ============================================================================
# E3: z-score normalization comparison
# ============================================================================
def build_tensor_global_zscore():
    """Variant of build_tensor that uses GLOBAL z-score (single μ,σ across all entries)."""
    td = build_tensor()
    X = td["tensor_raw"].copy()
    mu = X.mean()
    sigma = max(X.std(), 1e-6)
    X_global = (X - mu) / sigma
    td_global = dict(td)
    td_global["tensor"] = X_global
    # 重要：feature_means/stds 仍按 per-feature 给（便于查询投影一致），但 tensor 用 global
    return td_global


def run_e3_zscore_compare():
    print("\n" + "=" * 70)
    print("  E3: z-score 标准化对比 (per-feature vs global, R=12)")
    print("=" * 70)

    td_pf = build_tensor()
    td_gl = build_tensor_global_zscore()

    decomp_pf = decompose_tensor(td_pf, rank=12, random_state=42)
    decomp_gl = decompose_tensor(td_gl, rank=12, random_state=42)

    print(f"  per-feature rec_err: {decomp_pf['reconstruction_error']:.4f}")
    print(f"  global rec_err:      {decomp_gl['reconstruction_error']:.4f}")

    results = {
        "queries": [],
        "summary": {
            "per_feature": {"rec_err": decomp_pf["reconstruction_error"]},
            "global": {"rec_err": decomp_gl["reconstruction_error"]},
        }
    }

    for q in REFERENCE_QUERIES:
        top_pf = get_top_candidates(decomp_pf, q["args"], alpha=0.4)
        top_gl = get_top_candidates(decomp_gl, q["args"], alpha=0.4)
        results["queries"].append({
            "name": q["name"],
            "args": q["args"],
            "top_per_feature": top_pf,
            "top_global": top_gl,
            "spearman": spearman_rank_corr(top_pf, top_gl),
            "top1_agree": 1.0 if (top_pf and top_gl and top_pf[0] == top_gl[0]) else 0.0,
            "top3_jaccard": topk_intersection(top_pf, top_gl, 3),
            "top5_jaccard": topk_intersection(top_pf, top_gl, 5),
        })

    sp = np.mean([q["spearman"] for q in results["queries"]])
    t1 = np.mean([q["top1_agree"] for q in results["queries"]])
    t3 = np.mean([q["top3_jaccard"] for q in results["queries"]])
    t5 = np.mean([q["top5_jaccard"] for q in results["queries"]])
    results["summary"]["agreement"] = {
        "spearman_mean": float(sp),
        "top1_match_rate": float(t1),
        "top3_jaccard_mean": float(t3),
        "top5_jaccard_mean": float(t5),
    }

    out_path = OUT_DIR / "e3_zscore_compare.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  ✓ saved: {out_path}")

    print("\n  ----  E3 SUMMARY  ----")
    print(f"  per-feature rec_err: {decomp_pf['reconstruction_error']:.4f}")
    print(f"  global rec_err:      {decomp_gl['reconstruction_error']:.4f}")
    print(f"  Top-1 一致率:        {t1:.2f}")
    print(f"  Top-3 Jaccard:       {t3:.3f}")
    print(f"  Top-5 Jaccard:       {t5:.3f}")
    print(f"  Spearman 平均:       {sp:.3f}")

    return results


# ============================================================================
# Markdown summary writer
# ============================================================================
def write_summary(e1, e2, e3):
    out_path = OUT_DIR / "sensitivity_summary.md"
    lines = ["# 张量分解超参敏感性实验结果汇总", "",
             "> 自动生成 · 数据来源: e1/e2/e3 *.json", "",
             "## E1: CP 分解秩 R 灵敏性", ""]

    lines += ["| R | 重构误差 | Spearman vs R=12 | Top-1 一致率 | Top-3 Jaccard | Top-5 Jaccard |",
              "|---|---|---|---|---|---|"]
    for R in e1["R_values"]:
        s = e1["summary"][R]
        lines.append(
            f"| {R} | {s['rec_err']:.4f} | {s['spearman_mean_vs_R12']:.3f}±{s['spearman_std_vs_R12']:.3f} | "
            f"{s['top1_match_rate_vs_R12']:.2f} | {s['top3_jaccard_mean']:.3f} | {s['top5_jaccard_mean']:.3f} |"
        )

    lines += ["", "## E2: 混合相似度 α 灵敏性 (R=12 固定)", "",
              "| α | Spearman vs α=0.4 | Top-1 一致率 | Top-3 Jaccard | Top-5 Jaccard |",
              "|---|---|---|---|---|"]
    for alpha in e2["alphas"]:
        s = e2["summary"][alpha]
        lines.append(
            f"| {alpha} | {s['spearman_mean_vs_a04']:.3f}±{s['spearman_std_vs_a04']:.3f} | "
            f"{s['top1_match_rate_vs_a04']:.2f} | {s['top3_jaccard_mean']:.3f} | {s['top5_jaccard_mean']:.3f} |"
        )

    lines += ["", "## E3: z-score 标准化方式对比 (R=12, α=0.4)", "",
              f"- per-feature 重构误差: **{e3['summary']['per_feature']['rec_err']:.4f}**",
              f"- global 重构误差:      **{e3['summary']['global']['rec_err']:.4f}**",
              f"- Top-1 一致率:         {e3['summary']['agreement']['top1_match_rate']:.2f}",
              f"- Top-3 Jaccard:        {e3['summary']['agreement']['top3_jaccard_mean']:.3f}",
              f"- Top-5 Jaccard:        {e3['summary']['agreement']['top5_jaccard_mean']:.3f}",
              f"- Spearman 平均:        {e3['summary']['agreement']['spearman_mean']:.3f}",
              ""]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n  ✓ saved: {out_path}")


def main():
    e1, td = run_e1_r_sensitivity()
    e2 = run_e2_alpha_sensitivity(td)
    e3 = run_e3_zscore_compare()
    write_summary(e1, e2, e3)
    print("\n" + "=" * 70)
    print("  Done. Outputs in:", OUT_DIR)
    print("=" * 70)


if __name__ == "__main__":
    main()
