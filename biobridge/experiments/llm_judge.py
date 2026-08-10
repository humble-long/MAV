"""LLM-as-Judge 评测指标 — 统一 A2/A3/A4 三类题的评分。

使用方式:
    from biobridge.experiments.llm_judge import evaluate_a_metrics
    result = evaluate_a_metrics(predictions_dict, gold_items)
"""

from __future__ import annotations
import json
import os
from openai import OpenAI


JUDGE_SYSTEM_PROMPT = (
    "你是仿生扑翼飞行器（FWMAV）领域的专家评审。"
    "你需要对比「金答案」和「系统答案」，按照题目类型给出评分。"
    "严格按 JSON 格式输出，不要输出其他文字。"
)


def _judge_prompt(question: str, gold_answer: str, pred_answer: str, category: str) -> str:
    """构造三类题通用的评判 prompt，区别仅在 rubric。"""

    if category == "A2":
        rubric = (
            "A2 题是单实体属性查询（如「云鸮的扑频是多少？」），"
            "重点看系统答案给出的具体数值是否与金答案一致。\n\n"
            "JSON 格式要求：\n"
            "{{\n"
            '  "gold_triples": ['
            '["实体名", "属性名", "数值"], ...],\n'
            '  "pred_triples": ['
            '["实体名", "属性名", "数值"], ...],\n'
            '  "matched_count": N,\n'
            '  "accuracy": 0.0-1.0\n'
            "}}\n"
            "- gold_triples: 从金答案中抽取所有 (实体, 属性, 数值) 三元组\n"
            "- pred_triples: 从系统答案中抽取所有 (实体, 属性, 数值) 三元组\n"
            "- matched_count: pred_triples 与 gold_triples 匹配的数量（属性名和数值都一致才算匹配）\n"
            "- accuracy: matched_count / gold_triples 总数"
        )
    elif category == "A3":
        rubric = (
            "A3 题是多实体对比（如「DelFly Nimble 和 Nano Hummingbird 在尺寸、重量上有什么差异？」），"
            "重点看系统答案是否覆盖了所有对比实体、所有对比维度，以及每个维度上的数值是否正确。\n\n"
            "JSON 格式要求：\n"
            "{{\n"
            '  "entity_covered": true/false,\n'
            '  "dimensions_covered": true/false,\n'
            '  "dimension_scores": ['
            '{{"dimension": "翼展", "correct": true/false}}, ...],'
            '  "completeness": 0.0-1.0\n'
            "}}\n"
            "- entity_covered: 系统答案是否提到了金答案中所有需要对比的实体\n"
            "- dimensions_covered: 系统答案是否覆盖了金答案中所有对比维度\n"
            "- dimension_scores: 逐个维度的正确性\n"
            "- completeness: (entity_covered?0.33:0 + dimensions_covered?0.33:0 + dim_correct_mean*0.34) 的三项加权平均"
        )
    else:  # A4
        rubric = (
            "A4 题是因果推理（如「参考蜂鸟做 30min 续航可行吗？」），"
            "重点看系统答案的核心结论是否与金答案一致，以及是否引用了具体的实体/样机作为推理证据。\n\n"
            "JSON 格式要求：\n"
            "{{\n"
            '  "conclusion_correct": true/false,\n'
            '  "evidence_entities_matched": N,\n'
            '  "evidence_entities_total": N,\n'
            '  "validity": 0.0-1.0\n'
            "}}\n"
            "- conclusion_correct: 系统答案的核心结论（可行/不可行，推荐哪个）是否与金答案一致\n"
            "- evidence_entities_matched: 系统答案中引用的证据实体的数量\n"
            "- evidence_entities_total: 金答案中引用的证据实体的数量\n"
            "- validity: 0.5 * (conclusion_correct?1:0) + 0.5 * min(evidence_entities_matched/evidence_entities_total, 1.0)"
        )

    return (
        f"【题目类型】{category}\n\n"
        f"【问题】{question}\n\n"
        f"【金答案】{gold_answer}\n\n"
        f"【系统答案】{pred_answer}\n\n"
        f"【评分要求】{rubric}"
    )


