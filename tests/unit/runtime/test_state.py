"""Unit tests for Redis state management."""

import json
from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import LockError, RedisError

from entropy_playground.infrastructure.config import Config
from entropy_playground.runtime.state import AgentState, StateManager


@pytest.fixture
def config():
    """Create test configuration."""
    from entropy_playground.infrastructure.config import GitHubConfig
    
    return Config(
        github=GitHubConfig(token="test-token"),
        redis_url="redis://localhost:6379/0",
    )


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.info.return_value = {
        "redis_version": "7.0.0",
        "connected_clients": 1,
        "used_memory_human": "1M",
        "used_memory_peak_human": "2M",
        "total_commands_processed": 100,
        "instantaneous_ops_per_sec": 10,
        "keyspace_hits": 80,
        "keyspace_misses": 20,
    }
    return mock


@pytest.fixture
def state_manager(config, mock_redis):
    """Create state manager with mocked Redis."""
    with patch("entropy_playground.runtime.state.Redis") as mock_redis_cls:
        mock_redis_cls.return_value = mock_redis
        manager = StateManager(config)
        # Force client initialization
        _ = manager.client
        return manager


class TestStateManager:
    """Test StateManager class."""

    def test_initialization(self, config):
        """Test state manager initialization."""
        manager = StateManager(config)
        assert manager.config == config
        assert manager._pool is None
        assert manager._client is None

    def test_connection_pool_creation(self, config):
        """Test Redis connection pool creation."""
        with patch("entropy_playground.runtime.state.redis.ConnectionPool.from_url") as mock_pool:
            manager = StateManager(config)
            pool = manager.pool
            mock_pool.assert_called_once_with(
                config.redis_url,
                max_connections=50,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30,
            )
            assert pool == mock_pool.return_value

    def test_client_creation(self, state_manager, mock_redis):
        """Test Redis client creation."""
        assert state_manager.client == mock_redis

    def test_close(self, state_manager):
        """Test closing connections."""
        mock_pool = MagicMock()
        state_manager._pool = mock_pool
        state_manager.close()
        mock_pool.disconnect.assert_called_once()
        assert state_manager._pool is None
        assert state_manager._client is None

    # State Persistence Tests

    def test_get_existing_key(self, state_manager, mock_redis):
        """Test getting an existing key."""
        mock_redis.get.return_value = '{"name": "test", "value": 123}'
        result = state_manager.get("test_key")
        assert result == {"name": "test", "value": 123}
        mock_redis.get.assert_called_once_with("test_key")

    def test_get_nonexistent_key(self, state_manager, mock_redis):
        """Test getting a nonexistent key."""
        mock_redis.get.return_value = None
        result = state_manager.get("missing_key")
        assert result is None

    def test_get_non_json_value(self, state_manager, mock_redis):
        """Test getting a non-JSON value."""
        mock_redis.get.return_value = "plain_string"
        result = state_manager.get("string_key")
        assert result == "plain_string"

    def test_get_redis_error(self, state_manager, mock_redis):
        """Test handling Redis errors on get."""
        mock_redis.get.side_effect = RedisError("Connection failed")
        with pytest.raises(RedisError):
            state_manager.get("error_key")

    def test_set_value(self, state_manager, mock_redis):
        """Test setting a value."""
        mock_redis.set.return_value = True
        result = state_manager.set("test_key", {"data": "value"})
        assert result is True
        mock_redis.set.assert_called_once_with("test_key", '{"data": "value"}')

    def test_set_with_ttl(self, state_manager, mock_redis):
        """Test setting a value with TTL."""
        mock_redis.setex.return_value = True
        result = state_manager.set("temp_key", {"temp": True}, ttl=3600)
        assert result is True
        mock_redis.setex.assert_called_once_with("temp_key", 3600, '{"temp": true}')

    def test_set_non_serializable(self, state_manager):
        """Test setting a non-serializable value."""
        with pytest.raises(TypeError):
            state_manager.set("bad_key", lambda x: x)

    def test_delete_key(self, state_manager, mock_redis):
        """Test deleting a key."""
        mock_redis.delete.return_value = 1
        result = state_manager.delete("test_key")
        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")

    def test_exists_key(self, state_manager, mock_redis):
        """Test checking key existence."""
        mock_redis.exists.return_value = 1
        assert state_manager.exists("test_key") is True
        mock_redis.exists.return_value = 0
        assert state_manager.exists("missing_key") is False

    def test_get_many(self, state_manager, mock_redis):
        """Test getting multiple values."""
        mock_redis.mget.return_value = [
            '{"value": 1}',
            None,
            '{"value": 3}',
        ]
        result = state_manager.get_many(["key1", "key2", "key3"])
        assert result == {
            "key1": {"value": 1},
            "key3": {"value": 3},
        }

    def test_set_many(self, state_manager, mock_redis):
        """Test setting multiple values."""
        mock_redis.mset.return_value = True
        mapping = {"key1": {"a": 1}, "key2": {"b": 2}}
        result = state_manager.set_many(mapping)
        assert result is True
        expected_call = {
            "key1": '{"a": 1}',
            "key2": '{"b": 2}',
        }
        mock_redis.mset.assert_called_once_with(expected_call)

    # Distributed Locking Tests

    def test_lock_acquired(self, state_manager, mock_redis):
        """Test successful lock acquisition."""
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_redis.lock.return_value = mock_lock

        with state_manager.lock("test_lock") as lock:
            assert lock == mock_lock

        mock_redis.lock.assert_called_once_with(
            "test_lock",
            timeout=10.0,
            blocking_timeout=5.0,
            sleep=0.1,
        )
        mock_lock.acquire.assert_called_once()
        mock_lock.release.assert_called_once()

    def test_lock_not_acquired(self, state_manager, mock_redis):
        """Test failed lock acquisition."""
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = False
        mock_redis.lock.return_value = mock_lock

        with pytest.raises(LockError):
            with state_manager.lock("test_lock"):
                pass

    def test_lock_release_fails(self, state_manager, mock_redis):
        """Test lock release failure handling."""
        mock_lock = MagicMock()
        mock_lock.acquire.return_value = True
        mock_lock.release.side_effect = LockError("Already released")
        mock_redis.lock.return_value = mock_lock

        # Should not raise even if release fails
        with state_manager.lock("test_lock"):
            pass

    # Migration Tests

    def test_migrate_key(self, state_manager, mock_redis):
        """Test key migration."""
        mock_redis.get.return_value = '{"old": "data"}'
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1

        # Mock the lock
        with patch.object(state_manager, "lock"):
            result = state_manager.migrate_key("old_key", "new_key")
            assert result is True

        mock_redis.get.assert_called_with("old_key")
        mock_redis.set.assert_called_with("new_key", '{"old": "data"}')
        mock_redis.delete.assert_called_with("old_key")

    def test_migrate_key_with_transform(self, state_manager, mock_redis):
        """Test key migration with transformation."""
        mock_redis.get.return_value = '{"value": 10}'
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1

        def transform(data):
            data["value"] *= 2
            return data

        with patch.object(state_manager, "lock"):
            result = state_manager.migrate_key("old_key", "new_key", transform_fn=transform)
            assert result is True

        mock_redis.set.assert_called_with("new_key", '{"value": 20}')

    def test_migrate_nonexistent_key(self, state_manager, mock_redis):
        """Test migrating a nonexistent key."""
        mock_redis.get.return_value = None
        result = state_manager.migrate_key("missing", "new")
        assert result is False

    def test_bulk_migrate(self, state_manager, mock_redis):
        """Test bulk key migration."""
        mock_redis.scan_iter.return_value = ["agent:1", "agent:2", "agent:3"]
        mock_redis.get.return_value = '{"data": "value"}'
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1

        def transform(data):
            data["migrated"] = True
            return data

        def new_key_fn(old_key):
            return f"v2:{old_key}"

        with patch.object(state_manager, "lock"):
            count = state_manager.bulk_migrate("agent:*", transform, new_key_fn)
            assert count == 3

    # Backup and Restore Tests

    def test_backup_keys(self, state_manager, mock_redis):
        """Test backing up keys."""
        mock_redis.scan_iter.return_value = ["key1", "key2", "key3"]
        mock_redis.get.side_effect = [
            '{"data": "1"}',
            '{"data": "2"}',
            '{"data": "3"}',
        ]
        mock_redis.set.return_value = True

        with patch("entropy_playground.runtime.state.datetime") as mock_dt:
            mock_dt.utcnow.return_value.isoformat.return_value = "2024-01-01T00:00:00"
            count = state_manager.backup_keys()

        assert count == 3
        assert mock_redis.set.call_count == 3

    def test_restore_from_backup(self, state_manager, mock_redis):
        """Test restoring from backup."""
        backup_keys = [
            "backup:2024-01-01T00:00:00:key1",
            "backup:2024-01-01T00:00:00:key2",
        ]
        mock_redis.scan_iter.return_value = backup_keys
        mock_redis.get.side_effect = ['{"data": "1"}', '{"data": "2"}']
        mock_redis.exists.return_value = 0
        mock_redis.set.return_value = True

        count = state_manager.restore_from_backup("2024-01-01T00:00:00")
        assert count == 2

    def test_restore_skip_existing(self, state_manager, mock_redis):
        """Test restore skips existing keys when overwrite=False."""
        mock_redis.scan_iter.return_value = ["backup:2024-01-01T00:00:00:key1"]
        mock_redis.exists.return_value = 1

        count = state_manager.restore_from_backup("2024-01-01T00:00:00", overwrite=False)
        assert count == 0

    def test_list_backups(self, state_manager, mock_redis):
        """Test listing available backups."""
        mock_redis.scan_iter.return_value = [
            "backup:2024-01-01T00:00:00:key1",
            "backup:2024-01-01T00:00:00:key2",
            "backup:2024-01-02T00:00:00:key1",
        ]

        backups = state_manager.list_backups()
        assert backups == ["2024-01-02T00", "2024-01-01T00"]

    # Monitoring Tests

    def test_get_metrics(self, state_manager, mock_redis):
        """Test getting Redis metrics."""
        state_manager._pool = MagicMock()
        state_manager._pool.max_connections = 50

        metrics = state_manager.get_metrics()
        assert metrics["redis_version"] == "7.0.0"
        assert metrics["pool_max_connections"] == 50

    def test_health_check_success(self, state_manager, mock_redis):
        """Test successful health check."""
        mock_redis.ping.return_value = True
        assert state_manager.health_check() is True

    def test_health_check_failure(self, state_manager, mock_redis):
        """Test failed health check."""
        mock_redis.ping.side_effect = Exception("Connection failed")
        assert state_manager.health_check() is False


