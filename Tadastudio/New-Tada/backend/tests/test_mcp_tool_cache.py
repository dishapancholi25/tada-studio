"""Tests for MCP tool definition caching in McpClientManager."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.mcp_client_manager import McpClientManager, _ToolCacheEntry


class TestToolCacheKey:
    """Tests for _create_tool_cache_key."""

    def test_same_config_produces_same_key(self):
        manager = McpClientManager()
        config = {"transport": "streamable_http", "url": "http://example.com/mcp"}
        key1 = manager._create_tool_cache_key(config)
        key2 = manager._create_tool_cache_key(config)
        assert key1 == key2

    def test_different_url_produces_different_key(self):
        manager = McpClientManager()
        config1 = {"transport": "streamable_http", "url": "http://a.com/mcp"}
        config2 = {"transport": "streamable_http", "url": "http://b.com/mcp"}
        assert manager._create_tool_cache_key(
            config1
        ) != manager._create_tool_cache_key(config2)

    def test_different_auth_headers_produce_different_key(self):
        manager = McpClientManager()
        config1 = {
            "transport": "streamable_http",
            "url": "http://example.com/mcp",
            "headers": {"Authorization": "Bearer token_a"},
        }
        config2 = {
            "transport": "streamable_http",
            "url": "http://example.com/mcp",
            "headers": {"Authorization": "Bearer token_b"},
        }
        assert manager._create_tool_cache_key(
            config1
        ) != manager._create_tool_cache_key(config2)

    def test_stdio_env_excluded_except_token_vars(self):
        manager = McpClientManager()
        config = {
            "transport": "stdio",
            "command": "/usr/bin/node",
            "args": ["server.js"],
            "env": {
                "PATH": "/usr/bin",
                "HOME": "/root",
                "SHAREPOINT_ACCESS_TOKEN": "tok123",
            },
        }
        key1 = manager._create_tool_cache_key(config)
        # Changing PATH/HOME should not change the key
        config2 = {
            "transport": "stdio",
            "command": "/usr/bin/node",
            "args": ["server.js"],
            "env": {
                "PATH": "/other",
                "HOME": "/other",
                "SHAREPOINT_ACCESS_TOKEN": "tok123",
            },
        }
        assert manager._create_tool_cache_key(config2) == key1

    def test_stdio_different_token_env_produces_different_key(self):
        manager = McpClientManager()
        config1 = {
            "transport": "stdio",
            "command": "node",
            "args": [],
            "env": {"DATABRICKS_TOKEN": "token_a"},
        }
        config2 = {
            "transport": "stdio",
            "command": "node",
            "args": [],
            "env": {"DATABRICKS_TOKEN": "token_b"},
        }
        assert manager._create_tool_cache_key(
            config1
        ) != manager._create_tool_cache_key(config2)

    def test_does_not_mutate_input(self):
        manager = McpClientManager()
        env = {"PATH": "/usr/bin", "DATABRICKS_TOKEN": "tok"}
        config = {"transport": "stdio", "command": "node", "args": [], "env": dict(env)}
        manager._create_tool_cache_key(config)
        # Original config should still have env key
        assert "env" in config


class TestToolCacheHitMiss:
    """Tests for cache hit/miss behavior."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_tools(self):
        manager = McpClientManager()
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"

        conn_config = {"transport": "streamable_http", "url": "http://example.com"}
        with patch.object(
            manager, "_build_connection_config", return_value=conn_config
        ):
            with patch(
                "backend.mcp_client_manager.load_mcp_tools",
                new_callable=AsyncMock,
                return_value=[mock_tool],
            ) as mock_load:
                # First call - cache miss
                tools1 = await manager.load_tools_from_server({"server_name": "Test"})
                assert len(tools1) == 1
                assert mock_load.call_count == 1

                # Second call - cache hit
                tools2 = await manager.load_tools_from_server({"server_name": "Test"})
                assert len(tools2) == 1
                assert mock_load.call_count == 1  # Not called again

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self):
        manager = McpClientManager()
        manager._tool_cache_ttl = 1  # 1 second TTL for testing
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"

        conn_config = {"transport": "streamable_http", "url": "http://example.com"}
        with patch.object(
            manager, "_build_connection_config", return_value=conn_config
        ):
            with patch(
                "backend.mcp_client_manager.load_mcp_tools",
                new_callable=AsyncMock,
                return_value=[mock_tool],
            ) as mock_load:
                await manager.load_tools_from_server({"server_name": "Test"})
                assert mock_load.call_count == 1

                time.sleep(1.5)

                await manager.load_tools_from_server({"server_name": "Test"})
                assert mock_load.call_count == 2  # Reloaded after TTL expiry

    @pytest.mark.asyncio
    async def test_different_configs_cached_separately(self):
        manager = McpClientManager()

        tool_a = MagicMock()
        tool_a.name = "tool_a"
        tool_b = MagicMock()
        tool_b.name = "tool_b"

        call_count = 0

        async def mock_load(client, connection=None):
            nonlocal call_count
            call_count += 1
            if "server-a" in connection.get("url", ""):
                return [tool_a]
            return [tool_b]

        configs = [
            {"transport": "streamable_http", "url": "http://server-a.com"},
            {"transport": "streamable_http", "url": "http://server-b.com"},
        ]
        config_idx = [0]

        def mock_build(config):
            result = configs[config_idx[0]]
            config_idx[0] = (config_idx[0] + 1) % 2
            return result

        with patch.object(manager, "_build_connection_config", side_effect=mock_build):
            with patch(
                "backend.mcp_client_manager.load_mcp_tools", side_effect=mock_load
            ):
                tools1 = await manager.load_tools_from_server({"server_name": "A"})
                tools2 = await manager.load_tools_from_server({"server_name": "B"})
                assert call_count == 2  # Both loaded fresh
                assert tools1[0].name == "tool_a"
                assert tools2[0].name == "tool_b"

    @pytest.mark.asyncio
    async def test_failed_load_not_cached(self):
        manager = McpClientManager()

        conn_config = {"transport": "streamable_http", "url": "http://example.com"}
        with patch.object(
            manager, "_build_connection_config", return_value=conn_config
        ):
            with patch(
                "backend.mcp_client_manager.load_mcp_tools",
                new_callable=AsyncMock,
                side_effect=Exception("Connection refused"),
            ) as mock_load:
                tools1 = await manager.load_tools_from_server({"server_name": "Test"})
                assert tools1 == []
                assert mock_load.call_count == 1

                # Second call should retry, not return cached empty
                tools2 = await manager.load_tools_from_server({"server_name": "Test"})
                assert tools2 == []
                assert mock_load.call_count == 2


class TestToolCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_all(self):
        manager = McpClientManager()
        manager._tool_cache["key1"] = _ToolCacheEntry(
            tools=[], timestamp=time.time(), server_name="Server A", tool_count=0
        )
        manager._tool_cache["key2"] = _ToolCacheEntry(
            tools=[], timestamp=time.time(), server_name="Server B", tool_count=0
        )
        count = manager.invalidate_tool_cache()
        assert count == 2
        assert len(manager._tool_cache) == 0

    def test_invalidate_by_server_name(self):
        manager = McpClientManager()
        manager._tool_cache["key1"] = _ToolCacheEntry(
            tools=[], timestamp=time.time(), server_name="Server A", tool_count=0
        )
        manager._tool_cache["key2"] = _ToolCacheEntry(
            tools=[], timestamp=time.time(), server_name="Server B", tool_count=0
        )
        count = manager.invalidate_tool_cache("Server A")
        assert count == 1
        assert len(manager._tool_cache) == 1
        assert "key2" in manager._tool_cache

    def test_invalidate_nonexistent_server(self):
        manager = McpClientManager()
        manager._tool_cache["key1"] = _ToolCacheEntry(
            tools=[], timestamp=time.time(), server_name="Server A", tool_count=0
        )
        count = manager.invalidate_tool_cache("Nonexistent")
        assert count == 0
        assert len(manager._tool_cache) == 1


class TestToolCacheEviction:
    """Tests for cache eviction behavior."""

    def test_max_size_evicts_lru(self):
        manager = McpClientManager()
        manager._tool_cache_max_size = 2

        # Add two entries
        manager._tool_cache["key1"] = _ToolCacheEntry(
            tools=[],
            timestamp=time.time(),
            server_name="A",
            tool_count=0,
            access_count=5,
        )
        manager._tool_cache["key2"] = _ToolCacheEntry(
            tools=[],
            timestamp=time.time(),
            server_name="B",
            tool_count=0,
            access_count=1,
        )

        # Adding a third should evict the LRU (key2 with fewest accesses)
        manager._cache_tools("key3", [], "C")
        assert len(manager._tool_cache) == 2
        assert "key1" in manager._tool_cache
        assert "key3" in manager._tool_cache
        assert "key2" not in manager._tool_cache

    def test_expired_entries_evicted_on_cache_store(self):
        manager = McpClientManager()
        manager._tool_cache_ttl = 0  # Instant expiry

        manager._tool_cache["old"] = _ToolCacheEntry(
            tools=[], timestamp=time.time() - 10, server_name="Old", tool_count=0
        )

        manager._cache_tools("new", [], "New")
        assert "old" not in manager._tool_cache
        assert "new" in manager._tool_cache


class TestToolCacheStats:
    """Tests for cache statistics."""

    def test_get_stats_empty(self):
        manager = McpClientManager()
        stats = manager.get_tool_cache_stats()
        assert stats["cache_size"] == 0
        assert stats["entries"] == []

    def test_get_stats_with_entries(self):
        manager = McpClientManager()
        manager._tool_cache["key1"] = _ToolCacheEntry(
            tools=[],
            timestamp=time.time(),
            server_name="Server A",
            tool_count=5,
            access_count=3,
        )
        stats = manager.get_tool_cache_stats()
        assert stats["cache_size"] == 1
        assert stats["max_size"] == manager._tool_cache_max_size
        assert stats["ttl_seconds"] == manager._tool_cache_ttl
        assert stats["entries"][0]["server_name"] == "Server A"
        assert stats["entries"][0]["tool_count"] == 5
        assert stats["entries"][0]["access_count"] == 3
        assert stats["entries"][0]["expired"] is False


class TestCleanupIncludesCache:
    """Tests that cleanup_all_sessions also clears the tool cache."""

    @pytest.mark.asyncio
    async def test_cleanup_clears_tool_cache(self):
        manager = McpClientManager()
        manager._tool_cache["key1"] = _ToolCacheEntry(
            tools=[], timestamp=time.time(), server_name="Test", tool_count=0
        )
        assert len(manager._tool_cache) == 1

        await manager.cleanup_all_sessions()
        assert len(manager._tool_cache) == 0
