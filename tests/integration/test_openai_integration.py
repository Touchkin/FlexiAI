"""
Integration tests for FlexiAI with real OpenAI API.

These tests make actual API calls and require OPENAI_API_KEY to be set.
Run with: pytest -m integration -v

Note: These tests will consume API tokens and incur costs.
"""

import pytest

from flexiai import ProviderConfig

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestBasicCompletion:
    """Test basic chat completion with real API."""

    def test_simple_completion(self, integration_client, track_tokens, rate_limiter):
        """Test simple chat completion returns valid response."""
        # Use minimal prompt to save tokens
        response = integration_client.chat_completion(
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=10,
        )

        # Verify response structure
        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
        assert response.model == "gpt-4.1-nano-2025-04-14"
        assert response.provider == "openai"
        assert response.finish_reason in ["stop", "length"]

        # Verify usage tracking
        assert response.usage is not None
        assert response.usage.total_tokens > 0
        assert response.usage.prompt_tokens > 0
        assert response.usage.completion_tokens > 0

        # Track tokens
        track_tokens(response.usage.total_tokens)

        # Rate limit
        rate_limiter()

    def test_completion_with_custom_parameters(
        self, integration_client, track_tokens, rate_limiter
    ):
        """Test completion with custom temperature and max_tokens."""
        response = integration_client.chat_completion(
            messages=[{"role": "user", "content": "Count to 3"}],
            temperature=0.3,  # Low temperature for deterministic output
            max_tokens=20,
        )

        assert response is not None
        assert response.content is not None
        # Should contain numbers given the prompt
        assert any(char.isdigit() for char in response.content)

        # Track tokens
        track_tokens(response.usage.total_tokens)

        # Rate limit
        rate_limiter()

    def test_completion_tracks_metadata(self, integration_client, track_tokens, rate_limiter):
        """Test that request metadata is tracked correctly."""
        # Make a request
        response = integration_client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
        )

        # Check metadata
        stats = integration_client.get_request_stats()
        assert stats["total_requests"] >= 1
        assert stats["successful_requests"] >= 1
        assert stats["failed_requests"] == 0

        # Check last used provider
        assert integration_client.get_last_used_provider() == "openai"

        # Track tokens
        track_tokens(response.usage.total_tokens)

        # Rate limit
        rate_limiter()


class TestMultiTurnConversation:
    """Test multi-turn conversations."""

    def test_simple_conversation(self, integration_client, track_tokens, rate_limiter):
        """Test a simple 2-turn conversation."""
        # First turn
        response1 = integration_client.chat_completion(
            messages=[{"role": "user", "content": "What is 2+2?"}],
            max_tokens=20,
        )

        assert response1 is not None
        assert "4" in response1.content

        # Second turn - build on conversation
        response2 = integration_client.chat_completion(
            messages=[
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": response1.content},
                {"role": "user", "content": "What about 3+3?"},
            ],
            max_tokens=20,
        )

        assert response2 is not None
        assert "6" in response2.content

        # Track tokens for both requests
        track_tokens(response1.usage.total_tokens)
        track_tokens(response2.usage.total_tokens)

        # Rate limit
        rate_limiter()


class TestErrorHandling:
    """Test error handling with real API."""

    def test_invalid_api_key(self, rate_limiter):
        """Test that invalid API key raises error during API call."""
        from flexiai.exceptions import ValidationError
        from flexiai.providers.registry import ProviderRegistry

        # Clear registry
        with ProviderRegistry._lock:
            if ProviderRegistry._instance is not None:
                ProviderRegistry._instance.clear()

        # Invalid API key will fail validation during client initialization
        # because we validate the key format
        with pytest.raises(ValidationError) as exc_info:
            ProviderConfig(
                name="openai",
                priority=1,
                api_key="sk-invalid-key-12345",  # Invalid format
                model="gpt-4.1-nano-2025-04-14",
            )

        assert "Invalid API key format" in str(exc_info.value)

        # Cleanup
        with ProviderRegistry._lock:
            if ProviderRegistry._instance is not None:
                ProviderRegistry._instance.clear()

        # Rate limit
        rate_limiter()

    def test_empty_message_list(self, integration_client, rate_limiter):
        """Test that empty message list raises appropriate error."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            integration_client.chat_completion(
                messages=[],  # Empty list
                max_tokens=10,
            )

        # Rate limit
        rate_limiter()


class TestCircuitBreakerIntegration:
    """Test circuit breaker behavior with real API scenarios."""

    def test_circuit_breaker_tracks_successes(self, integration_client, track_tokens, rate_limiter):
        """Test that successful requests keep circuit closed."""
        # Make several successful requests
        for i in range(3):
            response = integration_client.chat_completion(
                messages=[{"role": "user", "content": f"Say {i}"}],
                max_tokens=10,
            )
            track_tokens(response.usage.total_tokens)

        # Check provider status - circuit should be closed
        status = integration_client.get_provider_status("openai")
        assert status["circuit_breaker"]["state"] == "closed"
        assert status["circuit_breaker"]["failure_count"] == 0

        # Rate limit
        rate_limiter()

    def test_provider_status_after_success(self, integration_client, track_tokens, rate_limiter):
        """Test provider status reporting after successful request."""
        # Make a successful request
        response = integration_client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
        )
        track_tokens(response.usage.total_tokens)

        # Get provider status
        status = integration_client.get_provider_status("openai")

        assert status["name"] == "openai"
        assert status["model"] == "gpt-4.1-nano-2025-04-14"
        assert status["priority"] == 1
        assert status["status"] == "registered"
        assert status["circuit_breaker"]["state"] == "closed"

        # Rate limit
        rate_limiter()


class TestProviderManagement:
    """Test provider management features."""

    def test_get_all_provider_status(self, integration_client, track_tokens, rate_limiter):
        """Test retrieving status of all providers."""
        # Make a request first
        response = integration_client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
        )
        track_tokens(response.usage.total_tokens)

        # Get all provider status
        all_status = integration_client.get_provider_status()

        assert "providers" in all_status
        assert len(all_status["providers"]) >= 1

        # Check OpenAI provider is in the list
        openai_found = any(p["name"] == "openai" for p in all_status["providers"])
        assert openai_found

        # Rate limit
        rate_limiter()

    def test_request_statistics(self, integration_client, track_tokens, rate_limiter):
        """Test that request statistics are accurately tracked."""
        # Get initial stats
        initial_stats = integration_client.get_request_stats()
        initial_total = initial_stats["total_requests"]

        # Make a request
        response = integration_client.chat_completion(
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=10,
        )
        track_tokens(response.usage.total_tokens)

        # Get updated stats
        updated_stats = integration_client.get_request_stats()

        assert updated_stats["total_requests"] == initial_total + 1
        assert updated_stats["successful_requests"] >= initial_stats["successful_requests"]
        assert "providers_used" in updated_stats  # Changed from provider_stats
        assert "openai" in updated_stats["providers_used"]

        # Rate limit
        rate_limiter()
