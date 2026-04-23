# video-ai — 仿「小Lin说」AI 视频自动化生产系统

腾讯云服务器上的视频生产项目，统一放在 `/home/ubuntu/video-ai/` 下。

---

## 目录结构

```
/home/ubuntu/video-ai/
├── pipeline/          # Python 流水线（Streamlit UI + Multi-Agent）
└── remotion-video/    # 主渲染器（React + TypeScript，pipeline 集成）
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
remotion-video/render.py  →  npx remotion render  →  MP4
```

**渲染器**：Remotion（React/Chromium），11 个动画组件 + fitText/measureText 自适应布局。

---

## 子项目说明

- `pipeline/CLAUDE.md`：Python 流水线详情（Agents、审核门、环境变量）
- `remotion-video/CLAUDE.md`：Remotion 组件详情（数据格式、11 个组件、渲染命令）

---

## 当前进度（2026-04-23）

### orchestrator 成片改调 Remotion，废弃 composer.py（compose-to-remotion 分支，merge SHA `28867cb`）
- 删除 `pipeline/tools/composer.py`（ffmpeg concat demuxer + AI 生图幻灯片的老方案，已被 Remotion 11 个动画组件取代）
- `pipeline/orchestrator.py` 的 `node_compose` 重写为内联调 `remotion-video/render.py`：注入 `audio_processed_paths[0]`（退回 `audio_raw_paths[0]`）作为 `audioPath`，`subprocess` 调 render.py 输出到 `{project_dir}/final_video.mp4`
- 同时写 `draft_video_path`（gate_4 UI 现用的 key）和 `final_video_path`（state.py 已定义但从未赋值）
- Remotion 渲染失败抛 `RuntimeError` 带末尾 800 字 stderr
- gate_3 preview（`_run_remotion_render`）保持独立，不共享成片产物（成片 node 要用批准后的 state 重新渲一次）
- gate_4 UI 零改动

### Tavily 搜索验证与 fallback 可见化（tavily-visibility 分支，merge SHA `1ff47b5`）
- `research.py` 的 `_tavily_search` 改返回结构化 `TavilyResult`（status/text/hit_count/reason），fallback 原因在日志里区分 `no_key` / `http_error` / `empty`
- `ResearchAgent.run` 用 `✅ Tavily HIT` / `⚠️ Tavily MISS` 前缀打报告，用户在 UI 左侧日志面板一眼可见
- 新增 `REQUIRE_TAVILY=1` 严格模式开关：任一搜索未命中直接 `RuntimeError`，阻止 LLM 用训练截止 2024 年中的内部知识续跑
- `agents/__init__.py` 的 `BaseAgent._log` 加模块级 `_log_sink` / `set_log_sink()`，Agent 日志同时转发到 Streamlit UI（原本只落 pm2 stdout）
- `app.py` 的 `run_pipeline_thread` 和 `resume_pipeline_thread` 开头注入 `set_log_sink(bridge.post_log)`

### Remotion 组件库改造（remotion-change 分支，merge SHA `8a4cbf7`）
- 引入 `@remotion/layout-utils` 的 fitText/measureText 做精确自适应布局
- 切换到 `@remotion/google-fonts/NotoSansSC`（latin 子集 + 系统 CJK fallback）
- design-system 扩展：springs / easings / shadows / gradients 预设
- 9 个原组件全部重写（去 flex:1 拉伸、去硬编码字号、加渐变发光等视觉升级）
- 新增 2 组件：PieChartAnimated（环形图）、TypewriterText（打字机）
- 新增 KeyPoint `style:"highlight"` 模式（词级擦除扫光）
- 新增 FlowSteps `direction:"circular"` 模式（圆周飞轮排列）
- Transition 升级支持 fade / slide / cut 三种模式
- generate_storyboard.py LLM prompt 同步更新教会 pipeline 选择新组件

