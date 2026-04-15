"""
AI 科普视频自动化生产系统 - Web UI

用法：
  streamlit run app.py
  （或直接双击 start_ui.bat）
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import queue
import time
import json
from datetime import datetime
from pathlib import Path

# 设置环境变量（代理和编码）
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["NO_PROXY"] = "*"

import streamlit as st

# 加入项目路径
sys.path.insert(0, str(Path(__file__).parent))


# ============================================================
# 流水线线程通信
# ============================================================

# 进程级全局 bridge：只要 Streamlit 进程还活着，即使浏览器断线重连也能恢复
_GLOBAL_BRIDGE: "PipelineBridge | None" = None

# Remotion 渲染状态（进程级，线程安全简单字典）
# status: "idle" | "rendering" | "done" | "error"
_REMOTION: dict = {"status": "idle", "output_path": "", "error": ""}


class PipelineBridge:
    """
    在 Streamlit 主线程和流水线子线程之间传递消息。

    流水线线程在审核门暂停，等待 UI 的指令。
    UI 收到暂停信号后展示内容，收到用户操作后把决定发回流水线。
    """

    def __init__(self):
        # 流水线 → UI：日志和审核门请求
        self.log_queue: queue.Queue = queue.Queue()
        # UI → 流水线：审核决定
        self.review_event = threading.Event()
        self.review_result: dict = {}
        # 流水线当前状态
        self.status: str = "idle"   # idle / running / gate / done / error
        self.gate_name: str = ""
        self.state_snapshot: dict = {}
        self.error: str = ""

    def post_log(self, msg: str):
        self.log_queue.put(("log", msg))

    def request_review(self, gate_name: str, state: dict):
        """流水线线程在审核门调用，阻塞等待 UI 决定"""
        self.gate_name = gate_name
        self.state_snapshot = dict(state)
        self.status = "gate"
        self.log_queue.put(("gate", gate_name))
        # 阻塞，等待 UI 调用 submit_review
        self.review_event.clear()
        self.review_event.wait()
        return self.review_result

    def submit_review(self, action: str, feedback: str, edited_script: str = "", audio_path: str = ""):
        """UI 线程调用，把审核结果发回流水线"""
        self.review_result = {"action": action, "feedback": feedback, "edited_script": edited_script, "audio_path": audio_path}
        self.status = "running"
        self.review_event.set()


# ============================================================
# 流水线执行（在子线程中运行）
# ============================================================

def _run_remotion_render(video_script_json: str, project_dir: str, audio_path: str = ""):
    """
    在后台线程中执行 Remotion 渲染，结果写入 _REMOTION 全局字典。
    fragment run_every=3 会自动轮询状态。
    """
    import tempfile
    global _REMOTION
    try:
        script = json.loads(video_script_json)
        if audio_path and Path(audio_path).exists():
            script["audioPath"] = audio_path

        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", encoding="utf-8", delete=False
        ) as f:
            json.dump(script, f, ensure_ascii=False)
            tmp_path = f.name

        output_path = str(Path(project_dir) / "remotion_output.mp4")
        env = {**os.environ, "BROWSER_EXECUTABLE_PATH": "/usr/bin/chromium-browser"}

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "remotion-video" / "render.py"),
                "--script", tmp_path,
                "--output", output_path,
                "--concurrency", "2",
            ],
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )

        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        if result.returncode == 0:
            _REMOTION["status"] = "done"
            _REMOTION["output_path"] = output_path
            _REMOTION["error"] = ""
        else:
            _REMOTION["status"] = "error"
            _REMOTION["error"] = (result.stderr or result.stdout)[-800:]
    except Exception as e:
        _REMOTION["status"] = "error"
        _REMOTION["error"] = str(e)


def _list_resumable_projects(projects_root: str) -> list:
    """列出有 checkpoint 且停在审核门的项目（可继续的）"""
    import json as _json
    checkpoints_dir = Path(projects_root) / "_checkpoints"
    resumable = []
    if not checkpoints_dir.exists():
        return resumable
    for ck_file in sorted(checkpoints_dir.glob("*.json"), reverse=True):
        try:
            ck = _json.loads(ck_file.read_text(encoding="utf-8"))
            next_node = ck.get("next_node", "")
            if not next_node or not next_node.startswith("gate_"):
                continue
            # 找对应的 project_state.json
            project_id = ck_file.stem  # 文件名即 project_id（已做安全转换）
            # 遍历 projects 目录匹配
            for proj_dir in Path(projects_root).iterdir():
                if not proj_dir.is_dir() or proj_dir.name.startswith("_"):
                    continue
                state_file = proj_dir / "project_state.json"
                if not state_file.exists():
                    continue
                state_data = _json.loads(state_file.read_text(encoding="utf-8"))
                # 用 project_id 匹配（checkpoint 文件名是 project_id 安全化后的）
                safe_pid = "".join(c if c.isalnum() or c in "-_" else "_" for c in state_data.get("project_id", ""))
                if safe_pid == ck_file.stem:
                    gate_labels = {
                        "gate_1": "审核门1-选题",
                        "gate_2a": "审核门2a-大纲",
                        "gate_2b": "审核门2b-脚本",
                        "gate_3": "审核门3-分镜",
                        "gate_4": "审核门4-成片",
                    }
                    # 优先用 checkpoint 里的 state（含完整内容），fallback 到 project_state.json
                    ck_state = ck.get("state", state_data)
                    resumable.append({
                        "project_id": state_data.get("project_id", ""),
                        "topic": state_data.get("topic_direction", ""),
                        "gate": next_node,
                        "gate_label": gate_labels.get(next_node, next_node),
                        "updated_at": state_data.get("updated_at", ""),
                        "project_dir": str(proj_dir),
                        "state": ck_state,
                        "checkpoint": ck,
                    })
                    break
        except Exception:
            continue
    return resumable


def resume_pipeline_thread(project_info: dict, bridge: PipelineBridge):
    """从检查点恢复流水线，直接进入对应审核门等待"""
    try:
        bridge.status = "running"
        project_id = project_info["project_id"]
        gate = project_info["gate"]
        state = project_info["state"]
        bridge.post_log(f"🔄 恢复项目：{project_info['topic']}")
        bridge.post_log(f"📍 从 {project_info['gate_label']} 继续")

        from config import load_config
        from project_manager import ProjectManager
        from orchestrator import create_app
        from mini_graph import FileCheckpointer

        config = load_config()
        pm = ProjectManager(config.projects_root)
        checkpoints_dir = str(Path(config.projects_root) / "_checkpoints")
        checkpointer = FileCheckpointer(checkpoints_dir)
        app = create_app(checkpointer=checkpointer)
        thread_config = {"configurable": {"thread_id": project_id}}

        gate_labels = {
            "gate_1": "审核门 1 — 选题确认",
            "gate_2a": "审核门 2a — 脚本大纲确认",
            "gate_2b": "审核门 2b — 完整脚本确认",
            "gate_3": "审核门 3 — 分镜方案确认",
            "gate_4": "审核门 4 — 成片确认",
        }

        # 直接进入审核门等待（checkpoint 已在磁盘，get_state 能读到）
        bridge.post_log(f"🔒 {gate_labels.get(gate, gate)} — 等待审核")
        result = bridge.request_review(gate, state)
        action = result["action"]
        feedback = result["feedback"]
        bridge.post_log(f"  → 操作：{action}")

        history = list(state.get("review_history", []))
        history.append({
            "gate": gate,
            "action": action,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat(),
        })
        update = {
            "review_action": action,
            "review_feedback": feedback,
            "review_history": history,
        }
        if gate == "gate_2b" and action == "approve":
            edited_script = result.get("edited_script", "")
            if edited_script and edited_script != state.get("script_full", ""):
                update["script_full"] = edited_script
        if gate == "gate_3" and action == "approve":
            audio_path = result.get("audio_path", "")
            if audio_path:
                update["audio_raw_paths"] = [audio_path]

        app.update_state(thread_config, update)
        state.update(update)

        # 继续后续流水线
        input_state = None
        while True:
            for event in app.stream(input_state, thread_config):
                for node_name, node_state in event.items():
                    bridge.post_log(f"✓ [{node_name}] 完成")
                    if isinstance(node_state, dict):
                        state.update(node_state)
            input_state = None

            snapshot = app.get_state(thread_config)
            if not snapshot.next:
                bridge.post_log("🎉 流水线执行完毕！")
                bridge.status = "done"
                bridge.state_snapshot = dict(state)
                pm.save_state(state)
                break

            next_node = snapshot.next[0]
            if next_node not in gate_labels:
                continue

            bridge.post_log(f"🔒 {gate_labels[next_node]} — 等待审核")
            result = bridge.request_review(next_node, state)
            action = result["action"]
            feedback = result["feedback"]
            bridge.post_log(f"  → 操作：{action}")

            history = list(state.get("review_history", []))
            history.append({"gate": next_node, "action": action, "feedback": feedback, "timestamp": datetime.now().isoformat()})
            update = {"review_action": action, "review_feedback": feedback, "review_history": history}
            if next_node == "gate_2b" and action == "approve":
                edited_script = result.get("edited_script", "")
                if edited_script and edited_script != state.get("script_full", ""):
                    update["script_full"] = edited_script
            if next_node == "gate_3" and action == "approve":
                audio_path = result.get("audio_path", "")
                if audio_path:
                    update["audio_raw_paths"] = [audio_path]
            app.update_state(thread_config, update)
            state.update(update)
            bridge.status = "running"

        pm.save_state(state)

    except Exception as e:
        import traceback
        bridge.error = f"{e}\n{traceback.format_exc()}"
        bridge.status = "error"
        bridge.post_log(f"❌ 恢复失败：{e}")


def run_pipeline_thread(topic: str, bridge: PipelineBridge):
    """在子线程中执行流水线，通过 bridge 与 UI 通信"""
    try:
        bridge.status = "running"
        bridge.post_log(f"✨ 项目启动：{topic}")

        from config import load_config
        from project_manager import ProjectManager
        from orchestrator import create_app
        from mini_graph import FileCheckpointer
        from state import create_initial_state

        config = load_config()
        pm = ProjectManager(config.projects_root)
        checkpoints_dir = str(Path(config.projects_root) / "_checkpoints")
        checkpointer = FileCheckpointer(checkpoints_dir)
        app = create_app(checkpointer=checkpointer)

        state = pm.create_project(topic_direction=topic)
        bridge.post_log(f"📁 项目目录：{state['project_dir']}")

        thread_config = {"configurable": {"thread_id": state["project_id"]}}
        input_state = state

        # 各审核门的中文名
        gate_labels = {
            "gate_1": "审核门 1 — 选题确认",
            "gate_2a": "审核门 2a — 脚本大纲确认",
            "gate_2b": "审核门 2b — 完整脚本确认",
            "gate_3": "审核门 3 — 分镜方案确认",
            "gate_4": "审核门 4 — 成片确认",
        }

        while True:
            for event in app.stream(input_state, thread_config):
                for node_name, node_state in event.items():
                    bridge.post_log(f"✓ [{node_name}] 完成")
                    if isinstance(node_state, dict):
                        state.update(node_state)

            input_state = None

            snapshot = app.get_state(thread_config)
            if not snapshot.next:
                bridge.post_log("🎉 流水线执行完毕！")
                bridge.status = "done"
                bridge.state_snapshot = dict(state)
                pm.save_state(state)
                break

            next_node = snapshot.next[0]
            gate_name = next_node  # gate 节点名和 gate_name 一致

            if gate_name not in gate_labels:
                continue

            bridge.post_log(f"🔒 {gate_labels[gate_name]} — 等待审核")

            # 请求审核，阻塞等待 UI
            result = bridge.request_review(gate_name, state)
            action = result["action"]
            feedback = result["feedback"]

            bridge.post_log(f"  → 操作：{action}" + (f"（{feedback[:30]}...）" if len(feedback) > 30 else f"（{feedback}）" if feedback else ""))

            # 注入审核结果到 state
            history = list(state.get("review_history", []))
            history.append({
                "gate": gate_name,
                "action": action,
                "feedback": feedback,
                "timestamp": datetime.now().isoformat(),
            })
            update = {
                "review_action": action,
                "review_feedback": feedback,
                "review_history": history,
            }

            # gate_2b 通过时，若创作者直接编辑了脚本，保存编辑版本
            if gate_name == "gate_2b" and action == "approve":
                edited_script = result.get("edited_script", "")
                if edited_script and edited_script != state.get("script_full", ""):
                    update["script_full"] = edited_script
                    bridge.post_log("  ✏️ 已保存你编辑的脚本版本")

            # gate_3 通过时，把已上传的录音路径写入 state
            if gate_name == "gate_3" and action == "approve":
                audio_path = result.get("audio_path", "")
                if audio_path:
                    update["audio_raw_paths"] = [audio_path]
                    bridge.post_log(f"  🎙️ 录音已就绪：{Path(audio_path).name}")

            app.update_state(thread_config, update)
            state.update(update)
            bridge.status = "running"

        pm.save_state(state)

    except Exception as e:
        import traceback
        bridge.error = f"{e}\n{traceback.format_exc()}"
        bridge.status = "error"
        bridge.post_log(f"❌ 出错：{e}")


# ============================================================
# UI 组件
# ============================================================

def _parse_storyboard_segments(storyboard_raw: str) -> list:
    """从 storyboard 原始文本提取分镜段列表"""
    import re
    if not storyboard_raw:
        return []
    blocks = re.findall(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', storyboard_raw)
    for block in blocks:
        try:
            parsed = json.loads(block.strip())
            if isinstance(parsed, dict) and "storyboard" in parsed:
                return parsed["storyboard"]
            if isinstance(parsed, list) and parsed and "segment_id" in parsed[0]:
                return parsed
        except Exception:
            continue
    return []


GATE_ACTIONS = {
    "gate_1":  [("approve", "✅ 通过"), ("revise", "✏️ 局部修改"), ("change_direction", "🔄 换方向")],
    "gate_2a": [("approve", "✅ 通过"), ("revise", "✏️ 局部修改"), ("rewrite", "🔁 重写大纲")],
    "gate_2b": [("approve", "✅ 通过"), ("revise", "✏️ 局部修改"), ("rewrite", "🔁 重写脚本")],
    "gate_3":  [("approve", "✅ 通过"), ("revise", "✏️ 局部修改")],
    "gate_4":  [("approve", "✅ 通过"), ("revise", "✏️ 局部修改")],
}

GATE_TITLES = {
    "gate_1":  "🔒 审核门 1：选题主旨确认",
    "gate_2a": "🔒 审核门 2a：脚本大纲确认",
    "gate_2b": "🔒 审核门 2b：完整脚本 + 口播预演",
    "gate_3":  "🔒 审核门 3：分镜方案确认",
    "gate_4":  "🔒 审核门 4：成片确认",
}


def render_gate_content(gate_name: str, state: dict):
    """展示审核门的核心内容"""
    if gate_name == "gate_1":
        proposal = state.get("topic_proposal", "")
        st.markdown("#### 📋 选题提案")
        st.markdown(proposal)
        st.info("**审核要点**：角度是否锐利？时效性钩子是否具体？B站用户匹配度？")

    elif gate_name == "gate_2a":
        outline = state.get("script_outline", "")
        st.markdown("#### 📋 脚本大纲")
        st.markdown(outline)
        st.info("**审核要点**：叙事结构是否合适？段落节奏是否有起伏？开头30秒够不够抓人？")

    elif gate_name == "gate_2b":
        script = state.get("script_full", "")
        st.warning("🎤 **口播预演**：请把脚本大声念一遍，边念边直接在下方文本框里修改不顺畅的地方。")
        st.markdown("#### 📋 完整脚本（可直接编辑）")
        edited = st.text_area(
            label="脚本内容",
            value=script,
            height=600,
            key="script_edit_box",
            label_visibility="collapsed",
        )
        # 把编辑后的内容存回 session_state，供审核按钮读取
        st.session_state["_edited_script"] = edited
        if edited != script:
            st.caption("✏️ 你已修改过脚本内容，点「通过」将保存你的修改版本。")

    elif gate_name == "gate_3":
        storyboard_raw = state.get("storyboard", "")
        style_seeds_raw = state.get("style_seeds", "")

        # 视觉风格区
        if style_seeds_raw:
            try:
                seeds = json.loads(style_seeds_raw)
                with st.expander("🎨 视觉风格设定", expanded=True):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**情绪基调**：{seeds.get('visual_mood', '')}")
                        st.markdown(f"**字体风格**：{seeds.get('font_style', '')}")
                        palette = seeds.get("color_palette", {})
                        if palette:
                            color_html = "".join(
                                f'<span title="{k}: {v}" style="display:inline-block;background:{v};'
                                f'width:36px;height:36px;border-radius:4px;margin:3px;'
                                f'border:1px solid #333"></span>'
                                for k, v in palette.items()
                            )
                            st.markdown(f"**配色方案**：{color_html}", unsafe_allow_html=True)
                    with col2:
                        st.markdown("**AI生图风格词**")
                        st.caption(seeds.get("ai_image_style_keywords", ""))
            except Exception:
                pass

        # 分镜卡片
        st.markdown("#### 🎬 分镜表")
        segments = _parse_storyboard_segments(storyboard_raw)
        if segments:
            VISUAL_TYPE_ICONS = {
                "data_chart": "📊",
                "flow_diagram": "🔀",
                "comparison": "⚖️",
                "ai_image": "🖼",
                "text_animation": "✍️",
                "mixed": "🎭",
            }
            for seg in segments:
                icon = VISUAL_TYPE_ICONS.get(seg.get("visual_type", ""), "🎬")
                duration = seg.get("estimated_duration_sec", 0)
                vtype = seg.get("visual_type", "")
                title = seg.get("segment_title", f"段落 {seg.get('segment_id', '')}")
                with st.expander(
                    f"{icon} [{seg.get('segment_id', '')}] {title}  ·  {vtype}  ·  约{duration}秒",
                    expanded=False
                ):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"**画面描述**：{seg.get('visual_description', '')}")
                        elements = seg.get("key_elements", [])
                        if elements:
                            st.markdown("**必须出现**：" + " · ".join(elements))
                    with col_b:
                        if seg.get("text_overlay"):
                            st.markdown(f"**叠加文字**：{seg.get('text_overlay')}")
                        if seg.get("transition"):
                            st.markdown(f"**转场**：{seg.get('transition')}")
                        if seg.get("notes"):
                            st.caption(f"备注：{seg.get('notes')}")
                    script_text = seg.get("script_text", "")
                    if script_text:
                        st.markdown(f"> {script_text[:150]}{'...' if len(script_text) > 150 else ''}")
        else:
            st.markdown(storyboard_raw)

        st.info("**审核要点**：画面切换节奏？视觉类型分配是否合理？开头画面有冲击力吗？")

        # 配音设置（上传录音 或 AI 语音合成）
        st.divider()
        st.markdown("#### 🎤 配音设置")

        audio_mode = st.radio(
            "配音方式",
            ["上传录音", "AI 语音合成"],
            key="audio_mode_select",
            horizontal=True,
        )
        st.session_state["_audio_mode"] = "upload" if audio_mode == "上传录音" else "tts"

        if audio_mode == "上传录音":
            st.caption("通过分镜审核后，系统将用你的录音合成视频。支持 mp3 / wav / m4a。")
            uploaded = st.file_uploader(
                "选择录音文件",
                type=["mp3", "wav", "m4a", "aac"],
                key="audio_uploader",
            )
            if uploaded:
                project_dir = Path(state.get("project_dir", "."))
                raw_dir = project_dir / "05_audio" / "raw"
                raw_dir.mkdir(parents=True, exist_ok=True)
                save_path = raw_dir / uploaded.name
                save_path.write_bytes(uploaded.getvalue())
                st.session_state["_uploaded_audio_path"] = str(save_path)
                st.success(f"录音已上传：{uploaded.name}（{len(uploaded.getvalue())//1024} KB）")
            elif st.session_state.get("_uploaded_audio_path"):
                p = Path(st.session_state["_uploaded_audio_path"])
                if p.exists():
                    st.success(f"已上传：{p.name}")

        else:
            # AI 语音合成
            from tools.tts_generator import AVAILABLE_VOICES, synthesize_speech

            st.caption("使用 AI 语音自动合成配音，可选音色和语速。")

            col_voice, col_speed = st.columns([3, 1])
            with col_voice:
                voice_display = st.selectbox(
                    "音色",
                    list(AVAILABLE_VOICES.keys()),
                    key="tts_voice_select",
                )
            with col_speed:
                tts_speed = st.slider("语速", 0.5, 2.0, 1.0, 0.1, key="tts_speed")

            # 默认用清洗后的纯口播文本，用户可编辑
            from tools.tts_generator import extract_narration
            default_text = extract_narration(state.get("script_full", "")).strip()
            tts_text = st.text_area(
                "合成文本（已自动过滤画面提示/语气指令，可继续编辑）",
                value=default_text,
                height=200,
                key="tts_text_input",
            )

            if st.button("🎙️ 生成语音", key="btn_tts_generate"):
                from config import load_config
                cfg = load_config()
                api_key = cfg.tts_api_key
                if not api_key:
                    st.error("未配置 SiliconFlow API Key（IMAGE_GEN_API_KEY），无法合成语音。")
                elif not tts_text.strip():
                    st.error("合成文本不能为空。")
                else:
                    project_dir = Path(state.get("project_dir", "."))
                    raw_dir = project_dir / "05_audio" / "raw"
                    raw_dir.mkdir(parents=True, exist_ok=True)
                    output_path = str(raw_dir / "tts_output.mp3")
                    tts_model, tts_voice = AVAILABLE_VOICES[voice_display]
                    with st.spinner("AI 语音合成中，请稍候..."):
                        try:
                            synthesize_speech(
                                text=tts_text.strip(),
                                output_path=output_path,
                                api_key=api_key,
                                voice=tts_voice,
                                model=tts_model,
                                base_url=cfg.tts_base_url,
                                speed=tts_speed,
                            )
                            st.session_state["_tts_audio_path"] = output_path
                            st.rerun()
                        except Exception as e:
                            st.error(f"语音合成失败：{e}")

            # 已生成的语音预览
            tts_path = st.session_state.get("_tts_audio_path", "")
            if tts_path and Path(tts_path).exists():
                size_kb = Path(tts_path).stat().st_size // 1024
                st.success(f"语音已生成（{size_kb} KB），通过分镜审核后将用此配音合成视频。")
                st.audio(tts_path)

        # Remotion 动态预览（实验性）
        video_script_json = state.get("video_script_json", "")
        if video_script_json:
            st.divider()
            st.markdown("#### 🎬 Remotion 动态视频预览（实验性）")
            st.caption("基于分镜方案实时渲染动态视频（约2-5分钟），可与静态方案对比效果。")

            render_status = _REMOTION.get("status", "idle")

            col_btn, col_info = st.columns([1, 2])
            with col_btn:
                btn_disabled = render_status == "rendering"
                if st.button(
                    "🚀 触发 Remotion 渲染",
                    key="btn_remotion_render",
                    disabled=btn_disabled,
                ):
                    _REMOTION["status"] = "rendering"
                    _REMOTION["output_path"] = ""
                    _REMOTION["error"] = ""
                    # 获取当前配音路径
                    _audio = ""
                    _mode = st.session_state.get("_audio_mode", "upload")
                    if _mode == "tts":
                        _audio = st.session_state.get("_tts_audio_path", "")
                    else:
                        _audio = st.session_state.get("_uploaded_audio_path", "")
                    t = threading.Thread(
                        target=_run_remotion_render,
                        args=(video_script_json, state.get("project_dir", "/tmp"), _audio),
                        daemon=True,
                    )
                    t.start()

            with col_info:
                if render_status == "rendering":
                    st.info("渲染中，请稍候（约2-5分钟）...")
                elif render_status == "done":
                    st.success("Remotion 渲染完成！")
                elif render_status == "error":
                    st.error(f"渲染失败：{_REMOTION.get('error', '')[:300]}")

            # 渲染完成后展示视频和下载按钮
            output_path = _REMOTION.get("output_path", "")
            if render_status == "done" and output_path and Path(output_path).exists():
                st.video(output_path)
                st.download_button(
                    "⬇️ 下载 Remotion 动态视频",
                    data=open(output_path, "rb").read(),
                    file_name=Path(output_path).name,
                    mime="video/mp4",
                    key="dl_remotion",
                )

    elif gate_name == "gate_4":
        video_path = state.get("draft_video_path", "")
        if video_path and Path(video_path).exists():
            st.video(video_path)
            st.download_button(
                "⬇️ 下载视频",
                data=open(video_path, "rb").read(),
                file_name=Path(video_path).name,
                mime="video/mp4",
            )
        else:
            st.warning("成片文件未生成，请检查后端日志")


def render_review_controls(gate_name: str, bridge: PipelineBridge):
    """渲染审核操作按钮和反馈输入"""
    actions = GATE_ACTIONS.get(gate_name, [("approve", "✅ 通过")])

    st.divider()
    feedback = st.text_area(
        "修改意见（通过时可留空）",
        key=f"feedback_{gate_name}",
        height=100,
        placeholder="说明你希望怎么改，Agent 会据此重做..."
    )

    cols = st.columns(len(actions))
    for i, (action_key, action_label) in enumerate(actions):
        if cols[i].button(action_label, key=f"btn_{gate_name}_{action_key}", use_container_width=True):
            edited_script = st.session_state.pop("_edited_script", "") if gate_name == "gate_2b" else ""
            audio_path = ""
            if gate_name == "gate_3":
                mode = st.session_state.get("_audio_mode", "upload")
                if mode == "tts":
                    audio_path = st.session_state.get("_tts_audio_path", "")
                else:
                    audio_path = st.session_state.get("_uploaded_audio_path", "")
            bridge.submit_review(action_key, feedback, edited_script=edited_script, audio_path=audio_path)
            st.session_state["_submitted_gate"] = gate_name
            st.session_state["_need_rerun"] = True


# 各审核门"之前"已完成的阶段内容映射
_GATE_HISTORY = {
    "gate_1":  [],
    "gate_2a": [("知识框架", "knowledge_framework"), ("选题提案", "topic_proposal")],
    "gate_2b": [("知识框架", "knowledge_framework"), ("选题提案", "topic_proposal"), ("脚本大纲", "script_outline")],
    "gate_3":  [("知识框架", "knowledge_framework"), ("选题提案", "topic_proposal"), ("脚本大纲", "script_outline"), ("完整脚本", "script_full")],
    "gate_4":  [("知识框架", "knowledge_framework"), ("选题提案", "topic_proposal"), ("脚本大纲", "script_outline"), ("完整脚本", "script_full")],
}


def render_history(gate_name: str, state: dict):
    """在当前审核门下方展示之前各阶段的产出，供回溯查看"""
    history_items = _GATE_HISTORY.get(gate_name, [])
    if not history_items:
        return

    st.divider()
    st.markdown("#### 📚 历史记录（可展开回看）")
    for label, key in history_items:
        content = state.get(key, "")
        if not content:
            continue
        with st.expander(f"📄 {label}", expanded=False):
            if key == "script_full":
                st.markdown(content[:3000] + ("..." if len(content) > 3000 else ""))
            else:
                st.markdown(content)


# ============================================================
# 右栏 Fragment（独立渲染，不触发整页 rerun，彻底消除 removeChild）
# ============================================================

@st.fragment(run_every=3)
def _render_log_panel():
    """左栏日志面板，独立 fragment，每3秒自动拉取新日志"""
    bridge: PipelineBridge | None = st.session_state.get("bridge")
    if bridge:
        while not bridge.log_queue.empty():
            try:
                _, msg = bridge.log_queue.get_nowait()
                st.session_state.setdefault("logs", []).append(msg)
            except Exception:
                break
    st.markdown("### 📟 执行日志")
    log_container = st.container(height=400)
    with log_container:
        for log in reversed(st.session_state.get("logs", [])):
            st.text(log)


@st.fragment(run_every=3)
def _render_right_panel():
    """
    右栏以 fragment 方式渲染。
    - run_every=3：每3秒自动刷新一次，只重绘右栏
    - fragment 内部调用 st.rerun() 也只重绘右栏
    - 不会触发整页 rerun，因此左栏 DOM 完全稳定，removeChild 不可能发生
    """
    bridge: PipelineBridge | None = st.session_state.get("bridge")

    # 从 bridge 同步最新状态到 session_state（fragment 内读取）
    if bridge:
        actual_status = bridge.status
        actual_gate = bridge.gate_name if actual_status == "gate" else ""

        # 更新显示模式
        cur_mode = st.session_state.get("_display_mode", "idle")
        cur_gate = st.session_state.get("_display_gate", "")
        submitted_gate = st.session_state.get("_submitted_gate", "")
        in_transition = submitted_gate and actual_status == "running"

        if not in_transition:
            new_mode = actual_status if actual_status in ("running", "gate", "done", "error") else "idle"
            if new_mode != cur_mode or actual_gate != cur_gate:
                st.session_state["_display_mode"] = new_mode
                st.session_state["_display_gate"] = actual_gate
                if submitted_gate:
                    st.session_state["_submitted_gate"] = None

    display_mode = st.session_state.get("_display_mode", "idle")
    display_gate = st.session_state.get("_display_gate", "")

    if display_mode == "idle":
        st.markdown("### 👋 使用说明")
        st.markdown("""
