"""Event definitions for circuit breaker state synchronization."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class CircuitBreakerEventType(str, Enum):
    """Circuit breaker event types for state synchronization."""

    OPENED = "opened"
    CLOSED = "closed"
    HALF_OPEN = "half_open"
    FAILURE = "failure"
    SUCCESS = "success"


@dataclass
class CircuitBreakerEvent:
    """Event representing a circuit breaker state change.

    Attributes:
        provider_name: Name of the provider (e.g., 'openai', 'anthropic')
        event_type: Type of event (OPENED, CLOSED, etc.)
        worker_id: Unique identifier for the worker that generated the event
        timestamp: When the event occurred
        metadata: Additional event-specific data
    """

    provider_name: str
    event_type: CircuitBreakerEventType
    worker_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization.

        Returns:
            Dictionary representation of the event
        """
        return {
            "provider_name": self.provider_name,
            "event_type": self.event_type.value,
            "worker_id": self.worker_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CircuitBreakerEvent":
        """Create event from dictionary.

        Args:
            data: Dictionary representation of the event

        Returns:
            CircuitBreakerEvent instance
        """
        return cls(
            provider_name=data["provider_name"],
            event_type=CircuitBreakerEventType(data["event_type"]),
            worker_id=data["worker_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class StateUpdateEvent:
    """Event representing a complete state update for a circuit breaker.

    Attributes:
        provider_name: Name of the provider
        state_data: Complete state dictionary (failure_count, last_failure_time, etc.)
        worker_id: Unique identifier for the worker that generated the event
        timestamp: When the state update occurred
    """

    provider_name: str
    state_data: Dict[str, Any]
    worker_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization.

        Returns:
            Dictionary representation of the event
        """
        return {
            "provider_name": self.provider_name,
            "state_data": self.state_data,
            "worker_id": self.worker_id,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateUpdateEvent":
        """Create event from dictionary.

        Args:
            data: Dictionary representation of the event

        Returns:
            StateUpdateEvent instance
        """
        return cls(
            provider_name=data["provider_name"],
            state_data=data["state_data"],
            worker_id=data["worker_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )
