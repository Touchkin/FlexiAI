#!/usr/bin/env python3
"""Advanced Decorator Examples.

This example demonstrates advanced features of the @flexiai_chat decorator:
- Multi-provider configuration with failover
- Provider selection
- Temperature control for different tasks
- Different decorator syntax options

Requirements:
    - Set OPENAI_API_KEY environment variable
    - Optionally set GOOGLE_APPLICATION_CREDENTIALS for Vertex AI
"""

import os

from flexiai import FlexiAI, FlexiAIConfig, flexiai_chat

# Configure FlexiAI with multiple providers and automatic failover
config = FlexiAIConfig(
    providers=[
        {
            "name": "openai",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-4o-mini",
            "priority": 1,  # Primary provider
        },
        {
            "name": "vertexai",
            "api_key": "not-used",  # Uses Application Default Credentials (service account)
            "model": "gemini-1.5-flash",
            "priority": 2,  # Fallback provider
            "config": {
                "project": "dev-gemini-427512",  # GCP project ID
                "location": "us-central1",
            },
        },
    ],
)

FlexiAI.set_global_config(config)


# Example 1: Use OpenAI explicitly
@flexiai_chat(provider="openai", temperature=0.3)
def openai_assistant(question: str) -> str:
    """Use OpenAI specifically for precise answers."""
    pass


# Example 2: Use Vertex AI/Gemini explicitly
@flexiai_chat(provider="vertexai", temperature=0.7)
def gemini_assistant(question: str) -> str:
    """Use Google Gemini via Vertex AI for balanced responses."""
    pass


# Example 3: Function for travel advice (shows multi-parameter usage)
@flexiai_chat(system_message="You are a travel expert. Provide detailed recommendations.")
def travel_advisor(query: str, budget: str = None, interests: str = None) -> str:
    """Get travel advice. First parameter is always the user message."""
    pass


# Example 4: Low temperature for factual responses
@flexiai_chat(
    system_message="Provide accurate, factual information.",
    temperature=0.1,
    max_tokens=300,
)
def fact_checker(claim: str) -> str:
    """Verify factual claims with low temperature (more deterministic)."""
    pass


# Example 5: High temperature for creative tasks
@flexiai_chat(
    system_message="You are a creative storyteller.",
    temperature=0.95,
    max_tokens=500,
)
def story_generator(theme: str) -> str:
    """Generate creative stories with high temperature (more random)."""
    pass


# Example 6: Using decorator without parentheses
@flexiai_chat
def quick_answer(question: str) -> str:
    """Quick answers with default settings."""
    pass


def demonstrate_basic_usage():
    """Demonstrate basic advanced features."""
    print("\n" + "=" * 60)
    print("BASIC ADVANCED USAGE")
    print("=" * 60)

    # Using specific provider
    print("\n1. Using Gemini Provider:")
    print("-" * 40)
    answer = gemini_assistant("What are the benefits of cloud computing?")
    print(answer)

    # Low temperature for facts
    print("\n2. Fact Checking (Low Temperature):")
    print("-" * 40)
    result = fact_checker("The Earth is flat.")
    print(result)

    # High temperature for creativity
    print("\n3. Creative Story (High Temperature):")
    print("-" * 40)
    story = story_generator("A robot discovering emotions")
    print(story)


def demonstrate_multiple_parameters():
    """Demonstrate functions with multiple parameters."""
    print("\n" + "=" * 60)
    print("MULTIPLE PARAMETERS")
    print("=" * 60)

    # Note: The decorator extracts the first parameter as the user message
    # For more complex scenarios, you can structure your prompt in the function call

    print("\n1. Travel Advisor:")
    print("-" * 40)

    # The first parameter becomes the user message
    # You can construct it with information from other parameters
    destination = "Tokyo"
    budget = "$2000"
    interests = "technology, food, culture"

    query = (
        f"I want to visit {destination} with a budget of {budget}. "
        f"My interests are: {interests}. Please suggest an itinerary."
    )

    # Note: When using multiple parameters, construct the message manually
    # or use a wrapper function
    # For simplicity with decorators, use a single parameter or construct the prompt
    advice = travel_advisor(query, budget, interests)
    print(advice)


def demonstrate_temperature_effects():
    """Demonstrate the effect of different temperature settings."""
    print("\n" + "=" * 60)
    print("TEMPERATURE EFFECTS")
    print("=" * 60)

    prompt = "Describe a sunset"

    print("\n1. Low Temperature (0.1) - More Deterministic:")
    print("-" * 40)
    factual = fact_checker(prompt)
    print(factual)

    print("\n2. High Temperature (0.95) - More Creative:")
    print("-" * 40)
    creative = story_generator(prompt)
    print(creative)


def demonstrate_different_syntax():
    """Demonstrate different decorator syntax options."""
    print("\n" + "=" * 60)
    print("DECORATOR SYNTAX OPTIONS")
    print("=" * 60)

    # Both syntax options work the same:

    # Option 1: Without parentheses (uses defaults)
    @flexiai_chat
    def option1(question: str) -> str:
        pass

    # Option 2: With parentheses (can specify parameters)
    @flexiai_chat()
    def option2(question: str) -> str:
        pass

    # Option 3: With parameters
    @flexiai_chat(temperature=0.5)
    def option3(question: str) -> str:
        pass

    print("\nAll three syntax options work correctly:")
    test_q = "What is 2+2?"

    print(f"\nOption 1 (no parentheses): {option1(test_q)}")
    print(f"Option 2 (empty parentheses): {option2(test_q)}")
    print(f"Option 3 (with params): {option3(test_q)}")


def demonstrate_error_handling():
    """Demonstrate error handling with decorators."""
    print("\n" + "=" * 60)
    print("ERROR HANDLING")
    print("=" * 60)

    @flexiai_chat
    def safe_chat(message: str) -> str:
        pass

    try:
        # This will use fallback providers if primary fails
        result = safe_chat("Tell me a joke")
        print(f"\nSuccess: {result}")
    except Exception as e:
        print(f"\nError occurred: {e}")
        print("All providers failed or configuration issue")


def main():
    """Run all advanced examples."""
    print("=" * 60)
    print("FlexiAI Decorator - Advanced Examples")
    print("=" * 60)

    try:
        demonstrate_basic_usage()
        demonstrate_multiple_parameters()
        demonstrate_temperature_effects()
        demonstrate_different_syntax()
        demonstrate_error_handling()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Make sure you have set valid API keys in the configuration.")


if __name__ == "__main__":
    main()
