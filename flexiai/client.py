"""
FlexiAI main client implementation.

This module provides the main FlexiAI client class that integrates
all components (providers, circuit breaker, registry) to provide
a unified interface for GenAI API calls with automatic failover.
"""

import threading
import time
from typing import Any, Dict, List, Optional

from flexiai.exceptions import AllProvidersFailedError, CircuitBreakerOpenError
from flexiai.models import FlexiAIConfig, UnifiedRequest, UnifiedResponse
from flexiai.providers import BaseProvider, OpenAIProvider, ProviderRegistry, VertexAIProvider
from flexiai.utils.logger import FlexiAILogger


class FlexiAI:
    """
    Main FlexiAI client for unified GenAI API access.

    This client provides a unified interface to multiple GenAI providers
    with automatic failover, circuit breaker pattern, and comprehensive
    error handling.

    Attributes:
        config: FlexiAI configuration
        registry: Provider registry instance
        logger: Logger instance
        _last_used_provider: Name of the last successfully used provider
        _request_lock: Thread lock for request metadata
        _request_metadata: Dictionary storing metadata about recent requests

    Example:
        >>> from flexiai import FlexiAI
        >>> from flexiai.models import FlexiAIConfig, ProviderConfig
        >>>
        >>> config = FlexiAIConfig(
        ...     providers=[
        ...         ProviderConfig(
        ...             name="openai",
        ...             priority=1,
        ...             api_key="sk-...",
        ...             model="gpt-4"
        ...         )
        ...     ]
        ... )
        >>> client = FlexiAI(config)
        >>> response = client.chat_completion(
        ...     messages=[{"role": "user", "content": "Hello!"}]
        ... )
    """

    def __init__(self, config: Optional[FlexiAIConfig] = None) -> None:
        """
        Initialize FlexiAI client.

        Args:
            config: FlexiAI configuration. If None, providers must be registered manually.
        """
        self.config = config
        self.registry = ProviderRegistry()
        self.logger = FlexiAILogger.get_logger("flexiai.client")
        self._last_used_provider: Optional[str] = None
        self._request_lock = threading.Lock()
        self._request_metadata: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "providers_used": {},
        }

        # Register providers from config
        if config:
            self._register_providers_from_config()

        self.logger.info("FlexiAI client initialized")

    def _register_providers_from_config(self) -> None:
        """Register all providers from configuration."""
        if not self.config or not self.config.providers:
            return

        for provider_config in self.config.providers:
            # Create provider instance based on name
            provider = self._create_provider(provider_config)

            # Register with circuit breaker config
            self.registry.register(
                provider=provider,
                circuit_breaker_config=self.config.circuit_breaker,
            )

            self.logger.info(
                f"Registered provider '{provider_config.name}' "
                f"with model '{provider_config.model}' (priority: {provider_config.priority})"
            )

    def _create_provider(self, provider_config) -> BaseProvider:
        """
        Create a provider instance based on configuration.

        Args:
            provider_config: Provider configuration

        Returns:
            Provider instance

        Raises:
            ValueError: If provider type is not supported
        """
        provider_map = {
            "openai": OpenAIProvider,
            "vertexai": VertexAIProvider,
            # Add more providers as implemented:
            # "anthropic": AnthropicProvider,
        }

        provider_class = provider_map.get(provider_config.name)
        if not provider_class:
            raise ValueError(
                f"Provider '{provider_config.name}' is not supported. "
                f"Supported providers: {list(provider_map.keys())}"
            )

        return provider_class(provider_config)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> UnifiedResponse:
        """
        Execute a chat completion request with automatic failover.

        This is the main method for making chat completion requests. It will
        automatically try providers in priority order, skipping any with open
        circuit breakers, until a successful response is received.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 2.0). Uses config default if not provided.
            max_tokens: Maximum tokens to generate. Uses config default if not provided.
            **kwargs: Additional provider-specific parameters

        Returns:
            UnifiedResponse object with the completion result

        Raises:
            AllProvidersFailedError: If all providers fail or have open circuit breakers
            ValidationError: If request validation fails

        Example:
            >>> response = client.chat_completion(
            ...     messages=[
            ...         {"role": "system", "content": "You are a helpful assistant"},
            ...         {"role": "user", "content": "What is AI?"}
            ...     ],
            ...     temperature=0.7,
            ...     max_tokens=150
            ... )
            >>> print(response.content)
        """
        start_time = time.time()

        # Apply defaults from config if not provided
        if temperature is None and self.config:
            temperature = self.config.default_temperature
        if max_tokens is None and self.config:
            max_tokens = self.config.default_max_tokens

        # Create unified request
        request = UnifiedRequest(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Track attempt metadata
        attempts = []
        errors = []

        # Get providers sorted by priority
        providers = self.registry.get_providers_by_priority(only_available=True)

        if not providers:
            raise AllProvidersFailedError(
                "No providers available - all circuit breakers are OPEN",
                details={
                    "total_providers": len(self.registry),
                    "available_providers": 0,
                },
            )

        self.logger.info(
            f"Starting chat completion request with {len(providers)} available provider(s)"
        )

        # Try each provider until success
        for provider in providers:
            attempt_start = time.time()

            try:
                self.logger.debug(
                    f"Attempting request with provider '{provider.name}' "
                    f"(model: {provider.config.model})"
                )

                # Get circuit breaker for this provider
                circuit_breaker = self.registry.get_circuit_breaker(provider.name)

                # Execute through circuit breaker
                response = circuit_breaker.call(lambda: provider.chat_completion(request))

                # Success! Record metrics and return
                attempt_time = time.time() - attempt_start
                total_time = time.time() - start_time

                attempts.append(
                    {
                        "provider": provider.name,
                        "status": "success",
                        "latency": attempt_time,
                    }
                )

                self._record_successful_request(
                    provider_name=provider.name,
                    latency=total_time,
                    attempts_count=len(attempts),
                )

                self.logger.info(
                    f"Request successful with provider '{provider.name}' "
                    f"(latency: {attempt_time:.2f}s, total: {total_time:.2f}s)"
                )

                return response

            except CircuitBreakerOpenError:
                # Circuit breaker is open, skip this provider
                attempt_time = time.time() - attempt_start
                attempts.append(
                    {
                        "provider": provider.name,
                        "status": "circuit_open",
                        "latency": attempt_time,
                    }
                )

                self.logger.warning(
                    f"Circuit breaker OPEN for provider '{provider.name}', skipping"
                )
                errors.append({"provider": provider.name, "error": "Circuit breaker open"})
                continue

            except Exception as e:
                # Provider failed, circuit breaker will record the failure
                attempt_time = time.time() - attempt_start
                attempts.append(
                    {
                        "provider": provider.name,
                        "status": "error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "latency": attempt_time,
                    }
                )

                self.logger.error(
                    f"Provider '{provider.name}' failed: {type(e).__name__}: {str(e)}"
                )
                errors.append(
                    {
                        "provider": provider.name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
                continue

        # All providers failed
        total_time = time.time() - start_time
        self._record_failed_request(total_time, len(attempts))

        raise AllProvidersFailedError(
            f"All {len(providers)} provider(s) failed",
            details={
                "providers_tried": [p.name for p in providers],
                "attempts": attempts,
                "errors": errors,
                "total_time": total_time,
            },
        )

    def _record_successful_request(
        self, provider_name: str, latency: float, attempts_count: int
    ) -> None:
        """Record metrics for a successful request."""
        with self._request_lock:
            self._last_used_provider = provider_name
            self._request_metadata["total_requests"] += 1
            self._request_metadata["successful_requests"] += 1

            if provider_name not in self._request_metadata["providers_used"]:
                self._request_metadata["providers_used"][provider_name] = {
                    "requests": 0,
                    "total_latency": 0.0,
                    "avg_latency": 0.0,
                }

            provider_stats = self._request_metadata["providers_used"][provider_name]
            provider_stats["requests"] += 1
            provider_stats["total_latency"] += latency
            provider_stats["avg_latency"] = (
                provider_stats["total_latency"] / provider_stats["requests"]
            )

    def _record_failed_request(self, latency: float, attempts_count: int) -> None:
        """Record metrics for a failed request."""
        with self._request_lock:
            self._request_metadata["total_requests"] += 1
            self._request_metadata["failed_requests"] += 1

    def set_primary_provider(self, provider_name: str) -> None:
        """
        Set a provider as the primary (highest priority).

        This changes the provider's priority to 1 and adjusts other
        providers' priorities accordingly.

        Args:
            provider_name: Name of the provider to set as primary

        Raises:
            ProviderNotFoundError: If provider is not registered
        """
        # Verify provider exists (raises ProviderNotFoundError if not)
        self.registry.get_provider(provider_name)

        # Get all providers sorted by current priority
        all_providers = self.registry.get_providers_by_priority(only_available=False)

        # Update priorities
        for p in all_providers:
            if p.name == provider_name:
                p.config.priority = 1
            else:
                # Increment other providers' priorities
                p.config.priority += 1

        self.logger.info(f"Set provider '{provider_name}' as primary (priority: 1)")

    def get_provider_status(self, provider_name: Optional[str] = None) -> Dict:
        """
        Get status of a specific provider or all providers.

        Args:
            provider_name: Name of provider. If None, returns status of all providers.

        Returns:
            Dictionary with provider status information

        Raises:
            ProviderNotFoundError: If specified provider is not registered
        """
        if provider_name:
            return self.registry.get_provider_status(provider_name)
        return {"providers": self.registry.get_all_provider_status()}

    def reset_circuit_breakers(self, provider_name: Optional[str] = None) -> None:
        """
        Reset circuit breaker(s).

        Args:
            provider_name: Name of provider to reset. If None, resets all circuit breakers.
        """
        if provider_name:
            self.registry.reset_circuit_breaker(provider_name)
            self.logger.info(f"Reset circuit breaker for provider '{provider_name}'")
        else:
            self.registry.reset_all_circuit_breakers()
            self.logger.info("Reset all circuit breakers")

    def get_last_used_provider(self) -> Optional[str]:
        """
        Get the name of the last successfully used provider.

        Returns:
            Provider name or None if no successful requests yet
        """
        with self._request_lock:
            return self._last_used_provider

    def get_request_stats(self) -> Dict:
        """
        Get statistics about requests made by this client.

        Returns:
            Dictionary with request statistics
        """
        with self._request_lock:
            return {
                **self._request_metadata,
                "last_used_provider": self._last_used_provider,
            }

    def register_provider(
        self, provider: BaseProvider, circuit_breaker_config: Optional[Any] = None
    ) -> None:
        """
        Manually register a provider.

        Args:
            provider: Provider instance to register
            circuit_breaker_config: Optional circuit breaker configuration
        """
        cb_config = circuit_breaker_config or (self.config.circuit_breaker if self.config else None)
        self.registry.register(provider, circuit_breaker_config=cb_config)
        self.logger.info(f"Manually registered provider '{provider.name}'")

    def __repr__(self) -> str:
        """Return string representation of the client."""
        provider_count = len(self.registry)
        return f"FlexiAI(providers={provider_count})"

    def __enter__(self) -> "FlexiAI":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.logger.info("FlexiAI client context exiting")
