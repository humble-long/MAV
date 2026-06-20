"""执行 batch JSON 中的 add 命令，每次用前一次返回的 paraId 作为 --after.

resident process 加快 docx 反复打开关闭的开销。
"""

from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path

PAPER_DOCX = "/Users/humble/studyProject/MAV/papers/biobridge-graphrag-paper.docx"
BATCH_FILE = "/Users/humble/studyProject/MAV/papers/.docx-batch/03-body-content.json"

# 起始 anchor: 中图分类号
INITIAL_ANCHOR = "/body/p[@paraId=78D7ACC3]"


def run_add(parent: str, props: dict, after: str) -> str | None:
    """运行 add 命令，返回新段的 paraId."""
    cmd = ["officecli", "add", PAPER_DOCX, parent, "--type", "paragraph",
           "--after", after, "--json"]
    for k, v in props.items():
        cmd += ["--prop", f"{k}={v}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return None
    out = r.stdout
    try:
        d = json.loads(out)
        msg = d.get("data") or d.get("message", "")
    except json.JSONDecodeError:
        msg = out
    m = re.search(r"paraId=([0-9A-F]+)", msg)
    if m:
        return f"/body/p[@paraId={m.group(1)}]"
    return None


def main():
    with open(BATCH_FILE, encoding="utf-8") as f:
        commands = json.load(f)

    # 启动 resident
    print("Opening resident...")
    subprocess.run(["officecli", "open", PAPER_DOCX], capture_output=True, timeout=30)

    anchor = INITIAL_ANCHOR
    success = 0
    failed = 0
    try:
        for i, cmd in enumerate(commands, 1):
            if cmd.get("command") != "add":
                print(f"[{i}/{len(commands)}] skip non-add: {cmd}")
                continue
            parent = cmd.get("parent", "/body")
            props = cmd.get("props", {})
            new_path = run_add(parent, props, anchor)
            if new_path:
                anchor = new_path
                success += 1
                if i % 25 == 0:
                    print(f"  [{i}/{len(commands)}] anchor={anchor}")
            else:
                failed += 1
                print(f"  [{i}/{len(commands)}] FAILED: {props.get('text', '')[:60]}")
    finally:
        # 保存 + 关闭 resident
        print("\nSaving...")
        subprocess.run(["officecli", "save", PAPER_DOCX], capture_output=True, timeout=60)
        subprocess.run(["officecli", "close", PAPER_DOCX], capture_output=True, timeout=30)

    print(f"\n=== Done: {success} success, {failed} failed ===")
    print(f"Final anchor: {anchor}")


if __name__ == "__main__":
    main()
