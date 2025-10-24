"""
FlexiAI: A unified interface for multiple GenAI providers with automatic failover.

This package provides a simple, unified API for interacting with multiple GenAI providers
(OpenAI, Google Gemini, Anthropic Claude) with automatic failover using circuit breaker pattern.
"""

__version__ = "0.1.0"
__author__ = "FlexiAI Contributors"

from flexiai.client import FlexiAI
from flexiai.config import FlexiAIConfig, ProviderConfig, CircuitBreakerConfig
from flexiai.exceptions import (
    FlexiAIException,
    ProviderException,
    ConfigurationError,
    CircuitBreakerOpenError,
    AllProvidersFailedError,
    ValidationError,
    AuthenticationError,
)

__all__ = [
    "FlexiAI",
    "FlexiAIConfig",
    "ProviderConfig",
    "CircuitBreakerConfig",
    "FlexiAIException",
    "ProviderException",
    "ConfigurationError",
    "CircuitBreakerOpenError",
    "AllProvidersFailedError",
    "ValidationError",
    "AuthenticationError",
]
