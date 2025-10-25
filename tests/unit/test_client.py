"""Tests for FlexiAI main client."""

from unittest.mock import patch

import pytest

from flexiai import FlexiAI
from flexiai.circuit_breaker import CircuitState
from flexiai.exceptions import AllProvidersFailedError, ProviderException
from flexiai.models import CircuitBreakerConfig, FlexiAIConfig, ProviderConfig, UnifiedResponse
from flexiai.providers import BaseProvider


@pytest.fixture(autouse=True)
def reset_registry():
    """Automatically reset registry before each test."""
    from flexiai.providers.registry import ProviderRegistry

    with ProviderRegistry._lock:
        ProviderRegistry._instance = None
    yield
    # Clean up after test
    with ProviderRegistry._lock:
        if ProviderRegistry._instance:
            ProviderRegistry._instance.clear()


def clear_registry():
    """Clear the singleton registry."""
    from flexiai.providers.registry import ProviderRegistry

    with ProviderRegistry._lock:
        ProviderRegistry._instance = None


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    def __init__(self, config, should_fail=False, fail_count=0):
        """Initialize mock provider."""
        super().__init__(config)
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.call_count = 0

    def chat_completion(self, request):
        """Mock chat completion."""
        self.call_count += 1

        if self.should_fail:
            raise ProviderException("Mock provider error", provider=self.name)

        if self.fail_count > 0 and self.call_count <= self.fail_count:
            raise ProviderException("Mock provider error", provider=self.name)

        return UnifiedResponse(
            content=f"Response from {self.name}",
            model=self.config.model,
            provider=self.name,
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )

    def authenticate(self):
        """Mock authenticate."""
        return True

    def validate_credentials(self):
        """Mock validate credentials."""
        return True

    def health_check(self):
        """Mock health check."""
        return True


@pytest.fixture
def provider_config():
    """Create a test provider configuration."""
    return ProviderConfig(name="openai", priority=1, api_key="test-key", model="gpt-4")


@pytest.fixture
def flexiai_config(provider_config):
    """Create a test FlexiAI configuration."""
    return FlexiAIConfig(
        providers=[provider_config],
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=["ProviderException", "APIError", "RateLimitError"],
        ),
    )


@pytest.fixture
def client(flexiai_config):
    """Create a FlexiAI client instance."""
    with patch("flexiai.client.OpenAIProvider", MockProvider):
        return FlexiAI(flexiai_config)


class TestFlexiAIInitialization:
    """Test FlexiAI client initialization."""

    def test_init_with_config(self, flexiai_config):
        """Test initialization with configuration."""
        with patch("flexiai.client.OpenAIProvider", MockProvider):
            client = FlexiAI(flexiai_config)

            assert client.config == flexiai_config
            assert len(client.registry) == 1
            assert "openai" in client.registry

    def test_init_without_config(self):
        """Test initialization without configuration."""
        client = FlexiAI()

        assert client.config is None
        assert len(client.registry) == 0

    def test_init_registers_providers(self, flexiai_config):
        """Test that providers are registered from config."""
        with patch("flexiai.client.OpenAIProvider", MockProvider):
            client = FlexiAI(flexiai_config)

            provider = client.registry.get_provider("openai")
            assert provider is not None
            assert provider.name == "openai"

    def test_init_with_circuit_breaker_config(self):
        """Test initialization with custom circuit breaker config."""
        cb_config = CircuitBreakerConfig(failure_threshold=10, recovery_timeout=120)

        config = FlexiAIConfig(
            providers=[ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4")],
            circuit_breaker=cb_config,
        )

        with patch("flexiai.client.OpenAIProvider", MockProvider):
            client = FlexiAI(config)

            cb = client.registry.get_circuit_breaker("openai")
            assert cb.config.failure_threshold == 10
            assert cb.config.recovery_timeout == 120


class TestChatCompletion:
    """Test chat completion functionality."""

    def test_successful_request(self, client):
        """Test successful chat completion request."""
        response = client.chat_completion(messages=[{"role": "user", "content": "Hello"}])

        assert isinstance(response, UnifiedResponse)
        assert response.content == "Response from openai"
        assert response.provider == "openai"

    def test_request_with_temperature(self, client):
        """Test request with custom temperature."""
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}], temperature=0.5
        )

        assert response is not None

    def test_request_with_max_tokens(self, client):
        """Test request with max tokens."""
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}], max_tokens=100
        )

        assert response is not None

    def test_last_used_provider_tracking(self, client):
        """Test that last used provider is tracked."""
        assert client.get_last_used_provider() is None

        client.chat_completion(messages=[{"role": "user", "content": "Hello"}])

        assert client.get_last_used_provider() == "openai"

    def test_request_stats_tracking(self, client):
        """Test request statistics tracking."""
        # Make a successful request
        client.chat_completion(messages=[{"role": "user", "content": "Hello"}])

        stats = client.get_request_stats()
        assert stats["total_requests"] == 1
        assert stats["successful_requests"] == 1
        assert stats["failed_requests"] == 0
        assert "openai" in stats["providers_used"]
        assert stats["providers_used"]["openai"]["requests"] == 1


