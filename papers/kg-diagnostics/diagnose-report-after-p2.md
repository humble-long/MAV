# FWMAV KG 数据完整性诊断报告

> 生成时间：2026-06-16 22:45:29
> Neo4j: `bolt://localhost:7687`

---

## 1. 节点规模

| 标签 | 数量 |
|---|---|
| KGEntity+Performance | 272 |
| KGEntity+Equipment | 108 |
| KGEntity+Application | 54 |
| KGEntity+DriveMechanism | 44 |
| KGEntity+FlappingWingVehicle | 39 |
| KGEntity+Reference | 39 |
| KGEntity+Organization | 33 |
| KGEntity+Organism | 23 |

## 2. 关系规模

| 关系类型 | 数量 |
|---|---|
| HAS_PERFORMANCE | 272 |
| EQUIPPED_WITH | 117 |
| SUITABLE_FOR | 56 |
| MIMICS | 50 |
| HAS_DRIVE_MECHANISM | 46 |
| DEVELOPED_BY | 43 |
| HAS_REFERENCE | 40 |
| FUNDED_BY | 1 |

## 3. 属性命名一致性问题（重灾区）

### 3.1 重量属性 — 三种命名共存
| 字段 | 使用机型数 |
|---|---|
| `weight_total_g` | 20 |
| `weight_empty_g` | 16 |
| `weight_takeoff_g` | 7 |

**建议**: 统一为 `weight_takeoff_g`（缺失时用 empty + 估算 payload 推算）。

### 3.2 续航属性 — 三种单位共存
| 字段 | 使用机型数 |
|---|---|
| `endurance_min` | 34 |
| `endurance_sec` | 5 |
| `endurance_hover_min` | 1 |

**建议**: 统一为 `endurance_s`（秒）+ `endurance_condition` ∈ {hover, cruise, mixed}。

### 3.3 速度属性 — 多种命名共存
| 字段 | 使用机型数 |
|---|---|
| `speed_max_m_s` | 35 |
| `speed_max_km_h` | 2 |
| `speed_m_s` | 1 |
| `speed_forward_m_s` | 1 |
| `speed_side_m_s` | 1 |
| `flight_speed_m_s` | 1 |
| `climb_speed_m_s` | 1 |

**建议**: 统一为 `speed_max_m_s` + `speed_cruise_m_s`。

### 3.4 扑频属性 — 数字 vs 字符串混用
- 作为 **数字** 存储: 35 条
- 作为 **字符串** 存储: 4 条（如 "15-20"）
- 字符串示例:
    - 蜂鸟机器人 (Purdue Hummingbird): "30-40"
    - Allomyrina dichotoma (仿独角仙): "25-50"
    - BionicOpter: "15-20"
    - SmartBird: "2-3"

**建议**: 把字符串区间拆成 `frequency_hz_min` + `frequency_hz_max`，单值赋 min=max。

## 4. 各标签下属性完整度

### FlappingWingVehicle (共 39 个节点，平均完整度 100.0%)

| 节点 | 完整度 | 缺失字段 |
|---|---|---|
| 大中型仿鸟扑翼飞行器 (Large-Scale Ornithopter) | 100% | — |
| 蜂鸟机器人 (Purdue Hummingbird) | 100% | — |
| 凤凰 (Phoenix) | 100% | — |
| 机器海鸥 | 100% | — |
| 金鹰 | 100% | — |
| 空中仿生机器人 | 100% | — |
| 四动力装置可悬停扑翼飞行器 | 100% | — |
| 微机械飞行昆虫 (MFI) | 100% | — |
| 小隼 (Little Falcon) | 100% | — |
| 信鸽 | 100% | — |
| 云鸮 | 100% | — |
| 主动折叠变形扑翼飞行器 | 100% | — |
| Allomyrina dichotoma (仿独角仙) | 100% | — |
| Bionic Flying Fox | 100% | — |
| BionicOpter | 100% | — |
| C-GPTR (Mr. Bill) | 100% | — |
| Colibri | 100% | — |
| DelFly Explorer | 100% | — |
| DelFly I | 100% | — |
| DelFly II | 100% | — |
| DelFly Micro | 100% | — |
| DelFly Nimble | 100% | — |
| Entomopter | 100% | — |
| Insect-mimicking (仿昆虫无尾翼) | 100% | — |
| KUBeetle-S | 100% | — |
| MAV (University of Arizona) | 100% | — |
| Mentor | 100% | — |
| Microbat | 100% | — |
| Nano Hummingbird | 100% | — |
| PigeonBot | 100% | — |
| Richter (Ornithopter) | 100% | — |
| RoboBee (Hybrid Aerial-Aquatic) | 100% | — |
| RoboBee (Original) | 100% | — |
| RoboBee X-Wing | 100% | — |
| RoboRaven | 100% | — |
| Robotic Hummingbird | 100% | — |
| SmartBird | 100% | — |
| TechJect Dragonfly | 100% | — |
| USTBird | 100% | — |

### Organism (共 23 个节点，平均完整度 100.0%)

