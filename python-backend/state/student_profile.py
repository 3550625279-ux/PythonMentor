import json
import logging
from pathlib import Path
from teaching.cognitive_state import StudentProfile, CognitiveState, EmotionLevel

logger = logging.getLogger(__name__)

# 持久化存储目录
DATA_DIR = Path(__file__).parent.parent / "data" / "profiles"

def _ensure_data_dir():
    """确保数据目录存在。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def _profile_path(student_id: str) -> Path:
    """获取学生档案文件路径。"""
    return DATA_DIR / f"{student_id}.json"

def save_profile(profile: StudentProfile):
    """将学生档案保存到磁盘。"""
    _ensure_data_dir()
    data = {
        "student_id": profile.student_id,
        "current_state": profile.current_state.value,
        "current_emotion": profile.current_emotion.value,
        "state_history": profile.state_history,
        "topics_seen": profile.topics_seen,
        "common_mistakes": profile.common_mistakes,
        "hint_level": profile.hint_level,
        "message_count": profile.message_count,
        "emotion_trajectory": profile.emotion_trajectory,
        "mastery_updates": profile.mastery_updates,
    }
    path = _profile_path(profile.student_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_profile(student_id: str) -> StudentProfile | None:
    """从磁盘加载学生档案。损坏的文件会返回 None 并记录警告。"""
    path = _profile_path(student_id)
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("学生档案损坏，将创建新档案: %s (%s)", path, e)
        return None

    state_map = {
        "concept": CognitiveState.S1_CONCEPT,
        "converting": CognitiveState.S2_CONVERTING,
        "coding": CognitiveState.S3_CODING,
        "debugging": CognitiveState.S4_DEBUGGING,
    }
    emotion_map = {
        "green": EmotionLevel.GREEN,
        "yellow": EmotionLevel.YELLOW,
        "orange": EmotionLevel.ORANGE,
        "red": EmotionLevel.RED,
    }

    profile = StudentProfile(student_id=data.get("student_id", student_id))
    profile.current_state = state_map.get(data.get("current_state", "concept"), CognitiveState.S1_CONCEPT)
    profile.current_emotion = emotion_map.get(data.get("current_emotion", "green"), EmotionLevel.GREEN)
    profile.state_history = data.get("state_history", [])
    profile.topics_seen = data.get("topics_seen", [])
    profile.common_mistakes = data.get("common_mistakes", [])
    profile.hint_level = data.get("hint_level", 0)
    profile.message_count = data.get("message_count", 0)
    profile.emotion_trajectory = data.get("emotion_trajectory", "")
    profile.mastery_updates = data.get("mastery_updates", "")

    return profile

def list_profiles() -> list[str]:
    """列出所有已保存的学生 ID。"""
    _ensure_data_dir()
    return [p.stem for p in DATA_DIR.glob("*.json")]

def delete_profile(student_id: str) -> bool:
    """删除学生档案。"""
    path = _profile_path(student_id)
    if path.exists():
        path.unlink()
        return True
    return False
