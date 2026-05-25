"""端到端集成测试 — 通过 HTTP 测试完整 API 链路。

需要后端运行: cd python-backend && python main.py
然后: python test_integration.py

也可用 TestClient 无需启动服务器（自动模式）。
"""

import json
import sys
import time
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"

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


def check_server():
    """检查后端是否在运行。"""
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
# Test 1: 健康检查
# ══════════════════════════════════════════════════════════════

def test_health():
    section("Test 1: 健康检查")
    r = httpx.get(f"{BASE_URL}/health", timeout=5)
    test("状态码 200", r.status_code == 200)
    data = r.json()
    test("返回 status=ok", data.get("status") == "ok")


# ══════════════════════════════════════════════════════════════
# Test 2: /api/chat 流式对话 + 会话持久化
# ══════════════════════════════════════════════════════════════

def test_chat_stream():
    section("Test 2: /api/chat 流式对话 + 会话持久化")

    student_id = "integration_test"

    # 清理旧会话
    httpx.post(f"{BASE_URL}/api/chat/clear?student_id={student_id}", timeout=5)

    # 发送消息（SSE 流式）
    with httpx.stream(
        "POST",
        f"{BASE_URL}/api/chat",
        json={"message": "什么是变量？", "student_id": student_id},
        timeout=120,
    ) as r:
        test("状态码 200", r.status_code == 200)
        test("Content-Type 是 text/event-stream",
             "text/event-stream" in r.headers.get("content-type", ""))

        tokens = []
        done = False
        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            data = json.loads(line[6:])
            if data.get("token"):
                tokens.append(data["token"])
            if data.get("done"):
                done = True

        test("收到 token", len(tokens) > 0, f"token 数: {len(tokens)}")
        test("收到 done 信号", done)

    # 验证会话文件已创建
    session_file = Path("data/sessions") / f"{student_id}.jsonl"
    test("会话持久化文件已创建", session_file.exists())

    if session_file.exists():
        lines = session_file.read_text(encoding="utf-8").strip().splitlines()
        test("会话文件有消息", len(lines) >= 3, f"行数: {len(lines)}")

    return student_id


# ══════════════════════════════════════════════════════════════
# Test 3: /api/chat/end 会话结束流程
# ══════════════════════════════════════════════════════════════

def test_chat_end(student_id: str):
    section("Test 3: /api/chat/end 会话结束流程")

    r = httpx.post(
        f"{BASE_URL}/api/chat/end",
        json={"student_id": student_id},
        timeout=120,
    )
    test("状态码 200", r.status_code == 200)

    data = r.json()
    test("返回 status=ok", data.get("status") == "ok")
    test("返回 summary", "summary" in data)

    summary = data.get("summary", {})
    test("summary 包含 topics_covered", "topics_covered" in summary)
    test("summary 包含 mastery_updates", "mastery_updates" in summary)
    test("summary 包含 new_weak_points", "new_weak_points" in summary)
    test("summary 包含 emotion_trajectory", "emotion_trajectory" in summary)

    # 验证画像更新
    profile_path = Path("data/profiles") / f"{student_id}.json"
    if profile_path.exists():
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        test("画像包含 emotion_trajectory 字段", "emotion_trajectory" in profile)
        test("画像包含 mastery_updates 字段", "mastery_updates" in profile)

    # 验证会话已删除
    r2 = httpx.post(
        f"{BASE_URL}/api/chat/end",
        json={"student_id": student_id},
        timeout=10,
    )
    test("再次 end 返回 no_session", r2.json().get("status") == "no_session")

    # 验证会话文件已删除
    session_file = Path("data/sessions") / f"{student_id}.jsonl"
    test("会话持久化文件已删除", not session_file.exists())


# ══════════════════════════════════════════════════════════════
# Test 4: /api/knowledge/search 知识检索
# ══════════════════════════════════════════════════════════════

def test_knowledge_search():
    section("Test 4: /api/knowledge/search 知识检索")

    r = httpx.get(
        f"{BASE_URL}/api/knowledge/search",
        params={"q": "变量类型转换", "error_type": ""},
        timeout=30,
    )
    test("状态码 200", r.status_code == 200)

    data = r.json()
    test("返回 results 列表", isinstance(data.get("results"), list))
    test("结果非空", len(data.get("results", [])) > 0, f"结果数: {len(data.get('results', []))}")

    if data.get("results"):
        first = data["results"][0]
        test("结果包含 text 字段", "text" in first)
        test("结果包含 source 字段", "source" in first)
        test("结果包含 distance 字段", "distance" in first)
        test("source 是 knowledge 或 history",
             first.get("source") in ("knowledge", "history"))


# ══════════════════════════════════════════════════════════════
# Test 5: /api/state 画像接口
# ══════════════════════════════════════════════════════════════

def test_state():
    section("Test 5: /api/state 画像接口")

    r = httpx.get(f"{BASE_URL}/api/state/default", timeout=5)
    test("状态码 200", r.status_code == 200)

    data = r.json()
    test("包含 student_id", "student_id" in data)
    test("包含 current_state", "current_state" in data)
    test("包含 message_count", "message_count" in data)


# ══════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n PythonMentor 端到端集成测试")
    print("=" * 60)

    if not check_server():
        print("\n[ERROR] 后端未运行。请先启动: cd python-backend && python main.py")
        sys.exit(1)

    print("  后端已连接")

    test_health()
    student_id = test_chat_stream()
    test_chat_end(student_id)
    test_knowledge_search()
    test_state()

    print(f"\n{'='*60}")
    print(f"  结果: {_pass} 通过, {_fail} 失败")
    print(f"{'='*60}\n")

    sys.exit(0 if _fail == 0 else 1)
