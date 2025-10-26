# Multi-Worker Deployment Guide

This guide explains how to deploy FlexiAI with circuit breaker state synchronization across multiple workers using Redis.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment Scenarios](#deployment-scenarios)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

FlexiAI supports multi-worker deployments with synchronized circuit breaker states. When one worker opens a circuit breaker due to failures, all other workers are immediately notified and adjust their state accordingly. This prevents cascading failures and ensures consistent behavior across your application fleet.

### Key Features

- **Real-time State Synchronization**: Circuit breaker state changes are broadcast to all workers within milliseconds
- **Distributed State Storage**: Circuit breaker states persist in Redis with configurable TTL
- **Automatic Failover**: Graceful fallback to memory backend if Redis is unavailable
- **Worker Identification**: Unique worker IDs prevent state conflicts
- **Lock-free Design**: Event-driven architecture avoids distributed locking overhead

## Architecture

### Components

1. **StateSyncManager**: Coordinates state synchronization for each worker
2. **RedisSyncBackend**: Redis pub/sub for event broadcasting
3. **CircuitBreaker**: Broadcasts state changes and applies remote updates
4. **FlexiAI Client**: Initializes and manages sync lifecycle

### Data Flow

```
Worker 1                          Redis                          Worker 2
--------                          -----                          --------
Circuit Opens                      |                                |
  ↓                                |                                |
Broadcast Event → [Pub/Sub Channel] → Receive Event              |
  ↓                                |                  ↓            |
Store State  →   [State Storage]   ← Load State     Apply State  |
                                   |                  ↓            |
                                   |           Circuit Opens      |
```

### Event Types

- `OPENED`: Circuit breaker transitioned to open state
- `CLOSED`: Circuit breaker transitioned to closed state
- `HALF_OPEN`: Circuit breaker entered half-open state
- `FAILURE`: Request failure recorded
- `SUCCESS`: Request success recorded

## Prerequisites

### Required Dependencies

```bash
pip install redis>=4.5.0 hiredis>=2.0.0
```

### Redis Server

You need a Redis server accessible from all workers:

- **Production**: Redis Cluster or Redis Sentinel for high availability
- **Staging**: Single Redis instance with persistence
- **Development**: Local Redis instance or memory backend

### Install Redis

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Docker:**
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

## Configuration

### Basic Configuration

Enable sync in your FlexiAI configuration:

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, SyncConfig

config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            api_key="your-api-key",
            model="gpt-4",
            priority=1
        )
    ],
    sync=SyncConfig(
        enabled=True,
        backend="redis",
        redis_host="localhost",
        redis_port=6379,
        redis_db=0
    )
)

client = FlexiAI(config=config)
```

### Advanced Configuration

#### Redis with Authentication

```python
sync=SyncConfig(
    enabled=True,
    backend="redis",
    redis_host="redis.example.com",
    redis_port=6379,
    redis_db=0,
    redis_password="your-redis-password",
    redis_ssl=True,
    redis_socket_timeout=5.0,
    redis_socket_connect_timeout=5.0
)
```

#### Custom Worker ID

```python
sync=SyncConfig(
    enabled=True,
    backend="redis",
    redis_host="localhost",
    worker_id="web-worker-1"  # Custom identifier
)
```

#### Custom Key Prefix and Channel

```python
sync=SyncConfig(
    enabled=True,
    backend="redis",
    redis_host="localhost",
    key_prefix="myapp:flexiai",  # Default: "flexiai"
    channel="myapp:flexiai:events",  # Default: "flexiai:events"
    state_ttl=7200  # State expires after 2 hours (default: 3600)
)
```

### Environment Variables

You can also configure sync using environment variables:

```bash
export FLEXIAI_SYNC_ENABLED=true
export FLEXIAI_SYNC_BACKEND=redis
export FLEXIAI_SYNC_REDIS_HOST=redis.example.com
export FLEXIAI_SYNC_REDIS_PORT=6379
export FLEXIAI_SYNC_REDIS_PASSWORD=your-password
export FLEXIAI_SYNC_REDIS_SSL=true
```

Then load from environment:

```python
from flexiai import FlexiAI
from flexiai.config import load_config

config = load_config()  # Loads from environment
client = FlexiAI(config=config)
```

## Deployment Scenarios

### Scenario 1: Single-Server with Multiple Workers (Gunicorn/Uvicorn)

Perfect for applications running multiple worker processes on a single server.

**Gunicorn:**
```bash
gunicorn app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

**Uvicorn:**
```bash
uvicorn app:app --workers 4
```

**Configuration:**
```python
# app.py
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, SyncConfig

config = FlexiAIConfig(
    providers=[...],
    sync=SyncConfig(
        enabled=True,
        backend="redis",
        redis_host="localhost",  # Redis on same server
        redis_port=6379
    )
)

# Shared across all workers
client = FlexiAI(config=config)
```

