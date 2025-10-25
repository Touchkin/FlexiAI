"""
Unit tests for Claude Response Normalizer.

Tests the normalization of Claude API responses to unified format.
"""

import pytest

from flexiai.exceptions import InvalidResponseError
from flexiai.normalizers.response import ClaudeResponseNormalizer


class TestClaudeResponseNormalizerBasics:
    """Test basic response normalization for Claude."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude response normalizer instance."""
        return ClaudeResponseNormalizer()

    def test_basic_response(self, normalizer):
        """Test basic response normalization."""
        response = {
            "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello! How can I help you today?"}],
            "model": "claude-3-5-sonnet-20241022",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 25},
        }

        result = normalizer.normalize(
            response, provider_name="claude", model="claude-3-5-sonnet-20241022"
        )

        assert result.content == "Hello! How can I help you today?"
        assert result.model == "claude-3-5-sonnet-20241022"
        assert result.provider == "claude"
        assert result.finish_reason == "stop"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 25
        assert result.usage.total_tokens == 35

    def test_multiple_content_blocks(self, normalizer):
        """Test response with multiple text content blocks."""
        response = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "First part. "},
                {"type": "text", "text": "Second part."},
            ],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 10},
        }

        result = normalizer.normalize(response)

        # Content should be concatenated
        assert result.content == "First part. Second part."

    def test_tool_use_content_block(self, normalizer):
        """Test response with tool_use content block."""
        response = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me check that for you. "},
                {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "get_weather",
                    "input": {"location": "San Francisco"},
                },
            ],
            "model": "claude-3-opus-20240229",
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 15, "output_tokens": 30},
        }

        result = normalizer.normalize(response)

        assert "Let me check that for you." in result.content
        assert "[Tool use: get_weather]" in result.content
        assert result.finish_reason == "tool_calls"


class TestClaudeStopReasonMapping:
    """Test stop reason mapping from Claude to unified format."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude response normalizer instance."""
        return ClaudeResponseNormalizer()

    def test_end_turn_maps_to_stop(self, normalizer):
        """Test end_turn stop reason maps to 'stop'."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-3-sonnet",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 5},
        }

        result = normalizer.normalize(response)
        assert result.finish_reason == "stop"

    def test_max_tokens_maps_to_length(self, normalizer):
        """Test max_tokens stop reason maps to 'length'."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [{"type": "text", "text": "Response cut off"}],
            "model": "claude-3-sonnet",
            "stop_reason": "max_tokens",
            "usage": {"input_tokens": 5, "output_tokens": 100},
        }

        result = normalizer.normalize(response)
        assert result.finish_reason == "length"

    def test_stop_sequence_maps_to_stop(self, normalizer):
        """Test stop_sequence stop reason maps to 'stop'."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-3-sonnet",
            "stop_reason": "stop_sequence",
            "stop_sequence": "END",
            "usage": {"input_tokens": 5, "output_tokens": 5},
        }

        result = normalizer.normalize(response)
        assert result.finish_reason == "stop"
        assert result.metadata["stop_sequence"] == "END"

    def test_unknown_stop_reason(self, normalizer):
        """Test unknown stop reason defaults to 'unknown'."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-3-sonnet",
            "stop_reason": "some_new_reason",
            "usage": {"input_tokens": 5, "output_tokens": 5},
        }

        result = normalizer.normalize(response)
        assert result.finish_reason == "unknown"


