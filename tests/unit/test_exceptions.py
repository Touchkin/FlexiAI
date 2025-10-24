"""
Unit tests for FlexiAI exceptions.

Tests all custom exceptions for proper initialization and behavior.
"""

from flexiai.exceptions import (
    AllProvidersFailedError,
    APIConnectionError,
    AuthenticationError,
    CircuitBreakerOpenError,
    ConfigurationError,
    ContentFilterError,
    FlexiAIException,
    InvalidResponseError,
    ModelNotFoundError,
    ProviderException,
    RateLimitError,
    TimeoutError,
    ValidationError,
)


class TestFlexiAIException:
    """Tests for FlexiAIException base class."""

    def test_exception_with_message_only(self):
        """Test creating exception with message only."""
        exc = FlexiAIException("Something went wrong")
        assert exc.message == "Something went wrong"
        assert exc.details == {}
        assert str(exc) == "Something went wrong"

    def test_exception_with_details(self):
        """Test creating exception with details."""
        exc = FlexiAIException("Error occurred", details={"code": 500, "type": "server_error"})
        assert exc.message == "Error occurred"
        assert exc.details["code"] == 500
        assert "Details:" in str(exc)

    def test_exception_repr(self):
        """Test exception representation."""
        exc = FlexiAIException("Test error", details={"key": "value"})
        repr_str = repr(exc)
        assert "FlexiAIException" in repr_str
        assert "Test error" in repr_str


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_configuration_error(self):
        """Test creating configuration error."""
        exc = ConfigurationError("Missing API key")
        assert "Configuration Error:" in exc.message
        assert "Missing API key" in str(exc)

    def test_configuration_error_with_details(self):
        """Test configuration error with details."""
        exc = ConfigurationError(
            "Invalid provider", details={"provider": "invalid", "field": "name"}
        )
        assert exc.details["provider"] == "invalid"


class TestValidationError:
    """Tests for ValidationError."""

    def test_validation_error(self):
        """Test creating validation error."""
        exc = ValidationError("Temperature must be between 0.0 and 2.0")
        assert "Validation Error:" in exc.message

    def test_validation_error_with_details(self):
        """Test validation error with parameter details."""
        exc = ValidationError(
            "Invalid temperature",
            details={"parameter": "temperature", "value": 3.0, "range": "0.0-2.0"},
        )
        assert exc.details["parameter"] == "temperature"
        assert exc.details["value"] == 3.0


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_authentication_error(self):
        """Test creating authentication error."""
        exc = AuthenticationError("Invalid API key")
        assert "Authentication Error:" in exc.message

    def test_authentication_error_with_provider(self):
        """Test authentication error with provider name."""
        exc = AuthenticationError("Invalid API key", provider="openai")
        assert exc.details["provider"] == "openai"

    def test_authentication_error_with_all_params(self):
        """Test authentication error with provider and details."""
        exc = AuthenticationError(
            "API key expired", provider="openai", details={"expires_at": "2024-01-01"}
        )
        assert exc.details["provider"] == "openai"
        assert exc.details["expires_at"] == "2024-01-01"


class TestProviderException:
    """Tests for ProviderException."""

    def test_provider_exception(self):
        """Test creating provider exception."""
        exc = ProviderException("API error")
        assert "Provider Error:" in exc.message
        assert exc.is_retryable is True

    def test_provider_exception_with_provider(self):
        """Test provider exception with provider name."""
        exc = ProviderException("Connection failed", provider="openai")
        assert exc.provider == "openai"
        assert exc.details["provider"] == "openai"

    def test_provider_exception_not_retryable(self):
        """Test provider exception marked as not retryable."""
        exc = ProviderException("Invalid request", is_retryable=False)
        assert exc.is_retryable is False
        assert exc.details["retryable"] is False


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_rate_limit_error(self):
        """Test creating rate limit error."""
        exc = RateLimitError("Rate limit exceeded")
        assert "Rate limit exceeded" in exc.message
        assert exc.is_retryable is True

    def test_rate_limit_error_with_retry_after(self):
        """Test rate limit error with retry_after."""
        exc = RateLimitError("Rate limit exceeded", retry_after=60)
        assert exc.retry_after == 60
        assert exc.details["retry_after"] == 60

    def test_rate_limit_error_with_provider(self):
        """Test rate limit error with provider."""
        exc = RateLimitError("Rate limit exceeded", provider="openai", retry_after=30)
        assert exc.provider == "openai"
        assert exc.retry_after == 30


