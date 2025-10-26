# Circuit Breaker Documentation Index

Complete guide to understanding and using circuit breakers in FlexiAI.

## 📚 Documentation Files

### 1. **CIRCUIT_BREAKER_GUIDE.md** (START HERE)
**600+ lines | Comprehensive Guide**

The complete guide covering everything about circuit breakers:
- Overview and benefits
- State machine (CLOSED → OPEN → HALF_OPEN)
- Configuration options
- Failure detection
- Automatic failover
- Recovery process
- Complete code examples
- Best practices

**Read this first for complete understanding.**

→ [Open CIRCUIT_BREAKER_GUIDE.md](CIRCUIT_BREAKER_GUIDE.md)

---

### 2. **CIRCUIT_BREAKER_QUICK_REF.md**
**Visual Reference Card**

Quick reference for daily use:
- State diagram
- Configuration cheat sheet
- Common operations
- Timeline examples
- Monitoring snippets
- Production vs testing configs

**Print this for your desk!**

→ [Open CIRCUIT_BREAKER_QUICK_REF.md](CIRCUIT_BREAKER_QUICK_REF.md)

---

### 3. **PRIMARY_FAILBACK_GUIDE.md**
**Deep Dive into Recovery**

Detailed explanation of how primary recovery works:
- Complete state machine
- Step-by-step recovery process
- Timeline examples
- Configuration impact
- Long-lived client importance
- Real-world scenarios

**For understanding the recovery mechanism in depth.**

→ [Open PRIMARY_FAILBACK_GUIDE.md](PRIMARY_FAILBACK_GUIDE.md)

---

### 4. **CIRCUIT_BREAKER_TESTING.md**
**Testing Guide**

How to test circuit breaker functionality:
- Manual testing instructions
- Integration test results
- Configuration options
- Troubleshooting guide
- Best practices
- Production examples

**For QA and testing teams.**

→ [Open CIRCUIT_BREAKER_TESTING.md](CIRCUIT_BREAKER_TESTING.md)

---

### 5. **TESTING_METHODS.md**
**Alternative Testing Approaches**

Methods to test circuit breaker WITHOUT invalid API keys:
- Invalid model names (recommended)
- Extreme parameters
- Timeout simulation
- Rate limiting
- Manual state inspection

**For safe, production-like testing.**

→ [Open TESTING_METHODS.md](TESTING_METHODS.md)

---

### 6. **RECOVERY_TEST_RESULTS.md**
**Test Results Documentation**

Actual test results and analysis:
- Test methodology
- Phase-by-phase results
- Key insights
- Real-world scenarios
- Recommendations

**For validation and proof of concept.**

→ [Open RECOVERY_TEST_RESULTS.md](RECOVERY_TEST_RESULTS.md)

---

## 🎯 Learning Path

### Beginner Path
```
1. README.md (Quick Start section)
   ↓
2. CIRCUIT_BREAKER_GUIDE.md (Overview + How It Works)
   ↓
3. CIRCUIT_BREAKER_QUICK_REF.md (Keep handy)
   ↓
4. Try the examples
```

### Developer Path
```
1. CIRCUIT_BREAKER_GUIDE.md (Complete read)
   ↓
2. TESTING_METHODS.md (Learn testing approaches)
   ↓
3. Run test scripts
   ↓
4. PRIMARY_FAILBACK_GUIDE.md (Understand recovery)
   ↓
5. Implement in your project
```

### Operations/DevOps Path
```
1. CIRCUIT_BREAKER_GUIDE.md (Configuration section)
   ↓
2. CIRCUIT_BREAKER_QUICK_REF.md (Monitoring snippets)
   ↓
3. PRIMARY_FAILBACK_GUIDE.md (Recovery scenarios)
   ↓
4. Set up monitoring and alerting
```

---

## 🔧 Test Scripts

All test scripts are in the repository:

### **test_final_recovery.py**
Complete circuit breaker demonstration:
- Simulates primary failure (invalid model)
- Shows recovery timeout
- Demonstrates automatic recovery testing
- Best for understanding the full flow

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python test_final_recovery.py
```

### **test_recovery_simulation.py**
Multi-provider failover demonstration:
- Primary (OpenAI) → Backup (Anthropic)
- Real failover scenario
- Recovery simulation

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
python test_recovery_simulation.py
```

### **test_primary_recovery.py**
Primary failback demonstration:
- Invalid primary → Valid backup
- Circuit breaker state transitions
- Manual reset demonstration

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python test_primary_recovery.py
```

### **test_circuit_breaker_recovery.py**
Alternative testing methods:
- 5 different testing approaches
- Safe failure simulation
- No invalid API keys needed

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python test_circuit_breaker_recovery.py
```

### **examples/circuit_breaker_test.py**
Official example in package:
- Production-ready example
- All test scenarios
- Commented and documented

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
python examples/circuit_breaker_test.py
```

---

## 📖 Quick Start

### 5-Minute Setup

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, CircuitBreakerConfig

# 1. Configure providers with priorities
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

    # 2. Configure circuit breaker
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,      # Open after 3 failures
        recovery_timeout=60,      # Test recovery every 60s
        half_open_max_calls=1     # 1 test request
    )
)

# 3. Create client (keep it alive!)
client = FlexiAI(config)

# 4. Make requests - failover happens automatically
response = client.chat_completion(
    messages=[{"role": "user", "content": "Hello!"}]
)

print(f"Provider: {response.provider}")  # Shows which provider responded
```

That's it! Circuit breaker handles the rest automatically.

---

## 🔍 Common Questions

### Q: How does the circuit breaker know when primary has recovered?
**A:** See [PRIMARY_FAILBACK_GUIDE.md](PRIMARY_FAILBACK_GUIDE.md) - Section "Automatic Recovery Testing"

