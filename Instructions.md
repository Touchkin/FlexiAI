# FlexiAI: Comprehensive Development Plan

## Project Overview
FlexiAI is a Python wheel package that provides a unified interface for multiple GenAI providers (OpenAI, Vertex AI, Claude) with automatic failover capabilities using circuit breaker pattern.

**Note**: GeminiProvider (Developer API) has been removed. Use VertexAIProvider for Google's Gemini models on GCP.

---

## Architecture Overview

### Core Components

```
FlexiAI/
├── flexiai/
│   ├── __init__.py
│   ├── client.py              # Main FlexiAI client
│   ├── config.py              # Configuration management
│   ├── models.py              # Data models and schemas
│   ├── exceptions.py          # Custom exceptions
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract base provider
│   │   ├── openai_provider.py
│   │   ├── vertexai_provider.py  # Google Vertex AI (Gemini on GCP)
│   │   ├── anthropic_provider.py
│   │   └── registry.py       # Provider registry
│   ├── circuit_breaker/
│   │   ├── __init__.py
│   │   ├── breaker.py        # Circuit breaker implementation
│   │   └── state.py          # Circuit breaker state management
│   ├── normalizers/
│   │   ├── __init__.py
│   │   ├── request.py        # Normalize requests across providers
│   │   └── response.py       # Normalize responses across providers
│   └── utils/
│       ├── __init__.py
│       ├── logger.py         # Logging utilities
│       └── validators.py     # Input validation
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
├── examples/
├── setup.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── README.md
└── CHANGELOG.md
```

---

## Detailed Architecture Design

### 1. **Client Layer (client.py)**
- Main entry point for users
- Accepts unified request format
- Manages provider selection and failover
- Returns normalized responses
- Handles retry logic

**Key Methods:**
- `__init__(config)` - Initialize with configuration
- `chat_completion(messages, **kwargs)` - Main API call method
- `set_primary_provider(provider_name)` - Change primary provider
- `get_provider_status()` - Get health status of all providers
- `reset_circuit_breakers()` - Manually reset breakers

### 2. **Configuration Management (config.py)**
```python
Configuration Structure:
{
    "providers": [
        {
            "name": "openai",
            "priority": 1,
            "api_key": "sk-...",
            "model": "gpt-4.1-mini",
            "config": {
                "timeout": 30,
                "max_retries": 3
            }
        },
        {
            "name": "vertexai",
            "priority": 2,
            "api_key": "not-used",
            "model": "gemini-2.0-flash",
            "config": {
                "project": "gcp-project-id",
                "location": "us-central1"
            }
        },
        {
            "name": "anthropic",
            "priority": 3,
            "api_key": "...",
            "model": "claude-3-sonnet",
            "config": {}
        }
    ],
    "circuit_breaker": {
        "failure_threshold": 5,
        "recovery_timeout": 60,
        "expected_exception": ["APIError", "Timeout"]
    },
    "retry": {
        "max_attempts": 3,
        "backoff_factor": 2
    },
    "logging": {
        "level": "INFO",
        "file": "flexiai.log"
    }
}
```

### 3. **Provider Abstract Base Class (providers/base.py)**
```python
Abstract methods to implement:
- authenticate() - Handle API key authentication
- chat_completion(normalized_request) - Make API call
- validate_credentials() - Validate API keys
- get_model_info() - Return model capabilities
- handle_error(error) - Provider-specific error handling
```

### 4. **Circuit Breaker Pattern (circuit_breaker/breaker.py)**

**States:**
- CLOSED: Normal operation, requests pass through
- OPEN: Failures exceeded threshold, requests fail fast
- HALF_OPEN: Testing if service recovered

**Implementation Details:**
- Track failure count per provider
- Implement timeout for state transitions
- Thread-safe state management
- Emit events for state changes
- Persist state optionally (for multi-instance scenarios)

### 5. **Request/Response Normalization (normalizers/)**

**Request Normalizer:**
- Convert unified format to provider-specific format
- Handle parameter mapping (temperature, max_tokens, etc.)
- Support streaming and non-streaming modes
- Handle function calling / tool use differences

**Response Normalizer:**
- Convert provider responses to unified format
- Extract text, usage stats, metadata
- Handle streaming responses
- Normalize error responses

**Unified Format:**
```python
Request:
{
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "temperature": 0.7,
    "max_tokens": 1000,
    "stream": false,
    "tools": [],  # Optional
    "response_format": {}  # Optional
}

Response:
{
    "content": "Hello! How can I help?",
    "model": "gpt-4.1-mini",
    "provider": "openai",
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
    },
    "finish_reason": "stop",
    "metadata": {}
}
```

---

## Phase-wise Implementation Plan

## **PHASE 1: Core Foundation + OpenAI Support**

### Phase 1.1: Project Setup
**TODO:**
- [ ] Create project directory structure
- [ ] Initialize git repository
- [ ] Set up virtual environment
- [ ] Create `setup.py` and `pyproject.toml` for wheel packaging
- [ ] Create `requirements.txt` with dependencies:
  - `openai>=1.0.0`
  - `pydantic>=2.0.0`
  - `tenacity>=8.0.0`
  - `python-dotenv>=1.0.0`
- [ ] Create `requirements-dev.txt` with:
  - `pytest>=7.0.0`
  - `pytest-cov>=4.0.0`
  - `black>=23.0.0`
  - `flake8>=6.0.0`
  - `mypy>=1.0.0`
- [ ] Set up pre-commit hooks
- [ ] Create README.md with project description
- [ ] Create CHANGELOG.md

**Instructions for Copilot:**
- Follow Python best practices and PEP 8 style guide
- Use type hints throughout the codebase
- Set up project as a standard Python package with proper `__init__.py` files
- Configure setup.py for wheel distribution with metadata: name="flexiai", version="0.1.0", author, description, classifiers

### Phase 1.2: Core Models and Exceptions
**TODO:**
- [ ] Create `models.py` with Pydantic models:
  - `Message` model (role, content)
  - `UnifiedRequest` model
  - `UnifiedResponse` model
  - `ProviderConfig` model
  - `CircuitBreakerConfig` model
  - `FlexiAIConfig` model