class TestTimeoutError:
    """Tests for TimeoutError."""

    def test_timeout_error(self):
        """Test creating timeout error."""
        exc = TimeoutError("Request timed out")
        assert "Request timed out" in exc.message
        assert exc.is_retryable is True

    def test_timeout_error_with_timeout_value(self):
        """Test timeout error with timeout value."""
        exc = TimeoutError("Request timed out", timeout=30)
        assert exc.timeout == 30
        assert exc.details["timeout"] == 30

    def test_timeout_error_with_provider(self):
        """Test timeout error with provider."""
        exc = TimeoutError("Request timed out", provider="openai", timeout=30)
        assert exc.provider == "openai"
        assert exc.timeout == 30


class TestAPIConnectionError:
    """Tests for APIConnectionError."""

    def test_api_connection_error(self):
        """Test creating API connection error."""
        exc = APIConnectionError("Failed to connect")
        assert "Failed to connect" in exc.message
        assert exc.is_retryable is True

    def test_api_connection_error_with_provider(self):
        """Test API connection error with provider."""
        exc = APIConnectionError("Connection refused", provider="openai")
        assert exc.provider == "openai"

    def test_api_connection_error_with_details(self):
        """Test API connection error with connection details."""
        exc = APIConnectionError(
            "Connection failed",
            provider="openai",
            details={"endpoint": "https://api.openai.com", "reason": "Connection refused"},
        )
        assert exc.details["endpoint"] == "https://api.openai.com"


class TestCircuitBreakerOpenError:
    """Tests for CircuitBreakerOpenError."""

    def test_circuit_breaker_open_error(self):
        """Test creating circuit breaker open error."""
        exc = CircuitBreakerOpenError("Circuit breaker is OPEN")
        assert "Circuit Breaker:" in exc.message

    def test_circuit_breaker_open_error_with_provider(self):
        """Test circuit breaker error with provider."""
        exc = CircuitBreakerOpenError("Circuit OPEN", provider="openai")
        assert exc.provider == "openai"
        assert exc.details["provider"] == "openai"

    def test_circuit_breaker_open_error_with_failure_count(self):
        """Test circuit breaker error with failure count."""
        exc = CircuitBreakerOpenError("Circuit OPEN", failure_count=5)
        assert exc.failure_count == 5
        assert exc.details["failure_count"] == 5

    def test_circuit_breaker_open_error_with_all_params(self):
        """Test circuit breaker error with all parameters."""
        exc = CircuitBreakerOpenError(
            "Circuit OPEN for provider",
            provider="openai",
            failure_count=5,
            details={"recovery_timeout": 60},
        )
        assert exc.provider == "openai"
        assert exc.failure_count == 5
        assert exc.details["recovery_timeout"] == 60


class TestAllProvidersFailedError:
    """Tests for AllProvidersFailedError."""

    def test_all_providers_failed_error(self):
        """Test creating all providers failed error."""
        exc = AllProvidersFailedError("All providers failed")
        assert "All Providers Failed:" in exc.message

    def test_all_providers_failed_error_with_provider_errors(self):
        """Test all providers failed error with provider errors."""
        provider_errors = {
            "openai": "Rate limit exceeded",
            "gemini": "Connection failed",
            "anthropic": "Circuit breaker open",
        }
        exc = AllProvidersFailedError("All providers failed", provider_errors=provider_errors)
        assert exc.provider_errors == provider_errors
        assert exc.details["provider_errors"] == provider_errors

    def test_all_providers_failed_error_str_includes_errors(self):
        """Test that string representation includes all provider errors."""
        provider_errors = {"openai": "Error 1", "gemini": "Error 2"}
        exc = AllProvidersFailedError("Failed", provider_errors=provider_errors)
        error_str = str(exc)
        assert "openai" in error_str
        assert "Error 1" in error_str
        assert "gemini" in error_str
        assert "Error 2" in error_str


