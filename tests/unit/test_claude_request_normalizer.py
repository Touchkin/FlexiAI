"""
Unit tests for Claude Request Normalizer.

Tests the normalization of unified requests to Claude Messages API format.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from flexiai.exceptions import ValidationError
from flexiai.models import Message, UnifiedRequest
from flexiai.normalizers.request import ClaudeRequestNormalizer


class TestClaudeRequestNormalizerBasics:
    """Test basic request normalization for Claude."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude request normalizer instance."""
        return ClaudeRequestNormalizer()

    def test_basic_request(self, normalizer):
        """Test basic request normalization."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello, Claude!")],
            max_tokens=100,
        )

        result = normalizer.normalize(request)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "Hello, Claude!"
        assert result["max_tokens"] == 100

    def test_system_message_extraction(self, normalizer):
        """Test that system messages are extracted to separate parameter."""
        request = UnifiedRequest(
            messages=[
                Message(role="system", content="You are a helpful assistant."),
                Message(role="user", content="Hello!"),
            ]
        )

        result = normalizer.normalize(request)

        # System message should be in separate 'system' parameter
        assert "system" in result
        assert result["system"] == "You are a helpful assistant."

        # Only user message should be in messages array
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"

    def test_multiple_system_messages(self, normalizer):
        """Test combining multiple system messages."""
        request = UnifiedRequest(
            messages=[
                Message(role="system", content="First instruction."),
                Message(role="system", content="Second instruction."),
                Message(role="user", content="Hello!"),
            ]
        )

        result = normalizer.normalize(request)

        # Multiple system messages should be combined with newlines
        assert result["system"] == "First instruction.\n\nSecond instruction."
        assert len(result["messages"]) == 1

    def test_required_max_tokens(self, normalizer):
        """Test that max_tokens is always set (Claude requirement)."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello!")],
            # No max_tokens specified
        )

        result = normalizer.normalize(request)

        # Should default to 4096
        assert "max_tokens" in result
        assert result["max_tokens"] == 4096

    def test_max_tokens_override(self, normalizer):
        """Test that custom max_tokens is preserved."""
        request = UnifiedRequest(messages=[Message(role="user", content="Hello!")], max_tokens=500)

        result = normalizer.normalize(request)

        assert result["max_tokens"] == 500


class TestClaudeMessageNormalization:
    """Test message-specific normalization for Claude."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude request normalizer instance."""
        return ClaudeRequestNormalizer()

    def test_alternating_messages(self, normalizer):
        """Test proper alternating user/assistant messages."""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?"),
        ]

        result = normalizer.normalize_messages(messages)

        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user"

    def test_consecutive_same_role_error(self, normalizer):
        """Test that consecutive same-role messages raise error."""
        messages = [
            Message(role="user", content="First message"),
            Message(role="user", content="Second message"),  # Consecutive user!
        ]

        with pytest.raises(ValidationError, match="consecutive messages with the same role"):
            normalizer.normalize_messages(messages)

    def test_invalid_role_error(self, normalizer):
        """Test that invalid roles raise error."""
        messages = [Message(role="function", content="Some result")]

        with pytest.raises(ValidationError, match="only supports 'user' and 'assistant'"):
            normalizer.normalize_messages(messages)

    def test_system_messages_filtered(self, normalizer):
        """Test that system messages are filtered from message list."""
        messages = [
            Message(role="system", content="System instruction"),
            Message(role="user", content="User message"),
        ]

        result = normalizer.normalize_messages(messages)

        # System message should be skipped
        assert len(result) == 1
        assert result[0]["role"] == "user"


