"""
Unit tests for FlexiAI validators.

Tests validation of API keys, model names, request parameters,
and provider configurations.
"""

import pytest

from flexiai.exceptions import ValidationError
from flexiai.utils.validators import (
    APIKeyValidator,
    ModelValidator,
    RequestValidator,
    validate_provider_config,
)


class TestAPIKeyValidator:
    """Tests for APIKeyValidator."""

    def test_validate_openai_key_valid(self) -> None:
        """Test validation of valid OpenAI API key."""
        assert APIKeyValidator.validate("openai", "sk-1234567890abcdefghij") is True

    def test_validate_anthropic_key_valid(self) -> None:
        """Test validation of valid Anthropic API key."""
        assert APIKeyValidator.validate("anthropic", "sk-ant-1234567890abcdefghij") is True

    def test_validate_gemini_key_valid(self) -> None:
        """Test validation of valid Gemini API key."""
        assert APIKeyValidator.validate("gemini", "AIzaSyDemoKey1234567890") is True

    def test_validate_empty_key(self) -> None:
        """Test that empty API key raises error."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyValidator.validate("openai", "")
        assert "cannot be empty" in str(exc_info.value)

    def test_validate_whitespace_key(self) -> None:
        """Test that whitespace-only API key raises error."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyValidator.validate("openai", "   ")
        assert "cannot be empty" in str(exc_info.value)

    def test_validate_invalid_openai_key_format(self) -> None:
        """Test that invalid OpenAI key format raises error."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyValidator.validate("openai", "invalid-key")
        assert "Invalid API key format" in str(exc_info.value)

    def test_validate_unknown_provider(self) -> None:
        """Test that unknown provider accepts any non-empty key."""
        assert APIKeyValidator.validate("unknown_provider", "any-key-format") is True


class TestModelValidator:
    """Tests for ModelValidator."""

    def test_validate_openai_model_valid(self) -> None:
        """Test validation of valid OpenAI model."""
        assert ModelValidator.validate("openai", "gpt-4") is True
        assert ModelValidator.validate("openai", "gpt-3.5-turbo") is True

    def test_validate_anthropic_model_valid(self) -> None:
        """Test validation of valid Anthropic model."""
        assert ModelValidator.validate("anthropic", "claude-3-opus-20240229") is True

    def test_validate_gemini_model_valid(self) -> None:
        """Test validation of valid Gemini model."""
        assert ModelValidator.validate("gemini", "gemini-pro") is True

    def test_validate_empty_model(self) -> None:
        """Test that empty model name raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelValidator.validate("openai", "")
        assert "cannot be empty" in str(exc_info.value)

    def test_validate_invalid_model_strict(self) -> None:
        """Test that invalid model in strict mode raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelValidator.validate("openai", "invalid-model", strict=True)
        assert "not supported" in str(exc_info.value)

    def test_validate_invalid_model_non_strict(self) -> None:
        """Test that invalid model in non-strict mode is allowed."""
        assert ModelValidator.validate("openai", "new-future-model", strict=False) is True

    def test_validate_azure_model(self) -> None:
        """Test that Azure accepts any model (deployment name)."""
        assert ModelValidator.validate("azure", "my-custom-deployment") is True

    def test_get_supported_models_openai(self) -> None:
        """Test getting supported models for OpenAI."""
        models = ModelValidator.get_supported_models("openai")
        assert "gpt-4" in models
        assert "gpt-3.5-turbo" in models

    def test_get_supported_models_unknown(self) -> None:
        """Test getting supported models for unknown provider."""
        models = ModelValidator.get_supported_models("unknown")
        assert models == []


class TestRequestValidator:
    """Tests for RequestValidator."""

    def test_validate_temperature_valid(self) -> None:
        """Test validation of valid temperature."""
        assert RequestValidator.validate_temperature(0.7) is True
        assert RequestValidator.validate_temperature(0.0) is True
        assert RequestValidator.validate_temperature(2.0) is True

    def test_validate_temperature_invalid_type(self) -> None:
        """Test that non-numeric temperature raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_temperature("0.7")  # type: ignore
        assert "must be a number" in str(exc_info.value)

    def test_validate_temperature_out_of_range_low(self) -> None:
        """Test that temperature below 0.0 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_temperature(-0.1)
        assert "between 0.0 and 2.0" in str(exc_info.value)

    def test_validate_temperature_out_of_range_high(self) -> None:
        """Test that temperature above 2.0 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_temperature(2.1)
        assert "between 0.0 and 2.0" in str(exc_info.value)

    def test_validate_max_tokens_valid(self) -> None:
        """Test validation of valid max_tokens."""
        assert RequestValidator.validate_max_tokens(100) is True
        assert RequestValidator.validate_max_tokens(1) is True

    def test_validate_max_tokens_invalid_type(self) -> None:
        """Test that non-integer max_tokens raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_max_tokens(100.5)  # type: ignore
        assert "must be an integer" in str(exc_info.value)

    def test_validate_max_tokens_too_low(self) -> None:
        """Test that max_tokens < 1 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_max_tokens(0)
        assert "at least 1" in str(exc_info.value)

    def test_validate_max_tokens_exceeds_limit(self) -> None:
        """Test that max_tokens exceeding provider limit raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_max_tokens(10000, provider="openai")
        assert "exceeds" in str(exc_info.value)
        assert "limit" in str(exc_info.value)

    def test_validate_top_p_valid(self) -> None:
        """Test validation of valid top_p."""
        assert RequestValidator.validate_top_p(0.9) is True
        assert RequestValidator.validate_top_p(0.0) is True
        assert RequestValidator.validate_top_p(1.0) is True

    def test_validate_top_p_invalid_type(self) -> None:
        """Test that non-numeric top_p raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_top_p("0.9")  # type: ignore
        assert "must be a number" in str(exc_info.value)

    def test_validate_top_p_out_of_range(self) -> None:
        """Test that top_p out of range raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_top_p(1.5)
        assert "between 0.0 and 1.0" in str(exc_info.value)

    def test_validate_frequency_penalty_valid(self) -> None:
        """Test validation of valid frequency_penalty."""
        assert RequestValidator.validate_frequency_penalty(0.5) is True
        assert RequestValidator.validate_frequency_penalty(-2.0) is True
        assert RequestValidator.validate_frequency_penalty(2.0) is True

    def test_validate_frequency_penalty_invalid_type(self) -> None:
        """Test that non-numeric frequency_penalty raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_frequency_penalty("0.5")  # type: ignore
        assert "must be a number" in str(exc_info.value)

    def test_validate_frequency_penalty_out_of_range(self) -> None:
        """Test that frequency_penalty out of range raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_frequency_penalty(3.0)
        assert "between -2.0 and 2.0" in str(exc_info.value)

    def test_validate_presence_penalty_valid(self) -> None:
        """Test validation of valid presence_penalty."""
        assert RequestValidator.validate_presence_penalty(0.5) is True
        assert RequestValidator.validate_presence_penalty(-2.0) is True
        assert RequestValidator.validate_presence_penalty(2.0) is True

    def test_validate_presence_penalty_invalid_type(self) -> None:
        """Test that non-numeric presence_penalty raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_presence_penalty("0.5")  # type: ignore
        assert "must be a number" in str(exc_info.value)

    def test_validate_presence_penalty_out_of_range(self) -> None:
        """Test that presence_penalty out of range raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_presence_penalty(-3.0)
        assert "between -2.0 and 2.0" in str(exc_info.value)

    def test_validate_messages_valid(self) -> None:
        """Test validation of valid messages list."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        assert RequestValidator.validate_messages(messages) is True

    def test_validate_messages_with_tool_calls(self) -> None:
        """Test validation of messages with tool_calls."""
        messages = [
            {"role": "assistant", "tool_calls": [{"id": "1", "function": {}}]},
        ]
        assert RequestValidator.validate_messages(messages) is True

    def test_validate_messages_invalid_type(self) -> None:
        """Test that non-list messages raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_messages("not a list")  # type: ignore
        assert "must be a list" in str(exc_info.value)

    def test_validate_messages_empty(self) -> None:
        """Test that empty messages list raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_messages([])
        assert "cannot be empty" in str(exc_info.value)

    def test_validate_messages_invalid_item_type(self) -> None:
        """Test that non-dict message raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_messages(["not a dict"])  # type: ignore
        assert "must be a dictionary" in str(exc_info.value)

    def test_validate_messages_missing_role(self) -> None:
        """Test that message without role raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_messages([{"content": "Hello"}])
        assert "missing 'role'" in str(exc_info.value)

    def test_validate_messages_missing_content(self) -> None:
        """Test that message without content/tool_calls raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RequestValidator.validate_messages([{"role": "user"}])
        assert "content" in str(exc_info.value).lower()


class TestValidateProviderConfig:
    """Tests for validate_provider_config function."""

    def test_validate_complete_config(self) -> None:
        """Test validation of complete provider config."""
        config = {
            "api_key": "sk-1234567890abcdefghij",
            "model": "gpt-4",
            "timeout": 30,
            "max_retries": 3,
        }
        assert validate_provider_config("openai", config) is True

    def test_validate_minimal_config(self) -> None:
        """Test validation of minimal provider config."""
        config = {
            "api_key": "sk-1234567890abcdefghij",
            "model": "gpt-4",
        }
        assert validate_provider_config("openai", config) is True

    def test_validate_invalid_api_key(self) -> None:
        """Test that invalid API key raises error."""
        config = {
            "api_key": "invalid",
            "model": "gpt-4",
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_provider_config("openai", config)
        assert "Invalid API key format" in str(exc_info.value)

    def test_validate_invalid_timeout(self) -> None:
        """Test that invalid timeout raises error."""
        config = {
            "api_key": "sk-1234567890abcdefghij",
            "model": "gpt-4",
            "timeout": -5,
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_provider_config("openai", config)
        assert "Timeout" in str(exc_info.value)

    def test_validate_invalid_max_retries(self) -> None:
        """Test that invalid max_retries raises error."""
        config = {
            "api_key": "sk-1234567890abcdefghij",
            "model": "gpt-4",
            "max_retries": -1,
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_provider_config("openai", config)
        assert "max_retries" in str(exc_info.value)

    def test_validate_config_without_api_key(self) -> None:
        """Test validation of config without API key."""
        config = {
            "model": "gpt-4",
            "timeout": 30,
        }
        # Should not raise error if api_key is not in config
        assert validate_provider_config("openai", config) is True