class TestClaudeUsageExtraction:
    """Test usage information extraction."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude response normalizer instance."""
        return ClaudeResponseNormalizer()

    def test_usage_extraction(self, normalizer):
        """Test usage token extraction."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-3-sonnet",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 123, "output_tokens": 456},
        }

        result = normalizer.normalize(response)

        assert result.usage.prompt_tokens == 123
        assert result.usage.completion_tokens == 456
        assert result.usage.total_tokens == 579

    def test_missing_usage_defaults_to_zero(self, normalizer):
        """Test missing usage information defaults to zero."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-3-sonnet",
            "stop_reason": "end_turn",
            # No usage field
        }

        result = normalizer.normalize(response)

        assert result.usage.prompt_tokens == 0
        assert result.usage.completion_tokens == 0
        assert result.usage.total_tokens == 0

    def test_partial_usage_data(self, normalizer):
        """Test partial usage data handling."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-3-sonnet",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10},  # Missing output_tokens
        }

        result = normalizer.normalize(response)

        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 0
        assert result.usage.total_tokens == 10


class TestClaudeMetadataExtraction:
    """Test metadata extraction."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude response normalizer instance."""
        return ClaudeResponseNormalizer()

    def test_metadata_includes_message_id(self, normalizer):
        """Test metadata includes Claude message ID."""
        response = {
            "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
            "type": "message",
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-3-sonnet",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 5},
        }

        result = normalizer.normalize(response)

        assert result.metadata["message_id"] == "msg_01XFDUDYJgAACzvnptvVoYEL"
        assert result.metadata["type"] == "message"
        assert result.metadata["stop_reason"] == "end_turn"
        assert result.metadata["provider"] == "claude"

    def test_metadata_includes_stop_sequence(self, normalizer):
        """Test metadata includes stop_sequence when present."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-3-sonnet",
            "stop_reason": "stop_sequence",
            "stop_sequence": "DONE",
            "usage": {"input_tokens": 5, "output_tokens": 5},
        }

        result = normalizer.normalize(response)

        assert result.metadata["stop_sequence"] == "DONE"


class TestClaudeErrorNormalization:
    """Test error response normalization."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude response normalizer instance."""
        return ClaudeResponseNormalizer()

    def test_standard_error_format(self, normalizer):
        """Test standard Claude error format."""
        error_response = {
            "type": "error",
            "error": {"type": "invalid_request_error", "message": "Invalid parameter"},
        }

        result = normalizer.normalize_error(error_response, provider_name="claude")

        assert result["provider"] == "claude"
        assert result["type"] == "invalid_request_error"
        assert result["message"] == "Invalid parameter"
        assert result["status"] == "error"

    def test_authentication_error(self, normalizer):
        """Test authentication error normalization."""
        error_response = {
            "type": "error",
            "error": {
                "type": "authentication_error",
                "message": "Invalid API key",
            },
        }

        result = normalizer.normalize_error(error_response)

        assert result["type"] == "authentication_error"
        assert result["message"] == "Invalid API key"

    def test_rate_limit_error(self, normalizer):
        """Test rate limit error normalization."""
        error_response = {
            "type": "error",
            "error": {"type": "rate_limit_error", "message": "Too many requests"},
        }

        result = normalizer.normalize_error(error_response)

        assert result["type"] == "rate_limit_error"
        assert result["message"] == "Too many requests"

    def test_malformed_error_response(self, normalizer):
        """Test handling of malformed error response."""
        error_response = "Something went wrong"

        result = normalizer.normalize_error(error_response)

        assert result["provider"] == "claude"
        assert result["status"] == "error"
        assert "Something went wrong" in result["message"]


class TestClaudeEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude response normalizer instance."""
        return ClaudeResponseNormalizer()

    def test_empty_content_blocks(self, normalizer):
        """Test response with empty content blocks."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [],  # Empty content
            "model": "claude-3-sonnet",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 0},
        }

        result = normalizer.normalize(response)
        assert result.content == ""

    def test_invalid_response_type(self, normalizer):
        """Test handling of invalid response type."""
        with pytest.raises(InvalidResponseError):
            normalizer.normalize("not a dictionary")

    def test_missing_required_fields(self, normalizer):
        """Test handling of response with missing content field."""
        response = {
            "id": "msg_123",
            "type": "message",
            "model": "claude-3-sonnet",
            "stop_reason": "end_turn",
            # Missing content field (will default to empty)
        }

        # Should handle gracefully with empty content
        result = normalizer.normalize(response)
        assert result.content == ""

    def test_model_from_response_vs_parameter(self, normalizer):
        """Test model extraction from response vs parameter."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-3-opus-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 5},
        }

        # Model from response should take precedence
        result = normalizer.normalize(
            response, provider_name="claude", model="claude-3-sonnet-20240229"
        )

        assert result.model == "claude-3-opus-20240229"

    def test_streaming_response_detection(self, normalizer):
        """Test detection of streaming responses."""
        streaming_response = {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "Hello"},
        }

        assert normalizer.is_streaming_response(streaming_response) is True

        non_streaming_response = {
            "type": "message",
            "content": [{"type": "text", "text": "Hello"}],
        }

        assert normalizer.is_streaming_response(non_streaming_response) is False


class TestClaudeContentExtraction:
    """Test content extraction from various block types."""

    @pytest.fixture
    def normalizer(self):
        """Create a Claude response normalizer instance."""
        return ClaudeResponseNormalizer()

    def test_single_text_block(self, normalizer):
        """Test extraction from single text block."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [{"type": "text", "text": "Single text block"}],
            "model": "claude-3-sonnet",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 5},
        }

        result = normalizer.normalize(response)
        assert result.content == "Single text block"

    def test_mixed_content_blocks(self, normalizer):
        """Test extraction from mixed content blocks."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": [
                {"type": "text", "text": "Before tool. "},
                {"type": "tool_use", "id": "tool_1", "name": "calculator", "input": {}},
                {"type": "text", "text": " After tool."},
            ],
            "model": "claude-3-opus",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        result = normalizer.normalize(response)
        assert "Before tool." in result.content
        assert "[Tool use: calculator]" in result.content
        assert "After tool." in result.content

    def test_invalid_content_structure(self, normalizer):
        """Test handling of invalid content structure."""
        response = {
            "id": "msg_123",
            "type": "message",
            "content": "not a list",  # Should be a list
            "model": "claude-3-sonnet",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 5},
        }

        with pytest.raises(InvalidResponseError, match="content must be a list"):
            normalizer.normalize(response)
