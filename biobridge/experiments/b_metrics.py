"""B 类（B1+B2）评测指标：NDCG@3 + CSR@3.

评测来源：fwmav_qa_v2_b_annotated.jsonl（已用 LLM 自动标注 relevance + hard_constraints_satisfied）

指标定义
─────────
NDCG@3 (binary relevance):
  - rel_i = 1 if predicted[i] ∈ gold_recommendations else 0
  - DCG  = Σ rel_i / log2(i+2)            （i 从 0 开始）
  - IDCG = Σ 1   / log2(i+2)  for i=0..min(|gold|,3)-1
  - NDCG = DCG / IDCG

CSR@3 (Constraint Satisfaction Rate, 仅对有硬约束的题目计算):
  - 单候选 v 的 CSR_i：
      若 v ∈ gold: 用其 hard_constraints_satisfied 计算 (满足数 / 总数)
      若 v ∉ gold: CSR_i = 0（保守判定）
      若位置缺失（pred 不足 3 个）: CSR_i = 0
  - CSR_q@3 = (CSR_1 + CSR_2 + CSR_3) / 3
  - CSR@3   = 所有有硬约束的题目的 CSR_q@3 平均

预测列表抽取
────────────
从 pred_answer 自由文本中按"首次出现位置"抽取前 3 个 FWMAV 名字。
匹配规则：精确匹配 + 主名匹配（去掉括号内容）+ 括号别名匹配。
"""

from __future__ import annotations
import json
import math
import re
from pathlib import Path

# 39 个 FWMAV 名字（与 KG 一致）
FWMAV_NAMES = [
    "Allomyrina dichotoma (仿独角仙)", "Bionic Flying Fox", "BionicOpter",
    "C-GPTR (Mr. Bill)", "Colibri", "DelFly Explorer", "DelFly I", "DelFly II",
    "DelFly Micro", "DelFly Nimble", "Entomopter", "Insect-mimicking (仿昆虫无尾翼)",
    "KUBeetle-S", "MAV (University of Arizona)", "Mentor", "Microbat",
    "Nano Hummingbird", "PigeonBot", "Richter (Ornithopter)",
    "RoboBee (Hybrid Aerial-Aquatic)", "RoboBee (Original)", "RoboBee X-Wing",
    "RoboRaven", "Robotic Hummingbird", "SmartBird", "TechJect Dragonfly",
    "USTBird", "主动折叠变形扑翼飞行器", "云鸮", "信鸽", "凤凰 (Phoenix)",
    "四动力装置可悬停扑翼飞行器", "大中型仿鸟扑翼飞行器 (Large-Scale Ornithopter)",
    "小隼 (Little Falcon)", "微机械飞行昆虫 (MFI)", "机器海鸥", "空中仿生机器人",
    "蜂鸟机器人 (Purdue Hummingbird)", "金鹰",
]


def _build_aliases() -> list[tuple[str, str]]:
    """返回 [(alias_lower, canonical_name)] 列表，按 alias 长度降序（避免子串误匹配）.

    "DelFly I" 必须放在 "DelFly" 前面，"凤凰 (Phoenix)" 别名拆为 "凤凰" 和 "Phoenix"。
    """
    pairs = []
    for canonical in FWMAV_NAMES:
        # 完整名
        pairs.append((canonical, canonical))
        # 去括号主名
        m = re.match(r"^(.+?)\s*\((.+?)\)\s*$", canonical)
        if m:
            main = m.group(1).strip()
            paren = m.group(2).strip()
            if main != canonical and len(main) >= 2:
                pairs.append((main, canonical))
            if paren != canonical and len(paren) >= 2 and not paren.startswith("仿"):
                # 仿XXX 这种括号内的别名是描述性的，太短不要
                pairs.append((paren, canonical))
    # 按 alias 长度降序排，确保更长的先匹配
    pairs.sort(key=lambda x: -len(x[0]))
    return pairs


_ALIAS_TABLE = _build_aliases()


