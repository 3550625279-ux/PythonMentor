import asyncio
import json
import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import settings
from llm import get_provider
from llm.prompts import build_system_prompt
from rag import get_retriever
from state.session_manager import SessionManager
from state.student_profile import save_profile, load_profile
from teaching.cognitive_state import StudentProfile, EmotionLevel
from teaching.state_evaluator import StateEvaluator
from teaching.error_diagnosis import ErrorDiagnosis
from teaching.emotion_detector import EmotionDetector
from teaching.critic import Critic
from teaching.session_summarizer import SessionSummarizer
from rag.history_indexer import HistoryIndexer
from llm import get_critique_provider

router = APIRouter()


async def _run_critique(provider, student_id: str, session_id: str, user_msg: str, reply: str):
    """异步运行批评检查，失败静默跳过。"""
    try:
        critic = Critic(provider)
        await critic.check(
            student_message=user_msg,
            assistant_reply=reply,
            student_id=student_id,
            session_id=session_id,
        )
    except Exception as e:
        logger.debug("批评检查异常（已忽略）: %s", e)

# ── 模块级单例 ──
session_manager = SessionManager()

# 评估频率：前 3 条消息跳过评估，之后每 3 条评估一次
SKIP_EVAL_MESSAGES = 3
EVAL_EVERY_N = 3


class ChatRequest(BaseModel):
    message: str
    student_id: str = "default"
    context: dict = {}
    mode: str = "auto"


@router.post("/chat")
async def chat(request: ChatRequest):
    """主对话端点。流水线：SessionManager → 快速预筛 → RAG → 按需评估 → 教学回复。"""

    provider = get_provider()

    # ── 1. 获取或创建会话 ──
    session = session_manager.get_or_create_session(request.student_id)

    # ── 2. 获取或加载学生档案 ──
    profile = load_profile(request.student_id)
    if profile is None:
        profile = StudentProfile(student_id=request.student_id)
    profile.message_count += 1

    # ── 3. 将用户消息加入会话（持久化到文件）──
    session_manager.add_message(request.student_id, session, "user", request.message)

    # ── 4. 快速情绪预筛 ──
    quick_emotion = EmotionDetector().quick_check(request.message)

    # ── 5. 确定教学模式 ──
    if request.mode == "auto":
        if request.context.get("error_info"):
            mode = "diagnosis"
        elif request.context.get("request_explain"):
            mode = "explain"
        else:
            mode = "socratic"
    else:
        mode = request.mode

    # ── 6. 状态评估（按需）──
    should_evaluate = (
        quick_emotion != "RED"
        and profile.message_count > SKIP_EVAL_MESSAGES
        and (profile.message_count - SKIP_EVAL_MESSAGES) % EVAL_EVERY_N == 0
    )

    if should_evaluate:
        evaluator = StateEvaluator(provider)
        eval_context = ""
        if request.context.get("error_info"):
            eval_context = f"学生遇到了错误:\n{request.context['error_info']}"
        if request.context.get("code"):
            eval_context += f"\n学生当前代码:\n{request.context['code']}"

        eval_result = await evaluator.evaluate(
            profile=profile,
            student_message=request.message,
            context=eval_context,
        )
        evaluator.apply_evaluation(profile, eval_result)

    # ── 7. RAG 检索 ──
    error_diagnosis = ErrorDiagnosis()
    error = None
    if mode == "diagnosis":
        error = error_diagnosis.parse_traceback(request.context.get("error_info", ""))

    retriever = get_retriever()
    try:
        rag_results = await asyncio.to_thread(
            retriever.retrieve,
            query=request.message,
            top_k=3,
            error_type=error.error_type if error else None,
        )
    except Exception as e:
        logger.warning("RAG 检索失败，跳过: %s", e)
        rag_results = []

    # ── 8. 构建 system prompt（四层拼装）──
    state_description = profile.get_state_description()

    if quick_emotion == "RED":
        # 情绪 RED 时强制覆盖状态
        profile.current_emotion = EmotionLevel.RED
        system = build_system_prompt(
            mode="socratic",
            student_profile=profile,
            rag_chunks=rag_results,
        )
    elif mode == "diagnosis":
        error_info = (
            error_diagnosis.build_diagnosis_context(error, request.context.get("code", ""))
            if error
            else request.context.get("error_info", "")
        )
        system = build_system_prompt(
            mode="diagnosis",
            student_profile=profile,
            rag_chunks=rag_results,
            error_info=error_info,
            code_context=request.context.get("code", ""),
        )
    elif mode == "explain":
        system = build_system_prompt(
            mode="explain",
            student_profile=profile,
            rag_chunks=rag_results,
        )
    else:
        system = build_system_prompt(
            mode="socratic",
            student_profile=profile,
            rag_chunks=rag_results,
        )

    # ── 9. 从 Session 获取对话历史，流式调用 LLM ──
    messages = session.get_recent_messages(n=40)

    async def generate():
        yield f"data: {json.dumps({'status': 'thinking'}, ensure_ascii=False)}\n\n"

        full_reply = ""
        try:
            async for token in provider.chat_stream(messages=messages, system=system):
                full_reply += token
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("LLM 流式调用失败: %s", e)
            if not full_reply:
                yield f"data: {json.dumps({'token': '抱歉，AI 服务暂时不可用，请稍后重试。'}, ensure_ascii=False)}\n\n"
        finally:
            # 无论成功失败，都保存已有对话（保护性写入，不阻断 done 信号）
            try:
                if full_reply:
                    session_manager.add_message(request.student_id, session, "assistant", full_reply)
                    # fire-and-forget: 用小模型检查教学合规性
                    critique_provider = get_critique_provider()
                    if critique_provider:
                        asyncio.create_task(_run_critique(
                            critique_provider, request.student_id, session.session_id,
                            request.message, full_reply,
                        ))
                save_profile(profile)
            except Exception as e:
                logger.error("保存会话状态失败: %s", e)

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/chat/clear")
async def clear_chat(student_id: str = "default"):
    """清空指定学生的会话历史。"""
    session = session_manager.get_active_session(student_id)
    if session:
        session.messages.clear()
        session_manager._remove_persist_file(student_id)
    return {"status": "ok", "student_id": student_id}


