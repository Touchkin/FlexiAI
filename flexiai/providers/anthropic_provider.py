"""
Anthropic Claude provider implementation.

This module provides integration with Anthropic's Claude API using
their Messages API format.
"""

from typing import Any, Dict, Optional

import anthropic
from anthropic import APIConnectionError, APIError
from anthropic import AuthenticationError as AnthropicAuthError
from anthropic import BadRequestError, PermissionDeniedError
from anthropic import RateLimitError as AnthropicRateLimitError

from flexiai.exceptions import (
    AuthenticationError,
    ProviderException,
    RateLimitError,
    ValidationError,
)
from flexiai.models import ProviderConfig, UnifiedRequest, UnifiedResponse
from flexiai.normalizers.request import ClaudeRequestNormalizer
from flexiai.normalizers.response import ClaudeResponseNormalizer
from flexiai.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """
    Provider implementation for Anthropic Claude API.

    Supports Claude 3 models (Opus, Sonnet, Haiku) via Messages API.
    Uses API key authentication with x-api-key header.

    Key Features:
    - System message separation
    - Required max_tokens parameter
    - Alternating user/assistant messages
    - Multi-content block responses
    - Tool use support
    - Streaming support

    Example:
        >>> config = ProviderConfig(
        ...     name="anthropic",
        ...     api_key="sk-ant-...",
        ...     model="claude-3-5-sonnet-20241022",
        ...     priority=1
        ... )
        >>> provider = AnthropicProvider(config)
        >>> response = provider.chat_completion(request)
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize Anthropic provider.

        Args:
            config: Provider configuration with API key

        Raises:
            ValidationError: If configuration is invalid
            AuthenticationError: If API key is invalid
        """
        # Initialize normalizers first
        self.request_normalizer = ClaudeRequestNormalizer()
        self.response_normalizer = ClaudeResponseNormalizer()

        # Now initialize parent class
        super().__init__(config)

        # Initialize Anthropic client
        self.client: Optional[anthropic.Anthropic] = None
        self._initialize_client()

        self.logger.info(f"Initialized Anthropic provider with model: {self.config.model}")

    def _initialize_client(self) -> None:
        """
        Initialize the Anthropic client.

        Raises:
            AuthenticationError: If API key is invalid or missing
        """
        try:
            api_key = self.config.api_key

            if not api_key or api_key.startswith("not-"):
                raise AuthenticationError(
                    "Valid Anthropic API key is required. "
                    "Get your API key from https://console.anthropic.com/"
                )

            # Initialize client with API key and configuration
            # Note: Anthropic client doesn't support timeout/max_retries in __init__
            # These are set per-request
            self.client = anthropic.Anthropic(api_key=api_key)

            self.logger.debug("Anthropic client initialized successfully")

        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(f"Failed to initialize Anthropic client: {str(e)}") from e

    def authenticate(self) -> bool:
        """
        Verify authentication with Anthropic API.

        Returns:
            True if authentication is successful

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Make a minimal request to verify API key
            self.client.messages.create(
                model=self.config.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True

        except AnthropicAuthError as e:
            raise AuthenticationError(f"Anthropic authentication failed: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Authentication check failed: {str(e)}")
            return False

    def validate_credentials(self) -> bool:
        """
        Validate that credentials are properly configured.

        Returns:
            True if credentials are valid
        """
        return bool(self.config.api_key and not self.config.api_key.startswith("not-"))

    def chat_completion(self, request: UnifiedRequest) -> UnifiedResponse:
        """
        Execute a chat completion request using Claude.

        Args:
            request: Unified request object

        Returns:
            Unified response object

        Raises:
            ProviderException: If the request fails
            RateLimitError: If rate limit is exceeded
            ValidationError: If request validation fails
            InvalidResponseError: If response is malformed
        """
        try:
            # Normalize request to Claude Messages API format
            claude_request = self.request_normalizer.normalize(request)

            self.logger.debug(f"Making Anthropic request with model: {self.config.model}")
            self.logger.debug(f"Request params: {list(claude_request.keys())}")

            # Make API call
            response = self.client.messages.create(model=self.config.model, **claude_request)

            self.logger.debug("Received response from Anthropic")

            # Convert response to dict for normalization
            response_dict = self._response_to_dict(response)

            # Normalize response to unified format
            unified_response = self.response_normalizer.normalize(
                response_dict, provider_name="anthropic", model=self.config.model
            )

            self.logger.info(
                f"Anthropic completion successful. "
                f"Tokens: {unified_response.usage.total_tokens}"
            )

            return unified_response

        except Exception as e:
            self.logger.error(f"Anthropic request failed: {str(e)}")
            self._handle_error(e)

    def _response_to_dict(self, response) -> Dict[str, Any]:
        """
        Convert Anthropic response object to dictionary.

        Args:
            response: Anthropic response object

        Returns:
            Dictionary representation of the response
        """
        result = {
            "id": response.id,
            "type": response.type,
            "role": response.role,
            "model": response.model,
            "stop_reason": response.stop_reason,
            "content": [],  # Always include content array
        }

        # Add content blocks
        if hasattr(response, "content") and response.content:
            for block in response.content:
                if hasattr(block, "type"):
                    if block.type == "text":
                        result["content"].append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        result["content"].append(
                            {
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            }
                        )

        # Add stop_sequence if present
        if hasattr(response, "stop_sequence") and response.stop_sequence:
            result["stop_sequence"] = response.stop_sequence

        # Add usage information
        if hasattr(response, "usage") and response.usage:
            result["usage"] = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

        return result

    def _handle_error(self, error: Exception) -> None:
        """
        Handle and transform Anthropic-specific errors.

        Args:
            error: The exception that occurred

        Raises:
            Appropriate FlexiAI exception based on error type
        """
        error_msg = str(error)
        error_type = type(error).__name__

        self.logger.error(f"Anthropic error: {error_type} - {error_msg}")

        # Rate limit errors
        if isinstance(error, AnthropicRateLimitError):
            raise RateLimitError(f"Anthropic rate limit exceeded: {error_msg}") from error

        # Authentication errors
        if isinstance(error, (AnthropicAuthError, PermissionDeniedError)):
            raise AuthenticationError(f"Anthropic authentication failed: {error_msg}") from error

        # Validation errors
        if isinstance(error, BadRequestError):
            raise ValidationError(f"Anthropic request validation failed: {error_msg}") from error

        # Connection errors
        if isinstance(error, APIConnectionError):
            raise ProviderException(
                f"Anthropic connection failed: {error_msg}",
                details={"error_type": error_type, "provider": "anthropic"},
            ) from error

        # Generic API errors
        if isinstance(error, APIError):
            raise ProviderException(
                f"Anthropic API error: {error_msg}",
                details={"error_type": error_type, "provider": "anthropic"},
            ) from error

        # Unknown errors
        raise ProviderException(
            f"Anthropic request failed: {error_msg}",
            details={"error_type": error_type, "provider": "anthropic"},
        ) from error

    def health_check(self) -> bool:
        """
        Check if the Anthropic provider is healthy and responsive.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            # Make a minimal request to check health
            request = UnifiedRequest(messages=[{"role": "user", "content": "Hi"}], max_tokens=5)

            response = self.chat_completion(request)

            # Check if we got a valid response
            return bool(response and response.content)

        except Exception as e:
            self.logger.warning(f"Anthropic health check failed: {str(e)}")
            return False

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Get rate limit information from last response.

        Note:
            Anthropic includes rate limit info in response headers.
            This is a placeholder for future implementation.

        Returns:
            Dictionary with rate limit information
        """
        return {
            "provider": "anthropic",
            "note": "Rate limit info available in response headers",
            "requests_limit": None,
            "requests_remaining": None,
            "tokens_limit": None,
            "tokens_remaining": None,
        }
