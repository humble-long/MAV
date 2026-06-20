# BioBridge-GraphRAG 知识图谱结构与构建说明

> 写于 2026-06-20
> 对应 Neo4j 数据库版本：P0–P2 升级完成
> 配套脚本目录：`papers/fwmav-qa-benchmark/scripts/`
> 配套报告：`papers/kg-diagnostics/p0-p2-summary.md`（机器生成的对比数据）
>
> 本文档面向新协作者：**当前 KG 长什么样、如何构建、为什么这样构建。**

---

## 0. 文档导航

| 节 | 内容 |
|---|---|
| §1 | 一图速览：当前 KG 全貌 |
| §2 | 节点结构（8 类标签 / 612 节点）|
| §3 | 关系结构（8 类关系 / 625 边）|
| §4 | **跨层桥梁：4 类细分 MIMICS**（论文创新 1 核心）|
| §5 | 7 步调整全记录（P0 → P1 → P2）|
| §6 | 调整前后对比 |
| §7 | KG 对论文 4 个创新点的支撑 |
| §8 | 当前已知瑕疵与修补建议 |

---

# §1 一图速览

```
                  BioBridge KG
                  612 节点 / 625 关系
                          │
        ┌─────────────────┼─────────────────────────┐
        │                 │                         │
    生物层 (23)        工程层 (核心)              辅助层 (152)
    Organism           437 节点                
        │                 │                         │
        │       ┌─────────┼─────────┐
        │       │         │         │
        │     FWMAV   Performance   ...           Application
        │     (39)     (272)                       (54)
        │                                          DriveMechanism
        │                                          (44)
        │      ╲                                   Organization
        │       ╲                                  (33)
        │        ╲ MIMICS × 50                     Reference
        │         ╲ (带 4 类相似度)                  (39)
        │          ╲                               Equipment
        ▼           ▼                              (108, 10 类 category)
   生物-工程        生物 → 工程
   双向桥梁
```

**核心数字**：
- **612 节点 / 625 关系** —— 总规模
- **23 生物 + 39 样机** —— 双层本体的两端
- **50 条 MIMICS 边 × 4 类相似度** —— 跨层桥梁
- **272 条 Performance 节点** —— 创新 3 张量的第 3 维度

---

# §2 节点结构（8 类）

| 标签 | 数量 | 角色 | 备注 |
|---|---|---|---|
| **Organism** | 23 | 生物原型层（双层本体之一）| 蜂鸟/苍蝇/甲虫/海鸥等 |
| **FlappingWingVehicle**（FWMAV）| 39 | 工程样机层（双层本体之二）| 39 架公开 FWMAV |
| **Performance** | **272** | 性能记录子节点 | **P1-2 新增**——支撑创新 3 |
| Equipment | 108 | 组件 | 已分 10 类 category |
| Application | 54 | 应用场景/任务 | 侦察、监测、巡检等 |
| DriveMechanism | 44 | 驱动机构 | 双曲柄、空间四杆、压电式等 |
| Reference | 39 | 参考文献 | 每架样机的来源论文 |
| Organization | 33 | 研制单位 | TU Delft / KAIST / 北航等 |
| **总计** | **612** | | |

## 2.1 生物层（Organism）23 个

按生物分类：

| 大类 | 数量 | 名单（部分）|
|---|---|---|
| 鸟类 | 11 | 蜂鸟、鸽子、隼、海鸥、海鸠 (Guillemot)、金鹰、鸮、乌鸦、鸟类（统称）、大型鸟类、凤凰* |
| 昆虫 | 7 | 苍蝇、蜜蜂、蜻蜓、蝴蝶、甲虫 (Beetle)、独角仙、昆虫（统称）|
| 蝙蝠 | 2 | 蝙蝠、狐蝠 |
| 鱼 | 1 | 飞鱼 |
| 重复/小瑕疵 | 2 | "甲虫" vs "甲虫 (Beetle)"、"昆虫" vs "昆虫 (布局)" |

\* 凤凰是神话生物，建议合并到"金鹰"或重命名为"大型猛禽"——见 §8。

**每个 Organism 节点的 16+ 属性**（P0-1 后 100% 完整）：