- [ ] Create `exceptions.py` with custom exceptions:
  - `FlexiAIException` (base exception)
  - `ProviderException`
  - `ConfigurationError`
  - `CircuitBreakerOpenError`
  - `AllProvidersFailedError`
  - `ValidationError`
  - `AuthenticationError`
- [ ] Add proper exception hierarchy
- [ ] Add docstrings to all models and exceptions

**Instructions for Copilot:**
- Use Pydantic v2 syntax for models
- Add field validators for required fields (API keys, model names)
- Include `model_config` for Pydantic settings
- Make models JSON serializable
- Add `from_dict()` and `to_dict()` methods where needed
- Include examples in docstrings

### Phase 1.3: Configuration Management
**TODO:**
- [ ] Implement `config.py`:
  - `ConfigLoader` class to load from dict/file/env
  - Validation logic for configuration
  - Default configuration values
  - Configuration merging (defaults + user config)
- [ ] Support loading from:
  - Python dict
  - JSON file
  - Environment variables (FLEXIAI_ prefix)
- [ ] Add configuration validation
- [ ] Create example configuration files in docs/

**Instructions for Copilot:**
- Use singleton pattern for ConfigLoader
- Implement environment variable override logic
- Add clear error messages for configuration errors
- Support both file paths and file-like objects
- Include schema validation using Pydantic
- Add method to export current config to dict/JSON

### Phase 1.4: Logging and Utilities
**TODO:**
- [ ] Implement `utils/logger.py`:
  - Configure logging with rotating file handler
  - Console handler for warnings/errors
  - Structured logging format
  - Log levels configuration
- [ ] Implement `utils/validators.py`:
  - API key format validators
  - Model name validators
  - Request parameter validators
- [ ] Add utility functions for common operations

**Instructions for Copilot:**
- Use Python's `logging` module
- Create logger instance: `logger = logging.getLogger('flexiai')`
- Add log correlation IDs for tracing requests
- Implement sensitive data masking (API keys in logs)
- Add debug mode that logs request/response bodies (with masking)
- Include helper functions for validating each provider's requirements

### Phase 1.5: Provider Base Class
**TODO:**
- [ ] Implement `providers/base.py`:
  - `BaseProvider` abstract class
  - Abstract methods: `chat_completion()`, `authenticate()`, `validate_credentials()`
  - Common retry logic
  - Common error handling wrapper
  - Health check method
- [ ] Add provider interface documentation
- [ ] Create provider registration mechanism

**Instructions for Copilot:**
- Use ABC (Abstract Base Class) from Python's abc module
- Define clear method signatures with type hints
- Implement common functionality in base class (logging, basic validation)
- Use `@abstractmethod` decorator for methods that must be implemented
- Add retry decorator using tenacity library
- Include timeout handling in base class
- Document expected exceptions from each method

### Phase 1.6: Request/Response Normalizers (Foundation)
**TODO:**
- [ ] Implement `normalizers/request.py`:
  - `RequestNormalizer` base class
  - OpenAI request normalizer
  - Message format conversion
  - Parameter mapping
- [ ] Implement `normalizers/response.py`:
  - `ResponseNormalizer` base class
  - OpenAI response normalizer
  - Extract content, usage, metadata
  - Error response normalization

**Instructions for Copilot:**
- Create mapping dictionaries for parameter names across providers
- Handle optional parameters gracefully (set defaults)
- For OpenAI, map directly since it's the reference implementation
- Preserve all provider-specific metadata in `metadata` field
- Handle both streaming and non-streaming responses
- Add validation that required fields are present in responses
- Include comprehensive error handling for malformed responses

### Phase 1.7: OpenAI Provider Implementation
**TODO:**
- [ ] Implement `providers/openai_provider.py`:
  - Inherit from `BaseProvider`
  - Initialize OpenAI client
  - Implement `authenticate()` method
  - Implement `chat_completion()` method
  - Implement `validate_credentials()` method
  - Handle OpenAI-specific errors
  - Map OpenAI exceptions to FlexiAI exceptions
- [ ] Add support for:
  - Standard chat completions
  - Streaming responses
  - Function calling (basic)
- [ ] Add comprehensive error handling

**Instructions for Copilot:**
- Use the official `openai` Python library (version 1.0+)
- Initialize client in `__init__` with API key
- Use `openai.OpenAI(api_key=...)` client pattern
- Implement exponential backoff for rate limits
- Handle specific OpenAI errors: RateLimitError, APIError, Timeout, APIConnectionError
- Add logging for all API calls (request/response)
- Implement health check using a lightweight API call (list models or simple completion)
- Support both async and sync calls (start with sync in Phase 1)
- Add model validation against OpenAI's available models

### Phase 1.8: Circuit Breaker Implementation
**TODO:**
- [ ] Implement `circuit_breaker/state.py`:
  - `CircuitState` enum (CLOSED, OPEN, HALF_OPEN)
  - `CircuitBreakerState` class to track state
  - Failure counter
  - State transition timestamps
- [ ] Implement `circuit_breaker/breaker.py`:
  - `CircuitBreaker` class
  - State transition logic
  - Failure threshold checking
  - Recovery timeout handling
  - Thread-safe implementation
- [ ] Add circuit breaker metrics

**Instructions for Copilot:**
- Use threading.Lock for thread safety
- Implement state machine pattern for state transitions
- Add timestamps for state changes
- Track consecutive failures, not just total failures
- Reset failure count on successful call
- Implement half-open state with single test request
- Add callbacks/hooks for state change events
- Use time.time() for timing, make configurable
- Add method to manually trip/reset breaker
- Log all state transitions with context
- Consider using dataclasses for state management

### Phase 1.9: Provider Registry
**TODO:**
- [ ] Implement `providers/registry.py`:
  - `ProviderRegistry` singleton class
  - Register/unregister providers
  - Get provider by name
  - List available providers
  - Provider priority management
- [ ] Add provider discovery mechanism

