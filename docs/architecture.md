# FlexiAI Architecture

This document describes the architecture, design patterns, and implementation details of FlexiAI.

## Table of Contents

- [Overview](#overview)
- [Architecture Diagram](#architecture-diagram)
- [Core Components](#core-components)
- [Design Patterns](#design-patterns)
- [Data Flow](#data-flow)
- [Thread Safety](#thread-safety)
- [Error Handling](#error-handling)
- [Extensibility](#extensibility)

## Overview

FlexiAI is designed as a modular, extensible framework for integrating multiple GenAI providers with automatic failover, circuit breaker pattern, and production-grade reliability.

### Design Goals

1. **Reliability**: Automatic failover with circuit breaker pattern
2. **Simplicity**: Single unified API for all providers
3. **Type Safety**: Pydantic models and full type hints
4. **Extensibility**: Easy to add new providers
5. **Observability**: Comprehensive logging and metrics
6. **Performance**: Efficient with minimal overhead

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        FlexiAI Client                        │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          chat_completion()                          │   │
│  │  - Validate request                                 │   │
│  │  - Select provider (priority-based)                 │   │
│  │  - Execute with circuit breaker                     │   │
│  │  - Handle failover on error                         │   │
│  │  - Track metadata                                   │   │
│  └───────────────────┬─────────────────────────────────┘   │
│                      │                                      │
└──────────────────────┼──────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│ Provider        │       │  Request/       │
│ Registry        │       │  Response       │
│                 │       │  Normalizers    │
│ ┌─────────────┐ │       │                 │
│ │  Providers  │ │       │ ┌─────────────┐ │
│ │   - OpenAI  │ │       │ │   Request   │ │
│ │   - Gemini  │ │       │ │  Normalizer │ │
│ │   - Claude  │ │       │ └─────────────┘ │
│ └─────────────┘ │       │                 │
│                 │       │ ┌─────────────┐ │
│ ┌─────────────┐ │       │ │  Response   │ │
│ │  Circuit    │ │       │ │  Normalizer │ │
│ │  Breakers   │ │       │ └─────────────┘ │
│ └─────────────┘ │       └─────────────────┘
│                 │                │
│ ┌─────────────┐ │                │
│ │  Metadata   │ │                │
│ └─────────────┘ │                │
└─────────────────┘                │
          │                        │
          │                        │
          ▼                        ▼
┌─────────────────────────────────────┐
│           Utilities                 │
│                                     │
│  ┌────────────┐  ┌──────────────┐  │
│  │ Validators │  │    Logger    │  │
│  │            │  │              │  │
│  │ - API Keys │  │ - Structured │  │
│  │ - Models   │  │ - Correlation│  │
│  │ - Requests │  │ - Masking    │  │
│  └────────────┘  └──────────────┘  │
└─────────────────────────────────────┘
```

## Core Components

### 1. FlexiAI Client (`client.py`)

**Purpose**: Main entry point for all API interactions

**Responsibilities**:
- Validate incoming requests
- Select appropriate provider based on priority
- Execute requests through circuit breakers
- Handle automatic failover
- Track request metadata and statistics
- Manage provider lifecycle

**Key Methods**:
```python
def chat_completion(messages, **kwargs) -> UnifiedResponse
def get_provider_status() -> Dict[str, Any]
def get_request_stats() -> Dict[str, Any]
def reset_circuit_breakers() -> None
```

### 2. Provider Registry (`providers/registry.py`)

**Purpose**: Singleton registry managing all provider instances

**Responsibilities**:
- Register/unregister providers
- Maintain provider priority order
- Manage circuit breakers per provider
- Provide thread-safe provider access
- Track provider metadata

**Pattern**: Singleton with double-checked locking

**Key Methods**:
```python
def register(provider: BaseProvider, priority: int) -> None
def get_provider(name: str) -> BaseProvider
def get_all_providers() -> List[BaseProvider]
def list_providers() -> List[Tuple[str, int]]
```

### 3. Base Provider (`providers/base.py`)

**Purpose**: Abstract base class for all provider implementations

**Responsibilities**:
- Define provider interface
- Implement retry logic with exponential backoff
- Provide health check mechanism with caching
- Standardize error handling

**Key Abstract Methods**:
```python
def chat_completion(request: UnifiedRequest) -> UnifiedResponse
def authenticate() -> bool
def validate_credentials() -> bool
def health_check() -> bool
```

**Key Implementations**:
```python
def chat_completion_with_retry(...) -> UnifiedResponse
def is_healthy() -> bool  # With 60s cache
```

### 4. OpenAI Provider (`providers/openai_provider.py`)

**Purpose**: OpenAI-specific implementation

**Responsibilities**:
- Initialize OpenAI client
- Normalize requests for OpenAI API
- Parse OpenAI responses
- Handle OpenAI-specific errors
- Validate OpenAI API keys

**Error Mapping**:
- `AuthenticationError` → `AuthenticationError`
- `RateLimitError` → `RateLimitError`
- `BadRequestError` → `ValidationError`
- `APIError` → `ProviderException`

### 5. Circuit Breaker (`circuit_breaker/`)

**Purpose**: Implement circuit breaker pattern for fault tolerance

**Components**:

#### CircuitBreakerState (`state.py`)
```python
class CircuitState(Enum):
    CLOSED      # Normal operation
    OPEN        # Failures detected, reject requests
    HALF_OPEN   # Testing recovery
```

**State Tracking**:
- Failure count
- Success count
- State transition timestamps
- Consecutive failures/successes

#### CircuitBreaker (`breaker.py`)

**State Transitions**:
```
CLOSED --[failures >= threshold]--> OPEN
OPEN --[timeout elapsed]--> HALF_OPEN
HALF_OPEN --[success]--> CLOSED
HALF_OPEN --[failure]--> OPEN
```

**Configuration**:
- `failure_threshold`: Failures before opening (default: 5)
- `recovery_timeout`: Seconds before trying recovery (default: 60)
- `expected_exceptions`: Which exceptions to track

### 6. Request/Response Normalizers (`normalizers/`)

**Purpose**: Convert between unified format and provider-specific formats

#### Request Normalizer
```python
def normalize(request: UnifiedRequest) -> Dict[str, Any]:
    """Convert UnifiedRequest to provider-specific format"""
```

**Handles**:
- Message format conversion
- Parameter mapping (temperature, max_tokens, etc.)
- Model validation
- Provider-specific features

#### Response Normalizer
```python
def normalize(response: Any) -> UnifiedResponse:
    """Convert provider response to UnifiedResponse"""
```

**Extracts**:
- Generated content
- Token usage
- Metadata
- Finish reason
- Function/tool calls

### 7. Models (`models.py`)

**Purpose**: Type-safe data models using Pydantic

**Key Models**:

```python
class Message(BaseModel):
    role: str
    content: str
    name: Optional[str] = None
    # ...

class UnifiedRequest(BaseModel):
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    # ...

class UnifiedResponse(BaseModel):
    content: str
    provider: str
    model: str
    usage: TokenUsage
    # ...

class ProviderConfig(BaseModel):
    name: str
    priority: int
    api_key: str
    model: str
    # ...

class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = 5
    recovery_timeout: int = 60
    # ...
```

### 8. Validators (`utils/validators.py`)

**Purpose**: Validate API keys, models, and request parameters

**Components**:

#### APIKeyValidator
```python
PATTERNS = {
    "openai": r"^sk-[a-zA-Z0-9\-_]{20,}$",
    "anthropic": r"^sk-ant-[a-zA-Z0-9\-_]{20,}$",
    "gemini": r"^[a-zA-Z0-9\-_]{20,}$",
    # ...
}
```

#### ModelValidator
Maintains lists of supported models per provider

#### RequestValidator
Validates:
- Temperature (0.0-2.0)
- Max tokens (> 0)
- Top-p (0.0-1.0)
- Frequency/presence penalties (-2.0 to 2.0)
- Messages list (non-empty)

### 9. Logger (`utils/logger.py`)

**Purpose**: Structured logging with security features

**Features**:
- Singleton pattern
- Correlation ID tracking
- Sensitive data masking (API keys, tokens)
- Rotating file handler
- Configurable log levels
- Console output for warnings/errors

**Usage**:
```python
with logger.correlation_id("req-123"):
    logger.info("Processing request", extra={"user_id": 456})
```

## Design Patterns

### 1. Singleton Pattern

**Used In**:
- `ProviderRegistry`
- `FlexiAILogger`

**Implementation**:
```python
class ProviderRegistry:
    _instance: Optional["ProviderRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

**Benefits**:
- Single source of truth
- Thread-safe initialization
- Shared state across application

### 2. Circuit Breaker Pattern

**Purpose**: Prevent cascading failures

**States**:
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures, reject requests immediately
- **HALF_OPEN**: Testing if service recovered

**Benefits**:
- Fail fast when service is down
- Automatic recovery detection
- Reduced load on failing services

### 3. Strategy Pattern

**Used In**: Request/Response Normalizers

**Purpose**: Different algorithms (normalization strategies) for different providers

**Benefits**:
- Easy to add new providers
- Clean separation of provider-specific logic
- Testable in isolation

### 4. Factory Pattern

**Used In**: Provider creation in client

```python
def _create_provider(self, config: ProviderConfig) -> BaseProvider:
    provider_map = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,  # Future
        # ...
    }
    provider_class = provider_map[config.name]
    return provider_class(config)
```

### 5. Dependency Injection

**Used Throughout**: Configuration objects passed as dependencies

**Benefits**:
- Testability (easy to mock)
- Flexibility (different configs)
- No global state

## Data Flow

### Request Flow

```
1. User calls client.chat_completion(messages, **kwargs)
   │
   ▼
2. Client validates request using RequestValidator
   │
   ▼
3. Client gets available providers from Registry
   │
   ▼
4. For each provider (by priority):
   │
   ├─▶ 5. Check circuit breaker state
   │   │
   │   ├─▶ OPEN: Skip provider, try next
   │   │
   │   └─▶ CLOSED/HALF_OPEN: Continue
   │       │
   │       ▼
   │   6. Normalize request for provider
   │       │
   │       ▼
   │   7. Execute through circuit breaker
   │       │
   │       ├─▶ SUCCESS:
   │       │   ├─ Normalize response
   │       │   ├─ Update circuit breaker (success)
   │       │   ├─ Track metadata
   │       │   └─ Return response
   │       │
   │       └─▶ FAILURE:
   │           ├─ Update circuit breaker (failure)
   │           ├─ Log error
   │           └─ Continue to next provider
   │
   └─▶ 8. If all providers fail:
       └─ Raise AllProvidersFailedError
```

### Error Handling Flow

```
Provider Error
   │
   ▼
Map to FlexiAI Exception
   │
   ├─▶ AuthenticationError
   ├─▶ RateLimitError
   ├─▶ ValidationError
   └─▶ ProviderException
   │
   ▼
Update Circuit Breaker
   │
   ├─▶ Increment failure count
   ├─▶ Check threshold
   └─▶ Transition state if needed
   │
   ▼
Try Next Provider (if available)
   │
   ├─▶ Found: Retry with next provider
   └─▶ None: Raise AllProvidersFailedError
```

## Thread Safety

### Synchronized Components

1. **Provider Registry**
```python
with ProviderRegistry._lock:
    # Thread-safe operations
```

2. **Circuit Breaker**
```python
with self._lock:
    # Thread-safe state transitions
```

3. **Request Metadata**
```python
with self._metadata_lock:
    # Thread-safe metadata updates
```

### Thread-Safe Patterns

- Double-checked locking for singletons
- Lock-protected critical sections
- Immutable configurations
- Thread-local storage for correlation IDs (future)

## Error Handling

### Exception Hierarchy

```
FlexiAIException (base)
├── ProviderException
│   ├── AuthenticationError
│   ├── RateLimitError
│   └── APIError
├── CircuitBreakerOpenError
├── AllProvidersFailedError
├── ValidationError
├── ConfigurationError
└── ProviderNotFoundError
```

### Error Handling Strategy

1. **Provider-Level**: Catch provider-specific errors, map to FlexiAI exceptions
2. **Circuit Breaker**: Track errors, manage state transitions
3. **Client-Level**: Attempt failover, aggregate errors
4. **User-Level**: Receive meaningful error with context

### Retry Logic

```python
@retry(
    stop=stop_after_attempt(max_retries),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ProviderException, RateLimitError))
)
def chat_completion_with_retry(...):
    # Automatic retry with exponential backoff
```

## Extensibility

### Adding a New Provider

1. **Create Provider Class**
```python
class GeminiProvider(BaseProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = genai.GenerativeModel(config.model)

    def chat_completion(self, request: UnifiedRequest) -> UnifiedResponse:
        # Implementation
        pass
```

2. **Create Normalizers**
```python
class GeminiRequestNormalizer(RequestNormalizer):
    def normalize(self, request: UnifiedRequest) -> Dict:
        # Convert to Gemini format
        pass

class GeminiResponseNormalizer(ResponseNormalizer):
    def normalize(self, response) -> UnifiedResponse:
        # Convert from Gemini format
        pass
```

3. **Register Provider**
```python
# In client.py
provider_map = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    # ...
}
```

4. **Add Validators**
```python
# In validators.py
PATTERNS = {
    "gemini": r"^[a-zA-Z0-9\-_]{20,}$",
    # ...
}

SUPPORTED_MODELS = {
    "gemini": ["gemini-pro", "gemini-pro-vision"],
    # ...
}
```

5. **Add Tests**
```python
def test_gemini_provider():
    # Unit tests
    pass

def test_gemini_integration():
    # Integration tests
    pass
```

### Configuration Extension

FlexiAI supports provider-specific configuration:

```python
ProviderConfig(
    name="openai",
    priority=1,
    api_key="...",
    model="gpt-4",
    config={
        "organization": "org-123",  # OpenAI-specific
        "custom_param": "value"
    }
)
```

### Middleware/Hooks (Future)

```python
# Future extensibility
def before_request_hook(request: UnifiedRequest) -> UnifiedRequest:
    # Modify request before sending
    return request

def after_response_hook(response: UnifiedResponse) -> UnifiedResponse:
    # Process response
    return response

client.register_hook("before_request", before_request_hook)
```

## Performance Considerations

### Optimization Techniques

1. **Health Check Caching**: 60-second cache to avoid repeated health checks
2. **Lazy Provider Initialization**: Providers created on first use
3. **Efficient State Checks**: O(1) circuit breaker state lookups
4. **Minimal Lock Contention**: Fine-grained locking

### Scalability

- Stateless request handling
- Thread-safe concurrent requests
- Minimal memory footprint
- No persistent connections (stateless HTTP)

## Security Considerations

1. **API Key Protection**:
   - Never logged in plain text
   - Masked in logs (shows only last 4 chars)
   - Stored in memory only, not persisted

2. **Input Validation**:
   - All requests validated before processing
   - Type checking with Pydantic
   - Parameter range validation

3. **Error Messages**:
   - No sensitive data in error messages
   - Sanitized error responses
   - Detailed logging (but masked sensitive fields)

## Future Enhancements

### Planned Features

1. **Async Support**: `AsyncFlexiAI` client
2. **Streaming**: Real-time response streaming
3. **Caching**: Response caching layer
4. **Metrics**: Prometheus-compatible metrics
5. **Cost Tracking**: Token cost calculation
6. **Request Hooks**: Middleware system
7. **Multi-Region**: Geographic failover

### Extension Points

- Custom circuit breaker strategies
- Custom retry policies
- Custom normalizers
- Custom validators
- Plugin system for providers

---

**Last Updated**: October 25, 2025
**Version**: 1.0 (Phase 1 Complete)
