"""创新点 3 端到端 demo - 粗筛 + 精排两阶段流程.

展示 BioBridge-GraphRAG 完整链路：
- Stage 1 (Recall): tensor_recall 张量分解粗筛 → Top-10
- Stage 2 (Rank): hassanalian_weight 物理校验 → Top-3 + 推理理由

这就是论文 §4 的核心范式。
"""

from __future__ import annotations
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from biobridge.agent.llm_client import LLMClient
from biobridge.agent.react_loop import react_loop


DEMO_QUERIES = [
    {
        "id": "innov3_demo_1",
        "title": "微型悬停 - 粗筛 + 精排",
        "query": "推荐一架翼展不超过 200 mm、能悬停的微型扑翼机参考样机。",
    },
    {
        "id": "innov3_demo_2",
        "title": "中型长航时巡航 - 多约束推荐",
        "query": "推荐一架重量 300 g 左右、续航 30 分钟以上、用于户外巡航侦察的扑翼机。",
    },
    {
        "id": "innov3_demo_3",
        "title": "昆虫尺度极致小型化",
        "query": "想做一架重量 0.3 g、翼展 35 mm、扑频 170 Hz 的昆虫尺度扑翼机，推荐参考样机。",
    },
]


def run_one(demo: dict, llm: LLMClient):
    print("\n" + "█" * 70)
    print(f"█  Demo: {demo['title']}")
    print(f"█  ID: {demo['id']}")
    print("█" * 70)
    print(f"\n📝 用户问题：{demo['query']}\n")

    result = react_loop(demo["query"], llm=llm, max_iterations=8, verbose=True)

    print("\n" + "─" * 70)
    print("📊 推理摘要：")
    print(f"   迭代: {result['iterations']}")
    print(f"   工具调用序列: {' → '.join(result['tools_called'])}")
    print("─" * 70)

    return result


def main():
    print("=" * 70)
    print("  BioBridge-GraphRAG 创新点 3 端到端 Demo")
    print("  Stage 1 (Recall): 张量分解粗筛")
    print("  Stage 2 (Rank):   物理工具精排（接入创新点 2）")
    print("=" * 70)

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
        })

    print("\n\n" + "█" * 70)
    print("█  Demo 总览")
    print("█" * 70)
    print(f"\n模式: {llm.mode}\n")
    for r in results:
        used_tensor = "tensor_recall" in r["tools_called"]
        print(f"  [{r['id']}]  {r['title']}")
        print(f"     迭代={r['iterations']}, 调用粗筛={'✅' if used_tensor else '❌'}, "
              f"工具序列={r['tools_called']}")

    out_path = os.path.join(os.path.dirname(__file__), 'innov3_demo_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📁 完整结果已保存到: {out_path}")


if __name__ == "__main__":
    main()
