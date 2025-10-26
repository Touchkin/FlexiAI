# FlexiAI Multi-Worker FastAPI Example

This example demonstrates how to deploy FlexiAI in a production environment with multiple uvicorn workers and Redis-based state synchronization.

## Features

- ✅ Multiple LLM providers (OpenAI, Anthropic) with automatic failover
- ✅ Redis-based circuit breaker state synchronization across workers
- ✅ Comprehensive health check endpoints for monitoring
- ✅ Graceful shutdown handling
- ✅ Both decorator and direct client usage examples
- ✅ Structured logging with worker identification
- ✅ Production-ready error handling
- ✅ Kubernetes-ready readiness/liveness probes

## Quick Start

### Prerequisites

- Python 3.8+
- Redis server running
- OpenAI and/or Anthropic API keys

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Redis

```bash
# Using Docker (recommended)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or install and start Redis locally
# Ubuntu/Debian:
sudo apt-get install redis-server
sudo systemctl start redis

# macOS (with Homebrew):
brew install redis
brew services start redis
```

### 3. Set Environment Variables

```bash
# Required: At least one LLM provider
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"

# Optional: Redis configuration (defaults shown)
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_DB="0"
# export REDIS_PASSWORD="your-redis-password"  # If Redis auth is enabled
```

### 4. Run the Application

**Development (single worker with auto-reload):**
```bash
python app.py
# or
uvicorn app:app --reload
```

**Production (multiple workers):**
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

**Production (with detailed logging):**
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info
```

## API Endpoints

### Chat Completion Endpoints

#### 1. Direct Client Usage
```bash
curl -X POST http://localhost:8000/chat/direct \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is Python?",
    "system_message": "You are a helpful programming assistant.",
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

Response:
```json
{
  "content": "Python is a high-level, interpreted programming language...",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "worker_id": 12345,
  "timestamp": "2024-01-15T10:30:00.123456"
}
```

#### 2. Decorator Usage
```bash
curl -X POST http://localhost:8000/chat/decorator \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain async/await in Python",
    "temperature": 0.8
  }'
```

### Health Check Endpoints

#### Comprehensive Health Check
```bash
curl http://localhost:8000/health
```

Response (healthy):
```json
{
  "status": "healthy",
  "worker_id": 12345,
  "timestamp": "2024-01-15T10:30:00.123456",
  "redis_connected": true,
  "sync_enabled": true,
  "providers": [
    {
      "name": "openai",
      "model": "gpt-4o-mini",
      "available": true,
      "circuit_state": "CLOSED",
      "failure_count": 0,
      "last_failure_time": null,
      "priority": 1
    },
    {
      "name": "anthropic",
      "model": "claude-3-5-haiku-20241022",
      "available": true,
      "circuit_state": "CLOSED",
      "failure_count": 0,
      "last_failure_time": null,
      "priority": 2
    }
  ]
}
```

#### Kubernetes Readiness Probe
```bash
curl http://localhost:8000/health/ready
```

#### Kubernetes Liveness Probe
```bash
curl http://localhost:8000/health/live
```

### Provider Management

#### Get Provider Status
```bash
curl http://localhost:8000/providers
```

#### Reset Circuit Breaker
```bash
curl -X POST http://localhost:8000/providers/openai/reset
```

### Metrics

```bash
curl http://localhost:8000/metrics
```

## Multi-Worker Architecture

### How It Works

When running with multiple workers (`--workers 4`), each uvicorn worker is a separate Python process:

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    │   (uvicorn)     │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  Worker 1    │ │  Worker 2   │ │  Worker 3   │
    │ PID: 12345   │ │ PID: 12346  │ │ PID: 12347  │
    │              │ │             │ │             │
    │ FlexiAI      │ │ FlexiAI     │ │ FlexiAI     │
    │ + Circuit    │ │ + Circuit   │ │ + Circuit   │
    │   Breakers   │ │   Breakers  │ │   Breakers  │
    └───────┬──────┘ └──────┬──────┘ └──────┬──────┘
            │                │                │
            └────────────────┼────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Redis Server   │
                    │  (State Sync)   │
                    └─────────────────┘
```

### State Synchronization

FlexiAI uses Redis pub/sub to synchronize circuit breaker states across all workers:

1. **Worker 1** experiences failures with OpenAI provider
2. Circuit breaker opens after threshold (e.g., 5 failures)
3. **Worker 1** publishes state change to Redis
4. **Workers 2, 3, 4** receive the update via Redis pub/sub
5. All workers now know OpenAI is unavailable and will use Anthropic

This ensures:
- ✅ Consistent failover across all workers
- ✅ No duplicate failure attempts
- ✅ Fast recovery when provider becomes available
- ✅ Efficient resource usage

### Benefits of Multi-Worker Deployment

1. **Performance**: Handle multiple concurrent requests in parallel
2. **Reliability**: If one worker crashes, others continue serving
3. **Zero-downtime deploys**: Rolling restarts possible
4. **Resource utilization**: Use multiple CPU cores effectively
5. **State consistency**: Redis sync keeps all workers coordinated

## Testing Multi-Worker Setup

### 1. Start the Application with 4 Workers

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### 2. Verify All Workers Are Running

```bash
# Check health from different workers
for i in {1..10}; do
  curl -s http://localhost:8000/health | jq '.worker_id'
