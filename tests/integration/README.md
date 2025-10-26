# Redis Multi-Worker Integration Tests

This directory contains integration tests for Redis-based multi-worker synchronization.

## Prerequisites

1. **Redis Server**: You need a Redis server running locally
   ```bash
   # Install Redis (Ubuntu/Debian)
   sudo apt-get install redis-server

   # Or using Docker
   docker run -d -p 6379:6379 redis:latest

   # Or on macOS
   brew install redis
   brew services start redis
   ```

2. **Python Dependencies**:
   ```bash
   pip install redis hiredis pytest
   ```

## Running the Tests

### Run all integration tests:
```bash
pytest tests/integration/test_redis_multiworker.py -v
```

### Run with detailed output:
```bash
pytest tests/integration/test_redis_multiworker.py -v -s
```

### Run specific test class:
```bash
pytest tests/integration/test_redis_multiworker.py::TestRedisPubSub -v
pytest tests/integration/test_redis_multiworker.py::TestMultiWorkerSync -v
pytest tests/integration/test_redis_multiworker.py::TestCircuitBreakerIntegration -v
```

### Run specific test:
```bash
pytest tests/integration/test_redis_multiworker.py::TestRedisPubSub::test_subscribe_to_events -v
```

## Test Coverage

The integration tests cover:

### 1. Redis Pub/Sub (`TestRedisPubSub`)
- ✅ Basic Redis connection and health check
- ✅ Publishing events to Redis channel
- ✅ Subscribing to events with callback
- ✅ Multiple subscribers receiving same event

### 2. State Persistence (`TestRedisStatePersistence`)
- ✅ Setting and getting provider state
- ✅ State TTL (Time To Live) expiration
- ✅ State persistence across backend instances

### 3. Distributed Locking (`TestDistributedLocking`)
- ✅ Lock acquisition and release
- ✅ Lock blocking concurrent access
- ✅ Lock auto-expiry after timeout

### 4. Multi-Worker Synchronization (`TestMultiWorkerSync`)
- ✅ Pub/sub across multiple processes
- ✅ State sync across processes
- ✅ Concurrent state updates with locking
- ✅ Race condition prevention

### 5. Circuit Breaker Integration (`TestCircuitBreakerIntegration`)
- ✅ Circuit breaker state sync across instances
- ✅ Multi-process circuit breaker synchronization
- ✅ Event propagation to all workers

## What These Tests Verify

### Real Multi-Process Testing
Unlike unit tests that may use mocks or threads, these tests use actual `multiprocessing.Process` to simulate real worker processes.

### Redis Pub/Sub Functionality
- Events published by one worker are received by all other workers
- Pub/sub latency is acceptable (< 500ms)
- No message loss under normal conditions

### State Synchronization
- State updates in one worker are visible to others
- Distributed locking prevents race conditions
- State persists and can be recovered

### Production Scenarios
- Worker startup/shutdown
- Concurrent state modifications
- Circuit breaker state sharing
- Lock contention handling

## Troubleshooting

### Tests are skipped
**Problem**: All tests show "SKIPPED - Redis server not available"

**Solution**:
1. Start Redis server: `redis-server`
2. Verify Redis is running: `redis-cli ping` (should return "PONG")
3. Check Redis is on default port 6379

### Connection refused errors
**Problem**: `redis.exceptions.ConnectionError: Error connecting to localhost:6379`

**Solution**:
1. Check Redis is running: `systemctl status redis` or `brew services list`
2. Check Redis port: `netstat -an | grep 6379`
3. Try connecting manually: `redis-cli ping`

### Tests timeout
**Problem**: Tests hang or timeout waiting for events

**Solution**:
1. Check Redis pub/sub is working: `redis-cli SUBSCRIBE test`
2. Verify no firewall blocking localhost
3. Increase test timeouts if running on slow system

### Database not empty errors
**Problem**: Tests fail because Redis DB already has data

**Solution**:
The tests use Redis DB 15 (separate from default DB 0) and include cleanup fixtures. If issues persist:
```bash
redis-cli -n 15 FLUSHDB
```

## Performance Expectations

- **Pub/Sub Latency**: < 100ms for event propagation
- **Lock Acquisition**: < 50ms under normal load
- **State Persistence**: < 10ms for set/get operations
- **Multi-Worker Sync**: Events should reach all workers within 300ms

## CI/CD Integration

To run these tests in CI/CD:

```yaml
# .github/workflows/test.yml
services:
  redis:
    image: redis:latest
    ports:
      - 6379:6379
    options: >-
      --health-cmd "redis-cli ping"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5

steps:
  - name: Run integration tests
    run: pytest tests/integration/test_redis_multiworker.py -v
```

## Development Tips

### Watch Redis Activity
Monitor Redis commands in real-time:
```bash
redis-cli MONITOR
```

### Check Pub/Sub Channels
See active channels:
```bash
redis-cli PUBSUB CHANNELS
```

### View Test Database
Connect to test database:
```bash
redis-cli -n 15
KEYS *
GET test_flexiai:state:test_provider
```

### Debug Event Flow
Add logging to see event flow:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Additional Notes

- Tests use Redis DB 15 to avoid conflicts with development/production
- Each test includes cleanup to ensure test isolation
- Tests are safe to run multiple times
- No data from tests will affect your application's Redis data
