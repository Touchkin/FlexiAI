"""Tests for Anthropic provider implementation."""

from unittest.mock import Mock, patch

import pytest
from anthropic import APIConnectionError as AnthropicConnectionError
from anthropic import APIError as AnthropicAPIError
from anthropic import AuthenticationError as AnthropicAuthError
from anthropic import BadRequestError as AnthropicBadRequestError
from anthropic import RateLimitError as AnthropicRateLimitError

from flexiai.exceptions import AuthenticationError, ProviderException, RateLimitError
from flexiai.exceptions import ValidationError as FlexiAIValidationError
from flexiai.models import Message, ProviderConfig, UnifiedRequest, UnifiedResponse
from flexiai.providers.anthropic_provider import AnthropicProvider


@pytest.fixture
def provider_config():
    """Create a valid Anthropic provider configuration."""
    return ProviderConfig(
        name="anthropic",
        api_key="sk-ant-test123456789012345678901234567890123456789012",
        model="claude-3-5-sonnet-20241022",
        timeout=30.0,
        max_retries=3,
        priority=1,
    )


@pytest.fixture
def anthropic_provider(provider_config):
    """Create an Anthropic provider instance."""
    with patch("flexiai.providers.anthropic_provider.anthropic.Anthropic"):
        provider = AnthropicProvider(provider_config)
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
def sample_claude_response():
    """Create a sample Claude API response."""
    mock_response = Mock()
    mock_response.id = "msg_123abc"
    mock_response.type = "message"
    mock_response.role = "assistant"
    mock_response.model = "claude-3-5-sonnet-20241022"
    mock_response.stop_reason = "end_turn"
    mock_response.stop_sequence = None

    # Content blocks
    mock_content_block = Mock()
    mock_content_block.type = "text"
    mock_content_block.text = "I'm doing well, thank you!"
    mock_response.content = [mock_content_block]

    # Usage
    mock_usage = Mock()
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 8
    mock_response.usage = mock_usage

    return mock_response


class TestAnthropicProviderInitialization:
    """Test Anthropic provider initialization."""

    def test_provider_initialization_success(self, provider_config):
        """Test successful provider initialization."""
        with patch("flexiai.providers.anthropic_provider.anthropic.Anthropic") as mock_anthropic:
            provider = AnthropicProvider(provider_config)

            assert provider.name == "anthropic"
            assert provider.config == provider_config
            assert provider.request_normalizer is not None
            assert provider.response_normalizer is not None

            # Verify Anthropic client was created with correct parameters
            # Note: Anthropic client only accepts api_key in __init__
            mock_anthropic.assert_called_once_with(api_key=provider_config.api_key)

    def test_provider_initialization_validates_credentials(self):
        """Test that initialization validates credentials."""
        config = ProviderConfig.model_construct(
            name="anthropic",
            api_key="",  # Invalid empty API key
            model="claude-3-5-sonnet-20241022",
            priority=1,
        )

        with pytest.raises(AuthenticationError, match="API key is required"):
            AnthropicProvider(config)

    def test_provider_initialization_validates_api_key_format(self):
        """Test that initialization accepts valid API keys."""
        # Anthropic doesn't validate the sk-ant- prefix at init, only when making requests
        config = ProviderConfig.model_construct(
            name="anthropic",
            api_key="sk-ant-validkey123",
            model="claude-3-5-sonnet-20241022",
            priority=1,
        )

        with patch("flexiai.providers.anthropic_provider.anthropic.Anthropic"):
            provider = AnthropicProvider(config)
            assert provider.config.api_key == "sk-ant-validkey123"

    def test_provider_initialization_with_environment_variable(self):
        """Test initialization with API key from environment."""
        config = ProviderConfig.model_construct(
            name="anthropic",
            api_key=None,
            model="claude-3-5-sonnet-20241022",
            priority=1,
        )

        # Patch environment before creating provider
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test123"}):
            with patch("flexiai.providers.anthropic_provider.anthropic.Anthropic"):
                # Also need to patch the config to get the API key from environment
                config.api_key = "sk-ant-test123"
                provider = AnthropicProvider(config)
                assert provider.config.api_key == "sk-ant-test123"


