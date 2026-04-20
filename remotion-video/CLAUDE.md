# remotion-video — 科普视频动画组件库

仿「小Lin说」风格，基于 React/Remotion 的动态视频生产方案。
与 `/home/ubuntu/video-ai/pipeline`（Python 流水线）集成，接收 `StoryboardData` JSON。

---

## 目录结构

```
/home/ubuntu/video-ai/remotion-video/
├── src/
│   ├── index.ts                 # 入口：waitUntilDone 后 registerRoot
│   ├── Root.tsx                 # Composition 注册 + Demo 分镜（16 段）
│   ├── VideoComposition.tsx     # 主合成：按 segment.transition 分发转场
│   ├── design-system.ts         # 全局主题 token + springs/easings/shadows/gradients 预设
│   ├── fonts.ts                 # Noto Sans SC 集中加载（@remotion/google-fonts）
│   ├── types.ts                 # StoryboardData / Segment 类型定义
│   └── components/
│       ├── DataReveal.tsx          # 大数字冲击（easeOut countUp + impact pulse）
│       ├── BarChartAnimated.tsx    # 柱状图（渐变+发光+easeOut 数值）
│       ├── LineChartAnimated.tsx   # 折线图（发光 filter + 点 spring drop-in）
│       ├── PieChartAnimated.tsx    # 环形图（SVG donut + spring 分片）
│       ├── CompareTwo.tsx          # 左右对比（按条目数分档字号）
│       ├── FlowSteps.tsx           # 流程步骤（horizontal / vertical / circular）
│       ├── KeyPoint.tsx            # 金句强调（quote/statement/question/highlight）
│       ├── TitleCard.tsx           # 段落标题（fitText 自适应）
│       ├── BulletList.tsx          # 要点列表（分档字号 + spring 滑入）
│       ├── ImageWithOverlay.tsx    # 图片叠层（Ken Burns + fitText）
│       ├── TypewriterText.tsx      # 打字机（slice 逐字 + 闪烁光标）
│       ├── Transition.tsx          # FadeIn/FadeOverlay + SlideIn/SlideOverlay
│       └── index.ts                # COMPONENT_MAP 注册表
├── generate_storyboard.py       # LLM 分镜生成器（11 组件 prompt）
├── render.py                    # Python 渲染桥（→ MP4）
└── public/
    └── assets/                  # 图片/音频资源
```

---

## 数据格式（StoryboardData）

```typescript
interface StoryboardData {
  title: string
  fps: number           // 30
  width: number         // 1920
  height: number        // 1080
  audioPath?: string    // 相对 public/ 的路径
  segments: Segment[]
}

interface Segment {
  id: number
  component: ComponentName  // 11 种组件之一
  props: Record<string, any>
  durationInSeconds: number
  transition?: 'fade' | 'slide' | 'cut'  // 默认 fade
  background?: { type: 'solid' | 'gradient' | 'image'; value: string }
  narrationText?: string    // 口播文字（不渲染，仅供 TTS 使用）
}

type ComponentName =
  'DataReveal' | 'BarChartAnimated' | 'LineChartAnimated' | 'PieChartAnimated' |
  'CompareTwo' | 'FlowSteps' | 'KeyPoint' | 'TitleCard' |
  'BulletList' | 'ImageWithOverlay' | 'TypewriterText'
```

---

## 组件选择规则

| 场景 | 组件 |
|------|------|
| 单个核心数字 | DataReveal |
| 多个数字横向对比 | BarChartAnimated |
| 时间序列/趋势 | LineChartAnimated |
| 占比/份额（总和≈100%，≤5 项） | PieChartAnimated |
| A vs B 两者对比 | CompareTwo |
| 线性流程 | FlowSteps direction="horizontal" |
| 循环/飞轮流程（≥5 步） | FlowSteps direction="circular" + centerIcon |
| 一句话总结/金句 | KeyPoint style=quote/statement/question |
| 最重一击金句（词级擦除扫光） | KeyPoint style=highlight |
| 段落标题/章节转场 | TitleCard |
| 3~6 条并列要点 | BulletList |
| 氛围背景（≤20%） | ImageWithOverlay |
| 引文/代码/口号逐字展开 | TypewriterText |

---

## 渲染命令

```bash
cd /home/ubuntu/video-ai/remotion-video

# 1. 生成分镜 JSON（从脚本文本）
python generate_storyboard.py --input script.txt
# 输出到 public/storyboard.json

# 2. 渲染视频
BROWSER_EXECUTABLE_PATH=/usr/bin/chromium-browser \
python render.py --script public/storyboard.json --output out/video.mp4

# 3. 渲染单帧截图（调试用）
BROWSER_EXECUTABLE_PATH=/usr/bin/chromium-browser \
  npx remotion still Main out/test.png --frame=30

# 4. 本地预览（开发环境有桌面时）
npx remotion studio
```

---

## pipeline 集成

`/home/ubuntu/video-ai/pipeline/app.py:114` 中触发 Remotion 渲染：
- 调用本目录的 `render.py`
- 传入 `state["video_script_json"]`（StoryboardData JSON 字符串）
- 输出到 `{project_dir}/remotion_output.mp4`

---

## 重要约定

- **字体**：`@remotion/google-fonts/NotoSansSC` latin 子集 + 系统 `Noto Sans CJK SC` fallback；数字用 `Noto Sans Mono CJK SC`
- **字体加载时机**：`src/index.ts` 中 `waitUntilDone().then(registerRoot)`，确保 `@remotion/layout-utils` 的 fitText/measureText 能精确测量
- **自适应布局**：优先用 `fitText` 单行；多列/多条目场景用 `measureText` + 分档 fontSize
- **路径长度**：LineChartAnimated 用纯 JS 欧氏距离计算 path length，避免 DOM `getTotalLength` 在 headless 下失效
- **渲染环境**：`BROWSER_EXECUTABLE_PATH=/usr/bin/chromium-browser`
- **Props 传递**：通过文件传递（`--props=public/_render_props.json`），避免 CLI 长度限制
- **FlowSteps centerIcon**：用 Unicode 符号（如 `↻` `★`）而非 emoji，服务器无 emoji 字体会渲染为方块
- **ImageWithOverlay**：图片路径填 `assets/placeholder.jpg`，后续人工替换真实图片
- **内容分离**：`display_points` 面向观众（显示在视频画面），`key_elements` / `visual_description` 仅供制作系统参考，禁止渲染到视频

---

## 当前进度（2026-04-20）

### 组件库改造（remotion-change 分支）完成
- 9 个原组件全部重写：去 `flex:1` 撑满、去硬编码字号、统一用 theme.springs/easings 预设
- 新增 PieChartAnimated（SVG donut spring 分片）、TypewriterText（逐字+闪烁光标）
- KeyPoint 新增 `style:"highlight"` 词级擦除扫光模式
- FlowSteps 新增 `direction:"circular"` 圆周飞轮排列
- Transition 升级：fade / slide / cut 三种转场模式
- 自适应布局：`@remotion/layout-utils.fitText/measureText` 精确测量
- 字体：切换到 `@remotion/google-fonts/NotoSansSC`
- 视觉升级：渐变、发光、延迟渐现、easeOut 数字滚动、impact pulse、Ken Burns 缩放等

### 之前里程碑
- Phase 1 独立闭环：9 个动画组件 + demo 分镜渲染
- Phase 2 pipeline 集成：storyboard.py / video_script.py / app.py 对接
- 端到端验证：智能驾驶脚本 → DeepSeek 18 段分镜 → Remotion 渲染 MP4
