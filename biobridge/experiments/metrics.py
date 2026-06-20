"""FWMAV-QA 评测指标实现.

实现以下指标：
- EM (Exact Match)        — 文本归一化后精确匹配
- F1 (token-level)        — 中文字符级 F1
- Hit@k (entity-level)    — 答案是否包含金答案的任一实体
- Faithfulness (lite)     — 答案中是否每个数字/实体都在 gold 中提及（轻量代理）
- NDCG@k (推荐子集)       — 预留接口（需要相关度等级标注）

使用方式:
    from biobridge.experiments.metrics import evaluate_qa
    metrics = evaluate_qa(predictions, gold_items)

predictions: dict {qid: answer_text}
gold_items: list of dict (FWMAV-QA jsonl item)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

import jieba


# ============================================================
# 文本归一化
# ============================================================

def normalize_text(text: str) -> str:
    """统一全/半角，去除标点与多余空白，转小写."""
    if text is None:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    # 移除中英文标点
    text = re.sub(r"[\s\.,;:!?\-—–'\"`(){}\[\]<>《》（）【】，。；：！？、…“”‘’]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def char_tokens(text: str) -> list[str]:
    """中文字符级分词（每个字一个 token，英文按词）。"""
    text = normalize_text(text)
    tokens = []
    buf = []
    for ch in text:
        if "一" <= ch <= "鿿":  # CJK 字符
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(ch)
        elif ch.isalnum():
            buf.append(ch)
        else:
            if buf:
                tokens.append("".join(buf))
                buf = []
    if buf:
        tokens.append("".join(buf))
    return tokens


def jieba_tokens(text: str) -> list[str]:
    """jieba 中文分词."""
    text = normalize_text(text)
    return [t for t in jieba.lcut(text) if t.strip()]


# ============================================================
# EM / F1
# ============================================================

def exact_match(pred: str, gold: str) -> float:
    return float(normalize_text(pred) == normalize_text(gold))


def token_f1(pred: str, gold: str, tokenizer=char_tokens) -> float:
    """字符级或词级 F1."""
    p_toks = tokenizer(pred)
    g_toks = tokenizer(gold)
    if not p_toks or not g_toks:
        return 0.0
    common = {}
    for t in p_toks:
        common[t] = min(p_toks.count(t), g_toks.count(t))
    n_same = sum(common.values())
    if n_same == 0:
        return 0.0
    precision = n_same / len(p_toks)
    recall = n_same / len(g_toks)
    return 2 * precision * recall / (precision + recall)


# ============================================================
# Entity-level Hit@k
# ============================================================

def entity_hit_at_k(
    pred: str,
    gold_entities: list[str],
    k: int = 5,
) -> float:
    """检查预测答案中是否包含至少 k 分之一的金答案实体.

    Hit@1: 至少包含 1 个金实体
    Hit@5: 至少包含 5 个或全部金实体（取 min）
    Hit@10: 同上但 k=10

    实体匹配采用 substring 匹配（normalize 后）。
    """
    if not gold_entities:
        return 0.0
    pred_norm = normalize_text(pred)
    matched = sum(1 for e in gold_entities if normalize_text(e) and normalize_text(e) in pred_norm)
    target = min(k, len(gold_entities))
    return float(matched >= target)


def entity_recall(pred: str, gold_entities: list[str]) -> float:
    """Recall on entities — 命中比例."""
    if not gold_entities:
        return 0.0
    pred_norm = normalize_text(pred)
    matched = sum(1 for e in gold_entities if normalize_text(e) and normalize_text(e) in pred_norm)
    return matched / len(gold_entities)


# ============================================================
# Faithfulness (lite)
# ============================================================

def faithfulness_lite(pred: str, gold: str) -> float:
    """轻量 faithfulness 代理：预测答案中的关键数字/百分号/单位，是否都在 gold 中提及.

    抽取 pred 中所有 \\d+\\.?\\d* 后跟可能单位的"数值短语"，看 gold 中是否含同样数值。
    给出 [0, 1] 比例。
    """
    pred_norm = normalize_text(pred)
    gold_norm = normalize_text(gold)
    # 抽取数值
    nums_pred = set(re.findall(r"\d+(?:\.\d+)?", pred_norm))
    if not nums_pred:
        return 1.0  # 无数字则视为可信
    nums_gold = set(re.findall(r"\d+(?:\.\d+)?", gold_norm))
    matched = sum(1 for n in nums_pred if n in nums_gold)
    return matched / len(nums_pred)


# ============================================================
# 综合 evaluate
# ============================================================

def evaluate_qa(predictions: dict[str, str], gold_items: list[dict]) -> dict:
    """
    Args:
        predictions: {qid: answer_text}
        gold_items: list of FWMAV-QA dict items

    Returns:
        dict of aggregated + per-category metrics
    """
    per_item = []
    for it in gold_items:
        qid = it["id"]
        pred = predictions.get(qid, "")
        gold = it.get("gold_answer", "")
        gold_ents = it.get("gold_entities", [])

        per_item.append({
            "id": qid,
            "category": it.get("category", "?"),
            "difficulty": it.get("difficulty", "?"),
            "pred_len": len(pred),
            "em": exact_match(pred, gold),
            "f1_char": token_f1(pred, gold, tokenizer=char_tokens),
            "f1_jieba": token_f1(pred, gold, tokenizer=jieba_tokens),
            "hit_at_1": entity_hit_at_k(pred, gold_ents, k=1),
            "hit_at_5": entity_hit_at_k(pred, gold_ents, k=5),
            "entity_recall": entity_recall(pred, gold_ents),
            "faithfulness_lite": faithfulness_lite(pred, gold),
        })

    # 聚合
    n = len(per_item) if per_item else 1
    overall = {
        "n_items": len(per_item),
        "em": sum(d["em"] for d in per_item) / n,
        "f1_char": sum(d["f1_char"] for d in per_item) / n,
        "f1_jieba": sum(d["f1_jieba"] for d in per_item) / n,
        "hit_at_1": sum(d["hit_at_1"] for d in per_item) / n,
        "hit_at_5": sum(d["hit_at_5"] for d in per_item) / n,
        "entity_recall": sum(d["entity_recall"] for d in per_item) / n,
        "faithfulness_lite": sum(d["faithfulness_lite"] for d in per_item) / n,
    }

    # 按 category 聚合
    by_cat = {}
    for d in per_item:
        c = d["category"]
        by_cat.setdefault(c, []).append(d)
    cat_metrics = {}
    for c, items in by_cat.items():
        m = len(items)
        cat_metrics[c] = {
            "n": m,
            "em": sum(d["em"] for d in items) / m,
            "f1_char": sum(d["f1_char"] for d in items) / m,
            "hit_at_1": sum(d["hit_at_1"] for d in items) / m,
            "hit_at_5": sum(d["hit_at_5"] for d in items) / m,
            "entity_recall": sum(d["entity_recall"] for d in items) / m,
            "faithfulness_lite": sum(d["faithfulness_lite"] for d in items) / m,
        }

    return {
        "overall": overall,
        "by_category": cat_metrics,
        "per_item": per_item,
    }


# ============================================================
# Smoke test
# ============================================================

if __name__ == "__main__":
    # smoke test
    test_cases = [
        # exact match
        ("Strouhal 数定义为 fA/U", "Strouhal 数定义为 fA/U", "EM expected 1.0"),
        # partial match
        ("Strouhal 数是无量纲数", "Strouhal 数定义为 fA/U", "F1 expected partial"),
        # entity hit
        ("DelFly Nimble 的扑频是 17 Hz", ["DelFly Nimble", "17 Hz"], "Hit@1 expected 1.0"),
    ]
    print("EM:", exact_match(test_cases[0][0], test_cases[0][1]))
    print("F1 (char):", token_f1(test_cases[1][0], test_cases[1][1], char_tokens))
    print("F1 (jieba):", token_f1(test_cases[1][0], test_cases[1][1], jieba_tokens))
    print("Hit@1:", entity_hit_at_k(test_cases[2][0], test_cases[2][1], k=1))
    print("Faithfulness (lite):", faithfulness_lite("扑频 17 Hz", "扑频范围 17-25 Hz"))
