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


class GeminiRequestNormalizer(RequestNormalizer):
    """
    Request normalizer for Google Gemini API.

    Gemini uses a different message format and parameter names compared to OpenAI:
    - Role 'assistant' maps to 'model'
    - Uses 'contents' instead of 'messages'
    - max_tokens maps to maxOutputTokens in generationConfig
    - System messages are passed via system_instruction parameter
    """

    # Parameter mapping from UnifiedRequest to Gemini generationConfig
    PARAMETER_MAPPING = {
        "temperature": "temperature",
        "max_tokens": "maxOutputTokens",
        "top_p": "topP",
        "top_k": "topK",
        "stop": "stopSequences",
        "seed": "seed",
        "presence_penalty": "presencePenalty",
        "frequency_penalty": "frequencyPenalty",
    }

    # Gemini role mapping
    ROLE_MAPPING = {
        "system": None,  # System messages are handled separately
        "user": "user",
        "assistant": "model",  # Gemini uses 'model' instead of 'assistant'
        "function": "function",  # Function results
    }

    def normalize(self, request: UnifiedRequest) -> Dict[str, Any]:
        """
        Normalize unified request to Gemini API format.

        Args:
            request: Unified request object

        Returns:
            Dictionary containing Gemini API request parameters

        Raises:
            ValidationError: If request is invalid

        Example:
            >>> normalizer = GeminiRequestNormalizer()
            >>> request = UnifiedRequest(
            ...     messages=[Message(role="user", content="Hello")],
            ...     temperature=0.7,
            ...     max_tokens=1000
            ... )
            >>> api_request = normalizer.normalize(request)
        """
        self._validate_request(request)

        # Separate system messages from conversation messages
        system_messages = [msg for msg in request.messages if msg.role == "system"]
        conversation_messages = [msg for msg in request.messages if msg.role != "system"]

        # Build normalized request
        normalized = {}

        # Add contents (conversation messages)
        if conversation_messages:
            normalized["contents"] = self.normalize_messages(conversation_messages)

        # Handle system instructions (Gemini's way of handling system messages)
        if system_messages:
            # Combine all system messages into one system_instruction
            system_content = " ".join(msg.content for msg in system_messages)
            normalized["system_instruction"] = {"parts": [{"text": system_content}]}

        # Build generationConfig for optional parameters
        generation_config = {}
        for unified_param, gemini_param in self.PARAMETER_MAPPING.items():
            value = getattr(request, unified_param, None)
            if value is not None:
                generation_config[gemini_param] = value

        if generation_config:
            normalized["generationConfig"] = generation_config

        # Handle safety settings if provided in extra parameters
        # (This is optional - we can add default safety settings if needed)
        if hasattr(request, "safety_settings"):
            normalized["safetySettings"] = request.safety_settings

        return normalized

    def normalize_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        Normalize messages to Gemini format.

        Gemini uses a different structure:
        - role: 'user' or 'model' (not 'assistant')
        - parts: list of content parts (text, images, etc.)

        Args:
            messages: List of unified message objects (excluding system messages)

        Returns:
            List of Gemini-formatted message dictionaries

        Raises:
            ValidationError: If messages contain invalid data

        Example:
            >>> normalizer = GeminiRequestNormalizer()
            >>> messages = [
            ...     Message(role="user", content="Hello"),
            ...     Message(role="assistant", content="Hi there!")
            ... ]
            >>> gemini_messages = normalizer.normalize_messages(messages)
        """
        if not messages:
            raise ValidationError("Messages list cannot be empty")

        normalized_messages = []
        for msg in messages:
            # Map role to Gemini format
            gemini_role = self.ROLE_MAPPING.get(msg.role)

            if gemini_role is None:
                # Skip system messages (they're handled separately)
                continue

            # Build Gemini message format
            normalized_msg = {"role": gemini_role, "parts": [{"text": msg.content}]}

            # Note: Gemini supports multimodal parts (images, etc.)
            # For now, we're only supporting text content
            # Future enhancement: support images and other modalities

            normalized_messages.append(normalized_msg)

        return normalized_messages

    def validate_model_support(self, model: str) -> bool:
        """
        Check if a model is supported by Gemini.

        Args:
            model: Model name to validate

        Returns:
            True if model is supported

        Note:
            This is a basic check. Full validation should be done
            by the ModelValidator in utils/validators.py
        """
        supported_prefixes = [
            "gemini-2.5",
            "gemini-2.0",
            "gemini-1.5",
            "gemini-pro",
            "gemini-ultra",
        ]
        return any(model.startswith(prefix) for prefix in supported_prefixes)


class ClaudeRequestNormalizer(RequestNormalizer):
    """
    Request normalizer for Anthropic Claude API.

    Key differences from OpenAI:
    - System messages are separate (not in messages array)
    - max_tokens is REQUIRED
    - No consecutive messages with same role
    - Uses stop_sequences instead of stop
    - Supports top_k parameter (Claude-specific)
    """

    # Parameter mapping from UnifiedRequest to Claude API
    PARAMETER_MAPPING = {
        "temperature": "temperature",
        "max_tokens": "max_tokens",
        "top_p": "top_p",
        "stop": "stop_sequences",  # Claude uses stop_sequences
    }

    def normalize(self, request: UnifiedRequest) -> Dict[str, Any]:
        """
        Normalize unified request to Claude Messages API format.

        Args:
            request: Unified request object

        Returns:
            Dictionary with Claude-specific request parameters

        Raises:
            ValidationError: If request contains invalid parameters
        """
        self._validate_request(request)

        # Separate system messages from conversation messages
        system_messages = []
        conversation_messages = []

        for msg in request.messages:
            if msg.role == "system":
                system_messages.append(msg.content)
            else:
                conversation_messages.append(msg)

        # Build base parameters
        params: Dict[str, Any] = {}

        # Add system instruction if present (Claude uses separate 'system' parameter)
        if system_messages:
            # Combine multiple system messages with newlines
            params["system"] = "\n\n".join(system_messages)

        # Normalize conversation messages (user/assistant only)
        params["messages"] = self.normalize_messages(conversation_messages)

        # Map parameters from unified format to Claude format
        for unified_param, claude_param in self.PARAMETER_MAPPING.items():
            value = getattr(request, unified_param, None)
            if value is not None:
                # Special handling for stop_sequences
                if unified_param == "stop":
                    # Convert single stop to list if needed
                    if isinstance(value, str):
                        params[claude_param] = [value]
                    else:
                        params[claude_param] = value
                else:
                    params[claude_param] = value

        # Claude REQUIRES max_tokens - set default if not provided
        if "max_tokens" not in params:
            params["max_tokens"] = 4096  # Claude default

        # Add Claude-specific parameters if present in request config
        if hasattr(request, "provider_params") and request.provider_params:
            # top_k is Claude-specific
            if "top_k" in request.provider_params:
                params["top_k"] = request.provider_params["top_k"]

        # Handle streaming
        if request.stream:
            params["stream"] = True

        return params

    def normalize_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        Normalize messages to Claude format.

        Claude requirements:
        - Only user and assistant roles (system handled separately)
        - No consecutive messages with same role
        - Messages must alternate between user and assistant

        Args:
            messages: List of message objects (no system messages)

        Returns:
            List of Claude-formatted message dictionaries

        Raises:
            ValidationError: If messages violate Claude constraints
        """
        normalized_messages = []
        last_role = None

        for msg in messages:
            # Skip system messages (already handled)
            if msg.role == "system":
                continue

            # Map assistant role to assistant (same as OpenAI)
            role = msg.role
            if role not in ["user", "assistant"]:
                raise ValidationError(
                    f"Claude only supports 'user' and 'assistant' roles, got: {role}"
                )

            # Check for consecutive same-role messages
            if last_role == role:
                raise ValidationError(
                    f"Claude does not support consecutive messages with the same role. "
                    f"Found consecutive '{role}' messages. Messages must alternate between "
                    f"user and assistant."
                )

            normalized_msg = {"role": role, "content": msg.content}

            normalized_messages.append(normalized_msg)
            last_role = role

        return normalized_messages

    def validate_model_support(self, model: str) -> bool:
        """
        Check if a model is supported by Claude.

        Args:
            model: Model name to validate

        Returns:
            True if model is supported

        Note:
            This is a basic check. Full validation should be done
            by the ModelValidator in utils/validators.py
        """
        supported_models = [
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-3-haiku",
            "claude-3-5-sonnet",
            "claude-3-5-haiku",
        ]
        return any(model.startswith(prefix) for prefix in supported_models)
