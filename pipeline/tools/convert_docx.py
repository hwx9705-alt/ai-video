"""
convert_docx.py — 把 /home/ubuntu/upload/小lin说文字稿/*.docx 转为 Markdown

一次性工具。输出到 pipeline/knowledge_base/xiaolin/scripts/ 下。
docx 里的段落样式保留（Heading -> #、加粗 -> **），表格和图片忽略。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document


SRC_DIR = Path("/home/ubuntu/upload/小lin说文字稿")
DST_DIR = Path(__file__).parent.parent / "knowledge_base" / "xiaolin" / "scripts"

# 文件名清洗：去 "一口气了解" "【硬核】" "(Av...P1)" 等噪音 → 保留核心主题
FILENAME_MAP = {
    "一口气了解关税": "关税",
    "美元开启降息周期了，所以呢": "降息周期",
    "【硬核】一口气了解国债，这么一直借下去真的可以么？": "国债",
    "小Lin说_文字稿合集_整理版": "_合集整理版",
    "机器人篇_讲解逻辑脉络分析": "_机器人篇_脉络分析",
    "小Lin说_讲解逻辑脉络分析_5篇合集": "_脉络分析_5篇合集",
    "机器人，真的要来了么...？": "机器人",
    "一口气了解全球经济形势": "全球经济",
    "【硬核】一口气了解美联储 全球权力最大的金融机构": "美联储",
}


def clean_filename(docx_name: str) -> str:
    # 去掉 " - 1.xxx(AvXXX,P1).docx" 后缀
    base = re.sub(r"\s*-\s*1\..*$", "", docx_name.rsplit(".", 1)[0])
    # 查映射表
    for raw, clean in FILENAME_MAP.items():
        if base.startswith(raw):
            return clean
    # fallback：保留原名
    return base.replace(" ", "_")


def paragraph_to_md(para) -> str:
    style = para.style.name.lower() if para.style else ""
    text_parts = []
    for run in para.runs:
        t = run.text
        if not t:
            continue
        if run.bold:
            t = f"**{t}**"
        text_parts.append(t)
    text = "".join(text_parts).strip()
    if not text:
        return ""
    if style.startswith("heading 1"):
        return f"# {text}"
    if style.startswith("heading 2"):
        return f"## {text}"
    if style.startswith("heading 3"):
        return f"### {text}"
    return text


def convert_one(src: Path, dst: Path) -> int:
    doc = Document(str(src))
    lines: list[str] = []
    for para in doc.paragraphs:
        md = paragraph_to_md(para)
        if md:
            lines.append(md)
        elif lines and lines[-1] != "":
            lines.append("")  # 空行保留段落分隔
    content = "\n\n".join(l for l in lines if l).strip() + "\n"
    dst.write_text(content, encoding="utf-8")
    return len(content)


def main() -> None:
    if not SRC_DIR.exists():
        print(f"Source dir not found: {SRC_DIR}", file=sys.stderr)
        sys.exit(1)
    DST_DIR.mkdir(parents=True, exist_ok=True)

    total = 0
    for src in sorted(SRC_DIR.glob("*.docx")):
        name = clean_filename(src.name)
        dst = DST_DIR / f"{name}.md"
        size = convert_one(src, dst)
        total += size
        print(f"  {src.name:60s} → {dst.name}  ({size} chars)")

    print(f"\nTotal: {total} chars across {len(list(DST_DIR.glob('*.md')))} files")
    print(f"Output: {DST_DIR}")


if __name__ == "__main__":
    main()
