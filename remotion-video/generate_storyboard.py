"""
generate_storyboard.py — LLM 分镜生成器

读取视频脚本文本，调用 DeepSeek API，生成符合 StoryboardData 格式的分镜 JSON。
输出到 public/storyboard.json（同时也可指定输出路径）。

用法：
    python generate_storyboard.py --input script.txt
    python generate_storyboard.py --input script.txt --output out.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

# ============================================================
# 读取 API Key
# ============================================================

def load_api_key() -> str:
    # 优先环境变量
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    # 从 pipeline .env 文件读取
    env_path = Path(__file__).parent.parent / "pipeline" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    return key
    raise RuntimeError("DEEPSEEK_API_KEY 未设置，请在环境变量或 pipeline/.env 中配置")


# ============================================================
# System Prompt
# ============================================================

SYSTEM_PROMPT = """\
你是一个专业的科普视频分镜师，将脚本转化为 Remotion 视频分镜 JSON。

## 可用组件列表

每个分镜段（segment）必须选择以下 11 个组件之一：

### 1. DataReveal — 大数字冲击展示
```
props: {
  number: string,       // 核心数字，如 "3.73亿" "92.07%" "$1.2T"
  prefix?: string,      // 数字前缀，如 "$" "¥"
  suffix?: string,      // 附加后缀（number 中已含的不填）
  subtitle: string,     // 解释这个数字的一句话（不超过40字）
  highlightColor?: string,  // 高亮色，默认 "#ffb74d"
  countUp?: boolean     // 数字是否从0跳到目标值，默认 true
}
```

### 2. BarChartAnimated — 柱状图（多数据对比）
```
props: {
  title: string,
  data: Array<{ label: string, value: number, color?: string }>,
  unit?: string,        // 如 "%" "亿元" "万辆"
  highlightIndex?: number   // 要突出显示的柱子序号（从0开始）
}
```

### 3. LineChartAnimated — 折线图（趋势/时间序列）
```
props: {
  title: string,
  data: Array<{ x: string, y: number }>,   // x 为标签，y 为数值
  unit?: string,
  annotations?: Array<{ x: string, text: string }>  // 关键时间点标注
}
```

### 4. PieChartAnimated — 环形图（占比/份额）
```
props: {
  title: string,
  data: Array<{ label: string, value: number, color?: string }>,  // 2~5 项
  centerLabel?: string,    // 中央文字，如 "总计"
  unit?: string             // 默认 "%"
}
```
**仅当数据为占比/份额（总和约为 100% 或视为整体切分）时使用，项目数 ≤5。否则用 BarChart。**

### 5. CompareTwo — 左右对比
```
props: {
  title: string,
  left: { label: string, points: string[], color?: string },
  right: { label: string, points: string[], color?: string },
  vsText?: string   // 默认 "VS"
}
```

### 6. FlowSteps — 流程/步骤图
```
props: {
  title: string,
  steps: Array<{ label: string, description?: string }>,
  direction?: "horizontal" | "vertical" | "circular",
  centerIcon?: string   // direction=circular 时中央装饰字符（如 "↻" "★"，不要用 emoji）
}
```
**步骤 ≥ 5 且有因果循环/飞轮性质时使用 `direction: "circular"` + `centerIcon`；纯线性流程用 horizontal。**

### 7. KeyPoint — 金句/核心观点全屏强调
```
props: {
  text: string,           // 一句话，不超过50字
  emphasis?: string[],    // 要高亮的关键词（建议 1~3 个）
  style?: "quote" | "statement" | "question" | "highlight"
}
```
**style 选择：**
- `quote` — 引用/他人观点（大引号装饰）
- `statement` — 作者总结陈述（底部装饰线）
- `question` — 引发思考的反问（问号装饰）
- `highlight` — 关键词擦除式扫光强调（emphasis 词最强视觉突出，用于最重要的一击金句）

### 8. TitleCard — 段落标题/章节转场
```
props: {
  title: string,
  subtitle?: string,
  sectionNumber?: number  // 章节编号（可选）
}
```

### 9. BulletList — 要点列表（3~5条最佳，最多 6 条）
```
props: {
  title: string,
  items: Array<{ text: string }>   // 每条不超过60字
}
```

### 10. ImageWithOverlay — 图片+文字叠层（氛围/场景）
```
props: {
  imageSrc: string,       // 填 "assets/placeholder.jpg"（后续人工替换）
  overlayOpacity?: number,    // 0~1，默认 0.5
  title: string,
  subtitle?: string
}
```

### 11. TypewriterText — 打字机逐字效果
```
props: {
  text: string,                 // 要打出的文字（不超过30字）
  title?: string,               // 上方可选小标题
  charsPerSecond?: number,      // 打字速度，默认 8
  highlight?: string,           // 文字中的某个子串，打到时变色
  showCursor?: boolean          // 默认 true
}
```
**适合：引文/代码/口号的逐字揭示，强调"过程感"。整段视频最多用 1-2 次，不要频繁使用。**

## 组件选择规则

1. 脚本出现**核心数字**（单个重要数字）→ DataReveal
2. 脚本出现**多个同类指标对比**（柱状数据）→ BarChartAnimated
3. 脚本出现**随时间变化的数据**（趋势/时间序列）→ LineChartAnimated
4. 脚本出现**占比/份额**（总和≈100%，市场份额/组成比例）→ PieChartAnimated
5. 脚本做**两者对比**（A vs B，两种方案/两个阵营）→ CompareTwo
6. 脚本讲**流程/步骤/因果链**（有先后顺序）→ FlowSteps（线性用 horizontal；循环/飞轮用 circular）
7. 脚本有**一句话总结/金句** → KeyPoint（最重一击用 `style:"highlight"`）
8. 新话题/段落**开场标题**、视频结尾 → TitleCard
9. 脚本列举**3~6条并列要点**（无明确顺序）→ BulletList
10. 需要**氛围背景**（宏观叙述/历史背景/情感渲染）→ ImageWithOverlay（不超过总段落20%）
11. 脚本有**引文/代码/口号**需要"过程感"强调 → TypewriterText（整段视频 1-2 次即可）

