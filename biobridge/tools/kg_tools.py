"""KG 检索工具 - 把 Neo4j 查询封装成 LLM 可调用的函数.

3 个工具：
- search_fwmav:        按名称/属性筛选 FWMAV 节点（工程层）
- search_organism:     按生物原型筛选（生物层）
- query_mimics_path:   两层之间的 MIMICS 路径查询
"""

from __future__ import annotations
import os
import json
from typing import Optional
from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")


def _get_driver():
    """每次调用打开新 driver，避免长连接（demo 用）."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# ============================================================
# 1. search_fwmav - 工程层节点搜索
# ============================================================

def search_fwmav(
    name: Optional[str] = None,
    weight_max_g: Optional[float] = None,
    weight_min_g: Optional[float] = None,
    wingspan_max_mm: Optional[float] = None,
    wingspan_min_mm: Optional[float] = None,
    can_hover: Optional[bool] = None,
    biological_prototype: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """搜索扑翼飞行器 (FlappingWingVehicle) 节点.

    支持按名称模糊匹配、重量/翼展范围、悬停能力、仿生原型筛选.
    """
    where_parts = []
    params = {"limit": limit}

    if biological_prototype:
        cypher = """
        MATCH (v:FlappingWingVehicle)-[m:MIMICS]->(o:Organism)
        WHERE o.name CONTAINS $bio
        """
        params["bio"] = biological_prototype
    else:
        cypher = "MATCH (v:FlappingWingVehicle)"

    if name:
        where_parts.append("v.name CONTAINS $name")
        params["name"] = name
    if weight_max_g is not None:
        where_parts.append("v.weight_g_std <= $w_max")
        params["w_max"] = weight_max_g
    if weight_min_g is not None:
        where_parts.append("v.weight_g_std >= $w_min")
        params["w_min"] = weight_min_g
    if wingspan_max_mm is not None:
        where_parts.append("v.wingspan_mm <= $ws_max")
        params["ws_max"] = wingspan_max_mm
    if wingspan_min_mm is not None:
        where_parts.append("v.wingspan_mm >= $ws_min")
        params["ws_min"] = wingspan_min_mm
    if can_hover is not None:
        where_parts.append("v.can_hover = $hover")
        params["hover"] = can_hover

    if where_parts:
        if "WHERE" in cypher:
            cypher += " AND " + " AND ".join(where_parts)
        else:
            cypher += " WHERE " + " AND ".join(where_parts)

    cypher += """
    RETURN v.name AS name,
           v.weight_g_std AS weight_g,
           v.wingspan_mm AS wingspan_mm,
           v.frequency_hz AS frequency_hz,
           v.endurance_s_std AS endurance_s,
           v.speed_max_m_s_std AS speed_m_s,
           v.can_hover AS can_hover,
           v.is_atypical_fwmav AS is_atypical
    ORDER BY v.name
    LIMIT $limit
    """

    with _get_driver() as drv:
        with drv.session() as sess:
            res = sess.run(cypher, **params)
            vehicles = []
            for r in res:
                d = dict(r)
                d = {k: v for k, v in d.items() if v is not None}
                vehicles.append(d)

    return {
        "count": len(vehicles),
        "vehicles": vehicles,
        "query_summary": _summarize_filters(
            name, weight_max_g, weight_min_g, wingspan_max_mm,
            wingspan_min_mm, can_hover, biological_prototype
        ),
    }


def _summarize_filters(name, w_max, w_min, ws_max, ws_min, hover, bio):
    parts = []
    if name: parts.append(f"name~'{name}'")
    if w_min is not None: parts.append(f"weight≥{w_min}g")
    if w_max is not None: parts.append(f"weight≤{w_max}g")
    if ws_min is not None: parts.append(f"wingspan≥{ws_min}mm")
    if ws_max is not None: parts.append(f"wingspan≤{ws_max}mm")
    if hover is not None: parts.append(f"hover={hover}")
    if bio: parts.append(f"MIMICS~'{bio}'")
    return " AND ".join(parts) if parts else "ALL"


# ============================================================
# 2. search_organism - 生物层节点搜索
# ============================================================

def search_organism(name: Optional[str] = None, can_hover: Optional[bool] = None) -> dict:
    """搜索生物原型 (Organism) 节点."""
    where_parts = []
    params = {}
    cypher = "MATCH (o:Organism)"

    if name:
        where_parts.append("o.name CONTAINS $name")
        params["name"] = name
    if can_hover is not None:
        where_parts.append("o.can_hover = $hover")
        params["hover"] = can_hover

    if where_parts:
        cypher += " WHERE " + " AND ".join(where_parts)

    cypher += """
    RETURN o.name AS name,
           o.scientific_name AS scientific_name,
           o.body_mass_g_min AS mass_g_min,
           o.body_mass_g_max AS mass_g_max,
           o.wingspan_cm_min AS wingspan_cm_min,
           o.wingspan_cm_max AS wingspan_cm_max,
           o.flap_freq_hz_min AS flap_freq_hz_min,
           o.flap_freq_hz_max AS flap_freq_hz_max,
           o.cruise_speed_m_s_min AS speed_m_s_min,
           o.cruise_speed_m_s_max AS speed_m_s_max,
           o.can_hover AS can_hover,
           o.notes AS notes
    ORDER BY o.name
    """

    with _get_driver() as drv:
        with drv.session() as sess:
            res = sess.run(cypher, **params)
            orgs = []
            for r in res:
                d = dict(r)
                d = {k: v for k, v in d.items() if v is not None}
                orgs.append(d)

    return {"count": len(orgs), "organisms": orgs}


# ============================================================
# 3. query_mimics_path - 双层本体路径查询
# ============================================================

def query_mimics_path(
    fwmav_name: Optional[str] = None,
    organism_name: Optional[str] = None,
    dominant_type: Optional[str] = None,
    min_score: float = 0.5,
) -> dict:
    """查询 MIMICS 仿生映射路径，含 4 类相似度分数."""
    where_parts = ["m.mimics_dominant_score >= $min_score"]
    params = {"min_score": min_score}

    if fwmav_name:
        where_parts.append("v.name CONTAINS $vname")
        params["vname"] = fwmav_name
    if organism_name:
        where_parts.append("o.name CONTAINS $oname")
        params["oname"] = organism_name
    if dominant_type:
        where_parts.append("m.mimics_dominant_type = $dom")
        params["dom"] = dominant_type

    cypher = """
    MATCH (v:FlappingWingVehicle)-[m:MIMICS]->(o:Organism)
    WHERE """ + " AND ".join(where_parts) + """
    RETURN v.name AS vehicle,
           o.name AS organism,
           m.mimics_aero AS aero,
           m.mimics_kinematics AS kinematics,
           m.mimics_morphology AS morphology,
           m.mimics_scale AS scale,
           m.mimics_dominant_type AS dominant_type,
           m.mimics_dominant_score AS dominant_score
    ORDER BY m.mimics_dominant_score DESC
    LIMIT 30
    """

    with _get_driver() as drv:
        with drv.session() as sess:
            res = sess.run(cypher, **params)
            paths = []
            for r in res:
                d = dict(r)
                d = {k: v for k, v in d.items() if v is not None}
                paths.append(d)

    return {
        "count": len(paths),
        "paths": paths,
        "filter_summary": (
            f"vehicle~'{fwmav_name or 'any'}', "
            f"organism~'{organism_name or 'any'}', "
            f"dominant={dominant_type or 'any'}, "
            f"score≥{min_score}"
        ),
    }


# ============================================================
# 工具注册表
# ============================================================

KG_TOOLS = {
    "search_fwmav": search_fwmav,
    "search_organism": search_organism,
    "query_mimics_path": query_mimics_path,
}


if __name__ == "__main__":
    print("=== Tool: search_fwmav (能悬停, 翼展<200mm, 5 个) ===")
    r = search_fwmav(can_hover=True, wingspan_max_mm=200, limit=5)
    print(json.dumps(r, ensure_ascii=False, indent=2))

    print("\n=== Tool: search_organism (蜂鸟) ===")
    r = search_organism(name="蜂鸟")
    print(json.dumps(r, ensure_ascii=False, indent=2))

    print("\n=== Tool: query_mimics_path (DelFly Nimble 的仿生映射) ===")
    r = query_mimics_path(fwmav_name="DelFly Nimble")
    print(json.dumps(r, ensure_ascii=False, indent=2))
