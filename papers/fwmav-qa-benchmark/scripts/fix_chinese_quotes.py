#!/usr/bin/env python3
"""自动修复 JSONL 文件中"中文上下文裸 ASCII 双引号"问题.

可独立运行: python3 fix_chinese_quotes.py path/to/file.jsonl
也可作为 module 导入: from fix_chinese_quotes import fix_file
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path


def fix_text(text: str) -> tuple[str, int]:
    """修复中文上下文里的 ASCII 双引号. 返回 (修复后文本, 修复次数).

    关键安全约束: 只在出现在 JSON 字符串"值"内部 (key:"...{要修}...") 的地方修,
    不能跨越 JSON 数组分隔符 ","; 否则 ["A","B"] 这种合法数组会被破坏成
    ["A","B"] (中间分隔符变中文) 导致语义错误.

    实现思路: 逐行处理, 用 JSON 解析器找到失败位置, 仅在失败附近做最小修复.
    """
    n_fix = 0
    out_lines = []

    for raw in text.splitlines():
        if not raw.strip():
            out_lines.append(raw)
            continue

        # 已经合法 -> 不动
        try:
            json.loads(raw)
            out_lines.append(raw)
            continue
        except json.JSONDecodeError:
            pass

        # 尝试逐步修复: 反复找解析错误位置, 把错误位置附近"中文+ASCII"+任意+ASCII"+中文" 改为中文引号
        cur = raw
        max_iter = 10
        for _ in range(max_iter):
            try:
                json.loads(cur)
                break
            except json.JSONDecodeError as e:
                col = e.colno - 1  # 0-based
                # 在 col 附近 (前后 200 字符) 搜中文+ASCII"...ASCII"+中文 模式
                window_lo = max(0, col - 200)
                window_hi = min(len(cur), col + 200)
                window = cur[window_lo:window_hi]
                # 注意: 只匹配两个 " 之间是非"非分隔符的内容 (不能跨过 "," 或 ":")
                # 即: 中文 + " + (除 " 和 , 和 : 之外的任意) + " + 中文/中文标点
                pattern = re.compile(
                    r'([一-鿿])"([^",:]+?)"([一-鿿，。、；：！？（）【】—])'
                )
                new_window, n = pattern.subn(r'\1“\2”\3', window, count=1)
                if n == 0:
                    break
                cur = cur[:window_lo] + new_window + cur[window_hi:]
                n_fix += 1

        out_lines.append(cur)

    return '\n'.join(out_lines) + ('\n' if text.endswith('\n') else ''), n_fix


def fix_file(path: Path) -> tuple[int, int]:
    """修复一个文件. 返回 (修复次数, 剩余 JSON 错误数)."""
    text = path.read_text(encoding='utf-8')
    fixed_text, n_fix = fix_text(text)
    if n_fix > 0:
        path.write_text(fixed_text, encoding='utf-8')

    # 校验
    errors = 0
    for i, line in enumerate(fixed_text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            errors += 1
            print(f"  Line {i}: col {e.colno}, ...{line[max(0,e.colno-40):e.colno+40]}...")
    return n_fix, errors


def main():
    if len(sys.argv) < 2:
        print("用法: python3 fix_chinese_quotes.py file.jsonl [file2.jsonl ...]")
        return 1
    rc = 0
    for fp in sys.argv[1:]:
        path = Path(fp)
        if not path.exists():
            print(f"⚠ 不存在: {path}")
            continue
        print(f"\n=== {path} ===")
        n_fix, errors = fix_file(path)
        print(f"  自动修复 {n_fix} 处中文引号; 剩余 JSON 错误 {errors}")
        if errors > 0:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
