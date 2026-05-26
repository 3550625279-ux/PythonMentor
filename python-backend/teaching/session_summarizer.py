"""会话摘要提取模块。

会话结束时用 LLM 提取结构化摘要，用于写入历史 collection 和更新学生画像。
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """\
你是一个教学会话分析器。分析以下对话，提取结构化摘要。

## 对话内容
{conversation}

## 输出要求
只输出一个 JSON 对象，不要有任何其他文字、解释或 markdown 格式：
{{"topics_covered": ["topic1", "topic2"], "mastery_updates": "一句话描述学生掌握情况变化", "new_weak_points": ["weak1"], "emotion_trajectory": "GREEN→YELLOW→GREEN"}}

- topics_covered: 本次涉及的 Python 知识点（snake_case，如 type_casting, list_operations）
- mastery_updates: 学生理解程度的变化（如"从完全不懂列表推导到能写出基本形式"）
- new_weak_points: 本次发现的薄弱点（如果有的话）
- emotion_trajectory: 情绪变化轨迹（如 "GREEN→YELLOW→GREEN"）

重要：你的回复必须以 {{ 开始，以 }} 结束。不要输出任何其他内容。
"""


class SessionSummarizer:
    """会话摘要提取器。"""

    def __init__(self, llm_provider):
        self.llm = llm_provider

    async def summarize(self, messages: list[dict]) -> dict:
        """从对话消息中提取结构化摘要。

        Args:
            messages: 完整对话消息列表 [{"role": str, "content": str}]

        Returns:
            摘要字典 {topics_covered, mastery_updates, new_weak_points, emotion_trajectory}
        """
        if not messages:
            return self._empty_summary()

        # 构建对话文本（限制长度避免 token 溢出）
        conv_lines = []
        total_len = 0
        for msg in reversed(messages):
            line = f"{msg['role']}: {msg['content'][:300]}"
            if total_len + len(line) > 4000:
                break
            conv_lines.insert(0, line)
            total_len += len(line)

        conversation = "\n".join(conv_lines)
        prompt = SUMMARY_PROMPT.format(conversation=conversation)

        try:
            response = await self.llm.chat(
                messages=[{"role": "user", "content": "提取会话摘要，只输出JSON。回复必须以 { 开始，以 } 结束。"}],
                system=prompt,
                temperature=0.2,
                max_tokens=512,
            )
            result = self._extract_json(response)
            if result:
                return {
                    "topics_covered": result.get("topics_covered", []),
                    "mastery_updates": result.get("mastery_updates", ""),
                    "new_weak_points": result.get("new_weak_points", []),
                    "emotion_trajectory": result.get("emotion_trajectory", ""),
                }
        except Exception as e:
            logger.warning("会话摘要提取失败: %s", e)

        return self._empty_summary()

    def _extract_json(self, text: str) -> dict | None:
        """从 LLM 响应中提取 JSON。"""
        if not text or not text.strip():
            return None
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 括号深度匹配 — 从每个 '{' 开始计算深度，找到对应的 '}'
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
                            if isinstance(result, dict):
                                return result
                        except json.JSONDecodeError:
                            break
                        break

        return None

    def _empty_summary(self) -> dict:
        return {
            "topics_covered": [],
            "mastery_updates": "",
            "new_weak_points": [],
            "emotion_trajectory": "",
        }