done
```

You should see different worker IDs (process IDs) in the responses.

### 3. Test State Synchronization

```bash
# Make a request that will be handled by a random worker
curl -X POST http://localhost:8000/chat/direct \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# Check provider status from different workers
curl http://localhost:8000/providers | jq '.worker_id'
```

### 4. Monitor Logs

Watch the logs to see which worker handles each request:

```bash
# Look for lines like:
# 2024-01-15 10:30:00 - INFO - [Worker:12345] - Worker 12345 processed request with provider: openai
# 2024-01-15 10:30:01 - INFO - [Worker:12346] - Worker 12346 processed request with provider: openai
```

### 5. Load Testing

Use tools like `ab` (Apache Bench) or `wrk` to test concurrent load:

```bash
# Install Apache Bench
sudo apt-get install apache2-utils  # Ubuntu/Debian
brew install httpd  # macOS

# Run load test (100 requests, 10 concurrent)
ab -n 100 -c 10 -p request.json -T application/json http://localhost:8000/chat/direct
```

Create `request.json`:
```json
{"message": "What is Python?", "temperature": 0.7}
```

## Production Deployment

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  flexiai-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - redis
    command: uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4

volumes:
  redis_data:
```

Run with:
```bash
docker-compose up -d
```

### Using Kubernetes

Create `deployment.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: flexiai-api
spec:
  selector:
    app: flexiai-api
  ports:
    - port: 80
      targetPort: 8000
  type: LoadBalancer

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flexiai-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: flexiai-api
  template:
    metadata:
      labels:
        app: flexiai-api
    spec:
      containers:
      - name: flexiai-api
        image: your-registry/flexiai-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: "redis-service"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: anthropic
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 20
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | Yes* | - | Anthropic API key |
| `REDIS_HOST` | No | `localhost` | Redis server hostname |
| `REDIS_PORT` | No | `6379` | Redis server port |
| `REDIS_DB` | No | `0` | Redis database number |
| `REDIS_PASSWORD` | No | - | Redis authentication password |

*At least one LLM provider is required

## Monitoring and Observability

### Health Checks

The application provides three health check endpoints:

1. **`/health`**: Comprehensive health check with provider status
2. **`/health/ready`**: Readiness check for load balancers
3. **`/health/live`**: Liveness check for container orchestration

### Metrics

The `/metrics` endpoint provides:
- Circuit breaker states and counts
- Redis connection status
- Provider availability
- Worker identification

### Logging

All logs include:
- Timestamp
- Log level
- Worker process ID
- Contextual information

Example log output:
```
2024-01-15 10:30:00 - flexiai - INFO - [Worker:12345] - Worker 12345 processed request with provider: openai
2024-01-15 10:30:01 - flexiai - WARNING - [Worker:12346] - Redis health check failed: Connection refused
2024-01-15 10:30:02 - flexiai - INFO - [Worker:12347] - Circuit breaker reset for provider 'openai' by worker 12347
```

### Redis Monitoring

Monitor Redis pub/sub activity:

```bash
# Connect to Redis CLI
redis-cli

# Monitor all commands
MONITOR

# Subscribe to FlexiAI state changes
SUBSCRIBE circuit_breaker:state:*

# Check active subscriptions
PUBSUB CHANNELS circuit_breaker:*
```

## Troubleshooting

### Workers Not Synchronizing

**Problem**: Circuit breaker states differ between workers

**Solutions**:
1. Verify Redis is running: `redis-cli ping`
2. Check Redis connection in logs
3. Verify environment variables are set correctly
4. Check firewall rules if Redis is on a different host

### Redis Connection Errors

**Problem**: `Failed to connect to Redis`

**Solutions**:
1. Ensure Redis is running: `systemctl status redis` or `docker ps | grep redis`
2. Check Redis host/port configuration
3. Verify network connectivity: `telnet localhost 6379`
4. Check Redis authentication if password is set

### No Provider Available

**Problem**: `No providers available` error

**Solutions**:
1. Check API keys are set correctly
2. Verify provider API is accessible
3. Check circuit breaker states: `curl http://localhost:8000/providers`
4. Reset circuit breakers if needed: `curl -X POST http://localhost:8000/providers/openai/reset`

### High Latency

**Problem**: Slow response times

**Solutions**:
1. Increase number of workers: `--workers 8`
2. Check Redis latency: `redis-cli --latency`
3. Monitor provider API response times
4. Consider using Redis Cluster for high traffic
5. Use connection pooling for Redis

## Best Practices

### 1. Worker Count

- **CPU-bound**: `workers = (2 * num_cores) + 1`
- **I/O-bound** (typical for LLM APIs): `workers = num_cores * 4`
- **Start conservative**: Begin with 4 workers and scale up based on monitoring

### 2. Redis Configuration

- **Enable persistence**: Use AOF (Append-Only File) for durability
- **Set maxmemory policy**: `maxmemory-policy allkeys-lru`
- **Use Redis Cluster**: For high availability in production
- **Enable authentication**: Set `requirepass` in redis.conf
- **Use SSL/TLS**: For Redis connections over the network

### 3. Monitoring

- Monitor health endpoints with uptime monitoring (e.g., Datadog, Prometheus)
- Set up alerts for circuit breaker state changes
- Track response times and error rates
- Monitor Redis connection status

### 4. Security

- Never commit API keys to version control
- Use environment variables or secret management (e.g., AWS Secrets Manager)
- Enable Redis authentication in production
- Use TLS for Redis connections over the internet
- Implement rate limiting to prevent abuse

### 5. Scaling

- Start with vertical scaling (more workers per instance)
- Move to horizontal scaling (more instances) as needed
- Use load balancers (Nginx, HAProxy) for multiple instances
- Consider regional deployments for global users

## Next Steps

- Explore the [FlexiAI documentation](../../README.md)
- Check out other examples in the `examples/` directory
- Learn about [Decorator API](../../README.md#using-decorators)
- Set up monitoring and alerting
- Implement custom circuit breaker strategies

## Support

For issues or questions:
- GitHub Issues: [FlexiAI Issues](https://github.com/yourusername/flexiai/issues)
- Documentation: [README.md](../../README.md)
