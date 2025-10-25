"""
Unit tests for the BaseProvider abstract class.

Tests the base provider functionality including retry logic,
error handling, health checks, and abstract method enforcement.
"""

from typing import Optional

import pytest

from flexiai.exceptions import (
    AuthenticationError,
    ProviderException,
    RateLimitError,
    ValidationError,
)
from flexiai.models import Message, ProviderConfig, UnifiedRequest, UnifiedResponse, UsageInfo
from flexiai.providers.base import BaseProvider


class MockProvider(BaseProvider):
    """Mock provider implementation for testing."""

    def __init__(
        self,
        config: ProviderConfig,
        should_fail: bool = False,
        fail_count: int = 0,
        fail_with: Optional[Exception] = None,
    ) -> None:
        """
        Initialize mock provider.

        Args:
            config: Provider configuration
            should_fail: Whether chat_completion should fail
            fail_count: Number of times to fail before succeeding
            fail_with: Exception to raise on failure
        """
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.fail_with = fail_with or ProviderException("Mock provider error")
        self.call_count = 0
        self.health_check_called = False
        self.authenticate_called = False
        super().__init__(config)

    def chat_completion(self, request: UnifiedRequest) -> UnifiedResponse:
        """Mock chat completion implementation."""
        self.call_count += 1

        # Fail for the first fail_count calls
        if self.call_count <= self.fail_count:
            raise self.fail_with

        if self.should_fail:
            raise self.fail_with

        # Return a mock response
        return UnifiedResponse(
            content="Mock response",
            model=self.config.model,
            provider=self.name,
            usage=UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            finish_reason="stop",
        )

    def authenticate(self) -> bool:
        """Mock authentication."""
        self.authenticate_called = True
        if not self.config.api_key:
            raise AuthenticationError("API key missing")
        self._authenticated = True
        return True

    def validate_credentials(self) -> bool:
        """Mock credential validation."""
        if not self.config.api_key:
            raise ValidationError("API key required")
        return True

    def health_check(self) -> bool:
        """Mock health check."""
        self.health_check_called = True
        if self.should_fail:
            raise ProviderException("Health check failed")
        return True

    def get_supported_models(self):
        """Return mock supported models."""
        return ["model-1", "model-2", "model-3"]


class TestBaseProviderInitialization:
    """Test BaseProvider initialization."""

    def test_initialization_success(self) -> None:
        """Test successful provider initialization."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config)

        assert provider.name == "openai"
        assert provider.config == config
        assert provider._authenticated is False
        assert provider._last_health_check is None

    def test_initialization_validates_credentials(self) -> None:
        """Test that initialization validates credentials."""
        # Use model_construct to bypass Pydantic validation
        config = ProviderConfig.model_construct(
            name="openai", api_key="", priority=1, model="model-1"
        )

        with pytest.raises(ValidationError, match="API key required"):
            MockProvider(config)

    def test_logger_created(self) -> None:
        """Test that logger is created for provider."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config)

        assert provider.logger is not None
        assert "openai" in provider.logger.name


class TestAbstractMethods:
    """Test that abstract methods must be implemented."""

    def test_cannot_instantiate_base_provider(self) -> None:
        """Test that BaseProvider cannot be instantiated directly."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")

        with pytest.raises(TypeError):
            BaseProvider(config)  # type: ignore


class TestChatCompletion:
    """Test chat completion functionality."""

    def test_chat_completion_success(self) -> None:
        """Test successful chat completion."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config)

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        response = provider.chat_completion(request)

        assert response.content == "Mock response"
        assert response.model == "model-1"
        assert response.provider == "openai"
        assert response.usage.total_tokens == 30

    def test_chat_completion_failure(self) -> None:
        """Test chat completion failure."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config, should_fail=True)

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        with pytest.raises(ProviderException, match="Mock provider error"):
            provider.chat_completion(request)


class TestChatCompletionWithRetry:
    """Test chat completion with retry logic."""

    def test_retry_success_on_first_attempt(self) -> None:
        """Test successful completion on first attempt."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config)

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        response = provider.chat_completion_with_retry(request)

        assert response.content == "Mock response"
        assert provider.call_count == 1

    def test_retry_success_after_failures(self) -> None:
        """Test successful completion after initial failures."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        # Fail first 2 attempts, succeed on 3rd
        provider = MockProvider(config, fail_count=2)

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        response = provider.chat_completion_with_retry(
            request, max_attempts=3, min_wait=0.1, max_wait=0.2
        )

        assert response.content == "Mock response"
        assert provider.call_count == 3

    def test_retry_exhausted(self) -> None:
        """Test that retry stops after max attempts."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config, should_fail=True)

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        with pytest.raises(ProviderException):
            provider.chat_completion_with_retry(request, max_attempts=2, min_wait=0.1, max_wait=0.2)

        assert provider.call_count == 2

    def test_retry_with_rate_limit_error(self) -> None:
        """Test retry with rate limit error."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(
            config, fail_count=1, fail_with=RateLimitError("Rate limit exceeded")
        )

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        response = provider.chat_completion_with_retry(
            request, max_attempts=3, min_wait=0.1, max_wait=0.2
        )

        assert response.content == "Mock response"
        assert provider.call_count == 2

    def test_retry_with_authentication_error(self) -> None:
        """Test that authentication errors are not retried."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(
            config,
            should_fail=True,
            fail_with=AuthenticationError("Authentication failed"),
        )

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        with pytest.raises(AuthenticationError):
            provider.chat_completion_with_retry(request, max_attempts=3, min_wait=0.1, max_wait=0.2)

        # Should fail immediately without retry
        assert provider.call_count == 1


