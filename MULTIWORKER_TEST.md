# Multi-Worker Circuit Breaker Synchronization Test

This test demonstrates that circuit breaker state is synchronized across multiple FastAPI workers using Redis pub/sub.

## Test Scenario

1. **FastAPI app runs with 4 workers** (Worker A, B, C, D)
2. **Worker A experiences OpenAI failures** (e.g., invalid API key)
3. **Worker A trips circuit breaker** (state changes to OPEN)
4. **Worker A publishes event to Redis** pub/sub channel
5. **All workers (B, C, D) receive the event** via Redis subscription
6. **All workers trip their circuit breakers** for OpenAI

## Prerequisites

1. **Redis server running**:
   ```bash
   redis-server
   ```

2. **Python environment activated**:
   ```bash
   source venv/bin/activate
   ```

3. **FastAPI and uvicorn installed** (already in requirements):
   ```bash
   pip install fastapi uvicorn requests
   ```

## Running the Test

### Option 1: Automated Test (Recommended)

#### Terminal 1 - Start the FastAPI server:
```bash
uvicorn test_multiworker_fastapi:app --workers 4 --host 0.0.0.0 --port 8000
```

You should see 4 workers starting up:
```
🚀 Worker 12345 starting up...
✅ Worker 12345 initialized FlexiAI with Redis sync

🚀 Worker 12346 starting up...
✅ Worker 12346 initialized FlexiAI with Redis sync

🚀 Worker 12347 starting up...
✅ Worker 12347 initialized FlexiAI with Redis sync

🚀 Worker 12348 starting up...
✅ Worker 12348 initialized FlexiAI with Redis sync
```

#### Terminal 2 - Run the automated test:
```bash
python test_circuit_breaker_sync.py
```

The test will:
1. Collect status from all 4 workers
2. Trigger failures on one worker
3. Wait for Redis pub/sub propagation (2 seconds)
4. Verify all workers show circuit breaker as OPEN
5. Display results

### Option 2: Manual Testing

#### Step 1: Check initial status
```bash
# Make multiple requests to see different workers
curl http://localhost:8000/status
curl http://localhost:8000/status
curl http://localhost:8000/status
curl http://localhost:8000/status
```

You should see different worker IDs responding, all showing circuit breakers as CLOSED.

#### Step 2: Trigger failure on one worker
```bash
curl -X POST http://localhost:8000/trigger-failure/openai
```

This will:
- Trigger 5 failures on whichever worker handles this request
- Trip the circuit breaker to OPEN
- Publish event to Redis

#### Step 3: Verify all workers are synchronized
```bash
# Check status on all workers (make multiple requests)
for i in {1..10}; do
  curl -s http://localhost:8000/status | jq '.worker_id, .providers[0].circuit_breaker.state'
  sleep 0.5
done
```

Expected output: **All workers should show "open" for OpenAI circuit breaker**

#### Step 4: Reset (optional)
```bash
curl -X POST http://localhost:8000/reset/openai
```

## Expected Results

### ✅ PASSING Test

All workers show OpenAI circuit breaker as OPEN:

```
Worker 12345:
  🔴 openai     - State: open       Failures: 5

Worker 12346:
  🔴 openai     - State: open       Failures: 0

Worker 12347:
  🔴 openai     - State: open       Failures: 0

Worker 12348:
  🔴 openai     - State: open       Failures: 0
```

**Key observations:**
- Only Worker 12345 (or whichever worker handled the request) shows actual failures
- **ALL workers show circuit breaker as OPEN**
- Workers 12346, 12347, 12348 received the state via Redis pub/sub

### ❌ FAILING Test

Workers have different states:

```
Worker 12345:
  🔴 openai     - State: open       Failures: 5

Worker 12346:
  🟢 openai     - State: closed     Failures: 0

Worker 12347:
  🟢 openai     - State: closed     Failures: 0
```

This would indicate Redis pub/sub is not working.

## How It Works

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Worker A   │     │  Worker B   │     │  Worker C   │     │  Worker D   │
│  PID: 1001  │     │  PID: 1002  │     │  PID: 1003  │     │  PID: 1004  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │ 1. Failure        │                   │                   │
       │ detected          │                   │                   │
       │                   │                   │                   │
       │ 2. Circuit        │                   │                   │
       │ breaker           │                   │                   │
       │ trips to          │                   │                   │
       │ OPEN              │                   │                   │
       │                   │                   │                   │
       │ 3. Publish        │                   │                   │
       │ event to          │                   │                   │
       │ Redis ────────────┼───────────────────┼───────────────────┤
       │                   │                   │                   │
       │                   │ 4. Receive event  │                   │
       │                   │ from Redis        │                   │
       │                   │                   │                   │
       │                   │ 5. Trip CB        │                   │
       │                   │ to OPEN           │                   │
       │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┘
                                     │
                              ┌──────▼──────┐
                              │    Redis    │
                              │   Pub/Sub   │
                              │ Channel:    │
                              │ flexiai:    │
                              │  events     │
                              └─────────────┘
```

### Code Flow

1. **Worker A** experiences failures:
   ```python
   # In test_multiworker_fastapi.py
   flexiai_client.chat_completion(...)  # Fails
   # Circuit breaker trips after 3 failures (threshold)
   ```

2. **Worker A** publishes to Redis:
   ```python
   # In FlexiAI internals
   sync_manager.on_local_state_change(
       provider_name="openai",
       event_type="opened",
       metadata={"failure_count": 5}
   )
   # This calls redis_backend.publish_event()
   ```

3. **All workers** receive via subscription:
   ```python
   # In FlexiAI internals (automatic)
   # Each worker subscribed on startup:
   redis_backend.subscribe_to_events(callback)
   # When event arrives, callback updates circuit breaker
   ```

4. **Workers B, C, D** update their circuit breakers:
   ```python
   # Callback in circuit breaker
   def handle_remote_event(event):
       if event.state == "open":
           self.circuit_breaker._state = "open"
   ```

## Troubleshooting

### Workers not starting
- Check Redis is running: `redis-cli ping`
- Check port 8000 is free: `lsof -i :8000`

### Circuit breakers not synchronizing
- Check Redis connection: `redis-cli MONITOR` (watch for pub/sub messages)
- Check worker logs for subscription messages
- Increase wait time in test (2 seconds → 5 seconds)

### Only seeing 1-2 workers
- Uvicorn may be reusing workers
- Try making more requests (10-15)
- Check process list: `ps aux | grep uvicorn`

## What This Proves

✅ **Redis pub/sub is working** - Events published by one worker reach all workers

✅ **Circuit breaker synchronization is working** - State changes propagate across processes

✅ **Multi-worker safety** - All workers know about provider failures immediately

✅ **Production-ready** - The system works in a real multi-process environment

## Cleanup

Stop the FastAPI server:
```bash
# In the server terminal, press Ctrl+C
```

Stop Redis (if you want):
```bash
redis-cli shutdown
```

## Next Steps

After verifying the test passes:
1. ✅ Confirm Phase 7.2 is fully validated
2. ✅ Ready for production deployment
3. ✅ Can proceed with v0.5.0 release
