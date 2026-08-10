#!/usr/bin/env python3
"""P2-3: 补充 wing_pairs / has_tail / can_glide 三个字段.

给 39 个 FlappingWingVehicle 和 23 个 Organism 节点各加三个字段:
  wing_pairs : int  1=双翼(单对)  2=四翼(双对)
  has_tail   : bool 是否有尾翼/尾控制面
  can_glide  : bool 是否具备滑翔/扑滑结合能力

数据来源: 文献 + 公开工程资料, 硬编码, 幂等可重跑.
"""

from __future__ import annotations
import os
from neo4j import GraphDatabase

URI      = "bolt://localhost:7687"
USER     = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")

# ──────────────────────────────────────────────
# Organism 数据 (23 个)
# wing_pairs: 1=单对翼, 2=双对翼
# ──────────────────────────────────────────────
ORGANISM_DATA: dict[str, dict] = {
    "乌鸦":              {"wing_pairs": 1, "has_tail": True,  "can_glide": True},
    "凤凰":              {"wing_pairs": 1, "has_tail": True,  "can_glide": True},
    "大型鸟类":           {"wing_pairs": 1, "has_tail": True,  "can_glide": True},
    "昆虫":              {"wing_pairs": 2, "has_tail": False, "can_glide": False},
    "昆虫 (布局)":        {"wing_pairs": 2, "has_tail": False, "can_glide": False},
    "海鸠 (Guillemot)":  {"wing_pairs": 1, "has_tail": True,  "can_glide": True},
    "海鸥":              {"wing_pairs": 1, "has_tail": True,  "can_glide": True},
    "狐蝠":              {"wing_pairs": 1, "has_tail": False, "can_glide": False},
    "独角仙":             {"wing_pairs": 2, "has_tail": False, "can_glide": False},
    "甲虫":              {"wing_pairs": 2, "has_tail": False, "can_glide": False},
    "甲虫 (Beetle)":     {"wing_pairs": 2, "has_tail": False, "can_glide": False},
    "苍蝇":              {"wing_pairs": 1, "has_tail": False, "can_glide": False},
    "蜂鸟":              {"wing_pairs": 1, "has_tail": True,  "can_glide": False},
    "蜜蜂":              {"wing_pairs": 2, "has_tail": False, "can_glide": False},
    "蜻蜓":              {"wing_pairs": 2, "has_tail": False, "can_glide": True},
    "蝙蝠":              {"wing_pairs": 1, "has_tail": False, "can_glide": False},
    "蝴蝶":              {"wing_pairs": 2, "has_tail": False, "can_glide": True},
    "金鹰":              {"wing_pairs": 1, "has_tail": True,  "can_glide": True},
    "隼":               {"wing_pairs": 1, "has_tail": True,  "can_glide": True},
    "飞鱼":              {"wing_pairs": 1, "has_tail": False, "can_glide": True},
    "鸟类":              {"wing_pairs": 1, "has_tail": True,  "can_glide": True},
    "鸮":               {"wing_pairs": 1, "has_tail": True,  "can_glide": True},
    "鸽子":              {"wing_pairs": 1, "has_tail": True,  "can_glide": True},
}

