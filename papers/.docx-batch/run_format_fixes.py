"""修复 docx 格式：
1. 一级/二级/三级标题应用航空学报字号 + 字体（黑体）
2. 把 markdown 行内/独立公式 (含 $...$ 或 markdown 代码) 转为 OMML 原生公式
3. 分栏问题——查模板的 sectPr，确认是否包含 cols=2

策略：
- 标题识别：以 `^\d+\s+` 或 `^\d+\.\d+\s+` 或 `^\d+\.\d+\.\d+\s+` 开头的段
- 公式识别：含 $...$ 或 \\mathcal{...} 等
"""

from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path

PAPER_DOCX = "/Users/humble/studyProject/MAV/papers/biobridge-graphrag-paper.docx"


def get_all_paragraphs():
    r = subprocess.run(["officecli", "view", PAPER_DOCX, "text"],
                       capture_output=True, text=True, timeout=30)
    paras = []
    for line in r.stdout.split("\n"):
        m = re.match(r"^\[/body/p\[@paraId=([0-9A-F]+)\]\]\s?(.*)$", line)
        if m:
            paras.append({"paraId": m.group(1), "text": m.group(2)})
    return paras


def classify_heading(text: str) -> int | None:
    """返回标题级别 (1, 2, 3) 或 None.

    "1 引言" → 1
    "2.1 双层本体设计" → 2
    "2.1.1 设计动机" → 3
    """
    t = text.strip()
    if re.match(r"^\d+\.\d+\.\d+\s", t):
        return 3
    if re.match(r"^\d+\.\d+\s", t):
        return 2
    if re.match(r"^\d+\s", t) and len(t) < 50:
        return 1
    return None


