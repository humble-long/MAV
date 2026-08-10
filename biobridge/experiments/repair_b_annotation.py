"""修复 fwmav_qa_v2_b_annotated.jsonl 中 fallback 项.

从 /tmp/annotate_errors.log 读取所有 LLM 解析失败项的原始输出，
用正则降级提取 relevance / constraint_status / hard_constraints_satisfied，
更新到 jsonl 中替换 fallback 占位值（rationale_auto = 'fallback (LLM parse failed)'）。

原因：claude-sonnet-4-6 在 rationale 字段中嵌入未转义的中文双引号，
导致 JSON 解析失败，但其他三个核心字段格式都是正常的。
"""

from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

ERROR_LOG = Path("/tmp/annotate_errors.log")
ANNO_PATH = ROOT / "papers" / "fwmav-qa-benchmark" / "data" / "fwmav_qa_v2_b_annotated.jsonl"


# ──────────────────────────────────────────────────────────────────
# 1. 解析错误日志，按 (qid, vehicle) 索引每条 raw_output
# ──────────────────────────────────────────────────────────────────

def parse_error_log(path: Path) -> dict[tuple[str, str], str]:
    """返回 {(qid, vehicle): raw_output} 字典."""
    text = path.read_text(encoding="utf-8")
    # 每个 block: ━━━ qid / vehicle ━━━ \n error: ... \n (json_error)? \n raw_output:\n {RAW}
    pattern = re.compile(
        r'━━━\s*(?P<qid>\S+)\s*/\s*(?P<veh>.+?)\s*━━━\s*\n'
        r'error:[^\n]*\n'
        r'(?:json_error:[^\n]*\n)?'
        r'raw_output:\s*\n'
        r'(?P<raw>.*?)'
        r'(?=\n━━━|\Z)',
        re.DOTALL,
    )
    result = {}
    for m in pattern.finditer(text):
        qid = m.group("qid").strip()
        veh = m.group("veh").strip()
        raw = m.group("raw").strip()
        result[(qid, veh)] = raw
    return result


# ──────────────────────────────────────────────────────────────────
# 2. 正则降级提取核心字段
# ──────────────────────────────────────────────────────────────────

VALID_STATUS = {"fully_satisfied", "requires_modification", "boundary_violated", "infeasible"}

def extract_fields(raw: str) -> dict | None:
    """从损坏 JSON 文本里提取 relevance / constraint_status / hard_constraints_satisfied.

    Returns None if cannot extract relevance.
    """
    out = {}

    # relevance: 整数 0-3
    m = re.search(r'"relevance"\s*:\s*(\d)', raw)
    if not m:
        return None
    out["relevance"] = int(m.group(1))

    # constraint_status: 引号内字符串
    m = re.search(r'"constraint_status"\s*:\s*"([^"]+)"', raw)
    out["constraint_status"] = m.group(1) if m and m.group(1) in VALID_STATUS else None

    # hard_constraints_satisfied: 在 { ... } 之间的 key:bool 对
    m = re.search(r'"hard_constraints_satisfied"\s*:\s*\{(.*?)\}', raw, re.DOTALL)
    hcs = {}
    if m:
        body = m.group(1)
        # 匹配 "key": true|false
        for km in re.finditer(r'"([^"]+)"\s*:\s*(true|false)', body):
            hcs[km.group(1)] = (km.group(2) == "true")
    out["hard_constraints_satisfied"] = hcs

    # rationale: 提取从 "rationale": " 开始到末尾 (} 之前) 的内容，截断 + 转义引号
    m = re.search(r'"rationale"\s*:\s*"(.*?)"\s*\}', raw, re.DOTALL)
    if m:
        # 把内嵌的双引号替换成单引号，截断到 200 字
        rat = m.group(1).replace('"', "'")[:200]
        out["rationale"] = rat
    else:
        out["rationale"] = "(extracted from broken JSON)"

    return out


# ──────────────────────────────────────────────────────────────────
# 3. 修复 jsonl
# ──────────────────────────────────────────────────────────────────

def main():
    print(f"读取错误日志: {ERROR_LOG}")
    err_map = parse_error_log(ERROR_LOG)
    print(f"  共 {len(err_map)} 条 (qid, vehicle) 的 raw_output")

    # 解析这些 raw 的有效字段
    extracted = {}  # (qid, vehicle) -> dict
    extract_fail = []
    for (qid, veh), raw in err_map.items():
        fields = extract_fields(raw)
        if fields is None:
            extract_fail.append((qid, veh))
        else:
            extracted[(qid, veh)] = fields

    print(f"  正则提取成功: {len(extracted)}")
    print(f"  正则提取失败: {len(extract_fail)}")
    if extract_fail:
        for qid, veh in extract_fail[:5]:
            print(f"    - {qid} / {veh}")

    # 读取 jsonl
    print(f"\n读取标注文件: {ANNO_PATH}")
    items = []
    with open(ANNO_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    # 遍历替换 fallback 项
    n_repaired = 0
    n_already_ok = 0
    n_still_fallback = 0
    for it in items:
        if it.get("category") not in ("B1", "B2"):
            continue
        qid = it["id"]
        for rec in it.get("gold_recommendations", []):
            veh = rec.get("vehicle")
            is_fallback = rec.get("rationale_auto", "").startswith("fallback")
            if not is_fallback:
                n_already_ok += 1
                continue
            key = (qid, veh)
            if key in extracted:
                fix = extracted[key]
                rec["relevance"] = fix["relevance"]
                rec["constraint_status"] = fix["constraint_status"]
                rec["hard_constraints_satisfied"] = fix["hard_constraints_satisfied"]
                rec["rationale_auto"] = fix["rationale"]
                n_repaired += 1
            else:
                n_still_fallback += 1

    # 写回
    with open(ANNO_PATH, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    print(f"\n=== 修复完成 ===")
    print(f"  修复成功: {n_repaired}")
    print(f"  原本无问题: {n_already_ok}")
    print(f"  仍为 fallback: {n_still_fallback}")
    print(f"  写回: {ANNO_PATH}")


if __name__ == "__main__":
    main()
