# FWMAV KG 数据完整性诊断报告

> 生成时间：2026-06-16 22:19:08
> Neo4j: `bolt://localhost:7687`

---

## 1. 节点规模

| 标签 | 数量 |
|---|---|
| KGEntity+Equipment | 108 |
| KGEntity+Application | 54 |
| KGEntity+DriveMechanism | 44 |
| KGEntity+FlappingWingVehicle | 39 |
| KGEntity+Organization | 33 |
| KGEntity+Reference | 31 |
| KGEntity+Organism | 23 |

## 2. 关系规模

| 关系类型 | 数量 |
|---|---|
| EQUIPPED_WITH | 117 |
| SUITABLE_FOR | 56 |
| MIMICS | 50 |
| HAS_DRIVE_MECHANISM | 46 |
| DEVELOPED_BY | 43 |
| HAS_REFERENCE | 32 |
| FUNDED_BY | 1 |

## 3. 属性命名一致性问题（重灾区）

### 3.1 重量属性 — 三种命名共存
| 字段 | 使用机型数 |
|---|---|
| `weight_total_g` | 14 |
| `weight_empty_g` | 16 |
| `weight_takeoff_g` | 5 |

**建议**: 统一为 `weight_takeoff_g`（缺失时用 empty + 估算 payload 推算）。

### 3.2 续航属性 — 三种单位共存
| 字段 | 使用机型数 |
|---|---|
| `endurance_min` | 11 |
| `endurance_sec` | 2 |
| `endurance_hover_min` | 1 |

**建议**: 统一为 `endurance_s`（秒）+ `endurance_condition` ∈ {hover, cruise, mixed}。

### 3.3 速度属性 — 多种命名共存
| 字段 | 使用机型数 |
|---|---|
| `speed_max_m_s` | 6 |
| `speed_max_km_h` | 2 |
| `speed_m_s` | 1 |
| `speed_forward_m_s` | 1 |
| `speed_side_m_s` | 1 |
| `flight_speed_m_s` | 1 |
| `climb_speed_m_s` | 1 |

**建议**: 统一为 `speed_max_m_s` + `speed_cruise_m_s`。

### 3.4 扑频属性 — 数字 vs 字符串混用
- 作为 **数字** 存储: 14 条
- 作为 **字符串** 存储: 4 条（如 "15-20"）
- 字符串示例:
    - 蜂鸟机器人 (Purdue Hummingbird): "30-40"
    - Allomyrina dichotoma (仿独角仙): "25-50"
    - BionicOpter: "15-20"
    - SmartBird: "2-3"

**建议**: 把字符串区间拆成 `frequency_hz_min` + `frequency_hz_max`，单值赋 min=max。

## 4. 各标签下属性完整度

### FlappingWingVehicle (共 39 个节点，平均完整度 63.5%)