def extract_predicted_vehicles(pred_answer: str, top_k: int = 3) -> list[str]:
    """从 pred_answer 抽取前 K 个推荐样机（按文本中首次出现位置）.

    注意：DelFly I/II/Micro/Explorer/Nimble 这种共享前缀的名字，靠 _ALIAS_TABLE 长度降序避免误匹配。
    """
    if not pred_answer:
        return []

    text = pred_answer
    occurrences = []  # (pos, canonical)
    consumed = [False] * len(text)  # 标记已被长 alias 占用的字符位置

    for alias, canonical in _ALIAS_TABLE:
        start = 0
        while True:
            pos = text.find(alias, start)
            if pos == -1:
                break
            # 如果该位置已被更长 alias 占用，跳过
            if any(consumed[pos:pos + len(alias)]):
                start = pos + 1
                continue
            for i in range(pos, pos + len(alias)):
                consumed[i] = True
            occurrences.append((pos, canonical))
            start = pos + len(alias)

    occurrences.sort(key=lambda x: x[0])

    result, seen = [], set()
    for _, canonical in occurrences:
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
            if len(result) >= top_k:
                break
    return result


def ndcg_at_k_binary(predicted: list[str], gold_set: set[str], k: int = 3) -> float:
    """Binary NDCG@k. gold 为空时返回 0."""
    if not gold_set:
        return 0.0
    dcg = 0.0
    for i, v in enumerate(predicted[:k]):
        if v in gold_set:
            dcg += 1.0 / math.log2(i + 2)
    n_ideal = min(len(gold_set), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(n_ideal))
    return dcg / idcg if idcg > 0 else 0.0


def ndcg_at_k_graded(predicted: list[str], graded_relevance: dict[str, int],
                     k: int = 3) -> float:
    """Graded NDCG@k. graded_relevance: {vehicle_name: 0-3}."""
    if not graded_relevance:
        return 0.0
    # DCG
    dcg = 0.0
    for i, v in enumerate(predicted[:k]):
        rel = graded_relevance.get(v, 0)
        dcg += (2 ** rel - 1) / math.log2(i + 2)
    # IDCG: 把 graded_relevance 里前 k 个最大的 rel 排前面
    sorted_rels = sorted(graded_relevance.values(), reverse=True)[:k]
    idcg = sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(sorted_rels))
    return dcg / idcg if idcg > 0 else 0.0


def recall_strict_at_k(predicted: list[str], graded_relevance: dict[str, int],
                       k: int = 3) -> float:
    """Recall_strict@k: 命中的 rel=3 样机数 / 全部 rel=3 样机数."""
    rel3_set = {v for v, r in graded_relevance.items() if r == 3}
    if not rel3_set:
        return 0.0
    hit = sum(1 for v in predicted[:k] if v in rel3_set)
    return hit / min(len(rel3_set), k)  # 分母不超过 k，防止天花板低


def recall_loose_at_k(predicted: list[str], graded_relevance: dict[str, int],
                      k: int = 3) -> float:
    """Recall_loose@k: 命中的 rel≥2 样机数 / 全部 rel≥2 样机数（cap by k）."""
    rel2_set = {v for v, r in graded_relevance.items() if r >= 2}
    if not rel2_set:
        return 0.0
    hit = sum(1 for v in predicted[:k] if v in rel2_set)
    return hit / min(len(rel2_set), k)


def precision_at_1(predicted: list[str], graded_relevance: dict[str, int]) -> float:
    """第一推荐是不是 rel=3 (1.0 if yes, 0.0 otherwise)."""
    if not predicted:
        return 0.0
    return 1.0 if graded_relevance.get(predicted[0], 0) == 3 else 0.0


def ndcg_at_k_binary(predicted: list[str], gold_set: set[str], k: int = 3) -> float:
    """旧 Binary NDCG@k (保留兼容)."""
    if not gold_set:
        return 0.0
    dcg = 0.0
    for i, v in enumerate(predicted[:k]):
        if v in gold_set:
            dcg += 1.0 / math.log2(i + 2)
    n_ideal = min(len(gold_set), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(n_ideal))
    return dcg / idcg if idcg > 0 else 0.0


