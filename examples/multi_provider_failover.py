"""
Multi-Provider Failover Example

This script demonstrates FlexiAI's automatic failover capabilities with
multiple providers (OpenAI → Gemini → Vertex AI).

Requirements:
- At least one provider configured with valid credentials
- Environment variables:
  - OPENAI_API_KEY (optional)
  - GEMINI_API_KEY (optional)
  - GOOGLE_CLOUD_PROJECT (optional)
  - GOOGLE_APPLICATION_CREDENTIALS (optional)
"""

import os
import json
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, Message, CircuitBreakerConfig
from flexiai.exceptions import AllProvidersFailedError


def example_1_basic_failover():
    """Example 1: Basic three-provider failover"""
    print("\n" + "="*70)
    print("Example 1: Basic Multi-Provider Failover")
    print("="*70)
    
    providers = []
    
    # Add OpenAI if available
    if os.getenv("OPENAI_API_KEY"):
        providers.append(
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=1
            )
        )
        print("✓ OpenAI configured (Priority 1)")
    
    # Add Gemini if available
    if os.getenv("GEMINI_API_KEY"):
        providers.append(
            ProviderConfig(
                name="gemini",
                api_key=os.getenv("GEMINI_API_KEY"),
                model="gemini-2.0-flash",
                priority=2
            )
        )
        print("✓ Gemini configured (Priority 2)")
    
    # Add Vertex AI if available
    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_file and os.path.exists(service_account_file):
        with open(service_account_file, 'r') as f:
            project_id = json.load(f).get('project_id')
        
        providers.append(
            ProviderConfig(
                name="vertexai",
                api_key="not-used",
                model="gemini-2.0-flash",
                priority=3,
                config={
                    "project": project_id,
                    "location": "us-central1",
                    "service_account_file": service_account_file
                }
            )
        )
        print("✓ Vertex AI configured (Priority 3)")
    
    if not providers:
        print("\n⚠️  No providers configured. Please set at least one API key.")
        return
    
    print(f"\nTotal providers: {len(providers)}")
    
    config = FlexiAIConfig(providers=providers)
    client = FlexiAI(config)
    
    # Make a request - will use highest priority available provider
    response = client.chat_completion(
        messages=[
            Message(role="user", content="Say hello and tell me which provider you are!")
        ],
        max_tokens=50
    )
    
    print(f"\n✅ Response: {response.content}")
    print(f"🔧 Provider used: {response.metadata.provider}")
    print(f"📊 Tokens: {response.usage.total_tokens}")


def example_2_failover_simulation():
    """Example 2: Simulate failover when primary provider fails"""
    print("\n" + "="*70)
    print("Example 2: Failover Simulation")
    print("="*70)
    
    providers = [
        # Invalid OpenAI key (will fail)
        ProviderConfig(
            name="openai",
            api_key="sk-invalid-key-for-testing",
            model="gpt-4o-mini",
            priority=1
        )
    ]
    
    # Add valid fallback if available
    if os.getenv("GEMINI_API_KEY"):
        providers.append(
            ProviderConfig(
                name="gemini",
                api_key=os.getenv("GEMINI_API_KEY"),
                model="gemini-2.0-flash",
                priority=2
            )
        )
    elif os.getenv("OPENAI_API_KEY"):
        # Use valid OpenAI as fallback
        providers.append(
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=2
            )
        )
    
    config = FlexiAIConfig(
        providers=providers,
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=1,  # Fail fast for demo
            recovery_timeout=60
        )
    )
    
    client = FlexiAI(config)
    
    print("\n📝 Attempting request with invalid primary provider...")
    print("   (Should automatically failover to secondary)")
    
    try:
        response = client.chat_completion(
            messages=[
                Message(role="user", content="Hello!")
            ],
            max_tokens=30
        )
        
        print(f"\n✅ Failover successful!")
        print(f"🔧 Provider used: {response.metadata.provider}")
        print(f"📝 Response: {response.content}")
        
    except AllProvidersFailedError as e:
        print(f"\n❌ All providers failed: {e}")


def example_3_circuit_breaker_demo():
    """Example 3: Circuit breaker pattern demonstration"""
    print("\n" + "="*70)
    print("Example 3: Circuit Breaker Pattern")
    print("="*70)
    
    providers = []
    
    # Configure available providers
    if os.getenv("OPENAI_API_KEY"):
        providers.append(
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=1
            )
        )
    
    if os.getenv("GEMINI_API_KEY"):
        providers.append(
            ProviderConfig(
                name="gemini",
                api_key=os.getenv("GEMINI_API_KEY"),
                model="gemini-2.0-flash",
                priority=2
            )
        )
    
    if not providers:
        print("⚠️  Need at least one valid provider")
        return
    
    config = FlexiAIConfig(
        providers=providers,
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception="ProviderException"
        )
    )
    
    client = FlexiAI(config)
    
    print("\nCircuit Breaker Configuration:")
    print(f"  Failure Threshold: 3 failures")
    print(f"  Recovery Timeout: 60 seconds")
    
    # Make several requests
    for i in range(5):
        response = client.chat_completion(
            messages=[
                Message(role="user", content=f"Request {i+1}: Say hi!")
            ],
            max_tokens=20
        )
        
        print(f"\nRequest {i+1}:")
        print(f"  Provider: {response.metadata.provider}")
        print(f"  Response: {response.content}")
    
    # Check provider status
    print("\n" + "="*70)
    print("Provider Status After Requests:")
    print("="*70)
    
    status = client.get_provider_status()
    for provider_name, info in status.items():
        print(f"\n{provider_name}:")
        print(f"  Healthy: {info['healthy']}")
        print(f"  Circuit Breaker State: {info['circuit_breaker']['state']}")
        print(f"  Successes: {info['circuit_breaker']['successes']}")
        print(f"  Failures: {info['circuit_breaker']['failures']}")
        print(f"  Total Requests: {info['total_requests']}")


