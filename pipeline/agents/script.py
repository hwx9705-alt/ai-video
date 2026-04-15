"""
Script Agent（脚本生成）

整个系统的灵魂环节。分两步执行：
  Step 1: 生成脚本大纲 → 审核门 2a
  Step 2: 生成完整脚本 + 自审循环 → 审核门 2b（含口播预演建议）

使用 DeepSeek。System prompt 中直接嵌入叙事结构模板和技巧库。
"""

from agents import BaseAgent
from state import ProjectState, Stage, StageStatus


# ============================================================
# 大纲生成的 System Prompt
# ============================================================

OUTLINE_SYSTEM_PROMPT = """\
你是一个顶级科普视频脚本策划师，风格参考B站UP主"小Lin说"的财经科普视频。

你的任务是生成视频脚本大纲（不是完整脚本）。大纲是创作者确认结构方向的关键步骤。

## 你可以使用的叙事结构模板

1. **常识颠覆型**：数据震撼开场 → 理论科普 → 核心框架 → 应对方案
   - 适用于：观众以为自己懂但其实不懂的话题
   - 真实案例：小Lin说《一口气了解国债》——用"国债比GDP 206%"的震撼数据开场，然后从亚当·斯密讲到凯恩斯，层层递进到"内债vs外债"的核心框架

2. **机构揭秘型**：权力感渲染 → 历史溯源 → 制度拆解 → 人物传奇 → 深层博弈
   - 适用于：讲某个机构/组织的运作逻辑
   - 真实案例：小Lin说《一口气了解美联储》——先渲染"12个人开开会动动嘴皮子就能影响全球经济"的权力感，再用1907银行危机和1929大萧条两段历史讲制度演变

3. **横向对比型**：全景地图 → 逐个深入分析 → 方法论分享
   - 适用于：多个国家/公司/方案的对比

4. **视野升级型**：微观案例 → 经典模型 → 现实修正 → 博弈论 → 历史长卷
   - 适用于：一个概念从入门到深度的层层递进
   - 真实案例：小Lin说《一口气了解关税》——从经典"无谓损失三角形"模型出发，然后用五个现实修正逐步推翻教科书

5. **期望管理型**：共情切入 → 理论预期搭建 → 数据摧毁预期 → 更深洞察
   - 适用于：大家对某事有强烈预期但现实不同
   - 真实案例：小Lin说《美元开启降息周期了》——先花大量篇幅搭建"降息应该→股市涨/美元跌/新兴市场好"的预期，再用历史数据逐条摧毁

## 开头设计参考（前30秒必须抓人）

以下是小Lin说的实际开头，注意她如何在前三句话内制造认知冲突：

> "美联储可以说是这个星球上对金融市场影响力最大的机构。政策出点问题就导致了20世纪最严重的全球经济大萧条，一次就带来了美国股市十多年的大流势。稍微监管不严又招来了多次金融海啸。这12个人开开会动动嘴皮子决策就能影响全球经济。而就是这么重要的机构，它竟然还有股东，每年还会分红。"

技法拆解：排比式权力渲染（大萧条→金融海啸→12个人），最后用反直觉事实（有股东、分红）制造悬念。

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

## 核心叙事技巧库（每段可灵活调用，附真实示例）

### 1. 抽象数据两步翻译法
先给大数字，再换算成生活化感知。示例：
> "国债比GDP 206%，冠绝全球。这个数字是什么概念？就是日本所有人赚的钱，2.6年才够还他政府的债。你要是按日本政府2022年财政收入算，那他就是不吃不喝，完全不花钱，一分钱也不花，18年才能还清这些债。"

注意"不吃不喝，完全不花钱，一分钱也不花"这种修辞堆叠——让数字从理性认知变成身体感受。

### 2. 用历史因果链驱动理论
不是"理论是什么"，而是"什么危机逼出了这个理论"。把理论嵌入历史叙事，观众不知不觉就学会了。

### 3. 对偶标签法
一对标签抓住本质区别。如"内债是缓冲器，外债是放大器"。给观众一个可以带走的思维工具。

### 4. 先给解药再揭短
"政府可以借钱花钱，促进就业刺激经济——但这么无止境的借下去肯定不合理。因为它具备一个你我都不具备的能力——印钱。" 先给出解决方案让观众放松，再揭示更深限制。

### 5. 共情式视角转换
让观众站在决策者的角度看问题。"站在鲍威尔的鞋里看"——把观众从评论者变成模拟决策者。

### 6. 搭建预期→摧毁预期
先花篇幅搭建理论预期（降息→股市涨/美元跌），再用历史数据逐条摧毁。预期搭得越认真，摧毁时的冲击越大。

### 7. 一词定调法
用一个标签统领整段分析。如用"拧巴"定义日本经济——后续所有现象都围绕这个词展开。

### 8. 段落转折的黄金句式
示例：
> "好那你说，就算政府它可以借钱花钱，可以促进就业刺激经济，难道说你就这么无止境的借钱这么花下去吗？对吧，这听着肯定不合理。"

技法：(1) 替观众说出疑问，(2) 认可这个疑问，(3) 话锋一转引出新知识。

### 9. 冷知识彩蛋
不影响主线但增加获得感。

### 10. 自造金句做记忆锚点
幽默方式自造名言让核心结论难忘。

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
3. **每段开头要承上启下**：不是生硬切换，要有过渡。参考上面"段落转折的黄金句式"
4. **语气标注**：在关键处用【加重】【停顿】【语速加快】等标注
5. **预估每段时长**：按每分钟约 250 字估算
6. **每个核心数据必须做"两步翻译"**：先给原始数据，再用生活化比喻让观众"感受到"
7. **数据核实标注**：所有具体数字、百分比、人物现任职位、事件最终结果，如果不是来自本次提供的搜索资料，必须在该处加"⚠️（数据待核实）"标注。宁可多标，不可漏标。创作者看到标注后会自行核查替换。
"""


# ============================================================
# 自审 Prompt
# ============================================================

SELF_REVIEW_PROMPT = """\
你是一个严格的脚本审核编辑。请对以下脚本进行自审，检查以下方面：

1. **节奏检查**：是否有连续超过2分钟的纯说教段？是否有段落过短或过长？
2. **风格一致性**：口语化程度是否全篇统一？有没有突然变得书面化的段落？
3. **逻辑断裂**：段落之间的过渡是否顺畅？有没有跳跃感？
4. **开头吸引力**：前30秒是否足够抓人？
5. **结尾力度**：结尾是否有力，有没有虎头蛇尾？
6. **信息密度**：有没有灌水的段落？有没有信息过载的段落？

## 重要输出规则

- 如果脚本质量达标，只需在最开头写"【自审通过】"加一句理由，然后**原文照抄完整脚本**。
- 如果发现问题，**必须输出修改后的完整脚本**（不是只列出问题，不是只改几行，是完整的逐字稿），并在最开头注明修改了哪里。
- **绝对禁止**：只输出摘要、只输出批注、只输出部分段落——必须是可以直接交给创作者念的完整口播稿。

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

        result = self.call_llm(OUTLINE_SYSTEM_PROMPT, user_prompt)

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

        # 第一轮：生成初稿
        self._log("生成初稿...")
        draft = self.call_llm(SCRIPT_SYSTEM_PROMPT, user_prompt)

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
