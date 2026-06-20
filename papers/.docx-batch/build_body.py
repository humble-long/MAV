"""把 papers/sections/section{1..6}*.md 的正文内容 (跳过笔记部分) 转换为 docx batch script.

策略：
1. 解析 markdown，识别 H1（# 1 引言）/ H2（## 2.1 设计动机）/ H3（### 3.3.1 算法描述）/正文段落
2. H1 用 heading 1 风格，H2 用 heading 2，H3 用 heading 3
3. 段首句的 markdown 加粗（**...**）保留为 docx bold 但简化
4. 在每个 H1 前加分页或空段
5. 表/公式/算法占位段，用注释式留住

把所有内容序列化为 batch JSON，每条命令都是 add to /body --after <prev_paraId>。
"""

from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path

PAPER_DOCX = Path("/Users/humble/studyProject/MAV/papers/biobridge-graphrag-paper.docx")
SECTIONS_DIR = Path("/Users/humble/studyProject/MAV/papers/sections")

# 我们要插入的 sections，按顺序
SECTION_FILES = [
    "section1-introduction.md",
    "section2-kg.md",
    "section3-path-reasoning.md",
    "section4-tensor.md",
    "section5-experiments.md",
    "section6-conclusion.md",
]


def parse_md(path: Path) -> list[dict]:
    """解析 markdown 为 [{type, text, level}] 列表.

    跳过：> 引用块 / --- 分隔线 / 后续的"写作笔记"小节
    """
    text = path.read_text(encoding="utf-8")
    out = []
    in_notes = False
    in_code = False
    in_table = False
    table_rows: list[str] = []

    for line in text.split("\n"):
        # 跳过 markdown frontmatter 注释
        if line.startswith("> ") and not in_notes:
            continue
        # 写作笔记开始
        if re.match(r"^##\s*写作笔记", line):
            in_notes = True
        if in_notes:
            continue
        # 跳过 hr
        if line.strip() == "---":
            continue

        # 代码块
        if line.startswith("```"):
            in_code = not in_code
            if not in_code:
                # 代码块结束，把累积代码作为 algo 段
                pass
            continue
        if in_code:
            # algorithm 1 或代码——简化处理：作为 monospace 段
            if line.strip():
                out.append({"type": "code", "text": line})
            continue

        # 表格
        if "|" in line and line.strip().startswith("|"):
            in_table = True
            table_rows.append(line.strip())
            continue
        else:
            if in_table:
                # 表结束
                out.append({"type": "table", "rows": list(table_rows)})
                table_rows = []
                in_table = False

        # 标题
        m = re.match(r"^(#+)\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            txt = m.group(2).strip()
            out.append({"type": "heading", "level": level, "text": txt})
            continue

        # 普通段
        if line.strip():
            out.append({"type": "para", "text": line.strip()})

    if in_table:
        out.append({"type": "table", "rows": list(table_rows)})

    return out


def normalize_text(s: str) -> str:
    """处理 inline markdown：去 ** 粗体（保留文字）、去反引号、去 <sup>...<sup> 简化。"""
    # 加粗：**text** -> text
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    # 斜体：*text* -> text
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", s)
    # 行内代码：`text` -> text
    s = re.sub(r"`([^`]+)`", r"\1", s)
    # <sup>[Ref]</sup> -> [Ref]
    s = re.sub(r"<sup>(.+?)</sup>", r"\1", s)
    # 数学：$...$ -> 简化保留
    # 留 $...$ 在文本里，docx 看不到 LaTeX 语法可读
    return s


def md_block_to_batch_commands(blocks: list[dict], prev_para_id: str) -> list[dict]:
    """把 md 块列表转 batch commands.

    所有 add 都用 --after 链式，先生成的段落必须有 paraId。
    然而 batch 不直接支持 --after 字段——我们需要拼接到正确位置。

    简化：用 --index 不行，因为 add 命令在 batch 中没有 index/after 参数明显文档。
    回退方案：单独调用 add，每次拿 paraId。

    实际上 dump 显示的 add 是 {parent, type, props} 没有 after——
    但文档说 add 命令本身支持 --after。

    在 batch 命令中，按 dump 看应该是 {command, parent, type, props}——
    没有 after 等位置参数，会都加到 parent 末尾。

    所以策略：用单独调用 add，每次记录返回的新 paraId。
    """
    commands = []

    for blk in blocks:
        t = blk["type"]
        if t == "heading":
            lvl = blk["level"]
            txt = normalize_text(blk["text"])
            if lvl == 1:
                # § 一级标题
                commands.append({
                    "command": "add", "parent": "/body", "type": "p",
                    "props": {
                        "text": txt,
                        "style": "Heading1",
                        "spaceBefore": "12pt", "spaceAfter": "6pt",
                    }
                })
            elif lvl == 2:
                commands.append({
                    "command": "add", "parent": "/body", "type": "p",
                    "props": {
                        "text": txt,
                        "style": "Heading2",
                        "spaceBefore": "9pt", "spaceAfter": "5pt",
                    }
                })
            elif lvl == 3:
                commands.append({
                    "command": "add", "parent": "/body", "type": "p",
                    "props": {
                        "text": txt,
                        "style": "Heading3",
                        "spaceBefore": "6pt", "spaceAfter": "3pt",
                    }
                })
        elif t == "para":
            commands.append({
                "command": "add", "parent": "/body", "type": "p",
                "props": {
                    "text": normalize_text(blk["text"]),
                    "firstLineIndent": "21.1pt",
                    "lineSpacing": "15pt",
                }
            })
        elif t == "code":
            # algorithm/伪代码：用等宽字体 + 不缩进
            commands.append({
                "command": "add", "parent": "/body", "type": "p",
                "props": {
                    "text": blk["text"],
                    "font.ascii": "Consolas",
                    "font.eastAsia": "等线",
                    "size": "9pt",
                    "lineSpacing": "13pt",
                }
            })
        elif t == "table":
            # 简化：把表格作为一段文字（| 分隔）暂占位，后续单独处理
            for row in blk["rows"]:
                commands.append({
                    "command": "add", "parent": "/body", "type": "p",
                    "props": {
                        "text": row,
                        "size": "9pt",
                        "font.ascii": "Times New Roman",
                    }
                })

    return commands


def main():
    all_commands = []
    for sec_file in SECTION_FILES:
        path = SECTIONS_DIR / sec_file
        if not path.exists():
            print(f"WARN: {path} missing")
            continue
        blocks = parse_md(path)
        cmds = md_block_to_batch_commands(blocks, prev_para_id="78D7ACC3")
        all_commands.extend(cmds)
        print(f"[{sec_file}] parsed {len(blocks)} blocks -> {len(cmds)} commands")

    out_path = Path("/Users/humble/studyProject/MAV/papers/.docx-batch/03-body-content.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_commands, f, ensure_ascii=False, indent=2)
    print(f"\nTotal commands: {len(all_commands)}")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
