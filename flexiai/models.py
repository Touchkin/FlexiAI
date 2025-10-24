"""
Data models for FlexiAI using Pydantic v2.

This module defines all data structures used throughout FlexiAI for type safety
and validation. All models use Pydantic v2 for schema validation and serialization.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class MessageRole(str, Enum):
    """Valid roles for chat messages."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class Message(BaseModel):
    """
    Represents a single message in a conversation.

    This is the unified message format used across all providers.
    Provider-specific normalizers will convert to/from this format.

    Attributes:
        role: The role of the message sender (system, user, assistant, function, tool)
        content: The text content of the message
        name: Optional name of the function/tool that created this message
        function_call: Optional function call details (deprecated, use tool_calls)
        tool_calls: Optional list of tool calls made by the assistant

    Example:
        >>> msg = Message(role="user", content="Hello, AI!")
        >>> print(msg.role)
        user
        >>> print(msg.content)
        Hello, AI!
    """

    role: MessageRole = Field(..., description="Role of the message sender")
    content: Optional[str] = Field(None, description="Text content of the message")
    name: Optional[str] = Field(None, description="Name of function/tool sender")
    function_call: Optional[Dict[str, Any]] = Field(
        None, description="Function call details (deprecated)"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="List of tool calls")

    model_config = {"use_enum_values": True, "str_strip_whitespace": True}

    @model_validator(mode="after")
    def validate_content(self) -> "Message":
        """Validate that content exists for non-function/tool messages."""
        # Content can be None if there are tool_calls or function_call
        if self.tool_calls or self.function_call:
            return self

        # Otherwise, content is required for user, assistant, and system messages
        if self.role in [MessageRole.USER, MessageRole.ASSISTANT, MessageRole.SYSTEM]:
            if self.content is None or (isinstance(self.content, str) and not self.content.strip()):
                raise ValueError(
                    f"Content is required for {self.role} messages and cannot be empty"
                )
        return self


class UsageInfo(BaseModel):
    """
    Token usage information for API calls.

    Attributes:
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total tokens used (prompt + completion)

    Example:
        >>> usage = UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        >>> print(usage.total_tokens)
        30
    """

    prompt_tokens: int = Field(..., ge=0, description="Number of tokens in prompt")
    completion_tokens: int = Field(..., ge=0, description="Number of tokens in completion")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")

    @model_validator(mode="after")
    def validate_total(self) -> "UsageInfo":
        """Validate that total_tokens equals prompt_tokens + completion_tokens."""
        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            self.total_tokens = self.prompt_tokens + self.completion_tokens
        return self


class UnifiedRequest(BaseModel):
    """
    Unified request format for chat completions across all providers.

    This standardized format is converted to provider-specific formats
    by the request normalizers.

    Attributes:
        messages: List of conversation messages
        temperature: Sampling temperature (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        top_p: Nucleus sampling parameter
        frequency_penalty: Frequency penalty (-2.0 to 2.0)
        presence_penalty: Presence penalty (-2.0 to 2.0)
        stop: Stop sequences
        stream: Whether to stream the response
        tools: List of available tools/functions
        tool_choice: Tool choice strategy
        response_format: Desired response format
        seed: Random seed for deterministic outputs
        user: User identifier for tracking

    Example:
        >>> request = UnifiedRequest(
        ...     messages=[Message(role="user", content="Hello!")],
        ...     temperature=0.7,
        ...     max_tokens=100
        ... )
        >>> print(len(request.messages))
        1
    """

    messages: List[Message] = Field(..., min_length=1, description="Conversation messages")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling")
    frequency_penalty: Optional[float] = Field(
        None, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Presence penalty")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    stream: bool = Field(False, description="Stream response")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="Available tools/functions")
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="Tool choice strategy"
    )
    response_format: Optional[Dict[str, Any]] = Field(
        None, description="Response format specification"
    )
    seed: Optional[int] = Field(None, description="Random seed for deterministic output")
    user: Optional[str] = Field(None, description="User identifier")

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: List[Message]) -> List[Message]:
        """Validate that messages list is not empty."""
        if not v:
            raise ValueError("Messages list cannot be empty")
        return v


