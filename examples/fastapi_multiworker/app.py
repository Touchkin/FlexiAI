"""
Production-Ready FastAPI Application with FlexiAI Multi-Worker Support

This example demonstrates how to deploy FlexiAI in a production environment
with multiple uvicorn workers and Redis-based state synchronization.

Features:
- Multiple LLM providers with automatic failover
- Redis-based circuit breaker state synchronization across workers
- Comprehensive health check endpoints
- Graceful shutdown handling
- Both decorator and direct client usage examples
- Structured logging
- Production-ready error handling

Run with:
    uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4

Or for development:
    uvicorn app:app --reload
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from flexiai import FlexiAI
from flexiai.decorators import flexiai_chat_completion
from flexiai.types import Message, ProviderConfig, SyncConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [Worker:%(process)d] - %(message)s",
)
logger = logging.getLogger(__name__)

# Global FlexiAI client instance
flexiai_client: Optional[FlexiAI] = None
redis_client: Optional[redis.Redis] = None

# Environment configuration with defaults
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")  # Optional

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Worker identification
WORKER_ID = os.getpid()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Handles graceful initialization and cleanup of resources.
    """
    global flexiai_client, redis_client

    logger.info(f"🚀 Starting FlexiAI worker {WORKER_ID}")

    try:
        # Initialize Redis client for health checks
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )
        await redis_client.ping()
        logger.info(f"✅ Redis connection established at {REDIS_HOST}:{REDIS_PORT}")

    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        logger.warning("⚠️  Proceeding without Redis - state sync will be disabled")
        redis_client = None

    try:
        # Configure providers
        providers = []

        if OPENAI_API_KEY:
            providers.append(
                ProviderConfig(
                    name="openai", api_key=OPENAI_API_KEY, model="gpt-4o-mini", priority=1
                )
            )
            logger.info("✅ OpenAI provider configured")

        if ANTHROPIC_API_KEY:
            providers.append(
                ProviderConfig(
                    name="anthropic",
                    api_key=ANTHROPIC_API_KEY,
                    model="claude-3-5-haiku-20241022",
                    priority=2,
                )
            )
            logger.info("✅ Anthropic provider configured")

        if not providers:
            raise ValueError("No LLM providers configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")

        # Configure sync settings
        sync_config = None
        if redis_client:
            sync_config = SyncConfig(
                enabled=True,
                backend="redis",
                redis_host=REDIS_HOST,
                redis_port=REDIS_PORT,
                redis_db=REDIS_DB,
                redis_password=REDIS_PASSWORD,
            )
            logger.info("✅ Redis sync enabled for multi-worker state sharing")

        # Initialize FlexiAI client
        flexiai_client = FlexiAI(providers=providers, sync=sync_config)

        logger.info(f"✅ FlexiAI client initialized with {len(providers)} provider(s)")
        logger.info(f"🎯 Worker {WORKER_ID} ready to handle requests")

    except Exception as e:
        logger.error(f"❌ Failed to initialize FlexiAI: {e}")
        raise

    yield  # Application runs here

    # Shutdown
    logger.info(f"🛑 Shutting down FlexiAI worker {WORKER_ID}")

    if flexiai_client:
        try:
            # Give time for in-flight requests to complete
            await asyncio.sleep(1)
            logger.info("✅ FlexiAI client cleaned up")
        except Exception as e:
            logger.error(f"❌ Error during FlexiAI cleanup: {e}")

    if redis_client:
        try:
            await redis_client.close()
            logger.info("✅ Redis connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Redis connection: {e}")

    logger.info(f"👋 Worker {WORKER_ID} shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="FlexiAI Multi-Worker API",
    description="Production-ready LLM API with multi-provider support and automatic failover",
    version="1.0.0",
    lifespan=lifespan,
)


# ==============================================================================
# Request/Response Models
# ==============================================================================


class ChatRequest(BaseModel):
    """Chat completion request"""

    message: str = Field(..., description="User message to send to the LLM")
    system_message: Optional[str] = Field(None, description="Optional system message")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")


class ChatResponse(BaseModel):
    """Chat completion response"""

    content: str = Field(..., description="LLM response content")
    provider: str = Field(..., description="Provider that handled the request")
    model: str = Field(..., description="Model used for generation")
    worker_id: int = Field(..., description="Worker process ID that handled the request")
    timestamp: str = Field(..., description="Response timestamp")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Overall health status")
    worker_id: int = Field(..., description="Worker process ID")
    timestamp: str = Field(..., description="Health check timestamp")
    redis_connected: bool = Field(..., description="Redis connection status")
    sync_enabled: bool = Field(..., description="State synchronization enabled")
    providers: List[Dict[str, Any]] = Field(..., description="Provider health status")


