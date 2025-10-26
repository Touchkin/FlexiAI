"""Tests for sync manager."""

import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from flexiai.sync.events import CircuitBreakerEvent, CircuitBreakerEventType
from flexiai.sync.manager import StateSyncManager
from flexiai.sync.memory_backend import MemorySyncBackend


class TestStateSyncManager:
    """Tests for StateSyncManager."""

    @pytest.fixture
    def backend(self):
        """Create a memory backend for testing."""
        return MemorySyncBackend()

    @pytest.fixture
    def manager(self, backend):
        """Create a sync manager for testing."""
        return StateSyncManager(backend=backend, worker_id="test-worker-1")

    def test_initialization(self, backend):
        """Test manager initialization."""
        manager = StateSyncManager(backend=backend, worker_id="test-worker")
        assert manager.worker_id == "test-worker"
        assert manager.backend == backend
        assert not manager._started

    def test_initialization_with_auto_worker_id(self, backend):
        """Test initialization with auto-generated worker ID."""
        manager = StateSyncManager(backend=backend)
        assert manager.worker_id is not None
        assert "-" in manager.worker_id  # Should contain separators

    def test_start_and_stop(self, manager):
        """Test starting and stopping the manager."""
        assert not manager._started

        manager.start()
        assert manager._started

        manager.stop()
        assert not manager._started

    def test_register_circuit_breaker(self, manager):
        """Test registering a circuit breaker."""
        breaker = Mock()
        breaker.name = "test_provider"

        manager.register_circuit_breaker(breaker)

        assert "test_provider" in manager._circuit_breakers
        assert manager._circuit_breakers["test_provider"] == breaker

    def test_register_multiple_circuit_breakers(self, manager):
        """Test registering multiple circuit breakers."""
        breaker1 = Mock()
        breaker1.name = "provider_1"
        breaker2 = Mock()
        breaker2.name = "provider_2"

        manager.register_circuit_breaker(breaker1)
        manager.register_circuit_breaker(breaker2)

        assert len(manager._circuit_breakers) == 2
        assert "provider_1" in manager._circuit_breakers
        assert "provider_2" in manager._circuit_breakers

    def test_on_local_state_change_publishes_event(self, manager):
        """Test that local state changes are published."""
        manager.start()

        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id=manager.worker_id,
            timestamp=datetime.now(timezone.utc),
        )

        # Mock the backend's publish_event
        with patch.object(manager.backend, "publish_event") as mock_publish:
            manager.on_local_state_change(event)
            mock_publish.assert_called_once_with(event)

    def test_on_local_state_change_updates_state_storage(self, manager):
        """Test that local state changes update state storage."""
        manager.start()

        breaker = Mock()
        breaker.name = "test_provider"
        breaker.get_state_dict.return_value = {"state": "open", "failure_count": 5}
        manager.register_circuit_breaker(breaker)

        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id=manager.worker_id,
            timestamp=datetime.now(timezone.utc),
        )

        manager.on_local_state_change(event)

        # Verify state was stored
        stored_state = manager.backend.get_state("test_provider")
        assert stored_state == {"state": "open", "failure_count": 5}

    def test_on_remote_state_change_ignores_own_events(self, manager):
        """Test that events from the same worker are ignored."""
        manager.start()

        breaker = Mock()
        breaker.name = "test_provider"
        manager.register_circuit_breaker(breaker)

        # Create event from same worker
        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id=manager.worker_id,  # Same worker ID
            timestamp=datetime.now(timezone.utc),
        )

        manager.on_remote_state_change(event)

        # Should not call apply_remote_state
        breaker.apply_remote_state.assert_not_called()

    def test_on_remote_state_change_applies_to_breaker(self, manager):
        """Test that remote events are applied to circuit breakers."""
        manager.start()

        breaker = Mock()
        breaker.name = "test_provider"
        manager.register_circuit_breaker(breaker)

        # Create event from different worker
        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id="different-worker",
            timestamp=datetime.now(timezone.utc),
        )

        manager.on_remote_state_change(event)

        # Should call apply_remote_state
        breaker.apply_remote_state.assert_called_once_with(event)

    def test_on_remote_state_change_unknown_provider(self, manager):
        """Test handling events for unknown providers."""
        manager.start()

        event = CircuitBreakerEvent(
            provider_name="unknown_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id="different-worker",
            timestamp=datetime.now(timezone.utc),
        )

        # Should not raise an error
        manager.on_remote_state_change(event)

    def test_sync_all_states(self, manager):
        """Test syncing all states to storage."""
        breaker1 = Mock()
        breaker1.name = "provider_1"
        breaker1.get_state_dict.return_value = {"state": "closed"}

        breaker2 = Mock()
        breaker2.name = "provider_2"
        breaker2.get_state_dict.return_value = {"state": "open"}

        manager.register_circuit_breaker(breaker1)
        manager.register_circuit_breaker(breaker2)

        manager.sync_all_states()

        # Verify states were stored
        assert manager.backend.get_state("provider_1") == {"state": "closed"}
        assert manager.backend.get_state("provider_2") == {"state": "open"}

    def test_load_remote_states(self, manager):
        """Test loading states from remote storage."""
        # Prepare remote states
        manager.backend.set_state("provider_1", {"state": "open", "failure_count": 3})
        manager.backend.set_state("provider_2", {"state": "closed"})

        breaker1 = Mock()
        breaker1.name = "provider_1"
        breaker2 = Mock()
        breaker2.name = "provider_2"

        manager.register_circuit_breaker(breaker1)
        manager.register_circuit_breaker(breaker2)

        manager.load_remote_states()

        # Verify load_state was called
        breaker1.load_state.assert_called_once()
        breaker2.load_state.assert_called_once()

        # Verify correct state was passed
        state_dict_1 = breaker1.load_state.call_args[0][0]
        assert state_dict_1 == {"state": "open", "failure_count": 3}

    def test_start_subscribes_to_backend(self, manager):
        """Test that start subscribes to backend events."""
        with patch.object(manager.backend, "subscribe_to_events") as mock_subscribe:
            manager.start()
            mock_subscribe.assert_called_once()

    def test_start_loads_remote_states(self, manager):
        """Test that start loads remote states."""
        with patch.object(manager, "load_remote_states") as mock_load:
            manager.start()
            mock_load.assert_called_once()

    def test_stop_unsubscribes(self, manager):
        """Test that stop properly cleans up."""
        manager.start()
        assert manager._started

        manager.stop()
        assert not manager._started

    def test_event_callback_integration(self, manager, backend):
        """Test full event flow through manager."""
        manager.start()

        breaker = Mock()
        breaker.name = "test_provider"
        manager.register_circuit_breaker(breaker)

        # Publish event directly to backend (simulates remote worker)
        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id="remote-worker",
            timestamp=datetime.now(timezone.utc),
        )
        backend.publish_event(event)

        # Give time for callback to execute
        time.sleep(0.1)

        # Verify breaker received the event
        breaker.apply_remote_state.assert_called_once()

    def test_error_handling_in_state_change(self, manager):
        """Test error handling when state change fails."""
        manager.start()

        breaker = Mock()
        breaker.name = "test_provider"
        breaker.get_state_dict.side_effect = Exception("State error")
        manager.register_circuit_breaker(breaker)

        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id=manager.worker_id,
            timestamp=datetime.now(timezone.utc),
        )

        # Should not raise, should log error
        manager.on_local_state_change(event)

    def test_error_handling_in_remote_state_apply(self, manager):
        """Test error handling when applying remote state fails."""
        manager.start()

        breaker = Mock()
        breaker.name = "test_provider"
        breaker.apply_remote_state.side_effect = Exception("Apply error")
        manager.register_circuit_breaker(breaker)

        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id="remote-worker",
            timestamp=datetime.now(timezone.utc),
        )

        # Should not raise, should log error
        manager.on_remote_state_change(event)

    def test_multiple_managers_same_backend(self, backend):
        """Test multiple managers sharing the same backend."""
        manager1 = StateSyncManager(backend=backend, worker_id="worker-1")
        manager2 = StateSyncManager(backend=backend, worker_id="worker-2")

        manager1.start()
        manager2.start()

        breaker1 = Mock()
        breaker1.name = "test_provider"
        manager1.register_circuit_breaker(breaker1)

        breaker2 = Mock()
        breaker2.name = "test_provider"
        manager2.register_circuit_breaker(breaker2)

        # Manager1 publishes event
        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id="worker-1",
            timestamp=datetime.now(timezone.utc),
        )
        manager1.on_local_state_change(event)

        time.sleep(0.1)

        # Manager2 should receive it
        breaker2.apply_remote_state.assert_called_once()

        # Manager1 should not apply its own event
        breaker1.apply_remote_state.assert_not_called()

    def test_repr(self, manager):
        """Test string representation."""
        repr_str = repr(manager)
        assert "StateSyncManager" in repr_str
        assert "test-worker-1" in repr_str
        assert "MemorySyncBackend" in repr_str
