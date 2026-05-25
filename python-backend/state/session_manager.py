import json
import uuid
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(__file__).parent.parent / "data" / "sessions"


@dataclass
class Session:
    """会话对象。"""
    session_id: str
    student_id: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    messages: list[dict] = field(default_factory=list)

    def add_message(self, role: str, content: str):
        """添加一条消息到会话历史。"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        self.last_active = time.time()

    def get_recent_messages(self, n: int = 10) -> list[dict]:
        """获取最近 n 条消息（不含 timestamp）。"""
        recent = self.messages[-n:]
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    def is_expired(self, timeout: float = 3600.0) -> bool:
        """检查会话是否过期（默认 1 小时）。"""
        return (time.time() - self.last_active) > timeout


class SessionManager:
    """会话管理器 — 管理学生对话会话的生命周期。

    活跃会话消息持久化到 data/sessions/{student_id}.jsonl。
    每次 add_message() 时追加写入，服务器重启后可恢复。
    """

    def __init__(self, persist_dir: str | Path = SESSIONS_DIR):
        self.sessions: dict[str, Session] = {}
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._recover_sessions()

    def _session_file(self, student_id: str) -> Path:
        return self.persist_dir / f"{student_id}.jsonl"

    def _save_message(self, student_id: str, session_id: str, role: str, content: str, timestamp: float):
        """追加一条消息到持久化文件。"""
        path = self._session_file(student_id)
        entry = {"type": "message", "session_id": session_id, "role": role, "content": content, "timestamp": timestamp}
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("持久化消息失败 [%s]: %s", student_id, e)

    def _save_meta(self, student_id: str, session_id: str, created_at: float):
        """写入会话元数据（文件首行）。"""
        path = self._session_file(student_id)
        entry = {"type": "meta", "session_id": session_id, "student_id": student_id, "created_at": created_at}
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("持久化元数据失败 [%s]: %s", student_id, e)

    def _recover_sessions(self):
        """从持久化文件恢复未结束的会话。"""
        count = 0
        for path in self.persist_dir.glob("*.jsonl"):
            try:
                lines = path.read_text(encoding="utf-8").strip().splitlines()
                if not lines:
                    continue
                meta = json.loads(lines[0])
                if meta.get("type") != "meta":
                    continue

                student_id = meta["student_id"]
                session_id = meta["session_id"]
                created_at = meta.get("created_at", time.time())

                messages = []
                for line in lines[1:]:
                    entry = json.loads(line)
                    if entry.get("type") == "message":
                        messages.append({
                            "role": entry["role"],
                            "content": entry["content"],
                            "timestamp": entry.get("timestamp", 0),
                        })

                session = Session(
                    session_id=session_id,
                    student_id=student_id,
                    created_at=created_at,
                    last_active=time.time(),
                    messages=messages,
                )
                self.sessions[session_id] = session
                count += 1
            except Exception as e:
                logger.warning("恢复会话失败 [%s]: %s", path.name, e)

        if count:
            logger.info("从文件恢复了 %d 个活跃会话", count)

    def create_session(self, student_id: str) -> Session:
        """创建新会话。"""
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id, student_id=student_id)
        self.sessions[session_id] = session
        self._save_meta(student_id, session_id, session.created_at)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话。"""
        session = self.sessions.get(session_id)
        if session and session.is_expired():
            self._remove_persist_file(session.student_id)
            del self.sessions[session_id]
            return None
        return session

    def get_active_session(self, student_id: str) -> Optional[Session]:
        """获取学生最近的活跃会话。"""
        for session in self.sessions.values():
            if session.student_id == student_id and not session.is_expired():
                return session
        return None

    def get_or_create_session(self, student_id: str) -> Session:
        """获取活跃会话，没有则创建。"""
        session = self.get_active_session(student_id)
        if not session:
            session = self.create_session(student_id)
        return session

    def add_message(self, student_id: str, session: Session, role: str, content: str):
        """添加消息并持久化。"""
        session.add_message(role, content)
        msg = session.messages[-1]
        self._save_message(student_id, session.session_id, role, content, msg["timestamp"])

    def end_session(self, student_id: str, session_id: str = "") -> Optional[Session]:
        """结束并移除学生的活跃会话，返回被移除的会话（供摘要用）。

        如果传入 session_id，只有当活跃会话匹配时才删除（防竞态）。
        """
        session = self.get_active_session(student_id)
        if session:
            if session_id and session.session_id != session_id:
                # 活跃会话已不是要结束的那个（用户已开始新会话），跳过删除
                return None
            self._remove_persist_file(student_id)
            del self.sessions[session.session_id]
        return session

    def _remove_persist_file(self, student_id: str):
        """删除持久化文件。"""
        path = self._session_file(student_id)
        try:
            if path.exists():
                path.unlink()
        except Exception as e:
            logger.warning("删除会话文件失败 [%s]: %s", student_id, e)

    def cleanup_expired(self):
        """清理所有过期会话。"""
        expired_ids = [
            sid for sid, s in self.sessions.items()
            if s.is_expired()
        ]
        for sid in expired_ids:
            self._remove_persist_file(self.sessions[sid].student_id)
            del self.sessions[sid]
        return len(expired_ids)

    def list_sessions(self, student_id: Optional[str] = None) -> list[dict]:
        """列出会话（可按学生 ID 过滤）。"""
        sessions = self.sessions.values()
        if student_id:
            sessions = [s for s in sessions if s.student_id == student_id]
        return [
            {
                "session_id": s.session_id,
                "student_id": s.student_id,
                "created_at": s.created_at,
                "last_active": s.last_active,
                "message_count": len(s.messages),
            }
            for s in sessions
        ]