def example_4_provider_comparison():
    """Example 4: Compare responses from different providers"""
    print("\n" + "="*70)
    print("Example 4: Provider Comparison")
    print("="*70)
    
    prompt = "Explain machine learning in one sentence"
    
    providers_to_test = []
    
    if os.getenv("OPENAI_API_KEY"):
        providers_to_test.append(("openai", "gpt-4o-mini"))
    
    if os.getenv("GEMINI_API_KEY"):
        providers_to_test.append(("gemini", "gemini-2.0-flash"))
    
    service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_file and os.path.exists(service_account_file):
        providers_to_test.append(("vertexai", "gemini-2.0-flash"))
    
    if not providers_to_test:
        print("⚠️  No providers configured")
        return
    
    print(f"\nPrompt: \"{prompt}\"\n")
    
    for provider_name, model in providers_to_test:
        print(f"\n{provider_name.upper()} ({model}):")
        print("-" * 70)
        
        # Configure single provider
        if provider_name == "vertexai":
            with open(service_account_file, 'r') as f:
                project_id = json.load(f).get('project_id')
            
            provider_config = ProviderConfig(
                name=provider_name,
                api_key="not-used",
                model=model,
                priority=1,
                config={
                    "project": project_id,
                    "location": "us-central1",
                    "service_account_file": service_account_file
                }
            )
        else:
            api_key = os.getenv(
                "OPENAI_API_KEY" if provider_name == "openai" else "GEMINI_API_KEY"
            )
            provider_config = ProviderConfig(
                name=provider_name,
                api_key=api_key,
                model=model,
                priority=1
            )
        
        config = FlexiAIConfig(providers=[provider_config])
        client = FlexiAI(config)
        
        response = client.chat_completion(
            messages=[Message(role="user", content=prompt)],
            temperature=0.7,
            max_tokens=100
        )
        
        print(f"Response: {response.content}")
        print(f"Tokens: {response.usage.total_tokens}")


def example_5_request_statistics():
    """Example 5: Track request statistics across providers"""
    print("\n" + "="*70)
    print("Example 5: Request Statistics Tracking")
    print("="*70)
    
    providers = []
    
    if os.getenv("OPENAI_API_KEY"):
        providers.append(
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=1
            )
        )
    
    if os.getenv("GEMINI_API_KEY"):
        providers.append(
            ProviderConfig(
                name="gemini",
                api_key=os.getenv("GEMINI_API_KEY"),
                model="gemini-2.0-flash",
                priority=2
            )
        )
    
    if not providers:
        print("⚠️  No providers configured")
        return
    
    config = FlexiAIConfig(providers=providers)
    client = FlexiAI(config)
    
    # Make multiple requests
    print("\nMaking 10 requests...")
    for i in range(10):
        response = client.chat_completion(
            messages=[Message(role="user", content=f"Count to {i+1}")],
            max_tokens=20
        )
        print(f"  Request {i+1}: {response.metadata.provider}")
    
    # Get statistics
    stats = client.get_request_stats()
    
    print("\n" + "="*70)
    print("Request Statistics:")
    print("="*70)
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Successful: {stats['successful_requests']}")
    print(f"Failed: {stats['failed_requests']}")
    print(f"\nProviders Used:")
    for provider, count in stats['providers_used'].items():
        percentage = (count / stats['total_requests']) * 100
        print(f"  {provider}: {count} requests ({percentage:.1f}%)")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("FlexiAI - Multi-Provider Failover Examples")
    print("="*70)
    
    # Check configuration
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    has_vertexai = bool(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and 
        os.path.exists(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""))
    )
    
    print("\nConfigured Providers:")
    print(f"  OpenAI: {'✓' if has_openai else '✗'}")
    print(f"  Gemini: {'✓' if has_gemini else '✗'}")
    print(f"  Vertex AI: {'✓' if has_vertexai else '✗'}")
    
    if not (has_openai or has_gemini or has_vertexai):
        print("\n⚠️  No providers configured!")
        print("\nPlease set at least one of:")
        print("  export OPENAI_API_KEY='sk-...'")
        print("  export GEMINI_API_KEY='AIza...'")
        print("  export GOOGLE_APPLICATION_CREDENTIALS='/path/to/service-account.json'")
        return
    
    try:
        example_1_basic_failover()
        example_2_failover_simulation()
        example_3_circuit_breaker_demo()
        example_4_provider_comparison()
        example_5_request_statistics()
        
        print("\n" + "="*70)
        print("✅ All examples completed successfully!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
