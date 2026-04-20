"""
Script Agent（脚本生成）

整个系统的灵魂环节。分两步执行：
  Step 1: 生成脚本大纲 → 审核门 2a
  Step 2: 生成完整脚本 + 自审循环 → 审核门 2b（含口播预演建议）

使用 DeepSeek。System prompt 中直接嵌入叙事结构模板和技巧库。
"""

from agents import BaseAgent
from agents import _knowledge
from state import ProjectState, Stage, StageStatus


# ============================================================
# 大纲生成的 System Prompt
# ============================================================

OUTLINE_SYSTEM_PROMPT = """\
你是一个顶级科普视频脚本策划师，风格参考B站UP主"小Lin说"的财经科普视频。

你的任务是生成视频脚本大纲（不是完整脚本）。大纲是创作者确认结构方向的关键步骤。

## 你可以使用的叙事结构模板（共 5 种，每种都带真实案例）

{STRUCTURES}

---

## 开头设计参考（前 30 秒必须抓人，共 3 种钩子类型）

{OPENINGS}

## 输出格式（Markdown）

# 脚本大纲：{视频标题}

## 采用结构：{结构类型名}
理由：{为什么选这个结构}

## 段落规划

### 第1段：{段落标题}（预估 X 分钟）
- **核心内容**：这段要讲什么
- **叙事目的**：这段在全片中的功能（吸引注意/建立认知/制造冲突/给出答案...）
- **关键素材**：需要用到的数据/案例/比喻
- **使用技巧**：{从技巧库中选取}

### 第2段：...
（以此类推，一般 5-8 个段落）

## 预估总时长：{分钟}
## 节奏设计备注：{对整体节奏的说明，比如哪里要快、哪里要慢、高潮在哪}

要求：
- 每个段落的"叙事目的"必须明确，不是罗列信息
- 段落之间要有逻辑递进，不是平铺
- 开头必须在 30 秒内抓住注意力
- 至少有一处"搭建预期→摧毁预期"的结构设计
"""


# ============================================================
# 完整脚本生成的 System Prompt
# ============================================================

SCRIPT_SYSTEM_PROMPT = """\
你是一个顶级科普视频脚本作家，风格参考B站UP主"小Lin说"。

你的任务是基于审核通过的大纲，写出完整的视频脚本（口播台词）。

## 核心叙事技巧库（10 个技巧，每个都有真实片段 + 技法拆解 + 禁忌）

{TECHNIQUES}

## 输出格式

# 完整脚本：{视频标题}

---
### 第1段：{段落标题}
**[使用技巧：{技巧名}]**
**[画面提示：{简要描述这段适合配什么类型的画面}]**

{口播台词，直接就是创作者要念的话}

---
### 第2段：...

---
（以此类推）

## 写作要求：
1. **口语化**：这是要念出来的，不是书面文章。用短句、口语词、语气词。参考："你要是按日本政府2022年财政收入算，那他就是不吃不喝，完全不花钱，一分钱也不花"——注意这种口语堆叠的节奏
2. **节奏感**：重要信息前留停顿暗示（用 "..." 或换行），高潮段加速推进
3. **每段开头要承上启下**：不是生硬切换，要有过渡。参考技巧 8（段落转折黄金句式）
4. **语气标注**：在关键处用【加重】【停顿】【语速加快】等标注
5. **预估每段时长**：按每分钟约 250 字估算
6. **每个核心数据必须做"两步翻译"**：先给原始数据，再用生活化比喻让观众"感受到"
7. **数据核实标注**：所有具体数字、百分比、人物现任职位、事件最终结果，如果不是来自本次提供的搜索资料，必须在该处加"⚠️（数据待核实）"标注。宁可多标，不可漏标。创作者看到标注后会自行核查替换。
8. **技巧多样性**：整篇至少使用 **4 种不同的技巧**（从 10 个里挑），不要全篇只堆一个技巧（常见问题：只用"两步翻译"和"段落转折"）
9. **尾段同等质量**：不要虎头蛇尾。最后 2 段和中间段必须保持和首段一样的口语化、技巧密度、节奏
10. **✨ 稿末必须加一节 `## 本稿使用的技巧清单`**：逐段标注该段用了哪个技巧编号 + 一句话说明。范例格式：
    ```
    ## 本稿使用的技巧清单

    - 第 1 段：技巧 1（两步翻译）+ 技巧 10（自造金句）—— "206% → 18 年不吃不喝" + "这些政府都疯了吗"
    - 第 2 段：技巧 3（对偶标签）—— "内债缓冲器 vs 外债放大器"
    - 第 3 段：技巧 8（段落转折）+ 技巧 2（历史因果链）—— "难道就这么无止境借下去吗？" + 斯密→大萧条→凯恩斯
    - 第 4 段：技巧 6（搭建预期摧毁预期）—— 先讲央行能压利率，再亮出"可是天下没有免费的午餐"
    - 第 5 段：技巧 7（一词定调）—— 用"拖"概括大多数国家的应对
    ```
    自审会抽查 2 段比对声明与实际文本，对不上会被打回重写。
"""


