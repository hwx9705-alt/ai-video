"""
音频处理器

负责：
1. 音量标准化（loudnorm）
2. BGM 混音（BGM 音量压到 15%，时长以人声为准）

技术栈：ffmpeg（通过 imageio-ffmpeg 获取可执行文件路径）
不需要 pydub / Whisper。
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from state import ProjectState, Stage, StageStatus


def _ffmpeg_exe() -> str:
    """获取 ffmpeg 可执行文件路径（imageio-ffmpeg 自带）"""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"  # 降级到系统 PATH


def _run(cmd: list, log_fn=None) -> bool:
    """执行 ffmpeg 命令，返回是否成功"""
    if log_fn:
        log_fn("执行: " + " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if log_fn:
            log_fn(f"ffmpeg 错误: {result.stderr[-300:]}")
        return False
    return True


class AudioProcessor:
    name = "audio_processor"

    def __init__(self, bgm_volume: float = 0.15):
        self.bgm_volume = bgm_volume
        self.ffmpeg = _ffmpeg_exe()

    def process(self, state: ProjectState) -> ProjectState:
        self._log("开始音频处理")

        raw_paths = state.get("audio_raw_paths", [])
        if not raw_paths:
            self._log("暂无录音文件，跳过音频处理")
            return state

        project_dir = Path(state["project_dir"])
        processed_dir = project_dir / "05_audio" / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        processed_paths = []

        for raw_path in raw_paths:
            if not Path(raw_path).exists():
                self._log(f"⚠️ 录音文件不存在：{raw_path}")
                continue

            # Step 1：音量标准化
            normalized_path = str(processed_dir / ("normalized_" + Path(raw_path).name))
            ok = self._normalize(raw_path, normalized_path)
            if not ok:
                self._log("标准化失败，使用原始文件")
                normalized_path = raw_path

            # Step 2：BGM 混音（如果有 BGM 文件）
            bgm_path = self._find_bgm(state)
            if bgm_path:
                mixed_path = str(processed_dir / ("mixed_" + Path(raw_path).stem + ".mp3"))
                ok = self._mix_bgm(normalized_path, bgm_path, mixed_path)
                final_path = mixed_path if ok else normalized_path
                if ok:
                    self._log(f"BGM 混音完成：{Path(mixed_path).name}")
            else:
                final_path = normalized_path
                self._log("未找到 BGM 文件，跳过混音")

            processed_paths.append(final_path)
            self._log(f"音频处理完成：{Path(final_path).name}")

        state["audio_processed_paths"] = processed_paths
        state["last_agent"] = self.name

        status = dict(state.get("stage_status", {}))
        status[Stage.AUDIO.value] = StageStatus.COMPLETED.value
        state["stage_status"] = status

        self._log(f"音频处理完成，共 {len(processed_paths)} 个文件")
        return state

    def _normalize(self, input_path: str, output_path: str) -> bool:
        """用 ffmpeg loudnorm 做音量标准化"""
        cmd = [
            self.ffmpeg, "-y", "-i", input_path,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            output_path
        ]
        return _run(cmd, self._log)

    def _mix_bgm(self, voice_path: str, bgm_path: str, output_path: str) -> bool:
        """人声 + BGM 混音，BGM 音量压到 bgm_volume，时长以人声为准"""
        vol = self.bgm_volume
        cmd = [
            self.ffmpeg, "-y",
            "-i", voice_path,
            "-i", bgm_path,
            "-filter_complex",
            f"[1:a]volume={vol},afade=t=out:st=0:d=3[bgm];[0:a][bgm]amix=inputs=2:duration=first[out]",
            "-map", "[out]",
            output_path
        ]
        return _run(cmd, self._log)

    def _find_bgm(self, state: ProjectState) -> str:
        """
        查找 BGM 文件：
        1. 先看本地 assets/bgm/ 有没有手动放的文件
        2. 没有则调 Freesound API 自动下载
        """
        bgm_dir = Path(__file__).parent.parent / "assets" / "bgm"

        # 先找本地已有文件
        extensions = [".mp3", ".wav", ".m4a", ".aac"]
        if bgm_dir.exists():
            for ext in extensions:
                files = sorted(bgm_dir.glob(f"*{ext}"))
                if files:
                    self._log(f"使用本地 BGM：{files[0].name}")
                    return str(files[0])

        # 没有则自动下载
        self._log("本地无 BGM，尝试 Freesound 自动下载...")
        try:
            from tools.bgm_finder import find_and_download_bgm
            # 估算视频总时长（用于选接近的 BGM）
            total_dur = 300.0
            path = find_and_download_bgm(
                state=dict(state),
                output_dir=str(bgm_dir),
                duration_seconds=total_dur,
                log_fn=self._log,
            )
            return path
        except Exception as e:
            self._log(f"自动 BGM 获取失败：{e}")
            return ""

    def _log(self, msg: str):
        print(f"[{time.strftime('%H:%M:%S')}] [{self.name}] {msg}")
