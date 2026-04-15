"""
Orchestrator（中央编排器）

使用 LangGraph 构建有向图工作流：
- 每个 Agent/工具 是一个节点
- 审核门是中断点（interrupt），等待人工输入
- 条件边根据审核结果决定走向（通过 → 下一步 / 打回 → 重做）

关键设计：
- Agent 之间不直接对话，只通过 State 交换数据
- 审核门暂停执行，等待创作者反馈
- 共享项目文档 = LangGraph State
"""

from typing import Literal
from mini_graph import MiniStateGraph as StateGraph, END, InMemoryCheckpointer as MemorySaver

from state import ProjectState, Stage, StageStatus, ReviewAction
from config import SystemConfig, load_config
from project_manager import ProjectManager


def _save_if_approved(state: ProjectState, stage: Stage, content: str) -> None:
    """审核通过时将产出内容写到项目对应子目录。"""
    if state.get("review_action") == ReviewAction.APPROVE.value and content:
        pm = ProjectManager()
        pm.save_stage_output(state, stage, content)

# Agent imports
from agents.research import ResearchAgent
from agents.topic import TopicAgent
from agents.script import ScriptOutlineAgent, ScriptFullAgent
from agents.storyboard import StoryboardAgent
from agents.video_script import VideoScriptAgent
from agents.visual import VisualProducer

# Tool imports
from tools.audio_processor import AudioProcessor
from tools.composer import VideoComposer


# ============================================================
# 节点函数（包装 Agent 调用）
# ============================================================

def _get_config() -> SystemConfig:
    return load_config()


def node_research(state: ProjectState) -> ProjectState:
    config = _get_config()
    agent = ResearchAgent(config.research_llm)
    return agent.run(state)


def node_topic(state: ProjectState) -> ProjectState:
    config = _get_config()
    agent = TopicAgent(config.topic_llm)
    return agent.run(state)


def node_script_outline(state: ProjectState) -> ProjectState:
    config = _get_config()
    agent = ScriptOutlineAgent(config.script_llm)
    return agent.run(state)


def node_script_full(state: ProjectState) -> ProjectState:
    config = _get_config()
    agent = ScriptFullAgent(config.script_llm, config.script_review_llm)
    return agent.run(state)


def node_storyboard(state: ProjectState) -> ProjectState:
    config = _get_config()
    agent = StoryboardAgent(config.storyboard_llm)
    return agent.run(state)


def node_video_script(state: ProjectState) -> ProjectState:
    config = _get_config()
    agent = VideoScriptAgent(config.storyboard_llm)
    return agent.run(state)


def node_visual(state: ProjectState) -> ProjectState:
    config = _get_config()
    agent = VisualProducer(config.visual_prompt_llm)
    return agent.run(state)


def node_audio(state: ProjectState) -> ProjectState:
    processor = AudioProcessor()
    return processor.process(state)


def node_compose(state: ProjectState) -> ProjectState:
    composer = VideoComposer()
    return composer.compose(state)


# ============================================================
# 审核门节点（轻量级，只做状态标记）
# 显示和交互逻辑在 main.py 中处理
# ============================================================

def gate_1_topic_review(state: ProjectState) -> ProjectState:
    """审核门 1：选题确认。执行时 review_action 已被注入。"""
    state["current_review_gate"] = "gate_1"
    _save_if_approved(state, Stage.RESEARCH, state.get("knowledge_framework", ""))
    _save_if_approved(state, Stage.TOPIC, state.get("topic_proposal", ""))
    return state

def gate_2a_outline_review(state: ProjectState) -> ProjectState:
    """审核门 2a：大纲确认"""
    state["current_review_gate"] = "gate_2a"
    _save_if_approved(state, Stage.SCRIPT_OUTLINE, state.get("script_outline", ""))
    return state

def gate_2b_script_review(state: ProjectState) -> ProjectState:
    """审核门 2b：脚本确认"""
    state["current_review_gate"] = "gate_2b"
    _save_if_approved(state, Stage.SCRIPT_FULL, state.get("script_full", ""))
    return state

def gate_3_storyboard_review(state: ProjectState) -> ProjectState:
    """审核门 3：分镜确认"""
    state["current_review_gate"] = "gate_3"
    _save_if_approved(state, Stage.STORYBOARD, state.get("storyboard", ""))
    return state

def gate_4_final_review(state: ProjectState) -> ProjectState:
    """审核门 4：成片确认"""
    state["current_review_gate"] = "gate_4"
    return state


# ============================================================
# 条件路由函数
# ============================================================

def route_after_gate_1(state: ProjectState) -> str:
    """审核门1后的路由"""
    action = state.get("review_action", "")
    if action == ReviewAction.APPROVE.value:
        return "script_outline"
    elif action == ReviewAction.CHANGE_DIRECTION.value:
        return "research"       # 换方向需要重新研究
    else:  # revise
        return "topic"          # 打回给 Topic Agent


def route_after_gate_2a(state: ProjectState) -> str:
    """审核门2a后的路由"""
    action = state.get("review_action", "")
    if action == ReviewAction.APPROVE.value:
        return "script_full"
    else:
        return "script_outline"  # 打回重做大纲


def route_after_gate_2b(state: ProjectState) -> str:
    """审核门2b后的路由"""
    action = state.get("review_action", "")
    if action == ReviewAction.APPROVE.value:
        return "storyboard"
    elif action == ReviewAction.REWRITE.value:
        return "script_outline"  # 大改，回到大纲
    else:
        return "script_full"     # 局部修改


