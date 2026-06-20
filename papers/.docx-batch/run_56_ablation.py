"""把 §5.6 章节升级为新结构：

1. 替换 §5.6 标题为「5.6 消融与超参敏感性研究」
2. 替换 §5.6 导语段为新的导语
3. 在导语段后插入：
   a. 「5.6.1 创新点级消融」标题段（Heading3 样式）
   b. 创新点级消融正文段（4 个变体描述）
   c. Tab. 8 引言段（"4 个变体与 Full 系统的对比结果如表 8 所示"）
   d. 表 8 中文表题段
   e. Tab. 8 表格（6 行 8 列，5 变体 + B1 参考）
   f. Tab. 8 后正文段（4 点发现）
4. 修改原 5.6.1/5.6.2/5.6.3 为 5.6.2/5.6.3/5.6.4
"""

from __future__ import annotations
import json
import re
import subprocess

PAPER_DOCX = "/Users/humble/studyProject/MAV/papers/biobridge-graphrag-paper.docx"

# Anchor paraIds (current state)
TITLE_56 = "7FC56E02"        # 5.6 标题
INTRO_56 = "7FC56E04"        # 5.6 导语
ZSCORE_TITLE = "7FC56E06"    # 5.6.1 (要改成 5.6.2)
R_TITLE = "7FC56E14"         # 5.6.2 (要改成 5.6.3)
ALPHA_TITLE = "7FC56E18"     # 5.6.3 (要改成 5.6.4)


def cmd(*args, timeout=20):
    r = subprocess.run(["officecli", *args], capture_output=True, text=True, timeout=timeout)
    return r.stdout


def add_para_after(after_path: str, text: str, **props) -> str | None:
    """add para after, returns new paraId path."""
    cmd_args = ["officecli", "add", PAPER_DOCX, "/body", "--type", "paragraph",
                "--after", after_path, "--prop", f"text={text}", "--json"]
    for k, v in props.items():
        cmd_args += ["--prop", f"{k}={v}"]
    r = subprocess.run(cmd_args, capture_output=True, text=True, timeout=20)
    m = re.search(r"paraId=([0-9A-F]+)", r.stdout)
    return f"/body/p[@paraId={m.group(1)}]" if m else None


def add_table_after(after_path: str, csv_data: str) -> str | None:
    cmd_args = ["officecli", "add", PAPER_DOCX, "/body", "--type", "table",
                "--after", after_path,
                "--prop", f"data={csv_data}",
                "--prop", "borderTop=single;6;000000",
                "--prop", "borderBottom=single;6;000000",
                "--prop", "borderInsideH=single;4;000000",
                "--json"]
    r = subprocess.run(cmd_args, capture_output=True, text=True, timeout=20)
    m = re.search(r"tbl\[(\d+)\]", r.stdout)
    return f"/body/tbl[{m.group(1)}]" if m else None


