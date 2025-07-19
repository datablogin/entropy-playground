"""Redis-based state management for agents.

This module provides a distributed state management system using Redis,
enabling agents to share state, coordinate actions, and maintain consistency
across the distributed system.
"""

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import redis
from redis import ConnectionPool, Redis
from redis.exceptions import LockError, RedisError
from structlog import get_logger

from entropy_playground.infrastructure.config import Config

logger = get_logger()


class StateManager:
    """Manages distributed state using Redis."""

    def __init__(self, config: Config):
        """Initialize the state manager.

        Args:
            config: Application configuration containing Redis URL
        """
        self.config = config
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    @property
    def pool(self) -> ConnectionPool:
        """Get or create the Redis connection pool."""
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                self.config.redis_url,
                max_connections=50,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30,
            )
            logger.info("redis_pool_created", url=self.config.redis_url)
        return self._pool

    @property
    def client(self) -> Redis:
        """Get or create the Redis client."""
        if self._client is None:
            self._client = Redis(connection_pool=self.pool, decode_responses=True)
            logger.info("redis_client_created")
        return self._client

    def close(self) -> None:
        """Close the Redis connection pool."""
        if self._pool:
            self._pool.disconnect()
            logger.info("redis_pool_closed")
            self._pool = None
            self._client = None

    # State Persistence Layer

    def get(self, key: str) -> Any | None:
        """Get a value from state.

        Args:
            key: The key to retrieve

        Returns:
            The value if found, None otherwise
        """
        try:
            value = self.client.get(key)
            if value is not None:
                return json.loads(value)
            return None
        except json.JSONDecodeError:
            logger.warning("state_get_decode_error", key=key, value=value)
            return value
        except RedisError as e:
            logger.error("state_get_error", key=key, error=str(e))
            raise

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set a value in state.

        Args:
            key: The key to set
            value: The value to store (will be JSON serialized)
            ttl: Optional TTL in seconds

        Returns:
            True if successful
        """
        try:
            serialized = json.dumps(value)
            if ttl:
                return bool(self.client.setex(key, ttl, serialized))
            return bool(self.client.set(key, serialized))
        except (TypeError, ValueError) as e:
            logger.error("state_set_serialize_error", key=key, error=str(e))
            raise
        except RedisError as e:
            logger.error("state_set_error", key=key, error=str(e))
            raise

    def delete(self, key: str) -> bool:
        """Delete a key from state.

        Args:
            key: The key to delete

        Returns:
            True if the key was deleted
        """
        try:
            return bool(self.client.delete(key))
        except RedisError as e:
            logger.error("state_delete_error", key=key, error=str(e))
            raise

    def exists(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: The key to check

        Returns:
            True if the key exists
        """
        try:
            return bool(self.client.exists(key))
        except RedisError as e:
            logger.error("state_exists_error", key=key, error=str(e))
            raise

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values at once.

        Args:
            keys: List of keys to retrieve

        Returns:
            Dictionary mapping keys to values
        """
        try:
            values = self.client.mget(keys)
            result = {}
            for key, value in zip(keys, values, strict=False):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value
            return result
        except RedisError as e:
            logger.error("state_get_many_error", keys=keys, error=str(e))
            raise

    def set_many(self, mapping: dict[str, Any]) -> bool:
        """Set multiple values at once.

        Args:
            mapping: Dictionary of key-value pairs

        Returns:
            True if successful
        """
        try:
            serialized = {k: json.dumps(v) for k, v in mapping.items()}
            return bool(self.client.mset(serialized))
        except (TypeError, ValueError) as e:
            logger.error("state_set_many_serialize_error", error=str(e))
            raise
        except RedisError as e:
            logger.error("state_set_many_error", error=str(e))
            raise

    # Distributed Locking

    @contextmanager
    def lock(
        self,
        name: str,
        timeout: float = 10.0,
        blocking_timeout: float = 5.0,
        sleep: float = 0.1,
    ) -> Iterator[Any]:
        """Acquire a distributed lock.

        Args:
            name: Name of the lock
            timeout: Lock timeout in seconds
            blocking_timeout: How long to wait for the lock
            sleep: Sleep interval between lock attempts

        Yields:
            The lock object

        Example:
            with state_manager.lock("my_resource"):
                # Critical section
                pass
        """
        lock = self.client.lock(
            name,
            timeout=timeout,
            blocking_timeout=blocking_timeout,
            sleep=sleep,
        )
        try:
            if lock.acquire():
                logger.info("lock_acquired", name=name)
                yield lock
            else:
                raise LockError(f"Failed to acquire lock: {name}")
        finally:
            try:
                lock.release()
                logger.info("lock_released", name=name)
            except LockError:
                # Lock might have timed out
                logger.warning("lock_release_failed", name=name)

    # State Migration Utilities

    def migrate_key(
        self,
        old_key: str,
        new_key: str,
        transform_fn: Callable[[Any], Any] | None = None,
    ) -> bool:
        """Migrate a key to a new name, optionally transforming the value.

        Args:
            old_key: The current key name
            new_key: The new key name
            transform_fn: Optional function to transform the value

        Returns:
            True if migration was successful
        """
        try:
            value = self.get(old_key)
            if value is None:
                logger.warning("migrate_key_not_found", old_key=old_key)
                return False

            if transform_fn:
                value = transform_fn(value)

            with self.lock(f"migration:{old_key}:{new_key}"):
                self.set(new_key, value)
                self.delete(old_key)
                logger.info("key_migrated", old_key=old_key, new_key=new_key)
                return True

        except Exception as e:
            logger.error(
                "migrate_key_error",
                old_key=old_key,
                new_key=new_key,
                error=str(e),
            )
            raise

    def bulk_migrate(
        self,
        pattern: str,
        transform_fn: Callable[[Any], Any],
        new_key_fn: Callable[[str], str],
    ) -> int:
        """Bulk migrate keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "agent:*")
            transform_fn: Function to transform values
            new_key_fn: Function to generate new key names

        Returns:
            Number of keys migrated
        """
        count = 0
        try:
            for key in self.client.scan_iter(match=pattern):
                new_key = new_key_fn(key)
                if self.migrate_key(key, new_key, transform_fn):
                    count += 1
            logger.info("bulk_migration_complete", pattern=pattern, count=count)
            return count
        except Exception as e:
            logger.error("bulk_migrate_error", pattern=pattern, error=str(e))
            raise

    # Backup and Restore

    def backup_keys(
        self,
        pattern: str = "*",
        backup_prefix: str = "backup:",
    ) -> int:
        """Backup keys matching a pattern.

        Args:
            pattern: Redis key pattern
            backup_prefix: Prefix for backup keys

        Returns:
            Number of keys backed up
        """
        count = 0
        timestamp = datetime.utcnow().isoformat()
        try:
            for key in self.client.scan_iter(match=pattern):
                if key.startswith(backup_prefix):
                    continue
                value = self.get(key)
                if value is not None:
                    backup_key = f"{backup_prefix}{timestamp}:{key}"
                    self.set(backup_key, value)
                    count += 1
            logger.info("backup_complete", pattern=pattern, count=count)
            return count
        except Exception as e:
            logger.error("backup_error", pattern=pattern, error=str(e))
            raise

    def restore_from_backup(
        self,
        backup_timestamp: str,
        backup_prefix: str = "backup:",
        overwrite: bool = False,
    ) -> int:
        """Restore keys from a backup.

        Args:
            backup_timestamp: The backup timestamp to restore from
            backup_prefix: Prefix used for backup keys
            overwrite: Whether to overwrite existing keys

        Returns:
            Number of keys restored
        """
        count = 0
        pattern = f"{backup_prefix}{backup_timestamp}:*"
        try:
            for backup_key in self.client.scan_iter(match=pattern):
                original_key = backup_key.replace(f"{backup_prefix}{backup_timestamp}:", "", 1)
                if not overwrite and self.exists(original_key):
                    logger.warning(
                        "restore_skip_existing",
                        key=original_key,
                    )
                    continue
                value = self.get(backup_key)
                if value is not None:
                    self.set(original_key, value)
                    count += 1
            logger.info(
                "restore_complete",
                timestamp=backup_timestamp,
                count=count,
            )
            return count
        except Exception as e:
            logger.error(
                "restore_error",
                timestamp=backup_timestamp,
                error=str(e),
            )
            raise

    def list_backups(self, backup_prefix: str = "backup:") -> list[str]:
        """List available backup timestamps.

        Args:
            backup_prefix: Prefix used for backup keys

        Returns:
            List of backup timestamps
        """
        timestamps: set[str] = set()
        pattern = f"{backup_prefix}*"
        try:
            for key in self.client.scan_iter(match=pattern):
                # Extract timestamp from key
                parts = key.split(":", 2)
                if len(parts) >= 2:
                    timestamps.add(parts[1])
            return sorted(timestamps, reverse=True)
        except Exception as e:
            logger.error("list_backups_error", error=str(e))
            raise

    # Monitoring and Metrics

    def get_metrics(self) -> dict[str, Any]:
        """Get Redis metrics and statistics.

        Returns:
            Dictionary of metrics
        """
        try:
            info = self.client.info()
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
                "total_commands_processed": info.get("total_commands_processed"),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "pool_max_connections": self.pool.max_connections,
            }
        except Exception as e:
            logger.error("get_metrics_error", error=str(e))
            return {"error": str(e)}

    def health_check(self) -> bool:
        """Check if Redis is healthy and responsive.

        Returns:
            True if healthy
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return False


