"""
FastAPI Multi-Worker Circuit Breaker Test

This application tests that circuit breaker state is synchronized across
multiple workers using Redis pub/sub.

Test scenario:
1. Start FastAPI with 4 workers
2. Worker A experiences OpenAI provider failure
3. Worker A trips circuit breaker and publishes event to Redis
4. All other workers (B, C, D) receive event via pub/sub
5. All workers trip their circuit breakers for OpenAI

Run with:
    uvicorn test_multiworker_fastapi:app --workers 4 --host 0.0.0.0 --port 8000
"""

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, SyncConfig


# Response models
class ChatRequest(BaseModel):
    message: str
    provider: str = None  # Optional: specify which provider to use


class ChatResponse(BaseModel):
    response: str
    provider_used: str
    worker_id: str
    circuit_breaker_state: dict


class StatusResponse(BaseModel):
    worker_id: str
    providers: list
    uptime: float
    sync_enabled: bool = False
    sync_backend: str | None = None


# Global FlexiAI client
flexiai_client = None
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize FlexiAI client on startup, cleanup on shutdown."""
    global flexiai_client

    print(f"\n{'='*80}")
    print(f"🚀 Worker {os.getpid()} starting up...")
    print(f"{'='*80}\n")

    # Configure FlexiAI with multiple providers and Redis sync
    config = FlexiAIConfig(
        providers=[
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY", "sk-fake-key-for-testing-only"),
                model="gpt-4o-mini",
                priority=1,
            ),
            ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY", "sk-ant-fake-key-for-testing"),
                model="claude-3-5-haiku-20241022",
                priority=2,
            ),
        ],
        sync=SyncConfig(
            enabled=True,
            backend="redis",
            redis_host="localhost",
            redis_port=6379,
            redis_db=0,
        ),
        timeout=10.0,
        validate_on_init=False,  # Skip validation to allow fake keys for testing
    )

    flexiai_client = FlexiAI(config)

    print(f"✅ Worker {os.getpid()} initialized FlexiAI with Redis sync")
    print(f"   Providers: openai (priority 1), anthropic (priority 2)")
    print(f"   Redis: localhost:6379 (db 0)")
    print(f"   Sync manager: {flexiai_client._sync_manager is not None}")
    if flexiai_client._sync_manager:
        print(f"   Sync backend: {type(flexiai_client._sync_manager._backend).__name__}")
    print(f"\n{'='*80}\n")

    yield

    # Cleanup
    print(f"\n🛑 Worker {os.getpid()} shutting down...")
    if flexiai_client:
        flexiai_client.close()


# Create FastAPI app
app = FastAPI(
    title="FlexiAI Multi-Worker Circuit Breaker Test",
    description="Test circuit breaker synchronization across multiple workers",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint with instructions."""
    return {
        "message": "FlexiAI Multi-Worker Test",
        "worker_id": os.getpid(),
        "endpoints": {
            "/status": "Check worker status and circuit breaker states",
            "/chat": "Send a chat message (POST)",
            "/trigger-failure/{provider}": "Manually trigger circuit breaker failure",
            "/reset/{provider}": "Reset circuit breaker for a provider",
        },
        "test_instructions": [
            "1. Check status: GET /status",
            "2. Trigger failure: POST /trigger-failure/openai",
            "3. Check all workers: GET /status (multiple times to hit different workers)",
            "4. Observe that ALL workers show OpenAI circuit as OPEN",
        ],
    }


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current worker status and circuit breaker states."""
    global flexiai_client

    provider_status = flexiai_client.get_provider_status()

    providers_info = []
    for provider in provider_status.get("providers", []):
        cb_state = provider.get("circuit_breaker", {})
        providers_info.append(
            {
                "name": provider["name"],
                "model": provider["model"],
                "priority": provider["priority"],
                "circuit_breaker": {
                    "state": cb_state.get("state", "unknown"),
                    "failure_count": cb_state.get("failure_count", 0),
                    "last_failure": cb_state.get("last_failure_time"),
                },
            }
        )

    return StatusResponse(
        worker_id=str(os.getpid()),
        providers=providers_info,
        uptime=time.time() - start_time,
        sync_enabled=flexiai_client._sync_manager is not None,
        sync_backend=(
            type(flexiai_client._sync_manager._backend).__name__
            if flexiai_client._sync_manager
            else None
        ),
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a chat message through FlexiAI."""
    global flexiai_client

    try:
        response = flexiai_client.chat_completion(
            messages=[{"role": "user", "content": request.message}],
            max_tokens=100,
        )

        # Get circuit breaker states
        status = flexiai_client.get_provider_status()
        cb_states = {}
        for provider in status.get("providers", []):
            cb_states[provider["name"]] = {
                "state": provider["circuit_breaker"]["state"],
                "failure_count": provider["circuit_breaker"]["failure_count"],
            }

        return ChatResponse(
            response=response.content,
            provider_used=response.provider,
            worker_id=str(os.getpid()),
            circuit_breaker_state=cb_states,
        )

    except Exception as e:
        # Get circuit breaker states even on error
        status = flexiai_client.get_provider_status()
        cb_states = {}
        for provider in status.get("providers", []):
            cb_states[provider["name"]] = {
                "state": provider["circuit_breaker"]["state"],
                "failure_count": provider["circuit_breaker"]["failure_count"],
            }

        return ChatResponse(
            response=f"Error: {str(e)}",
            provider_used="none",
            worker_id=str(os.getpid()),
            circuit_breaker_state=cb_states,
        )


