"""State serialization utilities for multi-worker synchronization."""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict

from flexiai.sync.events import CircuitBreakerEvent, StateUpdateEvent


class StateSerializer:
    """Serialize and deserialize circuit breaker state for Redis storage."""

    @staticmethod
    def serialize_state(state_dict: Dict[str, Any]) -> str:
        """Serialize state dictionary to JSON string.

        Args:
            state_dict: State dictionary to serialize

        Returns:
            JSON string representation

        Example:
            >>> state = {"failure_count": 5, "last_failure": datetime.now()}
            >>> json_str = StateSerializer.serialize_state(state)
        """
        # Convert datetime objects to ISO format strings
        serializable = {}
        for key, value in state_dict.items():
            if isinstance(value, datetime):
                serializable[key] = value.isoformat()
            elif isinstance(value, Enum):
                serializable[key] = value.value
            else:
                serializable[key] = value

        return json.dumps(serializable)

    @staticmethod
    def deserialize_state(json_str: str) -> Dict[str, Any]:
        """Deserialize JSON string to state dictionary.

        Args:
            json_str: JSON string to deserialize

        Returns:
            State dictionary

        Example:
            >>> state = StateSerializer.deserialize_state(json_str)
        """
        state = json.loads(json_str)

        # Convert ISO format strings back to datetime objects
        # Handle common datetime field names
        datetime_fields = [
            "last_failure_time",
            "last_success_time",
            "state_changed_at",
            "timestamp",
        ]
        for field in datetime_fields:
            if field in state and isinstance(state[field], str):
                try:
                    state[field] = datetime.fromisoformat(state[field])
                except (ValueError, TypeError):
                    pass  # Keep as string if conversion fails

        return state

    @staticmethod
    def serialize_event(event: Any) -> str:
        """Serialize an event object to JSON string.

        Args:
            event: CircuitBreakerEvent or StateUpdateEvent

        Returns:
            JSON string representation

        Example:
            >>> event = CircuitBreakerEvent(...)
            >>> json_str = StateSerializer.serialize_event(event)
        """
        if isinstance(event, (CircuitBreakerEvent, StateUpdateEvent)):
            event_dict = event.to_dict()
            # Add event class type for deserialization
            event_dict["__event_type__"] = event.__class__.__name__
            return json.dumps(event_dict)
        else:
            raise TypeError(f"Cannot serialize event of type {type(event)}")

    @staticmethod
    def deserialize_event(json_str: str) -> Any:
        """Deserialize JSON string to event object.

        Args:
            json_str: JSON string to deserialize

        Returns:
            CircuitBreakerEvent or StateUpdateEvent

        Example:
            >>> event = StateSerializer.deserialize_event(json_str)
        """
        data = json.loads(json_str)
        event_type = data.pop("__event_type__", None)

        if event_type == "CircuitBreakerEvent":
            return CircuitBreakerEvent.from_dict(data)
        elif event_type == "StateUpdateEvent":
            return StateUpdateEvent.from_dict(data)
        else:
            raise ValueError(f"Unknown event type: {event_type}")
