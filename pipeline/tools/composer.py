"""
视频合成器

负责：
1. 读取分镜表中每段的预估时长
2. 将图片序列按时长拼成视频
3. 叠加处理后的音频（人声 + BGM）
4. 输出 MP4

技术栈：ffmpeg（通过 imageio-ffmpeg）
时长策略：以分镜表 estimated_duration_sec 为基础，
         按比例缩放到实际录音时长，确保画面不超出/不短于音频。
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from state import ProjectState, Stage, StageStatus


def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _run(cmd: list, log_fn=None) -> tuple:
    """执行命令，返回 (success, stderr)"""
    if log_fn:
        log_fn("执行: " + " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and log_fn:
        log_fn(f"ffmpeg 错误: {result.stderr[-400:]}")
    return result.returncode == 0, result.stderr


def _get_audio_duration(ffmpeg: str, audio_path: str) -> float:
    """获取音频时长（秒）"""
    cmd = [
        ffmpeg, "-i", audio_path,
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # 从 stderr 解析 Duration
    for line in result.stderr.splitlines():
        if "Duration:" in line:
            parts = line.strip().split("Duration:")[1].split(",")[0].strip()
            h, m, s = parts.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
    return 0.0


def _parse_storyboard(storyboard_raw: str) -> list:
    """解析分镜表，返回 segment 列表"""
    if not storyboard_raw:
        return []
    import re
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


class VideoComposer:
    name = "video_composer"

    def __init__(self, resolution=(1920, 1080), fps=30):
        self.resolution = resolution
        self.fps = fps
        self.ffmpeg = _ffmpeg_exe()

    def compose(self, state: ProjectState) -> ProjectState:
        self._log("开始视频合成")

        visual_paths = state.get("visual_paths", [])
        audio_paths = state.get("audio_processed_paths", []) or state.get("audio_raw_paths", [])
        storyboard_raw = state.get("storyboard", "")
        project_dir = Path(state["project_dir"])
        output_dir = project_dir / "07_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        if not visual_paths:
            self._log("⚠️ 没有视觉素材，无法合成")
            state["error_message"] = "缺少视觉素材"
            return state

        if not audio_paths:
            self._log("⚠️ 没有音频文件，将合成无声视频")

        # 解析分镜段时长
        segments = _parse_storyboard(storyboard_raw)
        durations = self._calc_durations(segments, visual_paths, audio_paths)

        self._log(f"共 {len(visual_paths)} 张图片，总预估时长 {sum(durations):.1f}s")

        # 合成视频
        output_path = str(output_dir / "draft_video.mp4")
        audio_path = audio_paths[0] if audio_paths else None

        ok = self._compose_video(visual_paths, durations, audio_path, output_path)

        if ok:
            self._log(f"视频合成完成：{output_path}")
            state["draft_video_path"] = output_path
        else:
            self._log("视频合成失败")
            state["error_message"] = "ffmpeg 合成失败，请查看后端日志"

        state["last_agent"] = self.name
        status = dict(state.get("stage_status", {}))
        status[Stage.COMPOSE.value] = StageStatus.AWAITING_REVIEW.value
        state["stage_status"] = status
        state["current_review_gate"] = "gate_4"

        self._log("等待审核门4")
        return state

    def _calc_durations(
        self,
        segments: list,
        visual_paths: list,
        audio_paths: list,
    ) -> list:
        """
        计算每张图片的显示时长。
        - 如果有录音：用分镜预估时长按比例缩放到录音总时长
        - 如果没有录音：直接用分镜预估时长，默认 5s/张
        """
        n = len(visual_paths)

        # 从分镜表取预估时长
        seg_durations = []
        for i in range(n):
            if i < len(segments):
                d = segments[i].get("estimated_duration_sec", 5)
                seg_durations.append(max(float(d), 1.0))
            else:
                seg_durations.append(5.0)

        if not audio_paths or not Path(audio_paths[0]).exists():
            return seg_durations

        # 获取实际录音时长，按比例缩放
        audio_dur = _get_audio_duration(self.ffmpeg, audio_paths[0])
        if audio_dur <= 0:
            return seg_durations

        total_estimated = sum(seg_durations)
        if total_estimated <= 0:
            return [audio_dur / n] * n

        scale = audio_dur / total_estimated
        scaled = [d * scale for d in seg_durations]
        self._log(f"录音时长 {audio_dur:.1f}s，分镜预估 {total_estimated:.1f}s，缩放比例 {scale:.2f}")
        return scaled

    def _compose_video(
        self,
        image_paths: list,
        durations: list,
        audio_path: str | None,
        output_path: str,
    ) -> bool:
        """
        用 ffmpeg concat demuxer 把图片序列拼成视频，叠加音频。
        """
        w, h = self.resolution

        # 写 concat 文件（必须用绝对路径，ffmpeg 相对路径是相对 concat 文件目录，不是 CWD）
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            concat_file = f.name
            for img_path, dur in zip(image_paths, durations):
                safe_path = str(Path(img_path).resolve()).replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
                f.write(f"duration {dur:.3f}\n")
            # 最后一帧重复写一次（ffmpeg concat 需要）
            if image_paths:
                safe_path = str(Path(image_paths[-1]).resolve()).replace("\\", "/")
                f.write(f"file '{safe_path}'\n")

        try:
            if audio_path and Path(audio_path).exists():
                cmd = [
                    self.ffmpeg, "-y",
                    "-f", "concat", "-safe", "0", "-i", concat_file,
                    "-i", audio_path,
                    "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                           f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    "-pix_fmt", "yuv420p",
                    output_path
                ]
            else:
                cmd = [
                    self.ffmpeg, "-y",
                    "-f", "concat", "-safe", "0", "-i", concat_file,
                    "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                           f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    output_path
                ]

            ok, _ = _run(cmd, self._log)
            return ok
        finally:
            try:
                os.unlink(concat_file)
            except Exception:
                pass

    def _log(self, msg: str):
        print(f"[{time.strftime('%H:%M:%S')}] [{self.name}] {msg}")
