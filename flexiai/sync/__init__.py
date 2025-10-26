"""Multi-worker synchronization module for FlexiAI.

This module provides state synchronization across multiple worker processes
using Redis pub/sub and distributed state storage.
"""

from flexiai.sync.base import BaseSyncBackend
from flexiai.sync.events import CircuitBreakerEvent, CircuitBreakerEventType, StateUpdateEvent
from flexiai.sync.manager import StateSyncManager
from flexiai.sync.memory_backend import MemorySyncBackend
from flexiai.sync.redis_backend import RedisSyncBackend
from flexiai.sync.serializers import StateSerializer

__all__ = [
    "BaseSyncBackend",
    "CircuitBreakerEvent",
    "CircuitBreakerEventType",
    "StateUpdateEvent",
    "StateSyncManager",
    "MemorySyncBackend",
    "RedisSyncBackend",
    "StateSerializer",
]