```
Organism: 蜂鸟
  ├ name: "蜂鸟"
  ├ scientific_name: "Trochilidae"
  ├ body_mass_g_min: 2.0
  ├ body_mass_g_max: 20.0
  ├ wingspan_cm_min: 8.0
  ├ wingspan_cm_max: 15.0
  ├ flap_freq_hz_min: 20
  ├ flap_freq_hz_max: 80
  ├ can_hover: True
  ├ reynolds_min: 1000
  ├ reynolds_max: 10000
  ├ strouhal_min: 0.20
  ├ strouhal_max: 0.40
  └ source: "Pennycuick 1996 / Greenewalt 1975 / Shyy 2013"
```

## 2.2 工程层（FlappingWingVehicle）39 架

覆盖 **昆虫尺度 → 鸟类尺度** 的全谱系：

| 尺度 | 代表样机 |
|---|---|
| 亚克级（< 1 g）| RoboBee (Original)、RoboBee X1 |
| 微型（1-30 g）| Nano Hummingbird、KUBeetle-S、DelFly Nimble、TechJect Dragonfly |
| 小型（30-100 g）| DelFly II、DelFly Explorer、信鸽 |
| 中型（100-500 g）| SmartBird、BionicOpter、RoboRaven |
| 大型（> 500 g）| Festo eMotionButterfly、金鹰仿生体 |

**关键属性（P0-3 标准化后）**：

```
FlappingWingVehicle: KUBeetle-S
  ├ name: "KUBeetle-S"
  ├ wingspan_mm: 200
  ├ frequency_hz: 30
  ├ weight_g_std: 26          ← P0-3 新增统一字段
  ├ endurance_s_std: 540      ← 同上
  ├ speed_max_m_s_std: 2.5    ← 同上
  ├ frequency_hz_min_std: 30  ← 同上
  ├ can_hover: True
  ├ description: "..."
  └ p0_2_source: "..."        ← 数据来源回溯
```

## 2.3 性能节点（Performance）272 个 — P1-2 新增

每架 FWMAV 平均 7 个 Performance 子节点，存放具体性能记录：

```
(KUBeetle-S) ─[HAS_PERFORMANCE]─► Performance
                                    ├ metric: "endurance"
                                    ├ value: 540
                                    ├ unit: "s"
                                    ├ condition: "hover"
                                    └ source_field: "endurance_hover_s"
```

**为什么不直接做扁平字段**：扁平字段无法表达"在不同条件下的不同测得值"——比如某架样机巡航续航 30 min、悬停续航 9 min。子节点结构能支撑创新 3 张量的第 3 维度（性能/条件矩阵）。

---

# §3 关系结构（8 类）

| 关系 | 条数 | 含义 | 是否带属性 |
|---|---|---|---|
| **MIMICS** | **50** | **生物 → 工程跨层映射（4 类相似度）** | ✅ **核心** |
| **HAS_PERFORMANCE** | **272** | 样机 → 性能记录 | — |
| EQUIPPED_WITH | 117 | 样机 → 组件 | — |
| SUITABLE_FOR | 56 | 样机 → 应用场景 | — |
| HAS_DRIVE_MECHANISM | 46 | 样机 → 驱动 | — |
| DEVELOPED_BY | 43 | 样机 → 研制单位 | — |
| HAS_REFERENCE | 40 | 样机 → 文献 | — |
| FUNDED_BY | 1 | 样机 → 资助方 | — |
| **总计** | **625** | | |

---

# §4 跨层桥梁：4 类细分 MIMICS（论文创新 1 核心）

## 4.1 边的结构

50 条 MIMICS 边里，**每一条都打 4 个分数 + 1 个主导维度**：

```
(KUBeetle-S) ───── MIMICS ───────────────────► (甲虫)
                  ├ mimics_aero         = 0.82
                  ├ mimics_kinematics   = 0.68
                  ├ mimics_morphology   = 0.74
                  ├ mimics_scale        = 0.91   ← dominant
                  ├ mimics_dominant_type  = "scale"
                  └ mimics_dominant_score = 0.91
```

## 4.2 4 类相似度的物理含义

