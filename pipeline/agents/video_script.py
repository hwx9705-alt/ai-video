"""
VideoScript Agent

输入：state["video_script_json"]（storyboard agent 生成的 StoryboardData JSON）
      + state["script_full"]（完整口播脚本）
输出：更新 state["video_script_json"]，为每段补充：
      - narrationText：对应段落的纯口播文本（已过滤制作标注）

注：新格式中组件 props 直接包含面向观众的内容，
    本 Agent 只负责提取纯口播 narrationText，供 TTS 使用。
"""

import json
import re

from agents import BaseAgent
from state import ProjectState


SYSTEM_PROMPT = """\
你是一个视频内容编辑，负责从口播脚本中为每个分镜段提取对应的纯口播文字。

## 任务

给定分镜段列表（含每段标题和简短的 narrationText 线索）和完整口播脚本，
为每个分镜段提取对应的完整口播文字（narrationText）。

## 要求

1. 根据分镜段的标题/内容线索，从完整脚本中定位对应段落
2. 去除所有制作标注：**[画面提示]**、【语气指令】、（语气说明）、⚠️、--- 分隔线等
3. 只保留真正需要说出口的句子
4. 每段 narrationText 应与 durationInSeconds 大致匹配（中文朗读约 4~5 字/秒）

## 输出格式

只输出 JSON 数组，不要任何解释文字：

[
  {
    "id": 1,
    "narrationText": "纯口播文本，不含任何标注..."
  }
]
"""


class VideoScriptAgent(BaseAgent):
    name = "video_script_agent"

    def run(self, state: ProjectState) -> ProjectState:
        self._log("开始提取各段 narrationText")

        video_script_json = state.get("video_script_json", "")
        script_full = state.get("script_full", "")

        if not video_script_json:
            self._log("⚠️ video_script_json 为空，跳过")
            return state

        try:
            storyboard = json.loads(video_script_json)
        except json.JSONDecodeError as e:
            self._log(f"⚠️ video_script_json 解析失败：{e}，跳过")
            return state

        segments = storyboard.get("segments", [])
        if not segments:
            self._log("⚠️ segments 为空，跳过")
            return state

        # 构造给 LLM 的分镜段摘要
        seg_summary = [
            {
                "id": seg.get("id"),
                "component": seg.get("component", ""),
                "title": seg.get("props", {}).get("title", seg.get("props", {}).get("text", "")),
                "narrationHint": seg.get("narrationText", "")[:100],
                "durationInSeconds": seg.get("durationInSeconds", 12),
            }
            for seg in segments
        ]

        user_prompt = f"""分镜段列表：
```json
{json.dumps(seg_summary, ensure_ascii=False, indent=2)}
```

完整口播脚本：
{script_full[:6000]}

请为每个分镜段提取 narrationText，只输出 JSON 数组。"""

        try:
            result = self.call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.2)
            narrations = self._parse_json_array(result)
        except Exception as e:
            self._log(f"⚠️ LLM 调用失败：{e}，保留原始 video_script_json")
            return state

        if not narrations:
            self._log("⚠️ LLM 输出解析失败，保留原始 video_script_json")
            return state

        # 按 id 建立索引
        narr_map = {item["id"]: item.get("narrationText", "") for item in narrations if "id" in item}

        updated = 0
        for seg in segments:
            sid = seg.get("id")
            if sid in narr_map and narr_map[sid]:
                seg["narrationText"] = narr_map[sid]
                updated += 1

        self._log(f"已为 {updated}/{len(segments)} 个分镜段更新 narrationText")
        state["video_script_json"] = json.dumps(storyboard, ensure_ascii=False)
        state["last_agent"] = self.name
        return state

    @staticmethod
    def _parse_json_array(text: str) -> list:
        m = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
        if m:
            text = m.group(1).strip()
        start = text.find('[')
        end = text.rfind(']')
        if start == -1 or end == -1:
            return []
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return []
