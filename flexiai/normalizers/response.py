"""
Response normalization for different AI providers.

This module provides normalizers to convert provider-specific API responses
to FlexiAI's unified response format.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from flexiai.exceptions import InvalidResponseError
from flexiai.models import UnifiedResponse, UsageInfo


class ResponseNormalizer(ABC):
    """
    Abstract base class for response normalization.

    Each provider should implement this class to convert their API responses
    into UnifiedResponse objects.
    """

    @abstractmethod
    def normalize(
        self, response: Dict[str, Any], provider_name: str, model: str
    ) -> UnifiedResponse:
        """
        Normalize a provider-specific response to unified format.

        Args:
            response: Provider-specific response dictionary
            provider_name: Name of the provider
            model: Model name used for the request

        Returns:
            Unified response object

        Raises:
            InvalidResponseError: If response is malformed or missing required fields
        """
        pass

    @abstractmethod
    def normalize_error(self, error_response: Dict[str, Any], provider_name: str) -> Dict[str, Any]:
        """
        Normalize provider-specific error responses.

        Args:
            error_response: Provider error response
            provider_name: Name of the provider

        Returns:
            Dictionary with normalized error information
        """
        pass

    def _validate_response(self, response: Dict[str, Any]) -> None:
        """
        Validate that response contains minimum required fields.

        Args:
            response: Response to validate

        Raises:
            InvalidResponseError: If response is invalid
        """
        if not isinstance(response, dict):
            raise InvalidResponseError("Response must be a dictionary")


class OpenAIResponseNormalizer(ResponseNormalizer):
    """
    Response normalizer for OpenAI API.

    Converts OpenAI API responses to UnifiedResponse format.
    """

    def normalize(
        self, response: Dict[str, Any], provider_name: str = "openai", model: str = ""
    ) -> UnifiedResponse:
        """
        Normalize OpenAI response to unified format.

        Args:
            response: OpenAI API response dictionary
            provider_name: Name of the provider (default: "openai")
            model: Model name (will be extracted from response if not provided)

        Returns:
            Unified response object

        Raises:
            InvalidResponseError: If response is malformed

        Example:
            >>> normalizer = OpenAIResponseNormalizer()
            >>> openai_response = {
            ...     "id": "chatcmpl-123",
            ...     "choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}],
            ...     "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            ...     "model": "gpt-4"
            ... }
            >>> unified = normalizer.normalize(openai_response)
        """
        self._validate_response(response)

        # Validate required fields
        if "choices" not in response or not response["choices"]:
            raise InvalidResponseError("Response must contain at least one choice")

        # Extract first choice (main response)
        choice = response["choices"][0]

        # Extract content
        content = self._extract_content(choice)

        # Extract model (prefer parameter over response)
        # This allows provider to override response model with config model
        response_model = model if model else response.get("model", "")
        if not response_model:
            raise InvalidResponseError("Model name must be provided or in response")

        # Extract usage information
        usage = self._extract_usage(response.get("usage", {}))

        # Extract finish reason
        finish_reason = choice.get("finish_reason") or "unknown"

        # Extract metadata
        metadata = {
            "id": response.get("id"),
            "created": response.get("created"),
            "system_fingerprint": response.get("system_fingerprint"),
            "object": response.get("object"),
        }

        # Remove None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return UnifiedResponse(
            content=content,
            model=response_model,
            provider=provider_name,
            usage=usage,
            finish_reason=finish_reason,
            metadata=metadata if metadata else None,
        )

    def _extract_content(self, choice: Dict[str, Any]) -> str:
        """
        Extract content from OpenAI choice object.

        Args:
            choice: OpenAI choice dictionary

        Returns:
            Extracted content string

        Raises:
            InvalidResponseError: If content cannot be extracted
        """
        # Try to get message content
        if "message" in choice:
            message = choice["message"]
            if "content" in message and message["content"] is not None:
                return message["content"]
            # Handle function/tool calls
            if "function_call" in message:
                return str(message["function_call"])
            if "tool_calls" in message:
                return str(message["tool_calls"])

        # Try to get delta content (for streaming)
        if "delta" in choice:
            delta = choice["delta"]
            if "content" in delta and delta["content"] is not None:
                return delta["content"]

        # If we can't find content, raise error
        raise InvalidResponseError("Could not extract content from response")

    def _extract_usage(self, usage_data: Dict[str, Any]) -> UsageInfo:
        """
        Extract usage information from OpenAI response.

        Args:
            usage_data: OpenAI usage dictionary

        Returns:
            UsageInfo object

        Note:
            If usage data is missing, returns UsageInfo with 0 tokens
        """
        return UsageInfo(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

    def normalize_error(
        self, error_response: Dict[str, Any], provider_name: str = "openai"
    ) -> Dict[str, Any]:
        """
        Normalize OpenAI error response.

        Args:
            error_response: OpenAI error response
            provider_name: Name of the provider

        Returns:
            Dictionary with normalized error information

        Example:
            >>> normalizer = OpenAIResponseNormalizer()
            >>> error = {
            ...     "error": {
            ...         "message": "Invalid API key",
            ...         "type": "invalid_request_error",
            ...         "code": "invalid_api_key"
            ...     }
            ... }
            >>> normalized = normalizer.normalize_error(error)
        """
        if "error" in error_response:
            error = error_response["error"]
            return {
                "provider": provider_name,
                "message": error.get("message", "Unknown error"),
                "type": error.get("type", "unknown"),
                "code": error.get("code"),
                "param": error.get("param"),
            }

        # Fallback for unexpected error format
        return {
            "provider": provider_name,
            "message": str(error_response),
            "type": "unknown",
        }

    def is_streaming_response(self, response: Dict[str, Any]) -> bool:
        """
        Check if response is from a streaming request.

        Args:
            response: Response to check

        Returns:
            True if response is from streaming
        """
        return response.get("object") == "chat.completion.chunk"


class GeminiResponseNormalizer(ResponseNormalizer):
    """
    Response normalizer for Google Gemini API.

    Converts Gemini API responses to UnifiedResponse format.
    Gemini has a different response structure:
    - Uses 'candidates' instead of 'choices'
    - Content is in candidates[0].content.parts[0].text
    - Usage is in usageMetadata with different field names
    - Has safety_ratings for content filtering
    """

    # Finish reason mapping from Gemini to unified format
    FINISH_REASON_MAPPING = {
        "STOP": "stop",
        "MAX_TOKENS": "length",
        "SAFETY": "content_filter",
        "RECITATION": "content_filter",
        "OTHER": "unknown",
        "FINISH_REASON_UNSPECIFIED": "unknown",
    }

    def normalize(
        self, response: Dict[str, Any], provider_name: str = "gemini", model: str = ""
    ) -> UnifiedResponse:
        """
        Normalize Gemini response to unified format.

        Args:
            response: Gemini API response dictionary
            provider_name: Name of the provider (default: "gemini")
            model: Model name (will be extracted from response if not provided)

        Returns:
            Unified response object

        Raises:
            InvalidResponseError: If response is malformed or blocked

        Example:
            >>> normalizer = GeminiResponseNormalizer()
            >>> gemini_response = {
            ...     "candidates": [{
            ...         "content": {"parts": [{"text": "Hello!"}]},
            ...         "finishReason": "STOP"
            ...     }],
            ...     "usageMetadata": {
            ...         "promptTokenCount": 10,
            ...         "candidatesTokenCount": 5,
            ...         "totalTokenCount": 15
            ...     },
            ...     "modelVersion": "gemini-2.0-flash"
            ... }
            >>> unified = normalizer.normalize(gemini_response)
        """
        self._validate_response(response)

        # Check if the response was blocked
        if "promptFeedback" in response:
            prompt_feedback = response["promptFeedback"]
            if "blockReason" in prompt_feedback:
                block_reason = prompt_feedback["blockReason"]
                safety_ratings = prompt_feedback.get("safetyRatings", [])
                raise InvalidResponseError(
                    f"Gemini blocked the request: {block_reason}",
                    details={
                        "block_reason": block_reason,
                        "safety_ratings": safety_ratings,
                    },
                )

        # Validate required fields
        if "candidates" not in response or not response["candidates"]:
            # Check if there's a prompt feedback explaining why no candidates
            if "promptFeedback" in response:
                prompt_feedback = response["promptFeedback"]
                raise InvalidResponseError(
                    "No candidates in response",
                    details={"prompt_feedback": prompt_feedback},
                )
            raise InvalidResponseError("Response must contain at least one candidate")

        # Extract first candidate (main response)
        candidate = response["candidates"][0]

        # Extract content
        content = self._extract_content(candidate)

        # Extract model (prefer parameter over response)
        response_model = model if model else response.get("modelVersion", "")
        if not response_model:
            raise InvalidResponseError("Model name must be provided or in response")

        # Extract usage information
        usage = self._extract_usage(response.get("usageMetadata", {}))

        # Extract finish reason
        finish_reason = self._map_finish_reason(candidate.get("finishReason", "UNKNOWN"))

        # Extract metadata
        metadata = {
            "candidate_count": len(response.get("candidates", [])),
            "safety_ratings": candidate.get("safetyRatings"),
            "citation_metadata": candidate.get("citationMetadata"),
            "token_count": candidate.get("tokenCount"),
            "grounding_attributions": candidate.get("groundingAttributions"),
            "response_id": response.get("responseId"),
        }

        # Remove None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return UnifiedResponse(
            content=content,
            model=response_model,
            provider=provider_name,
            usage=usage,
            finish_reason=finish_reason,
            metadata=metadata if metadata else None,
        )

    def _extract_content(self, candidate: Dict[str, Any]) -> str:
        """
        Extract content from Gemini candidate object.

        Gemini structure: candidates[0].content.parts[0].text

        Args:
            candidate: Gemini candidate dictionary

        Returns:
            Extracted content string

        Raises:
            InvalidResponseError: If content cannot be extracted
        """
        # Check if candidate has content
        if "content" not in candidate:
            # Check if it was blocked for safety
            if "safetyRatings" in candidate:
                safety_ratings = candidate["safetyRatings"]
                blocked = any(rating.get("blocked", False) for rating in safety_ratings)
                if blocked:
                    raise InvalidResponseError(
                        "Content was blocked by safety filters",
                        details={"safety_ratings": safety_ratings},
                    )
            raise InvalidResponseError("Candidate does not contain content")

        content = candidate["content"]

        # Extract text from parts
        if "parts" not in content or not content["parts"]:
            raise InvalidResponseError("Content does not contain parts")

        # Combine all text parts (Gemini can return multiple parts)
        text_parts = []
        for part in content["parts"]:
            if "text" in part:
                text_parts.append(part["text"])

        if not text_parts:
            raise InvalidResponseError("No text content found in parts")

        # Join all parts with newline
        return "\n".join(text_parts)

    def _extract_usage(self, usage_data: Dict[str, Any]) -> UsageInfo:
        """
        Extract usage information from Gemini response.

        Gemini uses different field names:
        - promptTokenCount -> prompt_tokens
        - candidatesTokenCount -> completion_tokens
        - totalTokenCount -> total_tokens

        Args:
            usage_data: Gemini usageMetadata dictionary

        Returns:
            UsageInfo object

        Note:
            If usage data is missing, returns UsageInfo with 0 tokens
        """
        return UsageInfo(
            prompt_tokens=usage_data.get("promptTokenCount", 0),
            completion_tokens=usage_data.get("candidatesTokenCount", 0),
            total_tokens=usage_data.get("totalTokenCount", 0),
        )

    def _map_finish_reason(self, gemini_reason: str) -> str:
        """
        Map Gemini finish reason to unified format.

        Args:
            gemini_reason: Gemini finish reason

        Returns:
            Unified finish reason string
        """
        return self.FINISH_REASON_MAPPING.get(gemini_reason, "unknown")

    def normalize_error(
        self, error_response: Dict[str, Any], provider_name: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Normalize Gemini error response.

        Args:
            error_response: Gemini error response
            provider_name: Name of the provider

        Returns:
            Dictionary with normalized error information

        Example:
            >>> normalizer = GeminiResponseNormalizer()
            >>> error = {
            ...     "error": {
            ...         "message": "API key not valid",
            ...         "status": "INVALID_ARGUMENT",
            ...         "code": 400
            ...     }
            ... }
            >>> normalized = normalizer.normalize_error(error)
        """
        if "error" in error_response:
            error = error_response["error"]
            return {
                "provider": provider_name,
                "message": error.get("message", "Unknown error"),
                "status": error.get("status", "unknown"),
                "code": error.get("code"),
                "details": error.get("details"),
            }

        # Fallback for unexpected error format
        return {
            "provider": provider_name,
            "message": str(error_response),
            "status": "unknown",
        }

    def is_streaming_response(self, response: Dict[str, Any]) -> bool:
        """
        Check if response is from a streaming request.

        Args:
            response: Response to check

        Returns:
            True if response is from streaming

        Note:
            Gemini streaming responses come in chunks with similar structure.
            This can be enhanced based on actual streaming behavior.
        """
        # Gemini streaming responses have similar structure to non-streaming
        # We can check if it's a partial response or has specific streaming indicators
        # For now, we'll use a simple heuristic
        return "candidates" in response and len(response.get("candidates", [])) == 1
