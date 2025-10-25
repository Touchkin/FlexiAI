"""Additional edge case tests for FlexiAI - Phase 1.11."""

import pytest

from flexiai.circuit_breaker import CircuitBreaker, CircuitState
from flexiai.exceptions import ProviderException
from flexiai.models import CircuitBreakerConfig


class TestCircuitBreakerEdgeCases:
    """Additional edge case tests for circuit breaker."""

    def test_half_open_failure_reopens_circuit(self):
        """Test that failure in HALF_OPEN state reopens the circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,
            expected_exception=["ProviderException"],
        )
        breaker = CircuitBreaker(name="test", config=config)

        # Trigger failures to open circuit
        for _ in range(2):
            with pytest.raises(ProviderException):
                breaker.call(lambda: exec('raise ProviderException("error", provider="test")'))

        assert breaker.is_open()

        # Wait for recovery timeout to enter HALF_OPEN
        import time

        time.sleep(1.1)

        # Verify we're in HALF_OPEN by checking the next call attempts
        # A failure in HALF_OPEN should reopen the circuit
        with pytest.raises(ProviderException):
            breaker.call(lambda: exec('raise ProviderException("error", provider="test")'))

        # Circuit should be OPEN again (not just staying HALF_OPEN)
        assert breaker.is_open()
        assert breaker.state.state == CircuitState.OPEN

    def test_should_count_failure_with_no_expected_exceptions(self):
        """Test that all failures are counted when no expected exceptions configured."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=2,
            expected_exception=[],  # Empty list - should count all exceptions
        )
        breaker = CircuitBreaker(name="test", config=config)

        # Any exception should be counted when expected_exception is empty
        # These should all be counted
        for _ in range(3):
            with pytest.raises(ValueError):
                breaker.call(lambda: (_ for _ in ()).throw(ValueError("error")))

        # Circuit should open since all failures were counted
        assert breaker.is_open()

    def test_unexpected_exception_not_counted(self):
        """Test that unexpected exceptions are not counted as failures."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=2,
            expected_exception=["ProviderException"],  # Only count ProviderException
        )
        breaker = CircuitBreaker(name="test", config=config)

        # Unexpected exceptions should raise but not count
        with pytest.raises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("error")))

        # Failure count should still be 0
        assert breaker.state.failure_count == 0
        assert breaker.is_closed()

        # Now cause expected failures
        for _ in range(2):
            with pytest.raises(ProviderException):
                breaker.call(lambda: exec('raise ProviderException("error", provider="test")'))

        # Now it should open
        assert breaker.is_open()

    def test_success_in_half_open_resets_failure_count(self):
        """Test that success in HALF_OPEN state closes circuit and resets failures."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,
            expected_exception=["ProviderException"],
            success_threshold=1,  # Only need 1 success to close
        )
        breaker = CircuitBreaker(name="test", config=config)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ProviderException):
                breaker.call(lambda: exec('raise ProviderException("error", provider="test")'))

        assert breaker.is_open()
        assert breaker.state.failure_count == 2

        # Wait for recovery
        import time

        time.sleep(1.1)

        # Success should close the circuit
        result = breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.is_closed()
        # Failure count is reset on close
        assert breaker.state.failure_count == 0

    def test_state_transition_no_change(self):
        """Test that transitioning to the same state doesn't do anything."""
        config = CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=2, expected_exception=["ProviderException"]
        )
        breaker = CircuitBreaker(name="test", config=config)

        # Circuit starts in CLOSED state
        assert breaker.is_closed()

        # Manually try to transition to CLOSED again (should be no-op)
        old_state = breaker.state.state
        breaker._transition_to(CircuitState.CLOSED)

        # State should still be CLOSED, no error
        assert breaker.is_closed()
        assert breaker.state.state == old_state


class TestConfigEdgeCases:
    """Additional edge case tests for configuration."""

    def test_config_from_yaml_with_invalid_yaml(self):
        """Test config loading from invalid YAML."""
        from flexiai.config import ConfigLoader

        # Invalid YAML syntax
        invalid_yaml = """
        providers:
          - name: openai
            priority: 1
          - invalid_indentation_here
        """

        with pytest.raises(Exception):  # Should raise yaml.YAMLError or similar
            ConfigLoader.from_yaml_string(invalid_yaml)

    def test_config_from_json_with_invalid_json(self):
        """Test config loading from invalid JSON."""
        from flexiai.config import ConfigLoader

        # Invalid JSON syntax (missing quotes around key)
        invalid_json = '{invalid_key: "value"}'

        with pytest.raises(Exception):  # Should raise json.JSONDecodeError
            ConfigLoader.from_json_string(invalid_json)


class TestClientEdgeCases:
    """Additional edge case tests for FlexiAI client."""

    def test_create_provider_validates_provider_name(self):
        """Test that ProviderConfig validates unsupported provider names."""
        from pydantic import ValidationError

        from flexiai.models import ProviderConfig

        # Should raise validation error for unsupported provider
        with pytest.raises(ValidationError) as exc_info:
            ProviderConfig(
                name="unsupported_provider",
                priority=1,
                api_key="test-key",
                model="test-model",
            )

        assert "not supported" in str(exc_info.value).lower()

    def test_config_validates_minimum_providers(self):
        """Test that FlexiAIConfig requires at least one provider."""
        from pydantic import ValidationError

        from flexiai import FlexiAIConfig

        # Should raise validation error for empty providers list
        with pytest.raises(ValidationError) as exc_info:
            FlexiAIConfig(providers=[])

        assert "at least 1 item" in str(exc_info.value).lower()


class TestModelsEdgeCases:
    """Additional edge case tests for models."""

    def test_unified_request_with_tools(self):
        """Test UnifiedRequest with tools parameter."""
        from flexiai.models import Message, UnifiedRequest

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        request = UnifiedRequest(
            messages=[Message(role="user", content="What's the weather?")],
            tools=tools,
            temperature=0.7,
        )

        assert request.tools == tools
        assert len(request.messages) == 1

    def test_provider_config_with_invalid_priority(self):
        """Test ProviderConfig with invalid priority value."""
        from pydantic import ValidationError

        from flexiai.models import ProviderConfig

        # Priority must be >= 1
        with pytest.raises(ValidationError):
            ProviderConfig(name="openai", priority=0, api_key="test-key", model="gpt-4")  # Invalid

        with pytest.raises(ValidationError):
            ProviderConfig(name="openai", priority=-1, api_key="test-key", model="gpt-4")  # Invalid

    def test_unified_response_with_minimal_fields(self):
        """Test UnifiedResponse with only required fields."""
        from flexiai.models import UnifiedResponse, UsageInfo

        # Create with minimal required fields
        response = UnifiedResponse(
            content="Hello",
            model="gpt-4",
            provider="openai",  # Required field
            finish_reason="stop",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

        assert response.content == "Hello"
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        # Optional fields should be None or default
        assert response.tool_calls is None
        assert response.metadata == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
