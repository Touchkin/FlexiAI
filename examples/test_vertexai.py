"""
Quick test script for Vertex AI Gemini API.

Prerequisites:
1. Run: gcloud auth application-default login
2. Set: export GOOGLE_CLOUD_PROJECT=your-project-id
3. Enable Vertex AI API in your GCP project

Usage:
    python examples/test_vertexai.py
"""

import os
import sys

# Check prerequisites
if not os.getenv("GOOGLE_CLOUD_PROJECT"):
    print("❌ Error: GOOGLE_CLOUD_PROJECT environment variable not set")
    print("\nRun: export GOOGLE_CLOUD_PROJECT=your-project-id")
    sys.exit(1)

from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, Message, ProviderConfig, UnifiedRequest

print("🚀 Testing Vertex AI Gemini API\n")

# Configure Vertex AI provider
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="vertexai",
            api_key="not-used",  # Vertex AI uses ADC, not API keys
            model="gemini-2.0-flash",
            priority=1,
            config={
                "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "location": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            },
        )
    ]
)

# Create client
print(f"📦 Project: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
print(f"📍 Location: {os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')}")
print(f"🤖 Model: gemini-2.0-flash\n")

try:
    client = FlexiAI(config)
    print("✅ Client initialized successfully\n")

    # Test 1: Simple completion
    print("=" * 60)
    print("Test 1: Simple Completion")
    print("=" * 60)

    request = UnifiedRequest(
        messages=[Message(role="user", content="Say 'Hello from Vertex AI!' and nothing else")],
        max_tokens=50,
        temperature=0.0,
    )

    response = client.chat_completion(request)

    print(f"✅ Response: {response.content}")
    print(
        f"📊 Tokens: {response.usage.prompt_tokens} prompt + {response.usage.completion_tokens} completion = {response.usage.total_tokens} total"
    )
    print(f"🏁 Finish reason: {response.finish_reason}")
    print(f"🔧 Provider: {response.provider}")
    print(f"🤖 Model: {response.model}\n")

    # Test 2: Multi-turn conversation
    print("=" * 60)
    print("Test 2: Multi-turn Conversation")
    print("=" * 60)

    request = UnifiedRequest(
        messages=[
            Message(role="user", content="What is 2+2?"),
            Message(role="assistant", content="2+2 equals 4."),
            Message(role="user", content="What is 3+3?"),
        ],
        max_tokens=50,
        temperature=0.0,
    )

    response = client.chat_completion(request)

    print(f"✅ Response: {response.content}")
    print(f"📊 Tokens: {response.usage.total_tokens} total\n")

    # Test 3: System message
    print("=" * 60)
    print("Test 3: System Message")
    print("=" * 60)

    request = UnifiedRequest(
        messages=[
            Message(role="system", content="You are a helpful math tutor. Be concise."),
            Message(role="user", content="Explain what prime numbers are"),
        ],
        max_tokens=100,
        temperature=0.7,
    )

    response = client.chat_completion(request)

    print(f"✅ Response: {response.content}")
    print(f"📊 Tokens: {response.usage.total_tokens} total\n")

    # Test 4: Provider stats
    print("=" * 60)
    print("Client Statistics")
    print("=" * 60)

    stats = client.get_request_stats()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Successful requests: {stats['successful_requests']}")
    print(f"Failed requests: {stats['failed_requests']}")
    print(f"Success rate: {stats['success_rate']:.1f}%\n")

    print("🎉 All tests passed!")

except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"\nTroubleshooting:")
    print("1. Make sure you're authenticated: gcloud auth application-default login")
    print("2. Verify your project: gcloud config get-value project")
    print("3. Enable Vertex AI API: gcloud services enable aiplatform.googleapis.com")
    print("4. Check billing is enabled in your GCP project")
    sys.exit(1)