### Scenario 2: Multi-Server Deployment (Kubernetes)

Ideal for applications running across multiple pods/nodes.

**Kubernetes Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flexiai-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: flexiai-app
  template:
    metadata:
      labels:
        app: flexiai-app
    spec:
      containers:
      - name: app
        image: your-app:latest
        env:
        - name: FLEXIAI_SYNC_ENABLED
          value: "true"
        - name: FLEXIAI_SYNC_REDIS_HOST
          value: "redis-service"
        - name: FLEXIAI_SYNC_REDIS_PORT
          value: "6379"
        - name: FLEXIAI_SYNC_REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: password
---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

### Scenario 3: Serverless Functions (AWS Lambda/Cloud Functions)

For serverless deployments with shared Redis.

**Configuration:**
```python
import os
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, SyncConfig

config = FlexiAIConfig(
    providers=[...],
    sync=SyncConfig(
        enabled=True,
        backend="redis",
        redis_host=os.getenv("REDIS_HOST"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_password=os.getenv("REDIS_PASSWORD"),
        redis_ssl=True,
        state_ttl=300  # Shorter TTL for serverless
    )
)

# Initialize once (outside handler for warm starts)
client = FlexiAI(config=config)

def handler(event, context):
    response = client.generate(
        prompt="Translate to French: Hello world",
        temperature=0.7
    )
    return response
```

### Scenario 4: Development Without Redis

For local development without Redis infrastructure.

**Configuration:**
```python
config = FlexiAIConfig(
    providers=[...],
    sync=SyncConfig(
        enabled=False  # Disable sync for development
    )
)

# OR: Enabled but with memory backend (single process only)
config = FlexiAIConfig(
    providers=[...],
    sync=SyncConfig(
        enabled=True,
        backend="memory"  # In-memory, no Redis required
    )
)
```

## Lifecycle Management

### Graceful Shutdown

Always call `close()` to cleanup sync resources:

```python
# Context manager (recommended)
with FlexiAI(config=config) as client:
    response = client.generate(prompt="Hello")
# Automatically calls close()

# Manual cleanup
client = FlexiAI(config=config)
try:
    response = client.generate(prompt="Hello")
finally:
    client.close()  # Stops sync manager, closes Redis connection
```

### Health Checks

Check sync manager health:

```python
if client._sync_manager and client._sync_manager.backend.health_check():
    print("Sync backend healthy")
else:
    print("Sync backend unavailable")
```

## Monitoring

### Redis Monitoring

Monitor sync activity in Redis:

```bash
# Monitor pub/sub activity
redis-cli
> PUBSUB CHANNELS flexiai:*
> PUBSUB NUMSUB flexiai:events

# View stored states
> KEYS flexiai:state:*
> GET flexiai:state:openai
> TTL flexiai:state:openai
```

### Application Metrics

Track sync events in your application:

```python
import logging

# FlexiAI logs sync events
logging.basicConfig(level=logging.INFO)

# Example log output:
# INFO:flexiai.client:Sync manager initialized (backend: redis)
# INFO:flexiai.sync.manager:Worker worker-1 started
# INFO:flexiai.circuit_breaker:Circuit opened for provider openai
# INFO:flexiai.sync.manager:Broadcasting state change: openai OPENED
```

### Performance Metrics

Key metrics to monitor:

- **Sync Latency**: Time between state change and remote application
- **Event Frequency**: Number of circuit breaker events per minute
- **Redis Connection Pool**: Active connections per worker
- **State Synchronization Success Rate**: % of successful broadcasts

## Troubleshooting

### Issue: Sync not working between workers

**Symptoms:**
- Circuit breaker opens on one worker but not others
- No error messages in logs

**Diagnosis:**
```python
# Check if sync is enabled
print(client._sync_manager)  # Should not be None

# Check backend health
print(client._sync_manager.backend.health_check())  # Should be True

# Check worker ID
print(client._sync_manager.worker_id)  # Each worker should have unique ID
```

**Solution:**
1. Verify Redis is accessible from all workers
2. Check firewall rules allow Redis port (6379)
3. Ensure all workers use same `channel` and `key_prefix`
4. Verify Redis password (if using authentication)

### Issue: High Redis memory usage

**Symptoms:**
- Redis memory growing over time
- OOM errors from Redis

**Diagnosis:**
```bash
redis-cli
> INFO memory
> KEYS flexiai:state:*
```

**Solution:**
1. Reduce `state_ttl` in SyncConfig (default: 3600s)
2. Set Redis `maxmemory` policy:
   ```
   maxmemory 256mb
   maxmemory-policy allkeys-lru
   ```
3. Monitor and clean up stale keys

### Issue: Circuit breaker state desynchronization

**Symptoms:**
- Workers have different circuit breaker states
- Inconsistent behavior across workers

