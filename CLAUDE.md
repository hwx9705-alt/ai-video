# video-ai — 仿「小Lin说」AI 视频自动化生产系统

腾讯云服务器上的视频生产项目，统一放在 `/home/ubuntu/video-ai/` 下。

---

## 目录结构

```
/home/ubuntu/video-ai/
├── pipeline/          # Python 流水线（Streamlit UI + Multi-Agent）
├── remotion-video/    # ⭐ 主渲染器（React + TypeScript，Phase 2 已 pipeline 集成）
└── remotion/          # 旧渲染器（initial commit 后未更新，计划在 remotion-change 分支删除）
```

---

## 访问信息

- **Web UI**：`http://43.162.90.138:8502`（Nginx → 8501）
- **账号**：`admin` / `huweixuan`（Basic Auth）
- **pm2 进程名**：`video-ai`

---

## 整体架构

```
pipeline/agents/
  research.py → topic.py → script.py → storyboard.py → video_script.py
                                                               ↓
                                               VideoScript JSON（数据契约）
                                               含 display_points（面向观众）
                                                               ↓
                              [gate_3 审核] → visual.py（图表+AI生图）
                                                               ↓
remotion/render.py  →  npx remotion render  →  MP4
```

**渲染器**：Remotion（React/Chromium），ffmpeg compose 方案待替换。

---

## 子项目说明

- `pipeline/CLAUDE.md`：Python 流水线详情（Agents、审核门、环境变量）
- `remotion/CLAUDE.md`：Remotion 组件详情（数据格式、渲染命令）

---

## 当前进度（2026-04-08）

### 已完成
- 全流水线可跑通（research → storyboard → Remotion render）
- 7 个 Remotion 组件：TitleCard、TextCard、BarChart、LineChart、ComparisonCard、AIImageCard、Transition
- gate_3 TTS 语音合成（SiliconFlow CosyVoice2-0.5B，8 种音色）
- gate_3 触发 Remotion 渲染（后台线程，轮询状态，视频预览）
- Storyboard Agent 自动生成 VideoScript JSON 基础结构
- **VideoScript Agent**（`pipeline/agents/video_script.py`）：调用 LLM 从 script_full 提取面向观众的 `display_points` 和纯口播 `narration`，合并进 VideoScript JSON
- **TTS 文本清洗**（`extract_narration()`）：过滤 `**[画面提示]**`、`【语气指令】`、`⚠️` 等制作标注，TTS 合成框默认显示清洗后文本
- **Remotion 组件 display_points 改造**：TextCard/TitleCard/AIImageCard 改为优先使用 `display_points`，不再渲染 `visual_description`/`key_elements`
- **orchestrator 改造**：流水线加入 `video_script` 节点（`storyboard → video_script → gate_3`）

---

## 后续计划

### 近期（高优先级）
1. **storyboard prompt 直出 display_points**：让 LLM 在生成分镜时同时产出 `display_points`，减少 VideoScript Agent 单独调用的 LLM 消耗
2. **chart_data 结构化**：VideoScript Agent 或专用工具从脚本中提取真实数值，生成可渲染的 `chart_data`（目前 chart 段落靠 visual agent 手动填充）
3. **Remotion 替代 ffmpeg compose**：orchestrator 成片阶段改为调用 `remotion/render.py`，彻底废弃 `tools/composer.py`

### 中期
- Script Agent prompt 优化（内容深度不足）
- 各 Agent 输入输出日志透明化

---

## 重要约定

- **Python HTTP**：必须用 `requests.Session(trust_env=False)`
- **LLM 调用**：`requests.post` 直连 OpenAI 兼容接口，不用 openai 库
- **Remotion 渲染**：必须设置 `BROWSER_EXECUTABLE_PATH=/usr/bin/chromium-browser`
- **TTS voice 格式**：`FunAudioLLM/CosyVoice2-0.5B:{voice_name}`（必须带模型前缀）
- **内容分离原则**：`display_points` 面向观众（显示在视频画面），`key_elements`/`visual_description` 仅供制作系统参考，**禁止渲染到视频**

---

## Git 工作流

**远端**：`https://github.com/hwx9705-alt/ai-video.git`（origin）

### 日常流程

```bash
# 1. 开工前：main 同步远端
git checkout main
git pull

# 2. 开/切功能分支（如 remotion-change）
git checkout -b <branch-name>        # 首次创建
# 或
git checkout <branch-name>           # 已有分支

# 3. 改代码 → 测试 → 小步 commit
git add <file>
git commit -m "..."

# 4. 推分支（留痕/多端同步）
git push -u origin <branch-name>     # 首次加 -u，之后直接 git push

# 5. 验收通过 → 合回 main
git checkout main
git pull                              # 再次同步，防止远端有新 commit
git merge --no-ff <branch-name>       # 保留分支拓扑
git push origin main

# 6. 分支收尾（可选）
git branch -d <branch-name>                   # 删本地
git push origin --delete <branch-name>        # 删远端
```

### 关键约定

- **不直接在 main 上改代码**，只在 main 上写文档/合并分支
- **pull 只在 main 上做**，避免把远端 main 的提交混进 feature 分支
- **merge 用 `--no-ff`**，保留分支拓扑（想让 main 更干净可改用 `--squash`）
- **先 push 分支再 merge**，分支有备份；merge 后再 push main
- **查分支**：`git branch` 看本地，`git branch -a` 看远端，`git reflog` 看所有 HEAD 历史（误删兜底）

### 当前活跃分支

- `main` — 主线
- `remotion-change` — remotion-video 改造（套用 remotion-video-skill 技巧、删除旧 remotion/）
