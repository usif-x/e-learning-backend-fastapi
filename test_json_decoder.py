"""
Test JSON decoder for AI responses
"""

import asyncio

from app.utils.ai import ai_service


async def test_json_decoder():
    """Test that responses are properly decoded to JSON"""
    print("\n" + "=" * 60)
    print("Testing JSON Decoder for AI Responses")
    print("=" * 60)

    if not ai_service.is_configured():
        print("❌ AI service is not configured!")
        return

    print("✅ AI service is configured\n")

    # Test question generation
    print("🔄 Generating questions about 'homeostasis'...")
    try:
        result = await ai_service.generate_questions(
            topic="homeostasis",
            difficulty="medium",
            count=3,
            question_type="multiple_choice",
        )

        print("✅ Questions generated successfully!")
        print(f"\n📋 Result type: {type(result)}")
        print(f"📋 Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

        if isinstance(result, dict) and "questions" in result:
            questions = result["questions"]
            print(f"\n✅ SUCCESS: Got clean JSON with {len(questions)} questions")

            # Show first question
            if questions:
                first_q = questions[0]
                print(f"\n📝 First Question:")
                print(f"   Q: {first_q.get('question', 'N/A')[:80]}...")
                print(f"   Options: {len(first_q.get('options', []))} choices")
                print(f"   Correct: {first_q.get('correct_answer', 'N/A')}")
                print(f"   Has explanation: {bool(first_q.get('explanation'))}")
        else:
            print("❌ FAILED: Result is not proper JSON structure")
            print(f"Result: {result}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_json_decoder())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {str(e)}")
