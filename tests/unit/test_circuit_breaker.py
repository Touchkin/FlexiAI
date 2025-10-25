"""Tests for circuit breaker implementation."""

import threading
import time

import pytest

from flexiai.circuit_breaker import CircuitBreaker, CircuitBreakerState, CircuitState
from flexiai.exceptions import CircuitBreakerOpenError, ProviderException
from flexiai.models import CircuitBreakerConfig


@pytest.fixture
def circuit_config():
    """Create a test circuit breaker configuration."""
    return CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=2,  # 2 seconds for faster testing
        expected_exception=["ProviderException", "APIError"],
        half_open_max_calls=1,
    )


@pytest.fixture
def circuit_breaker(circuit_config):
    """Create a circuit breaker instance."""
    return CircuitBreaker(name="test_provider", config=circuit_config)


class TestCircuitBreakerState:
    """Test CircuitBreakerState class."""

    def test_initial_state(self):
        """Test initial state is CLOSED with zero failures."""
        state = CircuitBreakerState()
        assert state.state == CircuitState.CLOSED
        assert state.failure_count == 0
        assert state.success_count == 0
        assert state.last_failure_time is None
        assert state.opened_at is None

    def test_record_success_in_closed_state(self):
        """Test recording success in CLOSED state resets failure count."""
        state = CircuitBreakerState()
        state.failure_count = 5
        state.record_success()
        assert state.failure_count == 0
        assert state.success_count == 0  # Not incremented in CLOSED

    def test_record_success_in_half_open_state(self):
        """Test recording success in HALF_OPEN state increments success count."""
        state = CircuitBreakerState()
        state.transition_to(CircuitState.HALF_OPEN)
        state.record_success()
        assert state.success_count == 1
        assert state.failure_count == 0

    def test_record_failure(self):
        """Test recording failure increments count and sets timestamp."""
        state = CircuitBreakerState()
        state.record_failure()
        assert state.failure_count == 1
        assert state.success_count == 0
        assert state.last_failure_time is not None

    def test_transition_to_open(self):
        """Test transitioning to OPEN state sets opened_at."""
        state = CircuitBreakerState()
        state.transition_to(CircuitState.OPEN)
        assert state.state == CircuitState.OPEN
        assert state.opened_at is not None

    def test_transition_to_half_open(self):
        """Test transitioning to HALF_OPEN resets success count."""
        state = CircuitBreakerState()
        state.success_count = 5
        state.transition_to(CircuitState.HALF_OPEN)
        assert state.state == CircuitState.HALF_OPEN
        assert state.success_count == 0

    def test_transition_to_closed(self):
        """Test transitioning to CLOSED resets all counters."""
        state = CircuitBreakerState()
        state.failure_count = 5
        state.success_count = 3
        state.opened_at = time.time()
        state.transition_to(CircuitState.CLOSED)
        assert state.state == CircuitState.CLOSED
        assert state.failure_count == 0
        assert state.success_count == 0
        assert state.opened_at is None

    def test_time_since_opened(self):
        """Test calculating time since circuit opened."""
        state = CircuitBreakerState()
        state.transition_to(CircuitState.OPEN)
        time.sleep(0.1)
        time_since = state.time_since_opened()
        assert time_since is not None
        assert time_since >= 0.1

    def test_time_since_opened_when_not_open(self):
        """Test time_since_opened returns None when not opened."""
        state = CircuitBreakerState()
        assert state.time_since_opened() is None

    def test_time_since_last_failure(self):
        """Test calculating time since last failure."""
        state = CircuitBreakerState()
        state.record_failure()
        time.sleep(0.1)
        time_since = state.time_since_last_failure()
        assert time_since is not None
        assert time_since >= 0.1

    def test_time_since_last_failure_no_failures(self):
        """Test time_since_last_failure returns None with no failures."""
        state = CircuitBreakerState()
        assert state.time_since_last_failure() is None

    def test_time_in_current_state(self):
        """Test calculating time in current state."""
        state = CircuitBreakerState()
        time.sleep(0.1)
        time_in_state = state.time_in_current_state()
        assert time_in_state >= 0.1

    def test_reset(self):
        """Test resetting state clears all data."""
        state = CircuitBreakerState()
        state.transition_to(CircuitState.OPEN)
        state.failure_count = 10
        state.success_count = 5
        state.record_failure()

        state.reset()

        assert state.state == CircuitState.CLOSED
        assert state.failure_count == 0
        assert state.success_count == 0
        assert state.last_failure_time is None
        assert state.opened_at is None

    def test_get_state_info(self):
        """Test getting comprehensive state information."""
        state = CircuitBreakerState()
        state.transition_to(CircuitState.OPEN)
        state.failure_count = 3

        info = state.get_state_info()

        assert info["state"] == "open"
        assert info["failure_count"] == 3
        assert info["opened_at"] is not None
        assert "time_since_opened" in info
        assert "time_in_current_state" in info

    def test_repr(self):
        """Test string representation."""
        state = CircuitBreakerState()
        state.failure_count = 5
        repr_str = repr(state)
        assert "CircuitBreakerState" in repr_str
        assert "closed" in repr_str
        assert "5" in repr_str


