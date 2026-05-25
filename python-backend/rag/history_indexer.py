"""历史交互记录索引模块。

将完成的会话对话写入 ChromaDB collection_history，
用于 RAG 检索时参考学生的历史学习经历。

用法：
    从 routers/chat.py 的会话结束流程中调用。
"""

import chromadb
from rag.embedding_provider import create_embedding_provider


class HistoryIndexer:
    """将会话摘要和对话记录索引到 collection_history。"""

    def __init__(
        self,
        db_path: str,
        model_name: str = "all-MiniLM-L6-v2",
        api_key: str = "",
        api_model: str = "text-embedding-v4",
        api_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        dimensions: int = 1024,
    ):
        self.embedder = create_embedding_provider(
            api_key=api_key, model=api_model, base_url=api_url,
            dimensions=dimensions, fallback_model=model_name,
        )
        client = chromadb.PersistentClient(path=db_path)
        self.collection = client.get_or_create_collection(
            name="collection_history",
            metadata={"hnsw:space": "cosine"},
        )

    def index_session(
        self,
        student_id: str,
        session_id: str,
        messages: list[dict],
        summary: dict,
    ):
        """将完成的会话索引到 collection_history。

        每个会话生成一个文档，包含摘要信息和最近几条对话。

        Args:
            student_id: 学生 ID
            session_id: 会话 ID
            messages: 完整对话消息列表 [{"role": str, "content": str}]
            summary: 会话摘要 {"topics_covered": [], "mastery_updates": str,
                     "new_weak_points": [], "emotion_trajectory": str}
        """
        # 构建文档文本
        text = f"学生 {student_id} 的学习会话\n"
        topics = summary.get("topics_covered", [])
        if topics:
            text += f"涉及主题: {', '.join(topics)}\n"
        mastery = summary.get("mastery_updates", "")
        if mastery:
            text += f"掌握情况: {mastery}\n"
        weak_points = summary.get("new_weak_points", [])
        if weak_points:
            text += f"薄弱点: {', '.join(weak_points)}\n"
        trajectory = summary.get("emotion_trajectory", "")
        if trajectory:
            text += f"情绪轨迹: {trajectory}\n"

        # 包含最近几条对话作为上下文
        recent = messages[-6:]
        if recent:
            text += "\n对话片段:\n"
            for msg in recent:
                role = "学生" if msg["role"] == "user" else "助手"
                text += f"{role}: {msg['content']}\n"

        doc_id = f"session_{session_id}"
        embedding = self.embedder.encode([text])

        self.collection.upsert(
            ids=[doc_id],
            embeddings=embedding,
            documents=[text],
            metadatas=[{
                "student_id": student_id,
                "session_id": session_id,
                "topics": ",".join(topics),
                "type": "session_history",
            }],
        )

    def count(self) -> int:
        """返回 history collection 中的文档数量。"""
        return self.collection.count()