**Instructions for Copilot:**
- Implement as singleton using __new__ method
- Use dictionary to store providers: {name: provider_instance}
- Validate provider implements BaseProvider interface
- Sort providers by priority (1 = highest)
- Add method to get next available provider based on circuit breaker state
- Include provider metadata (name, model, status)
- Add thread-safe operations
- Implement lazy loading of providers (only initialize when needed)

### Phase 1.10: Main Client Implementation
**TODO:**
- [ ] Implement `client.py` - `FlexiAI` class:
  - Initialize with configuration
  - Load and register providers
  - Implement `chat_completion()` main method
  - Provider selection logic
  - Failover logic
  - Circuit breaker integration
  - Response aggregation
- [ ] Add convenience methods:
  - `set_primary_provider()`
  - `get_provider_status()`
  - `reset_circuit_breakers()`
- [ ] Add context manager support (optional)

**Instructions for Copilot:**
- Main flow for `chat_completion()`:
  1. Validate and normalize request
  2. Get list of providers sorted by priority
  3. For each provider (until success):
     - Check if circuit breaker is OPEN, skip if yes
     - Try to make API call
     - If success: normalize response and return
     - If failure: record failure in circuit breaker
     - Move to next provider
  4. If all providers fail: raise AllProvidersFailedError
- Add detailed logging at each step
- Track request metadata (attempts, providers tried, latencies)
- Implement timeout for entire request (not just per provider)
- Add method to get the last used provider
- Support passing additional kwargs to providers
- Make thread-safe for concurrent requests

### Phase 1.11: Unit Tests for Phase 1
**TODO:**
- [ ] Test `models.py`:
  - Model validation
  - Serialization/deserialization
- [ ] Test `config.py`:
  - Loading from different sources
  - Validation
  - Default values
- [ ] Test `providers/openai_provider.py`:
  - Mock OpenAI API responses
  - Error handling
  - Request/response normalization
- [ ] Test `circuit_breaker/breaker.py`:
  - State transitions
  - Failure threshold
  - Recovery timeout
- [ ] Test `client.py`:
  - Failover logic
  - Provider selection
  - End-to-end flow with mocked providers

**Instructions for Copilot:**
- Use pytest framework
- Use pytest fixtures for common test setup
- Mock external API calls using `unittest.mock` or `pytest-mock`
- Test both success and failure scenarios
- Test edge cases (empty messages, invalid API keys, etc.)
- Aim for >80% code coverage
- Use parametrized tests for testing multiple scenarios
- Create fixtures for sample requests/responses
- Test thread safety with concurrent requests

### Phase 1.12: Integration Tests
**TODO:**
- [ ] Create integration tests with real OpenAI API:
  - Simple completion test
  - Multi-turn conversation test
  - Error handling test (invalid API key)
  - Failover test (mock primary failure)
- [ ] Add tests in `tests/integration/`
- [ ] Use environment variables for API keys
- [ ] Add skip markers for tests requiring API keys

**Instructions for Copilot:**
- Mark integration tests with `@pytest.mark.integration`
- Use `@pytest.mark.skipif` to skip if API key not present
- Add small rate limits/delays between tests
- Test with minimal token usage to reduce costs
- Include tests for circuit breaker behavior with real APIs
- Create separate test for each major feature

### Phase 1.13: Documentation and Examples
**TODO:**
- [ ] Create comprehensive README.md:
  - Installation instructions
  - Quick start guide
  - Configuration examples
  - Basic usage examples
- [ ] Create `docs/` folder with:
  - Architecture documentation
  - API reference
  - Configuration guide
  - Circuit breaker explained
- [ ] Create `examples/` folder:
  - `basic_usage.py`
  - `with_failover.py`
  - `configuration_examples.py`
  - `error_handling.py`

**Instructions for Copilot:**
- Use clear, concise language in documentation
- Include code examples that can be copy-pasted
- Add troubleshooting section
- Document all configuration options
- Include diagrams for architecture (ASCII art or reference to images)
- Add FAQ section
- Include examples for common use cases

### Phase 1.14: Package Build and Distribution
**TODO:**
- [ ] Test package installation:
  - Build wheel: `python setup.py bdist_wheel`
  - Install locally: `pip install dist/flexiai-0.1.0-py3-none-any.whl`
  - Test imports and basic functionality
- [ ] Set up version management
- [ ] Create GitHub releases workflow (optional)
- [ ] Test on different Python versions (3.8, 3.9, 3.10, 3.11)

**Instructions for Copilot:**
- Ensure setup.py includes all dependencies
- Set minimum Python version to 3.8+
- Include long_description from README.md
- Add classifiers for PyPI
- Test wheel installation in clean virtual environment
- Verify all package data is included (config examples, etc.)

---

## **PHASE 2: Google Gemini Integration**

### Phase 2.1: Gemini Provider Research and Setup
**TODO:**
- [ ] Research Google Gemini API:
  - Authentication method
  - Request/response format
  - Available models
  - Rate limits and error codes
  - Streaming support
- [ ] Add Gemini dependencies to requirements.txt:
  - `google-generativeai>=0.3.0`
- [ ] Update documentation with Gemini support

**Instructions for Copilot:**
- Study official Gemini Python SDK documentation
- Document differences from OpenAI API
- Note parameter name differences (temperature, max_output_tokens vs max_tokens)
- Understand Gemini's content safety settings
- Map Gemini error codes to FlexiAI exceptions

### Phase 2.2: Gemini Request Normalizer
**TODO:**
- [ ] Extend `normalizers/request.py`:
  - Implement `GeminiRequestNormalizer` class
  - Map unified format to Gemini format
  - Handle message role mapping (user/model vs user/assistant)
  - Convert parameters (max_tokens → max_output_tokens, etc.)
  - Handle safety settings
- [ ] Add Gemini-specific parameter handling

**Instructions for Copilot:**
- Gemini uses "model" role instead of "assistant"
- Map temperature (same range 0-1)
- Map max_tokens to max_output_tokens
- Add default safety settings (configurable)
- Handle Gemini's "parts" structure in messages
- Support text and optional image parts
- Convert function calling format if needed

