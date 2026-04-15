# Remotion 视频渲染流程说明

## 一、整体流程概览

```
pipeline（Python）                          remotion（Node.js/React）
─────────────────────────────────────────────────────────────────────
① Storyboard Agent
   LLM 输出分镜 JSON + 视觉风格
   └→ 组装成 VideoScript JSON（基础结构）
         存入 state["video_script_json"]

② VideoScript Agent
   LLM 从 script_full 中提取
   - display_points（面向观众的要点）
   - narration（纯口播文本）
   └→ 合并回 state["video_script_json"]

③ gate_3 审核门（Streamlit UI）
   创作者点击「触发 Remotion 渲染」
   └→ 后台线程调用 app.py::_run_remotion_render()

④ render.py（Python 渲染桥）
   - 读取 video_script_json
   - 复制图片/音频到 remotion/public/assets/
   - 写入 remotion/public/script.json
   - 调用 npx remotion render VideoDemo <output.mp4>
         ↓
⑤ Remotion（React/Chromium）
   读取 public/script.json → 按 segments 逐帧渲染组件 → MP4

输出：{project_dir}/remotion_output.mp4
```

---

## 二、各阶段详细说明

### 阶段①：Storyboard Agent（`pipeline/agents/storyboard.py`）

#### 输入
| 字段 | 来源 |
|------|------|
| `state["script_full"]` | Script Agent 生成的完整口播脚本 |
| `state["topic_proposal"]` | Topic Agent 生成的选题提案（视觉方向参考） |
| `state["review_feedback"]` | 如果是打回重做，带上创作者意见 |

#### System Prompt
```
你是一个专业的视频分镜师，负责将科普视频脚本转化为详细的分镜表。

这是一个"纯画面流"视频——没有真人出镜，所有视觉注意力靠画面撑住。
配音由创作者真人录制，你需要规划每段配音对应什么画面。

## 画面类型（每段必须指定一个主类型）

- data_chart:    数据图表（柱状图、折线图、饼图等）→ 程序化生成
- flow_diagram:  流程图/关系图/结构图 → Mermaid 生成
- comparison:    对比框架图（左右对比、表格对比）→ 程序化生成
- ai_image:      AI 生成的氛围图/场景图/概念图 → AI 生图
- text_animation:文字动画（关键词弹出、数字跳动）→ Remotion 动画
- mixed:         混合类型（图表 + 文字叠加等）

## 输出格式（必须是合法的 JSON）

### 第一部分：视觉风格种子（style_seeds）
{
  "color_palette": {
    "primary": "#颜色代码",
    "secondary": "#颜色代码",
    "accent": "#颜色代码",
    "background": "#颜色代码",
    "text": "#颜色代码"
  },
  "font_style": "说明字体风格倾向",
  "visual_mood": "整体视觉情绪关键词（如：专业冷静/活泼有趣/严肃深沉）",
  "ai_image_style_keywords": "AI生图时固定携带的风格关键词（英文）"
}

### 第二部分：分镜表（storyboard）
[
  {
    "segment_id": 1,
    "segment_title": "段落标题",
    "script_text": "对应的脚本文本（简要）",
    "estimated_duration_sec": 60,
    "visual_type": "data_chart",
    "visual_description": "详细的画面描述：需要展示什么内容，什么布局",
    "key_elements": ["必须出现在画面上的关键元素"],
    "text_overlay": "需要在画面上叠加的文字/数字",
    "transition": "与上一段的过渡方式（cut/fade/slide）",
    "notes": "给 Visual Producer 的补充说明"
  }
]

## 要求
- 每个脚本段落对应一个或多个分镜段
- 画面切换不要太频繁（每段至少 15 秒），也不要太单调（单个画面不超过 60 秒）
- 数据密集的段落用 data_chart，故事性强的段落用 ai_image
- 开头第一个画面要有冲击力
- 视觉风格种子会贯穿全片，请根据主题选择合适的色调
```

#### User Prompt 结构
```
完整脚本：
{script_full}

选题提案（参考视觉方向）：
{topic_proposal}

[如打回重做，追加：]
创作者反馈（请据此修改）：{review_feedback}
上一版分镜表（需修改）：{storyboard}

请输出视觉风格种子和分镜表（JSON格式）。
```

#### 输出
- `state["storyboard"]`：LLM 原始文本（用于审核门显示）
- `state["style_seeds"]`：解析出的配色/风格 JSON 字符串
- `state["video_script_json"]`：组装好的 VideoScript JSON 字符串（基础结构，此时 display_points 为空）

VideoScript JSON 基础结构：
```json
{
  "title": "智能驾驶发展",
  "style": {
    "primary":    "#1E3A8A",
    "secondary":  "#DC2626",
    "accent":     "#F59E0B",
    "background": "#0F172A",
    "text":       "#F8FAFC"
  },
  "segments": [
    {
      "segment_id": 1,
      "segment_title": "开场",
      "visual_type": "title_card",
      "visual_description": "...",
      "text_overlay": "智能驾驶：驶向未来",
      "key_elements": [],
      "estimated_duration_sec": 8,
      "narration": "..."
    }
  ]
}
```

