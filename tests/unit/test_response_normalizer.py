"""
Unit tests for response normalizers.

Tests the ResponseNormalizer base class and OpenAIResponseNormalizer.
"""

import pytest

from flexiai.exceptions import InvalidResponseError
from flexiai.normalizers.response import OpenAIResponseNormalizer, ResponseNormalizer


class TestResponseNormalizerBase:
    """Test ResponseNormalizer base class."""

    def test_cannot_instantiate_base_class(self) -> None:
        """Test that ResponseNormalizer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ResponseNormalizer()  # type: ignore


class TestOpenAIResponseNormalizer:
    """Test OpenAI response normalizer."""

    def test_normalize_simple_response(self) -> None:
        """Test normalizing a simple OpenAI response."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        }

        result = normalizer.normalize(response)

        assert result.content == "Hello!"
        assert result.model == "gpt-4"
        assert result.provider == "openai"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.usage.total_tokens == 15
        assert result.finish_reason == "stop"

    def test_normalize_response_with_metadata(self) -> None:
        """Test that metadata is preserved in normalized response."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4",
            "system_fingerprint": "fp_123",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        result = normalizer.normalize(response)

        assert result.metadata is not None
        assert result.metadata["id"] == "chatcmpl-123"
        assert result.metadata["created"] == 1677652288
        assert result.metadata["system_fingerprint"] == "fp_123"
        assert result.metadata["object"] == "chat.completion"

    def test_normalize_response_missing_choices_raises_error(self) -> None:
        """Test that response without choices raises InvalidResponseError."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "model": "gpt-4",
        }

        with pytest.raises(InvalidResponseError, match="at least one choice"):
            normalizer.normalize(response)

    def test_normalize_response_empty_choices_raises_error(self) -> None:
        """Test that response with empty choices raises InvalidResponseError."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "model": "gpt-4",
            "choices": [],
        }

        with pytest.raises(InvalidResponseError, match="at least one choice"):
            normalizer.normalize(response)

    def test_normalize_response_with_model_parameter(self) -> None:
        """Test normalizing response with model passed as parameter."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        result = normalizer.normalize(response, model="gpt-4")

        assert result.model == "gpt-4"

    def test_normalize_response_no_model_raises_error(self) -> None:
        """Test that response without model in data or parameter raises error."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
        }

        with pytest.raises(InvalidResponseError, match="Model name must be provided"):
            normalizer.normalize(response)

    def test_normalize_response_with_function_call(self) -> None:
        """Test normalizing response with function call."""
        normalizer = OpenAIResponseNormalizer()
        function_call = {"name": "get_weather", "arguments": '{"location": "NYC"}'}
        response = {
            "id": "chatcmpl-123",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "function_call": function_call,
                    },
                    "finish_reason": "function_call",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        result = normalizer.normalize(response)

        assert str(function_call) in result.content
        assert result.finish_reason == "function_call"

    def test_normalize_response_with_tool_calls(self) -> None:
        """Test normalizing response with tool calls."""
        normalizer = OpenAIResponseNormalizer()
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"location": "NYC"}'},
            }
        ]
        response = {
            "id": "chatcmpl-123",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls,
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        result = normalizer.normalize(response)

        assert str(tool_calls) in result.content
        assert result.finish_reason == "tool_calls"

    def test_normalize_response_missing_usage(self) -> None:
        """Test normalizing response without usage information."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
        }

        result = normalizer.normalize(response)

        assert result.usage.prompt_tokens == 0
        assert result.usage.completion_tokens == 0
        assert result.usage.total_tokens == 0

    def test_normalize_response_missing_finish_reason(self) -> None:
        """Test normalizing response without finish_reason."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello!"},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        result = normalizer.normalize(response)

        assert result.finish_reason == "unknown"

    def test_normalize_response_with_delta_content(self) -> None:
        """Test normalizing streaming response with delta content."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "model": "gpt-4",
            "choices": [
                {
                    "delta": {"content": "Hello"},
                    "finish_reason": None,
                }
            ],
        }

        result = normalizer.normalize(response)

        assert result.content == "Hello"

    def test_normalize_response_no_content_raises_error(self) -> None:
        """Test that response without content raises InvalidResponseError."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {"role": "assistant"},
                    "finish_reason": "stop",
                }
            ],
        }

        with pytest.raises(InvalidResponseError, match="Could not extract content"):
            normalizer.normalize(response)

    def test_normalize_error_with_standard_format(self) -> None:
        """Test normalizing standard OpenAI error response."""
        normalizer = OpenAIResponseNormalizer()
        error_response = {
            "error": {
                "message": "Invalid API key provided",
                "type": "invalid_request_error",
                "code": "invalid_api_key",
            }
        }

        result = normalizer.normalize_error(error_response)

        assert result["provider"] == "openai"
        assert result["message"] == "Invalid API key provided"
        assert result["type"] == "invalid_request_error"
        assert result["code"] == "invalid_api_key"

    def test_normalize_error_with_param(self) -> None:
        """Test normalizing error with param field."""
        normalizer = OpenAIResponseNormalizer()
        error_response = {
            "error": {
                "message": "Invalid parameter",
                "type": "invalid_request_error",
                "param": "temperature",
            }
        }

        result = normalizer.normalize_error(error_response)

        assert result["param"] == "temperature"

    def test_normalize_error_unexpected_format(self) -> None:
        """Test normalizing error with unexpected format."""
        normalizer = OpenAIResponseNormalizer()
        error_response = {"unexpected": "format", "message": "Something went wrong"}

        result = normalizer.normalize_error(error_response)

        assert result["provider"] == "openai"
        assert result["type"] == "unknown"
        assert "unexpected" in result["message"].lower()

    def test_is_streaming_response_true(self) -> None:
        """Test detecting streaming response."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"content": "Hello"}}],
        }

        assert normalizer.is_streaming_response(response) is True

    def test_is_streaming_response_false(self) -> None:
        """Test detecting non-streaming response."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "object": "chat.completion",
            "choices": [{"message": {"content": "Hello"}}],
        }

        assert normalizer.is_streaming_response(response) is False

    def test_normalize_response_with_custom_provider_name(self) -> None:
        """Test normalizing response with custom provider name."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        result = normalizer.normalize(response, provider_name="azure-openai")

        assert result.provider == "azure-openai"

    def test_normalize_response_invalid_type_raises_error(self) -> None:
        """Test that non-dict response raises InvalidResponseError."""
        normalizer = OpenAIResponseNormalizer()

        with pytest.raises(InvalidResponseError, match="must be a dictionary"):
            normalizer.normalize("not a dict", model="gpt-4")  # type: ignore

    def test_normalize_response_with_partial_usage(self) -> None:
        """Test normalizing response with partial usage data."""
        normalizer = OpenAIResponseNormalizer()
        response = {
            "id": "chatcmpl-123",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                # Missing completion_tokens and total_tokens
            },
        }

        result = normalizer.normalize(response)

        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 0
        # UsageInfo auto-calculates total_tokens as prompt + completion
        assert result.usage.total_tokens == 10
