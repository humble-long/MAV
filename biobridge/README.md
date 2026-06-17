# BioBridge-GraphRAG — 三大创新点的可执行 demo

> 论文创新点 1（双层本体）+ 创新点 2（路径推理 + 物理工具）+ 创新点 3（张量分解粗筛）的端到端实现
>
> 基于 ReAct 范式 + OpenAI Function Calling 协议

## 1. 模块结构

```
biobridge/
├── tools/
│   ├── physics_tools.py    [创新 2] 4 个物理工具
│   ├── kg_tools.py          [创新 1+2] 3 个 KG 检索工具（含 MIMICS 4 类细分）
│   ├── tensor_recall.py    [创新 3] 张量分解 + KNN 粗筛
│   └── tool_specs.py        OpenAI Function Calling JSON Schema + 统一调度
├── agent/
│   ├── llm_client.py        LLM 客户端（real / mock 双模式）
│   └── react_loop.py        ReAct 推理主循环
└── demo/
    ├── run_demo.py                  创新点 2 端到端 demo（3 个查询）
    ├── run_innov3_demo.py           创新点 3 端到端 demo（粗筛 + 精排）
    └── tensor_decomp_cache.npz      CP 分解缓存
```

## 2. 8 个工具一览

### 物理工具（创新点 2）

| 工具 | 输入 | 输出 | 来源 |
|---|---|---|---|
| `hassanalian_weight` | 续航 + 载重 | 起飞重量 + 子系统分配 + 可行性 | Hassanalian 2017 (Meccanica) |
| `shyy_scaling_law` | 重量 | 翼展/翼面积/翼载荷/扑频/速度 | Shyy 2013 + Pennycuick 1996 |
| `strouhal_check` | 扑频 + 翼展 + 速度 | St 数 + 是否在 0.2-0.4 区间 | Triantafyllou 1991 |
| `reynolds_check` | 翼弦 + 速度 | Re 数 + 流态判别 | Shyy 2013 §1.3 |

### KG 检索工具（创新点 1+2）

| 工具 | 用途 |
|---|---|
| `search_fwmav` | 按重量/翼展/悬停/仿生原型筛选扑翼机 |
| `search_organism` | 查生物原型参数（生物层） |
| `query_mimics_path` | 双层本体路径查询（含 4 类相似度分数） |

### 张量分解工具（创新点 3）

| 工具 | 用途 |
|---|---|
| `tensor_recall` | 3 阶张量 (FWMAV × Feature × Mission) 的 CP 分解粗筛 + KNN，秒级返回 Top-K |

## 3. 运行 demo

```bash
# 必须先启动 Neo4j 并设置密码
export NEO4J_PASSWORD="your-password"

# 安装依赖
pip3 install neo4j tensorly numpy

# 可选：用真实 LLM 跑（需要 API key）
export DEEPSEEK_API_KEY="..."   # 或者 OPENAI_API_KEY

# 创新点 2 demo（4 个物理工具 + KG 检索）
python3 biobridge/demo/run_demo.py

# 创新点 3 demo（粗筛 + 精排两阶段）
python3 biobridge/demo/run_innov3_demo.py
```

**自动检测 API key**：找到则用真实 LLM；没找到则回退 mock 模式（决策树模拟 LLM 决策，仍能跑完所有工具调用流程）。

## 4. Demo 案例总览

### 创新点 2 demo（run_demo.py）

| Demo | 类型 | 关键工具序列 |
|---|---|---|
| 1 | Strouhal 数知识查询 | strouhal_check |
| 2 | 跨域可行性推理 | search_organism → hassanalian_weight → shyy_scaling_law |
| 3 | 翼展约束推荐 | search_fwmav |

### 创新点 3 demo（run_innov3_demo.py）

| Demo | 类型 | 关键工具序列 |
|---|---|---|
| 1 | 微型悬停推荐 | tensor_recall（粗筛）→ search_fwmav（精排）|
| 2 | 中型长航时巡航 | hassanalian_weight（可行性）→ tensor_recall（粗筛）→ search_fwmav（精排）|
| 3 | 昆虫尺度推荐 | tensor_recall → search_fwmav |

## 5. 与论文创新点的对应

```
论文 §4.2 Bio-Engineering 双层本体    → kg_tools.py + KG 数据
论文 §4.3 工具增强的图路径推理         → physics_tools.py + react_loop.py
论文 §4.4 张量分解的方案候选检索       → tensor_recall.py
论文 §5 实验                          → demo/*.py + FWMAV-QA Benchmark
```

## 6. 创新点 3 张量分解的关键设计选择

### 张量结构

```
X (39 × 14 × 5)
  axis 1 (39): FWMAV 节点
  axis 2 (14): 9 Performance metric + 5 Equipment category
  axis 3 (5):  Mission 大类 (research/task/maneuver/performance/other)
```

### 混合相似度

最终采用 **raw 特征 cosine（60%）+ CP 嵌入 cosine（40%）** 的混合相似度：
- raw 特征 cosine 保证物理量级一致性（重量、翼展直接对齐）
- CP 嵌入 cosine 引入潜在语义（同尺度同任务的样机会聚类）
- 经验上 0.4 的 embedding_weight 在 39 样本规模下最稳健

### 与 Jia 2021 (AEI) 的差异

Jia 等人在工程设计领域用 3 阶张量分解 + KNN（DOI:10.1016/j.aei.2021.101505）。本工具的扩展：
1. Feature 维度纳入 Performance + Equipment（Jia 仅用 Performance）
2. 混合相似度（Jia 仅用嵌入空间）
3. 与创新点 2 物理工具协同形成"粗筛 + 精排"两阶段范式

## 7. 已知局限

1. **重构误差 0.39** 偏高：39 样本 + 70+ 参数（rank=12）下不可避免；论文实验阶段可加正则化或贝叶斯张量分解
2. **mock 模式决策树过简**：用关键词匹配；真实 LLM 下决策更智能
3. **Shyy 尺度律基于自然界飞行生物拟合**：工程实现的扑频系统性偏低（见 `shyy_scaling_law` 的 caveat 字段）
4. **没有 beam search**：当前是 greedy；论文 ToG 风格的多路径推理需要扩展

## 8. License

MIT