class TestAgentState:
    """Test AgentState helper class."""

    def test_initialization(self, state_manager):
        """Test agent state initialization."""
        agent_state = AgentState(state_manager, "test-agent-123")
        assert agent_state.agent_id == "test-agent-123"
        assert agent_state.prefix == "agent:test-agent-123"

    def test_key_generation(self, state_manager):
        """Test key generation."""
        agent_state = AgentState(state_manager, "test-agent")
        assert agent_state._key("status") == "agent:test-agent:status"

    def test_get_state(self, state_manager, mock_redis):
        """Test getting all agent state."""
        mock_redis.scan_iter.return_value = [
            "agent:test-agent:status",
            "agent:test-agent:task",
        ]
        mock_redis.get.side_effect = [
            '{"status": "running"}',
            '{"task": "process"}',
        ]

        agent_state = AgentState(state_manager, "test-agent")
        state = agent_state.get_state()

        assert state == {
            "status": {"status": "running"},
            "task": {"task": "process"},
        }

    def test_set_status(self, state_manager, mock_redis):
        """Test setting agent status."""
        mock_redis.set.return_value = True

        with patch("entropy_playground.runtime.state.datetime") as mock_dt:
            mock_dt.utcnow.return_value.isoformat.return_value = "2024-01-01T00:00:00"
            agent_state = AgentState(state_manager, "test-agent")
            result = agent_state.set_status("active")

        assert result is True
        expected_data = {
            "status": "active",
            "timestamp": "2024-01-01T00:00:00",
            "agent_id": "test-agent",
        }
        mock_redis.set.assert_called_with(
            "agent:test-agent:status",
            json.dumps(expected_data),
        )

    def test_get_status(self, state_manager, mock_redis):
        """Test getting agent status."""
        status_data = {
            "status": "active",
            "timestamp": "2024-01-01T00:00:00",
            "agent_id": "test-agent",
        }
        mock_redis.get.return_value = json.dumps(status_data)

        agent_state = AgentState(state_manager, "test-agent")
        status = agent_state.get_status()

        assert status == status_data

    def test_set_task(self, state_manager, mock_redis):
        """Test setting current task."""
        mock_redis.set.return_value = True

        with patch("entropy_playground.runtime.state.datetime") as mock_dt:
            mock_dt.utcnow.return_value.isoformat.return_value = "2024-01-01T00:00:00"
            agent_state = AgentState(state_manager, "test-agent")
            result = agent_state.set_task("task-123", {"description": "Process data"})

        assert result is True

    def test_clear_task(self, state_manager, mock_redis):
        """Test clearing current task."""
        mock_redis.delete.return_value = 1

        agent_state = AgentState(state_manager, "test-agent")
        result = agent_state.clear_task()

        assert result is True
        mock_redis.delete.assert_called_with("agent:test-agent:current_task")

    def test_add_to_history(self, state_manager, mock_redis):
        """Test adding event to history."""
        mock_redis.get.return_value = "[]"
        mock_redis.set.return_value = True

        with patch("entropy_playground.runtime.state.datetime") as mock_dt:
            mock_dt.utcnow.return_value.isoformat.return_value = "2024-01-01T00:00:00"
            agent_state = AgentState(state_manager, "test-agent")
            result = agent_state.add_to_history({"event": "task_completed"})

        assert result is True

    def test_history_limit(self, state_manager, mock_redis):
        """Test history is limited to 100 events."""
        # Create a history with 100 items
        existing_history = [{"event": f"event_{i}"} for i in range(100)]
        mock_redis.get.return_value = json.dumps(existing_history)
        mock_redis.set.return_value = True

        agent_state = AgentState(state_manager, "test-agent")
        agent_state.add_to_history({"event": "new_event"})

        # Verify the set call
        call_args = mock_redis.set.call_args[0]
        saved_history = json.loads(call_args[1])
        assert len(saved_history) == 100
        assert saved_history[-1]["event"] == "new_event"

