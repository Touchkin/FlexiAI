"""
Custom exceptions for FlexiAI.

This module defines a hierarchy of exceptions used throughout FlexiAI for
error handling and reporting. All exceptions inherit from FlexiAIException.
"""

from typing import Any, Dict, Optional


class FlexiAIException(Exception):
    """
    Base exception for all FlexiAI errors.

    All custom exceptions in FlexiAI inherit from this base class.
    This allows users to catch all FlexiAI-specific errors with a single except block.

    Attributes:
        message: Human-readable error message
        details: Optional dictionary with additional error context

    Example:
        >>> try:
        ...     raise FlexiAIException("Something went wrong", details={"code": 500})
        ... except FlexiAIException as e:
        ...     print(e.message)
        Something went wrong
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize FlexiAIException.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message

    def __repr__(self) -> str:
        """Return detailed representation of the exception."""
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


class ConfigurationError(FlexiAIException):
    """
    Raised when there is an error in the configuration.

    This exception is raised when:
    - Required configuration is missing
    - Configuration values are invalid
    - Configuration file cannot be loaded
    - Environment variables are malformed

    Example:
        >>> raise ConfigurationError(
        ...     "Missing API key for provider 'openai'",
        ...     details={"provider": "openai", "field": "api_key"}
        ... )
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize ConfigurationError.

        Args:
            message: Description of the configuration error
            details: Additional context about the error
        """
        super().__init__(f"Configuration Error: {message}", details)


class ValidationError(FlexiAIException):
    """
    Raised when input validation fails.

    This exception is raised when:
    - Request parameters are invalid
    - Message format is incorrect
    - Required fields are missing
    - Values are out of acceptable range

    Example:
        >>> raise ValidationError(
        ...     "Temperature must be between 0.0 and 2.0",
        ...     details={"parameter": "temperature", "value": 3.0, "range": "0.0-2.0"}
        ... )
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize ValidationError.

        Args:
            message: Description of the validation error
            details: Additional context about the validation failure
        """
        super().__init__(f"Validation Error: {message}", details)


class AuthenticationError(FlexiAIException):
    """
    Raised when authentication with a provider fails.

    This exception is raised when:
    - API key is invalid or expired
    - API key format is incorrect
    - Authentication request fails
    - Credentials cannot be verified

    Example:
        >>> raise AuthenticationError(
        ...     "Invalid API key for OpenAI",
        ...     details={"provider": "openai", "key_format": "sk-..."}
        ... )
    """

    def __init__(
        self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize AuthenticationError.

        Args:
            message: Description of the authentication error
            provider: Name of the provider that failed authentication
            details: Additional context about the error
        """
        error_details = details or {}
        if provider:
            error_details["provider"] = provider
        super().__init__(f"Authentication Error: {message}", error_details)


class ProviderException(FlexiAIException):
    """
    Raised when a provider encounters an error.

    This is a general exception for provider-related errors that don't fit
    into more specific categories. Provider-specific errors are mapped to
    this exception by the provider implementations.

    Example:
        >>> raise ProviderException(
        ...     "OpenAI API returned an error",
        ...     provider="openai",
        ...     details={"status_code": 500, "error": "Internal server error"}
        ... )
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        is_retryable: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize ProviderException.

        Args:
            message: Description of the provider error
            provider: Name of the provider that encountered the error
            is_retryable: Whether the operation can be retried
            details: Additional context about the error
        """
        error_details = details or {}
        if provider:
            error_details["provider"] = provider
        error_details["retryable"] = is_retryable
        super().__init__(f"Provider Error: {message}", error_details)
        self.provider = provider
        self.is_retryable = is_retryable


class RateLimitError(ProviderException):
    """
    Raised when a provider's rate limit is exceeded.

    This exception is raised when:
    - Too many requests in a time window
    - Token quota exceeded
    - Concurrent request limit reached

    Example:
        >>> raise RateLimitError(
        ...     "Rate limit exceeded for OpenAI API",
        ...     provider="openai",
        ...     retry_after=60,
        ...     details={"limit": 10000, "reset_time": "2024-01-01T00:00:00Z"}
        ... )
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize RateLimitError.

        Args:
            message: Description of the rate limit error
            provider: Name of the provider
            retry_after: Seconds to wait before retrying
            details: Additional context about the rate limit
        """
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
        super().__init__(message, provider=provider, is_retryable=True, details=error_details)
        self.retry_after = retry_after


class TimeoutError(ProviderException):
    """
    Raised when a provider request times out.

    This exception is raised when:
    - Request exceeds configured timeout
    - Connection cannot be established
    - Response takes too long to arrive

    Example:
        >>> raise TimeoutError(
        ...     "Request to OpenAI timed out after 30 seconds",
        ...     provider="openai",
        ...     timeout=30,
        ...     details={"endpoint": "https://api.openai.com/v1/chat/completions"}
        ... )
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        timeout: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize TimeoutError.

        Args:
            message: Description of the timeout error
            provider: Name of the provider
            timeout: Timeout value in seconds
            details: Additional context about the timeout
        """
        error_details = details or {}
        if timeout:
            error_details["timeout"] = timeout
        super().__init__(message, provider=provider, is_retryable=True, details=error_details)
        self.timeout = timeout


