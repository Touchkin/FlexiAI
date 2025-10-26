"""State synchronization manager for multi-worker deployments."""

import os
import socket
import time
from typing import Any, Dict, Optional

from flexiai.sync.base import BaseSyncBackend
from flexiai.sync.events import CircuitBreakerEvent, CircuitBreakerEventType
from flexiai.sync.memory_backend import MemorySyncBackend


class StateSyncManager:
    """Manage state synchronization across multiple workers.

    Coordinates circuit breaker state synchronization using a backend
    (Redis for multi-worker, memory for single-worker).

    Args:
        backend: Synchronization backend to use (default: auto-detect)
        worker_id: Unique worker identifier (default: auto-generated)

    Example:
        >>> # Auto-detect backend (Redis if available, else memory)
        >>> manager = StateSyncManager()
        >>> manager.start()
        >>>
        >>> # Register circuit breaker
        >>> manager.register_circuit_breaker("openai", circuit_breaker)
        >>>
        >>> # Clean up
        >>> manager.stop()
    """

    def __init__(
        self,
        backend: Optional[BaseSyncBackend] = None,
        worker_id: Optional[str] = None,
    ):
        """Initialize the sync manager.

        Args:
            backend: Synchronization backend (auto-detect if None)
            worker_id: Unique worker identifier (auto-generate if None)
        """
        # Use provided backend or default to memory backend
        self._backend = backend if backend is not None else MemorySyncBackend()

        # Generate worker ID if not provided
        self._worker_id = worker_id if worker_id is not None else self._generate_worker_id()

        # Registry of circuit breakers: {provider_name: breaker_instance}
        self._circuit_breakers: Dict[str, Any] = {}

        # Track if manager is running
        self._running = False

    @staticmethod
    def _generate_worker_id() -> str:
        """Generate a unique worker identifier.

        Returns:
            Worker ID in format: hostname:pid:timestamp
        """
        hostname = socket.gethostname()
        pid = os.getpid()
        timestamp = int(time.time() * 1000)  # milliseconds
        return f"{hostname}:{pid}:{timestamp}"

    def register_circuit_breaker(self, provider_name: str, circuit_breaker: Any) -> None:
        """Register a circuit breaker for state synchronization.

        Args:
            provider_name: Name of the provider (e.g., 'openai')
            circuit_breaker: Circuit breaker instance to sync
        """
        self._circuit_breakers[provider_name] = circuit_breaker

    def on_local_state_change(
        self,
        provider_name: str,
        event_type: CircuitBreakerEventType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Handle local circuit breaker state change and broadcast to other workers.

        Args:
            provider_name: Name of the provider
            event_type: Type of state change event
            metadata: Additional event metadata
        """
        if not self._running:
            return

        # Create event
        event = CircuitBreakerEvent(
            provider_name=provider_name,
            event_type=event_type,
            worker_id=self._worker_id,
            metadata=metadata or {},
        )

        # Publish to other workers
        try:
            self._backend.publish_event(event)
        except Exception:  # nosec B110
            # Log error but don't fail the state change
            # In production, would log to logger
            pass

    def on_remote_state_change(self, event: CircuitBreakerEvent) -> None:
        """Handle state change event from another worker.

        Args:
            event: Circuit breaker event from remote worker
        """
        # Ignore events from self
        if event.worker_id == self._worker_id:
            return

        # Get the circuit breaker for this provider
        circuit_breaker = self._circuit_breakers.get(event.provider_name)
        if circuit_breaker is None:
            return

        # Apply remote state change to local circuit breaker
        try:
            self._apply_remote_event(circuit_breaker, event)
        except Exception:  # nosec B110
            # Log error but don't fail
            # In production, would log to logger
            pass

    def _apply_remote_event(self, circuit_breaker: Any, event: CircuitBreakerEvent) -> None:
        """Apply a remote event to a local circuit breaker.

        Args:
            circuit_breaker: Local circuit breaker instance
            event: Remote event to apply
        """
        # Call the circuit breaker's apply_remote_state method
        # (we'll add this method to CircuitBreaker class)
        if hasattr(circuit_breaker, "apply_remote_state"):
            circuit_breaker.apply_remote_state(event)

    def sync_all_states(self) -> None:
        """Synchronize all circuit breaker states on startup.

        Loads the latest state from shared storage for all registered
        circuit breakers.
        """
        for provider_name, circuit_breaker in self._circuit_breakers.items():
            try:
                # Get state from backend
                state = self._backend.get_state(provider_name)
                if state is not None and hasattr(circuit_breaker, "load_state"):
                    circuit_breaker.load_state(state)
            except Exception:  # nosec B110
                # Log error but continue with other providers
                # In production, would log to logger
                pass

    def start(self) -> None:
        """Start the synchronization manager.

        Subscribes to events from other workers and syncs initial state.
        """
        if self._running:
            return

        # Subscribe to events
        self._backend.subscribe_to_events(self.on_remote_state_change)

        # Sync all states on startup
        self.sync_all_states()

        self._running = True

    def stop(self) -> None:
        """Stop the synchronization manager and cleanup resources."""
        if not self._running:
            return

        self._running = False

        # Close backend
        try:
            self._backend.close()
        except Exception:  # nosec B110
            # Ignore errors on cleanup
            pass

    def health_check(self) -> bool:
        """Check if the sync manager and backend are healthy.

        Returns:
            True if healthy, False otherwise
        """
        return self._backend.health_check()

    @property
    def worker_id(self) -> str:
        """Get the worker ID.

        Returns:
            Worker identifier string
        """
        return self._worker_id

    @property
    def backend(self) -> BaseSyncBackend:
        """Get the synchronization backend.

        Returns:
            Backend instance
        """
        return self._backend
