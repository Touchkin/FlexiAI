#!/usr/bin/env python3
"""Basic Decorator Examples.

This example demonstrates the simplest usage of the @flexiai_chat decorator
for creating AI-powered functions.
"""

from flexiai import FlexiAI, FlexiAIConfig, flexiai_chat

# Step 1: Configure FlexiAI globally
# This needs to be done once at the start of your application
config = FlexiAIConfig(
    providers=[
        {
            "name": "openai",
            "api_key": "your-openai-api-key-here",  # Replace with real key
        },
    ],
    primary_provider="openai",
)

# Set global config using either method:
FlexiAI.set_global_config(config)
# OR: set_global_config(config)


# Example 1: Simplest decorator usage
@flexiai_chat
def ask_ai(question: str) -> str:
    """Ask AI a question and get an answer."""
    pass  # Implementation handled by decorator


# Example 2: Decorator with system message
@flexiai_chat(system_message="You are a helpful math tutor.")
def math_tutor(problem: str) -> str:
    """Get help with math problems."""
    pass


# Example 3: Decorator with temperature control
@flexiai_chat(temperature=0.9)
def creative_writer(prompt: str) -> str:
    """Generate creative content."""
    pass


# Example 4: Decorator with multiple parameters
@flexiai_chat(
    system_message="You are a Python programming expert.",
    temperature=0.3,
    max_tokens=500,
)
def code_helper(question: str) -> str:
    """Get help with Python programming."""
    pass


def main():
    """Run basic decorator examples."""
    print("=" * 60)
    print("FlexiAI Decorator - Basic Examples")
    print("=" * 60)

    # Example 1: Simple question
    print("\n1. Simple Question:")
    print("-" * 40)
    question = "What is the capital of France?"
    answer = ask_ai(question)
    print(f"Q: {question}")
    print(f"A: {answer}")

    # Example 2: Math tutoring
    print("\n2. Math Tutoring:")
    print("-" * 40)
    problem = "How do I solve quadratic equations?"
    explanation = math_tutor(problem)
    print(f"Q: {problem}")
    print(f"A: {explanation}")

    # Example 3: Creative writing
    print("\n3. Creative Writing:")
    print("-" * 40)
    prompt = "Write a short poem about autumn"
    poem = creative_writer(prompt)
    print(f"Prompt: {prompt}")
    print(f"Result:\n{poem}")

    # Example 4: Code help
    print("\n4. Code Help:")
    print("-" * 40)
    question = "How do I read a CSV file in Python?"
    help_text = code_helper(question)
    print(f"Q: {question}")
    print(f"A: {help_text}")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
