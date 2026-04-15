"""
系统配置

所有可配置项集中管理。API 密钥通过环境变量读取，不硬编码。
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Tuple


def _load_dotenv():
    """从项目根目录的 .env 文件加载环境变量（不依赖 python-dotenv）"""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if value and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]
            os.environ.setdefault(key, value)

_load_dotenv()


@dataclass
class LLMConfig:
    """单个 LLM 的配置"""
    provider: str           # "deepseek" | "kimi"
    model: str              # 具体模型名
    api_key: str = ""
    base_url: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class SystemConfig:
    """系统总配置"""

    # ---- 项目路径 ----
    projects_root: str = "./projects"
    prompts_dir: str = "./prompts"
    reference_scripts_dir: str = ""   # 小Lin说脚本素材目录

    # ---- LLM 分配 ----
    # 当前版本：DeepSeek + Kimi
    # 后续可替换为 Claude Opus / GPT-4o 等

    research_llm: LLMConfig = field(default_factory=lambda: LLMConfig(
        provider="deepseek",
        model="deepseek-chat",        # DeepSeek：政治话题不被过滤，Research 输入不长不需要128k
        base_url="https://api.deepseek.com",
        max_tokens=8192,
        temperature=0.3,              # 研究阶段要准确，温度低
    ))

    topic_llm: LLMConfig = field(default_factory=lambda: LLMConfig(
        provider="deepseek",
        model="deepseek-chat",        # DeepSeek 推理能力强
        base_url="https://api.deepseek.com",
        max_tokens=4096,
        temperature=0.7,
    ))

    script_llm: LLMConfig = field(default_factory=lambda: LLMConfig(
        provider="deepseek",
        model="deepseek-chat",        # DeepSeek 写初稿：创意写作、口语化表达强
        base_url="https://api.deepseek.com",
        max_tokens=8192,
        temperature=0.7,
    ))

    script_review_llm: LLMConfig = field(default_factory=lambda: LLMConfig(
        provider="kimi",
        model="moonshot-v1-128k",     # Kimi 做自审：长上下文读完整初稿再输出修改版
        base_url="https://api.moonshot.cn/v1",
        max_tokens=8192,
        temperature=0.3,
    ))

    storyboard_llm: LLMConfig = field(default_factory=lambda: LLMConfig(
        provider="kimi",
        model="moonshot-v1-128k",     # Kimi 长上下文，分镜需要读完整脚本
        base_url="https://api.moonshot.cn/v1",
        max_tokens=8192,              # 从4096加大，防止多段落分镜JSON被截断
        temperature=0.5,
    ))

    visual_prompt_llm: LLMConfig = field(default_factory=lambda: LLMConfig(
        provider="deepseek",
        model="deepseek-chat",        # 生成生图 prompt
        base_url="https://api.deepseek.com",
        max_tokens=2048,
        temperature=0.6,
    ))

    # ---- AI 生图配置 ----
    image_gen_provider: str = "siliconflow"   # "siliconflow" | "fal_flux" | "replicate" | "dalle3"
    image_gen_model: str = "Kwai-Kolors/Kolors"  # 硅基流动上的模型名
    image_gen_api_key: str = ""
    image_gen_base_url: str = "https://api.siliconflow.cn/v1"

    # ---- TTS 配置 ----
    tts_base_url: str = "https://api.siliconflow.cn/v1"
    tts_model: str = "fishaudio/fish-speech-1.5"
    tts_default_voice: str = "fishaudio/fish-speech-1.5:alex"
    tts_api_key: str = ""             # 与 image_gen_api_key 共用 SiliconFlow key

    # ---- 音频处理配置 ----
    whisper_model: str = "base"       # whisper 模型大小
    bgm_default_volume: float = 0.15  # BGM 默认音量比例

    # ---- 视频合成配置 ----
    video_resolution: Tuple[int, int] = (1920, 1080)
    video_fps: int = 30
    video_format: str = "mp4"

    # ---- 审核门配置 ----
    max_retries_per_stage: int = 3    # 每个阶段最多重做次数

    def __post_init__(self):
        """从环境变量加载 API 密钥"""
        # DeepSeek
        ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.topic_llm.api_key = ds_key
        self.script_llm.api_key = ds_key
        self.visual_prompt_llm.api_key = ds_key

        # Kimi：长上下文，只用于脚本自审 / Storyboard（不用于 Research，避免政治话题过滤）
        kimi_key = os.environ.get("KIMI_API_KEY", "")
        self.script_review_llm.api_key = kimi_key
        self.storyboard_llm.api_key = kimi_key

        # research_llm 和 script_llm 用 DeepSeek
        self.research_llm.api_key = ds_key
        self.script_llm.api_key = ds_key

        # AI 生图
        self.image_gen_api_key = os.environ.get("IMAGE_GEN_API_KEY", "")

        # TTS：复用 SiliconFlow key
        self.tts_api_key = self.image_gen_api_key


def load_config() -> SystemConfig:
    """加载系统配置（后续可从 YAML/TOML 文件加载）"""
    return SystemConfig()