### Q: How can I test circuit breaker without invalid API keys?
**A:** See [TESTING_METHODS.md](TESTING_METHODS.md) - Method 1: Invalid Model Names

### Q: What happens if all providers fail?
**A:** See [CIRCUIT_BREAKER_GUIDE.md](CIRCUIT_BREAKER_GUIDE.md) - Section "Best Practices #5"

### Q: How do I monitor circuit breaker in production?
**A:** See [CIRCUIT_BREAKER_QUICK_REF.md](CIRCUIT_BREAKER_QUICK_REF.md) - Section "Monitoring Code Snippet"

### Q: Can I manually reset the circuit breaker?
**A:** See [CIRCUIT_BREAKER_GUIDE.md](CIRCUIT_BREAKER_GUIDE.md) - Section "Best Practices #6"

### Q: What are the recommended configuration values?
**A:** See [CIRCUIT_BREAKER_QUICK_REF.md](CIRCUIT_BREAKER_QUICK_REF.md) - Section "Production Configuration"

---

## 📊 Visual Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    CIRCUIT BREAKER LIFECYCLE                    │
└─────────────────────────────────────────────────────────────────┘

Phase 1: NORMAL OPERATION
├─ Circuit: CLOSED
├─ Primary: Serving requests ✅
└─ Backup: Idle

        │ Primary fails 3 times
        ▼

Phase 2: FAILURE DETECTED
├─ Circuit: OPEN
├─ Primary: Blocked ❌
└─ Backup: Serving requests ✅

        │ Wait 60 seconds (recovery_timeout)
        ▼

Phase 3: TESTING RECOVERY
├─ Circuit: HALF_OPEN
├─ Primary: Test request sent 🔄
└─ Backup: Standing by

        │ Test succeeds
        ▼

Phase 4: RECOVERED
├─ Circuit: CLOSED
├─ Primary: Serving requests again ✅
└─ Backup: Idle

[Cycle repeats if primary fails again]
```

---

## 🎓 Recommended Reading Order

### First Time Users
1. Start: [CIRCUIT_BREAKER_GUIDE.md](CIRCUIT_BREAKER_GUIDE.md) - Read "Overview" and "How It Works"
2. Practice: Run `test_final_recovery.py`
3. Reference: Keep [CIRCUIT_BREAKER_QUICK_REF.md](CIRCUIT_BREAKER_QUICK_REF.md) open
4. Implement: Use code from "Complete Example" section

### Understanding Recovery
1. [CIRCUIT_BREAKER_GUIDE.md](CIRCUIT_BREAKER_GUIDE.md) - "Recovery Process" section
2. [PRIMARY_FAILBACK_GUIDE.md](PRIMARY_FAILBACK_GUIDE.md) - Complete read
3. [RECOVERY_TEST_RESULTS.md](RECOVERY_TEST_RESULTS.md) - See actual results

### Testing
1. [TESTING_METHODS.md](TESTING_METHODS.md) - All methods
2. [CIRCUIT_BREAKER_TESTING.md](CIRCUIT_BREAKER_TESTING.md) - Detailed guide
3. Run all test scripts
4. [RECOVERY_TEST_RESULTS.md](RECOVERY_TEST_RESULTS.md) - Compare with your results

---

## 💼 Production Checklist

Before deploying to production:

- [ ] Read [CIRCUIT_BREAKER_GUIDE.md](CIRCUIT_BREAKER_GUIDE.md) completely
- [ ] Configure appropriate `failure_threshold` and `recovery_timeout`
- [ ] Set up at least one backup provider
- [ ] Test failover with [TESTING_METHODS.md](TESTING_METHODS.md) approach
- [ ] Implement monitoring from [CIRCUIT_BREAKER_QUICK_REF.md](CIRCUIT_BREAKER_QUICK_REF.md)
- [ ] Create alerts for circuit state changes
- [ ] Document your provider priorities
- [ ] Test recovery scenarios
- [ ] Keep client instance alive (don't recreate)
- [ ] Review [CIRCUIT_BREAKER_GUIDE.md](CIRCUIT_BREAKER_GUIDE.md) "Best Practices"

---

## 🔗 External Resources

- **Martin Fowler's Circuit Breaker**: https://martinfowler.com/bliki/CircuitBreaker.html
- **Microsoft Pattern Guide**: https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker
- **Netflix Hystrix** (inspiration): https://github.com/Netflix/Hystrix

---

## 📝 Document Status

| Document | Last Updated | Lines | Status |
|----------|-------------|-------|--------|
| CIRCUIT_BREAKER_GUIDE.md | 2025-10-26 | 600+ | ✅ Complete |
| CIRCUIT_BREAKER_QUICK_REF.md | 2025-10-26 | 250+ | ✅ Complete |
| PRIMARY_FAILBACK_GUIDE.md | 2025-10-26 | 388 | ✅ Complete |
| CIRCUIT_BREAKER_TESTING.md | 2025-10-26 | 303 | ✅ Complete |
| TESTING_METHODS.md | 2025-10-26 | 250+ | ✅ Complete |
| RECOVERY_TEST_RESULTS.md | 2025-10-26 | 200+ | ✅ Complete |

---

## 🤝 Contributing

Found an error or want to improve the documentation?

1. Open an issue describing the problem
2. Submit a pull request with improvements
3. Include code examples if relevant

---

## 📧 Support

- **Documentation Issues**: Check all 6 documents above
- **Code Issues**: See [README.md](README.md)
- **Testing Help**: See [TESTING_METHODS.md](TESTING_METHODS.md)
- **Production Support**: See [CIRCUIT_BREAKER_GUIDE.md](CIRCUIT_BREAKER_GUIDE.md) "Best Practices"

---

**Happy coding with resilient AI applications! 🚀**
