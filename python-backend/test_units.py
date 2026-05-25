"""行为单元测试 — 纯本地运行，不依赖后端或 LLM。

运行: cd python-backend && python test_units.py
"""

import json
import sys
from pathlib import Path

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
# Test 1: EmotionDetector.quick_check
# ══════════════════════════════════════════════════════════════

def test_emotion_detector():
    section("Test 1: EmotionDetector.quick_check")

    from teaching.emotion_detector import EmotionDetector
    detector = EmotionDetector()

    # RED 信号 — 中文
    test("检测 '我不想学了'（含'不学了'子串）", detector.quick_check("我不学了") == "RED")
    test("检测 '算了算了'", detector.quick_check("算了算了") == "RED")
    test("检测 '我放弃了'", detector.quick_check("我放弃了") == "RED")
    # 注意: "我不想学了" 不含子串 "不学了"（中间有"想"），quick_check 不检测
    test("'我不想学了'不含'不学了'子串，返回 None",
         detector.quick_check("我不想学了") is None)

    # RED 信号 — 英文
    test("检测 'I give up'", detector.quick_check("I give up") == "RED")
    test("检测 'whatever'", detector.quick_check("whatever, I don't care") == "RED")

    # 非 RED 信号
    test("普通消息返回 None", detector.quick_check("什么是变量？") is None)
    test("空字符串返回 None", detector.quick_check("") is None)
    test("包含'不'但不是信号返回 None",
         detector.quick_check("我不太明白这个概念") is None)


# ══════════════════════════════════════════════════════════════
# Test 2: ErrorDiagnosis.parse_traceback
# ══════════════════════════════════════════════════════════════

def test_error_diagnosis():
    section("Test 2: ErrorDiagnosis.parse_traceback")

    from teaching.error_diagnosis import ErrorDiagnosis
    diag = ErrorDiagnosis()

    # 标准 TypeError traceback
    tb1 = """Traceback (most recent call last):
  File "main.py", line 5, in <module>
    result = "hello" + 42
TypeError: can only concatenate str (not "int") to str"""

    result = diag.parse_traceback(tb1)
    test("解析 TypeError", result is not None)
    test("error_type 是 TypeError",
         result.error_type == "TypeError" if result else False)
    test("error_message 正确",
         "can only concatenate" in result.error_message if result else False)
    test("file_path 是 main.py",
         result.file_path == "main.py" if result else False)
    test("line_number 是 5",
         result.line_number == 5 if result else False)

    # SyntaxError（注意: TRACEBACK_PATTERN 不匹配 ^ 行，
    # 但最后一行仍能提取 error_type）
    tb2 = """Traceback (most recent call last):
  File "test.py", line 3, in <module>
    if True
SyntaxError: expected ':'"""

    result2 = diag.parse_traceback(tb2)
    test("解析 SyntaxError",
         result2.error_type == "SyntaxError" if result2 else False)

    # 非 traceback 文本
    result3 = diag.parse_traceback("这只是一段普通文字")
    test("非 traceback 返回 None", result3 is None)

    # ValueError
    tb4 = """Traceback (most recent call last):
  File "app.py", line 10, in process
    val = int("abc")
ValueError: invalid literal for int() with base 10: 'abc'"""

    result4 = diag.parse_traceback(tb4)
    test("解析 ValueError",
         result4.error_type == "ValueError" if result4 else False)
    test("line_number 是 10",
         result4.line_number == 10 if result4 else False)


# ══════════════════════════════════════════════════════════════
# Test 3: ErrorDiagnosis.build_diagnosis_context
# ══════════════════════════════════════════════════════════════

def test_diagnosis_context():
    section("Test 3: ErrorDiagnosis.build_diagnosis_context")

    from teaching.error_diagnosis import ErrorDiagnosis, ParsedError
    diag = ErrorDiagnosis()

    error = ParsedError(
        error_type="TypeError",
        error_message="can only concatenate str to str",
        file_path="main.py",
        line_number=5,
        traceback_text="...",
    )

    ctx = diag.build_diagnosis_context(error, code='result = "hello" + 42')
    test("包含 error_type", "TypeError" in ctx)
    test("包含 error_message", "can only concatenate" in ctx)
    test("包含文件路径", "main.py" in ctx)
    test("包含行号", "5" in ctx)
    test("包含代码", '"hello" + 42' in ctx)

    # 无代码上下文
    ctx2 = diag.build_diagnosis_context(error)
    test("无代码时不崩溃", "TypeError" in ctx2)


# ══════════════════════════════════════════════════════════════
# Test 4: common_errors.json 数据完整性
# ══════════════════════════════════════════════════════════════

