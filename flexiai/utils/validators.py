"""
Validation utilities for FlexiAI.

This module provides validators for:
- API keys for different providers
- Model names
- Request parameters
- Provider-specific requirements
"""

import re
from typing import Any, Dict, List

from flexiai.exceptions import ValidationError


class APIKeyValidator:
    """
    Validator for API keys across different providers.

    Each provider has different API key formats. This class validates
    API keys to ensure they match expected patterns.
    """

    # API key patterns for different providers
    PATTERNS = {
        "openai": re.compile(
            r"^sk-[a-zA-Z0-9\-_]{20,}$"
        ),  # Updated to support new OpenAI key format with dashes
        "anthropic": re.compile(r"^sk-ant-[a-zA-Z0-9\-]{20,}$"),
        "gemini": re.compile(r"^[a-zA-Z0-9\-_]{20,}$"),
        "azure": re.compile(r"^[a-zA-Z0-9]{32}$"),
        "bedrock": re.compile(r"^[A-Z0-9]{20}$"),
    }

    @classmethod
    def validate(cls, provider: str, api_key: str) -> bool:
        """
        Validate an API key for a specific provider.

        Args:
            provider: Provider name (openai, anthropic, gemini, etc.)
            api_key: API key to validate

        Returns:
            True if the API key is valid

        Raises:
            ValidationError: If the API key is invalid

        Example:
            >>> APIKeyValidator.validate("openai", "sk-abc123...")
            True
        """
        if not api_key or not api_key.strip():
            raise ValidationError(
                f"API key for {provider} cannot be empty",
                details={"provider": provider},
            )

        provider_lower = provider.lower()
        pattern = cls.PATTERNS.get(provider_lower)

        if pattern is None:
            # Unknown provider - just check it's not empty
            return True

        if not pattern.match(api_key):
            raise ValidationError(
                f"Invalid API key format for {provider}",
                details={"provider": provider, "expected_pattern": pattern.pattern},
            )

        return True


class ModelValidator:
    """
    Validator for model names across different providers.

    Maintains lists of supported models for each provider and validates
    that requested models are available.
    """

    # Supported models for each provider
    SUPPORTED_MODELS = {
        "openai": [
            "gpt-4",
            "gpt-4-turbo-preview",
            "gpt-4-1106-preview",
            "gpt-4-0125-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-3.5-turbo-1106",
        ],
        "anthropic": [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2",
        ],
        "gemini": [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-ultra",
        ],
        "azure": [
            # Azure uses deployment names, so we allow any non-empty string
            "*",
        ],
        "bedrock": [
            "anthropic.claude-v2",
            "anthropic.claude-v2:1",
            "anthropic.claude-instant-v1",
            "ai21.j2-ultra-v1",
            "ai21.j2-mid-v1",
            "amazon.titan-text-express-v1",
        ],
    }

    @classmethod
    def validate(cls, provider: str, model: str, strict: bool = False) -> bool:
        """
        Validate a model name for a specific provider.

        Args:
            provider: Provider name
            model: Model name to validate
            strict: If True, raise error for unknown models. If False, allow them.

        Returns:
            True if the model is valid

        Raises:
            ValidationError: If the model is invalid and strict=True

        Example:
            >>> ModelValidator.validate("openai", "gpt-4")
            True
            >>> ModelValidator.validate("openai", "invalid-model", strict=True)
            ValidationError: Model 'invalid-model' not supported for provider openai
        """
        if not model or not model.strip():
            raise ValidationError(
                f"Model name for {provider} cannot be empty",
                details={"provider": provider},
            )

        provider_lower = provider.lower()
        supported = cls.SUPPORTED_MODELS.get(provider_lower, [])

        # Azure allows any model (deployment name)
        if "*" in supported:
            return True

        # Check if model is in supported list
        if model not in supported:
            if strict:
                raise ValidationError(
                    f"Model '{model}' not supported for provider {provider}",
                    details={
                        "provider": provider,
                        "model": model,
                        "supported_models": supported,
                    },
                )
            # In non-strict mode, allow unknown models (they might be newer)
            return True

        return True

    @classmethod
    def get_supported_models(cls, provider: str) -> List[str]:
        """
        Get list of supported models for a provider.

        Args:
            provider: Provider name

        Returns:
            List of supported model names

        Example:
            >>> models = ModelValidator.get_supported_models("openai")
            >>> print(models)
            ['gpt-4', 'gpt-4-turbo-preview', ...]
        """
        return cls.SUPPORTED_MODELS.get(provider.lower(), [])


