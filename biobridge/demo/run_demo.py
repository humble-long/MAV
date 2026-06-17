"""BioBridge-GraphRAG 创新点 2 端到端 Demo.

跑 3 个真实查询来展示完整推理链路：
1. 知识查询：Strouhal 数 + 工具校验
2. 复杂可行性推理：参考蜂鸟做 30 分钟续航
3. 方案推荐精排：30 km 续航 + 50 g 载重
"""

from __future__ import annotations
import os
import sys
import json

# 让脚本能直接 python3 demo/run_demo.py 跑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from biobridge.agent.llm_client import LLMClient
from biobridge.agent.react_loop import react_loop


DEMO_QUERIES = [
    {
        "id": "demo_1_definition_with_tool",
        "title": "知识查询·定义类（涉及计算）",
        "query": "什么是 Strouhal 数？验证一下 DelFly Nimble（扑频 17 Hz、翼展 330 mm、速度 7 m/s）的 Strouhal 数是否在最优区间。",
        "expected_tools": ["strouhal_check"],
    },
    {
        "id": "demo_2_feasibility_reasoning",
        "title": "可行性推理·跨域",
        "query": "想做一架续航 30 分钟、载重 50 g 的扑翼机，参考蜂鸟原型可行吗？",
        "expected_tools": ["search_organism", "hassanalian_weight", "shyy_scaling_law"],
    },
    {
        "id": "demo_3_recommendation_with_filter",
        "title": "方案推荐·多约束",
        "query": "推荐一架翼展不超过 200 mm、能悬停的微型扑翼机参考样机。",
        "expected_tools": ["search_fwmav"],
    },
]


def run_one(demo: dict, llm: LLMClient):
    """跑一个 demo 并打印结果."""
    print("\n" + "█" * 70)
    print(f"█  Demo: {demo['title']}")
    print(f"█  ID: {demo['id']}")
    print("█" * 70)
    print(f"\n📝 用户问题：{demo['query']}\n")

    result = react_loop(demo["query"], llm=llm, max_iterations=6, verbose=True)

    print("\n" + "─" * 70)
    print(f"📊 推理摘要：")
    print(f"   迭代次数: {result['iterations']}")
    print(f"   调用工具: {result['tools_called']}")
    print(f"   预期工具: {demo['expected_tools']}")
    print("─" * 70)

    return result


def main():
    print("=" * 70)
    print("  BioBridge-GraphRAG 创新点 2 端到端 Demo")
    print("  ReAct 范式：LLM × KG × 物理工具")
    print("=" * 70)

    # 初始化 LLM（自动检测 API key，没有则 mock）
    llm = LLMClient(mode="auto")

    results = []
    for demo in DEMO_QUERIES:
        result = run_one(demo, llm)
        results.append({
            "id": demo["id"],
            "title": demo["title"],
            "query": demo["query"],
            "iterations": result["iterations"],
            "tools_called": result["tools_called"],
            "final_answer": result["final_answer"][:500] if result.get("final_answer") else None,
        })

    # 汇总报告
    print("\n\n" + "█" * 70)
    print("█  Demo 总览")
    print("█" * 70)
    print(f"\n模式: {llm.mode}")
    print(f"共跑 {len(DEMO_QUERIES)} 个 demo\n")
    for r in results:
        print(f"  [{r['id']}]  {r['title']}")
        print(f"     迭代={r['iterations']}, 工具={r['tools_called']}")

    # 保存结果到 JSON
    out_path = os.path.join(os.path.dirname(__file__), 'demo_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📁 完整结果已保存到: {out_path}")


if __name__ == "__main__":
    main()
