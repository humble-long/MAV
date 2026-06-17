"""LLM 客户端封装 - 兼容 OpenAI / DeepSeek / Anthropic API.

支持两种模式：
1. real: 真实调用 LLM API（需要环境变量配 API key 或 base URL）
2. mock: 离线模拟 LLM 决策（用于演示 + 无需 API 也能跑）

mock 模式使用预定义的"决策脚本"——根据问题文本匹配应该调哪些工具，
是创新点 2 流程的一个 demonstration，不依赖真实 LLM。
"""

from __future__ import annotations
import os
import json
from typing import Optional


SYSTEM_PROMPT = """你是 BioBridge-GraphRAG 系统的核心智能体，专门服务仿生扑翼飞行器（FWMAV）的概念设计。

你有 7 个工具可用：
- 4 个物理工具（hassanalian_weight / shyy_scaling_law / strouhal_check / reynolds_check）
- 3 个 KG 工具（search_fwmav / search_organism / query_mimics_path）

工作流程（ReAct 范式）：
1. 分析用户问题：识别这是『知识查询』还是『方案推荐』
2. 主动调用工具：
   - 涉及生物原型：必先调 search_organism 查生物参数
   - 涉及计算（重量/扑频/St数/Re数）：调对应物理工具
   - 涉及样机推荐：调 search_fwmav + query_mimics_path
3. 综合工具结果生成最终答案，必须：
   - 引用工具输出的具体数值
   - 标明参考的样机/生物
   - 物理可行性结论 + 推荐建议

回答风格：中文、简洁、有数据支撑。如果工具返回 unfeasible 或越界，明确告知用户。"""