### Phase 2.3: Gemini Response Normalizer
**TODO:**
- [ ] Extend `normalizers/response.py`:
  - Implement `GeminiResponseNormalizer` class
  - Extract content from Gemini response
  - Normalize usage statistics
  - Handle safety ratings
  - Extract finish reason
- [ ] Map Gemini metadata to unified format

**Instructions for Copilot:**
- Extract text from response.text or response.candidates[0].content.parts[0].text
- Map usage: prompt_token_count → prompt_tokens, etc.
- Include safety_ratings in metadata
- Map finish_reason: STOP, MAX_TOKENS, SAFETY, etc.
- Handle blocked responses (safety filters)
- Extract model name from response

### Phase 2.4: Gemini Provider Implementation
**TODO:**
- [ ] Implement `providers/gemini_provider.py`:
  - Inherit from `BaseProvider`
  - Initialize Gemini client
  - Implement `authenticate()` method
  - Implement `chat_completion()` method
  - Implement `validate_credentials()` method
  - Handle Gemini-specific errors
  - Map Gemini exceptions to FlexiAI exceptions
- [ ] Add support for streaming
- [ ] Handle content safety filters

**Instructions for Copilot:**
- Use `google.generativeai` library
- Configure with: `genai.configure(api_key=api_key)`
- Create model: `model = genai.GenerativeModel(model_name)`
- Use `model.generate_content()` for completion
- Handle errors: `APIError`, `InvalidArgument`, `ResourceExhausted`
- Implement retry logic for rate limits
- Add health check using model info or simple generation
- Handle SAFETY and BLOCKED responses appropriately
- Log all API interactions

### Phase 2.5: Update Client for Multi-Provider
**TODO:**
- [ ] Update `client.py`:
  - Auto-detect and register Gemini provider
  - Update failover logic to support multiple providers
  - Ensure circuit breakers are independent per provider
- [ ] Update configuration examples with Gemini
- [ ] Test OpenAI → Gemini failover

**Instructions for Copilot:**
- Registry should handle multiple providers simultaneously
- Each provider gets its own circuit breaker instance
- Update provider sorting to respect priorities
- Test failover between OpenAI and Gemini
- Ensure no interference between provider states

### Phase 2.6: Gemini-Specific Tests
**TODO:**
- [ ] Unit tests for Gemini provider:
  - Request normalization
  - Response normalization
  - Error handling
  - Safety filter handling
- [ ] Integration tests with real Gemini API:
  - Basic completion
  - Multi-turn conversation
  - Safety filter triggered
  - Failover from OpenAI to Gemini
- [ ] Add mock Gemini responses

**Instructions for Copilot:**
- Mock Gemini API using similar patterns as OpenAI tests
- Test content safety scenarios
- Test parameter mapping accuracy
- Verify usage statistics extraction
- Test with various Gemini models (gemini-pro, gemini-pro-vision)
- Add integration test markers for Gemini

### Phase 2.7: Documentation Update
**TODO:**
- [ ] Update README with Gemini support
- [ ] Add Gemini configuration examples
- [ ] Add Gemini-specific troubleshooting
- [ ] Create `examples/gemini_example.py`
- [ ] Update API reference with Gemini parameters

**Instructions for Copilot:**
- Document how to get Gemini API key
- Show example configuration with both OpenAI and Gemini
- Explain safety settings configuration
- Add example of OpenAI-to-Gemini failover
- Document Gemini-specific limitations or differences

---

## **PHASE 3: Anthropic Claude Integration**

### Phase 3.1: Claude Provider Research and Setup
**TODO:**
- [ ] Research Anthropic Claude API:
  - Authentication method (x-api-key header)
  - Request/response format
  - Available models
  - Rate limits and error codes
  - Streaming support
  - Messages API structure
- [ ] Add Claude dependencies to requirements.txt:
  - `anthropic>=0.7.0`
- [ ] Update documentation with Claude support

**Instructions for Copilot:**
- Study Anthropic's Messages API documentation
- Note Claude's unique message structure (system messages separate)
- Understand Claude's model naming (claude-3-opus, claude-3-sonnet, etc.)
- Map Claude error codes to FlexiAI exceptions
- Document differences in streaming implementation
- Note max_tokens is required for Claude (unlike OpenAI)

### Phase 3.2: Claude Request Normalizer
**TODO:**
- [ ] Extend `normalizers/request.py`:
  - Implement `ClaudeRequestNormalizer` class
  - Handle system message extraction
  - Map unified format to Claude Messages format
  - Convert parameters
  - Handle max_tokens requirement
- [ ] Add Claude-specific parameter handling

**Instructions for Copilot:**
- Claude separates system messages from conversation messages
- Extract system messages and put in `system` parameter
- Remaining messages go in `messages` array
- Ensure max_tokens is always set (default to 4096 if not specified)
- Map temperature (same range 0-1)
- Map top_p, top_k parameters
- Handle Claude's tool use format if applicable
- Validate no consecutive messages with same role

### Phase 3.3: Claude Response Normalizer
**TODO:**
- [ ] Extend `normalizers/response.py`:
  - Implement `ClaudeResponseNormalizer` class
  - Extract content from Claude response
  - Normalize usage statistics
  - Handle stop reasons
  - Extract model information
- [ ] Map Claude metadata to unified format

**Instructions for Copilot:**
- Extract text from response.content[0].text
- Map usage: input_tokens → prompt_tokens, output_tokens → completion_tokens
- Map stop_reason: end_turn → stop, max_tokens → length, etc.
- Include Claude's stop_sequence in metadata if present
- Handle multiple content blocks (Claude can return multiple)
- Extract model from response.model field

### Phase 3.4: Claude Provider Implementation
**TODO:**
- [ ] Implement `providers/anthropic_provider.py`:
  - Inherit from `BaseProvider`
  - Initialize Anthropic client
  - Implement `authenticate()` method
  - Implement `chat_completion()` method
  - Implement `validate_credentials()` method
  - Handle Claude-specific errors
  - Map Claude exceptions to FlexiAI exceptions
- [ ] Add support for streaming
- [ ] Handle Claude-specific features

