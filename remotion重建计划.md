# Plan: Remotion 视频组件库重建

## Context

当前 `/home/ubuntu/video-ai/remotion/` 的渲染效果很差——基本上是静态文字卡+简单柱状图的幻灯片。用户与 Claude 讨论后制定了新方案（`claude_code_remotion_prompt.md`），要求：
1. 新建一个 Remotion 项目（`remotion-video/`），包含 9 个动画组件
2. 新的数据契约（`StoryboardData` 格式，按组件名分发而非 visual_type）
3. LLM 分镜生成器（Python 脚本，调 DeepSeek 生成分镜 JSON）
4. 先跑通独立闭环，再接回主流水线

分两个 Phase 执行：Phase 1 独立闭环，Phase 2 接回 pipeline。

---

## Phase 1: 独立闭环（新 Remotion 项目）

### Step 1: 初始化项目

```bash
cd /home/ubuntu/video-ai
npx create-video@latest remotion-video --blank
cd remotion-video
npm install
npm install @remotion/google-fonts  # JetBrains Mono 字体加载
```

清理 Tailwind 依赖（旧项目用了但实际全用 inline styles，不需要）。

验证：`npx remotion render` 基础 composition 能跑通。

### Step 2: 安装 Remotion AI Skills

```bash
cd /home/ubuntu/video-ai/remotion-video
npx skills add remotion-dev/skills
```

如果失败不阻塞——这是开发辅助工具，不影响运行时。

### Step 3: 设计系统

**创建** `src/design-system.ts`

```typescript
export const theme = {
  colors: {
    background: '#0f0f1a',
    surface: '#1a1a2e',
    primary: '#4fc3f7',
    secondary: '#81c784',
    accent: '#ffb74d',
    danger: '#ef5350',
    text: '#ffffff',
    textSecondary: '#b0b0b0',
    textMuted: '#666666',
  },
  fonts: {
    title: "'Noto Sans CJK SC', 'Noto Sans SC', sans-serif",
    body: "'Noto Sans CJK SC', 'Noto Sans SC', sans-serif",
    data: "'JetBrains Mono', 'Noto Sans Mono CJK SC', monospace",
  },
  fontSize: { hero: 72, title: 48, subtitle: 32, body: 24, label: 18 },
};
```

**字体策略**：
- 中文：系统已装 `Noto Sans CJK SC` (Regular/Bold)，Chromium headless 通过 fontconfig 自动识别
- 数字等宽：用 `@remotion/google-fonts` 加载 JetBrains Mono，fallback 到系统已装的 `Noto Sans Mono CJK SC`
- 在 `Root.tsx` 中调用 `loadFont()` 加载 JetBrains Mono

### Step 4: 创建 9 个组件

**目录** `src/components/`，每个组件用 Remotion 的 `spring()` + `interpolate()` 做动画：

| # | 文件 | Props 接口 | 核心动画 |
|---|------|-----------|---------|
| 1 | `DataReveal.tsx` | `{number, prefix?, suffix?, subtitle, highlightColor?, countUp?}` | 数字从 0 countUp 到目标值（interpolate），副标题延迟淡入 |
| 2 | `BarChartAnimated.tsx` | `{title, data: {label,value,color?}[], unit?, highlightIndex?}` | 柱子从底到顶 spring 生长，每根错帧 8 帧 |
| 3 | `LineChartAnimated.tsx` | `{title, data: {x,y}[], unit?, annotations?}` | SVG stroke-dashoffset 从左到右绘制，标注在线到达时弹出 |
| 4 | `CompareTwo.tsx` | `{title, left: {label,points[],color?}, right: ..., vsText?}` | 两卡片从左右飞入，VS 中央出现，要点逐条淡入 |
| 5 | `FlowSteps.tsx` | `{title, steps: {label,description?}[], direction?}` | 节点依次点亮（muted→primary），箭头 stroke-dashoffset 连线 |
| 6 | `KeyPoint.tsx` | `{text, emphasis?: string[], style?: 'quote'\|'statement'\|'question'}` | 全屏居中文字，emphasis 词高亮，按 style 不同动画 |
| 7 | `TitleCard.tsx` | `{title, subtitle?, sectionNumber?}` | 编号先出，标题 spring 缩放弹出，副标题从下滑入 |
| 8 | `BulletList.tsx` | `{title, items: {text}[]}` | 标题先入，每条从右滑入（错帧 12 帧），bullet 图标 pop |
| 9 | `ImageWithOverlay.tsx` | `{imageSrc, overlayOpacity?, title, subtitle?}` | Ken Burns 慢缩放，暗色遮罩，文字底部滑入 |