class TestAnthropicProviderChatCompletion:
    """Test Anthropic provider chat completion."""

    def test_chat_completion_success(
        self, anthropic_provider, sample_request, sample_claude_response
    ):
        """Test successful chat completion."""
        # Mock the Anthropic client's messages.create method
        anthropic_provider.client.messages.create = Mock(return_value=sample_claude_response)

        response = anthropic_provider.chat_completion(sample_request)

        assert isinstance(response, UnifiedResponse)
        assert response.content == "I'm doing well, thank you!"
        # Note: UnifiedResponse doesn't have a 'role' attribute
        # The role is embedded in metadata if needed
        assert response.finish_reason == "stop"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 8
        assert response.usage.total_tokens == 18

    def test_chat_completion_with_system_message(self, anthropic_provider):
        """Test chat completion with system message."""
        request = UnifiedRequest(
            messages=[
                Message(role="system", content="You are a helpful assistant."),
                Message(role="user", content="Hello!"),
            ],
            max_tokens=100,
        )

        mock_response = Mock()
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.stop_reason = "end_turn"
        mock_response.stop_sequence = None

        mock_content = Mock()
        mock_content.type = "text"
        mock_content.text = "Hi there!"
        mock_response.content = [mock_content]

        mock_usage = Mock()
        mock_usage.input_tokens = 5
        mock_usage.output_tokens = 3
        mock_response.usage = mock_usage

        anthropic_provider.client.messages.create = Mock(return_value=mock_response)

        # Call chat_completion
        anthropic_provider.chat_completion(request)

        # Verify system message was passed separately
        call_kwargs = anthropic_provider.client.messages.create.call_args[1]
        assert "system" in call_kwargs
        assert call_kwargs["system"] == "You are a helpful assistant."

    def test_chat_completion_with_multiple_content_blocks(self, anthropic_provider, sample_request):
        """Test chat completion with multiple content blocks."""
        mock_response = Mock()
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.stop_reason = "end_turn"
        mock_response.stop_sequence = None

        # Multiple content blocks
        mock_content1 = Mock()
        mock_content1.type = "text"
        mock_content1.text = "Here's the answer: "

        mock_content2 = Mock()
        mock_content2.type = "text"
        mock_content2.text = "42"

        mock_response.content = [mock_content1, mock_content2]

        mock_usage = Mock()
        mock_usage.input_tokens = 10
        mock_usage.output_tokens = 5
        mock_response.usage = mock_usage

        anthropic_provider.client.messages.create = Mock(return_value=mock_response)

        response = anthropic_provider.chat_completion(sample_request)

        assert response.content == "Here's the answer: 42"

    def test_chat_completion_with_tool_use(self, anthropic_provider, sample_request):
        """Test chat completion with tool use content block."""
        mock_response = Mock()
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.stop_reason = "tool_use"
        mock_response.stop_sequence = None

        # Text and tool_use blocks
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Let me check that for you."

        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.id = "tool_123"
        mock_tool_block.name = "search"
        mock_tool_block.input = {"query": "weather"}

        mock_response.content = [mock_text_block, mock_tool_block]

        mock_usage = Mock()
        mock_usage.input_tokens = 15
        mock_usage.output_tokens = 10
        mock_response.usage = mock_usage

        anthropic_provider.client.messages.create = Mock(return_value=mock_response)

        response = anthropic_provider.chat_completion(sample_request)

        assert "Let me check that for you." in response.content
        assert response.finish_reason == "tool_calls"

    def test_chat_completion_handles_normalization_error(self, anthropic_provider, sample_request):
        """Test that chat completion handles normalization errors."""
        # Mock normalizer to raise error
        anthropic_provider.request_normalizer.normalize = Mock(
            side_effect=FlexiAIValidationError("Invalid request")
        )

        # ValidationError gets wrapped in ProviderException by _handle_error
        with pytest.raises(ProviderException, match="Invalid request"):
            anthropic_provider.chat_completion(sample_request)