### Script Agent 小 Lin 风格深化（script-prompt-v2 分支，merge SHA `2e31654`）
- 新建 `pipeline/knowledge_base/xiaolin/` 素材库（8 万字 docx 转 md + 18 份示例）
- `pipeline/agents/_knowledge.py` 加载器（Path.glob，无 RAG）
- `script.py` 的 OUTLINE/SCRIPT prompt 改占位符动态注入：结构 5/5、技巧 10/10、开头 3/3 全覆盖（原只有 1/5 + 2/10 + 0/3）
- 强制稿末输出"本稿使用的技巧清单"并逐段标注
- Kimi 自审正向化：技巧落地核对 + 多样性 ≥4 + 尾段质量守护
- 用户后续追加小 Lin 原稿只需 drop 进 `/home/ubuntu/upload/小lin说文字稿/` 重跑 convert_docx 再 pm2 restart

### 视频编码兼容性修复（main 直接 commit `2591856`）
- v3/v4 因 png 中间格式导致 `pix_fmt=yuv420p + color_range=unknown`，部分浏览器拒播
- `remotion-video/remotion.config.ts` 回到 `setVideoImageFormat("jpeg")` + `setCrf(18)`
- 输出 `pix_fmt=yuvj420p`（完整色域），和能播的 v2 一致

### 定稿产物
- `remotion-video/out/demo-v5.mp4`（222s / 17.5 MB / yuvj420p / 跨浏览器可播）—— demo 改造最终版
- 旧 demo（v2/v3/v4）可删

### 原有里程碑
- 全流水线跑通（research → storyboard → Remotion render）
- gate_3 TTS 语音合成（SiliconFlow CosyVoice2-0.5B，8 种音色）
- gate_3 触发 Remotion 渲染（后台线程，轮询状态，视频预览）
- VideoScript Agent 从 script_full 提取 display_points 和 narration

---

## Rollback 机制（回撤选项）

每次大改造合并到 main 都用 `git merge --no-ff <branch>`，生成的 merge commit 是回撤锚点：

```bash
# 查合并点
git log --oneline --merges main

# 整体回撤某次改造（连 merge commit 一起撤）
git revert -m 1 <merge-commit-sha>
git push origin main
```

### 可回撤的改造锚点
- **orchestrator 成片改调 Remotion** — merge commit `28867cb`（2 commits 合并入 main）
- **Tavily 搜索验证与 fallback 可见化** — merge commit `1ff47b5`（3 commits 合并入 main）
- **Remotion 组件库改造** — merge commit `8a4cbf7`（11 commits 合并入 main）
- **Script Agent 小 Lin 风格深化** — merge commit `2e31654`（4 commits 合并入 main）
- **视频编码兼容性修复** — 直接 commit `2591856`（单文件改动，用 `git revert 2591856` 回撤即可）

分支本身也保留（`compose-to-remotion`、`tavily-visibility`、`remotion-change`、`script-prompt-v2`），可作 checkout 参照。

### 回撤示例
```bash
# 不满意 Script Agent 改造，回撤它
git revert -m 1 2e31654
git push origin main

# 不满意 Remotion 改造，回撤它
git revert -m 1 8a4cbf7
git push origin main

# 回撤后还想恢复，再 revert 一次那个 revert commit 就行
```

---

## 未来规划

### P3 — Topic Agent 接入 openings 范例
- **问题**：Topic Agent 选角度时**不考虑开头钩子可行性**，导致 Script 后面强凑开头。现状 `knowledge_base/xiaolin/examples/openings/` 只有 Script Agent 在用
- **方案**：在 `pipeline/agents/topic.py` 的 prompt 里注入 `openings/` 三份 md（数据震撼 / 权力感排比 / 共情代入），Topic 选题时反向考虑角度是否匹配某类 hook
- **边界**：**仅 Topic 接 openings**，Storyboard/Research/VideoScript 不接（创作类 vs 信息处理类的边界划清，避免稀释这些 agent 的本职任务）

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

# 2. 开/切功能分支
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
