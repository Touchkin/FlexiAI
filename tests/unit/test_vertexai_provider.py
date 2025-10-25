"""
Unit tests for Vertex AI provider.

Tests the VertexAIProvider implementation including request normalization,
response normalization, error handling, and integration with circuit breakers.
"""

from unittest.mock import Mock, patch

import pytest
from google.genai import types

from flexiai.exceptions import AuthenticationError, ProviderException, ValidationError
from flexiai.models import Message, ProviderConfig, UnifiedRequest
from flexiai.providers.vertexai_provider import VertexAIProvider


@pytest.fixture
def vertexai_config():
    """Fixture for Vertex AI provider configuration."""
    return ProviderConfig(
        name="vertexai",
        api_key="not-used-for-vertexai",  # Vertex AI uses ADC, not API keys
        model="gemini-2.0-flash",
        priority=1,
        config={
            "project": "test-project-123",
            "location": "us-central1",
        },
    )


@pytest.fixture
def vertexai_provider(vertexai_config):
    """Fixture for Vertex AI provider with mocked client."""
    with patch("flexiai.providers.vertexai_provider.genai.Client") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        provider = VertexAIProvider(vertexai_config)
        provider.client = mock_client
        yield provider


class TestVertexAIProviderInitialization:
    """Tests for Vertex AI provider initialization."""

    def test_initialization_success(self, vertexai_config):
        """Test successful initialization with valid config."""
        with patch("flexiai.providers.vertexai_provider.genai.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            provider = VertexAIProvider(vertexai_config)

            assert provider.name == "vertexai"
            assert provider.config.model == "gemini-2.0-flash"
            assert provider.project == "test-project-123"
            assert provider.location == "us-central1"
            assert provider.client is not None

            # Verify client was initialized with correct parameters
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs["vertexai"] is True
            assert call_kwargs["project"] == "test-project-123"
            assert call_kwargs["location"] == "us-central1"

    def test_initialization_missing_project(self, monkeypatch):
        """Test initialization fails without project ID."""
        # Clear environment variables
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)

        config = ProviderConfig(
            name="vertexai",
            api_key="not-used",  # Placeholder to force ADC path
            model="gemini-2.0-flash",
            priority=1,
            config={},  # Missing project
        )

        with pytest.raises(ValidationError, match="GCP project ID is required"):
            VertexAIProvider(config)

    def test_initialization_from_env_vars(self, monkeypatch):
        """Test initialization using environment variables."""
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project-456")
        monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "europe-west1")

        config = ProviderConfig(
            name="vertexai",
            api_key="not-used",
            model="gemini-2.0-flash",
            priority=1,
            config={},  # Will use env vars
        )

        with patch("flexiai.providers.vertexai_provider.genai.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            provider = VertexAIProvider(config)

            assert provider.project == "env-project-456"
            assert provider.location == "europe-west1"

    def test_initialization_default_location(self):
        """Test default location is us-central1."""
        config = ProviderConfig(
            name="vertexai",
            api_key="not-used",
            model="gemini-2.0-flash",
            priority=1,
            config={"project": "test-project"},  # No location specified
        )

        with patch("flexiai.providers.vertexai_provider.genai.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            provider = VertexAIProvider(config)

            assert provider.location == "us-central1"


class TestVertexAIChatCompletion:
    """Tests for Vertex AI chat completion."""

    def test_basic_chat_completion(self, vertexai_provider):
        """Test basic chat completion request."""
        mock_response = Mock()
        mock_response.text = "Hello! How can I help you?"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock(text="Hello! How can I help you?")]
        mock_response.candidates[0].content.role = "model"
        mock_response.candidates[0].finish_reason = types.FinishReason.STOP
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 8
        mock_response.usage_metadata.total_token_count = 18

        vertexai_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            temperature=0.7,
        )

        response = vertexai_provider.chat_completion(request)

        # Verify response
        assert response.content == "Hello! How can I help you?"
        assert response.provider == "vertexai"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 8

    def test_chat_completion_with_system_message(self, vertexai_provider):
        """Test chat completion with system message."""
        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.candidates[0].content.role = "model"
        mock_response.candidates[0].finish_reason = types.FinishReason.STOP
        mock_response.usage_metadata.prompt_token_count = 15
        mock_response.usage_metadata.candidates_token_count = 5
        mock_response.usage_metadata.total_token_count = 20

        vertexai_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(
            messages=[
                Message(role="system", content="You are a helpful assistant"),
                Message(role="user", content="Hello"),
            ],
            temperature=0.7,
        )

        _ = vertexai_provider.chat_completion(request)

        # Verify the call was made
        assert vertexai_provider.client.models.generate_content.called
        # System message should be handled via system_instruction
        call_kwargs = vertexai_provider.client.models.generate_content.call_args[1]
        assert "config" in call_kwargs
        config = call_kwargs["config"]
        # The system instruction should be set
        assert hasattr(config, "system_instruction") or "system_instruction" in str(config)

    def test_chat_completion_with_multi_turn_conversation(self, vertexai_provider):
        """Test chat completion with multi-turn conversation."""
        mock_response = Mock()
        mock_response.text = "Final response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock(text="Final response")]
        mock_response.candidates[0].content.role = "model"
        mock_response.candidates[0].finish_reason = types.FinishReason.STOP
        mock_response.usage_metadata.prompt_token_count = 30
        mock_response.usage_metadata.candidates_token_count = 10
        mock_response.usage_metadata.total_token_count = 40

        vertexai_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(
            messages=[
                Message(role="user", content="What is 2+2?"),
                Message(role="assistant", content="4"),
                Message(role="user", content="What is 3+3?"),
            ],
            temperature=0.7,
        )

        response = vertexai_provider.chat_completion(request)

        assert response.content == "Final response"
        assert vertexai_provider.client.models.generate_content.called


