"""
Basic Anthropic Claude Usage Example.

This example demonstrates how to use FlexiAI with Anthropic's Claude models.

Prerequisites:
    - Set ANTHROPIC_API_KEY environment variable
    - Or provide api_key directly in ProviderConfig

Supported Models:
    - claude-3-opus-20240229 (most capable)
    - claude-3-sonnet-20240229 (balanced)
    - claude-3-haiku-20240307 (fastest)
    - claude-3-5-sonnet-20241022 (latest sonnet)
    - claude-3-5-haiku-20241022 (latest haiku)
"""

import os

from dotenv import load_dotenv

from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, Message, ProviderConfig

# Load environment variables
load_dotenv()


def basic_chat_completion():
    """Demonstrate basic chat completion with Claude."""
    # Configure FlexiAI with Anthropic provider
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-sonnet-20241022",
                priority=1,
            )
        ]
    )

    # Initialize client
    client = FlexiAI(config)

    # Simple chat completion
    response = client.chat_completion(
        messages=[Message(role="user", content="What is the capital of France?")],
        temperature=0.7,
        max_tokens=100,
    )

    print("=" * 80)
    print("Basic Chat Completion")
    print("=" * 80)
    print(f"Model: {response.model}")
    print(f"Provider: {response.provider}")
    print(f"Response: {response.content}")
    print(f"Tokens: {response.usage.total_tokens}")
    print()


def chat_with_system_message():
    """Demonstrate chat completion with system message."""
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-sonnet-20241022",
                priority=1,
            )
        ]
    )

    client = FlexiAI(config)

    # Chat with system message
    response = client.chat_completion(
        messages=[
            Message(
                role="system", content="You are a helpful assistant that responds in haiku format."
            ),
            Message(role="user", content="Tell me about artificial intelligence."),
        ],
        temperature=0.8,
        max_tokens=150,
    )

    print("=" * 80)
    print("Chat with System Message")
    print("=" * 80)
    print(f"Response:\n{response.content}")
    print(f"Finish Reason: {response.finish_reason}")
    print()


def multi_turn_conversation():
    """Demonstrate multi-turn conversation."""
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-haiku-20241022",  # Use faster model
                priority=1,
            )
        ]
    )

    client = FlexiAI(config)

    # Multi-turn conversation
    messages = [
        Message(role="user", content="I'm planning a trip to Japan."),
    ]

    response1 = client.chat_completion(messages=messages, max_tokens=200)
    print("=" * 80)
    print("Multi-Turn Conversation")
    print("=" * 80)
    print(f"User: {messages[0].content}")
    print(f"Assistant: {response1.content}")
    print()

    # Add assistant response and continue conversation
    messages.append(Message(role="assistant", content=response1.content))
    messages.append(
        Message(role="user", content="What's the best time of year to visit for cherry blossoms?")
    )

    response2 = client.chat_completion(messages=messages, max_tokens=200)
    print(f"User: {messages[2].content}")
    print(f"Assistant: {response2.content}")
    print()


def different_claude_models():
    """Compare different Claude model outputs."""
    models = [
        "claude-3-5-haiku-20241022",  # Fastest
        "claude-3-5-sonnet-20241022",  # Balanced
        "claude-3-opus-20240229",  # Most capable
    ]

    question = "Explain quantum entanglement in one sentence."

    print("=" * 80)
    print("Comparing Claude Models")
    print("=" * 80)
    print(f"Question: {question}\n")

    for model in models:
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(
                    name="anthropic",
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                    model=model,
                    priority=1,
                )
            ]
        )

        client = FlexiAI(config)

        response = client.chat_completion(
            messages=[Message(role="user", content=question)],
            temperature=0.5,
            max_tokens=100,
        )

        print(f"{model}:")
        print(f"  Response: {response.content}")
        print(f"  Tokens: {response.usage.total_tokens}")
        print()


def main():
    """Run all examples."""
    try:
        print("\n🤖 FlexiAI - Anthropic Claude Examples\n")

        # Example 1: Basic chat completion
        basic_chat_completion()

        # Example 2: Chat with system message
        chat_with_system_message()

        # Example 3: Multi-turn conversation
        multi_turn_conversation()

        # Example 4: Compare different models
        different_claude_models()

        print("=" * 80)
        print("✅ All examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Set ANTHROPIC_API_KEY environment variable")
        print("2. Installed required dependencies: pip install -r requirements.txt")


if __name__ == "__main__":
    main()
