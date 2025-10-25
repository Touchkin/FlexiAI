"""
Example: Testing FlexiAI with Real OpenAI API.

This script demonstrates how to use FlexiAI with a real OpenAI API key.
Make sure you have set your OPENAI_API_KEY environment variable:
    export OPENAI_API_KEY="your-api-key-here"

Or you can pass it directly in the config (not recommended for production).
"""

import os

from flexiai import FlexiAI, FlexiAIConfig, ProviderConfig

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY environment variable not set!")
    print("Please run: export OPENAI_API_KEY='your-api-key-here'")
    exit(1)

# Option 1: Simple initialization (uses OPENAI_API_KEY from environment)
print("=" * 60)
print("Testing FlexiAI with Real OpenAI API")
print("=" * 60)

config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            priority=1,
            api_key=api_key,  # Read from environment
            model="gpt-4.1-nano-2025-04-14",  # Using the recommended nano model
        )
    ],
    default_model="gpt-4.1-nano-2025-04-14",
    default_temperature=0.7,
    default_max_tokens=150,
)

client = FlexiAI(config=config)

# Test 1: Simple chat completion
print("\n1. Simple Chat Completion:")
print("-" * 60)
try:
    response = client.chat_completion(
        messages=[{"role": "user", "content": "Say hello and introduce yourself in one sentence."}]
    )
    print(f"Response: {response.content}")
    print(f"Model: {response.model}")
    print(f"Tokens used: {response.usage}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: With custom parameters
print("\n2. With Custom Temperature:")
print("-" * 60)
try:
    response = client.chat_completion(
        messages=[{"role": "user", "content": "Tell me a very short joke about programming."}],
        temperature=1.0,  # More creative
        max_tokens=100,
    )
    print(f"Response: {response.content}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Check statistics
print("\n3. Request Statistics:")
print("-" * 60)
stats = client.get_request_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Successful requests: {stats['successful_requests']}")
print(f"Failed requests: {stats['failed_requests']}")
print(f"Last used provider: {client.get_last_used_provider()}")

# Test 4: Provider status
print("\n4. Provider Status:")
print("-" * 60)
status = client.get_provider_status("openai")
print(f"Provider: {status['name']}")
print(f"Model: {status['model']}")
print(f"Priority: {status['priority']}")
print(f"Status: {status['status']}")
print(f"Circuit breaker state: {status['circuit_breaker']['state']}")
print(f"Failure count: {status['circuit_breaker']['failure_count']}")
print(f"Success count: {status['circuit_breaker']['success_count']}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
