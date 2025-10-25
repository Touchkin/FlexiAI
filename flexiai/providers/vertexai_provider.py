"""
Google Vertex AI Provider for FlexiAI.

This module implements the Vertex AI provider using the Google GenAI SDK.
It uses Google Cloud authentication (ADC) instead of API keys.
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


class VertexAIProvider(BaseProvider):
    """
    Google Vertex AI provider implementation.

    This provider uses the google-genai SDK with Vertex AI endpoints.
    It uses Google Cloud Application Default Credentials (ADC) for authentication
    instead of API keys.

    Authentication:
        Uses Google Cloud Application Default Credentials (ADC).
        Set up ADC by running: gcloud auth application-default login
        Or use a service account: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

    Configuration:
        - project: GCP project ID (or GOOGLE_CLOUD_PROJECT env var)
        - location: GCP region (or GOOGLE_CLOUD_LOCATION env var, default: us-central1)

    Attributes:
        client: Vertex AI client
        project: GCP project ID
        location: GCP region
        request_normalizer: Request normalizer (reuses Gemini normalizer)
        response_normalizer: Response normalizer (reuses Gemini normalizer)
    """

    def __init__(self, config: ProviderConfig) -> None:
        """
        Initialize Vertex AI provider.

        Args:
            config: Provider configuration with project and location info
                   - config.api_key: GCP API key (for API key auth) OR set to "not-used" for ADC
                   - config.config['project']: GCP project ID (required for ADC, optional for API key)
                   - config.config['location']: GCP region (optional, default: us-central1)

        Raises:
            ValidationError: If configuration is invalid
            AuthenticationError: If credentials are not available
        """
        # Extract Vertex AI specific config BEFORE calling super().__init__
        # because the parent calls validate_credentials() which needs self.project
        self.config = config
        self.project = config.config.get("project") or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = config.config.get("location") or os.getenv(
            "GOOGLE_CLOUD_LOCATION", "us-central1"
        )

        # Check if using API key authentication
        api_key = config.api_key
        using_api_key = api_key and api_key != "not-used" and not api_key.startswith("not-")

        # Validate required config
        # Project is only required when using ADC (not API key)
        if not using_api_key and not self.project:
            raise ValidationError(
                "GCP project ID is required for Vertex AI when using ADC. "
                "Set 'project' in config or GOOGLE_CLOUD_PROJECT environment variable. "
                "Or provide an API key for authentication."
            )

        # Now initialize parent class (which will call validate_credentials)
        super().__init__(config)

        # Initialize normalizers (reuse Gemini normalizers since API is the same)
        self.request_normalizer = GeminiRequestNormalizer()
        self.response_normalizer = GeminiResponseNormalizer()

        # Initialize client
        self.client: genai.Client = None
        self._initialize_client()

        if using_api_key:
            self.logger.info(
                f"Initialized Vertex AI provider with model: {self.config.model} (API key auth)"
            )
        else:
            self.logger.info(
                f"Initialized Vertex AI provider with model: {self.config.model}, "
                f"project: {self.project}, location: {self.location}"
            )

    def _initialize_client(self) -> None:
        """
        Initialize the Vertex AI client.

        Supports multiple authentication methods:
        1. Service Account JSON file (via GOOGLE_APPLICATION_CREDENTIALS env var or config)
        2. Google Cloud Application Default Credentials (ADC)

        Raises:
            AuthenticationError: If credentials are not available
        """
        try:
            # Check for service account credentials
            service_account_path = (
                self.config.config.get("service_account_file")
                or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            )

            if service_account_path:
                # Use service account file
                self.logger.debug(f"Initializing Vertex AI with service account: {service_account_path}")
                
                # Load credentials from service account file
                from google.oauth2 import service_account
                
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                
                self.client = genai.Client(
                    vertexai=True,
                    project=self.project,
                    location=self.location,
                    credentials=credentials,
                )
                self.logger.debug(
                    f"Vertex AI client initialized with service account for project: {self.project}"
                )
            else:
                # Use Application Default Credentials (ADC)
                self.logger.debug("Initializing Vertex AI client with ADC")
                self.client = genai.Client(
                    vertexai=True,
                    project=self.project,
                    location=self.location,
                    # credentials=None means use ADC
                )
                self.logger.debug(
                    f"Vertex AI client initialized with ADC for project: {self.project}"
                )
        except Exception as e:
            raise AuthenticationError(
                f"Failed to initialize Vertex AI client: {str(e)}. "
                "Make sure you have either: "
                "1. A valid service account JSON file (set GOOGLE_APPLICATION_CREDENTIALS env var or 'service_account_file' in config), or "
                "2. Valid Google Cloud credentials (run 'gcloud auth application-default login')"
            ) from e

    def chat_completion(self, request: UnifiedRequest) -> UnifiedResponse:
        """
        Execute a chat completion request using Vertex AI.

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
            # Normalize request to Gemini/Vertex AI format
            gemini_request = self.request_normalizer.normalize(request)

            self.logger.debug(
                f"Making Vertex AI request with model: {self.config.model}, "
                f"project: {self.project}, location: {self.location}"
            )
            self.logger.debug(f"Request params: {gemini_request.keys()}")

            # Make API call using the Vertex AI endpoints
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=gemini_request.get("contents"),
                config=types.GenerateContentConfig(
                    system_instruction=gemini_request.get("system_instruction"),
                    **gemini_request.get("generationConfig", {}),
                ),
            )

            self.logger.debug("Received response from Vertex AI")

            # Convert response to dict for normalization
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
            # Handle and map Vertex AI-specific errors
            self._handle_error(e)

    def _response_to_dict(self, response) -> Dict[str, Any]:
        """
        Convert Vertex AI response object to dictionary.

        Args:
            response: Vertex AI response object

        Returns:
            Dictionary representation of the response
        """
        result = {}

        # Extract candidates
        if hasattr(response, "candidates") and response.candidates:
            result["candidates"] = []
            for candidate in response.candidates:
                candidate_dict = {}

                # Extract content
                if hasattr(candidate, "content") and candidate.content:
                    content_dict = {}
                    if hasattr(candidate.content, "parts") and candidate.content.parts:
                        content_dict["parts"] = []
                        for part in candidate.content.parts:
                            if hasattr(part, "text"):
                                content_dict["parts"].append({"text": part.text})
                    if hasattr(candidate.content, "role"):
                        content_dict["role"] = candidate.content.role
                    candidate_dict["content"] = content_dict

                # Extract finish reason
                if hasattr(candidate, "finish_reason"):
                    candidate_dict["finishReason"] = str(candidate.finish_reason).split(".")[-1]

                # Extract safety ratings
                if hasattr(candidate, "safety_ratings") and candidate.safety_ratings:
                    candidate_dict["safetyRatings"] = []
                    for rating in candidate.safety_ratings:
                        rating_dict = {}
                        if hasattr(rating, "category"):
                            rating_dict["category"] = str(rating.category).split(".")[-1]
                        if hasattr(rating, "probability"):
                            rating_dict["probability"] = str(rating.probability).split(".")[-1]
                        candidate_dict["safetyRatings"].append(rating_dict)

                result["candidates"].append(candidate_dict)

        # Extract usage metadata
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage_dict = {}
            if hasattr(response.usage_metadata, "prompt_token_count"):
                usage_dict["promptTokenCount"] = response.usage_metadata.prompt_token_count
            if hasattr(response.usage_metadata, "candidates_token_count"):
                usage_dict["candidatesTokenCount"] = response.usage_metadata.candidates_token_count
            if hasattr(response.usage_metadata, "total_token_count"):
                usage_dict["totalTokenCount"] = response.usage_metadata.total_token_count
            result["usageMetadata"] = usage_dict

        # Extract model version
        if hasattr(response, "model_version"):
            result["modelVersion"] = response.model_version

        return result

    def _handle_error(self, error: Exception) -> None:
        """
        Handle and transform Vertex AI-specific errors.

        Args:
            error: The exception that occurred

        Raises:
            Appropriate FlexiAI exception based on error type
        """
        error_msg = str(error)
        error_type = type(error).__name__

        self.logger.error(f"Vertex AI error: {error_type} - {error_msg}")

        # Rate limit errors
        if "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            raise RateLimitError(f"Vertex AI rate limit exceeded: {error_msg}") from error

        # Authentication errors
        if (
            "permission" in error_msg.lower()
            or "credential" in error_msg.lower()
            or "authentication" in error_msg.lower()
            or "unauthorized" in error_msg.lower()
        ):
            raise AuthenticationError(f"Vertex AI authentication failed: {error_msg}") from error

        # Validation errors
        if "invalid" in error_msg.lower() or "validation" in error_msg.lower():
            raise ValidationError(f"Vertex AI request validation failed: {error_msg}") from error

        # Generic provider error
        raise ProviderException(
            f"Vertex AI request failed: {error_msg}",
            details={"error_type": error_type, "provider": "vertexai"},
        ) from error

    def authenticate(self) -> bool:
        """
        Authenticate with Vertex AI using Google Cloud credentials.

        Vertex AI uses Google Cloud Application Default Credentials (ADC),
        so authentication is handled during client initialization.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # For Vertex AI, authentication happens during client initialization
            # via Application Default Credentials (ADC)
            if self.client is None:
                self._initialize_client()
            return True
        except Exception as e:
            raise AuthenticationError(
                f"Vertex AI authentication failed: {str(e)}. "
                "Make sure you have valid Google Cloud credentials. "
                "Run 'gcloud auth application-default login' or set "
                "GOOGLE_APPLICATION_CREDENTIALS environment variable."
            ) from e

    def validate_credentials(self) -> bool:
        """
        Validate Vertex AI credentials.

        For API key mode: Check that API key exists
        For ADC mode: Check that project ID is set

        Returns:
            True if credentials configuration is valid

        Raises:
            AuthenticationError: If credentials are invalid
        """
        try:
            # Check if using API key
            api_key = self.config.api_key
            using_api_key = api_key and api_key != "not-used" and not api_key.startswith("not-")

            if using_api_key:
                # API key mode - just verify key exists
                if not api_key or len(api_key) < 20:
                    raise ValidationError("Invalid GCP API key")
            else:
                # ADC mode - check that project is set
                if not self.project:
                    raise ValidationError("GCP project ID is required for Vertex AI with ADC")

            return True
        except ValidationError as e:
            raise AuthenticationError(f"Invalid Vertex AI configuration: {str(e)}") from e
        except Exception as e:
            raise AuthenticationError(f"Invalid Vertex AI credentials: {str(e)}") from e

    def health_check(self) -> bool:
        """
        Check if Vertex AI provider is healthy and accessible.

        Returns:
            True if provider is healthy, False otherwise
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
            self.logger.debug("Vertex AI health check passed")
            return True

        except Exception as e:
            self.logger.warning(f"Vertex AI health check failed: {str(e)}")
            return False

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Return Vertex AI provider capabilities.

        Returns:
            Dictionary of capabilities
        """
        return {
            "name": "vertexai",
            "supports_streaming": True,
            "supports_functions": True,
            "supports_vision": "gemini-pro-vision" in self.config.model
            or "2.0" in self.config.model,
            "max_tokens": 32768,  # Default for Gemini 2.0, can vary by model
            "context_window": 1048576 if "2.0" in self.config.model else 32768,  # 1M for 2.0
            "authentication": "gcp-adc",  # Uses Application Default Credentials
            "project": self.project,
            "location": self.location,
        }

    def __repr__(self) -> str:
        """Return string representation of the provider."""
        return (
            f"VertexAIProvider(model='{self.config.model}', "
            f"project='{self.project}', location='{self.location}', "
            f"priority={self.config.priority})"
        )
