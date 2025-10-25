"""
Base provider class for FlexiAI.

This module provides the abstract base class that all providers must inherit from.
It includes common functionality like retry logic, error handling, and health checks.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from flexiai.exceptions import ProviderException, RateLimitError
from flexiai.models import ProviderConfig, UnifiedRequest, UnifiedResponse
from flexiai.utils.logger import FlexiAILogger


class BaseProvider(ABC):
    """
    Abstract base class for all AI providers.

    This class defines the interface that all providers must implement
    and provides common functionality like retry logic, error handling,
    and health checks.

    Attributes:
        name: Provider name (e.g., "openai", "anthropic")
        config: Provider configuration
        logger: Logger instance for this provider
        _authenticated: Whether the provider is authenticated
        _last_health_check: Timestamp of last health check
    """

    def __init__(self, config: ProviderConfig) -> None:
        """
        Initialize the provider.

        Args:
            config: Provider configuration

        Raises:
            ValidationError: If configuration is invalid
        """
        self.config = config
        self.name = config.name
        self.logger = FlexiAILogger.get_logger(f"flexiai.providers.{self.name}")
        self._authenticated = False
        self._last_health_check: Optional[float] = None

        # Validate configuration on initialization
        self.validate_credentials()

    @abstractmethod
    def chat_completion(self, request: UnifiedRequest) -> UnifiedResponse:
        """
        Execute a chat completion request.

        This method must be implemented by each provider to handle
        chat completion requests specific to their API.

        Args:
            request: Unified request object

        Returns:
            Unified response object

        Raises:
            ProviderError: If the request fails
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
            ValidationError: If request validation fails
        """
        pass

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the provider.

        This method should verify credentials and establish authentication.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    def validate_credentials(self) -> bool:
        """
        Validate provider credentials.

        This method should check that credentials are properly formatted
        and present without making external API calls.

        Returns:
            True if credentials are valid

        Raises:
            ValidationError: If credentials are invalid or missing
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Perform a health check on the provider.

        This method should verify that the provider is accessible
        and functioning properly.

        Returns:
            True if provider is healthy

        Raises:
            ProviderError: If health check fails
        """
        pass

    def chat_completion_with_retry(
        self,
        request: UnifiedRequest,
        max_attempts: int = 3,
        min_wait: float = 1.0,
        max_wait: float = 10.0,
    ) -> UnifiedResponse:
        """
        Execute chat completion with automatic retry logic.

        This method wraps chat_completion with exponential backoff retry logic.

        Args:
            request: Unified request object
            max_attempts: Maximum number of retry attempts
            min_wait: Minimum wait time between retries (seconds)
            max_wait: Maximum wait time between retries (seconds)

        Returns:
            Unified response object

        Raises:
            ProviderError: If all retry attempts fail
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
            ValidationError: If request validation fails
        """

        @retry(
            retry=retry_if_exception_type((ProviderException, RateLimitError)),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            reraise=True,
        )
        def _execute_with_retry() -> UnifiedResponse:
            """Inner function with retry decorator."""
            with FlexiAILogger.correlation_context() as corr_id:
                self.logger.info(
                    "Executing chat completion request",
                    extra={
                        "provider": self.name,
                        "model": self.config.model,
                        "correlation_id": corr_id,
                    },
                )
                try:
                    response = self.chat_completion(request)
                    self.logger.info(
                        "Chat completion successful",
                        extra={
                            "provider": self.name,
                            "model": self.config.model,
                            "correlation_id": corr_id,
                        },
                    )
                    return response
                except Exception as e:
                    self.logger.error(
                        f"Chat completion failed: {str(e)}",
                        extra={
                            "provider": self.name,
                            "model": self.config.model,
                            "correlation_id": corr_id,
                            "error_type": type(e).__name__,
                        },
                    )
                    raise

        return _execute_with_retry()

    def is_healthy(self, cache_duration: int = 60) -> bool:
        """
        Check if provider is healthy (with caching).

        This method caches health check results to avoid excessive API calls.

        Args:
            cache_duration: How long to cache health check results (seconds)

        Returns:
            True if provider is healthy
        """
        current_time = time.time()

        # Return cached result if available and fresh
        if (
            self._last_health_check is not None
            and (current_time - self._last_health_check) < cache_duration
        ):
            return True

        # Perform health check
        try:
            is_healthy = self.health_check()
            if is_healthy:
                self._last_health_check = current_time
            return is_healthy
        except Exception as e:
            self.logger.warning(
                f"Health check failed: {str(e)}",
                extra={"provider": self.name, "error_type": type(e).__name__},
            )
            return False

    def get_supported_models(self) -> List[str]:
        """
        Get list of models supported by this provider.

        Returns:
            List of supported model names
        """
        # This can be overridden by subclasses to provide dynamic model lists
        return []

    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get provider information and metadata.

        Returns:
            Dictionary containing provider information
        """
        return {
            "name": self.name,
            "authenticated": self._authenticated,
            "priority": self.config.priority,
            "timeout": self.config.timeout,
            "max_retries": self.config.max_retries,
            "supported_models": self.get_supported_models(),
        }

    def __repr__(self) -> str:
        """
        Return string representation of the provider.

        Returns:
            String representation
        """
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"priority={self.config.priority}, "
            f"authenticated={self._authenticated})"
        )
