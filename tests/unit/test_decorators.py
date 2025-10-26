"""
Unit tests for decorator functionality.

This module tests:
- @flexiai_chat decorator with various configurations
- Global configuration management
- Sync and async function decoration
- Parameter extraction from function signatures
- Error handling and validation
"""

import asyncio
from unittest.mock import patch

import pytest

from flexiai import FlexiAI, FlexiAIConfig, flexiai_chat, set_global_config
from flexiai.decorators import (
    _construct_messages,
    _extract_message_parameter,
    get_global_client,
)
from flexiai.exceptions import ProviderException
from flexiai.models import UnifiedResponse, UsageInfo


@pytest.fixture(autouse=True)
def cleanup_global_state():
    """Clean up global state before and after each test."""
    # Reset global decorator state
    import flexiai.decorators as dec_module

    dec_module._global_client = None
    dec_module._global_config = None

    # Reset provider registry
    from flexiai.providers.registry import ProviderRegistry

    ProviderRegistry._instance = None

    yield

    # Clean up after test
    dec_module._global_client = None
    dec_module._global_config = None
    ProviderRegistry._instance = None


class TestGlobalConfiguration:
    """Test global configuration management."""

    def test_set_global_config_with_dict(self):
        """Test setting global config with a dictionary."""
        config = {
            "providers": [
                {
                    "name": "openai",
                    "api_key": "sk-proj-test123456789012345678901234567890",  # pragma: allowlist secret  # noqa: E501  # pragma: allowlist secret
                    "model": "gpt-3.5-turbo",
                    "priority": 1,
                }
            ],
            "primary_provider": "openai",
        }
        set_global_config(config)
        client = get_global_client()
        assert client is not None
        assert isinstance(client, FlexiAI)

    def test_set_global_config_with_flexiai_config(self):
        """Test setting global config with FlexiAIConfig object."""
        config = FlexiAIConfig(
            providers=[
                {
                    "name": "openai",
                    "api_key": "sk-proj-test123456789012345678901234567890",  # pragma: allowlist secret  # noqa: E501  # pragma: allowlist secret
                    "model": "gpt-3.5-turbo",
                    "priority": 1,
                }
            ],
            primary_provider="openai",
        )
        set_global_config(config)
        client = get_global_client()
        assert client is not None
        assert isinstance(client, FlexiAI)

    def test_set_global_config_via_flexiai_class_method(self):
        """Test setting global config via FlexiAI.set_global_config()."""
        config = FlexiAIConfig(
            providers=[
                {
                    "name": "openai",
                    "api_key": "sk-proj-test123456789012345678901234567890",  # pragma: allowlist secret  # noqa: E501
                    "model": "gpt-3.5-turbo",
                    "priority": 1,
                }
            ],
            primary_provider="openai",
        )
        FlexiAI.set_global_config(config)
        client = get_global_client()
        assert client is not None
        assert isinstance(client, FlexiAI)

    def test_get_global_client_without_config_raises_error(self):
        """Test that getting global client without config raises error."""
        # Reset global state by setting to None
        import flexiai.decorators as dec_module

        dec_module._global_client = None
        dec_module._global_config = None

        with pytest.raises(
            RuntimeError,
            match="Global FlexiAI config not set",
        ):
            get_global_client()

    def test_global_config_persists_across_calls(self):
        """Test that global config persists across multiple calls."""
        config = FlexiAIConfig(
            providers=[
                {
                    "name": "openai",
                    "api_key": "sk-proj-test123456789012345678901234567890",  # pragma: allowlist secret  # noqa: E501
                    "model": "gpt-3.5-turbo",
                    "priority": 1,
                }
            ],
            primary_provider="openai",
        )
        set_global_config(config)
        client1 = get_global_client()
        client2 = get_global_client()
        assert client1 is client2  # Should be the same instance


class TestMessageConstruction:
    """Test message construction helpers."""

    def test_construct_messages_with_system_message(self):
        """Test message construction with system message."""
        messages = _construct_messages("Hello AI", "You are helpful")
        assert len(messages) == 2
        assert messages[0] == {"role": "system", "content": "You are helpful"}
        assert messages[1] == {"role": "user", "content": "Hello AI"}

    def test_construct_messages_without_system_message(self):
        """Test message construction without system message."""
        messages = _construct_messages("Hello AI", None)
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "Hello AI"}

    def test_construct_messages_empty_system_message(self):
        """Test message construction with empty system message."""
        messages = _construct_messages("Hello AI", "")
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "Hello AI"}


