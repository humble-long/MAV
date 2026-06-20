"""把 9 张图（PNG）+ 中英文图题 嵌入 docx 对应位置.

在每张图相应正文段后插入：
1. 一个空段 → 容纳图片
2. 中文图题段（用 中文图题 样式 styleId=36）
3. 英文图题段（用 英文图题 样式 styleId=41）
"""

from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

PAPER_DOCX = "/Users/humble/studyProject/MAV/papers/biobridge-graphrag-paper.docx"
FIG_DIR = Path("/Users/humble/studyProject/MAV/papers/figures")

# 9 张图 + 插入位置 + 中英图题
FIGURES = [
    {
        "fig_num": 1,
        "src": str(FIG_DIR / "fig1-bilayer-ontology.drawio.png"),
        "after": "/body/p[@paraId=7FC56C94]",  # MIMICS 段（更靠近 §2.1.2 末）
        "zh_caption": "图 1  BioBridge 双层本体结构示意图",
        "en_caption": "Fig.1  Bilayer ontology of BioBridge knowledge graph",
        "width_cm": 8.0,
    },
    {
        "fig_num": 2,
        "src": str(FIG_DIR / "fig2-kg-pipeline.drawio.png"),
        "after": "/body/p[@paraId=7FC56CA2]",  # 6 阶段段
        "zh_caption": "图 2  BioBridge-KG 构建流水线",
        "en_caption": "Fig.2  Construction pipeline of BioBridge knowledge graph",
        "width_cm": 16.0,  # 双栏宽
    },
    {
        "fig_num": 3,
        "src": str(FIG_DIR / "fig3-path-reasoning-flow.drawio.png"),
        "after": "/body/p[@paraId=7FC56CDC]",  # 推理范式段
        "zh_caption": "图 3  尺度律工具增强的图路径推理流程",
        "en_caption": "Fig.3  Scaling-law tool-augmented graph path reasoning flow",
        "width_cm": 16.0,
    },
    {
        "fig_num": 4,
        "src": str(FIG_DIR / "fig4-application-modes.drawio.png"),
        "after": "/body/p[@paraId=7FC56D3A]",  # 两类工作段
        "zh_caption": "图 4  知识查询模式与推荐精排模式对比",
        "en_caption": "Fig.4  Knowledge query mode versus recommendation rerank mode",
        "width_cm": 16.0,
    },
    {
        "fig_num": 5,
        "src": str(FIG_DIR / "fig5-tensor-decomposition.drawio.png"),
        "after": "/body/p[@paraId=7FC56D4E]",  # 张量结构段
        "zh_caption": "图 5  3 阶张量结构与 CP 分解示意",
        "en_caption": "Fig.5  3-mode tensor structure and CP decomposition schematic",
        "width_cm": 16.0,
    },
    {
        "fig_num": 6,
        "src": str(FIG_DIR / "fig6-recall-rerank-pipeline.drawio.png"),
        "after": "/body/p[@paraId=7FC56D70]",  # 两阶段架构段
        "zh_caption": "图 6  粗筛—精排两阶段方案推荐范式",
        "en_caption": "Fig.6  Recall-rerank two-stage paradigm for design recommendation",
        "width_cm": 16.0,
    },
    {
        "fig_num": 7,
        "src": str(FIG_DIR / "fig7-r-sensitivity.png"),
        "after": "/body/p[@paraId=7FC56E16]",  # R 灵敏性论述段
        "zh_caption": "图 7  CP 分解秩 R 对重构误差与检索一致性的影响",
        "en_caption": "Fig.7  Effect of CP rank R on reconstruction error and retrieval consistency",
        "width_cm": 8.0,
    },
    {
        "fig_num": 8,
        "src": str(FIG_DIR / "fig8-alpha-sensitivity.png"),
        "after": "/body/p[@paraId=7FC56E1A]",  # α 灵敏性论述段
        "zh_caption": "图 8  混合相似度 α 对检索一致性的影响（R = 12 固定）",
        "en_caption": "Fig.8  Effect of hybrid-similarity alpha on retrieval consistency (R = 12 fixed)",
        "width_cm": 8.0,
    },
    {
        "fig_num": 9,
        "src": str(FIG_DIR / "fig9-case-study-traces.drawio.png"),
        "after": None,  # 后面找——案例 3 末段
        "zh_caption": "图 9  三个案例的推理路径可视化",
        "en_caption": "Fig.9  Reasoning traces of the three case studies",
        "width_cm": 16.0,
    },
]


