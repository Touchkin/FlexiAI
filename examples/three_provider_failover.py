"""
Three-Provider Failover Example.

This example demonstrates FlexiAI's automatic failover with all three supported providers:
OpenAI → Vertex AI → Anthropic

The system will automatically try providers in priority order until one succeeds.

Prerequisites:
    At least one of the following:
    - OPENAI_API_KEY environment variable
    - GOOGLE_APPLICATION_CREDENTIALS + GOOGLE_CLOUD_PROJECT
    - ANTHROPIC_API_KEY environment variable

Failover Priority:
    1. OpenAI (highest priority - fastest)
    2. Vertex AI (middle priority - cost-effective)
    3. Anthropic Claude (lowest priority - most capable)
"""

import json
import os

from dotenv import load_dotenv

from flexiai import FlexiAI
from flexiai.exceptions import AllProvidersFailedError
from flexiai.models import CircuitBreakerConfig, FlexiAIConfig, Message, ProviderConfig

# Load environment variables
load_dotenv()


def example_1_three_provider_setup():
    """Demonstrate three-provider failover configuration."""
    print("\n" + "=" * 80)
    print("Example 1: Three-Provider Failover Setup")
    print("=" * 80)

    providers = []

    # Provider 1: OpenAI (Priority 1 - Primary)
    if os.getenv("OPENAI_API_KEY"):
        providers.append(
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=1,
            )
        )
        print("✅ OpenAI configured (Priority 1 - Primary)")
    else:
        print("⚠️  OpenAI not configured (OPENAI_API_KEY not set)")

    # Provider 2: Vertex AI (Priority 2 - Secondary)
    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_file and os.path.exists(service_account_file):
        with open(service_account_file, "r") as f:
            project_id = json.load(f).get("project_id")

        providers.append(
            ProviderConfig(
                name="vertexai",
                api_key="not-used",
                model="gemini-2.0-flash-exp",
                priority=2,
                config={
                    "project": project_id,
                    "location": "us-central1",
                    "service_account_file": service_account_file,
                },
            )
        )
        print("✅ Vertex AI configured (Priority 2 - Secondary)")
    else:
        print("⚠️  Vertex AI not configured (GOOGLE_APPLICATION_CREDENTIALS not set)")

    # Provider 3: Anthropic (Priority 3 - Tertiary)
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append(
            ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-sonnet-20241022",
                priority=3,
            )
        )
        print("✅ Anthropic Claude configured (Priority 3 - Tertiary)")
    else:
        print("⚠️  Anthropic not configured (ANTHROPIC_API_KEY not set)")

    if not providers:
        print("\n❌ No providers configured. Please set at least one API key.")
        return None

    print(f"\n📊 Total providers configured: {len(providers)}")

    config = FlexiAIConfig(providers=providers)
    client = FlexiAI(config)

    # Make a request - will use highest priority available provider
    print("\n🔄 Making request (will use highest priority provider)...")
    response = client.chat_completion(
        messages=[
            Message(
                role="user", content="Say hello and identify yourself (which AI model you are)."
            )
        ],
        max_tokens=100,
    )

    print("\n✅ Success!")
    print(f"🤖 Provider: {response.provider}")
    print(f"📝 Model: {response.model}")
    print(f"💬 Response: {response.content}")
    print(f"📊 Tokens: {response.usage.total_tokens}")

    return client


def example_2_failover_cascade():
    """Simulate cascade failover through all three providers."""
    print("\n" + "=" * 80)
    print("Example 2: Cascade Failover Simulation")
    print("=" * 80)

    providers = [
        # Invalid OpenAI (will fail immediately)
        ProviderConfig(
            name="openai",
            api_key="sk-invalid-key-for-testing",
            model="gpt-4o-mini",
            priority=1,
        ),
    ]
    print("❌ OpenAI configured with invalid key (will fail)")

    # Try to add Vertex AI with invalid config
    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_file and os.path.exists(service_account_file):
        # Use invalid project to simulate failure
        providers.append(
            ProviderConfig(
                name="vertexai",
                api_key="not-used",
                model="gemini-2.0-flash-exp",
                priority=2,
                config={
                    "project": "invalid-project-id-12345",
                    "location": "us-central1",
                    "service_account_file": service_account_file,
                },
            )
        )
        print("❌ Vertex AI configured with invalid project (will fail)")

    # Add valid Anthropic as final fallback
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append(
            ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-haiku-20241022",
                priority=3,
            )
        )
        print("✅ Anthropic configured (valid - should succeed)")
    else:
        print("⚠️  Anthropic not configured - failover will fail completely")

    config = FlexiAIConfig(
        providers=providers,
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=1,  # Fail fast
            recovery_timeout=60,
        ),
    )

    client = FlexiAI(config)

    print("\n🔄 Attempting request...")
    print("   Expected: OpenAI fails → Vertex AI fails → Anthropic succeeds")

    try:
        response = client.chat_completion(
            messages=[Message(role="user", content="Hello! Which provider am I using?")],
            max_tokens=50,
        )

        print("\n✅ Cascade failover successful!")
        print(f"🤖 Final provider: {response.provider}")
        print(f"💬 Response: {response.content}")

    except AllProvidersFailedError as e:
        print(f"\n❌ All providers failed: {e}")
        print("   Make sure at least one provider has valid credentials")