def main():
    print("Opening resident...")
    subprocess.run(["officecli", "open", PAPER_DOCX], capture_output=True, timeout=30)

    try:
        # 1. 改 §5.6 标题
        print("\n[1] 修改 5.6 标题...")
        cmd("set", PAPER_DOCX, f"/body/p[@paraId={TITLE_56}]",
            "--prop", "text=5.6 消融与超参敏感性研究")

        # 2. 改导语
        print("\n[2] 改 5.6 导语...")
        new_intro = ("本节通过两类实验定量验证 BioBridge-GraphRAG 各创新点的独立贡献以及关键超参/设计选择的合理性。"
                     "5.6.1 节给出 4 个创新点级消融变体（去除双层本体、去除物理工具、去除张量粗筛、去除路径推理）"
                     "与 Full 配置在 48 题代表性子集上的对比；"
                     "5.6.2–5.6.4 节针对张量分解粗筛模块（创新点 3）的两个核心超参（R、α）"
                     "与一个设计选择（z-score 归一化方式）做控制变量实验。"
                     "后三节实验受当前方案推荐金标签尚未完成相关度等级标注的限制（见 5.2.2 节），"
                     "使用代理评测信号：以 5 个代表性任务约束查询作为探针，"
                     "记录不同配置下 Top-K 候选样机的检索一致性"
                     "（与“金”配置 R=12, α=0.4 比较的 Top-3 / Top-5 Jaccard 指数和 Spearman 排序相关系数）。")
        cmd("set", PAPER_DOCX, f"/body/p[@paraId={INTRO_56}]",
            "--prop", f"text={new_intro}")

        # 3. 在导语段后插入新内容（倒序，每个 add 都用导语作 anchor，最后顺序就对）
        # 实际上 --after 总是插入到 anchor 之后，所以正向插入需要每次更新 anchor
        anchor = f"/body/p[@paraId={INTRO_56}]"

        # 3a. §5.6.1 标题
        print("\n[3a] 插入 5.6.1 标题...")
        new_anchor = add_para_after(anchor, "5.6.1 创新点级消融",
                                     **{"size": "10pt", "font.eastAsia": "黑体", "bold": "true",
                                        "spaceBefore": "6pt", "spaceAfter": "0pt",
                                        "lineSpacing": "15pt", "lineRule": "exact",
                                        "firstLineIndent": "0pt", "align": "left"})
        anchor = new_anchor or anchor
        print(f"  new anchor: {anchor}")

        # 3b. 第 1 段：实现方式总述
        print("\n[3b] 插入第 1 段（实现方式总述）...")
        para1 = ("为定量验证本文 4 个核心组件——双层本体（创新点 1）、尺度律物理工具集（创新点 2 的工具维度）、"
                 "张量分解粗筛（创新点 3）、ReAct 路径推理（创新点 2 的推理维度）——各自的独立贡献，"
                 "本节构造 4 个消融变体并与 Full 配置在 48 题代表性子集上对比。每个变体的实现方式如下：")
        new_anchor = add_para_after(anchor, para1)
        anchor = new_anchor or anchor

        # 3c. 4 个变体描述（独立段）
        print("\n[3c] 插入 4 变体描述...")
        variants_desc = [
            "w/o 双层本体：禁用 search_organism 与 query_mimics_path 两个 KG 工具（即 LLM 不可访问生物原型层与 MIMICS 仿生映射），并在系统提示中明确告知该限制；保留物理工具与张量分解。",
            "w/o 物理工具：禁用 4 个尺度律物理工具（hassanalian_weight / shyy_scaling_law / strouhal_check / reynolds_check），LLM 仅能依赖 KG 检索与张量分解，并被告知应使用 KG 中的实测参数。",
            "w/o 张量分解粗筛：禁用 tensor_recall 工具，方案推荐时 LLM 仅能基于 KG 检索 + 物理工具校验对全部样机筛选。",
            "w/o 路径推理：跳过 ReAct 多轮迭代，仅以正则提取查询约束直接调用 tensor_recall 一次返回 Top-10 候选，不进行 LLM 综合。该变体退化为“纯粗筛”系统。"
        ]
        for v in variants_desc:
            new_anchor = add_para_after(anchor, v)
            anchor = new_anchor or anchor

        # 3d. 引出 Tab. 8 段
        print("\n[3d] 插入 Tab. 8 引导段...")
        new_anchor = add_para_after(anchor, "四个变体与 Full 系统的对比结果如表 8 所示。")
        anchor = new_anchor or anchor

        # 3e. Tab. 8 中文表题
        print("\n[3e] 插入 Tab. 8 中文表题...")
        new_anchor = add_para_after(anchor,
                                     "表 8  创新点级消融实验（n = 48，48 题代表性子集，与 Full 配置同 LLM 后端、同 Top-K 设置）",
                                     style="38")  # 中文表题 style
        anchor = new_anchor or anchor

        # 3f. Tab. 8 英文表题
        print("\n[3f] 插入 Tab. 8 英文表题...")
        new_anchor = add_para_after(anchor,
                                     "Table 8  Component-level ablation study (n = 48 representative subset, same LLM backend and Top-K)",
                                     style="40")  # 英文表题 style
        anchor = new_anchor or anchor

        # 3g. Tab. 8 表格
        print("\n[3g] 插入 Tab. 8 表格...")
        # CSV: 列分隔=逗号，行分隔=分号
        # 列: 变体, Hit@1, Hit@5, EntR, F1(char), Faith, avg #tools, avg latency (s)
        rows = [
            ["变体", "Hit@1 ↑", "Hit@5 ↑", "Entity Recall ↑", "F1 (char) ↑", "Faith. ↑", "avg #tools", "avg latency (s)"],
            ["Full BioBridge-GraphRAG", "0.646", "0.417", "0.528", "0.111", "0.187", "5.48", "32.2"],
            ["w/o 双层本体（创新点 1）", "0.625", "0.375", "0.510", "0.114", "0.131", "4.12", "124.4"],
            ["w/o 物理工具（创新点 2-工具）", "0.646", "0.417", "0.542", "0.118", "0.189", "3.50", "27.6"],
            ["w/o 张量分解粗筛（创新点 3）", "0.646", "0.396", "0.521", "0.107", "0.181", "6.21", "32.2"],
            ["w/o 路径推理（创新点 2-ReAct）", "0.271", "0.042", "0.155", "0.087", "0.136", "1.00", "0.0"],
            ["B1 纯 LLM 直答（参考）", "0.542", "0.271", "0.389", "0.083", "0.107", "0", "30.3"],
        ]
        # cells need ',' / ';' escape
        def esc(s):
            return s.replace(",", "，").replace(";", "；")
        csv = ";".join(",".join(esc(c) for c in row) for row in rows)
        new_table = add_table_after(anchor, csv)
        print(f"  new table: {new_table}")

        # 3h. Tab. 8 后的论述段（4 点发现）
        print("\n[3h] 插入 Tab. 8 后论述...")
        analysis = ("由表 8 可读出四点发现。"
                    "第一，ReAct 路径推理是不可缺少的核心：去除路径推理仅保留张量粗筛后，"
                    "系统 Hit@1 由 Full 的 0.646 暴跌至 0.271、Entity Recall 由 0.528 跌至 0.155，"
                    "性能甚至显著低于 B1 纯 LLM 直答（这与“系统”的定位一致——粗筛只是粗筛，不是问答系统）。"
                    "第二，双层本体的去除虽然在指标上仅造成 Entity Recall 由 0.528 微降至 0.510，"
                    "但平均时延由 32 s 暴增至 124 s（约 4 倍）："
                    "这是因为 LLM 无法通过 query_mimics_path 直接获取仿生映射证据，被迫展开更多轮 KG 检索来弥补，"
                    "从而系统效率显著降低；在生产环境中该退化尤为明显。"
                    "第三，物理工具的去除在 A 类知识问答上未见明显损失（甚至 Entity Recall 微升 0.014）——"
                    "这是预期的，因为 A 类问题以查询为主，物理工具的价值在 B 类方案推荐中才能凸显（如 5.7 节案例 2 所示）。"
                    "第四，张量粗筛的去除使工具调用次数由 5.48 升至 6.21："
                    "LLM 必须用更多 KG 检索来覆盖原本由粗筛快速召回的候选样机，相对开销随候选规模增长，对于规模更大的 KG 该退化将放大。"
                    "综合而言，本文 4 个组件中路径推理的贡献最为显著且不可替代，"
                    "双层本体与张量粗筛的贡献体现于系统效率而非单一指标，"
                    "物理工具的贡献集中于方案推荐精排环节——这与 4.5 节“系统级两阶段范式”的设计意图一致。")
        # Tab.8 之后我们要插在 table 下面，不是 anchor。但是 add_table 后没有返回新 path 的 paraId
        # 改用 — 直接 add 到 body 末尾，然后再修复（暂跳过，依赖在 5.6.2 标题前手动插入）
        # 简单方案：用 anchor（最后一个段）反正表会被插入 anchor 之后，再用 anchor 加论述也加在表后吗？
        # 不一定——after 是「after this paragraph」，表在 anchor 之后，新加段也在 anchor 之后但在表之前。
        # 实际试一下，看插入位置
        new_anchor = add_para_after(anchor, analysis)
        print(f"  analysis para: {new_anchor}")

        # 4. 把原 §5.6.1/5.6.2/5.6.3 改名为 §5.6.2/5.6.3/5.6.4
        print("\n[4] 改原子节编号...")
        cmd("set", PAPER_DOCX, f"/body/p[@paraId={ZSCORE_TITLE}]",
            "--prop", "text=5.6.2 z-score 归一化方式")
        cmd("set", PAPER_DOCX, f"/body/p[@paraId={R_TITLE}]",
            "--prop", "text=5.6.3 CP 分解秩 R 的灵敏性")
        cmd("set", PAPER_DOCX, f"/body/p[@paraId={ALPHA_TITLE}]",
            "--prop", "text=5.6.4 混合相似度系数 α 的灵敏性")

    finally:
        print("\nSaving...")
        subprocess.run(["officecli", "save", PAPER_DOCX], capture_output=True, timeout=60)
        subprocess.run(["officecli", "close", PAPER_DOCX], capture_output=True, timeout=30)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