class UnifiedResponse(BaseModel):
    """
    Unified response format for chat completions across all providers.

    This standardized format is created from provider-specific responses
    by the response normalizers.

    Attributes:
        content: The generated text content
        model: Model name used for generation
        provider: Provider name (openai, gemini, anthropic)
        usage: Token usage information
        finish_reason: Reason for completion (stop, length, content_filter, etc.)
        metadata: Provider-specific metadata
        tool_calls: Tool calls made by the assistant
        raw_response: Raw provider response (optional, for debugging)

    Example:
        >>> response = UnifiedResponse(
        ...     content="Hello! How can I help?",
        ...     model="gpt-4",
        ...     provider="openai",
        ...     usage=UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        ...     finish_reason="stop"
        ... )
        >>> print(response.content)
        Hello! How can I help?
    """

    content: str = Field(..., description="Generated text content")
    model: str = Field(..., description="Model name used")
    provider: str = Field(..., description="Provider name")
    usage: UsageInfo = Field(..., description="Token usage information")
    finish_reason: str = Field(..., description="Completion finish reason")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific metadata")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls made")
    raw_response: Optional[Dict[str, Any]] = Field(None, description="Raw provider response")


class ProviderConfig(BaseModel):
    """
    Configuration for a single GenAI provider.

    Attributes:
        name: Provider name (openai, gemini, anthropic)
        priority: Priority level (1 = highest, used for failover ordering)
        api_key: API key for authentication
        model: Model name to use
        base_url: Optional custom API base URL
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        config: Additional provider-specific configuration

    Example:
        >>> provider = ProviderConfig(
        ...     name="openai",
        ...     priority=1,
        ...     api_key="sk-...",
        ...     model="gpt-4-turbo-preview",
        ...     timeout=30
        ... )
        >>> print(provider.name)
        openai
    """

    name: str = Field(..., description="Provider name")
    priority: int = Field(..., ge=1, description="Priority level (1=highest)")
    api_key: str = Field(..., min_length=1, description="API key")
    model: str = Field(..., min_length=1, description="Model name")
    base_url: Optional[str] = Field(None, description="Custom API base URL")
    timeout: int = Field(30, ge=1, le=300, description="Request timeout (seconds)")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    config: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific config")

    model_config = {"str_strip_whitespace": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate provider name is one of the supported providers."""
        supported = ["openai", "gemini", "anthropic", "azure", "bedrock"]
        if v.lower() not in supported:
            raise ValueError(f"Provider '{v}' not supported. Supported providers: {supported}")
        return v.lower()

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key is not empty."""
        if not v or not v.strip():
            raise ValueError("API key cannot be empty")
        return v.strip()


class CircuitBreakerConfig(BaseModel):
    """
    Configuration for circuit breaker pattern.

    The circuit breaker prevents cascading failures by temporarily disabling
    failed providers and allowing them to recover.

    Attributes:
        failure_threshold: Number of consecutive failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: List of exception types to count as failures
        half_open_max_calls: Max calls allowed in half-open state

    Example:
        >>> cb_config = CircuitBreakerConfig(
        ...     failure_threshold=5,
        ...     recovery_timeout=60,
        ...     expected_exception=["APIError", "Timeout"]
        ... )
        >>> print(cb_config.failure_threshold)
        5
    """

    failure_threshold: int = Field(5, ge=1, description="Failures before opening circuit")
    recovery_timeout: int = Field(60, ge=1, description="Seconds before recovery attempt")
    expected_exception: List[str] = Field(
        default_factory=lambda: ["APIError", "Timeout", "RateLimitError"],
        description="Exception types to count as failures",
    )
    half_open_max_calls: int = Field(1, ge=1, description="Max calls in half-open state")


class RetryConfig(BaseModel):
    """
    Configuration for retry logic.

    Attributes:
        max_attempts: Maximum retry attempts
        backoff_factor: Exponential backoff multiplier
        max_backoff: Maximum backoff time in seconds
        retryable_errors: List of error types to retry

    Example:
        >>> retry_config = RetryConfig(max_attempts=3, backoff_factor=2)
        >>> print(retry_config.max_attempts)
        3
    """

    max_attempts: int = Field(3, ge=1, le=10, description="Maximum retry attempts")
    backoff_factor: float = Field(2.0, ge=1.0, description="Exponential backoff factor")
    max_backoff: int = Field(60, ge=1, description="Maximum backoff seconds")
    retryable_errors: List[str] = Field(
        default_factory=lambda: ["RateLimitError", "APIConnectionError", "Timeout"],
        description="Error types to retry",
    )


class LoggingConfig(BaseModel):
    """
    Configuration for logging.

    Attributes:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        file: Optional log file path
        format: Log message format
        max_bytes: Maximum log file size
        backup_count: Number of backup log files

    Example:
        >>> log_config = LoggingConfig(level="INFO", file="flexiai.log")
        >>> print(log_config.level)
        INFO
    """

    level: str = Field("INFO", description="Logging level")
    file: Optional[str] = Field(None, description="Log file path")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )
    max_bytes: int = Field(10485760, ge=1024, description="Max log file size")
    backup_count: int = Field(5, ge=0, description="Number of backup files")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()


