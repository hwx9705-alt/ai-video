"""
_knowledge.py — 从 knowledge_base/xiaolin/examples/ 动态加载 prompt 注入素材

启动时一次性读取所有 .md，缓存在模块级变量。用户追加新示例后重启 streamlit 生效。
不做热重载以避免并发问题；不做 RAG / 向量检索，就是简单文件拼接。
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache


_BASE = Path(__file__).parent.parent / "knowledge_base" / "xiaolin" / "examples"


def _load_dir(subdir: str) -> str:
    d = _BASE / subdir
    if not d.exists():
        return f"（knowledge_base 目录未找到：{d}）"
    parts: list[str] = []
    for f in sorted(d.glob("*.md")):
        try:
            parts.append(f.read_text(encoding="utf-8").strip())
        except OSError as e:
            # 单文件读失败不应拖垮整个 agent
            parts.append(f"（读取失败 {f.name}: {e}）")
    if not parts:
        return f"（{subdir} 目录为空）"
    return "\n\n---\n\n".join(parts)


@lru_cache(maxsize=1)
def load_structures() -> str:
    """5 种叙事结构模板的完整案例库"""
    return _load_dir("structures")


@lru_cache(maxsize=1)
def load_techniques() -> str:
    """10 种叙事技巧的真实片段 + 技法拆解"""
    return _load_dir("techniques")


@lru_cache(maxsize=1)
def load_openings() -> str:
    """3 种开头钩子的范例"""
    return _load_dir("openings")


def available_scripts() -> list[str]:
    """列出 knowledge_base/xiaolin/scripts/ 下的原稿文件名，供自审引用"""
    scripts_dir = _BASE.parent / "scripts"
    if not scripts_dir.exists():
        return []
    return sorted(f.stem for f in scripts_dir.glob("*.md"))


if __name__ == "__main__":
    # 自测：python _knowledge.py
    print(f"Structures: {len(load_structures())} chars")
    print(f"Techniques: {len(load_techniques())} chars")
    print(f"Openings:   {len(load_openings())} chars")
    print(f"Scripts:    {available_scripts()}")