**可复用的已有模式**（来自旧项目）：
- `LineChart.tsx:30-38` — 纯 JS 欧氏距离计算 path length（避免 DOM getTotalLength），直接搬到 `LineChartAnimated`
- `TextCard.tsx:19-34` — `useFadeSlideIn` hook（spring + opacity + translateY），可提取为共用 hook
- `Transition.tsx` — FadeIn/FadeOverlay 组件，直接复制

**验证**：每写完一个组件，在 Root.tsx 加测试 Composition，`npx remotion still` 渲染单帧检查。

### Step 5: 组合层

**创建** `src/types.ts`
```typescript
type ComponentName = 'DataReveal' | 'BarChartAnimated' | 'LineChartAnimated' |
  'CompareTwo' | 'FlowSteps' | 'KeyPoint' | 'TitleCard' | 'BulletList' | 'ImageWithOverlay';

interface Segment {
  id: number;
  component: ComponentName;
  props: Record<string, any>;
  durationInSeconds: number;
  transition?: 'fade' | 'slide' | 'cut';
  background?: { type: 'solid' | 'gradient' | 'image'; value: string };
  narrationText?: string;
}

interface StoryboardData {
  title: string;
  totalDurationInSeconds: number;
  fps: number;
  width: number;
  height: number;
  segments: Segment[];
}
```

**创建** `src/components/index.ts` — 导出 `COMPONENT_MAP: Record<ComponentName, React.FC<any>>`

**创建** `src/VideoComposition.tsx`
- 接收 `StoryboardData` 作为 props
- 用 `COMPONENT_MAP[segment.component]` 分发渲染
- 用 `Series` 序列化，段间 fade 转场（复用旧项目的 FadeIn/FadeOverlay 模式）
- 每段 AbsoluteFill 应用 background（solid/gradient/image）

**修改** `src/Root.tsx`
- 注册 Composition id `"Main"`
- 内置一个 hardcoded 的 demo StoryboardData（覆盖全部 9 种组件）
- 调用 `@remotion/google-fonts` 的 `loadFont()` 加载 JetBrains Mono

**验证**：完整 demo 视频渲染，全部 9 种组件出现且动画正常。

### Step 6: LLM 分镜生成器

**创建** `generate_storyboard.py`

- 读取脚本文本（命令行参数 `--input`）
- 构造 system prompt：9 个组件的 props 接口 + 10 条组件选择规则 + 输出 JSON 格式要求
- 调用 DeepSeek API：复用 pipeline 的 `_call_once` 模式（`requests.Session(trust_env=False)`, POST 到 `/chat/completions`）
- 从 `/home/ubuntu/video-ai/pipeline/.env` 读取 `DEEPSEEK_API_KEY`
- 解析 JSON 响应（处理 markdown 包裹、提取 JSON 块）
- 校验：检查每段 `component` 在允许集合内
- 输出到 `public/storyboard.json`

**测试数据**：从 checkpoint 提取智能驾驶的 `script_full`（4933 字）作为输入。

### Step 7: 渲染桥

**创建** `render.py`

复用旧 `remotion/render.py` 的模式，适配新格式：
- 读取 StoryboardData JSON
- 复制 ImageWithOverlay 的 imageSrc 引用的图片到 `public/assets/`
- 写 `public/storyboard.json`
- 计算总帧数 = Σ(segment.durationInSeconds × fps)
- 调用 `npx remotion render Main <output> --props <json> --concurrency 2`
- 环境变量 `BROWSER_EXECUTABLE_PATH=/usr/bin/chromium-browser`