1. **输入主题方向** — 在左侧输入你想做的视频主题
2. **启动流水线** — 点击「开始生产」，系统自动运行 Research → Topic → Script → Storyboard
3. **审核每个阶段** — 每到关键节点，系统会在这里展示完整内容，等你确认或给出修改意见
4. **查看脚本口播** — 审核 2b 时建议把脚本大声念一遍
5. **循环迭代** — 不满意可以打回重做，系统会把你的反馈注入给对应 Agent
""")

    elif display_mode == "running":
        st.markdown("### ⚙️ 生产中...")
        st.info("Agent 正在工作，每3秒自动刷新，完成后自动跳转到审核内容。")

    elif display_mode == "gate":
        st.markdown(f"### {GATE_TITLES.get(display_gate, display_gate)}")
        if bridge:
            render_gate_content(display_gate, bridge.state_snapshot)
            render_review_controls(display_gate, bridge)
            render_history(display_gate, bridge.state_snapshot)

    elif display_mode == "done":
        if bridge:
            state = bridge.state_snapshot
            st.markdown("### ✅ 项目完成！")
            st.success(f"项目 `{state.get('project_id', '')}` 已完成所有阶段。")
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 脚本", "🎬 分镜表", "🖼 视觉素材", "📋 选题提案", "🔬 知识框架"])
            with tab1:
                st.markdown(state.get("script_full", "（空）"))
            with tab2:
                segments = _parse_storyboard_segments(state.get("storyboard", ""))
                if segments:
                    VISUAL_TYPE_ICONS = {"data_chart":"📊","flow_diagram":"🔀","comparison":"⚖️","ai_image":"🖼","text_animation":"✍️","mixed":"🎭"}
                    for seg in segments:
                        icon = VISUAL_TYPE_ICONS.get(seg.get("visual_type",""), "🎬")
                        with st.expander(f"{icon} [{seg.get('segment_id','')}] {seg.get('segment_title','')}  ·  {seg.get('visual_type','')}  ·  约{seg.get('estimated_duration_sec',0)}秒", expanded=False):
                            st.markdown(f"**画面描述**：{seg.get('visual_description','')}")
                            if seg.get("key_elements"):
                                st.markdown("**必须出现**：" + " · ".join(seg["key_elements"]))
                            if seg.get("text_overlay"):
                                st.markdown(f"**叠加文字**：{seg['text_overlay']}")
                else:
                    st.markdown(state.get("storyboard", "（空）"))
            with tab3:
                visual_paths = state.get("visual_paths", [])
                segments = _parse_storyboard_segments(state.get("storyboard", ""))
                seg_map = {str(s.get("segment_id","")): s for s in segments}
                if visual_paths:
                    cols_per_row = 2
                    rows = [visual_paths[i:i+cols_per_row] for i in range(0, len(visual_paths), cols_per_row)]
                    for row_paths in rows:
                        cols = st.columns(cols_per_row)
                        for ci, vpath in enumerate(row_paths):
                            p = Path(vpath)
                            if p.exists():
                                seg_id = p.stem.replace("visual_", "").lstrip("0") or "0"
                                seg_info = seg_map.get(seg_id, {})
                                caption = f"[{seg_id}] {seg_info.get('segment_title', p.name)}  ·  {seg_info.get('visual_type','')}"
                                cols[ci].image(str(p), caption=caption, use_container_width=True)
                            else:
                                cols[ci].warning(f"文件不存在：{p.name}")
                else:
                    st.info("本次流水线未生成视觉素材（需经过完整的 Production 阶段）")
            with tab4:
                st.markdown(state.get("topic_proposal", "（空）"))
            with tab5:
                st.markdown(state.get("knowledge_framework", "（空）"))

    elif display_mode == "error":
        st.markdown("### ❌ 出错了")
        if bridge:
            st.error(bridge.error)


# ============================================================
# 主页面
# ============================================================

_LOGIN_PASSWORD = "huweixuan"
_LOGIN_TOKEN_KEY = "tok"


def check_auth() -> bool:
    """
    简单 token 登录。
    - 首次：输入密码 → URL 追加 ?tok=<token>，书签保存后永久免密
    - 再次访问带 token 的 URL：自动通过
    """
    token = st.query_params.get(_LOGIN_TOKEN_KEY, "")
    if token == _LOGIN_PASSWORD:
        return True

    st.markdown("## 🔐 视频生产系统")
    pwd = st.text_input("请输入访问密码", type="password", key="_login_pwd")
    if st.button("登录", type="primary"):
        if pwd == _LOGIN_PASSWORD:
            st.query_params[_LOGIN_TOKEN_KEY] = _LOGIN_PASSWORD
            st.rerun()
        else:
            st.error("密码错误")
    st.caption("登录成功后请保存带参数的网址，下次直接访问无需再输密码。")
    return False


def main():
    global _GLOBAL_BRIDGE
    st.set_page_config(
        page_title="AI 科普视频生产系统",
        page_icon="🎬",
        layout="wide",
    )

    # 登录检查
    if not check_auth():
        st.stop()

    # 移动端适配：让右栏（审核内容）在手机上显示在上方
    st.markdown("""
