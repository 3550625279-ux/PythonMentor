"""Capture raw thinking content from Xiaomi API for debugging"""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

async def main():
    from config import settings
    from llm import get_provider
    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key=settings.claude_api_key,
        base_url=settings.claude_base_url,
    )

    test_cases = [
        ("概念问题", "Python 列表和元组有什么区别？"),
        ("调试场景", "我的代码报错了：TypeError: cannot unpack non-iterable int"),
        ("沮丧学生", "算了，太难了，我不想学了"),
    ]

    for name, msg in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {name}")
        print(f"Input: {msg}")
        print(f"{'='*60}")

        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            temperature=0.1,
            system="你是一个教学状态评估器。分析学生的最新回复，判断认知状态和情绪。直接输出你的分析。",
            messages=[{"role": "user", "content": msg}],
        )

        for i, block in enumerate(response.content):
            print(f"\nBlock {i}: type={block.type}")
            if hasattr(block, 'thinking'):
                print(f"  thinking ({len(block.thinking)} chars):")
                print(f"  {block.thinking[:500]}...")
            if hasattr(block, 'text'):
                print(f"  text: {block.text[:300]}")

if __name__ == "__main__":
    asyncio.run(main())