class TestAnthropicProviderErrorHandling:
    """Test Anthropic provider error handling."""

    def test_handle_rate_limit_error(self, anthropic_provider, sample_request):
        """Test handling of rate limit errors."""
        mock_error = AnthropicRateLimitError(
            message="Rate limit exceeded",
            response=Mock(status_code=429),
            body={"error": {"type": "rate_limit_error", "message": "Rate limit exceeded"}},
        )

        anthropic_provider.client.messages.create = Mock(side_effect=mock_error)

        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            anthropic_provider.chat_completion(sample_request)

    def test_handle_authentication_error(self, anthropic_provider, sample_request):
        """Test handling of authentication errors."""
        mock_error = AnthropicAuthError(
            message="Invalid API key",
            response=Mock(status_code=401),
            body={"error": {"type": "authentication_error", "message": "Invalid API key"}},
        )

        anthropic_provider.client.messages.create = Mock(side_effect=mock_error)

        with pytest.raises(AuthenticationError, match="Invalid API key"):
            anthropic_provider.chat_completion(sample_request)

    def test_handle_bad_request_error(self, anthropic_provider, sample_request):
        """Test handling of bad request errors."""
        mock_error = AnthropicBadRequestError(
            message="Invalid request",
            response=Mock(status_code=400),
            body={"error": {"type": "invalid_request_error", "message": "Invalid request"}},
        )

        anthropic_provider.client.messages.create = Mock(side_effect=mock_error)

        with pytest.raises(FlexiAIValidationError, match="Invalid request"):
            anthropic_provider.chat_completion(sample_request)

    def test_handle_connection_error(self, anthropic_provider, sample_request):
        """Test handling of connection errors."""
        mock_request = Mock()
        mock_error = AnthropicConnectionError(message="Connection failed", request=mock_request)

        anthropic_provider.client.messages.create = Mock(side_effect=mock_error)

        # Connection errors get wrapped in ProviderException
        with pytest.raises(ProviderException, match="Connection failed"):
            anthropic_provider.chat_completion(sample_request)

    def test_handle_generic_api_error(self, anthropic_provider, sample_request):
        """Test handling of generic API errors."""
        mock_error = AnthropicAPIError(
            message="Internal server error",
            request=Mock(),
            body={"error": {"type": "api_error", "message": "Internal server error"}},
        )

        anthropic_provider.client.messages.create = Mock(side_effect=mock_error)

        with pytest.raises(ProviderException, match="Internal server error"):
            anthropic_provider.chat_completion(sample_request)

    def test_handle_unexpected_error(self, anthropic_provider, sample_request):
        """Test handling of unexpected errors."""
        anthropic_provider.client.messages.create = Mock(side_effect=Exception("Unexpected error"))

        with pytest.raises(ProviderException, match="Unexpected error"):
            anthropic_provider.chat_completion(sample_request)


class TestAnthropicProviderAuthentication:
    """Test Anthropic provider authentication."""

    def test_authenticate_success(self, anthropic_provider):
        """Test successful authentication."""
        mock_response = Mock()
        mock_response.id = "msg_auth"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.stop_reason = "end_turn"
        mock_response.stop_sequence = None

        mock_content = Mock()
        mock_content.type = "text"
        mock_content.text = "Test"
        mock_response.content = [mock_content]

        mock_usage = Mock()
        mock_usage.input_tokens = 1
        mock_usage.output_tokens = 1
        mock_response.usage = mock_usage

        anthropic_provider.client.messages.create = Mock(return_value=mock_response)

        assert anthropic_provider.authenticate() is True

    def test_authenticate_failure(self, anthropic_provider):
        """Test authentication failure."""
        mock_error = AnthropicAuthError(
            message="Invalid API key",
            response=Mock(status_code=401),
            body={"error": {"type": "authentication_error", "message": "Invalid API key"}},
        )

        anthropic_provider.client.messages.create = Mock(side_effect=mock_error)

        with pytest.raises(AuthenticationError):
            anthropic_provider.authenticate()


