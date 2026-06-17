"""OpenAI Function Calling 工具规格 (JSON Schema).

把 4 个物理工具 + 3 个 KG 工具 + 1 个张量分解粗筛工具暴露给 LLM。
所有 spec 遵循 OpenAI Tool Use 标准（被 DeepSeek、Anthropic、Google 兼容）。
"""

from __future__ import annotations
import json
from .physics_tools import PHYSICS_TOOLS
from .kg_tools import KG_TOOLS
from .tensor_recall import tensor_recall_tool


TOOL_SPECS = [
    # ============ 物理工具 ============
    {
        "type": "function",
        "function": {
            "name": "hassanalian_weight",
            "description": (
                "基于 Hassanalian 2017 (Meccanica) 重量分数模型估算扑翼飞行器起飞重量。"
                "输入续航需求与载荷，迭代求解物理可行的总重量、电池重量、子系统分配。"
                "适用场景：用户问『做一架续航 X 分钟、载重 Y g 的扑翼机需要多重』。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "endurance_min": {
                        "type": "number",
                        "description": "任务续航需求（分钟）",
                    },
                    "payload_g": {
                        "type": "number",
                        "description": "任务载荷（g），不含航电",
                        "default": 0.0,
                    },
                    "avionics_g": {
                        "type": "number",
                        "description": "航电+控制系统重量（g）",
                        "default": 5.0,
                    },
                    "battery_energy_density_wh_per_kg": {
                        "type": "number",
                        "description": "电池能量密度（Wh/kg），锂聚合物典型 200",
                        "default": 200.0,
                    },
                },
                "required": ["endurance_min"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shyy_scaling_law",
            "description": (
                "基于 Shyy 2013 + Pennycuick 1996 尺度律估算扑翼飞行器总体参数。"
                "输入起飞重量，输出预测的翼展、翼面积、翼载荷、扑频、最小功率速度、展弦比。"
                "注意：基于自然界飞行生物拟合，工程实现的扑频通常系统性低于预测（电机带宽限制）。"
                "适用场景：根据重量反推合理的总体参数；判断给定参数是否符合尺度律。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "weight_g": {
                        "type": "number",
                        "description": "起飞重量（g）",
                    },
                },
                "required": ["weight_g"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "strouhal_check",
            "description": (
                "计算 Strouhal 数 St = f·A/U 并校验是否在最优区间 0.2-0.4。"
                "扑翼飞行的 St 决定推进效率，超出最优区间会显著降低效率。"
                "若 flap_amplitude_m 未指定，按 wingspan/4 估算（对应 60° 扑动幅角）。"
                "适用场景：给定扑频、翼展、速度，判断推进效率；优化某个参数找最优 St。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "flap_freq_hz": {
                        "type": "number",
                        "description": "扑动频率（Hz）",
                    },
                    "flap_amplitude_m": {
                        "type": "number",
                        "description": "扑动半幅（m），可选；不指定时用 wingspan/4 估算",
                    },
                    "wingspan_mm": {
                        "type": "number",
                        "description": "翼展（mm），用于估算 flap_amplitude",
                    },
                    "flight_speed_m_s": {
                        "type": "number",
                        "description": "飞行速度（m/s）",
                        "default": 5.0,
                    },
                },
                "required": ["flap_freq_hz"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reynolds_check",
            "description": (
                "计算雷诺数 Re = U·c/ν 并判别流态。仿生扑翼飞行器通常处于 Re=100-1e6 的低 Re 范围："
                "Re<1e3 (昆虫前缘涡主导) / Re=1e3-1e4 (中小昆虫) / Re=1e4-1e5 (过渡) / Re>1e5 (鸟类)。"
                "适用场景：判断扑翼气动机理（是否非定常涡主导）；选择合适的气动建模方法。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chord_mm": {
                        "type": "number",
                        "description": "翼弦长（mm）",
                    },
                    "flight_speed_m_s": {
                        "type": "number",
                        "description": "飞行速度（m/s）",
                    },
                    "altitude_m": {
                        "type": "number",
                        "description": "海拔（m），影响空气密度",
                        "default": 0.0,
                    },
                    "temperature_c": {
                        "type": "number",
                        "description": "温度（℃），影响粘度",
                        "default": 20.0,
                    },
                },
                "required": ["chord_mm", "flight_speed_m_s"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "tensor_recall",
            "description": (
                "[创新点 3] 基于 4 阶张量 CP 分解 + KNN 的方案候选粗筛。"
                "用嵌入向量空间检索，速度快（毫秒级）、覆盖广，从 39 个 FWMAV 中召回 Top-K 候选。"
                "注意：粗筛后建议用创新点 2 的物理工具（hassanalian_weight 等）做精排校验。"
                "适用场景：B1/B2 类方案推荐题，先粗筛再精排是论文核心范式。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "weight_g": {"type": "number", "description": "目标重量约束（g）"},
                    "wingspan_mm": {"type": "number", "description": "目标翼展（mm）"},
                    "frequency_hz": {"type": "number", "description": "目标扑频（Hz）"},
                    "speed_max_m_s": {"type": "number", "description": "目标最大速度（m/s）"},
                    "endurance_s": {"type": "number", "description": "目标续航（秒）"},
                    "can_hover": {"type": "boolean", "description": "是否需要悬停能力"},
                    "mission": {
                        "type": "string",
                        "enum": ["research", "task", "maneuver", "performance", "other"],
                        "description": "任务大类（research=研究/验证, task=侦察/巡航/监测, maneuver=高机动/特技, performance=高效率/长航时, other=表演/教学）",
                    },
                    "top_k": {"type": "integer", "description": "返回的候选数", "default": 10},
                },
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "tensor_recall",
            "description": (
                "[创新点 3] 基于 4 阶张量 CP 分解 + KNN 的方案候选粗筛。"
                "用嵌入向量空间检索，速度快（毫秒级）、覆盖广，从 39 个 FWMAV 中召回 Top-K 候选。"
                "注意：粗筛后建议用创新点 2 的物理工具（hassanalian_weight 等）做精排校验。"
                "适用场景：B1/B2 类方案推荐题，先粗筛再精排是论文核心范式。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "weight_g": {"type": "number", "description": "目标重量约束（g）"},
                    "wingspan_mm": {"type": "number", "description": "目标翼展（mm）"},
                    "frequency_hz": {"type": "number", "description": "目标扑频（Hz）"},
                    "speed_max_m_s": {"type": "number", "description": "目标最大速度（m/s）"},
                    "endurance_s": {"type": "number", "description": "目标续航（秒）"},
                    "can_hover": {"type": "boolean", "description": "是否需要悬停能力"},
                    "mission": {
                        "type": "string",
                        "enum": ["research", "task", "maneuver", "performance", "other"],
                        "description": "任务大类（research=研究/验证, task=侦察/巡航/监测, maneuver=高机动/特技, performance=高效率/长航时, other=表演/教学）",
                    },
                    "top_k": {"type": "integer", "description": "返回的候选数", "default": 10},
                },
            },
        },
    },

    # ============ KG 检索工具 ============
    {
        "type": "function",
        "function": {
            "name": "search_fwmav",
            "description": (
                "搜索扑翼飞行器（FlappingWingVehicle）节点。"
                "支持按名称模糊匹配 / 重量范围 / 翼展范围 / 是否能悬停 / 仿生原型筛选。"
                "适用场景：找匹配某些约束的样机；查特定机型的参数。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "名称模糊匹配（如 'DelFly'）"},
                    "weight_max_g": {"type": "number", "description": "重量上限（g）"},
                    "weight_min_g": {"type": "number", "description": "重量下限（g）"},
                    "wingspan_max_mm": {"type": "number", "description": "翼展上限（mm）"},
                    "wingspan_min_mm": {"type": "number", "description": "翼展下限（mm）"},
                    "can_hover": {"type": "boolean", "description": "是否能悬停"},
                    "biological_prototype": {
                        "type": "string",
                        "description": "仿生原型名（如 '蜂鸟'、'苍蝇'），基于 MIMICS 关系反查",
                    },
                    "limit": {"type": "integer", "description": "最大返回数", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_organism",
            "description": (
                "搜索生物原型（Organism）节点 - BioBridge 双层本体的生物层。"
                "返回该生物的体重、翼展、扑频、悬停能力等关键参数。"
                "适用场景：查蜂鸟/苍蝇/海鸥等生物的真实飞行参数；判断『任务是否符合生物原型能力』。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "生物名称（如 '蜂鸟', '苍蝇'）"},
                    "can_hover": {"type": "boolean", "description": "是否能悬停"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_mimics_path",
            "description": (
                "查询 MIMICS 仿生映射边的 4 类相似度分数（aero/kinematics/morphology/scale）。"
                "BioBridge 创新点 1 双层本体的核心查询接口。"
                "适用场景：分析某机型 vs 某生物的仿生主导维度；找某类相似度主导的机型。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fwmav_name": {"type": "string", "description": "飞行器名"},
                    "organism_name": {"type": "string", "description": "生物原型名"},
                    "dominant_type": {
                        "type": "string",
                        "enum": ["aero", "kinematics", "morphology", "scale"],
                        "description": "主导仿生类型",
                    },
                    "min_score": {
                        "type": "number",
                        "description": "最小相似度阈值",
                        "default": 0.5,
                    },
                },
            },
        },
    },
]


# 工具注册表合并
ALL_TOOLS = {**PHYSICS_TOOLS, **KG_TOOLS, "tensor_recall": tensor_recall_tool}


def call_tool(tool_name: str, **kwargs) -> dict:
    """统一工具调度入口."""
    if tool_name not in ALL_TOOLS:
        return {"error": f"未知工具: {tool_name}", "available": list(ALL_TOOLS.keys())}
    try:
        return ALL_TOOLS[tool_name](**kwargs)
    except TypeError as e:
        return {"error": f"参数错误: {e}", "tool": tool_name}
    except Exception as e:
        return {"error": f"工具运行失败: {e}", "tool": tool_name}


if __name__ == "__main__":
    # 打印所有工具规格
    print(f"=== BioBridge Tool Suite ({len(TOOL_SPECS)} tools) ===\n")
    for spec in TOOL_SPECS:
        f = spec["function"]
        print(f"📦 {f['name']}")
        print(f"   {f['description'][:80]}...")
        params = f["parameters"]["properties"]
        print(f"   Params: {list(params.keys())}\n")