class TestContentFilterError:
    """Tests for ContentFilterError."""

    def test_content_filter_error(self):
        """Test creating content filter error."""
        exc = ContentFilterError("Content filtered")
        assert "Content filtered" in exc.message
        assert exc.is_retryable is False

    def test_content_filter_error_with_provider(self):
        """Test content filter error with provider."""
        exc = ContentFilterError("Safety violation", provider="gemini")
        assert exc.provider == "gemini"

    def test_content_filter_error_with_details(self):
        """Test content filter error with filter details."""
        exc = ContentFilterError(
            "Content blocked",
            provider="gemini",
            details={"category": "harassment", "severity": "high"},
        )
        assert exc.details["category"] == "harassment"
        assert exc.details["severity"] == "high"


class TestModelNotFoundError:
    """Tests for ModelNotFoundError."""

    def test_model_not_found_error(self):
        """Test creating model not found error."""
        exc = ModelNotFoundError("Model not found")
        assert "Model not found" in exc.message
        assert exc.is_retryable is False

    def test_model_not_found_error_with_model_name(self):
        """Test model not found error with model name."""
        exc = ModelNotFoundError("Model not available", model="gpt-5")
        assert exc.model == "gpt-5"
        assert exc.details["model"] == "gpt-5"

    def test_model_not_found_error_with_provider(self):
        """Test model not found error with provider."""
        exc = ModelNotFoundError("Model not found", provider="openai", model="gpt-5")
        assert exc.provider == "openai"
        assert exc.model == "gpt-5"


class TestInvalidResponseError:
    """Tests for InvalidResponseError."""

    def test_invalid_response_error(self):
        """Test creating invalid response error."""
        exc = InvalidResponseError("Invalid JSON")
        assert "Invalid JSON" in exc.message
        assert exc.is_retryable is False

    def test_invalid_response_error_with_provider(self):
        """Test invalid response error with provider."""
        exc = InvalidResponseError("Malformed response", provider="openai")
        assert exc.provider == "openai"

    def test_invalid_response_error_with_details(self):
        """Test invalid response error with response details."""
        exc = InvalidResponseError(
            "Invalid response",
            provider="openai",
            details={"error": "Missing required field", "field": "content"},
        )
        assert exc.details["error"] == "Missing required field"


class TestExceptionInheritance:
    """Tests for exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from FlexiAIException."""
        exceptions = [
            ConfigurationError("test"),
            ValidationError("test"),
            AuthenticationError("test"),
            ProviderException("test"),
            RateLimitError("test"),
            TimeoutError("test"),
            APIConnectionError("test"),
            CircuitBreakerOpenError("test"),
            AllProvidersFailedError("test"),
            ContentFilterError("test"),
            ModelNotFoundError("test"),
            InvalidResponseError("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, FlexiAIException)
            assert isinstance(exc, Exception)

    def test_provider_specific_exceptions_inherit_from_provider_exception(self):
        """Test that provider-specific exceptions inherit from ProviderException."""
        exceptions = [
            RateLimitError("test"),
            TimeoutError("test"),
            APIConnectionError("test"),
            ContentFilterError("test"),
            ModelNotFoundError("test"),
            InvalidResponseError("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, ProviderException)

    def test_can_catch_all_with_base_exception(self):
        """Test that all exceptions can be caught with base exception."""
        try:
            raise RateLimitError("Rate limit")
        except FlexiAIException as e:
            assert "Rate limit" in str(e)

    def test_can_catch_provider_exceptions(self):
        """Test that provider exceptions can be caught specifically."""
        try:
            raise TimeoutError("Timeout")
        except ProviderException as e:
            assert "Timeout" in str(e)