class TestFailover:
    """Test failover functionality."""

    def test_failover_to_backup_provider(self):
        """Test failover when primary provider fails."""
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4"),
                ProviderConfig(name="anthropic", priority=2, api_key="key", model="claude"),
            ],
            circuit_breaker=CircuitBreakerConfig(expected_exception=["ProviderException"]),
        )

        def create_mock_provider(cfg):
            if cfg.name == "openai":
                return MockProvider(cfg, should_fail=True)
            return MockProvider(cfg, should_fail=False)

        with patch("flexiai.client.OpenAIProvider", side_effect=create_mock_provider):
            # Patch _create_provider to handle both openai and anthropic
            with patch.object(FlexiAI, "_create_provider", side_effect=create_mock_provider):
                client = FlexiAI(config)

                response = client.chat_completion(messages=[{"role": "user", "content": "Hello"}])

                assert response.provider == "anthropic"
                assert client.get_last_used_provider() == "anthropic"

    def test_all_providers_fail(self):
        """Test error when all providers fail."""
        config = FlexiAIConfig(
            providers=[ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4")]
        )

        with patch(
            "flexiai.client.OpenAIProvider",
            lambda cfg: MockProvider(cfg, should_fail=True),
        ):
            client = FlexiAI(config)

            with pytest.raises(AllProvidersFailedError) as exc_info:
                client.chat_completion(messages=[{"role": "user", "content": "Hello"}])

            assert "All 1 provider(s) failed" in str(exc_info.value)
            assert "providers_tried" in exc_info.value.details

    def test_skip_provider_with_open_circuit(self):
        """Test that providers with open circuits are skipped."""
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4"),
                ProviderConfig(name="anthropic", priority=2, api_key="key", model="claude"),
            ],
            circuit_breaker=CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60),
        )

        def create_mock_provider(cfg):
            return MockProvider(cfg, should_fail=False)

        with patch("flexiai.client.OpenAIProvider", side_effect=create_mock_provider):
            with patch.object(FlexiAI, "_create_provider", side_effect=create_mock_provider):
                client = FlexiAI(config)

                # Open the circuit for openai
                cb = client.registry.get_circuit_breaker("openai")
                cb.state.transition_to(CircuitState.OPEN)

                # Request should use anthropic
                response = client.chat_completion(messages=[{"role": "user", "content": "Hello"}])

                assert response.provider == "anthropic"


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration."""

    def test_circuit_opens_after_failures(self, client):
        """Test that circuit breaker opens after threshold failures."""
        # Configure provider to fail
        provider = client.registry.get_provider("openai")
        provider.should_fail = True

        # Make requests until circuit opens (threshold is 5 by default in CB config)
        # But we configured 3 for the provider in the fixture
        cb_config = client.registry.get_circuit_breaker("openai").config
        threshold = cb_config.failure_threshold

        for _ in range(threshold):
            try:
                client.chat_completion(messages=[{"role": "user", "content": "Hi"}])
            except AllProvidersFailedError:
                pass

        # Circuit should be open
        cb = client.registry.get_circuit_breaker("openai")
        assert cb.is_open()

    def test_failed_request_recorded_in_circuit_breaker(self, client):
        """Test that failed requests are recorded in circuit breaker."""
        provider = client.registry.get_provider("openai")
        provider.should_fail = True

        cb = client.registry.get_circuit_breaker("openai")
        initial_failures = cb.state.failure_count

        try:
            client.chat_completion(messages=[{"role": "user", "content": "Hello"}])
        except AllProvidersFailedError:
            pass

        assert cb.state.failure_count == initial_failures + 1


class TestConvenienceMethods:
    """Test convenience methods."""

    def test_set_primary_provider(self):
        """Test setting a provider as primary."""
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4"),
                ProviderConfig(name="anthropic", priority=2, api_key="key", model="claude"),
            ]
        )

        def create_mock_provider(cfg):
            return MockProvider(cfg, should_fail=False)

        with patch("flexiai.client.OpenAIProvider", side_effect=create_mock_provider):
            with patch.object(FlexiAI, "_create_provider", side_effect=create_mock_provider):
                client = FlexiAI(config)

                # Set anthropic as primary
                client.set_primary_provider("anthropic")

                anthropic = client.registry.get_provider("anthropic")
                assert anthropic.config.priority == 1

    def test_get_provider_status_specific(self, client):
        """Test getting status of specific provider."""
        status = client.get_provider_status("openai")

        assert status["name"] == "openai"
        assert "circuit_breaker" in status

    def test_get_provider_status_all(self, client):
        """Test getting status of all providers."""
        status = client.get_provider_status()

        assert "providers" in status
        assert len(status["providers"]) == 1

    def test_reset_circuit_breaker_specific(self, client):
        """Test resetting specific circuit breaker."""
        cb = client.registry.get_circuit_breaker("openai")
        cb.state.transition_to(CircuitState.OPEN)

        assert cb.is_open()

        client.reset_circuit_breakers("openai")

        assert cb.is_closed()

    def test_reset_all_circuit_breakers(self):
        """Test resetting all circuit breakers."""
        config = FlexiAIConfig(
            providers=[
                ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4"),
                ProviderConfig(name="anthropic", priority=2, api_key="key", model="claude"),
            ]
        )

        def create_mock_provider(cfg):
            return MockProvider(cfg, should_fail=False)

        with patch("flexiai.client.OpenAIProvider", side_effect=create_mock_provider):
            with patch.object(FlexiAI, "_create_provider", side_effect=create_mock_provider):
                client = FlexiAI(config)

                # Open both circuits
                client.registry.get_circuit_breaker("openai").state.transition_to(CircuitState.OPEN)
                client.registry.get_circuit_breaker("anthropic").state.transition_to(
                    CircuitState.OPEN
                )

                client.reset_circuit_breakers()

                assert client.registry.get_circuit_breaker("openai").is_closed()
                assert client.registry.get_circuit_breaker("anthropic").is_closed()

    def test_register_provider_manually(self):
        """Test manually registering a provider."""
        client = FlexiAI()

        config = ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4")
        provider = MockProvider(config)

        client.register_provider(provider)

        assert "openai" in client.registry


class TestContextManager:
    """Test context manager support."""

    def test_context_manager(self, flexiai_config):
        """Test using FlexiAI as context manager."""
        with patch("flexiai.client.OpenAIProvider", MockProvider):
            with FlexiAI(flexiai_config) as client:
                assert client is not None
                response = client.chat_completion(messages=[{"role": "user", "content": "Hello"}])
                assert response is not None


class TestErrorHandling:
    """Test error handling."""

    def test_no_providers_available(self):
        """Test error when no providers are available."""
        client = FlexiAI()

        with pytest.raises(AllProvidersFailedError) as exc_info:
            client.chat_completion(messages=[{"role": "user", "content": "Hello"}])

        assert "No providers available" in str(exc_info.value)

    def test_all_circuits_open(self, client):
        """Test error when all circuit breakers are open."""
        cb = client.registry.get_circuit_breaker("openai")
        cb.state.transition_to(CircuitState.OPEN)

        with pytest.raises(AllProvidersFailedError) as exc_info:
            client.chat_completion(messages=[{"role": "user", "content": "Hello"}])

        assert "No providers available" in str(exc_info.value)


class TestRepr:
    """Test string representation."""

    def test_repr(self, client):
        """Test __repr__ method."""
        repr_str = repr(client)

        assert "FlexiAI" in repr_str
        assert "providers=1" in repr_str
