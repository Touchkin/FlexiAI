"""Google Vertex AI Basic Examples.

This script demonstrates basic usage of FlexiAI with Google Vertex AI on GCP.

Requirements:
- GCP project with Vertex AI API enabled
- Service account with Vertex AI permissions OR gcloud authentication
- Environment variables:
  - GOOGLE_CLOUD_PROJECT="your-project-id"
  - GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json" (optional)
"""

import json
import os

from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, Message, ProviderConfig


def example_1_with_service_account():
    """Use service account authentication."""
    print("\n" + "=" * 60)
    print("Example 1: Service Account Authentication")
    print("=" * 60)

    # Path to your service account JSON file
    service_account_file = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", "/path/to/service-account.json"
    )

    # Read project ID from service account file
    try:
        with open(service_account_file, "r") as f:
            service_account = json.load(f)
            project_id = service_account.get("project_id")
    except FileNotFoundError:
        print(f"⚠️  Service account file not found: {service_account_file}")
        print("Please set GOOGLE_APPLICATION_CREDENTIALS environment variable")
        return

    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="vertexai",
                api_key="not-used",  # Vertex AI doesn't use API keys
                model="gemini-2.0-flash",
                priority=1,
                config={
                    "project": project_id,
                    "location": "us-central1",
                    "service_account_file": service_account_file,
                },
            )
        ]
    )

    client = FlexiAI(config)

    response = client.chat_completion(
        messages=[Message(role="user", content="What is Python in one sentence?")], max_tokens=100
    )

    print(f"Response: {response.content}")
    print(f"Tokens used: {response.usage.total_tokens}")
    print(f"Provider: {response.metadata.provider}")
    print(f"Project: {project_id}")


def example_2_with_adc():
    """Use Application Default Credentials (ADC)."""
    print("\n" + "=" * 60)
    print("Example 2: Application Default Credentials")
    print("=" * 60)
    print("Note: Requires 'gcloud auth application-default login'")

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    if not project_id:
        print("⚠️  GOOGLE_CLOUD_PROJECT environment variable not set")
        return

    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="vertexai",
                api_key="not-used",
                model="gemini-2.0-flash",
                priority=1,
                config={
                    "project": project_id,
                    "location": "us-central1"
                    # Will use ADC automatically
                },
            )
        ]
    )

    client = FlexiAI(config)

    response = client.chat_completion(
        messages=[Message(role="user", content="Hello from Vertex AI!")], max_tokens=50
    )

    print(f"Response: {response.content}")
    print(f"Project: {project_id}")


def example_3_different_regions():
    """Use different GCP regions."""
    print("\n" + "=" * 60)
    print("Example 3: Different GCP Regions")
    print("=" * 60)

    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not service_account_file or not os.path.exists(service_account_file):
        print("⚠️  Skipping: Service account file not found")
        return

    with open(service_account_file, "r") as f:
        project_id = json.load(f).get("project_id")

    # Available regions for Vertex AI
    regions = ["us-central1", "us-east1", "europe-west1", "asia-northeast1"]

    print(f"\nAvailable regions: {', '.join(regions)}")
    print("\nUsing region: us-central1")

    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="vertexai",
                api_key="not-used",
                model="gemini-2.0-flash",
                priority=1,
                config={
                    "project": project_id,
                    "location": "us-central1",  # Try different regions
                    "service_account_file": service_account_file,
                },
            )
        ]
    )

    client = FlexiAI(config)

    response = client.chat_completion(
        messages=[Message(role="user", content="What region are you running in?")], max_tokens=100
    )

    print(f"Response: {response.content}")


