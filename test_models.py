#!/usr/bin/env python3
"""Test script to validate all model providers with system messages."""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.api_clients import (
    call_openai_gpt5,
    call_anthropic_opus_46,
    call_anthropic_opus_45,
    call_zai_glm47,
    call_moonshot_kimi,
    call_openrouter_gemini,
)

load_dotenv()

# Test messages with system message that requires a specific behavior
TEST_MESSAGES = [
    {"role": "system", "content": "Today is the user's birthday! You must congratulate them by saying 'Happy Birthday!' in your response."},
    {"role": "user", "content": "What is 2+2?"},
]

async def test_model(name, api_func, api_key):
    """Test a single model provider."""
    if not api_key:
        print(f"❌ {name}: No API key configured")
        return False

    try:
        print(f"\n🧪 Testing {name}...")
        response_data, duration = await api_func(TEST_MESSAGES, api_key)

        content = response_data.get('content', '')

        # Check for error in response
        if content.startswith("Error:"):
            print(f"❌ {name}: API ERROR")
            print(f"   Error: {content[:150]}")
            return False

        # Check if model followed the system message instruction
        if "happy birthday" in content.lower() or "birthday" in content.lower():
            print(f"✅ {name}: SUCCESS - Followed system message")
            print(f"   Duration: {duration:.2f}s")
            print(f"   Response: {content[:100]}...")
            if response_data.get('thinking'):
                print(f"   Thinking: {response_data.get('thinking')[:80]}...")
            return True
        else:
            print(f"⚠️  {name}: Response received but didn't follow system message")
            print(f"   Duration: {duration:.2f}s")
            print(f"   Response: {content[:100]}...")
            print(f"   Expected: Response to include 'Happy Birthday'")
            return False

    except Exception as e:
        print(f"❌ {name}: FAILED")
        print(f"   Error: {type(e).__name__}: {str(e)[:200]}")
        return False

async def run_tests():
    """Run tests for all model providers."""
    print("=" * 60)
    print("Model Provider System Message Compatibility Test")
    print("=" * 60)

    tests = [
        ("OpenAI GPT-5.2", call_openai_gpt5, os.getenv("OPENAI_API_KEY")),
        ("Anthropic Claude 4.6 Opus", call_anthropic_opus_46, os.getenv("ANTHROPIC_API_KEY")),
        ("Anthropic Claude 4.5 Opus", call_anthropic_opus_45, os.getenv("ANTHROPIC_API_KEY")),
        ("Z.AI GLM-4.7", call_zai_glm47, os.getenv("ZAI_API_KEY")),
        ("Moonshot Kimi K2.5", call_moonshot_kimi, os.getenv("MOONSHOT_API_KEY")),
        ("OpenRouter Gemini-3-pro-preview", call_openrouter_gemini, os.getenv("OPENROUTER_API_KEY")),
    ]

    results = []
    for name, func, key in tests:
        result = await test_model(name, func, key)
        results.append((name, result))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY - System Message Compliance")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Models following system instructions: {passed}/{total}")
    print()
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print("\n" + "=" * 60)
    if passed == total:
        print("✅ All models properly support system messages!")
    else:
        print(f"⚠️  {total - passed} model(s) need investigation")

if __name__ == "__main__":
    asyncio.run(run_tests())
