"""B 类题自动标注：relevance (0-3) + hard_constraints_satisfied (dict).

为每条 gold_recommendation 生成两个新字段：
  - relevance        : 0/1/2/3，按候选与任务约束的匹配程度
  - hard_constraints_satisfied : {字段名: bool}，逐项硬约束满足情况

输入: papers/fwmav-qa-benchmark/data/fwmav_qa_v2_final.jsonl
输出: papers/fwmav-qa-benchmark/data/fwmav_qa_v2_b_annotated.jsonl
      （A 类题原样保留，B 类题在 gold_recommendations 每条加 2 字段）

LLM 调用：复用 llm_judge._get_judge_client（qproxy + deepseek-v4-pro-official）。
"""

from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from biobridge.experiments.llm_judge import _get_judge_client


# ──────────────────────────────────────────────────────────────────
# 1. 硬/软约束识别规则
# ──────────────────────────────────────────────────────────────────

# 数值上下限：以 _max / _min 结尾，或字段名中含 max/min 关键字
NUMERIC_HARD_PATTERNS = ("_max_", "_min_", "_max", "_min")

# 明确语义字段：值非默认时即视为硬约束
SEMANTIC_HARD_FIELDS = {"drive_mechanism", "capability", "drive_feature", "wing_count"}

# 软约束：用于 relevance 解释，不计入硬约束集合
SOFT_FIELDS = {"biological_prototype", "mission_type", "endurance_unit"}

# bool 字段：仅当值为 true 时算硬约束
BOOL_HARD_WHEN_TRUE = {"can_hover", "needs_camera", "is_tailless", "untethered"}


def is_numeric_constraint(field: str) -> bool:
    return any(p in field for p in NUMERIC_HARD_PATTERNS) or field == "endurance_min"


def extract_hard_constraints(task_constraints: dict) -> dict:
    """从 task_constraints 抽出硬约束子集（按用户给定规则）。"""
    hard = {}
    for k, v in task_constraints.items():
        if k in SOFT_FIELDS:
            continue
        if is_numeric_constraint(k):
            hard[k] = v
        elif k in SEMANTIC_HARD_FIELDS and v not in (None, "", False):
            hard[k] = v
        elif k in BOOL_HARD_WHEN_TRUE and v is True:
            hard[k] = v
    return hard


# ──────────────────────────────────────────────────────────────────
# 2. LLM Prompt
# ──────────────────────────────────────────────────────────────────

ANNOTATE_SYSTEM = (
    "你是仿生扑翼飞行器（FWMAV）领域的专家标注员。"
    "你需要根据已标注的 reasoning 文本，对每个候选样机给出 relevance 评分和硬约束逐项满足情况。"
    "严格按 JSON 格式输出，不要输出 JSON 以外的任何文字。"
)


RELEVANCE_RUBRIC = """
relevance 取值（4 档）：
  3 - 满足全部硬约束，可直接推荐。reasoning 中常见："满足全部硬约束""完美匹配""唯一同时满足"
  2 - 满足核心硬约束，但缺少软约束或需小改装。reasoning 中常见："需加装""需优化""缺少视觉系统""续航略短但可扩展"
  1 - 违反一个硬约束、或仅作为宽泛参考。reasoning 中常见："略超硬约束""不达标""仅可参考""约束外但接近"
  0 - 明显不满足任务或与任务无关。reasoning 中常见："不满足关键约束""与原型不匹配""无相关证据"

constraint_status 取值：
  "fully_satisfied"        - 全部硬约束满足
  "requires_modification"  - 需要加装/改装才能满足
  "boundary_violated"      - 违反 1 个硬约束（边界越界、单项不达标）
  "infeasible"             - 不满足关键硬约束 / 与任务无关
""".strip()


def build_annotate_prompt(question: str, task_constraints: dict, hard_constraints: dict,
                          rec: dict) -> str:
    return f"""【题目】{question}

【任务约束（task_constraints）】
{json.dumps(task_constraints, ensure_ascii=False, indent=2)}

【其中硬约束（hard_constraints）】
{json.dumps(hard_constraints, ensure_ascii=False, indent=2)}

【候选样机】{rec.get("vehicle", "")}
【标注员给的 reasoning】{rec.get("reasoning", "")}
【原始 rank】{rec.get("rank", "?")}
【原始 match_score（仅供参考，不要直接采用）】{rec.get("match_score", "?")}

【任务】
请基于 reasoning + 任务约束，输出该候选样机的 relevance、constraint_status、以及硬约束逐项满足情况。

{RELEVANCE_RUBRIC}

【输出 JSON 格式】
{{
  "relevance": 0/1/2/3,
  "constraint_status": "fully_satisfied" | "requires_modification" | "boundary_violated" | "infeasible",
  "hard_constraints_satisfied": {{ <硬约束字段名>: true/false, ... }},
  "rationale": "≤80 字简短解释，引用 reasoning 中的关键词"
}}

注意：
- hard_constraints_satisfied 的键必须与上面【硬约束】的键完全一致
- 数值硬约束严格判断（"略超"也算 false）
- 如果 reasoning 没明确说某个硬约束，按合理推断给 true（既然标注员已认可此候选）"""


