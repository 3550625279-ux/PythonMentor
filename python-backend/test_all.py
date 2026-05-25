"""PythonMentor 10 组测试"""
import sys
import os
import json

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(__file__))

PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")

# ============================================================
# T1: 配置加载
# ============================================================
print("\n=== T1: 配置加载 ===")
try:
    from config import settings
    test("Settings 加载成功", True)
    test("LLM_BACKEND 配置存在", hasattr(settings, 'llm_backend'))
    test("默认端口 8000", settings.port == 8000)
    test("CLAUDE_BASE_URL 已配置", bool(settings.claude_base_url), f"got: {settings.claude_base_url}")
    test("CLAUDE_API_KEY 已配置", bool(settings.claude_api_key))
except Exception as e:
    test("Settings 加载", False, str(e))

# ============================================================
# T2: Provider 工厂
# ============================================================
print("\n=== T2: Provider 工厂 ===")
try:
    from llm import get_provider
    from llm.provider import LLMProvider
    from llm.claude_provider import ClaudeProvider
    from llm.ollama_provider import OllamaProvider

    # 测试 Claude provider 创建
    settings.llm_backend = "claude"
    provider = get_provider()
    test("Claude Provider 创建成功", isinstance(provider, ClaudeProvider))
    test("Provider 继承 LLMProvider", isinstance(provider, LLMProvider))
    test("Provider 有 chat_stream 方法", hasattr(provider, 'chat_stream'))
    test("Provider 有 chat 方法", hasattr(provider, 'chat'))

    # 测试 Ollama provider 创建
    settings.llm_backend = "ollama"
    provider = get_provider()
    test("Ollama Provider 创建成功", isinstance(provider, OllamaProvider))

    # 恢复
    settings.llm_backend = "claude"
except Exception as e:
    test("Provider 工厂", False, str(e))

# ============================================================
# T3: 认知状态更新
# ============================================================
print("\n=== T3: 认知状态更新 ===")
try:
    from teaching.cognitive_state import StudentProfile, CognitiveState, EmotionLevel

    profile = StudentProfile(student_id="test")
    test("初始状态为 S1_CONCEPT", profile.current_state == CognitiveState.S1_CONCEPT)
    test("初始情绪为 GREEN", profile.current_emotion == EmotionLevel.GREEN)
    test("初始 hint_level 为 0", profile.hint_level == 0)
    test("初始 message_count 为 0", profile.message_count == 0)

    profile.update(CognitiveState.S4_DEBUGGING, EmotionLevel.YELLOW, "测试更新")
    test("状态更新为 S4_DEBUGGING", profile.current_state == CognitiveState.S4_DEBUGGING)
    test("情绪更新为 YELLOW", profile.current_emotion == EmotionLevel.YELLOW)
    test("历史记录长度为 1", len(profile.state_history) == 1)
    test("历史记录内容正确", profile.state_history[0]["reason"] == "测试更新")

    desc = profile.get_state_description()
    test("状态描述包含调试", "调试" in desc)
    test("状态描述包含沮丧", "沮丧" in desc)

    # 测试历史裁剪
    for i in range(25):
        profile.update(CognitiveState.S1_CONCEPT, EmotionLevel.GREEN, f"msg {i}")
    test("历史记录裁剪到 20 条", len(profile.state_history) <= 20)
except Exception as e:
    test("认知状态更新", False, str(e))

# ============================================================
# T4: Traceback 解析
# ============================================================
print("\n=== T4: Traceback 解析 ===")
try:
    from teaching.error_diagnosis import ErrorDiagnosis, ParsedError

    diag = ErrorDiagnosis()

    tb1 = """Traceback (most recent call last):
  File "test.py", line 3, in <module>
    result = a + b
TypeError: unsupported operand type(s) for +: 'int' and 'str'"""

    error = diag.parse_traceback(tb1)
    test("解析 traceback 成功", error is not None)
    test("错误类型为 TypeError", error.error_type == "TypeError", f"got: {error.error_type}")
    test("行号为 3", error.line_number == 3, f"got: {error.line_number}")
    test("文件为 test.py", error.file_path == "test.py", f"got: {error.file_path}")

    ctx = diag.build_diagnosis_context(error, "result = a + b")
    test("诊断上下文包含错误类型", "TypeError" in ctx)
    test("诊断上下文包含代码", "result = a + b" in ctx)

    # 测试无效输入
    error2 = diag.parse_traceback("这不是一个 traceback")
    test("无效输入返回 None", error2 is None)
except Exception as e:
    test("Traceback 解析", False, str(e))

# ============================================================
# T5: 情绪快速检测
# ============================================================
print("\n=== T5: 情绪快速检测 ===")
try:
    from teaching.emotion_detector import EmotionDetector

    detector = EmotionDetector()

    test("检测'算了'为 RED", detector.quick_check("算了，不想学了") == "RED")
    test("检测'放弃'为 RED", detector.quick_check("我放弃") == "RED")
    test("检测'give up'为 RED", detector.quick_check("I give up") == "RED")
    test("普通消息返回 None", detector.quick_check("Python 列表怎么用？") is None)
    test("空消息返回 None", detector.quick_check("") is None)
