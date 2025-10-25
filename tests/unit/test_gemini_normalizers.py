"""
Unit tests for Gemini request and response normalizers.

Tests the normalization of requests and responses between FlexiAI's
unified format and Gemini's API format.
"""

from unittest.mock import Mock

import pytest

from flexiai.models import Message, UnifiedRequest
from flexiai.normalizers.request import GeminiRequestNormalizer
from flexiai.normalizers.response import GeminiResponseNormalizer


class TestGeminiRequestNormalizer:
    """Tests for GeminiRequestNormalizer."""

    @pytest.fixture
    def normalizer(self):
        """Fixture for request normalizer."""
        return GeminiRequestNormalizer()

    def test_basic_message_normalization(self, normalizer):
        """Test basic message format conversion."""
        request = UnifiedRequest(
            messages=[
                Message(role="user", content="Hello, Gemini!"),
            ],
        )

        normalized = normalizer.normalize(request)

        assert "contents" in normalized
        assert len(normalized["contents"]) == 1
        assert normalized["contents"][0]["role"] == "user"
        assert normalized["contents"][0]["parts"][0]["text"] == "Hello, Gemini!"

    def test_role_mapping_assistant_to_model(self, normalizer):
        """Test that 'assistant' role is mapped to 'model' for Gemini."""
        request = UnifiedRequest(
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there!"),
                Message(role="user", content="How are you?"),
            ],
        )

        normalized = normalizer.normalize(request)

        assert len(normalized["contents"]) == 3
        assert normalized["contents"][0]["role"] == "user"
        assert normalized["contents"][1]["role"] == "model"  # assistant -> model
        assert normalized["contents"][2]["role"] == "user"

    def test_system_message_handling(self, normalizer):
        """Test that system messages are handled separately."""
        request = UnifiedRequest(
            messages=[
                Message(role="system", content="You are a helpful assistant."),
                Message(role="user", content="Hello"),
            ],
        )

        normalized = normalizer.normalize(request)

        # System message should be in system_instruction
        assert "system_instruction" in normalized
        assert (
            normalized["system_instruction"]["parts"][0]["text"] == "You are a helpful assistant."
        )

        # Contents should only have the user message
        assert len(normalized["contents"]) == 1
        assert normalized["contents"][0]["role"] == "user"

    def test_multiple_system_messages_combined(self, normalizer):
        """Test that multiple system messages are combined."""
        request = UnifiedRequest(
            messages=[
                Message(role="system", content="You are helpful."),
                Message(role="system", content="You are concise."),
                Message(role="user", content="Hello"),
            ],
        )

        normalized = normalizer.normalize(request)

        # System messages should be combined
        assert "system_instruction" in normalized
        system_text = normalized["system_instruction"]["parts"][0]["text"]
        assert "You are helpful." in system_text
        assert "You are concise." in system_text

    def test_parameter_mapping_temperature(self, normalizer):
        """Test temperature parameter mapping."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            temperature=0.8,
        )

        normalized = normalizer.normalize(request)

        assert "generationConfig" in normalized
        assert normalized["generationConfig"]["temperature"] == 0.8

    def test_parameter_mapping_max_tokens(self, normalizer):
        """Test max_tokens to maxOutputTokens mapping."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            max_tokens=1000,
        )

        normalized = normalizer.normalize(request)

        assert "generationConfig" in normalized
        assert normalized["generationConfig"]["maxOutputTokens"] == 1000

    def test_parameter_mapping_top_p(self, normalizer):
        """Test top_p parameter mapping."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            top_p=0.95,
        )

        normalized = normalizer.normalize(request)

        assert "generationConfig" in normalized
        assert normalized["generationConfig"]["topP"] == 0.95

    def test_parameter_mapping_stop_sequences(self, normalizer):
        """Test stop sequences parameter mapping."""
        request = UnifiedRequest(
            messages=[Message(role="user", content="Hello")],
            stop=["END", "STOP"],
        )

        normalized = normalizer.normalize(request)

        assert "generationConfig" in normalized
        assert normalized["generationConfig"]["stopSequences"] == ["END", "STOP"]

    def test_all_parameters_together(self, normalizer):
        """Test normalization with all parameters."""
        request = UnifiedRequest(
            messages=[
                Message(role="system", content="Be helpful."),
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi!"),
                Message(role="user", content="Tell me more"),
            ],
            temperature=0.7,
            max_tokens=500,
            top_p=0.9,
            stop=["END"],
        )

        normalized = normalizer.normalize(request)

        # Check system instruction
        assert "system_instruction" in normalized

        # Check contents (3 messages: user, assistant, user)
        assert len(normalized["contents"]) == 3

        # Check generation config
        assert normalized["generationConfig"]["temperature"] == 0.7
        assert normalized["generationConfig"]["maxOutputTokens"] == 500
        assert normalized["generationConfig"]["topP"] == 0.9
        assert normalized["generationConfig"]["stopSequences"] == ["END"]

    def test_empty_messages_raises_error(self, normalizer):
        """Test that empty messages list raises ValidationError."""
        # Pydantic already validates this at model level
        with pytest.raises(Exception):  # ValidationError from pydantic
            _ = UnifiedRequest(messages=[])

    def test_model_support_validation(self, normalizer):
        """Test model support validation."""
        assert normalizer.validate_model_support("gemini-2.5-pro") is True
        assert normalizer.validate_model_support("gemini-2.0-flash") is True
        assert normalizer.validate_model_support("gemini-1.5-pro") is True
        assert normalizer.validate_model_support("gemini-pro") is True
        assert normalizer.validate_model_support("gpt-4") is False
        assert normalizer.validate_model_support("claude-3") is False


class TestGeminiResponseNormalizer:
    """Tests for GeminiResponseNormalizer."""

    @pytest.fixture
    def normalizer(self):
        """Fixture for response normalizer."""
        return GeminiResponseNormalizer()

    def test_basic_response_normalization(self, normalizer):
        """Test basic response normalization."""
        # Mock Gemini response
        from google.genai.types import FinishReason

        mock_response = Mock()
        mock_response.text = "Hello! How can I help you today?"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="Hello! How can I help you today?")]
        mock_response.usage_metadata = Mock(
            prompt_token_count=10, candidates_token_count=15, total_token_count=25
        )

        unified_response = normalizer.normalize(
            mock_response, model="gemini-2.0-flash-exp", provider="gemini"
        )

        assert unified_response.content == "Hello! How can I help you today?"
        assert unified_response.model == "gemini-2.0-flash-exp"
        assert unified_response.provider == "gemini"
        assert unified_response.usage.prompt_tokens == 10
        assert unified_response.usage.completion_tokens == 15
        assert unified_response.usage.total_tokens == 25
        assert unified_response.finish_reason == "stop"

    def test_finish_reason_stop(self, normalizer):
        """Test STOP finish reason normalization."""
        from google.genai.types import FinishReason

        mock_response = Mock()
        mock_response.text = "Done"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="Done")]
        mock_response.usage_metadata = Mock(
            prompt_token_count=5, candidates_token_count=5, total_token_count=10
        )

        unified_response = normalizer.normalize(mock_response, "gemini-2.0-flash-exp", "gemini")
        assert unified_response.finish_reason == "stop"

    def test_finish_reason_max_tokens(self, normalizer):
        """Test MAX_TOKENS finish reason normalization."""
        from google.genai.types import FinishReason

        mock_response = Mock()
        mock_response.text = "Incomplete"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = FinishReason.MAX_TOKENS
        mock_response.candidates[0].content.parts = [Mock(text="Incomplete")]
        mock_response.usage_metadata = Mock(
            prompt_token_count=5, candidates_token_count=100, total_token_count=105
        )

        unified_response = normalizer.normalize(mock_response, "gemini-2.0-flash-exp", "gemini")
        assert unified_response.finish_reason == "length"

    def test_finish_reason_safety(self, normalizer):
        """Test SAFETY finish reason normalization."""
        from google.genai.types import FinishReason

        mock_response = Mock()
        mock_response.text = None
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = FinishReason.SAFETY
        mock_response.candidates[0].content = None

        # Should raise exception for blocked content
        with pytest.raises(Exception):  # Provider will handle this
            normalizer.normalize(mock_response, "gemini-2.0-flash-exp", "gemini")

    def test_finish_reason_other(self, normalizer):
        """Test OTHER/RECITATION finish reason normalization."""
        from google.genai.types import FinishReason

        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = FinishReason.OTHER
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.usage_metadata = Mock(
            prompt_token_count=5, candidates_token_count=5, total_token_count=10
        )

        unified_response = normalizer.normalize(mock_response, "gemini-2.0-flash-exp", "gemini")
        assert unified_response.finish_reason == "stop"  # Default to stop for OTHER

    def test_usage_metadata_extraction(self, normalizer):
        """Test token usage metadata extraction."""
        from google.genai.types import FinishReason

        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.usage_metadata = Mock(
            prompt_token_count=100, candidates_token_count=50, total_token_count=150
        )

        unified_response = normalizer.normalize(mock_response, "gemini-2.0-flash-exp", "gemini")

        assert unified_response.usage.prompt_tokens == 100
        assert unified_response.usage.completion_tokens == 50
        assert unified_response.usage.total_tokens == 150

    def test_missing_usage_metadata(self, normalizer):
        """Test handling of missing usage metadata."""
        from google.genai.types import FinishReason

        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.usage_metadata = None

        unified_response = normalizer.normalize(mock_response, "gemini-2.0-flash-exp", "gemini")

        # Should handle missing usage gracefully
        assert unified_response.usage.prompt_tokens == 0
        assert unified_response.usage.completion_tokens == 0
        assert unified_response.usage.total_tokens == 0

    def test_metadata_preservation(self, normalizer):
        """Test that Gemini-specific metadata is preserved."""
        from google.genai.types import FinishReason

        mock_response = Mock()
        mock_response.text = "Response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = FinishReason.STOP
        mock_response.candidates[0].content.parts = [Mock(text="Response")]
        mock_response.candidates[0].safety_ratings = [
            Mock(category="HARM_CATEGORY_HATE_SPEECH", probability="NEGLIGIBLE")
        ]
        mock_response.usage_metadata = Mock(
            prompt_token_count=10, candidates_token_count=10, total_token_count=20
        )

        unified_response = normalizer.normalize(mock_response, "gemini-2.0-flash-exp", "gemini")

        # Gemini-specific metadata should be in the metadata field
        assert "safety_ratings" in unified_response.metadata
        assert len(unified_response.metadata["safety_ratings"]) > 0
