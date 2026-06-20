"""把 docx 中的 markdown 表格 (一行一段，含 |) 转为 docx 原生表格.

策略:
1. 抓取所有 paraId / text
2. 识别连续的 markdown 表格行（| 开头，以 |---| 分隔 header）
3. 对每个表 group：
   a. 在 group 之前的段落（前面那段）后插入 table
   b. 删除 group 中的所有 markdown 段
"""

from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

PAPER_DOCX = "/Users/humble/studyProject/MAV/papers/biobridge-graphrag-paper.docx"


def run_cli(*args, timeout=30):
    r = subprocess.run(["officecli", *args, "--json"],
                       capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"raw": r.stdout, "stderr": r.stderr}


def get_all_paragraphs():
    """通过 view 拿全部 paraId + text."""
    r = subprocess.run(["officecli", "view", PAPER_DOCX, "text"],
                       capture_output=True, text=True, timeout=30)
    paras = []
    for line in r.stdout.split("\n"):
        m = re.match(r"^\[/body/p\[@paraId=([0-9A-F]+)\]\]\s?(.*)$", line)
        if m:
            paras.append({"paraId": m.group(1), "text": m.group(2)})
    return paras


def is_md_table_row(text: str) -> bool:
    """判断一行是否 markdown 表格行."""
    t = text.strip()
    return t.startswith("|") and t.endswith("|") and t.count("|") >= 2


def is_md_table_separator(text: str) -> bool:
    """识别 |---|---| 分隔线."""
    t = text.strip()
    if not t.startswith("|"):
        return False
    inner = t.strip("|").replace("|", " ").strip()
    parts = inner.split()
    return all(p in ("---", "-", ":---", "---:", ":---:") or set(p) <= set("-:") for p in parts) and parts


def parse_md_row(text: str) -> list[str]:
    """把 | a | b | c | 拆为 ['a', 'b', 'c']."""
    t = text.strip()
    parts = t.split("|")
    # 去掉首尾空字符串
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [p.strip() for p in parts]


def cleanup_cell(cell: str) -> str:
    """清洗 markdown cell：去 ** 粗体、去 <sup>...</sup>、去内嵌反引号."""
    cell = re.sub(r"\*\*(.+?)\*\*", r"\1", cell)
    cell = re.sub(r"<sup>(.+?)</sup>", r"\1", cell)
    cell = re.sub(r"`([^`]+)`", r"\1", cell)
    return cell


def find_table_groups(paras: list[dict]) -> list[dict]:
    """识别 markdown 表格 group: 返回 [{start_idx, end_idx, rows}].

    一个表格连续段：N 行均为 | ... |，且其中至少一行是分隔线。
    """
    groups = []
    i = 0
    n = len(paras)
    while i < n:
        if not is_md_table_row(paras[i]["text"]):
            i += 1
            continue
        start = i
        # 找连续的 md 表格行
        j = i
        while j < n and is_md_table_row(paras[j]["text"]):
            j += 1
        # j 是第一个非表格行
        # 跳过空行：偶尔有空段插在表中
        end = j - 1
        # 检查是否含分隔线
        rows_text = [paras[k]["text"] for k in range(start, end + 1)]
        if any(is_md_table_separator(t) for t in rows_text):
            # 解析 cells
            row_cells = []
            for t in rows_text:
                if is_md_table_separator(t):
                    continue
                row_cells.append([cleanup_cell(c) for c in parse_md_row(t)])
            if row_cells:
                groups.append({
                    "start_idx": start,
                    "end_idx": end,
                    "para_ids": [paras[k]["paraId"] for k in range(start, end + 1)],
                    "rows": row_cells,
                })
        i = j
    return groups


def rows_to_csv_data(rows: list[list[str]]) -> str:
    """把 [[h1, h2], [r1c1, r1c2]] 转为 'h1,h2;r1c1,r1c2' (escape 逗号 / 分号)."""
    out_rows = []
    for row in rows:
        cells = []
        for c in row:
            # 替换内部逗号 / 分号 / 反引号
            c = c.replace(",", "，").replace(";", "；")
            cells.append(c)
        out_rows.append(",".join(cells))
    return ";".join(out_rows)


def main():
    paras = get_all_paragraphs()
    print(f"Total paragraphs: {len(paras)}")

    groups = find_table_groups(paras)
    print(f"Found {len(groups)} markdown table groups")

    if not groups:
        return

    print("\nOpening resident...")
    subprocess.run(["officecli", "open", PAPER_DOCX], capture_output=True, timeout=30)

    try:
        # 注意：每次插入新表 + 删段后，paraId 不变（officecli 用 paraId 而非 index）
        # 所以我们倒序处理 (从最后一个 group 处理回来)，避免位置移动后影响
        for gi, group in enumerate(reversed(groups), 1):
            n_rows = len(group["rows"])
            n_cols = len(group["rows"][0]) if group["rows"] else 0
            print(f"\nGroup {gi}/{len(groups)}: {n_rows} rows × {n_cols} cols")
            print(f"  Header: {group['rows'][0]}")

            # 1. 在 group 第一行的前一段后插入 table
            anchor_idx = group["start_idx"] - 1
            if anchor_idx < 0:
                print("  ERROR: no anchor (start_idx=0)")
                continue
            anchor_para_id = paras[anchor_idx]["paraId"]
            anchor_path = f"/body/p[@paraId={anchor_para_id}]"
            print(f"  Anchor: {anchor_path}")

            csv_data = rows_to_csv_data(group["rows"])
            # 加 table
            cmd = ["officecli", "add", PAPER_DOCX, "/body", "--type", "table",
                   "--after", anchor_path,
                   "--prop", f"data={csv_data}",
                   "--prop", "borderTop=single;6;000000",
                   "--prop", "borderBottom=single;6;000000",
                   "--prop", "borderInsideH=single;4;000000",
                   "--json"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            print(f"  Add table: {r.stdout[:120].strip()}")

            # 2. 删除原 markdown 段
            removed = 0
            for pid in group["para_ids"]:
                r = subprocess.run(["officecli", "remove", PAPER_DOCX,
                                    f"/body/p[@paraId={pid}]"],
                                   capture_output=True, text=True, timeout=15)
                if "Removed" in r.stdout or "removed" in r.stdout.lower():
                    removed += 1
            print(f"  Removed {removed}/{len(group['para_ids'])} markdown rows")

    finally:
        print("\nSaving...")
        subprocess.run(["officecli", "save", PAPER_DOCX], capture_output=True, timeout=60)
        subprocess.run(["officecli", "close", PAPER_DOCX], capture_output=True, timeout=30)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
