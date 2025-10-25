"""
Google Gemini Basic Examples

This script demonstrates basic usage of FlexiAI with Google Gemini Developer API.

Requirements:
- Google Gemini API key (get from https://aistudio.google.com/app/apikey)
- Set environment variable: export GEMINI_API_KEY="your-key"
"""

import os
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, Message


def example_1_simple_completion():
    """Example 1: Simple completion with Gemini"""
    print("\n" + "="*60)
    print("Example 1: Simple Completion")
    print("="*60)
    
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="gemini",
                api_key=os.getenv("GEMINI_API_KEY"),
                model="gemini-2.0-flash",
                priority=1
            )
        ]
    )
    
    client = FlexiAI(config)
    
    response = client.chat_completion(
        messages=[
            Message(role="user", content="What is Python in one sentence?")
        ],
        max_tokens=100
    )
    
    print(f"Response: {response.content}")
    print(f"Tokens used: {response.usage.total_tokens}")
    print(f"Provider: {response.metadata.provider}")


def example_2_with_system_message():
    """Example 2: Using system messages"""
    print("\n" + "="*60)
    print("Example 2: With System Message")
    print("="*60)
    
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="gemini",
                api_key=os.getenv("GEMINI_API_KEY"),
                model="gemini-2.0-flash",
                priority=1
            )
        ]
    )
    
    client = FlexiAI(config)
    
    response = client.chat_completion(
        messages=[
            Message(role="system", content="You are a helpful Python programming expert. Keep answers concise."),
            Message(role="user", content="How do I create a list in Python?")
        ],
        max_tokens=200,
        temperature=0.7
    )
    
    print(f"Response: {response.content}")
    print(f"Tokens: {response.usage.total_tokens}")


def example_3_multi_turn_conversation():
    """Example 3: Multi-turn conversation"""
    print("\n" + "="*60)
    print("Example 3: Multi-Turn Conversation")
    print("="*60)
    
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="gemini",
                api_key=os.getenv("GEMINI_API_KEY"),
                model="gemini-2.0-flash",
                priority=1
            )
        ]
    )
    
    client = FlexiAI(config)
    
    # Start conversation
    conversation = [
        Message(role="user", content="What is machine learning?")
    ]
    
    response1 = client.chat_completion(
        messages=conversation,
        max_tokens=150
    )
    
    print("User: What is machine learning?")
    print(f"Assistant: {response1.content}\n")
    
    # Continue conversation
    conversation.extend([
        Message(role="assistant", content=response1.content),
        Message(role="user", content="Can you give me a simple example?")
    ])
    
    response2 = client.chat_completion(
        messages=conversation,
        max_tokens=200
    )
    
    print("User: Can you give me a simple example?")
    print(f"Assistant: {response2.content}")
    print(f"\nTotal tokens used: {response1.usage.total_tokens + response2.usage.total_tokens}")


def example_4_temperature_control():
    """Example 4: Temperature control for creativity"""
    print("\n" + "="*60)
    print("Example 4: Temperature Control")
    print("="*60)
    
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="gemini",
                api_key=os.getenv("GEMINI_API_KEY"),
                model="gemini-2.0-flash",
                priority=1
            )
        ]
    )
    
    client = FlexiAI(config)
    
    prompt = "Write a one-sentence description of a sunset"
    
    # Low temperature (more deterministic)
    print("\nWith temperature=0.3 (more focused):")
    response_low = client.chat_completion(
        messages=[Message(role="user", content=prompt)],
        temperature=0.3,
        max_tokens=50
    )
    print(f"  {response_low.content}")
    
    # High temperature (more creative)
    print("\nWith temperature=1.5 (more creative):")
    response_high = client.chat_completion(
        messages=[Message(role="user", content=prompt)],
        temperature=1.5,
        max_tokens=50
    )
    print(f"  {response_high.content}")


def example_5_advanced_parameters():
    """Example 5: Using advanced parameters"""
    print("\n" + "="*60)
    print("Example 5: Advanced Parameters")
    print("="*60)
    
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="gemini",
                api_key=os.getenv("GEMINI_API_KEY"),
                model="gemini-1.5-pro",  # More powerful model
                priority=1
            )
        ]
    )
    
    client = FlexiAI(config)
    
    response = client.chat_completion(
        messages=[
            Message(role="user", content="Explain quantum computing")
        ],
        temperature=0.7,
        max_tokens=500,
        top_p=0.95,  # Nucleus sampling
        top_k=40,    # Top-k sampling (Gemini-specific)
        stop=["Conclusion:", "Summary:"]  # Stop sequences
    )
    
    print(f"Response: {response.content}")
    print(f"\nMetadata:")
    print(f"  Model: {response.metadata.model}")
    print(f"  Provider: {response.metadata.provider}")
    print(f"  Finish Reason: {response.metadata.finish_reason}")
    print(f"  Tokens: {response.usage.total_tokens}")


def example_6_error_handling():
    """Example 6: Error handling"""
    print("\n" + "="*60)
    print("Example 6: Error Handling")
    print("="*60)
    
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="gemini",
                api_key="invalid-api-key",  # Invalid key
                model="gemini-2.0-flash",
                priority=1
            )
        ]
    )
    
    client = FlexiAI(config)
    
    try:
        response = client.chat_completion(
            messages=[Message(role="user", content="Hello")]
        )
    except Exception as e:
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\n✅ Error handled gracefully!")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("FlexiAI - Google Gemini Examples")
    print("="*60)
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("\n⚠️  ERROR: GEMINI_API_KEY environment variable not set!")
        print("Please set it with: export GEMINI_API_KEY='your-key'")
        print("Get your API key from: https://aistudio.google.com/app/apikey")
        return
    
    try:
        example_1_simple_completion()
        example_2_with_system_message()
        example_3_multi_turn_conversation()
        example_4_temperature_control()
        example_5_advanced_parameters()
        example_6_error_handling()
        
        print("\n" + "="*60)
        print("✅ All examples completed successfully!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
