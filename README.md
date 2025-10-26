# FlexiAI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/Touchkin/FlexiAI/actions/workflows/tests.yml/badge.svg)](https://github.com/Touchkin/FlexiAI/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-98%25-brightgreen.svg)]()

**FlexiAI** is a production-ready Python library that provides a unified interface for multiple GenAI providers with automatic failover capabilities using the circuit breaker pattern.

## 🌟 Features

- **Multi-Provider Support**: OpenAI, Google Vertex AI, and Anthropic Claude
- **Automatic Failover**: Priority-based provider selection with circuit breaker pattern
- **Multi-Worker Synchronization**: Redis-based circuit breaker state sync across workers
- **Unified Interface**: Single API for all providers
- **Type-Safe**: Full type hints and Pydantic validation
- **Production-Ready**: 95% test coverage, comprehensive error handling
- **Flexible Authentication**: API keys, service accounts, and ADC support
- **Token Tracking**: Monitor usage across all providers
- **Request Metadata**: Track which provider handled each request

## 📦 Installation

### Install from GitHub Release

```bash
# Download the latest release
gh release download --repo Touchkin/FlexiAI

# Install the wheel file
pip install flexiai-*.whl
```

### Install from Git Repository

```bash
# Install from a specific release tag
pip install git+https://github.com/Touchkin/FlexiAI.git@v0.3.0

# Or install from main branch (latest development)
pip install git+https://github.com/Touchkin/FlexiAI.git
```

### Provider-Specific Dependencies

```bash
# For OpenAI support
pip install openai

# For Google Vertex AI support
pip install google-genai google-auth

# For Anthropic Claude support
pip install anthropic
```

Or install all providers at once:

```bash
pip install flexiai[all]
```

## 🚀 Quick Start

### Basic Usage with OpenAI

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, Message

# Configure with OpenAI
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            api_key="sk-your-openai-api-key",
            model="gpt-4o-mini",
            priority=1
        )
    ]
)

# Create client and make a request
client = FlexiAI(config)
response = client.chat_completion(
    messages=[
        Message(role="user", content="What is Python?")
    ],
    max_tokens=500
)

print(response.content)
print(f"Tokens used: {response.usage.total_tokens}")
print(f"Provider: {response.provider}")
```

### Using Google Vertex AI (GCP)

```python
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="vertexai",
            api_key="not-used",  # Vertex AI uses OAuth2, not API keys
            model="gemini-2.0-flash",
            priority=1,
            config={
                "project": "your-gcp-project-id",
                "location": "us-central1",
                "service_account_file": "/path/to/service-account.json"
            }
        )
    ]
)

client = FlexiAI(config)
response = client.chat_completion(
    messages=[
        Message(role="user", content="Hello!")
    ]
)
```

### Using Anthropic Claude

```python
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="anthropic",
            api_key="sk-ant-your-anthropic-api-key",
            model="claude-3-5-sonnet-20241022",
            priority=1
        )
    ]
)

client = FlexiAI(config)
response = client.chat_completion(
    messages=[
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Explain quantum computing briefly.")
    ],
    max_tokens=200
)

print(response.content)
```

**Supported Claude Models:**
- `claude-3-opus-20240229` - Most capable model
- `claude-3-sonnet-20240229` - Balanced performance
- `claude-3-haiku-20240307` - Fastest responses
- `claude-3-5-sonnet-20241022` - Latest Sonnet (recommended)
- `claude-3-5-haiku-20241022` - Latest Haiku

## 🔄 Multi-Provider Failover

Configure multiple providers with priorities for automatic failover:

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, Message, CircuitBreakerConfig

config = FlexiAIConfig(
    providers=[
        # Primary: OpenAI
        ProviderConfig(
            name="openai",
            api_key="sk-your-openai-key",
            model="gpt-4o-mini",
            priority=1
        ),
        # Secondary: Google Vertex AI
        ProviderConfig(
            name="vertexai",
            api_key="not-used",
            model="gemini-2.0-flash-exp",
            priority=2,
            config={
                "project": "your-gcp-project",
                "location": "us-central1",
                "service_account_file": "/path/to/credentials.json"
            }
        ),
        # Tertiary: Anthropic Claude
        ProviderConfig(
            name="anthropic",
            api_key="sk-ant-your-anthropic-key",
            model="claude-3-5-sonnet-20241022",
            priority=3
        )
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60,
        expected_exception="ProviderException"
    )
)

client = FlexiAI(config)

# If OpenAI fails, automatically falls back to Vertex AI, then Claude
response = client.chat_completion(
    messages=[Message(role="user", content="Tell me a joke")]
)

# Check which provider was used
print(f"Response from: {response.provider}")
```

