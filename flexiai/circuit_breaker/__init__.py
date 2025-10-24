"""
Circuit breaker pattern implementation for provider failover.
"""

from flexiai.circuit_breaker.state import CircuitState, CircuitBreakerState
from flexiai.circuit_breaker.breaker import CircuitBreaker

__all__ = ["CircuitState", "CircuitBreakerState", "CircuitBreaker"]