### Step 8: 端到端验证

```bash
# 提取测试脚本
python3 -c "..." > test_script.txt

# 生成分镜
python generate_storyboard.py --input test_script.txt

# 渲染视频
python render.py --script public/storyboard.json --output out/video.mp4
```

验证标准：
1. 视频风格统一（深色背景，青/绿/金配色）
2. 数据有动画（数字跳动、图表生长）
3. 画面切换有节奏感
4. 开头有冲击力
5. 看起来像"信息动画"而非 PPT

---

## Phase 2: 接回主流水线（Phase 1 验证通过后）

### Step 9: 改造 StoryboardAgent

**修改** `/home/ubuntu/video-ai/pipeline/agents/storyboard.py`
- SYSTEM_PROMPT 改为输出新的组件名（DataReveal、BarChartAnimated...）+ props 接口
- `_build_video_script()` 输出 `StoryboardData` 格式
- `_parse_storyboard_output()` 适配新格式

### Step 10: 适配 VideoScriptAgent

**修改** `/home/ubuntu/video-ai/pipeline/agents/video_script.py`
- 角色简化为：从 script_full 提取每段 `narrationText`
- 不再需要 `display_points`（新格式中组件 props 直接包含观众内容）

### Step 11: 更新渲染触发

**修改** `/home/ubuntu/video-ai/pipeline/app.py`（第 114 行）
- 路径从 `remotion/render.py` → `remotion-video/render.py`
- JSON 格式已是 StoryboardData，无需其他改动

### Step 12: 更新文档

- 更新 `pipeline/CLAUDE.md`、`video-ai/CLAUDE.md` 中的渲染器路径和数据格式
- 创建 `remotion-video/CLAUDE.md`

---

## 文件清单

### Phase 1 — 新建（`/home/ubuntu/video-ai/remotion-video/`）
| 文件 | 说明 |
|------|------|
| `src/design-system.ts` | 全局主题 token |
| `src/types.ts` | StoryboardData / Segment 类型 |
| `src/components/DataReveal.tsx` | 大数字展示 |
| `src/components/BarChartAnimated.tsx` | 柱状图 |
| `src/components/LineChartAnimated.tsx` | 折线图 |
| `src/components/CompareTwo.tsx` | 左右对比 |
| `src/components/FlowSteps.tsx` | 流程步骤 |
| `src/components/KeyPoint.tsx` | 金句强调 |
| `src/components/TitleCard.tsx` | 段落标题 |
| `src/components/BulletList.tsx` | 要点列表 |
| `src/components/ImageWithOverlay.tsx` | 图片+文字叠层 |
| `src/components/Transition.tsx` | FadeIn/FadeOverlay（复制自旧项目） |
| `src/components/index.ts` | 组件注册表 |
| `src/VideoComposition.tsx` | 主合成 |
| `src/Root.tsx` | Composition 注册 + demo 数据 |
| `generate_storyboard.py` | LLM 分镜生成 |
| `render.py` | Python 渲染桥 |

### Phase 2 — 修改
| 文件 | 改动 |
|------|------|
| `pipeline/agents/storyboard.py` | SYSTEM_PROMPT + 输出格式 |
| `pipeline/agents/video_script.py` | 简化为 narrationText 提取 |
| `pipeline/app.py:114` | 渲染器路径 |
| 多个 CLAUDE.md | 文档更新 |

---

## 风险

| 风险 | 应对 |
|------|------|
| `npx create-video --blank` 交互式挂起 | 用 `yes "" \|` 管道或手动创建项目结构 |
| JetBrains Mono 加载失败 | fallback 到系统已有的 `Noto Sans Mono CJK SC` |
| DeepSeek 生成的 JSON 格式错误 | JSON 修复：剥 markdown fence、regex 提取、校验组件名 |
| `--props` CLI 长度超限 | 改用文件传递：`--props=public/storyboard.json` |
| `npx skills add` 不可用 | 非运行时依赖，跳过不影响 |
