# Phase 7.2: Multi-Worker Synchronization Architecture - Implementation Plan

## Overview
Enable circuit breaker state synchronization across multiple workers using Redis for production-ready multi-worker deployments.

## Goals
- ✅ Redis-based state sharing across workers
- ✅ Automatic failover detection and synchronization
- ✅ Distributed locking for state updates
- ✅ Graceful fallback to single-worker mode
- ✅ Production-ready with comprehensive tests

## Implementation Phases

### 1️⃣ Foundation (Day 1, Part 1)
**Time Estimate:** 2-3 hours

#### 1.1 Module Structure
- [ ] Create `flexiai/sync/` directory
- [ ] Create `flexiai/sync/__init__.py`
- [ ] Create `flexiai/sync/events.py` - Event classes
- [ ] Create `flexiai/sync/serializers.py` - State serialization
- [ ] Create `flexiai/sync/base.py` - Abstract base classes

#### 1.2 Event Definitions (`events.py`)
- [ ] `CircuitBreakerEvent` class
  - Event types: OPENED, CLOSED, HALF_OPEN, FAILURE, SUCCESS
  - Fields: provider_name, event_type, timestamp, worker_id, metadata
- [ ] `StateUpdateEvent` class
  - Fields: provider_name, state_data, timestamp, worker_id
- [ ] Event serialization to/from dict

#### 1.3 State Serialization (`serializers.py`)
- [ ] `StateSerializer` class
- [ ] `serialize_state(state_dict) -> str` (JSON)
- [ ] `deserialize_state(json_str) -> dict`
- [ ] `serialize_event(event) -> str`
- [ ] `deserialize_event(json_str) -> Event`
- [ ] Handle datetime, enums, and custom types

### 2️⃣ Backend Implementations (Day 1, Part 2)
**Time Estimate:** 3-4 hours

#### 2.1 Base Backend (`base.py`)
- [ ] `BaseSyncBackend` abstract class
- [ ] Abstract methods:
  - `publish_event(event)`
  - `subscribe_to_events(callback)`
  - `get_state(provider_name)`
  - `set_state(provider_name, state)`
  - `health_check()`
  - `close()`

#### 2.2 Memory Backend (`memory_backend.py`)
- [ ] `MemorySyncBackend` implementation
- [ ] In-memory state storage (dict)
- [ ] No-op pub/sub (single process)
- [ ] Thread-safe with locks
- [ ] For development and single-worker deployments

#### 2.3 Redis Backend (`redis_backend.py`)
- [ ] `RedisSyncBackend` implementation
- [ ] Redis connection with connection pooling
- [ ] Pub/Sub for event broadcasting
- [ ] Distributed state storage with keys: `flexiai:state:{provider_name}`
- [ ] Distributed locking with `SETNX` + TTL
- [ ] Channel: `flexiai:events`
- [ ] Automatic reconnection handling
- [ ] State TTL configuration

### 3️⃣ Synchronization Manager (Day 2, Part 1)
**Time Estimate:** 3-4 hours

#### 3.1 Manager Core (`manager.py`)
- [ ] `StateSyncManager` class
- [ ] Initialize with backend (auto-detect or configured)
- [ ] Worker ID generation: `{hostname}:{pid}:{timestamp}`
- [ ] Circuit breaker registry: `{provider_name: breaker}`
- [ ] Event handlers and callbacks

#### 3.2 State Synchronization
- [ ] `register_circuit_breaker(provider_name, breaker)`
- [ ] `on_local_state_change(provider_name, state)` - broadcast to others
- [ ] `on_remote_state_change(provider_name, state)` - apply to local breaker
- [ ] `sync_all_states()` - startup synchronization
- [ ] Thread-safe state updates

#### 3.3 Lifecycle Management
- [ ] `start()` - start pub/sub listener
- [ ] `stop()` - graceful shutdown
- [ ] Worker heartbeat mechanism (optional)
- [ ] Health checks

### 4️⃣ Circuit Breaker Integration (Day 2, Part 2)
**Time Estimate:** 2-3 hours

#### 4.1 Modify `circuit_breaker/breaker.py`
- [ ] Add `sync_manager` parameter to `__init__`
- [ ] Emit events on state transitions:
  - `_open()` → emit OPENED event
  - `_close()` → emit CLOSED event
  - `_half_open()` → emit HALF_OPEN event
  - `record_failure()` → emit FAILURE event
  - `record_success()` → emit SUCCESS event
- [ ] Add `apply_remote_state(state_dict)` method
- [ ] Register with sync_manager on initialization

