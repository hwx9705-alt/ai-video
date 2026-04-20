# knowledge_base — 风格素材库

供 Agent 在 prompt 中动态引用的风格参考库。目前只有小 Lin 说，未来可扩展其他风格作者。

## 目录

```
knowledge_base/
└── xiaolin/
    ├── scripts/          # 小 Lin 原稿（9 份 .md，docx 转换得到）
    └── examples/         # 从原稿 + 用户脉络分析中提炼的 prompt 注入素材
        ├── structures/   # 5 种叙事结构（每个 1 份完整案例）
        ├── techniques/   # 10 种叙事技巧（每个 1 份真实片段 + 技法拆解）
        └── openings/     # 3 种开头钩子
```

## Agent 怎么用

`pipeline/agents/_knowledge.py` 提供三个加载函数：

```python
from agents._knowledge import load_structures, load_techniques, load_openings

# 启动时一次性加载，缓存在模块级变量
# script.py 的 prompt 里有 {STRUCTURES} / {TECHNIQUES} / {OPENINGS} 占位符
prompt = OUTLINE_SYSTEM_PROMPT.replace("{STRUCTURES}", load_structures())
```

**不用 RAG，不做向量检索**。就是 `Path.glob("*.md")` 读所有 .md 文件，拼接成字符串插到 prompt 里。

## 怎么追加新素材

### 追加新原稿
```bash
cp /your/new/小lin说_xxx.docx /home/ubuntu/upload/小lin说文字稿/
cd /home/ubuntu/video-ai/pipeline
venv/bin/python tools/convert_docx.py   # 重跑转换脚本
# 新的 md 自动落到 scripts/
```

### 追加新示例
直接在 `examples/{structures|techniques|openings}/` 下加 .md 文件，按 `NN-名称.md` 命名（数字排序）。模板见已有文件。

### 生效方式
改动后 **重启 Streamlit**（`pm2 restart video-ai`），loader 会重新读取。不做热重载，避免复杂度。

## 为什么外置而不是硬编码

1. **docx 不能直接塞 python 字符串**
2. **素材体量大**：9 份稿 + 18 份示例 ≈ 80 K 字，硬编码 script.py 就爆了
3. **用户会持续追加**：脚本迭代时不用改代码 + commit
4. **多 Agent 未来可共享**：Topic/Research/Storyboard 也可能引用同一批素材

## 文件规范

每个示例 .md 的固定结构：

```markdown
# 结构/技巧/开头名

## 适用场景（或"什么时候用"）
一句话。

## 真实片段（出自《XXX》）
> [真实稿节选 200-400 字]

## 技法拆解
1. …
2. …

## 其他案例（可选）
- ...

## 禁忌
- ❌ …
- ✅ …
```

## 当前缺口 / TODO

- 更多原稿放进 scripts/（欢迎追加：机器人篇深度分析、关税系列等）
- 示例目前从 2 篇脉络分析（国债/美联储/全球经济/关税/降息 + 机器人）提炼，品类够用但深度可以继续充实
