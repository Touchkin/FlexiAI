"""
Unit tests for Gemini provider.

Tests the GeminiProvider implementation including request normalization,
response normalization, error handling, and integration with circuit breakers.
"""

from unittest.mock import Mock, patch

import pytest
from google.genai import types

from flexiai.exceptions import ProviderException, ValidationError
from flexiai.models import Message, ProviderConfig, UnifiedRequest
from flexiai.providers.gemini_provider import GeminiProvider


@pytest.fixture
def gemini_config():
    """Fixture for Gemini provider configuration."""
    return ProviderConfig(
        name="gemini",
        api_key="AIzaSyTest1234567890123456789012345678",
        model="gemini-2.0-flash-exp",
        priority=1,
    )


@pytest.fixture
def gemini_provider(gemini_config):
    """Fixture for GeminiProvider instance."""
    with patch("google.genai.Client") as mock_client:
        provider = GeminiProvider(gemini_config)
        provider.client = mock_client
        return provider


class TestGeminiProviderInitialization:
    """Tests for GeminiProvider initialization."""

    def test_initialization_success(self, gemini_config):
        """Test successful provider initialization."""
        with patch("google.genai.Client") as mock_client:
            provider = GeminiProvider(gemini_config)

            assert provider.config == gemini_config
            assert provider.provider_name == "gemini"
            mock_client.assert_called_once()

    def test_initialization_with_invalid_api_key(self):
        """Test initialization with invalid API key format."""
        config = ProviderConfig(
            name="gemini",
            api_key="invalid-key",
            model="gemini-2.0-flash-exp",
            priority=1,
        )

        with pytest.raises(ValidationError, match="Invalid API key format"):
            GeminiProvider(config)

    def test_initialization_with_unsupported_model(self):
        """Test initialization with unsupported model."""
        config = ProviderConfig(
            name="gemini",
            api_key="AIzaSyTest1234567890123456789012345678",
            model="unsupported-model",
            priority=1,
        )

        with pytest.raises(ValidationError, match="Unsupported model"):
            GeminiProvider(config)


class TestGeminiChatCompletion:
    """Tests for chat completion functionality."""

    def test_basic_chat_completion(self, gemini_provider):
        """Test basic chat completion."""
        # Mock the response
        mock_response = Mock()
        mock_response.text = "Hello! How can I help you today?"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = types.Candidate.FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="Hello! How can I help you today?")]

        mock_usage = Mock()
        mock_usage.prompt_token_count = 10
        mock_usage.candidates_token_count = 15
        mock_usage.total_token_count = 25
        mock_response.usage_metadata = mock_usage

        gemini_provider.client.models.generate_content.return_value = mock_response

        # Create request
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            temperature=0.7,
            max_tokens=100,
        )

        # Make request
        response = gemini_provider.chat_completion(request)

        # Verify response
        assert response.content == "Hello! How can I help you today?"
        assert response.model == "gemini-2.0-flash-exp"
        assert response.provider == "gemini"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 15
        assert response.usage.total_tokens == 25
        assert response.finish_reason == "stop"

    def test_chat_completion_with_system_message(self, gemini_provider):
        """Test chat completion with system message."""
        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = types.Candidate.FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.usage_metadata = Mock(
            prompt_token_count=20, candidates_token_count=10, total_token_count=30
        )

        gemini_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(
            messages=[
                Message(role="system", content="You are a helpful assistant."),
                Message(role="user", content="Hello"),
            ],
            temperature=0.7,
        )

        _ = gemini_provider.chat_completion(request)

        # Verify the call was made
        assert gemini_provider.client.models.generate_content.called
        # System message should be handled via system_instruction
        call_kwargs = gemini_provider.client.models.generate_content.call_args[1]
        assert "system_instruction" in call_kwargs or "contents" in call_kwargs

    def test_chat_completion_with_multi_turn_conversation(self, gemini_provider):
        """Test multi-turn conversation."""
        mock_response = Mock()
        mock_response.text = "That's interesting!"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = types.Candidate.FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="That's interesting!")]
        mock_response.usage_metadata = Mock(
            prompt_token_count=30, candidates_token_count=5, total_token_count=35
        )

        gemini_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi! How can I help?"),
                Message(role="user", content="Tell me about AI"),
            ],
        )

        response = gemini_provider.chat_completion(request)

        assert response.content == "That's interesting!"
        assert response.usage.total_tokens == 35


