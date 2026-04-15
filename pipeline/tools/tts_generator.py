"""
TTS 语音合成工具

使用硅基流动 (SiliconFlow) 的 TTS API 合成语音。
API 兼容 OpenAI audio/speech 接口格式。

支持模型：
  - FunAudioLLM/CosyVoice2-0.5B（推荐，中文效果好）
  - fishaudio/fish-speech-1.4（备选）
"""

from __future__ import annotations

import re
import time
from pathlib import Path
import requests

_session = requests.Session()
_session.trust_env = False

# 可选音色
# key = UI 显示名，value = (model, voice)
# voice 格式：{model}:{voice_name}
AVAILABLE_VOICES = {
    "女声·温柔 (claire)":   ("FunAudioLLM/CosyVoice2-0.5B", "FunAudioLLM/CosyVoice2-0.5B:claire"),
    "女声·稳定 (anna)":     ("FunAudioLLM/CosyVoice2-0.5B", "FunAudioLLM/CosyVoice2-0.5B:anna"),
    "女声·热情 (bella)":    ("FunAudioLLM/CosyVoice2-0.5B", "FunAudioLLM/CosyVoice2-0.5B:bella"),
    "女声·欢快 (diana)":    ("FunAudioLLM/CosyVoice2-0.5B", "FunAudioLLM/CosyVoice2-0.5B:diana"),
    "男声·稳定 (alex)":     ("FunAudioLLM/CosyVoice2-0.5B", "FunAudioLLM/CosyVoice2-0.5B:alex"),
    "男声·深沉 (benjamin)": ("FunAudioLLM/CosyVoice2-0.5B", "FunAudioLLM/CosyVoice2-0.5B:benjamin"),
    "男声·磁性 (charles)":  ("FunAudioLLM/CosyVoice2-0.5B", "FunAudioLLM/CosyVoice2-0.5B:charles"),
    "男声·欢快 (david)":    ("FunAudioLLM/CosyVoice2-0.5B", "FunAudioLLM/CosyVoice2-0.5B:david"),
}

DEFAULT_MODEL = "FunAudioLLM/CosyVoice2-0.5B"
DEFAULT_VOICE = "FunAudioLLM/CosyVoice2-0.5B:claire"


def extract_narration(script_full: str) -> str:
    """
    从完整脚本中提取纯口播文本，过滤所有制作指令标记。

    过滤内容：
    - Markdown 标题行（#、##、### 等）
    - **[画面提示]** / **[使用技巧]** 等方括号指令行
    - 【语气指令】等中文方括号指令行（单独成行）
    - ⚠️ 数据核实提示行
    - 段落标题行（如 **第一段：XXXX**）
    行内清理：
    - 移除 （语气/说明/技巧/提示/指令/注意）类括号注释
    - 移除 【...】 片段
    - 移除 ** 加粗标记（保留文字）
    """
    lines = script_full.splitlines()
    result = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            result.append("")
            continue

        # 跳过 Markdown 标题
        if re.match(r'^#{1,6}\s', stripped):
            continue

        # 跳过 **[...]** 类指令行（整行都是指令）
        if re.match(r'^\*\*\[.+?\]\*\*', stripped):
            continue

        # 跳过 【...】 类指令行（单独成行）
        if re.match(r'^【.+?】\s*$', stripped):
            continue

        # 跳过 ⚠️ 行
        if stripped.startswith('⚠'):
            continue

        # 跳过段落标题行（形如 **第X段：...** 或 **一、...**）
        if re.match(r'^\*\*.{1,30}[：:].{0,30}\*\*$', stripped):
            continue

        # 行内：移除括号内含指令性词汇的注释
        cleaned = re.sub(
            r'（[^）]{0,40}(?:语气|说明|技巧|提示|指令|注意|建议)[^）]{0,40}）',
            '', stripped
        )
        # 行内：移除剩余的 【...】 片段
        cleaned = re.sub(r'【[^】]{0,30}】', '', cleaned)
        # 行内：移除 ** 加粗标记（保留文字）
        cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', cleaned)

        cleaned = cleaned.strip()
        if cleaned:
            result.append(cleaned)

    text = '\n'.join(result)
    # 合并多个连续空行为单空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def synthesize_speech(
    text: str,
    output_path: str,
    api_key: str,
    voice: str = DEFAULT_VOICE,
    model: str = DEFAULT_MODEL,
    base_url: str = "https://api.siliconflow.cn/v1",
    speed: float = 1.0,
    log_fn=None,
) -> str:
    """
    合成语音并保存到文件。

    参数：
      text        : 待合成文本
      output_path : 输出 MP3 路径
      api_key     : SiliconFlow API key
      voice       : 音色名称（见 AVAILABLE_VOICES）
      model       : TTS 模型名
      base_url    : API 基地址
      speed       : 语速，0.5–2.0，默认 1.0

    返回保存的文件路径，失败时抛出异常。
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    url = f"{base_url.rstrip('/')}/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": "mp3",
        "speed": speed,
    }

    _log(log_fn, f"开始合成，模型：{model}，音色：{voice}，文本 {len(text)} 字")

    resp = _session.post(url, headers=headers, json=payload, timeout=180)
    if not resp.ok:
        try:
            err = resp.json().get("message") or resp.text[:300]
        except Exception:
            err = resp.text[:300]
        raise RuntimeError(f"TTS API 错误 {resp.status_code}: {err}")

    with open(output_path, "wb") as f:
        f.write(resp.content)

    size_kb = Path(output_path).stat().st_size // 1024
    _log(log_fn, f"合成完成，{size_kb} KB → {output_path}")
    return output_path


def _log(log_fn, msg: str):
    ts = time.strftime("%H:%M:%S")
    if log_fn:
        log_fn(f"[{ts}] [tts] {msg}")
    else:
        print(f"[{ts}] [tts] {msg}")
