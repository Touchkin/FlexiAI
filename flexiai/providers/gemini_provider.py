"""
Google Gemini Provider for FlexiAI.

This module implements the Gemini provider using the Google GenAI SDK.
"""

import os
import time
from typing import Any, Dict

from google import genai
from google.genai import types

from flexiai.exceptions import (
    AuthenticationError,
    InvalidResponseError,
    ProviderException,
    RateLimitError,
    ValidationError,
)
from flexiai.models import ProviderConfig, UnifiedRequest, UnifiedResponse
from flexiai.normalizers.request import GeminiRequestNormalizer
from flexiai.normalizers.response import GeminiResponseNormalizer
from flexiai.providers.base import BaseProvider
from flexiai.utils.validators import APIKeyValidator, ModelValidator


class GeminiProvider(BaseProvider):
    """
    Google Gemini provider implementation.

    This provider uses the google-genai SDK to interact with the Gemini API.
    It handles request/response normalization, authentication, and error handling
    specific to the Gemini platform.

    Attributes:
        client: Gemini API client
        request_normalizer: Request normalizer for Gemini
        response_normalizer: Response normalizer for Gemini
    """

    def __init__(self, config: ProviderConfig) -> None:
        """
        Initialize Gemini provider.

        Args:
            config: Provider configuration with API key and model info

        Raises:
            ValidationError: If configuration is invalid
            AuthenticationError: If API key is invalid
        """
        # Initialize parent class
        super().__init__(config)

        # Initialize normalizers
        self.request_normalizer = GeminiRequestNormalizer()
        self.response_normalizer = GeminiResponseNormalizer()

        # Initialize client
        self.client: genai.Client = None
        self._initialize_client()

        self.logger.info(f"Initialized Gemini provider with model: {self.config.model}")

    def _initialize_client(self) -> None:
        """
        Initialize the Gemini client.

        The API key can come from:
        1. config.api_key
        2. Environment variable GEMINI_API_KEY
        3. Environment variable GOOGLE_API_KEY

        Raises:
            AuthenticationError: If no API key is available
        """
        # Get API key from config or environment
        api_key = self.config.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise AuthenticationError(
                "Gemini API key not found. Set GEMINI_API_KEY environment variable "
                "or provide api_key in configuration."
            )

        try:
            # Initialize the client
            # The google-genai SDK automatically picks up GEMINI_API_KEY from env
            # but we can also pass it explicitly
            self.client = genai.Client(api_key=api_key)
            self.logger.debug("Gemini client initialized successfully")
        except Exception as e:
            raise AuthenticationError(f"Failed to initialize Gemini client: {str(e)}") from e

    def chat_completion(self, request: UnifiedRequest) -> UnifiedResponse:
        """
        Execute a chat completion request using Gemini API.

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
            # Normalize request to Gemini format
            gemini_request = self.request_normalizer.normalize(request)

            self.logger.debug(f"Making Gemini API request with model: {self.config.model}")
            self.logger.debug(f"Request params: {gemini_request.keys()}")

            # Make API call using the new SDK structure
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=gemini_request.get("contents"),
                config=types.GenerateContentConfig(
                    system_instruction=gemini_request.get("system_instruction"),
                    **gemini_request.get("generationConfig", {}),
                ),
            )

            self.logger.debug("Received response from Gemini API")

            # Convert response to dict for normalization
            # The genai SDK returns response objects, we need to extract the data
            response_dict = self._response_to_dict(response)

            # Normalize response to unified format
            unified_response = self.response_normalizer.normalize(
                response_dict,
                provider_name=self.name,
                model=self.config.model,
            )

            self.logger.info(
                f"Successfully completed request. Tokens: "
                f"prompt={unified_response.usage.prompt_tokens}, "
                f"completion={unified_response.usage.completion_tokens}"
            )

            return unified_response

        except InvalidResponseError:
            # Re-raise response errors as-is
            raise
        except Exception as e:
            # Handle and map Gemini-specific errors
            self._handle_error(e)

    def _response_to_dict(self, response) -> Dict[str, Any]:
        """
        Convert Gemini response object to dictionary.

        Args:
            response: Gemini response object

        Returns:
            Dictionary representation of the response
        """
        try:
            # The genai SDK response has attributes we can access
            response_dict = {
                "candidates": [],
                "usageMetadata": {},
                "modelVersion": getattr(response, "model_version", self.config.model),
            }

            # Extract candidates
            if hasattr(response, "candidates") and response.candidates:
                for candidate in response.candidates:
                    candidate_dict = {
                        "content": {"parts": []},
                        "finishReason": getattr(candidate, "finish_reason", "UNKNOWN"),
                        "safetyRatings": getattr(candidate, "safety_ratings", []),
                    }

                    # Extract content parts
                    if hasattr(candidate, "content") and candidate.content:
                        if hasattr(candidate.content, "parts"):
                            for part in candidate.content.parts:
                                if hasattr(part, "text"):
                                    candidate_dict["content"]["parts"].append({"text": part.text})

                    response_dict["candidates"].append(candidate_dict)

            # Extract usage metadata
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                response_dict["usageMetadata"] = {
                    "promptTokenCount": getattr(usage, "prompt_token_count", 0),
                    "candidatesTokenCount": getattr(usage, "candidates_token_count", 0),
                    "totalTokenCount": getattr(usage, "total_token_count", 0),
                }

            # Extract prompt feedback if present
            if hasattr(response, "prompt_feedback"):
                feedback = response.prompt_feedback
                response_dict["promptFeedback"] = {
                    "blockReason": getattr(feedback, "block_reason", None),
                    "safetyRatings": getattr(feedback, "safety_ratings", []),
                }

            return response_dict

        except Exception as e:
            self.logger.error(f"Error converting response to dict: {str(e)}")
            raise InvalidResponseError(f"Failed to parse Gemini response: {str(e)}") from e

    def _handle_error(self, error: Exception) -> None:
        """
        Handle and map Gemini-specific errors to FlexiAI exceptions.

        Args:
            error: Original exception from Gemini API

        Raises:
            Appropriate FlexiAI exception based on error type
        """
        error_message = str(error)
        error_type = type(error).__name__

        self.logger.error(f"Gemini API error ({error_type}): {error_message}")

        # Check for rate limiting
        if (
            "429" in error_message
            or "quota" in error_message.lower()
            or "rate" in error_message.lower()
        ):
            raise RateLimitError(
                f"Gemini rate limit exceeded: {error_message}",
                provider="gemini",
            ) from error

        # Check for authentication errors
        if (
            "401" in error_message
            or "unauthorized" in error_message.lower()
            or "api key" in error_message.lower()
        ):
            raise AuthenticationError(
                f"Gemini authentication failed: {error_message}",
                provider="gemini",
            ) from error

        # Check for validation errors
        if "400" in error_message or "invalid" in error_message.lower():
            raise ValidationError(
                f"Invalid request to Gemini: {error_message}",
                details={"provider": "gemini", "error": error_message},
            ) from error

        # Generic provider exception for other errors
        raise ProviderException(
            f"Gemini provider error: {error_message}",
            provider="gemini",
        ) from error

    def authenticate(self) -> bool:
        """
        Authenticate with Gemini API.

        For Gemini, authentication is done via API key.
        This method verifies the client is initialized.

        Returns:
            True if authenticated

        Raises:
            AuthenticationError: If authentication fails
        """
        if self.client is None:
            self._initialize_client()

        self._authenticated = True
        self.logger.info("Gemini provider authenticated successfully")
        return True

    def validate_credentials(self) -> bool:
        """
        Validate Gemini API credentials.

        This validates the API key format without making an API call.

        Returns:
            True if credentials are valid

        Raises:
            ValidationError: If credentials are invalid
        """
        api_key = self.config.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValidationError(
                "Gemini API key is required",
                details={"provider": "gemini"},
            )

        # Validate API key format
        APIKeyValidator.validate("gemini", api_key)

        # Validate model
        ModelValidator.validate("gemini", self.config.model)

        self.logger.debug("Gemini credentials validated successfully")
        return True

    def health_check(self) -> bool:
        """
        Perform a health check on the Gemini provider.

        This makes a minimal API call to verify the service is available.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Make a minimal request to check health
            test_request = UnifiedRequest(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,  # Minimal tokens to save cost
            )

            _ = self.chat_completion(test_request)

            # If we got a response, provider is healthy
            self._last_health_check = time.time()
            self.logger.debug("Gemini health check passed")
            return True

        except Exception as e:
            self.logger.warning(f"Gemini health check failed: {str(e)}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the configured model.

        Returns:
            Dictionary containing model information
        """
        return {
            "provider": self.name,
            "model": self.config.model,
            "supports_streaming": True,  # Gemini supports streaming
            "supports_function_calling": True,  # Gemini supports function calling
            "supports_vision": "vision" in self.config.model.lower(),
            "max_tokens": 32768,  # Default for Gemini 2.0, can vary by model
            "context_window": 1048576 if "2.0" in self.config.model else 32768,  # 1M for 2.0
        }

    def __repr__(self) -> str:
        """Return string representation of the provider."""
        return f"GeminiProvider(model='{self.config.model}', priority={self.config.priority})"
