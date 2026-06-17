"""创新点 3: 张量分解的方案候选检索（粗筛阶段）.

从 KG 构建 3 阶张量 (FWMAV × Feature × Mission)，
用 TensorLy CP 分解学习每个 FWMAV 的低维嵌入向量，
KNN 检索给定任务约束最相似的 Top-N 候选。

可独立运行，也可作为创新点 2 ReAct 链路里的 tensor_recall 工具。

设计参考：Jia 2021 AEI (10.1016/j.aei.2021.101505) 在工程设计领域的 KG 张量分解.
扩展点：本研究在 Feature 维度同时纳入 Performance + Equipment，使粗筛能同时考虑
"性能匹配"与"组件配置匹配"，论文里可声明为"扩展自 Jia 的 3 阶张量到含组件维度的实用化变体"。
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Optional

import numpy as np
import tensorly as tl
from tensorly.decomposition import parafac
from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")

# ============================================================
# 维度定义
# ============================================================

# 9 个 Performance metric（按 KG 实际 metric+condition 组合）
PERFORMANCE_DIMS = [
    ("weight",         "general"),
    ("wingspan",       "general"),
    ("frequency_min",  "general"),
    ("frequency_max",  "general"),
    ("speed_max",      "max"),
    ("endurance",      "hover"),
    ("endurance",      "mixed"),
    ("hover",          "general"),  # boolean
    ("aspect_ratio",   "general"),  # 由 wingspan² / wing_area 推算
]

# 5 个核心 Equipment category（按 KG 实际分布）
EQUIPMENT_DIMS = [
    "actuator",
    "sensor",
    "power",
    "flight_control",
    "payload",
]

# 5 个 Mission 大类（基于 KG Application 节点的语义聚合）
MISSION_DIMS = [
    "research",      # 机理研究/控制律验证/原理验证
    "task",          # 侦察/巡航/监测/航拍/运输
    "maneuver",      # 高机动/特技/俯冲/转弯
    "performance",   # 高效率/长航时/悬停飞行
    "other",         # 表演/教学/概念探索
]

MISSION_KEYWORDS = {
    "research": ["研究", "验证", "测试", "原理", "机理", "实验"],
    "task": ["侦察", "巡航", "监测", "航拍", "运输", "巡逻", "探测"],
    "maneuver": ["机动", "特技", "俯冲", "转弯", "悬停机动", "避障"],
    "performance": ["高效率", "长航时", "悬停飞行", "续航"],
    "other": ["表演", "编队", "游戏"],
}


# ============================================================
# 1. 从 KG 加载并构建张量
# ============================================================

def _safe_num(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if "-" in s and not s.startswith("-"):
        # 区间值取均值
        try:
            parts = s.split("-")
            return (float(parts[0]) + float(parts[1])) / 2
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def categorize_application(app_name: str) -> str:
    """把 Application 节点名称归入 5 大类."""
    for cat, kws in MISSION_KEYWORDS.items():
        for kw in kws:
            if kw in app_name:
                return cat
    return "other"


def build_tensor() -> dict:
    """从 KG 构建 3 阶张量 X (n_fwmav × n_feature × n_mission).

    Feature 维度 = Performance (9) + Equipment (5) = 14 个特征
    Mission 维度 = 5 大类

    Returns:
        dict {
            "tensor": np.ndarray (n_fwmav, n_feature, n_mission),
            "fwmav_names": [...],
            "feature_labels": [...],
            "mission_labels": [...],
            "fwmav_attrs": {name: dict of raw attrs},  # 保存原属性方便 KNN 解释
        }
    """
    drv = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # 1. 拿全部 FWMAV 节点 + 标准化属性
    with drv.session() as sess:
        res = sess.run("MATCH (v:FlappingWingVehicle) RETURN properties(v) AS p ORDER BY v.name")
        fwmavs = [row["p"] for row in res]
    fwmav_names = [v["name"] for v in fwmavs]
    fwmav_attrs = {v["name"]: v for v in fwmavs}
    n_fwmav = len(fwmav_names)

    # 2. 拿每个 FWMAV 的 Equipment category 计数
    with drv.session() as sess:
        res = sess.run("""
            MATCH (v:FlappingWingVehicle)-[:EQUIPPED_WITH]->(e:Equipment)
            RETURN v.name AS v_name, e.category AS cat, count(*) AS n
        """)
        equipment_counts = {}
        for row in res:
            equipment_counts.setdefault(row["v_name"], {})[row["cat"]] = row["n"]

    # 3. 拿每个 FWMAV 的 Application
    with drv.session() as sess:
        res = sess.run("""
            MATCH (v:FlappingWingVehicle)-[:SUITABLE_FOR]->(a:Application)
            RETURN v.name AS v_name, a.name AS app_name
        """)
        fwmav_apps = {}
        for row in res:
            fwmav_apps.setdefault(row["v_name"], []).append(row["app_name"])

    drv.close()

    # 4. 构建特征向量（每个 FWMAV 在每个 mission 下的特征值）
    # 对于 Performance 类特征，假设它在所有 mission 下相同；只在该 FWMAV 实际适用的 mission 下激活
    feature_labels = [f"{m}_{c}" for m, c in PERFORMANCE_DIMS] + [f"equip_{c}" for c in EQUIPMENT_DIMS]
    n_feature = len(feature_labels)
    n_mission = len(MISSION_DIMS)

    X = np.zeros((n_fwmav, n_feature, n_mission), dtype=np.float32)

    for i, name in enumerate(fwmav_names):
        attrs = fwmav_attrs[name]

        # 该 FWMAV 适用哪些 mission 类别
        apps = fwmav_apps.get(name, [])
        mission_set = set()
        for app in apps:
            mission_set.add(categorize_application(app))
        if not mission_set:
            mission_set = {"other"}  # 兜底

        # 5 个 Equipment category 计数
        ec = equipment_counts.get(name, {})

        for k, mission in enumerate(MISSION_DIMS):
            if mission not in mission_set:
                continue  # 该 mission 下该 FWMAV 不激活

            # Performance 特征
            f_idx = 0
            X[i, f_idx, k] = _safe_num(attrs.get("weight_g_std")) or 0; f_idx += 1
            X[i, f_idx, k] = _safe_num(attrs.get("wingspan_mm")) or 0; f_idx += 1
            X[i, f_idx, k] = _safe_num(attrs.get("frequency_hz_min_std")) or 0; f_idx += 1
            X[i, f_idx, k] = _safe_num(attrs.get("frequency_hz_max_std")) or 0; f_idx += 1
            X[i, f_idx, k] = _safe_num(attrs.get("speed_max_m_s_std")) or 0; f_idx += 1
            # endurance hover / mixed
            cond = attrs.get("endurance_condition_std", "mixed")
            es = _safe_num(attrs.get("endurance_s_std")) or 0
            if cond == "hover":
                X[i, f_idx, k] = es; f_idx += 1
                X[i, f_idx, k] = 0; f_idx += 1
            else:
                X[i, f_idx, k] = 0; f_idx += 1
                X[i, f_idx, k] = es; f_idx += 1
            # hover boolean
            X[i, f_idx, k] = 1.0 if attrs.get("can_hover") else 0.0; f_idx += 1
            # aspect_ratio (估算)
            ws = _safe_num(attrs.get("wingspan_mm")) or 0
            # 用 wingspan/4 估算 wing area（粗略，等价于翼弦 = wingspan/8）
            if ws > 0:
                wing_area = (ws * ws / 8) / 100  # cm^2 → 比例值
                X[i, f_idx, k] = (ws/10) ** 2 / wing_area if wing_area > 0 else 0
            else:
                X[i, f_idx, k] = 0
            f_idx += 1

            # Equipment 维度
            for cat in EQUIPMENT_DIMS:
                X[i, f_idx, k] = float(ec.get(cat, 0))
                f_idx += 1

    # 5. 归一化（每个特征做 z-score 标准化）
    # 沿着 (FWMAV × Mission) 二维做归一化（per feature）
    X_normalized = np.copy(X)
    for f in range(n_feature):
        slice_ = X[:, f, :]
        mu = slice_.mean()
        sigma = slice_.std()
        if sigma > 1e-6:
            X_normalized[:, f, :] = (slice_ - mu) / sigma

    return {
        "tensor_raw": X,
        "tensor": X_normalized,
        "shape": X.shape,
        "fwmav_names": fwmav_names,
        "feature_labels": feature_labels,
        "mission_labels": MISSION_DIMS,
        "fwmav_attrs": fwmav_attrs,
        # 保存归一化常数，供 query 使用
        "feature_means": np.array([X[:, f, :].mean() for f in range(n_feature)]),
        "feature_stds": np.array([max(X[:, f, :].std(), 1e-6) for f in range(n_feature)]),
    }


# ============================================================
# 2. CP 分解 + 嵌入
# ============================================================

def decompose_tensor(tensor_data: dict, rank: int = 8, random_state: int = 42) -> dict:
    """对 3 阶张量做 CP 分解，得到 FWMAV 嵌入.

    X ≈ Σ_{r=1}^R u_r ⊗ v_r ⊗ w_r
    其中 u_r ∈ R^n_fwmav, v_r ∈ R^n_feature, w_r ∈ R^n_mission

    每个 FWMAV i 的嵌入 = U[i, :]，是 R 维向量.

    Args:
        tensor_data: build_tensor() 输出
        rank: CP 分解秩（潜在维度数）

    Returns:
        dict {
            "rank": int,
            "fwmav_embeddings": np.ndarray (n_fwmav, rank),
            "feature_factors": np.ndarray (n_feature, rank),
            "mission_factors": np.ndarray (n_mission, rank),
            "reconstruction_error": float,
            "fwmav_names": [...],
            ...
        }
    """
    X = tensor_data["tensor"]
    tl.set_backend("numpy")
    X_tl = tl.tensor(X)

    # CP 分解
    np.random.seed(random_state)
    weights, factors = parafac(X_tl, rank=rank, init="random", n_iter_max=200, tol=1e-7)
    # factors: list of 3 矩阵 [U (n_fwmav, R), V (n_feature, R), W (n_mission, R)]

    U, V, W = factors

    # 重构误差
    X_reconstructed = tl.cp_to_tensor((weights, factors))
    rec_err = float(np.linalg.norm(X - X_reconstructed) / np.linalg.norm(X))

    # 把权重吸收到 U（FWMAV 嵌入）中，方便 KNN
    U_weighted = U * weights

    return {
        "rank": rank,
        "fwmav_embeddings": U_weighted,
        "feature_factors": V,
        "mission_factors": W,
        "weights": weights,
        "reconstruction_error": rec_err,
        "fwmav_names": tensor_data["fwmav_names"],
        "feature_labels": tensor_data["feature_labels"],
        "mission_labels": tensor_data["mission_labels"],
        "fwmav_attrs": tensor_data["fwmav_attrs"],
        "feature_means": tensor_data["feature_means"],
        "feature_stds": tensor_data["feature_stds"],
    }


# ============================================================
# 3. 任务约束 → 查询向量
# ============================================================

def constraints_to_query_vector(
    decomp: dict,
    weight_g: Optional[float] = None,
    wingspan_mm: Optional[float] = None,
    frequency_hz: Optional[float] = None,
    speed_max_m_s: Optional[float] = None,
    endurance_s: Optional[float] = None,
    can_hover: Optional[bool] = None,
    mission: Optional[str] = None,
    equip_categories_required: Optional[list] = None,
) -> np.ndarray:
    """把任务约束转成嵌入空间的查询向量（v3 - 用 raw 张量归一化常数）.

    流程:
    1. 构造 raw query 矩阵 Q_raw (n_feature, n_mission)
    2. 用 build_tensor 同样的归一化把 Q_raw → Q_norm
    3. 用 CP 因子把 Q_norm 投影到 R 维潜在空间

    关键修复 vs v2: 显式使用 feature_means / feature_stds 归一化查询，
    使查询空间与样本空间对齐。
    """
    feature_labels = decomp["feature_labels"]
    n_feature = len(feature_labels)
    V = decomp["feature_factors"]   # (n_feature, R)
    W = decomp["mission_factors"]   # (n_mission, R)
    n_mission = W.shape[0]
    mission_labels = decomp["mission_labels"]
    rank = V.shape[1]
    f_means = decomp["feature_means"]
    f_stds = decomp["feature_stds"]

    field_map = {
        "weight_general": weight_g,
        "wingspan_general": wingspan_mm,
        "frequency_min_general": frequency_hz,
        "frequency_max_general": frequency_hz,
        "speed_max_max": speed_max_m_s,
        "endurance_hover": endurance_s if can_hover else None,
        "endurance_mixed": endurance_s if (can_hover is False or can_hover is None) else None,
        "hover_general": (1.0 if can_hover else 0.0) if can_hover is not None else None,
        "aspect_ratio_general": None,
    }
    for cat in EQUIPMENT_DIMS:
        if equip_categories_required and cat in equip_categories_required:
            field_map[f"equip_{cat}"] = 1.0
        else:
            field_map[f"equip_{cat}"] = None

    active_missions = [mission] if (mission and mission in mission_labels) else mission_labels
    active_mission_idx = [mission_labels.index(m) for m in active_missions]

    # 构造 raw query 矩阵 (n_feature, n_mission)，未指定的字段为 NaN
    Q_raw = np.full((n_feature, n_mission), np.nan, dtype=np.float32)
    for i, label in enumerate(feature_labels):
        v = field_map.get(label)
        if v is None:
            continue
        for m_idx in active_mission_idx:
            Q_raw[i, m_idx] = float(v)

    # 归一化（用样本的 mean/std）
    Q_norm = np.zeros_like(Q_raw, dtype=np.float32)
    valid_mask = ~np.isnan(Q_raw)
    for i in range(n_feature):
        for k in range(n_mission):
            if valid_mask[i, k]:
                Q_norm[i, k] = (Q_raw[i, k] - f_means[i]) / f_stds[i]

    # 投影到潜在空间
    # CP 重构: X[i,j,k] ≈ Σ_r U[i,r] V[j,r] W[k,r]
    # 给定 Q_norm[j,k]，最小化 ||Q_norm - Σ_r q[r] V[j,r] W[k,r]|| → 解 q
    # 等价于：q[r] = <Q_norm, outer(V[:,r], W[:,r])> / ||outer||²
    q = np.zeros(rank, dtype=np.float32)
    for r in range(rank):
        outer = np.outer(V[:, r], W[:, r])  # (n_feature, n_mission)
        # 只考虑有指定值的位置（用 mask）
        masked_outer = outer * valid_mask
        masked_q = Q_norm * valid_mask
        denom = (masked_outer ** 2).sum() + 1e-9
        q[r] = (masked_q * masked_outer).sum() / denom

    return q


# ============================================================
# 4. KNN Top-N 候选检索（粗筛）
# ============================================================

def tensor_recall(
    decomp: dict,
    weight_g: Optional[float] = None,
    wingspan_mm: Optional[float] = None,
    frequency_hz: Optional[float] = None,
    speed_max_m_s: Optional[float] = None,
    endurance_s: Optional[float] = None,
    can_hover: Optional[bool] = None,
    mission: Optional[str] = None,
    equip_categories_required: Optional[list] = None,
    top_k: int = 10,
    embedding_weight: float = 0.4,
) -> dict:
    """张量分解粗筛：给定任务约束 → Top-K 候选 FWMAV.

    创新点 3 的核心入口。

    采用混合相似度（论文里更稳健的做法）：
    - raw 特征空间 cosine 相似度（主导）
    - CP 嵌入空间 cosine 相似度（语义增强）
    final_sim = (1 - embedding_weight) * raw_sim + embedding_weight * embed_sim

    embedding_weight=0 → 纯 raw 特征匹配
    embedding_weight=1 → 纯 CP 嵌入匹配
    默认 0.4 平衡可解释性 + 潜在语义.
    """
    # ===== 1. CP 嵌入空间相似度 =====
    q_embed = constraints_to_query_vector(
        decomp,
        weight_g=weight_g, wingspan_mm=wingspan_mm,
        frequency_hz=frequency_hz, speed_max_m_s=speed_max_m_s,
        endurance_s=endurance_s, can_hover=can_hover,
        mission=mission, equip_categories_required=equip_categories_required,
    )
    U = decomp["fwmav_embeddings"]
    q_embed_norm = q_embed / (np.linalg.norm(q_embed) + 1e-9)
    U_norm = U / (np.linalg.norm(U, axis=1, keepdims=True) + 1e-9)
    sims_embed = U_norm @ q_embed_norm  # (n_fwmav,)

    # ===== 2. raw 特征空间相似度（更稳健）=====
    # 把每个 FWMAV 在所有 mission 下的特征向量平均，得到 (n_fwmav, n_feature) 表征
    # 然后用查询的 (n_feature,) 向量做 cosine
    f_means = decomp["feature_means"]
    f_stds = decomp["feature_stds"]
    feature_labels = decomp["feature_labels"]
    n_feature = len(feature_labels)

    # 重构 raw 特征矩阵（用 fwmav_attrs 直接读，避免依赖原 raw 张量）
    fwmav_names = decomp["fwmav_names"]
    n_fwmav = len(fwmav_names)
    F_raw = np.zeros((n_fwmav, n_feature), dtype=np.float32)

    for i, name in enumerate(fwmav_names):
        attrs = decomp["fwmav_attrs"][name]
        # 与 build_tensor 一致的特征顺序
        F_raw[i, 0] = _safe_num(attrs.get("weight_g_std")) or 0
        F_raw[i, 1] = _safe_num(attrs.get("wingspan_mm")) or 0
        F_raw[i, 2] = _safe_num(attrs.get("frequency_hz_min_std")) or 0
        F_raw[i, 3] = _safe_num(attrs.get("frequency_hz_max_std")) or 0
        F_raw[i, 4] = _safe_num(attrs.get("speed_max_m_s_std")) or 0
        cond = attrs.get("endurance_condition_std", "mixed")
        es = _safe_num(attrs.get("endurance_s_std")) or 0
        if cond == "hover":
            F_raw[i, 5] = es
            F_raw[i, 6] = 0
        else:
            F_raw[i, 5] = 0
            F_raw[i, 6] = es
        F_raw[i, 7] = 1.0 if attrs.get("can_hover") else 0.0
        # idx 8: aspect_ratio - 跳过
        # idx 9-13: equipment counts - 跳过（query 也很少指定）

    # 归一化（用同样的 means/stds）
    F_norm = (F_raw - f_means[:n_feature]) / (f_stds[:n_feature] + 1e-9)

    # 构造 raw query
    q_raw = np.zeros(n_feature, dtype=np.float32)
    valid = np.zeros(n_feature, dtype=bool)
    if weight_g is not None:
        q_raw[0] = (weight_g - f_means[0]) / f_stds[0]; valid[0] = True
    if wingspan_mm is not None:
        q_raw[1] = (wingspan_mm - f_means[1]) / f_stds[1]; valid[1] = True
    if frequency_hz is not None:
        q_raw[2] = (frequency_hz - f_means[2]) / f_stds[2]; valid[2] = True
        q_raw[3] = (frequency_hz - f_means[3]) / f_stds[3]; valid[3] = True
    if speed_max_m_s is not None:
        q_raw[4] = (speed_max_m_s - f_means[4]) / f_stds[4]; valid[4] = True
    if endurance_s is not None:
        if can_hover:
            q_raw[5] = (endurance_s - f_means[5]) / f_stds[5]; valid[5] = True
        else:
            q_raw[6] = (endurance_s - f_means[6]) / f_stds[6]; valid[6] = True
    if can_hover is not None:
        q_raw[7] = (1.0 if can_hover else 0.0 - f_means[7]) / f_stds[7]; valid[7] = True

    # 余弦相似度（仅在 valid 维度上算）
    if valid.any():
        F_masked = F_norm[:, valid]
        q_masked = q_raw[valid]
        F_lengths = np.linalg.norm(F_masked, axis=1) + 1e-9
        q_length = np.linalg.norm(q_masked) + 1e-9
        sims_raw = (F_masked @ q_masked) / (F_lengths * q_length)
    else:
        sims_raw = np.zeros(n_fwmav)

    # ===== 3. 混合相似度 =====
    sims = (1 - embedding_weight) * sims_raw + embedding_weight * sims_embed

    # 排序取 Top-K
    order = np.argsort(-sims)[:top_k]

    candidates = []
    for rank, idx in enumerate(order, 1):
        name = decomp["fwmav_names"][idx]
        attrs = decomp["fwmav_attrs"][name]
        candidates.append({
            "rank": rank,
            "name": name,
            "similarity": float(sims[idx]),
            "sim_raw": float(sims_raw[idx]),
            "sim_embed": float(sims_embed[idx]),
            "weight_g": _safe_num(attrs.get("weight_g_std")),
            "wingspan_mm": _safe_num(attrs.get("wingspan_mm")),
            "frequency_hz": attrs.get("frequency_hz"),
            "endurance_s": _safe_num(attrs.get("endurance_s_std")),
            "can_hover": attrs.get("can_hover"),
        })

    return {
        "top_k": top_k,
        "candidates": candidates,
        "query_constraints": {
            "weight_g": weight_g,
            "wingspan_mm": wingspan_mm,
            "frequency_hz": frequency_hz,
            "speed_max_m_s": speed_max_m_s,
            "endurance_s": endurance_s,
            "can_hover": can_hover,
            "mission": mission,
            "equip_categories_required": equip_categories_required,
        },
        "method": f"Hybrid: {(1-embedding_weight)*100:.0f}% raw cosine + {embedding_weight*100:.0f}% CP embedding cosine",
        "rank_R": decomp["rank"],
    }


# ============================================================
# 5. 一次性 train + persist 到磁盘（避免每次启动重新分解）
# ============================================================

CACHE_PATH = Path(__file__).resolve().parent.parent / "demo" / "tensor_decomp_cache.npz"


def train_and_save(rank: int = 12, force_rebuild: bool = False) -> dict:
    """训练（CP 分解）并缓存到磁盘."""
    if CACHE_PATH.exists() and not force_rebuild:
        return load_decomp()
    print(f"  从 KG 构建张量...")
    td = build_tensor()
    print(f"  Tensor shape: {td['shape']}, density: {(td['tensor_raw'] != 0).mean():.3f}")
    print(f"  CP 分解 (rank={rank})...")
    decomp = decompose_tensor(td, rank=rank)
    print(f"  重构误差: {decomp['reconstruction_error']:.4f}")

    # 保存
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        CACHE_PATH,
        fwmav_embeddings=decomp["fwmav_embeddings"],
        feature_factors=decomp["feature_factors"],
        mission_factors=decomp["mission_factors"],
        weights=decomp["weights"],
        rank=decomp["rank"],
        reconstruction_error=decomp["reconstruction_error"],
        feature_means=decomp["feature_means"],
        feature_stds=decomp["feature_stds"],
    )
    # fwmav_names / feature_labels / mission_labels / fwmav_attrs 单独存 JSON
    meta = {
        "fwmav_names": decomp["fwmav_names"],
        "feature_labels": decomp["feature_labels"],
        "mission_labels": decomp["mission_labels"],
        "fwmav_attrs": decomp["fwmav_attrs"],
    }
    with open(str(CACHE_PATH).replace(".npz", "_meta.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2, default=str)

    print(f"  已缓存到: {CACHE_PATH}")
    return decomp


def load_decomp() -> dict:
    """从磁盘加载分解结果."""
    npz = np.load(CACHE_PATH, allow_pickle=True)
    meta_path = str(CACHE_PATH).replace(".npz", "_meta.json")
    with open(meta_path) as f:
        meta = json.load(f)
    return {
        "fwmav_embeddings": npz["fwmav_embeddings"],
        "feature_factors": npz["feature_factors"],
        "mission_factors": npz["mission_factors"],
        "weights": npz["weights"],
        "rank": int(npz["rank"]),
        "reconstruction_error": float(npz["reconstruction_error"]),
        "feature_means": npz["feature_means"],
        "feature_stds": npz["feature_stds"],
        **meta,
    }


# ============================================================
# 工具注册（供 ReAct 链路使用）
# ============================================================

_decomp_cache = None


def tensor_recall_tool(
    weight_g: Optional[float] = None,
    wingspan_mm: Optional[float] = None,
    frequency_hz: Optional[float] = None,
    speed_max_m_s: Optional[float] = None,
    endurance_s: Optional[float] = None,
    can_hover: Optional[bool] = None,
    mission: Optional[str] = None,
    equip_categories_required: Optional[list] = None,
    top_k: int = 10,
) -> dict:
    """LLM 可调用的统一入口——首次调用时训练，后续调用复用."""
    global _decomp_cache
    if _decomp_cache is None:
        _decomp_cache = train_and_save()
    return tensor_recall(
        _decomp_cache,
        weight_g=weight_g,
        wingspan_mm=wingspan_mm,
        frequency_hz=frequency_hz,
        speed_max_m_s=speed_max_m_s,
        endurance_s=endurance_s,
        can_hover=can_hover,
        mission=mission,
        equip_categories_required=equip_categories_required,
        top_k=top_k,
    )


# ============================================================
# 自检
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  创新点 3: 张量分解粗筛  ·  自检")
    print("=" * 70)

    # 1. 构建 + 分解
    print("\n[1] 构建张量 + CP 分解 (rank=12)")
    decomp = train_and_save(rank=12, force_rebuild=True)

    # 2. 看几个测试 query
    test_queries = [
        {
            "name": "微型悬停（Demo 3 类型）",
            "args": {"wingspan_mm": 200, "can_hover": True, "weight_g": 20},
        },
        {
            "name": "中型仿鸟 + 长航时（Demo 2 类型）",
            "args": {"weight_g": 300, "endurance_s": 1800, "can_hover": False, "mission": "task"},
        },
        {
            "name": "昆虫尺度极致小型化",
            "args": {"weight_g": 0.3, "wingspan_mm": 35, "frequency_hz": 170},
        },
    ]

    for tq in test_queries:
        print(f"\n[Query] {tq['name']}")
        print(f"   约束: {tq['args']}")
        result = tensor_recall(decomp, top_k=5, **tq["args"])
        print(f"   Top-5 候选:")
        for c in result["candidates"]:
            print(f"     [{c['rank']}] {c['name']:35s}  sim={c['similarity']:+.3f}  "
                  f"w={c['weight_g']}g, ws={c['wingspan_mm']}mm, hover={c['can_hover']}")