class LLMClient:
    """LLM 客户端 - 自适应 API 模式或 mock 模式."""

    def __init__(self, mode: str = "auto"):
        """
        Args:
            mode: 'real' / 'mock' / 'auto'
                - auto: 尝试用 OPENAI_API_KEY / DEEPSEEK_API_KEY，找不到则回退 mock
        """
        self.mode = mode
        self.api_key = None
        self.base_url = None
        self.model = None

        if mode in ("real", "auto"):
            self._try_setup_real_api()

        if self.api_key is None and mode == "real":
            raise RuntimeError("real 模式但未找到 API key")
        if self.api_key is None:
            self.mode = "mock"
            print(f"[LLMClient] 使用 mock 模式（未检测到 API key）")
        else:
            self.mode = "real"
            print(f"[LLMClient] 使用 real 模式: model={self.model}, base={self.base_url}")

    def _try_setup_real_api(self):
        """按优先级尝试 DeepSeek / OpenAI / Tencent qproxy API."""
        # 优先级 1: 显式指定的 OPENAI_BASE_URL（如腾讯 qproxy）
        if os.environ.get("OPENAI_BASE_URL") and os.environ.get("OPENAI_API_KEY"):
            self.api_key = os.environ["OPENAI_API_KEY"]
            self.base_url = os.environ["OPENAI_BASE_URL"]
            self.model = os.environ.get("OPENAI_MODEL", "claude-sonnet-4-6")
        elif os.environ.get("DEEPSEEK_API_KEY"):
            self.api_key = os.environ["DEEPSEEK_API_KEY"]
            self.base_url = "https://api.deepseek.com/v1"
            self.model = "deepseek-chat"
        elif os.environ.get("OPENAI_API_KEY"):
            self.api_key = os.environ["OPENAI_API_KEY"]
            self.base_url = "https://api.openai.com/v1"
            self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def chat_with_tools(self, messages: list, tools: list) -> dict:
        """单轮对话调用，支持工具.

        Returns:
            dict 模拟 OpenAI API 返回结构：
            {
                "role": "assistant",
                "content": "...",          # 文本回答（如果有）
                "tool_calls": [...]        # 要调用的工具（如果有）
            }
        """
        if self.mode == "real":
            return self._call_real_api(messages, tools)
        else:
            return self._call_mock(messages, tools)

    def _call_real_api(self, messages, tools):
        """调用真实 OpenAI 兼容 API."""
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("请先 pip install openai")

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        # 注意: Anthropic 风格的 API（如腾讯 qproxy 的 Claude）要求 max_tokens
        kwargs = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.3,
            "max_tokens": 2048,
        }
        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        return {
            "role": msg.role,
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
                for tc in (msg.tool_calls or [])
            ],
        }

    def _call_mock(self, messages, tools):
        """Mock 模式：基于规则判断该调用什么工具."""
        # 找原始用户问题（用于关键词匹配）
        user_query = ""
        for m in messages:
            if m.get("role") == "user":
                content = m.get("content", "")
                if isinstance(content, list):
                    content = " ".join(str(c) for c in content)
                user_query = content
                break

        # 已经调过的工具
        prior_tool_calls = []
        prior_tool_results = {}
        for m in messages:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    tname = tc.get("name") or tc.get("function", {}).get("name")
                    if tname:
                        prior_tool_calls.append(tname)
            if m.get("role") == "tool":
                tname = m.get("name") or m.get("tool_name")
                if tname:
                    prior_tool_results[tname] = m.get("content", "")

        # 决策：基于原始用户问题 + 已调用工具 决定下一步
        return self._mock_decide(user_query, "user", prior_tool_calls, prior_tool_results)

    def _mock_decide(self, text: str, role: str, prior_tools: list, prior_results: dict) -> dict:
        """简单决策树（论文里这部分会是 LLM 自主推理）."""
        text_lower = text.lower() if isinstance(text, str) else ""
        text_zh = text  # 保留中文

        import re

        # 决策规则（按优先级）：

        # 0. 题目涉及"Strouhal" + 同时给了扑频/翼展/速度 → 调 strouhal_check
        if any(k in text_zh for k in ["Strouhal", "strouhal"]) and "strouhal_check" not in prior_tools:
            freq_m = re.search(r'扑频[^\d]*?(\d+(?:\.\d+)?)\s*Hz', text_zh)
            ws_m = re.search(r'翼展[^\d]*?(\d+(?:\.\d+)?)\s*mm', text_zh)
            sp_m = re.search(r'速度[^\d]*?(\d+(?:\.\d+)?)\s*m/s', text_zh)
            if freq_m:
                args = {"flap_freq_hz": float(freq_m.group(1))}
                if ws_m:
                    args["wingspan_mm"] = float(ws_m.group(1))
                if sp_m:
                    args["flight_speed_m_s"] = float(sp_m.group(1))
                else:
                    args["flight_speed_m_s"] = 5.0
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_strouhal",
                        "name": "strouhal_check",
                        "arguments": args,
                    }],
                }

        # 0b. 涉及"雷诺数 Re" + 弦长/速度 → 调 reynolds_check
        if any(k in text_zh for k in ["雷诺数", "Reynolds", "reynolds"]) and "reynolds_check" not in prior_tools:
            chord_m = re.search(r'(?:翼弦|弦长)[^\d]*?(\d+(?:\.\d+)?)\s*mm', text_zh)
            sp_m = re.search(r'速度[^\d]*?(\d+(?:\.\d+)?)\s*m/s', text_zh)
            if chord_m and sp_m:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_reynolds",
                        "name": "reynolds_check",
                        "arguments": {
                            "chord_mm": float(chord_m.group(1)),
                            "flight_speed_m_s": float(sp_m.group(1)),
                        },
                    }],
                }

        # 1. 题目里提到生物名 + 还没查 search_organism → 先查生物
        bio_keywords = ["蜂鸟", "苍蝇", "蜜蜂", "蜻蜓", "海鸥", "鸽子", "甲虫", "蝙蝠", "鹰", "隼", "鸮", "狐蝠"]
        for bio in bio_keywords:
            if bio in text_zh and "search_organism" not in prior_tools:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": f"call_organism_{bio}",
                        "name": "search_organism",
                        "arguments": {"name": bio},
                    }],
                }

        # 2. 题目涉及"续航 X 分钟" + "载重 Y g" → 调 hassanalian_weight
        endurance_match = re.search(r'续航[^\d]*?(\d+(?:\.\d+)?)\s*(?:分钟|min|km)', text_zh)
        payload_match = re.search(r'载重[^\d]*?(\d+(?:\.\d+)?)\s*g', text_zh)
        if (endurance_match or payload_match) and "hassanalian_weight" not in prior_tools:
            args = {}
            if endurance_match:
                value = float(endurance_match.group(1))
                if "km" in endurance_match.group(0):
                    value = value * 1000 / 12 / 60  # 12 m/s 巡航
                args["endurance_min"] = round(value, 1)
            else:
                args["endurance_min"] = 10
            if payload_match:
                args["payload_g"] = float(payload_match.group(1))
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_hassanalian",
                    "name": "hassanalian_weight",
                    "arguments": args,
                }],
            }

        # 3. 已调 hassanalian → 调 shyy_scaling_law 验证总体参数
        if "hassanalian_weight" in prior_tools and "shyy_scaling_law" not in prior_tools:
            try:
                ham_result = json.loads(prior_results.get("hassanalian_weight", "{}"))
                weight = ham_result.get("total_weight_g", 50)
            except (json.JSONDecodeError, KeyError):
                weight = 50
            if weight:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_shyy",
                        "name": "shyy_scaling_law",
                        "arguments": {"weight_g": float(weight)},
                    }],
                }

        # 4. 题目涉及"推荐"或"参考样机" → 优先调 tensor_recall 做粗筛（创新点 3），再考虑 search_fwmav
        if any(k in text_zh for k in ["推荐", "参考样机", "可参考"]):
            # 4a. 第一步：tensor_recall 粗筛
            if "tensor_recall" not in prior_tools:
                args = {"top_k": 10}
                if "悬停" in text_zh:
                    args["can_hover"] = True
                ws_match = re.search(r'翼展[^\d]*?(?:不超过|≤|<=|<)?\s*(\d+)\s*(?:mm|毫米)', text_zh)
                if ws_match:
                    args["wingspan_mm"] = float(ws_match.group(1))
                w_match = re.search(r'重量[^\d]*?(\d+(?:\.\d+)?)\s*g', text_zh)
                if w_match:
                    args["weight_g"] = float(w_match.group(1))
                if endurance_match := re.search(r'续航[^\d]*?(\d+(?:\.\d+)?)\s*分钟', text_zh):
                    args["endurance_s"] = float(endurance_match.group(1)) * 60
                if "巡航" in text_zh or "侦察" in text_zh:
                    args["mission"] = "task"
                elif "机动" in text_zh or "特技" in text_zh:
                    args["mission"] = "maneuver"
                elif "长航时" in text_zh or "悬停" in text_zh:
                    args["mission"] = "performance"
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_tensor_recall",
                        "name": "tensor_recall",
                        "arguments": args,
                    }],
                }
            # 4b. 第二步：粗筛已有，再用 search_fwmav 验证（可选，演示协同）
            if "search_fwmav" not in prior_tools:
                args = {"limit": 5}
                if "悬停" in text_zh:
                    args["can_hover"] = True
                ws_match = re.search(r'翼展[^\d]*?(?:不超过|≤|<=)?\s*(\d+)\s*(?:mm|毫米)', text_zh)
                if ws_match:
                    args["wingspan_max_mm"] = float(ws_match.group(1))
                for bio in bio_keywords:
                    if bio in text_zh:
                        args["biological_prototype"] = bio
                        break
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_search",
                        "name": "search_fwmav",
                        "arguments": args,
                    }],
                }

        # 5. 都查过了 → 综合答案
        summary_parts = ["[Mock LLM 综合答案]"]
        for tname, tresult in prior_results.items():
            try:
                tr = json.loads(tresult) if isinstance(tresult, str) else tresult
                summary_parts.append(f"\n📌 {tname} 结果摘要：")
                if isinstance(tr, dict):
                    for k, v in list(tr.items())[:6]:
                        if isinstance(v, (list, dict)):
                            v = f"({len(v)} items)" if isinstance(v, list) else str(v)[:80]
                        summary_parts.append(f"   {k}: {v}")
            except Exception:
                summary_parts.append(f"\n   {tname}: {str(tresult)[:120]}")

        summary_parts.append(
            "\n\n🤖 综合判断：基于以上工具调用结果，"
            f"已收集到 {len(prior_results)} 个证据维度。"
            "在真实 LLM 下，这一步会综合所有证据生成自然语言回答；"
            "Mock 模式仅展示流程。"
        )
        return {
            "role": "assistant",
            "content": "\n".join(summary_parts),
            "tool_calls": [],
        }
