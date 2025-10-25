"""
Integration test configuration and fixtures.

These tests require real API keys and make actual API calls.
Run with: pytest -m integration
"""

import os
import time

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require real API keys)"
    )


@pytest.fixture(scope="session")
def openai_api_key():
    """Get OpenAI API key from environment."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")
    return api_key


@pytest.fixture(scope="session")
def token_budget():
    """
    Token budget tracker to prevent excessive API costs.

    Max 1000 tokens across all integration tests.
    """
    budget = {"used": 0, "limit": 1000}

    yield budget

    # Report at end of session
    print(f"\n📊 Integration Test Token Usage: {budget['used']}/{budget['limit']}")
    if budget["used"] > budget["limit"]:
        print("⚠️  WARNING: Token budget exceeded!")


@pytest.fixture
def rate_limiter():
    """
    Add rate limiting to prevent hitting API rate limits.

    Adds 1 second delay between tests.
    """
    delay = float(os.getenv("INTEGRATION_TEST_DELAY", "1.0"))

    def wait():
        time.sleep(delay)

    yield wait

    # Cleanup: wait after test completes
    wait()


@pytest.fixture
def track_tokens(token_budget):
    """
    Track token usage and enforce budget.

    Usage:
        response = client.chat_completion(...)
        track_tokens(response.usage.total_tokens)
    """

    def track(tokens_used: int):
        token_budget["used"] += tokens_used
        if token_budget["used"] > token_budget["limit"]:
            pytest.fail("Token budget exceeded: " f"{token_budget['used']}/{token_budget['limit']}")

    return track


@pytest.fixture
def integration_client(openai_api_key):
    """
    Create FlexiAI client configured for integration testing.

    Uses minimal token limits to reduce costs.
    """
    from flexiai import FlexiAI, FlexiAIConfig, ProviderConfig
    from flexiai.providers.registry import ProviderRegistry

    # Clear the singleton registry before each test
    with ProviderRegistry._lock:
        if ProviderRegistry._instance is not None:
            ProviderRegistry._instance.clear()

    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="openai",
                priority=1,
                api_key=openai_api_key,
                model="gpt-4.1-nano-2025-04-14",  # Use the nano model for cost savings
                timeout=30,
            )
        ],
        default_model="gpt-4.1-nano-2025-04-14",
        default_temperature=0.7,
        default_max_tokens=50,  # Keep responses short
    )

    client = FlexiAI(config=config)

    yield client

    # Cleanup after test
    with ProviderRegistry._lock:
        if ProviderRegistry._instance is not None:
            ProviderRegistry._instance.clear()