# Agent-specific state helpers


class AgentState:
    """Helper class for agent-specific state management."""

    def __init__(self, state_manager: StateManager, agent_id: str):
        """Initialize agent state helper.

        Args:
            state_manager: The state manager instance
            agent_id: Unique agent identifier
        """
        self.state_manager = state_manager
        self.agent_id = agent_id
        self.prefix = f"agent:{agent_id}"

    def _key(self, name: str) -> str:
        """Generate a namespaced key for this agent."""
        return f"{self.prefix}:{name}"

    def get_state(self) -> dict[str, Any]:
        """Get all state for this agent."""
        pattern = f"{self.prefix}:*"
        state = {}
        for key in self.state_manager.client.scan_iter(match=pattern):
            name = key.replace(f"{self.prefix}:", "", 1)
            state[name] = self.state_manager.get(key)
        return state

    def set_status(self, status: str) -> bool:
        """Set agent status."""
        return self.state_manager.set(
            self._key("status"),
            {
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "agent_id": self.agent_id,
            },
        )

    def get_status(self) -> dict[str, Any] | None:
        """Get agent status."""
        return self.state_manager.get(self._key("status"))

    def set_task(self, task_id: str, task_data: dict[str, Any]) -> bool:
        """Set current task information."""
        return self.state_manager.set(
            self._key("current_task"),
            {
                "task_id": task_id,
                "task_data": task_data,
                "started_at": datetime.utcnow().isoformat(),
            },
        )

    def clear_task(self) -> bool:
        """Clear current task."""
        return self.state_manager.delete(self._key("current_task"))

    def add_to_history(self, event: dict[str, Any]) -> bool:
        """Add an event to agent history."""
        key = self._key("history")
        history = self.state_manager.get(key) or []
        history.append(
            {
                **event,
                "timestamp": datetime.utcnow().isoformat(),
                "agent_id": self.agent_id,
            }
        )
        # Keep only last 100 events
        if len(history) > 100:
            history = history[-100:]
        return self.state_manager.set(key, history)