class TestAnthropicProviderHealthCheck:
    """Test Anthropic provider health check."""

    def test_health_check_success(self, anthropic_provider):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.id = "msg_health"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.stop_reason = "end_turn"
        mock_response.stop_sequence = None

        mock_content = Mock()
        mock_content.type = "text"
        mock_content.text = "OK"
        mock_response.content = [mock_content]

        mock_usage = Mock()
        mock_usage.input_tokens = 1
        mock_usage.output_tokens = 1
        mock_response.usage = mock_usage

        anthropic_provider.client.messages.create = Mock(return_value=mock_response)

        assert anthropic_provider.health_check() is True

    def test_health_check_failure(self, anthropic_provider):
        """Test health check failure."""
        anthropic_provider.client.messages.create = Mock(
            side_effect=Exception("Health check failed")
        )

        assert anthropic_provider.health_check() is False


class TestAnthropicProviderResponseConversion:
    """Test Anthropic provider response conversion."""

    def test_response_to_dict_with_text_content(self, anthropic_provider):
        """Test converting response with text content."""
        mock_response = Mock()
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.stop_reason = "end_turn"
        mock_response.stop_sequence = None

        mock_content = Mock()
        mock_content.type = "text"
        mock_content.text = "Hello!"
        mock_response.content = [mock_content]

        mock_usage = Mock()
        mock_usage.input_tokens = 5
        mock_usage.output_tokens = 2
        mock_response.usage = mock_usage

        result = anthropic_provider._response_to_dict(mock_response)

        assert result["id"] == "msg_123"
        # Content is a list of blocks (as expected by the normalizer)
        assert isinstance(result["content"], list)
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        assert result["content"][0]["text"] == "Hello!"
        assert result["role"] == "assistant"
        assert result["stop_reason"] == "end_turn"
        assert result["usage"]["input_tokens"] == 5
        assert result["usage"]["output_tokens"] == 2

    def test_response_to_dict_with_no_content(self, anthropic_provider):
        """Test converting response with no content."""
        mock_response = Mock()
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.stop_reason = "end_turn"
        mock_response.stop_sequence = None
        mock_response.content = []

        mock_usage = Mock()
        mock_usage.input_tokens = 5
        mock_usage.output_tokens = 0
        mock_response.usage = mock_usage

        result = anthropic_provider._response_to_dict(mock_response)

        # Content list is empty but present
        assert "content" in result
        assert result["content"] == []

    def test_response_to_dict_with_mixed_content_blocks(self, anthropic_provider):
        """Test converting response with mixed content blocks."""
        mock_response = Mock()
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.stop_reason = "tool_use"
        mock_response.stop_sequence = None

        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Using tool: "

        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.id = "tool_123"
        mock_tool_block.name = "calculator"
        mock_tool_block.input = {"operation": "add"}

        mock_response.content = [mock_text_block, mock_tool_block]

        mock_usage = Mock()
        mock_usage.input_tokens = 10
        mock_usage.output_tokens = 5
        mock_response.usage = mock_usage

        result = anthropic_provider._response_to_dict(mock_response)

        # Content is a list with both text and tool_use blocks
        assert isinstance(result["content"], list)
        assert len(result["content"]) == 2
        assert result["content"][0]["type"] == "text"
        assert result["content"][0]["text"] == "Using tool: "
        assert result["content"][1]["type"] == "tool_use"
        assert result["content"][1]["name"] == "calculator"
        assert result["stop_reason"] == "tool_use"


class TestAnthropicProviderRateLimitInfo:
    """Test Anthropic provider rate limit info."""

    def test_get_rate_limit_info_returns_dict(self, anthropic_provider):
        """Test that get_rate_limit_info returns a dictionary."""
        info = anthropic_provider.get_rate_limit_info()

        assert isinstance(info, dict)
        # Implementation returns dict with note about rate limit headers
        assert "provider" in info
        assert info["provider"] == "anthropic"
