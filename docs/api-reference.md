# FlexiAI API Reference

Complete API documentation for FlexiAI.

## Table of Contents

- [Client API](#client-api)
- [Configuration](#configuration)
- [Models](#models)
- [Exceptions](#exceptions)
- [Providers](#providers)
- [Circuit Breaker](#circuit-breaker)
- [Utilities](#utilities)

## Client API

### FlexiAI

Main client class for interacting with GenAI providers.

```python
from flexiai import FlexiAI, FlexiAIConfig

client = FlexiAI(config=FlexiAIConfig(...))
```

#### Methods

##### `__init__(config: FlexiAIConfig)`

Initialize FlexiAI client with configuration.

**Parameters**:
- `config` (FlexiAIConfig): Configuration object with providers and settings

**Example**:
```python
config = FlexiAIConfig(
    providers=[...],
    circuit_breaker=CircuitBreakerConfig(...)
)
client = FlexiAI(config=config)
```

##### `chat_completion(messages, **kwargs) -> UnifiedResponse`

Generate a chat completion using the configured providers.

**Parameters**:
- `messages` (List[Dict[str, str]]): List of message dictionaries with 'role' and 'content'
- `temperature` (float, optional): Sampling temperature (0.0-2.0). Default: 0.7
- `max_tokens` (int, optional): Maximum tokens to generate
- `top_p` (float, optional): Nucleus sampling parameter (0.0-1.0)
- `frequency_penalty` (float, optional): Frequency penalty (-2.0 to 2.0)
- `presence_penalty` (float, optional): Presence penalty (-2.0 to 2.0)
- `stop` (Union[str, List[str]], optional): Stop sequences
- `n` (int, optional): Number of completions to generate

**Returns**:
- `UnifiedResponse`: Response object with content, metadata, and usage information

**Raises**:
- `ValidationError`: If parameters are invalid
- `AllProvidersFailedError`: If all configured providers fail
- `CircuitBreakerOpenError`: If circuit breaker is open

**Example**:
```python
response = client.chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "What is Python?"}
    ],
    temperature=0.7,
    max_tokens=500
)
print(response.content)
```

##### `get_provider_status() -> Dict[str, Dict[str, Any]]`

Get status of all configured providers.

**Returns**:
Dictionary mapping provider names to status information:
```python
{
    "openai-1": {
        "healthy": True,
        "circuit_breaker": {
            "state": "CLOSED",
            "failures": 0,
            "successes": 10
        },
        "total_requests": 15,
        "successful_requests": 12,
        "failed_requests": 3
    }
}
```

**Example**:
```python
status = client.get_provider_status()
for name, info in status.items():
    print(f"{name}: {info['circuit_breaker']['state']}")
```

##### `get_request_stats() -> Dict[str, Any]`

Get aggregate statistics for all requests.

**Returns**:
```python
{
    "total_requests": 100,
    "successful_requests": 95,
    "failed_requests": 5,
    "providers_used": {"openai": 95, "backup": 5}
}
```

##### `get_last_used_provider() -> Optional[str]`

Get the name of the last provider that successfully handled a request.

**Returns**:
- `str` or `None`: Provider name or None if no requests made

##### `reset_circuit_breakers() -> None`

Manually reset all circuit breakers to CLOSED state.

**Example**:
```python
client.reset_circuit_breakers()
```

##### `set_primary_provider(provider_name: str) -> None`

Set a specific provider as primary by adjusting priorities.

**Parameters**:
- `provider_name` (str): Name of the provider to set as primary

##### Context Manager Support

```python
with FlexiAI(config=config) as client:
    response = client.chat_completion(messages=[...])
    # Automatic cleanup on exit
```

## Configuration

### FlexiAIConfig

Main configuration class for FlexiAI client.

```python
from flexiai import FlexiAIConfig, ProviderConfig, CircuitBreakerConfig

config = FlexiAIConfig(
    providers=[...],
    circuit_breaker=CircuitBreakerConfig(...),
    default_timeout=30,
    enable_logging=True,
    log_level="INFO"
)
```

**Attributes**:
- `providers` (List[ProviderConfig]): List of provider configurations
- `circuit_breaker` (CircuitBreakerConfig, optional): Circuit breaker configuration
- `default_timeout` (int): Default request timeout in seconds. Default: 30
- `enable_logging` (bool): Enable logging. Default: True
- `log_level` (str): Logging level. Default: "INFO"

### ProviderConfig

Configuration for a single provider.

```python
from flexiai import ProviderConfig

provider = ProviderConfig(
    name="openai",
    priority=1,
    api_key="sk-...",
    model="gpt-4-turbo-preview",
    base_url=None,
    timeout=30,
    max_retries=3,
    config={}
)
```

**Attributes**:
- `name` (str): Provider name. Supported: "openai", "gemini", "anthropic", "azure", "bedrock"
- `priority` (int): Priority level (1 = highest). Must be >= 1
- `api_key` (str): API key for authentication. Must not be empty
- `model` (str): Model name to use. Must not be empty
- `base_url` (str, optional): Custom API base URL
- `timeout` (int): Request timeout in seconds (1-300). Default: 30
- `max_retries` (int): Maximum retry attempts (0-10). Default: 3
- `config` (Dict[str, Any]): Provider-specific configuration. Default: {}

**Validation**:
- Provider name must be in supported list
- API key format validated per provider
- Priority must be >= 1
- Timeout must be 1-300 seconds
- Max retries must be 0-10

### CircuitBreakerConfig

Configuration for circuit breaker behavior.

```python
from flexiai import CircuitBreakerConfig

cb_config = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception_types=["ProviderException", "RateLimitError"]
)
```

**Attributes**:
- `failure_threshold` (int): Number of failures before opening circuit (>= 1). Default: 5
- `recovery_timeout` (int): Seconds before attempting recovery (>= 1). Default: 60
- `expected_exception_types` (List[str]): Exception types to track. Default: ["ProviderException"]

## Models

### Message

Represents a single message in a conversation.

```python
from flexiai.models import Message

message = Message(
    role="user",
    content="Hello!",
    name="John",
    function_call=None,
    tool_calls=None
)
```

**Attributes**:
- `role` (str): Message role ("system", "user", "assistant", "function", "tool")
- `content` (str): Message content
- `name` (str, optional): Participant name
- `function_call` (Dict, optional): Function call information
- `tool_calls` (List[Dict], optional): Tool call information

### UnifiedRequest

Standardized request format across all providers.

```python
from flexiai.models import UnifiedRequest, Message

request = UnifiedRequest(
    messages=[Message(role="user", content="Hello")],
    temperature=0.7,
    max_tokens=500,
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0,
    stop=None,
    n=1,
    stream=False,
    tools=None,
    metadata={}
)
```

**Attributes**:
- `messages` (List[Message]): Conversation messages
- `temperature` (float): Sampling temperature (0.0-2.0). Default: 0.7
- `max_tokens` (int, optional): Maximum tokens to generate
- `top_p` (float): Nucleus sampling (0.0-1.0). Default: 1.0
- `frequency_penalty` (float): Frequency penalty (-2.0 to 2.0). Default: 0.0
- `presence_penalty` (float): Presence penalty (-2.0 to 2.0). Default: 0.0
- `stop` (Union[str, List[str]], optional): Stop sequences
- `n` (int): Number of completions. Default: 1
- `stream` (bool): Enable streaming. Default: False
- `tools` (List[Dict], optional): Available tools/functions
- `metadata` (Dict[str, Any]): Additional metadata

### UnifiedResponse

Standardized response format across all providers.

```python
from flexiai.models import UnifiedResponse, TokenUsage

response = UnifiedResponse(
    content="Hello! How can I help?",
    provider="openai",
    model="gpt-4-turbo",
    usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    finish_reason="stop",
    metadata={},
    raw_response={}
)
```

**Attributes**:
- `content` (str): Generated text content
- `provider` (str): Provider that generated the response
- `model` (str): Model used
- `usage` (TokenUsage): Token usage information
- `finish_reason` (str): Reason for completion ("stop", "length", "content_filter", etc.)
- `metadata` (Dict[str, Any]): Additional metadata
- `raw_response` (Dict[str, Any]): Original provider response

### TokenUsage

Token usage information.

```python
from flexiai.models import TokenUsage

usage = TokenUsage(
    prompt_tokens=10,
    completion_tokens=20,
    total_tokens=30
)
```

**Attributes**:
- `prompt_tokens` (int): Tokens in the prompt
- `completion_tokens` (int): Tokens in the completion
- `total_tokens` (int): Total tokens used

## Exceptions

### FlexiAIException

Base exception for all FlexiAI errors.

```python
from flexiai.exceptions import FlexiAIException

try:
    response = client.chat_completion(...)
except FlexiAIException as e:
    print(f"FlexiAI error: {e}")
```

### ProviderException

Base exception for provider-related errors.

```python
from flexiai.exceptions import ProviderException

try:
    response = client.chat_completion(...)
except ProviderException as e:
    print(f"Provider error: {e.message}")
    print(f"Provider: {e.provider}")
    print(f"Details: {e.details}")
```

**Attributes**:
- `message` (str): Error message
- `provider` (str, optional): Provider name
- `details` (Dict[str, Any]): Additional error details

### AuthenticationError

Authentication failed (invalid API key).

```python
from flexiai.exceptions import AuthenticationError

try:
    response = client.chat_completion(...)
except AuthenticationError as e:
    print(f"Authentication failed for {e.provider}")
```

### RateLimitError

Rate limit exceeded.

```python
from flexiai.exceptions import RateLimitError

try:
    response = client.chat_completion(...)
except RateLimitError as e:
    print(f"Rate limit exceeded: {e.retry_after} seconds")
```

**Attributes**:
- `retry_after` (int, optional): Seconds to wait before retrying

### ValidationError

Request validation failed.

```python
from flexiai.exceptions import ValidationError

try:
    response = client.chat_completion(
        messages=[],  # Invalid: empty
        temperature=3.0  # Invalid: > 2.0
    )
except ValidationError as e:
    print(f"Validation error: {e.message}")
    print(f"Details: {e.details}")
```

### CircuitBreakerOpenError

Circuit breaker is open, requests rejected.

```python
from flexiai.exceptions import CircuitBreakerOpenError

try:
    response = client.chat_completion(...)
except CircuitBreakerOpenError as e:
    print(f"Circuit open for {e.provider}")
    print(f"State: {e.state_info}")
```

**Attributes**:
- `provider` (str): Provider name
- `state_info` (Dict[str, Any]): Circuit breaker state information

### AllProvidersFailedError

All configured providers failed.

```python
from flexiai.exceptions import AllProvidersFailedError

try:
    response = client.chat_completion(...)
except AllProvidersFailedError as e:
    print(f"All providers failed")
    print(f"Errors: {e.provider_errors}")
```

**Attributes**:
- `provider_errors` (Dict[str, Exception]): Map of provider names to their errors

### ConfigurationError

Invalid configuration.

```python
from flexiai.exceptions import ConfigurationError

try:
    config = FlexiAIConfig(providers=[])  # Invalid: no providers
except ConfigurationError as e:
    print(f"Configuration error: {e.message}")
```

## Providers

### BaseProvider

Abstract base class for all provider implementations.

```python
from flexiai.providers import BaseProvider
from flexiai.models import ProviderConfig, UnifiedRequest, UnifiedResponse

class MyProvider(BaseProvider):
    def chat_completion(self, request: UnifiedRequest) -> UnifiedResponse:
        # Implementation
        pass

    def authenticate(self) -> bool:
        # Implementation
        pass

    def validate_credentials(self) -> bool:
        # Implementation
        pass

    def health_check(self) -> bool:
        # Implementation
        pass
```

#### Abstract Methods

##### `chat_completion(request: UnifiedRequest) -> UnifiedResponse`

Execute a chat completion request.

##### `authenticate() -> bool`

Authenticate with the provider.

##### `validate_credentials() -> bool`

Validate API credentials without making an API call.

##### `health_check() -> bool`

Check if the provider is healthy.

#### Provided Methods

##### `chat_completion_with_retry(request: UnifiedRequest) -> UnifiedResponse`

Execute chat completion with automatic retry logic.

**Retry Configuration**:
- Exponential backoff (1s, 2s, 4s, 8s, 10s max)
- Retries on: `ProviderException`, `RateLimitError`
- Max attempts: from `config.max_retries`

##### `is_healthy() -> bool`

Check health with caching (60-second cache).

##### `get_provider_info() -> Dict[str, Any]`

Get provider information.

**Returns**:
```python
{
    "name": "openai",
    "model": "gpt-4-turbo",
    "base_url": "https://api.openai.com/v1",
    "timeout": 30
}
```

## Circuit Breaker

### CircuitBreaker

Circuit breaker for fault tolerance.

```python
from flexiai.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

breaker = CircuitBreaker(
    name="my-service",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60
    )
)
```

#### Methods

##### `call(func: Callable, *args, **kwargs) -> Any`

Execute a function through the circuit breaker.

**Example**:
```python
result = breaker.call(lambda: provider.chat_completion(request))
```

##### `reset() -> None`

Manually reset circuit breaker to CLOSED state.

##### `is_open() -> bool`

Check if circuit is open.

##### `is_closed() -> bool`

Check if circuit is closed.

##### `is_half_open() -> bool`

Check if circuit is half-open.

##### `get_state_info() -> Dict[str, Any]`

Get detailed state information.

**Returns**:
```python
{
    "state": "CLOSED",
    "failure_count": 0,
    "success_count": 10,
    "last_failure_time": None,
    "opened_at": None,
    "consecutive_failures": 0,
    "consecutive_successes": 10
}
```

### CircuitState

Enum representing circuit states.

```python
from flexiai.circuit_breaker import CircuitState

if breaker.state == CircuitState.OPEN:
    print("Circuit is open")
```

**Values**:
- `CLOSED`: Normal operation
- `OPEN`: Failures detected, rejecting requests
- `HALF_OPEN`: Testing recovery

## Utilities

### Validators

#### APIKeyValidator

Validate API keys for different providers.

```python
from flexiai.utils.validators import APIKeyValidator

# Validate
is_valid = APIKeyValidator.validate("openai", "sk-abc123...")

# Get pattern
pattern = APIKeyValidator.get_pattern("openai")
```

**Supported Providers**:
- `openai`: `sk-[a-zA-Z0-9\-_]{20,}`
- `anthropic`: `sk-ant-[a-zA-Z0-9\-_]{20,}`
- `gemini`: `[a-zA-Z0-9\-_]{20,}`
- `azure`: `[a-zA-Z0-9]{32}`
- `bedrock`: AWS access key format

#### ModelValidator

Validate model names for providers.

```python
from flexiai.utils.validators import ModelValidator

# Validate
is_valid = ModelValidator.validate("openai", "gpt-4-turbo")

# Get supported models
models = ModelValidator.get_supported_models("openai")
```

#### RequestValidator

Validate request parameters.

```python
from flexiai.utils.validators import RequestValidator

# Validate individual parameters
RequestValidator.validate_temperature(0.7)  # Raises ValidationError if invalid
RequestValidator.validate_max_tokens(500)
RequestValidator.validate_top_p(1.0)
RequestValidator.validate_messages([...])

# Validate request object
from flexiai.models import UnifiedRequest
RequestValidator.validate_request(request)
```

### Logger

Structured logging with sensitive data masking.

```python
from flexiai.utils.logger import FlexiAILogger

logger = FlexiAILogger.get_logger()

# Log with correlation ID
with logger.correlation_id("req-123"):
    logger.info("Processing request", extra={"user_id": 456})
    logger.error("Request failed", extra={"error": "timeout"})

# Direct logging
logger.debug("Debug message")
logger.warning("Warning message")
```

**Features**:
- Correlation ID tracking
- Sensitive data masking (API keys, tokens)
- Rotating file handler
- Structured logging format
- Configurable log levels

---

**Last Updated**: October 25, 2025
**Version**: 1.0 (Phase 1 Complete)
