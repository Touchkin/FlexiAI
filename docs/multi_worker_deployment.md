# Multi-Worker Deployment Guide

Complete guide for deploying FlexiAI in production with multiple workers and Redis-based state synchronization.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Deployment Options](#deployment-options)
- [Load Balancing](#load-balancing)
- [Monitoring and Observability](#monitoring-and-observability)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Performance Tuning](#performance-tuning)
- [Security](#security)

## Architecture Overview

### Multi-Worker Architecture

FlexiAI supports multi-worker deployments where multiple processes handle requests concurrently while maintaining consistent state across all workers through Redis pub/sub.

```
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer                          │
│                  (Nginx, HAProxy, etc.)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
    ┌───────▼──────┐ ┌──▼──────┐ ┌──▼──────┐
    │  Instance 1  │ │Instance2│ │Instance3│
    │              │ │         │ │         │
    │ ┌──────────┐ │ │┌───────┐│ │┌───────┐│
    │ │Worker 1  │ │ ││Worker1││ ││Worker1││
    │ │Worker 2  │ │ ││Worker2││ ││Worker2││
    │ │Worker 3  │ │ ││Worker3││ ││Worker3││
    │ │Worker 4  │ │ ││Worker4││ ││Worker4││
    │ └────┬─────┘ │ │└───┬───┘│ │└───┬───┘│
    └──────┼───────┘ └────┼────┘ └────┼────┘
           │              │           │
           └──────────────┼───────────┘
                          │
                ┌─────────▼────────┐
                │  Redis Cluster   │
                │  (State Sync)    │
                └──────────────────┘
```

### How State Synchronization Works

1. **Circuit Breaker Event**: Worker 1 detects OpenAI failures
2. **State Change**: Circuit breaker opens after threshold (e.g., 5 failures)
3. **Publish to Redis**: Worker 1 publishes state change to Redis
4. **Redis Pub/Sub**: Redis broadcasts to all subscribed workers
5. **State Update**: All workers update their circuit breaker state
6. **Consistent Behavior**: All workers now use Anthropic as primary

**Time to Sync**: Typically 10-50ms across all workers

### Benefits

| Benefit | Description |
|---------|-------------|
| **Performance** | Handle thousands of concurrent requests |
| **Reliability** | If one worker crashes, others continue serving |
| **Consistency** | All workers have the same view of provider health |
| **Efficiency** | No duplicate failure attempts across workers |
| **Scalability** | Easily scale horizontally by adding more workers/instances |
| **Zero-downtime** | Rolling deployments without service interruption |

## Prerequisites

### System Requirements

- **Python**: 3.8 or higher
- **Redis**: 6.0 or higher (7.0+ recommended)
- **Memory**: Minimum 512MB per worker (1GB+ recommended)
- **CPU**: 1+ cores (multi-core recommended for multiple workers)
- **Network**: Low-latency connection between workers and Redis

### Software Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip redis-server

# CentOS/RHEL
sudo yum install -y python3 python3-pip redis

# macOS (with Homebrew)
brew install python redis
```

### Python Packages

```bash
pip install flexiai fastapi uvicorn redis
```

## Quick Start

### 1. Install Redis

**Using Docker (Recommended for Development)**:
```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

**Using System Package Manager**:
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# macOS
brew install redis
brew services start redis
```

**Verify Redis is Running**:
```bash
redis-cli ping
# Expected output: PONG
```

### 2. Configure Environment

Create `.env` file:
```bash
# LLM Provider API Keys (at least one required)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 3. Run Multi-Worker Application

```bash
# Navigate to example directory
cd examples/fastapi_multiworker

# Start with 4 workers
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Verify Multi-Worker Setup

**Check Different Workers Respond**:
```bash
# Make multiple requests and observe different worker IDs
for i in {1..5}; do
  curl -s http://localhost:8000/health | jq '.worker_id'
done
```

**Expected Output**:
```
12345
12346
12347
12348
12345  # Round-robin back to first worker
```

## Configuration

### FlexiAI Configuration

```python
from flexiai import FlexiAI
from flexiai.types import ProviderConfig, SyncConfig

# Provider configuration
providers = [
    ProviderConfig(
        name="openai",
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini",
        priority=1
    ),
    ProviderConfig(
        name="anthropic",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-5-haiku-20241022",
        priority=2
    )
]

# Redis sync configuration
sync_config = SyncConfig(
    enabled=True,
    backend="redis",
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    redis_password=None  # Set if Redis requires auth
)

# Initialize client
client = FlexiAI(
    providers=providers,
    sync=sync_config
)
```

### Redis Configuration

**Basic Configuration** (`redis.conf`):
```conf
# Network
bind 0.0.0.0
port 6379
protected-mode yes

# Persistence (for durability)
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec

# Memory
maxmemory 256mb
maxmemory-policy allkeys-lru

# Security (production)
requirepass your-strong-password
```

**Apply Configuration**:
```bash
sudo systemctl restart redis
# or
docker run -d -p 6379:6379 -v /path/to/redis.conf:/etc/redis/redis.conf redis:7-alpine redis-server /etc/redis/redis.conf
```

### Uvicorn Configuration

**Worker Count Guidelines**:
```bash
# CPU-bound workloads
workers = (2 * num_cores) + 1

# I/O-bound workloads (LLM API calls)
workers = num_cores * 4

# Example for 4-core machine
uvicorn app:app --workers 16  # I/O-bound
uvicorn app:app --workers 9   # CPU-bound
```

**Full Configuration**:
```bash
uvicorn app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout-keep-alive 65 \
  --limit-concurrency 1000 \
  --limit-max-requests 10000 \
  --log-level info
```

## Deployment Options

### Option 1: Single Instance with Multiple Workers

**Best for**: Small to medium applications (up to 10k requests/min)

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

**Pros**:
- Simple setup
- Low latency (local Redis)
- Easy monitoring

**Cons**:
- Single point of failure
- Limited by single machine resources

### Option 2: Multiple Instances with Load Balancer

**Best for**: High-traffic applications (10k+ requests/min)

```
┌─────────────────┐
│ Load Balancer   │
│   (Nginx)       │
└────────┬────────┘
         │
    ┌────┼────┐
    │    │    │
┌───▼┐ ┌─▼─┐ ┌▼──┐
│Inst│ │Ins│ │Ins│
│ 1  │ │ 2 │ │ 3 │
└────┘ └───┘ └───┘
```

**Nginx Configuration**:
```nginx
upstream flexiai_backend {
    least_conn;  # Connection-based load balancing
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://flexiai_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long LLM responses
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://flexiai_backend/health;
        access_log off;
    }
}
```

**Start Multiple Instances**:
```bash
# Instance 1
uvicorn app:app --host 127.0.0.1 --port 8001 --workers 4 &

# Instance 2
uvicorn app:app --host 127.0.0.1 --port 8002 --workers 4 &

# Instance 3
uvicorn app:app --host 127.0.0.1 --port 8003 --workers 4 &
```

### Option 3: Docker Compose

**Best for**: Development and small production deployments

See [`examples/fastapi_multiworker/docker-compose.yml`](../examples/fastapi_multiworker/docker-compose.yml)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f flexiai-api

# Scale horizontally
docker-compose up -d --scale flexiai-api=3
```

### Option 4: Kubernetes

**Best for**: Large-scale production, auto-scaling needs

```yaml
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
        image: flexiai-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: "redis-service"
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
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: flexiai-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: flexiai-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Load Balancing

### Algorithms

**1. Round Robin (Default)**:
- Distributes requests evenly across workers
- Simple and effective for uniform workloads
- Built into uvicorn

**2. Least Connections (Nginx)**:
- Sends requests to worker with fewest active connections
- Better for variable response times (LLM APIs)
- Recommended for FlexiAI

**3. IP Hash (Nginx)**:
- Same client always goes to same worker
- Useful for session affinity (not needed for FlexiAI)

**4. Weighted Round Robin (HAProxy)**:
- Assign different weights to workers/instances
- Useful when instances have different capacities

### HAProxy Configuration

```haproxy
global
    log /dev/log local0
    maxconn 4096

defaults
    log global
    mode http
    timeout connect 10s
    timeout client 300s
    timeout server 300s

frontend flexiai_frontend
    bind *:80
    default_backend flexiai_backend

backend flexiai_backend
    balance leastconn
    option httpchk GET /health/ready
    http-check expect status 200

    server worker1 127.0.0.1:8001 check inter 5s fall 3 rise 2
    server worker2 127.0.0.1:8002 check inter 5s fall 3 rise 2
    server worker3 127.0.0.1:8003 check inter 5s fall 3 rise 2
```

## Monitoring and Observability

### Health Check Endpoints

FlexiAI provides three health check endpoints:

**1. Comprehensive Health** (`/health`):
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "worker_id": 12345,
  "redis_connected": true,
  "sync_enabled": true,
  "providers": [
    {
      "name": "openai",
      "available": true,
      "circuit_state": "CLOSED",
      "failure_count": 0
    }
  ]
}
```

**2. Readiness Probe** (`/health/ready`):
- Returns 200 if ready to accept traffic
- Returns 503 if not ready (no available providers)
- Use in load balancers and Kubernetes

**3. Liveness Probe** (`/health/live`):
- Returns 200 if process is alive
- Use in Kubernetes to detect crashed containers

### Metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

Response:
```json
{
  "worker_id": 12345,
  "timestamp": "2024-01-15T10:30:00",
  "redis_status": "connected",
  "sync_enabled": true,
  "circuit_breakers": {
    "openai": {
      "state": "CLOSED",
      "failure_count": 0,
      "success_count": 1234
    },
    "anthropic": {
      "state": "CLOSED",
      "failure_count": 0,
      "success_count": 567
    }
  }
}
```

### Redis Monitoring

**Monitor Pub/Sub Activity**:
```bash
# Connect to Redis CLI
redis-cli

# Monitor all commands (verbose)
MONITOR

# View pub/sub channels
PUBSUB CHANNELS circuit_breaker:*

# Count subscribers
PUBSUB NUMSUB circuit_breaker:state:openai
```

**Check Redis Performance**:
```bash
# Latency monitoring
redis-cli --latency

# Latency history
redis-cli --latency-history

# Memory usage
redis-cli INFO memory

# Keyspace statistics
redis-cli INFO keyspace
```

### Application Logs

FlexiAI logs include worker identification:

```
2024-01-15 10:30:00 - INFO - [Worker:12345] - Worker 12345 ready to handle requests
2024-01-15 10:30:01 - INFO - [Worker:12345] - Worker 12345 processed request with provider: openai
2024-01-15 10:30:02 - WARNING - [Worker:12346] - Circuit breaker opened for provider: openai
2024-01-15 10:30:03 - INFO - [Worker:12347] - State sync received: openai circuit opened
```

### Prometheus Integration (Optional)

Export metrics to Prometheus for advanced monitoring:

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_count = Counter('flexiai_requests_total', 'Total requests', ['provider', 'status'])
response_time = Histogram('flexiai_response_seconds', 'Response time', ['provider'])
circuit_state = Gauge('flexiai_circuit_state', 'Circuit state (0=closed, 1=open)', ['provider'])

# In your endpoint
@app.post("/chat")
async def chat(request: ChatRequest):
    start = time.time()
    try:
        response = flexiai_client.chat.completions.create(...)
        request_count.labels(provider=response.provider, status='success').inc()
        return response
    except Exception as e:
        request_count.labels(provider='unknown', status='error').inc()
        raise
    finally:
        response_time.labels(provider=response.provider).observe(time.time() - start)
```

## Troubleshooting

### Common Issues

#### 1. Workers Not Synchronizing

**Symptoms**:
- Different circuit breaker states across workers
- Inconsistent failover behavior

**Diagnosis**:
```bash
# Check Redis connection from each worker
curl http://localhost:8000/health | jq '.redis_connected'

# Monitor Redis pub/sub
redis-cli
> PUBSUB CHANNELS circuit_breaker:*
> PUBSUB NUMSUB circuit_breaker:state:openai
```

**Solutions**:
- Verify Redis is running: `redis-cli ping`
- Check environment variables: `REDIS_HOST`, `REDIS_PORT`
- Review logs for Redis connection errors
- Ensure firewall allows Redis port (6379)
- Check Redis `bind` configuration (should allow worker IPs)

#### 2. Redis Connection Errors

**Symptoms**:
```
Failed to connect to Redis: Connection refused
sync_enabled: false
```

**Solutions**:
```bash
# Verify Redis is running
systemctl status redis
# or
docker ps | grep redis

# Test connection
telnet localhost 6379
redis-cli ping

# Check Redis logs
tail -f /var/log/redis/redis.log
# or
docker logs redis

# Verify network connectivity
netstat -tlnp | grep 6379
```

#### 3. High Latency

**Symptoms**:
- Slow response times
- Timeouts

**Diagnosis**:
```bash
# Check Redis latency
redis-cli --latency
redis-cli --latency-history

# Monitor slow queries
redis-cli --bigkeys

# Check worker load
top -p $(pgrep -f 'uvicorn.*app:app')
```

**Solutions**:
- Increase worker count: `--workers 8`
- Use Redis Cluster for high traffic
- Enable Redis persistence optimizations
- Increase connection pool size
- Monitor LLM provider response times

#### 4. Memory Issues

**Symptoms**:
- Workers crashing
- Out of memory errors

**Diagnosis**:
```bash
# Check worker memory usage
ps aux | grep uvicorn

# Monitor Redis memory
redis-cli INFO memory

# System memory
free -h
```

**Solutions**:
```bash
# Limit Redis memory
redis-cli CONFIG SET maxmemory 256mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Reduce worker count
uvicorn app:app --workers 2

# Increase system memory
# Add swap space or upgrade instance
```

#### 5. Circuit Breaker Stuck Open

**Symptoms**:
- Provider marked unavailable despite being healthy
- `circuit_state: OPEN` for extended period

**Solutions**:
```bash
# Check provider health
curl http://localhost:8000/providers

# Reset circuit breaker manually
curl -X POST http://localhost:8000/providers/openai/reset

# Verify provider API is accessible
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"

# Check logs for error patterns
grep "Circuit breaker" /var/log/flexiai/app.log
```

## Best Practices

### 1. Worker Configuration

✅ **Do**:
- Start with 4 workers per instance
- Use `workers = cores * 4` for I/O-bound workloads
- Monitor and adjust based on CPU/memory usage
- Use graceful shutdown (built into uvicorn)

❌ **Don't**:
- Use too many workers (>16 per instance typically)
- Set workers = 1 in production
- Change worker count without testing

### 2. Redis Configuration

✅ **Do**:
- Enable persistence (AOF) in production
- Set `maxmemory` and `maxmemory-policy`
- Use Redis Cluster for high availability
- Enable authentication (`requirepass`)
- Use TLS for remote connections
- Monitor memory usage

❌ **Don't**:
- Run Redis without persistence in production
- Use default Redis password
- Expose Redis to the internet without TLS
- Ignore Redis warnings in logs

### 3. Security

✅ **Do**:
- Use environment variables for API keys
- Enable Redis authentication
- Use TLS for Redis connections over network
- Implement rate limiting (e.g., with Nginx)
- Monitor for suspicious activity
- Rotate API keys regularly

❌ **Don't**:
- Commit API keys to version control
- Use weak Redis passwords
- Expose application directly to internet (use reverse proxy)
- Disable authentication in production

### 4. Monitoring

✅ **Do**:
- Set up health check monitoring (Datadog, Pingdom, etc.)
- Alert on circuit breaker state changes
- Track response times and error rates
- Monitor Redis connection status
- Log all errors with context
- Use structured logging

❌ **Don't**:
- Ignore health check failures
- Run without monitoring in production
- Disable logging to save resources
- Overlook gradual performance degradation

### 5. Scaling

✅ **Do**:
- Start with vertical scaling (more workers)
- Move to horizontal scaling as needed
- Use load balancers for multiple instances
- Implement auto-scaling based on metrics
- Test scaling under load before production

❌ **Don't**:
- Scale without load testing
- Add instances without load balancer
- Ignore resource limits
- Scale beyond what your budget allows

## Performance Tuning

### Optimizing Worker Count

**Formula for I/O-Bound Workloads** (LLM APIs):
```
workers = (2 * cores) to (4 * cores)
```

**Test Different Configurations**:
```bash
# Test with wrk or ab
for workers in 2 4 8 16; do
  echo "Testing with $workers workers"
  uvicorn app:app --workers $workers &
  PID=$!
  sleep 5
  wrk -t 4 -c 100 -d 30s http://localhost:8000/chat/direct
  kill $PID
done
```

### Redis Performance

**Optimize Persistence**:
```conf
# AOF rewrite
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Disable RDB snapshots (use AOF only)
save ""

# Or use hybrid persistence
save 900 1
save 300 10
appendonly yes
```

**Connection Pooling**:
```python
# In your application
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    max_connections=50,  # Pool size
    socket_keepalive=True,
    socket_connect_timeout=5,
    retry_on_timeout=True
)
```

### Uvicorn Tuning

```bash
uvicorn app:app \
  --workers 4 \
  --timeout-keep-alive 65 \
  --limit-concurrency 1000 \
  --limit-max-requests 10000 \
  --backlog 2048
```

### Load Testing

**Using Apache Bench**:
```bash
ab -n 1000 -c 10 -p request.json -T application/json \
  http://localhost:8000/chat/direct
```

**Using wrk**:
```bash
wrk -t 4 -c 100 -d 60s --latency \
  -s post.lua \
  http://localhost:8000/chat/direct
```

`post.lua`:
```lua
wrk.method = "POST"
wrk.body   = '{"message": "Hello", "temperature": 0.7}'
wrk.headers["Content-Type"] = "application/json"
```

## Security

### API Keys Management

**Use Environment Variables**:
```bash
# .env file (never commit)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Use Secrets Manager** (Production):
```python
# AWS Secrets Manager
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

secrets = get_secret('flexiai/api-keys')
OPENAI_API_KEY = secrets['openai_key']
```

### Redis Security

**Enable Authentication**:
```conf
# redis.conf
requirepass your-very-strong-password-here
```

```python
# In application
sync_config = SyncConfig(
    enabled=True,
    backend="redis",
    redis_host=REDIS_HOST,
    redis_password=os.getenv("REDIS_PASSWORD")
)
```

**Enable TLS** (for remote Redis):
```conf
# redis.conf
port 0
tls-port 6379
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt
```

```python
# In application
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=6379,
    password=REDIS_PASSWORD,
    ssl=True,
    ssl_ca_certs='/path/to/ca.crt'
)
```

### Network Security

**Firewall Rules**:
```bash
# Allow only specific IPs to Redis
sudo ufw allow from 192.168.1.0/24 to any port 6379

# Allow HTTP/HTTPS for API
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

**Rate Limiting** (Nginx):
```nginx
http {
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        location /chat {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://flexiai_backend;
        }
    }
}
```

### Input Validation

Already handled by Pydantic models in FastAPI:

```python
class ChatRequest(BaseModel):
    message: str = Field(..., max_length=10000)
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0, le=4000)
```

## Next Steps

- **Production Checklist**: Review [`examples/fastapi_multiworker/README.md`](../examples/fastapi_multiworker/README.md)
- **Example Application**: [`examples/fastapi_multiworker/app.py`](../examples/fastapi_multiworker/app.py)
- **Docker Deployment**: [`examples/fastapi_multiworker/docker-compose.yml`](../examples/fastapi_multiworker/docker-compose.yml)
- **Main Documentation**: [FlexiAI README](../README.md)

## Support

For issues or questions:
- GitHub Issues: [FlexiAI Issues](https://github.com/yourusername/flexiai/issues)
- Documentation: [README.md](../README.md)