class TestClaudeParameterMapping:
    """Test parameter mapping from unified format to Claude format."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude request normalizer instance."""
        return ClaudeRequestNormalizer()

    def test_temperature_mapping(self, normalizer):
        """Test temperature parameter mapping."""
        request = UnifiedRequest(messages=[Message(role="user", content="Test")], temperature=0.7)

        result = normalizer.normalize(request)

        assert result["temperature"] == 0.7

    def test_top_p_mapping(self, normalizer):
        """Test top_p parameter mapping."""
        request = UnifiedRequest(messages=[Message(role="user", content="Test")], top_p=0.9)

        result = normalizer.normalize(request)

        assert result["top_p"] == 0.9

    def test_stop_sequences_mapping_single(self, normalizer):
        """Test stop parameter maps to stop_sequences (single value)."""
        request = UnifiedRequest(messages=[Message(role="user", content="Test")], stop="STOP")

        result = normalizer.normalize(request)

        # Single stop should be converted to list
        assert result["stop_sequences"] == ["STOP"]

    def test_stop_sequences_mapping_list(self, normalizer):
        """Test stop parameter maps to stop_sequences (list)."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Test")], stop=["END", "STOP"]
        )

        result = normalizer.normalize(request)

        assert result["stop_sequences"] == ["END", "STOP"]

    def test_stream_parameter(self, normalizer):
        """Test streaming parameter."""
        request = UnifiedRequest(messages=[Message(role="user", content="Test")], stream=True)

        result = normalizer.normalize(request)

        assert result["stream"] is True


class TestClaudeModelValidation:
    """Test Claude model validation."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude request normalizer instance."""
        return ClaudeRequestNormalizer()

    def test_valid_opus_model(self, normalizer):
        """Test Claude Opus model validation."""
        assert normalizer.validate_model_support("claude-3-opus-20240229")

    def test_valid_sonnet_model(self, normalizer):
        """Test Claude Sonnet model validation."""
        assert normalizer.validate_model_support("claude-3-sonnet-20240229")

    def test_valid_haiku_model(self, normalizer):
        """Test Claude Haiku model validation."""
        assert normalizer.validate_model_support("claude-3-haiku-20240307")

    def test_valid_sonnet_3_5_model(self, normalizer):
        """Test Claude 3.5 Sonnet model validation."""
        assert normalizer.validate_model_support("claude-3-5-sonnet-20241022")

    def test_valid_haiku_3_5_model(self, normalizer):
        """Test Claude 3.5 Haiku model validation."""
        assert normalizer.validate_model_support("claude-3-5-haiku-20241022")

    def test_invalid_model(self, normalizer):
        """Test invalid model rejection."""
        assert not normalizer.validate_model_support("gpt-4")
        assert not normalizer.validate_model_support("gemini-pro")


class TestClaudeEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude request normalizer instance."""
        return ClaudeRequestNormalizer()

    def test_empty_messages_error(self, normalizer):
        """Test that empty messages are caught by Pydantic validation."""
        # Pydantic validates this before normalizer is called
        with pytest.raises(PydanticValidationError):
            UnifiedRequest(messages=[])

    def test_only_system_messages(self, normalizer):
        """Test request with only system messages."""
        request = UnifiedRequest(messages=[Message(role="system", content="You are helpful.")])

        result = normalizer.normalize(request)

        # Should have system parameter but empty messages array
        assert result["system"] == "You are helpful."
        assert len(result["messages"]) == 0

    def test_multi_turn_conversation(self, normalizer):
        """Test multi-turn conversation normalization."""
        request = UnifiedRequest(
            messages=[
                Message(role="user", content="What is 2+2?"),
                Message(role="assistant", content="4"),
                Message(role="user", content="What is 3+3?"),
                Message(role="assistant", content="6"),
                Message(role="user", content="Thanks!"),
            ],
            temperature=0.5,
            max_tokens=100,
        )

        result = normalizer.normalize(request)

        assert len(result["messages"]) == 5
        assert result["temperature"] == 0.5
        assert result["max_tokens"] == 100

        # Verify alternating pattern
        for i, msg in enumerate(result["messages"]):
            expected_role = "user" if i % 2 == 0 else "assistant"
            assert msg["role"] == expected_role