# ──────────────────────────────────────────────
# FWMAV 数据 (39 个)
# ──────────────────────────────────────────────
FWMAV_DATA: dict[str, dict] = {
    # 独角仙仿生 ─ 双对翼，无尾，不滑翔
    "Allomyrina dichotoma (仿独角仙)": {"wing_pairs": 2, "has_tail": False, "can_glide": False},

    # Festo 蝙蝠机器人 ─ 单对翼大翼展，无尾，能被动滑翔
    "Bionic Flying Fox":              {"wing_pairs": 1, "has_tail": False, "can_glide": True},

    # Festo 蜻蜓机器人 ─ 双对翼，无尾
    "BionicOpter":                    {"wing_pairs": 2, "has_tail": False, "can_glide": False},

    # 大型鸟类扑翼机，有尾，可滑翔
    "C-GPTR (Mr. Bill)":              {"wing_pairs": 1, "has_tail": True,  "can_glide": True},

    # 蜂鸟悬停，单对翼，无尾
    "Colibri":                        {"wing_pairs": 1, "has_tail": False, "can_glide": False},

    # DelFly 系列: X 形双对翼
    # Explorer/I/II/Micro 有泡沫尾翼; Nimble 专门去掉尾翼
    "DelFly Explorer":                {"wing_pairs": 2, "has_tail": True,  "can_glide": False},
    "DelFly I":                       {"wing_pairs": 2, "has_tail": True,  "can_glide": False},
    "DelFly II":                      {"wing_pairs": 2, "has_tail": True,  "can_glide": False},
    "DelFly Micro":                   {"wing_pairs": 2, "has_tail": True,  "can_glide": False},
    "DelFly Nimble":                  {"wing_pairs": 2, "has_tail": False, "can_glide": False},

    # Entomopter: 化学肌肉驱动四翼概念机
    "Entomopter":                     {"wing_pairs": 2, "has_tail": False, "can_glide": False},

    # 仿昆虫无尾翼：名字已说明无尾，单对翼
    "Insect-mimicking (仿昆虫无尾翼)": {"wing_pairs": 1, "has_tail": False, "can_glide": False},

    # KAIST 甲虫仿生：仅仿后翅单对
    "KUBeetle-S":                     {"wing_pairs": 1, "has_tail": False, "can_glide": False},

    # Arizona 小型鸟类扑翼机
    "MAV (University of Arizona)":    {"wing_pairs": 1, "has_tail": True,  "can_glide": False},

    # Mentor: 大型鸟类扑翼机，有尾，可滑翔
    "Mentor":                         {"wing_pairs": 1, "has_tail": True,  "can_glide": True},

    # 蝙蝠仿生，膜翼单对，无尾
    "Microbat":                       {"wing_pairs": 1, "has_tail": False, "can_glide": False},

    # AeroVironment 蜂鸟机器人，单对翼，无尾
    "Nano Hummingbird":               {"wing_pairs": 1, "has_tail": False, "can_glide": False},

    # Stanford 鸽子机器人，折叠羽翼，有尾，可滑翔
    "PigeonBot":                      {"wing_pairs": 1, "has_tail": True,  "can_glide": True},

    # 大型鸟类扑翼机
    "Richter (Ornithopter)":          {"wing_pairs": 1, "has_tail": True,  "can_glide": True},

    # Harvard RoboBee 系列 ─ 昆虫尺度单对翼，无尾
    "RoboBee (Hybrid Aerial-Aquatic)":{"wing_pairs": 1, "has_tail": False, "can_glide": False},
    "RoboBee (Original)":             {"wing_pairs": 1, "has_tail": False, "can_glide": False},
    "RoboBee X-Wing":                 {"wing_pairs": 2, "has_tail": False, "can_glide": False},

    # 乌鸦仿生，单对翼，无尾，可滑翔
    "RoboRaven":                      {"wing_pairs": 1, "has_tail": False, "can_glide": True},

    # Purdue 蜂鸟机器人（与下方区分）
    "Robotic Hummingbird":            {"wing_pairs": 1, "has_tail": False, "can_glide": False},

    # Festo SmartBird: 海鸥仿生，有尾，可滑翔
    "SmartBird":                      {"wing_pairs": 1, "has_tail": True,  "can_glide": True},

    # 蜻蜓仿生，双对翼，无尾
    "TechJect Dragonfly":             {"wing_pairs": 2, "has_tail": False, "can_glide": False},

    # 小型鸟类扑翼机
    "USTBird":                        {"wing_pairs": 1, "has_tail": True,  "can_glide": False},

    # 主动折叠变形：鸟类仿生，有尾，可滑翔
    "主动折叠变形扑翼飞行器":              {"wing_pairs": 1, "has_tail": True,  "can_glide": True},

    # 云鸮：鸮仿生大型扑翼机
    "云鸮":                            {"wing_pairs": 1, "has_tail": True,  "can_glide": True},

    # 信鸽：鸽子仿生
    "信鸽":                            {"wing_pairs": 1, "has_tail": True,  "can_glide": True},

    # 凤凰仿生鸟
    "凤凰 (Phoenix)":                  {"wing_pairs": 1, "has_tail": True,  "can_glide": True},

    # 四动力装置可悬停：四翼悬停设计
    "四动力装置可悬停扑翼飞行器":           {"wing_pairs": 2, "has_tail": False, "can_glide": False},

    # 大中型仿鸟扑翼机
    "大中型仿鸟扑翼飞行器 (Large-Scale Ornithopter)": {
        "wing_pairs": 1, "has_tail": True, "can_glide": True
    },

    # 小隼：隼仿生
    "小隼 (Little Falcon)":            {"wing_pairs": 1, "has_tail": True,  "can_glide": True},

    # 微机械飞行昆虫 (Berkeley MFI 系): 单对翼
    "微机械飞行昆虫 (MFI)":              {"wing_pairs": 1, "has_tail": False, "can_glide": False},

    # 机器海鸥
    "机器海鸥":                          {"wing_pairs": 1, "has_tail": True,  "can_glide": True},

    # 空中仿生机器人：大型鸟类扑翼
    "空中仿生机器人":                      {"wing_pairs": 1, "has_tail": True,  "can_glide": False},

    # Purdue 蜂鸟机器人
    "蜂鸟机器人 (Purdue Hummingbird)":   {"wing_pairs": 1, "has_tail": False, "can_glide": False},

    # 金鹰仿生大型扑翼机
    "金鹰":                            {"wing_pairs": 1, "has_tail": True,  "can_glide": True},
}


def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    updated_orgs = 0
    updated_fwmav = 0
    skipped = []

    with driver.session() as sess:
        # ── Organism ──
        print("=== Organism 节点 ===")
        for name, props in ORGANISM_DATA.items():
            res = sess.run(
                "MATCH (o:Organism {name: $name}) SET o += $props RETURN o.name",
                name=name, props=props
            )
            if res.single():
                updated_orgs += 1
                print(f"  ✅ {name:30s}  wing_pairs={props['wing_pairs']}  "
                      f"has_tail={str(props['has_tail']):5s}  can_glide={props['can_glide']}")
            else:
                skipped.append(f"Organism/{name}")
                print(f"  ⚠ 未找到: {name}")

        # ── FWMAV ──
        print("\n=== FlappingWingVehicle 节点 ===")
        for name, props in FWMAV_DATA.items():
            res = sess.run(
                "MATCH (v:FlappingWingVehicle {name: $name}) SET v += $props RETURN v.name",
                name=name, props=props
            )
            if res.single():
                updated_fwmav += 1
                print(f"  ✅ {name:52s}  wing_pairs={props['wing_pairs']}  "
                      f"has_tail={str(props['has_tail']):5s}  can_glide={props['can_glide']}")
            else:
                skipped.append(f"FWMAV/{name}")
                print(f"  ⚠ 未找到: {name}")

    driver.close()
    print(f"\n=== 完成 ===")
    print(f"  Organism 更新: {updated_orgs}/{len(ORGANISM_DATA)}")
    print(f"  FWMAV    更新: {updated_fwmav}/{len(FWMAV_DATA)}")
    if skipped:
        print(f"  未匹配节点: {skipped}")


if __name__ == "__main__":
    main()
