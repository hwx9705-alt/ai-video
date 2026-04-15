"""
Visual Producer（视觉素材生产）

混合型模块：LLM 生成数据/prompt，工具执行渲染。
两条技术路线：
  1. 程序化生成：data_chart / comparison → Plotly
                 text_animation → Matplotlib 文字卡片
  2. AI 生图：ai_image → fal.ai Flux / Replicate / DALL-E 3
  3. flow_diagram：LLM 生成 Mermaid 代码（后续集成 Mermaid CLI）
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from agents import BaseAgent
from state import ProjectState, Stage, StageStatus


# 懒加载工具，避免 import 失败阻塞整个系统
def _get_chart_generator():
    try:
        from tools.chart_generator import generate_from_storyboard_segment
        return generate_from_storyboard_segment
    except ImportError as e:
        print(f"[visual_producer] chart_generator 不可用: {e}")
        return None


def _get_image_generator():
    try:
        from tools.image_generator import generate_image, build_image_prompt
        return generate_image, build_image_prompt
    except ImportError as e:
        print(f"[visual_producer] image_generator 不可用: {e}")
        return None, None


# LLM Prompt：生成 AI 生图的英文 prompt
IMAGE_PROMPT_SYSTEM = """\
你是一个专业的 AI 生图 prompt 工程师。
根据视频分镜描述，生成适合 Flux/DALL-E 的英文生图 prompt。

要求：
- 纯英文，不超过 300 词
- 风格词自动拼接到末尾
- 重点描述画面构图、光线、氛围、主体
- 避免文字/Logo，因为 AI 生图文字效果差
- 财经科普风格：专业、有质感、视觉冲击力强

只输出 prompt，不要任何解释。
"""


class VisualProducer(BaseAgent):
    """
    Visual Producer：根据分镜表逐段生产视觉素材。
    data_chart / comparison / text_animation → 程序化生成
    ai_image → AI 生图 API
    flow_diagram → 暂用文字卡片（后续集成 Mermaid）
    mixed → 优先程序化，失败降级到文字卡片
    """
    name = "visual_producer"

    def run(self, state: ProjectState) -> ProjectState:
        self._log("开始视觉素材生产")

        storyboard_raw = state.get("storyboard", "")
        if not storyboard_raw:
            state["error_message"] = "分镜表为空，无法生产视觉素材"
            return state

        # 解析分镜表
        storyboard_list = self._parse_storyboard(storyboard_raw)
        if not storyboard_list:
            self._log("⚠️ 分镜表解析失败，跳过视觉生产")
            state["visual_paths"] = []
            state["last_agent"] = self.name
            return state

        # 解析风格种子
        style_seeds = self._parse_style_seeds(state.get("style_seeds", ""))
        style_keywords = style_seeds.get("ai_image_style_keywords", "") if style_seeds else ""

        # 输出目录
        project_dir = state.get("project_dir", "./projects/unknown")
        visual_dir = str(Path(project_dir) / "visuals")
        os.makedirs(visual_dir, exist_ok=True)

        # 加载工具
        chart_gen = _get_chart_generator()
        image_gen, build_prompt = _get_image_generator()

        # 从 config 读 AI 生图配置
        from config import load_config
        cfg = load_config()
        img_provider = cfg.image_gen_provider
        img_api_key = cfg.image_gen_api_key
        img_model = getattr(cfg, "image_gen_model", "black-forest-labs/FLUX.1-pro")
        img_base_url = getattr(cfg, "image_gen_base_url", "")

        visual_paths = []
        self._log(f"共 {len(storyboard_list)} 个分镜段，开始逐段生产...")

        for seg in storyboard_list:
            seg_id = seg.get("segment_id", 0)
            visual_type = seg.get("visual_type", "text_animation")
            title = seg.get("segment_title", f"段落{seg_id}")
            self._log(f"  [{seg_id}] {title} → {visual_type}")

            output_path = str(Path(visual_dir) / f"visual_{seg_id:02d}.png")

            try:
                path = self._produce_segment(
                    seg=seg,
                    visual_type=visual_type,
                    output_path=output_path,
                    style_seeds=style_seeds,
                    style_keywords=style_keywords,
                    chart_gen=chart_gen,
                    image_gen=image_gen,
                    build_prompt=build_prompt,
                    img_provider=img_provider,
                    img_api_key=img_api_key,
                    img_model=img_model,
                    img_base_url=img_base_url,
                )
                if path:
                    visual_paths.append(path)
                    self._log(f"    ✓ 已生成: {Path(path).name}")
                else:
                    self._log(f"    ⚠️ 生成失败，跳过")
            except Exception as e:
                self._log(f"    ❌ 出错: {e}")

        state["visual_paths"] = visual_paths
        state["last_agent"] = self.name

        status = dict(state.get("stage_status", {}))
        status[Stage.VISUAL.value] = StageStatus.COMPLETED.value
        state["stage_status"] = status

        self._log(f"视觉素材生产完成，共 {len(visual_paths)}/{len(storyboard_list)} 段")
        return state

    def _produce_segment(
        self, seg, visual_type, output_path, style_seeds, style_keywords,
        chart_gen, image_gen, build_prompt, img_provider, img_api_key,
        img_model="", img_base_url=""
    ):
        """根据 visual_type 调用对应工具"""

        # --- 程序化图表 ---
        if visual_type in ("data_chart", "comparison", "mixed") and chart_gen:
            return chart_gen(
                segment=seg,
                output_dir=str(Path(output_path).parent),
                style_seeds=style_seeds,
                llm_caller=lambda p: self.call_llm("你是图表数据生成专家，只输出JSON。", p),
            )

        # --- 文字卡片（text_animation / flow_diagram 降级）---
        if visual_type in ("text_animation", "flow_diagram"):
            if chart_gen:
                return chart_gen(
                    segment=seg,
                    output_dir=str(Path(output_path).parent),
                    style_seeds=style_seeds,
                    llm_caller=None,  # 文字卡片不需要 LLM
                )

        # --- AI 生图 ---
        if visual_type == "ai_image" and image_gen:
            # 用 LLM 将中文描述转为英文 prompt
            description = seg.get("visual_description", seg.get("segment_title", ""))
            if img_api_key:
                eng_prompt = self.call_llm(
                    IMAGE_PROMPT_SYSTEM,
                    f"分镜描述：{description}\n风格关键词：{style_keywords}",
                    temperature=0.7,
                    max_tokens=300,
                )
            else:
                eng_prompt = build_prompt(description, style_keywords) if build_prompt else description

            return image_gen(
                prompt=eng_prompt,
                output_path=output_path,
                style_keywords=style_keywords,
                provider=img_provider,
                api_key=img_api_key,
            )  # model/base_url 由 image_generator 内部从 config 读取

        # --- 兜底：文字卡片 ---
        if chart_gen:
            return chart_gen(
                segment=seg,
                output_dir=str(Path(output_path).parent),
                style_seeds=style_seeds,
                llm_caller=None,
            )

        return None

    @staticmethod
    def _parse_storyboard(raw: str) -> list:
        """从 storyboard 原始文本中提取分镜数组"""
        import re
        # 找 markdown 代码块中的 JSON
        blocks = re.findall(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', raw)
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

    @staticmethod
    def _parse_style_seeds(raw: str) -> dict | None:
        """解析 style_seeds JSON"""
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None
