"""
项目状态定义 - 整个流水线的共享数据结构

这是 LangGraph 的 State 对象，所有 Agent 和审核门通过它交换数据。
State 中只存轻量级的文本内容和元数据，大文件（音频、图片、视频）
通过 project_manager 存到文件系统，State 中只保留路径引用。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TypedDict, Literal, Optional
from enum import Enum
import json
from datetime import datetime


# ============================================================
# 阶段与状态枚举
# ============================================================

class Stage(str, Enum):
    """流水线阶段"""
    RESEARCH = "research"
    TOPIC = "topic"
    SCRIPT_OUTLINE = "script_outline"
    SCRIPT_FULL = "script_full"
    STORYBOARD = "storyboard"
    AUDIO = "audio"
    VISUAL = "visual"
    COMPOSE = "compose"
    PUBLISHED = "published"


class StageStatus(str, Enum):
    """每个阶段的状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"         # Agent 完成产出
    AWAITING_REVIEW = "awaiting_review"  # 等待人工审核
    APPROVED = "approved"           # 审核通过
    REVISION_REQUESTED = "revision_requested"  # 打回重做
    FAILED = "failed"


class ReviewAction(str, Enum):
    """审核门操作"""
    APPROVE = "approve"
    REVISE = "revise"           # 局部修改
    REWRITE = "rewrite"         # 重写
    CHANGE_DIRECTION = "change_direction"  # 换方向（仅审核门1）


# ============================================================
# 审核记录
# ============================================================

@dataclass
class ReviewRecord:
    """单次审核的记录"""
    gate: str                    # "gate_1", "gate_2a", "gate_2b", "gate_3", "gate_4"
    action: ReviewAction
    feedback: str = ""           # 创作者的修改意见
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "gate": self.gate,
            "action": self.action.value,
            "feedback": self.feedback,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReviewRecord":
        return cls(
            gate=d["gate"],
            action=ReviewAction(d["action"]),
            feedback=d.get("feedback", ""),
            timestamp=d.get("timestamp", ""),
        )


# ============================================================
# 核心 State —— LangGraph 的状态对象
# ============================================================

class ProjectState(TypedDict, total=False):
    """
    LangGraph State 对象。
    
    设计原则：
    - 文本内容直接存在 State 里（知识框架、选题、脚本等）
    - 大文件只存路径引用
    - 审核反馈也存在 State 里，供 Agent 重做时参考
    """

    # ---- 项目元信息 ----
    project_id: str
    topic_direction: str          # 用户输入的主题方向
    raw_materials: list[str]      # 用户提供的原始素材路径/链接
    project_dir: str              # 项目目录路径
    current_stage: Stage
    created_at: str
    updated_at: str

    # ---- 各阶段产出（文本内容直接存） ----
    knowledge_framework: str       # Research Agent 产出
    topic_proposal: str            # Topic Agent 产出
    script_outline: str            # Script Agent 第一步产出
    script_full: str               # Script Agent 第二步产出
    storyboard: str                # Storyboard Agent 产出（JSON 字符串）
    style_seeds: str               # 视觉风格种子（JSON 字符串）
    video_script_json: str         # Remotion VideoScript JSON（由 storyboard agent 生成）

    # ---- 文件路径引用 ----
    keyframe_paths: list[str]      # 关键帧草稿图片路径
    audio_raw_paths: list[str]     # 原始录音路径
    audio_processed_paths: list[str]  # 处理后音频路径
    audio_timestamps: str          # 时间戳 JSON
    visual_paths: list[str]        # 视觉素材路径
    draft_video_path: str          # 初稿视频路径
    final_video_path: str          # 终稿视频路径

    # ---- 审核相关 ----
    review_history: list[dict]     # ReviewRecord.to_dict() 的列表
    current_review_gate: str       # 当前在哪个审核门
    review_action: str             # 当前审核操作
    review_feedback: str           # 当前审核反馈

    # ---- 各阶段状态追踪 ----
    stage_status: dict[str, str]   # {stage_name: status}
    retry_count: dict[str, int]    # {stage_name: retry_count}

    # ---- 错误处理 ----
    error_message: str
    last_agent: str                # 最后执行的 Agent 名称


# ============================================================
# 状态初始化工厂函数
# ============================================================

def create_initial_state(
    project_id: str,
    topic_direction: str,
    raw_materials: list[str] | None = None,
    project_dir: str = "",
) -> ProjectState:
    """创建一个新项目的初始状态"""
    now = datetime.now().isoformat()

    return ProjectState(
        # 元信息
        project_id=project_id,
        topic_direction=topic_direction,
        raw_materials=raw_materials or [],
        project_dir=project_dir,
        current_stage=Stage.RESEARCH,
        created_at=now,
        updated_at=now,

        # 各阶段产出（初始为空）
        knowledge_framework="",
        topic_proposal="",
        script_outline="",
        script_full="",
        storyboard="",
        style_seeds="",
        video_script_json="",

        # 文件路径引用
        keyframe_paths=[],
        audio_raw_paths=[],
        audio_processed_paths=[],
        audio_timestamps="",
        visual_paths=[],
        draft_video_path="",
        final_video_path="",

        # 审核相关
        review_history=[],
        current_review_gate="",
        review_action="",
        review_feedback="",

        # 状态追踪
        stage_status={
            Stage.RESEARCH.value: StageStatus.PENDING.value,
            Stage.TOPIC.value: StageStatus.PENDING.value,
            Stage.SCRIPT_OUTLINE.value: StageStatus.PENDING.value,
            Stage.SCRIPT_FULL.value: StageStatus.PENDING.value,
            Stage.STORYBOARD.value: StageStatus.PENDING.value,
            Stage.AUDIO.value: StageStatus.PENDING.value,
            Stage.VISUAL.value: StageStatus.PENDING.value,
            Stage.COMPOSE.value: StageStatus.PENDING.value,
        },
        retry_count={},

        # 错误处理
        error_message="",
        last_agent="",
    )