# ============================================================
# 自审 Prompt
# ============================================================

SELF_REVIEW_PROMPT = """\
你是一个严格的脚本审核编辑，专门审查"小 Lin 说"风格的财经/科技科普脚本。请对以下脚本进行自审。

## 反向检查（避免什么）

1. **节奏检查**：有没有连续超过 2 分钟的纯说教段？段落过短或过长？
2. **风格一致性**：口语化程度是否全篇统一？有没有突然书面化的段落？
3. **逻辑断裂**：段落之间过渡是否顺畅？
4. **开头吸引力**：前 30 秒是否足够抓人？
5. **结尾力度**：结尾是否有力？有没有虎头蛇尾？
6. **信息密度**：有没有灌水段？有没有信息过载段？

## 正向检查（做到什么）—— 这是重点

### 7. 技巧清单真实性（必查）
稿末应该有一节 `## 本稿使用的技巧清单`。如果没有，直接打回重写（说"缺失技巧清单"）。

如果有，**随机抽 2 段**（最好抽中间段和末段），比对该段声明的技巧和实际文本：
- 声明用了技巧 1（两步翻译），实际文本里真的有"大数字 + 生活化换算"吗？
- 声明用了技巧 6（搭建预期摧毁预期），实际文本里真的有"先让观众相信 X → 再用数据 / 事实打脸"吗？
- 声明和实际**对不上的段落必须重写**，并在修订版里更新技巧清单

### 8. 技巧多样性（必查）
统计技巧清单里**不同的技巧编号数量**。如果 < 4 种，打回重写（提示："全篇只用了 X 种技巧，过于单一，请至少使用 4 种"）。

### 9. 尾段质量守护（必查）
对比**首段、中间段、末段**的：
- 口语化程度（是否全篇一致，末段是否突然书面化）
- 技巧密度（每段是否都有至少 1 个明显技巧，还是末段变成空洞总结）
- 节奏感（停顿、转折、口语堆叠的出现频率）

如果末段明显比首段质量低，**必须重写末段**，保留原稿的同时把末段改得和首段一样有节奏。

## 输出规则

- **自审完全通过**（9 项全过）→ 开头写"【自审通过】"+ 一句理由，然后 **原文照抄完整脚本**（含技巧清单）。
- **发现问题** → 必须输出 **修改后的完整脚本**（不是只列问题，不是只改几行，是完整逐字稿 + 更新后的技巧清单），开头注明修改了哪里、修了哪些检查项。
- **绝对禁止**：只输出摘要、只输出批注、只输出部分段落。必须是可以直接交给创作者念的完整口播稿。

脚本如下：
"""


