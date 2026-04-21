"""
Research Agent（知识提取）

输入：用户提供的主题方向 + 原始素材
输出：结构化知识框架文档

先用 Tavily 实时搜索获取最新资讯，再注入 LLM prompt 生成知识框架。
"""
from __future__ import annotations

import os
import logging
from typing import NamedTuple

from agents import BaseAgent
from state import ProjectState, Stage, StageStatus

logger = logging.getLogger(__name__)


class TavilyResult(NamedTuple):
    """Tavily 搜索的结构化结果。text 只有 status='hit' 时非空。"""
    status: str          # "hit" | "no_key" | "http_error" | "empty"
    text: str
    hit_count: int
    reason: str


SYSTEM_PROMPT = """\
你是一个专业的知识研究员，负责为科普视频创作整理知识框架。

你的任务是根据给定的主题方向、原始素材以及最新搜索结果，输出一份结构化的知识框架文档。

输出格式要求（使用 Markdown）：

# 知识框架：{主题名}

## 1. 核心论点与关键事实
- 列出 3-5 个核心论点
- 每个论点附带支撑事实

## 2. 因果关系链条
- 梳理出关键的因果逻辑链
- 用 "A → B → C" 的格式呈现

## 3. 常见误区与反直觉点
- 大众对这个话题的常见误解
- 反直觉的事实（这些是视频的绝佳 hook）

## 4. 关键数据与数字
- 列出核心数据，标注数据来源
- 注意数据的时效性

## 5. 历史案例与人物故事
- 可用于叙事的历史案例
- 关键人物及其故事

## 6. 时事热点关联
- 当前哪些热点与此主题相关
- 为什么"现在"讲这个话题有意义

要求：
- 信息必须准确，不确定的内容标注"待验证"
- 区分事实和观点
- 优先提取对视频创作有价值的内容（能讲故事的、能制造冲突感的、数据震撼的）
- 如果提供了实时搜索结果，优先使用其中的最新数据和事件
"""


def _tavily_search(query: str, max_results: int = 5) -> TavilyResult:
    """调用 Tavily 搜索，返回结构化结果。不抛异常，失败状态由 status 区分。"""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        logger.warning("TAVILY_API_KEY 未配置，跳过实时搜索")
        return TavilyResult("no_key", "", 0, "TAVILY_API_KEY 未配置")

    try:
        import requests
        session = requests.Session()
        session.trust_env = False

        resp = session.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_answer": True,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        reason = str(e)[:200]
        logger.warning(f"Tavily 搜索失败：{reason}")
        return TavilyResult("http_error", "", 0, reason)

    results = data.get("results", []) or []
    if not results:
        return TavilyResult("empty", "", 0, "Tavily 返回 0 条结果")

    lines = ["【实时搜索结果】"]

    # 如果 Tavily 返回了摘要答案
    answer = data.get("answer", "")
    if answer:
        lines.append(f"搜索摘要：{answer}\n")

    for i, result in enumerate(results, 1):
        title = result.get("title", "")
        content = result.get("content", "")
        published = result.get("published_date", "")
        date_str = f"（{published}）" if published else ""
        lines.append(f"{i}. {title}{date_str}")
        # 去掉 URL（对 LLM 理解内容无帮助，浪费 tokens）
        if content:
            snippet = content[:800].replace("\n", " ")  # 截断从400→800，保留更多上下文
            lines.append(f"   摘要：{snippet}")
        lines.append("")

    return TavilyResult("hit", "\n".join(lines), len(results), "")


class ResearchAgent(BaseAgent):
    name = "research_agent"

    def run(self, state: ProjectState) -> ProjectState:
        topic = state["topic_direction"]
        self._log(f"开始知识提取：{topic}")

        def _report(label: str, res: TavilyResult):
            if res.status == "hit":
                self._log(f"✅ Tavily HIT [{label}]: {res.hit_count} 条结果")
            else:
                self._log(f"⚠️ Tavily MISS [{label}]: {res.reason}（已 fallback 到 LLM 内部知识）")

        # 1. Tavily 双重搜索：主话题 + 当前热点背景
        self._log("正在调用 Tavily 实时搜索（主话题）…")
        main_res = _tavily_search(topic)
        _report("主话题", main_res)

        # 补充搜索"当前热点"，帮助 LLM 挖掘跨话题关联
        import time as _time
        year = _time.strftime("%Y")
        context_query = f"{year}年 {topic} 相关热点事件 地缘政治 经济影响"
        self._log("正在调用 Tavily 实时搜索（热点背景）…")
        ctx_res = _tavily_search(context_query, max_results=3)
        _report("热点背景", ctx_res)

        # REQUIRE_TAVILY=1/true/yes：任一搜索未命中则 abort，禁止 fallback
        require = os.getenv("REQUIRE_TAVILY", "").lower() in ("1", "true", "yes")
        if require and (main_res.status != "hit" or ctx_res.status != "hit"):
            raise RuntimeError(
                f"REQUIRE_TAVILY=1 但 Tavily 搜索未命中："
                f"主话题={main_res.status}（{main_res.reason}），"
                f"热点={ctx_res.status}（{ctx_res.reason}）。"
                f"阻止 fallback 到 LLM 内部知识。"
            )

        # 2. 构建用户 prompt
        user_prompt = f"主题方向：{topic}\n\n"

        if main_res.text:
            user_prompt += main_res.text + "\n\n"

        if ctx_res.text:
            user_prompt += "【相关热点背景（供挖掘跨话题关联）】\n" + ctx_res.text + "\n\n"

        if state.get("raw_materials"):
            user_prompt += "用户提供的原始素材：\n"
            for material in state["raw_materials"]:
                user_prompt += f"- {material}\n"
            user_prompt += "\n"
        else:
            user_prompt += "（无额外素材）\n\n"

        user_prompt += "请结合以上所有信息，输出结构化的知识框架文档。"

        # 3. 调用 LLM
        result = self.call_llm(SYSTEM_PROMPT, user_prompt)

        # 4. 更新 State
        state["knowledge_framework"] = result
        state["current_stage"] = Stage.TOPIC
        state["last_agent"] = self.name

        status = dict(state.get("stage_status", {}))
        status[Stage.RESEARCH.value] = StageStatus.COMPLETED.value
        state["stage_status"] = status

        self._log("知识框架生成完成")
        return state
