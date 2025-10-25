# Primary Failback: How Circuit Breaker Recovery Works

## Your Question

> "Priority 1 model fails and instant circuit breaker switches to secondary model. Once switched, how does program know when primary model is back and start serving with that and leave secondary as backup?"

## Answer

FlexiAI's circuit breaker uses a **state machine with automatic recovery testing** to detect when the primary provider is healthy again and automatically switches back.

---

## Circuit Breaker State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  🔵 CLOSED (Healthy)                                           │
│  ├─ All requests go to primary provider (priority 1)          │
│  ├─ Circuit breaker monitors for failures                     │
│  └─ Success counter increments                                │
│                                                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Failures exceed threshold (default: 5)
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  🔴 OPEN (Failed)                                              │
│  ├─ Primary has failed too many times                         │
│  ├─ Circuit breaker BLOCKS requests to primary                │
│  ├─ System automatically uses secondary (priority 2)          │
│  ├─ Start recovery timer (default: 60 seconds)                │
│  └─ Wait for timeout before testing recovery                  │
│                                                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ After recovery_timeout elapses
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  🟡 HALF_OPEN (Testing Recovery)                               │
│  ├─ Circuit allows LIMITED test requests to primary           │
│  ├─ If primary succeeds → Close circuit (back to CLOSED)      │
│  ├─ If primary fails → Reopen circuit (back to OPEN)          │
│  └─ Max test requests: half_open_max_calls (default: 1)       │
│                                                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Test request succeeds
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  🔵 CLOSED (Recovered!)                                        │
│  ├─ Primary provider is healthy again                         │
│  ├─ System switches back to priority 1                        │
│  ├─ Secondary becomes backup again                            │
│  └─ Normal operation resumes                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## How It Works in Practice

### Step 1: Normal Operation
```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig

# Configure with primary and backup
config = FlexiAIConfig(providers=[
    ProviderConfig(
        name="openai",
        priority=1,  # PRIMARY
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini"
    ),
    ProviderConfig(
        name="anthropic",
        priority=2,  # SECONDARY (backup)
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-5-haiku-20241022"
    )
])

# Create ONE client for application lifetime
client = FlexiAI(config)

# Make request - uses primary (OpenAI)
response = client.chat_completion(messages=[...])
print(response.provider)  # Output: "openai"
```

**Circuit Status:** 🔵 CLOSED - Primary healthy

---

### Step 2: Primary Fails

```python
# Primary provider starts failing (API outage, network issue, etc.)
# Circuit breaker detects failures...

# Request 1: Primary fails ❌ (failure count: 1)
# Request 2: Primary fails ❌ (failure count: 2)
# Request 3: Primary fails ❌ (failure count: 3)
# Request 4: Primary fails ❌ (failure count: 4)
# Request 5: Primary fails ❌ (failure count: 5)

# Threshold reached! Circuit opens 🔴
```

**Circuit Status:** 🔴 OPEN - Primary circuit opened, using secondary

```python
# Subsequent requests automatically use secondary
response = client.chat_completion(messages=[...])
print(response.provider)  # Output: "anthropic"
```

---

### Step 3: Automatic Recovery Testing

After `recovery_timeout` seconds (default: 60), the circuit breaker automatically:

1. **Enters HALF_OPEN state** 🟡
2. **Tests primary provider** with next request
3. **Makes decision:**
   - ✅ Success → Close circuit, resume using primary
   - ❌ Failure → Reopen circuit, continue with secondary

```python
# 60 seconds after circuit opened...
# Circuit automatically enters HALF_OPEN state

# Next request tests primary
response = client.chat_completion(messages=[...])

# If primary API is back:
# ✅ Request succeeds
# → Circuit closes 🔵
# → Provider switches back to "openai"
print(response.provider)  # Output: "openai" (primary is back!)

# If primary is still down:
# ❌ Request fails
# → Circuit reopens 🔴
# → Continues using "anthropic"
# → Waits another 60s before retrying
```

**Circuit Status:** 🔵 CLOSED - Primary recovered and active again

---

## Configuration Options

### Default Configuration

```python
# Default circuit breaker settings
{
    "failure_threshold": 5,      # Failures before opening circuit
    "recovery_timeout": 60,      # Seconds before testing recovery
    "half_open_max_calls": 1,    # Test requests in HALF_OPEN
    "expected_exception": [      # Exceptions to count as failures
        "APIError",
        "Timeout",
        "RateLimitError"
    ]
}
```

### Custom Configuration

```python
from flexiai.models import CircuitBreakerConfig

config = FlexiAIConfig(
    providers=[...],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,      # More sensitive (open after 3 failures)
        recovery_timeout=30,      # Faster recovery testing (every 30s)
        half_open_max_calls=2     # Allow 2 test requests
    )
)
```