class TestHealthCheck:
    """Test health check functionality."""

    def test_health_check_success(self) -> None:
        """Test successful health check."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config)

        result = provider.health_check()

        assert result is True
        assert provider.health_check_called is True

    def test_health_check_failure(self) -> None:
        """Test failed health check."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config, should_fail=True)

        with pytest.raises(ProviderException, match="Health check failed"):
            provider.health_check()

    def test_is_healthy_caching(self) -> None:
        """Test that is_healthy caches results."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config)

        # First call should execute health check
        result1 = provider.is_healthy(cache_duration=60)
        assert result1 is True
        assert provider._last_health_check is not None

        # Reset the flag
        provider.health_check_called = False

        # Second call within cache duration should use cached result
        result2 = provider.is_healthy(cache_duration=60)
        assert result2 is True
        assert provider.health_check_called is False

    def test_is_healthy_cache_expiry(self) -> None:
        """Test that is_healthy cache expires."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config)

        # First call
        result1 = provider.is_healthy(cache_duration=0)
        assert result1 is True

        # Reset the flag
        provider.health_check_called = False

        # Second call with expired cache should execute health check
        result2 = provider.is_healthy(cache_duration=0)
        assert result2 is True
        assert provider.health_check_called is True

    def test_is_healthy_handles_exceptions(self) -> None:
        """Test that is_healthy handles exceptions gracefully."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config, should_fail=True)

        result = provider.is_healthy()

        assert result is False


class TestAuthentication:
    """Test authentication functionality."""

    def test_authenticate_success(self) -> None:
        """Test successful authentication."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config)

        result = provider.authenticate()

        assert result is True
        assert provider._authenticated is True
        assert provider.authenticate_called is True

    def test_authenticate_failure(self) -> None:
        """Test failed authentication."""
        # Use model_construct to bypass Pydantic validation
        config = ProviderConfig.model_construct(
            name="openai", api_key="", priority=1, model="model-1"
        )

        # Should fail during initialization
        with pytest.raises(ValidationError):
            MockProvider(config)


class TestProviderInfo:
    """Test provider information methods."""

    def test_get_supported_models(self) -> None:
        """Test getting supported models."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=1, model="model-1")
        provider = MockProvider(config)

        models = provider.get_supported_models()

        assert models == ["model-1", "model-2", "model-3"]

    def test_get_provider_info(self) -> None:
        """Test getting provider information."""
        config = ProviderConfig(
            name="openai",
            api_key="test-key",
            priority=5,
            timeout=30,
            max_retries=3,
            model="gpt-4",
        )
        provider = MockProvider(config)

        info = provider.get_provider_info()

        assert info["name"] == "openai"
        assert info["priority"] == 5
        assert info["timeout"] == 30
        assert info["max_retries"] == 3
        assert info["authenticated"] is False
        assert info["supported_models"] == ["model-1", "model-2", "model-3"]

    def test_repr(self) -> None:
        """Test string representation."""
        config = ProviderConfig(name="openai", api_key="test-key", priority=5, model="model-1")
        provider = MockProvider(config)

        repr_str = repr(provider)

        assert "MockProvider" in repr_str
        assert "name='openai'" in repr_str
        assert "priority=5" in repr_str
        assert "authenticated=False" in repr_str