# ──────────────────────────────────────────────────────────────────
# 3. LLM 调用 + JSON 解析
# ──────────────────────────────────────────────────────────────────

def _strip_json_md(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:]) if len(lines) > 1 else raw
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].strip()
    return raw


def annotate_one(question: str, task_constraints: dict, hard_constraints: dict,
                 rec: dict, client, model: str) -> dict:
    prompt = build_annotate_prompt(question, task_constraints, hard_constraints, rec)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": ANNOTATE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=1500,
        )
        raw = resp.choices[0].message.content or ""
    except Exception as e:
        return {"error": "api_error", "raw": f"{type(e).__name__}: {str(e)[:200]}"}

    try:
        return json.loads(_strip_json_md(raw))
    except json.JSONDecodeError as e:
        return {"error": "parse_failed", "raw": raw, "json_error": str(e)}


# ──────────────────────────────────────────────────────────────────
# 4. 主循环
# ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",
                        default=str(ROOT / "papers" / "fwmav-qa-benchmark" / "data" / "fwmav_qa_v2_final.jsonl"))
    parser.add_argument("--out",
                        default=str(ROOT / "papers" / "fwmav-qa-benchmark" / "data" / "fwmav_qa_v2_b_annotated.jsonl"))
    parser.add_argument("--n", type=int, default=9999, help="处理 B 类题数上限（调试用）")
    parser.add_argument("--ids", type=str, default="", help="逗号分隔的 id 列表，仅处理这些题（调试用）")
    args = parser.parse_args()

    client, model = _get_judge_client()
    print(f"[Annotate] LLM model: {model}")

    in_path = Path(args.data)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    items = []
    with open(in_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    target_ids = set(s.strip() for s in args.ids.split(",") if s.strip())
    b_items = [it for it in items if it.get("category") in ("B1", "B2")]
    if target_ids:
        b_items = [it for it in b_items if it["id"] in target_ids]
    b_items = b_items[: args.n]

    print(f"[Annotate] B 类题待处理: {len(b_items)}")

    # 统计将处理的 gold_recommendations 总数
    total_recs = sum(len(it.get("gold_recommendations", [])) for it in b_items)
    print(f"[Annotate] 共需标注 {total_recs} 条 gold_recommendations")

    # 复制全部 items（A 类原样写出，B 类即将更新）
    annotated_lookup = {}  # id -> 修改后的 item
    err_log_path = Path("/tmp/annotate_errors.log")
    err_log = open(err_log_path, "w", encoding="utf-8")
    print(f"[Annotate] 错误日志: {err_log_path}")

    n_done = 0
    n_err = 0
    t0 = time.time()
    for idx, it in enumerate(b_items, 1):
        qid = it["id"]
        question = it["question"]
        tc = it.get("task_constraints", {})
        hard = extract_hard_constraints(tc)

        new_recs = []
        for rec in it.get("gold_recommendations", []):
            anno = annotate_one(question, tc, hard, rec, client, model)
            if "error" in anno:
                n_err += 1
                err_log.write(f"━━━ {qid} / {rec.get('vehicle')} ━━━\n")
                err_log.write(f"error: {anno.get('error')}\n")
                if anno.get("json_error"):
                    err_log.write(f"json_error: {anno['json_error']}\n")
                err_log.write(f"raw_output:\n{anno.get('raw','')}\n\n")
                err_log.flush()
                # fallback: 给一个保守值，以免漏数据
                anno = {
                    "relevance": 2,
                    "constraint_status": "requires_modification",
                    "hard_constraints_satisfied": {k: True for k in hard},
                    "rationale": "fallback (LLM parse failed)",
                }
            merged = dict(rec)
            merged.update({
                "relevance": anno.get("relevance"),
                "constraint_status": anno.get("constraint_status"),
                "hard_constraints_satisfied": anno.get("hard_constraints_satisfied", {}),
                "rationale_auto": anno.get("rationale", ""),
            })
            new_recs.append(merged)
            n_done += 1

        new_it = dict(it)
        new_it["gold_recommendations"] = new_recs
        new_it["hard_constraints"] = hard  # 顶层也存一份方便评测
        annotated_lookup[qid] = new_it

        elapsed = time.time() - t0
        print(f"  [{idx:3}/{len(b_items)}] {qid:14s} {it.get('category')} "
              f"recs={len(new_recs)} done={n_done} err={n_err} t={elapsed:.0f}s")

    err_log.close()

    # 写出: A 类原样 + B 类用 annotated_lookup 替换
    with open(out_path, "w", encoding="utf-8") as f:
        for it in items:
            out_it = annotated_lookup.get(it["id"], it)
            f.write(json.dumps(out_it, ensure_ascii=False) + "\n")

    print(f"\n=== 完成 ===")
    print(f"  B 类题: {len(b_items)}")
    print(f"  标注 gold_recommendations: {n_done}  (parse 失败 fallback: {n_err})")
    print(f"  输出: {out_path}")
    print(f"  耗时: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
