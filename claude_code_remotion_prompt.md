# Claude Code 任务指令：Remotion 视频组件库（集成官方 AI 工具）

## 目标

搭建一个 Remotion 视频项目，包含一套科普视频组件库，用一篇现有脚本生成分镜 JSON，渲染出一段完整的视频。先跑通这个闭环，再接回主流水线。

## ⚠️ 第零步：安装 Remotion 官方 AI 工具（在写任何代码之前）

Remotion 官方提供了专门给 AI Agent 用的工具链，必须先装好：

### A. 安装 Agent Skills
```bash
npx skills add remotion-dev/skills
```
这会在项目中安装 28 个模块化的 SKILL.md 规则文件，涵盖：
- animations.md - 动画基础（interpolate, spring, 时序控制）
- charts.md - 图表和数据可视化模式
- sequencing.md - Sequence, Series, TransitionSeries 的正确用法
- fonts.md - 字体加载（中文字体尤其重要）
- audio.md - 音频处理
- assets.md - 图片、视频、静态资源引入
- 等等

**在写任何 Remotion 代码之前，先读对应的 rule 文件。** 比如要写图表组件就先读 rules/charts.md，要写动画就先读 rules/animations.md。

### B. 安装 MCP Server（文档查询）
在 Claude Code 配置中添加：
```json
{
  "mcpServers": {
    "remotion-documentation": {
      "command": "npx",
      "args": ["@remotion/mcp@latest"]
    }
  }
}
```
这样你遇到不确定的 Remotion API 时可以直接查官方文档。

### C. 参考 System Prompt
Remotion 的完整 LLM 教学 prompt 在：https://www.remotion.dev/llms.txt
任何 Remotion 文档页面的 URL 后面加 .md 就能获取 markdown 版本（如 remotion.dev/docs/player.md）。
需要查阅具体 API 时直接 fetch 对应的 .md URL。

## 核心理念

这是纯画面流科普视频（参考B站UP主"小Lin说"），没有真人出镜。视频的视觉主体是"信息动画"——数字跳动、图表生长、框架展开、文字弹出。AI 生图只做背景点缀。

画面类型分布：
- 数据动画（数字、图表）：50-60%
- 结构/关系图（流程、对比、时间线）：20-30%
- 氛围背景 + 文字叠加：10-20%

## 第一步：初始化 Remotion 项目

```bash
npx create-video@latest remotion-video --blank
cd remotion-video
npm install
npx skills add remotion-dev/skills
```

## 第二步：建立设计系统

创建 `src/design-system.ts`，定义全局设计 token。所有组件共享这套视觉规范：

```typescript
export const theme = {
  colors: {
    background: '#0f0f1a',       // 深色背景
    surface: '#1a1a2e',           // 卡片/面板背景
    primary: '#4fc3f7',           // 主色（数据、强调）
    secondary: '#81c784',         // 副色
    accent: '#ffb74d',            // 点缀色
    danger: '#ef5350',            // 负面数据
    text: '#ffffff',
    textSecondary: '#b0b0b0',
    textMuted: '#666666',
  },
  fonts: {
    title: 'Noto Sans SC, sans-serif',
    body: 'Noto Sans SC, sans-serif',
    data: 'JetBrains Mono, monospace',
  },
  fontSize: {
    hero: 72,
    title: 48,
    subtitle: 32,
    body: 24,
    label: 18,
  },
};
```

**字体加载**：先读 rules/fonts.md 了解 Remotion 中加载字体的正确方式，中文必须用 Noto Sans SC 或 Source Han Sans，否则会显示方块。

## 第三步：开发核心组件

在 `src/components/` 下创建以下组件。**写每个组件前先读对应的 rules 文件。**

### 组件清单

| 组件名 | 用途 | 写之前读 |
|--------|------|---------|
| DataReveal | 大数字展示（数字从0跳到目标值 + 副标题） | rules/animations.md |
| BarChartAnimated | 柱状图（柱子依次从底部长出） | rules/charts.md, rules/animations.md |
| LineChartAnimated | 折线图（从左到右绘制） | rules/charts.md |
| CompareTwo | 左右对比（两个卡片从两侧飞入） | rules/animations.md |
| FlowSteps | 流程/步骤（节点依次点亮 + 箭头连线） | rules/animations.md |
| KeyPoint | 金句强调（全屏文字，打字机或淡入效果） | rules/animations.md |
| TitleCard | 段落标题转场 | rules/animations.md |
| BulletList | 要点列表（逐条滑入） | rules/animations.md |
| ImageWithOverlay | 图片 + 暗色遮罩 + 文字叠加 | rules/images.md, rules/assets.md |

### 每个组件的接口规范

**DataReveal**
```typescript
interface DataRevealProps {
  number: string;         // "206%"
  prefix?: string;        // "$" "¥"
  suffix?: string;        // "%" "万亿"
  subtitle: string;       // "日本政府债务占GDP比例"
  highlightColor?: string;
  countUp?: boolean;      // 默认 true
}
```
动画：数字从 0 countUp 到目标值（用 interpolate + spring），副标题延迟淡入。

**BarChartAnimated**
```typescript
interface BarChartAnimatedProps {
  title: string;
  data: Array<{ label: string; value: number; color?: string }>;
  unit?: string;
  highlightIndex?: number;
}
```
动画：柱子从左到右依次长出（每根用 spring 动画，间隔错开），数值标签跟随柱子顶部。

**LineChartAnimated**
```typescript
interface LineChartAnimatedProps {
  title: string;
  data: Array<{ x: string; y: number }>;
  unit?: string;
  annotations?: Array<{ x: string; text: string }>;
}
```
动画：用 SVG path + stroke-dashoffset 从左到右"画"出折线。标注文字在线画到该点时弹出。