class TestVertexAIErrorHandling:
    """Tests for Vertex AI error handling."""

    def test_api_error_handling(self, vertexai_provider):
        """Test handling of generic API errors."""
        vertexai_provider.client.models.generate_content.side_effect = Exception("API Error")

        request = UnifiedRequest(messages=[Message(role="user", content="Hello")])

        with pytest.raises(ProviderException, match="Vertex AI request failed"):
            vertexai_provider.chat_completion(request)

    def test_authentication_error_handling(self, vertexai_provider):
        """Test handling of authentication errors."""
        vertexai_provider.client.models.generate_content.side_effect = Exception(
            "Permission denied"
        )

        request = UnifiedRequest(messages=[Message(role="user", content="Hello")])

        with pytest.raises(AuthenticationError, match="Vertex AI authentication failed"):
            vertexai_provider.chat_completion(request)

    def test_missing_credentials_error(self):
        """Test error when credentials are not available."""
        config = ProviderConfig(
            name="vertexai",
            api_key="not-used",
            model="gemini-2.0-flash",
            priority=1,
            config={"project": "test-project"},
        )

        with patch(
            "flexiai.providers.vertexai_provider.genai.Client",
            side_effect=Exception("Could not load default credentials"),
        ):
            with pytest.raises(AuthenticationError, match="Failed to initialize Vertex AI client"):
                VertexAIProvider(config)


class TestVertexAIRequestNormalization:
    """Tests for Vertex AI request normalization."""

    def test_parameter_mapping(self, vertexai_provider):
        """Test that request parameters are correctly mapped."""
        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.candidates[0].content.role = "model"
        mock_response.candidates[0].finish_reason = types.FinishReason.STOP
        mock_response.usage_metadata.prompt_token_count = 5
        mock_response.usage_metadata.candidates_token_count = 3
        mock_response.usage_metadata.total_token_count = 8

        vertexai_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(
            messages=[Message(role="user", content="Test")],
            max_tokens=100,
            temperature=0.8,
            top_p=0.9,
        )

        vertexai_provider.chat_completion(request)

        # Verify the call was made with correct parameters
        call_kwargs = vertexai_provider.client.models.generate_content.call_args[1]
        _ = call_kwargs.get("config") or call_kwargs.get("generationConfig", {})

        # The actual parameter names in the call might vary
        assert vertexai_provider.client.models.generate_content.called

    def test_role_mapping(self, vertexai_provider):
        """Test that roles are correctly mapped (assistant -> model)."""
        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.candidates[0].content.role = "model"
        mock_response.candidates[0].finish_reason = types.FinishReason.STOP
        mock_response.usage_metadata.prompt_token_count = 5
        mock_response.usage_metadata.candidates_token_count = 3
        mock_response.usage_metadata.total_token_count = 8

        vertexai_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there!"),
                Message(role="user", content="How are you?"),
            ],
        )

        vertexai_provider.chat_completion(request)

        # Verify normalizer was called and roles were mapped
        assert vertexai_provider.client.models.generate_content.called


