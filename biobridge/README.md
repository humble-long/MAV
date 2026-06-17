# BioBridge-GraphRAG 创新点 2 — 工具增强的图路径推理

> 论文创新点 2 的可执行 demo
>
> 框架：**LLM × KG × 物理工具**（基于 ReAct 范式 + OpenAI Function Calling 协议）

## 1. 模块结构

```
biobridge/
├── tools/
│   ├── physics_tools.py   4 个物理工具（hassanalian / shyy / strouhal / reynolds）
│   ├── kg_tools.py        3 个 KG 检索工具（search_fwmav / search_organism / query_mimics_path）
│   └── tool_specs.py      OpenAI Function Calling JSON Schema + 统一调度
├── agent/
│   ├── llm_client.py      LLM 客户端（real / mock 双模式）
│   └── react_loop.py      ReAct 推理主循环
└── demo/
    ├── run_demo.py        端到端 demo（3 个真实查询）
    └── demo_results.json  最近一次 demo 输出
```

## 2. 7 个工具一览

### 物理工具（创新点 2 的"灵魂"）

| 工具 | 输入 | 输出 | 来源 |
|---|---|---|---|
| `hassanalian_weight` | 续航 + 载重 | 起飞重量 + 子系统分配 + 可行性 | Hassanalian 2017 (Meccanica) |
| `shyy_scaling_law` | 重量 | 翼展/翼面积/翼载荷/扑频/速度 | Shyy 2013 + Pennycuick 1996 |
| `strouhal_check` | 扑频 + 翼展 + 速度 | St 数 + 是否在 0.2-0.4 区间 | Triantafyllou 1991 |
| `reynolds_check` | 翼弦 + 速度 | Re 数 + 流态判别 | Shyy 2013 §1.3 |

### KG 检索工具

| 工具 | 用途 |
|---|---|
| `search_fwmav` | 按重量/翼展/悬停/仿生原型筛选扑翼机 |
| `search_organism` | 查生物原型参数（生物层） |
| `query_mimics_path` | 双层本体路径查询（含 4 类相似度分数） |

## 3. 运行 demo

```bash
# 必须先启动 Neo4j 并设置密码
export NEO4J_PASSWORD="your-password"

# 可选：用真实 LLM 跑（需要 API key）
export DEEPSEEK_API_KEY="..."   # 或者
export OPENAI_API_KEY="..."

# 运行 demo
cd /Users/humble/studyProject/MAV
python3 biobridge/demo/run_demo.py
```

**自动检测 API key**：找到则用真实 LLM；没找到则回退 mock 模式（用决策树模拟 LLM 决策，仍能跑完所有工具调用流程）。

## 4. 3 个 demo 案例

### Demo 1: 知识查询·涉及计算
> 问：什么是 Strouhal 数？验证 DelFly Nimble（17 Hz, 330 mm, 7 m/s）的 St 是否在最优区间？

期望：调用 `strouhal_check` 计算 St=0.2 → 落入最优区间 ✓

### Demo 2: 可行性推理·跨域
> 问：想做一架续航 30 分钟、载重 50 g 的扑翼机，参考蜂鸟原型可行吗？

期望多步推理：
1. `search_organism("蜂鸟")` → 蜂鸟 2-20 g, 18-80 Hz
2. `hassanalian_weight(30, 50)` → 起飞重量 146.67 g
3. `shyy_scaling_law(146.67)` → 翼展 55 cm, 扑频 7.34 Hz
4. 综合：146 g >> 蜂鸟最大 20 g → **不可行**

### Demo 3: 方案推荐·KG 检索
> 问：推荐翼展不超过 200 mm、能悬停的微型扑翼机？

期望：`search_fwmav(wingspan_max_mm=200, can_hover=True)` → Top-5 候选

## 5. 与论文创新点 2 的对应

```
论文 §4.3 尺度律工具增强的图路径推理
│
├─ §4.3.1 LLM Agent 路径规划         → react_loop.py
├─ §4.3.2 4 个物理工具                → physics_tools.py
├─ §4.3.3 知识查询模式 + 推荐精排模式 → demo 1 (知识) / demo 2-3 (推荐)
└─ §4.3.4 ReAct + Function Calling   → llm_client.py + tool_specs.py
```

## 6. 已知局限（论文实验阶段需补全）

1. **mock 模式决策树过简**：只用关键词匹配；真实 LLM 下决策更智能
2. **没有 beam search**：当前是 greedy（每步只选一个工具），论文的 ToG 风格需要 beam search
3. **Shyy 尺度律**：基于自然界飞行生物拟合，工程实现的扑频系统性偏低（见 `shyy_scaling_law` 的 caveat 字段）
4. **物理工具未涵盖功率密度/电池热管理等次要因素**：足够论文 demo 但工程化还需扩展

## 7. License

MIT