| 维度 | 比的是什么 | 物理意义 |
|---|---|---|
| `mimics_aero` | 雷诺数、Strouhal 数 | 是否在同一气动机理区间（前缘涡 / 准定常）|
| `mimics_kinematics` | 扑频比 | 扑动时间尺度是否一致 |
| `mimics_morphology` | 展弦比、悬停能力 | 翼形几何 + 能力一致性 |
| `mimics_scale` | 重量、翼展量级 | 是否在同一物理尺度 |

## 4.3 计算公式

**单值 vs 单值**（对数尺度的相对距离）：

```
sim_log(a, b) = exp(-|log(a/b)|)
```

值域 (0, 1]，相对差 1 倍 → 0.37、相对差 10 倍 → 0.10。

**工程层单值 vs 生物层 [min, max] 区间**：

```
若工程值在生物区间内 → 1.0
否则按最近邻取相对距离 → exp(-|log(value / nearest)|)
```

**主导类型**：4 类分数中的最大值对应的维度，写入 `mimics_dominant_type`。

## 4.4 主导维度的统计分布（50 条边）

按 `dominant_type` 看 50 条 MIMICS 边的分布（粗略）：

| dominant_type | 边数 | 含义 |
|---|---|---|
| `scale` | ~18 | 尺度主导仿生（最常见，因为体型容易匹配）|
| `kinematics` | ~14 | 扑频驱动型仿生 |
| `aero` | ~11 | 气动机理仿生 |
| `morphology` | ~7 | 形态仿生（最少，因为形态严格匹配难）|

## 4.5 为什么这是创新 1 的"核心抓手"

**单层本体**只能说"借鉴自甲虫"——是个字符串标签。
**双层本体 + 4 类细分**让"借鉴"成为**可量化、可反查、可多对多**的关系：

| 操作 | 单层做不到 | 双层做得到 |
|---|---|---|
| 反查："哪些样机仿生甲虫？" | 全表扫字符串 | 一跳 MATCH |
| 量化："KUBeetle-S 在哪个维度最像甲虫？" | 字段中无 | dominant_type=scale, score=0.91 |
| 多生物：一架样机同时仿生甲虫 + 独角仙 | 字符串爆炸 | 两条 MIMICS 边各自带 4 分数 |
| 多跳推理："仿食蚜蝇的 DelFly 是哪所大学做的？" | 跨层断链 | 沿 MIMICS → DEVELOPED_BY 一跳到底 |

---

# §5 7 步调整全记录

时间点：**2026-06-16**，3 阶段共 7 个脚本，全部幂等可重跑。

## P0 阶段：数据完整性补全

### ① P0-A：诊断现状

- 脚本：`kg_diagnose.py`
- 输出：`papers/kg-diagnostics/diagnose-report.md`
- **3 大问题诊出**：
  - Organism 完整度仅 7.7%（只有名字）
  - FWMAV 完整度 63.5%
  - 属性命名混乱：`weight_g` / `weight_total_g` / `weight_takeoff_g` 4 种叫法

### ② P0-1：补全 23 个 Organism 属性 ⭐

- 脚本：`p0_1_enrich_organisms.py`
- **完整度 7.7% → 100%**（+92.3 pp）
- 每个生物补 16+ 属性：体重区间、翼展区间、扑频区间、雷诺数、Strouhal 数、悬停能力
- 数据来源：
  - Pennycuick 1996（鸟类扑频权威）
  - Greenewalt 1975（早期鸟类飞行综述）
  - Shyy 2013（Cambridge UP 扑翼气动学）
  - Tennekes 2009（《飞行的简单科学》）
  - AnAge / EOL / Wikipedia 公开数据库

**为什么是核心**：单层本体把"借鉴自蜂鸟"压成字符串；P0-1 让生物层成为有完整参数的一等公民节点——双层本体能成立的物理基础。

### ③ P0-2：补全 36 个 FWMAV 属性

- 脚本：`p0_2_enrich_fwmavs.py`
- 36/39 节点共补 114 条新属性（3 个原本完整的跳过）
- 每条带 `p0_2_source` 注释回溯
- **完整度 63.5% → ~95%**

### ④ P0-3：属性命名标准化 ⭐