class ScriptOutlineAgent(BaseAgent):
    """脚本大纲生成（第一步）"""
    name = "script_outline_agent"

    def run(self, state: ProjectState) -> ProjectState:
        self._log("开始生成脚本大纲")

        user_prompt = f"""选题提案：
{state['topic_proposal']}

知识框架：
{state['knowledge_framework']}

"""
        # 如果是打回重做，带上反馈
        if state.get("review_feedback") and state.get("current_review_gate") == "gate_2a":
            user_prompt += f"\n创作者反馈（请据此修改）：\n{state['review_feedback']}\n"
            if state.get("script_outline"):
                user_prompt += f"\n上一版大纲（需修改）：\n{state['script_outline']}\n"

        user_prompt += "\n请生成脚本大纲。"

        # 注入 knowledge_base 的结构模板 + 开头钩子
        system_prompt = (
            OUTLINE_SYSTEM_PROMPT
            .replace("{STRUCTURES}", _knowledge.load_structures())
            .replace("{OPENINGS}", _knowledge.load_openings())
        )
        result = self.call_llm(system_prompt, user_prompt)

        state["script_outline"] = result
        state["current_stage"] = Stage.SCRIPT_OUTLINE
        state["last_agent"] = self.name

        status = dict(state.get("stage_status", {}))
        status[Stage.SCRIPT_OUTLINE.value] = StageStatus.AWAITING_REVIEW.value
        state["stage_status"] = status
        state["current_review_gate"] = "gate_2a"

        self._log("脚本大纲生成完成，等待审核门2a")
        return state


class ScriptFullAgent(BaseAgent):
    """完整脚本生成（第二步）+ 自审循环（双模型：DeepSeek写稿，Kimi审稿）"""
    name = "script_full_agent"

    def __init__(self, llm_config, review_llm_config=None):
        super().__init__(llm_config)
        self.review_llm_config = review_llm_config or llm_config

    def run(self, state: ProjectState) -> ProjectState:
        self._log("开始生成完整脚本")

        user_prompt = f"""审核通过的大纲：
{state['script_outline']}

知识框架：
{state['knowledge_framework']}

选题提案：
{state['topic_proposal']}
"""
        # 打回重做的情况
        if state.get("review_feedback") and state.get("current_review_gate") == "gate_2b":
            user_prompt += f"\n创作者反馈（请据此修改）：\n{state['review_feedback']}\n"
            if state.get("script_full"):
                user_prompt += f"\n上一版脚本（需修改）：\n{state['script_full']}\n"

        user_prompt += "\n请生成完整脚本。"

        # 第一轮：生成初稿（注入 knowledge_base 的 10 种技巧片段）
        self._log("生成初稿...")
        script_system = SCRIPT_SYSTEM_PROMPT.replace("{TECHNIQUES}", _knowledge.load_techniques())
        draft = self.call_llm(script_system, user_prompt)

        # 第二轮：自审循环（换用 review_llm，默认 Kimi 读完整初稿）
        self._log(f"执行自审循环（{self.review_llm_config.provider}/{self.review_llm_config.model}）...")
        # 临时切换 llm_config 调用审核模型
        original_config = self.llm_config
        self.llm_config = self.review_llm_config
        reviewed = self.call_llm(
            SELF_REVIEW_PROMPT,
            draft,
            temperature=0.3,
        )
        self.llm_config = original_config

        # 判断自审结果
        if "【自审通过】" in reviewed:
            final_script = draft
            self._log("自审通过，使用初稿")
        elif len(reviewed) < len(draft) * 0.8:
            # 自审结果比初稿短超过20%，说明模型只输出了摘要/批注而非完整脚本
            # 这种情况直接用初稿，避免内容损失
            final_script = draft
            self._log(f"⚠️ 自审结果过短（{len(reviewed)} vs 初稿 {len(draft)} 字），丢弃自审，使用初稿")
        else:
            final_script = reviewed
            self._log("自审有修改，使用修订版")

        state["script_full"] = final_script
        state["current_stage"] = Stage.SCRIPT_FULL
        state["last_agent"] = self.name

        status = dict(state.get("stage_status", {}))
        status[Stage.SCRIPT_FULL.value] = StageStatus.AWAITING_REVIEW.value
        state["stage_status"] = status
        state["current_review_gate"] = "gate_2b"

        self._log("完整脚本生成完成，等待审核门2b（含口播预演）")
        return state
