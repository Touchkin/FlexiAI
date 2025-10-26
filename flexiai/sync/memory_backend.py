"""In-memory synchronization backend for single-worker deployments."""

import threading
from typing import Any, Callable, Dict, Optional

from flexiai.sync.base import BaseSyncBackend
from flexiai.sync.events import CircuitBreakerEvent


class MemorySyncBackend(BaseSyncBackend):
    """In-memory synchronization backend for single-worker deployments.

    This backend stores state in memory and provides no-op synchronization.
    Use this for development or single-worker deployments where Redis is not needed.

    Note:
        State is not shared across processes. This is only suitable for
        single-worker deployments.
    """

    def __init__(self):
        """Initialize the memory backend."""
        self._state: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._lock = threading.Lock()
        self._event_callbacks: list[Callable[[CircuitBreakerEvent], None]] = []

    def publish_event(self, event: CircuitBreakerEvent) -> None:
        """Publish an event (no-op for single worker).

        Args:
            event: The event to publish

        Note:
            In memory backend, events are only delivered to local callbacks
            since there are no other workers to notify.
        """
        # Call local callbacks immediately
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception:  # nosec B110
                # Silently ignore callback errors to prevent breaking the publisher
                pass

    def subscribe_to_events(self, callback: Callable[[CircuitBreakerEvent], None]) -> None:
        """Subscribe to events (local callbacks only).

        Args:
            callback: Function to call when an event is received
        """
        self._event_callbacks.append(callback)

    def get_state(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get the current state for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            State dictionary or None if not found
        """
        with self._lock:
            return self._state.get(provider_name)

    def set_state(self, provider_name: str, state: Dict[str, Any]) -> None:
        """Set the state for a provider.

        Args:
            provider_name: Name of the provider
            state: State dictionary to store
        """
        with self._lock:
            self._state[provider_name] = state.copy()

    def acquire_lock(self, lock_name: str, timeout: float = 10.0) -> bool:
        """Acquire a lock.

        Args:
            lock_name: Name of the lock
            timeout: Maximum time to wait for the lock (seconds)

        Returns:
            True if lock acquired, False otherwise
        """
        with self._lock:
            if lock_name not in self._locks:
                self._locks[lock_name] = threading.Lock()

        lock = self._locks[lock_name]
        return lock.acquire(timeout=timeout)

    def release_lock(self, lock_name: str) -> None:
        """Release a lock.

        Args:
            lock_name: Name of the lock to release
        """
        if lock_name in self._locks:
            try:
                self._locks[lock_name].release()
            except RuntimeError:
                # Lock was not held, ignore
                pass

    def health_check(self) -> bool:
        """Check if the backend is healthy.

        Returns:
            Always True for memory backend
        """
        return True

    def close(self) -> None:
        """Close the backend and cleanup resources."""
        with self._lock:
            self._state.clear()
            self._locks.clear()
            self._event_callbacks.clear()
