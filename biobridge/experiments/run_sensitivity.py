"""E1+E2+E3: 张量分解超参敏感性实验（v2 - 基于 B 类 graded relevance 的独立评测）.

═══════════════════════════════════════════════════════════════════════════
v2 相对 v1 的三处换血（修复 v1 的方法学硬伤）
─────────────────────────────────────────────────────────────────────────
  换① 评测尺子：  "与 R=12/α=0.4 的 Spearman/Jaccard 一致性"（循环论证，自己跟自己比）
                  → NDCG@3 / Recall_strict@3 / P@1（用 B 类 graded relevance 当独立标准答案）
  换② 样本划分：  同一组 5 个参考 query 既选参数又报告（在测试集上调参）
                  → 82 道纯数值 B 题，50/50 切成 tune/report 两集，tune 选参数、report 报结果
  换③ 样本量：    5 个 query（±0.145 剧烈抖动）
                  → 每集 41 题，统计稳定
═══════════════════════════════════════════════════════════════════════════

为什么只用"纯数值约束"的 B 题？
  张量粗筛只处理数值约束（重量/翼展/频率/悬停/任务），不认 biological_prototype。
  用它能力范围内的题测它的超参，才干净、公平。带生物原型的 146 题交给整套 Mavent 处理，
  不属于张量粗筛这一个模块的评测范围。

E1 R sensitivity: 固定 α=0.4，扫 R ∈ {4,6,8,10,12,16,20}，在 tune 集上选 best_R
E2 α sensitivity: 固定 best_R，扫 α ∈ {0,0.2,0.4,0.6,0.8,1.0}，在 tune 集上选 best_α
E3 z-score 对比:  固定 (best_R, best_α)，比 per-feature vs global 归一化在 report 集上的表现
报告:            用 (best_R, best_α) 在 report 集（未参与选参）上跑一次，得最终数字

输出:
- experiment-results/e1_r_sensitivity.json
- experiment-results/e2_alpha_sensitivity.json
- experiment-results/e3_zscore_compare.json
- experiment-results/sensitivity_summary.md
"""

from __future__ import annotations
import sys
import os
import json
import random
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
    MISSION_DIMS,
)
from biobridge.experiments.b_metrics import (
    ndcg_at_k_graded,
    precision_at_1,
)

# ============================================================================
# 配置
# ============================================================================
DATA_PATH = ROOT / "papers" / "fwmav-qa-benchmark" / "data" / "fwmav_qa_v2_b_graded.jsonl"
OUT_DIR = ROOT / "papers" / "experiment-results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42            # 固定随机种子，保证 tune/report 切分可复现
TUNE_RATIO = 0.5     # 50/50 切分
RECALL_K = 10        # ★ 粗筛尺子：张量输出 Top-10 候选，考核"好样机有没有被漏掉"
NDCG_K = 3           # NDCG@3 只作参考（那是下游精排的考题，不是粗筛的）
N_RANDOM_TRIALS = 200  # 随机基线蒙特卡洛次数

R_VALUES = [4, 6, 8, 10, 12, 16, 20]
ALPHA_VALUES = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

# 张量粗筛只认这些数值约束字段（其余如 biological_prototype 视为不可处理）
NUMERIC_FIELDS = {
    "weight_max_g", "weight_min_g", "wingspan_max_mm", "wingspan_min_mm",
    "endurance_min_s", "endurance_max_s", "can_hover", "mission_type",
    "frequency_min_hz", "frequency_max_hz", "speed_max_m_s", "speed_min_m_s",
}

# B 题 mission_type（英文标签）→ 张量的 5 大类
MISSION_TYPE_MAP = {
    "reconnaissance": "task",
    "outdoor_cruise": "task",
    "long_endurance_cruise": "performance",
    "indoor_hover": "performance",
    "high_speed_aerobatics": "maneuver",
    "indoor_autonomous": "research",
    "hybrid_aerial_aquatic": "task",
    "formation_flight": "other",
    "education_demo": "other",
}