**Instructions for Copilot:**
- Use `anthropic` library
- Initialize client: `client = anthropic.Anthropic(api_key=api_key)`
- Use `client.messages.create()` for completion
- Handle errors: `APIError`, `RateLimitError`, `APIConnectionError`, `AuthenticationError`
- Implement retry logic for rate limits and timeouts
- Add health check using a simple message request
- Support streaming with `client.messages.stream()`
- Log all API interactions with request IDs
- Handle Claude's required max_tokens parameter

### Phase 3.5: Complete Multi-Provider Integration
**TODO:**
- [ ] Update `client.py`:
  - Auto-detect and register Claude provider
  - Test three-way failover: OpenAI → Gemini → Claude
  - Ensure all circuit breakers work independently
- [ ] Update configuration for three providers
- [ ] Add provider health dashboard method

**Instructions for Copilot:**
- Test all permutations of provider failover
- Ensure priority system works with 3+ providers
- Add method to get real-time status of all providers
- Implement provider preference learning (optional: track success rates)
- Test concurrent requests with multiple providers

### Phase 3.6: Claude-Specific Tests
**TODO:**
- [ ] Unit tests for Claude provider:
  - Request normalization (especially system message handling)
  - Response normalization
  - Error handling
  - Multi-content block handling
- [ ] Integration tests with real Claude API:
  - Basic completion
  - Multi-turn conversation
  - System message handling
  - Three-way failover test
- [ ] Add mock Claude responses

**Instructions for Copilot:**
- Mock Claude API responses accurately
- Test system message extraction logic thoroughly
- Verify max_tokens is always set
- Test with various Claude models
- Add comprehensive failover tests (all provider combinations)
- Test circuit breaker recovery across all providers

### Phase 3.7: Documentation Update
**TODO:**
- [ ] Update README with Claude support
- [ ] Add Claude configuration examples
- [ ] Add Claude-specific troubleshooting
- [ ] Create `examples/claude_example.py`
- [ ] Create `examples/multi_provider_failover.py`
- [ ] Update API reference with Claude parameters

**Instructions for Copilot:**
- Document how to get Claude API key
- Show example configuration with all three providers
- Explain system message handling
- Add example of three-way failover
- Document Claude-specific limitations (max_tokens requirement)
- Include performance comparison considerations

---

## **PHASE 4: Advanced Features and Polish**

### Phase 4.1: Streaming Support
**TODO:**
- [ ] Implement streaming in base provider
- [ ] Add streaming support to OpenAI provider
- [ ] Add streaming support to Gemini provider
- [ ] Add streaming support to Claude provider
- [ ] Implement streaming response normalization
- [ ] Add streaming examples
- [ ] Test streaming with failover

**Instructions for Copilot:**
- Use generator/iterator pattern for streaming
- Yield normalized chunks in consistent format
- Handle streaming errors and failover mid-stream
- Implement reconnection logic if stream breaks
- Add buffering for partial chunks
- Test streaming with all providers
- Document streaming API

### Phase 4.2: Advanced Configuration Options
**TODO:**
- [ ] Add per-provider timeout configuration
- [ ] Add custom retry strategies per provider
- [ ] Add provider-specific parameters pass-through
- [ ] Implement configuration presets (fast, balanced, reliable)
- [ ] Add environment-based configuration (dev, staging, prod)
- [ ] Support configuration hot-reloading

**Instructions for Copilot:**
- Allow override of defaults per provider
- Support provider-specific kwargs in requests
- Create configuration templates for common use cases
- Add validation for preset configurations
- Implement config watchers for file-based config
- Document all configuration options thoroughly

### Phase 4.3: Monitoring and Metrics
**TODO:**
- [ ] Implement metrics collection:
  - Request count per provider
  - Success/failure rates
  - Latency percentiles
  - Token usage
  - Circuit breaker trips
- [ ] Add metrics export (Prometheus format optional)
- [ ] Add health check endpoint logic
- [ ] Create metrics dashboard helper

**Instructions for Copilot:**
- Use thread-safe counters for metrics
- Implement sliding window for rate calculations
- Add method to export metrics as dict/JSON
- Consider using OpenTelemetry for instrumentation (optional)
- Add metrics reset capability
- Document metrics collection and export

### Phase 4.4: Async Support
**TODO:**
- [ ] Create async versions of all providers:
  - `AsyncOpenAIProvider`
  - `AsyncGeminiProvider`
  - `AsyncClaudeProvider`
- [ ] Create `AsyncFlexiAI` client
- [ ] Implement async circuit breaker
- [ ] Add async examples
- [ ] Test async operations thoroughly

**Instructions for Copilot:**
- Use `asyncio` and `aiohttp` for async operations
- Use official async clients from provider SDKs
- Implement async context managers
- Use `asyncio.Lock` for thread safety
- Test with `pytest-asyncio`
- Document async API usage
- Consider maintaining sync and async code separately to avoid complexity

### Phase 4.5: Function/Tool Calling Support
**TODO:**
- [ ] Implement function calling normalization:
  - OpenAI format (functions/tools)
  - Gemini format (function declarations)
  - Claude format (tools)
- [ ] Add function call handling in providers
- [ ] Create unified function calling interface
- [ ] Add examples for function calling
- [ ] Test cross-provider function calling

**Instructions for Copilot:**
- Study each provider's function calling format
- Create mapping between formats
- Handle function call responses
- Support automatic function execution (optional)
- Document function calling API
- Add examples with real function calls


### Phase 4.6: Cost Tracking (continued)
**TODO:**
- [ ] Implement token cost calculation:
  - Add pricing data for each model
  - Calculate cost per request
  - Track cumulative costs per provider
  - Track costs per session/user (if applicable)
- [ ] Add cost estimation before request
- [ ] Create cost report generation
- [ ] Add cost limits and warnings

**Instructions for Copilot:**
- Create pricing database with up-to-date model costs (input/output tokens)
- Store pricing in separate JSON file for easy updates
- Calculate: (prompt_tokens * input_price + completion_tokens * output_price) / 1M
- Add method `estimate_cost(messages, model)` before making request
- Track costs in metrics system
- Add optional cost ceiling that raises error if exceeded
- Create cost summary report method
- Document pricing data source and update schedule
- Add warning in docs that pricing data needs manual updates

