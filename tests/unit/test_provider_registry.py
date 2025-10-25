"""Tests for provider registry."""

import threading
from unittest.mock import Mock

import pytest

from flexiai.circuit_breaker import CircuitState
from flexiai.exceptions import ProviderNotFoundError, ProviderRegistrationError
from flexiai.models import CircuitBreakerConfig, ProviderConfig
from flexiai.providers import BaseProvider, ProviderRegistry


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    def chat_completion(self, request):
        """Mock chat completion."""
        return Mock()

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
def registry():
    """Create a fresh registry instance for each test."""
    # Clear singleton instance and create new one
    with ProviderRegistry._lock:
        ProviderRegistry._instance = None
    reg = ProviderRegistry()
    reg.clear()
    yield reg
    # Cleanup after test
    reg.clear()


@pytest.fixture
def provider_config():
    """Create a test provider configuration."""
    return ProviderConfig(
        name="openai",
        priority=1,
        api_key="test-key",
        model="gpt-4",
        timeout=30,
        max_retries=3,
    )


@pytest.fixture
def provider(provider_config):
    """Create a test provider."""
    return MockProvider(provider_config)


class TestProviderRegistrySingleton:
    """Test singleton pattern of ProviderRegistry."""

    def test_singleton_instance(self):
        """Test that only one instance exists."""
        # Clear singleton
        ProviderRegistry._instance = None

        registry1 = ProviderRegistry()
        registry2 = ProviderRegistry()

        assert registry1 is registry2

    def test_initialization_only_once(self):
        """Test that __init__ only initializes once."""
        # Clear singleton
        ProviderRegistry._instance = None

        registry1 = ProviderRegistry()
        registry1.register(
            MockProvider(ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4"))
        )

        # Create another "instance"
        registry2 = ProviderRegistry()

        # Should have same providers
        assert "openai" in registry2


class TestProviderRegistration:
    """Test provider registration and unregistration."""

    def test_register_provider(self, registry, provider):
        """Test registering a provider."""
        registry.register(provider)

        assert "openai" in registry
        assert len(registry) == 1

    def test_register_with_circuit_breaker_config(self, registry, provider):
        """Test registering provider with custom circuit breaker config."""
        cb_config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=120)

        registry.register(provider, circuit_breaker_config=cb_config)

        cb = registry.get_circuit_breaker("openai")
        assert cb.config.failure_threshold == 5
        assert cb.config.recovery_timeout == 120

    def test_register_duplicate_provider(self, registry, provider):
        """Test registering same provider twice raises error."""
        registry.register(provider)

        with pytest.raises(ProviderRegistrationError) as exc_info:
            registry.register(provider)

        assert "already registered" in str(exc_info.value)

    def test_register_invalid_provider(self, registry):
        """Test registering non-BaseProvider raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            registry.register("not a provider")

        assert "BaseProvider" in str(exc_info.value)

    def test_unregister_provider(self, registry, provider):
        """Test unregistering a provider."""
        registry.register(provider)
        assert "openai" in registry

        registry.unregister("openai")
        assert "openai" not in registry
        assert len(registry) == 0

    def test_unregister_nonexistent_provider(self, registry):
        """Test unregistering nonexistent provider raises error."""
        with pytest.raises(ProviderNotFoundError) as exc_info:
            registry.unregister("nonexistent")

        assert "not registered" in str(exc_info.value)


class TestProviderRetrieval:
    """Test provider retrieval methods."""

    def test_get_provider(self, registry, provider):
        """Test getting a provider by name."""
        registry.register(provider)

        retrieved = registry.get_provider("openai")
        assert retrieved is provider

    def test_get_nonexistent_provider(self, registry):
        """Test getting nonexistent provider raises error."""
        with pytest.raises(ProviderNotFoundError):
            registry.get_provider("nonexistent")

    def test_get_circuit_breaker(self, registry, provider):
        """Test getting circuit breaker for a provider."""
        registry.register(provider)

        cb = registry.get_circuit_breaker("openai")
        assert cb.name == "openai"
        assert cb.is_closed()

    def test_get_circuit_breaker_nonexistent(self, registry):
        """Test getting circuit breaker for nonexistent provider."""
        with pytest.raises(ProviderNotFoundError):
            registry.get_circuit_breaker("nonexistent")

    def test_list_providers(self, registry):
        """Test listing all providers."""
        # Register multiple providers
        for i, name in enumerate(["openai", "gemini", "anthropic"]):
            config = ProviderConfig(name=name, priority=i + 1, api_key="key", model="model")
            registry.register(MockProvider(config))

        providers = registry.list_providers()
        assert len(providers) == 3
        assert "openai" in providers
        assert "gemini" in providers
        assert "anthropic" in providers

    def test_list_providers_with_metadata(self, registry):
        """Test listing providers with metadata."""
        config = ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4")
        registry.register(MockProvider(config))

        metadata = registry.list_providers(include_metadata=True)
        assert len(metadata) == 1
        assert metadata[0]["name"] == "openai"
        assert metadata[0]["model"] == "gpt-4"
        assert metadata[0]["priority"] == 1


class TestProviderPriority:
    """Test priority-based provider selection."""

    def test_get_providers_by_priority(self, registry):
        """Test providers are returned in priority order."""
        # Register with different priorities
        configs = [
            ProviderConfig(name="anthropic", priority=3, api_key="key", model="claude"),
            ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4"),
            ProviderConfig(name="gemini", priority=2, api_key="key", model="gemini-pro"),
        ]

        for config in configs:
            registry.register(MockProvider(config))

        providers = registry.get_providers_by_priority()
        assert len(providers) == 3
        assert providers[0].name == "openai"  # priority 1
        assert providers[1].name == "gemini"  # priority 2
        assert providers[2].name == "anthropic"  # priority 3

    def test_get_providers_by_priority_only_available(self, registry):
        """Test only returns providers with closed circuit breakers."""
        # Register two providers
        config1 = ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4")
        config2 = ProviderConfig(name="gemini", priority=2, api_key="key", model="gemini-pro")

        registry.register(MockProvider(config1))
        registry.register(MockProvider(config2))

        # Open the circuit for openai
        cb = registry.get_circuit_breaker("openai")
        cb.state.transition_to(CircuitState.OPEN)

        # Should only return gemini
        providers = registry.get_providers_by_priority(only_available=True)
        assert len(providers) == 1
        assert providers[0].name == "gemini"

    def test_get_providers_by_priority_include_unavailable(self, registry):
        """Test returns all providers when only_available=False."""
        # Register two providers
        config1 = ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4")
        config2 = ProviderConfig(name="gemini", priority=2, api_key="key", model="gemini-pro")

        registry.register(MockProvider(config1))
        registry.register(MockProvider(config2))

        # Open the circuit for openai
        cb = registry.get_circuit_breaker("openai")
        cb.state.transition_to(CircuitState.OPEN)

        # Should return both
        providers = registry.get_providers_by_priority(only_available=False)
        assert len(providers) == 2


class TestNextAvailableProvider:
    """Test getting next available provider."""

    def test_get_next_available_provider(self, registry):
        """Test getting next available provider."""
        # Register multiple providers
        configs = [
            ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4"),
            ProviderConfig(name="gemini", priority=2, api_key="key", model="gemini-pro"),
        ]

        for config in configs:
            registry.register(MockProvider(config))

        provider = registry.get_next_available_provider()
        assert provider.name == "openai"  # Highest priority

    def test_get_next_available_skips_open_circuits(self, registry):
        """Test skips providers with open circuit breakers."""
        # Register multiple providers
        configs = [
            ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4"),
            ProviderConfig(name="gemini", priority=2, api_key="key", model="gemini-pro"),
        ]

        for config in configs:
            registry.register(MockProvider(config))

        # Open circuit for openai
        cb = registry.get_circuit_breaker("openai")
        cb.state.transition_to(CircuitState.OPEN)

        # Should get gemini instead
        provider = registry.get_next_available_provider()
        assert provider.name == "gemini"

    def test_get_next_available_with_exclusions(self, registry):
        """Test getting next available provider with exclusions."""
        # Register multiple providers
        configs = [
            ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4"),
            ProviderConfig(name="gemini", priority=2, api_key="key", model="gemini-pro"),
            ProviderConfig(name="anthropic", priority=3, api_key="key", model="claude"),
        ]

        for config in configs:
            registry.register(MockProvider(config))

        # Exclude openai
        provider = registry.get_next_available_provider(exclude=["openai"])
        assert provider.name == "gemini"

    def test_get_next_available_none_available(self, registry):
        """Test returns None when no providers available."""
        # Register provider with open circuit
        config = ProviderConfig(name="openai", priority=1, api_key="key", model="gpt-4")
        registry.register(MockProvider(config))

        # Open circuit
        cb = registry.get_circuit_breaker("openai")
        cb.state.transition_to(CircuitState.OPEN)

        # Should return None
        provider = registry.get_next_available_provider()
        assert provider is None


class TestProviderStatus:
    """Test provider status methods."""

    def test_get_provider_status(self, registry, provider):
        """Test getting status of a provider."""
        registry.register(provider)

        status = registry.get_provider_status("openai")
        assert status["name"] == "openai"
        assert status["model"] == "gpt-4"
        assert status["priority"] == 1
        assert "circuit_breaker" in status
        assert status["circuit_breaker"]["state"] == "closed"

    def test_get_provider_status_nonexistent(self, registry):
        """Test getting status of nonexistent provider."""
        with pytest.raises(ProviderNotFoundError):
            registry.get_provider_status("nonexistent")

    def test_get_all_provider_status(self, registry):
        """Test getting status of all providers."""
        # Register multiple providers
        for i, name in enumerate(["openai", "gemini"]):
            config = ProviderConfig(name=name, priority=i + 1, api_key="key", model="model")
            registry.register(MockProvider(config))

        statuses = registry.get_all_provider_status()
        assert len(statuses) == 2
        assert any(s["name"] == "openai" for s in statuses)
        assert any(s["name"] == "gemini" for s in statuses)


class TestCircuitBreakerControl:
    """Test circuit breaker control methods."""

    def test_reset_circuit_breaker(self, registry, provider):
        """Test resetting a circuit breaker."""
        registry.register(provider)

        # Open the circuit
        cb = registry.get_circuit_breaker("openai")
        cb.state.transition_to(CircuitState.OPEN)
        assert cb.is_open()

        # Reset it
        registry.reset_circuit_breaker("openai")
        assert cb.is_closed()

    def test_reset_circuit_breaker_nonexistent(self, registry):
        """Test resetting nonexistent circuit breaker."""
        with pytest.raises(ProviderNotFoundError):
            registry.reset_circuit_breaker("nonexistent")

    def test_reset_all_circuit_breakers(self, registry):
        """Test resetting all circuit breakers."""
        # Register multiple providers
        for i, name in enumerate(["openai", "gemini"]):
            config = ProviderConfig(name=name, priority=i + 1, api_key="key", model="model")
            registry.register(MockProvider(config))

        # Open both circuits
        for name in ["openai", "gemini"]:
            cb = registry.get_circuit_breaker(name)
            cb.state.transition_to(CircuitState.OPEN)

        # Reset all
        registry.reset_all_circuit_breakers()

        # Both should be closed
        assert registry.get_circuit_breaker("openai").is_closed()
        assert registry.get_circuit_breaker("gemini").is_closed()


class TestRegistryThreadSafety:
    """Test thread safety of registry operations."""

    def test_concurrent_registration(self, registry):
        """Test concurrent provider registration."""
        errors = []

        def register_provider(name, priority):
            try:
                config = ProviderConfig(name=name, priority=priority, api_key="key", model="model")
                registry.register(MockProvider(config))
            except Exception as e:
                errors.append(e)

        # Create threads to register different providers
        threads = []
        for i, name in enumerate(["openai", "gemini", "anthropic"]):
            thread = threading.Thread(target=register_provider, args=(name, i + 1))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have all three providers, no errors
        assert len(registry) == 3
        assert len(errors) == 0

    def test_concurrent_access(self, registry):
        """Test concurrent access to providers."""
        # Register providers
        for i, name in enumerate(["openai", "gemini"]):
            config = ProviderConfig(name=name, priority=i + 1, api_key="key", model="model")
            registry.register(MockProvider(config))

        results = []
        errors = []

        def access_provider():
            try:
                provider = registry.get_next_available_provider()
                results.append(provider.name if provider else None)
            except Exception as e:
                errors.append(e)

        # Create many threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=access_provider)
            threads.append(thread)
            thread.start()

        # Wait for all
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0
        assert len(results) == 10
        # All should get openai (highest priority)
        assert all(r == "openai" for r in results)


class TestRegistryUtilities:
    """Test utility methods."""

    def test_clear(self, registry):
        """Test clearing all providers."""
        # Register providers
        for i, name in enumerate(["openai", "gemini"]):
            config = ProviderConfig(name=name, priority=i + 1, api_key="key", model="model")
            registry.register(MockProvider(config))

        assert len(registry) == 2

        registry.clear()
        assert len(registry) == 0

    def test_len(self, registry):
        """Test __len__ returns number of providers."""
        assert len(registry) == 0

        config = ProviderConfig(name="openai", priority=1, api_key="key", model="model")
        registry.register(MockProvider(config))

        assert len(registry) == 1

    def test_contains(self, registry, provider):
        """Test __contains__ checks if provider is registered."""
        assert "openai" not in registry

        registry.register(provider)
        assert "openai" in registry

    def test_repr(self, registry):
        """Test string representation."""
        config = ProviderConfig(name="openai", priority=1, api_key="key", model="model")
        registry.register(MockProvider(config))

        repr_str = repr(registry)
        assert "ProviderRegistry" in repr_str
        assert "openai" in repr_str
