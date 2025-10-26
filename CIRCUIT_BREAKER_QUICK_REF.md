# Circuit Breaker Quick Reference Card

## 📊 Visual State Diagram

```
          Normal Operation
                │
                ▼
        ┌───────────────┐
        │    CLOSED     │ ◄─────┐
        │   (Healthy)   │       │
        └───────┬───────┘       │
                │               │
          3 failures            │ Test
                │             succeeds
                ▼               │
        ┌───────────────┐       │
        │     OPEN      │       │
        │   (Failing)   │       │
        └───────┬───────┘       │
                │               │
          60 seconds            │
                │               │
                ▼               │
        ┌───────────────┐       │
        │  HALF_OPEN    │───────┘
        │   (Testing)   │
        └───────────────┘
                │
          Test fails
                │
                ▼
        (Back to OPEN)
```

## ⚙️ Configuration Cheat Sheet

```python
# Quick Setup
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, CircuitBreakerConfig

client = FlexiAI(FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",           # Primary
            api_key="sk-...",
            model="gpt-4o-mini",
            priority=1               # Lower = higher priority
        ),
        ProviderConfig(
            name="anthropic",        # Backup
            api_key="sk-ant-...",
            model="claude-3-5-haiku-20241022",
            priority=2
        )
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,         # Failures before opening
        recovery_timeout=60,         # Seconds before testing recovery
        half_open_max_calls=1        # Test requests allowed
    )
))
```

## 🔍 Common Operations

### Check Circuit Status
```python
status = client.get_provider_status()
for p in status['providers']:
    print(f"{p['name']}: {p['circuit_breaker']['state']}")
```

### Monitor Failures
```python
status = client.get_provider_status()
for p in status['providers']:
    cb = p['circuit_breaker']
    print(f"Failures: {cb['failure_count']}/{cb['config']['failure_threshold']}")
```

### Reset Circuit Manually
```python
# Reset specific provider
client.reset_circuit_breakers("openai")

# Reset all
client.reset_circuit_breakers()
```

### Get Request Statistics
```python
stats = client.get_request_stats()
print(f"Total: {stats['total_requests']}")
print(f"Success: {stats['successful_requests']}")
print(f"Failed: {stats['failed_requests']}")
print(f"Last provider: {stats['last_used_provider']}")
```

## 📅 Timeline Example

```
TIME    PROVIDER    CIRCUIT     EVENT
────────────────────────────────────────────────────────────────
T=0s    OpenAI      CLOSED      ✅ Request succeeds
T=2s    OpenAI      CLOSED      ❌ Request fails (1/3)
T=4s    OpenAI      CLOSED      ❌ Request fails (2/3)
T=6s    OpenAI      CLOSED      ❌ Request fails (3/3)
                    OPEN        🔥 Circuit opens!

T=8s    Anthropic   CLOSED      ✅ Failover to backup
T=10s   Anthropic   CLOSED      ✅ Using backup
T=30s   Anthropic   CLOSED      ✅ Still using backup

T=66s               HALF_OPEN   ⏱️  Recovery timeout reached
T=67s   OpenAI      HALF_OPEN   🔄 Testing primary...
                    CLOSED      ✅ Primary recovered!

T=69s   OpenAI      CLOSED      ✅ Back to primary
```

## 🎯 State Behavior Reference

| State | Requests Go To | Counting Failures? | Next State |
|-------|---------------|-------------------|------------|
| CLOSED | Primary | ✅ Yes | OPEN (after threshold) |
| OPEN | Backup | ❌ No | HALF_OPEN (after timeout) |
| HALF_OPEN | Primary (test) | ✅ Yes | CLOSED (success) or OPEN (fail) |

## 🚨 Error Handling

```python
from flexiai.exceptions import AllProvidersFailedError

try:
    response = client.chat_completion(messages=[...])
    print(f"✅ {response.provider}")

except AllProvidersFailedError:
    # All providers down or circuits open
    print("❌ No available providers")

except Exception as e:
    # Other errors
    print(f"❌ Error: {e}")
```

