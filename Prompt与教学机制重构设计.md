# PythonMentor Prompt 与教学机制重构设计

## 背景

当前 PythonMentor 的 prompt 系统存在三个问题：

1. **模板太通用** — 三套固定模板（socratic/diagnosis/explain）+ 字符串替换，不管什么错误、什么知识点都用同一套引导方式
2. **状态评估与教学回复割裂** — 两个独立 LLM 调用之间信息传递效率低
3. **没有自我纠正** — LLM 生成的回复可能违反苏格拉底原则（如不小心给答案），系统不检查

本设计基于以下论文洞察：
- "How Do Teachers Create Pedagogical Chatbots?" (CHI 2025) — 教师主动限制 chatbot 能力范围，设计任务特化的引导
- "LLM-as-a-Judge" (EMNLP 2025) — 多维度评估 + 自评机制
- "KAG: Knowledge Augmented Generation" (WWW 2025) — 语义关系检索替代相似度检索
- "Demystifying Long Chain-of-Thought Reasoning" (2025) — 推理链 + 自我纠错
- "Agent Q" (2024) — 自我批评机制

---

## 一、四层 Prompt 动态组装

### 设计思路

将当前的"按模式选模板"改为"按学生状态动态组装"。Prompt 由四层拼装而成：

```
┌─────────────────────────────────────────────┐
│  第 1 层：身份与铁律（永远不变）              │
├─────────────────────────────────────────────┤
│  第 2 层：当前学生状态（结构化注入）          │
├─────────────────────────────────────────────┤
│  第 3 层：RAG 知识检索结果（动态注入）        │
├─────────────────────────────────────────────┤
│  第 4 层：教学策略指令（根据状态动态生成）    │
└─────────────────────────────────────────────┘
```

### 第 1 层：身份与铁律（固定）

```python
IDENTITY_LAYER = """\
你是 PythonMentor，一个 Python 编程教练。

铁律（永远不可违反）：
1. 不直接给答案。你的工作是通过精心设计的问题引导学生自己发现答案。
2. 每次只问一个问题。
3. 问题必须能让学生用一个具体例子、一行代码、或一个推理步骤来回答。
4. 如果学生回答正确 → 推进；回答模糊 → 要求具体化；回答错误 → 引导发现矛盾。
5. 不说"你错了"，用"如果...会怎样？"引导。
6. 回复控制在 3-5 句以内，简洁直接。

例外情况（可以突破铁律）：
- 学生明确要求"直接告诉我吧" — 给出答案后追问一个检验理解的问题
- 纯记忆性问题（len() 怎么用）— 直接回答
- 学生已尝试 3 次以上仍完全卡住 — 给部分思路
- 学生情绪 RED — 先处理情绪，降低难度"""
```

### 第 2 层：学生状态（结构化注入）

不再用自然语言描述，改为结构化信息，让 LLM 自己判断策略：

```python
def build_state_layer(profile: StudentProfile) -> str:
    return f"""\
学生状态：
- 认知阶段：{profile.current_state.value}
- 情绪：{profile.current_emotion.value}
- 提示级别：{profile.hint_level}（0=轻推, 1=针对性提问, 2=部分揭示）
- 已对话轮数：{profile.message_count}
- 已见过的知识点：{', '.join(profile.topics_seen[-5:]) or '无'}
- 常见错误模式：{', '.join(profile.common_mistakes[-3:]) or '无'}"""
```

### 第 3 层：RAG 知识检索结果

从知识库中检索与当前问题最相关的知识片段，包含推理链和引导策略：

```python
def build_knowledge_layer(rag_results: list[dict]) -> str:
    parts = []
    for i, result in enumerate(rag_results, 1):
        part = f"### 相关知识 #{i}\n{result['text']}"
        if result.get('reasoning_chain'):
            part += f"\n\n参考推理链：\n" + "\n".join(result['reasoning_chain'])
        if result.get('guidance_strategy'):
            part += f"\n\n引导策略：\n" + "\n".join(
                f"- {k}: {v}" for k, v in result['guidance_strategy'].items()
            )
        parts.append(part)
    return "\n\n".join(parts) if parts else "（无相关知识检索结果）"
```

