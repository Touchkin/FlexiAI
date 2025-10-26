# Circuit Breaker Pattern in FlexiAI

## Table of Contents
1. [Overview](#overview)
2. [Circuit Breaker States](#circuit-breaker-states)
3. [How It Works](#how-it-works)
4. [Configuration](#configuration)
5. [Failure Detection](#failure-detection)
6. [Automatic Failover](#automatic-failover)
7. [Recovery Process](#recovery-process)
8. [Complete Example](#complete-example)
9. [Best Practices](#best-practices)

---

## Overview

The **Circuit Breaker Pattern** is a design pattern used to detect failures and prevent cascading failures in distributed systems. FlexiAI implements circuit breakers to provide automatic failover between multiple GenAI providers (OpenAI, Anthropic, Google Vertex AI).

### What Problem Does It Solve?

Without circuit breaker:
```
API Request → Provider Timeout (30s) → Retry → Timeout (30s) → Fail
Total time: 60+ seconds of waiting!
```

With circuit breaker:
```
API Request → Circuit OPEN → Immediate failover to backup → Response in 2s
Total time: 2 seconds!
```

### Key Benefits

✅ **Fast Failure**: Stop trying failed providers immediately
✅ **Automatic Failover**: Switch to backup providers seamlessly
✅ **Self-Healing**: Automatically detect when primary recovers
✅ **No Manual Intervention**: Everything happens automatically
✅ **Production Ready**: Battle-tested pattern used by Netflix, AWS, etc.

---

## Circuit Breaker States

The circuit breaker operates in **three states**:

```
┌─────────────────────────────────────────────────────────────┐
│                    CIRCUIT BREAKER STATES                   │
└─────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │   CLOSED     │  ← Normal operation, requests flow through
    │  (Healthy)   │     Provider is working correctly
    └──────┬───────┘
           │
           │ Failures reach threshold
           │ (e.g., 3 consecutive failures)
           ▼
    ┌──────────────┐
    │     OPEN     │  ← Failing fast, requests blocked
    │  (Failing)   │     Using backup provider instead
    └──────┬───────┘
           │
           │ After recovery_timeout
           │ (e.g., 60 seconds)
           ▼
    ┌──────────────┐
    │  HALF_OPEN   │  ← Testing recovery, limited requests
    │  (Testing)   │     Allowing 1 request to test if recovered
    └──────┬───────┘
           │
           │ Test succeeds          │ Test fails
           ▼                        ▼
    ┌──────────────┐         ┌──────────────┐
    │   CLOSED     │         │     OPEN     │
    │  (Recovered) │         │  (Still Bad) │
    └──────────────┘         └──────────────┘
```

### State Descriptions

#### 1. CLOSED (Normal Operation)
- **Meaning**: Provider is healthy
- **Behavior**: All requests pass through normally
- **Monitoring**: Counting failures in background
- **Transition**: Opens after threshold failures (e.g., 3 failures)

```python
# When circuit is CLOSED
response = client.chat_completion(messages=[...])
# ✅ Request goes to primary provider
```

#### 2. OPEN (Failing Fast)
- **Meaning**: Provider is failing
- **Behavior**: Requests immediately fail (or use backup provider)
- **Duration**: Stays open for `recovery_timeout` seconds
- **Transition**: Becomes HALF_OPEN after timeout

```python
# When circuit is OPEN
response = client.chat_completion(messages=[...])
# ⚠️ Request immediately skips failed provider
# ✅ Uses backup provider instead (if configured)
```

#### 3. HALF_OPEN (Testing Recovery)
- **Meaning**: Testing if provider has recovered
- **Behavior**: Allows limited requests through (default: 1)
- **Success**: Closes circuit, back to normal
- **Failure**: Reopens circuit, waits another timeout

```python
# When circuit is HALF_OPEN
response = client.chat_completion(messages=[...])
# 🔄 Sends test request to primary
# ✅ If success: Circuit closes, primary is back!
# ❌ If failure: Circuit reopens, try again later
```

---

## How It Works

### Step-by-Step Flow

#### Initial Setup

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, CircuitBreakerConfig

# Configure with multiple providers
config = FlexiAIConfig(
    providers=[
        # Primary provider (Priority 1)
        ProviderConfig(
            name="openai",
            api_key="sk-...",
            model="gpt-4o-mini",
            priority=1  # Highest priority
        ),
        # Backup provider (Priority 2)
        ProviderConfig(
            name="anthropic",
            api_key="sk-ant-...",
            model="claude-3-5-haiku-20241022",
            priority=2  # Lower priority = backup
        )
    ],
    # Circuit breaker configuration
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,      # Open after 3 failures
        recovery_timeout=60,      # Test recovery after 60s
        half_open_max_calls=1     # Allow 1 test request
    )
)

# Create client (circuit starts in CLOSED state)
client = FlexiAI(config)
```

#### Normal Operation (Circuit CLOSED)

```python
# T=0s: First request
response = client.chat_completion(
    messages=[{"role": "user", "content": "Hello"}]
)
# ✅ Success! OpenAI responds
# Circuit state: CLOSED
# Failure count: 0/3

print(response.provider)  # "openai"
```

---

## Configuration

### Circuit Breaker Parameters

```python
CircuitBreakerConfig(
    failure_threshold=3,      # Number of failures before opening
    recovery_timeout=60,      # Seconds before testing recovery
    half_open_max_calls=1,    # Requests allowed in HALF_OPEN
    expected_exception="ProviderException"  # Exception type to catch
)
```

#### Parameter Details

| Parameter | Default | Description | Recommendation |
|-----------|---------|-------------|----------------|
| `failure_threshold` | 5 | Failures before circuit opens | 3-5 for quick failover, 10+ for tolerance |
| `recovery_timeout` | 60 | Seconds before testing recovery | 60s for APIs, 300s for heavy services |
| `half_open_max_calls` | 1 | Test requests in HALF_OPEN | Keep at 1 to minimize load |
| `expected_exception` | ProviderException | Exception type to catch | Use default |

### Examples for Different Scenarios

#### Development/Testing
```python
# Fast failover for quick testing
CircuitBreakerConfig(
    failure_threshold=2,      # Open after just 2 failures
    recovery_timeout=10,      # Test recovery every 10 seconds
    half_open_max_calls=1
)
```

#### Production - High Availability
```python
# Aggressive failover for critical systems
CircuitBreakerConfig(
    failure_threshold=3,      # Quick detection
    recovery_timeout=30,      # Frequent recovery checks
    half_open_max_calls=1
)
```

#### Production - Cost Sensitive
```python
# Tolerate temporary issues, reduce failovers
CircuitBreakerConfig(
    failure_threshold=10,     # More tolerant
    recovery_timeout=300,     # Less frequent checks
    half_open_max_calls=1
)
```

---

## Failure Detection

### How Failures Are Detected

FlexiAI considers these as failures:

1. **Authentication Errors** (401, 403)
2. **Rate Limiting** (429)
3. **Server Errors** (500, 502, 503, 504)
4. **Timeout Errors**
5. **Network Errors**
6. **Invalid Model/Configuration**

### Failure Tracking Example

```python
# Request 1
try:
    response = client.chat_completion(messages=[...])
except Exception as e:
    # Failure recorded
    # Circuit: CLOSED, Failures: 1/3
    pass

# Request 2
try:
    response = client.chat_completion(messages=[...])
except Exception as e:
    # Failure recorded
    # Circuit: CLOSED, Failures: 2/3
    pass

# Request 3
try:
    response = client.chat_completion(messages=[...])
except Exception as e:
    # Threshold reached!
    # Circuit: OPEN, Failures: 3/3
    # Future requests will use backup provider
    pass
```

### Monitoring Failures

```python
# Check circuit breaker status
status = client.get_provider_status()

for provider_info in status['providers']:
    cb = provider_info['circuit_breaker']

    print(f"Provider: {provider_info['name']}")
    print(f"Circuit State: {cb['state']}")
    print(f"Failures: {cb['failure_count']}/{cb['config']['failure_threshold']}")
    print(f"Successes: {cb['success_count']}")
    print()
```

**Output:**
```
Provider: openai
Circuit State: open
Failures: 3/3
Successes: 0

Provider: anthropic
Circuit State: closed
Failures: 0/3
Successes: 5
```

---

## Automatic Failover

### How Failover Works

When primary provider fails, FlexiAI automatically tries backup providers in priority order:

```python
# Configuration
providers=[
    ProviderConfig(name="openai", priority=1),      # Try first
    ProviderConfig(name="anthropic", priority=2),   # Try second
    ProviderConfig(name="vertexai", priority=3)     # Try third
]
```

### Failover Timeline

```
TIME    EVENT                           PROVIDER    CIRCUIT STATE
─────────────────────────────────────────────────────────────────
T=0s    Request 1                       OpenAI      CLOSED
        ❌ OpenAI fails (timeout)

T=2s    Request 2                       OpenAI      CLOSED
        ❌ OpenAI fails (timeout)
        Failure count: 2/3

T=4s    Request 3                       OpenAI      CLOSED
        ❌ OpenAI fails (timeout)
        🔥 Threshold reached!           OpenAI      OPEN

T=6s    Request 4
        ⚠️  OpenAI circuit OPEN         OpenAI      OPEN (skipped)
        ✅ Anthropic succeeds           Anthropic   CLOSED

T=8s    Request 5
        ⚠️  OpenAI circuit OPEN         OpenAI      OPEN (skipped)
        ✅ Anthropic succeeds           Anthropic   CLOSED
```

### Code Example

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, CircuitBreakerConfig

# Setup with primary and backup
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            api_key="sk-...",
            model="gpt-4o-mini",
            priority=1  # Primary
        ),
        ProviderConfig(
            name="anthropic",
            api_key="sk-ant-...",
            model="claude-3-5-haiku-20241022",
            priority=2  # Backup
        )
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60
    )
)

client = FlexiAI(config)

# Make requests - automatic failover happens
for i in range(10):
    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": f"Request {i+1}"}],
            max_tokens=50
        )

        print(f"Request {i+1}: ✅ {response.provider}")

    except Exception as e:
        print(f"Request {i+1}: ❌ {type(e).__name__}")

# Check which provider is being used
stats = client.get_request_stats()
print(f"\nProviders used: {stats['providers_used']}")
print(f"Last provider: {stats['last_used_provider']}")
```

**Sample Output:**
```
Request 1: ❌ AllProvidersFailedError  (OpenAI down)
Request 2: ❌ AllProvidersFailedError  (OpenAI down)
Request 3: ❌ AllProvidersFailedError  (OpenAI down, circuit opens)
Request 4: ✅ anthropic                (Failover to backup!)
Request 5: ✅ anthropic
Request 6: ✅ anthropic
Request 7: ✅ anthropic
Request 8: ✅ anthropic

Providers used: {'anthropic': {'requests': 5, 'avg_latency': 1.2}}
Last provider: anthropic
```

---

## Recovery Process

### Automatic Recovery Detection

The circuit breaker automatically detects when the primary provider has recovered.

### Recovery Timeline

```
TIME    EVENT                           CIRCUIT STATE    ACTION
──────────────────────────────────────────────────────────────────
T=0s    Primary fails                   OPEN            Using backup
        Circuit opened

T=15s   Still using backup              OPEN            Normal operation
        Primary not tested yet

T=30s   Still using backup              OPEN            Normal operation
        Primary not tested yet

T=60s   Recovery timeout reached!       HALF_OPEN       Ready to test
        Next request will test primary

T=61s   New request arrives             HALF_OPEN       Testing...
        🔄 Send to primary (test)

        Case A: Primary recovered
        ✅ Primary responds             CLOSED          Back to primary!
        Circuit closes

        OR

        Case B: Primary still down
        ❌ Primary fails                OPEN            Back to backup
        Circuit reopens
        Wait another 60 seconds
```

### Step-by-Step Recovery Process

#### Step 1: Primary Fails and Circuit Opens

```python
# T=0s: Circuit is CLOSED
client = FlexiAI(config)

# Primary provider fails 3 times
# Circuit automatically opens
```

#### Step 2: Using Backup Provider

```python
# T=5s to T=60s: Circuit is OPEN
# All requests automatically go to backup

response = client.chat_completion(messages=[...])
print(response.provider)  # "anthropic" (backup)

# Check status
status = client.get_provider_status()
for provider_info in status['providers']:
    if provider_info['name'] == 'openai':
        cb = provider_info['circuit_breaker']
        print(f"OpenAI Circuit: {cb['state']}")  # "open"
        print(f"Last failure: {cb['last_failure_time']}")
```

**Output:**
```
openai
Circuit: open
Last failure: 2025-10-26T12:00:05Z
```

#### Step 3: Recovery Timeout Expires

```python
# T=60s: recovery_timeout (60 seconds) has passed
# Circuit automatically transitions to HALF_OPEN
# No code needed - happens automatically!
```

#### Step 4: Testing Primary Recovery

```python
# T=61s: Next request triggers recovery test
response = client.chat_completion(
    messages=[{"role": "user", "content": "Test"}]
)

# Behind the scenes:
# 1. Circuit is HALF_OPEN
# 2. FlexiAI sends request to primary (OpenAI)
# 3. If OpenAI responds: Circuit CLOSES ✅
# 4. If OpenAI fails: Circuit REOPENS ❌

print(f"Provider: {response.provider}")  # "openai" if recovered!
```

#### Step 5A: Primary Recovered Successfully

```python
# Primary responded successfully!
# Circuit automatically closes

status = client.get_provider_status()
for provider_info in status['providers']:
    if provider_info['name'] == 'openai':
        cb = provider_info['circuit_breaker']
        print(f"Circuit: {cb['state']}")  # "closed"
        print(f"Successes: {cb['success_count']}")  # 1

# All future requests go back to primary
response = client.chat_completion(messages=[...])
print(response.provider)  # "openai" - we're back!
```

#### Step 5B: Primary Still Failing

```python
# Primary still not responding
# Circuit automatically reopens

status = client.get_provider_status()
for provider_info in status['providers']:
    if provider_info['name'] == 'openai':
        cb = provider_info['circuit_breaker']
        print(f"Circuit: {cb['state']}")  # "open" again

# System waits another recovery_timeout (60s)
# Will try again at T=121s
```

### Complete Recovery Example

```python
import time
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, CircuitBreakerConfig

# Create client with short recovery timeout for demo
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="anthropic",
            api_key="sk-ant-...",
            model="invalid-model-xyz",  # Will fail
            priority=1
        )
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=10,  # Only 10 seconds for demo
        half_open_max_calls=1
    )
)

client = FlexiAI(config)

# Trigger failures
print("Phase 1: Triggering failures...")
for i in range(3):
    try:
        client.chat_completion(messages=[{"role": "user", "content": "test"}])
    except:
        print(f"  Failure {i+1}")

# Check circuit is open
status = client.get_provider_status()
cb = status['providers'][0]['circuit_breaker']
print(f"\nCircuit opened! State: {cb['state']}")

# Wait for recovery timeout
print(f"\nPhase 2: Waiting {cb['config']['recovery_timeout']} seconds...")
time.sleep(cb['config']['recovery_timeout'] + 1)

# Next request will test recovery
print("\nPhase 3: Testing recovery...")
try:
    response = client.chat_completion(
        messages=[{"role": "user", "content": "recovery test"}]
    )
    print("✅ Primary recovered!")
except:
    print("❌ Primary still down, circuit reopened")

# Check final state
status = client.get_provider_status()
cb = status['providers'][0]['circuit_breaker']
print(f"\nFinal circuit state: {cb['state']}")
```

---

## Complete Example

### Production-Ready Setup

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, CircuitBreakerConfig
import os

def create_resilient_client():
    """
    Create a FlexiAI client with automatic failover.

    This configuration provides:
    - Primary: OpenAI (fastest, most reliable)
    - Backup 1: Anthropic Claude (high quality)
    - Backup 2: Google Vertex AI (scalable)
    - Automatic failover in <5 seconds
    - Automatic recovery detection
    """

    config = FlexiAIConfig(
        providers=[
            # Primary Provider
            ProviderConfig(
                name="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model="gpt-4o-mini",
                priority=1,
                config={
                    "timeout": 30,
                    "max_retries": 2
                }
            ),

            # Backup Provider 1
            ProviderConfig(
                name="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model="claude-3-5-haiku-20241022",
                priority=2
            ),

            # Backup Provider 2
            ProviderConfig(
                name="vertexai",
                api_key="not-used",
                model="gemini-2.0-flash-exp",
                priority=3,
                config={
                    "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
                    "location": "us-central1"
                }
            )
        ],

        # Circuit Breaker Configuration
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=3,      # Open after 3 failures
            recovery_timeout=60,      # Test recovery every 60s
            half_open_max_calls=1,    # 1 test request
            expected_exception="ProviderException"
        ),

        # Default parameters
        default_temperature=0.7,
        default_max_tokens=1000
    )

    return FlexiAI(config)


def make_request_with_monitoring(client, prompt):
    """
    Make a request and monitor circuit breaker status.
    """
    try:
        # Make request
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )

        # Log success
        print(f"✅ Success: {response.provider}")
        print(f"   Tokens: {response.usage.total_tokens}")

        # Check provider health
        status = client.get_provider_status()
        for provider_info in status['providers']:
            cb = provider_info['circuit_breaker']
            if cb['state'] != 'closed':
                print(f"⚠️  Warning: {provider_info['name']} circuit is {cb['state']}")

        return response

    except Exception as e:
        # Log failure
        print(f"❌ Failed: {type(e).__name__}")

        # Check all providers
        status = client.get_provider_status()
        print("\nProvider Status:")
        for provider_info in status['providers']:
            cb = provider_info['circuit_breaker']
            print(f"  {provider_info['name']}: {cb['state']}")

        raise


# Usage
if __name__ == "__main__":
    # Create client (keep alive for entire application)
    client = create_resilient_client()

    # Make requests - failover happens automatically
    prompts = [
        "What is Python?",
        "Explain machine learning",
        "Write a hello world program"
    ]

    for i, prompt in enumerate(prompts, 1):
        print(f"\n{'='*60}")
        print(f"Request {i}: {prompt[:30]}...")
        print('='*60)

        try:
            response = make_request_with_monitoring(client, prompt)
            print(f"\nResponse: {response.content[:100]}...")
        except Exception as e:
            print(f"\nAll providers failed: {e}")

    # Get statistics
    print(f"\n{'='*60}")
    print("SESSION STATISTICS")
    print('='*60)

    stats = client.get_request_stats()
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Successful: {stats['successful_requests']}")
    print(f"Failed: {stats['failed_requests']}")
    print(f"\nProviders Used:")
    for provider, info in stats['providers_used'].items():
        print(f"  {provider}: {info['requests']} requests, "
              f"avg latency: {info['avg_latency']:.2f}s")
```

---

## Best Practices

### 1. Keep Client Alive

❌ **Don't create new client for each request:**
```python
# BAD: Creates new circuit breaker each time
def make_request(prompt):
    client = FlexiAI(config)  # New client every time!
    return client.chat_completion(messages=[...])
```

✅ **Create client once, reuse it:**
```python
# GOOD: Circuit breaker state persists
client = FlexiAI(config)  # Create once at startup

def make_request(prompt):
    return client.chat_completion(messages=[...])  # Reuse client
```

### 2. Configure Appropriate Timeouts

```python
# Development: Fast feedback
CircuitBreakerConfig(
    failure_threshold=2,
    recovery_timeout=10
)

# Production: Balance between availability and cost
CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=60
)

# High-load systems: More tolerance
CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=120
)
```

### 3. Monitor Circuit Breaker Status

```python
import logging

def monitor_health(client):
    """Periodic health check for monitoring/alerting."""
    status = client.get_provider_status()

    for provider_info in status['providers']:
        cb = provider_info['circuit_breaker']

        if cb['state'] == 'open':
            logging.warning(
                f"Circuit OPEN for {provider_info['name']}! "
                f"Failures: {cb['failure_count']}"
            )
        elif cb['state'] == 'half_open':
            logging.info(
                f"Testing recovery for {provider_info['name']}"
            )

# Call periodically (e.g., every 30 seconds)
monitor_health(client)
```

### 4. Set Up Multiple Backup Providers

```python
# Single backup: If primary fails, only one option
providers=[
    ProviderConfig(name="openai", priority=1),
    ProviderConfig(name="anthropic", priority=2)
]

# Better: Multiple backups for redundancy
providers=[
    ProviderConfig(name="openai", priority=1),
    ProviderConfig(name="anthropic", priority=2),
    ProviderConfig(name="vertexai", priority=3)
]
```

### 5. Handle All Providers Failing

```python
from flexiai.exceptions import AllProvidersFailedError

try:
    response = client.chat_completion(messages=[...])
except AllProvidersFailedError as e:
    # All providers are down or circuits are open
    logging.error(f"All providers failed: {e}")

    # Fallback strategies:
    # 1. Return cached response
    # 2. Queue request for later
    # 3. Return error to user
    # 4. Use degraded mode

    return handle_total_failure()
```

### 6. Manual Circuit Control (When Needed)

```python
# Check status before important operation
status = client.get_provider_status()
all_open = all(
    p['circuit_breaker']['state'] == 'open'
    for p in status['providers']
)

if all_open:
    # All circuits open, manual intervention
    logging.critical("All circuits open! Manual reset needed")
    client.reset_circuit_breakers()

# Reset specific provider
client.reset_circuit_breakers("openai")

# Reset all providers
client.reset_circuit_breakers()
```

### 7. Testing Circuit Breaker

```python
# Use invalid model to safely test failover
test_config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="anthropic",
            api_key="valid-key",
            model="invalid-model-xyz",  # Will fail safely
            priority=1
        ),
        ProviderConfig(
            name="anthropic",
            api_key="valid-key",
            model="claude-3-5-haiku-20241022",  # Will work
            priority=2
        )
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout=5  # Short for testing
    )
)
```

---

## Summary

### Key Takeaways

✅ **Circuit Breaker Protects Your Application**
- Detects failures quickly
- Prevents cascading failures
- Provides automatic failover

✅ **Three States: CLOSED → OPEN → HALF_OPEN**
- CLOSED: Normal operation
- OPEN: Failing fast, using backup
- HALF_OPEN: Testing recovery

✅ **Automatic Recovery**
- No manual intervention needed
- Tests primary after timeout
- Switches back when recovered

✅ **Production Ready**
- Used by major companies
- Battle-tested pattern
- Handles real-world failures

### Quick Reference

```python
# Minimal setup
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, CircuitBreakerConfig

client = FlexiAI(FlexiAIConfig(
    providers=[
        ProviderConfig(name="openai", api_key="...", model="gpt-4o-mini", priority=1),
        ProviderConfig(name="anthropic", api_key="...", model="claude-3-5-haiku", priority=2)
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60
    )
))

# Make requests - failover happens automatically
response = client.chat_completion(messages=[...])
```

That's it! FlexiAI handles the rest automatically. 🎯

---

**Related Documentation:**
- [CIRCUIT_BREAKER_TESTING.md](CIRCUIT_BREAKER_TESTING.md) - Testing guide
- [PRIMARY_FAILBACK_GUIDE.md](PRIMARY_FAILBACK_GUIDE.md) - Detailed recovery explanation
- [README.md](README.md) - Main documentation