## 🎯 Advanced Features

### System Messages

```python
response = client.chat_completion(
    messages=[
        Message(role="system", content="You are a helpful Python expert"),
        Message(role="user", content="How do I use decorators?")
    ],
    max_tokens=1000
)
```

### Multi-Turn Conversations

```python
conversation = [
    Message(role="user", content="What is Flask?"),
    Message(role="assistant", content="Flask is a lightweight Python web framework..."),
    Message(role="user", content="How does it compare to Django?")
]

response = client.chat_completion(
    messages=conversation,
    temperature=0.8
)
```

### Provider Status Monitoring

```python
# Get health status of all providers
status = client.get_provider_status()
for provider_info in status['providers']:
    print(f"{provider_info['name']}: {provider_info['healthy']}")
    print(f"  Circuit Breaker: {provider_info['circuit_breaker']['state']}")
    print(f"  Success Rate: {provider_info['successful_requests']}/{provider_info['total_requests']}")
```

### Multi-Worker Deployments

FlexiAI supports circuit breaker state synchronization across multiple workers using Redis. When one worker opens a circuit breaker, all other workers are immediately notified.

```python
from flexiai.models import SyncConfig

config = FlexiAIConfig(
    providers=[...],
    sync=SyncConfig(
        enabled=True,
        backend="redis",
        redis_host="localhost",
        redis_port=6379,
        state_ttl=3600  # State expires after 1 hour
    )
)

# Use with Gunicorn/Uvicorn
# gunicorn app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

**Key Benefits:**
- **Consistent Behavior**: All workers react to failures simultaneously
- **Faster Recovery**: Distributed state prevents redundant failure attempts
- **Production-Ready**: Tested with Gunicorn, Uvicorn, and Kubernetes deployments

See [Multi-Worker Deployment Guide](docs/multi-worker-deployment.md) for detailed setup instructions.

## 🌐 Using FlexiAI with FastAPI

FlexiAI integrates seamlessly with FastAPI applications, supporting both single-worker and multi-worker deployments with Redis-based synchronization.

### Method 1: Normal FastAPI Integration

Create a production-ready FastAPI application with FlexiAI:

```python
"""
FastAPI application with FlexiAI multi-provider support.
Supports multi-worker deployment with Redis synchronization.
"""

import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, SyncConfig


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    max_tokens: int = 500


class ChatResponse(BaseModel):
    response: str
    provider: str
    tokens_used: int
    worker_id: int


