"""重新插入 3 个公式（修复之前 \\text 残留 'ext' 的问题）.

策略：
1. 删除现有 3 个 OMML 公式段（paraId: 7FC5714B / 7FC5714E / 7FC57151）
2. 在原 anchor 段（7FC56D4C / D58 / D6A）之后重新插入公式（用更稳健的 LaTeX simplification）
"""

from __future__ import annotations
import json
import subprocess

PAPER_DOCX = "/Users/humble/studyProject/MAV/papers/biobridge-graphrag-paper.docx"

# (旧 OMML paraId, anchor paraId, simplified LaTeX, mode)
EQUATIONS = [
    {
        "old_omml": "7FC5714B",
        "anchor": "7FC56D4C",
        # 张量空间定义 X ∈ R^(N1 x N2 x N3)
        "latex": "X \\in R^{N_1 \\times N_2 \\times N_3}, \\quad N_1 = 39, N_2 = 14, N_3 = 5",
    },
    {
        "old_omml": "7FC5714E",
        "anchor": "7FC56D58",
        # CP 分解 X ≈ sum_{r=1}^R lambda_r u_r ⊗ v_r ⊗ w_r
        "latex": "X \\approx \\sum_{r=1}^{R} \\lambda_r u_r \\otimes v_r \\otimes w_r",
    },
    {
        "old_omml": "7FC57151",
        "anchor": "7FC56D6A",
        # 混合相似度 sim(i,q) = (1-α) cos_raw(i,q) + α cos_embed(i,q)
        "latex": "sim(i, q) = (1 - \\alpha) cos_{raw}(i, q) + \\alpha cos_{embed}(i, q)",
    },
]


def main():
    print("Opening resident...")
    subprocess.run(["officecli", "open", PAPER_DOCX], capture_output=True, timeout=30)

    try:
        for eq in EQUATIONS:
            old_omml = eq["old_omml"]
            anchor = eq["anchor"]
            latex = eq["latex"]
            print(f"\n=== Fixing equation at anchor={anchor} ===")

            # 1. 删除旧 OMML 段
            r = subprocess.run([
                "officecli", "remove", PAPER_DOCX,
                f"/body/p[@paraId={old_omml}]"
            ], capture_output=True, text=True, timeout=15)
            if "Removed" in r.stdout:
                print(f"  ✓ removed old OMML {old_omml}")
            else:
                print(f"  ✗ old removal: {r.stdout[:100]}")

            # 2. 重新插入新公式
            r = subprocess.run([
                "officecli", "add", PAPER_DOCX,
                f"/body/p[@paraId={anchor}]",
                "--type", "equation",
                "--prop", "mode=display",
                "--prop", f"formula={latex}",
                "--json",
            ], capture_output=True, text=True, timeout=15)
            if "success" in r.stdout:
                print(f"  ✓ inserted new equation")
                print(f"    {latex}")
            else:
                print(f"  ✗ insertion failed: {r.stdout[:200]}")

    finally:
        print("\nSaving...")
        subprocess.run(["officecli", "save", PAPER_DOCX], capture_output=True, timeout=60)
        subprocess.run(["officecli", "close", PAPER_DOCX], capture_output=True, timeout=30)


if __name__ == "__main__":
    main()
