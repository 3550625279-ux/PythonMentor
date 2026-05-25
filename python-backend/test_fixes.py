"""验证 6 个修复的端到端测试脚本。

运行方式: cd python-backend && python test_fixes.py
不需要启动服务器，直接在进程内测试。
"""

import json
import sys
import shutil
import tempfile
from pathlib import Path

# ── 测试工具 ──

_pass = 0
_fail = 0


def test(name: str, condition: bool, detail: str = ""):
    global _pass, _fail
    if condition:
        _pass += 1
        print(f"  [PASS] {name}")
    else:
        _fail += 1
        print(f"  [FAIL] {name} {detail}")


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ══════════════════════════════════════════════════════════════
# Test 1: 会话消息持久化 (Fix 1)
# ══════════════════════════════════════════════════════════════

def test_session_persistence():
    section("Test 1: 会话消息持久化 (Fix 1)")

    from state.session_manager import SessionManager

    tmp_dir = Path(tempfile.mkdtemp(prefix="test_sessions_"))

    try:
        # 创建会话并添加消息
        sm = SessionManager(persist_dir=tmp_dir)
        session = sm.get_or_create_session("student_a")
        sid = session.session_id

        sm.add_message("student_a", session, "user", "你好")
        sm.add_message("student_a", session, "assistant", "你好！有什么可以帮你？")

        # 验证文件存在
        session_file = tmp_dir / "student_a.jsonl"
        test("持久化文件已创建", session_file.exists())

        # 验证文件内容
        lines = session_file.read_text(encoding="utf-8").strip().splitlines()
        test("文件有 3 行（1 meta + 2 message）", len(lines) == 3, f"实际 {len(lines)} 行")

        meta = json.loads(lines[0])
        test("首行是 meta", meta.get("type") == "meta")
        test("meta 包含正确的 student_id", meta.get("student_id") == "student_a")
        test("meta 包含 session_id", "session_id" in meta)

        msg1 = json.loads(lines[1])
        test("第2行是 user message", msg1.get("role") == "user" and msg1.get("type") == "message")

        msg2 = json.loads(lines[2])
        test("第3行是 assistant message", msg2.get("role") == "assistant")

        # 模拟重启：创建新的 SessionManager 实例
        sm2 = SessionManager(persist_dir=tmp_dir)
        restored = sm2.get_active_session("student_a")
        test("重启后会话恢复成功", restored is not None)
        test("恢复的 session_id 一致", restored.session_id == sid if restored else False)
        test("恢复的消息数为 2", len(restored.messages) == 2 if restored else False)
        test("恢复的消息内容正确",
             restored.messages[0]["content"] == "你好" if restored else False)

        # end_session 删除文件
        sm2.end_session("student_a")
        test("end_session 后文件已删除", not session_file.exists())

        # 确认会话已移除
        test("end_session 后会话已移除", sm2.get_active_session("student_a") is None)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════
# Test 2: StudentProfile 新字段 (Fix 3)
# ══════════════════════════════════════════════════════════════

def test_profile_fields():
    section("Test 2: StudentProfile 新字段 (Fix 3)")

    from teaching.cognitive_state import StudentProfile

    p = StudentProfile(student_id="test_fix3")
    test("emotion_trajectory 默认为空字符串", p.emotion_trajectory == "")
    test("mastery_updates 默认为空字符串", p.mastery_updates == "")

    # 模拟 /api/chat/end 写入
    p.emotion_trajectory = "GREEN→YELLOW→GREEN"
    p.mastery_updates = "从完全不懂列表推导到能写出基本形式"

    # 序列化验证
    from state.student_profile import save_profile, load_profile
    save_profile(p)
    loaded = load_profile("test_fix3")
    test("画像保存后可加载", loaded is not None)
    test("emotion_trajectory 持久化正确",
         loaded.emotion_trajectory == "GREEN→YELLOW→GREEN" if loaded else False)
    test("mastery_updates 持久化正确",
         loaded.mastery_updates == "从完全不懂列表推导到能写出基本形式" if loaded else False)

    # 清理
    profile_path = Path("data/profiles/test_fix3.json")
    if profile_path.exists():
        profile_path.unlink()


# ══════════════════════════════════════════════════════════════
# Test 3: knowledge.py DashScope 配置 (Fix 4)
# ══════════════════════════════════════════════════════════════