class RequestValidator:
    """
    Validator for request parameters.

    Validates common request parameters like temperature, max_tokens, etc.
    """

    @classmethod
    def validate_temperature(cls, temperature: float) -> bool:
        """
        Validate temperature parameter.

        Args:
            temperature: Temperature value (0.0 to 2.0)

        Returns:
            True if valid

        Raises:
            ValidationError: If temperature is out of range

        Example:
            >>> RequestValidator.validate_temperature(0.7)
            True
        """
        if not isinstance(temperature, (int, float)):
            raise ValidationError(
                "Temperature must be a number",
                details={"temperature": temperature, "type": type(temperature).__name__},
            )

        if not 0.0 <= temperature <= 2.0:
            raise ValidationError(
                "Temperature must be between 0.0 and 2.0",
                details={"temperature": temperature},
            )

        return True

    @classmethod
    def validate_max_tokens(cls, max_tokens: int, provider: str = "openai") -> bool:
        """
        Validate max_tokens parameter.

        Args:
            max_tokens: Maximum tokens to generate
            provider: Provider name (for provider-specific limits)

        Returns:
            True if valid

        Raises:
            ValidationError: If max_tokens is invalid

        Example:
            >>> RequestValidator.validate_max_tokens(100)
            True
        """
        if not isinstance(max_tokens, int):
            raise ValidationError(
                "max_tokens must be an integer",
                details={"max_tokens": max_tokens, "type": type(max_tokens).__name__},
            )

        if max_tokens < 1:
            raise ValidationError(
                "max_tokens must be at least 1",
                details={"max_tokens": max_tokens},
            )

        # Provider-specific limits
        limits = {
            "openai": 4096,
            "anthropic": 4096,
            "gemini": 2048,
        }

        limit = limits.get(provider.lower(), 4096)
        if max_tokens > limit:
            raise ValidationError(
                f"max_tokens exceeds {provider} limit of {limit}",
                details={"max_tokens": max_tokens, "limit": limit, "provider": provider},
            )

        return True

    @classmethod
    def validate_top_p(cls, top_p: float) -> bool:
        """
        Validate top_p parameter.

        Args:
            top_p: Top-p sampling value (0.0 to 1.0)

        Returns:
            True if valid

        Raises:
            ValidationError: If top_p is out of range

        Example:
            >>> RequestValidator.validate_top_p(0.9)
            True
        """
        if not isinstance(top_p, (int, float)):
            raise ValidationError(
                "top_p must be a number",
                details={"top_p": top_p, "type": type(top_p).__name__},
            )

        if not 0.0 <= top_p <= 1.0:
            raise ValidationError(
                "top_p must be between 0.0 and 1.0",
                details={"top_p": top_p},
            )

        return True

    @classmethod
    def validate_frequency_penalty(cls, frequency_penalty: float) -> bool:
        """
        Validate frequency_penalty parameter.

        Args:
            frequency_penalty: Frequency penalty value (-2.0 to 2.0)

        Returns:
            True if valid

        Raises:
            ValidationError: If frequency_penalty is out of range

        Example:
            >>> RequestValidator.validate_frequency_penalty(0.5)
            True
        """
        if not isinstance(frequency_penalty, (int, float)):
            raise ValidationError(
                "frequency_penalty must be a number",
                details={
                    "frequency_penalty": frequency_penalty,
                    "type": type(frequency_penalty).__name__,
                },
            )

        if not -2.0 <= frequency_penalty <= 2.0:
            raise ValidationError(
                "frequency_penalty must be between -2.0 and 2.0",
                details={"frequency_penalty": frequency_penalty},
            )

        return True

    @classmethod
    def validate_presence_penalty(cls, presence_penalty: float) -> bool:
        """
        Validate presence_penalty parameter.

        Args:
            presence_penalty: Presence penalty value (-2.0 to 2.0)

        Returns:
            True if valid

        Raises:
            ValidationError: If presence_penalty is out of range

        Example:
            >>> RequestValidator.validate_presence_penalty(0.5)
            True
        """
        if not isinstance(presence_penalty, (int, float)):
            raise ValidationError(
                "presence_penalty must be a number",
                details={
                    "presence_penalty": presence_penalty,
                    "type": type(presence_penalty).__name__,
                },
            )

        if not -2.0 <= presence_penalty <= 2.0:
            raise ValidationError(
                "presence_penalty must be between -2.0 and 2.0",
                details={"presence_penalty": presence_penalty},
            )

        return True

    @classmethod
    def validate_messages(cls, messages: List[Dict[str, Any]]) -> bool:
        """
        Validate messages list.

        Args:
            messages: List of message dictionaries

        Returns:
            True if valid

        Raises:
            ValidationError: If messages are invalid

        Example:
            >>> RequestValidator.validate_messages([
            ...     {"role": "user", "content": "Hello"}
            ... ])
            True
        """
        if not isinstance(messages, list):
            raise ValidationError(
                "messages must be a list",
                details={"type": type(messages).__name__},
            )

        if not messages:
            raise ValidationError("messages list cannot be empty")

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValidationError(
                    f"Message at index {i} must be a dictionary",
                    details={"index": i, "type": type(msg).__name__},
                )

            if "role" not in msg:
                raise ValidationError(
                    f"Message at index {i} missing 'role' field",
                    details={"index": i, "message": msg},
                )

            if "content" not in msg and "tool_calls" not in msg and "function_call" not in msg:
                raise ValidationError(
                    f"Message at index {i} must have 'content', 'tool_calls', or 'function_call'",
                    details={"index": i, "message": msg},
                )

        return True


def validate_provider_config(provider: str, config: Dict[str, Any]) -> bool:
    """
    Validate provider-specific configuration.

    Args:
        provider: Provider name
        config: Configuration dictionary

    Returns:
        True if valid

    Raises:
        ValidationError: If configuration is invalid

    Example:
        >>> validate_provider_config("openai", {
        ...     "api_key": "sk-...",
        ...     "model": "gpt-4"
        ... })
        True
    """
    # Validate API key
    if "api_key" in config:
        APIKeyValidator.validate(provider, config["api_key"])

    # Validate model
    if "model" in config:
        ModelValidator.validate(provider, config["model"], strict=False)

    # Validate timeout
    if "timeout" in config:
        timeout = config["timeout"]
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValidationError(
                "Timeout must be a positive number",
                details={"timeout": timeout},
            )

    # Validate max_retries
    if "max_retries" in config:
        max_retries = config["max_retries"]
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValidationError(
                "max_retries must be a non-negative integer",
                details={"max_retries": max_retries},
            )

    return True