class TestCircuitBreakerInitialization:
    """Test CircuitBreaker initialization."""

    def test_initialization(self, circuit_config):
        """Test circuit breaker initializes correctly."""
        cb = CircuitBreaker(name="test", config=circuit_config)
        assert cb.name == "test"
        assert cb.config == circuit_config
        assert cb.state.state == CircuitState.CLOSED
        assert cb._lock is not None

    def test_initial_state_is_closed(self, circuit_breaker):
        """Test initial state is CLOSED."""
        assert circuit_breaker.is_closed()
        assert not circuit_breaker.is_open()
        assert not circuit_breaker.is_half_open()


class TestCircuitBreakerCallSuccess:
    """Test successful calls through circuit breaker."""

    def test_call_success_in_closed_state(self, circuit_breaker):
        """Test successful call in CLOSED state."""

        def success_func():
            return "success"

        result = circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.is_closed()
        assert circuit_breaker.state.failure_count == 0

    def test_multiple_successful_calls(self, circuit_breaker):
        """Test multiple successful calls keep circuit closed."""

        def success_func():
            return "ok"

        for _ in range(10):
            result = circuit_breaker.call(success_func)
            assert result == "ok"

        assert circuit_breaker.is_closed()
        assert circuit_breaker.state.failure_count == 0


class TestCircuitBreakerFailures:
    """Test failure handling in circuit breaker."""

    def test_single_failure_keeps_circuit_closed(self, circuit_breaker):
        """Test single failure doesn't open circuit."""

        def failing_func():
            raise ProviderException("Test error", provider="test")

        with pytest.raises(ProviderException):
            circuit_breaker.call(failing_func)

        assert circuit_breaker.is_closed()
        assert circuit_breaker.state.failure_count == 1

    def test_threshold_failures_open_circuit(self, circuit_breaker):
        """Test exceeding failure threshold opens circuit."""

        def failing_func():
            raise ProviderException("Test error", provider="test")

        # Fail 3 times (threshold is 3)
        for _ in range(3):
            with pytest.raises(ProviderException):
                circuit_breaker.call(failing_func)

        assert circuit_breaker.is_open()
        assert circuit_breaker.state.failure_count == 3

    def test_open_circuit_fails_fast(self, circuit_breaker):
        """Test OPEN circuit fails fast without calling function."""
        # Open the circuit by causing 3 failures
        for _ in range(3):
            with pytest.raises(ProviderException):
                circuit_breaker.call(
                    lambda: exec('raise ProviderException("Test error", provider="test")')
                )

        assert circuit_breaker.is_open()

        # Now try to call - should fail fast with CircuitBreakerOpenError
        call_count = 0

        def should_not_be_called():
            nonlocal call_count
            call_count += 1
            return "should not execute"

        with pytest.raises(CircuitBreakerOpenError):
            circuit_breaker.call(should_not_be_called)

        assert call_count == 0  # Function was not called

    def test_success_resets_failure_count_in_closed(self, circuit_breaker):
        """Test successful call resets failure count in CLOSED state."""

        def failing_func():
            raise ProviderException("Test error", provider="test")

        def success_func():
            return "ok"

        # Record 2 failures
        for _ in range(2):
            with pytest.raises(ProviderException):
                circuit_breaker.call(failing_func)

        assert circuit_breaker.state.failure_count == 2

        # Successful call resets counter
        circuit_breaker.call(success_func)
        assert circuit_breaker.state.failure_count == 0

    def test_non_expected_exception_not_counted(self, circuit_breaker):
        """Test exceptions not in expected list are not counted."""

        def unexpected_error():
            raise ValueError("Not a provider error")

        # This should raise ValueError but not count as failure
        with pytest.raises(ValueError):
            circuit_breaker.call(unexpected_error)

        assert circuit_breaker.state.failure_count == 0
        assert circuit_breaker.is_closed()