def fix_headings(paras):
    """重新设置每个标题段的样式属性."""
    print("\nFixing heading styles...")

    # 标题样式字典（航空学报标准）
    h_styles = {
        1: {  # 一级标题: 1 引言
            "size": "12pt",
            "font.eastAsia": "黑体",
            "bold": "true",
            "spaceBefore": "12pt",
            "spaceAfter": "6pt",
            "lineSpacing": "18pt",
            "lineRule": "exact",
            "firstLineIndent": "0pt",
            "align": "left",
        },
        2: {  # 二级: 2.1 双层本体设计
            "size": "10.5pt",
            "font.eastAsia": "黑体",
            "bold": "true",
            "spaceBefore": "9pt",
            "spaceAfter": "3pt",
            "lineSpacing": "15pt",
            "lineRule": "exact",
            "firstLineIndent": "0pt",
            "align": "left",
        },
        3: {  # 三级: 2.1.1 设计动机
            "size": "10pt",
            "font.eastAsia": "黑体",
            "bold": "true",
            "spaceBefore": "6pt",
            "spaceAfter": "0pt",
            "lineSpacing": "15pt",
            "lineRule": "exact",
            "firstLineIndent": "0pt",
            "align": "left",
        },
    }

    n_updated = 0
    for p in paras:
        lvl = classify_heading(p["text"])
        if lvl is None:
            continue
        path = f"/body/p[@paraId={p['paraId']}]"
        cmd = ["officecli", "set", PAPER_DOCX, path]
        for k, v in h_styles[lvl].items():
            cmd += ["--prop", f"{k}={v}"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if "Updated" in r.stdout:
            n_updated += 1
        else:
            print(f"  WARN failed for {path}: {p['text'][:40]}: {r.stdout[:100]}")
    print(f"  Updated {n_updated} heading paragraphs")


# 公式识别 + 替换
EQUATION_PATTERNS = [
    # CP 分解
    (r"\$\$\\mathcal\{X\}\s*\\approx\s*\\sum_\{r=1\}\^\{R\}\s*\\lambda_r\\,\s*\\mathbf\{u\}_r\s*\\otimes\s*\\mathbf\{v\}_r\s*\\otimes\s*\\mathbf\{w\}_r\$\$",
     r"\mathcal{X} \approx \sum_{r=1}^{R} \lambda_r \mathbf{u}_r \otimes \mathbf{v}_r \otimes \mathbf{w}_r",
     "display"),
    # 查询投影
    (r"\$\$q_r = \\frac\{\\langle \\mathbf\{Q\}_\{\\text\{norm\}\} \\odot \\mathbf\{M\},\\ \\mathbf\{v\}_r \\mathbf\{w\}_r\^\\top \\odot \\mathbf\{M\}\\rangle_F\}\{\\\|\\mathbf\{v\}_r \\mathbf\{w\}_r\^\\top \\odot \\mathbf\{M\}\\\|_F\^2 \+ \\varepsilon\}\$\$",
     r"q_r = \frac{\langle \mathbf{Q}_{\text{norm}} \odot \mathbf{M}, \mathbf{v}_r \mathbf{w}_r^\top \odot \mathbf{M} \rangle_F}{\|\mathbf{v}_r \mathbf{w}_r^\top \odot \mathbf{M}\|_F^2 + \varepsilon}",
     "display"),
    # 混合相似度
    (r"\$\$\\text\{sim\}\(i, q\) = \(1 - \\alpha\)\\,\s*\\text\{cos\}_\{\\text\{raw\}\}\(i, q\) \+ \\alpha\\,\s*\\text\{cos\}_\{\\text\{embed\}\}\(i, q\)\$\$",
     r"\text{sim}(i, q) = (1 - \alpha) \text{cos}_{\text{raw}}(i, q) + \alpha \text{cos}_{\text{embed}}(i, q)",
     "display"),
]


def find_equation_paras(paras):
    """找出含独立公式（以 $$ 开头/结尾）的段."""
    eq_paras = []
    for p in paras:
        t = p["text"].strip()
        if t.startswith("$$") and t.endswith("$$"):
            eq_paras.append(p)
    return eq_paras


def latex_simplify(s: str) -> str:
    """简化 LaTeX 让 OMML parser 能解析."""
    # 去掉 $$ 包裹
    s = s.strip()
    if s.startswith("$$") and s.endswith("$$"):
        s = s[2:-2].strip()
    # 替换某些 LaTeX-only 命令 (FormulaParser 可能不识别)
    s = s.replace("\\mathcal", "")  # 把 \mathcal{X} 简化为 X
    s = s.replace("\\mathbf", "\\mathit")  # 替换 \mathbf
    s = s.replace("\\,", " ")  # 小空格
    s = s.replace("\\langle", "<")  # 简化角括号
    s = s.replace("\\rangle", ">")
    s = s.replace("\\odot", "*")
    s = s.replace("\\otimes", "*")
    s = s.replace("\\text{norm}", "norm")
    s = s.replace("\\text{raw}", "raw")
    s = s.replace("\\text{embed}", "embed")
    s = s.replace("\\text{sim}", "sim")
    s = s.replace("\\text{cos}", "cos")
    s = s.replace("\\varepsilon", "ε")
    s = s.replace("\\lambda", "λ")
    s = s.replace("\\alpha", "α")
    s = s.replace("\\sum", "Σ")
    s = s.replace("\\approx", "≈")
    s = s.replace("\\top", "T")
    s = s.replace("\\|", "‖")
    s = s.replace("\\\\", "")
    s = s.replace("_F", "_F")
    return s


def fix_equations(paras):
    """把含 $$...$$ 的段替换为 OMML 公式."""
    print("\nFixing equations...")
    eq_paras = find_equation_paras(paras)
    print(f"  Found {len(eq_paras)} equation paragraphs")

    for p in eq_paras:
        path = f"/body/p[@paraId={p['paraId']}]"
        latex = latex_simplify(p["text"])
        print(f"\n  {path}")
        print(f"    LaTeX: {latex[:80]}")

        # 1. 清空段文字
        subprocess.run(["officecli", "set", PAPER_DOCX, path,
                        "--prop", "text="], capture_output=True, text=True, timeout=15)

        # 2. 在该段内插入 inline equation
        cmd = ["officecli", "add", PAPER_DOCX, path, "--type", "equation",
               "--prop", "mode=display",
               "--prop", f"formula={latex}",
               "--json"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if "success" in r.stdout:
            print(f"    ✓ inserted")
        else:
            print(f"    ✗ FAIL: {r.stdout[:120]}")


def main():
    paras = get_all_paragraphs()
    print(f"Total paragraphs: {len(paras)}")

    print("\nOpening resident...")
    subprocess.run(["officecli", "open", PAPER_DOCX], capture_output=True, timeout=30)

    try:
        fix_headings(paras)
        # 重新拿 paras（标题修复后段未变）
        # paras = get_all_paragraphs()
        fix_equations(paras)

    finally:
        print("\nSaving...")
        subprocess.run(["officecli", "save", PAPER_DOCX], capture_output=True, timeout=60)
        subprocess.run(["officecli", "close", PAPER_DOCX], capture_output=True, timeout=30)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
