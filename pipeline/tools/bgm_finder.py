"""
BGM 自动查找工具

流程：
1. 从 style_seeds 读取 visual_mood 和 ai_image_style_keywords
2. 用 LLM 把中文情绪描述翻译成 Freesound 搜索标签
3. 调 Freesound API 搜索匹配的免版权音乐
4. 下载最合适的一首到 assets/bgm/

Freesound API 免费：https://freesound.org/apiv2/
注册后在 https://freesound.org/apiv2/apply/ 申请 key，填入 .env 的 FREESOUND_API_KEY
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

# 绕过系统代理
_session = requests.Session()
_session.trust_env = False


# 情绪 → Freesound 标签映射（离线兜底，不依赖 LLM）
MOOD_TAG_MAP = {
    "专业稳重": ["corporate", "background", "calm", "piano"],
    "紧张刺激": ["tension", "dramatic", "cinematic", "suspense"],
    "活泼轻松": ["upbeat", "cheerful", "happy", "acoustic"],
    "沉重严肃": ["serious", "dark", "ambient", "orchestral"],
    "科技感": ["electronic", "technology", "ambient", "modern"],
    "温暖人文": ["warm", "acoustic", "gentle", "emotional"],
    "宏大史诗": ["epic", "cinematic", "orchestral", "dramatic"],
    "轻松幽默": ["funny", "quirky", "playful", "ukulele"],
}

# 默认标签（无法匹配时用）
DEFAULT_TAGS = ["background", "music", "calm", "loop"]


def _mood_to_tags(visual_mood: str, topic_keywords: str = "") -> list:
    """把 visual_mood 转换为 Freesound 搜索标签"""
    # 先查本地映射
    for key, tags in MOOD_TAG_MAP.items():
        if key in visual_mood:
            return tags

    # 降级：从 topic_keywords 提取英文词
    if topic_keywords:
        words = [w.strip() for w in topic_keywords.replace(",", " ").split() if w.strip().isascii()]
        if words:
            return words[:3] + ["background", "music"]

    return DEFAULT_TAGS


def find_and_download_bgm(
    state: dict,
    output_dir: str,
    duration_seconds: float = 300.0,
    log_fn=None,
) -> str:
    """
    根据视频风格自动查找并下载 BGM。

    参数：
        state: ProjectState，读取 style_seeds
        output_dir: BGM 保存目录
        duration_seconds: 期望时长（秒），优先选接近的
        log_fn: 日志回调

    返回：下载的文件路径，失败返回空字符串
    """
    api_key = os.environ.get("FREESOUND_API_KEY", "")
    if not api_key:
        _log("⚠️ FREESOUND_API_KEY 未配置，跳过自动 BGM", log_fn)
        return ""

    # 解析 style_seeds
    visual_mood = ""
    topic_keywords = ""
    seeds_raw = state.get("style_seeds", "")
    if seeds_raw:
        try:
            seeds = json.loads(seeds_raw)
            visual_mood = seeds.get("visual_mood", "")
            topic_keywords = seeds.get("ai_image_style_keywords", "")
        except Exception:
            pass

    # 如果没有 style_seeds，从话题方向推断
    if not visual_mood:
        topic = state.get("topic_direction", "")
        visual_mood = "专业稳重"  # 财经科普默认风格
        _log(f"style_seeds 为空，使用默认情绪：{visual_mood}", log_fn)

    tags = _mood_to_tags(visual_mood, topic_keywords)
    query = " ".join(tags[:3])
    _log(f"视频情绪：{visual_mood} → 搜索标签：{query}", log_fn)

    # 搜索 Freesound
    try:
        resp = _session.get(
            "https://freesound.org/apiv2/search/text/",
            params={
                "query": query,
                "filter": "duration:[60 TO 600] tag:music tag:loop",
                "fields": "id,name,duration,previews,license,username",
                "page_size": 15,
                "sort": "rating_desc",
                "token": api_key,
            },
            timeout=20,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except Exception as e:
        _log(f"Freesound 搜索失败：{e}", log_fn)
        return ""

    if not results:
        _log("未找到匹配 BGM，尝试宽松搜索...", log_fn)
        try:
            resp = _session.get(
                "https://freesound.org/apiv2/search/text/",
                params={
                    "query": "background music calm",
                    "filter": "duration:[60 TO 600]",
                    "fields": "id,name,duration,previews,license,username",
                    "page_size": 5,
                    "sort": "rating_desc",
                    "token": api_key,
                },
                timeout=20,
            )
            results = resp.json().get("results", [])
        except Exception:
            return ""

    if not results:
        _log("Freesound 无结果", log_fn)
        return ""

    # 选最接近目标时长的一首
    best = min(results, key=lambda r: abs(r.get("duration", 0) - duration_seconds))
    name = best.get("name", "bgm")
    duration = best.get("duration", 0)
    license_ = best.get("license", "")
    _log(f"选中：{name}（{duration:.0f}s）License: {license_}", log_fn)

    # 下载 preview mp3（高质量）
    preview_url = (best.get("previews") or {}).get("preview-hq-mp3", "")
    if not preview_url:
        preview_url = (best.get("previews") or {}).get("preview-lq-mp3", "")

    if not preview_url:
        _log("无可用下载链接", log_fn)
        return ""

    try:
        dl = _session.get(preview_url, timeout=60)
        dl.raise_for_status()
    except Exception as e:
        _log(f"BGM 下载失败：{e}", log_fn)
        return ""

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name)[:50]
    out_path = str(Path(output_dir) / f"{safe_name}.mp3")
    with open(out_path, "wb") as f:
        f.write(dl.content)

    _log(f"BGM 已下载：{out_path}（{len(dl.content)//1024} KB）", log_fn)
    return out_path


def _log(msg: str, log_fn=None):
    ts = time.strftime("%H:%M:%S")
    full = f"[{ts}] [bgm_finder] {msg}"
    print(full)
    if log_fn:
        log_fn(msg)
