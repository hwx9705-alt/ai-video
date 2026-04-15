"""
Storyboard Agent（分镜规划）

输入：审核通过的完整脚本
输出：StoryboardData JSON（新格式，按组件名分发）

使用 DeepSeek。输出直接对接 remotion-video 渲染器。
"""

import re
import json

from agents import BaseAgent
from state import ProjectState, Stage, StageStatus


SYSTEM_PROMPT = """\
你是一个专业的科普视频分镜师，将脚本转化为 Remotion 视频分镜 JSON。

这是一个"纯画面流"视频（参考B站UP主"小Lin说"）——没有真人出镜。视频的视觉主体是"信息动画"——数字跳动、图表生长、框架展开、文字弹出。AI生图只做背景点缀。

## 可用组件列表

每个分镜段（segment）必须选择以下 9 个组件之一：

### 1. DataReveal — 大数字冲击展示
```
props: {
  number: string,       // 核心数字，如 "3.73亿" "92.07%" "$1.2T"
  prefix?: string,      // 数字前缀，如 "$" "¥"
  suffix?: string,      // 附加后缀（number 中已含的不填）
  subtitle: string,     // 解释这个数字的一句话（不超过40字）
  highlightColor?: string,
  countUp?: boolean     // 默认 true
}
```

### 2. BarChartAnimated — 柱状图（多数据对比）
```
props: {
  title: string,
  data: Array<{ label: string, value: number, color?: string }>,
  unit?: string,
  highlightIndex?: number
}
```

### 3. LineChartAnimated — 折线图（趋势/时间序列）
```
props: {
  title: string,
  data: Array<{ x: string, y: number }>,
  unit?: string,
  annotations?: Array<{ x: string, text: string }>
}
```

### 4. CompareTwo — 左右对比
```
props: {
  title: string,
  left: { label: string, points: string[], color?: string },
  right: { label: string, points: string[], color?: string },
  vsText?: string
}
```

### 5. FlowSteps — 流程/步骤图
```
props: {
  title: string,
  steps: Array<{ label: string, description?: string }>,
  direction?: "horizontal" | "vertical"
}
```

### 6. KeyPoint — 金句/核心观点全屏强调
```
props: {
  text: string,
  emphasis?: string[],
  style?: "quote" | "statement" | "question"
}
```

### 7. TitleCard — 段落标题/章节转场
```
props: {
  title: string,
  subtitle?: string,
  sectionNumber?: number
}
```

### 8. BulletList — 要点列表（3~5条）
```
props: {
  title: string,
  items: Array<{ text: string }>
}
```

### 9. ImageWithOverlay — 图片+文字叠层（氛围/场景）
```
props: {
  imageSrc: string,       // 填 "assets/placeholder.jpg"
  overlayOpacity?: number,
  title: string,
  subtitle?: string
}
```

## 组件选择规则

1. 脚本出现**核心数字**（单个重要数字）→ DataReveal
2. 脚本出现**多个数字对比**（横向比较）→ BarChartAnimated
3. 脚本出现**趋势/时间变化**（随时间的数字序列）→ LineChartAnimated
4. 脚本做**两者对比**（A vs B）→ CompareTwo
5. 脚本讲**流程/步骤/因果链** → FlowSteps
6. 脚本有**一句话总结/金句** → KeyPoint
7. 新话题/段落**开场标题**、视频结尾 → TitleCard
8. 脚本列举**3~5条并列要点** → BulletList
9. 需要**氛围背景** → ImageWithOverlay（不超过总段落20%）

**额外要求：**
- 开头第一段必须是 TitleCard（视频标题）
- 开头第二段必须是 DataReveal 或 KeyPoint（制造冲击感）
- 脚本里的数据必须准确搬到 props，不要编造数据
- 每段时长 8~35 秒，有节奏变化
- 总段落数 10~18 个

## 输出格式

只输出合法 JSON，不要任何解释文字，不要 markdown 代码块：

{
  "title": "视频标题",
  "totalDurationInSeconds": 总秒数,
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "segments": [
    {
      "id": 1,
      "component": "TitleCard",
      "props": { ... },
      "durationInSeconds": 8,
      "transition": "fade",
      "narrationText": "对应的口播文字..."
    }
  ]
}
"""


ALLOWED_COMPONENTS = {
    "DataReveal", "BarChartAnimated", "LineChartAnimated",
    "CompareTwo", "FlowSteps", "KeyPoint", "TitleCard",
    "BulletList", "ImageWithOverlay",
}


class StoryboardAgent(BaseAgent):
    name = "storyboard_agent"

    def run(self, state: ProjectState) -> ProjectState:
        self._log("开始生成分镜表")

        user_prompt = f"""请将以下视频脚本转化为分镜 JSON：

完整脚本：
{state['script_full']}

选题提案（参考主题方向）：
{state['topic_proposal']}
"""
        if state.get("review_feedback") and state.get("current_review_gate") == "gate_3":
            user_prompt += f"\n创作者反馈（请据此修改）：\n{state['review_feedback']}\n"
            if state.get("storyboard"):
                user_prompt += f"\n上一版分镜表（需修改）：\n{state['storyboard']}\n"

        result = self.call_llm(SYSTEM_PROMPT, user_prompt)

        # 保留原始文本供审核显示
        state["storyboard"] = result

        # 解析并校验 StoryboardData JSON
        storyboard_data = self._parse_storyboard_data(result)
        if storyboard_data:
            seg_count = len(storyboard_data.get("segments", []))
            total_sec = sum(s.get("durationInSeconds", 12) for s in storyboard_data.get("segments", []))
            storyboard_data["totalDurationInSeconds"] = total_sec
            state["video_script_json"] = json.dumps(storyboard_data, ensure_ascii=False)
            self._log(f"StoryboardData JSON 已生成，{seg_count} 段，共 {total_sec}s")
        else:
            self._log("⚠️ 未能解析出结构化分镜，保留原始文本")

        state["current_stage"] = Stage.STORYBOARD
        state["last_agent"] = self.name

        status = dict(state.get("stage_status", {}))
        status[Stage.STORYBOARD.value] = StageStatus.AWAITING_REVIEW.value
        state["stage_status"] = status
        state["current_review_gate"] = "gate_3"

        self._log("分镜表生成完成，等待审核门3")
        return state

    def _parse_storyboard_data(self, text: str) -> dict | None:
        """从 LLM 输出中提取并校验 StoryboardData JSON"""
        # 去除 markdown 代码块
        m = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
        if m:
            text = m.group(1).strip()

        # 找 JSON 对象
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1:
            return None

        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError as e:
            self._log(f"⚠️ JSON 解析失败：{e}")
            return None

        # 基本校验
        if "segments" not in data or not isinstance(data["segments"], list):
            self._log("⚠️ 缺少 segments 字段")
            return None

        # 确保必填字段
        data.setdefault("fps", 30)
        data.setdefault("width", 1920)
        data.setdefault("height", 1080)

        valid_segs = []
        for i, seg in enumerate(data["segments"]):
            if seg.get("component") not in ALLOWED_COMPONENTS:
                self._log(f"⚠️ segment[{i}] 组件名无效: {seg.get('component')}，跳过")
                continue
            seg.setdefault("id", i + 1)
            seg.setdefault("durationInSeconds", 12)
            seg.setdefault("transition", "fade")
            valid_segs.append(seg)

        data["segments"] = valid_segs
        return data
