from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import chat, knowledge, state

app = FastAPI(title="PythonMentor Backend", version="0.1.0")

# CORS（VSCode WebView 需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(state.router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok", "llm_backend": settings.llm_backend}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.dev_mode)
