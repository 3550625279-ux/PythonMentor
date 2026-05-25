# teaching/emotion_detector.py — 轻量 fallback（可选）

class EmotionDetector:
    """快速情绪预筛（仅用于 LLM 评估前的粗略判断）。"""

    RED_SIGNALS = ["算了", "放弃", "不学了", "give up", "whatever"]

    def quick_check(self, message: str) -> str | None:
        """只检测严重情绪（RED），其他交给 LLM 评估。"""
        if any(s in message for s in self.RED_SIGNALS):
            return "RED"
        return None  # 其他情绪由 LLM 评估
