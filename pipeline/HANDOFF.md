# AI 科普视频自动化生产系统 - 开发交接文档

## 项目现状

### 已完成
骨架代码全部就绪，dry-run 测试通过。完整流水线可以从 research 跑到 published，5 个审核门全部正常暂停和恢复。

### 文件清单

```
video_production_system/
├── main.py              # 主入口，CLI 交互，审核门反馈收集
├── orchestrator.py      # 工作流定义：节点、边、条件路由、审核门
├── mini_graph.py        # 轻量级图执行引擎（替代 LangGraph，接口兼容）
├── state.py             # ProjectState 定义，所有 Agent 共享的数据结构
├── config.py            # LLM 分配（DeepSeek + Kimi）、API 配置
├── project_manager.py   # 项目文件管理 + JSON 状态持久化 + 版本管理
├── requirements.txt     # 依赖清单
├── agents/
│   ├── __init__.py      # BaseAgent 基类，统一的 LLM 调用封装（OpenAI 兼容）
│   ├── research.py      # Research Agent - Kimi 长上下文，知识提取
│   ├── topic.py         # Topic Agent - DeepSeek，选题策划
│   ├── script.py        # Script Agent - DeepSeek，分两步：大纲 + 完整脚本 + 自审循环
│   ├── storyboard.py    # Storyboard Agent - 分镜规划，输出 JSON 分镜表
│   └── visual.py        # Visual Producer - 混合型，LLM 生成指令 + 工具执行（STUB）
└── tools/
    ├── __init__.py
    ├── audio_processor.py  # 音频处理器 - ffmpeg + Whisper（STUB）
    └── composer.py         # 视频合成器 - Remotion + ffmpeg（STUB）
```

### 流水线路径

```
Research → Topic → 🔒审核门1 → Script大纲 → 🔒审核门2a → Script完整(含自审) → 🔒审核门2b(含口播预演)
→ Storyboard → 🔒审核门3 → Production(音频+视觉并行) → Compose → 🔒审核门4 → Published
```

每个审核门支持三种操作：approve（通过）、revise（局部修改）、rewrite/change_direction（重做）。
打回时创作者的反馈会注入 State，对应 Agent 下次执行时会读取反馈作为额外输入。

### 模块分类

| 类型 | 模块 | 需要 LLM | 状态 |
|------|------|----------|------|
| LLM Agent | Research, Topic, Script(x2), Storyboard | 是 | system prompt 已写好，LLM 调用封装已完成 |
| 混合型 | Visual Producer | LLM 生成 prompt + 工具执行 | STUB，需要集成 Plotly/Mermaid/AI生图 |
| 确定性工具 | AudioProcessor | 否 | STUB，需要集成 ffmpeg + Whisper |
| 确定性工具 | VideoComposer | 否 | STUB，需要集成 Remotion + ffmpeg |
| 基础设施 | Orchestrator, ProjectManager, MiniGraph | 否 | 已完成 |

---

## 架构关键设计决策

### 1. mini_graph.py vs LangGraph
当前用自建的轻量级图引擎，接口与 LangGraph 基本一致。等部署环境能 pip install langgraph 时，只需改 orchestrator.py 的 import：
```python
# 从
from mini_graph import MiniStateGraph as StateGraph, END, InMemoryCheckpointer as MemorySaver
# 改为
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
```

### 2. Agent 不直接对话
所有 Agent 通过 State 交换数据，不存在 Agent-to-Agent 的直接通信。这是为了：
- 保护创作者的审核权（Agent 不能绕过审核门私下改动）
- 避免 LLM 对话发散
- 每步可追溯

### 3. LLM 调用统一封装
BaseAgent.call_llm() 统一了 DeepSeek 和 Kimi 的调用，都走 OpenAI 兼容 API。切换模型只需改 config.py 中的配置。

### 4. 审核门的中断/恢复机制
mini_graph 通过 interrupt_before 在审核门节点前暂停。main.py 在暂停时：
1. 显示当前阶段的产出内容
2. 收集创作者反馈
3. 通过 update_state 注入反馈
4. stream(None) 恢复执行，审核门节点执行后路由函数读取反馈决定走向

---

## 环境配置

### API 密钥
通过环境变量设置：
```bash
export DEEPSEEK_API_KEY="your-key"
export KIMI_API_KEY="your-key"
```

### 依赖安装
```bash
pip install openai   # 当前唯一必需的外部依赖
# 可选（后续集成时需要）：
# pip install langgraph langchain-core  # 替换 mini_graph
# pip install openai-whisper pydub      # 音频处理
# pip install plotly matplotlib kaleido # 图表生成
```

### 运行
```bash
python main.py --topic "美联储加息"                    # 交互模式
python main.py --topic "美联储" --dry-run --auto-approve  # 全自动测试
python main.py --list                                   # 查看项目列表
```

---

## 下一步开发任务（建议顺序）

### 第一优先级：让 LLM Agent 真正跑起来

**任务 1：集成 LLM API 调用**
- agents/__init__.py 中的 BaseAgent.call_llm() 已封装好
- 只需配好 API 密钥就能跑
- 验证方式：不加 --dry-run 运行，看各 Agent 是否正常产出

**任务 2：优化 Script Agent 的 system prompt**
- 创作者有小Lin说的实际脚本文本，路径：`C:\Users\windows\Desktop\UP主的内容\小林说`
- 需要：从中选 2-3 段最精彩的片段作为 few-shot examples
- 嵌入到 agents/script.py 的 SCRIPT_SYSTEM_PROMPT 中
- 这是提升脚本质量最关键的一步

**任务 3：Storyboard Agent 的输出解析**
- 当前 storyboard 产出是原始 LLM 文本
- 需要加一个解析层：从 LLM 输出中提取 JSON（style_seeds + storyboard 数组）
- 处理 LLM 可能输出 markdown 代码块包裹的 JSON

### 第二优先级：工具层集成

**任务 4：音频处理器**
- 集成 Whisper 做语音识别 + 时间戳提取
- 集成 ffmpeg/pydub 做降噪、音量标准化
- 输出：处理后音频文件 + timestamps.json

**任务 5：图表生成器**
- Plotly/Matplotlib 生成数据图表
- Mermaid CLI 生成流程图 → SVG
- Visual Producer 根据分镜表的 visual_type 字段调度

**任务 6：AI 生图集成**
- Flux 或 DALL-E 3 API
- Visual Producer 用 LLM 生成英文 prompt → 调用生图 API
- 风格一致性：style_seeds 中的关键词自动拼接到每个 prompt

### 第三优先级：视频合成

**任务 7：视频合成器**
- 推荐 Remotion (React-based) + ffmpeg
- 以录音时间戳为主时钟对齐画面
- 字幕叠加、花字特效、BGM 混合

### 第四优先级：体验优化

**任务 8：Web UI**
- 当前是 CLI 交互，审核体验不够好
- 建议用 Streamlit 或 Gradio 搭一个简单的审核界面
- 创作者可以看到完整内容、做标注、给反馈

**任务 9：替换为 LangGraph**
- pip install langgraph 后替换 mini_graph
- 获得更强的持久化、并行执行、错误恢复能力

---

## 参考：架构方案原文
完整的产品需求和架构设计见项目文件：`AI科普视频自动化生产系统_架构方案_v1_0.docx`
