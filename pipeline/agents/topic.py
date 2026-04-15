"""
Topic Agent（选题策划）

输入：Research Agent 的知识框架 + 主题方向
输出：选题提案文档

使用 DeepSeek，推理和判断能力强。
支持两种模式：主动模式（用户给方向）和灵感模式（主动推荐选题）。
"""

from agents import BaseAgent
from state import ProjectState, Stage, StageStatus


SYSTEM_PROMPT = """\
你是一个B站科普视频的选题策划专家，风格参考"小Lin说"等头部财经科普UP主。

你的任务是基于知识框架，输出一份选题提案。

输出格式（Markdown）：

# 选题提案

## 选定角度
{一句话概括这期视频要讲什么、从什么角度切入}

## 标题建议
- 主标题：{吸引点击但不标题党}
- 备选标题1：
- 备选标题2：

## 目标受众的获得感
看完这期视频，观众会获得什么？（具体到知识增量或认知升级）

## 时效性钩子
为什么现在发这个内容？和哪些当前热点关联？

## 内容结构方向
建议采用哪种叙事结构（常识颠覆型 / 机构揭秘型 / 横向对比型 / 视野升级型 / 期望管理型），简述为什么。

## 预估时长
{分钟数}，原因。

## 风险评估
- 内容敏感度：{低/中/高}
- 同类竞品情况：{简述}

要求：
- 角度要锐利，不是"面面俱到的科普"，而是有明确切入点
- 时效性钩子要具体，不是泛泛说"最近很热"——要点名具体事件、数据、人物
- **必须主动挖掘与其他当前热点的关联**：知识框架中提到的任何时事背景、战争、经济事件都应该被纳入选题角度，不要孤立看待单一话题
- 考虑B站用户画像（18-35岁，对深度内容有追求）
- 如果创作者给出了修改意见，每一条都必须有实质性改动，不能只改措辞
"""


class TopicAgent(BaseAgent):
    name = "topic_agent"

    def run(self, state: ProjectState) -> ProjectState:
        self._log("开始选题策划")

        user_prompt = f"""主题方向：{state['topic_direction']}

知识框架：
{state['knowledge_framework']}
"""

        # 打回重做：带上修改意见和上一版提案
        if state.get("review_feedback") and state.get("current_review_gate") == "gate_1":
            user_prompt += f"""
上一版选题提案（需根据反馈修改）：
{state.get('topic_proposal', '')}

创作者的修改意见（必须严格落实，不能只做表面修改）：
{state['review_feedback']}

请根据以上反馈，重新输出修改后的选题提案。修改意见中提到的每一点都必须有实质性改动。
"""
        else:
            user_prompt += "\n请基于以上知识框架，输出一份选题提案。"

        result = self.call_llm(SYSTEM_PROMPT, user_prompt)

        state["topic_proposal"] = result
        state["current_stage"] = Stage.TOPIC
        state["last_agent"] = self.name

        status = dict(state.get("stage_status", {}))
        status[Stage.TOPIC.value] = StageStatus.AWAITING_REVIEW.value
        state["stage_status"] = status
        state["current_review_gate"] = "gate_1"

        self._log("选题提案生成完成，等待审核门1")
        return state