**额外要求：**
- 开头第一段必须是 TitleCard（视频标题）
- 开头第二段必须是 DataReveal、KeyPoint 或 TypewriterText（制造冲击感）
- 脚本里的数据必须准确搬到 props，不要编造数据
- 每段时长 8~35 秒，有节奏变化（不要每段都一样长）
- 总段落数 10~18 个（不要太碎也不要太少）
- `transition` 通常填 `"fade"`；若两段语义紧密相连想无缝切换，可填 `"cut"`；想左右滑入切换可填 `"slide"`

## 输出格式

只输出合法 JSON，不要任何解释文字，不要 markdown 代码块。格式如下：

{
  "title": "视频标题",
  "totalDurationInSeconds": 总秒数,
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "segments": [
    {
      "id": 1,
      "component": "TitleCard",
      "props": { ... },
      "durationInSeconds": 8,
      "transition": "fade",
      "narrationText": "对应的口播文字..."
    }
  ]
}
"""

# ============================================================
# LLM 调用
# ============================================================

def call_deepseek(api_key: str, script_text: str) -> str:
    session = requests.Session()
    session.trust_env = False

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请将以下视频脚本转化为分镜 JSON：\n\n{script_text}"},
        ],
        "temperature": 0.4,
        "max_tokens": 8192,
    }

    retry_delays = [3, 10, 30]
    for attempt, delay in enumerate([0] + retry_delays):
        if delay:
            print(f"[generate] 等待 {delay}s 后重试 (第 {attempt+1} 次)...")
            time.sleep(delay)
        try:
            print(f"[generate] 调用 DeepSeek API (尝试 {attempt+1}/{len(retry_delays)+1})...")
            resp = session.post(url, headers=headers, json=payload, timeout=180)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"] or ""
            print(f"[generate] LLM 返回 {len(content)} 字符")
            return content
        except Exception as e:
            print(f"[generate] 调用失败: {e}")
            if attempt == len(retry_delays):
                raise

    return ""


# ============================================================
# JSON 解析与校验
# ============================================================

ALLOWED_COMPONENTS = {
    "DataReveal", "BarChartAnimated", "LineChartAnimated", "PieChartAnimated",
    "CompareTwo", "FlowSteps", "KeyPoint", "TitleCard",
    "BulletList", "ImageWithOverlay", "TypewriterText",
}

def extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON，处理 markdown 包裹"""
    # 去除 markdown 代码块
    m = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
    if m:
        text = m.group(1).strip()

    # 找第一个 { 到最后一个 }
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        raise ValueError("LLM 输出中未找到 JSON 对象")

    return json.loads(text[start:end + 1])


def validate_storyboard(data: dict) -> None:
    """校验 StoryboardData 结构"""
    required = ["title", "fps", "width", "height", "segments"]
    for field in required:
        if field not in data:
            raise ValueError(f"缺少必填字段: {field}")

    segments = data["segments"]
    if not isinstance(segments, list) or len(segments) == 0:
        raise ValueError("segments 必须是非空数组")

    for i, seg in enumerate(segments):
        if "component" not in seg:
            raise ValueError(f"segment[{i}] 缺少 component 字段")
        if seg["component"] not in ALLOWED_COMPONENTS:
            raise ValueError(f"segment[{i}] 的 component '{seg['component']}' 不在允许列表中")
        if "props" not in seg:
            raise ValueError(f"segment[{i}] 缺少 props 字段")
        if "durationInSeconds" not in seg:
            seg["durationInSeconds"] = 12  # 默认值
        if "id" not in seg:
            seg["id"] = i + 1


# ============================================================
# 主函数
# ============================================================

def generate(input_path: str, output_path: str) -> None:
    script_text = Path(input_path).read_text(encoding="utf-8")
    print(f"[generate] 脚本长度: {len(script_text)} 字符")

    api_key = load_api_key()
    raw = call_deepseek(api_key, script_text)

    print("[generate] 解析 JSON...")
    try:
        data = extract_json(raw)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[generate] ❌ JSON 解析失败: {e}")
        # 保存原始输出供调试
        debug_path = Path(output_path).with_suffix(".debug.txt")
        debug_path.write_text(raw, encoding="utf-8")
        print(f"[generate] 原始输出已保存到: {debug_path}")
        sys.exit(1)

    validate_storyboard(data)

    # 计算 totalDurationInSeconds
    data["totalDurationInSeconds"] = sum(
        seg.get("durationInSeconds", 12) for seg in data["segments"]
    )

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    seg_count = len(data["segments"])
    total_sec = data["totalDurationInSeconds"]
    print(f"[generate] ✅ 分镜生成成功: {seg_count} 段, 共 {total_sec}s ({total_sec/60:.1f}min)")
    print(f"[generate] 输出: {out_path}")

    # 打印摘要
    for seg in data["segments"]:
        print(f"  [{seg['id']:2d}] {seg['component']:20s} {seg['durationInSeconds']:3d}s  {str(seg.get('props',{}))[:60]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM 分镜生成器")
    parser.add_argument("--input", required=True, help="脚本文本文件路径")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "public" / "storyboard.json"),
        help="输出 JSON 路径（默认 public/storyboard.json）",
    )
    args = parser.parse_args()
    generate(args.input, args.output)
