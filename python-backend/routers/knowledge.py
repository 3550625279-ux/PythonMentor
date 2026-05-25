import asyncio
from fastapi import APIRouter
from rag import get_retriever

router = APIRouter()


@router.get("/knowledge/search")
async def search_knowledge(q: str = "", error_type: str = ""):
    """RAG 知识检索接口。"""
    if not q:
        return {"results": [], "query": q}

    retriever = get_retriever()
    results = await asyncio.to_thread(
        retriever.retrieve,
        query=q,
        top_k=5,
        error_type=error_type or None,
    )
    return {"results": results, "query": q}