class TestParameterExtraction:
    """Test parameter extraction from function signatures."""

    def test_extract_single_positional_parameter(self):
        """Test extracting parameter from single positional argument."""

        def func(message: str):
            pass

        result = _extract_message_parameter(func, ("Hello",), {})
        assert result == "Hello"

    def test_extract_keyword_parameter(self):
        """Test extracting parameter from keyword argument."""

        def func(message: str):
            pass

        result = _extract_message_parameter(func, (), {"message": "Hello"})
        assert result == "Hello"

    def test_extract_from_multiple_parameters_first(self):
        """Test extracting first parameter when function has multiple."""

        def func(user_input: str, context: str):
            pass

        result = _extract_message_parameter(func, ("Hello", "Context"), {})
        assert result == "Hello"

    def test_extract_from_kwargs_with_multiple_params(self):
        """Test extracting from kwargs when function has multiple params."""

        def func(user_input: str, context: str):
            pass

        result = _extract_message_parameter(func, (), {"user_input": "Hello", "context": "Context"})
        assert result == "Hello"

    def test_extract_mixed_args_kwargs(self):
        """Test extracting when using mix of args and kwargs."""

        def func(user_input: str, temperature: float = 0.7):
            pass

        result = _extract_message_parameter(func, ("Hello",), {"temperature": 0.9})
        assert result == "Hello"

    def test_extract_no_parameters_raises_error(self):
        """Test that function with no parameters raises error."""

        def func():
            pass

        with pytest.raises(
            ValueError, match="must have at least one parameter for the user message"
        ):
            _extract_message_parameter(func, (), {})

    def test_extract_no_args_provided_raises_error(self):
        """Test that calling with no args raises error."""

        def func(message: str):
            pass

        with pytest.raises(ValueError, match="Could not extract message parameter"):
            _extract_message_parameter(func, (), {})


