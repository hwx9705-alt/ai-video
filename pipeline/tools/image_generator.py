"""
AI 生图工具

支持多个生图 API，通过 config.py 的 image_gen_provider 切换。
当前支持：
  - fal_flux   : fal.ai 的 Flux.1 (推荐，性价比最高)
  - replicate  : Replicate 平台 (支持 Flux / SDXL 等)
  - dalle3     : OpenAI DALL-E 3

API key 未配置时自动生成占位图。
"""

from __future__ import annotations

import os
import json
import time
import requests
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# 代理绕过 Session
_session = requests.Session()
_session.trust_env = False


# ============================================================
# 主入口
# ============================================================

def generate_image(
    prompt: str,
    output_path: str,
    style_keywords: str = "",
    provider: str = "",
    api_key: str = "",
    width: int = 1920,
    height: int = 1080,
) -> str:
    """
    生成 AI 图片。

    参数：
      prompt         : 英文描述（由 LLM 生成）
      output_path    : 输出 PNG 路径
      style_keywords : 来自 style_seeds 的风格关键词，自动拼接到 prompt
      provider       : "fal_flux" | "replicate" | "dalle3"
      api_key        : 对应平台的 API key

    返回生成的图片路径。
    """
    os.makedirs(str(Path(output_path).parent), exist_ok=True)

    full_prompt = f"{prompt}, {style_keywords}".strip(", ") if style_keywords else prompt

    if not api_key:
        print(f"[image_generator] API key 未配置，生成占位图")
        return _placeholder_image(output_path, prompt, width, height)

    try:
        if provider == "siliconflow":
            from config import load_config
            cfg = load_config()
            model = getattr(cfg, "image_gen_model", "black-forest-labs/FLUX.1-pro")
            base_url = getattr(cfg, "image_gen_base_url", "https://api.siliconflow.cn/v1")
            return _generate_siliconflow(full_prompt, output_path, api_key, model, base_url, width, height)
        elif provider == "fal_flux":
            return _generate_fal_flux(full_prompt, output_path, api_key, width, height)
        elif provider == "replicate":
            return _generate_replicate(full_prompt, output_path, api_key, width, height)
        elif provider == "dalle3":
            return _generate_dalle3(full_prompt, output_path, api_key)
        else:
            print(f"[image_generator] 未知 provider: {provider}，生成占位图")
            return _placeholder_image(output_path, prompt, width, height)
    except Exception as e:
        print(f"[image_generator] 生成失败: {e}，回退到占位图")
        return _placeholder_image(output_path, prompt, width, height)


# ============================================================
# 硅基流动 SiliconFlow（国内直连，推荐首选）
# ============================================================

def _generate_siliconflow(prompt: str, output_path: str, api_key: str,
                           model: str, base_url: str,
                           width: int, height: int) -> str:
    """
    调用硅基流动的图像生成 API（OpenAI images 兼容接口）
    支持 FLUX.1-pro / FLUX.1-dev / FLUX.1-schnell 等
    """
    url = f"{base_url.rstrip('/')}/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "image_size": f"{width}x{height}",
        "num_inference_steps": 20,
        "guidance_scale": 3.5,
        "num_images": 1,
    }

    print(f"[image_generator] 调用硅基流动 {model}...")
    resp = _session.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    img_url = data["images"][0]["url"]
    return _download_image(img_url, output_path)


# ============================================================
# fal.ai Flux.1
# ============================================================

def _generate_fal_flux(prompt: str, output_path: str, api_key: str,
                        width: int, height: int) -> str:
    """
    调用 fal.ai 的 Flux.1-schnell（快速版，约 $0.003/张）
    或 Flux.1-dev（高质量版，约 $0.025/张）
    """
    url = "https://fal.run/fal-ai/flux/schnell"
    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "image_size": {"width": width, "height": height},
        "num_inference_steps": 4,
        "num_images": 1,
        "enable_safety_checker": False,
    }

    print(f"[image_generator] 调用 fal.ai Flux.1...")
    resp = _session.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    # 下载图片
    img_url = data["images"][0]["url"]
    return _download_image(img_url, output_path)


# ============================================================
# Replicate
# ============================================================

def _generate_replicate(prompt: str, output_path: str, api_key: str,
                         width: int, height: int) -> str:
    """
    调用 Replicate 平台的 Flux.1-schnell
    约 $0.003/张
    """
    url = "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }
    payload = {
        "input": {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_outputs": 1,
            "go_fast": True,
        }
    }

    print(f"[image_generator] 调用 Replicate Flux.1...")
    resp = _session.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    # Replicate 可能异步，轮询结果
    if data.get("status") in ("starting", "processing"):
        pred_url = data["urls"]["get"]
        for _ in range(30):
            time.sleep(3)
            r = _session.get(pred_url, headers=headers, timeout=30)
            d = r.json()
            if d.get("status") == "succeeded":
                data = d
                break
            elif d.get("status") == "failed":
                raise RuntimeError(f"Replicate 生成失败: {d.get('error')}")

    img_url = data["output"][0]
    return _download_image(img_url, output_path)


# ============================================================
# DALL-E 3
# ============================================================

def _generate_dalle3(prompt: str, output_path: str, api_key: str) -> str:
    """
    调用 OpenAI DALL-E 3
    标准质量 1792x1024：$0.04/张
    HD 质量：$0.08/张
    """
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "dall-e-3",
        "prompt": prompt[:4000],   # DALL-E 3 限制
        "size": "1792x1024",
        "quality": "standard",
        "n": 1,
    }

    print(f"[image_generator] 调用 DALL-E 3...")
    resp = _session.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    img_url = data["data"][0]["url"]
    return _download_image(img_url, output_path)


# ============================================================
# 工具函数
# ============================================================

def _download_image(url: str, output_path: str) -> str:
    """下载图片到本地"""
    resp = _session.get(url, timeout=60)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    print(f"[image_generator] 图片已保存: {output_path}")
    return output_path


def _placeholder_image(output_path: str, prompt: str,
                        width: int = 1920, height: int = 1080) -> str:
    """生成占位图（深色背景 + 提示文字）"""
    if not HAS_PIL:
        # 无 PIL 时创建空文件占位
        Path(output_path).write_bytes(b"")
        return output_path

    img = Image.new("RGB", (width, height), color=(15, 23, 42))   # #0F172A
    draw = ImageDraw.Draw(img)

    # 画边框
    draw.rectangle([40, 40, width-40, height-40],
                   outline=(30, 58, 138), width=3)   # #1E3A8A

    # 写提示文字
    text = f"[AI 生图占位]\n{prompt[:120]}"
    draw.text((width//2, height//2), text,
              fill=(248, 250, 252),   # #F8FAFC
              anchor="mm",
              align="center")

    img.save(output_path)
    print(f"[image_generator] 占位图已保存: {output_path}")
    return output_path


# ============================================================
# Prompt 优化工具
# ============================================================

def build_image_prompt(
    visual_description: str,
    style_keywords: str,
    segment_title: str = "",
) -> str:
    """
    将中文的 visual_description 转为适合 AI 生图的英文 prompt 结构。
    （实际使用时由 LLM 翻译和优化，这里提供基础结构）
    """
    base = visual_description[:300]
    return f"{base}, {style_keywords}, high quality, 16:9 aspect ratio"