**CompareTwo**
```typescript
interface CompareTwoProps {
  title: string;
  left: { label: string; points: string[]; color?: string };
  right: { label: string; points: string[]; color?: string };
  vsText?: string;
}
```

**FlowSteps**
```typescript
interface FlowStepsProps {
  title: string;
  steps: Array<{ label: string; description?: string }>;
  direction?: 'horizontal' | 'vertical';
}
```

**KeyPoint**
```typescript
interface KeyPointProps {
  text: string;
  emphasis?: string[];    // 高亮的关键词
  style?: 'quote' | 'statement' | 'question';
}
```

**TitleCard**
```typescript
interface TitleCardProps {
  title: string;
  subtitle?: string;
  sectionNumber?: number;
}
```

**BulletList**
```typescript
interface BulletListProps {
  title: string;
  items: Array<{ text: string }>;
}
```

**ImageWithOverlay**
```typescript
interface ImageWithOverlayProps {
  imageSrc: string;
  overlayOpacity?: number; // 默认 0.5
  title: string;
  subtitle?: string;
}
```

## 第四步：组合层 - 场景序列渲染器

创建 `src/VideoComposition.tsx`，它：
1. 读取分镜 JSON 文件
2. 根据每段的 `component` 字段映射到对应组件
3. 用 Remotion 的 `Series` 或 `TransitionSeries` 按时间顺序排列（读 rules/sequencing.md）
4. 段落之间用 fade 转场

**分镜 JSON 的接口协议**（这是 LLM 和 Remotion 之间的数据合同）：

```typescript
interface Segment {
  id: number;
  component: 'DataReveal' | 'BarChartAnimated' | 'LineChartAnimated' |
             'CompareTwo' | 'FlowSteps' | 'KeyPoint' | 'TitleCard' |
             'BulletList' | 'ImageWithOverlay';
  props: Record<string, any>;    // 传给组件的参数，必须符合上面的接口
  durationInSeconds: number;
  transition?: 'fade' | 'slide' | 'cut';
  background?: {
    type: 'solid' | 'gradient' | 'image';
    value: string;
  };
  narrationText?: string;  // 对应的旁白文字（不渲染，仅参考）
}

interface StoryboardData {
  title: string;
  totalDurationInSeconds: number;
  fps: number;              // 默认 30
  width: number;            // 默认 1920
  height: number;           // 默认 1080
  segments: Segment[];
}
```

## 第五步：用 LLM 生成分镜 JSON

写一个独立的 Python 脚本 `generate_storyboard.py`：
1. 读入一篇脚本文本（从主流水线的产出中拿一篇，或用小Lin说的一段脚本）
2. 调用 DeepSeek API，system prompt 包含：
   - 可用组件列表及每个组件的 props 接口
   - 组件选择规则（下面列出）
   - 输出格式要求（严格 JSON，不要 markdown 包裹）

**组件选择规则（写进 system prompt）**：
```
1. 脚本提到具体数字 → DataReveal（单个核心数字）或 BarChartAnimated/LineChartAnimated（多个数字对比/趋势）
2. 脚本做两者对比 → CompareTwo
3. 脚本讲流程/因果链/步骤 → FlowSteps
4. 脚本有一句话总结/金句 → KeyPoint
5. 脚本列举多个要点 → BulletList
6. 段落过渡/新话题开始 → TitleCard
7. 讲历史场景/需要氛围 → ImageWithOverlay（不超过总段落的 20%）
8. 一段脚本可以拆成多个 segment，节奏要有变化（不要每段都 10 秒）
9. 开头必须用 DataReveal 或 KeyPoint，要有冲击力
10. 脚本里的数据必须准确搬到 props 里，不要编造
```

3. 解析 LLM 返回的 JSON，保存为 `public/storyboard.json`

**把 Remotion 的 llms.txt（https://www.remotion.dev/llms.txt）也包含在 system prompt 中**，让 DeepSeek 理解 Remotion 的基本概念。

## 第六步：渲染视频

```bash
cd remotion-video
# 开发预览（可以实时看效果）
npx remotion studio

# 渲染输出
npx remotion render MyComp out/video.mp4
```

## 验证标准

渲染出的视频应该：
1. 全片风格统一（颜色、字体、动画节奏一致）
2. 数据出现时有动画（数字跳动、图表生长，不是静态图片）
3. 画面切换有节奏感（不是每段都一样长）
4. 开头有冲击力
5. 看起来是"有设计感的信息呈现"，不是 PPT 录屏或图片轮播

## 预期文件结构

```
remotion-video/
├── .claude/
│   └── skills/              # npx skills add 自动生成
│       └── remotion/
│           └── rules/       # 28 个规则文件
├── src/
│   ├── index.ts
│   ├── Root.tsx
│   ├── design-system.ts
│   ├── VideoComposition.tsx
│   └── components/
│       ├── DataReveal.tsx
│       ├── BarChartAnimated.tsx
│       ├── LineChartAnimated.tsx
│       ├── CompareTwo.tsx
│       ├── FlowSteps.tsx
│       ├── KeyPoint.tsx
│       ├── TitleCard.tsx
│       ├── BulletList.tsx
│       └── ImageWithOverlay.tsx
├── public/
│   └── storyboard.json
├── generate_storyboard.py
└── package.json
```

## 关键提醒

- **写代码前先读 rules**。这是最重要的一条。Remotion 的 Agent Skills 包含了大量最佳实践，直接用比自己摸索好很多。
- 遇到不确定的 API，用 MCP 查文档，或者 fetch remotion.dev/docs/xxx.md
- 先确保每个组件单独能在 Remotion Studio 中渲染出来，再串联
- 中文字体加载是常见坑，优先解决
- 暂时不需要处理音频，只做画面
