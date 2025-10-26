"""Redis-based synchronization backend for multi-worker deployments."""

import threading
import time
from typing import Any, Callable, Dict, Optional

from flexiai.sync.base import BaseSyncBackend
from flexiai.sync.events import CircuitBreakerEvent
from flexiai.sync.serializers import StateSerializer

try:
    import redis
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import RedisError

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    RedisConnectionError = Exception
    RedisError = Exception


class RedisSyncBackend(BaseSyncBackend):
    """Redis-based synchronization backend for multi-worker deployments.

    Uses Redis pub/sub for event broadcasting and Redis keys for state storage.
    Supports distributed locking for concurrent state updates.

    Args:
        host: Redis server host (default: localhost)
        port: Redis server port (default: 6379)
        db: Redis database number (default: 0)
        password: Redis password (default: None)
        ssl: Use SSL connection (default: False)
        key_prefix: Prefix for all Redis keys (default: flexiai)
        channel: Pub/sub channel name (default: flexiai:events)
        state_ttl: TTL for state keys in seconds (default: 3600)
        socket_timeout: Socket timeout in seconds (default: 5)
        socket_connect_timeout: Socket connect timeout in seconds (default: 5)

    Raises:
        ImportError: If redis package is not installed
        ConnectionError: If unable to connect to Redis
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = False,
        key_prefix: str = "flexiai",
        channel: str = "flexiai:events",
        state_ttl: int = 3600,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
    ):
        """Initialize Redis backend."""
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis package not installed. " "Install with: pip install redis hiredis"
            )

        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.ssl = ssl
        self.key_prefix = key_prefix
        self.channel = channel
        self.state_ttl = state_ttl

        # Create Redis connection pool
        # Note: In redis-py 7.0+, SSL is handled via connection_class parameter
        if ssl:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                ssl=True,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                decode_responses=True,
            )
        else:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                decode_responses=True,
            )

        self._pool = self._client.connection_pool
        self._pubsub = None
        self._pubsub_thread = None
        self._serializer = StateSerializer()
        self._lock = threading.Lock()

        # Test connection
        try:
            self._client.ping()
        except (RedisConnectionError, RedisError) as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}") from e

    def _get_state_key(self, provider_name: str) -> str:
        """Get Redis key for provider state.

        Args:
            provider_name: Name of the provider

        Returns:
            Redis key string
        """
        return f"{self.key_prefix}:state:{provider_name}"

    def _get_lock_key(self, lock_name: str) -> str:
        """Get Redis key for distributed lock.

        Args:
            lock_name: Name of the lock

        Returns:
            Redis key string
        """
        return f"{self.key_prefix}:lock:{lock_name}"

    def publish_event(self, event: CircuitBreakerEvent) -> None:
        """Publish a circuit breaker event to all workers.

        Args:
            event: The event to publish

        Raises:
            ConnectionError: If unable to publish the event
        """
        try:
            serialized = self._serializer.serialize_event(event)
            self._client.publish(self.channel, serialized)
        except (RedisConnectionError, RedisError) as e:
            raise ConnectionError(f"Failed to publish event: {e}") from e

    def subscribe_to_events(self, callback: Callable[[CircuitBreakerEvent], None]) -> None:
        """Subscribe to circuit breaker events from other workers.

        Args:
            callback: Function to call when an event is received

        Note:
            This starts a background thread that listens for events.
        """
        with self._lock:
            if self._pubsub is not None:
                return  # Already subscribed

            self._pubsub = self._client.pubsub()
            self._pubsub.subscribe(**{self.channel: self._event_handler(callback)})
            self._pubsub_thread = self._pubsub.run_in_thread(sleep_time=0.01, daemon=True)

    def _event_handler(self, callback: Callable[[CircuitBreakerEvent], None]) -> Callable:
        """Create event handler for pub/sub messages.

        Args:
            callback: Function to call when an event is received

        Returns:
            Handler function for pub/sub
        """

        def handler(message):
            if message["type"] == "message":
                try:
                    event = self._serializer.deserialize_event(message["data"])
                    callback(event)
                except Exception:  # nosec B110
                    # Silently ignore deserialization or callback errors
                    pass

        return handler

    def get_state(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get the current state for a provider from Redis.

        Args:
            provider_name: Name of the provider

        Returns:
            State dictionary or None if not found

        Raises:
            ConnectionError: If unable to retrieve state
        """
        try:
            key = self._get_state_key(provider_name)
            data = self._client.get(key)
            if data is None:
                return None
            return self._serializer.deserialize_state(data)
        except (RedisConnectionError, RedisError) as e:
            raise ConnectionError(f"Failed to get state: {e}") from e

    def set_state(self, provider_name: str, state: Dict[str, Any]) -> None:
        """Set the state for a provider in Redis.

        Args:
            provider_name: Name of the provider
            state: State dictionary to store

        Raises:
            ConnectionError: If unable to set state
        """
        try:
            key = self._get_state_key(provider_name)
            serialized = self._serializer.serialize_state(state)
            self._client.setex(key, self.state_ttl, serialized)
        except (RedisConnectionError, RedisError) as e:
            raise ConnectionError(f"Failed to set state: {e}") from e

    def acquire_lock(self, lock_name: str, timeout: float = 10.0) -> bool:
        """Acquire a distributed lock using Redis.

        Args:
            lock_name: Name of the lock
            timeout: Maximum time to wait for the lock (seconds)

        Returns:
            True if lock acquired, False otherwise
        """
        key = self._get_lock_key(lock_name)
        lock_timeout = int(timeout * 2)  # Lock expiry (twice the wait timeout)
        identifier = f"{threading.get_ident()}:{time.time()}"

        end_time = time.time() + timeout
        while time.time() < end_time:
            # Try to acquire lock with SETNX (SET if Not eXists)
            if self._client.set(key, identifier, nx=True, ex=lock_timeout):
                return True
            # Wait a bit before retrying
            time.sleep(0.01)

        return False

    def release_lock(self, lock_name: str) -> None:
        """Release a distributed lock.

        Args:
            lock_name: Name of the lock to release
        """
        key = self._get_lock_key(lock_name)
        try:
            self._client.delete(key)
        except (RedisConnectionError, RedisError):
            # Ignore errors on release
            pass

    def health_check(self) -> bool:
        """Check if Redis is healthy and accessible.

        Returns:
            True if Redis is accessible, False otherwise
        """
        try:
            return self._client.ping()
        except (RedisConnectionError, RedisError):
            return False

    def close(self) -> None:
        """Close Redis connections and cleanup resources."""
        with self._lock:
            if self._pubsub_thread is not None:
                self._pubsub_thread.stop()
                self._pubsub_thread = None

            if self._pubsub is not None:
                self._pubsub.close()
                self._pubsub = None

            if self._pool is not None:
                self._pool.disconnect()