**Recommendations:**
- **Production:** `failure_threshold=5-10`, `recovery_timeout=60-120`
- **Development:** `failure_threshold=2-3`, `recovery_timeout=30`
- **Testing:** `failure_threshold=2`, `recovery_timeout=10`

---

## Key Points

### ✅ Automatic Detection

The circuit breaker **automatically detects** when primary is back:
- Uses **recovery_timeout** to schedule testing
- Tests primary in **HALF_OPEN** state
- No manual intervention needed

### ✅ Zero Configuration

Once configured, failover and recovery happen **automatically**:
- No code changes required
- No manual health checks needed
- System self-heals

### ✅ Priority-Based

Always prefers **higher priority** (lower number):
- Circuit CLOSED → uses priority 1
- Circuit OPEN → uses priority 2
- Circuit recovers → back to priority 1

### ⚠️ Important: Long-Lived Client

**CRITICAL:** Use ONE client instance for your application:

```python
# ✅ CORRECT - One client, circuit breaker maintains state
client = FlexiAI(config)

while True:
    # Circuit breaker automatically manages recovery
    response = client.chat_completion(...)

# ❌ WRONG - Don't recreate client!
for request in requests:
    client = FlexiAI(config)  # ❌ Circuit breaker state resets!
    response = client.chat_completion(...)
```

If you recreate the client:
- Circuit breaker state resets
- Recovery timer resets
- Automatic failback doesn't work

---

## Monitoring Recovery

### Check Circuit Breaker Status

```python
status = client.get_provider_status()

for provider_info in status["providers"]:
    name = provider_info["name"]
    state = provider_info["circuit_breaker"]["state"]
    healthy = provider_info["healthy"]
    failures = provider_info["circuit_breaker"]["failure_count"]

    print(f"{name}: {state} (failures={failures}, healthy={healthy})")
```

**Example Output:**
```
openai: closed (failures=0, healthy=True)
anthropic: closed (failures=0, healthy=True)
```

After primary failure:
```
openai: open (failures=5, healthy=False)
anthropic: closed (failures=0, healthy=True)
```

After recovery:
```
openai: closed (failures=0, healthy=True)
anthropic: closed (failures=0, healthy=True)
```

### Manual Recovery Control

```python
# Force circuit breaker reset (if needed)
client.reset_circuit_breakers()

# Or reset specific provider
client.reset_circuit_breakers("openai")
```

---

## Real-World Example

### Scenario: API Rate Limit

```python
import os
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, CircuitBreakerConfig

# Configure with aggressive failover
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            priority=1,
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini"
        ),
        ProviderConfig(
            name="anthropic",
            priority=2,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model="claude-3-5-haiku-20241022"
        )
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,   # Open after 3 rate limit errors
        recovery_timeout=60    # OpenAI rate limits typically reset in 60s
    )
)

client = FlexiAI(config)

# Your application runs...
while processing:
    try:
        response = client.chat_completion(messages=[...])

        # Automatic behavior:
        # 1. OpenAI hits rate limit → 3 failures → circuit opens
        # 2. System switches to Claude automatically
        # 3. After 60s, circuit tests OpenAI recovery
        # 4. OpenAI rate limit reset → circuit closes
        # 5. System switches back to OpenAI
        # All without any code changes!

    except Exception as e:
        # Handle any remaining errors
        logger.error(f"All providers failed: {e}")
```

---

## Timeline Example

**T=0s:** Primary healthy, all requests use OpenAI
**T=10s:** OpenAI API goes down
**T=11s:** Request fails (failure 1/5)
**T=12s:** Request fails (failure 2/5)
**T=13s:** Request fails (failure 3/5)
**T=14s:** Request fails (failure 4/5)
**T=15s:** Request fails (failure 5/5) → **Circuit opens** 🔴
**T=16s:** Request uses Claude (secondary) ✅
**T=17s-75s:** All requests use Claude
**T=76s:** (60s after opening) → **Circuit enters HALF_OPEN** 🟡
**T=76s:** Next request **tests OpenAI**
**T=76s:** OpenAI is back! Test succeeds → **Circuit closes** 🔵
**T=77s+:** All requests use OpenAI again (primary restored)

**Total downtime seen by users:** 0 seconds (automatic failover)

---

## Summary

**How does the program know when primary is back?**

1. **Recovery Timer:** After circuit opens, starts countdown (default: 60s)
2. **HALF_OPEN State:** When timer expires, allows test request to primary
3. **Success Test:** If primary succeeds, circuit closes and switches back
4. **Automatic:** No manual intervention, monitoring, or code changes needed
5. **Continuous:** If primary still failing, reopens and waits another 60s

**You don't need to check** - the circuit breaker does it for you automatically!

---

**For detailed implementation, see:**
- `flexiai/circuit_breaker.py` - State machine implementation
- `examples/circuit_breaker_test.py` - Working test examples
- `CIRCUIT_BREAKER_TESTING.md` - Testing guide