def route_after_gate_3(state: ProjectState) -> str:
    """审核门3后的路由"""
    action = state.get("review_action", "")
    if action == ReviewAction.APPROVE.value:
        return "production"      # 进入素材生产
    else:
        return "storyboard"


def route_after_gate_4(state: ProjectState) -> str:
    """审核门4后的路由"""
    action = state.get("review_action", "")
    if action == ReviewAction.APPROVE.value:
        return "published"
    else:
        return "compose"


# ============================================================
# 素材生产并行节点（音频 + 视觉）
# ============================================================

def node_production(state: ProjectState) -> ProjectState:
    """
    素材生产阶段入口。
    
    实际运行中，录音由创作者手动上传。
    这个节点检查录音是否就绪，然后触发音频处理和视觉生产。
    
    V1 版本按顺序执行（音频 → 视觉），
    后续可改为并行（LangGraph 的 parallel 分支）。
    """
    print("\n" + "=" * 60)
    print("🎙️ 素材生产阶段")
    print("=" * 60)
    print("请上传录音文件后继续。")
    print("（V1版本：录音路径通过 State 传入）")
    print("=" * 60)

    # 先处理音频
    state = node_audio(state)

    # 再生产视觉素材
    state = node_visual(state)

    return state


# ============================================================
# 终点节点
# ============================================================

def node_published(state: ProjectState) -> ProjectState:
    """发布完成"""
    state["current_stage"] = Stage.PUBLISHED

    status = dict(state.get("stage_status", {}))
    for s in status:
        if status[s] != StageStatus.FAILED.value:
            status[s] = StageStatus.APPROVED.value
    state["stage_status"] = status

    print("\n" + "=" * 60)
    print("✅ 视频制作完成！")
    print("=" * 60)
    print(f"项目：{state.get('project_id', '')}")
    print(f"成片：{state.get('final_video_path', state.get('draft_video_path', ''))}")
    print("=" * 60)
    return state


# ============================================================
# 构建 LangGraph 工作流
# ============================================================

def build_workflow() -> StateGraph:
    """
    构建完整的 LangGraph 工作流图。

    图结构：
    
    research → topic → [gate_1] →(条件)→ script_outline → [gate_2a]
       ↑         ↑                              ↑
       └─(换方向)─┘                              │
                  └──────(打回)──────────────────┘

    →(条件)→ script_full → [gate_2b] →(条件)→ storyboard → video_script → [gate_3]
                 ↑              ↑                    ↑
                 └──(局部修改)───┘                    │
                 └──────(大改，回大纲)────────────────┘
    
    →(条件)→ production(音频+视觉) → compose → [gate_4] →(条件)→ published
                                      ↑                         │
                                      └────(调整)────────────────┘
    """

    workflow = StateGraph(ProjectState)

    # ---- 添加节点 ----
    workflow.add_node("research", node_research)
    workflow.add_node("topic", node_topic)
    workflow.add_node("gate_1", gate_1_topic_review)
    workflow.add_node("script_outline", node_script_outline)
    workflow.add_node("gate_2a", gate_2a_outline_review)
    workflow.add_node("script_full", node_script_full)
    workflow.add_node("gate_2b", gate_2b_script_review)
    workflow.add_node("storyboard", node_storyboard)
    workflow.add_node("video_script", node_video_script)
    workflow.add_node("gate_3", gate_3_storyboard_review)
    workflow.add_node("production", node_production)
    workflow.add_node("compose", node_compose)
    workflow.add_node("gate_4", gate_4_final_review)
    workflow.add_node("published", node_published)

    # ---- 设置入口 ----
    workflow.set_entry_point("research")

    # ---- 固定边（顺序推进） ----
    workflow.add_edge("research", "topic")
    workflow.add_edge("topic", "gate_1")
    workflow.add_edge("script_outline", "gate_2a")
    workflow.add_edge("script_full", "gate_2b")
    workflow.add_edge("storyboard", "video_script")
    workflow.add_edge("video_script", "gate_3")
    workflow.add_edge("production", "compose")
    workflow.add_edge("compose", "gate_4")
    workflow.add_edge("published", END)

    # ---- 条件边（审核门路由） ----
    workflow.add_conditional_edges(
        "gate_1",
        route_after_gate_1,
        {
            "script_outline": "script_outline",
            "topic": "topic",
            "research": "research",
        },
    )

    workflow.add_conditional_edges(
        "gate_2a",
        route_after_gate_2a,
        {
            "script_full": "script_full",
            "script_outline": "script_outline",
        },
    )

    workflow.add_conditional_edges(
        "gate_2b",
        route_after_gate_2b,
        {
            "storyboard": "storyboard",
            "script_full": "script_full",
            "script_outline": "script_outline",
        },
    )

    workflow.add_conditional_edges(
        "gate_3",
        route_after_gate_3,
        {
            "production": "production",
            "storyboard": "storyboard",
        },
    )

    workflow.add_conditional_edges(
        "gate_4",
        route_after_gate_4,
        {
            "published": "published",
            "compose": "compose",
        },
    )

    return workflow


def create_app(checkpointer=None):
    """
    创建可执行的 LangGraph 应用。
    
    checkpointer 用于持久化执行状态，
    使得流程可以在审核门暂停后恢复。
    """
    workflow = build_workflow()

    if checkpointer is None:
        checkpointer = MemorySaver()

    # 在审核门节点前中断，等待人工输入
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=[
            "gate_1",
            "gate_2a",
            "gate_2b",
            "gate_3",
            "gate_4",
        ],
    )

    return app