## 💡 Best Practices

### ✅ DO
- Keep client instance alive (create once)
- Configure multiple backup providers
- Monitor circuit states in production
- Use appropriate timeouts for your use case
- Test failover before production

### ❌ DON'T
- Create new client for each request
- Set threshold too low (<2)
- Set recovery_timeout too short (<10s)
- Ignore circuit breaker state in logs
- Test with invalid API keys (use invalid models instead)

## 🔧 Testing Configuration

```python
# For Testing/Development
CircuitBreakerConfig(
    failure_threshold=2,          # Quick failover
    recovery_timeout=10,          # Fast recovery tests
    half_open_max_calls=1
)
```

## 🏭 Production Configuration

```python
# For Production
CircuitBreakerConfig(
    failure_threshold=3,          # Balanced
    recovery_timeout=60,          # Standard recovery
    half_open_max_calls=1
)

# High-Volume Production
CircuitBreakerConfig(
    failure_threshold=5,          # More tolerant
    recovery_timeout=120,         # Less frequent tests
    half_open_max_calls=1
)
```

## 📊 Monitoring Code Snippet

```python
import logging

def log_circuit_status(client):
    """Log circuit breaker status for monitoring."""
    status = client.get_provider_status()

    for provider in status['providers']:
        cb = provider['circuit_breaker']
        name = provider['name']
        state = cb['state']

        if state == 'open':
            logging.warning(f"🔴 {name} circuit OPEN - using backup")
        elif state == 'half_open':
            logging.info(f"🟡 {name} circuit HALF_OPEN - testing recovery")
        else:
            logging.debug(f"🟢 {name} circuit CLOSED - healthy")

# Call periodically or before critical operations
log_circuit_status(client)
```

## 🧪 Safe Testing Method

```python
# Use invalid model (NOT invalid API key!)
test_config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="anthropic",
            api_key="valid-api-key",           # Valid key
            model="invalid-model-xyz",         # Invalid model
            priority=1                         # Will fail
        ),
        ProviderConfig(
            name="anthropic",
            api_key="valid-api-key",           # Valid key
            model="claude-3-5-haiku-20241022", # Valid model
            priority=2                         # Will work
        )
    ]
)
```

## 📝 Common Scenarios

### Scenario 1: API Rate Limit Hit
```
T=0s:   Primary hits rate limit → Fails → Failover to backup
T=60s:  Circuit tests primary → Rate limit reset → Back to primary
```

### Scenario 2: Temporary Network Issue
```
T=0s:   Network timeout → Primary fails → Use backup
T=5s:   Network restored but circuit still open → Still using backup
T=60s:  Circuit tests → Primary works → Back to primary
```

### Scenario 3: Provider Outage
```
T=0s:   Provider down → Primary fails → Use backup
T=60s:  Circuit tests → Still down → Keep using backup
T=120s: Circuit tests → Still down → Keep using backup
T=180s: Circuit tests → Provider recovered → Back to primary
```

## 🔗 Related Commands

```bash
# Check FlexiAI version
pip show flexiai

# Enable debug logging
export FLEXIAI_LOG_LEVEL=DEBUG

# Run tests
pytest tests/integration/test_circuit_breaker.py

# Check circuit breaker status from terminal
python -c "from flexiai import FlexiAI; \
client = FlexiAI(config); \
print(client.get_provider_status())"
```

## 📚 Documentation Links

- **Full Guide**: [CIRCUIT_BREAKER_GUIDE.md](CIRCUIT_BREAKER_GUIDE.md)
- **Testing Guide**: [CIRCUIT_BREAKER_TESTING.md](CIRCUIT_BREAKER_TESTING.md)
- **Recovery Details**: [PRIMARY_FAILBACK_GUIDE.md](PRIMARY_FAILBACK_GUIDE.md)
- **Main Docs**: [README.md](README.md)

---

**Print this card for quick reference! 📋**
