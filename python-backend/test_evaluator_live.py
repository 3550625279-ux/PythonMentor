"""Live test: StateEvaluator with Xiaomi API (ThinkingBlock handling)"""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

async def main():
    from config import settings
    from llm import get_provider
    from teaching.cognitive_state import StudentProfile, CognitiveState, EmotionLevel
    from teaching.state_evaluator import StateEvaluator

    provider = get_provider()
    evaluator = StateEvaluator(provider)
    profile = StudentProfile(student_id="test-student-001")

    print("=== Test 1: Simple concept question ===")
    print("Input: 'Python 列表和元组有什么区别？'")
    result = await evaluator.evaluate(profile, "Python 列表和元组有什么区别？")
    print(f"Result: {result}")
    print(f"  cognitive_state: {result.get('cognitive_state')}")
    print(f"  emotion: {result.get('emotion')}")
    print(f"  answer_quality: {result.get('answer_quality')}")
    print(f"  hint_level: {result.get('hint_level')}")
    print(f"  reason: {result.get('reason')}")
    print()

    # Apply the evaluation
    evaluator.apply_evaluation(profile, result)
    print(f"After apply: state={profile.current_state.value}, emotion={profile.current_emotion.value}, hint={profile.hint_level}")
    print()

    print("=== Test 2: Debugging scenario ===")
    print("Input: '我的代码报错了：TypeError: cannot unpack non-iterable int'")
    result2 = await evaluator.evaluate(profile, "我的代码报错了：TypeError: cannot unpack non-iterable int")
    print(f"Result: {result2}")
    print(f"  cognitive_state: {result2.get('cognitive_state')}")
    print(f"  emotion: {result2.get('emotion')}")
    print(f"  answer_quality: {result2.get('answer_quality')}")
    print(f"  hint_level: {result2.get('hint_level')}")
    print(f"  reason: {result2.get('reason')}")
    print()

    print("=== Test 3: Frustrated student ===")
    print("Input: '算了，太难了，我不想学了'")
    result3 = await evaluator.evaluate(profile, "算了，太难了，我不想学了")
    print(f"Result: {result3}")
    print(f"  cognitive_state: {result3.get('cognitive_state')}")
    print(f"  emotion: {result3.get('emotion')}")
    print(f"  answer_quality: {result3.get('answer_quality')}")
    print(f"  hint_level: {result3.get('hint_level')}")
    print(f"  reason: {result3.get('reason')}")

    # Check that the default fallback is NOT used
    all_results = [result, result2, result3]
    fallback_count = sum(1 for r in all_results if "评估解析失败" in r.get("reason", ""))
    print(f"\n=== Summary: {fallback_count}/3 used fallback (should be 0) ===")

if __name__ == "__main__":
    asyncio.run(main())