#### 4.2 Thread Safety
- [ ] Ensure all state updates are thread-safe
- [ ] Use existing `_lock` for local updates
- [ ] Handle concurrent remote updates

### 5️⃣ Client Integration (Day 2, Part 3)
**Time Estimate:** 1-2 hours

#### 5.1 FlexiAI Client Updates
- [ ] Add sync configuration to `FlexiAIConfig`
- [ ] Initialize `StateSyncManager` if sync enabled
- [ ] Pass `sync_manager` to circuit breakers
- [ ] Add `close()` method for cleanup
- [ ] Start sync_manager in `__init__`

#### 5.2 Configuration Schema
```python
sync_config = {
    "enabled": True,
    "backend": "redis",  # or "memory"
    "redis": {
        "host": "localhost",
        "port": 6379,
        "password": None,
        "db": 0,
        "ssl": False,
    },
    "worker_id": None,  # auto-generated if None
    "key_prefix": "flexiai",
    "channel": "flexiai:events",
    "state_ttl": 3600,  # 1 hour
}
```

### 6️⃣ Testing (Day 3)
**Time Estimate:** 4-5 hours

#### 6.1 Unit Tests
- [ ] Test event serialization/deserialization
- [ ] Test state serialization/deserialization
- [ ] Test memory backend operations
- [ ] Test Redis backend operations (requires Redis)
- [ ] Test sync manager registration
- [ ] Test sync manager event handling

#### 6.2 Integration Tests
- [ ] Test state sync between 2 workers (multiprocessing)
- [ ] Test distributed locking
- [ ] Test Redis connection failure and fallback
- [ ] Test concurrent state updates
- [ ] Test circuit breaker state propagation
- [ ] Test worker startup synchronization

#### 6.3 Multi-Process Tests
- [ ] Create test harness with multiprocessing
- [ ] Simulate worker1 opening circuit → worker2 receives state
- [ ] Test race conditions and concurrent updates
- [ ] Test Redis pub/sub latency

### 7️⃣ Dependencies & Documentation (Day 3)
**Time Estimate:** 1-2 hours

#### 7.1 Dependencies
- [ ] Add to `requirements.txt`:
  ```
  redis>=4.5.0
  hiredis>=2.0.0  # optional, for performance
  ```
- [ ] Update `setup.py` with extras:
  ```python
  extras_require={
      'redis': ['redis>=4.5.0', 'hiredis>=2.0.0'],
      'sync': ['redis>=4.5.0', 'hiredis>=2.0.0'],
  }
  ```

#### 7.2 Documentation
- [ ] Update README with multi-worker configuration
- [ ] Create `docs/multi-worker-deployment.md`
- [ ] Add configuration examples
- [ ] Document Redis setup requirements
- [ ] Add troubleshooting section

## File Structure
```
flexiai/
├── sync/
│   ├── __init__.py          # Exports
│   ├── base.py              # BaseSyncBackend
│   ├── events.py            # Event classes
│   ├── serializers.py       # StateSerializer
│   ├── memory_backend.py    # MemorySyncBackend
│   ├── redis_backend.py     # RedisSyncBackend
│   └── manager.py           # StateSyncManager
├── circuit_breaker/
│   └── breaker.py           # Updated with sync support
└── client.py                # Updated with sync manager

tests/
├── unit/
│   ├── test_sync_events.py
│   ├── test_sync_serializers.py
│   ├── test_sync_memory_backend.py
│   ├── test_sync_redis_backend.py
│   └── test_sync_manager.py
└── integration/
    ├── test_multiworker_sync.py
    └── test_redis_integration.py
```

## Success Criteria
- ✅ All unit tests passing (>90% coverage)
- ✅ Integration tests with real Redis
- ✅ Multi-process tests demonstrating state sync
- ✅ Graceful fallback to memory backend
- ✅ No breaking changes to existing API
- ✅ Documentation complete
- ✅ Pre-commit hooks passing

## Timeline
- **Day 1:** Foundation + Backends (5-7 hours)
- **Day 2:** Manager + Integration (6-9 hours)
- **Day 3:** Testing + Documentation (5-7 hours)
- **Total:** 16-23 hours (2-3 days)

## Next Steps After Phase 7.2
1. Test with real multi-worker deployment
2. Phase 7.3: Uvicorn integration examples
3. Phase 7.4: Production deployment guide
4. Release v0.5.0 (Full multi-worker support)

---

**Status:** 📋 Ready to Start
**Start Date:** October 26, 2025
**Target Completion:** October 28-29, 2025
