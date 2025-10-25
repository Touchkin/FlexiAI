"""
Test Vertex AI with GCP API Key.

Prerequisites:
1. GCP API key restricted to Vertex AI
2. GCP project ID
3. Vertex AI API enabled in your project

Usage:
    export VERTEX_AI_API_KEY=your-api-key-here
    export GOOGLE_CLOUD_PROJECT=your-project-id
    python examples/test_vertexai_with_api_key.py
"""

import os
import sys

# Check prerequisites
if not os.getenv("VERTEX_AI_API_KEY"):
    print("❌ Error: VERTEX_AI_API_KEY environment variable not set")
    print("\nRun: export VERTEX_AI_API_KEY=your-api-key")
    sys.exit(1)

if not os.getenv("GOOGLE_CLOUD_PROJECT"):
    print("❌ Error: GOOGLE_CLOUD_PROJECT environment variable not set")
    print("\nRun: export GOOGLE_CLOUD_PROJECT=your-project-id")
    sys.exit(1)

from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, Message, ProviderConfig, UnifiedRequest

print("🚀 Testing Vertex AI Gemini API with API Key\n")

# Get configuration from environment
api_key = os.getenv("VERTEX_AI_API_KEY")
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

print(f"📦 Project: {project_id}")
print(f"📍 Location: {location}")
print(f"🔑 API Key: {api_key[:20]}..." if len(api_key) > 20 else f"🔑 API Key: {api_key}")
print(f"🤖 Model: gemini-2.0-flash\n")

# Configure Vertex AI provider with API key
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="vertexai",
            api_key=api_key,  # Your GCP API key
            model="gemini-2.0-flash",
            priority=1,
            config={
                "project": project_id,
                "location": location,
            },
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

    request = UnifiedRequest(
        messages=[
            Message(
                role="user",
                content="Say 'Hello from Vertex AI with API key!' and nothing else",
            )
        ],
        max_tokens=50,
        temperature=0.0,
    )

    print("📤 Sending request...")
    response = client.chat_completion(request)

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

    request = UnifiedRequest(
        messages=[
            Message(role="user", content="What is 15 + 27? Just give the number."),
        ],
        max_tokens=20,
        temperature=0.0,
    )

    print("📤 Sending request...")
    response = client.chat_completion(request)

    print(f"\n✅ Response: {response.content}")
    print(f"📊 Tokens: {response.usage.total_tokens} total\n")

    # Test 3: Multi-turn conversation
    print("=" * 70)
    print("Test 3: Multi-turn Conversation")
    print("=" * 70)

    request = UnifiedRequest(
        messages=[
            Message(role="user", content="What is the capital of France?"),
            Message(role="assistant", content="The capital of France is Paris."),
            Message(role="user", content="What is its population?"),
        ],
        max_tokens=100,
        temperature=0.3,
    )

    print("📤 Sending request...")
    response = client.chat_completion(request)

    print(f"\n✅ Response: {response.content}")
    print(f"📊 Tokens: {response.usage.total_tokens} total\n")

    # Test 4: With system message
    print("=" * 70)
    print("Test 4: System Message (Personality)")
    print("=" * 70)

    request = UnifiedRequest(
        messages=[
            Message(
                role="system",
                content="You are a pirate. Always respond in pirate speak.",
            ),
            Message(role="user", content="Hello, how are you?"),
        ],
        max_tokens=100,
        temperature=0.7,
    )

    print("📤 Sending request...")
    response = client.chat_completion(request)

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

    print("🎉 All tests passed! Your Vertex AI API key is working correctly.")
    print("\n💡 Tips:")
    print("   - Your API key is restricted to Vertex AI (good security practice)")
    print("   - You can use any Gemini model available in Vertex AI")
    print("   - Check pricing: https://cloud.google.com/vertex-ai/pricing")

except Exception as e:
    print(f"\n❌ Error occurred: {type(e).__name__}")
    print(f"📄 Details: {e}")
    print("\n🔍 Troubleshooting:")
    print("1. Verify your API key is correct:")
    print("   - Go to Google Cloud Console > APIs & Credentials")
    print("   - Check if the key is active and not expired")
    print(
        "2. Ensure Vertex AI API is enabled:\n   gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT"
    )
    print("3. Verify your project ID is correct")
    print("4. Check if billing is enabled for your project")
    print(f"5. Ensure your API key is restricted to: Vertex AI API")
    sys.exit(1)
