"""
FlexiAI: A unified interface for multiple GenAI providers with automatic failover.

This package provides a simple, unified API for interacting with multiple GenAI providers
(OpenAI, Google Gemini, Anthropic Claude) with automatic failover using circuit breaker pattern.
"""

__version__ = "0.1.0"
__author__ = "FlexiAI Contributors"

from flexiai.client import FlexiAI
from flexiai.exceptions import (
    AllProvidersFailedError,
    CircuitBreakerOpenError,
    ConfigurationError,
    FlexiAIException,
    ProviderException,
    ValidationError,
)
from flexiai.models import (
    CircuitBreakerConfig,
    FlexiAIConfig,
    LoggingConfig,
    ProviderConfig,
    RetryConfig,
    UnifiedRequest,
    UnifiedResponse,
)

__all__ = [
    "__version__",
    "__author__",
    "FlexiAI",
    "FlexiAIConfig",
    "ProviderConfig",
    "CircuitBreakerConfig",
    "RetryConfig",
    "LoggingConfig",
    "UnifiedRequest",
    "UnifiedResponse",
    "FlexiAIException",
    "ProviderException",
    "ConfigurationError",
    "ValidationError",
    "CircuitBreakerOpenError",
    "AllProvidersFailedError",
]
