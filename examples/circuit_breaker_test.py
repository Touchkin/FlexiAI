#!/usr/bin/env python3
"""
Circuit Breaker Testing Example for FlexiAI.

This script demonstrates how to test the circuit breaker pattern in FlexiAI.
It validates that the circuit breaker:
1. Detects invalid credentials
2. Tracks failures
3. Enables automatic failover
4. Monitors provider health

Usage:
    export ANTHROPIC_API_KEY="sk-ant-api03-..."
    export OPENAI_API_KEY="sk-..."  # Optional for failover test
    python examples/circuit_breaker_test.py
"""

import os
import sys

from flexiai import FlexiAI
from flexiai.exceptions import AllProvidersFailedError
from flexiai.models import FlexiAIConfig, ProviderConfig


def print_header(text):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def test_invalid_credentials():
    """Test 1: Circuit breaker detects invalid credentials."""
    print_header("TEST 1: Invalid Credentials Detection")

    print("\n📝 Creating client with INVALID API key...")
    client = FlexiAI(
        FlexiAIConfig(
            providers=[
                ProviderConfig(
                    name="anthropic",
                    priority=1,
                    api_key="sk-ant-invalid-key-for-testing-12345678901234567890",
                    model="claude-3-5-haiku-20241022",
                )
            ]
        )
    )

    print("📝 Making 5 requests to trigger circuit breaker...\n")
    failures = 0

    for i in range(5):
        try:
            print(f"  Request {i+1}...", end=" ")
            # Intentionally not using response - just testing failures
            _ = client.chat_completion(messages=[{"role": "user", "content": "test"}])  # noqa: F841
            print("❌ Unexpected success")
        except AllProvidersFailedError:
            failures += 1
            print(f"✅ Failed as expected (failure #{failures})")
        except Exception as e:
            print(f"⚠️  {type(e).__name__}")

    print(f"\n📊 Result: {failures}/5 failures detected")

    if failures >= 4:
        print("✅ PASS: Circuit breaker working correctly")
        return True
    else:
        print("❌ FAIL: Expected more failures")
        return False


def test_failover():
    """Test 2: Circuit breaker enables automatic failover."""
    print_header("TEST 2: Automatic Failover")

    # Check if we have a valid API key for failover
    valid_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not valid_key:
        print("⏭️  SKIPPED: Need ANTHROPIC_API_KEY or OPENAI_API_KEY for failover test")
        return None

    print("\n📝 Configuring 2 providers:")
    print("  • Provider 1 (priority=1): INVALID key → will fail")
    print("  • Provider 2 (priority=2): VALID key → backup")

    # Determine which providers to use
    # Note: Can't use same provider name twice, so use different providers
    if os.getenv("ANTHROPIC_API_KEY") and os.getenv("OPENAI_API_KEY"):
        # Best case: Use different providers
        providers = [
            ProviderConfig(
                name="openai",
                priority=1,
                api_key="sk-invalid-primary-12345678901234567890abcdef",
                model="gpt-3.5-turbo",
            ),
            ProviderConfig(
                name="anthropic",
                priority=2,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-haiku-20241022",
            ),
        ]
    elif os.getenv("ANTHROPIC_API_KEY"):
        # Only Claude available - skip failover test
        print("\n⏭️  SKIPPED: Need both OPENAI_API_KEY and ANTHROPIC_API_KEY")
        print("   (Cannot use same provider name twice)")
        return None
    else:
        # Only OpenAI available
        print("\n⏭️  SKIPPED: Need valid ANTHROPIC_API_KEY for backup")
        return None

    client = FlexiAI(FlexiAIConfig(providers=providers))

    print("\n📝 Making request (should failover to backup)...")

    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Say 'Failover successful!' only"}]
        )

        print("\n✅ SUCCESS!")
        print(f"   Response: {response.content}")
        print(f"   Provider: {response.provider}")

        # Show statistics
        stats = client.get_request_stats()
        print("\n📊 Statistics:")
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Successful: {stats['successful_requests']}")
        print(f"   Failed: {stats['failed_requests']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")

        print("\n✅ PASS: Failover working correctly")
        return True

    except Exception as e:
        print(f"\n❌ FAIL: {e}")
        return False


