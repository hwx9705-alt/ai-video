"""
Research Agent（知识提取）

输入：用户提供的主题方向 + 原始素材
输出：结构化知识框架文档

先用 Tavily 实时搜索获取最新资讯，再注入 LLM prompt 生成知识框架。
"""
from __future__ import annotations

import os
import logging

from agents import BaseAgent
from state import ProjectState, Stage, StageStatus

logger = logging.getLogger(__name__)


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


def _tavily_search(query: str, max_results: int = 5) -> str:
    """调用 Tavily 搜索，返回格式化的搜索结果字符串。失败时返回空字符串。"""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        logger.warning("TAVILY_API_KEY 未配置，跳过实时搜索")
        return ""

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
        logger.warning(f"Tavily 搜索失败：{e}")
        return ""

    lines = ["【实时搜索结果】"]

    # 如果 Tavily 返回了摘要答案
    answer = data.get("answer", "")
    if answer:
        lines.append(f"搜索摘要：{answer}\n")

    for i, result in enumerate(data.get("results", []), 1):
        title = result.get("title", "")
        url = result.get("url", "")
        content = result.get("content", "")
        published = result.get("published_date", "")
        date_str = f"（{published}）" if published else ""
        lines.append(f"{i}. {title}{date_str}")
        # 去掉 URL（对 LLM 理解内容无帮助，浪费 tokens）
        if content:
            snippet = content[:800].replace("\n", " ")  # 截断从400→800，保留更多上下文
            lines.append(f"   摘要：{snippet}")
        lines.append("")

    return "\n".join(lines)


class ResearchAgent(BaseAgent):
    name = "research_agent"

    def run(self, state: ProjectState) -> ProjectState:
        topic = state["topic_direction"]
        self._log(f"开始知识提取：{topic}")

        # 1. Tavily 双重搜索：主话题 + 当前热点背景
        self._log("正在调用 Tavily 实时搜索（主话题）…")
        search_results = _tavily_search(topic)

        # 补充搜索"当前热点"，帮助 LLM 挖掘跨话题关联
        import time as _time
        year = _time.strftime("%Y")
        context_query = f"{year}年 {topic} 相关热点事件 地缘政治 经济影响"
        self._log("正在调用 Tavily 实时搜索（热点背景）…")
        context_results = _tavily_search(context_query, max_results=3)

        if search_results or context_results:
            self._log("Tavily 搜索成功，结果已注入 prompt")
        else:
            self._log("Tavily 搜索跳过或失败，仅使用 LLM 内部知识")

        # 2. 构建用户 prompt
        user_prompt = f"主题方向：{topic}\n\n"

        if search_results:
            user_prompt += search_results + "\n\n"

        if context_results:
            user_prompt += "【相关热点背景（供挖掘跨话题关联）】\n" + context_results + "\n\n"

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
