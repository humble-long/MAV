"""Generate Fig. 1 (Bilayer ontology) and Fig. 2 (KG pipeline) for the paper.

Outputs SVG + PNG@600dpi + PDF to papers/figures/.
Selected backend: matplotlib (exclusive per nature-figure contract).
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.path import Path as MplPath
import numpy as np

OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Style —航空学报 / submission-grade
# ---------------------------------------------------------------------------

matplotlib.rcParams.update({
    "font.family": ["Heiti SC", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,   # editable text in vector
    "ps.fonttype": 42,
    "svg.fonttype": "none",  # text remains text, not paths
    "axes.linewidth": 0.6,
    "lines.linewidth": 0.8,
})

# Restrained palette (5 hues, no neon)
COLOR_BIO = "#5D8AA8"        # 工程层 (Engineering, blue-grey)
COLOR_ENG = "#7BAA6E"        # 生物层 (Biology, sage green) — NOTE intentionally swapping below
ENG_FILL = "#E8EFF5"         # light blue
ENG_EDGE = "#3A6B8A"
BIO_FILL = "#EAF2E5"         # light green
BIO_EDGE = "#587A4A"
NEUTRAL_FILL = "#F5F5F0"     # parchment for ancillary nodes
NEUTRAL_EDGE = "#999988"
TEXT_DARK = "#1F2A36"

# 4 MIMICS colors — same hue family, different saturation
MIMICS_COLORS = {
    "aero":        "#C0392B",   # warm red
    "kinematics":  "#D89B30",   # amber
    "morphology":  "#7E57C2",   # purple
    "scale":       "#28867D",   # teal
}

MM_TO_INCH = 1 / 25.4


def save_all(fig, name: str):
    """Save the figure to SVG, PDF, and PNG@600dpi."""
    base = OUT_DIR / name
    fig.savefig(str(base) + ".svg", bbox_inches="tight", pad_inches=0.05)
    fig.savefig(str(base) + ".pdf", bbox_inches="tight", pad_inches=0.05)
    fig.savefig(str(base) + ".png", bbox_inches="tight", pad_inches=0.05, dpi=600)
    print(f"  saved {name}.svg / .pdf / .png")


# ---------------------------------------------------------------------------
# Fig. 1 — Bilayer ontology schematic
# ---------------------------------------------------------------------------

def draw_node(ax, x, y, w, h, label, fill, edge, fontsize=8, fontweight="normal"):
    """Rounded rectangle node with centered label."""
    box = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.005,rounding_size=0.012",
        linewidth=0.7, edgecolor=edge, facecolor=fill,
    )
    ax.add_patch(box)
    ax.text(x, y, label, ha="center", va="center",
            fontsize=fontsize, fontweight=fontweight, color=TEXT_DARK)


def draw_arrow(ax, x1, y1, x2, y2, color, lw=0.8, style="->", connection="arc3,rad=0.0", alpha=1.0):
    arr = FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style,
        mutation_scale=8, linewidth=lw, color=color,
        connectionstyle=connection, alpha=alpha,
    )
    ax.add_patch(arr)


def fig1_bilayer():
    # Single column = 88 mm; height ≈ 88 mm tall to give layered structure room
    fig_w_mm, fig_h_mm = 165, 95
    fig = plt.figure(figsize=(fig_w_mm * MM_TO_INCH, fig_h_mm * MM_TO_INCH))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("auto")
    ax.axis("off")

    # ---- Layer titles ----
    ax.text(0.025, 0.92, "工程样机层  Engineering Layer",
            fontsize=9, fontweight="bold", color=ENG_EDGE, ha="left")
    ax.text(0.025, 0.32, "生物原型层  Biology Layer",
            fontsize=9, fontweight="bold", color=BIO_EDGE, ha="left")

    # ---- Engineering Layer (top) ----
    # Center node: FlappingWingVehicle
    fwmav_xy = (0.40, 0.72)
    draw_node(ax, *fwmav_xy, 0.18, 0.10,
              "FlappingWingVehicle\n(整机)",
              ENG_FILL, ENG_EDGE, fontsize=8.5, fontweight="bold")

    # Surrounding 6 satellite nodes
    sats = [
        ("Equipment\n(组件)",     (0.13, 0.83)),
        ("DriveMechanism\n(驱动)", (0.13, 0.62)),
        ("Application\n(任务)",    (0.67, 0.83)),
        ("Organization\n(单位)",   (0.67, 0.62)),
        ("Performance\n(性能)",    (0.13, 0.45)),
        ("Reference\n(文献)",      (0.67, 0.45)),
    ]
    for label, xy in sats:
        draw_node(ax, *xy, 0.12, 0.07, label, NEUTRAL_FILL, NEUTRAL_EDGE, fontsize=7)
        # arrow from satellite to FWMAV (no arrowhead, plain edge)
        draw_arrow(ax, xy[0], xy[1], fwmav_xy[0], fwmav_xy[1],
                   color=ENG_EDGE, lw=0.6, style="-", alpha=0.5)

    # ---- Biology Layer (bottom) ----
    bio_xs = [0.18, 0.32, 0.46, 0.60, 0.74]
    bio_labels = ["蜂鸟\nHummingbird", "苍蝇\nFly", "鸽子\nPigeon",
                  "海鸥\nSeagull", "蝙蝠\nBat"]
    bio_y = 0.14
    bio_xy = []
    for x, lbl in zip(bio_xs, bio_labels):
        draw_node(ax, x, bio_y, 0.10, 0.07, lbl, BIO_FILL, BIO_EDGE, fontsize=7)
        bio_xy.append((x, bio_y))

    ax.text(0.92, bio_y, "...",
            fontsize=10, color=BIO_EDGE, ha="center", va="center", fontweight="bold")

    # ---- MIMICS edges (4 colored curves from FWMAV down to organism examples) ----
    # Engineering side anchors (slightly offset along bottom edge of FWMAV)
    eng_y = fwmav_xy[1] - 0.05  # bottom edge of FWMAV node
    mimics_examples = [
        # (name, target_xy, label_tex, label_y_offset)
        ("aero",       bio_xy[0], "$s_\\mathrm{aero}{=}0.81$", 0.030),  # → Hummingbird
        ("scale",      bio_xy[1], "$s_\\mathrm{sca}{=}0.85$",  0.005),  # → Fly
        ("kinematics", bio_xy[2], "$s_\\mathrm{kin}{=}0.74$", -0.015),  # → Pigeon
        ("morphology", bio_xy[3], "$s_\\mathrm{mor}{=}0.69$", -0.040),  # → Seagull
    ]

    # Slightly different x anchors at top so edges don't overlap
    eng_xs = [0.34, 0.38, 0.42, 0.46]
    for (name, target, lbl, dy), eng_x in zip(mimics_examples, eng_xs):
        color = MIMICS_COLORS[name]
        draw_arrow(ax, eng_x, eng_y, target[0], target[1] + 0.04,
                   color=color, lw=1.1, style="->",
                   connection="arc3,rad=0.18", alpha=0.92)
        # midpoint label with staggered y offsets to avoid label collisions
        mid_x = 0.55 * eng_x + 0.45 * target[0]
        mid_y = 0.50 * eng_y + 0.50 * (target[1] + 0.04)
        ax.text(mid_x, mid_y + dy, lbl,
                fontsize=6.5, color=color, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.95))

    # ---- MIMICS legend (top-right inset) ----
    legend_x, legend_y = 0.86, 0.70
    ax.text(legend_x, legend_y + 0.12, "MIMICS 4 类映射",
            fontsize=7.5, fontweight="bold", color=TEXT_DARK, ha="left")
    legend_items = [
        ("aero",       "气动相似 (Re, St)"),
        ("kinematics", "运动学相似 (扑频/扑动模态)"),
        ("morphology", "形态相似 (翼形/展弦比)"),
        ("scale",      "尺度相似 (翼展/质量)"),
    ]
    for i, (key, desc) in enumerate(legend_items):
        y = legend_y + 0.08 - i * 0.035
        ax.plot([legend_x, legend_x + 0.025], [y, y],
                color=MIMICS_COLORS[key], lw=1.4, solid_capstyle="round")
        ax.text(legend_x + 0.030, y, desc, fontsize=6.5,
                ha="left", va="center", color=TEXT_DARK)

    # Layer separator (faint horizontal rule between layers)
    ax.plot([0.025, 0.825], [0.32, 0.32], color="#CCC", lw=0.4, ls=(0, (4, 4)))

    save_all(fig, "fig1_bilayer_ontology")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig. 2 — KG construction pipeline
# ---------------------------------------------------------------------------

def fig2_pipeline():
    fig_w_mm, fig_h_mm = 180, 65
    fig = plt.figure(figsize=(fig_w_mm * MM_TO_INCH, fig_h_mm * MM_TO_INCH))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    stages = [
        ("①\n预处理",             "PDF 解析\n段落分块"),
        ("②\n实体识别",          "DeepSeek-R1\n+ few-shot"),
        ("③\n关系抽取",          "LLM 关系\n分类"),
        ("④\n量纲归一",          "规则 + LLM\n单位转换"),
        ("⑤\n人工校验",          "10% 抽样\n专家复核"),
        ("⑥\nNeo4j 入库",        "图数据库\n+ provenance"),
    ]

    n = len(stages)
    margin_x = 0.025
    box_w = (1 - 2 * margin_x) / n * 0.86
    gap = (1 - 2 * margin_x - n * box_w) / (n - 1)
    box_h = 0.32
    box_y = 0.55

    centers = []
    for i, (title, sub) in enumerate(stages):
        x = margin_x + box_w / 2 + i * (box_w + gap)
        centers.append(x)
        # Main stage box
        draw_node(ax, x, box_y, box_w, box_h, title,
                  ENG_FILL, ENG_EDGE, fontsize=8.5, fontweight="bold")
        # Sub-text below the box
        ax.text(x, box_y - box_h / 2 - 0.10, sub,
                ha="center", va="center", fontsize=7, color=TEXT_DARK,
                linespacing=1.3)

    # Arrows between stages
    for i in range(n - 1):
        x1 = centers[i] + box_w / 2 + 0.005
        x2 = centers[i + 1] - box_w / 2 - 0.005
        draw_arrow(ax, x1, box_y, x2, box_y,
                   color=ENG_EDGE, lw=1.0, style="->")

    # Top-strip header
    ax.text(0.5, 0.96, "BioBridge-KG 构建流水线 — 6 阶段",
            ha="center", va="top", fontsize=9, fontweight="bold", color=TEXT_DARK)

    # Bottom-strip footer with examples
    ax.text(0.5, 0.05, "输入：PDF 论文 + 课题组样机台账 + 飞行生物学手册   →   输出：双层 KG (Neo4j, 612 节点 / 625 关系)",
            ha="center", va="bottom", fontsize=7, color="#555555", style="italic")

    save_all(fig, "fig2_kg_pipeline")
    plt.close(fig)


def main():
    print("Generating Fig. 1 — bilayer ontology ...")
    fig1_bilayer()
    print("Generating Fig. 2 — KG pipeline ...")
    fig2_pipeline()
    print("Done.")


if __name__ == "__main__":
    main()