### Phase 4.7: Caching Layer (Optional)
**TODO:**
- [ ] Implement response caching:
  - Cache key generation from request
  - TTL-based cache expiration
  - Cache storage (memory/Redis)
  - Cache invalidation
- [ ] Add cache hit/miss metrics
- [ ] Make caching configurable per provider
- [ ] Add cache examples

**Instructions for Copilot:**
- Use request hash as cache key (hash of messages + model + parameters)
- Implement in-memory cache using `cachetools` or simple dict with LRU
- Support Redis backend as optional dependency
- Add cache bypass flag in requests
- Respect rate limits even with cache hits
- Document cache configuration
- Consider cache size limits
- Add cache statistics to metrics

### Phase 4.8: Request/Response Hooks
**TODO:**
- [ ] Implement middleware/hook system:
  - `before_request` hooks
  - `after_response` hooks
  - `on_error` hooks
  - `on_failover` hooks
- [ ] Add built-in hooks:
  - Request logging hook
  - Response logging hook
  - Timing hook
  - Cost tracking hook
- [ ] Create hook registration API
- [ ] Add hook examples

**Instructions for Copilot:**
- Use callable/function pattern for hooks
- Hooks receive context object with request/response/error data
- Allow multiple hooks per event
- Execute hooks in registration order
- Handle hook errors gracefully (log but don't fail request)
- Provide hook context with: timestamp, provider, attempt_number, etc.
- Document hook API and parameters
- Create examples for common use cases (audit logging, custom metrics)

### Phase 4.9: Enhanced Error Handling
**TODO:**
- [ ] Improve error messages with context
- [ ] Add error categorization (retryable vs non-retryable)
- [ ] Implement error aggregation for all failed attempts
- [ ] Add suggestions for common errors
- [ ] Create error documentation
- [ ] Add error handling best practices guide

**Instructions for Copilot:**
- Include provider name, model, and attempt number in errors
- Categorize errors: AUTHENTICATION, RATE_LIMIT, TIMEOUT, API_ERROR, VALIDATION, etc.
- For AllProvidersFailedError, include all individual errors
- Add `is_retryable()` method to exceptions
- Provide helpful error messages (e.g., "Check API key format" for auth errors)
- Create error troubleshooting guide in docs
- Add error code enumeration
- Log full error details but show user-friendly messages

---

## **PHASE 5: Testing, Documentation, and Release**

### Phase 5.1: Comprehensive Testing
**TODO:**
- [ ] Achieve >85% code coverage
- [ ] Add edge case tests:
  - Empty messages
  - Very long messages
  - Invalid configurations
  - Network failures
  - Malformed responses
- [ ] Add stress tests:
  - Concurrent requests (100+)
  - Rapid failover scenarios
  - Circuit breaker under load
- [ ] Add performance benchmarks
- [ ] Create test matrix for Python versions (3.8-3.12)

**Instructions for Copilot:**
- Use `pytest-cov` for coverage reports
- Add `pytest-benchmark` for performance tests
- Create fixtures for common test scenarios
- Use `pytest-xdist` for parallel test execution
- Mock external APIs for unit tests, use real APIs for integration tests
- Add timeout markers for slow tests
- Create separate test suites: unit, integration, e2e, performance
- Document test execution in CONTRIBUTING.md
- Set up GitHub Actions for CI/CD testing

### Phase 5.2: Security Audit
**TODO:**
- [ ] API key handling review:
  - No keys in logs
  - No keys in error messages
  - Secure storage recommendations
- [ ] Dependency security scan
- [ ] Input validation review
- [ ] Rate limiting implementation review
- [ ] Create security best practices guide

**Instructions for Copilot:**
- Use `bandit` for security linting
- Scan dependencies with `safety` or `pip-audit`
- Ensure API keys are masked in all log outputs
- Add input sanitization for all user inputs
- Implement rate limiting per provider (client-side)
- Document secure configuration practices
- Add warning about API key security in docs
- Create security policy (SECURITY.md)

### Phase 5.3: Performance Optimization
**TODO:**
- [ ] Profile code for bottlenecks
- [ ] Optimize request/response normalization
- [ ] Optimize circuit breaker state checks
- [ ] Reduce latency in provider selection
- [ ] Implement connection pooling
- [ ] Add performance tips to documentation

**Instructions for Copilot:**
- Use `cProfile` or `py-spy` for profiling
- Minimize object creation in hot paths
- Use connection pooling for HTTP clients
- Cache provider instances
- Optimize JSON serialization/deserialization
- Consider using `orjson` for faster JSON
- Document performance characteristics
- Add performance benchmarks to README

### Phase 5.4: Complete Documentation
**TODO:**
- [ ] API Reference (all classes, methods, parameters)
- [ ] Architecture deep-dive
- [ ] Configuration reference
- [ ] Troubleshooting guide
- [ ] Migration guide (if coming from direct provider usage)
- [ ] Best practices guide
- [ ] FAQ section
- [ ] Contributing guide (CONTRIBUTING.md)
- [ ] Code of conduct (CODE_OF_CONDUCT.md)
- [ ] License (LICENSE - recommend MIT or Apache 2.0)

**Instructions for Copilot:**
- Use Sphinx for API documentation generation
- Write docs in Markdown or reStructuredText
- Include UML diagrams for architecture
- Add code examples for every major feature
- Create quickstart tutorials (5-minute, 15-minute)
- Document all configuration options with examples
- Add comparison table (OpenAI vs Gemini vs Claude features)
- Include real-world use case examples
- Create troubleshooting flowcharts
- Add video tutorial links (if created)

### Phase 5.5: Example Projects
**TODO:**
- [ ] Create example projects:
  - Simple chatbot with failover
  - Customer support automation
  - Content generation pipeline
  - Data analysis with AI
  - Multi-provider comparison tool
- [ ] Add `examples/` directory with complete projects
- [ ] Include README for each example
- [ ] Test all examples work correctly

**Instructions for Copilot:**
- Create self-contained example projects
- Include requirements.txt for each example
- Add clear instructions to run each example
- Use realistic scenarios
- Show best practices in examples
- Include error handling in examples
- Add comments explaining key concepts
- Make examples progressively complex (basic → advanced)

### Phase 5.6: Package Publishing Preparation
**TODO:**
- [ ] Finalize setup.py and pyproject.toml
- [ ] Create wheel and source distribution
- [ ] Test installation from wheel
- [ ] Prepare release notes (CHANGELOG.md)
- [ ] Version tagging strategy (semantic versioning)
- [ ] Create release checklist

**Instructions for Copilot:**
- Follow semantic versioning: MAJOR.MINOR.PATCH
- Start with version 0.1.0 for initial release
- Ensure all metadata is complete in setup.py:
  - name, version, author, author_email
  - description, long_description, long_description_content_type
  - url, project_urls (documentation, source, issues)
  - classifiers (Python versions, license, development status)
  - keywords, license
- Include all necessary package data in MANIFEST.in
- Test wheel installation in clean environment
- Create release process documentation

### Phase 5.7: GitHub Repository Setup
**TODO:**
- [ ] Create public GitHub repository
- [ ] Add comprehensive README.md
- [ ] Set up GitHub Issues templates
- [ ] Set up Pull Request template
- [ ] Create GitHub Actions workflows:
  - CI/CD testing
  - Code coverage reporting
  - Linting and formatting checks
  - Automated releases
- [ ] Add badges to README (build status, coverage, PyPI version)
- [ ] Create GitHub project board for tracking

**Instructions for Copilot:**
- Initialize repo with appropriate .gitignore (Python)
- Create issue templates: bug report, feature request, question
- Add PR template with checklist
- Set up GitHub Actions:
  - Run tests on push/PR
  - Check code style (black, flake8)
  - Generate coverage report (upload to Codecov)
  - Auto-publish to PyPI on release tag
- Add shields.io badges for: PyPI version, Python versions, license, build status, coverage
- Create contributing guidelines
- Set up branch protection rules

### Phase 5.8: Release and Announcement
**TODO:**
- [ ] Create v1.0.0 release
- [ ] Write release announcement
- [ ] Post on relevant forums/communities:
  - Reddit (r/Python, r/MachineLearning)
  - Hacker News
  - Python Discord servers
  - LinkedIn/Twitter
- [ ] Create demo video (optional)
- [ ] Write blog post about FlexiAI
- [ ] Submit to awesome-python lists

**Instructions for Copilot:**
- Create Git tag: `git tag -a v1.0.0 -m "Initial release"`
- Push tag: `git push origin v1.0.0`
- Create GitHub release with release notes
- Highlight key features in announcement:
  - Multi-provider support (OpenAI, Gemini, Claude)
  - Automatic failover
  - Circuit breaker pattern
  - Easy integration
- Include code example in announcement
- Add GIF/video demo if possible
- Provide installation instructions
- Link to documentation

---

## **PHASE 6: Post-Release Maintenance**

### Phase 6.1: Community Management
**TODO:**
- [ ] Monitor GitHub Issues
- [ ] Respond to questions and bug reports
- [ ] Review and merge pull requests
- [ ] Update documentation based on feedback
- [ ] Create GitHub Discussions for Q&A
- [ ] Set up monitoring for dependency updates

**Instructions for Copilot:**
- Set up issue labels: bug, enhancement, documentation, question
- Create issue response templates
- Set up Dependabot for dependency updates
- Review PRs within 48 hours
- Add contributors to CONTRIBUTORS.md
- Maintain changelog with each release

### Phase 6.2: Feature Requests and Roadmap
**TODO:**
- [ ] Create public roadmap
- [ ] Prioritize feature requests
- [ ] Plan future versions:
  - v1.1: Additional provider support (AWS Bedrock, Azure OpenAI)
  - v1.2: Advanced features (prompt templates, response validation)
  - v2.0: Major improvements based on feedback
- [ ] Implement most requested features

**Instructions for Copilot:**
- Use GitHub Projects for roadmap
- Label issues with versions (e.g., v1.1, v2.0)
- Document breaking changes clearly
- Maintain backward compatibility when possible
- Use semantic versioning for releases

### Phase 6.3: Monitoring and Analytics (Optional)
**TODO:**
- [ ] Set up anonymous usage analytics (opt-in)
- [ ] Track popular features
- [ ] Monitor error reports (with user consent)
- [ ] Analyze failover patterns
- [ ] Create usage dashboard for maintainers

**Instructions for Copilot:**
- Make analytics completely optional and opt-in
- Use privacy-respecting analytics (no PII)
- Document what data is collected
- Provide opt-out mechanism
- Use data to improve library
- Respect user privacy always

---

## Development Guidelines for GitHub Copilot

### Code Style and Standards
```
- Follow PEP 8 style guide strictly
- Use type hints for all functions and methods
- Maximum line length: 100 characters
- Use double quotes for strings
- Use meaningful variable names (no single letters except loop counters)
- Write docstrings for all public classes and methods (Google style)
- Add inline comments for complex logic
- Use f-strings for string formatting
- Prefer explicit over implicit
- Use dataclasses or Pydantic models for structured data
```

### Testing Standards
```
- Minimum 80% code coverage
- Test file naming: test_<module_name>.py
- Test function naming: test_<functionality>_<scenario>
- Use fixtures for common test setup
- Mock external dependencies in unit tests
- Use parametrize for testing multiple scenarios
- Add docstrings to test functions explaining what is being tested
- Group related tests in classes
```

### Git Commit Messages
```
Format: <type>(<scope>): <subject>

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- test: Adding or updating tests
- refactor: Code refactoring
- perf: Performance improvements
- chore: Maintenance tasks

Examples:
- feat(providers): add Gemini provider support
- fix(circuit-breaker): resolve state transition bug
- docs(readme): update installation instructions
- test(openai): add streaming response tests
```

### Branch Naming
```
- feature/<feature-name>
- bugfix/<bug-description>
- hotfix/<critical-fix>
- docs/<documentation-update>
- test/<test-improvement>

Examples:
- feature/gemini-provider
- bugfix/circuit-breaker-timeout
- docs/api-reference
```

### TODO Management
```
Create a TODO.md file in the project root with the following structure:

# FlexiAI Development TODO

## Current Phase: [Phase Number and Name]

### In Progress
- [ ] Task currently being worked on

### Completed ✓
- [x] Completed task 1
- [x] Completed task 2

### Next Up
- [ ] Next task to work on
- [ ] Following task

### Blocked
- [ ] Task blocked by: [reason]

## Phase 1: Core Foundation + OpenAI Support
[Copy all Phase 1 TODOs here]

## Phase 2: Google Gemini Integration
[Copy all Phase 2 TODOs here]

... and so on for all phases

Update this file after completing each task.
```

### Error Handling Pattern
```python
# Always follow this pattern for error handling:

try:
    # Attempt operation
    result = provider.chat_completion(request)
except ProviderSpecificError as e:
    # Log the specific error
    logger.error(f"Provider error: {e}", exc_info=True)
    # Convert to FlexiAI exception
    raise ProviderException(f"Failed to complete request: {str(e)}") from e
except Exception as e:
    # Catch unexpected errors
    logger.exception("Unexpected error occurred")
    raise FlexiAIException(f"Unexpected error: {str(e)}") from e
finally:
    # Cleanup if needed
    pass
```

### Logging Pattern
```python
# Standard logging pattern:

import logging

logger = logging.getLogger(__name__)

# Log levels:
# DEBUG: Detailed diagnostic information
# INFO: General informational messages
# WARNING: Warning messages for potentially harmful situations
# ERROR: Error messages for serious problems
# CRITICAL: Critical messages for very serious errors

# Examples:
logger.debug(f"Request normalized: {request}")
logger.info(f"Using provider: {provider_name}")
logger.warning(f"Retry attempt {attempt} for provider {provider_name}")
logger.error(f"Provider {provider_name} failed: {error}")
logger.critical(f"All providers failed for request {request_id}")
```

### Documentation Pattern
```python
def method_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    Brief description of what the method does.

    Longer description if needed, explaining the purpose and behavior.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this exception is raised

    Example:
        >>> obj = ClassName()
        >>> result = obj.method_name("value1", "value2")
        >>> print(result)
        Expected output
    """
    pass
```

---

## Critical Success Factors

1. **Simplicity**: The API should be dead simple - one line to initialize, one line to call
2. **Reliability**: Failover should be seamless and transparent
3. **Performance**: Minimal overhead compared to direct provider calls
4. **Documentation**: Comprehensive docs with examples for every feature
5. **Testing**: Thorough tests to prevent regressions
6. **Maintenance**: Easy to add new providers in the future

---

## Key Design Decisions

### Provider Priority System
- Priority 1 = highest (tried first)
- Lower numbers = higher priority
- If priorities are equal, use registration order
- Failed providers are skipped in current request but tried again in next request (after cooldown)

### Circuit Breaker Strategy
- Failure threshold: 5 consecutive failures
- Recovery timeout: 60 seconds
- Half-open state: Single test request to check recovery
- Independent breakers per provider

### Request/Response Format
- Use OpenAI format as the base/reference format
- Map other providers to/from this format
- Preserve provider-specific features in metadata
- Keep response format consistent across providers

### Configuration Philosophy
- Sensible defaults for everything
- Environment variables override config file
- Config file overrides defaults
- Explicit parameters override everything

---

## Development Workflow

1. **Before Starting Each Phase:**
   - Review the phase objectives
   - Update TODO.md with phase tasks
   - Create feature branch

2. **During Development:**
   - Write tests first (TDD approach recommended)
   - Implement functionality
   - Update documentation
   - Mark completed tasks in TODO.md

3. **After Completing Each Phase:**
   - Run full test suite
   - Update CHANGELOG.md
   - Review and refactor code
   - Merge to main branch
   - Tag version if applicable

4. **Code Review Checklist:**
   - [ ] Tests pass
   - [ ] Code coverage maintained/improved
   - [ ] Documentation updated
   - [ ] Type hints added
   - [ ] Error handling implemented
   - [ ] Logging added
   - [ ] No security vulnerabilities
   - [ ] Performance acceptable

---

## Copilot Agent Instructions

**Role**: You are an AI coding assistant helping to build FlexiAI, a production-ready Python library for multi-provider GenAI integration with failover capabilities.

**Your Responsibilities:**
1. Follow this plan strictly and sequentially
2. Maintain TODO.md with current progress
3. Write clean, well-documented, tested code
4. Ask for clarification when requirements are ambiguous
5. Suggest improvements while staying aligned with core architecture
6. Flag potential issues early
7. Ensure backward compatibility in updates

**When Starting Work:**
1. Read the current phase objectives
2. Check TODO.md for current tasks
3. Review relevant existing code
4. Plan your implementation approach
5. Write tests first, then implementation

**When Implementing:**
1. Follow all code style guidelines
2. Add comprehensive docstrings
3. Include type hints
4. Implement error handling
5. Add logging statements
6. Write unit tests
7. Update TODO.md as you complete tasks

**When Stuck:**
1. Review the architecture documentation
2. Check similar implementations in the codebase
3. Consult the phase-specific instructions
4. Ask for clarification with specific questions

**Quality Checkpoints:**
- Does this code follow the established patterns?
- Is it well-tested?
- Is it documented?
- Does it handle errors gracefully?
- Is it performant?
- Is it maintainable?

**Remember**: This is a production library that others will depend on. Quality and reliability are paramount. When in doubt, err on the side of more testing and better error handling.

---

## Final Notes

This plan is comprehensive but flexible. As development progresses:
- Adjust timelines based on complexity
- Add tasks as new requirements emerge
- Remove tasks that become irrelevant
- Document all decisions in CHANGELOG.md

The goal is a production-ready, well-tested, well-documented library that developers love to use.

Good luck with development! 🚀