### 第 4 层：教学策略指令（动态生成）

根据学生状态动态生成当前应该怎么做：

```python
def generate_strategy(profile: StudentProfile) -> str:
    parts = []

    # 认知阶段对应的引导方向
    stage_guidance = {
        "concept": "用类比和具体例子帮助理解概念，不要要求写代码",
        "converting": "帮学生梳理数据流和伪代码，不要直接给实现",
        "coding": "让学生写完再看，不逐行打断",
        "debugging": "引导学生分析报错，不要直接指出 bug",
    }
    parts.append(stage_guidance.get(profile.current_state.value, ""))

    # 情绪调整
    if profile.current_emotion.value in ("orange", "red"):
        parts.append("学生情绪低落，先处理情绪，降低难度，给更多提示")
    elif profile.current_emotion.value == "yellow":
        parts.append("学生有些沮丧，用鼓励语气，给更具体的方向")

    # 提示级别
    hint_desc = {
        0: "用开放性问题引导（nudge）",
        1: "给更具体的方向或提示（targeted question）",
        2: "可以给部分思路或伪代码（partial reveal）",
    }
    parts.append(f"提示级别：{hint_desc.get(profile.hint_level, '')}")

    # 对话轮数调整
    if profile.message_count > 10:
        parts.append("对话已较长，考虑总结当前进展，给出阶段性结论")

    return "\n".join(f"- {p}" for p in parts if p)
```

### 拼装函数

```python
def assemble_prompt(
    student_state: str,
    knowledge_context: str,
    strategy: str,
) -> str:
    parts = [IDENTITY_LAYER]
    if student_state:
        parts.append(f"## 当前学生状态\n{student_state}")
    if knowledge_context:
        parts.append(f"## 相关知识\n{knowledge_context}")
    if strategy:
        parts.append(f"## 当前教学策略\n{strategy}")
    return "\n\n".join(parts)
```

---

## 二、增强 RAG 知识库

### 当前格式（不足）

```json
{
  "error_type": "TypeError",
  "pattern": "unsupported operand type(s)",
  "description": "尝试对不兼容的类型执行操作",
  "guide_question": "这两个变量的类型分别是什么？"
}
```

问题：只有一个引导问题，没有推理链，没有分步引导策略。

### 新格式

```json
{
  "error_type": "TypeError",
  "pattern": "unsupported operand type(s) for +: 'int' and 'str'",
  "common_causes": [
    "input() 返回 str 未转换",
    "除法 / 返回 float 与 int 混用",
    "f-string 拼接时忘记 str() 转换"
  ],
  "reasoning_chain": [
    "1. 报错信息说 int 和 str 不能做 + 运算",
    "2. 找到 + 运算涉及的两个操作数",
    "3. 分别检查每个操作数的类型",
    "4. 追溯类型不匹配的变量的赋值来源",
    "5. 发现是 input() 返回了字符串",
    "6. 用 int() 或 float() 显式转换即可"
  ],
  "guidance_strategy": {
    "step1_确认理解": "问学生'这个报错信息里，你觉得哪几个词是关键？'",
    "step2_定位问题": "问学生'报错说问题在第 N 行，那一行在做什么？'",
    "step3_检查类型": "问学生'你能告诉我，这一行里每个变量的值分别是什么类型吗？'",
    "step4_追溯来源": "问学生'这个类型不对的变量，它是在哪里被赋值的？'"
  },
  "difficulty": "beginner",
  "related_concepts": ["input()", "type casting", "int()", "float()", "str()"]
}
```

### 知识库扩充计划

除了错误模式，还需要扩充以下内容：

