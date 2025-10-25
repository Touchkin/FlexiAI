"""
Unit tests for FlexiAI data models.

Tests all Pydantic models for validation, serialization, and business logic.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from flexiai.models import (
    CircuitBreakerConfig,
    FlexiAIConfig,
    LoggingConfig,
    Message,
    MessageRole,
    ProviderConfig,
    RetryConfig,
    UnifiedRequest,
    UnifiedResponse,
    UsageInfo,
)


class TestMessage:
    """Tests for Message model."""

    def test_message_creation_valid(self):
        """Test creating a valid message."""
        msg = Message(role="user", content="Hello, AI!")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, AI!"
        assert msg.name is None

    def test_message_system_role(self):
        """Test creating a system message."""
        msg = Message(role="system", content="You are a helpful assistant.")
        assert msg.role == MessageRole.SYSTEM
        assert msg.content == "You are a helpful assistant."

    def test_message_assistant_role(self):
        """Test creating an assistant message."""
        msg = Message(role="assistant", content="I can help with that!")
        assert msg.role == MessageRole.ASSISTANT

    def test_message_with_tool_calls(self):
        """Test message with tool calls."""
        msg = Message(
            role="assistant",
            content=None,
            tool_calls=[{"id": "call_1", "function": {"name": "get_weather"}}],
        )
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1

    def test_message_empty_content_user_role_fails(self):
        """Test that user message with empty content fails validation."""
        with pytest.raises(PydanticValidationError):
            Message(role="user", content="")

    def test_message_no_content_user_role_fails(self):
        """Test that user message without content fails validation."""
        with pytest.raises(PydanticValidationError):
            Message(role="user", content=None)

    def test_message_whitespace_stripped(self):
        """Test that whitespace is stripped from content."""
        msg = Message(role="user", content="  Hello  ")
        assert msg.content == "Hello"


class TestUsageInfo:
    """Tests for UsageInfo model."""

    def test_usage_info_valid(self):
        """Test creating valid usage info."""
        usage = UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 20
        assert usage.total_tokens == 30

    def test_usage_info_auto_calculates_total(self):
        """Test that total tokens is auto-calculated if incorrect."""
        usage = UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=0)
        assert usage.total_tokens == 30

    def test_usage_info_negative_tokens_fails(self):
        """Test that negative token counts fail validation."""
        with pytest.raises(PydanticValidationError):
            UsageInfo(prompt_tokens=-1, completion_tokens=20, total_tokens=19)


class TestUnifiedRequest:
    """Tests for UnifiedRequest model."""

    def test_unified_request_minimal(self):
        """Test creating request with minimal required fields."""
        request = UnifiedRequest(messages=[Message(role="user", content="Hello")])
        assert len(request.messages) == 1
        assert request.temperature == 0.7
        assert request.stream is False

    def test_unified_request_full(self):
        """Test creating request with all fields."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            temperature=0.5,
            max_tokens=100,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            stop=["END"],
            stream=True,
        )
        assert request.temperature == 0.5
        assert request.max_tokens == 100
        assert request.stream is True

    def test_unified_request_empty_messages_fails(self):
        """Test that empty messages list fails validation."""
        with pytest.raises(PydanticValidationError):
            UnifiedRequest(messages=[])

    def test_unified_request_temperature_out_of_range_fails(self):
        """Test that temperature out of range fails validation."""
        with pytest.raises(PydanticValidationError):
            UnifiedRequest(messages=[Message(role="user", content="Hello")], temperature=3.0)

    def test_unified_request_with_tools(self):
        """Test request with tools/functions."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="What's the weather?")],
            tools=[{"type": "function", "function": {"name": "get_weather"}}],
        )
        assert request.tools is not None
        assert len(request.tools) == 1


class TestUnifiedResponse:
    """Tests for UnifiedResponse model."""

    def test_unified_response_valid(self):
        """Test creating a valid response."""
        response = UnifiedResponse(
            content="Hello! How can I help?",
            model="gpt-4",
            provider="openai",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            finish_reason="stop",
        )
        assert response.content == "Hello! How can I help?"
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        assert response.finish_reason == "stop"

    def test_unified_response_with_metadata(self):
        """Test response with metadata."""
        response = UnifiedResponse(
            content="Response",
            model="gpt-4",
            provider="openai",
            usage=UsageInfo(prompt_tokens=5, completion_tokens=10, total_tokens=15),
            finish_reason="stop",
            metadata={"request_id": "req_123", "latency_ms": 250},
        )
        assert response.metadata["request_id"] == "req_123"
        assert response.metadata["latency_ms"] == 250


class TestProviderConfig:
    """Tests for ProviderConfig model."""

    def test_provider_config_valid(self):
        """Test creating a valid provider configuration."""
        config = ProviderConfig(
            name="openai",
            priority=1,
            api_key="sk-test123",
            model="gpt-4-turbo-preview",
        )
        assert config.name == "openai"
        assert config.priority == 1
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_provider_config_with_custom_values(self):
        """Test provider config with custom timeout and retries."""
        config = ProviderConfig(
            name="openai",
            priority=1,
            api_key="sk-test123",
            model="gpt-4",
            timeout=60,
            max_retries=5,
        )
        assert config.timeout == 60
        assert config.max_retries == 5

    def test_provider_config_invalid_name_fails(self):
        """Test that invalid provider name fails validation."""
        with pytest.raises(PydanticValidationError):
            ProviderConfig(
                name="invalid_provider",
                priority=1,
                api_key="sk-test123",
                model="gpt-4",
            )

    def test_provider_config_empty_api_key_fails(self):
        """Test that empty API key fails validation."""
        with pytest.raises(PydanticValidationError):
            ProviderConfig(name="openai", priority=1, api_key="", model="gpt-4")

    def test_provider_config_name_case_insensitive(self):
        """Test that provider name is case-insensitive."""
        config = ProviderConfig(name="OpenAI", priority=1, api_key="sk-test123", model="gpt-4")
        assert config.name == "openai"

    def test_provider_config_with_base_url(self):
        """Test provider config with custom base URL."""
        config = ProviderConfig(
            name="openai",
            priority=1,
            api_key="sk-test123",
            model="gpt-4",
            base_url="https://custom.api.com",
        )
        assert config.base_url == "https://custom.api.com"


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig model."""

    def test_circuit_breaker_config_defaults(self):
        """Test circuit breaker config with default values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60
        assert "APIError" in config.expected_exception

    def test_circuit_breaker_config_custom(self):
        """Test circuit breaker config with custom values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=120,
            expected_exception=["CustomError"],
        )
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 120
        assert config.expected_exception == ["CustomError"]