- 脚本：`p0_3_standardize_props.py`
- 加 4 个 `*_std` 标准字段，**100% 覆盖**：
  - `weight_g_std` (39/39)
  - `endurance_s_std` (39/39)
  - `speed_max_m_s_std` (39/39)
  - `frequency_hz_min_std` (39/39)
- 旧字段保留便于回溯

**为什么是核心**：张量分解需要**统一规格的 39×14×5 张量**——没有标准化字段，张量根本组装不起来。P0-3 是创新 3 的物理基础。

## P1 阶段：跨层桥梁 + 性能子结构

### ⑤ P1-1：MIMICS 关系细分 + 自动打分 ⭐⭐⭐

- 脚本：`p1_1_mimics_score.py`
- 50 条 MIMICS 边全部升级为 4 类分数 + dominant_type
- **这是创新点 1 的核心实现**

**调整前**：
```
(KUBeetle-S) ──MIMICS──► (甲虫)   # 一条裸边
```

**调整后**：
```
(KUBeetle-S) ──MIMICS──► (甲虫)
   ├ mimics_aero=0.82
   ├ mimics_kinematics=0.68
   ├ mimics_morphology=0.74
   ├ mimics_scale=0.91
   ├ mimics_dominant_type="scale"
   └ mimics_dominant_score=0.91
```

### ⑥ P1-2：引入 Performance 节点 ⭐⭐

- 脚本：`p1_2_performance_nodes.py`
- **新增 272 个 Performance 节点 + 272 条 HAS_PERFORMANCE 边**
- 覆盖 39/39 个 FWMAV，每架平均 7 个性能数据点
- 字段：metric / value / unit / condition / source_field

**为什么是核心**：原扁平字段无法表达"不同条件下的不同测得值"；Performance 子节点提供**创新 3 张量的第 3 维度**（performance × condition）。没有它，张量退化成 2 阶矩阵。

## P2 阶段：长尾完善

### ⑦ P2-1：补 8 个 FWMAV 文献溯源

- 脚本：`p2_1_add_references.py`
- Reference 覆盖率 79% → **100%**（39/39）
- 6 个标 `inferred`，留待补真实 DOI

### ⑧ P2-2：108 个 Equipment 分类

- 脚本：`p2_2_equipment_categorize.py`
- 给所有 Equipment 节点加 `category` 字段，10 类：

| category | 数量 | 例子 |
|---|---|---|
| actuator | 23 | 电机、舵机、伺服 |
| sensor | 21 | IMU、加速度计、磁、光流 |
| power | 16 | 锂电池、太阳能 |
| flight_control | 14 | 微控制器、飞控 |
| payload | 9 | 相机、影像 |
| wing | 8 | 机翼/翼面材料 |
| structure | 7 | 碳纤维、ABS |
| communication | 5 | 无线、Wi-Fi、蓝牙 |
| transmission | 2 | 齿轮、传动 |
| other | 3 | 不分类 |

---

# §6 调整前后对比

```
                  调整前 (P0 之前)      调整后 (P2 完成)
                  ─────────────────    ─────────────────
节点总数              332                  612    (+280)
关系总数              345                  625    (+280)

Organism 完整度        7.7%                 100%   (+92.3 pp) 🚀
FWMAV 完整度          63.5%                ~95%   (+31.5 pp)
属性命名              混乱 4 种叫法         100% 标准化
MIMICS 维度信息       零                   4 类分数 + dominant
Performance 节点       0                   272                ⭐
Reference 覆盖        79%                  100%
Equipment 分类         零                   10 类
```

---

# §7 KG 对论文 4 个创新点的支撑

| 创新点 | 调整前 | 调整后 | 关键脚本 |
|---|---|---|---|
| **创新 1：双层本体** | ❌ 生物层是空壳 | ✅ 生物层完整属性 + 4 类细分 MIMICS | P0-1 + P1-1 |
| **创新 2：工具增强 ReAct** | ⚠️ 工具校验缺数据 | ✅ 4 个物理工具的输入参数 100% 覆盖 | P0-2 + P0-3 |
| **创新 3：张量分解粗筛** | ❌ 张量稀疏 70%+ | ✅ 39×14×5 张量数据齐 | P0-3 + P1-2 |
| 创新 4：FWMAV-QA Benchmark | — | ✅ A 类题答案直接来自 KG（gold_entities 可标）| 全部 |

