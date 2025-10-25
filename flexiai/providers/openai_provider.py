"""
OpenAI provider implementation for FlexiAI.

This module provides the OpenAI provider that integrates with OpenAI's API
using the official OpenAI Python SDK.
"""

from typing import Any, Dict, List

import openai
from openai import OpenAI

from flexiai.exceptions import (
    AuthenticationError,
    InvalidResponseError,
    ProviderException,
    RateLimitError,
    ValidationError,
)
from flexiai.models import ProviderConfig, UnifiedRequest, UnifiedResponse
from flexiai.normalizers.request import OpenAIRequestNormalizer
from flexiai.normalizers.response import OpenAIResponseNormalizer
from flexiai.providers.base import BaseProvider
from flexiai.utils.validators import APIKeyValidator


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider implementation.

    This class implements the BaseProvider interface for OpenAI's API,
    handling authentication, request normalization, and error mapping.

    Attributes:
        client: OpenAI client instance
        request_normalizer: Normalizer for converting unified requests to OpenAI format
        response_normalizer: Normalizer for converting OpenAI responses to unified format
    """

    # OpenAI models supported by this provider
    SUPPORTED_MODELS = [
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4-turbo-preview",
        "gpt-4-0125-preview",
        "gpt-4-1106-preview",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo-1106",
    ]

    def __init__(self, config: ProviderConfig) -> None:
        """
        Initialize OpenAI provider.

        Args:
            config: Provider configuration

        Raises:
            ValidationError: If configuration is invalid
            AuthenticationError: If credentials are invalid
        """
        super().__init__(config)

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=0,  # We handle retries in BaseProvider
        )

        # Initialize normalizers
        self.request_normalizer = OpenAIRequestNormalizer()
        self.response_normalizer = OpenAIResponseNormalizer()

        self.logger.info(
            "OpenAI provider initialized",
            extra={"model": self.config.model, "timeout": self.config.timeout},
        )

    def chat_completion(self, request: UnifiedRequest) -> UnifiedResponse:
        """
        Execute a chat completion request with OpenAI.

        Args:
            request: Unified request object

        Returns:
            Unified response object

        Raises:
            ProviderException: If the request fails
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
            ValidationError: If request validation fails
        """
        try:
            # Normalize request to OpenAI format
            openai_request = self.request_normalizer.normalize(request)

            # Add model from config
            openai_request["model"] = self.config.model

            self.logger.debug(
                "Sending request to OpenAI",
                extra={
                    "model": self.config.model,
                    "message_count": len(request.messages),
                },
            )

            # Make API call
            response = self.client.chat.completions.create(**openai_request)

            # Convert response to dictionary for normalization
            response_dict = response.model_dump()

            self.logger.debug(
                "Received response from OpenAI",
                extra={
                    "model": response_dict.get("model"),
                    "finish_reason": response_dict.get("choices", [{}])[0].get("finish_reason"),
                },
            )

            # Normalize response to unified format
            unified_response = self.response_normalizer.normalize(
                response_dict, provider_name=self.name, model=self.config.model
            )

            return unified_response

        except openai.AuthenticationError as e:
            self.logger.error(
                f"OpenAI authentication failed: {str(e)}",
                extra={"error_type": "AuthenticationError"},
            )
            raise AuthenticationError(f"OpenAI authentication failed: {str(e)}", provider=self.name)

        except openai.RateLimitError as e:
            self.logger.warning(
                f"OpenAI rate limit exceeded: {str(e)}",
                extra={"error_type": "RateLimitError"},
            )
            raise RateLimitError(
                f"OpenAI rate limit exceeded: {str(e)}",
                provider=self.name,
                retry_after=getattr(e, "retry_after", None),
            )

        except openai.BadRequestError as e:
            self.logger.error(
                f"OpenAI bad request: {str(e)}", extra={"error_type": "BadRequestError"}
            )
            raise ValidationError(f"Invalid request to OpenAI: {str(e)}")

        except openai.APIError as e:
            self.logger.error(f"OpenAI API error: {str(e)}", extra={"error_type": "APIError"})
            raise ProviderException(f"OpenAI API error: {str(e)}", provider=self.name)

        except InvalidResponseError as e:
            # Response normalization failed
            self.logger.error(
                f"Failed to normalize OpenAI response: {str(e)}",
                extra={"error_type": "InvalidResponseError"},
            )
            raise

        except Exception as e:
            self.logger.error(
                f"Unexpected error in OpenAI provider: {str(e)}",
                extra={"error_type": type(e).__name__},
            )
            raise ProviderException(f"Unexpected error: {str(e)}", provider=self.name)

    def authenticate(self) -> bool:
        """
        Authenticate with OpenAI.

        This method verifies that credentials are valid by making a simple API call.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Make a simple API call to verify authentication
            # List models is a lightweight operation
            self.client.models.list(limit=1)

            self._authenticated = True
            self.logger.info("OpenAI authentication successful")
            return True

        except openai.AuthenticationError as e:
            self.logger.error(f"OpenAI authentication failed: {str(e)}")
            raise AuthenticationError(f"OpenAI authentication failed: {str(e)}", provider=self.name)

        except Exception as e:
            self.logger.error(f"Unexpected error during authentication: {str(e)}")
            raise AuthenticationError(f"Authentication error: {str(e)}", provider=self.name)

    def validate_credentials(self) -> bool:
        """
        Validate OpenAI credentials.

        This method checks that credentials are properly formatted
        without making external API calls.

        Returns:
            True if credentials are valid

        Raises:
            ValidationError: If credentials are invalid or missing
        """
        # Validate API key format
        APIKeyValidator.validate("openai", self.config.api_key)

        # Validate model is supported
        if self.config.model not in self.SUPPORTED_MODELS:
            self.logger.warning(
                f"Model '{self.config.model}' not in known supported models list",
                extra={"model": self.config.model},
            )
            # Don't fail - model might be new or custom
            # Just log a warning

        self.logger.debug("OpenAI credentials validated")
        return True

    def health_check(self) -> bool:
        """
        Perform a health check on OpenAI API.

        This method verifies that the OpenAI API is accessible
        and functioning properly.

        Returns:
            True if provider is healthy

        Raises:
            ProviderException: If health check fails
        """
        try:
            # Make a lightweight API call to check health
            # List models with limit=1 is quick and cheap
            response = self.client.models.list(limit=1)

            # Check that we got a valid response
            if not response or not hasattr(response, "data"):
                raise ProviderException(
                    "Invalid response from OpenAI health check", provider=self.name
                )

            self.logger.debug("OpenAI health check passed")
            return True

        except openai.AuthenticationError as e:
            raise AuthenticationError(
                f"Health check failed - authentication error: {str(e)}",
                provider=self.name,
            )

        except Exception as e:
            raise ProviderException(f"Health check failed: {str(e)}", provider=self.name)

    def get_supported_models(self) -> List[str]:
        """
        Get list of models supported by OpenAI provider.

        Returns:
            List of supported model names
        """
        return self.SUPPORTED_MODELS.copy()

    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get OpenAI provider information and metadata.

        Returns:
            Dictionary containing provider information
        """
        info = super().get_provider_info()
        info["sdk_version"] = openai.__version__
        return info
