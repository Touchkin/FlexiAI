"""
Provider registry for FlexiAI.

This module provides a singleton registry to manage multiple AI providers
with priority-based selection and circuit breaker integration.
"""

import threading
from typing import TYPE_CHECKING, Dict, List, Optional

from flexiai.circuit_breaker import CircuitBreaker
from flexiai.exceptions import ProviderNotFoundError, ProviderRegistrationError
from flexiai.models import CircuitBreakerConfig
from flexiai.providers.base import BaseProvider
from flexiai.utils.logger import FlexiAILogger

if TYPE_CHECKING:
    from flexiai.sync.manager import StateSyncManager


class ProviderRegistry:
    """
    Singleton registry for managing AI providers.

    This class maintains a registry of all available providers, handles
    provider registration/unregistration, and provides methods for
    provider selection based on priority and circuit breaker state.

    The registry is thread-safe and implements the singleton pattern
    to ensure only one instance exists throughout the application.

    Attributes:
        _instance: Singleton instance
        _lock: Thread lock for thread-safe operations
        _providers: Dictionary mapping provider names to instances
        _circuit_breakers: Dictionary mapping provider names to circuit breakers
        _provider_metadata: Dictionary storing provider metadata
        logger: Logger instance
    """

    _instance: Optional["ProviderRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ProviderRegistry":
        """
        Create or return the singleton instance.

        Returns:
            The singleton ProviderRegistry instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the provider registry (only once)."""
        if self._initialized:
            return

        self._providers: Dict[str, BaseProvider] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._provider_metadata: Dict[str, Dict] = {}
        self._registry_lock = threading.Lock()
        self.logger = FlexiAILogger.get_logger("flexiai.providers.registry")
        self._initialized = True

        self.logger.info("Provider registry initialized")

    def register(
        self,
        provider: BaseProvider,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        sync_manager: Optional["StateSyncManager"] = None,
    ) -> None:
        """
        Register a provider with the registry.

        Args:
            provider: Provider instance to register
            circuit_breaker_config: Optional circuit breaker configuration
            sync_manager: Optional sync manager for multi-worker synchronization

        Raises:
            ProviderRegistrationError: If provider is invalid or already registered
            TypeError: If provider doesn't implement BaseProvider
        """
        if not isinstance(provider, BaseProvider):
            raise TypeError(f"Provider must be an instance of BaseProvider, got {type(provider)}")

        with self._registry_lock:
            if provider.name in self._providers:
                raise ProviderRegistrationError(f"Provider '{provider.name}' is already registered")

            # Create circuit breaker for this provider
            if circuit_breaker_config is None:
                circuit_breaker_config = CircuitBreakerConfig()

            circuit_breaker = CircuitBreaker(
                name=provider.name, config=circuit_breaker_config, sync_manager=sync_manager
            )

            self._providers[provider.name] = provider
            self._circuit_breakers[provider.name] = circuit_breaker
            self._provider_metadata[provider.name] = {
                "name": provider.name,
                "model": provider.config.model,
                "priority": provider.config.priority,
                "status": "registered",
            }

            self.logger.info(
                f"Registered provider '{provider.name}' with model '{provider.config.model}' "
                f"(priority: {provider.config.priority})"
            )

    def unregister(self, provider_name: str) -> None:
        """
        Unregister a provider from the registry.

        Args:
            provider_name: Name of the provider to unregister

        Raises:
            ProviderNotFoundError: If provider is not registered
        """
        with self._registry_lock:
            if provider_name not in self._providers:
                raise ProviderNotFoundError(f"Provider '{provider_name}' is not registered")

            del self._providers[provider_name]
            del self._circuit_breakers[provider_name]
            del self._provider_metadata[provider_name]

            self.logger.info(f"Unregistered provider '{provider_name}'")

    def get_provider(self, provider_name: str) -> BaseProvider:
        """
        Get a provider by name.

        Args:
            provider_name: Name of the provider

        Returns:
            The provider instance

        Raises:
            ProviderNotFoundError: If provider is not registered
        """
        with self._registry_lock:
            if provider_name not in self._providers:
                raise ProviderNotFoundError(f"Provider '{provider_name}' is not registered")
            return self._providers[provider_name]

    def get_circuit_breaker(self, provider_name: str) -> CircuitBreaker:
        """
        Get the circuit breaker for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            The circuit breaker instance

        Raises:
            ProviderNotFoundError: If provider is not registered
        """
        with self._registry_lock:
            if provider_name not in self._circuit_breakers:
                raise ProviderNotFoundError(f"Provider '{provider_name}' is not registered")
            return self._circuit_breakers[provider_name]

    def list_providers(self, include_metadata: bool = False) -> List[str]:
        """
        List all registered providers.

        Args:
            include_metadata: If True, return full metadata instead of just names

        Returns:
            List of provider names or metadata dictionaries
        """
        with self._registry_lock:
            if include_metadata:
                return list(self._provider_metadata.values())
            return list(self._providers.keys())

    def get_providers_by_priority(self, only_available: bool = True) -> List[BaseProvider]:
        """
        Get providers sorted by priority.

        Args:
            only_available: If True, only return providers with CLOSED circuit breakers

        Returns:
            List of providers sorted by priority (highest first)
        """
        with self._registry_lock:
            providers = []
            for name, provider in self._providers.items():
                if only_available:
                    circuit_breaker = self._circuit_breakers[name]
                    if circuit_breaker.is_open():
                        self.logger.debug(f"Skipping provider '{name}' - circuit breaker is OPEN")
                        continue
                providers.append(provider)

            # Sort by priority (lower number = higher priority)
            return sorted(providers, key=lambda p: p.config.priority)

    def get_next_available_provider(
        self, exclude: Optional[List[str]] = None
    ) -> Optional[BaseProvider]:
        """
        Get the next available provider based on priority and circuit breaker state.

        Args:
            exclude: Optional list of provider names to exclude

        Returns:
            The next available provider, or None if no providers available
        """
        exclude = exclude or []

        with self._registry_lock:
            for name, provider in sorted(
                self._providers.items(), key=lambda x: x[1].config.priority
            ):
                if name in exclude:
                    continue

                circuit_breaker = self._circuit_breakers[name]
                if not circuit_breaker.is_open():
                    self.logger.debug(
                        f"Selected provider '{name}' (priority: {provider.config.priority})"
                    )
                    return provider

                self.logger.debug(f"Skipping provider '{name}' - circuit breaker is OPEN")

            return None

    def get_provider_status(self, provider_name: str) -> Dict:
        """
        Get detailed status of a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Dictionary with provider status information

        Raises:
            ProviderNotFoundError: If provider is not registered
        """
        with self._registry_lock:
            if provider_name not in self._providers:
                raise ProviderNotFoundError(f"Provider '{provider_name}' is not registered")

            circuit_breaker = self._circuit_breakers[provider_name]
            metadata = self._provider_metadata[provider_name]

            return {
                **metadata,
                "circuit_breaker": circuit_breaker.get_state_info(),
            }

    def get_all_provider_status(self) -> List[Dict]:
        """
        Get status of all registered providers.

        Returns:
            List of provider status dictionaries
        """
        with self._registry_lock:
            statuses = []
            for name in self._providers.keys():
                circuit_breaker = self._circuit_breakers[name]
                metadata = self._provider_metadata[name]

                statuses.append(
                    {
                        **metadata,
                        "circuit_breaker": circuit_breaker.get_state_info(),
                    }
                )

            return statuses

    def reset_circuit_breaker(self, provider_name: str) -> None:
        """
        Reset the circuit breaker for a specific provider.

        Args:
            provider_name: Name of the provider

        Raises:
            ProviderNotFoundError: If provider is not registered
        """
        with self._registry_lock:
            if provider_name not in self._circuit_breakers:
                raise ProviderNotFoundError(f"Provider '{provider_name}' is not registered")

            self._circuit_breakers[provider_name].reset()
            self.logger.info(f"Reset circuit breaker for provider '{provider_name}'")

    def reset_all_circuit_breakers(self) -> None:
        """Reset all circuit breakers."""
        with self._registry_lock:
            for name, circuit_breaker in self._circuit_breakers.items():
                circuit_breaker.reset()
                self.logger.debug(f"Reset circuit breaker for provider '{name}'")

            self.logger.info("Reset all circuit breakers")

    def clear(self) -> None:
        """Clear all registered providers (mainly for testing)."""
        with self._registry_lock:
            self._providers.clear()
            self._circuit_breakers.clear()
            self._provider_metadata.clear()
            self.logger.info("Cleared all providers from registry")

    def __len__(self) -> int:
        """Return the number of registered providers."""
        with self._registry_lock:
            return len(self._providers)

    def __contains__(self, provider_name: str) -> bool:
        """Check if a provider is registered."""
        with self._registry_lock:
            return provider_name in self._providers

    def __repr__(self) -> str:
        """Return string representation of the registry."""
        with self._registry_lock:
            provider_list = ", ".join(self._providers.keys())
            return f"ProviderRegistry(providers=[{provider_list}])"