**概念知识**（新文件：`knowledge-base/textbooks/concepts.json`）：
```json
{
  "topic": "input() 函数",
  "key_point": "input() 永远返回字符串，即使用户输入的是数字",
  "common_misconception": "以为 input(5) 会返回整数 5",
  "teaching_examples": [
    {
      "example": "age = input('请输入年龄: ')\nprint(age + 1)",
      "expected_error": "TypeError: can only concatenate str to str",
      "teaching_flow": "先让学生运行 → 看到报错 → 问'age 是什么类型？' → 让学生查 type(age)"
    }
  ]
}
```

**成功引导案例**（新文件：`knowledge-base/teaching_cases/`）：
```json
{
  "case_id": "typeerror_input_001",
  "student_error": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
  "conversation": [
    {"role": "student", "content": "我的代码报错了"},
    {"role": "mentor", "content": "这个报错信息里，你觉得哪几个词是关键？"},
    {"role": "student", "content": "好像说 int 和 str 不能加？"},
    {"role": "mentor", "content": "对。那你能告诉我，第 15 行里 age 的值是从哪来的？它是什么类型？"},
    {"role": "student", "content": "是 input() 返回的... 哦，input() 返回的是字符串！"},
    {"role": "mentor", "content": "试试看怎么解决。"}
  ],
  "outcome": "student_self_resolved",
  "effectiveness": "high"
}
```

---

## 三、自我批评机制

### 流程

```
学生消息 → 状态评估（按需）→ 四层拼装 prompt → LLM 生成回复
                                                      ↓
                                              自我批评检查
                                                      ↓
                                        ┌─ 通过 → 直接返回
                                        └─ 违规 → 修正后返回
```

### 自我批评 Prompt

```python
CRITIQUE_PROMPT = """\
检查以下教学回复是否符合苏格拉底教学原则。

原则：
1. 不直接给出答案或修复代码
2. 每次只问一个问题
3. 不在学生明显沮丧时继续追问
4. 问题要具体可操作，不能太宽泛

学生当前状态：{student_state}

待检查的回复：
{reply}

判断：
- 如果完全符合原则，输出：PASS
- 如果违反了任何一条，输出修正后的回复（保持引导性，去掉泄露的答案部分）

只输出判断结果，不要解释。"""
```

### 调用方式

```python
# 非流式调用，低 temperature，短 max_tokens
critique_result = await provider.chat(
    messages=[{"role": "user", "content": "检查教学回复"}],
    system=CRITIQUE_PROMPT.format(student_state=state_desc, reply=generated_reply),
    temperature=0.1,
    max_tokens=512,
)

if critique_result.strip() == "PASS":
    return generated_reply
else:
    return critique_result  # 修正后的回复
```

### 性能优化

- 自我批评只在**前 5 轮对话**和**每隔 5 轮**执行（与状态评估频率对齐）
- 对于明显合规的回复（如只包含一个问号结尾的短问题），可以跳过批评
- 如果批评结果与原回复差异很小（如只是措辞调整），使用原回复

---

## 四、持久化学生档案

### 当前问题

`student_profiles` 是内存字典，`routers/chat.py` 第 16 行：
```python
student_profiles: dict[str, StudentProfile] = {}
```

服务重启后所有学生数据丢失。

### 设计

新建 `teaching/persistence.py`：

```python
import json
from pathlib import Path
from teaching.cognitive_state import StudentProfile, CognitiveState, EmotionLevel

STORAGE_DIR = Path("./student_data")

def save_profile(profile: StudentProfile):
    """保存学生档案到 JSON 文件"""
    STORAGE_DIR.mkdir(exist_ok=True)
    data = {
        "student_id": profile.student_id,
        "current_state": profile.current_state.value,
        "current_emotion": profile.current_emotion.value,
        "hint_level": profile.hint_level,
        "topics_seen": profile.topics_seen,
        "common_mistakes": profile.common_mistakes,
        "message_count": profile.message_count,
        "state_history": profile.state_history[-50:],  # 保留最近50条
    }
    (STORAGE_DIR / f"{profile.student_id}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def load_profile(student_id: str) -> StudentProfile | None:
    """从 JSON 文件加载学生档案"""
    path = STORAGE_DIR / f"{student_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    profile = StudentProfile(student_id=data["student_id"])
    profile.current_state = CognitiveState(data["current_state"])
    profile.current_emotion = EmotionLevel(data["current_emotion"])
    profile.hint_level = data["hint_level"]
    profile.topics_seen = data["topics_seen"]
    profile.common_mistakes = data["common_mistakes"]
    profile.message_count = data["message_count"]
    profile.state_history = data["state_history"]
    return profile
```