class ProviderStatus(BaseModel):
    """Provider status information"""

    name: str
    available: bool
    circuit_state: str
    failure_count: int
    last_failure_time: Optional[str]


class StatsResponse(BaseModel):
    """Statistics response"""

    worker_id: int
    providers: List[ProviderStatus]
    timestamp: str


# ==============================================================================
# Health Check Endpoints
# ==============================================================================


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check endpoint for monitoring and load balancers.

    Checks:
    - FlexiAI client initialization
    - Redis connection (if configured)
    - Provider availability
    - Circuit breaker states

    Returns 200 if healthy, 503 if unhealthy.
    """
    global flexiai_client, redis_client

    timestamp = datetime.utcnow().isoformat()

    # Check FlexiAI client
    if not flexiai_client:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "worker_id": WORKER_ID,
                "timestamp": timestamp,
                "redis_connected": False,
                "sync_enabled": False,
                "providers": [],
                "error": "FlexiAI client not initialized",
            },
        )

    # Check Redis connection
    redis_connected = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_connected = True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")

    # Check provider statuses
    providers_status = []
    all_providers_healthy = True

    for provider_name, provider in flexiai_client.providers.items():
        circuit_breaker = flexiai_client.circuit_breakers.get(provider_name)

        if circuit_breaker:
            state = circuit_breaker.state
            failure_count = circuit_breaker.failure_count
            last_failure = circuit_breaker.last_failure_time

            is_available = state in ["CLOSED", "HALF_OPEN"]

            providers_status.append(
                {
                    "name": provider_name,
                    "model": provider.model,
                    "available": is_available,
                    "circuit_state": state,
                    "failure_count": failure_count,
                    "last_failure_time": last_failure.isoformat() if last_failure else None,
                    "priority": provider.priority,
                }
            )

            if not is_available:
                all_providers_healthy = False
        else:
            providers_status.append(
                {
                    "name": provider_name,
                    "model": provider.model,
                    "available": True,
                    "circuit_state": "UNKNOWN",
                    "failure_count": 0,
                    "last_failure_time": None,
                    "priority": provider.priority,
                }
            )

    # Determine overall status
    overall_status = "healthy" if all_providers_healthy else "degraded"
    status_code = 200 if all_providers_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "worker_id": WORKER_ID,
            "timestamp": timestamp,
            "redis_connected": redis_connected,
            "sync_enabled": (
                flexiai_client.config.sync.enabled if flexiai_client.config.sync else False
            ),
            "providers": providers_status,
        },
    )


@app.get("/health/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes/container orchestration.
    Returns 200 if the worker is ready to accept traffic.
    """
    global flexiai_client

    if not flexiai_client:
        return JSONResponse(
            status_code=503, content={"ready": False, "reason": "FlexiAI client not initialized"}
        )

    # Check if at least one provider is available
    has_available_provider = False
    for provider_name in flexiai_client.providers.keys():
        circuit_breaker = flexiai_client.circuit_breakers.get(provider_name)
        if circuit_breaker and circuit_breaker.state in ["CLOSED", "HALF_OPEN"]:
            has_available_provider = True
            break

    if not has_available_provider:
        return JSONResponse(
            status_code=503, content={"ready": False, "reason": "No providers available"}
        )

    return {"ready": True, "worker_id": WORKER_ID}


@app.get("/health/live")
async def liveness_check():
    """
    Liveness check for Kubernetes/container orchestration.
    Returns 200 if the worker process is alive.
    """
    return {"alive": True, "worker_id": WORKER_ID}


# ==============================================================================
# Provider Management Endpoints
# ==============================================================================


@app.get("/providers", response_model=StatsResponse)
async def get_provider_status():
    """
    Get detailed status of all configured providers.
    Includes circuit breaker states and failure counts.
    """
    global flexiai_client

    if not flexiai_client:
        raise HTTPException(status_code=503, detail="FlexiAI client not initialized")

    providers_status = []

    for provider_name, provider in flexiai_client.providers.items():
        circuit_breaker = flexiai_client.circuit_breakers.get(provider_name)

        if circuit_breaker:
            providers_status.append(
                {
                    "name": provider_name,
                    "available": circuit_breaker.state in ["CLOSED", "HALF_OPEN"],
                    "circuit_state": circuit_breaker.state,
                    "failure_count": circuit_breaker.failure_count,
                    "last_failure_time": (
                        circuit_breaker.last_failure_time.isoformat()
                        if circuit_breaker.last_failure_time
                        else None
                    ),
                }
            )

    return StatsResponse(
        worker_id=WORKER_ID, providers=providers_status, timestamp=datetime.utcnow().isoformat()
    )


