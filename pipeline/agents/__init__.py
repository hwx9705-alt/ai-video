"""
Agent 基类

所有 LLM Agent 继承此类。提供：
1. 统一的 LLM 调用接口（支持 DeepSeek / Kimi 的 OpenAI 兼容 API）
2. 统一的输入/输出日志
3. 重试逻辑
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import json
import time
import traceback

import requests as _requests

# 创建一个绕过系统代理的 Session（Windows 系统代理可能不可用）
_session = _requests.Session()
_session.trust_env = False

from config import LLMConfig
from state import ProjectState

# 可选的日志转发回调：Streamlit 侧在启动流水线线程前调用 set_log_sink(bridge.post_log)，
# 让 Agent 的 _log() 同时流进 UI 日志面板（不替代 print，只是复制一份）
_log_sink = None

def set_log_sink(sink):
    """注册日志 sink。签名 callable(str) -> None。传 None 可清除。"""
    global _log_sink
    _log_sink = sink


# DeepSeek 作为全局降级备用配置（内容过滤时自动切换）
_DEEPSEEK_FALLBACK: "LLMConfig | None" = None

def _get_deepseek_fallback() -> "LLMConfig | None":
    global _DEEPSEEK_FALLBACK
    if _DEEPSEEK_FALLBACK is None:
        import os
        key = os.environ.get("DEEPSEEK_API_KEY", "")
        if key:
            _DEEPSEEK_FALLBACK = LLMConfig(
                provider="deepseek",
                model="deepseek-chat",
                api_key=key,
                base_url="https://api.deepseek.com",
                max_tokens=8192,
                temperature=0.7,
            )
    return _DEEPSEEK_FALLBACK


def _call_once(config: LLMConfig, system_prompt: str, user_prompt: str,
               temperature: float, tokens: int) -> str:
    """发一次 HTTP 请求，返回内容字符串。失败时抛异常。"""
    url = f"{config.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": tokens,
    }
    resp = _session.post(url, headers=headers, json=payload, timeout=180)

    # 先检查是否内容过滤（400 content_filter），单独抛出以便上层识别
    if resp.status_code == 400:
        try:
            err = resp.json().get("error", {})
        except Exception:
            err = {}
        if err.get("type") == "content_filter" or "high risk" in err.get("message", ""):
            raise _ContentFilterError(f"内容过滤：{err.get('message', '')}")
        # 其他 400
        raise Exception(f"HTTP 400: {resp.text[:300]}")

    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"] or ""


class _ContentFilterError(Exception):
    """Kimi 等平台触发内容安全过滤时抛出，区别于普通网络错误"""
    pass


class BaseAgent(ABC):
    """所有 LLM Agent 的基类"""

    name: str = "base_agent"

    def __init__(self, llm_config: LLMConfig):
        self.llm_config = llm_config

    def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        调用 LLM 并返回文本响应。
        - 网络错误：重试 5 次，间隔 2/10/30/60s
        - 内容过滤（Kimi content_filter）：立即切换 DeepSeek 重试，不等待
        """
        config = self.llm_config
        if not config.api_key:
            self._log("⚠️ API key 未设置，返回占位响应")
            return f"[{self.name} STUB] API key 未设置。"

        # 在 system prompt 末尾注入当前日期（放末尾避免稀释开头指令的权重）
        today = time.strftime("%Y年%m月%d日")
        system_prompt = system_prompt + f"\n\n【当前日期：{today}，请以此为准判断时效性，不要使用训练数据中的过期日期。】"

        temp = temperature if temperature is not None else config.temperature
        tokens = max_tokens or config.max_tokens

        # 重试间隔：2s, 10s, 30s, 60s
        retry_delays = [2, 10, 30, 60]
        max_attempts = len(retry_delays) + 1

        for attempt in range(max_attempts):
            try:
                self._log(f"调用 {config.provider}/{config.model} (尝试 {attempt+1}/{max_attempts})...")
                content = _call_once(config, system_prompt, user_prompt, temp, tokens)
                self._log(f"LLM 返回 {len(content)} 字符")
                return content

            except _ContentFilterError as e:
                # 内容过滤：不重试当前模型，立即降级到 DeepSeek
                self._log(f"⚠️ {config.provider} 触发内容过滤，尝试切换 DeepSeek 重试...")
                fallback = _get_deepseek_fallback()
                if fallback and fallback.provider != config.provider:
                    try:
                        fb_temp = temp
                        fb_tokens = tokens
                        content = _call_once(fallback, system_prompt, user_prompt, fb_temp, fb_tokens)
                        self._log(f"DeepSeek 降级成功，返回 {len(content)} 字符")
                        return content
                    except Exception as fe:
                        self._log(f"DeepSeek 降级也失败：{fe}")
                raise RuntimeError(f"[{self.name}] 内容过滤且无可用降级模型: {e}") from e

            except Exception as e:
                self._log(f"LLM 调用失败 (尝试 {attempt+1}/{max_attempts}): {e}")
                if attempt < len(retry_delays):
                    wait = retry_delays[attempt]
                    self._log(f"等待 {wait}s 后重试...")
                    time.sleep(wait)
                else:
                    raise RuntimeError(
                        f"[{self.name}] LLM 调用 {max_attempts} 次均失败: {e}"
                    ) from e

        return ""

    @abstractmethod
    def run(self, state: ProjectState) -> ProjectState:
        """
        执行 Agent 逻辑，返回更新后的 State。
        每个子类必须实现此方法。
        """
        ...

    def _log(self, message: str):
        """简单日志：print 到 stdout（pm2 捕获），并复制一份给 UI sink"""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] [{self.name}] {message}"
        print(line)
        if _log_sink is not None:
            try:
                _log_sink(line)
            except Exception:
                pass