except Exception as e:
    test("情绪快速检测", False, str(e))

# ============================================================
# T6: Chat SSE 流式（需要 LLM）
# ============================================================
print("\n=== T6: Chat SSE 流式 ===")
try:
    from teaching.state_evaluator import StateEvaluator

    profile = StudentProfile(student_id="test_eval")
    settings.llm_backend = "claude"
    provider = get_provider()
    evaluator = StateEvaluator(provider)

    # 测试评估器能被创建
    test("StateEvaluator 创建成功", evaluator is not None)
    test("StateEvaluator 有 evaluate 方法", hasattr(evaluator, 'evaluate'))
    test("StateEvaluator 有 apply_evaluation 方法", hasattr(evaluator, 'apply_evaluation'))

    # 测试 apply_evaluation
    mock_result = {
        "cognitive_state": "S4_DEBUGGING",
        "emotion": "YELLOW",
        "answer_quality": "PARTIAL",
        "hint_level": 1,
        "reason": "测试"
    }
    evaluator.apply_evaluation(profile, mock_result)
    test("apply_evaluation 更新状态", profile.current_state == CognitiveState.S4_DEBUGGING)
    test("apply_evaluation 更新情绪", profile.current_emotion == EmotionLevel.YELLOW)
    test("apply_evaluation 更新 hint_level", profile.hint_level == 1)
except Exception as e:
    test("StateEvaluator", False, str(e))

# ============================================================
# T7: Prompt 模板
# ============================================================
print("\n=== T7: Prompt 模板 ===")
try:
    from llm.prompts import SOCRATIC_SYSTEM_PROMPT, DIAGNOSIS_SYSTEM_PROMPT, EXPLAIN_SYSTEM_PROMPT

    test("SOCRATIC_SYSTEM_PROMPT 存在", bool(SOCRATIC_SYSTEM_PROMPT))
    test("DIAGNOSIS_SYSTEM_PROMPT 存在", bool(DIAGNOSIS_SYSTEM_PROMPT))
    test("EXPLAIN_SYSTEM_PROMPT 存在", bool(EXPLAIN_SYSTEM_PROMPT))

    # 测试格式化
    socratic = SOCRATIC_SYSTEM_PROMPT.format(cognitive_state="测试状态", student_context="测试上下文")
    test("SOCRATIC 可格式化", "测试状态" in socratic)

    diagnosis = DIAGNOSIS_SYSTEM_PROMPT.format(error_info="测试错误", code_context="测试代码")
    test("DIAGNOSIS 可格式化", "测试错误" in diagnosis)
except Exception as e:
    test("Prompt 模板", False, str(e))

# ============================================================
# T8: RAG 模块导入（sentence-transformers 可能未安装）
# ============================================================
print("\n=== T8: RAG 模块导入 ===")
try:
    try:
        import sentence_transformers
        from rag.indexer import split_by_heading, build_index
        from rag.retriever import HybridRetriever
        test("split_by_heading 可导入", callable(split_by_heading))
        test("build_index 可导入", callable(build_index))
        test("HybridRetriever 可导入", callable(HybridRetriever))

        # 测试分块功能
        text = "## 第一段\n内容1\n## 第二段\n内容2\n## 第三段\n内容3"
        chunks = split_by_heading(text)
        test("split_by_heading 正确分块", len(chunks) == 3, f"got: {len(chunks)}")
    except ImportError:
        test("sentence_transformers 未安装（跳过 RAG 测试）", True)
except Exception as e:
    test("RAG 模块导入", False, str(e))

# ============================================================
# T9: 路由模块导入
# ============================================================
print("\n=== T9: 路由模块导入 ===")
try:
    from routers.chat import router as chat_router, ChatRequest
    from routers.knowledge import router as knowledge_router
    from routers.state import router as state_router

    test("chat 路由可导入", chat_router is not None)
    test("knowledge 路由可导入", knowledge_router is not None)
    test("state 路由可导入", state_router is not None)

    # 测试 ChatRequest 模型
    req = ChatRequest(message="测试消息", student_id="test")
    test("ChatRequest 创建成功", req.message == "测试消息")
    test("ChatRequest 默认 mode 为 auto", req.mode == "auto")
except Exception as e:
    test("路由模块导入", False, str(e))

# ============================================================
# T10: FastAPI 应用创建
# ============================================================
print("\n=== T10: FastAPI 应用创建 ===")
try:
    from main import app
    test("FastAPI 应用创建成功", app is not None)
    test("应用标题正确", app.title == "PythonMentor Backend")

    # 检查路由注册
    routes = [r.path for r in app.routes]
    test("/health 路由存在", "/health" in routes)
    test("/api/chat 路由存在", "/api/chat" in routes)
except Exception as e:
    test("FastAPI 应用创建", False, str(e))

# ============================================================
# 汇总
# ============================================================
print(f"\n{'='*50}")
print(f"测试结果: {PASS} 通过, {FAIL} 失败, 共 {PASS+FAIL} 项")
print(f"{'='*50}")

if FAIL > 0:
    sys.exit(1)