class TestDecoratorBasicUsage:
    """Test basic decorator usage patterns."""

    @pytest.fixture(autouse=True)
    def setup_global_config(self):
        """Set up global config before each test."""
        config = FlexiAIConfig(
            providers=[
                {
                    "name": "openai",
                    "api_key": "sk-proj-test123456789012345678901234567890",  # pragma: allowlist secret  # noqa: E501
                    "model": "gpt-3.5-turbo",
                    "priority": 1,
                }
            ],
            primary_provider="openai",
        )
        set_global_config(config)

    def test_simple_decorator_no_parentheses(self):
        """Test decorator without parentheses."""

        @flexiai_chat
        def ask_ai(question: str) -> str:
            pass

        assert callable(ask_ai)
        assert hasattr(ask_ai, "__wrapped__")

    def test_decorator_with_empty_parentheses(self):
        """Test decorator with empty parentheses."""

        @flexiai_chat()
        def ask_ai(question: str) -> str:
            pass

        assert callable(ask_ai)
        assert hasattr(ask_ai, "__wrapped__")

    def test_decorator_with_system_message(self):
        """Test decorator with system message parameter."""

        @flexiai_chat(system_message="You are a helpful assistant")
        def ask_ai(question: str) -> str:
            pass

        assert callable(ask_ai)

    def test_decorator_with_temperature(self):
        """Test decorator with temperature parameter."""

        @flexiai_chat(temperature=0.7)
        def ask_ai(question: str) -> str:
            pass

        assert callable(ask_ai)

    def test_decorator_with_multiple_parameters(self):
        """Test decorator with multiple parameters."""

        @flexiai_chat(
            system_message="You are helpful",
            temperature=0.8,
            max_tokens=100,
        )
        def ask_ai(question: str) -> str:
            pass

        assert callable(ask_ai)

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""

        @flexiai_chat
        def ask_ai(question: str) -> str:
            """Ask AI a question."""
            pass

        assert ask_ai.__name__ == "ask_ai"
        assert ask_ai.__doc__ == "Ask AI a question."

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_decorated_function_calls_client(self, mock_chat):
        """Test that decorated function calls FlexiAI client."""
        mock_response = UnifiedResponse(
            content="Test response",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        mock_chat.return_value = mock_response

        @flexiai_chat
        def ask_ai(question: str) -> str:
            pass

        result = ask_ai("Hello")
        assert result == "Test response"
        mock_chat.assert_called_once()

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_decorated_function_with_system_message_constructs_messages(self, mock_chat):
        """Test that system message is properly included in chat call."""
        mock_response = UnifiedResponse(
            content="Test response",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        mock_chat.return_value = mock_response

        @flexiai_chat(system_message="You are helpful")
        def ask_ai(question: str) -> str:
            pass

        ask_ai("Hello")
        call_args = mock_chat.call_args
        messages = call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"


class TestDecoratorAsyncSupport:
    """Test async function decoration."""

    @pytest.fixture(autouse=True)
    def setup_global_config(self):
        """Set up global config before each test."""
        config = FlexiAIConfig(
            providers=[
                {
                    "name": "openai",
                    "api_key": "sk-proj-test123456789012345678901234567890",  # pragma: allowlist secret  # noqa: E501
                    "model": "gpt-3.5-turbo",
                    "priority": 1,
                }
            ],
            primary_provider="openai",
        )
        set_global_config(config)

    def test_async_function_decoration(self):
        """Test that async functions can be decorated."""

        @flexiai_chat
        async def ask_ai_async(question: str) -> str:
            pass

        assert asyncio.iscoroutinefunction(ask_ai_async)

    @pytest.mark.asyncio
    @patch("flexiai.client.FlexiAI.chat_completion")
    async def test_async_decorated_function_calls_async_client(self, mock_chat):
        """Test that async decorated function calls client via executor."""
        mock_response = UnifiedResponse(
            content="Async response",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        mock_chat.return_value = mock_response

        @flexiai_chat
        async def ask_ai_async(question: str) -> str:
            pass

        result = await ask_ai_async("Hello async")
        assert result == "Async response"
        mock_chat.assert_called_once()

    @pytest.mark.asyncio
    @patch("flexiai.client.FlexiAI.chat_completion")
    async def test_async_with_system_message(self, mock_chat):
        """Test async function with system message."""
        mock_response = UnifiedResponse(
            content="Async response",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        mock_chat.return_value = mock_response

        @flexiai_chat(system_message="You are an async assistant")
        async def ask_ai_async(question: str) -> str:
            pass

        await ask_ai_async("Hello")
        call_args = mock_chat.call_args
        messages = call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["content"] == "You are an async assistant"


class TestDecoratorParameters:
    """Test decorator parameter handling."""

    @pytest.fixture(autouse=True)
    def setup_global_config(self):
        """Set up global config before each test."""
        config = FlexiAIConfig(
            providers=[
                {
                    "name": "openai",
                    "api_key": "sk-proj-test123456789012345678901234567890",  # pragma: allowlist secret  # noqa: E501
                    "model": "gpt-3.5-turbo",
                    "priority": 1,
                }
            ],
            primary_provider="openai",
        )
        set_global_config(config)

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_temperature_parameter_passed_to_client(self, mock_chat):
        """Test that temperature parameter is passed to client."""
        mock_response = UnifiedResponse(
            content="Response",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        mock_chat.return_value = mock_response

        @flexiai_chat(temperature=0.9)
        def ask_ai(question: str) -> str:
            pass

        ask_ai("Hello")
        call_args = mock_chat.call_args
        assert call_args[1]["temperature"] == 0.9

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_max_tokens_parameter_passed_to_client(self, mock_chat):
        """Test that max_tokens parameter is passed to client."""
        mock_response = UnifiedResponse(
            content="Response",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        mock_chat.return_value = mock_response

        @flexiai_chat(max_tokens=500)
        def ask_ai(question: str) -> str:
            pass

        ask_ai("Hello")
        call_args = mock_chat.call_args
        assert call_args[1]["max_tokens"] == 500

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_provider_parameter_passed_to_client(self, mock_chat):
        """Test that provider parameter is passed to client."""
        mock_response = UnifiedResponse(
            content="Response",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        mock_chat.return_value = mock_response

        @flexiai_chat(provider="openai")
        def ask_ai(question: str) -> str:
            pass

        ask_ai("Hello")
        call_args = mock_chat.call_args
        assert call_args[1]["provider"] == "openai"

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_stream_parameter_passed_to_client(self, mock_chat):
        """Test that stream parameter is passed to client."""
        mock_response = UnifiedResponse(
            content="Response",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        mock_chat.return_value = mock_response

        @flexiai_chat(stream=True)
        def ask_ai(question: str) -> str:
            pass

        ask_ai("Hello")
        call_args = mock_chat.call_args
        assert call_args[1]["stream"] is True

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_all_parameters_passed_together(self, mock_chat):
        """Test that all parameters can be passed together."""
        mock_response = UnifiedResponse(
            content="Response",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        mock_chat.return_value = mock_response

        @flexiai_chat(
            system_message="You are helpful",
            temperature=0.8,
            max_tokens=200,
            provider="openai",
            stream=False,
        )
        def ask_ai(question: str) -> str:
            pass

        ask_ai("Hello")
        call_args = mock_chat.call_args
        assert call_args[1]["temperature"] == 0.8
        assert call_args[1]["max_tokens"] == 200
        assert call_args[1]["provider"] == "openai"
        assert call_args[1]["stream"] is False


class TestDecoratorErrorHandling:
    """Test error handling in decorators."""

    @pytest.fixture(autouse=True)
    def setup_global_config(self):
        """Set up global config before each test."""
        config = FlexiAIConfig(
            providers=[
                {
                    "name": "openai",
                    "api_key": "sk-proj-test123456789012345678901234567890",  # pragma: allowlist secret  # noqa: E501
                    "model": "gpt-3.5-turbo",
                    "priority": 1,
                }
            ],
            primary_provider="openai",
        )
        set_global_config(config)

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_provider_exception_propagates(self, mock_chat):
        """Test that ProviderException from client propagates."""
        mock_chat.side_effect = ProviderException("API Error", "openai")

        @flexiai_chat
        def ask_ai(question: str) -> str:
            pass

        with pytest.raises(ProviderException, match="API Error"):
            ask_ai("Hello")

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_function_with_no_parameters_raises_error(self, mock_chat):
        """Test that decorating function with no parameters raises error when called."""

        @flexiai_chat
        def no_params_func():
            pass

        # The error happens at call time, not decoration time
        with pytest.raises(ValueError, match="Could not extract message parameter"):
            no_params_func()

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_calling_with_no_args_raises_error(self, mock_chat):
        """Test that calling decorated function with no args raises error."""

        @flexiai_chat
        def ask_ai(question: str) -> str:
            pass

        with pytest.raises(ValueError, match="Could not extract message parameter"):
            ask_ai()


class TestDecoratorIntegration:
    """Integration tests for decorator with real scenarios."""

    @pytest.fixture(autouse=True)
    def setup_global_config(self):
        """Set up global config before each test."""
        config = FlexiAIConfig(
            providers=[
                {
                    "name": "openai",
                    "api_key": "sk-proj-test123456789012345678901234567890",  # pragma: allowlist secret  # noqa: E501
                    "model": "gpt-3.5-turbo",
                    "priority": 1,
                },
                {
                    "name": "anthropic",
                    "api_key": "sk-proj-test123456789012345678901234567890",  # pragma: allowlist secret  # noqa: E501
                    "model": "claude-3-sonnet-20240229",
                    "priority": 2,
                },
            ],
            primary_provider="openai",
            fallback_providers=["anthropic"],
        )
        set_global_config(config)

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_chatbot_function_with_decorator(self, mock_chat):
        """Test complete chatbot function using decorator."""
        mock_response = UnifiedResponse(
            content="The capital of France is Paris.",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=20, completion_tokens=10, total_tokens=30),
            finish_reason="stop",
        )
        mock_chat.return_value = mock_response

        @flexiai_chat(
            system_message="You are a geography expert",
            temperature=0.3,
            max_tokens=100,
        )
        def geography_bot(question: str) -> str:
            """Answer geography questions."""
            pass

        answer = geography_bot("What is the capital of France?")
        assert answer == "The capital of France is Paris."
        assert geography_bot.__name__ == "geography_bot"
        assert geography_bot.__doc__ == "Answer geography questions."

    @patch("flexiai.client.FlexiAI.chat_completion")
    def test_multiple_decorated_functions(self, mock_chat):
        """Test multiple decorated functions with different configs."""
        mock_response1 = UnifiedResponse(
            content="Creative response",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        mock_response2 = UnifiedResponse(
            content="Factual response",
            provider="openai",
            model="gpt-3.5-turbo",
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        mock_chat.side_effect = [mock_response1, mock_response2]

        @flexiai_chat(system_message="Be creative", temperature=0.9)
        def creative_writer(prompt: str) -> str:
            pass

        @flexiai_chat(system_message="Be factual", temperature=0.1)
        def fact_checker(question: str) -> str:
            pass

        result1 = creative_writer("Write a story")
        result2 = fact_checker("What is 2+2?")

        assert result1 == "Creative response"
        assert result2 == "Factual response"
        assert mock_chat.call_count == 2