def test_knowledge_config():
    section("Test 3: knowledge.py DashScope 配置 (Fix 4)")

    from config import settings

    test("embedding_api_key 已配置", bool(settings.embedding_api_key), f"值: {settings.embedding_api_key[:10]}...")
    test("embedding_api_model 已配置", settings.embedding_api_model == "text-embedding-v4")
    test("embedding_dimensions 已配置", settings.embedding_dimensions == 1024)

    # 验证 knowledge.py 的 get_retriever 会传这些参数
    from routers.knowledge import get_retriever as kr_func
    import inspect
    source = inspect.getsource(kr_func)
    test("get_retriever 传 api_key 参数", "api_key" in source)
    test("get_retriever 传 dimensions 参数", "dimensions" in source)


# ══════════════════════════════════════════════════════════════
# Test 4: chat.py 修复验证 (Fix 2, 6)
# ══════════════════════════════════════════════════════════════

def test_chat_fixes():
    section("Test 4: chat.py 修复验证 (Fix 2, 6)")

    import inspect
    from routers import chat

    # Fix 2: end_session 在摘要之后
    source = inspect.getsource(chat.end_session)
    lines = source.splitlines()

    # 找到 end_session 调用和 summarize 调用的行号
    summarize_line = None
    end_session_line = None
    for i, line in enumerate(lines):
        if "summarizer.summarize" in line:
            summarize_line = i
        if "session_manager.end_session" in line:
            end_session_line = i

    test("end_session 在 summarize 之后",
         end_session_line is not None and summarize_line is not None and end_session_line > summarize_line,
         f"summarize@{summarize_line}, end_session@{end_session_line}")

    # Fix 3: emotion_trajectory 写入画像
    test("end_session 包含 emotion_trajectory 写入", "emotion_trajectory" in source)
    test("end_session 包含 mastery_updates 写入", "mastery_updates" in source)

    # Fix 6: _run_critique 接收 session_id
    critique_source = inspect.getsource(chat._run_critique)
    test("_run_critique 接收 session_id 参数", "session_id" in critique_source)


# ══════════════════════════════════════════════════════════════
# Test 5: session_manager 修复验证 (Fix 1 - 代码结构)
# ══════════════════════════════════════════════════════════════

def test_session_manager_structure():
    section("Test 5: SessionManager 结构验证 (Fix 1)")

    import inspect
    from state.session_manager import SessionManager

    # 验证关键方法存在
    test("有 _save_message 方法", hasattr(SessionManager, "_save_message"))
    test("有 _save_meta 方法", hasattr(SessionManager, "_save_meta"))
    test("有 _recover_sessions 方法", hasattr(SessionManager, "_recover_sessions"))
    test("有 _remove_persist_file 方法", hasattr(SessionManager, "_remove_persist_file"))
    test("有 add_message 方法", hasattr(SessionManager, "add_message"))

    # 验证 __init__ 接受 persist_dir 参数
    sig = inspect.signature(SessionManager.__init__)
    test("__init__ 接受 persist_dir 参数", "persist_dir" in sig.parameters)


# ══════════════════════════════════════════════════════════════
# Test 6: VSCode 扩展 deactivate (Fix 5)
# ══════════════════════════════════════════════════════════════

def test_vscode_deactivate():
    section("Test 6: VSCode deactivate 钩子 (Fix 5)")

    ext_path = Path(__file__).parent.parent / "vscode-extension" / "src" / "extension.ts"
    if ext_path.exists():
        content = ext_path.read_text(encoding="utf-8")
        test("deactivate 函数包含 endSession 调用", "endSession" in content)
        test("deactivate 是 async 函数", "async function deactivate" in content or "export async function deactivate" in content)
    else:
        test("extension.ts 文件存在", False, f"路径: {ext_path}")


# ══════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n PythonMentor 修复验证测试")
    print("=" * 60)

    # 确保在正确的工作目录
    import os
    os.chdir(Path(__file__).parent)

    test_session_persistence()
    test_profile_fields()
    test_knowledge_config()
    test_chat_fixes()
    test_session_manager_structure()
    test_vscode_deactivate()

    print(f"\n{'='*60}")
    print(f"  结果: {_pass} 通过, {_fail} 失败")
    print(f"{'='*60}\n")

    sys.exit(0 if _fail == 0 else 1)