class FlexiAIConfig(BaseModel):
    """
    Main configuration for FlexiAI client.

    This is the top-level configuration object that contains all settings
    for providers, circuit breaker, retry logic, and logging.

    Attributes:
        providers: List of provider configurations
        circuit_breaker: Circuit breaker configuration
        retry: Retry configuration
        logging: Logging configuration
        default_temperature: Default temperature for requests
        default_max_tokens: Default max tokens for requests

    Example:
        >>> config = FlexiAIConfig(
        ...     providers=[
        ...         ProviderConfig(
        ...             name="openai",
        ...             priority=1,
        ...             api_key="sk-...",
        ...             model="gpt-4-turbo-preview"
        ...         )
        ...     ]
        ... )
        >>> print(len(config.providers))
        1
    """

    providers: List[ProviderConfig] = Field(
        ..., min_length=1, description="Provider configurations"
    )
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=lambda: CircuitBreakerConfig(),
        description="Circuit breaker config",
    )
    retry: RetryConfig = Field(default_factory=lambda: RetryConfig(), description="Retry config")
    logging: LoggingConfig = Field(
        default_factory=lambda: LoggingConfig(), description="Logging config"
    )
    default_temperature: float = Field(0.7, ge=0.0, le=2.0, description="Default temperature")
    default_max_tokens: Optional[int] = Field(None, ge=1, description="Default max tokens")

    @field_validator("providers")
    @classmethod
    def validate_providers(cls, v: List[ProviderConfig]) -> List[ProviderConfig]:
        """Validate that providers list is not empty and priorities are unique."""
        if not v:
            raise ValueError("At least one provider must be configured")

        # Check for duplicate priorities
        priorities = [p.priority for p in v]
        if len(priorities) != len(set(priorities)):
            raise ValueError("Provider priorities must be unique")

        # Check for duplicate provider names
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            raise ValueError("Provider names must be unique")

        return v

    @model_validator(mode="after")
    def sort_providers_by_priority(self) -> "FlexiAIConfig":
        """Sort providers by priority (lower number = higher priority)."""
        self.providers = sorted(self.providers, key=lambda p: p.priority)
        return self

    def get_provider_by_name(self, name: str) -> Optional[ProviderConfig]:
        """
        Get a provider configuration by name.

        Args:
            name: Provider name to search for

        Returns:
            Provider configuration if found, None otherwise

        Example:
            >>> config = FlexiAIConfig(providers=[...])
            >>> openai = config.get_provider_by_name("openai")
        """
        for provider in self.providers:
            if provider.name == name:
                return provider
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of the configuration

        Example:
            >>> config = FlexiAIConfig(providers=[...])
            >>> config_dict = config.to_dict()
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlexiAIConfig":
        """
        Create configuration from dictionary.

        Args:
            data: Dictionary containing configuration data

        Returns:
            FlexiAIConfig instance

        Example:
            >>> config_dict = {"providers": [...]}
            >>> config = FlexiAIConfig.from_dict(config_dict)
        """
        return cls(**data)
