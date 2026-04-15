# remotion-video — 科普视频动画组件库

仿「小Lin说」风格，基于 React/Remotion 的动态视频生产方案。
与 `/home/ubuntu/video-ai/pipeline`（Python 流水线）集成，接收 `StoryboardData` JSON。

---

## 目录结构

```
/home/ubuntu/video-ai/remotion-video/
├── src/
│   ├── index.ts                 # 入口，registerRoot
│   ├── Root.tsx                 # Composition 注册 + Demo 分镜
│   ├── VideoComposition.tsx     # 主合成：按组件名分发渲染
│   ├── design-system.ts         # 全局主题 token（颜色/字体/尺寸）
│   ├── types.ts                 # StoryboardData / Segment 类型定义
│   └── components/
│       ├── DataReveal.tsx        # 大数字冲击展示（countUp 动画）
│       ├── BarChartAnimated.tsx  # 柱状图（柱子依次生长）
│       ├── LineChartAnimated.tsx # 折线图（stroke-dashoffset 绘制）
│       ├── CompareTwo.tsx        # 左右对比（两卡片飞入）
│       ├── FlowSteps.tsx         # 流程步骤（节点依次点亮）
│       ├── KeyPoint.tsx          # 金句强调（全屏高亮文字）
│       ├── TitleCard.tsx         # 段落标题转场
│       ├── BulletList.tsx        # 要点列表（逐条滑入）
│       ├── ImageWithOverlay.tsx  # 图片+文字叠层（Ken Burns）
│       ├── Transition.tsx        # FadeIn / FadeOverlay
│       └── index.ts             # COMPONENT_MAP 注册表
├── generate_storyboard.py       # LLM 分镜生成器（→ public/storyboard.json）
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
  component: ComponentName  // 9 种组件之一
  props: Record<string, any>
  durationInSeconds: number
  transition?: 'fade' | 'slide' | 'cut'
  background?: { type: 'solid' | 'gradient' | 'image'; value: string }
  narrationText?: string    // 口播文字（不渲染，仅供 TTS 使用）
}

type ComponentName =
  'DataReveal' | 'BarChartAnimated' | 'LineChartAnimated' |
  'CompareTwo' | 'FlowSteps' | 'KeyPoint' | 'TitleCard' |
  'BulletList' | 'ImageWithOverlay'
```

---

## 组件选择规则

| 场景 | 组件 |
|------|------|
| 单个核心数字 | DataReveal |
| 多个数字横向对比 | BarChartAnimated |
| 时间序列/趋势 | LineChartAnimated |
| A vs B 两者对比 | CompareTwo |
| 流程/步骤/因果链 | FlowSteps |
| 一句话总结/金句 | KeyPoint |
| 段落标题/章节转场 | TitleCard |
| 3~5条并列要点 | BulletList |
| 氛围背景（≤20%） | ImageWithOverlay |

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

- **字体**：中文使用系统已装的 `Noto Sans CJK SC`（fontconfig 自动识别），数字使用 `Noto Sans Mono CJK SC`
- **路径长度**：LineChartAnimated 用纯 JS 欧氏距离计算 path length，避免 DOM `getTotalLength` 在 headless 下失效
- **渲染环境**：`BROWSER_EXECUTABLE_PATH=/usr/bin/chromium-browser`
- **Props 传递**：通过文件传递（`--props=public/_render_props.json`），避免 CLI 长度限制
- **ImageWithOverlay**：图片路径填 `assets/placeholder.jpg`，后续人工替换真实图片