def example_4_advanced_models():
    """Use different Vertex AI models."""
    print("\n" + "=" * 60)
    print("Example 4: Different Vertex AI Models")
    print("=" * 60)

    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not service_account_file or not os.path.exists(service_account_file):
        print("⚠️  Skipping: Service account file not found")
        return

    with open(service_account_file, "r") as f:
        project_id = json.load(f).get("project_id")

    # Available Vertex AI models
    models = [
        "gemini-2.0-flash",  # Latest and fastest
        "gemini-1.5-pro",  # More powerful
        "gemini-1.5-flash",  # Fast and efficient
    ]

    for model in models[:1]:  # Test with first model
        print(f"\nTesting with model: {model}")

        config = FlexiAIConfig(
            providers=[
                ProviderConfig(
                    name="vertexai",
                    api_key="not-used",
                    model=model,
                    priority=1,
                    config={
                        "project": project_id,
                        "location": "us-central1",
                        "service_account_file": service_account_file,
                    },
                )
            ]
        )

        client = FlexiAI(config)

        response = client.chat_completion(
            messages=[Message(role="user", content="Say hello in 5 words")], max_tokens=50
        )

        print(f"  Response: {response.content}")
        print(f"  Tokens: {response.usage.total_tokens}")


def example_5_multi_turn_conversation():
    """Demonstrate multi-turn conversation with Vertex AI."""
    print("\n" + "=" * 60)
    print("Example 5: Multi-Turn Conversation")
    print("=" * 60)

    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not service_account_file or not os.path.exists(service_account_file):
        print("⚠️  Skipping: Service account file not found")
        return

    with open(service_account_file, "r") as f:
        project_id = json.load(f).get("project_id")

    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="vertexai",
                api_key="not-used",
                model="gemini-2.0-flash",
                priority=1,
                config={
                    "project": project_id,
                    "location": "us-central1",
                    "service_account_file": service_account_file,
                },
            )
        ]
    )

    client = FlexiAI(config)

    # Build conversation
    conversation = [
        Message(role="system", content="You are a helpful GCP expert"),
        Message(role="user", content="What is Vertex AI?"),
    ]

    response1 = client.chat_completion(messages=conversation, max_tokens=150)

    print("User: What is Vertex AI?")
    print(f"Assistant: {response1.content}\n")

    # Continue conversation
    conversation.extend(
        [
            Message(role="assistant", content=response1.content),
            Message(role="user", content="How does it differ from Gemini API?"),
        ]
    )

    response2 = client.chat_completion(messages=conversation, max_tokens=150)

    print("User: How does it differ from Gemini API?")
    print(f"Assistant: {response2.content}")


def example_6_provider_status():
    """Check provider health and status."""
    print("\n" + "=" * 60)
    print("Example 6: Provider Status Monitoring")
    print("=" * 60)

    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not service_account_file or not os.path.exists(service_account_file):
        print("⚠️  Skipping: Service account file not found")
        return

    with open(service_account_file, "r") as f:
        project_id = json.load(f).get("project_id")

    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="vertexai",
                api_key="not-used",
                model="gemini-2.0-flash",
                priority=1,
                config={
                    "project": project_id,
                    "location": "us-central1",
                    "service_account_file": service_account_file,
                },
            )
        ]
    )

    client = FlexiAI(config)

    # Make a few requests
    for i in range(3):
        response = client.chat_completion(
            messages=[Message(role="user", content=f"Count to {i+1}")], max_tokens=20
        )
        print(f"Request {i+1}: {response.content}")

    # Check provider status
    print("\nProvider Status:")
    status = client.get_provider_status()
    for provider_name, info in status.items():
        print(f"\n{provider_name}:")
        print(f"  Healthy: {info['healthy']}")
        print(f"  Circuit Breaker: {info['circuit_breaker']['state']}")
        print(f"  Total Requests: {info['total_requests']}")
        print(f"  Successful: {info['successful_requests']}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("FlexiAI - Google Vertex AI Examples")
    print("=" * 60)

    # Check for required environment variables
    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    if not service_account_file and not project_id:
        print("\n⚠️  Setup Required:")
        print("\nOption 1 - Service Account:")
        print("  export GOOGLE_APPLICATION_CREDENTIALS='/path/to/service-account.json'")
        print("\nOption 2 - ADC:")
        print("  gcloud auth application-default login")
        print("  export GOOGLE_CLOUD_PROJECT='your-project-id'")
        print("\nGet service account from GCP Console → IAM & Admin → Service Accounts")
        return

    try:
        example_1_with_service_account()
        example_2_with_adc()
        example_3_different_regions()
        example_4_advanced_models()
        example_5_multi_turn_conversation()
        example_6_provider_status()

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
