#!/usr/bin/env python3
"""Async Decorator Examples.

This example demonstrates using the @flexiai_chat decorator with async functions.
The decorator automatically detects async functions and uses the async client.

Requirements:
    - Set OPENAI_API_KEY environment variable
    - Install flexiai: pip install -e .
"""

import asyncio
import os

from flexiai import FlexiAI, FlexiAIConfig, flexiai_chat

# Configure FlexiAI globally
config = FlexiAIConfig(
    providers=[
        {
            "name": "openai",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-4o-mini",
            "priority": 1,
            "timeout": 60,  # Increase timeout
        },
    ],
)

FlexiAI.set_global_config(config)


# Example 1: Simple async function
@flexiai_chat(max_tokens=50)
async def ask_ai_async(question: str) -> str:
    """Async version of ask_ai."""
    pass  # Implementation handled by decorator


# Example 2: Async with system message
@flexiai_chat(
    system_message="You are a helpful coding assistant. Answer in one sentence.",
    max_tokens=50,
)
async def code_assistant(question: str) -> str:
    """Get coding help asynchronously."""
    pass


# Example 3: Async with temperature
@flexiai_chat(temperature=0.8, max_tokens=30)
async def creative_async(prompt: str) -> str:
    """Generate creative content asynchronously."""
    pass


# Example 4: Multiple async calls concurrently
@flexiai_chat(
    system_message="Answer in 5 words or less.",
    max_tokens=20,
)
async def quick_answer(question: str) -> str:
    """Quick answers for concurrent testing."""
    pass


async def example_basic_async():
    """Demonstrate basic async usage."""
    print("\n" + "=" * 60)
    print("BASIC ASYNC USAGE")
    print("=" * 60)

    print("\n1. Simple Async Question:")
    print("-" * 40)
    answer = await ask_ai_async("What is 2+2?")
    print(f"Answer: {answer}")

    print("\n2. Code Assistant:")
    print("-" * 40)
    help_text = await code_assistant("How do I use asyncio?")
    print(f"Help: {help_text}")

    print("\n3. Creative Content:")
    print("-" * 40)
    content = await creative_async("Haiku about code")
    print(f"Haiku: {content}")


async def example_concurrent_calls():
    """Demonstrate concurrent async calls."""
    print("\n" + "=" * 60)
    print("CONCURRENT ASYNC CALLS")
    print("=" * 60)

    print("\nMaking 3 concurrent requests...")
    print("-" * 40)

    # Create multiple async tasks with short answers
    tasks = [
        quick_answer("What is ML?"),
        quick_answer("What is AI?"),
        quick_answer("What is NLP?"),
    ]

    # Run them concurrently
    import time

    start = time.time()
    results = await asyncio.gather(*tasks)
    end = time.time()

    print(f"\nCompleted {len(tasks)} requests in {end - start:.2f} seconds")
    print("\nResults:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result}")


async def main():
    """Run all async examples."""
    print("=" * 60)
    print("FlexiAI Decorator - Async Examples")
    print("=" * 60)

    try:
        await example_basic_async()
        await example_concurrent_calls()

        print("\n" + "=" * 60)
        print("✅ All async examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