<style>
@media (max-width: 768px) {
    /* 主布局两栏在手机上反序：右栏（审核内容）优先显示 */
    [data-testid="stHorizontalBlock"] {
        flex-direction: column-reverse;
    }
    /* 审核按钮行保持正常顺序（嵌套在右栏内部，重新覆盖） */
    [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] {
        flex-direction: row;
    }
}
</style>
""", unsafe_allow_html=True)

    # 初始化 session state
    if "bridge" not in st.session_state:
        st.session_state.bridge = None
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "thread" not in st.session_state:
        st.session_state.thread = None
    if "_submitted_gate" not in st.session_state:
        st.session_state["_submitted_gate"] = None
    if "_display_mode" not in st.session_state:
        st.session_state["_display_mode"] = "idle"
    if "_display_gate" not in st.session_state:
        st.session_state["_display_gate"] = ""

    # ---- 断线重连：session 丢失时自动恢复 ----
    if st.session_state.bridge is None:
        # 优先接管进程级全局 bridge（同进程内断线重连）
        if _GLOBAL_BRIDGE is not None and _GLOBAL_BRIDGE.status not in ("idle", "done", "error"):
            g = _GLOBAL_BRIDGE
            st.session_state.bridge = g
            recovered_logs = []
            while not g.log_queue.empty():
                try:
                    _, msg = g.log_queue.get_nowait()
                    recovered_logs.append(msg)
                except queue.Empty:
                    break
            st.session_state.logs = recovered_logs
            st.session_state["_display_mode"] = g.status if g.status in ("running", "gate", "done", "error") else "idle"
            st.session_state["_display_gate"] = g.gate_name if g.status == "gate" else ""

        else:
            # _GLOBAL_BRIDGE 丢失（模块重载）：自动检测最近5分钟内的 checkpoint 并恢复
            try:
                from config import load_config as _lc
                _recent_projects = _list_resumable_projects(_lc().projects_root)
                if _recent_projects:
                    import os as _os
                    from config import load_config as _lc2
                    ck_dir = Path(_lc2().projects_root) / "_checkpoints"
                    # 找最近5分钟内修改过的
                    _cutoff = time.time() - 300
                    for _proj in _recent_projects:
                        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in _proj["project_id"])
                        ck_file = ck_dir / f"{safe_id}.json"
                        if ck_file.exists() and ck_file.stat().st_mtime > _cutoff:
                            # 自动静默恢复最近的项目
                            new_bridge = PipelineBridge()
                            new_bridge.state_snapshot = _proj["state"]
                            _GLOBAL_BRIDGE = new_bridge
                            st.session_state.bridge = new_bridge
                            st.session_state.logs = [f"🔄 自动恢复：{_proj['topic']}（{_proj['gate_label']}）"]
                            st.session_state["_display_mode"] = "gate"
                            st.session_state["_display_gate"] = _proj["gate"]
                            t = threading.Thread(
                                target=resume_pipeline_thread,
                                args=(_proj, new_bridge),
                                daemon=True,
                            )
                            t.start()
                            st.session_state.thread = t
                            break
            except Exception:
                pass

    bridge: PipelineBridge | None = st.session_state.bridge

    # ---- 标题栏 ----
    st.title("🎬 AI 科普视频生产系统")
    st.caption("风格参考「小Lin说」· DeepSeek 驱动 · 多 Agent 协作")

    # ---- 布局：左栏控制 / 右栏内容 ----
    left, right = st.columns([1, 2])

    with left:
        st.markdown("### 🚀 启动新项目")

        topic = st.text_input(
            "主题方向",
            placeholder="例如：美联储加息、比特币减半、关税战...",
            disabled=(bridge is not None and bridge.status not in ("idle", "done", "error")),
        )

        if st.button(
            "开始生产",
            type="primary",
            use_container_width=True,
            disabled=(not topic or (bridge is not None and bridge.status == "running")),
        ):
            new_bridge = PipelineBridge()
            _GLOBAL_BRIDGE = new_bridge
            st.session_state.bridge = new_bridge
            st.session_state.logs = []
            bridge = new_bridge

            t = threading.Thread(
                target=run_pipeline_thread,
                args=(topic, new_bridge),
                daemon=True,
            )
            t.start()
            st.session_state.thread = t
            st.rerun()

        # ---- 继续已有项目 ----
        st.divider()
        st.markdown("### 🔄 继续已有项目")
        if bridge is None or bridge.status in ("idle", "done", "error"):
            from config import load_config as _lc
            _cfg = _lc()
            resumable = _list_resumable_projects(_cfg.projects_root)
            if resumable:
                options = {
                    f"{r['topic']}（{r['gate_label']}）": r
                    for r in resumable
                }
                selected_label = st.selectbox(
                    "选择要继续的项目",
                    list(options.keys()),
                    key="resume_select",
                    label_visibility="collapsed",
                )
                if st.button("继续此项目", use_container_width=True):
                    selected = options[selected_label]
                    new_bridge = PipelineBridge()
                    new_bridge.state_snapshot = selected["state"]
                    _GLOBAL_BRIDGE = new_bridge
                    st.session_state.bridge = new_bridge
                    st.session_state.logs = [f"🔄 恢复项目：{selected['topic']}"]
                    st.session_state["_display_mode"] = "gate"
                    st.session_state["_display_gate"] = selected["gate"]
                    t = threading.Thread(
                        target=resume_pipeline_thread,
                        args=(selected, new_bridge),
                        daemon=True,
                    )
                    t.start()
                    st.session_state.thread = t
                    st.rerun()
            else:
                st.caption("暂无可继续的项目")

        # ---- 状态指示器 ----
        st.divider()
        if bridge is None:
            st.markdown("**状态**：等待启动")
        elif bridge.status == "running":
            st.markdown("**状态**：⚙️ 运行中...")
        elif bridge.status == "gate":
            st.markdown(f"**状态**：🔒 等待审核")
        elif bridge.status == "done":
            st.markdown("**状态**：✅ 完成！")
        elif bridge.status == "error":
            st.markdown("**状态**：❌ 出错")
            st.error(bridge.error[:500])

        # ---- 日志窗口（fragment 自动刷新） ----
        st.divider()
        _render_log_panel()

    # ---- 右栏：用 @st.fragment 完全隔离，独立轮询，不触发整页 rerun ----
    # fragment 内部的 rerun 只重绘右栏自身，不影响左栏 DOM，彻底消除 removeChild
    with right:
        _render_right_panel()


if __name__ == "__main__":
    main()
