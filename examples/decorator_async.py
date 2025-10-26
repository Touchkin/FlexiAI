#!/usr/bin/env python3
"""Async Decorator Examples.

This example demonstrates using the @flexiai_chat decorator with async functions.
The decorator automatically detects async functions and uses the async client.
"""

import asyncio

from flexiai import FlexiAI, FlexiAIConfig, flexiai_chat

# Configure FlexiAI globally
config = FlexiAIConfig(
    providers=[
        {"name": "openai", "api_key": "your-openai-api-key"},
        {"name": "gemini", "api_key": "your-gemini-api-key"},
    ],
    primary_provider="openai",
    fallback_providers=["gemini"],
)

FlexiAI.set_global_config(config)


# Example 1: Simple async function
@flexiai_chat
async def ask_ai_async(question: str) -> str:
    """Async version of ask_ai."""
    pass  # Implementation handled by decorator


# Example 2: Async with system message
@flexiai_chat(system_message="You are a helpful coding assistant.")
async def code_assistant(question: str) -> str:
    """Get coding help asynchronously."""
    pass


# Example 3: Async with temperature
@flexiai_chat(temperature=0.8)
async def creative_async(prompt: str) -> str:
    """Generate creative content asynchronously."""
    pass


# Example 4: Multiple async calls concurrently
@flexiai_chat(system_message="You are a translator.")
async def translator(text: str) -> str:
    """Translate text."""
    pass


async def example_basic_async():
    """Demonstrate basic async usage."""
    print("\n" + "=" * 60)
    print("BASIC ASYNC USAGE")
    print("=" * 60)

    print("\n1. Simple Async Question:")
    print("-" * 40)
    answer = await ask_ai_async("What is async programming?")
    print(f"Answer: {answer}")

    print("\n2. Code Assistant:")
    print("-" * 40)
    help_text = await code_assistant("How do I use asyncio in Python?")
    print(f"Help: {help_text}")

    print("\n3. Creative Content:")
    print("-" * 40)
    content = await creative_async("Write a haiku about programming")
    print(f"Haiku:\n{content}")


async def example_concurrent_calls():
    """Demonstrate concurrent async calls."""
    print("\n" + "=" * 60)
    print("CONCURRENT ASYNC CALLS")
    print("=" * 60)

    print("\nMaking 3 concurrent requests...")
    print("-" * 40)

    # Create multiple async tasks
    tasks = [
        ask_ai_async("What is machine learning?"),
        ask_ai_async("What is deep learning?"),
        ask_ai_async("What is natural language processing?"),
    ]

    # Run them concurrently
    import time

    start = time.time()
    results = await asyncio.gather(*tasks)
    end = time.time()

    print(f"\nCompleted {len(tasks)} requests in {end - start:.2f} seconds")
    print("\nResults:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result[:100]}...")


async def example_translation_pipeline():
    """Demonstrate an async translation pipeline."""
    print("\n" + "=" * 60)
    print("ASYNC TRANSLATION PIPELINE")
    print("=" * 60)

    texts = [
        "Hello, how are you?",
        "The weather is nice today.",
        "I love programming.",
    ]

    print(f"\nTranslating {len(texts)} texts to Spanish concurrently...")
    print("-" * 40)

    # Create translation tasks
    translation_tasks = [translator(f"Translate to Spanish: {text}") for text in texts]

    # Run concurrently
    import time

    start = time.time()
    translations = await asyncio.gather(*translation_tasks)
    end = time.time()

    print(f"\nCompleted in {end - start:.2f} seconds\n")
    for original, translated in zip(texts, translations):
        print(f"Original: {original}")
        print(f"Spanish:  {translated}\n")


async def example_async_workflow():
    """Demonstrate a complete async workflow."""
    print("\n" + "=" * 60)
    print("ASYNC WORKFLOW EXAMPLE")
    print("=" * 60)

    @flexiai_chat(system_message="You are a research assistant.")
    async def research_assistant(query: str) -> str:
        pass

    @flexiai_chat(system_message="You are a summarizer. Be concise.")
    async def summarizer(text: str) -> str:
        pass

    print("\n1. Research Phase:")
    print("-" * 40)
    topic = "quantum computing"
    research = await research_assistant(f"Explain {topic} in detail")
    print(f"Research results: {research[:200]}...")

    print("\n2. Summary Phase:")
    print("-" * 40)
    summary = await summarizer(f"Summarize this: {research}")
    print(f"Summary: {summary}")


async def example_error_handling():
    """Demonstrate error handling in async decorators."""
    print("\n" + "=" * 60)
    print("ASYNC ERROR HANDLING")
    print("=" * 60)

    @flexiai_chat
    async def safe_async_chat(message: str) -> str:
        pass

    try:
        print("\nAttempting async chat with automatic fallback...")
        result = await safe_async_chat("Tell me a joke")
        print(f"Success: {result}")
    except Exception as e:
        print(f"Error: {e}")
        print("All providers failed")


async def example_mixed_sync_async():
    """Demonstrate mixing sync and async decorated functions."""
    print("\n" + "=" * 60)
    print("MIXING SYNC AND ASYNC")
    print("=" * 60)

    # Sync version
    @flexiai_chat
    def sync_chat(message: str) -> str:
        pass

    # Async version
    @flexiai_chat
    async def async_chat(message: str) -> str:
        pass

    print("\n1. Using Sync Version:")
    print("-" * 40)
    sync_result = sync_chat("Hello from sync")
    print(f"Sync: {sync_result}")

    print("\n2. Using Async Version:")
    print("-" * 40)
    async_result = await async_chat("Hello from async")
    print(f"Async: {async_result}")

    print("\n3. Multiple Async Calls:")
    print("-" * 40)
    results = await asyncio.gather(
        async_chat("Question 1"), async_chat("Question 2"), async_chat("Question 3")
    )
    print(f"Got {len(results)} responses concurrently")


async def main():
    """Run all async examples."""
    print("=" * 60)
    print("FlexiAI Decorator - Async Examples")
    print("=" * 60)

    try:
        await example_basic_async()
        await example_concurrent_calls()
        await example_translation_pipeline()
        await example_async_workflow()
        await example_error_handling()
        await example_mixed_sync_async()

        print("\n" + "=" * 60)
        print("All async examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Make sure you have set valid API keys in the configuration.")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
