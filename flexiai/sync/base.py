"""Base classes for synchronization backends."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from flexiai.sync.events import CircuitBreakerEvent


class BaseSyncBackend(ABC):
    """Abstract base class for state synchronization backends.

    Backends are responsible for storing and synchronizing circuit breaker
    state across multiple workers.
    """

    @abstractmethod
    def publish_event(self, event: CircuitBreakerEvent) -> None:
        """Publish a circuit breaker event to all workers.

        Args:
            event: The event to publish

        Raises:
            ConnectionError: If unable to publish the event
        """
        pass

    @abstractmethod
    def subscribe_to_events(self, callback: Callable[[CircuitBreakerEvent], None]) -> None:
        """Subscribe to circuit breaker events from other workers.

        Args:
            callback: Function to call when an event is received

        Note:
            This method should run in a background thread to handle incoming events.
        """
        pass

    @abstractmethod
    def get_state(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get the current state for a provider from shared storage.

        Args:
            provider_name: Name of the provider

        Returns:
            State dictionary or None if not found

        Raises:
            ConnectionError: If unable to retrieve state
        """
        pass

    @abstractmethod
    def set_state(self, provider_name: str, state: Dict[str, Any]) -> None:
        """Set the state for a provider in shared storage.

        Args:
            provider_name: Name of the provider
            state: State dictionary to store

        Raises:
            ConnectionError: If unable to set state
        """
        pass

    @abstractmethod
    def acquire_lock(self, lock_name: str, timeout: float = 10.0) -> bool:
        """Acquire a distributed lock.

        Args:
            lock_name: Name of the lock
            timeout: Maximum time to wait for the lock (seconds)

        Returns:
            True if lock acquired, False otherwise
        """
        pass

    @abstractmethod
    def release_lock(self, lock_name: str) -> None:
        """Release a distributed lock.

        Args:
            lock_name: Name of the lock to release
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the backend is healthy and accessible.

        Returns:
            True if backend is healthy, False otherwise
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connections and cleanup resources."""
        pass