def csr_at_k(predicted: list[str], gold_recommendations: list[dict],
             hard_constraints: dict, k: int = 3) -> float | None:
    """CSR@k. 题目无硬约束时返回 None（不计入平均）."""
    if not hard_constraints:
        return None
    rec_lookup = {rec["vehicle"]: rec for rec in gold_recommendations}
    csr_sum = 0.0
    for i in range(k):
        if i >= len(predicted):
            csr_i = 0.0
        else:
            v = predicted[i]
            rec = rec_lookup.get(v)
            if rec is None:
                csr_i = 0.0
            else:
                hcs = rec.get("hard_constraints_satisfied", {})
                if hcs:
                    csr_i = sum(1 for ok in hcs.values() if ok) / len(hcs)
                else:
                    csr_i = 0.0
        csr_sum += csr_i
    return csr_sum / k


def load_b_gold(path: Path) -> dict[str, dict]:
    """加载 B 类标注文件，返回 {qid: item} 仅 B1/B2 题."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            it = json.loads(line)
            if it.get("category") in ("B1", "B2"):
                out[it["id"]] = it
    return out


def evaluate_b_metrics(predictions: dict[str, str], b_gold_lookup: dict[str, dict],
                       k: int = 3, verbose: bool = True) -> dict:
    """对 B 类题计算多指标：NDCG@3 (graded) + Recall_strict@3 + Recall_loose@3 + P@1.

    Args:
        predictions:     {qid: pred_answer 自由文本}
        b_gold_lookup:   {qid: {graded_relevance, gold_recommendations, ...}}
    """
    per_item = []
    for qid, gold in b_gold_lookup.items():
        pred_str = predictions.get(qid, "") or ""
        graded = gold.get("graded_relevance", {})

        predicted = extract_predicted_vehicles(pred_str, top_k=k)

        ndcg = ndcg_at_k_graded(predicted, graded, k=k)
        r_strict = recall_strict_at_k(predicted, graded, k=k)
        r_loose = recall_loose_at_k(predicted, graded, k=k)
        p1 = precision_at_1(predicted, graded)

        per_item.append({
            "id": qid,
            "category": gold.get("category"),
            "difficulty": gold.get("difficulty"),
            "predicted": predicted,
            "rel_of_top3": [graded.get(v, 0) for v in predicted[:k]],
            "ndcg_graded": ndcg,
            "recall_strict": r_strict,
            "recall_loose": r_loose,
            "p_at_1": p1,
        })
        if verbose:
            print(f"  [{gold.get('category')}] {qid}  NDCG={ndcg:.3f}  "
                  f"R_strict={r_strict:.3f}  R_loose={r_loose:.3f}  P@1={p1:.0f}  "
                  f"top3_rel={[graded.get(v, 0) for v in predicted[:k]]}")

    # 聚合（按 category）
    by_cat = {}
    for d in per_item:
        by_cat.setdefault(d["category"], []).append(d)
    cat_means = {}
    for c, items in by_cat.items():
        n = len(items)
        cat_means[c] = {
            "n": n,
            "ndcg_graded_mean":    sum(d["ndcg_graded"] for d in items) / n,
            "recall_strict_mean":  sum(d["recall_strict"] for d in items) / n,
            "recall_loose_mean":   sum(d["recall_loose"] for d in items) / n,
            "p_at_1_mean":         sum(d["p_at_1"] for d in items) / n,
        }

    n_total = max(len(per_item), 1)
    overall = {
        "n_total": len(per_item),
        "ndcg_graded_mean":    sum(d["ndcg_graded"] for d in per_item) / n_total,
        "recall_strict_mean":  sum(d["recall_strict"] for d in per_item) / n_total,
        "recall_loose_mean":   sum(d["recall_loose"] for d in per_item) / n_total,
        "p_at_1_mean":         sum(d["p_at_1"] for d in per_item) / n_total,
    }
    return {"overall": overall, "by_category": cat_means, "per_item": per_item}


if __name__ == "__main__":
    # Self-test
    sample = "推荐 Top-3 参考样机：1. Nano Hummingbird (165mm 翼展)；2. KUBeetle-S（轻量）；3. DelFly Explorer。"
    print(extract_predicted_vehicles(sample))
