"""
Circuit breaker state management.

This module provides state management for the circuit breaker pattern,
including state enumeration and state tracking.
"""

import time
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    """
    Circuit breaker states.

    - CLOSED: Normal operation, all requests pass through
    - OPEN: Circuit is open, requests fail fast without calling the provider
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __str__(self) -> str:
        """Return string representation of state."""
        return self.value


class CircuitBreakerState:
    """
    Tracks the state of a circuit breaker.

    This class maintains the current state, failure count, timestamps,
    and provides methods to query and update the state.

    Attributes:
        state: Current circuit state (CLOSED, OPEN, HALF_OPEN)
        failure_count: Number of consecutive failures
        success_count: Number of consecutive successes (in HALF_OPEN state)
        last_failure_time: Timestamp of last failure
        last_state_change_time: Timestamp of last state change
        opened_at: Timestamp when circuit was opened (None if not open)
    """

    def __init__(self) -> None:
        """Initialize circuit breaker state with CLOSED state."""
        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change_time: float = time.time()
        self.opened_at: Optional[float] = None

    def record_success(self) -> None:
        """
        Record a successful call.

        In CLOSED state: Resets failure count
        In HALF_OPEN state: Increments success count
        """
        if self.state == CircuitState.CLOSED:
            self.failure_count = 0
        elif self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.failure_count = 0

    def record_failure(self) -> None:
        """
        Record a failed call.

        Increments failure count and updates last failure time.
        """
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = time.time()

    def transition_to(self, new_state: CircuitState) -> None:
        """
        Transition to a new circuit state.

        Args:
            new_state: State to transition to

        Updates timestamps and resets counters appropriately.
        """
        self.state = new_state
        self.last_state_change_time = time.time()

        if new_state == CircuitState.OPEN:
            self.opened_at = self.last_state_change_time
        elif new_state == CircuitState.HALF_OPEN:
            self.success_count = 0
        elif new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.success_count = 0
            self.opened_at = None

    def time_since_opened(self) -> Optional[float]:
        """
        Get time elapsed since circuit was opened.

        Returns:
            Seconds since circuit opened, or None if not open
        """
        if self.opened_at is None:
            return None
        return time.time() - self.opened_at

    def time_since_last_failure(self) -> Optional[float]:
        """
        Get time elapsed since last failure.

        Returns:
            Seconds since last failure, or None if no failures recorded
        """
        if self.last_failure_time is None:
            return None
        return time.time() - self.last_failure_time

    def time_in_current_state(self) -> float:
        """
        Get time elapsed in current state.

        Returns:
            Seconds in current state
        """
        return time.time() - self.last_state_change_time

    def reset(self) -> None:
        """
        Reset circuit breaker state to initial CLOSED state.

        Clears all counters and timestamps.
        """
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change_time = time.time()
        self.opened_at = None

    def get_state_info(self) -> dict:
        """
        Get comprehensive state information.

        Returns:
            Dictionary containing all state information
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_state_change_time": self.last_state_change_time,
            "opened_at": self.opened_at,
            "time_since_opened": self.time_since_opened(),
            "time_since_last_failure": self.time_since_last_failure(),
            "time_in_current_state": self.time_in_current_state(),
        }

    def __repr__(self) -> str:
        """
        Return string representation of state.

        Returns:
            String representation
        """
        return (
            f"CircuitBreakerState(state={self.state.value}, "
            f"failure_count={self.failure_count}, "
            f"success_count={self.success_count})"
        )