def _get_judge_client():
    """用 DeepSeek-R1 作为评判模型（与被测系统不同的 LLM，避免自我偏好）。"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    base_url = "https://api.deepseek.com/v1"
    model = "deepseek-chat"

    if not api_key:
        # 回退到 qproxy
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://qproxy.gtimg.com/v1")
        model = os.environ.get("OPENAI_MODEL", "claude-sonnet-4-6")

    return OpenAI(api_key=api_key, base_url=base_url), model


def judge_one(
    question: str,
    gold_answer: str,
    pred_answer: str,
    category: str,
    client: OpenAI = None,
    model: str = None,
) -> dict:
    """对单道题打分，返回 rubric 对应的 dict。"""
    if client is None:
        client, model = _get_judge_client()

    prompt = _judge_prompt(question, gold_answer, pred_answer, category)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=int(os.environ.get("MAX_OUTPUT_TOKENS", "30000")),
    )

    try:
        raw = resp.choices[0].message.content or ""
        raw = raw.strip()

        # 优先：从 raw 中提取 ```json ... ``` 代码块（处理 Claude 把思维链放在 JSON 前的情况）
        import re
        m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if m:
            return json.loads(m.group(1))

        # 兼容：raw 整体本身就是 JSON
        return json.loads(raw)
    except (json.JSONDecodeError, AttributeError) as e:
        finish_reason = getattr(resp.choices[0], "finish_reason", "?")
        # 错误日志：写到 /tmp/judge_errors.log
        try:
            with open("/tmp/judge_errors.log", "a", encoding="utf-8") as ef:
                ef.write(f"━━━ category={category} finish={finish_reason} ━━━\n")
                ef.write(f"err: {type(e).__name__}: {e}\n")
                ef.write(f"raw: {raw[:1500]}\n\n")
        except Exception:
            pass
        return {"error": "judge parse failed", "finish_reason": finish_reason, "raw": raw[:200]}


def evaluate_a_metrics(
    predictions: dict[str, str],
    gold_items: list[dict],
    verbose: bool = True,
) -> dict:
    """对 A 类题（A2+A3+A4）跑 LLM-as-Judge 评测。

    Returns:
        {
            "overall": { "a2_accuracy_mean": ..., "a3_completeness_mean": ..., "a4_validity_mean": ... },
            "by_category": { "A2": {...}, "A3": {...}, "A4": {...} },
            "per_item": [...]
        }
    """
    client, model = _get_judge_client()
    if verbose:
        print(f"[LLM Judge] 使用模型: {model}")

    per_item = []
    for item in gold_items:
        qid = item["id"]
        cat = item.get("category", "?")
        question = item.get("question", "")
        gold = item.get("gold_answer", "")
        pred = predictions.get(qid, "") or ""

        if not gold or not pred:
            # gold_answer 或 pred 为空时给默认值
            default = {"accuracy": 0.0, "completeness": 0.0, "validity": 0.0}
            if cat == "A2":
                score = default["accuracy"]
            elif cat == "A3":
                score = default["completeness"]
            else:
                score = default["validity"]

            per_item.append({
                "id": qid,
                "category": cat,
                "score": score,
                "judge_result": {"error": "empty gold or pred"},
            })
            continue

        jr = judge_one(question, gold, pred, cat, client=client, model=model)

        # 提取该类的核心分数
        if cat == "A2":
            score = jr.get("accuracy", 0.0)
        elif cat == "A3":
            score = jr.get("completeness", 0.0)
        else:
            score = jr.get("validity", 0.0)

        per_item.append({
            "id": qid,
            "category": cat,
            "score": score,
            "judge_result": jr,
        })

        if verbose:
            print(f"  [{cat}] {qid} → score={score:.2f}")

    # 聚合
    by_cat = {}
    for d in per_item:
        by_cat.setdefault(d["category"], []).append(d)

    cat_means = {}
    for c, items in by_cat.items():
        scores = [d["score"] for d in items]
        cat_means[c] = {
            "n": len(items),
            "mean": sum(scores) / len(scores) if scores else 0.0,
            "min": min(scores) if scores else 0.0,
            "max": max(scores) if scores else 0.0,
        }

    overall = {
        "n_total": len(per_item),
        "a2_accuracy_mean": cat_means.get("A2", {}).get("mean", 0.0),
        "a3_completeness_mean": cat_means.get("A3", {}).get("mean", 0.0),
        "a4_validity_mean": cat_means.get("A4", {}).get("mean", 0.0),
    }

    return {
        "overall": overall,
        "by_category": cat_means,
        "per_item": per_item,
    }
