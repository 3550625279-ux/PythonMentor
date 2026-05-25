from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from state.student_profile import load_profile, save_profile
from teaching.cognitive_state import CognitiveState

router = APIRouter()


class StateUpdate(BaseModel):
    hint_level: Optional[int] = None
    current_state: Optional[str] = None
    topics_seen: Optional[list[str]] = None


@router.get("/state/{student_id}")
async def get_state(student_id: str):
    """获取学生当前状态。"""
    profile = load_profile(student_id)
    if not profile:
        return {
            "student_id": student_id,
            "exists": False,
            "message": "未找到该学生的档案",
        }

    return {
        "student_id": student_id,
        "exists": True,
        "current_state": profile.current_state.value,
        "current_emotion": profile.current_emotion.value,
        "hint_level": profile.hint_level,
        "message_count": profile.message_count,
        "topics_seen": profile.topics_seen,
        "common_mistakes": profile.common_mistakes,
        "state_history": profile.state_history[-5:],
    }


@router.put("/state/{student_id}")
async def update_state(student_id: str, update: StateUpdate):
    """手动更新学生状态（调试用）。"""
    profile = load_profile(student_id)
    if not profile:
        return {"error": "未找到该学生的档案"}

    if update.hint_level is not None:
        profile.hint_level = max(0, min(2, update.hint_level))

    if update.current_state is not None:
        state_map = {
            "concept": CognitiveState.S1_CONCEPT,
            "converting": CognitiveState.S2_CONVERTING,
            "coding": CognitiveState.S3_CODING,
            "debugging": CognitiveState.S4_DEBUGGING,
        }
        if update.current_state in state_map:
            profile.current_state = state_map[update.current_state]

    if update.topics_seen is not None:
        profile.topics_seen = update.topics_seen

    save_profile(profile)

    return {
        "student_id": student_id,
        "current_state": profile.current_state.value,
        "current_emotion": profile.current_emotion.value,
        "hint_level": profile.hint_level,
        "message": "状态已更新",
    }
