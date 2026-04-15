"""
图表生成器

根据分镜表中的 visual_description 和 key_elements，
使用 Plotly 生成数据图表，使用 Matplotlib 生成对比图。

输出：PNG 图片文件（1920x1080，适合视频合成）
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.font_manager as fm

    # 设置中文字体，优先 Windows 字体，其次 Linux Noto CJK
    _cjk_fonts = [
        "Microsoft YaHei", "SimHei", "STSong", "SimSun",
        "Noto Sans CJK SC", "Noto Serif CJK SC",
        "Noto Sans CJK JP", "Noto Serif CJK JP",  # JP 字体同样包含全部 CJK 汉字
    ]
    _available = {f.name for f in fm.fontManager.ttflist}
    _chosen = next((f for f in _cjk_fonts if f in _available), None)
    if _chosen:
        matplotlib.rcParams["font.family"] = _chosen
    matplotlib.rcParams["axes.unicode_minus"] = False  # 负号正常显示

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# 视频分辨率
VIDEO_W, VIDEO_H = 1920, 1080
# plotly 导出尺寸
PLOTLY_W, PLOTLY_H = 1920, 1080


def _get_style(style_seeds: dict | None) -> dict:
    """从 style_seeds 提取配色，提供默认值"""
    defaults = {
        "primary": "#1E3A8A",
        "secondary": "#DC2626",
        "accent": "#F59E0B",
        "background": "#0F172A",
        "text": "#F8FAFC",
    }
    if style_seeds and "color_palette" in style_seeds:
        palette = style_seeds["color_palette"]
        defaults.update({k: v for k, v in palette.items() if v})
    return defaults


def _plotly_base_layout(style: dict, title: str = "") -> dict:
    """返回统一的 Plotly 布局配置"""
    return dict(
        title=dict(text=title, font=dict(color=style["text"], size=32), x=0.5),
        paper_bgcolor=style["background"],
        plot_bgcolor=style["background"],
        font=dict(color=style["text"], size=18),
        margin=dict(l=80, r=80, t=100, b=80),
        width=PLOTLY_W,
        height=PLOTLY_H,
    )


# ============================================================
# 图表类型生成函数
# ============================================================

def generate_bar_chart(
    output_path: str,
    labels: list,
    values: list,
    title: str = "",
    x_title: str = "",
    y_title: str = "",
    style: dict | None = None,
) -> str:
    """生成柱状图"""
    if not HAS_PLOTLY:
        return _fallback_text_image(output_path, f"[柱状图] {title}")

    s = _get_style(style)
    colors = [s["primary"], s["secondary"], s["accent"],
              "#10B981", "#8B5CF6", "#EC4899"]
    bar_colors = [colors[i % len(colors)] for i in range(len(labels))]

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=bar_colors,
        text=[str(v) for v in values],
        textposition="outside",
        textfont=dict(color=s["text"], size=20),
    ))
    fig.update_layout(
        **_plotly_base_layout(s, title),
        xaxis=dict(title=x_title, gridcolor="#1E293B", tickfont=dict(size=16)),
        yaxis=dict(title=y_title, gridcolor="#1E293B", tickfont=dict(size=16)),
        bargap=0.3,
    )
    fig.write_image(output_path, scale=1)
    return output_path


def generate_line_chart(
    output_path: str,
    x_data: list,
    y_series: dict,   # {"系列名": [y值列表]}
    title: str = "",
    x_title: str = "",
    y_title: str = "",
    style: dict | None = None,
) -> str:
    """生成折线图（支持多条线）"""
    if not HAS_PLOTLY:
        return _fallback_text_image(output_path, f"[折线图] {title}")

    s = _get_style(style)
    line_colors = [s["primary"], s["secondary"], s["accent"], "#10B981"]

    fig = go.Figure()
    for i, (name, y_vals) in enumerate(y_series.items()):
        fig.add_trace(go.Scatter(
            x=x_data,
            y=y_vals,
            mode="lines+markers",
            name=name,
            line=dict(color=line_colors[i % len(line_colors)], width=4),
            marker=dict(size=10),
        ))
    fig.update_layout(
        **_plotly_base_layout(s, title),
        xaxis=dict(title=x_title, gridcolor="#1E293B"),
        yaxis=dict(title=y_title, gridcolor="#1E293B"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=16)),
    )
    fig.write_image(output_path, scale=1)
    return output_path


def generate_pie_chart(
    output_path: str,
    labels: list,
    values: list,
    title: str = "",
    style: dict | None = None,
) -> str:
    """生成饼图"""
    if not HAS_PLOTLY:
        return _fallback_text_image(output_path, f"[饼图] {title}")

    s = _get_style(style)
    colors = [s["primary"], s["secondary"], s["accent"],
              "#10B981", "#8B5CF6", "#EC4899", "#F97316"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors[:len(labels)],
                    line=dict(color=s["background"], width=3)),
        textfont=dict(size=18, color=s["text"]),
        textinfo="label+percent",
        hole=0.35,
    ))
    fig.update_layout(**_plotly_base_layout(s, title))
    fig.write_image(output_path, scale=1)
    return output_path


def generate_comparison_chart(
    output_path: str,
    items: list,          # [{"label": "A", "values": {"指标1": 80, "指标2": 60}}]
    title: str = "",
    style: dict | None = None,
) -> str:
    """生成多维度对比图（分组柱状图）"""
    if not HAS_PLOTLY:
        return _fallback_text_image(output_path, f"[对比图] {title}")

    s = _get_style(style)
    if not items:
        return _fallback_text_image(output_path, title)

    metrics = list(items[0]["values"].keys())
    colors = [s["primary"], s["secondary"], s["accent"], "#10B981"]

    fig = go.Figure()
    for i, metric in enumerate(metrics):
        fig.add_trace(go.Bar(
            name=metric,
            x=[item["label"] for item in items],
            y=[item["values"].get(metric, 0) for item in items],
            marker_color=colors[i % len(colors)],
            text=[str(item["values"].get(metric, 0)) for item in items],
            textposition="outside",
        ))
    fig.update_layout(
        **_plotly_base_layout(s, title),
        barmode="group",
        bargap=0.2,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=16)),
    )
    fig.write_image(output_path, scale=1)
    return output_path


def generate_text_card(
    output_path: str,
    title: str,
    body_lines: list,
    style: dict | None = None,
) -> str:
    """
    生成文字卡片（用于 text_animation 类型的静态底图）
    关键词大字展示，配合后续动画叠加。
    """
    if not HAS_MATPLOTLIB:
        return _fallback_text_image(output_path, title)

    s = _get_style(style)

    def hex2rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

    bg = hex2rgb(s["background"])
    text_color = hex2rgb(s["text"])
    accent_color = hex2rgb(s["accent"])

    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.axis("off")

    # 标题
    ax.text(0.5, 0.75, title, transform=ax.transAxes,
            fontsize=54, fontweight="bold", color=accent_color,
            ha="center", va="center", wrap=True)

    # 正文
    for i, line in enumerate(body_lines[:4]):
        ax.text(0.5, 0.5 - i * 0.12, line, transform=ax.transAxes,
                fontsize=32, color=text_color,
                ha="center", va="center")

    # 装饰线（用 plot 代替 axhline，方便在 axes 坐标系中定位）
    ax.plot([0.2, 0.8], [0.68, 0.68], color=accent_color,
            linewidth=2, transform=ax.transAxes)

    plt.tight_layout(pad=0)
    plt.savefig(output_path, dpi=100, bbox_inches="tight",
                facecolor=bg, edgecolor="none")
    plt.close()
    return output_path


def _fallback_text_image(output_path: str, label: str) -> str:
    """无法生成图表时输出纯文字占位图"""
    if HAS_MATPLOTLIB:
        fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
        fig.patch.set_facecolor("#0F172A")
        ax.axis("off")
        ax.text(0.5, 0.5, f"[图表占位]\n{label}", transform=ax.transAxes,
                fontsize=40, color="#F8FAFC", ha="center", va="center")
        plt.savefig(output_path, dpi=100, bbox_inches="tight",
                    facecolor="#0F172A")
        plt.close()
    return output_path


# ============================================================
# LLM 指令解析 → 自动生成图表
# ============================================================

def generate_from_storyboard_segment(
    segment: dict,
    output_dir: str,
    style_seeds: dict | None = None,
    llm_caller=None,
) -> str | None:
    """
    根据分镜表中的单个 segment，自动生成对应图表。

    优先尝试从 visual_description 中解析出结构化数据，
    如果解析不到就调用 llm_caller 让 LLM 生成数据。

    返回生成的图片路径，失败返回 None。
    """
    visual_type = segment.get("visual_type", "")
    seg_id = segment.get("segment_id", 0)
    title = segment.get("text_overlay") or segment.get("segment_title", "")
    description = segment.get("visual_description", "")
    key_elements = segment.get("key_elements", [])

    output_path = str(Path(output_dir) / f"visual_{seg_id:02d}.png")
    os.makedirs(output_dir, exist_ok=True)

    style = style_seeds

    # 如果有 LLM caller，让 LLM 生成图表数据
    if llm_caller and visual_type in ("data_chart", "comparison", "flow_diagram"):
        chart_data = _ask_llm_for_chart_data(
            llm_caller, visual_type, title, description, key_elements
        )
        if chart_data:
            return _render_from_llm_data(chart_data, output_path, style)

    # 没有 LLM 或解析失败，生成文字卡片占位
    return generate_text_card(
        output_path, title,
        [description[:60] + "..." if len(description) > 60 else description] +
        key_elements[:3],
        style
    )


def _ask_llm_for_chart_data(llm_caller, visual_type: str, title: str,
                             description: str, key_elements: list) -> dict | None:
    """让 LLM 根据分镜描述生成结构化图表数据"""
    type_hints = {
        "data_chart": "bar（柱状图）、line（折线图）或 pie（饼图）",
        "comparison": "comparison（对比图）",
        "flow_diagram": "text_card（流程图暂用文字卡片）",
    }
    prompt = f"""根据以下分镜描述，生成一个图表的数据。