class TestCircuitBreakerRecovery:
    """Test circuit breaker recovery (HALF_OPEN state)."""

    def test_transition_to_half_open_after_timeout(self, circuit_breaker):
        """Test circuit transitions to HALF_OPEN after recovery timeout."""
        # Open the circuit by causing 3 failures
        for _ in range(3):
            with pytest.raises(ProviderException):
                circuit_breaker.call(
                    lambda: exec('raise ProviderException("Test error", provider="test")')
                )

        assert circuit_breaker.is_open()

        # Wait for recovery timeout
        time.sleep(2.1)

        # Next call should transition to HALF_OPEN
        # We need a successful call to not reopen
        result = circuit_breaker.call(lambda: "success")
        assert result == "success"

        # Should now be closed after one successful call
        assert circuit_breaker.is_closed()

    def test_successful_call_in_half_open_closes_circuit(self, circuit_breaker):
        """Test successful call in HALF_OPEN closes circuit."""
        # Open the circuit by causing 3 failures
        for _ in range(3):
            with pytest.raises(ProviderException):
                circuit_breaker.call(
                    lambda: exec('raise ProviderException("Test error", provider="test")')
                )

        time.sleep(2.1)  # Wait for recovery timeout

        # Successful call should close circuit
        result = circuit_breaker.call(lambda: "success")
        assert result == "success"
        assert circuit_breaker.is_closed()

    def test_failure_in_half_open_reopens_circuit(self, circuit_breaker):
        """Test failure in HALF_OPEN reopens circuit."""
        # Open the circuit by causing 3 failures
        for _ in range(3):
            with pytest.raises(ProviderException):
                circuit_breaker.call(
                    lambda: exec('raise ProviderException("Test error", provider="test")')
                )

        assert circuit_breaker.is_open()
        time.sleep(2.1)  # Wait for recovery timeout

        # Circuit should be ready to test (would be HALF_OPEN)
        # But failure reopens it
        with pytest.raises(ProviderException):
            circuit_breaker.call(
                lambda: exec('raise ProviderException("Test error", provider="test")')
            )

        assert circuit_breaker.is_open()