# Global FlexiAI client
flexiai_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize FlexiAI on startup, cleanup on shutdown."""
    global flexiai_client

    # Configure FlexiAI with multiple providers and Redis sync
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=1,
            ),
            ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-haiku-20241022",
                priority=2,
            ),
            ProviderConfig(
                name="vertexai",
                api_key="not-used",
                model="gemini-2.0-flash-exp",
                priority=3,
                config={
                    "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
                    "location": "us-central1",
                },
            ),
        ],
        # Enable Redis sync for multi-worker deployments
        sync=SyncConfig(
            enabled=True,
            backend="redis",
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
        ),
        timeout=30.0,
    )

    flexiai_client = FlexiAI(config)
    print(f"✅ FlexiAI initialized with {len(config.providers)} providers")

    yield

    # Cleanup
    if flexiai_client:
        flexiai_client.close()
        print("🛑 FlexiAI client closed")


# Create FastAPI app
app = FastAPI(
    title="FlexiAI Chat API",
    description="Multi-provider AI chat with automatic failover",
    lifespan=lifespan,
)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a chat message and get AI response.

    Automatically handles provider failover and circuit breakers.
    """
    try:
        response = flexiai_client.chat_completion(
            messages=[{"role": "user", "content": request.message}],
            max_tokens=request.max_tokens,
        )

        return ChatResponse(
            response=response.content,
            provider=response.provider,
            tokens_used=response.usage.total_tokens,
            worker_id=os.getpid(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI request failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Check API health and provider status."""
    provider_status = flexiai_client.get_provider_status()
    stats = flexiai_client.get_request_stats()

    healthy_providers = [
        p["name"] for p in provider_status["providers"] if p["healthy"]
    ]

    return {
        "status": "healthy" if healthy_providers else "degraded",
        "worker_id": os.getpid(),
        "providers": {
            "total": len(provider_status["providers"]),
            "healthy": len(healthy_providers),
            "names": healthy_providers,
        },
        "stats": stats,
    }


@app.get("/providers")
async def get_providers():
    """Get detailed provider status including circuit breakers."""
    return flexiai_client.get_provider_status()


if __name__ == "__main__":
    import uvicorn

    # Single worker for development
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

    # Multi-worker for production (requires Redis)
    # uvicorn.run("app:app", host="0.0.0.0", port=8000, workers=4)
```

**Run the application:**

```bash
# Development (single worker, auto-reload)
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Production (4 workers with Redis sync)
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4

# With Gunicorn (recommended for production)
gunicorn app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Test the endpoints:**

```bash
# Send a chat message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Python?", "max_tokens": 500}'

# Check health
curl http://localhost:8000/health

# Get provider status
curl http://localhost:8000/providers
```

### Method 2: Using Decorators (Recommended)

FlexiAI provides decorators for cleaner integration with FastAPI:

```python
"""
FastAPI application using FlexiAI decorators.
Cleaner code with built-in error handling and monitoring.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from flexiai import FlexiAI
from flexiai.decorators import flexiai_chat_completion, flexiai_configure
from flexiai.models import FlexiAIConfig, ProviderConfig, SyncConfig


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    system_prompt: str = "You are a helpful assistant."
    max_tokens: int = 500


class ChatResponse(BaseModel):
    response: str
    provider: str
    tokens_used: int
    worker_id: int


# Global FlexiAI client
flexiai_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize FlexiAI on startup."""
    global flexiai_client

    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=1,
            ),
            ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-haiku-20241022",
                priority=2,
            ),
        ],
        sync=SyncConfig(
            enabled=True,
            backend="redis",
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
        ),
    )

    flexiai_client = FlexiAI(config)
    # Configure decorators to use this client
    flexiai_configure(flexiai_client)

    yield

    if flexiai_client:
        flexiai_client.close()


app = FastAPI(
    title="FlexiAI Chat API (Decorators)",
    description="Clean decorator-based FastAPI integration",
    lifespan=lifespan,
)


# Method 1: Using decorator on regular function
@flexiai_chat_completion(
    max_tokens=500,
    temperature=0.7,
    handle_errors=True,  # Automatic error handling
)
def generate_response(user_message: str, system_prompt: str):
    """
    Generate AI response using FlexiAI decorator.

    The decorator automatically:
    - Formats messages
    - Handles provider failover
    - Manages circuit breakers
    - Returns FlexiAI response object
    """
    return {
        "system": system_prompt,
        "user": user_message,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint using FlexiAI decorator.

    Benefits:
    - Cleaner code (no manual FlexiAI calls)
    - Automatic error handling
    - Built-in monitoring
    - Circuit breaker integration
    """
    try:
        # Call decorated function
        response = generate_response(
            user_message=request.message,
            system_prompt=request.system_prompt,
        )

        return ChatResponse(
            response=response.content,
            provider=response.provider,
            tokens_used=response.usage.total_tokens,
            worker_id=os.getpid(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Method 2: Using decorator with custom message formatting
@flexiai_chat_completion(max_tokens=200, temperature=0.5)
def summarize_text(text: str):
    """Summarize text using AI."""
    return {
        "system": "You are a text summarization expert. Provide concise summaries.",
        "user": f"Summarize this text:\n\n{text}",
    }


@app.post("/summarize")
async def summarize(text: str):
    """Summarize text endpoint."""
    try:
        response = summarize_text(text=text)
        return {
            "summary": response.content,
            "provider": response.provider,
            "tokens": response.usage.total_tokens,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Method 3: Using decorator with list of messages
@flexiai_chat_completion(max_tokens=1000)
def chat_with_history(messages: list):
    """Chat with conversation history."""
    return messages  # Decorator handles the message formatting


@app.post("/chat-history")
async def chat_history(messages: list):
    """
    Chat with conversation history.

    Example:
    [
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is..."},
        {"role": "user", "content": "Tell me more"}
    ]
    """
    try:
        response = chat_with_history(messages=messages)
        return {
            "response": response.content,
            "provider": response.provider,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check with provider status."""
    return flexiai_client.get_provider_status()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, workers=4)
```

**Run with decorators:**

```bash
# Development
uvicorn app:app --reload

# Production (4 workers)
uvicorn app:app --workers 4

# Test the endpoints
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain FastAPI in 2 sentences",
    "system_prompt": "You are a Python expert",
    "max_tokens": 200
  }'

curl -X POST http://localhost:8000/summarize?text="Long%20text%20here"

curl -X POST http://localhost:8000/chat-history \
  -H "Content-Type: application/json" \
  -d '[
    {"role": "user", "content": "Hi!"},
    {"role": "assistant", "content": "Hello! How can I help?"},
    {"role": "user", "content": "What is FastAPI?"}
  ]'
```

### Decorator Benefits

✅ **Cleaner Code**: Less boilerplate, more readable
✅ **Automatic Error Handling**: Built-in exception management
✅ **Monitoring**: Automatic request/response logging
✅ **Type Safety**: Full type hints and validation
✅ **Reusable**: Decorate any function, not just FastAPI routes
✅ **Circuit Breakers**: Automatic failover and recovery

### Multi-Worker Production Setup

For production deployments with multiple workers, ensure Redis is running:

```bash
# Start Redis (required for multi-worker sync)
redis-server

# Set environment variables
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export REDIS_HOST="localhost"
export REDIS_PORT="6379"

# Run with 4 workers (circuit breaker state synced via Redis)
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

**What happens with multi-worker sync:**
1. Worker 1 detects OpenAI is down (3+ failures)
2. Worker 1 opens circuit breaker and publishes event to Redis
3. Workers 2, 3, 4 receive the event within milliseconds
4. All workers open their OpenAI circuit breakers
5. All workers automatically failover to next provider (Anthropic)
6. **Result:** Consistent behavior across all workers!

See `tests/integration/test_multiworker_fastapi.py` for a complete working example.

### Request Statistics

```python
# Track requests and providers used
stats = client.get_request_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Successful: {stats['successful_requests']}")
print(f"Failed: {stats['failed_requests']}")
print(f"Providers used: {stats['providers_used']}")
```

### Circuit Breaker Control

```python
# Manually reset circuit breakers if needed
client.reset_circuit_breakers()

# Check last used provider
last_provider = client.get_last_used_provider()
print(f"Last request handled by: {last_provider}")
```

### Testing Circuit Breaker

The circuit breaker protects your application from cascading failures by detecting and isolating failing providers. Here's how to test it:

#### Test 1: Invalid Credentials Detection

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig
from flexiai.exceptions import AllProvidersFailedError

# Create client with invalid API key
client = FlexiAI(FlexiAIConfig(providers=[
    ProviderConfig(
        name="anthropic",
        priority=1,
        api_key="sk-ant-invalid-key-for-testing-12345678901234567890",
        model="claude-3-5-haiku-20241022"
    )
]))

# Make multiple requests - circuit breaker will track failures
failures = 0
for i in range(5):
    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": "test"}]
        )
    except AllProvidersFailedError:
        failures += 1
        print(f"Failure {failures}: Circuit breaker counting failures")

print(f"Total failures detected: {failures}/5")
print("✅ Circuit breaker is working - invalid credentials properly rejected")
```

#### Test 2: Automatic Failover

```python
# Configure primary provider (will fail) and backup provider (will succeed)
# Note: Must use different provider names
client = FlexiAI(FlexiAIConfig(providers=[
    ProviderConfig(
        name="openai",
        priority=1,  # Primary
        api_key="sk-invalid-key-will-fail-12345678901234567890",
        model="gpt-3.5-turbo"
    ),
    ProviderConfig(
        name="anthropic",
        priority=2,  # Backup
        api_key=os.getenv("ANTHROPIC_API_KEY"),  # Valid key
        model="claude-3-5-haiku-20241022"
    )
]))

# Make request - should automatically failover to backup
try:
    response = client.chat_completion(
        messages=[{"role": "user", "content": "Say 'Failover works!'"}]
    )
    print(f"✅ Failover successful!")
    print(f"Response: {response.content}")
    print(f"Provider used: {response.provider}")

    # Check statistics
    stats = client.get_request_stats()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Successful: {stats['successful_requests']}")
    print(f"Failed: {stats['failed_requests']}")
except Exception as e:
    print(f"❌ Failover failed: {e}")
```

#### Test 3: Circuit Breaker States

```python
# Monitor circuit breaker state transitions
provider_status = client.get_provider_status()

for provider_info in provider_status['providers']:
    print(f"\nProvider: {provider_info['name']}")
    print(f"  State: {provider_info['circuit_breaker']['state']}")
    print(f"  Healthy: {provider_info['healthy']}")
    print(f"  Failure Count: {provider_info['circuit_breaker']['failure_count']}")
    print(f"  Success Count: {provider_info['circuit_breaker']['success_count']}")
```

**Circuit Breaker States:**
- **CLOSED**: Normal operation, requests passing through
- **OPEN**: Too many failures, requests blocked (fail-fast)
- **HALF_OPEN**: Testing recovery, limited requests allowed

#### Test 4: Recovery Testing

```python
import time

# Create client with valid credentials
client = FlexiAI(FlexiAIConfig(providers=[
    ProviderConfig(
        name="anthropic",
        priority=1,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-5-haiku-20241022"
    )
]))

# Make successful request
response = client.chat_completion(
    messages=[{"role": "user", "content": "Hello"}]
)
print(f"✅ Successful request: {response.content}")

# Check that circuit is CLOSED (healthy)
status = client.get_provider_status()
for provider_info in status['providers']:
    state = provider_info['circuit_breaker']['state']
    print(f"Circuit state after success: {state}")
    assert state == "CLOSED", "Circuit should be CLOSED after successful request"
```

#### Complete Test Script

For a comprehensive test, see `examples/circuit_breaker_test.py`:

```bash
# Set your API keys
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export OPENAI_API_KEY="sk-..."

# Run the test
python examples/circuit_breaker_test.py
```

**What the test validates:**
- ✅ Invalid credentials are detected immediately
- ✅ Circuit breaker tracks failure counts
- ✅ Automatic failover to backup providers
- ✅ Provider health monitoring
- ✅ Request statistics tracking
- ✅ Graceful error handling

## 🔧 Configuration

### From Dictionary

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig

config_dict = {
    "providers": [
        {
            "name": "openai",
            "api_key": "sk-...",
            "model": "gpt-4o-mini",
            "priority": 1,
            "config": {
                "timeout": 30,
                "max_retries": 3
            }
        }
    ],
    "circuit_breaker": {
        "failure_threshold": 5,
        "recovery_timeout": 60
    }
}

config = FlexiAIConfig(**config_dict)
client = FlexiAI(config)
```

### From Environment Variables

```bash
export OPENAI_API_KEY="sk-your-key"
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

```python
import os
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig

config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",
            priority=1
        ),
        ProviderConfig(
            name="vertexai",
            api_key="not-used",
            model="gemini-2.0-flash",
            priority=2,
            config={
                "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "location": "us-central1"
            }
        )
    ]
)

client = FlexiAI(config)
```

## 🔐 Authentication

### OpenAI

OpenAI uses API keys for authentication:

```python
ProviderConfig(
    name="openai",
    api_key="sk-proj-...",  # Get from https://platform.openai.com/api-keys
    model="gpt-4o-mini"
)
```

### Google Vertex AI

Vertex AI supports multiple authentication methods:

#### Option 1: Service Account (Recommended for Production)

```python
ProviderConfig(
    name="vertexai",
    api_key="not-used",
    model="gemini-2.0-flash-exp",
    config={
        "project": "your-gcp-project-id",
        "location": "us-central1",
        "service_account_file": "/path/to/service-account.json"
    }
)
```

#### Option 2: Application Default Credentials (ADC)

```bash
# Authenticate using gcloud
gcloud auth application-default login

# Or set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

```python
ProviderConfig(
    name="vertexai",
    api_key="not-used",
    model="gemini-2.0-flash-exp",
    config={
        "project": "your-gcp-project-id",
        "location": "us-central1"
        # Will use ADC automatically
    }
)
```

### Anthropic Claude

Anthropic uses API keys for authentication:

```bash
# Set environment variable
export ANTHROPIC_API_KEY="sk-ant-..."
```

```python
ProviderConfig(
    name="anthropic",
    api_key="sk-ant-...",  # Get from https://console.anthropic.com/
    model="claude-3-5-sonnet-20241022"
)
```

Or load from environment:

```python
import os

ProviderConfig(
    name="anthropic",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-3-5-sonnet-20241022"
)
```

## 🛠️ Supported Models

### OpenAI Models

- `gpt-4o` - Most capable model
- `gpt-4o-mini` - Fast and affordable
- `gpt-4-turbo` - Previous generation flagship
- `gpt-3.5-turbo` - Fast and efficient

### Google Vertex AI Models

- `gemini-2.0-flash-exp` - Latest experimental Gemini on GCP
- `gemini-1.5-pro` - Advanced Gemini on GCP
- `gemini-1.5-flash` - Fast Gemini on GCP
- `text-bison` - Text generation
- `chat-bison` - Chat interactions
- `codechat-bison` - Code assistance

### Anthropic Claude Models

- `claude-3-opus-20240229` - Most capable, best for complex tasks
- `claude-3-sonnet-20240229` - Balanced performance and speed
- `claude-3-haiku-20240307` - Fastest, most cost-effective
- `claude-3-5-sonnet-20241022` - Latest Sonnet (recommended)
- `claude-3-5-haiku-20241022` - Latest Haiku

## 📚 Documentation

- [Architecture](docs/architecture.md) - System design and patterns
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Configuration Guide](docs/configuration.md) - Advanced configuration options
- [Examples](examples/) - Code examples and tutorials

## 🔧 Troubleshooting

### OpenAI Issues

#### Invalid API Key
```
Error: AuthenticationError: Incorrect API key provided
```
**Solution**:
- Verify API key starts with `sk-proj-` or `sk-`
- Check at https://platform.openai.com/api-keys
- Ensure no extra spaces or newlines in the key

#### Rate Limiting
```
Error: RateLimitError: You exceeded your current quota
```
**Solution**:
- Check your OpenAI account billing at https://platform.openai.com/account/billing
- Upgrade your plan or add payment method
- Implement exponential backoff (built into FlexiAI)

### Google Vertex AI Issues

#### Authentication Failed
```
Error: 401 UNAUTHENTICATED
```
**Solution**:

**For Service Account**:
```bash
# Verify file exists
ls -l /path/to/service-account.json

# Check file permissions
chmod 600 /path/to/service-account.json

# Verify JSON format
python -m json.tool service-account.json
```

**For ADC**:
```bash
# Re-authenticate
gcloud auth application-default login

# Verify authentication
gcloud auth application-default print-access-token

# Set project
gcloud config set project YOUR_PROJECT_ID
```

#### API Not Enabled
```
Error: Vertex AI API has not been used in project xxx before or it is disabled
```
**Solution**:
```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID

# Or visit: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
```

#### Permission Denied
```
Error: 403 PERMISSION_DENIED
```
**Solution**:
- Grant "Vertex AI User" role to your service account:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

#### Wrong Project or Location
```
Error: Project not found or Location not supported
```
**Solution**:
- Verify project ID: `gcloud projects list`
- Check supported locations: us-central1, us-east1, europe-west1, asia-northeast1
- Ensure project has billing enabled

#### API Keys Not Supported
```

#### API Keys Not Supported
```
Error: API keys are not supported by this API
```
**Solution**:
- Vertex AI requires OAuth2, not API keys
- Use service account file or ADC
- Vertex AI uses different authentication than Gemini Developer API

### Multi-Provider Failover Issues

#### All Providers Failed
```
Error: AllProvidersFailedError: All configured providers failed
```
**Solution**:
- Check each provider's credentials individually
- Verify network connectivity
- Review circuit breaker status: `client.get_provider_status()`
- Reset circuit breakers: `client.reset_circuit_breakers()`

#### Circuit Breaker Always Open
```
Warning: Circuit breaker open, skipping provider
```
**Solution**:
- Check provider health: `client.get_provider_status()`
- Wait for recovery timeout (default: 60 seconds)
- Manually reset: `client.reset_circuit_breakers()`
- Adjust threshold: `CircuitBreakerConfig(failure_threshold=10)`

### Common Configuration Issues

#### Environment Variables Not Loaded
```python
# ❌ Wrong
api_key = "$OPENAI_API_KEY"  # Literal string, not the value!

# ✅ Correct
import os
api_key = os.getenv("OPENAI_API_KEY")
```

#### Mixing Provider Types
```python
# ❌ Wrong - Vertex AI doesn't use Gemini API keys
ProviderConfig(
    name="vertexai",
    api_key="AIza...",  # Won't work!
    ...
)

# ✅ Correct - Vertex AI needs service account
ProviderConfig(
    name="vertexai",
    api_key="not-used",
    config={"service_account_file": "..."}
)
```

### Getting Help

If you're still experiencing issues:

1. **Check logs**: Enable debug logging
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Verify installation**:
   ```bash
   pip show flexiai
   pip list | grep -E "(openai|google-genai|google-auth)"
   ```

3. **Test providers individually**:
   ```python
   # Test each provider separately first
   config = FlexiAIConfig(providers=[single_provider])
   ```

4. **Open an issue**: Include:
   - FlexiAI version
   - Python version
   - Provider being used
   - Error message and stack trace (remove API keys!)
   - Minimal code to reproduce

## 🧪 Development

### Setup

```bash
git clone https://github.com/yourusername/flexiai.git
cd flexiai
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=flexiai --cov-report=html

# Run specific test file
pytest tests/unit/test_client.py

# Run integration tests (requires API keys)
export OPENAI_API_KEY="sk-..."
export GOOGLE_CLOUD_PROJECT="your-project"
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black flexiai tests

# Type checking
mypy flexiai

# Linting
flake8 flexiai tests
```

### Building and Installing

```bash
# Install build tool
pip install build

# Build wheel package
python -m build

# Install the built package
pip install dist/flexiai-*.whl
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for their powerful language models
- Google for Gemini and Vertex AI platforms
- The Python community for excellent libraries

## 📮 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/flexiai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/flexiai/discussions)
- **Email**: support@flexiai.dev

## 🗺️ Roadmap

- [x] Phase 1: OpenAI Support
- [x] Phase 2: Google Vertex AI Support
- [x] Phase 3: Anthropic Claude Support
- [ ] Phase 4: Streaming Support
- [ ] Phase 5: Azure OpenAI Support
- [ ] Phase 6: AWS Bedrock Support
- [ ] Advanced Features:
  - [ ] Function/Tool calling
  - [ ] Image generation
  - [ ] Embeddings support
  - [ ] Fine-tuning integration
  - [ ] Caching layer
  - [ ] Rate limiting per provider

---

**Made with ❤️ by the AI Team at WYSA**