---

### 阶段②：VideoScript Agent（`pipeline/agents/video_script.py`）

#### 输入
| 字段 | 来源 |
|------|------|
| `state["video_script_json"]` | Storyboard Agent 产出的基础结构 |
| `state["script_full"]` | 完整口播脚本（用于提取 narration） |

#### System Prompt
```
你是一个视频内容编辑，专注于将制作分镜表转化为观众可见的文字内容。

## 背景

视频分镜表中有两类信息需要严格区分：
1. 制作指令（不给观众看）：visual_description、key_elements、notes
   这些是给动画师/制作团队的说明，如"展示K线图""添加增长动画""使用蓝色配色"等
2. 观众内容（显示在视频画面上）：display_points、narration
   这些是视频画面上真正呈现给观众的文字

## 你的任务

给定分镜段列表和完整口播脚本，为每个分镜段生成：

1. display_points：面向观众的 2~4 个要点
   - 必须来自脚本的实质内容（数据、结论、核心观点）
   - 每条不超过 25 字，简洁有力
   - 禁止包含制作指令（"展示XXX""添加XXX动画"等）
   - 若是 title_card 类型，生成 1 条简短副标题（不超过 20 字）

2. narration：该段对应的纯口播文本
   - 从完整脚本中找到对应该段内容（按 script_text 线索定位）
   - 去除所有标注：**[画面提示]**、【语气指令】、（语气说明）、⚠️ 等
   - 只保留真正需要说出口的句子

## 输出格式

只输出 JSON 数组，不要任何解释文字：

[
  {
    "segment_id": 1,
    "display_points": ["核心观点或数据1", "核心观点或数据2"],
    "narration": "纯口播文本，不含任何标注..."
  }
]
```

#### User Prompt 结构
```
分镜段列表：
[
  {
    "segment_id": 1,
    "segment_title": "开场",
    "visual_type": "title_card",
    "text_overlay": "智能驾驶：驶向未来",
    "script_text": "...前200字的已有narration..."
  },
  ...
]

完整口播脚本：
{script_full 前6000字}

请为每个分镜段生成 display_points 和 narration，只输出 JSON 数组。
```

#### 输出
将每段的 `display_points` 和 `narration` 合并回 `state["video_script_json"]`，完整 VideoScript JSON 示例：

```json
{
  "title": "智能驾驶发展",
  "style": { ... },
  "segments": [
    {
      "segment_id": 1,
      "visual_type": "title_card",
      "text_overlay": "智能驾驶：驶向未来",
      "display_points": ["L2 普及率已超 60%，L4 商业化箭在弦上"],
      "narration": "今天我们来聊一个改变人类出行方式的话题...",
      "estimated_duration_sec": 8
    },
    {
      "segment_id": 2,
      "visual_type": "text_animation",
      "text_overlay": "什么是智能驾驶分级？",
      "display_points": [
        "L0：完全人工驾驶",
        "L2：辅助驾驶，占新车销量 60%+",
        "L4：特定场景全自动，北京/深圳已测试"
      ],
      "narration": "要理解智能驾驶，先从分级说起...",
      "estimated_duration_sec": 35
    }
  ]
}
```

---

### 阶段③：gate_3 触发渲染（`pipeline/app.py`）

用户在 Streamlit UI 点击「触发 Remotion 渲染」，后台线程启动：

```python
_run_remotion_render(
    video_script_json=state["video_script_json"],
    project_dir=state["project_dir"],
    audio_path="..."   # TTS 路径或上传录音路径
)
```

---

### 阶段④：render.py 渲染桥（`remotion/render.py`）

```
输入：VideoScript JSON 文件路径
输出：MP4 文件

执行步骤：
1. 读取 script.json
2. 复制图片（ai_image 的 image_path）→ remotion/public/assets/
3. 复制音频（audio_path）→ remotion/public/assets/
4. 将 script.json 写入 remotion/public/script.json
5. 计算总帧数 = Σ(segment.estimated_duration_sec × 30fps)
6. 调用：
   npx remotion render VideoDemo <output.mp4>
     --props '{"script": {...}, "fps": 30}'
     --concurrency 2
     --log verbose
```

环境变量要求：
```bash
BROWSER_EXECUTABLE_PATH=/usr/bin/chromium-browser
```

输出路径：`{project_dir}/remotion_output.mp4`

---

### 阶段⑤：Remotion 组件渲染（`remotion/src/`）

#### 主合成（`VideoComposition.tsx`）

