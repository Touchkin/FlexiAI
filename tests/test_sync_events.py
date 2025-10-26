"""Tests for sync event classes."""

from datetime import datetime, timezone

from flexiai.sync.events import (
    CircuitBreakerEvent,
    CircuitBreakerEventType,
    StateUpdateEvent,
)


class TestCircuitBreakerEventType:
    """Tests for CircuitBreakerEventType enum."""

    def test_event_types_exist(self):
        """Test that all event types are defined."""
        assert hasattr(CircuitBreakerEventType, "OPENED")
        assert hasattr(CircuitBreakerEventType, "CLOSED")
        assert hasattr(CircuitBreakerEventType, "HALF_OPEN")
        assert hasattr(CircuitBreakerEventType, "FAILURE")
        assert hasattr(CircuitBreakerEventType, "SUCCESS")

    def test_event_type_values(self):
        """Test that event types have correct values."""
        assert CircuitBreakerEventType.OPENED.value == "opened"
        assert CircuitBreakerEventType.CLOSED.value == "closed"
        assert CircuitBreakerEventType.HALF_OPEN.value == "half_open"
        assert CircuitBreakerEventType.FAILURE.value == "failure"
        assert CircuitBreakerEventType.SUCCESS.value == "success"


class TestCircuitBreakerEvent:
    """Tests for CircuitBreakerEvent dataclass."""

    def test_create_event(self):
        """Test creating a circuit breaker event."""
        timestamp = datetime.now(timezone.utc)
        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id="worker-1",
            timestamp=timestamp,
            metadata={"reason": "too many failures"},
        )

        assert event.provider_name == "test_provider"
        assert event.event_type == CircuitBreakerEventType.OPENED
        assert event.worker_id == "worker-1"
        assert event.timestamp == timestamp
        assert event.metadata == {"reason": "too many failures"}

    def test_create_event_without_metadata(self):
        """Test creating event without metadata."""
        timestamp = datetime.now(timezone.utc)
        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.CLOSED,
            worker_id="worker-1",
            timestamp=timestamp,
        )

        assert event.metadata == {}  # Defaults to empty dict, not None

    def test_to_dict(self):
        """Test converting event to dictionary."""
        timestamp = datetime.now(timezone.utc)
        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id="worker-1",
            timestamp=timestamp,
            metadata={"failure_count": 5},
        )

        event_dict = event.to_dict()

        assert event_dict["provider_name"] == "test_provider"
        assert event_dict["event_type"] == "opened"
        assert event_dict["worker_id"] == "worker-1"
        assert event_dict["timestamp"] == timestamp.isoformat()
        assert event_dict["metadata"] == {"failure_count": 5}

    def test_to_dict_without_metadata(self):
        """Test converting event to dict without metadata."""
        timestamp = datetime.now(timezone.utc)
        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.CLOSED,
            worker_id="worker-1",
            timestamp=timestamp,
        )

        event_dict = event.to_dict()

        assert event_dict["metadata"] == {}  # Defaults to empty dict

    def test_from_dict(self):
        """Test creating event from dictionary."""
        timestamp = datetime.now(timezone.utc)
        event_dict = {
            "provider_name": "test_provider",
            "event_type": "opened",
            "worker_id": "worker-1",
            "timestamp": timestamp.isoformat(),
            "metadata": {"failure_count": 5},
        }

        event = CircuitBreakerEvent.from_dict(event_dict)

        assert event.provider_name == "test_provider"
        assert event.event_type == CircuitBreakerEventType.OPENED
        assert event.worker_id == "worker-1"
        assert abs((event.timestamp - timestamp).total_seconds()) < 0.001
        assert event.metadata == {"failure_count": 5}

    def test_from_dict_without_metadata(self):
        """Test creating event from dict without metadata."""
        timestamp = datetime.now(timezone.utc)
        event_dict = {
            "provider_name": "test_provider",
            "event_type": "closed",
            "worker_id": "worker-1",
            "timestamp": timestamp.isoformat(),
        }

        event = CircuitBreakerEvent.from_dict(event_dict)

        assert event.metadata == {}  # Defaults to empty dict

    def test_round_trip_conversion(self):
        """Test that to_dict -> from_dict preserves data."""
        timestamp = datetime.now(timezone.utc)
        original = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.HALF_OPEN,
            worker_id="worker-1",
            timestamp=timestamp,
            metadata={"test": "data"},
        )

        # Convert to dict and back
        event_dict = original.to_dict()
        restored = CircuitBreakerEvent.from_dict(event_dict)

        assert restored.provider_name == original.provider_name
        assert restored.event_type == original.event_type
        assert restored.worker_id == original.worker_id
        assert abs((restored.timestamp - original.timestamp).total_seconds()) < 0.001
        assert restored.metadata == original.metadata


class TestStateUpdateEvent:
    """Tests for StateUpdateEvent dataclass."""

    def test_create_event(self):
        """Test creating a state update event."""
        timestamp = datetime.now(timezone.utc)
        state_data = {"state": "open", "failure_count": 5}
        event = StateUpdateEvent(
            provider_name="test_provider",
            state_data=state_data,
            worker_id="worker-1",
            timestamp=timestamp,
        )

        assert event.provider_name == "test_provider"
        assert event.state_data == state_data
        assert event.worker_id == "worker-1"
        assert event.timestamp == timestamp

    def test_to_dict(self):
        """Test converting state update event to dictionary."""
        timestamp = datetime.now(timezone.utc)
        state_data = {"state": "open", "failure_count": 5}
        event = StateUpdateEvent(
            provider_name="test_provider",
            state_data=state_data,
            worker_id="worker-1",
            timestamp=timestamp,
        )

        event_dict = event.to_dict()

        assert event_dict["provider_name"] == "test_provider"
        assert event_dict["state_data"] == state_data
        assert event_dict["worker_id"] == "worker-1"
        assert event_dict["timestamp"] == timestamp.isoformat()

    def test_from_dict(self):
        """Test creating state update event from dictionary."""
        timestamp = datetime.now(timezone.utc)
        event_dict = {
            "provider_name": "test_provider",
            "state_data": {"state": "open", "failure_count": 5},
            "worker_id": "worker-1",
            "timestamp": timestamp.isoformat(),
        }

        event = StateUpdateEvent.from_dict(event_dict)

        assert event.provider_name == "test_provider"
        assert event.state_data == {"state": "open", "failure_count": 5}
        assert event.worker_id == "worker-1"
        assert abs((event.timestamp - timestamp).total_seconds()) < 0.001

    def test_round_trip_conversion(self):
        """Test that to_dict -> from_dict preserves data."""
        timestamp = datetime.now(timezone.utc)
        state_data = {"state": "half_open", "success_count": 2}
        original = StateUpdateEvent(
            provider_name="test_provider",
            state_data=state_data,
            worker_id="worker-1",
            timestamp=timestamp,
        )

        # Convert to dict and back
        event_dict = original.to_dict()
        restored = StateUpdateEvent.from_dict(event_dict)

        assert restored.provider_name == original.provider_name
        assert restored.state_data == original.state_data
        assert restored.worker_id == original.worker_id
        assert abs((restored.timestamp - original.timestamp).total_seconds()) < 0.001