**结论**：**这 7 步调整不是"清理工作"——是"让论文 3 个创新点能跑起来"的物理基础**。
- 没有 P0-1，创新 1 双层本体没生物层
- 没有 P1-1，创新 1 没数值证据
- 没有 P1-2，创新 3 张量第 3 维度没数据
- 没有 P0-3，创新 3 张量根本组装不起来

---

# §8 当前已知瑕疵与修补建议

按严重程度排：

### 🟡 数据小瑕疵（不影响实验，但建议合并）

| 瑕疵 | 当前状态 | 建议 |
|---|---|---|
| `Organism: "凤凰"` | 神话生物 | 合并到"金鹰"或重命名为"大型猛禽" |
| `Organism: "甲虫"` vs `"甲虫 (Beetle)"` | 重复 | 合并 |
| `Organism: "昆虫"` vs `"昆虫 (布局)"` | 重复 | 合并 |
| 23 → 20 个 Organism | 当前 | 合并后更干净 |

### 🟡 数据待回填

| 项 | 数量 | 备注 |
|---|---|---|
| `inferred` Reference | 6 个 | 待补真实 DOI（Bionic Flying Fox 等）|

### 🟢 系统局限（不算瑕疵，是 SCOPE 决策）

| 项 | 说明 |
|---|---|
| 39 架样机是小样本 | 张量分解的因子有旋转模糊；论文 §6 已暴露 |
| 仅工程层 + 生物层 2 层 | 未来工作可加材料层、加工层（§6 未来方向）|

---

# §9 KG 复制方法（给新协作者）

如果你需要从头搭一个等价的 KG：

```bash
# 1. 安装 Neo4j Desktop
# 2. 设置 NEO4J_PASSWORD 环境变量
export NEO4J_PASSWORD="your-password"

# 3. 按顺序跑脚本（每个都幂等）
cd papers/fwmav-qa-benchmark/scripts/
python kg_diagnose.py            # 诊断（先跑看现状）
python p0_1_enrich_organisms.py  # 23 个 Organism 属性
python p0_2_enrich_fwmavs.py     # 36 个 FWMAV 属性
python p0_3_standardize_props.py # 4 个 *_std 字段
python p1_1_mimics_score.py      # 50 条 MIMICS 4 类分数
python p1_2_performance_nodes.py # 272 个 Performance 节点
python p2_1_add_references.py    # 8 个 Reference 节点
python p2_2_equipment_categorize.py # 108 个 Equipment 分类

# 4. 重跑 diagnose 看结果
python kg_diagnose.py --output ../papers/kg-diagnostics/diagnose-report-after-p2.md
```

---

# §10 配套文件清单

```
papers/
├── kg-diagnostics/
│   ├── diagnose-report.md             ← P0 前的诊断
│   ├── diagnose-report-after-p2.md    ← P2 后的诊断
│   └── p0-p2-summary.md               ← 机器汇总报告
│
├── KG-STRUCTURE.md                    ← 本文件
│
└── fwmav-qa-benchmark/scripts/
    ├── kg_diagnose.py
    ├── p0_1_enrich_organisms.py
    ├── p0_2_enrich_fwmavs.py
    ├── p0_3_standardize_props.py
    ├── p1_1_mimics_score.py
    ├── p1_2_performance_nodes.py
    ├── p2_1_add_references.py
    └── p2_2_equipment_categorize.py
```

---

# §11 一段话总结

> **当前 KG 是一个 612 节点 / 625 关系的双层结构**——生物原型层 23 个 Organism + 工程样机层 39 个 FWMAV，由 50 条 MIMICS 边跨层桥接（每条带 4 类相似度分数 + 主导维度）。**通过 7 步调整把它从"裸图"升级到"论文支撑级"**：补全 23 个生物属性（创新 1 物理基础）、标准化 4 个 FWMAV 字段（创新 3 物理基础）、引入 272 个 Performance 节点（创新 3 第 3 维度）、给 50 条 MIMICS 边打 4 类相似度分数（创新 1 核心抓手）、补 8 篇文献 + 给 108 个组件分类（数据完整度收尾）。**没有这 7 步，论文 3 个创新点都无法成立。**
