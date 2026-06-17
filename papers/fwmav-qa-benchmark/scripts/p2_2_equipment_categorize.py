#!/usr/bin/env python3
"""P2-2: 给 108 个 Equipment 节点加 category 分类标签.

不拆节点（避免破坏现有 EQUIPPED_WITH 边），仅增加属性.

分类粒度（10 类）:
    actuator       — 执行器（电机、舵机、伺服）
    power          — 电源（电池、太阳能）
    sensor         — 传感器（IMU、加速度、陀螺仪、磁、光流等）
    flight_control — 飞控/微控制器/自动驾驶仪
    communication  — 通信（无线模块、Wi-Fi、蓝牙、接收机）
    structure      — 机身/骨架（碳纤维、ABS、轻木）
    wing           — 机翼/翼面材料
    payload        — 载荷（相机、影像、有效载荷）
    transmission   — 传动（齿轮、传动带、连杆）
    other          — 其他/不分类
"""

from __future__ import annotations
import re
from datetime import datetime
import os
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD", "your-password-here")


# 关键词 → category 映射（注意顺序：先匹配上的优先）
# 中英文关键词同时支持
RULES = [
    # actuator
    ("actuator", ["电机", "Motor", "motor", "舵机", "伺服", "无刷", "空心杯",
                  "RCM驱动器", "DC电机", "Brushed", "Brushless", "actuator"]),
    # power
    ("power", ["电池", "battery", "锂电", "镍镉", "太阳能", "燃料", "升压", "电调",
               "ESC", "CO2", "Gas Generator", "电解板"]),
    # sensor
    ("sensor", ["传感器", "sensor", "IMU", "陀螺仪", "gyro", "加速度", "accelerometer",
                "光流", "光纤", "磁场", "霍尔", "皮托管", "应变片", "GPS",
                "超声波", "MEMS", "立体视觉", "MPU", "红外标记"]),
    # flight_control
    ("flight_control", ["飞控", "自动驾驶仪", "autopilot", "飞控板", "MWC", "Pixhawk",
                        "PixRacer", "Arduino", "微控制器", "controller", "ARM",
                        "PIC", "STM32", "MARC", "可编程微型计算机", "控制板",
                        "控制电路板", "姿态控制系统"]),
    # communication
    ("communication", ["无线", "Wi-Fi", "蓝牙", "Bluetooth", "wireless", "接收机",
                       "遥控", "GHz"]),
    # structure
    ("structure", ["机身", "frame", "骨架", "fuselage", "ABS", "聚酰亚胺", "弯曲铰链",
                   "碳纤维杆", "碳纤维板", "碳纤维骨架", "碳管", "轻木"]),
    # wing
    ("wing", ["机翼", "wing", "翼面", "翼", "尾翼", "副翼", "Aileron", "Mylar",
              "羽毛", "薄膜", "聚酯薄膜", "聚合物机翼"]),
    # payload
    ("payload", ["相机", "摄像头", "摄像装置", "云台", "imaging", "camera",
                 "高清", "视觉相机", "模拟摄像头", "可见光", "红外成像"]),
    # transmission
    ("transmission", ["齿轮", "gear", "传动带", "传动", "transmission", "减速装置",
                      "减速器", "连杆机构"]),
]


def classify(name: str) -> tuple[str, str]:
    """返回 (category, matched_keyword)."""
    for cat, keywords in RULES:
        for kw in keywords:
            if kw.lower() in name.lower():
                return cat, kw
    return "other", ""


def main():
    print("准备为 108 个 Equipment 节点打 category 标签...")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    today = datetime.now().strftime("%Y-%m-%d")
    classified = {}
    updated = 0

    with driver.session() as sess:
        # 取所有 Equipment
        res = sess.run(
            "MATCH (n:Equipment) RETURN n.name AS name ORDER BY name"
        )
        names = [r["name"] for r in res]

        for name in names:
            cat, kw = classify(name)
            classified.setdefault(cat, []).append((name, kw))

            # 写回
            sess.run(
                """
                MATCH (n:Equipment {name:$n})
                SET n.category = $cat,
                    n.classified_at = $today,
                    n.classified_keyword = $kw
                """,
                n=name,
                cat=cat,
                today=today,
                kw=kw,
            )
            updated += 1

    driver.close()

    # 打印统计
    print(f"\n=== 分类统计 ===")
    for cat in sorted(classified.keys(), key=lambda c: -len(classified[c])):
        items = classified[cat]
        sample = ", ".join(n for n, _ in items[:5])
        print(f"  {cat:15s}: {len(items):3d} 个   样例: {sample}")

    # 标记需要人工 review 的 'other'
    others = classified.get("other", [])
    if others:
        print(f"\n⚠ 'other' 类的 {len(others)} 个节点（建议人工 review）：")
        for n, _ in others:
            print(f"    - {n}")

    print(f"\n=== 完成: {updated}/{len(names)} ===")


if __name__ == "__main__":
    main()
