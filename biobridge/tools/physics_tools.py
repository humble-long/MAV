"""BioBridge 创新点 2 的 4 个物理工具.

每个工具都是纯 Python 函数（无外部依赖），输入参数 dict、返回结构化结果 dict。
- hassanalian_weight: 重量分数估算（输入续航/载重 → 输出起飞重量）
- shyy_scaling_law:   尺度律（输入重量 → 输出扑频/翼展/翼面积/翼载荷）
- strouhal_check:     Strouhal 数校验（输入扑频/扑幅/速度 → 输出 St 值 + 是否合理）
- reynolds_check:     雷诺数校验（输入翼弦/速度 → 输出 Re 值 + 流态判别）

所有工具均不依赖外部 API，可被 LLM 通过 Function Calling 调用。
"""

from __future__ import annotations
import math
from typing import Optional


# ============================================================
# 1. Hassanalian 重量分数估算
# ============================================================

def hassanalian_weight(
    endurance_min: float,
    payload_g: float = 0.0,
    avionics_g: float = 5.0,
    cruise_power_w: Optional[float] = None,
    battery_energy_density_wh_per_kg: float = 200.0,
    f_struct: float = 0.35,
    f_propulsion: float = 0.15,
    f_battery: Optional[float] = None,
) -> dict:
    """基于 Hassanalian 2017 (Meccanica) 重量分数模型估算扑翼飞行器起飞重量.

    模型：W_total = (W_payload + W_avionics) / (1 - f_struct - f_propulsion - f_battery)
    其中 f_battery 由续航需求 + 电池能量密度反推。

    Args:
        endurance_min: 任务续航需求（分钟）
        payload_g: 任务载荷（g）
        avionics_g: 航电+控制系统重量（g），默认 5g
        cruise_power_w: 巡航功率（W），不指定时按 0.5 * W_total^(1/2) 经验估算
        battery_energy_density_wh_per_kg: 电池能量密度（Wh/kg），默认锂聚合物 200
        f_struct: 结构重量分数，默认 0.35（典型仿鸟扑翼机 30-45%）
        f_propulsion: 推进系统重量分数，默认 0.15
        f_battery: 电池重量分数；不指定时由续航 + 功率反推

    Returns:
        dict 包含：
        - total_weight_g: 估算的起飞重量
        - battery_g: 电池重量
        - struct_g, propulsion_g, payload_g, avionics_g: 各子系统重量
        - f_battery, f_avionics_payload: 各重量分数
        - feasible: 是否物理可达（f_battery + f_struct + f_propulsion < 0.95）
        - notes: 说明文字
    """
    notes = []

    # 经验巡航功率 P ∝ W^(1/2)（受 Liu 2006 启发的简化）
    if cruise_power_w is None:
        # 假设起飞重量 100g 对应 5W 巡航功率，按 sqrt 缩放
        # 这只是初值，迭代时会更新
        cruise_power_w = 5.0
        notes.append("cruise_power_w 未指定，使用 5W 初值")

    # 迭代求解：电池分数依赖于总重量，但功率又依赖总重量
    W_total = (payload_g + avionics_g) / max(1 - f_struct - f_propulsion - 0.3, 0.05)  # 初值
    for _ in range(20):  # 通常 5-10 次收敛
        # 电池能量需求（Wh）
        E_required_wh = cruise_power_w * (endurance_min / 60.0)
        # 电池重量（g）= E / energy_density / (kg→g 换算)
        battery_g_raw = E_required_wh / (battery_energy_density_wh_per_kg / 1000.0)
        f_battery_calc = battery_g_raw / W_total if W_total > 0 else 1.0

        # 检查物理上下限
        f_battery_calc = min(max(f_battery_calc, 0.05), 0.7)

        # 用 f_battery 推回总重量
        f_other = 1 - f_struct - f_propulsion - f_battery_calc
        if f_other <= 0:
            notes.append(f"f_struct + f_propulsion + f_battery 已超 1，物理不可行")
            return {
                "total_weight_g": None,
                "battery_g": None,
                "feasible": False,
                "notes": "; ".join(notes) + "（建议提高电池能量密度或缩短续航）",
            }
        new_W = (payload_g + avionics_g) / f_other

        # 更新巡航功率（按 sqrt 缩放）
        # P_W = 0.05 * W_total（经验：仿鸟 100g 约 5W）
        cruise_power_w = 0.05 * new_W

        if abs(new_W - W_total) < W_total * 0.01:
            break
        W_total = new_W

    f_battery = f_battery_calc
    battery_g = W_total * f_battery
    struct_g = W_total * f_struct
    propulsion_g = W_total * f_propulsion
    f_avionics_payload = (payload_g + avionics_g) / W_total

    feasible = f_battery + f_struct + f_propulsion < 0.95

    if W_total > 5000:
        notes.append("起飞重量超过 5kg，超出常见仿生扑翼机范围")
    if W_total < 0.5:
        notes.append("起飞重量低于 0.5g，进入昆虫尺度，需考虑压电驱动")

    return {
        "total_weight_g": round(W_total, 2),
        "battery_g": round(battery_g, 2),
        "struct_g": round(struct_g, 2),
        "propulsion_g": round(propulsion_g, 2),
        "payload_g": round(payload_g, 2),
        "avionics_g": round(avionics_g, 2),
        "f_battery": round(f_battery, 3),
        "f_avionics_payload": round(f_avionics_payload, 3),
        "estimated_cruise_power_w": round(cruise_power_w, 2),
        "battery_energy_required_wh": round(cruise_power_w * endurance_min / 60.0, 2),
        "feasible": feasible,
        "notes": "; ".join(notes) if notes else "正常",
    }


