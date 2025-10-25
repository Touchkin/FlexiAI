"""Tests for OpenAI provider implementation."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from openai import APIError
from openai import AuthenticationError as OpenAIAuthError
from openai import BadRequestError
from openai import RateLimitError as OpenAIRateLimitError

from flexiai.exceptions import (
    AuthenticationError,
    InvalidResponseError,
    ProviderException,
    RateLimitError,
    ValidationError,
)
from flexiai.models import Message, ProviderConfig, UnifiedRequest, UnifiedResponse
from flexiai.providers.openai_provider import OpenAIProvider


@pytest.fixture
def provider_config():
    """Create a valid OpenAI provider configuration."""
    return ProviderConfig(
        name="openai",
        api_key="sk-test123456789012345678901234567890123456789012",
        model="gpt-4",
        timeout=30.0,
        max_retries=3,
        priority=1,
    )


@pytest.fixture
def openai_provider(provider_config):
    """Create an OpenAI provider instance."""
    with patch("flexiai.providers.openai_provider.OpenAI"):
        provider = OpenAIProvider(provider_config)
        return provider


@pytest.fixture
def sample_request():
    """Create a sample unified request."""
    return UnifiedRequest(
        messages=[
            Message(role="user", content="Hello, how are you?"),
        ],
        temperature=0.7,
        max_tokens=100,
    )


@pytest.fixture
def sample_openai_response():
    """Create a sample OpenAI API response."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "I'm doing well, thank you!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
    }


class TestOpenAIProviderInitialization:
    """Test OpenAI provider initialization."""

    def test_provider_initialization_success(self, provider_config):
        """Test successful provider initialization."""
        with patch("flexiai.providers.openai_provider.OpenAI") as mock_openai:
            provider = OpenAIProvider(provider_config)

            assert provider.name == "openai"
            assert provider.config == provider_config
            assert provider.request_normalizer is not None
            assert provider.response_normalizer is not None

            # Verify OpenAI client was created with correct parameters
            mock_openai.assert_called_once_with(
                api_key=provider_config.api_key,
                timeout=provider_config.timeout,
                max_retries=0,
            )

    def test_provider_initialization_validates_credentials(self):
        """Test that initialization validates credentials."""
        config = ProviderConfig.model_construct(
            name="openai",
            api_key="",  # Invalid empty API key
            model="gpt-4",
            priority=1,
        )

        with patch("flexiai.providers.openai_provider.OpenAI"):
            with pytest.raises(ValidationError, match="API key for openai cannot be empty"):
                OpenAIProvider(config)

    def test_get_supported_models(self, openai_provider):
        """Test getting supported models list."""
        models = openai_provider.get_supported_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-4" in models
        assert "gpt-3.5-turbo" in models

    def test_get_provider_info(self, openai_provider):
        """Test getting provider information."""
        with patch("flexiai.providers.openai_provider.openai.__version__", "1.0.0"):
            info = openai_provider.get_provider_info()

            assert info["name"] == "openai"
            assert "sdk_version" in info
            assert info["sdk_version"] == "1.0.0"
            assert "supported_models" in info
            assert isinstance(info["supported_models"], list)


