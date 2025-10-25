"""
Unit tests for request normalizers.

Tests the RequestNormalizer base class and OpenAIRequestNormalizer.
"""

import pytest

from flexiai.exceptions import ValidationError
from flexiai.models import Message, UnifiedRequest
from flexiai.normalizers.request import OpenAIRequestNormalizer, RequestNormalizer


class TestRequestNormalizerBase:
    """Test RequestNormalizer base class."""

    def test_cannot_instantiate_base_class(self) -> None:
        """Test that RequestNormalizer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RequestNormalizer()  # type: ignore


class TestOpenAIRequestNormalizer:
    """Test OpenAI request normalizer."""

    def test_normalize_simple_request(self) -> None:
        """Test normalizing a simple request with minimal parameters."""
        normalizer = OpenAIRequestNormalizer()
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
        )

        result = normalizer.normalize(request)

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "Hello"

    def test_normalize_request_with_temperature(self) -> None:
        """Test normalizing request with temperature parameter."""
        normalizer = OpenAIRequestNormalizer()
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            temperature=0.7,
        )

        result = normalizer.normalize(request)

        assert result["temperature"] == 0.7

    def test_normalize_request_with_all_parameters(self) -> None:
        """Test normalizing request with all supported parameters."""
        normalizer = OpenAIRequestNormalizer()
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            temperature=0.8,
            max_tokens=100,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            stop=["\\n", "END"],
            stream=False,
            seed=42,
            user="test-user",
        )

        result = normalizer.normalize(request)

        assert result["temperature"] == 0.8
        assert result["max_tokens"] == 100
        assert result["top_p"] == 0.9
        assert result["frequency_penalty"] == 0.5
        assert result["presence_penalty"] == 0.3
        assert result["stop"] == ["\\n", "END"]
        assert result["stream"] is False
        assert result["seed"] == 42
        assert result["user"] == "test-user"

    def test_normalize_empty_messages_raises_error(self) -> None:
        """Test that normalizing with empty messages raises ValidationError."""
        normalizer = OpenAIRequestNormalizer()
        # Use model_construct to bypass Pydantic validation
        request = UnifiedRequest.model_construct(messages=[])

        with pytest.raises(ValidationError, match="at least one message"):
            normalizer.normalize(request)

    def test_normalize_messages_system_and_user(self) -> None:
        """Test normalizing messages with system and user roles."""
        normalizer = OpenAIRequestNormalizer()
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
        ]

        result = normalizer.normalize_messages(messages)

        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are helpful"
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "Hello"

    def test_normalize_messages_with_name(self) -> None:
        """Test normalizing messages with name field."""
        normalizer = OpenAIRequestNormalizer()
        messages = [
            Message(role="user", content="Hello", name="Alice"),
        ]

        result = normalizer.normalize_messages(messages)

        assert result[0]["name"] == "Alice"

    def test_normalize_messages_with_function_call(self) -> None:
        """Test normalizing messages with function_call field."""
        normalizer = OpenAIRequestNormalizer()
        function_call = {"name": "get_weather", "arguments": '{"location": "NYC"}'}
        messages = [
            Message(role="assistant", content=None, function_call=function_call),
        ]

        result = normalizer.normalize_messages(messages)

        assert result[0]["function_call"] == function_call

    def test_normalize_messages_with_tool_calls(self) -> None:
        """Test normalizing messages with tool_calls field."""
        normalizer = OpenAIRequestNormalizer()
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"location": "NYC"}'},
            }
        ]
        messages = [
            Message(role="assistant", content=None, tool_calls=tool_calls),
        ]

        result = normalizer.normalize_messages(messages)

        assert result[0]["tool_calls"] == tool_calls

    def test_normalize_messages_empty_list_raises_error(self) -> None:
        """Test that normalizing empty messages list raises ValidationError."""
        normalizer = OpenAIRequestNormalizer()

        with pytest.raises(ValidationError, match="cannot be empty"):
            normalizer.normalize_messages([])

    def test_normalize_excludes_none_parameters(self) -> None:
        """Test that None parameters are excluded from result."""
        normalizer = OpenAIRequestNormalizer()
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            temperature=None,
            max_tokens=None,
        )

        result = normalizer.normalize(request)

        assert "temperature" not in result
        assert "max_tokens" not in result
        assert "messages" in result

    def test_validate_model_support_gpt4(self) -> None:
        """Test model validation for GPT-4 models."""
        normalizer = OpenAIRequestNormalizer()

        assert normalizer.validate_model_support("gpt-4") is True
        assert normalizer.validate_model_support("gpt-4-turbo") is True
        assert normalizer.validate_model_support("gpt-4o") is True
        assert normalizer.validate_model_support("gpt-4-32k") is True

    def test_validate_model_support_gpt35(self) -> None:
        """Test model validation for GPT-3.5 models."""
        normalizer = OpenAIRequestNormalizer()

        assert normalizer.validate_model_support("gpt-3.5-turbo") is True
        assert normalizer.validate_model_support("gpt-3.5-turbo-16k") is True

    def test_validate_model_support_o1(self) -> None:
        """Test model validation for O1 models."""
        normalizer = OpenAIRequestNormalizer()

        assert normalizer.validate_model_support("o1-preview") is True
        assert normalizer.validate_model_support("o1-mini") is True

    def test_validate_model_support_unsupported(self) -> None:
        """Test model validation for unsupported models."""
        normalizer = OpenAIRequestNormalizer()

        assert normalizer.validate_model_support("claude-3") is False
        assert normalizer.validate_model_support("gemini-pro") is False
        assert normalizer.validate_model_support("unknown-model") is False

    def test_normalize_with_response_format(self) -> None:
        """Test normalizing request with response_format parameter."""
        normalizer = OpenAIRequestNormalizer()
        response_format = {"type": "json_object"}
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            response_format=response_format,
        )

        result = normalizer.normalize(request)

        assert result["response_format"] == response_format

    def test_normalize_with_tools(self) -> None:
        """Test normalizing request with tools parameter."""
        normalizer = OpenAIRequestNormalizer()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            tools=tools,
        )

        result = normalizer.normalize(request)

        assert result["tools"] == tools

    def test_normalize_with_tool_choice(self) -> None:
        """Test normalizing request with tool_choice parameter."""
        normalizer = OpenAIRequestNormalizer()
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            tool_choice="auto",
        )

        result = normalizer.normalize(request)

        assert result["tool_choice"] == "auto"

    def test_normalize_conversation(self) -> None:
        """Test normalizing a multi-turn conversation."""
        normalizer = OpenAIRequestNormalizer()
        request = UnifiedRequest(
            messages=[
                Message(role="system", content="You are helpful"),
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there!"),
                Message(role="user", content="How are you?"),
            ],
        )

        result = normalizer.normalize(request)

        assert len(result["messages"]) == 4
        assert result["messages"][0]["role"] == "system"
        assert result["messages"][1]["role"] == "user"
        assert result["messages"][2]["role"] == "assistant"
        assert result["messages"][3]["role"] == "user"