def find_anchor_for_fig9(text_dump: str) -> str | None:
    """找到 §5.7 末段或案例 3 末段的 paraId."""
    # 找一段含"参考海鸥 / 鸽子原型"的段（案例 3 末）
    m = re.search(r'\[/body/p\[@paraId=([0-9A-F]+)\]\] [^\n]*替代建议[^\n]*', text_dump)
    if m:
        return f"/body/p[@paraId={m.group(1)}]"
    # 备选：找含"3 个案例"的段
    m = re.search(r'\[/body/p\[@paraId=([0-9A-F]+)\]\] [^\n]*纯 LLM 直答此类问题', text_dump)
    if m:
        return f"/body/p[@paraId={m.group(1)}]"
    return None


def find_paraid(text_dump: str, after_id: str) -> bool:
    """验证 after_id 段确实存在."""
    return f"paraId={after_id.split('=')[-1].rstrip(']')}" in text_dump


def add_picture(parent_para: str, src: str, width_cm: float) -> str | None:
    """在指定段内 add picture，返回 picture path."""
    cmd = ["officecli", "add", PAPER_DOCX, parent_para, "--type", "picture",
           "--prop", f"src={src}", "--prop", f"width={width_cm}cm",
           "--json"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    try:
        d = json.loads(r.stdout)
        return d.get("data") or d.get("message", "")
    except json.JSONDecodeError:
        return r.stdout


def add_para_after(after_path: str, text: str, style: str = None) -> str | None:
    """在 after_path 后插入新段，返回新段 paraId 路径."""
    cmd = ["officecli", "add", PAPER_DOCX, "/body", "--type", "paragraph",
           "--after", after_path, "--prop", f"text={text}",
           "--json"]
    if style:
        cmd += ["--prop", f"style={style}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    try:
        d = json.loads(r.stdout)
        msg = d.get("data") or d.get("message", "")
    except json.JSONDecodeError:
        msg = r.stdout
    m = re.search(r"paraId=([0-9A-F]+)", msg)
    if m:
        return f"/body/p[@paraId={m.group(1)}]"
    return None


def main():
    # 取一次 text dump 找 fig9 anchor
    r = subprocess.run(["officecli", "view", PAPER_DOCX, "text"],
                       capture_output=True, text=True, timeout=30)
    text_dump = r.stdout

    fig9_anchor = find_anchor_for_fig9(text_dump)
    if fig9_anchor:
        FIGURES[8]["after"] = fig9_anchor
        print(f"Fig.9 anchor: {fig9_anchor}")

    # Open resident
    print("Opening resident...")
    subprocess.run(["officecli", "open", PAPER_DOCX], capture_output=True, timeout=30)

    try:
        for fig in FIGURES:
            num = fig["fig_num"]
            src = fig["src"]
            after = fig["after"]
            if not after:
                print(f"  Fig.{num}: SKIP (no anchor)")
                continue
            if not Path(src).exists():
                print(f"  Fig.{num}: SKIP (source missing: {src})")
                continue

            print(f"\nFig.{num}: anchor={after}")
            # 1. 创建一个新空段
            empty_para = add_para_after(after, " ")
            if not empty_para:
                print(f"  ✗ FAILED to create empty para")
                continue
            print(f"  empty_para = {empty_para}")

            # 2. 在新空段中插入图片
            pic_result = add_picture(empty_para, src, fig["width_cm"])
            print(f"  picture inserted: {pic_result[:80] if pic_result else 'FAIL'}")

            # 3. 中文图题
            zh_cap = add_para_after(empty_para, fig["zh_caption"], style="36")
            print(f"  zh caption: {zh_cap}")

            # 4. 英文图题
            if zh_cap:
                en_cap = add_para_after(zh_cap, fig["en_caption"], style="41")
                print(f"  en caption: {en_cap}")

    finally:
        print("\nSaving...")
        subprocess.run(["officecli", "save", PAPER_DOCX], capture_output=True, timeout=60)
        subprocess.run(["officecli", "close", PAPER_DOCX], capture_output=True, timeout=30)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