**Diagnosis:**
```bash
# Check state in Redis for each provider
redis-cli
> GET flexiai:state:openai
> GET flexiai:state:anthropic
```

**Solution:**
1. Restart all workers to force state sync from Redis
2. Check for network partitions between workers and Redis
3. Verify `state_ttL` isn't too short (minimum: 60s)
4. Ensure workers have synchronized clocks (use NTP)

### Issue: Fallback to memory backend

**Symptoms:**
- Log message: "Failed to initialize Redis backend, falling back to memory"
- Sync not working between workers

**Diagnosis:**
Check Redis connectivity:
```bash
redis-cli -h <redis_host> -p <redis_port> ping
```

**Solution:**
1. Verify Redis server is running
2. Check `redis_host` and `redis_port` configuration
3. Test Redis credentials if using authentication
4. Check network connectivity to Redis

### Issue: Slow circuit breaker state updates

**Symptoms:**
- Delay between circuit breaker open on one worker and update on others
- Sync latency > 1 second

**Diagnosis:**
- Monitor Redis pub/sub latency
- Check network latency between workers and Redis

**Solution:**
1. Use Redis Cluster or Sentinel for better performance
2. Place Redis close to workers (same datacenter/region)
3. Increase `redis_socket_timeout` if network is unstable
4. Consider using dedicated Redis instance for FlexiAI

## Best Practices

1. **Use Redis Sentinel or Cluster in Production**
   - Ensures high availability
   - Automatic failover on Redis failure

2. **Set Appropriate State TTL**
   - Default 3600s (1 hour) is good for most cases
   - Shorter for serverless (300s)
   - Longer for stable deployments (7200s)

3. **Monitor Circuit Breaker Events**
   - Track frequency of opens/closes
   - Alert on abnormal patterns

4. **Use Context Managers**
   - Always use `with FlexiAI(...) as client:`
   - Ensures proper cleanup on shutdown

5. **Test Failover Scenarios**
   - Simulate Redis outage
   - Verify graceful fallback to memory backend

6. **Unique Worker IDs for Debugging**
   - Auto-generated IDs include hostname, PID, timestamp
   - Custom IDs helpful for tracing specific workers

7. **Secure Redis Connections**
   - Use authentication (redis_password)
   - Enable SSL (redis_ssl=True)
   - Restrict network access to Redis

## Examples

### Example 1: FastAPI with Multiple Workers

```python
# app.py
from fastapi import FastAPI
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, SyncConfig

app = FastAPI()

# Initialize once at module level (shared across requests)
config = FlexiAIConfig(
    providers=[
        ProviderConfig(name="openai", api_key="sk-...", model="gpt-4", priority=1),
        ProviderConfig(name="anthropic", api_key="sk-ant-...", model="claude-3-sonnet-20240229", priority=2)
    ],
    sync=SyncConfig(
        enabled=True,
        backend="redis",
        redis_host="localhost"
    )
)

client = FlexiAI(config=config)

@app.post("/generate")
async def generate(prompt: str):
    response = client.generate(prompt=prompt, temperature=0.7)
    return {"response": response.content}

@app.get("/health")
async def health():
    sync_healthy = client._sync_manager.backend.health_check() if client._sync_manager else False
    return {
        "status": "healthy",
        "sync_enabled": client._sync_manager is not None,
        "sync_healthy": sync_healthy
    }

@app.on_event("shutdown")
async def shutdown():
    client.close()
```

Run with:
```bash
uvicorn app:app --workers 4 --host 0.0.0.0 --port 8000
```

### Example 2: AWS Lambda with ElastiCache Redis

```python
import os
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, SyncConfig

# Initialize outside handler (reused across invocations)
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4-turbo-preview",
            priority=1
        )
    ],
    sync=SyncConfig(
        enabled=True,
        backend="redis",
        redis_host=os.getenv("ELASTICACHE_ENDPOINT"),
        redis_port=6379,
        redis_ssl=True,
        state_ttl=300  # 5 minutes for serverless
    )
)

client = FlexiAI(config=config)

def lambda_handler(event, context):
    prompt = event.get("prompt", "Hello, world!")

    response = client.generate(
        prompt=prompt,
        temperature=0.7,
        max_tokens=100
    )

    return {
        "statusCode": 200,
        "body": {
            "response": response.content,
            "provider": response.metadata.get("provider"),
            "worker_id": client._sync_manager.worker_id if client._sync_manager else None
        }
    }
```

## Additional Resources

- [FlexiAI Documentation](../README.md)
- [Configuration Guide](configuration.md)
- [Circuit Breaker Documentation](circuit-breaker.md)
- [Redis Best Practices](https://redis.io/docs/management/optimization/)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

## Support

For issues or questions:
- GitHub Issues: https://github.com/Touchkin/FlexiAI/issues
- Documentation: https://github.com/Touchkin/FlexiAI/docs
