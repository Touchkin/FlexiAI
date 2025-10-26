"""Tests for sync serializers."""

from datetime import datetime, timezone
from enum import Enum

import pytest

from flexiai.sync.events import CircuitBreakerEvent, CircuitBreakerEventType
from flexiai.sync.serializers import StateSerializer


class TestEnum(Enum):
    """Test enum for serialization."""

    VALUE_A = "value_a"
    VALUE_B = "value_b"


class TestStateSerializer:
    """Tests for StateSerializer."""

    def test_serialize_dict(self):
        """Test serializing a simple dictionary."""
        data = {"key": "value", "number": 42}
        serialized = StateSerializer.serialize(data)
        assert '"key": "value"' in serialized
        assert '"number": 42' in serialized

    def test_deserialize_dict(self):
        """Test deserializing a dictionary."""
        data = {"key": "value", "number": 42}
        serialized = StateSerializer.serialize(data)
        deserialized = StateSerializer.deserialize(serialized)
        assert deserialized == data

    def test_serialize_datetime(self):
        """Test serializing datetime objects."""
        timestamp = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        data = {"timestamp": timestamp}
        serialized = StateSerializer.serialize(data)
        assert "2024-01-15T12:30:45" in serialized

    def test_deserialize_datetime(self):
        """Test deserializing datetime objects."""
        timestamp = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        data = {"timestamp": timestamp}
        serialized = StateSerializer.serialize(data)
        deserialized = StateSerializer.deserialize(serialized)

        # Compare as ISO strings to avoid timezone comparison issues
        assert deserialized["timestamp"] == timestamp.isoformat()

    def test_serialize_enum(self):
        """Test serializing enum values."""
        data = {"status": TestEnum.VALUE_A}
        serialized = StateSerializer.serialize(data)
        assert '"status": "value_a"' in serialized

    def test_serialize_nested_data(self):
        """Test serializing nested data structures."""
        data = {
            "level1": {
                "level2": {"level3": "value", "timestamp": datetime.now(timezone.utc)},
                "enum": TestEnum.VALUE_B,
            },
            "list": [1, 2, {"nested": "dict"}],
        }
        serialized = StateSerializer.serialize(data)
        deserialized = StateSerializer.deserialize(serialized)

        assert deserialized["level1"]["level2"]["level3"] == "value"
        assert deserialized["level1"]["enum"] == "value_b"
        assert deserialized["list"][2]["nested"] == "dict"

    def test_serialize_circuit_breaker_event(self):
        """Test serializing CircuitBreakerEvent."""
        timestamp = datetime.now(timezone.utc)
        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id="worker-1",
            timestamp=timestamp,
            metadata={"failure_count": 5},
        )

        serialized = StateSerializer.serialize_event(event)
        assert "__event_type__" in serialized
        assert "CircuitBreakerEvent" in serialized
        assert "test_provider" in serialized
        assert "opened" in serialized

    def test_deserialize_circuit_breaker_event(self):
        """Test deserializing CircuitBreakerEvent."""
        timestamp = datetime.now(timezone.utc)
        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id="worker-1",
            timestamp=timestamp,
            metadata={"failure_count": 5},
        )

        serialized = StateSerializer.serialize_event(event)
        deserialized = StateSerializer.deserialize_event(serialized)

        assert isinstance(deserialized, CircuitBreakerEvent)
        assert deserialized.provider_name == event.provider_name
        assert deserialized.event_type == event.event_type
        assert deserialized.worker_id == event.worker_id
        assert deserialized.metadata == event.metadata

    def test_round_trip_event_serialization(self):
        """Test round-trip event serialization."""
        timestamp = datetime.now(timezone.utc)
        original = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.HALF_OPEN,
            worker_id="worker-1",
            timestamp=timestamp,
            metadata={"success_count": 2},
        )

        # Serialize and deserialize
        serialized = StateSerializer.serialize_event(original)
        restored = StateSerializer.deserialize_event(serialized)

        assert restored.provider_name == original.provider_name
        assert restored.event_type == original.event_type
        assert restored.worker_id == original.worker_id
        assert restored.metadata == original.metadata

    def test_deserialize_invalid_event_type(self):
        """Test deserializing event with invalid type."""
        invalid_json = '{"__event_type__": "InvalidEvent", "data": {}}'

        with pytest.raises(ValueError, match="Unknown event type"):
            StateSerializer.deserialize_event(invalid_json)

    def test_deserialize_missing_event_type(self):
        """Test deserializing event without __event_type__."""
        invalid_json = '{"provider_name": "test", "worker_id": "worker-1"}'

        with pytest.raises(ValueError, match="Missing __event_type__"):
            StateSerializer.deserialize_event(invalid_json)

    def test_serialize_none_values(self):
        """Test serializing None values."""
        data = {"key": None, "number": 42}
        serialized = StateSerializer.serialize(data)
        deserialized = StateSerializer.deserialize(serialized)
        assert deserialized["key"] is None
        assert deserialized["number"] == 42

    def test_serialize_empty_dict(self):
        """Test serializing empty dictionary."""
        data = {}
        serialized = StateSerializer.serialize(data)
        deserialized = StateSerializer.deserialize(serialized)
        assert deserialized == {}

    def test_serialize_list(self):
        """Test serializing list values."""
        data = {"items": [1, 2, 3, "four"]}
        serialized = StateSerializer.serialize(data)
        deserialized = StateSerializer.deserialize(serialized)
        assert deserialized["items"] == [1, 2, 3, "four"]

    def test_serialize_special_characters(self):
        """Test serializing strings with special characters."""
        data = {"text": 'String with "quotes" and \\backslashes\\'}
        serialized = StateSerializer.serialize(data)
        deserialized = StateSerializer.deserialize(serialized)
        assert deserialized["text"] == data["text"]

    def test_serialize_unicode(self):
        """Test serializing unicode characters."""
        data = {"text": "Hello 世界 🌍"}
        serialized = StateSerializer.serialize(data)
        deserialized = StateSerializer.deserialize(serialized)
        assert deserialized["text"] == "Hello 世界 🌍"
