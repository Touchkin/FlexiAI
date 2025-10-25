"""
Test Gemini API with your GCP API Key.

Your API key is for the Gemini Developer API, not Vertex AI.
Use the 'gemini' provider, not 'vertexai'.

Usage:
    export GEMINI_API_KEY=your-api-key-here
    python examples/test_gemini_with_api_key.py
"""

import os
import sys

# Check prerequisites
if not os.getenv("GEMINI_API_KEY") and not os.getenv("VERTEX_AI_API_KEY"):
    print("❌ Error: GEMINI_API_KEY environment variable not set")
    print("\nRun: export GEMINI_API_KEY=your-api-key")
    sys.exit(1)

from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig

print("🚀 Testing Gemini API with API Key\n")

# Get API key (try both env vars)
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VERTEX_AI_API_KEY")

print(f"🔑 API Key: {api_key[:20]}..." if len(api_key) > 20 else f"🔑 API Key: {api_key}")
print(f"🤖 Model: gemini-2.0-flash\n")

# Configure Gemini provider with API key
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="gemini",  # Use 'gemini' not 'vertexai'
            api_key=api_key,
            model="gemini-2.0-flash",
            priority=1,
        )
    ]
)

try:
    # Create client
    client = FlexiAI(config)
    print("✅ Client initialized successfully\n")

    # Test 1: Simple completion
    print("=" * 70)
    print("Test 1: Simple Completion")
    print("=" * 70)

    print("📤 Sending request...")
    response = client.chat_completion(
        messages=[{"role": "user", "content": "Say 'Hello from Gemini!' and nothing else"}],
        max_tokens=50,
        temperature=0.0,
    )

    print(f"\n✅ Success!")
    print(f"📝 Response: {response.content}")
    print(f"📊 Usage:")
    print(f"   - Prompt tokens: {response.usage.prompt_tokens}")
    print(f"   - Completion tokens: {response.usage.completion_tokens}")
    print(f"   - Total tokens: {response.usage.total_tokens}")
    print(f"🏁 Finish reason: {response.finish_reason}")
    print(f"🔧 Provider: {response.provider}")
    print(f"🤖 Model: {response.model}\n")

    # Test 2: Math question
    print("=" * 70)
    print("Test 2: Math Question")
    print("=" * 70)

    print("📤 Sending request...")
    response = client.chat_completion(
        messages=[{"role": "user", "content": "What is 15 + 27? Just give the number."}],
        max_tokens=20,
        temperature=0.0,
    )

    print(f"\n✅ Response: {response.content}")
    print(f"📊 Tokens: {response.usage.total_tokens} total\n")

    # Test 3: Multi-turn conversation
    print("=" * 70)
    print("Test 3: Multi-turn Conversation")
    print("=" * 70)

    print("📤 Sending request...")
    response = client.chat_completion(
        messages=[
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "The capital of France is Paris."},
            {"role": "user", "content": "What is its population?"},
        ],
        max_tokens=100,
        temperature=0.3,
    )

    print(f"\n✅ Response: {response.content}")
    print(f"📊 Tokens: {response.usage.total_tokens} total\n")

    # Test 4: With system message
    print("=" * 70)
    print("Test 4: System Message (Personality)")
    print("=" * 70)

    print("📤 Sending request...")
    response = client.chat_completion(
        messages=[
            {"role": "system", "content": "You are a friendly AI assistant. Be concise."},
            {"role": "user", "content": "Explain what Python is in one sentence."},
        ],
        max_tokens=100,
        temperature=0.7,
    )

    print(f"\n✅ Response: {response.content}")
    print(f"📊 Tokens: {response.usage.total_tokens} total\n")

    # Display statistics
    print("=" * 70)
    print("Overall Statistics")
    print("=" * 70)

    stats = client.get_request_stats()
    print(f"✅ Total requests: {stats['total_requests']}")
    print(f"✅ Successful: {stats['successful_requests']}")
    print(f"❌ Failed: {stats['failed_requests']}")
    print(f"📈 Success rate: {stats['success_rate']:.1f}%\n")

    print("🎉 All tests passed! Your Gemini API key is working correctly.")
    print("\n💡 Note:")
    print("   - You're using the Gemini Developer API (not Vertex AI)")
    print("   - This is perfect for development and testing")
    print("   - For production GCP deployments, use Vertex AI with OAuth2")

except Exception as e:
    print(f"\n❌ Error occurred: {type(e).__name__}")
    print(f"📄 Details: {e}")
    print("\n🔍 Troubleshooting:")
    print("1. Verify your API key is correct (should start with 'AIza')")
    print("2. Ensure Generative Language API is enabled:")
    print("   https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com")
    print("3. Check if the API key has restrictions (should allow Generative Language API)")
    print("4. Verify the key isn't expired or revoked")
    sys.exit(1)