class EndSessionRequest(BaseModel):
    student_id: str = "default"


@router.post("/chat/end")
async def end_session(request: EndSessionRequest):
    """结束会话：提取摘要 → 写入历史 collection → 更新画像 → 清除内存会话。"""
    provider = get_provider()

    # 1. 取出活跃会话（不立即删除，等摘要完成后再删）
    session = session_manager.get_active_session(request.student_id)
    if not session or not session.messages:
        return {"status": "no_session", "student_id": request.student_id}

    # 2. LLM 提取会话摘要
    summarizer = SessionSummarizer(provider)
    summary = await summarizer.summarize(session.messages)

    # 3. 写入 history collection
    try:
        history_indexer = HistoryIndexer(
            db_path=settings.chroma_db_path,
            model_name=settings.embedding_model,
            api_key=settings.embedding_api_key,
            api_model=settings.embedding_api_model,
            api_url=settings.embedding_api_url,
            dimensions=settings.embedding_dimensions,
        )
        await asyncio.to_thread(
            history_indexer.index_session,
            student_id=request.student_id,
            session_id=session.session_id,
            messages=session.get_recent_messages(n=50),
            summary=summary,
        )
    except Exception as e:
        logger.warning("历史索引写入失败: %s", e)

    # 4. 更新学生画像（将摘要中的所有字段写入）
    profile = load_profile(request.student_id)
    if profile:
        for topic in summary.get("topics_covered", []):
            if topic not in profile.topics_seen:
                profile.topics_seen.append(topic)
        for weak in summary.get("new_weak_points", []):
            if weak not in profile.common_mistakes:
                profile.common_mistakes.append(weak)
        profile.emotion_trajectory = summary.get("emotion_trajectory", "")
        profile.mastery_updates = summary.get("mastery_updates", "")
        save_profile(profile)

    # 5. 摘要+索引+画像全部完成后，才从内存移除会话
    session_manager.end_session(request.student_id, session.session_id)

    return {
        "status": "ok",
        "student_id": request.student_id,
        "summary": summary,
    }