按 `segments` 数组依次用 `Series.Sequence` 渲染，每段：
- 计算帧数 = `estimated_duration_sec × 30`
- 头 12 帧：`FadeIn`（从背景色淡入）
- 尾 12 帧：`FadeOverlay`（淡出到背景色）
- 中间：根据 `visual_type` 渲染对应组件
- 若有 `audio_path`：全局叠加 `<Audio>` 轨道

#### visual_type → 组件映射

| visual_type | 组件 | 渲染内容 | 动画效果 |
|-------------|------|---------|---------|
| `title_card` | `TitleCard` | `text_overlay` 为主标题，`display_points[0]` 为副标题 | 主标题缩放弹出，副标题从下飞入 |
| `text_animation` | `TextCard` | `text_overlay` 为标题，`display_points` 为要点列表（最多4条），降级顺序：`display_points → key_elements → visual_description.split()` | 标题+要点逐行飞入（错帧12帧） |
| `data_chart`（bar） | `BarChart` | `chart_data.title/labels/values/y_title` | 柱子从底部逐根生长 |
| `data_chart`（line） | `LineChart` | `chart_data.title/x_data/y_series` | stroke-dashoffset 绘制，多条线错帧10帧 |
| `comparison` | `ComparisonCard` | `chart_data.title/items`（分组柱状图） | 按指标批次顺序生长 |
| `ai_image` | `AIImageCard` | 全屏背景图（`image_path`），底部叠 `text_overlay` + `display_points[0]` | 图片淡入，文字从底部滑入 |
| `flow_diagram` | `TextCard`（降级） | 同 text_animation | — |

#### 字段优先级（内容分离原则）

```
面向观众（渲染到视频）：
  display_points  ← VideoScript Agent 生成，优先使用
  text_overlay    ← Storyboard Agent 生成的画面标题

制作参考（禁止渲染到视频）：
  visual_description  ← 给动画师看的画面布局说明
  key_elements        ← 给制作系统看的元素清单
```

---

## 三、数据结构（TypeScript 类型，`src/types.ts`）

```typescript
interface VideoScript {
  title: string
  style: {
    primary: string     // 主色（通常为深蓝）
    secondary: string   // 副色（通常为红）
    accent: string      // 强调色（通常为金黄）
    background: string  // 背景色（通常为深色）
    text: string        // 文字色（通常为白）
  }
  segments: StoryboardSegment[]
  audio_path?: string   // 相对 public/ 的路径
}

interface StoryboardSegment {
  segment_id: number
  segment_title: string
  visual_type: "title_card" | "text_animation" | "data_chart" | "ai_image" | "comparison" | "flow_diagram"
  text_overlay: string           // 画面大标题（面向观众）
  display_points?: string[]      // 面向观众的要点（优先渲染）
  key_elements: string[]         // 制作元素清单（禁止渲染到视频）
  visual_description: string     // 画面布局描述（禁止渲染到视频）
  estimated_duration_sec: number
  narration?: string             // 纯口播文本
  chart_data?: ChartData         // data_chart/comparison 时使用
  image_path?: string            // ai_image 时使用
}

// chart_data 支持的结构
type ChartData =
  | { chart_type: "bar";        title: string; labels: string[]; values: number[]; y_title?: string }
  | { chart_type: "line";       title: string; x_data: string[]; y_series: Record<string, number[]> }
  | { chart_type: "comparison"; title: string; items: Array<{ label: string; values: Record<string, number> }> }
  | { chart_type: "pie";        title: string; labels: string[]; values: number[] }
```

---

## 四、已知问题 / 待优化

| 问题 | 说明 |
|------|------|
| `chart_data` 经常为空 | Storyboard Agent 不输出真实数值，当前靠 visual agent 手动填，经常漏填，导致 `data_chart` 段降级到 `TextCard` |
| `display_points` 偶尔生成失败 | VideoScript Agent LLM 调用异常时静默跳过，保留空的 `display_points`，TextCard 降级使用 `key_elements` |
| 渲染耗时 2-5 分钟 | Chromium headless 单机渲染，concurrency=2 |
| ffmpeg compose 尚未废弃 | pipeline 成片阶段仍在用 `tools/composer.py`，尚未切换到 Remotion 作为最终出口 |

---

## 五、手动触发渲染命令

```bash
# 直接用 render.py（pipeline 集成方式）
cd /home/ubuntu/video-ai/remotion
BROWSER_EXECUTABLE_PATH=/usr/bin/chromium-browser \
python render.py \
  --script /home/ubuntu/video-ai/pipeline/projects/20260409_092202_智能驾驶发展/video_script.json \
  --output /tmp/test_output.mp4

# 用 Demo 硬编码脚本渲染（测试用）
cd /home/ubuntu/video-ai/remotion
BROWSER_EXECUTABLE_PATH=/usr/bin/chromium-browser \
  npx remotion render VideoDemo output/demo.mp4

# 渲染单帧截图（快速验证组件）
BROWSER_EXECUTABLE_PATH=/usr/bin/chromium-browser \
  npx remotion still VideoDemo output/frame.png --frame=30
```
