"""
render.py — Python → Remotion 渲染桥

读取 StoryboardData JSON，复制资源到 public/，调用 npx remotion render。

用法：
    python render.py --script public/storyboard.json --output out/video.mp4
    python render.py --script path/to/script.json --output out/video.mp4 --concurrency 4
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REMOTION_DIR = Path(__file__).parent
PUBLIC_DIR = REMOTION_DIR / "public"
COMPOSITION_ID = "Main"


def prepare_assets(storyboard: dict) -> dict:
    """
    将分镜中引用的本地图片复制到 public/assets/，
    并将路径改为相对 public/ 的路径（Remotion staticFile 用）。
    """
    assets_dir = PUBLIC_DIR / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 音频
    if storyboard.get("audioPath"):
        src = Path(storyboard["audioPath"])
        if src.exists():
            dst = assets_dir / src.name
            shutil.copy2(src, dst)
            storyboard["audioPath"] = f"assets/{src.name}"
            print(f"[render] 复制音频: {src.name}")

    # 各段 ImageWithOverlay 的 imageSrc
    for seg in storyboard.get("segments", []):
        if seg.get("component") == "ImageWithOverlay":
            img_src = seg.get("props", {}).get("imageSrc", "")
            if img_src and not img_src.startswith(("http://", "https://", "assets/")):
                src = Path(img_src)
                if src.exists():
                    dst = assets_dir / src.name
                    shutil.copy2(src, dst)
                    seg["props"]["imageSrc"] = f"assets/{src.name}"
                    print(f"[render] 复制图片: {src.name}")

    return storyboard


def calc_total_frames(storyboard: dict) -> int:
    fps = storyboard.get("fps", 30)
    return sum(
        round(seg.get("durationInSeconds", 5) * fps)
        for seg in storyboard.get("segments", [])
    )


def render(script_path: str, output_path: str, concurrency: int = 2) -> None:
    with open(script_path, encoding="utf-8") as f:
        storyboard = json.load(f)

    storyboard = prepare_assets(storyboard)
    fps = storyboard.get("fps", 30)
    total_frames = calc_total_frames(storyboard)
    total_sec = total_frames / fps

    print(f"[render] 标题: {storyboard.get('title', '未命名')}")
    print(f"[render] 共 {len(storyboard['segments'])} 段, {total_frames} 帧 ({total_sec:.1f}s)")

    # 写入 public/storyboard.json 供 Remotion 读取
    storyboard_json_path = PUBLIC_DIR / "storyboard.json"
    storyboard_json_path.write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[render] 分镜已写入 {storyboard_json_path}")

    # 输出目录
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # 通过 --props 文件传递（避免 CLI 长度限制）
    props_path = PUBLIC_DIR / "_render_props.json"
    props_path.write_text(
        json.dumps({"storyboard": storyboard}, ensure_ascii=False),
        encoding="utf-8",
    )

    cmd = [
        "npx", "remotion", "render",
        COMPOSITION_ID,
        str(output_path),
        f"--props={props_path}",
        "--concurrency", str(concurrency),
        "--log", "verbose",
    ]

    env = {**os.environ, "BROWSER_EXECUTABLE_PATH": "/usr/bin/chromium-browser"}

    print(f"[render] 执行渲染...")
    result = subprocess.run(cmd, cwd=str(REMOTION_DIR), env=env)

    # 清理临时 props 文件
    props_path.unlink(missing_ok=True)

    if result.returncode != 0:
        print("[render] ❌ 渲染失败")
        sys.exit(result.returncode)
    else:
        size_mb = Path(output_path).stat().st_size / 1024 / 1024 if Path(output_path).exists() else 0
        print(f"[render] ✅ 渲染完成: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remotion 视频渲染桥")
    parser.add_argument("--script", required=True, help="StoryboardData JSON 路径")
    parser.add_argument("--output", required=True, help="输出 MP4 路径")
    parser.add_argument("--concurrency", type=int, default=2, help="渲染并发数")
    args = parser.parse_args()
    render(args.script, args.output, args.concurrency)