class APIConnectionError(ProviderException):
    """
    Raised when connection to a provider API fails.

    This exception is raised when:
    - Network connection fails
    - DNS resolution fails
    - SSL/TLS handshake fails
    - Connection is refused

    Example:
        >>> raise APIConnectionError(
        ...     "Failed to connect to OpenAI API",
        ...     provider="openai",
        ...     details={"endpoint": "https://api.openai.com", "reason": "Connection refused"}
        ... )
    """

    def __init__(
        self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize APIConnectionError.

        Args:
            message: Description of the connection error
            provider: Name of the provider
            details: Additional context about the connection failure
        """
        super().__init__(message, provider=provider, is_retryable=True, details=details)


class CircuitBreakerOpenError(FlexiAIException):
    """
    Raised when a circuit breaker is open and prevents requests.

    The circuit breaker opens after a threshold of failures is reached,
    preventing further requests to give the provider time to recover.

    Example:
        >>> raise CircuitBreakerOpenError(
        ...     "Circuit breaker is OPEN for provider 'openai'",
        ...     provider="openai",
        ...     failure_count=5,
        ...     details={"recovery_timeout": 60, "last_failure": "2024-01-01T00:00:00Z"}
        ... )
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        failure_count: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize CircuitBreakerOpenError.

        Args:
            message: Description of the circuit breaker state
            provider: Name of the provider with open circuit
            failure_count: Number of failures that triggered the circuit
            details: Additional context about the circuit state
        """
        error_details = details or {}
        if provider:
            error_details["provider"] = provider
        if failure_count:
            error_details["failure_count"] = failure_count
        super().__init__(f"Circuit Breaker: {message}", error_details)
        self.provider = provider
        self.failure_count = failure_count


class AllProvidersFailedError(FlexiAIException):
    """
    Raised when all configured providers have failed.

    This is a critical error indicating that no providers are available
    to handle the request. It contains information about all the failures.

    Example:
        >>> raise AllProvidersFailedError(
        ...     "All 3 providers failed to complete the request",
        ...     provider_errors={
        ...         "openai": "Rate limit exceeded",
        ...         "gemini": "API connection failed",
        ...         "anthropic": "Circuit breaker open"
        ...     },
        ...     details={"request_id": "req_123", "timestamp": "2024-01-01T00:00:00Z"}
        ... )
    """

    def __init__(
        self,
        message: str,
        provider_errors: Optional[Dict[str, str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize AllProvidersFailedError.

        Args:
            message: Description of the failure
            provider_errors: Dictionary mapping provider names to error messages
            details: Additional context about the failure
        """
        error_details = details or {}
        if provider_errors:
            error_details["provider_errors"] = provider_errors
        super().__init__(f"All Providers Failed: {message}", error_details)
        self.provider_errors = provider_errors or {}

    def __str__(self) -> str:
        """Return detailed string representation including all provider errors."""
        base = super().__str__()
        if self.provider_errors:
            errors = "\n".join(
                [f"  - {provider}: {error}" for provider, error in self.provider_errors.items()]
            )
            return f"{base}\nProvider Errors:\n{errors}"
        return base


class ContentFilterError(ProviderException):
    """
    Raised when content is filtered by safety mechanisms.

    This exception is raised when:
    - Content violates provider's safety policies
    - Request is blocked by content filters
    - Response is blocked due to safety concerns

    Example:
        >>> raise ContentFilterError(
        ...     "Content filtered due to safety policies",
        ...     provider="gemini",
        ...     details={"category": "harassment", "severity": "high"}
        ... )
    """

    def __init__(
        self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize ContentFilterError.

        Args:
            message: Description of the content filter error
            provider: Name of the provider
            details: Additional context about the filtering
        """
        super().__init__(message, provider=provider, is_retryable=False, details=details)


class ModelNotFoundError(ProviderException):
    """
    Raised when the requested model is not found or not available.

    Example:
        >>> raise ModelNotFoundError(
        ...     "Model 'gpt-5' not found",
        ...     provider="openai",
        ...     model="gpt-5",
        ...     details={"available_models": ["gpt-4", "gpt-3.5-turbo"]}
        ... )
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize ModelNotFoundError.

        Args:
            message: Description of the error
            provider: Name of the provider
            model: Name of the model that was not found
            details: Additional context
        """
        error_details = details or {}
        if model:
            error_details["model"] = model
        super().__init__(message, provider=provider, is_retryable=False, details=error_details)
        self.model = model


class InvalidResponseError(ProviderException):
    """
    Raised when a provider returns an invalid or malformed response.

    Example:
        >>> raise InvalidResponseError(
        ...     "Provider returned invalid JSON",
        ...     provider="openai",
        ...     details={"error": "Invalid JSON format", "response_preview": "..."}
        ... )
    """

    def __init__(
        self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize InvalidResponseError.

        Args:
            message: Description of the error
            provider: Name of the provider
            details: Additional context about the invalid response
        """
        super().__init__(message, provider=provider, is_retryable=False, details=details)