def example_3_load_balancing():
    """Demonstrate load balancing across multiple providers."""
    print("\n" + "=" * 80)
    print("Example 3: Load Balancing Across Providers")
    print("=" * 80)

    providers = []

    # Add all available providers with same priority for load balancing
    if os.getenv("OPENAI_API_KEY"):
        providers.append(
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=1,
            )
        )

    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_file and os.path.exists(service_account_file):
        with open(service_account_file, "r") as f:
            project_id = json.load(f).get("project_id")

        providers.append(
            ProviderConfig(
                name="vertexai",
                api_key="not-used",
                model="gemini-2.0-flash-exp",
                priority=1,  # Same priority as OpenAI
                config={
                    "project": project_id,
                    "location": "us-central1",
                    "service_account_file": service_account_file,
                },
            )
        )

    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append(
            ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-haiku-20241022",
                priority=1,  # Same priority
            )
        )

    if len(providers) < 2:
        print("⚠️  Need at least 2 providers for load balancing demo")
        return

    print(f"✅ {len(providers)} providers configured with equal priority")

    config = FlexiAIConfig(providers=providers)
    client = FlexiAI(config)

    # Make multiple requests
    print("\n🔄 Making 5 requests to observe provider distribution...")
    provider_usage = {}

    for i in range(5):
        response = client.chat_completion(
            messages=[Message(role="user", content=f"Request {i+1}: Say hi!")],
            max_tokens=20,
        )

        provider = response.provider
        provider_usage[provider] = provider_usage.get(provider, 0) + 1
        print(f"  Request {i+1}: {provider}")

    print("\n📊 Provider Usage Distribution:")
    for provider, count in provider_usage.items():
        print(f"  {provider}: {count} requests ({count/5*100:.1f}%)")


def example_4_cost_optimization():
    """Demonstrate cost-optimized provider priority."""
    print("\n" + "=" * 80)
    print("Example 4: Cost-Optimized Provider Priority")
    print("=" * 80)
    print("\nStrategy: Use cheapest provider first, fallback to more expensive if needed")

    providers = []

    # Priority 1: Vertex AI (cheapest for Gemini)
    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_file and os.path.exists(service_account_file):
        with open(service_account_file, "r") as f:
            project_id = json.load(f).get("project_id")

        providers.append(
            ProviderConfig(
                name="vertexai",
                api_key="not-used",
                model="gemini-2.0-flash-exp",
                priority=1,  # Highest priority (cheapest)
                config={
                    "project": project_id,
                    "location": "us-central1",
                    "service_account_file": service_account_file,
                },
            )
        )
        print("✅ Vertex AI (Priority 1 - Most cost-effective)")

    # Priority 2: OpenAI GPT-4o-mini (moderate cost)
    if os.getenv("OPENAI_API_KEY"):
        providers.append(
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=2,
            )
        )
        print("✅ OpenAI GPT-4o-mini (Priority 2 - Moderate cost)")

    # Priority 3: Claude Sonnet (higher cost, better quality)
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append(
            ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-sonnet-20241022",
                priority=3,  # Lowest priority (most expensive)
            )
        )
        print("✅ Anthropic Claude Sonnet (Priority 3 - Premium quality)")

    if not providers:
        print("⚠️  No providers configured")
        return

    config = FlexiAIConfig(providers=providers)
    client = FlexiAI(config)

    # Complex task that might benefit from better models
    print("\n🔄 Making request for complex task...")
    response = client.chat_completion(
        messages=[
            Message(
                role="user", content="Explain quantum computing in simple terms (2-3 sentences)."
            )
        ],
        max_tokens=150,
    )

    print("\n✅ Success!")
    print(f"🤖 Provider: {response.provider}")
    print(f"💬 Response: {response.content}")
    print(f"💰 Cost optimization: Used {response.provider} (priority-based selection)")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("🚀 FlexiAI - Three-Provider Failover Examples")
    print("=" * 80)

    try:
        # Example 1: Basic three-provider setup
        client = example_1_three_provider_setup()

        if client:
            # Example 2: Cascade failover
            example_2_failover_cascade()

            # Example 3: Load balancing
            example_3_load_balancing()

            # Example 4: Cost optimization
            example_4_cost_optimization()

        print("\n" + "=" * 80)
        print("✅ All examples completed!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Set at least one provider's API key:")
        print("   - OPENAI_API_KEY for OpenAI")
        print("   - GOOGLE_APPLICATION_CREDENTIALS for Vertex AI")
        print("   - ANTHROPIC_API_KEY for Anthropic")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Load .env file if using one")


if __name__ == "__main__":
    main()