# ============================================================
# 2. Shyy 尺度律（重量 → 总体参数）
# ============================================================

def shyy_scaling_law(weight_g: float) -> dict:
    """基于 Shyy 2013 (An Introduction to Flapping Wing Aerodynamics) 尺度律估算扑翼飞行器总体参数.

    主要拟合公式（来自 Shyy 2013 §3 + Pennycuick 1996 + Greenewalt 1975 在飞行
    生物 + 工程样机数据上的回归）:

        翼展 b (m)           ≈ 1.17 · m^(0.39)        [m in kg]
        翼面积 S (m²)        ≈ 0.16 · m^(2/3)
        翼载荷 W/S (N/m²)    ≈ m·g / S
        扑频 f (Hz)          ≈ 3.87 · m^(-1/3)        [典型鸟类扑频 — Pennycuick 1996]
        最小功率速度 V_mp (m/s) ≈ 4.77 · m^(1/6)

    注意公式中 m 单位为 kg；本函数输入 weight_g 内部转换。

    Args:
        weight_g: 起飞重量（g）

    Returns:
        dict 包含估算的总体参数 + 物理一致性 notes
    """
    if weight_g <= 0:
        return {"error": "weight_g 必须 > 0"}

    notes = []
    if weight_g < 0.05:
        notes.append("低于昆虫极小尺度（< 0.05g），尺度律外推可能失真")
    if weight_g > 12000:
        notes.append("超过最大鸟类尺度（> 12kg），扑翼飞行不可行")

    m_kg = weight_g / 1000.0  # 公式输入用 kg

    # 翼展 (m) — Shyy 2013 §3 + Greenewalt 1975 鸟类拟合
    wingspan_m = 1.17 * (m_kg ** 0.39)
    wingspan_cm = wingspan_m * 100
    wingspan_mm = wingspan_m * 1000

    # 翼面积 (m²) — 几何相似下 S ∝ m^(2/3)
    wing_area_m2 = 0.16 * (m_kg ** (2.0 / 3.0))
    wing_area_cm2 = wing_area_m2 * 10000

    # 翼载荷 (N/m²) = mg/S
    wing_loading_N_m2 = (m_kg * 9.81) / wing_area_m2

    # 扑频 (Hz) — Pennycuick 1996 鸟类拟合
    flap_freq_hz = 3.87 * (m_kg ** (-1.0 / 3.0))

    # 最小功率速度 (m/s) — Pennycuick 1996
    min_power_speed_m_s = 4.77 * (m_kg ** (1.0 / 6.0))

    # 展弦比 AR = b²/S
    aspect_ratio = (wingspan_m * wingspan_m) / wing_area_m2

    return {
        "weight_g": round(weight_g, 3),
        "wingspan_cm": round(wingspan_cm, 2),
        "wingspan_mm": round(wingspan_mm, 1),
        "wing_area_cm2": round(wing_area_cm2, 2),
        "wing_loading_N_per_m2": round(wing_loading_N_m2, 2),
        "wing_loading_g_per_cm2": round(wing_loading_N_m2 / 9.81 / 10, 3),
        "flap_freq_hz": round(flap_freq_hz, 2),
        "min_power_speed_m_s": round(min_power_speed_m_s, 2),
        "aspect_ratio": round(aspect_ratio, 2),
        "scaling_exponent_freq": -1/3,
        "scaling_exponent_span": 0.39,
        "notes": "; ".join(notes) if notes else "正常",
        "source": "Shyy 2013 §3; Pennycuick 1996; Greenewalt 1975 (公式拟合自然界飞行生物)",
        "caveat": "工程实现的扑翼机扑频通常比尺度律预测系统性偏低（电机带宽限制）",
    }