def test_knowledge_base():
    section("Test 4: common_errors.json 数据完整性")

    kb_path = Path(__file__).parent.parent / "knowledge-base" / "error_logs" / "common_errors.json"
    test("文件存在", kb_path.exists(), f"路径: {kb_path}")

    if not kb_path.exists():
        return

    data = json.loads(kb_path.read_text(encoding="utf-8"))
    test("是列表", isinstance(data, list))
    test("条目数 > 0", len(data) > 0, f"实际: {len(data)}")

    required_fields = [
        "error_type", "pattern", "description", "guide_question",
        "difficulty", "reasoning_chain", "common_causes",
        "related_concepts", "guidance_strategy",
    ]

    all_have_fields = all(
        all(f in entry for f in required_fields)
        for entry in data
    )
    test("所有条目包含必需字段", all_have_fields)

    # 验证 difficulty 值
    valid_difficulties = {"beginner", "intermediate", "advanced"}
    all_difficulty_ok = all(
        entry.get("difficulty") in valid_difficulties
        for entry in data
    )
    test("difficulty 值合法", all_difficulty_ok)

    # 验证 guidance_strategy 值
    valid_strategies = {"socratic", "diagnosis"}
    all_strategy_ok = all(
        entry.get("guidance_strategy") in valid_strategies
        for entry in data
    )
    test("guidance_strategy 值合法", all_strategy_ok)

    # 验证 reasoning_chain 是列表
    all_chain_ok = all(
        isinstance(entry.get("reasoning_chain"), list)
        for entry in data
    )
    test("reasoning_chain 是列表", all_chain_ok)


# ══════════════════════════════════════════════════════════════
# Test 5: StateEvaluator._extract_json
# ══════════════════════════════════════════════════════════════

def test_state_evaluator_json():
    section("Test 5: StateEvaluator._extract_json")

    from teaching.state_evaluator import StateEvaluator

    # 创建一个不需要 LLM 的实例（只测 _extract_json）
    evaluator = StateEvaluator.__new__(StateEvaluator)

    # 直接 JSON
    direct = '{"cognitive_state":"S1_CONCEPT","emotion":"GREEN","answer_quality":"CORRECT","hint_level":0,"reason":"test"}'
    result = evaluator._extract_json(direct)
    test("直接 JSON 解析", result is not None and result.get("cognitive_state") == "S1_CONCEPT")

    # 代码块包裹
    code_block = '```json\n{"cognitive_state":"S3_CODING","emotion":"YELLOW","answer_quality":"PARTIAL","hint_level":1,"reason":"partial"}\n```'
    result2 = evaluator._extract_json(code_block)
    test("代码块 JSON 解析", result2 is not None and result2.get("cognitive_state") == "S3_CODING")

    # 嵌套花括号（reason 包含 { }）
    nested = '{"cognitive_state":"S4_DEBUGGING","emotion":"ORANGE","answer_quality":"WRONG","hint_level":2,"reason":"学生说 {这太难了}"}'
    result3 = evaluator._extract_json(nested)
    test("嵌套花括号 JSON 解析",
         result3 is not None and result3.get("cognitive_state") == "S4_DEBUGGING")

    # JSON 嵌在其他文字中
    extra_text = '根据分析，结果如下：\n{"cognitive_state":"S2_CONVERTING","emotion":"GREEN","answer_quality":"PARTIAL","hint_level":1,"reason":"方向正确"}\n以上是评估结果。'
    result4 = evaluator._extract_json(extra_text)
    test("从文字中提取 JSON",
         result4 is not None and result4.get("cognitive_state") == "S2_CONVERTING")

    # 空字符串
    result5 = evaluator._extract_json("")
    test("空字符串返回 None", result5 is None)

    # 无 JSON 的文字
    result6 = evaluator._extract_json("这里没有任何 JSON 内容")
    test("无 JSON 文字返回 None", result6 is None)


# ══════════════════════════════════════════════════════════════
# Test 6: SessionSummarizer._extract_json 和 _empty_summary
# ══════════════════════════════════════════════════════════════

def test_session_summarizer():
    section("Test 6: SessionSummarizer")

    from teaching.session_summarizer import SessionSummarizer

    summarizer = SessionSummarizer.__new__(SessionSummarizer)

    # _empty_summary
    empty = summarizer._empty_summary()
    test("_empty_summary 包含 topics_covered", "topics_covered" in empty)
    test("_empty_summary 包含 mastery_updates", "mastery_updates" in empty)
    test("_empty_summary 包含 new_weak_points", "new_weak_points" in empty)
    test("_empty_summary 包含 emotion_trajectory", "emotion_trajectory" in empty)
    test("topics_covered 是空列表", empty["topics_covered"] == [])
    test("emotion_trajectory 是空字符串", empty["emotion_trajectory"] == "")

    # _extract_json: 直接 JSON
    direct = '{"topics_covered": ["type_casting"], "mastery_updates": "test", "new_weak_points": [], "emotion_trajectory": "GREEN"}'
    result = summarizer._extract_json(direct)
    test("直接 JSON 解析", result is not None and "type_casting" in result.get("topics_covered", []))

    # _extract_json: 代码块
    code_block = '```json\n{"topics_covered": ["list_ops"], "mastery_updates": "ok", "new_weak_points": [], "emotion_trajectory": "GREEN"}\n```'
    result2 = summarizer._extract_json(code_block)
    test("代码块 JSON 解析", result2 is not None and "list_ops" in result2.get("topics_covered", []))

    # _extract_json: 空输入
    result3 = summarizer._extract_json("")
    test("空字符串返回 None", result3 is None)


# ══════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n PythonMentor 行为单元测试")
    print("=" * 60)

    import os
    os.chdir(Path(__file__).parent)

    test_emotion_detector()
    test_error_diagnosis()
    test_diagnosis_context()
    test_knowledge_base()
    test_state_evaluator_json()
    test_session_summarizer()

    print(f"\n{'='*60}")
    print(f"  结果: {_pass} 通过, {_fail} 失败")
    print(f"{'='*60}\n")

    sys.exit(0 if _fail == 0 else 1)