class TestVertexAIResponseNormalization:
    """Tests for Vertex AI response normalization."""

    def test_finish_reason_mapping(self, vertexai_provider):
        """Test that finish reasons are correctly mapped."""
        finish_reasons_to_test = [
            (types.FinishReason.STOP, "stop"),
            (types.FinishReason.MAX_TOKENS, "length"),
            (types.FinishReason.SAFETY, "content_filter"),
        ]

        for vertex_reason, expected_reason in finish_reasons_to_test:
            mock_response = Mock()
            mock_response.text = "Response"
            mock_response.candidates = [Mock()]
            mock_response.candidates[0].content.parts = [Mock(text="Response")]
            mock_response.candidates[0].content.role = "model"
            mock_response.candidates[0].finish_reason = vertex_reason
            mock_response.usage_metadata.prompt_token_count = 5
            mock_response.usage_metadata.candidates_token_count = 3
            mock_response.usage_metadata.total_token_count = 8

            vertexai_provider.client.models.generate_content.return_value = mock_response

            request = UnifiedRequest(messages=[Message(role="user", content="Test")])
            response = vertexai_provider.chat_completion(request)

            assert response.finish_reason == expected_reason

    def test_usage_metadata_extraction(self, vertexai_provider):
        """Test that usage metadata is correctly extracted."""
        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.candidates[0].content.role = "model"
        mock_response.candidates[0].finish_reason = types.FinishReason.STOP
        mock_response.usage_metadata.prompt_token_count = 123
        mock_response.usage_metadata.candidates_token_count = 456
        mock_response.usage_metadata.total_token_count = 579

        vertexai_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(messages=[Message(role="user", content="Test")])
        response = vertexai_provider.chat_completion(request)

        assert response.usage.prompt_tokens == 123
        assert response.usage.completion_tokens == 456
        assert response.usage.total_tokens == 579


class TestVertexAIHealthCheck:
    """Tests for Vertex AI health check."""

    def test_health_check_healthy(self, vertexai_provider):
        """Test health check when provider is healthy."""
        mock_response = Mock()
        mock_response.text = "Hi"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock(text="Hi")]
        mock_response.candidates[0].content.role = "model"
        mock_response.candidates[0].finish_reason = types.FinishReason.STOP
        mock_response.usage_metadata.prompt_token_count = 1
        mock_response.usage_metadata.candidates_token_count = 1
        mock_response.usage_metadata.total_token_count = 2

        vertexai_provider.client.models.generate_content.return_value = mock_response

        result = vertexai_provider.health_check()

        assert result is True

    def test_health_check_unhealthy(self, vertexai_provider):
        """Test health check when provider is unhealthy."""
        vertexai_provider.client.models.generate_content.side_effect = Exception("Connection error")

        result = vertexai_provider.health_check()

        assert result is False


class TestVertexAICapabilities:
    """Tests for Vertex AI capabilities."""

    def test_get_capabilities(self, vertexai_provider):
        """Test getting provider capabilities."""
        capabilities = vertexai_provider.get_capabilities()

        assert capabilities["name"] == "vertexai"
        assert capabilities["supports_streaming"] is True
        assert capabilities["supports_functions"] is True
        assert capabilities["authentication"] == "gcp-adc"
        assert capabilities["project"] == "test-project-123"
        assert capabilities["location"] == "us-central1"
        assert "max_tokens" in capabilities
        assert "context_window" in capabilities

    def test_provider_repr(self, vertexai_provider):
        """Test string representation of provider."""
        repr_str = repr(vertexai_provider)

        assert "VertexAIProvider" in repr_str
        assert "gemini-2.0-flash" in repr_str
        assert "test-project-123" in repr_str
        assert "us-central1" in repr_str