| 节点 | 完整度 | 缺失字段 |
|---|---|---|
| 蝙蝠 | 100% | — |
| 苍蝇 | 100% | — |
| 大型鸟类 | 100% | — |
| 独角仙 | 100% | — |
| 飞鱼 | 100% | — |
| 蜂鸟 | 100% | — |
| 凤凰 | 100% | — |
| 鸽子 | 100% | — |
| 海鸠 (Guillemot) | 100% | — |
| 海鸥 | 100% | — |
| 狐蝠 | 100% | — |
| 蝴蝶 | 100% | — |
| 甲虫 | 100% | — |
| 甲虫 (Beetle) | 100% | — |
| 金鹰 | 100% | — |
| 昆虫 | 100% | — |
| 昆虫 (布局) | 100% | — |
| 蜜蜂 | 100% | — |
| 鸟类 | 100% | — |
| 蜻蜓 | 100% | — |
| 隼 | 100% | — |
| 乌鸦 | 100% | — |
| 鸮 | 100% | — |

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

### Reference (共 39 个节点，平均完整度 67.3%)

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
| BionicFlyingFox: Ultra-light flight model with active aerodynamics | 75% | `doi` |
| Robotic ornithopter design and flight tests at University of Florida | 75% | `doi` |
| Historical ornithopter designs by individual researcher Richter | 75% | `doi` |
| 西工大云鸮大型仿生扑翼飞行器设计与试飞 | 75% | `doi` |
| 信鸽仿生扑翼飞行器设计研究 | 75% | `doi` |
| Design of a four-actuator hover-capable flapping-wing micro air vehicle | 75% | `doi` |
| Design of large-scale bio-inspired ornithopter for outdoor cruise | 75% | `doi` |
| HIT Little Falcon: Small-scale falcon-mimicking flapping-wing aerial vehicle | 75% | `doi` |

### Equipment (共 108 个节点，平均完整度 100.0%)

| 节点 | 完整度 | 缺失字段 |
|---|---|---|
| 1.5W直流电机 | 100% | — |
| 1020空心杯电机 | 100% | — |
| 2.4GHz无线模块 | 100% | — |
| 2S锂电池 | 100% | — |
| 370mAh锂电池 | 100% | — |
| 3S 800mAh锂电池 | 100% | — |
| 3S锂电池 | 100% | — |
| 40W无刷直流电机 | 100% | — |
| 4个独立电机 | 100% | — |
| 50mA锂电池 | 100% | — |
| 9个伺服电机 | 100% | — |
| 超声波测距发射机 | 100% | — |
| 储气罐 | 100% | — |
| 传动带 | 100% | — |
| 磁场传感器 | 100% | — |
| 点火火花器 | 100% | — |
| 电调 | 100% | — |
| 电解板 (Gas Generator) | 100% | — |
| 定制3S锂电池 | 100% | — |
| 定制升压电路 | 100% | — |
| 定制无刷电机 | 100% | — |
| 舵机 | 100% | — |
| 二级齿轮减速装置 | 100% | — |
| 浮力腔室 | 100% | — |
| 副翼(Ailerons) | 100% | — |
| 高清相机 | 100% | — |
| 惯性传感器 | 100% | — |
| 光流传感器 | 100% | — |
| 光纤传感器 | 100% | — |
| 好盈铂金电调 | 100% | — |
| 核心无刷电机 | 100% | — |
| 红外标记物 | 100% | — |
| 红外成像单元 | 100% | — |
| 霍尔传感器 | 100% | — |
| 机载姿态传感器 | 100% | — |
| 激光切割聚酯薄膜 | 100% | — |
| 加速度计 | 100% | — |
| 角速率传感器 | 100% | — |
| 接收机 | 100% | — |
| 聚合物锂电池 | 100% | — |
| 聚酰亚胺弯曲铰链 | 100% | — |
| 可编程微型计算机 | 100% | — |
| 可变形机翼 | 100% | — |
| 可见光摄像头 | 100% | — |
| 控制板 | 100% | — |
| 控制电路板 | 100% | — |
| 蓝牙模块 | 100% | — |
| 类三角形尾翼 | 100% | — |
| 锂聚合物电池 | 100% | — |
| 立体视觉系统(4.0g) | 100% | — |
| 两段式机翼 | 100% | — |
| 模拟摄像头 | 100% | — |
| 皮托管 | 100% | — |
| 轻木骨架 | 100% | — |
| 三轴陀螺仪 | 100% | — |
| 摄像头 | 100% | — |
| 视觉相机 | 100% | — |
| 碳管机身 | 100% | — |
| 碳纤维板材机身 | 100% | — |
| 碳纤维杆 | 100% | — |
| 碳纤维骨架 | 100% | — |
| 碳纤维增强聚合物机翼 | 100% | — |
| 微型电机 | 100% | — |
| 微型舵机(驱动折叠) | 100% | — |
| 微型摄像装置 | 100% | — |
| 微型太阳能电池 | 100% | — |
| 微型陀螺仪 | 100% | — |
| 微型相机 | 100% | — |
| 微型自动驾驶仪 | 100% | — |
| 无刷电机 | 100% | — |
| 无刷直流电机 | 100% | — |
| 无刷主电机 | 100% | — |
| 遥控接收机 | 100% | — |
| 应变片(用于测试) | 100% | — |
| 有刷电机(驱动折叠) | 100% | — |
| 有刷直流电机 | 100% | — |
| 云台 | 100% | — |
| 真实羽毛 | 100% | — |
| 姿态控制系统 | 100% | — |
| 自动驾驶仪(0.98g) | 100% | — |
| ABS材料机身 | 100% | — |
| Arduino Nano | 100% | — |
| ARM微控制器 | 100% | — |
| C-10 2900KV无刷电机 | 100% | — |
| CO2发动机 | 100% | — |
| DualSky锂电池 | 100% | — |
| EPS8-Brushed DC电机 | 100% | — |
| Futaba S9352HV数字伺服电机 | 100% | — |
| GPS | 100% | — |
| GPS定位模块 | 100% | — |
| IMU | 100% | — |
| KST215MG舵机 | 100% | — |
| MARC自动驾驶仪 | 100% | — |
| MEMS加速度计 | 100% | — |
| MEMS陀螺仪 | 100% | — |
| Micro MWC飞控板 | 100% | — |
| MK07-2.3 red34空心杯电机 | 100% | — |
| MPU-9150 IMU | 100% | — |
| MX3508无刷电机 | 100% | — |
| Mylar薄膜机翼 | 100% | — |
| PIC微控制器 | 100% | — |
| Pixhawk飞控 | 100% | — |
| PixRacer自动驾驶仪 | 100% | — |
| RCM驱动器 | 100% | — |
| Sanyo 50mAh镍镉电池 | 100% | — |
| STM32自动驾驶仪 | 100% | — |
| Tmotor MN1804无刷电机 | 100% | — |
| Wi-Fi模块 | 100% | — |

