"""自我批评模块。

用小模型异步检查主模型的回复是否违反教学原则。
违规记录写入 data/violation_log.jsonl，不影响主流程。
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CRITIQUE_PROMPT = """\
你是一个教学合规检查器。检查 AI 助手的回复是否违反以下教学原则。

## 教学原则
1. 不直接给答案 — 应该通过提问引导学生自己发现答案
2. 每次只问一个问题 — 不要一次抛出多个问题
3. 不说"你错了" — 用"如果...会怎样？"引导
4. 简洁 — 回复控制在 3-5 句以内
5. 代码只用于说明概念 — 不给出修复代码（除非学生已尝试 3 次以上）

## 学生消息
{student_message}

## AI 助手回复
{assistant_reply}

## 输出要求
只输出一个 JSON 对象，不要有任何其他文字、解释或 markdown 格式：
{{"compliant": true, "violations": [], "severity": "none"}}

- compliant: true 表示合规，false 表示违反原则
- violations: 违反的具体原则编号列表（如 [1, 4]）
- severity: "none" | "minor" | "major"
- 如果合规，violations 为空列表，severity 为 "none"

重要：你的回复必须以 {{ 开始，以 }} 结束。不要输出任何其他内容。
"""


class Critic:
    """教学合规检查器。

    用小模型（如 qwen2.5:3b）异步检查主模型回复。
    设计为 fire-and-forget：不阻塞主流程，失败静默降级。
    """

    def __init__(self, llm_provider, log_dir: str | Path | None = None):
        self.llm = llm_provider
        if log_dir is None:
            log_dir = Path(__file__).parent.parent / "data"
        self.log_path = Path(log_dir) / "violation_log.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def check(
        self,
        student_message: str,
        assistant_reply: str,
        student_id: str = "unknown",
        session_id: str = "unknown",
    ) -> dict | None:
        """检查回复是否合规。返回检查结果，失败时返回 None。"""
        try:
            prompt = CRITIQUE_PROMPT.format(
                student_message=student_message[:500],
                assistant_reply=assistant_reply[:1000],
            )

            response = await self.llm.chat(
                messages=[{"role": "user", "content": "检查合规性，只输出JSON。回复必须以 { 开始，以 } 结束。"}],
                system=prompt,
                temperature=0.1,
                max_tokens=256,
            )

            result = self._extract_json(response)
            if result and not result.get("compliant", True):
                self._log_violation(
                    student_id=student_id,
                    session_id=session_id,
                    student_message=student_message[:200],
                    assistant_reply=assistant_reply[:500],
                    violations=result.get("violations", []),
                    severity=result.get("severity", "unknown"),
                )
            return result

        except Exception as e:
            logger.debug("批评检查失败（静默降级）: %s", e)
            return None

    def _extract_json(self, text: str) -> dict | None:
        """从 LLM 响应中提取 JSON。"""
        if not text or not text.strip():
            return None
        text = text.strip()

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 从代码块中提取
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

    def _log_violation(self, **kwargs):
        """将违规记录追加到 JSONL 日志。"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.info("记录教学违规: severity=%s, violations=%s",
                        entry.get("severity"), entry.get("violations"))
        except Exception as e:
            logger.warning("写入违规日志失败: %s", e)
