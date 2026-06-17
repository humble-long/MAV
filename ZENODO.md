# Zenodo 提交指南

> 当本仓库准备发表时，按以下步骤申请 DOI

## 步骤 1: GitHub repo 设置

1. 在 https://github.com/humble-long/MAV/settings 打开 repo
2. 确保 repo 是 Public（Zenodo 只能给公开 repo 发 DOI）
3. 准备一个版本 tag（如 `v1.0`）作为 Zenodo 归档点

## 步骤 2: 注册 Zenodo + 关联 GitHub

1. 打开 https://zenodo.org/login
2. 用 GitHub 账户登录（推荐）
3. 进入 https://zenodo.org/account/settings/github/
4. 找到 `humble-long/MAV` repo，把开关打开（ON）

## 步骤 3: 在 GitHub 上发版本

```bash
# 在本地或 GitHub Web 界面创建 tag
git tag -a v1.0 -m "FWMAV-QA Benchmark v1.0 — 754 questions, BioBridge-GraphRAG framework"
git push origin v1.0
```

或者在 GitHub Web：
- 进入 Releases 页面
- 点 "Draft a new release"
- Tag: `v1.0`
- Release title: `FWMAV-QA v1.0 — 754-question Benchmark for Bionic Flapping-Wing MAV Conceptual Design`
- 描述：见下方模板
- 点 "Publish release"

## 步骤 4: Zenodo 自动归档

发版本后 Zenodo 会自动收到 webhook，5-10 分钟后会出现一个 DOI。
打开 Zenodo Dashboard 查看：https://zenodo.org/account/settings/github/

## 步骤 5: 完善 Zenodo 元数据

打开 Zenodo Record，编辑：

- **Title**: `FWMAV-QA Benchmark: A Knowledge Graph + LLM Question Answering Dataset for Bionic Flapping-Wing MAV Conceptual Design`
- **Authors**: `Wang Jialong (王嘉龙) — Northwestern Polytechnical University`
- **Description**: 见下方模板
- **Keywords**: `Knowledge Graph`, `Large Language Model`, `Bionic Aircraft`, `Flapping-Wing MAV`, `GraphRAG`, `Question Answering`, `Bio-inspired Design`
- **License**: Creative Commons Attribution 4.0 (CC-BY-4.0)
- **Resource type**: Dataset
- **Communities**: 可选加入 "Open Aerospace" 或 "AI for Engineering"

---

## Release / Zenodo 描述模板

```markdown
# FWMAV-QA Benchmark v1.0

A 754-question benchmark dataset for evaluating Knowledge Graph + Large Language Model question answering and design recommendation systems in the bionic flapping-wing micro air vehicle (FWMAV) domain.

## What's Included

- **754 Q&A items** in 6 categories (A1/A2/A3/A4/B1/B2)
  - 200 hand-annotated items (test set, multi-round Subagent reviewed)
  - 554 template-generated items (train/valid set, KG-grounded)
- **Schemas** (JSON Schema for validation)
- **Scripts** to:
  - Diagnose Neo4j knowledge graph completeness
  - Enrich biological prototype attributes
  - Auto-score MIMICS (bio-engineering similarity) relations into 4 sub-types
  - Generate template Q&A items
- **Documentation**
  - Annotation guide
  - KG diagnostic & validation reports
  - Aeronautics journal-style outline (Chinese)

## Companion Framework: BioBridge-GraphRAG

Three innovations:
1. **Bio-Engineering bilayer ontology** with 4 sub-types of MIMICS relations
2. **Scaling-law tool-augmented graph path reasoning** (Hassanalian / Shyy / Strouhal / Reynolds)
3. **Tensor-decomposition-based candidate retrieval** for design recommendation

## License

- Dataset & Docs: CC-BY-4.0
- Code: MIT

## Citation

If you use this dataset, please cite:

@dataset{wang2026fwmavqa,
  title  = {FWMAV-QA: A Benchmark Dataset for Question Answering and Design Recommendation in Bionic Flapping-Wing MAVs},
  author = {Wang, Jialong},
  year   = {2026},
  url    = {https://github.com/humble-long/MAV},
  doi    = {<TBD-Zenodo-DOI>}
}
```