## 5. FWMAV 节点关系挂载情况

| 飞行器 | MIMICS | DEVELOPED_BY | HAS_DRIVE_MECHANISM | SUITABLE_FOR | HAS_REFERENCE |
|---|---|---|---|---|---|
| Allomyrina dichotoma (仿独角仙) | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| Bionic Flying Fox | ✅ (2) | ✅ (1) | ✅ (2) | ✅ (2) | ✅ (1) |
| BionicOpter | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| C-GPTR (Mr. Bill) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
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
| Richter (Ornithopter) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| RoboBee (Hybrid Aerial-Aquatic) | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| RoboBee (Original) | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| RoboBee X-Wing | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| RoboRaven | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| Robotic Hummingbird | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (2) | ✅ (1) |
| SmartBird | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (2) | ✅ (1) |
| TechJect Dragonfly | ✅ (1) | ✅ (2) | ✅ (1) | ✅ (3) | ✅ (1) |
| USTBird | ✅ (1) | ✅ (1) | ✅ (1) | ❌ (0) | ✅ (1) |
| 主动折叠变形扑翼飞行器 | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| 云鸮 | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| 信鸽 | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| 凤凰 (Phoenix) | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| 四动力装置可悬停扑翼飞行器 | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (2) | ✅ (1) |
| 大中型仿鸟扑翼飞行器 (Large-Scale Ornithopter) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (2) | ✅ (1) |
| 小隼 (Little Falcon) | ✅ (3) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| 微机械飞行昆虫 (MFI) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (2) | ✅ (2) |
| 机器海鸥 | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| 空中仿生机器人 | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (1) |
| 蜂鸟机器人 (Purdue Hummingbird) | ✅ (1) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |
| 金鹰 | ✅ (2) | ✅ (1) | ✅ (1) | ✅ (2) | ✅ (1) |

## 6. MIMICS 关系是否细分

已有属性: [['scored_at', 'mimics_kinematics', 'mimics_dominant_type', 'mimics_morphology', 'mimics_scale', 'mimics_aero', 'relationKey', 'mimics_dominant_score'], ['scored_at', 'mimics_kinematics', 'mimics_dominant_type', 'mimics_morphology', 'mimics_scale', 'mimics_aero', 'relationKey', 'mimics_dominant_score'], ['scored_at', 'mimics_kinematics', 'mimics_dominant_type', 'mimics_morphology', 'mimics_scale', 'mimics_aero', 'relationKey', 'mimics_dominant_score'], ['scored_at', 'mimics_kinematics', 'mimics_dominant_type', 'mimics_morphology', 'mimics_scale', 'mimics_aero', 'relationKey', 'mimics_dominant_score'], ['scored_at', 'mimics_kinematics', 'mimics_dominant_type', 'mimics_morphology', 'mimics_scale', 'mimics_aero', 'relationKey', 'mimics_dominant_score']]

## 7. 总体诊断结论

- **FlappingWingVehicle 平均完整度**: 100.0%
- **Organism 平均完整度**: 100.0%

**结论**:
- ⚠️ 属性命名混乱，标注题目前必须先标准化。

**下一步建议**: 按 P0 → P1 → P2 顺序补全（详见论文 papers/02-FWMAV-QA-Benchmark-标注规范.md）。