# ============================================================
# 3. Strouhal 数校验
# ============================================================

def strouhal_check(
    flap_freq_hz: float,
    flap_amplitude_m: Optional[float] = None,
    wingspan_mm: Optional[float] = None,
    flight_speed_m_s: float = 5.0,
    optimal_min: float = 0.2,
    optimal_max: float = 0.4,
) -> dict:
    """计算 Strouhal 数并校验是否在最优区间.

    St = f * A / U
    其中 A 为扑动半幅（m）。
    扑翼飞行的 St 最优区间为 0.2 ~ 0.4（Triantafyllou 等的经典结果）。
    若不指定 flap_amplitude_m，按 wingspan/4 经验估算（典型 60° 扑动幅角下的端点位移）。

    Args:
        flap_freq_hz: 扑动频率（Hz）
        flap_amplitude_m: 扑动半幅（m），可选
        wingspan_mm: 翼展（mm），用于在 amplitude 缺失时估算
        flight_speed_m_s: 飞行速度（m/s）
        optimal_min, optimal_max: 最优区间，默认 0.2-0.4

    Returns:
        dict 包含 strouhal_number / 是否最优 / 建议
    """
    if flap_freq_hz <= 0 or flight_speed_m_s <= 0:
        return {"error": "flap_freq_hz 和 flight_speed_m_s 必须 > 0"}

    notes = []

    # 估算 flap_amplitude
    if flap_amplitude_m is None:
        if wingspan_mm is None:
            return {"error": "flap_amplitude_m 与 wingspan_mm 至少给一个"}
        # 经验：扑动半幅 ≈ wingspan/4（对应 60° 扑动幅角）
        flap_amplitude_m = (wingspan_mm / 1000.0) / 4.0
        notes.append(f"flap_amplitude_m 未指定，按 wingspan/4 估算 = {flap_amplitude_m:.3f}m")

    St = flap_freq_hz * flap_amplitude_m / flight_speed_m_s

    is_optimal = optimal_min <= St <= optimal_max
    if St < optimal_min:
        verdict = "推进效率偏低（扑频不足或扑幅不足）"
    elif St > optimal_max:
        verdict = "推进效率偏低（扑频过高或速度不足）"
    else:
        verdict = "落入扑翼飞行最优 Strouhal 区间"

    return {
        "strouhal_number": round(St, 3),
        "is_optimal": is_optimal,
        "optimal_range": [optimal_min, optimal_max],
        "verdict": verdict,
        "flap_freq_hz": flap_freq_hz,
        "flap_amplitude_m_used": round(flap_amplitude_m, 4),
        "flight_speed_m_s": flight_speed_m_s,
        "notes": "; ".join(notes) if notes else "",
        "source": "Triantafyllou 1991; Shyy 2013 §1.3",
    }


# ============================================================
# 4. 雷诺数校验
# ============================================================

