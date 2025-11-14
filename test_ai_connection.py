"""
Test AI connection to DeepSeek API
Run this file to verify AI service is working
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.ai import ai_service


async def test_connection():
    """Test basic connection to AI service"""
    print("🤖 Testing AI Service Connection")
    print("=" * 50)

    # Check configuration
    print(f"\n📋 Configuration:")
    print(
        f"  API Key: {'*' * 20}{ai_service.api_key[-10:] if len(ai_service.api_key) > 10 else 'NOT SET'}"
    )
    print(f"  Endpoint: {ai_service.api_endpoint}")
    print(f"  Model: {ai_service.model}")
    print(f"  Configured: {ai_service.is_configured()}")

    if not ai_service.is_configured():
        print("\n❌ AI service is not configured!")
        print("Please check your .env file and set:")
        print("  - AI_API_KEY")
        print("  - AI_API_ENDPOINT")
        print("  - AI_MODEL")
        return

    print("\n🔄 Testing basic completion...")
    try:
        response = await ai_service.generate_completion(
            prompt="Say 'Hello, I am working!' in one sentence.",
            temperature=0.5,
            max_tokens=50,
        )
        print(f"✅ Success! Response: {response}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return

    print("\n🔄 Testing question generation...")
    try:
        response = await ai_service.generate_questions(
            topic="Python programming basics",
            difficulty="easy",
            count=2,
            question_type="multiple_choice",
        )
        print(f"✅ Success! Generated questions:\n{response[:500]}...")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return

    print("\n✨ All tests passed! AI service is working correctly.")


if __name__ == "__main__":
    asyncio.run(test_connection())
