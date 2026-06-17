"""ReAct 推理主循环 - BioBridge-GraphRAG 创新点 2 的核心.

工作流程：
1. 接收用户 query
2. LLM 决定是否调用工具（思考 → 行动）
3. 执行工具 → 把结果加入对话历史（观察）
4. 重复 2-3 直到 LLM 给出最终答案 或 达到 max_iterations
5. 返回完整推理路径 + 最终答案

这就是论文创新点 2 的演示版本。
"""

from __future__ import annotations
import json
from .llm_client import LLMClient, SYSTEM_PROMPT
from biobridge.tools.tool_specs import TOOL_SPECS, call_tool


def react_loop(
    query: str,
    llm: LLMClient = None,
    max_iterations: int = 6,
    verbose: bool = True,
) -> dict:
    """运行 ReAct 推理循环.

    Returns:
        dict {
            "query": str,
            "final_answer": str,
            "iterations": int,
            "trace": [   # 完整推理路径
                {"step": "thought", "content": ...},
                {"step": "action", "tool": ..., "args": ...},
                {"step": "observation", "result": ...},
                {"step": "final_answer", "content": ...}
            ],
            "tools_called": [...]
        }
    """
    if llm is None:
        llm = LLMClient(mode="auto")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

    trace = []
    tools_called = []

    for iter_idx in range(max_iterations):
        if verbose:
            print(f"\n{'='*60}")
            print(f"  Iteration {iter_idx + 1}")
            print(f"{'='*60}")

        # 让 LLM 思考下一步
        response = llm.chat_with_tools(messages, TOOL_SPECS)

        if response.get("tool_calls"):
            # 思考 → 行动
            for tc in response["tool_calls"]:
                tname = tc["name"]
                targs = tc["arguments"]

                trace.append({
                    "step": "action",
                    "tool": tname,
                    "args": targs,
                })
                tools_called.append(tname)

                if verbose:
                    print(f"\n🔧 调用工具: {tname}")
                    print(f"   参数: {json.dumps(targs, ensure_ascii=False)}")

                # 执行工具
                result = call_tool(tname, **targs)

                trace.append({
                    "step": "observation",
                    "tool": tname,
                    "result": result,
                })

                if verbose:
                    # 简略输出工具结果
                    summary = json.dumps(result, ensure_ascii=False)[:300]
                    print(f"   ✓ 结果: {summary}{'...' if len(summary) >= 300 else ''}")

                # 把工具结果加入消息历史
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
            # LLM 给出最终答案
            trace.append({
                "step": "final_answer",
                "content": response["content"],
            })
            if verbose:
                print(f"\n✅ 最终答案：")
                print(response["content"][:500])

            return {
                "query": query,
                "final_answer": response["content"],
                "iterations": iter_idx + 1,
                "trace": trace,
                "tools_called": tools_called,
            }

        else:
            # 无 tool_calls 也无 content - 异常
            break

    # 达到最大迭代
    return {
        "query": query,
        "final_answer": "（达到最大推理步数，未生成最终答案）",
        "iterations": max_iterations,
        "trace": trace,
        "tools_called": tools_called,
    }