@app.post("/providers/{provider_name}/reset")
async def reset_provider_circuit(provider_name: str):
    """
    Reset circuit breaker for a specific provider.
    Useful for manual recovery after fixing provider issues.
    """
    global flexiai_client

    if not flexiai_client:
        raise HTTPException(status_code=503, detail="FlexiAI client not initialized")

    if provider_name not in flexiai_client.circuit_breakers:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")

    circuit_breaker = flexiai_client.circuit_breakers[provider_name]
    circuit_breaker.reset()

    logger.info(f"Circuit breaker reset for provider '{provider_name}' by worker {WORKER_ID}")

    return {
        "message": f"Circuit breaker reset for provider '{provider_name}'",
        "worker_id": WORKER_ID,
        "new_state": circuit_breaker.state,
    }


# ==============================================================================
# Chat Completion Endpoints
# ==============================================================================


@app.post("/chat/direct", response_model=ChatResponse)
async def chat_direct(request: ChatRequest):
    """
    Chat completion using direct FlexiAI client.

    This endpoint demonstrates direct usage of the FlexiAI client
    without decorators, giving you full control over the request.
    """
    global flexiai_client

    if not flexiai_client:
        raise HTTPException(status_code=503, detail="FlexiAI client not initialized")

    try:
        messages = []
        if request.system_message:
            messages.append(Message(role="system", content=request.system_message))
        messages.append(Message(role="user", content=request.message))

        # Create completion with optional parameters
        kwargs = {"temperature": request.temperature}
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens

        response = flexiai_client.chat.completions.create(messages=messages, **kwargs)

        logger.info(f"Worker {WORKER_ID} processed request with provider: {response.provider}")

        return ChatResponse(
            content=response.content,
            provider=response.provider,
            model=response.model,
            worker_id=WORKER_ID,
            timestamp=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Worker {WORKER_ID} error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/decorator", response_model=ChatResponse)
async def chat_decorator(request: ChatRequest):
    """
    Chat completion using decorator pattern.

    This endpoint demonstrates the clean decorator-based approach
    that reduces boilerplate and makes the code more maintainable.
    """

    @flexiai_chat_completion(
        client=flexiai_client,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        system_message=request.system_message,
    )
    def get_completion(user_message: str) -> str:
        """Generate a chat completion"""
        return user_message

    try:
        # The decorator handles all the FlexiAI logic
        response = get_completion(request.message)

        logger.info(f"Worker {WORKER_ID} processed decorator request")

        return ChatResponse(
            content=response.content,
            provider=response.provider,
            model=response.model,
            worker_id=WORKER_ID,
            timestamp=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Worker {WORKER_ID} decorator error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Metrics and Monitoring
# ==============================================================================


@app.get("/metrics")
async def get_metrics():
    """
    Get application metrics for monitoring.
    Can be extended to export Prometheus metrics.
    """
    global flexiai_client, redis_client

    if not flexiai_client:
        raise HTTPException(status_code=503, detail="FlexiAI client not initialized")

    # Collect circuit breaker metrics
    circuit_metrics = {}
    for provider_name, cb in flexiai_client.circuit_breakers.items():
        circuit_metrics[provider_name] = {
            "state": cb.state,
            "failure_count": cb.failure_count,
            "success_count": cb.success_count,
            "last_failure_time": cb.last_failure_time.isoformat() if cb.last_failure_time else None,
            "last_success_time": cb.last_success_time.isoformat() if cb.last_success_time else None,
        }

    # Check Redis connection
    redis_status = "disconnected"
    if redis_client:
        try:
            await redis_client.ping()
            redis_status = "connected"
        except:
            redis_status = "error"

    return {
        "worker_id": WORKER_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "redis_status": redis_status,
        "sync_enabled": flexiai_client.config.sync.enabled if flexiai_client.config.sync else False,
        "circuit_breakers": circuit_metrics,
        "provider_count": len(flexiai_client.providers),
    }


# ==============================================================================
# Root and Info Endpoints
# ==============================================================================


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "FlexiAI Multi-Worker API",
        "version": "1.0.0",
        "worker_id": WORKER_ID,
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "chat_direct": "/chat/direct",
            "chat_decorator": "/chat/decorator",
            "providers": "/providers",
            "metrics": "/metrics",
        },
    }


# ==============================================================================
# Error Handlers
# ==============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception in worker {WORKER_ID}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "worker_id": WORKER_ID,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    # For development - single worker with auto-reload
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
