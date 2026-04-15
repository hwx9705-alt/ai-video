"""
项目管理器

负责：
1. 创建和管理项目目录结构
2. 持久化项目状态（State ↔ JSON 文件）
3. 管理各阶段产出文件的存储和版本
"""

from __future__ import annotations

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

from state import ProjectState, Stage, StageStatus, create_initial_state


class ProjectManager:
    """项目文件和状态管理"""

    # 项目子目录结构
    SUBDIRS = [
        "01_research",
        "02_topic",
        "03_script",
        "04_storyboard",
        "04_storyboard/keyframes",
        "05_audio/raw",
        "05_audio/processed",
        "06_visual/charts",
        "06_visual/ai_images",
        "06_visual/diagrams",
        "07_output",
    ]

    def __init__(self, projects_root: str = "./projects"):
        self.projects_root = Path(projects_root)
        self.projects_root.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 项目创建
    # ============================================================

    def create_project(
        self,
        topic_direction: str,
        raw_materials: list[str] | None = None,
        project_id: str = "",
    ) -> ProjectState:
        """
        创建新项目：
        1. 生成项目ID
        2. 创建目录结构
        3. 初始化 State
        4. 持久化状态文件
        """
        if not project_id:
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 用主题方向的前20个字符做目录名
            safe_topic = self._safe_dirname(topic_direction[:20])
            project_id = f"{date_str}_{safe_topic}"

        project_dir = self.projects_root / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        for subdir in self.SUBDIRS:
            (project_dir / subdir).mkdir(parents=True, exist_ok=True)

        # 初始化 State
        state = create_initial_state(
            project_id=project_id,
            topic_direction=topic_direction,
            raw_materials=raw_materials,
            project_dir=str(project_dir),
        )

        # 持久化
        self.save_state(state)

        return state

    # ============================================================
    # 状态持久化
    # ============================================================

    def save_state(self, state: ProjectState) -> None:
        """将 State 保存为 JSON 文件"""
        state["updated_at"] = datetime.now().isoformat()
        state_path = Path(state["project_dir"]) / "project_state.json"
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(dict(state), f, ensure_ascii=False, indent=2)

    def load_state(self, project_id: str) -> ProjectState:
        """从 JSON 文件加载 State"""
        state_path = self.projects_root / project_id / "project_state.json"
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ProjectState(**data)

    def list_projects(self) -> list[dict]:
        """列出所有项目"""
        projects = []
        for d in sorted(self.projects_root.iterdir()):
            state_file = d / "project_state.json"
            if state_file.exists():
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                projects.append({
                    "project_id": data.get("project_id", d.name),
                    "topic": data.get("topic_direction", ""),
                    "stage": data.get("current_stage", ""),
                    "updated_at": data.get("updated_at", ""),
                })
        return projects

    # ============================================================
    # 阶段产出文件管理
    # ============================================================

    def save_stage_output(
        self,
        state: ProjectState,
        stage: Stage,
        content: str,
        filename: str = "",
    ) -> str:
        """
        保存某个阶段的文本产出到对应目录。
        返回保存的文件路径。
        """
        stage_dir_map = {
            Stage.RESEARCH: "01_research",
            Stage.TOPIC: "02_topic",
            Stage.SCRIPT_OUTLINE: "03_script",
            Stage.SCRIPT_FULL: "03_script",
            Stage.STORYBOARD: "04_storyboard",
        }

        default_filename_map = {
            Stage.RESEARCH: "knowledge_framework.md",
            Stage.TOPIC: "proposal.md",
            Stage.SCRIPT_OUTLINE: "outline.md",
            Stage.SCRIPT_FULL: "script.md",
            Stage.STORYBOARD: "storyboard.json",
        }

        subdir = stage_dir_map.get(stage, "")
        if not subdir:
            return ""

        fname = filename or default_filename_map.get(stage, "output.md")

        # 版本管理：如果文件已存在，加版本号
        output_dir = Path(state["project_dir"]) / subdir
        output_path = output_dir / fname
        if output_path.exists():
            version = self._get_next_version(output_dir, fname)
            stem = output_path.stem
            suffix = output_path.suffix
            # 旧文件改名
            archive_name = f"{stem}_v{version - 1}{suffix}"
            output_path.rename(output_dir / archive_name)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(output_path)

    # ============================================================
    # 工具方法
    # ============================================================

    @staticmethod
    def _safe_dirname(name: str) -> str:
        """将字符串转为安全的目录名"""
        # 保留中文字符、字母、数字、下划线
        safe = "".join(c if c.isalnum() or c == "_" or '\u4e00' <= c <= '\u9fff' else "_" for c in name)
        return safe.strip("_") or "untitled"

    @staticmethod
    def _get_next_version(directory: Path, filename: str) -> int:
        """获取下一个版本号"""
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        existing = list(directory.glob(f"{stem}_v*{suffix}"))
        if not existing:
            return 2
        versions = []
        for f in existing:
            try:
                v = int(f.stem.split("_v")[-1])
                versions.append(v)
            except ValueError:
                pass
        return max(versions, default=1) + 1
