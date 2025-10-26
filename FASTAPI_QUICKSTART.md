# FlexiAI FastAPI Quick Start Guide

Get FlexiAI running in your FastAPI application in less than 5 minutes!

## 🚀 Quick Start (Method 1: Normal Integration)

### Step 1: Install Dependencies

```bash
pip install flexiai fastapi uvicorn redis
```

### Step 2: Create Your FastAPI App

Save as `app.py`:

```python
import os
from contextlib import asynccontextmanager
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

# Global FlexiAI client
flexiai_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global flexiai_client

    # Configure FlexiAI
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=1,
            ),
        ],
        sync=SyncConfig(enabled=False),  # Enable for multi-worker
    )

    flexiai_client = FlexiAI(config)
    yield
    if flexiai_client:
        flexiai_client.close()

app = FastAPI(lifespan=lifespan)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response = flexiai_client.chat_completion(
            messages=[{"role": "user", "content": request.message}],
            max_tokens=request.max_tokens,
        )
        return ChatResponse(
            response=response.content,
            provider=response.provider,
            tokens_used=response.usage.total_tokens,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### Step 3: Set Environment Variables

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

### Step 4: Run the Application

```bash
# Development (single worker, auto-reload)
uvicorn app:app --reload

# Production (4 workers)
uvicorn app:app --workers 4
```

### Step 5: Test It

```bash
# Send a chat message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Python?", "max_tokens": 500}'

# Check health
curl http://localhost:8000/health
```

---

## 🎨 Quick Start (Method 2: Using Decorators) - RECOMMENDED

### Step 1: Install Dependencies

```bash
pip install flexiai fastapi uvicorn
```

### Step 2: Create Your FastAPI App

Save as `app.py`:

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from flexiai import FlexiAI
from flexiai.decorators import flexiai_chat_completion, flexiai_configure
from flexiai.models import FlexiAIConfig, ProviderConfig

class ChatRequest(BaseModel):
    message: str
    system_prompt: str = "You are a helpful assistant."
    max_tokens: int = 500

class ChatResponse(BaseModel):
    response: str
    provider: str
    tokens_used: int

flexiai_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global flexiai_client

    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=1,
            ),
        ],
    )

    flexiai_client = FlexiAI(config)
    flexiai_configure(flexiai_client)  # Configure decorators
    yield
    if flexiai_client:
        flexiai_client.close()

app = FastAPI(lifespan=lifespan)

# Use decorator for clean integration
@flexiai_chat_completion(max_tokens=500, temperature=0.7)
def generate_response(user_message: str, system_prompt: str):
    return {
        "system": system_prompt,
        "user": user_message,
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response = generate_response(
            user_message=request.message,
            system_prompt=request.system_prompt,
        )
        return ChatResponse(
            response=response.content,
            provider=response.provider,
            tokens_used=response.usage.total_tokens,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Step 3: Run and Test

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
uvicorn app:app --reload

# Test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain FastAPI in 2 sentences",
    "system_prompt": "You are a Python expert",
    "max_tokens": 200
  }'
```

---

## 🔄 Multi-Worker Setup with Redis

For production deployments with multiple workers:

### Step 1: Start Redis

```bash
redis-server
```

### Step 2: Update Configuration

```python
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
        redis_db=int(os.getenv("REDIS_DB", "0")),
    ),
)
```

### Step 3: Run with Multiple Workers

```bash
# Set environment variables
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export REDIS_HOST="localhost"
export REDIS_PORT="6379"

# Run with 4 workers
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4

# Or with Gunicorn (recommended for production)
gunicorn app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### What Happens:
- ✅ Worker 1 detects OpenAI is down → opens circuit breaker
- ✅ Event published to Redis channel "flexiai:events"
- ✅ Workers 2, 3, 4 receive event within milliseconds
- ✅ All workers open their circuit breakers
- ✅ All workers failover to Anthropic
- ✅ Consistent behavior across all workers!

---

## 📚 Additional Endpoints

Add these to your FastAPI app for better monitoring:

```python
@app.get("/providers")
async def get_providers():
    """Get detailed provider status including circuit breakers."""
    return flexiai_client.get_provider_status()

@app.get("/stats")
async def get_stats():
    """Get request statistics."""
    return flexiai_client.get_request_stats()

@app.post("/reset-circuit-breakers")
async def reset_circuit_breakers():
    """Manually reset all circuit breakers."""
    flexiai_client.reset_circuit_breakers()
    return {"status": "Circuit breakers reset"}
```

---

## 🔍 Testing Your Endpoints

```bash
# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "max_tokens": 100}'

# Provider status
curl http://localhost:8000/providers | jq

# Statistics
curl http://localhost:8000/stats | jq

# Health check
curl http://localhost:8000/health
```

---

## 🎯 Next Steps

1. **Add More Providers**: Configure multiple AI providers for automatic failover
2. **Custom Endpoints**: Create specialized endpoints (summarize, translate, etc.)
3. **Authentication**: Add FastAPI authentication/authorization
4. **Rate Limiting**: Implement rate limiting per user/endpoint
5. **Logging**: Add structured logging for production
6. **Monitoring**: Integrate with Prometheus/Grafana

---

## 📖 Complete Documentation

For comprehensive documentation, see:
- **README.md**: Full FlexiAI features and configuration
- **tests/integration/test_multiworker_fastapi.py**: Complete working example
- **MULTI_WORKER_REDIS_SYNC_VERIFICATION.md**: Multi-worker testing results

---

## 💡 Tips

- **Development**: Use `--reload` for auto-restart on code changes
- **Production**: Use 4+ workers with Redis sync enabled
- **Testing**: Start with one provider, then add more for failover
- **Monitoring**: Check `/providers` endpoint regularly for circuit breaker states
- **API Keys**: Never commit API keys! Always use environment variables

---

**That's it! You now have FlexiAI running in your FastAPI application with automatic failover and circuit breakers.** 🚀
