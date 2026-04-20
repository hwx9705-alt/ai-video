# AI 科普视频自动化生产系统（Python 流水线）

仿「小Lin说」风格的 B 站财经科普视频自动化生产系统。
Streamlit Web UI，多 Agent 流水线，每个节点有人工审核门。

主渲染器：`/home/ubuntu/video-ai/remotion-video`（Remotion 动态视频组件库，11 个动画组件）

---

## 访问信息

- 地址：`http://43.162.90.138:8502`
- 账号：`admin` / 密码：`huweixuan`（Nginx Basic Auth）

---

## 服务器管理

```bash
pm2 status
pm2 restart video-ai
pm2 logs video-ai --lines 50

# 手动启动（调试用）
cd /home/ubuntu/video-ai/pipeline
source venv/bin/activate
streamlit run app.py --server.port 8501 --server.headless true
```

---

## 项目结构

```
/home/ubuntu/video-ai/pipeline/
├── app.py               # Streamlit Web UI（主入口）
├── config.py            # 全局配置，从 .env 读取 API key
├── state.py             # ProjectState TypedDict
├── orchestrator.py      # MiniStateGraph 流水线编排
├── mini_graph.py        # 轻量 Graph/Checkpointer（替代 langgraph）
├── project_manager.py   # 项目目录管理
├── .env                 # API 密钥
├── venv/                # Python 虚拟环境
├── projects/            # 生成的项目文件
│   └── _checkpoints/    # 断点续跑检查点（JSON）
├── agents/
│   ├── __init__.py      # BaseAgent（requests 直连 LLM）
│   ├── research.py      # Research（DeepSeek + Tavily）
│   ├── topic.py         # Topic（选题策划）
│   ├── script.py        # Script（大纲→脚本→AI自审，Kimi）
│   ├── storyboard.py    # Storyboard（分镜+视觉风格+VideoScript JSON 基础结构）
│   ├── video_script.py  # VideoScript（LLM 提取 display_points + narration，供 Remotion 渲染）
│   └── visual.py        # Visual（图表+AI生图）
└── tools/
    ├── chart_generator.py   # Plotly/Matplotlib 图表
    ├── image_generator.py   # AI 生图（SiliconFlow Kolors）
    ├── audio_processor.py   # ffmpeg 音频处理（标准化+BGM混音）
    ├── tts_generator.py     # AI 语音合成（SiliconFlow CosyVoice2）含 extract_narration()
    ├── composer.py          # ffmpeg 视频合成（待被 Remotion 替代）
    └── bgm_finder.py        # BGM 搜索
```

---

## 流水线阶段

```
① Research      知识框架（DeepSeek + Tavily）
② Topic         选题策划
③ Script        大纲→脚本→AI自审（Kimi moonshot-v1-128k）
④ Storyboard    分镜表 + 视觉风格 + VideoScript JSON 基础结构
⑤ VideoScript   LLM 提取面向观众的 display_points + 纯口播 narration
    ↓ [gate_3 审核]
⑥ Visual        程序化图表 + AI生图（SiliconFlow Kolors）
⑦ Audio         ffmpeg 音量标准化 + BGM混音（或 TTS 合成）
⑧ Compose       ffmpeg → MP4（待改为 Remotion render）
```

每阶段有审核门（通过/局部修改/重做）。

---

## 审核门功能

| 审核门 | 位置 | 主要功能 |
|-------|------|---------|
| gate_1 | Research→Script | 选题确认 |
| gate_2a | Script Outline | 大纲确认 |
| gate_2b | Script Full | 完整脚本确认 |
| gate_3 | VideoScript→Visual | 分镜确认 + 配音设置（上传/TTS）+ **触发 Remotion 动态预览** |
| gate_4 | Compose | 成片确认 |

### gate_3 配音方式
- **上传录音**：支持 mp3/wav/m4a/aac
- **AI 语音合成**：SiliconFlow CosyVoice2-0.5B，8 种音色（4男4女），可调语速
  - TTS 默认文本已自动调用 `extract_narration()` 清洗，过滤 `**[画面提示]**`/`【语气指令】`/`⚠️` 等标注
  - voice 格式：`FunAudioLLM/CosyVoice2-0.5B:{voice_name}`
  - 有效 voice_name：`claire`、`anna`、`bella`、`diana`（女）、`alex`、`benjamin`、`charles`、`david`（男）

### gate_3 Remotion 动态预览
- storyboard + video_script agent 产出含 `display_points` 的 `video_script_json`（存入 state）
- gate_3 点击「触发 Remotion 渲染」→ 后台线程执行 render.py → 轮询状态（每3秒）→ 完成后展示视频
- 输出路径：`{project_dir}/remotion_output.mp4`
- 渲染时间约 2-5 分钟

---

## 当前进度（2026-04-08）

### 已完成
- 全流水线跑通，首个项目「美联储加息」已生成 draft_video.mp4
- Streamlit UI 可正常访问
- gate_3 TTS 语音合成（CosyVoice2，8 种音色）
- gate_3 Remotion 动态预览触发
- Storyboard Agent 自动生成 VideoScript JSON 基础结构
- **VideoScript Agent**（`agents/video_script.py`）：LLM 从 script_full 提取面向观众的 `display_points` 和纯口播 `narration`
- **TTS 文本清洗**：`tools/tts_generator.py` 新增 `extract_narration()`，TTS 合成框默认使用清洗后文本
- **Remotion 组件修复**：TextCard/TitleCard/AIImageCard 改为优先使用 `display_points`，不再渲染 `visual_description`/`key_elements`
- **orchestrator 改造**：插入 `video_script` 节点（`storyboard → video_script → gate_3`）

### 待优化（中低优先级）
- Script Agent prompt 优化（内容深度不足）
- 各 Agent 输入输出透明化（日志/可查询记录）
- AI 生图错误处理改善（现在静默跳过）
- Remotion 替代 ffmpeg compose（成片阶段改调 render.py）

---

## 环境变量（`.env`）

```
DEEPSEEK_API_KEY=sk-...
KIMI_API_KEY=sk-...
IMAGE_GEN_API_KEY=sk-...    # SiliconFlow，生图和 TTS 共用
TAVILY_API_KEY=tvly-dev-...
```

---

## 重要约定

- **HTTP**：必须用 `requests.Session(trust_env=False)`，禁止默认 session
- **LLM**：用 `requests.post` 直连 OpenAI 兼容接口，不用 openai 库
- **Streamlit**：流水线在 daemon 线程，`PipelineBridge` 通信；不在回调里调 `st.rerun()`
- **Nginx**：8502（外部）→ 8501（Streamlit 内部）
- **字体**：`chart_generator.py` 中 CJK 字体列表已包含 Noto 系列，勿删除
- **TTS voice 格式**：`FunAudioLLM/CosyVoice2-0.5B:{voice_name}`，必须带模型前缀
- **Remotion 渲染**：需设置 `BROWSER_EXECUTABLE_PATH=/usr/bin/chromium-browser`
- **内容分离**：`display_points` 面向观众（渲染到视频），`key_elements`/`visual_description` 仅制作系统参考，**禁止渲染到视频**