@app.post("/trigger-failure/{provider_name}")
async def trigger_failure(provider_name: str):
    """
    Manually trigger circuit breaker failure by directly recording failures.

    This simulates a provider going down.
    """
    global flexiai_client

    print(f"\n⚠️  Worker {os.getpid()} triggering circuit breaker for {provider_name}...")

    # Get the provider's circuit breaker directly from registry
    try:
        circuit_breaker = flexiai_client.registry.get_circuit_breaker(provider_name)
    except ValueError as e:
        return {
            "error": str(e),
            "worker_id": os.getpid(),
        }

    # Record multiple failures to trip the circuit breaker
    failure_threshold = circuit_breaker.config.failure_threshold
    failures_to_trigger = failure_threshold + 2  # Exceed threshold

    print(f"   Recording {failures_to_trigger} failures (threshold: {failure_threshold})...")
    print(
        f"   Initial state: {circuit_breaker.state.state}, failures: {circuit_breaker.state.failure_count}"
    )

    for i in range(failures_to_trigger):
        # Directly record failures through the circuit breaker's _on_failure method
        # Use APIError which is in the default expected_exception list
        class APIError(Exception):
            """Simulated API error"""

            pass

        try:
            circuit_breaker._on_failure(APIError(f"Test failure {i+1}"))
            print(
                f"   ❌ Failure {i+1} recorded - state: {circuit_breaker.state.state}, count: {circuit_breaker.state.failure_count}"
            )
        except Exception as e:
            print(f"   ⚠️  Error recording failure: {e}")

    # Check if circuit breaker opened
    cb_state = circuit_breaker.state.state
    print(f"   🔴 Circuit breaker state: {cb_state}")

    return {
        "worker_id": os.getpid(),
        "provider": provider_name,
        "failures_triggered": failures_to_trigger,
        "threshold": failure_threshold,
        "circuit_breaker_state": cb_state,
        "message": (
            f"Recorded {failures_to_trigger} failures on worker {os.getpid()}. "
            f"Circuit breaker should be {cb_state}. "
            f"Check /status on all workers to verify sync."
        ),
    }


@app.post("/reset/{provider_name}")
async def reset_circuit_breaker(provider_name: str):
    """Reset circuit breaker for a specific provider."""
    global flexiai_client

    flexiai_client.reset_circuit_breaker(provider_name)

    print(f"🔄 Worker {os.getpid()} reset circuit breaker for {provider_name}")

    return {
        "worker_id": os.getpid(),
        "provider": provider_name,
        "message": f"Circuit breaker reset for {provider_name}",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "worker_id": os.getpid(),
        "uptime": time.time() - start_time,
    }


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 80)
    print("🚀 Starting FlexiAI Multi-Worker Test Server")
    print("=" * 80)
    print("\nMake sure Redis is running:")
    print("  $ redis-server")
    print("\nStarting server with 4 workers...")
    print("=" * 80 + "\n")

    uvicorn.run(
        "test_multiworker_fastapi:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
        log_level="info",
    )
