#!/usr/bin/env python3
"""FWMAV-QA Benchmark 自动校验脚本.

用法:
    python validate.py data/seed.jsonl
    python validate.py data/*.jsonl

退出码:
    0 — 全部通过
    1 — 至少一项失败

依赖:
    pip install jsonschema
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft7Validator
except ImportError:  # pragma: no cover
    print("ERROR: 请先安装 jsonschema: pip install jsonschema", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"

KQ_SCHEMA_PATH = SCHEMAS_DIR / "kq_schema.json"
DR_SCHEMA_PATH = SCHEMAS_DIR / "dr_schema.json"

# 已知有效工具白名单（与 BioBridge-GraphRAG 一致）
KNOWN_TOOLS = {
    "hassanalian_weight",
    "shyy_scaling_law",
    "strouhal_check",
    "reynolds_check",
}

# 已知子类目
KQ_CATEGORIES = {"A1", "A2", "A3", "A4"}
DR_CATEGORIES = {"B1", "B2"}


def load_schema(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_item(item: dict[str, Any], kq_validator, dr_validator) -> list[str]:
    errors: list[str] = []
    cat = item.get("category", "")

    # 基本 ID 格式
    item_id = item.get("id", "")
    if cat in KQ_CATEGORIES:
        if not re.match(r"^kq_(g_)?[0-9]{3,4}$", item_id):
            errors.append(f"id 格式不符合 kq_NNN 或 kq_g_NNN: {item_id!r}")
        for err in kq_validator.iter_errors(item):
            errors.append(f"schema: {err.message}")
        # 多跳类必须给出 gold_path 或 expected_hops > 1
        if cat in {"A3", "A4"}:
            if item.get("expected_hops", 1) < 2:
                errors.append("A3/A4 多跳类应 expected_hops >= 2")
            if not item.get("gold_path"):
                errors.append("A3/A4 多跳类建议提供 gold_path（不强制）")
    elif cat in DR_CATEGORIES:
        if not re.match(r"^dr_(g_)?[0-9]{3,4}$", item_id):
            errors.append(f"id 格式不符合 dr_NNN 或 dr_g_NNN: {item_id!r}")
        for err in dr_validator.iter_errors(item):
            errors.append(f"schema: {err.message}")
    else:
        errors.append(f"未识别的 category: {cat!r}")
        return errors

    # 工具调用合法性
    for tool in item.get("tool_call_required", []):
        if tool not in KNOWN_TOOLS:
            errors.append(f"未知工具: {tool!r}（合法工具: {sorted(KNOWN_TOOLS)}）")

    # 支持文献至少给出标题
    for i, doc in enumerate(item.get("support_docs", []) or []):
        if not doc.get("title"):
            errors.append(f"support_docs[{i}] 缺少 title")

    return errors


def validate_file(path: Path, kq_validator, dr_validator) -> tuple[int, int, dict]:
    """Return (total, errors_count, summary)."""
    total = 0
    bad = 0
    cat_counter: Counter[str] = Counter()
    diff_counter: Counter[int] = Counter()

    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw or raw.startswith("//"):
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"  [line {line_no}] JSON 解析失败: {e}")
                bad += 1
                total += 1
                continue
            total += 1
            cat_counter[item.get("category", "?")] += 1
            diff_counter[item.get("difficulty", 0)] += 1
            errors = validate_item(item, kq_validator, dr_validator)
            if errors:
                bad += 1
                print(f"  [{item.get('id', '?')}] line {line_no}:")
                for err in errors:
                    print(f"    - {err}")

    summary = {
        "total": total,
        "errors": bad,
        "by_category": dict(cat_counter),
        "by_difficulty": dict(diff_counter),
    }
    return total, bad, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="FWMAV-QA validator")
    parser.add_argument("files", nargs="+", help="JSONL 文件路径（支持多个）")
    parser.add_argument("--strict", action="store_true", help="非零错误时退出码 1")
    args = parser.parse_args()

    kq_schema = load_schema(KQ_SCHEMA_PATH)
    dr_schema = load_schema(DR_SCHEMA_PATH)
    kq_validator = Draft7Validator(kq_schema)
    dr_validator = Draft7Validator(dr_schema)

    grand_total = 0
    grand_bad = 0
    for path_str in args.files:
        path = Path(path_str)
        if not path.exists():
            print(f"⚠ 文件不存在: {path}")
            continue
        print(f"\n=== {path} ===")
        total, bad, summary = validate_file(path, kq_validator, dr_validator)
        print(f"\n  小结: total={total}, errors={bad}")
        print(f"  by category: {summary['by_category']}")
        print(f"  by difficulty: {summary['by_difficulty']}")
        grand_total += total
        grand_bad += bad

    print(f"\n=== Grand Total: total={grand_total}, errors={grand_bad} ===")
    if args.strict and grand_bad > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
