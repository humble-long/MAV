"""ReAct loop 变体——只暴露指定的工具子集 / 完全禁用工具.

用于消融实验：
- w/o 双层本体：禁用 search_organism + query_mimics_path（生物层不可见）
- w/o 工具：禁用所有物理工具，只留 KG 检索
- w/o 张量：禁用 tensor_recall
- w/o 路径推理：跳过 ReAct，直接用 tensor_recall 返回 Top-K 当答案

复用 react_loop.py 的逻辑，只是过滤 TOOL_SPECS。
"""

from __future__ import annotations
import json
from biobridge.agent.llm_client import LLMClient, SYSTEM_PROMPT
from biobridge.tools.tool_specs import TOOL_SPECS, call_tool, ALL_TOOLS


def filter_tool_specs(allowed_names: list[str] | None) -> list:
    """从全局 TOOL_SPECS 过滤出 allowed_names 中的工具.

    None: 全部允许
    []:   完全禁用工具（纯 LLM）
    """
    if allowed_names is None:
        return TOOL_SPECS
    if not allowed_names:
        return []
    return [s for s in TOOL_SPECS if s["function"]["name"] in allowed_names]


def react_loop_subset(
    query: str,
    llm: LLMClient = None,
    max_iterations: int = 6,
    allowed_tools: list[str] | None = None,
    verbose: bool = False,
    extra_system_prompt: str = "",
) -> dict:
    """ReAct 循环 + 工具子集限制.

    Args:
        allowed_tools: 允许使用的工具名列表；None 等价于 react_loop（全部）；[] 完全禁用工具
        extra_system_prompt: 额外的系统提示，用于在消融时告知 LLM 限制

    Returns:
        与 react_loop 相同结构
    """
    if llm is None:
        llm = LLMClient(mode="auto")

    sys_prompt = SYSTEM_PROMPT
    if extra_system_prompt:
        sys_prompt = sys_prompt + "\n\n" + extra_system_prompt

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": query},
    ]

    tools_subset = filter_tool_specs(allowed_tools)
    trace = []
    tools_called = []

    for iter_idx in range(max_iterations):
        if verbose:
            print(f"\n=== Iter {iter_idx+1} (allowed={allowed_tools}) ===")

        response = llm.chat_with_tools(messages, tools_subset)

        if response.get("tool_calls"):
            for tc in response["tool_calls"]:
                tname = tc["name"]
                targs = tc["arguments"]

                # 安全检查：即使 LLM 试图调用未授权工具也阻断
                if allowed_tools is not None and tname not in allowed_tools:
                    if verbose:
                        print(f"   ⚠️  Blocked unauthorized tool call: {tname}")
                    continue

                trace.append({"step": "action", "tool": tname, "args": targs})
                tools_called.append(tname)

                if verbose:
                    print(f"  🔧 {tname}({json.dumps(targs, ensure_ascii=False)[:80]})")

                result = call_tool(tname, **targs)
                trace.append({"step": "observation", "tool": tname, "result": result})

                messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tc.get("id", f"call_{iter_idx}_{tname}"),
                        "type": "function",
                        "function": {"name": tname, "arguments": json.dumps(targs)},
                    }],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{iter_idx}_{tname}"),
                    "name": tname,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        elif response.get("content"):
            trace.append({"step": "final_answer", "content": response["content"]})
            return {
                "query": query,
                "final_answer": response["content"],
                "iterations": iter_idx + 1,
                "trace": trace,
                "tools_called": tools_called,
            }
        else:
            break

    return {
        "query": query,
        "final_answer": "（达到最大推理步数，未生成最终答案）",
        "iterations": max_iterations,
        "trace": trace,
        "tools_called": tools_called,
    }


# ============================================================
# 消融变体定义
# ============================================================

ABLATION_VARIANTS = {
    "full": {
        "name": "Full BioBridge-GraphRAG",
        "allowed_tools": None,  # 全部
        "extra_prompt": "",
    },
    "no_bilayer": {
        "name": "w/o 双层本体（禁用生物层）",
        "allowed_tools": [
            # 物理工具仍然可用
            "hassanalian_weight", "shyy_scaling_law", "strouhal_check", "reynolds_check",
            # KG 检索：去掉 search_organism + query_mimics_path（这两个依赖生物层与 MIMICS）
            "search_fwmav",
            # 张量分解仍可用
            "tensor_recall",
        ],
        "extra_prompt": "注意：本次会话不可访问生物原型层节点。请仅基于工程层的样机参数进行推理。",
    },
    "no_tools": {
        "name": "w/o 物理工具",
        "allowed_tools": [
            # 只留 KG + 张量
            "search_fwmav", "search_organism", "query_mimics_path",
            "tensor_recall",
        ],
        "extra_prompt": "注意：本次会话不可调用尺度律物理工具（hassanalian/shyy/strouhal/reynolds）。请基于 KG 中已有的实测参数进行推理。",
    },
    "no_tensor": {
        "name": "w/o 张量分解粗筛",
        "allowed_tools": [
            "hassanalian_weight", "shyy_scaling_law", "strouhal_check", "reynolds_check",
            "search_fwmav", "search_organism", "query_mimics_path",
            # 不含 tensor_recall
        ],
        "extra_prompt": "注意：本次会话不可使用张量分解粗筛工具。如需推荐方案，请直接基于 KG 检索 + 物理校验对全部样机筛选。",
    },
    "no_pathreasoning": {
        # 这个变体退化为只用粗筛 + 简单格式化
        # 不走 react_loop，单独处理
        "name": "w/o 路径推理（仅粗筛）",
        "allowed_tools": [],  # 不调用 LLM with tools
        "extra_prompt": "",
        "special": "tensor_only",  # 走单独分支
    },
}