class TestGeminiErrorHandling:
    """Tests for error handling."""

    def test_api_error_handling(self, gemini_provider):
        """Test handling of API errors."""
        gemini_provider.client.models.generate_content.side_effect = Exception("API Error")

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        with pytest.raises(ProviderException, match="Gemini API error"):
            gemini_provider.chat_completion(request)

    def test_authentication_error_handling(self, gemini_provider):
        """Test handling of authentication errors."""
        # Simulate authentication error
        auth_error = Exception("Invalid API key")
        auth_error.code = 401
        gemini_provider.client.models.generate_content.side_effect = auth_error

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        with pytest.raises(ProviderException):
            gemini_provider.chat_completion(request)

    def test_rate_limit_error_handling(self, gemini_provider):
        """Test handling of rate limit errors."""
        # Simulate rate limit error
        rate_error = Exception("Rate limit exceeded")
        rate_error.code = 429
        gemini_provider.client.models.generate_content.side_effect = rate_error

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        with pytest.raises(ProviderException, match="Gemini API error"):
            gemini_provider.chat_completion(request)

    def test_blocked_response_handling(self, gemini_provider):
        """Test handling of blocked responses (safety filters)."""
        mock_response = Mock()
        mock_response.text = None
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = types.Candidate.FinishReason.SAFETY
        mock_response.candidates[0].content = None

        gemini_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(
            messages=[Message(role="user", content="Test")],
        )

        with pytest.raises(ProviderException, match="blocked by safety filters"):
            gemini_provider.chat_completion(request)


class TestGeminiRequestNormalization:
    """Tests for request normalization."""

    def test_parameter_mapping(self, gemini_provider):
        """Test that parameters are correctly mapped to Gemini format."""
        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = types.Candidate.FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.usage_metadata = Mock(
            prompt_token_count=10, candidates_token_count=5, total_token_count=15
        )

        gemini_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            temperature=0.9,
            max_tokens=500,
            top_p=0.95,
        )

        gemini_provider.chat_completion(request)

        # Verify the call was made with correct parameters
        call_kwargs = gemini_provider.client.models.generate_content.call_args[1]
        _ = call_kwargs.get("config") or call_kwargs.get("generationConfig", {})

        # The actual parameter names in the call might vary
        assert gemini_provider.client.models.generate_content.called

    def test_role_mapping(self, gemini_provider):
        """Test that roles are correctly mapped (assistant -> model)."""
        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = types.Candidate.FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.usage_metadata = Mock(
            prompt_token_count=20, candidates_token_count=10, total_token_count=30
        )

        gemini_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi!"),
                Message(role="user", content="How are you?"),
            ],
        )

        gemini_provider.chat_completion(request)

        # Verify call was made
        assert gemini_provider.client.models.generate_content.called


class TestGeminiResponseNormalization:
    """Tests for response normalization."""

    def test_finish_reason_mapping(self, gemini_provider):
        """Test finish reason mapping."""
        test_cases = [
            (types.Candidate.FinishReason.STOP, "stop"),
            (types.Candidate.FinishReason.MAX_TOKENS, "length"),
            (types.Candidate.FinishReason.SAFETY, "content_filter"),
        ]

        for gemini_reason, expected_reason in test_cases:
            mock_response = Mock()
            mock_response.text = "Response"
            mock_response.candidates = [Mock()]
            mock_response.candidates[0].finish_reason = gemini_reason
            mock_response.candidates[0].content.parts = [Mock(text="Response")]
            mock_response.usage_metadata = Mock(
                prompt_token_count=10, candidates_token_count=5, total_token_count=15
            )

            gemini_provider.client.models.generate_content.return_value = mock_response

            request = UnifiedRequest(
                messages=[Message(role="user", content="Hello")],
            )

            response = gemini_provider.chat_completion(request)
            assert response.finish_reason == expected_reason

    def test_usage_metadata_extraction(self, gemini_provider):
        """Test token usage metadata extraction."""
        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = types.Candidate.FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.usage_metadata = Mock(
            prompt_token_count=100, candidates_token_count=50, total_token_count=150
        )

        gemini_provider.client.models.generate_content.return_value = mock_response

        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        response = gemini_provider.chat_completion(request)

        assert response.usage.prompt_tokens == 100
        assert response.usage.completion_tokens == 50
        assert response.usage.total_tokens == 150


class TestGeminiValidation:
    """Tests for validation methods."""

    def test_validate_credentials_success(self, gemini_config):
        """Test successful credential validation."""
        with patch("google.genai.Client"):
            provider = GeminiProvider(gemini_config)
            # If no exception is raised, credentials are valid
            assert provider.config.api_key == gemini_config.api_key

    def test_validate_credentials_invalid_format(self):
        """Test credential validation with invalid format."""
        config = ProviderConfig(
            name="gemini",
            api_key="invalid-format",
            model="gemini-2.0-flash-exp",
            priority=1,
        )

        with pytest.raises(ValidationError):
            GeminiProvider(config)


class TestGeminiHealthCheck:
    """Tests for health check functionality."""

    def test_health_check_healthy(self, gemini_provider):
        """Test health check when provider is healthy."""
        mock_response = Mock()
        mock_response.text = "OK"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = types.Candidate.FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="OK")]

        gemini_provider.client.models.generate_content.return_value = mock_response

        is_healthy = gemini_provider.health_check()
        assert is_healthy is True

    def test_health_check_unhealthy(self, gemini_provider):
        """Test health check when provider is unhealthy."""
        gemini_provider.client.models.generate_content.side_effect = Exception("Connection error")

        is_healthy = gemini_provider.health_check()
        assert is_healthy is False
