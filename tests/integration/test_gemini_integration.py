"""
Integration tests for Gemini provider with real API.

These tests make actual API calls to Google Gemini API.
Set GEMINI_API_KEY environment variable to run these tests.

Test budget: Limited API calls to minimize costs.
"""

import os
import time

import pytest

from flexiai import FlexiAI, FlexiAIConfig, ProviderConfig
from flexiai.exceptions import ProviderException
from flexiai.models import Message, UnifiedRequest
from flexiai.providers.gemini_provider import GeminiProvider

# Check if API key is available
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
pytestmark = pytest.mark.skipif(
    not GEMINI_API_KEY, reason="GEMINI_API_KEY environment variable not set"
)


@pytest.fixture
def gemini_config():
    """Fixture for Gemini provider configuration."""
    return ProviderConfig(
        name="gemini",
        api_key=GEMINI_API_KEY,
        model="gemini-2.0-flash-exp",
        priority=1,
    )


@pytest.fixture
def gemini_provider(gemini_config):
    """Fixture for GeminiProvider instance."""
    return GeminiProvider(gemini_config)


@pytest.fixture
def client_with_gemini():
    """Fixture for FlexiAI client with Gemini provider."""
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="gemini",
                api_key=GEMINI_API_KEY,
                model="gemini-2.0-flash-exp",
                priority=1,
            )
        ]
    )
    return FlexiAI(config)


class TestGeminiBasicCompletion:
    """Tests for basic Gemini completions."""

    def test_simple_completion(self, gemini_provider):
        """Test simple text completion with Gemini."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Say 'Hello' and nothing else.")],
            max_tokens=50,
            temperature=0.1,
        )

        response = gemini_provider.chat_completion(request)

        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
        assert response.provider == "gemini"
        assert response.model == "gemini-2.0-flash-exp"
        assert response.usage.total_tokens > 0
        assert response.finish_reason in ["stop", "length"]

        # Rate limit
        time.sleep(1)

    def test_multi_turn_conversation(self, gemini_provider):
        """Test multi-turn conversation."""
        request = UnifiedRequest(
            messages=[
                Message(role="user", content="What is 2+2?"),
                Message(role="assistant", content="2+2 equals 4."),
                Message(role="user", content="What about 3+3?"),
            ],
            max_tokens=50,
            temperature=0.1,
        )

        response = gemini_provider.chat_completion(request)

        assert response is not None
        assert "6" in response.content or "six" in response.content.lower()
        assert response.usage.total_tokens > 0

        # Rate limit
        time.sleep(1)

    def test_with_temperature(self, gemini_provider):
        """Test completion with different temperature."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Say hello")],
            temperature=0.9,
            max_tokens=30,
        )

        response = gemini_provider.chat_completion(request)

        assert response is not None
        assert len(response.content) > 0

        # Rate limit
        time.sleep(1)


class TestGeminiWithSystemMessage:
    """Tests for Gemini with system messages."""

    def test_system_message_handling(self, gemini_provider):
        """Test that system messages are properly handled."""
        request = UnifiedRequest(
            messages=[
                Message(role="system", content="You are a helpful math tutor. Be concise."),
                Message(role="user", content="What is 5+5?"),
            ],
            max_tokens=50,
            temperature=0.1,
        )

        response = gemini_provider.chat_completion(request)

        assert response is not None
        assert "10" in response.content or "ten" in response.content.lower()

        # Rate limit
        time.sleep(1)


class TestGeminiViaClient:
    """Tests for Gemini through FlexiAI client."""

    def test_client_completion(self, client_with_gemini):
        """Test completion through FlexiAI client."""
        response = client_with_gemini.chat_completion(
            messages=[Message(role="user", content="Say 'test' and nothing else.")],
            max_tokens=20,
            temperature=0.1,
        )

        assert response is not None
        assert response.provider == "gemini"
        assert response.content is not None

        # Rate limit
        time.sleep(1)

    def test_client_request_stats(self, client_with_gemini):
        """Test that request stats are tracked."""
        # Make a request
        client_with_gemini.chat_completion(
            messages=[Message(role="user", content="Hi")],
            max_tokens=10,
        )

        # Check stats
        stats = client_with_gemini.get_request_stats()
        assert stats["total_requests"] >= 1
        assert stats["successful_requests"] >= 1
        assert "gemini" in stats["providers_used"]

        # Rate limit
        time.sleep(1)


class TestGeminiTokenUsage:
    """Tests for token usage tracking."""

    def test_token_usage_tracking(self, gemini_provider):
        """Test that token usage is properly tracked."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Count from 1 to 5.")],
            max_tokens=100,
        )

        response = gemini_provider.chat_completion(request)

        assert response.usage is not None
        assert response.usage.prompt_tokens > 0
        assert response.usage.completion_tokens > 0
        assert response.usage.total_tokens == (
            response.usage.prompt_tokens + response.usage.completion_tokens
        )

        # Rate limit
        time.sleep(1)


class TestGeminiErrorHandling:
    """Tests for error handling."""

    def test_invalid_api_key(self):
        """Test handling of invalid API key."""
        config = ProviderConfig(
            name="gemini",
            api_key="AIzaSyInvalidKey123456789012345678901",  # Invalid but correct format
            model="gemini-2.0-flash-exp",
            priority=1,
        )

        provider = GeminiProvider(config)

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        with pytest.raises(ProviderException):
            provider.chat_completion(request)


class TestGeminiHealthCheck:
    """Tests for health check."""

    def test_health_check_with_valid_key(self, gemini_provider):
        """Test health check with valid API key."""
        is_healthy = gemini_provider.health_check()
        assert is_healthy is True

        # Rate limit
        time.sleep(1)

    def test_health_check_with_invalid_key(self):
        """Test health check with invalid API key."""
        config = ProviderConfig(
            name="gemini",
            api_key="AIzaSyInvalidKey123456789012345678901",
            model="gemini-2.0-flash-exp",
            priority=1,
        )

        provider = GeminiProvider(config)
        is_healthy = provider.health_check()
        assert is_healthy is False