class TestRetryConfig:
    """Tests for RetryConfig model."""

    def test_retry_config_defaults(self):
        """Test retry config with default values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.backoff_factor == 2.0
        assert "RateLimitError" in config.retryable_errors

    def test_retry_config_custom(self):
        """Test retry config with custom values."""
        config = RetryConfig(max_attempts=5, backoff_factor=1.5, max_backoff=120)
        assert config.max_attempts == 5
        assert config.backoff_factor == 1.5
        assert config.max_backoff == 120


class TestLoggingConfig:
    """Tests for LoggingConfig model."""

    def test_logging_config_defaults(self):
        """Test logging config with default values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.file is None
        assert config.backup_count == 5

    def test_logging_config_with_file(self):
        """Test logging config with file path."""
        config = LoggingConfig(level="DEBUG", file="flexiai.log")
        assert config.level == "DEBUG"
        assert config.file == "flexiai.log"

    def test_logging_config_invalid_level_fails(self):
        """Test that invalid log level fails validation."""
        with pytest.raises(PydanticValidationError):
            LoggingConfig(level="INVALID")

    def test_logging_config_level_case_insensitive(self):
        """Test that log level is normalized to uppercase."""
        config = LoggingConfig(level="debug")
        assert config.level == "DEBUG"


class TestFlexiAIConfig:
    """Tests for FlexiAIConfig model."""

    def test_flexiai_config_minimal(self):
        """Test FlexiAI config with minimal configuration."""
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(name="openai", priority=1, api_key="sk-test123", model="gpt-4")
            ]
        )
        assert len(config.providers) == 1
        assert config.default_temperature == 0.7

    def test_flexiai_config_multiple_providers(self):
        """Test FlexiAI config with multiple providers."""
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(name="openai", priority=1, api_key="sk-test123", model="gpt-4"),
                ProviderConfig(name="gemini", priority=2, api_key="test-key", model="gemini-pro"),
            ]
        )
        assert len(config.providers) == 2

    def test_flexiai_config_providers_sorted_by_priority(self):
        """Test that providers are automatically sorted by priority."""
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(name="gemini", priority=2, api_key="test-key", model="gemini-pro"),
                ProviderConfig(name="openai", priority=1, api_key="sk-test123", model="gpt-4"),
            ]
        )
        assert config.providers[0].name == "openai"
        assert config.providers[1].name == "gemini"

    def test_flexiai_config_empty_providers_fails(self):
        """Test that empty providers list fails validation."""
        with pytest.raises(PydanticValidationError):
            FlexiAIConfig(providers=[])

    def test_flexiai_config_duplicate_priorities_fails(self):
        """Test that duplicate priorities fail validation."""
        with pytest.raises(PydanticValidationError):
            FlexiAIConfig(
                providers=[
                    ProviderConfig(name="openai", priority=1, api_key="sk-test123", model="gpt-4"),
                    ProviderConfig(
                        name="gemini", priority=1, api_key="test-key", model="gemini-pro"
                    ),
                ]
            )

    def test_flexiai_config_duplicate_names_fails(self):
        """Test that duplicate provider names fail validation."""
        with pytest.raises(PydanticValidationError):
            FlexiAIConfig(
                providers=[
                    ProviderConfig(name="openai", priority=1, api_key="sk-test123", model="gpt-4"),
                    ProviderConfig(
                        name="openai",
                        priority=2,
                        api_key="sk-test456",
                        model="gpt-3.5-turbo",
                    ),
                ]
            )

    def test_flexiai_config_get_provider_by_name(self):
        """Test getting provider by name."""
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(name="openai", priority=1, api_key="sk-test123", model="gpt-4")
            ]
        )
        provider = config.get_provider_by_name("openai")
        assert provider is not None
        assert provider.name == "openai"

    def test_flexiai_config_get_provider_by_name_not_found(self):
        """Test getting non-existent provider returns None."""
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(name="openai", priority=1, api_key="sk-test123", model="gpt-4")
            ]
        )
        provider = config.get_provider_by_name("gemini")
        assert provider is None

    def test_flexiai_config_to_dict(self):
        """Test converting config to dictionary."""
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(name="openai", priority=1, api_key="sk-test123", model="gpt-4")
            ]
        )
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert "providers" in config_dict
        assert len(config_dict["providers"]) == 1

    def test_flexiai_config_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "providers": [
                {
                    "name": "openai",
                    "priority": 1,
                    "api_key": "sk-test123",
                    "model": "gpt-4",
                }
            ]
        }
        config = FlexiAIConfig.from_dict(config_dict)
        assert len(config.providers) == 1
        assert config.providers[0].name == "openai"

    def test_flexiai_config_with_all_sections(self):
        """Test config with all configuration sections."""
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(name="openai", priority=1, api_key="sk-test123", model="gpt-4")
            ],
            circuit_breaker=CircuitBreakerConfig(failure_threshold=10),
            retry=RetryConfig(max_attempts=5),
            logging=LoggingConfig(level="DEBUG"),
            default_temperature=0.5,
            default_max_tokens=2000,
        )
        assert config.circuit_breaker.failure_threshold == 10
        assert config.retry.max_attempts == 5
        assert config.logging.level == "DEBUG"
        assert config.default_temperature == 0.5
        assert config.default_max_tokens == 2000