| 节点 | 完整度 | 缺失字段 |
|---|---|---|
| DelFly I | 25% | `wingspan_mm`, `frequency_hz`, `weight_total_g|weight_empty_g|weight_takeoff_g`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| DelFly II | 25% | `wingspan_mm`, `frequency_hz`, `weight_total_g|weight_empty_g|weight_takeoff_g`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| Richter (Ornithopter) | 25% | `wingspan_mm`, `frequency_hz`, `weight_total_g|weight_empty_g|weight_takeoff_g`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| 大中型仿鸟扑翼飞行器 (Large-Scale Ornithopter) | 38% | `frequency_hz`, `weight_total_g|weight_empty_g|weight_takeoff_g`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| 四动力装置可悬停扑翼飞行器 | 38% | `wingspan_mm`, `frequency_hz`, `weight_total_g|weight_empty_g|weight_takeoff_g`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s` |
| MAV (University of Arizona) | 38% | `frequency_hz`, `weight_total_g|weight_empty_g|weight_takeoff_g`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| RoboBee (Hybrid Aerial-Aquatic) | 38% | `frequency_hz`, `weight_total_g|weight_empty_g|weight_takeoff_g`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| 凤凰 (Phoenix) | 50% | `frequency_hz`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| 机器海鸥 | 50% | `frequency_hz`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| Bionic Flying Fox | 50% | `frequency_hz`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| C-GPTR (Mr. Bill) | 50% | `frequency_hz`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| DelFly Explorer | 50% | `wingspan_mm`, `frequency_hz`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s` |
| DelFly Micro | 50% | `wingspan_mm`, `weight_total_g|weight_empty_g|weight_takeoff_g`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| Mentor | 50% | `frequency_hz`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| RoboBee (Original) | 50% | `frequency_hz`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| 蜂鸟机器人 (Purdue Hummingbird) | 62% | `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| 小隼 (Little Falcon) | 62% | `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| 主动折叠变形扑翼飞行器 | 62% | `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| PigeonBot | 62% | `frequency_hz`, `endurance_min|endurance_sec|endurance_hover_min`, `can_hover` |
| TechJect Dragonfly | 62% | `frequency_hz`, `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s` |
| 金鹰 | 75% | `frequency_hz`, `endurance_min|endurance_sec|endurance_hover_min` |
| 空中仿生机器人 | 75% | `frequency_hz`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s` |
| 微机械飞行昆虫 (MFI) | 75% | `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s` |
| 信鸽 | 75% | `frequency_hz`, `can_hover` |
| 云鸮 | 75% | `frequency_hz`, `can_hover` |
| Allomyrina dichotoma (仿独角仙) | 75% | `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s` |
| BionicOpter | 75% | `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s` |
| Entomopter | 75% | `endurance_min|endurance_sec|endurance_hover_min`, `can_hover` |
| Insect-mimicking (仿昆虫无尾翼) | 75% | `endurance_min|endurance_sec|endurance_hover_min`, `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s` |
| Microbat | 75% | `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| RoboBee X-Wing | 75% | `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s`, `can_hover` |
| SmartBird | 75% | `endurance_min|endurance_sec|endurance_hover_min`, `can_hover` |
| USTBird | 75% | `frequency_hz`, `can_hover` |
| Colibri | 88% | `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s` |
| KUBeetle-S | 88% | `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s` |
| Robotic Hummingbird | 88% | `speed_max_m_s|speed_max_km_h|speed_m_s|speed_forward_m_s` |
| DelFly Nimble | 100% | — |
| Nano Hummingbird | 100% | — |
| RoboRaven | 100% | — |

### Organism (共 23 个节点，平均完整度 7.7%)

| 节点 | 完整度 | 缺失字段 |
|---|---|---|
| 蝙蝠 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 苍蝇 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 大型鸟类 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 独角仙 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 飞鱼 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 蜂鸟 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 凤凰 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 鸽子 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 海鸠 (Guillemot) | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 海鸥 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 狐蝠 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 蝴蝶 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 甲虫 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 甲虫 (Beetle) | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 金鹰 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 昆虫 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 昆虫 (布局) | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 蜜蜂 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 鸟类 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 蜻蜓 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 隼 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 乌鸦 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |
| 鸮 | 8% | `scientific_name`, `body_mass_g_min`, `body_mass_g_max`, `wingspan_cm_min`, `wingspan_cm_max`, `flap_freq_hz_min`, `flap_freq_hz_max`, `can_hover`, `reynolds_min`, `reynolds_max`, `strouhal_min`, `strouhal_max` |

### DriveMechanism (共 44 个节点，平均完整度 33.3%)

| 节点 | 完整度 | 缺失字段 |
|---|---|---|
| 齿轮机构协同四连杆机构 | 33% | `category`, `description` |
| 齿轮减速机构 | 33% | `category`, `description` |
| 齿轮减速连杆机构 | 33% | `category`, `description` |
| 串联四连杆机构 | 33% | `category`, `description` |
| 垂直齿轮驱动机构 | 33% | `category`, `description` |
| 伺服驱动曲轴机构 | 33% | `category`, `description` |
| 带传动曲柄摇杆机构 | 33% | `category`, `description` |
| 单曲柄双摇杆复合机构 | 33% | `category`, `description` |
| 单曲柄双摇杆机构 | 33% | `category`, `description` |
| 电机驱动机构 | 33% | `category`, `description` |
| 电机驱动连杆机构 | 33% | `category`, `description` |
| 独立伺服直驱机构 | 33% | `category`, `description` |
| 独立舵机驱动 | 33% | `category`, `description` |
| 独立翼控制机构 | 33% | `category`, `description` |
| 二维对称扑翼机构 | 33% | `category`, `description` |
| 分布式驱动 | 33% | `category`, `description` |
| 复杂杠杆机构 | 33% | `category`, `description` |
| 复杂连杆机构 | 33% | `category`, `description` |
| 共振胸腔结构 | 33% | `category`, `description` |
| 共振X-翼结构 | 33% | `category`, `description` |
| 活塞连杆机构 | 33% | `category`, `description` |
| 空间曲柄摇杆机构 | 33% | `category`, `description` |
| 两级齿轮减速机构 (比率33.3) | 33% | `category`, `description` |
| 螺旋桨驱动 | 33% | `category`, `description` |
| 模块化扑翼机构 | 33% | `category`, `description` |
| 拍打-扭转耦合机构 | 33% | `category`, `description` |
| 平面连杆曲柄机构 | 33% | `category`, `description` |
| 扑动折叠耦合机构 | 33% | `category`, `description` |
| 曲柄连杆机构 | 33% | `category`, `description` |
| 曲柄推杆机构 | 33% | `category`, `description` |
| 上下扑动+左右差动扭转变形扑动机构 | 33% | `category`, `description` |
| 双驱动器独立驱动机构 | 33% | `category`, `description` |
| 四连杆机构改进型 | 33% | `category`, `description` |
| 四连杆曲柄滑块机构 | 33% | `category`, `description` |
| 往复式化学肌肉(RCM) | 33% | `category`, `description` |
| 五杆联动系统 | 33% | `category`, `description` |
| 压电驱动四连杆机构 | 33% | `category`, `description` |
| 压电陶瓷致动器 | 33% | `category`, `description` |
| 压电陶瓷致动器 (Piezoelectric Actuators) | 33% | `category`, `description` |
| 压电致动器 (多模式) | 33% | `category`, `description` |
| 圆锥摇杆机构(CRM) | 33% | `category`, `description` |
| 折叠翼机构 | 33% | `category`, `description` |
| 主动扭转机构 | 33% | `category`, `description` |
| 主动折叠机构 | 33% | `category`, `description` |

### Application (共 54 个节点，平均完整度 50.0%)

| 节点 | 完整度 | 缺失字段 |
|---|---|---|
| 安防 | 50% | `category` |
| 避障飞行 | 50% | `category` |
| 避障研究 | 50% | `category` |
| 编队飞行表演 | 50% | `category` |
| 变形翼测试 | 50% | `category` |
| 变翼机制研究 | 50% | `category` |
| 地外行星探测(概念) | 50% | `category` |
| 低空飞行验证 | 50% | `category` |
| 动力系统验证 | 50% | `category` |
| 独立翼控研究 | 50% | `category` |
| 负载运输研究 | 50% | `category` |
| 高海拔巡航 | 50% | `category` |
| 高机动特技飞行 | 50% | `category` |
| 高机动悬停 | 50% | `category` |
| 高频扑动研究 | 50% | `category` |
| 高效率仿生飞行 | 50% | `category` |
| 高效率巡航研究 | 50% | `category` |
| 海洋巡航监测 | 50% | `category` |
| 航拍 | 50% | `category` |
| 基础飞行原理验证 | 50% | `category` |
| 控制律验证 | 50% | `category` |
| 跨介质环境探测 | 50% | `category` |
| 民用/军事巡逻 | 50% | `category` |
| 模块化验证 | 50% | `category` |
| 鸟类飞行机理研究 | 50% | `category` |
| 气动弹性实验 | 50% | `category` |
| 全向机动飞行 | 50% | `category` |
| 摄影 | 50% | `category` |
| 室内半自主飞行 | 50% | `category` |
| 室内机动 | 50% | `category` |
| 室内游戏 | 50% | `category` |
| 特技动作研究 | 50% | `category` |
| 微型飞行机理研究 | 50% | `category` |
| 微型侦察 | 50% | `category` |
| 未知环境自主探索 | 50% | `category` |
| 无束缚微型飞行验证 | 50% | `category` |
| 狭小空间飞行 | 50% | `category` |
| 狭小空间探测 | 50% | `category` |
| 悬停 | 50% | `category` |
| 悬停飞行 | 50% | `category` |
| 悬停飞行研究 | 50% | `category` |
| 悬停机动研究 | 50% | `category` |
| 悬停与高机动飞行 | 50% | `category` |
| 悬停与机动飞行 | 50% | `category` |
| 隐蔽侦察 | 50% | `category` |
| 运动轨迹规划 | 50% | `category` |
| 早期扑翼飞行验证 | 50% | `category` |
| 长航时飞行 | 50% | `category` |
| 长航时微型侦察 | 50% | `category` |
| 长航时悬停监测 | 50% | `category` |
| 侦察 | 50% | `category` |
| 阵风环境测试 | 50% | `category` |
| 转弯机动研究 | 50% | `category` |
| 自主飞行 | 50% | `category` |

### Organization (共 33 个节点，平均完整度 33.3%)

| 节点 | 完整度 | 缺失字段 |
|---|---|---|
| 北京航空航天大学 | 33% | `country`, `type` |
| 北京交通大学 | 33% | `country`, `type` |
| 北京科技大学 | 33% | `country`, `type` |
| 比利时布鲁塞尔自由大学 | 33% | `country`, `type` |
| 哈尔滨工业大学 | 33% | `country`, `type` |
| 哈尔滨工业大学(深圳) | 33% | `country`, `type` |
| 哈佛大学 | 33% | `country`, `type` |
| 荷兰代尔夫特理工大学 | 33% | `country`, `type` |
| 加州大学伯克利分校 | 33% | `country`, `type` |
| 加州理工学院 | 33% | `country`, `type` |
| 美国德克萨斯A&M大学 | 33% | `country`, `type` |
| 南昌航空大学 | 33% | `country`, `type` |
| 南京航空航天大学 | 33% | `country`, `type` |
| 普渡大学 | 33% | `country`, `type` |
| 斯坦福大学 | 33% | `country`, `type` |
| 西北工业大学 | 33% | `country`, `type` |
| 佐治亚理工学院 | 33% | `country`, `type` |
| AeroVironment | 33% | `country`, `type` |
| DARPA | 33% | `country`, `type` |
| Delft University of Technology | 33% | `country`, `type` |
| FESTO | 33% | `country`, `type` |
| Georgia Tech | 33% | `country`, `type` |
| Harvard University | 33% | `country`, `type` |
| Jiangsu University (江苏大学) | 33% | `country`, `type` |
| Konkuk University | 33% | `country`, `type` |
| Konkuk University (韩国建国大学) | 33% | `country`, `type` |
| Richter (Individual/Researcher) | 33% | `country`, `type` |
| SRI International | 33% | `country`, `type` |
| TechJect | 33% | `country`, `type` |
| University of Arizona | 33% | `country`, `type` |
| University of Florida | 33% | `country`, `type` |
| University of Maryland | 33% | `country`, `type` |
| University of Toronto | 33% | `country`, `type` |

### Reference (共 31 个节点，平均完整度 65.3%)

| 节点 | 完整度 | 缺失字段 |
|---|---|---|
| A tailless aerial robotic flapper reveals that flies use torque coupling in rapid banked turns | 50% | `doi`, `authors` |
| Adaptive control of a millimeter-scale flapping-wing robot | 50% | `doi`, `authors` |
| An All Servo-Driven Bird-Like Flapping-Wing Aerial Robot Capable of Autonomous Flight | 50% | `doi`, `authors` |
| Autonomous flight of a 20-gram Flapping Wing MAV with a 4-gram onboard stereo vision system | 50% | `doi`, `authors` |
| Controlled flight of a biologically inspired, insect-scale robot | 50% | `doi`, `authors` |
| Demonstration of a tailless flapping-wing micro air vehicle with split-cycle frequency modulation | 50% | `doi`, `authors` |
| Design and aerodynamic analysis of a flapping wing rotor with active folding | 50% | `doi`, `authors` |
| Design and Aerodynamic Performance of a Flapping Wing Micro Air Vehicle | 50% | `doi`, `authors` |
| Design, aerodynamics and autonomy of the DelFly | 50% | `doi`, `authors` |
| Development of the nanohummingbird: a tailless flapping wing micro air vehicle | 50% | `doi`, `authors` |
| TechJect Dragonfly: Wi-Fi Robotic Dragonfly for Photography | 50% | `doi`, `authors` |
| The Mentor Project | 50% | `doi`, `authors` |
| 仿生微型扑翼飞行器的结构设计与研制 | 75% | `doi` |
| 机器海鸥的仿生设计及其实验研究 | 75% | `doi` |
| 可差动扭转扑翼飞行器的设计和风洞试验研究 | 75% | `doi` |
| A biologically inspired, flapping-wing, hybrid aerial-aquatic microrobot | 75% | `doi` |
| Artificial hinged-wing bird with active torsion and partially linear kinematics | 75% | `doi` |
| Attitude control for a micromechanical flying insect via sensor output feedback | 75% | `doi` |
| COLIBRI: A hovering flapping twin-wing robot | 75% | `doi` |
| Controlled Flight of a Biologically Inspired, Insect-Scale Robot | 75% | `doi` |
| Design optimization and experimental study of a novel mechanism for a hover-able bionic flapping-wing micro air vehicle | 75% | `doi` |
| Development of a Robotic Hummingbird Capable of Controlled Hover | 75% | `doi` |
| HIT-Hawk and HIT-Phoenix: Two kinds of flapping-wing flying robotic birds with wingspans beyond 2 meters | 75% | `doi` |
| How flight feathers stick together to form a continuous morphing wing | 75% | `doi` |
| Inventing a micro aerial vehicle inspired by the mechanics of dragonfly flight | 75% | `doi` |
| KUBeetle-S: An insect-like, tailless, hover-capable robot that can fly with a low-voltage power source | 75% | `doi` |
| Microbat: A palm-sized electrically powered ornithopter | 75% | `doi` |
| Robo Raven: A Flapping-Wing Air Vehicle with Highly Compliant and Independently Controlled Wings | 75% | `doi` |
| The entomopter | 75% | `doi` |
| Untethered flight of an insect-sized flapping-wing microscale aerial vehicle | 75% | `doi` |
| Wing transmission for a micromechanical flying insect | 75% | `doi` |

### Equipment (共 108 个节点，平均完整度 50.0%)

| 节点 | 完整度 | 缺失字段 |
|---|---|---|
| 1.5W直流电机 | 50% | `category` |
| 1020空心杯电机 | 50% | `category` |
| 2.4GHz无线模块 | 50% | `category` |
| 2S锂电池 | 50% | `category` |
| 370mAh锂电池 | 50% | `category` |
| 3S 800mAh锂电池 | 50% | `category` |
| 3S锂电池 | 50% | `category` |
| 40W无刷直流电机 | 50% | `category` |
| 4个独立电机 | 50% | `category` |
| 50mA锂电池 | 50% | `category` |
| 9个伺服电机 | 50% | `category` |
| 超声波测距发射机 | 50% | `category` |
| 储气罐 | 50% | `category` |
| 传动带 | 50% | `category` |
| 磁场传感器 | 50% | `category` |
| 点火火花器 | 50% | `category` |
| 电调 | 50% | `category` |
| 电解板 (Gas Generator) | 50% | `category` |
| 定制3S锂电池 | 50% | `category` |
| 定制升压电路 | 50% | `category` |
| 定制无刷电机 | 50% | `category` |
| 舵机 | 50% | `category` |
| 二级齿轮减速装置 | 50% | `category` |
| 浮力腔室 | 50% | `category` |
| 副翼(Ailerons) | 50% | `category` |
| 高清相机 | 50% | `category` |
| 惯性传感器 | 50% | `category` |
| 光流传感器 | 50% | `category` |
| 光纤传感器 | 50% | `category` |
| 好盈铂金电调 | 50% | `category` |
| 核心无刷电机 | 50% | `category` |
| 红外标记物 | 50% | `category` |
| 红外成像单元 | 50% | `category` |
| 霍尔传感器 | 50% | `category` |
| 机载姿态传感器 | 50% | `category` |
| 激光切割聚酯薄膜 | 50% | `category` |
| 加速度计 | 50% | `category` |
| 角速率传感器 | 50% | `category` |
| 接收机 | 50% | `category` |
| 聚合物锂电池 | 50% | `category` |
| 聚酰亚胺弯曲铰链 | 50% | `category` |
| 可编程微型计算机 | 50% | `category` |
| 可变形机翼 | 50% | `category` |
| 可见光摄像头 | 50% | `category` |
| 控制板 | 50% | `category` |
| 控制电路板 | 50% | `category` |
| 蓝牙模块 | 50% | `category` |
| 类三角形尾翼 | 50% | `category` |
| 锂聚合物电池 | 50% | `category` |
| 立体视觉系统(4.0g) | 50% | `category` |
| 两段式机翼 | 50% | `category` |
| 模拟摄像头 | 50% | `category` |
| 皮托管 | 50% | `category` |
| 轻木骨架 | 50% | `category` |
| 三轴陀螺仪 | 50% | `category` |
| 摄像头 | 50% | `category` |
| 视觉相机 | 50% | `category` |
| 碳管机身 | 50% | `category` |
| 碳纤维板材机身 | 50% | `category` |
| 碳纤维杆 | 50% | `category` |
| 碳纤维骨架 | 50% | `category` |
| 碳纤维增强聚合物机翼 | 50% | `category` |
| 微型电机 | 50% | `category` |
| 微型舵机(驱动折叠) | 50% | `category` |
| 微型摄像装置 | 50% | `category` |
| 微型太阳能电池 | 50% | `category` |
| 微型陀螺仪 | 50% | `category` |
| 微型相机 | 50% | `category` |
| 微型自动驾驶仪 | 50% | `category` |
| 无刷电机 | 50% | `category` |
| 无刷直流电机 | 50% | `category` |
| 无刷主电机 | 50% | `category` |
| 遥控接收机 | 50% | `category` |
| 应变片(用于测试) | 50% | `category` |
| 有刷电机(驱动折叠) | 50% | `category` |
| 有刷直流电机 | 50% | `category` |
| 云台 | 50% | `category` |
| 真实羽毛 | 50% | `category` |
| 姿态控制系统 | 50% | `category` |
| 自动驾驶仪(0.98g) | 50% | `category` |
| ABS材料机身 | 50% | `category` |
| Arduino Nano | 50% | `category` |
| ARM微控制器 | 50% | `category` |
| C-10 2900KV无刷电机 | 50% | `category` |
| CO2发动机 | 50% | `category` |
| DualSky锂电池 | 50% | `category` |
| EPS8-Brushed DC电机 | 50% | `category` |
| Futaba S9352HV数字伺服电机 | 50% | `category` |
| GPS | 50% | `category` |
| GPS定位模块 | 50% | `category` |
| IMU | 50% | `category` |
| KST215MG舵机 | 50% | `category` |
| MARC自动驾驶仪 | 50% | `category` |
| MEMS加速度计 | 50% | `category` |
| MEMS陀螺仪 | 50% | `category` |
| Micro MWC飞控板 | 50% | `category` |
| MK07-2.3 red34空心杯电机 | 50% | `category` |
| MPU-9150 IMU | 50% | `category` |
| MX3508无刷电机 | 50% | `category` |
| Mylar薄膜机翼 | 50% | `category` |
| PIC微控制器 | 50% | `category` |
| Pixhawk飞控 | 50% | `category` |
| PixRacer自动驾驶仪 | 50% | `category` |
| RCM驱动器 | 50% | `category` |
| Sanyo 50mAh镍镉电池 | 50% | `category` |
| STM32自动驾驶仪 | 50% | `category` |
| Tmotor MN1804无刷电机 | 50% | `category` |
| Wi-Fi模块 | 50% | `category` |

## 5. FWMAV 节点关系挂载情况

| 飞行器 | MIMICS | DEVELOPED_BY | HAS_DRIVE_MECHANISM | SUITABLE_FOR | HAS_REFERENCE |
|---|---|---|---|---|---|
| Allomyrina dichotoma (仿独角仙) | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| Bionic Flying Fox | ✅ (2) | ✅ (1) | ✅ (2) | ✅ (2) | ❌ (0) |
| BionicOpter | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| C-GPTR (Mr. Bill) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ❌ (0) |
| Colibri | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| DelFly Explorer | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| DelFly I | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| DelFly II | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| DelFly Micro | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| DelFly Nimble | ✅ (1) | ✅ (1) | ✅ (1) | ❌ (0) | ✅ (1) |
| Entomopter | ✅ (2) | ✅ (1) | ✅ (2) | ✅ (2) | ✅ (1) |
| Insect-mimicking (仿昆虫无尾翼) | ✅ (1) | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (1) |
| KUBeetle-S | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| MAV (University of Arizona) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| Mentor | ✅ (1) | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (1) |
| Microbat | ✅ (1) | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (1) |
| Nano Hummingbird | ✅ (1) | ✅ (1) | ✅ (1) | ❌ (0) | ✅ (1) |
| PigeonBot | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| Richter (Ornithopter) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ❌ (0) |
| RoboBee (Hybrid Aerial-Aquatic) | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| RoboBee (Original) | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| RoboBee X-Wing | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| RoboRaven | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| Robotic Hummingbird | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (2) | ✅ (1) |
| SmartBird | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (2) | ✅ (1) |
| TechJect Dragonfly | ✅ (1) | ✅ (2) | ✅ (1) | ✅ (3) | ✅ (1) |
| USTBird | ✅ (1) | ✅ (1) | ✅ (1) | ❌ (0) | ✅ (1) |
| 主动折叠变形扑翼飞行器 | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| 云鸮 | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (2) | ❌ (0) |
| 信鸽 | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ❌ (0) |
| 凤凰 (Phoenix) | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| 四动力装置可悬停扑翼飞行器 | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (2) | ❌ (0) |
| 大中型仿鸟扑翼飞行器 (Large-Scale Ornithopter) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (2) | ❌ (0) |
| 小隼 (Little Falcon) | ✅ (3) | ✅ (1) | ✅ (1) | ✅ (2) | ❌ (0) |
| 微机械飞行昆虫 (MFI) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (2) | ✅ (2) |
| 机器海鸥 | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| 空中仿生机器人 | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| 蜂鸟机器人 (Purdue Hummingbird) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| 金鹰 | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |

## 6. MIMICS 关系是否细分

已有属性: [['relationKey'], ['relationKey'], ['relationKey'], ['relationKey'], ['relationKey']]

## 7. 总体诊断结论

- **FlappingWingVehicle 平均完整度**: 63.5%
- **Organism 平均完整度**: 7.7%

**结论**:
- 🔴 Organism 节点严重缺失属性，无法支撑创新点 1 的双层本体——**必须先补全生物层数据**。
- ⚠️ FWMAV 完整度低于 70%，影响创新点 2 工具调用与创新点 3 张量分解。
- ⚠️ 属性命名混乱，标注题目前必须先标准化。

**下一步建议**: 按 P0 → P1 → P2 顺序补全（详见论文 papers/02-FWMAV-QA-Benchmark-标注规范.md）。