"""Tests for memory sync backend."""

import threading
import time
from datetime import datetime, timezone

import pytest

from flexiai.sync.events import CircuitBreakerEvent, CircuitBreakerEventType
from flexiai.sync.memory_backend import MemorySyncBackend


class TestMemorySyncBackend:
    """Tests for MemorySyncBackend."""

    @pytest.fixture
    def backend(self):
        """Create a memory backend for testing."""
        return MemorySyncBackend()

    def test_initialization(self, backend):
        """Test backend initialization."""
        assert backend is not None
        assert backend.health_check()

    def test_set_and_get_state(self, backend):
        """Test setting and getting state."""
        state_data = {"state": "open", "failure_count": 5}
        backend.set_state("test_provider", state_data)

        retrieved = backend.get_state("test_provider")
        assert retrieved == state_data

    def test_get_nonexistent_state(self, backend):
        """Test getting state that doesn't exist."""
        result = backend.get_state("nonexistent_provider")
        assert result is None

    def test_publish_and_subscribe_events(self, backend):
        """Test publishing and subscribing to events."""
        received_events = []

        def callback(event):
            received_events.append(event)

        # Subscribe to events
        backend.subscribe_to_events(callback)

        # Publish event
        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.OPENED,
            worker_id="worker-1",
            timestamp=datetime.now(timezone.utc),
        )
        backend.publish_event(event)

        # Give some time for callback to execute
        time.sleep(0.1)

        # Verify callback was called
        assert len(received_events) == 1
        assert received_events[0].provider_name == "test_provider"
        assert received_events[0].event_type == CircuitBreakerEventType.OPENED

    def test_multiple_subscribers(self, backend):
        """Test multiple subscribers receiving events."""
        received_1 = []
        received_2 = []

        backend.subscribe_to_events(lambda e: received_1.append(e))
        backend.subscribe_to_events(lambda e: received_2.append(e))

        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.CLOSED,
            worker_id="worker-1",
            timestamp=datetime.now(timezone.utc),
        )
        backend.publish_event(event)

        time.sleep(0.1)

        # Both subscribers should receive the event
        assert len(received_1) == 1
        assert len(received_2) == 1

    def test_acquire_and_release_lock(self, backend):
        """Test acquiring and releasing locks."""
        lock_acquired = backend.acquire_lock("test_lock", timeout=1.0)
        assert lock_acquired

        # Try to acquire same lock (should fail)
        lock_acquired_again = backend.acquire_lock("test_lock", timeout=0.1)
        assert not lock_acquired_again

        # Release lock
        backend.release_lock("test_lock")

        # Now should be able to acquire
        lock_acquired_after_release = backend.acquire_lock("test_lock", timeout=1.0)
        assert lock_acquired_after_release

        backend.release_lock("test_lock")

    def test_lock_timeout(self, backend):
        """Test lock acquisition timeout."""
        # Acquire lock
        backend.acquire_lock("test_lock", timeout=1.0)

        # Try to acquire with timeout
        start = time.time()
        result = backend.acquire_lock("test_lock", timeout=0.5)
        elapsed = time.time() - start

        assert not result
        assert elapsed >= 0.5

        backend.release_lock("test_lock")

    def test_thread_safety_state_operations(self, backend):
        """Test thread safety of state operations."""
        results = []

        def set_state(provider, value):
            backend.set_state(provider, {"value": value})
            time.sleep(0.01)
            retrieved = backend.get_state(provider)
            results.append(retrieved["value"])

        threads = []
        for i in range(10):
            thread = threading.Thread(target=set_state, args=(f"provider_{i}", i))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All values should have been set and retrieved correctly
        assert len(results) == 10
        assert sorted(results) == list(range(10))

    def test_thread_safety_lock_operations(self, backend):
        """Test thread safety of lock operations."""
        counter = [0]
        lock_name = "counter_lock"

        def increment():
            if backend.acquire_lock(lock_name, timeout=1.0):
                try:
                    current = counter[0]
                    time.sleep(0.01)
                    counter[0] = current + 1
                finally:
                    backend.release_lock(lock_name)

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=increment)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Counter should be exactly 10 if locking works correctly
        assert counter[0] == 10

    def test_close(self, backend):
        """Test closing the backend."""
        backend.set_state("test", {"data": "value"})
        backend.close()

        # After close, operations should still work (no-op close)
        backend.set_state("test2", {"data": "value2"})
        assert backend.get_state("test2") == {"data": "value2"}

    def test_health_check(self, backend):
        """Test health check."""
        assert backend.health_check()

        # Close and check again (should still be healthy for memory backend)
        backend.close()
        assert backend.health_check()

    def test_multiple_events(self, backend):
        """Test publishing multiple events."""
        received = []
        backend.subscribe_to_events(lambda e: received.append(e))

        # Publish multiple events
        for i in range(5):
            event = CircuitBreakerEvent(
                provider_name=f"provider_{i}",
                event_type=CircuitBreakerEventType.OPENED,
                worker_id="worker-1",
                timestamp=datetime.now(timezone.utc),
            )
            backend.publish_event(event)

        time.sleep(0.1)

        assert len(received) == 5
        assert all(e.worker_id == "worker-1" for e in received)

    def test_event_with_metadata(self, backend):
        """Test publishing event with metadata."""
        received = []
        backend.subscribe_to_events(lambda e: received.append(e))

        event = CircuitBreakerEvent(
            provider_name="test_provider",
            event_type=CircuitBreakerEventType.FAILURE,
            worker_id="worker-1",
            timestamp=datetime.now(timezone.utc),
            metadata={"error": "Connection timeout", "retry_count": 3},
        )
        backend.publish_event(event)

        time.sleep(0.1)

        assert len(received) == 1
        assert received[0].metadata["error"] == "Connection timeout"
        assert received[0].metadata["retry_count"] == 3

    def test_state_overwrite(self, backend):
        """Test that setting state overwrites previous value."""
        backend.set_state("test", {"value": 1})
        assert backend.get_state("test") == {"value": 1}

        backend.set_state("test", {"value": 2})
        assert backend.get_state("test") == {"value": 2}

    def test_independent_providers(self, backend):
        """Test that different providers have independent state."""
        backend.set_state("provider_a", {"value": "a"})
        backend.set_state("provider_b", {"value": "b"})

        assert backend.get_state("provider_a") == {"value": "a"}
        assert backend.get_state("provider_b") == {"value": "b"}
