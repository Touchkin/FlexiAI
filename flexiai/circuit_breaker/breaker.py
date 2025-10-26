"""
Circuit breaker implementation.

This module provides a thread-safe circuit breaker implementation following
the circuit breaker pattern to prevent cascading failures.
"""

import threading
from typing import TYPE_CHECKING, Callable, Optional, TypeVar

from flexiai.circuit_breaker.state import CircuitBreakerState, CircuitState
from flexiai.exceptions import CircuitBreakerOpenError
from flexiai.models import CircuitBreakerConfig
from flexiai.utils.logger import FlexiAILogger

if TYPE_CHECKING:
    from flexiai.sync.events import CircuitBreakerEvent
    from flexiai.sync.manager import StateSyncManager

T = TypeVar("T")


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation.

    The circuit breaker monitors failures and prevents calls to a failing
    service, allowing it time to recover.

    States:
        - CLOSED: Normal operation, all calls pass through
        - OPEN: Too many failures, calls fail fast
        - HALF_OPEN: Testing recovery, limited calls allowed

    Attributes:
        name: Name of the circuit breaker (usually provider name)
        config: Circuit breaker configuration
        state: Current circuit breaker state
        logger: Logger instance
        _lock: Thread lock for thread-safe operations
        _state_change_callbacks: Callbacks for state change events
        _sync_manager: Optional sync manager for multi-worker coordination
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig,
        sync_manager: Optional["StateSyncManager"] = None,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name (e.g., provider name)
            config: Circuit breaker configuration
            sync_manager: Optional sync manager for multi-worker state sharing
        """
        self.name = name
        self.config = config
        self.state = CircuitBreakerState()
        self.logger = FlexiAILogger.get_logger(f"flexiai.circuit_breaker.{name}")
        self._lock = threading.Lock()
        self._state_change_callbacks: list[Callable[[CircuitState, CircuitState], None]] = []
        self._sync_manager = sync_manager

        # Register with sync manager if provided
        if self._sync_manager is not None:
            self._sync_manager.register_circuit_breaker(name, self)

        self.logger.info(
            f"Circuit breaker initialized for {name}",
            extra={
                "failure_threshold": config.failure_threshold,
                "recovery_timeout": config.recovery_timeout,
                "sync_enabled": sync_manager is not None,
            },
        )

    def call(self, func: Callable[[], T]) -> T:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Function to execute

        Returns:
            Result of the function call

        Raises:
            CircuitBreakerOpenError: If circuit is OPEN
            Exception: Any exception raised by the function
        """
        with self._lock:
            # Transition to HALF_OPEN if recovery timeout has passed
            self._check_and_transition_to_half_open()

            # Check if we should attempt the call
            if not self._should_attempt_call():
                self.logger.warning(
                    f"Circuit breaker {self.name} is OPEN, failing fast",
                    extra={"state": self.state.state.value},
                )
                raise CircuitBreakerOpenError(
                    f"Circuit breaker for {self.name} is OPEN",
                    provider=self.name,
                )

        # Execute the function (outside lock to avoid blocking)
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _should_attempt_call(self) -> bool:
        """
        Check if call should be attempted based on current state.

        Returns:
            True if call should be attempted, False otherwise
        """
        if self.state.state == CircuitState.CLOSED:
            return True

        if self.state.state == CircuitState.HALF_OPEN:
            # In HALF_OPEN, allow limited calls
            return self.state.success_count < self.config.half_open_max_calls

        # OPEN state
        return False

    def _check_and_transition_to_half_open(self) -> None:
        """
        Check if enough time has passed to transition from OPEN to HALF_OPEN.

        Must be called while holding the lock.
        """
        if self.state.state == CircuitState.OPEN:
            time_since_opened = self.state.time_since_opened()
            if time_since_opened is not None and time_since_opened >= self.config.recovery_timeout:
                self.logger.info(
                    f"Recovery timeout passed for {self.name}, transitioning to HALF_OPEN",
                    extra={"time_since_opened": time_since_opened},
                )
                self._transition_to(CircuitState.HALF_OPEN)

    def _on_success(self) -> None:
        """
        Handle successful call.

        Updates state and potentially transitions from HALF_OPEN to CLOSED.
        """
        with self._lock:
            self.state.record_success()

            if self.state.state == CircuitState.HALF_OPEN:
                # Enough successful calls in HALF_OPEN, close the circuit
                if self.state.success_count >= self.config.half_open_max_calls:
                    self.logger.info(
                        f"Circuit breaker {self.name} recovered, transitioning to CLOSED",
                        extra={"success_count": self.state.success_count},
                    )
                    self._transition_to(CircuitState.CLOSED)

    def _on_failure(self, exception: Exception) -> None:
        """
        Handle failed call.

        Updates failure count and potentially opens the circuit.

        Args:
            exception: The exception that was raised
        """
        with self._lock:
            # Check if this exception type should be counted
            exception_name = type(exception).__name__
            if not self._should_count_failure(exception_name):
                self.logger.debug(
                    f"Exception {exception_name} not counted as circuit breaker failure",
                    extra={"exception_type": exception_name},
                )
                return

            self.state.record_failure()

            self.logger.warning(
                f"Failure recorded for {self.name}",
                extra={
                    "failure_count": self.state.failure_count,
                    "threshold": self.config.failure_threshold,
                    "exception_type": exception_name,
                },
            )

            # Transition to OPEN if threshold exceeded
            if self.state.failure_count >= self.config.failure_threshold:
                if self.state.state != CircuitState.OPEN:
                    self.logger.error(
                        f"Failure threshold exceeded for {self.name}, opening circuit",
                        extra={
                            "failure_count": self.state.failure_count,
                            "threshold": self.config.failure_threshold,
                        },
                    )
                    self._transition_to(CircuitState.OPEN)
            # In HALF_OPEN, any failure reopens the circuit
            elif self.state.state == CircuitState.HALF_OPEN:
                self.logger.warning(
                    f"Failure in HALF_OPEN state for {self.name}, reopening circuit",
                    extra={"exception_type": exception_name},
                )
                self._transition_to(CircuitState.OPEN)

    def _should_count_failure(self, exception_name: str) -> bool:
        """
        Check if an exception should be counted as a failure.

        Args:
            exception_name: Name of the exception class

        Returns:
            True if exception should be counted, False otherwise
        """
        # If no expected exceptions configured, count all failures
        if not self.config.expected_exception:
            return True

        # Check if exception is in the expected list
        return exception_name in self.config.expected_exception

    def _transition_to(self, new_state: CircuitState) -> None:
        """
        Transition to a new state.

        Must be called while holding the lock.

        Args:
            new_state: State to transition to
        """
        old_state = self.state.state
        if old_state == new_state:
            return

        self.state.transition_to(new_state)

        self.logger.info(
            f"Circuit breaker {self.name} transitioned from {old_state.value} to {new_state.value}",
            extra={"old_state": old_state.value, "new_state": new_state.value},
        )

        # Broadcast state change to other workers if sync manager is available
        self._broadcast_state_change(new_state)

        # Notify callbacks
        for callback in self._state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                self.logger.error(
                    f"Error in state change callback: {str(e)}",
                    extra={
                        "callback": (
                            callback.__name__ if hasattr(callback, "__name__") else str(callback)
                        )
                    },
                )

    def _broadcast_state_change(self, new_state: CircuitState) -> None:
        """
        Broadcast state change to other workers via sync manager.

        Args:
            new_state: The new state to broadcast
        """
        if self._sync_manager is None:
            return

        # Import here to avoid circular dependency
        from flexiai.sync.events import CircuitBreakerEventType

        # Map CircuitState to CircuitBreakerEventType
        event_type_map = {
            CircuitState.OPEN: CircuitBreakerEventType.OPENED,
            CircuitState.CLOSED: CircuitBreakerEventType.CLOSED,
            CircuitState.HALF_OPEN: CircuitBreakerEventType.HALF_OPEN,
        }

        event_type = event_type_map.get(new_state)
        if event_type is None:
            return

        # Get current state info for metadata
        metadata = {
            "failure_count": self.state.failure_count,
            "success_count": self.state.success_count,
        }

        # Broadcast via sync manager
        try:
            self._sync_manager.on_local_state_change(
                provider_name=self.name, event_type=event_type, metadata=metadata
            )
        except Exception as e:  # nosec B110
            # Log but don't fail on broadcast errors
            self.logger.error(f"Failed to broadcast state change: {str(e)}")

    def reset(self) -> None:
        """
        Manually reset the circuit breaker to CLOSED state.

        This clears all failure counts and timestamps.
        """
        with self._lock:
            old_state = self.state.state
            self.state.reset()
            self.logger.info(
                f"Circuit breaker {self.name} manually reset",
                extra={"old_state": old_state.value},
            )

    def get_state(self) -> CircuitState:
        """
        Get current circuit state.

        Returns:
            Current circuit state
        """
        with self._lock:
            return self.state.state

    def is_open(self) -> bool:
        """
        Check if circuit is currently open.

        Returns:
            True if circuit is OPEN, False otherwise
        """
        with self._lock:
            return self.state.state == CircuitState.OPEN

    def is_closed(self) -> bool:
        """
        Check if circuit is currently closed.

        Returns:
            True if circuit is CLOSED, False otherwise
        """
        with self._lock:
            return self.state.state == CircuitState.CLOSED

    def is_half_open(self) -> bool:
        """
        Check if circuit is currently half-open.

        Returns:
            True if circuit is HALF_OPEN, False otherwise
        """
        with self._lock:
            return self.state.state == CircuitState.HALF_OPEN

    def get_state_info(self) -> dict:
        """
        Get comprehensive state information.

        Returns:
            Dictionary containing state information
        """
        with self._lock:
            info = self.state.get_state_info()
            info["name"] = self.name
            info["config"] = {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "half_open_max_calls": self.config.half_open_max_calls,
            }
            return info

    def add_state_change_listener(
        self, callback: Callable[[CircuitState, CircuitState], None]
    ) -> None:
        """
        Add a callback for state change events.

        Args:
            callback: Function to call on state change (old_state, new_state)
        """
        with self._lock:
            self._state_change_callbacks.append(callback)

    def remove_state_change_listener(
        self, callback: Callable[[CircuitState, CircuitState], None]
    ) -> None:
        """
        Remove a state change callback.

        Args:
            callback: Callback to remove
        """
        with self._lock:
            if callback in self._state_change_callbacks:
                self._state_change_callbacks.remove(callback)

    def apply_remote_state(self, event: "CircuitBreakerEvent") -> None:
        """
        Apply a state change event from another worker.

        Args:
            event: Circuit breaker event from remote worker
        """
        from flexiai.sync.events import CircuitBreakerEventType

        # Map event type to circuit state
        event_to_state_map = {
            CircuitBreakerEventType.OPENED: CircuitState.OPEN,
            CircuitBreakerEventType.CLOSED: CircuitState.CLOSED,
            CircuitBreakerEventType.HALF_OPEN: CircuitState.HALF_OPEN,
        }

        new_state = event_to_state_map.get(event.event_type)
        if new_state is None:
            # Not a state transition event (e.g., FAILURE or SUCCESS)
            return

        with self._lock:
            old_state = self.state.state
            if old_state == new_state:
                return  # Already in this state

            # Apply the remote state change
            self.state.transition_to(new_state)

            # Update metadata if available
            if "failure_count" in event.metadata:
                self.state.failure_count = event.metadata["failure_count"]
            if "success_count" in event.metadata:
                self.state.success_count = event.metadata["success_count"]

            self.logger.info(
                (
                    f"Applied remote state change for {self.name}: "
                    f"{old_state.value} -> {new_state.value}"
                ),
                extra={
                    "old_state": old_state.value,
                    "new_state": new_state.value,
                    "remote_worker": event.worker_id,
                },
            )

    def get_state_dict(self) -> dict:
        """
        Get state as a dictionary for serialization.

        Returns:
            Dictionary containing serializable state
        """
        with self._lock:
            return {
                "state": self.state.state.value,
                "failure_count": self.state.failure_count,
                "success_count": self.state.success_count,
                "last_failure_time": (
                    self.state.last_failure_time.isoformat()
                    if self.state.last_failure_time
                    else None
                ),
                "state_changed_at": (
                    self.state.state_changed_at.isoformat() if self.state.state_changed_at else None
                ),
            }

    def load_state(self, state_dict: dict) -> None:
        """
        Load state from a dictionary (used for sync on startup).

        Args:
            state_dict: Dictionary containing state to load
        """
        from datetime import datetime

        with self._lock:
            # Only load if the remote state is more recent
            if "state_changed_at" in state_dict and state_dict["state_changed_at"]:
                try:
                    remote_time = datetime.fromisoformat(state_dict["state_changed_at"])
                    if self.state.state_changed_at and remote_time <= self.state.state_changed_at:
                        return  # Local state is newer or same
                except (ValueError, TypeError):
                    pass  # Continue with load if timestamp parsing fails

            # Load state
            if "state" in state_dict:
                try:
                    new_state = CircuitState(state_dict["state"])
                    self.state.transition_to(new_state)
                except (ValueError, KeyError):
                    pass  # Invalid state, skip

            if "failure_count" in state_dict:
                self.state.failure_count = state_dict["failure_count"]
            if "success_count" in state_dict:
                self.state.success_count = state_dict["success_count"]

            self.logger.info(f"Loaded state from sync storage for {self.name}")

    def __repr__(self) -> str:
        """
        Return string representation.

        Returns:
            String representation
        """
        return f"CircuitBreaker(name='{self.name}', state={self.state.state.value})"
