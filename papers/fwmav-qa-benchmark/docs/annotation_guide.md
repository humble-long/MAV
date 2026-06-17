# FWMAV-QA 标注协作者指南

> 给协作标注者看的快速上手文档
> 数据集目标：800 题（A1×150, A2×150, A3×150, A4×150, B1×100, B2×100）
> 当前进度：30 道种子题（已校验通过）

---

## 1. 你需要做什么

按照 `data/seed.jsonl` 里 30 道种子题的格式，写出分配给你的题目。

每道题写完后，用 `python3 scripts/validate.py data/your_batch.jsonl` 校验通过即可提交。

---

## 2. 一次写题的 5 个步骤

### Step 1：选类别 + 难度
- 类别：A1/A2/A3/A4/B1/B2 中的一个
- 难度：1（基础事实）/ 2（中等推理）/ 3（多跳/跨域）

### Step 2：写自然语言问题
- 用户视角，避免学术腔
- 长度 10-50 字，**不要一句话有多个问号**

### Step 3：写 gold_answer
- A1/A2 类：1-3 句话，事实型
- A3 类：3-5 句，对比型，说清楚"差异"在哪
- A4 类：4-7 句，推理型，说清楚"原因"或"是否可行"
- B 类：列出 Top-3 推荐 + 每个 1 句推荐理由

### Step 4：填 KG 锚点
- `gold_entities`: 答案中提到的所有 KG 节点名（必须能在 KG 里找到）
- `gold_relations`: 涉及的关系类型（如 MIMICS, DEVELOPED_BY, has_performance）
- `expected_hops`: 这个题需要在 KG 上走几跳？

### Step 5：填工具调用 + 文献溯源
- `tool_call_required`: 这个题应该调哪些工具？（hassanalian_weight / shyy_scaling_law / strouhal_check / reynolds_check）
- `support_docs`: 答案的依据文献

---

## 3. KG 里有什么数据可用

### 39 架扑翼飞行器（FlappingWingVehicle）
含字段：wingspan_mm、weight_g_std、frequency_hz_min/max_std、endurance_s_std、speed_max_m_s_std、can_hover

### 23 种生物原型（Organism）
含字段：scientific_name、body_mass_g_min/max、wingspan_cm_min/max、flap_freq_hz_min/max、cruise_speed_m_s_min/max、can_hover、reynolds_min/max、strouhal_min/max

### 50 条 MIMICS 仿生映射
每条带 4 类相似度分数（mimics_aero / mimics_kinematics / mimics_morphology / mimics_scale）+ dominant_type/score

### 其他实体
- 33 个研制单位（Organization）
- 44 种驱动机构（DriveMechanism）
- 108 个组件（Equipment）— 已分 10 类（actuator/sensor/power/...）
- 54 类应用场景（Application）
- 39 篇文献（Reference）

### 272 个 Performance 节点
每架飞行器约 7 个性能节点：weight, wingspan, speed_max, frequency_min/max, endurance, hover

---

## 4. 题目设计原则

### ✅ 写好的题目是这样的
- **答案能从 KG 直接验证**："DelFly Nimble 翼展是多少？" → 330 mm，KG 里能查到
- **生物-工程跨域**："参考蜂鸟做 30km 续航能行吗？" → 涉及生物层 + 工程层 + 工具调用
- **多跳推理**："列出所有用压电驱动的微型扑翼机" → MIMICS-Insect + HAS_DRIVE_MECHANISM

### ❌ 不要写这样的题目
- 答案不在 KG 里："谁是扑翼飞行器之父？" → KG 里没有这种节点
- 主观题：："你觉得最好的扑翼机是？" → 没有 gold answer
- 一题多问："X 的翼展是多少？它由谁研制？怎么仿生的？" → 拆成 3 题
- 答案在变化的："2025 年最新的扑翼机是什么？" → 不可重复验证

---

## 5. 各类别题目模板

### A1（单跳·定义类）模板
- "什么是 X？"
- "X 的定义是什么？"
- "X 与 Y 的区别是什么？（概念层面）"

样例：kq_001 ~ kq_008

### A2（单跳·属性类）模板
- "X 的 [属性] 是多少？"
- "X 由哪个机构研制？"
- "哪些 X 满足条件 C？"
- "用了 X 驱动机制的飞行器有哪些？"

样例：kq_009 ~ kq_016

### A3（多跳·对比类）模板
- "X 和 Y 在 [属性] 上有什么差异？"
- "FESTO/某机构 旗下的 N 个机型分别如何？"
- "哪些飞行器在仿生映射中以 [类型] 为主导？"

样例：kq_017 ~ kq_023

### A4（多跳·推理类）模板
- "为什么 X 比 Y 更 [属性]？"
- "参考 X 设计 Y 是否可行？"
- "如果想实现任务 T，应该参考什么生物原型？"
- "X 在 KG 里被标记为 Z 的原因是什么？"

样例：kq_024 ~ kq_027

### B1（简单约束推荐）模板
- "我想做 [尺度] + [能力] 的扑翼机，推荐参考样机？"
- "想以 [生物] 为仿生原型设计，有哪些样机？"

样例：dr_001 ~ dr_003

### B2（复杂约束推荐）模板
- "续航 X + 载重 Y + 任务类型 Z + 仿生原型 W，推荐方案？"
- 需要 4+ 个约束维度

---

## 6. 一些避坑提示

| 坑 | 避坑做法 |
|---|---|
| KG 里有 "甲虫" 和 "甲虫 (Beetle)" 重复节点 | 用 "甲虫 (Beetle)" 这个版本 |
| 重量字段有 weight_total/empty/takeoff 三种 | **答案直接说原始值；问题里说"起飞重量"或"空重"任选** |
| 频率有的是数字、有的是 "15-20" 字符串 | 答案直接复制 KG 里的字符串 |
| PigeonBot 不是真扑翼机 | 标注时**不要**问 PigeonBot 的扑频 |
| 凤凰节点是神话生物 | 不出现在题目中，仅作 KG 占位 |

---

## 7. 提交流程

1. 在 `data/` 下新建 `batch_<你名字>_<日期>.jsonl`，一行一题
2. 跑 `python3 scripts/validate.py data/batch_xxx.jsonl`，确保 0 errors
3. 抽查 5-10 题，跑 `check_seed_against_kg.py`（自己仿照写）确认答案一致
4. 提交给我（王嘉龙）做交叉校验

---

## 8. 工作量估计

| 类别 | 单题耗时 | 80 题/人耗时 |
|---|---|---|
| A1 | 5-8 分钟 | 6-10 小时 |
| A2 | 4-6 分钟 | 5-8 小时 |
| A3 | 8-12 分钟 | 11-16 小时 |
| A4 | 12-20 分钟 | 16-26 小时 |
| B1 | 8-12 分钟 | 11-16 小时 |
| B2 | 15-25 分钟 | 20-33 小时 |

3 人协作，每人均摊 ~270 题，约 35-45 小时。

---

## 9. 联系人

- 主负责人：王嘉龙（2024260137）
- KG 维护：王嘉龙
- 任何问题：先在群里问，或发邮件
