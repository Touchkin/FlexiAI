# Production Best Practices for FlexiAI Multi-Worker Deployments

This document outlines production-ready configurations and best practices for deploying FlexiAI at scale.

## Table of Contents

- [Redis Production Setup](#redis-production-setup)
- [Health Check Strategies](#health-check-strategies)
- [Scaling Guidelines](#scaling-guidelines)
- [Performance Optimization](#performance-optimization)
- [Security Hardening](#security-hardening)
- [Observability and Monitoring](#observability-and-monitoring)
- [Disaster Recovery](#disaster-recovery)

## Redis Production Setup

### High Availability with Redis Sentinel

For production, use Redis Sentinel for automatic failover:

```yaml
# docker-compose.yml for Redis HA
version: '3.8'

services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-master-data:/data
    networks:
      - redis-network

  redis-replica-1:
    image: redis:7-alpine
    command: redis-server --slaveof redis-master 6379 --masterauth ${REDIS_PASSWORD} --requirepass ${REDIS_PASSWORD}
    depends_on:
      - redis-master
    networks:
      - redis-network

  redis-sentinel-1:
    image: redis:7-alpine
    command: >
      sh -c "echo 'sentinel monitor mymaster redis-master 6379 2
             sentinel auth-pass mymaster ${REDIS_PASSWORD}
             sentinel down-after-milliseconds mymaster 5000
             sentinel parallel-syncs mymaster 1
             sentinel failover-timeout mymaster 10000' > /etc/redis/sentinel.conf
             && redis-sentinel /etc/redis/sentinel.conf"
    depends_on:
      - redis-master
    networks:
      - redis-network

volumes:
  redis-master-data:

networks:
  redis-network:
```

### Redis Cluster for Horizontal Scaling

For very high throughput (10k+ req/s):

```bash
# Create 6-node Redis Cluster (3 masters + 3 replicas)
docker run -d --name redis-cluster \
  -p 7000-7005:7000-7005 \
  -e "IP=0.0.0.0" \
  -e "REDIS_CLUSTER_ANNOUNCE_IP=your-public-ip" \
  grokzen/redis-cluster:latest
```

**FlexiAI Configuration** (Cluster-aware):
```python
from redis.cluster import RedisCluster

# Use cluster-aware client
redis_client = RedisCluster(
    startup_nodes=[
        {"host": "127.0.0.1", "port": "7000"},
        {"host": "127.0.0.1", "port": "7001"},
        {"host": "127.0.0.1", "port": "7002"},
    ],
    password=REDIS_PASSWORD,
    decode_responses=True
)
```

### Persistence Configuration

**AOF (Append-Only File) - Recommended**:
```conf
# redis.conf
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec  # Balance between safety and performance

# Auto-rewrite when AOF grows
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
```

**RDB Snapshots (Secondary Backup)**:
```conf
# Take snapshot every 15min if 1+ keys changed
save 900 1
# Take snapshot every 5min if 10+ keys changed
save 300 10
# Take snapshot every 1min if 10000+ keys changed
save 60 10000
```

**Hybrid Persistence**:
```conf
# Best of both worlds
appendonly yes
aof-use-rdb-preamble yes  # RDB format for faster restarts, AOF for durability
```

### Memory Management

```conf
# Set memory limit (adjust based on your instance)
maxmemory 2gb

# Eviction policy for FlexiAI (LRU is best for circuit breaker states)
maxmemory-policy allkeys-lru

# Don't evict keys with TTL
# maxmemory-policy volatile-lru

# Or use no eviction and monitor memory
# maxmemory-policy noeviction
```

### Security

```conf
# Authentication
requirepass your-very-strong-password-123456

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG "CONFIG_ADMIN_ONLY"

# Network security
bind 127.0.0.1 ::1  # Only local connections
# Or specific IPs for multi-host
# bind 127.0.0.1 192.168.1.100 192.168.1.101

protected-mode yes

# TLS/SSL for production
tls-port 6379
port 0
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt
tls-auth-clients no  # or yes for mutual TLS
```

### Monitoring

```conf
# Slow log
slowlog-log-slower-than 10000  # 10ms
slowlog-max-len 128

# Client output buffer limits
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit pubsub 32mb 8mb 60
```

## Health Check Strategies

### Multi-Level Health Checks

Implement different health check levels for different purposes:

```python
from enum import Enum
from typing import Dict, Any

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

async def comprehensive_health_check() -> Dict[str, Any]:
    """Full health check - use for monitoring dashboards"""
    checks = {
        "redis": await check_redis_health(),
        "providers": await check_provider_health(),
        "circuit_breakers": await check_circuit_breaker_health(),
        "memory": await check_memory_usage(),
    }

    # Determine overall status
    if any(c["status"] == HealthStatus.UNHEALTHY for c in checks.values()):
        overall = HealthStatus.UNHEALTHY
    elif any(c["status"] == HealthStatus.DEGRADED for c in checks.values()):
        overall = HealthStatus.DEGRADED
    else:
        overall = HealthStatus.HEALTHY

    return {
        "status": overall.value,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }

async def readiness_check() -> bool:
    """Quick check - use for load balancers"""
    # Only check if we can serve requests
    if not flexiai_client:
        return False

    # At least one provider must be available
    for provider_name in flexiai_client.providers.keys():
        cb = flexiai_client.circuit_breakers.get(provider_name)
        if cb and cb.state in ["CLOSED", "HALF_OPEN"]:
            return True

    return False

async def liveness_check() -> bool:
    """Minimal check - use for Kubernetes liveness"""
    # Just check if process is responsive
    return True
```

### Health Check Intervals

**Load Balancer**:
- Interval: 5-10 seconds
- Timeout: 3 seconds
- Unhealthy threshold: 3 consecutive failures
- Healthy threshold: 2 consecutive successes

**Kubernetes**:
```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 3
  successThreshold: 1

livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 20
  timeoutSeconds: 5
  failureThreshold: 3
```

### Circuit Breaker Health Monitoring

```python
async def check_circuit_breaker_health() -> Dict[str, Any]:
    """Monitor circuit breaker health"""
    unhealthy_providers = []
    degraded_providers = []

    for provider_name, cb in flexiai_client.circuit_breakers.items():
        if cb.state == "OPEN":
            unhealthy_providers.append(provider_name)
        elif cb.state == "HALF_OPEN":
            degraded_providers.append(provider_name)

    if unhealthy_providers and len(unhealthy_providers) == len(flexiai_client.circuit_breakers):
        status = HealthStatus.UNHEALTHY  # All providers down
    elif unhealthy_providers or degraded_providers:
        status = HealthStatus.DEGRADED  # Some providers down
    else:
        status = HealthStatus.HEALTHY

    return {
        "status": status,
        "unhealthy": unhealthy_providers,
        "degraded": degraded_providers,
        "healthy": [
            name for name, cb in flexiai_client.circuit_breakers.items()
            if cb.state == "CLOSED"
        ]
    }
```

## Scaling Guidelines

### Vertical Scaling (Scale Up)

**When to Scale Up**:
- CPU consistently above 70%
- Memory consistently above 80%
- Response time degradation

**How to Scale Up**:
1. **Increase worker count**:
   ```bash
   # From 4 to 8 workers
   uvicorn app:app --workers 8
   ```

2. **Increase instance size**:
   - Double vCPUs → double workers
   - Maintain 512MB-1GB RAM per worker

3. **Optimize Redis**:
   ```bash
   # Increase Redis memory
   redis-cli CONFIG SET maxmemory 4gb
   ```

**Limits of Vertical Scaling**:
- Single machine limit (~16 workers typically)
- Single point of failure
- Expensive for large instances

### Horizontal Scaling (Scale Out)

**When to Scale Out**:
- Vertical scaling limits reached
- Need high availability
- Geographic distribution required
- Traffic exceeds 10k req/min per instance

**How to Scale Out**:

1. **Add more instances**:
   ```yaml
   # Kubernetes
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: flexiai-hpa
   spec:
     scaleTargetRef:
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
   ```

2. **Use load balancer**:
   ```nginx
   upstream flexiai_backend {
       least_conn;
       server instance1:8000 max_fails=3 fail_timeout=30s;
       server instance2:8000 max_fails=3 fail_timeout=30s;
       server instance3:8000 max_fails=3 fail_timeout=30s;
   }
   ```

3. **Shared Redis** (critical):
   - All instances MUST connect to same Redis
   - Use Redis Cluster for high traffic
   - Consider Redis Enterprise for SLA

### Auto-Scaling Strategies

**CPU-Based** (Simple):
```yaml
metrics:
- type: Resource
  resource:
    name: cpu
    target:
      type: Utilization
      averageUtilization: 70
```

**Request-Based** (Better):
```yaml
metrics:
- type: Pods
  pods:
    metric:
      name: requests_per_second
    target:
      type: AverageValue
      averageValue: "100"
```

**Custom Metrics** (Best):
```yaml
metrics:
- type: External
  external:
    metric:
      name: flexiai_circuit_breaker_failures
    target:
      type: AverageValue
      averageValue: "10"
```

### Scaling Checklist

- [ ] Load test before scaling
- [ ] Monitor resource utilization
- [ ] Set up auto-scaling policies
- [ ] Configure health checks
- [ ] Test failover scenarios
- [ ] Document scaling procedures
- [ ] Set up alerts for scaling events

## Performance Optimization

### Connection Pooling

**Redis Connection Pool**:
```python
redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    max_connections=50,  # Adjust based on worker count
    socket_keepalive=True,
    socket_connect_timeout=5,
    retry_on_timeout=True
)

redis_client = redis.Redis(connection_pool=redis_pool)
```

**HTTP Client Pooling** (for LLM providers):
```python
# OpenAI SDK uses httpx with connection pooling by default
# Adjust limits if needed
import openai
openai.max_retries = 3
openai.timeout = 30.0
```

### Caching Strategies

**Response Caching** (for repeated queries):
```python
from functools import lru_cache
import hashlib

def cache_key(messages: List[Message], temperature: float) -> str:
    """Generate cache key from request"""
    content = "".join(m.content for m in messages) + str(temperature)
    return hashlib.md5(content.encode()).hexdigest()

async def get_completion_cached(messages: List[Message], temperature: float):
    """Get completion with caching"""
    key = f"completion:{cache_key(messages, temperature)}"

    # Try cache first
    cached = await redis_client.get(key)
    if cached:
        return json.loads(cached)

    # Generate completion
    response = flexiai_client.chat.completions.create(
        messages=messages,
        temperature=temperature
    )

    # Cache for 1 hour
    await redis_client.setex(
        key,
        3600,
        json.dumps(response.model_dump())
    )

    return response
```

### Request Batching

For high-volume deployments:

```python
from asyncio import Queue, create_task
import asyncio

class RequestBatcher:
    def __init__(self, batch_size: int = 10, max_wait: float = 0.1):
        self.batch_size = batch_size
        self.max_wait = max_wait
        self.queue = Queue()

    async def process_batch(self):
        """Process requests in batches"""
        batch = []
        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                timeout = max(0, self.max_wait - (asyncio.get_event_loop().time() - start_time))
                request = await asyncio.wait_for(self.queue.get(), timeout=timeout)
                batch.append(request)

                if len(batch) >= self.batch_size:
                    await self._process(batch)
                    batch = []
                    start_time = asyncio.get_event_loop().time()

            except asyncio.TimeoutError:
                if batch:
                    await self._process(batch)
                    batch = []
                start_time = asyncio.get_event_loop().time()
```

### Async Optimization

```python
# Use async/await for concurrent provider calls
async def try_multiple_providers(messages: List[Message]):
    """Try multiple providers concurrently"""
    tasks = [
        try_provider("openai", messages),
        try_provider("anthropic", messages),
    ]

    # Return first successful response
    for coro in asyncio.as_completed(tasks):
        try:
            result = await coro
            return result
        except Exception:
            continue

    raise Exception("All providers failed")
```

## Security Hardening

### API Rate Limiting

**Application Level**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, chat_request: ChatRequest):
    # ... implementation
    pass
```

**Nginx Level**:
```nginx
http {
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        location /chat {
            limit_req zone=api_limit burst=20 nodelay;
            limit_req_status 429;
            proxy_pass http://backend;
        }
    }
}
```

### Input Sanitization

```python
from pydantic import Field, validator

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    temperature: float = Field(0.7, ge=0.0, le=2.0)

    @validator('message')
    def sanitize_message(cls, v):
        # Remove null bytes
        v = v.replace('\x00', '')
        # Trim excessive whitespace
        v = ' '.join(v.split())
        return v
```

### Secrets Management

**AWS Secrets Manager**:
```python
import boto3
import json

def get_secrets():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='flexiai/production')
    secrets = json.loads(response['SecretString'])
    return secrets

# In application startup
secrets = get_secrets()
os.environ['OPENAI_API_KEY'] = secrets['openai_key']
os.environ['REDIS_PASSWORD'] = secrets['redis_password']
```

**HashiCorp Vault**:
```python
import hvac

client = hvac.Client(url='https://vault.example.com')
client.auth.approle.login(
    role_id=os.getenv('VAULT_ROLE_ID'),
    secret_id=os.getenv('VAULT_SECRET_ID')
)

secrets = client.secrets.kv.v2.read_secret_version(path='flexiai/production')
OPENAI_API_KEY = secrets['data']['data']['openai_key']
```

### Network Security

**Firewall Rules** (UFW):
```bash
# Default deny
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (for management)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow Redis only from app servers
sudo ufw allow from 192.168.1.0/24 to any port 6379

# Enable
sudo ufw enable
```

**Security Groups** (AWS):
```yaml
SecurityGroupIngress:
  - IpProtocol: tcp
    FromPort: 80
    ToPort: 80
    CidrIp: 0.0.0.0/0
  - IpProtocol: tcp
    FromPort: 443
    ToPort: 443
    CidrIp: 0.0.0.0/0
  - IpProtocol: tcp
    FromPort: 6379
    ToPort: 6379
    SourceSecurityGroupId: !Ref AppSecurityGroup  # Only from app servers
```

## Observability and Monitoring

### Structured Logging

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage
logger.info(
    "request_completed",
    worker_id=WORKER_ID,
    provider="openai",
    duration_ms=123.45,
    status="success"
)
```

### Metrics Export

**Prometheus Metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

# Define metrics
request_count = Counter(
    'flexiai_requests_total',
    'Total requests',
    ['provider', 'status', 'endpoint']
)

request_duration = Histogram(
    'flexiai_request_duration_seconds',
    'Request duration',
    ['provider', 'endpoint']
)

circuit_breaker_state = Gauge(
    'flexiai_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half_open, 2=open)',
    ['provider']
)

provider_failures = Counter(
    'flexiai_provider_failures_total',
    'Total provider failures',
    ['provider', 'error_type']
)

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Use in endpoints
@app.post("/chat")
async def chat(request: ChatRequest):
    start = time.time()
    try:
        response = flexiai_client.chat.completions.create(...)
        request_count.labels(
            provider=response.provider,
            status='success',
            endpoint='/chat'
        ).inc()
        return response
    except Exception as e:
        provider_failures.labels(
            provider='unknown',
            error_type=type(e).__name__
        ).inc()
        raise
    finally:
        duration = time.time() - start
        request_duration.labels(
            provider=response.provider if 'response' in locals() else 'unknown',
            endpoint='/chat'
        ).observe(duration)
```

### Alerting

**Prometheus Alerts**:
```yaml
groups:
- name: flexiai_alerts
  rules:
  # High error rate
  - alert: HighErrorRate
    expr: rate(flexiai_requests_total{status="error"}[5m]) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"

  # All providers down
  - alert: AllProvidersDown
    expr: sum(flexiai_circuit_breaker_state == 2) == count(flexiai_circuit_breaker_state)
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "All LLM providers are unavailable"

  # Redis connection lost
  - alert: RedisDisconnected
    expr: flexiai_redis_connected == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Redis connection lost on worker {{ $labels.worker_id }}"
```

### Distributed Tracing

**OpenTelemetry Integration**:
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Setup tracing
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

tracer = trace.get_tracer(__name__)

# Use in application
@app.post("/chat")
async def chat(request: ChatRequest):
    with tracer.start_as_current_span("chat_completion"):
        with tracer.start_as_current_span("flexiai_request"):
            response = flexiai_client.chat.completions.create(...)
        return response
```

## Disaster Recovery

### Backup Strategy

**Redis Backups**:
```bash
# Automated Redis backups
#!/bin/bash
BACKUP_DIR="/backups/redis"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Trigger BGSAVE
redis-cli BGSAVE

# Wait for save to complete
while [ $(redis-cli LASTSAVE) -eq $(redis-cli LASTSAVE) ]; do
    sleep 1
done

# Copy RDB file
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/dump_$TIMESTAMP.rdb"

# Copy AOF file
cp /var/lib/redis/appendonly.aof "$BACKUP_DIR/appendonly_$TIMESTAMP.aof"

# Retain last 7 days
find "$BACKUP_DIR" -mtime +7 -delete
```

**Schedule Backups**:
```bash
# Crontab
0 */6 * * * /usr/local/bin/redis-backup.sh  # Every 6 hours
```

### Recovery Procedures

**Restore from Backup**:
```bash
# 1. Stop Redis
sudo systemctl stop redis

# 2. Restore RDB file
sudo cp /backups/redis/dump_20240115_120000.rdb /var/lib/redis/dump.rdb

# 3. Restore AOF file (if using AOF)
sudo cp /backups/redis/appendonly_20240115_120000.aof /var/lib/redis/appendonly.aof

# 4. Set permissions
sudo chown redis:redis /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/appendonly.aof

# 5. Start Redis
sudo systemctl start redis
```

### Failover Testing

**Test Scenarios**:
1. Redis failure and recovery
2. Worker process crash
3. Complete instance failure
4. Provider API outage
5. Network partition

**Automated Failover Tests**:
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_redis_failover():
    """Test application handles Redis failure gracefully"""
    # 1. Verify normal operation
    response = await client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200

    # 2. Stop Redis
    await redis_container.stop()

    # 3. Verify degraded operation (no sync)
    response = await client.get("/health")
    assert response.json()["status"] == "degraded"
    assert response.json()["redis_connected"] == False

    # 4. Application should still work
    response = await client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200

    # 5. Restart Redis
    await redis_container.start()

    # 6. Verify recovery
    await asyncio.sleep(5)  # Wait for reconnection
    response = await client.get("/health")
    assert response.json()["redis_connected"] == True
```

## Checklist: Production Readiness

### Infrastructure
- [ ] Redis HA setup (Sentinel or Cluster)
- [ ] Load balancer configured
- [ ] Auto-scaling policies defined
- [ ] Firewall rules configured
- [ ] SSL/TLS certificates installed

### Security
- [ ] API keys in secrets manager
- [ ] Redis authentication enabled
- [ ] Network security groups configured
- [ ] Rate limiting implemented
- [ ] Input validation in place

### Monitoring
- [ ] Health check endpoints configured
- [ ] Metrics exported to monitoring system
- [ ] Alerts configured for critical issues
- [ ] Logging aggregation setup
- [ ] Distributed tracing enabled (optional)

### Operations
- [ ] Backup strategy defined and tested
- [ ] Disaster recovery procedures documented
- [ ] Runbook for common issues created
- [ ] On-call rotation established
- [ ] Incident response plan defined

### Performance
- [ ] Load testing completed
- [ ] Worker count optimized
- [ ] Connection pooling configured
- [ ] Caching strategy implemented (if needed)
- [ ] Performance baselines established

## Next Steps

- Review [Multi-Worker Deployment Guide](multi_worker_deployment.md)
- Check [Example Application](../examples/fastapi_multiworker/app.py)
- Set up [Monitoring and Alerts](#observability-and-monitoring)
- Test [Disaster Recovery](#disaster-recovery) procedures
- Read [Main Documentation](../README.md)