图表类型提示：{type_hints.get(visual_type, 'bar')}
标题：{title}
画面描述：{description}
关键元素：{', '.join(key_elements)}

请输出严格的 JSON，格式如下（选择最合适的 chart_type）：

柱状图格式：
{{"chart_type": "bar", "title": "图表标题", "x_title": "X轴说明", "y_title": "Y轴说明", "labels": ["A", "B", "C"], "values": [100, 200, 150]}}

折线图格式：
{{"chart_type": "line", "title": "图表标题", "x_title": "时间", "y_title": "数值", "x_data": ["2020", "2021", "2022"], "y_series": {{"指标1": [10, 20, 15]}}}}

饼图格式：
{{"chart_type": "pie", "title": "图表标题", "labels": ["A", "B", "C"], "values": [40, 35, 25]}}

对比图格式：
{{"chart_type": "comparison", "title": "对比标题", "items": [{{"label": "选项A", "values": {{"维度1": 80, "维度2": 60}}}}, {{"label": "选项B", "values": {{"维度1": 50, "维度2": 90}}}}]}}

只输出 JSON，不要其他文字。数据要真实合理，符合视频主题。"""

    try:
        result = llm_caller(prompt)
        # 提取 JSON
        match = re.search(r'\{[\s\S]*\}', result)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print(f"[chart_generator] LLM 生成图表数据失败: {e}")
    return None


def _render_from_llm_data(data: dict, output_path: str, style: dict | None) -> str | None:
    """根据 LLM 返回的结构化数据渲染图表"""
    chart_type = data.get("chart_type", "bar")
    title = data.get("title", "")

    try:
        if chart_type == "bar":
            return generate_bar_chart(
                output_path, data["labels"], data["values"],
                title=title,
                x_title=data.get("x_title", ""),
                y_title=data.get("y_title", ""),
                style=style,
            )
        elif chart_type == "line":
            return generate_line_chart(
                output_path,
                x_data=data["x_data"],
                y_series=data["y_series"],
                title=title,
                x_title=data.get("x_title", ""),
                y_title=data.get("y_title", ""),
                style=style,
            )
        elif chart_type == "pie":
            return generate_pie_chart(
                output_path, data["labels"], data["values"],
                title=title, style=style,
            )
        elif chart_type == "comparison":
            return generate_comparison_chart(
                output_path, data["items"],
                title=title, style=style,
            )
        elif chart_type == "text_card":
            return generate_text_card(
                output_path, title,
                data.get("body_lines", []),
                style=style,
            )
    except Exception as e:
        print(f"[chart_generator] 渲染失败: {e}")
    return None
