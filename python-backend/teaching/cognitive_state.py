from enum import Enum
from dataclasses import dataclass, field

class CognitiveState(Enum):
    """认知状态（从 deep-learning-coach-v3 简化）"""
    S1_CONCEPT = "concept"         # 概念理解中：能描述但不能实现
    S2_CONVERTING = "converting"   # 概念→代码转化中：知道要做什么但写不出
    S3_CODING = "coding"           # 代码实现中：能写可运行代码
    S4_DEBUGGING = "debugging"     # 调试中：代码报错或输出异常

class EmotionLevel(Enum):
    GREEN = "green"     # 正常
    YELLOW = "yellow"   # 轻度沮丧
    ORANGE = "orange"   # 中度沮丧
    RED = "red"         # 严重沮丧

@dataclass
class StudentProfile:
    """学生认知档案 — 只记录，不判断。判断由 LLM 完成。"""
    student_id: str
    current_state: CognitiveState = CognitiveState.S1_CONCEPT
    current_emotion: EmotionLevel = EmotionLevel.GREEN

    # LLM 推断的历史记录（不是计数器，是每次推断的完整结果）
    state_history: list[dict] = field(default_factory=list)
    # 格式: [{"state": "S1", "emotion": "green", "reason": "...", "timestamp": "..."}]

    # 学习记录
    topics_seen: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    hint_level: int = 0            # 当前提示级别 (0=nudge, 1=targeted_question, 2=partial_reveal)
    message_count: int = 0

    # 会话摘要字段（由 /api/chat/end 写入）
    emotion_trajectory: str = ""   # 情绪变化轨迹，如 "GREEN→YELLOW→GREEN"
    mastery_updates: str = ""      # 掌握情况变化描述

    def update(self, state: CognitiveState, emotion: EmotionLevel, reason: str):
        """更新状态（由 LLM 推断结果驱动）。"""
        self.current_state = state
        self.current_emotion = emotion
        self.state_history.append({
            "state": state.value,
            "emotion": emotion.value,
            "reason": reason,
        })
        # 只保留最近 20 条历史
        if len(self.state_history) > 20:
            self.state_history = self.state_history[-20:]

    def get_state_description(self) -> str:
        """返回当前状态的自然语言描述，注入 system prompt。"""
        state_desc = {
            CognitiveState.S1_CONCEPT: "学生当前在概念理解阶段。优先用类比和例子解释，不要要求写代码。",
            CognitiveState.S2_CONVERTING: "学生理解了概念但写不出代码。帮他梳理数据流和伪代码，不要直接给实现。",
            CognitiveState.S3_CODING: "学生正在写代码。让他写完再看，不逐行打断。有问题等他写完一个模块再指出。",
            CognitiveState.S4_DEBUGGING: "学生在调试。引导他分析报错类型和位置，不要直接指出 bug。",
        }
        emotion_desc = {
            EmotionLevel.GREEN: "",
            EmotionLevel.YELLOW: "学生可能有些沮丧。用鼓励的语气，降低问题难度，给更多提示。",
            EmotionLevel.ORANGE: "学生明显沮丧。建议切换活动或休息，不要继续追问。",
            EmotionLevel.RED: "学生情绪低落。立即停止追问，先处理情绪，建议休息。",
        }
        hint_desc = {
            0: "当前提示级别：nudge（轻推）。先问开放性问题。",
            1: "当前提示级别：targeted_question（针对性提问）。给一个更具体的方向。",
            2: "当前提示级别：partial_reveal（部分揭示）。可以给出部分思路或伪代码。",
        }
        desc = state_desc.get(self.current_state, "")
        desc += "\n" + emotion_desc.get(self.current_emotion, "")
        desc += "\n" + hint_desc.get(self.hint_level, "")
        return desc.strip()