# ============================================================================
# 1. 数据加载 + 纯数值题筛选 + tune/report 切分
# ============================================================================
def load_pure_numeric_questions() -> list[dict]:
    """加载 B 类纯数值约束题（排除 biological_prototype，且至少含一个可用数值约束）."""
    qs = []
    with open(DATA_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if not d.get("category", "").startswith("B"):
                continue
            tc = d.get("task_constraints", {})
            if "biological_prototype" in tc:
                continue
            if any(k in NUMERIC_FIELDS for k in tc):
                qs.append(d)
    return qs


def split_tune_report(questions: list[dict]) -> tuple[list[dict], list[dict]]:
    """固定种子把题目切成 tune / report 两集."""
    rng = random.Random(SEED)
    shuffled = questions[:]
    rng.shuffle(shuffled)
    n_tune = round(len(shuffled) * TUNE_RATIO)
    return shuffled[:n_tune], shuffled[n_tune:]


# ============================================================================
# 2. task_constraints → tensor_recall 查询参数
# ============================================================================
def _mid(lo, hi):
    """范围折成代表值：都有取中点，只有一端取该端."""
    if lo is not None and hi is not None:
        return (lo + hi) / 2
    return lo if lo is not None else hi


def build_query_args(tc: dict) -> dict:
    """把 B 题的 task_constraints 映射成 tensor_recall 的参数.

    约束是范围（如 weight_max_g/weight_min_g），张量粗筛吃单个代表值，
    故 min/max 都有时取中点，只有一端时取该端。
    """
    args = {}

    w = _mid(tc.get("weight_min_g"), tc.get("weight_max_g"))
    if w is not None:
        args["weight_g"] = float(w)

    ws = _mid(tc.get("wingspan_min_mm"), tc.get("wingspan_max_mm"))
    if ws is not None:
        args["wingspan_mm"] = float(ws)

    fr = _mid(tc.get("frequency_min_hz"), tc.get("frequency_max_hz"))
    if fr is not None:
        args["frequency_hz"] = float(fr)

    sp = _mid(tc.get("speed_min_m_s"), tc.get("speed_max_m_s"))
    if sp is not None:
        args["speed_max_m_s"] = float(sp)

    en = _mid(tc.get("endurance_min_s"), tc.get("endurance_max_s"))
    if en is not None:
        args["endurance_s"] = float(en)

    if "can_hover" in tc:
        args["can_hover"] = bool(tc["can_hover"])

    mt = tc.get("mission_type")
    if mt and mt in MISSION_TYPE_MAP:
        args["mission"] = MISSION_TYPE_MAP[mt]

    return args


# ============================================================================
# 3. 名字对齐校验（张量输出名 vs graded_relevance key）
# ============================================================================
def verify_name_alignment(decomp: dict, questions: list[dict]) -> None:
    """确认张量的 FWMAV 名字集合与 graded_relevance 的 key 集合一致，否则查分全 miss."""
    tensor_names = set(decomp["fwmav_names"])
    graded_names = set(questions[0]["graded_relevance"].keys())
    only_tensor = tensor_names - graded_names
    only_graded = graded_names - tensor_names
    if only_tensor or only_graded:
        print("  ⚠️  名字对齐告警：")
        if only_tensor:
            print(f"     仅在张量中: {sorted(only_tensor)}")
        if only_graded:
            print(f"     仅在graded中: {sorted(only_graded)}")
        overlap = len(tensor_names & graded_names)
        print(f"     交集 {overlap}/{len(graded_names)} —— 未对齐的样机在评测中会被当作 rel=0")
    else:
        print(f"  ✓ 名字对齐: 张量 {len(tensor_names)} 个样机与 graded_relevance 完全一致")


# ============================================================================
# 4. 核心：粗筛尺子 —— Recall@10（Top-10 捞回多少好样机）
# ============================================================================
def recall_at_k(predicted: list[str], graded: dict[str, int],
                min_rel: int, k: int) -> float:
    """Recall@k: Top-k 里命中的好样机数 / 全部好样机数.

    这是粗筛的正确考题：好样机(rel>=min_rel)有没有被漏掉，排第几无所谓。
    与 b_metrics 里 cap-by-k 的版本不同，这里分母是"全部好样机"（真召回率）。
    """
    good = {v for v, r in graded.items() if r >= min_rel}
    if not good:
        return None  # 该题没有此档好样机，不计入
    hit = sum(1 for v in predicted[:k] if v in good)
    return hit / len(good)


def _mean_skip_none(xs: list) -> float:
    vals = [x for x in xs if x is not None]
    return float(np.mean(vals)) if vals else 0.0


def evaluate_config(decomp: dict, questions: list[dict], alpha: float) -> dict:
    """对一批题跑张量粗筛，主看 Recall@10（粗筛尺子），NDCG@3/P@1 作参考."""
    rec_loose, rec_strict, ndcgs, p1s = [], [], [], []
    for q in questions:
        args = build_query_args(q["task_constraints"])
        res = tensor_recall(decomp, top_k=RECALL_K, embedding_weight=alpha, **args)
        predicted = [c["name"] for c in res["candidates"]]
        graded = q["graded_relevance"]

        rec_loose.append(recall_at_k(predicted, graded, min_rel=2, k=RECALL_K))
        rec_strict.append(recall_at_k(predicted, graded, min_rel=3, k=RECALL_K))
        ndcgs.append(ndcg_at_k_graded(predicted, graded, k=NDCG_K))
        p1s.append(precision_at_1(predicted, graded))

    return {
        "n": len(questions),
        "recall_loose@10": _mean_skip_none(rec_loose),   # ★ 主指标: 捞回 rel>=2 的比例
        "recall_strict@10": _mean_skip_none(rec_strict),  #   捞回 rel=3 的比例
        "ndcg@3": float(np.mean(ndcgs)),                  #   参考: 精排考题
        "p@1": float(np.mean(p1s)),                       #   参考: 精排考题
    }


def random_baseline(questions: list[dict], fwmav_names: list[str]) -> dict:
    """随机抓 K 个的 Recall@10 —— 及格线。张量必须明显超过它才算有用."""
    rng = random.Random(SEED)
    rec_loose, rec_strict = [], []
    for _ in range(N_RANDOM_TRIALS):
        for q in questions:
            picks = rng.sample(fwmav_names, RECALL_K)
            graded = q["graded_relevance"]
            rl = recall_at_k(picks, graded, min_rel=2, k=RECALL_K)
            rs = recall_at_k(picks, graded, min_rel=3, k=RECALL_K)
            if rl is not None:
                rec_loose.append(rl)
            if rs is not None:
                rec_strict.append(rs)
    return {
        "recall_loose@10": _mean_skip_none(rec_loose),
        "recall_strict@10": _mean_skip_none(rec_strict),
    }


# ============================================================================
# 5. E1: R sensitivity（tune 集上，α=0.4 固定）
# ============================================================================
def run_e1(td: dict, tune: list[dict]) -> tuple[dict, int, dict]:
    print("=" * 74)
    print("  E1: CP 分解秩 R sensitivity  (tune 集, α=0.4 固定)")
    print("=" * 74)

    results = {"R_values": R_VALUES, "alpha_fixed": 0.4, "by_R": {}}
    decomps = {}
    for R in R_VALUES:
        decomp = decompose_tensor(td, rank=R, random_state=42)
        decomps[R] = decomp
        m = evaluate_config(decomp, tune, alpha=0.4)
        m["rec_err"] = decomp["reconstruction_error"]
        results["by_R"][R] = m
        print(f"  R={R:>2}  rec_err={m['rec_err']:.4f}  "
              f"Recall_loose@10={m['recall_loose@10']:.3f}  "
              f"Recall_strict@10={m['recall_strict@10']:.3f}  "
              f"(NDCG@3={m['ndcg@3']:.3f})")

    # 选 best_R：粗筛主指标 Recall_loose@10 最高（并列时取较小 R，更简约）
    best_R = max(R_VALUES, key=lambda R: (results["by_R"][R]["recall_loose@10"], -R))
    results["best_R"] = best_R
    print(f"\n  → best_R = {best_R}  (Recall_loose@10={results['by_R'][best_R]['recall_loose@10']:.3f})")

    with open(OUT_DIR / "e1_r_sensitivity.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    return results, best_R, decomps


# ============================================================================
# 6. E2: α sensitivity（tune 集上，R=best_R 固定）
# ============================================================================
def run_e2(decomp: dict, tune: list[dict], best_R: int) -> tuple[dict, float]:
    print("\n" + "=" * 74)
    print(f"  E2: 混合相似度 α sensitivity  (tune 集, R={best_R} 固定)")
    print("=" * 74)

    results = {"alphas": ALPHA_VALUES, "R_fixed": best_R, "by_alpha": {}}
    for alpha in ALPHA_VALUES:
        m = evaluate_config(decomp, tune, alpha=alpha)
        results["by_alpha"][alpha] = m
        print(f"  α={alpha:.1f}  Recall_loose@10={m['recall_loose@10']:.3f}  "
              f"Recall_strict@10={m['recall_strict@10']:.3f}  (NDCG@3={m['ndcg@3']:.3f})")

    best_alpha = max(ALPHA_VALUES, key=lambda a: results["by_alpha"][a]["recall_loose@10"])
    results["best_alpha"] = best_alpha
    print(f"\n  → best_α = {best_alpha}  (Recall_loose@10={results['by_alpha'][best_alpha]['recall_loose@10']:.3f})")

    with open(OUT_DIR / "e2_alpha_sensitivity.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    return results, best_alpha


# ============================================================================
# 7. E3: z-score 归一化对比（report 集上，固定 best_R/best_α）
# ============================================================================
def build_tensor_global_zscore() -> dict:
    """build_tensor 的变体：全局 z-score（单一 μ,σ 覆盖所有元素）."""
    td = build_tensor()
    X = td["tensor_raw"].copy()
    mu = X.mean()
    sigma = max(X.std(), 1e-6)
    td_global = dict(td)
    td_global["tensor"] = (X - mu) / sigma
    return td_global


def run_e3(report: list[dict], best_R: int, best_alpha: float) -> dict:
    print("\n" + "=" * 74)
    print(f"  E3: z-score 归一化对比  (report 集, R={best_R}, α={best_alpha})")
    print("=" * 74)

    td_pf = build_tensor()
    td_gl = build_tensor_global_zscore()
    decomp_pf = decompose_tensor(td_pf, rank=best_R, random_state=42)
    decomp_gl = decompose_tensor(td_gl, rank=best_R, random_state=42)

    m_pf = evaluate_config(decomp_pf, report, alpha=best_alpha)
    m_gl = evaluate_config(decomp_gl, report, alpha=best_alpha)
    m_pf["rec_err"] = decomp_pf["reconstruction_error"]
    m_gl["rec_err"] = decomp_gl["reconstruction_error"]

    print(f"  per-feature:  rec_err={m_pf['rec_err']:.4f}  "
          f"Recall_loose@10={m_pf['recall_loose@10']:.3f}  Recall_strict@10={m_pf['recall_strict@10']:.3f}")
    print(f"  global:       rec_err={m_gl['rec_err']:.4f}  "
          f"Recall_loose@10={m_gl['recall_loose@10']:.3f}  Recall_strict@10={m_gl['recall_strict@10']:.3f}")

    results = {"per_feature": m_pf, "global": m_gl}
    with open(OUT_DIR / "e3_zscore_compare.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    return results


# ============================================================================
# 8. Markdown 汇总
# ============================================================================
def write_summary(e1, e2, e3, best_R, best_alpha, report_metrics, rand_report,
                  n_tune, n_report):
    lines = [
        "# 张量分解超参敏感性实验结果汇总 (v2 · 粗筛尺子)", "",
        "> 自动生成 · 评测基于 B 类 graded relevance（独立标准答案）",
        f"> tune 集 {n_tune} 题选参数 · report 集 {n_report} 题报告结果 · seed={SEED}",
        "> **主指标 Recall_loose@10**：张量粗筛 Top-10 捞回 rel≥2 好样机的比例。",
        "> 粗筛的职责是\"缩小范围不漏\"，排序精度(NDCG@3/P@1)交给下游 ReAct 精排，故仅作参考。", "",
        "## E1: CP 分解秩 R 灵敏性 (tune 集, α=0.4)", "",
        "| R | 重构误差 | Recall_loose@10 | Recall_strict@10 | (NDCG@3) |",
        "|---|---|---|---|---|",
    ]
    for R in e1["R_values"]:
        s = e1["by_R"][R]
        star = " ★" if R == best_R else ""
        lines.append(f"| {R}{star} | {s['rec_err']:.4f} | {s['recall_loose@10']:.3f} | "
                     f"{s['recall_strict@10']:.3f} | {s['ndcg@3']:.3f} |")

    lines += ["", f"**best_R = {best_R}**（Recall_loose@10 最高）", "",
              f"## E2: 混合相似度 α 灵敏性 (tune 集, R={best_R})", "",
              "| α | Recall_loose@10 | Recall_strict@10 | (NDCG@3) |",
              "|---|---|---|---|"]
    for a in e2["alphas"]:
        s = e2["by_alpha"][a]
        star = " ★" if abs(a - best_alpha) < 1e-9 else ""
        lines.append(f"| {a}{star} | {s['recall_loose@10']:.3f} | "
                     f"{s['recall_strict@10']:.3f} | {s['ndcg@3']:.3f} |")

    lines += ["", f"**best_α = {best_alpha}**（Recall_loose@10 最高）", "",
              f"## E3: z-score 归一化对比 (report 集, R={best_R}, α={best_alpha})", "",
              "| 归一化 | 重构误差 | Recall_loose@10 | Recall_strict@10 |",
              "|---|---|---|---|",
              f"| per-feature | {e3['per_feature']['rec_err']:.4f} | {e3['per_feature']['recall_loose@10']:.3f} | "
              f"{e3['per_feature']['recall_strict@10']:.3f} |",
              f"| global | {e3['global']['rec_err']:.4f} | {e3['global']['recall_loose@10']:.3f} | "
              f"{e3['global']['recall_strict@10']:.3f} |", "",
              "## ★ 最终报告 (report 集, 未参与选参)", "",
              f"用在 tune 集上选出的 **R={best_R}, α={best_alpha}** 在独立 report 集（{n_report} 题）上评测，"
              "并与随机抓 10 个的基线对比：", "",
              "| 方法 | Recall_loose@10 | Recall_strict@10 | (NDCG@3) | (P@1) |",
              "|---|---|---|---|---|",
              f"| 张量粗筛 | {report_metrics['recall_loose@10']:.3f} | "
              f"{report_metrics['recall_strict@10']:.3f} | {report_metrics['ndcg@3']:.3f} | {report_metrics['p@1']:.3f} |",
              f"| 随机基线 | {rand_report['recall_loose@10']:.3f} | "
              f"{rand_report['recall_strict@10']:.3f} | — | — |", "",
              f"张量粗筛相对随机基线的提升："
              f"Recall_loose@10 {report_metrics['recall_loose@10'] - rand_report['recall_loose@10']:+.3f}，"
              f"Recall_strict@10 {report_metrics['recall_strict@10'] - rand_report['recall_strict@10']:+.3f}。", ""]

    with open(OUT_DIR / "sensitivity_summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n  ✓ saved: {OUT_DIR / 'sensitivity_summary.md'}")


# ============================================================================
# main
# ============================================================================
def main():
    print("加载 B 类纯数值约束题...")
    questions = load_pure_numeric_questions()
    tune, report = split_tune_report(questions)
    print(f"  纯数值题 {len(questions)} 道 → tune {len(tune)} / report {len(report)} (seed={SEED})\n")

    print("从 KG 构建张量 + 名字对齐校验...")
    td = build_tensor()
    print(f"  Tensor shape: {td['shape']}")
    _decomp_check = decompose_tensor(td, rank=12, random_state=42)
    verify_name_alignment(_decomp_check, questions)
    print()

    # E1: 选 R
    e1, best_R, decomps = run_e1(td, tune)
    # E2: 固定 best_R 选 α
    e2, best_alpha = run_e2(decomps[best_R], tune, best_R)
    # E3: 归一化对比（report 集）
    e3 = run_e3(report, best_R, best_alpha)

    # ★ 最终报告：report 集 + 随机基线
    print("\n" + "=" * 74)
    print(f"  ★ 最终报告：R={best_R}, α={best_alpha} 在 report 集（未参与选参）上")
    print("=" * 74)
    report_metrics = evaluate_config(decomps[best_R], report, alpha=best_alpha)
    rand_report = random_baseline(report, decomps[best_R]["fwmav_names"])
    print(f"  张量粗筛  Recall_loose@10={report_metrics['recall_loose@10']:.3f}  "
          f"Recall_strict@10={report_metrics['recall_strict@10']:.3f}  "
          f"(NDCG@3={report_metrics['ndcg@3']:.3f}, P@1={report_metrics['p@1']:.3f})")
    print(f"  随机基线  Recall_loose@10={rand_report['recall_loose@10']:.3f}  "
          f"Recall_strict@10={rand_report['recall_strict@10']:.3f}")
    print(f"  → 相对随机提升  Recall_loose@10 "
          f"{report_metrics['recall_loose@10'] - rand_report['recall_loose@10']:+.3f}  "
          f"Recall_strict@10 {report_metrics['recall_strict@10'] - rand_report['recall_strict@10']:+.3f}")

    write_summary(e1, e2, e3, best_R, best_alpha, report_metrics, rand_report,
                  len(tune), len(report))
    print("\n" + "=" * 74)
    print("  Done. Outputs in:", OUT_DIR)
    print("=" * 74)


if __name__ == "__main__":
    main()