### 在 chat.py 中集成

```python
from teaching.persistence import save_profile, load_profile

# 获取或创建学生档案
profile = student_profiles.get(request.student_id)
if not profile:
    profile = load_profile(request.student_id)  # 先尝试从磁盘加载
    if not profile:
        profile = StudentProfile(student_id=request.student_id)
    student_profiles[request.student_id] = profile

# 每次状态更新后保存
# 在 apply_evaluation() 之后调用 save_profile(profile)
```

---

## 五、改动文件清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `llm/prompts.py` | **重构** | 新增 `assemble_prompt()`、`IDENTITY_LAYER`、`build_state_layer()`、`build_knowledge_layer()`、`generate_strategy()`、`CRITIQUE_PROMPT`；保留旧模板作为 fallback |
| `routers/chat.py` | **修改** | 改用 `assemble_prompt()` 拼装 prompt；加自我批评步骤；集成持久化 |
| `rag/indexer.py` | **修改** | 适配新的知识库 JSON 格式（reasoning_chain、guidance_strategy） |
| `rag/retriever.py` | **修改** | 返回更丰富的检索结果 |
| `knowledge-base/error_logs/common_errors.json` | **扩充** | 补充 reasoning_chain 和 guidance_strategy 字段 |
| 新建 `knowledge-base/textbooks/concepts.json` | **新建** | 概念知识（含教学示例和常见误解） |
| 新建 `knowledge-base/teaching_cases/` | **新建** | 成功引导案例库 |
| 新建 `teaching/strategy.py` | **新建** | 动态策略生成逻辑 |
| 新建 `teaching/persistence.py` | **新建** | 学生档案持久化 |
| `teaching/cognitive_state.py` | **微调** | 可能需要小幅调整以支持持久化序列化/反序列化 |

---

## 六、实施顺序

### Phase 1：核心 prompt 重构（优先级最高）
1. 在 `llm/prompts.py` 中实现四层拼装函数
2. 在 `routers/chat.py` 中切换到新的 prompt 组装方式
3. 测试：对比新旧 prompt 生成的教学回复质量

### Phase 2：增强 RAG 知识库
4. 扩充 `common_errors.json`，加入 reasoning_chain 和 guidance_strategy
5. 新建 `concepts.json` 概念知识库
6. 修改 `rag/indexer.py` 和 `rag/retriever.py` 适配新格式
7. 重建索引：`python -m rag.indexer`

### Phase 3：自我批评机制
8. 在 `llm/prompts.py` 中添加 `CRITIQUE_PROMPT`
9. 在 `routers/chat.py` 中添加自我批评步骤
10. 优化批评频率（不是每条消息都批评）

### Phase 4：持久化 + 教学案例
11. 实现 `teaching/persistence.py`
12. 在 `routers/chat.py` 中集成持久化
13. 收集并整理成功引导案例到 `teaching_cases/`

---

## 七、验证方式

1. **单元测试**：测试 `assemble_prompt()` 的四层拼装逻辑
2. **对比测试**：对同一组学生消息，对比新旧 prompt 生成的回复质量
3. **自我批评测试**：构造违反苏格拉底原则的回复，验证批评机制能正确修正
4. **端到端测试**：启动后端 → 通过 API 发送模拟对话 → 检查回复是否符合预期
5. **持久化测试**：发送消息 → 重启服务 → 再次发送消息 → 验证学生档案是否保留
