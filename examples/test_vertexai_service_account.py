"""
Test Vertex AI with Service Account JSON file.

Prerequisites:
1. Service account JSON file with Vertex AI permissions
2. GCP project ID (usually in the JSON file)

Usage Method 1 - Environment Variable (Recommended):
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/dev-gemini-427512-71ac4bd1f35d.json
    python examples/test_vertexai_service_account.py

Usage Method 2 - Specify in code:
    Edit SERVICE_ACCOUNT_FILE variable below
    python examples/test_vertexai_service_account.py
"""

import json
import os
import sys

# Configuration
SERVICE_ACCOUNT_FILE = "dev-gemini-427512-71ac4bd1f35d.json"  # Update if needed
LOCATION = "us-central1"  # Update if you prefer a different region

# Check for service account file
service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or SERVICE_ACCOUNT_FILE

if not os.path.exists(service_account_path):
    print(f"❌ Error: Service account file not found: {service_account_path}")
    print("\nOptions:")
    print("1. Set environment variable:")
    print(f"   export GOOGLE_APPLICATION_CREDENTIALS=/full/path/to/{SERVICE_ACCOUNT_FILE}")
    print("2. Or place the file in the current directory")
    print(f"3. Or update SERVICE_ACCOUNT_FILE variable in this script")
    sys.exit(1)

# Extract project ID from service account file
try:
    with open(service_account_path, "r") as f:
        service_account_info = json.load(f)
        project_id = service_account_info.get("project_id")
        service_account_email = service_account_info.get("client_email")
except Exception as e:
    print(f"❌ Error reading service account file: {e}")
    sys.exit(1)

if not project_id:
    print("❌ Error: Could not extract project_id from service account file")
    sys.exit(1)

from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, Message, ProviderConfig, UnifiedRequest

print("🚀 Testing Vertex AI with Service Account\n")
print(f"📦 Project: {project_id}")
print(f"📍 Location: {LOCATION}")
print(f"🔐 Service Account: {service_account_email}")
print(f"📄 Credentials File: {service_account_path}")
print(f"🤖 Model: gemini-2.0-flash\n")

# Configure Vertex AI provider with service account
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="vertexai",
            api_key="not-used",  # Not needed for service account
            model="gemini-2.0-flash",
            priority=1,
            config={
                "project": project_id,
                "location": LOCATION,
                "service_account_file": service_account_path,
            },
        )
    ]
)

try:
    # Create client
    print("🔧 Initializing FlexiAI client...")
    client = FlexiAI(config)
    print("✅ Client initialized successfully!\n")

    # Test 1: Simple completion
    print("=" * 70)
    print("Test 1: Simple Completion")
    print("=" * 70)

    request = UnifiedRequest(
        messages=[
            Message(
                role="user",
                content="Say 'Hello from Vertex AI with service account!' and nothing else",
            )
        ],
        max_tokens=50,
        temperature=0.0,
    )

    print("📤 Sending request to Vertex AI...")
    response = client.chat_completion(request)

    print(f"\n✅ Success!")
    print(f"📝 Response: {response.content}")
    print(f"📊 Token Usage:")
    print(f"   • Prompt tokens: {response.usage.prompt_tokens}")
    print(f"   • Completion tokens: {response.usage.completion_tokens}")
    print(f"   • Total tokens: {response.usage.total_tokens}")
    print(f"🏁 Finish reason: {response.finish_reason}")
    print(f"🔧 Provider: {response.provider}")
    print(f"🤖 Model: {response.model}\n")

    # Test 2: Calculation
    print("=" * 70)
    print("Test 2: Simple Math")
    print("=" * 70)

    request = UnifiedRequest(
        messages=[Message(role="user", content="What is 25 * 4? Just give the answer.")],
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
            Message(role="user", content="What's the capital of Japan?"),
            Message(role="assistant", content="The capital of Japan is Tokyo."),
            Message(role="user", content="What's its approximate population?"),
        ],
        max_tokens=100,
        temperature=0.3,
    )

    print("📤 Sending multi-turn conversation...")
    response = client.chat_completion(request)

    print(f"\n✅ Response: {response.content}")
    print(f"📊 Tokens: {response.usage.total_tokens} total\n")

    # Test 4: System message
    print("=" * 70)
    print("Test 4: System Message")
    print("=" * 70)

    request = UnifiedRequest(
        messages=[
            Message(
                role="system",
                content="You are a helpful assistant that always responds in exactly 10 words.",
            ),
            Message(role="user", content="Tell me about artificial intelligence."),
        ],
        max_tokens=100,
        temperature=0.7,
    )

    print("📤 Sending request with system message...")
    response = client.chat_completion(request)

    print(f"\n✅ Response: {response.content}")
    print(f"📊 Tokens: {response.usage.total_tokens} total")
    print(f"📏 Word count: {len(response.content.split())} words\n")

    # Display statistics
    print("=" * 70)
    print("Overall Statistics")
    print("=" * 70)

    stats = client.get_request_stats()
    print(f"📊 Total requests: {stats['total_requests']}")
    print(f"✅ Successful: {stats['successful_requests']}")
    print(f"❌ Failed: {stats['failed_requests']}")
    print(f"📈 Success rate: {stats['success_rate']:.1f}%\n")

    print("🎉 All tests passed successfully!")
    print("\n💡 Your Vertex AI integration is working perfectly!")
    print(f"   • Service account: {service_account_email}")
    print(f"   • Project: {project_id}")
    print(f"   • Region: {LOCATION}")

except Exception as e:
    print(f"\n❌ Error occurred: {type(e).__name__}")
    print(f"📄 Details: {str(e)}\n")
    print("🔍 Troubleshooting:")
    print("1. Verify service account has necessary permissions:")
    print("   • Vertex AI User (roles/aiplatform.user)")
    print("   • Or Service Usage Consumer (roles/serviceusage.serviceUsageConsumer)")
    print("\n2. Ensure Vertex AI API is enabled:")
    print(f"   gcloud services enable aiplatform.googleapis.com --project={project_id}")
    print("\n3. Check if billing is enabled for the project")
    print("\n4. Verify the service account JSON file is valid")
    print("\n5. Test authentication directly:")
    print(f"   export GOOGLE_APPLICATION_CREDENTIALS={service_account_path}")
    print("   gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS")
    sys.exit(1)
