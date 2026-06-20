"""Generate Fig. 7 (R sensitivity) and Fig. 8 (α sensitivity) for §5.6.

Source data: papers/experiment-results/{e1_r_sensitivity,e2_alpha_sensitivity}.json
Output: papers/figures/fig{7,8}-*.{svg,pdf,png}
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = Path(__file__).resolve().parent.parent / "experiment-results"

matplotlib.rcParams.update({
    "font.family": ["Heiti SC", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "axes.linewidth": 0.7,
    "lines.linewidth": 1.2,
    "font.size": 9,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
})

MM_TO_INCH = 1 / 25.4


def save_all(fig, name: str):
    base = OUT_DIR / name
    fig.savefig(str(base) + ".svg", bbox_inches="tight", pad_inches=0.05)
    fig.savefig(str(base) + ".pdf", bbox_inches="tight", pad_inches=0.05)
    fig.savefig(str(base) + ".png", bbox_inches="tight", pad_inches=0.05, dpi=600)
    print(f"  saved {name}.svg / .pdf / .png")


# ---------------------------------------------------------------------------
# Fig. 7: R sensitivity (dual-axis)
# ---------------------------------------------------------------------------
def fig7_r_sensitivity():
    with open(RESULTS_DIR / "e1_r_sensitivity.json", encoding="utf-8") as f:
        data = json.load(f)

    R_values = data["R_values"]
    rec_errs = [data["summary"][str(R)]["rec_err"] for R in R_values]
    top3 = [data["summary"][str(R)]["top3_jaccard_mean"] for R in R_values]
    top5 = [data["summary"][str(R)]["top5_jaccard_mean"] for R in R_values]
    top1 = [data["summary"][str(R)]["top1_match_rate_vs_R12"] for R in R_values]

    fig_w_mm, fig_h_mm = 165, 78
    fig, ax1 = plt.subplots(figsize=(fig_w_mm * MM_TO_INCH, fig_h_mm * MM_TO_INCH))

    color_left = "#3A6B8A"
    line1, = ax1.plot(R_values, rec_errs, "o-", color=color_left, lw=1.4, ms=5,
                      label=r"重构误差 $\|X - \hat{X}\|_F / \|X\|_F$", zorder=3)
    ax1.set_xlabel("CP 分解秩 $R$", fontsize=10)
    ax1.set_ylabel("重构误差", color=color_left, fontsize=10)
    ax1.tick_params(axis="y", labelcolor=color_left)
    ax1.set_ylim(0, 0.85)
    ax1.set_xticks(R_values)
    ax1.grid(True, axis="y", alpha=0.25, linestyle=":", linewidth=0.5)

    ax2 = ax1.twinx()
    color_right = "#B85450"
    line2, = ax2.plot(R_values, top3, "s-", color=color_right, lw=1.2, ms=5,
                      label="Top-3 Jaccard (vs R=12)", zorder=3)
    line3, = ax2.plot(R_values, top5, "^--", color="#D89B30", lw=1.0, ms=5,
                      label="Top-5 Jaccard (vs R=12)", zorder=3, alpha=0.85)
    ax2.set_ylabel("检索一致性", color=color_right, fontsize=10)
    ax2.tick_params(axis="y", labelcolor=color_right)
    ax2.set_ylim(0, 1.05)

    # 标注 R=12 最优点
    ax1.axvline(12, color="#999", linestyle="--", linewidth=0.8, alpha=0.6, zorder=1)
    ax1.annotate("R = 12\n（本文）", xy=(12, 0.39), xytext=(13.5, 0.62),
                 fontsize=9, color="#444",
                 arrowprops=dict(arrowstyle="->", color="#888", lw=0.7))

    # Combined legend
    lines = [line1, line2, line3]
    ax1.legend(lines, [l.get_label() for l in lines], loc="upper right",
               frameon=True, fontsize=8.5, framealpha=0.95)

    ax1.set_title("Fig. 7  CP 分解秩 R 对重构误差与检索一致性的影响", fontsize=11, pad=8)

    save_all(fig, "fig7-r-sensitivity")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig. 8: α sensitivity (single axis, multiple Top-K curves)
# ---------------------------------------------------------------------------
def fig8_alpha_sensitivity():
    with open(RESULTS_DIR / "e2_alpha_sensitivity.json", encoding="utf-8") as f:
        data = json.load(f)

    alphas = data["alphas"]
    top1 = [data["summary"][str(a)]["top1_match_rate_vs_a04"] for a in alphas]
    top3 = [data["summary"][str(a)]["top3_jaccard_mean"] for a in alphas]
    top5 = [data["summary"][str(a)]["top5_jaccard_mean"] for a in alphas]
    spear = [data["summary"][str(a)]["spearman_mean_vs_a04"] for a in alphas]

    fig_w_mm, fig_h_mm = 165, 78
    fig, ax = plt.subplots(figsize=(fig_w_mm * MM_TO_INCH, fig_h_mm * MM_TO_INCH))

    ax.plot(alphas, top1, "o-",  color="#3A6B8A", lw=1.4, ms=5, label="Top-1 一致率 (vs α=0.4)")
    ax.plot(alphas, top3, "s-",  color="#B85450", lw=1.4, ms=5, label="Top-3 Jaccard")
    ax.plot(alphas, top5, "^-",  color="#D89B30", lw=1.4, ms=5, label="Top-5 Jaccard")
    ax.plot(alphas, spear, "d:", color="#7E57C2", lw=1.0, ms=5, label="Spearman 排序相关",
            alpha=0.85)

    ax.set_xlabel(r"混合相似度系数 $\alpha$（α=0 纯 raw / α=1 纯 CP）", fontsize=10)
    ax.set_ylabel("检索一致性", fontsize=10)
    ax.set_xticks(alphas)
    ax.set_ylim(-0.05, 1.10)
    ax.grid(True, axis="both", alpha=0.25, linestyle=":", linewidth=0.5)

    # 标注 α=0.4 最优点
    ax.axvline(0.4, color="#999", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.annotate("α = 0.4\n（本文）", xy=(0.4, 1.0), xytext=(0.5, 0.65),
                fontsize=9, color="#444",
                arrowprops=dict(arrowstyle="->", color="#888", lw=0.7))

    # 阴影区域标注两端不稳定区
    ax.axvspan(-0.05, 0.10, color="#F0E0DC", alpha=0.35, zorder=0)
    ax.axvspan(0.90, 1.05, color="#F0E0DC", alpha=0.35, zorder=0)
    ax.text(0.05, 0.05, "纯 raw\n失稳", ha="center", va="bottom", fontsize=8, color="#9C5048", style="italic")
    ax.text(0.95, 0.05, "纯 CP\n失稳", ha="center", va="bottom", fontsize=8, color="#9C5048", style="italic")

    ax.legend(loc="upper right", frameon=True, fontsize=8.5, framealpha=0.95)
    ax.set_title("Fig. 8  混合相似度 α 对检索一致性的影响（R = 12 固定）", fontsize=11, pad=8)

    save_all(fig, "fig8-alpha-sensitivity")
    plt.close(fig)


def main():
    print("Generating Fig. 7 — R sensitivity ...")
    fig7_r_sensitivity()
    print("Generating Fig. 8 — α sensitivity ...")
    fig8_alpha_sensitivity()
    print("Done.")


if __name__ == "__main__":
    main()
