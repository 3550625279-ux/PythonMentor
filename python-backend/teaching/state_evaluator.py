import json
import logging
import re
from teaching.cognitive_state import StudentProfile, CognitiveState, EmotionLevel

logger = logging.getLogger(__name__)

# ============================================================
# 评估 prompt — 设计原则：
# 1. 指令清晰，减少歧义
# 2. 强制 JSON 输出，减少后处理
# 3. 提供判断标准而非关键词，让 LLM 做判断
# ============================================================
EVALUATION_PROMPT = """\
你是一个精准的教学状态评估器。分析学生回复，输出 JSON。

## 学生最近对话历史
{history}

## 学生最新回复
{student_message}

## 额外上下文
{context}

## 评估维度和判断标准

### 认知状态
判断学生当前处于哪个阶段：
- S1_CONCEPT: 学生在讨论概念、原理、定义或区别，没有涉及具体代码实现
- S2_CONVERTING: 学生理解了要做什么，但无法将想法转化为代码
- S3_CODING: 学生正在编写或已经写出可运行的代码
- S4_DEBUGGING: 学生的代码有错误，或输出不符合预期，正在排查问题

### 情绪状态
判断学生的沮丧程度：
- GREEN: 学生状态正常，积极学习，没有表现出任何沮丧
- YELLOW: 学生表现出轻微不确定，用词变得模糊（如"大概"、"应该吧"）
- ORANGE: 学生明确表达困难（如"太难了"、"搞不懂"），或同一问题反复询问
- RED: 学生表达放弃意愿（如"算了"、"不想学了"），或明显在逃避问题

### 回答质量
判断学生回答的准确程度：
- CORRECT: 回答准确，包含具体细节或代码
- PARTIAL: 方向正确但不完整，或有小偏差
- VAGUE: 回答模糊、空洞，缺乏具体内容
- WRONG: 方向性错误，核心理解有误

### 提示级别
根据学生状态决定下一步教学策略：
- 0: 学生状态好，用开放性问题引导
- 1: 学生有些卡住，给更具体的方向或提示
- 2: 学生严重卡住，可以给部分思路或伪代码

## 输出要求
只输出一个 JSON 对象，不要有任何其他文字、解释或 markdown 格式：
{{"cognitive_state":"S1_CONCEPT","emotion":"GREEN","answer_quality":"CORRECT","hint_level":0,"reason":"一句话说明判断依据","topic":"type_casting"}}

topic 字段：用 snake_case 标识学生当前在学的知识点（如 type_casting, list_operations, loop_control, function_basics 等）。如果无法判断，填 ""。

重要：你的回复必须以 {{ 开始，以 }} 结束。不要输出任何其他内容。
"""


class StateEvaluator:
    """LLM 驱动的状态评估器。

    设计哲学：让 LLM 做判断，不做硬编码规则匹配。
    JSON 提取只处理常见的 LLM 输出格式问题（代码块、多余文字等），
    不做关键词推断 — 如果 LLM 没有返回有效 JSON，使用合理的默认值。
    """

    def __init__(self, llm_provider):
        self.llm = llm_provider

    async def evaluate(
        self,
        profile: StudentProfile,
        student_message: str,
        context: str = "",
    ) -> dict:
        """用 LLM 评估学生的认知状态和情绪。"""
        # 构建历史摘要（最近 5 条）
        recent = profile.state_history[-5:] if profile.state_history else []
        history_text = "\n".join(
            f"- 认知:{h['state']} 情绪:{h['emotion']} | {h['reason']}"
            for h in recent
        ) or "（无历史记录，这是第一次对话）"

        prompt = EVALUATION_PROMPT.format(
            history=history_text,
            student_message=student_message,
            context=context or "（无额外上下文）",
        )

        # 调用 LLM（非流式，低温度保证稳定性）
        response = await self.llm.chat(
            messages=[{"role": "user", "content": "分析学生状态，只输出JSON。回复必须以 { 开始，以 } 结束。"}],
            system=prompt,
            temperature=0.1,
            max_tokens=2048,
        )

        # 提取 JSON
        result = self._extract_json(response)

        # 如果提取失败，使用当前状态作为默认值（不猜测）
        if result is None:
            result = {
                "cognitive_state": profile.current_state.value,
                "emotion": profile.current_emotion.value,
                "answer_quality": "PARTIAL",
                "hint_level": profile.hint_level,
                "reason": "评估未返回有效JSON，保持当前状态",
            }

        return result

    def _extract_json(self, text: str) -> dict | None:
        """从 LLM 响应中提取 JSON。

        处理常见的 LLM 输出格式问题：
        1. 代码块包裹的 JSON
        2. 直接输出的 JSON
        3. JSON 嵌在其他文字中
        4. 包含嵌套花括号的 JSON
        """
        if not text or not text.strip():
            logger.warning("评估器收到空响应")
            return None

        text = text.strip()

        # 策略 1: 从代码块中提取
        code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 策略 2: 直接解析整个响应
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 策略 3: 用正则找 JSON 对象（匹配包含目标字段的简单花括号）
        json_pattern = re.compile(
            r'\{[^{}]*"cognitive_state"\s*:\s*"[^"]*"[^{}]*\}',
            re.DOTALL
        )
        matches = list(json_pattern.finditer(text))
        if matches:
            for match in reversed(matches):
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue

        # 策略 4: 括号深度匹配 — 从每个 '{' 开始计算深度，找到对应的 '}'
        # 解决嵌套花括号问题（如 reason 字段包含 { 或 }）
        for i in range(len(text) - 1, -1, -1):
            if text[i] == '{':
                depth = 0
                for j in range(i, len(text)):
                    if text[j] == '{':
                        depth += 1
                    elif text[j] == '}':
                        depth -= 1
                    if depth == 0:
                        candidate = text[i:j + 1]
                        try:
                            result = json.loads(candidate)
                            if isinstance(result, dict) and "cognitive_state" in result:
                                return result
                        except json.JSONDecodeError:
                            break
                        break

        logger.warning("评估器 JSON 提取全部失败，原始响应: %s", text[:500])
        return None

    def apply_evaluation(self, profile: StudentProfile, result: dict):
        """将 LLM 评估结果应用到学生档案。"""
        state_map = {
            "S1_CONCEPT": CognitiveState.S1_CONCEPT,
            "S2_CONVERTING": CognitiveState.S2_CONVERTING,
            "S3_CODING": CognitiveState.S3_CODING,
            "S4_DEBUGGING": CognitiveState.S4_DEBUGGING,
        }
        emotion_map = {
            "GREEN": EmotionLevel.GREEN,
            "YELLOW": EmotionLevel.YELLOW,
            "ORANGE": EmotionLevel.ORANGE,
            "RED": EmotionLevel.RED,
        }

        new_state = state_map.get(result["cognitive_state"], profile.current_state)
        new_emotion = emotion_map.get(result["emotion"], profile.current_emotion)
        new_hint = result.get("hint_level", profile.hint_level)

        profile.update(new_state, new_emotion, result.get("reason", ""))
        profile.hint_level = max(0, min(2, new_hint))

        # 追踪知识点
        topic = result.get("topic", "")
        if topic and topic not in profile.topics_seen:
            profile.topics_seen.append(topic)

        # 追踪常见错误（answer_quality=WRONG 时记录）
        answer_quality = result.get("answer_quality", "")
        if answer_quality == "WRONG" and result.get("reason"):
            mistake = result["reason"][:100]
            if mistake not in profile.common_mistakes:
                profile.common_mistakes.append(mistake)
                if len(profile.common_mistakes) > 20:
                    profile.common_mistakes = profile.common_mistakes[-20:]