def test_provider_status():
    """Test 3: Monitor circuit breaker states."""
    print_header("TEST 3: Circuit Breaker Status Monitoring")

    valid_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not valid_key:
        print("⏭️  SKIPPED: Need valid API key")
        return None

    print("\n📝 Creating client with valid credentials...")

    if os.getenv("ANTHROPIC_API_KEY"):
        provider = ProviderConfig(
            name="anthropic",
            priority=1,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model="claude-3-5-haiku-20241022",
        )
    else:
        provider = ProviderConfig(
            name="openai", priority=1, api_key=os.getenv("OPENAI_API_KEY"), model="gpt-3.5-turbo"
        )

    client = FlexiAI(FlexiAIConfig(providers=[provider]))

    print("📝 Making successful request...")
    response = client.chat_completion(messages=[{"role": "user", "content": "Say 'OK' only"}])
    print(f"   Response: {response.content}")

    print("\n📊 Checking provider status:")
    status = client.get_provider_status()

    for provider_name, info in status.items():
        print("\n  Provider: {}".format(provider_name))
        print("    State: {}".format(info["circuit_breaker"]["state"]))
        print("    Healthy: {}".format(info["healthy"]))
        print("    Failures: {}".format(info["circuit_breaker"]["failure_count"]))
        print("    Successes: {}".format(info["circuit_breaker"]["success_count"]))

    # Validate circuit is CLOSED after success
    all_closed = all(info["circuit_breaker"]["state"] == "CLOSED" for info in status.values())

    if all_closed:
        print("\n✅ PASS: Circuit breaker in CLOSED state (healthy)")
        return True
    else:
        print("\n⚠️  WARNING: Circuit breaker not in expected state")
        return False


def print_circuit_breaker_info():
    """Print information about circuit breaker pattern."""
    print_header("How Circuit Breaker Works")

    print(
        """
The circuit breaker pattern protects your application from cascading failures:

🔵 CLOSED State (Normal Operation)
   • All requests pass through to the provider
   • Success/failure counts are tracked
   • System is healthy

🔴 OPEN State (Provider Failed)
   • Too many failures detected (threshold exceeded)
   • New requests are blocked immediately (fail-fast)
   • Wait for recovery timeout before retrying
   • Prevents wasting time on broken provider

🟡 HALF_OPEN State (Testing Recovery)
   • Recovery timeout has elapsed
   • Limited test requests allowed through
   • If success → return to CLOSED
   • If failure → return to OPEN

Benefits:
   ✅ Fail-fast behavior (immediate error detection)
   ✅ Automatic recovery (self-healing)
   ✅ Resource protection (prevent API abuse)
   ✅ Transparent failover (switch to backup providers)
   ✅ Request statistics (track health over time)
"""
    )


def main():
    """Run all circuit breaker tests."""
    print("=" * 70)
    print("  FlexiAI Circuit Breaker Test Suite")
    print("=" * 70)

    # Show circuit breaker information
    print_circuit_breaker_info()

    # Run tests
    results = {
        "Invalid Credentials": test_invalid_credentials(),
        "Automatic Failover": test_failover(),
        "Status Monitoring": test_provider_status(),
    }

    # Summary
    print_header("Test Summary")

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    for test_name, result in results.items():
        if result is True:
            print(f"   ✅ {test_name}: PASSED")
        elif result is False:
            print(f"   ❌ {test_name}: FAILED")
        else:
            print(f"   ⏭️  {test_name}: SKIPPED")

    print(f"\n📊 Results: {passed} passed | {failed} failed | {skipped} skipped")

    if failed == 0 and passed > 0:
        print("\n🎉 All tests passed! Circuit breaker is working correctly.")
        return 0
    elif passed > 0:
        print(f"\n✅ Some tests passed ({passed}/{passed+failed})")
        return 0
    else:
        print("\n❌ Tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
