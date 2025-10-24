"""
Request normalization for different AI providers.

This module provides normalizers to convert FlexiAI's unified request format
to provider-specific API request formats.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from flexiai.exceptions import ValidationError
from flexiai.models import Message, UnifiedRequest


class RequestNormalizer(ABC):
    """
    Abstract base class for request normalization.

    Each provider should implement this class to convert UnifiedRequest
    objects into their specific API request format.
    """

    @abstractmethod
    def normalize(self, request: UnifiedRequest) -> Dict[str, Any]:
        """
        Normalize a unified request to provider-specific format.

        Args:
            request: Unified request object

        Returns:
            Dictionary containing provider-specific request parameters

        Raises:
            ValidationError: If request contains invalid parameters
        """
        pass

    @abstractmethod
    def normalize_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        Normalize message format to provider-specific format.

        Args:
            messages: List of unified message objects

        Returns:
            List of provider-specific message dictionaries

        Raises:
            ValidationError: If messages contain invalid data
        """
        pass

    def _validate_request(self, request: UnifiedRequest) -> None:
        """
        Validate that request contains required fields.

        Args:
            request: Unified request to validate

        Raises:
            ValidationError: If request is invalid
        """
        if not request.messages or len(request.messages) == 0:
            raise ValidationError("Request must contain at least one message")


class OpenAIRequestNormalizer(RequestNormalizer):
    """
    Request normalizer for OpenAI API.

    OpenAI is our reference implementation, so most fields map directly.
    """

    # Parameter mapping from UnifiedRequest to OpenAI API
    PARAMETER_MAPPING = {
        "temperature": "temperature",
        "max_tokens": "max_tokens",
        "top_p": "top_p",
        "frequency_penalty": "frequency_penalty",
        "presence_penalty": "presence_penalty",
        "stop": "stop",
        "stream": "stream",
        "tools": "tools",
        "tool_choice": "tool_choice",
        "response_format": "response_format",
        "seed": "seed",
        "user": "user",
    }

    def normalize(self, request: UnifiedRequest) -> Dict[str, Any]:
        """
        Normalize unified request to OpenAI API format.

        Args:
            request: Unified request object

        Returns:
            Dictionary containing OpenAI API request parameters

        Raises:
            ValidationError: If request is invalid

        Example:
            >>> normalizer = OpenAIRequestNormalizer()
            >>> request = UnifiedRequest(
            ...     messages=[Message(role="user", content="Hello")],
            ...     temperature=0.7
            ... )
            >>> api_request = normalizer.normalize(request)
        """
        self._validate_request(request)

        # Start with messages
        normalized = {
            "messages": self.normalize_messages(request.messages),
        }

        # Add optional parameters if present
        for unified_param, openai_param in self.PARAMETER_MAPPING.items():
            value = getattr(request, unified_param, None)
            if value is not None:
                normalized[openai_param] = value

        return normalized

    def normalize_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        Normalize messages to OpenAI format.

        Args:
            messages: List of unified message objects

        Returns:
            List of OpenAI-formatted message dictionaries

        Raises:
            ValidationError: If messages contain invalid data

        Example:
            >>> normalizer = OpenAIRequestNormalizer()
            >>> messages = [
            ...     Message(role="system", content="You are helpful"),
            ...     Message(role="user", content="Hello")
            ... ]
            >>> openai_messages = normalizer.normalize_messages(messages)
        """
        if not messages:
            raise ValidationError("Messages list cannot be empty")

        normalized_messages = []
        for msg in messages:
            # Start with required fields
            normalized_msg = {
                "role": msg.role,
                "content": msg.content,
            }

            # Add optional fields if present
            if msg.name is not None:
                normalized_msg["name"] = msg.name

            if msg.function_call is not None:
                normalized_msg["function_call"] = msg.function_call

            if msg.tool_calls is not None:
                normalized_msg["tool_calls"] = msg.tool_calls

            normalized_messages.append(normalized_msg)

        return normalized_messages

    def validate_model_support(self, model: str) -> bool:
        """
        Check if a model is supported by OpenAI.

        Args:
            model: Model name to validate

        Returns:
            True if model is supported

        Note:
            This is a basic check. Full validation should be done
            by the ModelValidator in utils/validators.py
        """
        supported_prefixes = [
            "gpt-4",
            "gpt-3.5",
            "gpt-4-turbo",
            "gpt-4o",
            "o1",
        ]
        return any(model.startswith(prefix) for prefix in supported_prefixes)