class TestChatCompletion:
    """Test chat completion functionality."""

    def test_chat_completion_success(self, openai_provider, sample_request, sample_openai_response):
        """Test successful chat completion."""
        # Mock the OpenAI client response
        mock_response = MagicMock()
        mock_response.model_dump.return_value = sample_openai_response
        openai_provider.client.chat.completions.create = Mock(return_value=mock_response)

        # Execute chat completion
        response = openai_provider.chat_completion(sample_request)

        # Verify response
        assert isinstance(response, UnifiedResponse)
        assert response.content == "I'm doing well, thank you!"
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        assert response.finish_reason == "stop"
        assert response.usage.total_tokens == 18

        # Verify OpenAI client was called correctly
        openai_provider.client.chat.completions.create.assert_called_once()

    def test_chat_completion_with_all_parameters(self, openai_provider):
        """Test chat completion with all optional parameters."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Test")],
            temperature=0.8,
            max_tokens=150,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            stop=["END"],
            seed=12345,
        )

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "id": "test",
            "choices": [{"message": {"content": "Response"}, "finish_reason": "stop"}],
            "model": "gpt-4",
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        }
        openai_provider.client.chat.completions.create = Mock(return_value=mock_response)

        response = openai_provider.chat_completion(request)

        assert isinstance(response, UnifiedResponse)
        assert response.content == "Response"

        # Verify all parameters were passed to OpenAI
        call_kwargs = openai_provider.client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["max_tokens"] == 150
        assert call_kwargs["top_p"] == 0.9
        assert call_kwargs["frequency_penalty"] == 0.5
        assert call_kwargs["presence_penalty"] == 0.3
        assert call_kwargs["stop"] == ["END"]
        assert call_kwargs["seed"] == 12345

    def test_chat_completion_authentication_error(self, openai_provider, sample_request):
        """Test handling of authentication errors."""
        # Mock authentication error
        openai_provider.client.chat.completions.create = Mock(
            side_effect=OpenAIAuthError(
                "Invalid API key",
                response=MagicMock(status_code=401),
                body=None,
            )
        )

        with pytest.raises(AuthenticationError, match="OpenAI authentication failed"):
            openai_provider.chat_completion(sample_request)

    def test_chat_completion_rate_limit_error(self, openai_provider, sample_request):
        """Test handling of rate limit errors."""
        # Mock rate limit error
        mock_error = OpenAIRateLimitError(
            "Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None,
        )
        mock_error.retry_after = 60
        openai_provider.client.chat.completions.create = Mock(side_effect=mock_error)

        with pytest.raises(RateLimitError, match="OpenAI rate limit exceeded"):
            openai_provider.chat_completion(sample_request)

    def test_chat_completion_bad_request_error(self, openai_provider, sample_request):
        """Test handling of bad request errors."""
        openai_provider.client.chat.completions.create = Mock(
            side_effect=BadRequestError(
                "Invalid request",
                response=MagicMock(status_code=400),
                body=None,
            )
        )

        with pytest.raises(ValidationError, match="Invalid request to OpenAI"):
            openai_provider.chat_completion(sample_request)

    def test_chat_completion_api_error(self, openai_provider, sample_request):
        """Test handling of generic API errors."""
        openai_provider.client.chat.completions.create = Mock(
            side_effect=APIError(
                "Internal server error",
                request=MagicMock(),
                body=None,
            )
        )

        with pytest.raises(ProviderException, match="OpenAI API error"):
            openai_provider.chat_completion(sample_request)

    def test_chat_completion_invalid_response(self, openai_provider, sample_request):
        """Test handling of invalid response format."""
        # Mock response with missing required fields
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {"id": "test"}  # Missing choices
        openai_provider.client.chat.completions.create = Mock(return_value=mock_response)

        with pytest.raises(InvalidResponseError):
            openai_provider.chat_completion(sample_request)

    def test_chat_completion_unexpected_error(self, openai_provider, sample_request):
        """Test handling of unexpected errors."""
        openai_provider.client.chat.completions.create = Mock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(ProviderException, match="Unexpected error"):
            openai_provider.chat_completion(sample_request)


class TestAuthentication:
    """Test authentication functionality."""

    def test_authenticate_success(self, openai_provider):
        """Test successful authentication."""
        # Mock successful models.list call
        mock_models = MagicMock()
        openai_provider.client.models.list = Mock(return_value=mock_models)

        result = openai_provider.authenticate()

        assert result is True
        assert openai_provider._authenticated is True
        openai_provider.client.models.list.assert_called_once_with(limit=1)

    def test_authenticate_failure(self, openai_provider):
        """Test authentication failure."""
        openai_provider.client.models.list = Mock(
            side_effect=OpenAIAuthError(
                "Invalid API key",
                response=MagicMock(status_code=401),
                body=None,
            )
        )

        with pytest.raises(AuthenticationError, match="OpenAI authentication failed"):
            openai_provider.authenticate()

        assert openai_provider._authenticated is False

    def test_authenticate_unexpected_error(self, openai_provider):
        """Test authentication with unexpected error."""
        openai_provider.client.models.list = Mock(side_effect=Exception("Network error"))

        with pytest.raises(AuthenticationError, match="Authentication error"):
            openai_provider.authenticate()


class TestCredentialValidation:
    """Test credential validation."""

    def test_validate_credentials_success(self, openai_provider):
        """Test successful credential validation."""
        result = openai_provider.validate_credentials()
        assert result is True

    def test_validate_credentials_invalid_api_key(self, provider_config):
        """Test validation with invalid API key."""
        config = ProviderConfig(
            name="openai",
            api_key="invalid",  # Too short
            model="gpt-4",
            priority=1,
        )

        with patch("flexiai.providers.openai_provider.OpenAI"):
            with pytest.raises(ValidationError, match="Invalid API key format"):
                OpenAIProvider(config)

    def test_validate_credentials_unsupported_model_warning(self, provider_config, caplog):
        """Test validation with unsupported model (should warn but not fail)."""
        config = ProviderConfig(
            name="openai",
            api_key="sk-test123456789012345678901234567890123456789012",
            model="gpt-future-model",  # Not in supported list
            priority=1,
        )

        with patch("flexiai.providers.openai_provider.OpenAI"):
            provider = OpenAIProvider(config)
            assert provider is not None
            # Should have logged a warning
            assert "not in known supported models list" in caplog.text


class TestHealthCheck:
    """Test health check functionality."""

    def test_health_check_success(self, openai_provider):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "gpt-4"}]
        openai_provider.client.models.list = Mock(return_value=mock_response)

        result = openai_provider.health_check()

        assert result is True
        openai_provider.client.models.list.assert_called_once_with(limit=1)

    def test_health_check_invalid_response(self, openai_provider):
        """Test health check with invalid response."""
        mock_response = MagicMock(spec=[])  # No 'data' attribute
        openai_provider.client.models.list = Mock(return_value=mock_response)

        with pytest.raises(ProviderException, match="Invalid response from OpenAI health check"):
            openai_provider.health_check()

    def test_health_check_authentication_error(self, openai_provider):
        """Test health check with authentication error."""
        openai_provider.client.models.list = Mock(
            side_effect=OpenAIAuthError(
                "Invalid API key",
                response=MagicMock(status_code=401),
                body=None,
            )
        )

        with pytest.raises(AuthenticationError, match="Health check failed - authentication error"):
            openai_provider.health_check()

    def test_health_check_generic_error(self, openai_provider):
        """Test health check with generic error."""
        openai_provider.client.models.list = Mock(side_effect=Exception("Network error"))

        with pytest.raises(ProviderException, match="Health check failed"):
            openai_provider.health_check()

    def test_is_healthy_with_caching(self, openai_provider):
        """Test is_healthy method with caching."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "gpt-4"}]
        openai_provider.client.models.list = Mock(return_value=mock_response)

        # First call should execute health check
        result1 = openai_provider.is_healthy(cache_duration=60)
        assert result1 is True
        assert openai_provider.client.models.list.call_count == 1

        # Second call within cache duration should use cached result
        result2 = openai_provider.is_healthy(cache_duration=60)
        assert result2 is True
        assert openai_provider.client.models.list.call_count == 1  # Still 1, not 2

    def test_is_healthy_cache_expiration(self, openai_provider):
        """Test is_healthy cache expiration."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "gpt-4"}]
        openai_provider.client.models.list = Mock(return_value=mock_response)

        # First call
        result1 = openai_provider.is_healthy(cache_duration=0)  # Immediate expiration
        assert result1 is True
        assert openai_provider.client.models.list.call_count == 1

        # Second call should execute again due to cache expiration
        result2 = openai_provider.is_healthy(cache_duration=0)
        assert result2 is True
        assert openai_provider.client.models.list.call_count == 2


class TestNormalizerIntegration:
    """Test integration with request and response normalizers."""

    def test_request_normalization_integration(self, openai_provider):
        """Test that requests are properly normalized before sending to OpenAI."""
        request = UnifiedRequest(
            messages=[
                Message(role="system", content="You are helpful"),
                Message(role="user", content="Hello"),
            ],
            temperature=0.5,
            max_tokens=50,
        )

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "id": "test",
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "model": "gpt-4",
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
        }
        openai_provider.client.chat.completions.create = Mock(return_value=mock_response)

        openai_provider.chat_completion(request)

        # Verify normalized request structure
        call_kwargs = openai_provider.client.chat.completions.create.call_args[1]
        assert "messages" in call_kwargs
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 50
        assert call_kwargs["model"] == "gpt-4"

    def test_response_normalization_integration(self, openai_provider, sample_request):
        """Test that responses are properly normalized from OpenAI format."""
        openai_response = {
            "id": "chatcmpl-xyz",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4-turbo",
            "system_fingerprint": "fp_123",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Normalized response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25},
        }

        mock_response = MagicMock()
        mock_response.model_dump.return_value = openai_response
        openai_provider.client.chat.completions.create = Mock(return_value=mock_response)

        response = openai_provider.chat_completion(sample_request)

        # Verify normalized response
        assert response.content == "Normalized response"
        # Model comes from config, not response (config has gpt-4)
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        assert response.finish_reason == "stop"
        assert response.usage.prompt_tokens == 15
        assert response.usage.completion_tokens == 10
        assert response.usage.total_tokens == 25
        assert response.metadata is not None
        assert response.metadata["id"] == "chatcmpl-xyz"
        assert response.metadata["system_fingerprint"] == "fp_123"