def reynolds_check(
    chord_mm: float,
    flight_speed_m_s: float,
    altitude_m: float = 0.0,
    temperature_c: float = 20.0,
) -> dict:
    """计算雷诺数 Re 并判别流态.

    Re = ρ * U * c / μ = U * c / ν
    其中 ν 为运动粘度（m²/s）。
    流态判别（仿生扑翼经验）:
        Re < 1,000:    强非定常涡 / 高粘性效应（昆虫尺度）
        1,000 < Re < 10,000:  非定常涡为主（小昆虫到中等昆虫）
        10,000 < Re < 100,000: 过渡区（大昆虫到小鸟）
        100,000 < Re < 1,000,000: 鸟类尺度
        Re > 1,000,000: 大型鸟类 / 滑翔飞行器

    Args:
        chord_mm: 翼弦长（mm）
        flight_speed_m_s: 飞行速度（m/s）
        altitude_m: 海拔（m），影响空气密度，默认 0
        temperature_c: 温度（℃），影响粘度，默认 20

    Returns:
        dict 包含 Re / 流态判别
    """
    if chord_mm <= 0 or flight_speed_m_s <= 0:
        return {"error": "chord_mm 和 flight_speed_m_s 必须 > 0"}

    # 空气运动粘度（m²/s）随温度变化（Sutherland 公式简化）
    # 20℃ 海平面: ν ≈ 1.516e-5
    # 海拔越高，密度越低，运动粘度越大
    nu_sea_level = 1.516e-5  # 20℃
    # 温度修正（Sutherland）
    T_K = temperature_c + 273.15
    T_ref = 293.15
    nu_temp_factor = (T_K / T_ref) ** 1.5
    # 海拔修正（密度按 ICAO 标准大气简化）
    altitude_factor = math.exp(altitude_m / 8400.0)  # 标度高度 8.4km
    nu = nu_sea_level * nu_temp_factor * altitude_factor

    chord_m = chord_mm / 1000.0
    Re = flight_speed_m_s * chord_m / nu

    if Re < 1000:
        regime = "高粘性低 Re 区（昆虫尺度）"
        characteristic = "前缘涡稳定附着，非定常效应主导，传统翼型理论失效"
    elif Re < 10000:
        regime = "低 Re 非定常涡区（中小昆虫尺度）"
        characteristic = "前缘涡 + 翼尖涡 + 尾迹涡相互耦合，扑翼气动机理复杂"
    elif Re < 100000:
        regime = "过渡区（大昆虫到小鸟尺度）"
        characteristic = "层流-湍流转捩，气动性能对雷诺数敏感"
    elif Re < 1000000:
        regime = "鸟类尺度低 Re 区"
        characteristic = "传统翼型 + 部分非定常效应，可借鉴常规航空气动设计"
    else:
        regime = "高 Re 区（大鸟 / 大型扑翼机）"
        characteristic = "趋近常规航空尺度，扑动主要起推进作用"

    return {
        "reynolds_number": round(Re, 0),
        "reynolds_log10": round(math.log10(Re), 2),
        "regime": regime,
        "characteristic": characteristic,
        "chord_mm": chord_mm,
        "flight_speed_m_s": flight_speed_m_s,
        "kinematic_viscosity_m2_per_s": nu,
        "altitude_m": altitude_m,
        "temperature_c": temperature_c,
        "source": "Shyy 2013 §1.3; ICAO standard atmosphere",
    }


# ============================================================
# 工具注册表（供 Function Calling 调用）
# ============================================================

PHYSICS_TOOLS = {
    "hassanalian_weight": hassanalian_weight,
    "shyy_scaling_law": shyy_scaling_law,
    "strouhal_check": strouhal_check,
    "reynolds_check": reynolds_check,
}


if __name__ == "__main__":
    # 自检：跑 4 个工具的真实样机案例
    print("=" * 60)
    print("Tool 1: hassanalian_weight - 30 km 续航 + 50 g 载重")
    print("=" * 60)
    # 30 km @ 12 m/s = 41.7 分钟
    result = hassanalian_weight(endurance_min=42, payload_g=50)
    for k, v in result.items():
        print(f"  {k:30s}: {v}")

    print()
    print("=" * 60)
    print("Tool 2: shyy_scaling_law - DelFly Nimble (28.2 g)")
    print("=" * 60)
    result = shyy_scaling_law(weight_g=28.2)
    for k, v in result.items():
        print(f"  {k:30s}: {v}")

    print()
    print("=" * 60)
    print("Tool 3: strouhal_check - DelFly Nimble (17 Hz, span 330mm, 7 m/s)")
    print("=" * 60)
    result = strouhal_check(flap_freq_hz=17, wingspan_mm=330, flight_speed_m_s=7)
    for k, v in result.items():
        print(f"  {k:30s}: {v}")

    print()
    print("=" * 60)
    print("Tool 4: reynolds_check - DelFly Nimble (chord 140 mm, 7 m/s)")
    print("=" * 60)
    result = reynolds_check(chord_mm=140, flight_speed_m_s=7)
    for k, v in result.items():
        print(f"  {k:30s}: {v}")