class TestCircuitBreakerThreadSafety:
    """Test thread safety of circuit breaker."""

    def test_concurrent_calls(self, circuit_breaker):
        """Test circuit breaker handles concurrent calls safely."""
        results = []
        errors = []

        def concurrent_call(success: bool):
            try:
                if success:
                    result = circuit_breaker.call(lambda: "ok")
                    results.append(result)
                else:
                    circuit_breaker.call(lambda: 1 / 0)
            except Exception as e:
                errors.append(type(e).__name__)

        threads = []
        for i in range(20):
            t = threading.Thread(target=concurrent_call, args=(i % 2 == 0,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should complete without deadlock
        assert len(results) + len(errors) == 20

    def test_state_transitions_thread_safe(self, circuit_breaker):
        """Test state transitions are thread-safe."""
        states_observed = []

        def observe_state():
            for _ in range(10):
                state = circuit_breaker.get_state()
                states_observed.append(state)
                time.sleep(0.01)

        def cause_failures():
            for _ in range(5):
                try:
                    circuit_breaker.call(lambda: 1 / 0)
                except Exception:
                    pass
                time.sleep(0.01)

        t1 = threading.Thread(target=observe_state)
        t2 = threading.Thread(target=cause_failures)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Should have observed states
        assert len(states_observed) == 10


class TestCircuitBreakerManualControl:
    """Test manual control methods."""

    def test_reset_from_open_state(self, circuit_breaker):
        """Test resetting circuit from OPEN state."""
        # Open the circuit by causing 3 failures
        for _ in range(3):
            with pytest.raises(ProviderException):
                circuit_breaker.call(
                    lambda: exec('raise ProviderException("Test error", provider="test")')
                )

        assert circuit_breaker.is_open()

        # Reset should return to CLOSED
        circuit_breaker.reset()
        assert circuit_breaker.is_closed()
        assert circuit_breaker.state.failure_count == 0

    def test_get_state_info(self, circuit_breaker):
        """Test getting state information."""
        info = circuit_breaker.get_state_info()

        assert info["name"] == "test_provider"
        assert info["state"] == "closed"
        assert "config" in info
        assert info["config"]["failure_threshold"] == 3


class TestCircuitBreakerCallbacks:
    """Test state change callbacks."""

    def test_add_state_change_listener(self, circuit_breaker):
        """Test adding and triggering state change callback."""
        state_changes = []

        def callback(old_state, new_state):
            state_changes.append((old_state, new_state))

        circuit_breaker.add_state_change_listener(callback)

        # Open the circuit
        def failing_func():
            raise ProviderException("Test error", provider="test")

        for _ in range(3):
            with pytest.raises(ProviderException):
                circuit_breaker.call(failing_func)

        assert len(state_changes) == 1
        assert state_changes[0] == (CircuitState.CLOSED, CircuitState.OPEN)

    def test_remove_state_change_listener(self, circuit_breaker):
        """Test removing state change callback."""
        state_changes = []

        def callback(old_state, new_state):
            state_changes.append((old_state, new_state))

        circuit_breaker.add_state_change_listener(callback)
        circuit_breaker.remove_state_change_listener(callback)

        # Open the circuit
        def failing_func():
            raise ProviderException("Test error", provider="test")

        for _ in range(3):
            with pytest.raises(ProviderException):
                circuit_breaker.call(failing_func)

        # Callback should not have been triggered
        assert len(state_changes) == 0

    def test_callback_error_doesnt_break_circuit(self, circuit_breaker):
        """Test callback errors don't break circuit breaker."""

        def bad_callback(old_state, new_state):
            raise Exception("Callback error")

        circuit_breaker.add_state_change_listener(bad_callback)

        # Open the circuit - should work despite callback error
        def failing_func():
            raise ProviderException("Test error", provider="test")

        for _ in range(3):
            with pytest.raises(ProviderException):
                circuit_breaker.call(failing_func)

        assert circuit_breaker.is_open()


class TestCircuitBreakerRepr:
    """Test string representations."""

    def test_circuit_breaker_repr(self, circuit_breaker):
        """Test CircuitBreaker string representation."""
        repr_str = repr(circuit_breaker)
        assert "CircuitBreaker" in repr_str
        assert "test_provider" in repr_str
        assert "closed" in repr_str


class TestCircuitBreakerConfiguration:
    """Test different configuration scenarios."""

    def test_custom_failure_threshold(self):
        """Test custom failure threshold."""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=1,
            expected_exception=["ProviderException"],  # Add expected exception
        )
        cb = CircuitBreaker("test", config)

        def failing_func():
            raise ProviderException("Error", provider="test")

        # Should require 5 failures to open
        for _ in range(4):
            with pytest.raises(ProviderException):
                cb.call(failing_func)

        assert cb.is_closed()  # Still closed

        with pytest.raises(ProviderException):
            cb.call(failing_func)

        assert cb.is_open()  # Now open after 5th failure

    def test_half_open_max_calls(self):
        """Test half_open_max_calls configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,
            half_open_max_calls=2,  # Allow 2 test calls
        )
        cb = CircuitBreaker("test", config)

        # Open the circuit
        def failing_func():
            raise ProviderException("Error", provider="test")

        for _ in range(2):
            with pytest.raises(ProviderException):
                cb.call(failing_func)

        time.sleep(1.1)  # Wait for recovery

        # Should allow 2 successful calls before closing
        def success_func():
            return "ok"

        result1 = cb.call(success_func)
        result2 = cb.call(success_func)

        assert result1 == "ok"
        assert result2 == "ok"
        assert cb.is_closed()  # Closed after required successful calls
