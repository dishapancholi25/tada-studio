"""Tests for WebSocket connection manager.

Tests the ConnectionManager class which handles WebSocket connections,
message broadcasting, and buffering for connection resilience.
"""

import asyncio
import json
import threading
from unittest.mock import AsyncMock

import pytest

from backend.services.websocket.connection_manager import ConnectionManager


class TestConnectionManager:
    """Test suite for ConnectionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager for each test."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.send_json = AsyncMock()
        ws.accept = AsyncMock()
        return ws

    @pytest.fixture
    def mock_websockets(self):
        """Create multiple mock WebSockets."""
        websockets = []
        for i in range(5):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            ws.send_json = AsyncMock()
            ws.accept = AsyncMock()
            ws.id = i  # For tracking
            websockets.append(ws)
        return websockets

    @pytest.mark.asyncio
    async def test_connect_adds_to_all_connections(self, manager, mock_websocket):
        """Test that connect adds WebSocket to all_connections."""
        await manager.connect(mock_websocket)

        assert mock_websocket in manager.all_connections
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_execution_id(self, manager, mock_websocket):
        """Test connecting with an execution_id."""
        execution_id = "exec-123"
        await manager.connect(mock_websocket, execution_id)

        assert mock_websocket in manager.all_connections
        assert execution_id in manager.active_connections
        assert mock_websocket in manager.active_connections[execution_id]

    @pytest.mark.asyncio
    async def test_connect_multiple_to_same_execution(self, manager, mock_websockets):
        """Test multiple clients connecting to the same execution."""
        execution_id = "exec-123"

        for ws in mock_websockets:
            await manager.connect(ws, execution_id)

        assert len(manager.active_connections[execution_id]) == 5
        assert len(manager.all_connections) == 5

    def test_disconnect_removes_from_all_connections(self, manager, mock_websocket):
        """Test disconnect removes WebSocket from all_connections."""
        manager.all_connections.add(mock_websocket)

        manager.disconnect(mock_websocket)

        assert mock_websocket not in manager.all_connections

    def test_disconnect_with_execution_id(self, manager, mock_websocket):
        """Test disconnect with execution_id removes from execution group."""
        execution_id = "exec-123"
        manager.all_connections.add(mock_websocket)
        manager.active_connections[execution_id] = {mock_websocket}

        manager.disconnect(mock_websocket, execution_id)

        assert mock_websocket not in manager.all_connections
        assert execution_id not in manager.active_connections

    def test_disconnect_keeps_other_connections(self, manager, mock_websockets):
        """Test disconnect only removes the specified WebSocket."""
        execution_id = "exec-123"
        for ws in mock_websockets:
            manager.all_connections.add(ws)
        manager.active_connections[execution_id] = set(mock_websockets)

        # Disconnect first WebSocket
        manager.disconnect(mock_websockets[0], execution_id)

        assert len(manager.active_connections[execution_id]) == 4
        assert mock_websockets[0] not in manager.active_connections[execution_id]
        for ws in mock_websockets[1:]:
            assert ws in manager.active_connections[execution_id]

    @pytest.mark.asyncio
    async def test_send_execution_update_assigns_sequence(
        self, manager, mock_websocket
    ):
        """Test that send_execution_update assigns monotonic sequence numbers."""
        execution_id = "exec-123"
        await manager.connect(mock_websocket, execution_id)

        await manager.send_execution_update(execution_id, "token", {"content": "Hello"})
        await manager.send_execution_update(
            execution_id, "token", {"content": " world"}
        )

        # Check that messages were sent with sequence numbers
        assert mock_websocket.send_text.call_count == 2

        # Parse sent messages to verify sequences
        calls = mock_websocket.send_text.call_args_list
        msg1 = json.loads(calls[0][0][0])
        msg2 = json.loads(calls[1][0][0])

        assert msg1["seq"] == 1
        assert msg2["seq"] == 2

    @pytest.mark.asyncio
    async def test_send_execution_update_buffers_message(self, manager, mock_websocket):
        """Test that messages are buffered for replay."""
        execution_id = "exec-123"
        await manager.connect(mock_websocket, execution_id)

        await manager.send_execution_update(execution_id, "token", {"content": "test"})

        # Check buffer stats
        stats = manager.get_buffer_stats(execution_id)
        assert stats["exists"] is True
        assert stats["size"] == 1
        assert stats["latest_sequence"] == 1

    @pytest.mark.asyncio
    async def test_send_execution_update_buffers_without_connections(self, manager):
        """Test that messages are buffered even without active connections."""
        execution_id = "exec-123"

        # Send without any connections
        await manager.send_execution_update(
            execution_id, "token", {"content": "buffered"}
        )

        # Message should be buffered
        stats = manager.get_buffer_stats(execution_id)
        assert stats["exists"] is True
        assert stats["size"] == 1

    @pytest.mark.asyncio
    async def test_send_to_multiple_connections(self, manager, mock_websockets):
        """Test broadcasting to multiple connections."""
        execution_id = "exec-123"

        for ws in mock_websockets:
            await manager.connect(ws, execution_id)

        await manager.send_execution_update(
            execution_id, "token", {"content": "broadcast"}
        )

        # All connections should receive the message
        for ws in mock_websockets:
            assert ws.send_text.call_count == 1

    @pytest.mark.asyncio
    async def test_send_handles_failed_connection(self, manager, mock_websockets):
        """Test that failed sends don't crash and disconnect failed clients."""
        execution_id = "exec-123"

        for ws in mock_websockets:
            await manager.connect(ws, execution_id)

        # Make one WebSocket fail
        mock_websockets[2].send_text.side_effect = Exception("Connection lost")

        await manager.send_execution_update(execution_id, "token", {"content": "test"})

        # Failed connection should be removed
        assert mock_websockets[2] not in manager.active_connections.get(
            execution_id, set()
        )

    @pytest.mark.asyncio
    async def test_replay_from_sequence(self, manager, mock_websocket):
        """Test replaying messages from a sequence number."""
        execution_id = "exec-123"
        await manager.connect(mock_websocket, execution_id)

        # Send some messages
        for i in range(5):
            await manager.send_execution_update(
                execution_id, "token", {"content": f"msg{i}"}
            )

        # Clear the websocket mock to track replay
        mock_websocket.send_text.reset_mock()
        mock_websocket.send_json.reset_mock()

        # Simulate reconnection - replay from sequence 2
        replayed = await manager.replay_from_sequence(mock_websocket, execution_id, 2)

        assert replayed == 3  # Messages 3, 4, 5
        assert mock_websocket.send_json.call_count == 3

    @pytest.mark.asyncio
    async def test_replay_no_messages_to_replay(self, manager, mock_websocket):
        """Test replay when client is already up to date."""
        execution_id = "exec-123"
        await manager.connect(mock_websocket, execution_id)

        await manager.send_execution_update(execution_id, "token", {"content": "test"})

        mock_websocket.send_json.reset_mock()

        # Replay from the latest sequence - nothing to replay
        replayed = await manager.replay_from_sequence(mock_websocket, execution_id, 1)

        assert replayed == 0
        assert mock_websocket.send_json.call_count == 0

    def test_cleanup_execution_removes_buffer(self, manager):
        """Test cleanup_execution removes buffer and counter."""
        execution_id = "exec-123"

        # Create buffer by getting next sequence
        manager._get_next_sequence(execution_id)
        manager._get_buffer(execution_id)

        assert execution_id in manager.message_buffers
        assert execution_id in manager.sequence_counters

        manager.cleanup_execution(execution_id)

        assert execution_id not in manager.message_buffers
        assert execution_id not in manager.sequence_counters

    def test_get_buffer_stats_nonexistent(self, manager):
        """Test get_buffer_stats for non-existent execution."""
        stats = manager.get_buffer_stats("nonexistent")
        assert stats["exists"] is False

    @pytest.mark.asyncio
    async def test_broadcast_to_all_connections(self, manager, mock_websockets):
        """Test broadcast sends to all connected clients."""
        for ws in mock_websockets:
            await manager.connect(ws)

        await manager.broadcast('{"type": "global_notification"}')

        for ws in mock_websockets:
            ws.send_text.assert_called_once_with('{"type": "global_notification"}')


class TestConnectionManagerRaceConditionFix:
    """Tests specifically for the connection set race condition fix."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager for each test."""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_concurrent_send_and_disconnect_no_crash(self, manager):
        """Test that concurrent send and disconnect don't cause RuntimeError.

        This tests the fix for the race condition where iterating over
        active_connections while disconnecting could cause:
        'RuntimeError: Set changed size during iteration'
        """
        execution_id = "exec-123"
        errors = []

        # Create many mock WebSockets
        websockets = []
        for i in range(20):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            ws.accept = AsyncMock()
            await manager.connect(ws, execution_id)
            websockets.append(ws)

        async def send_messages():
            try:
                for i in range(50):
                    await manager.send_execution_update(
                        execution_id, "token", {"seq": i}
                    )
                    await asyncio.sleep(0.001)
            except RuntimeError as e:
                if "Set changed size during iteration" in str(e):
                    errors.append(e)
                raise

        async def disconnect_connections():
            try:
                for ws in websockets[::2]:  # Disconnect every other
                    manager.disconnect(ws, execution_id)
                    await asyncio.sleep(0.002)
            except Exception as e:
                errors.append(e)

        # Run concurrently
        await asyncio.gather(
            send_messages(),
            disconnect_connections(),
            return_exceptions=True,
        )

        # The key assertion: no "Set changed size during iteration" errors
        race_errors = [
            e for e in errors if "Set changed size during iteration" in str(e)
        ]
        assert len(race_errors) == 0, f"Race condition errors: {race_errors}"

    @pytest.mark.asyncio
    async def test_send_uses_snapshot(self, manager):
        """Verify send_execution_update uses a snapshot of connections."""
        execution_id = "exec-123"

        ws1 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws1.accept = AsyncMock()

        await manager.connect(ws1, execution_id)

        # This should work without issues
        await manager.send_execution_update(execution_id, "token", {"content": "test"})

        assert ws1.send_text.call_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_uses_snapshot(self, manager):
        """Verify broadcast uses a snapshot of all_connections."""
        websockets = []
        for _ in range(5):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            ws.accept = AsyncMock()
            await manager.connect(ws)
            websockets.append(ws)

        await manager.broadcast('{"type": "test"}')

        for ws in websockets:
            assert ws.send_text.call_count == 1

    @pytest.mark.asyncio
    async def test_disconnect_during_iteration_safe(self, manager):
        """Test that disconnect during send is handled safely."""
        execution_id = "exec-123"

        websockets = []
        for i in range(5):
            ws = AsyncMock()
            ws.send_text = AsyncMock()
            ws.accept = AsyncMock()
            await manager.connect(ws, execution_id)
            websockets.append(ws)

        # Make middle websocket fail (triggers disconnect during iteration)
        websockets[2].send_text.side_effect = Exception("Connection closed")

        # This should not raise RuntimeError
        await manager.send_execution_update(execution_id, "token", {"content": "test"})

        # Failed connection should be cleaned up
        remaining = manager.active_connections.get(execution_id, set())
        assert websockets[2] not in remaining


class TestSequenceNumbering:
    """Tests for sequence number management."""

    @pytest.fixture
    def manager(self):
        return ConnectionManager()

    def test_sequence_starts_at_one(self, manager):
        """Test sequence numbers start at 1."""
        execution_id = "exec-123"
        seq = manager._get_next_sequence(execution_id)
        assert seq == 1

    def test_sequence_is_monotonic(self, manager):
        """Test sequence numbers are monotonically increasing."""
        execution_id = "exec-123"
        sequences = [manager._get_next_sequence(execution_id) for _ in range(10)]
        assert sequences == list(range(1, 11))

    def test_sequences_per_execution(self, manager):
        """Test each execution has independent sequence counter."""
        seq1_a = manager._get_next_sequence("exec-1")
        seq2_a = manager._get_next_sequence("exec-2")
        seq1_b = manager._get_next_sequence("exec-1")
        seq2_b = manager._get_next_sequence("exec-2")

        assert seq1_a == 1
        assert seq2_a == 1
        assert seq1_b == 2
        assert seq2_b == 2

    def test_sequence_thread_safety(self, manager):
        """Test sequence numbers are thread-safe."""
        execution_id = "exec-123"
        sequences = []
        errors = []

        def get_sequences(count):
            try:
                for _ in range(count):
                    seq = manager._get_next_sequence(execution_id)
                    sequences.append(seq)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=get_sequences, args=(100,)) for _ in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        # All sequences should be unique
        assert len(sequences) == len(set(sequences))

        # Should go from 1 to 500
        assert sorted(sequences) == list(range(1, 501))


class TestDoSendMethod:
    """Tests for the extracted _do_send method."""

    @pytest.fixture
    def manager(self):
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.accept = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_do_send_sends_to_all_connections(self, manager):
        """Test _do_send sends message to every connection in the list."""
        ws1 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_text = AsyncMock()
        execution_id = "exec-123"

        # Register connections so disconnect can find them
        manager.all_connections.update({ws1, ws2})
        manager.active_connections[execution_id] = {ws1, ws2}

        await manager._do_send([ws1, ws2], '{"test": true}', execution_id, "token", 1)

        ws1.send_text.assert_called_once_with('{"test": true}')
        ws2.send_text.assert_called_once_with('{"test": true}')

    @pytest.mark.asyncio
    async def test_do_send_disconnects_failed_sockets(self, manager):
        """Test _do_send removes connections that raise during send."""
        ws_ok = AsyncMock()
        ws_ok.send_text = AsyncMock()
        ws_fail = AsyncMock()
        ws_fail.send_text = AsyncMock(side_effect=Exception("Connection lost"))
        execution_id = "exec-456"

        manager.all_connections.update({ws_ok, ws_fail})
        manager.active_connections[execution_id] = {ws_ok, ws_fail}

        await manager._do_send([ws_ok, ws_fail], "{}", execution_id, "node_update", 1)

        ws_ok.send_text.assert_called_once()
        assert ws_fail not in manager.active_connections.get(execution_id, set())

    @pytest.mark.asyncio
    async def test_do_send_is_single_path_for_send_execution_update(
        self, manager, mock_websocket
    ):
        """Test that send_execution_update delegates to _do_send (no duplication)."""
        execution_id = "exec-789"
        await manager.connect(mock_websocket, execution_id)

        # Patch _do_send to verify delegation
        original_do_send = manager._do_send
        do_send_calls = []

        async def tracking_do_send(*args):
            do_send_calls.append(args)
            return await original_do_send(*args)

        manager._do_send = tracking_do_send

        await manager.send_execution_update(execution_id, "token", {"content": "hi"})

        assert len(do_send_calls) == 1
        assert do_send_calls[0][2] == execution_id
        assert do_send_calls[0][3] == "token"


class TestCrossLoopSendQueue:
    """Tests for the cross-loop send queue and drain task."""

    @pytest.fixture
    def manager(self):
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_set_main_loop_initializes_queue_and_drain(self, manager):
        """Test that set_main_loop creates the queue and drain task."""
        loop = asyncio.get_running_loop()
        manager.set_main_loop(loop)

        assert manager._main_loop is loop
        assert manager._send_queue is not None
        assert manager._drain_task is not None
        assert not manager._drain_task.done()

        manager.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_cancels_drain_task(self, manager):
        """Test that shutdown cancels the drain task."""
        loop = asyncio.get_running_loop()
        manager.set_main_loop(loop)

        drain_task = manager._drain_task
        manager.shutdown()

        # Give the cancellation a chance to propagate
        await asyncio.sleep(0.01)
        assert drain_task.done()

    @pytest.mark.asyncio
    async def test_drain_processes_queued_items(self, manager):
        """Test that the drain task processes items from the queue."""
        loop = asyncio.get_running_loop()
        manager.set_main_loop(loop)

        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.accept = AsyncMock()
        execution_id = "exec-drain"

        await manager.connect(ws, execution_id)

        # Enqueue a send item directly
        send_item = ([ws], '{"type":"test"}', execution_id, "token", 1)
        manager._send_queue.put_nowait(send_item)

        # Let the drain task process it
        await asyncio.sleep(0.05)

        ws.send_text.assert_called_once_with('{"type":"test"}')
        manager.shutdown()

    @pytest.mark.asyncio
    async def test_drain_preserves_message_order(self, manager):
        """Test that the drain task preserves FIFO ordering."""
        loop = asyncio.get_running_loop()
        manager.set_main_loop(loop)

        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.accept = AsyncMock()
        execution_id = "exec-order"

        await manager.connect(ws, execution_id)

        # Enqueue multiple items
        for i in range(5):
            send_item = ([ws], f'{{"seq":{i}}}', execution_id, "token", i)
            manager._send_queue.put_nowait(send_item)

        # Let the drain task process all items
        await asyncio.sleep(0.1)

        assert ws.send_text.call_count == 5
        calls = [call[0][0] for call in ws.send_text.call_args_list]
        assert calls == [f'{{"seq":{i}}}' for i in range(5)]
        manager.shutdown()

    @pytest.mark.asyncio
    async def test_drain_logs_errors_without_crashing(self, manager):
        """Test that errors in the drain task are logged, not swallowed."""
        loop = asyncio.get_running_loop()
        manager.set_main_loop(loop)

        ws_fail = AsyncMock()
        ws_fail.send_text = AsyncMock(side_effect=Exception("boom"))
        ws_ok = AsyncMock()
        ws_ok.send_text = AsyncMock()
        execution_id = "exec-err"

        manager.all_connections.update({ws_fail, ws_ok})
        manager.active_connections[execution_id] = {ws_fail, ws_ok}

        # Enqueue failing item, then succeeding item
        manager._send_queue.put_nowait(([ws_fail], "{}", execution_id, "token", 1))
        manager._send_queue.put_nowait(([ws_ok], "{}", execution_id, "token", 2))

        # Let the drain task process both
        await asyncio.sleep(0.1)

        # The second send should still succeed despite the first failing
        ws_ok.send_text.assert_called_once()
        manager.shutdown()

    @pytest.mark.asyncio
    async def test_same_loop_skips_queue(self, manager):
        """Test that sends on the same loop go directly to _do_send."""
        loop = asyncio.get_running_loop()
        manager.set_main_loop(loop)

        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.accept = AsyncMock()
        execution_id = "exec-same"

        await manager.connect(ws, execution_id)

        # Since we're on the same loop as _main_loop, this should
        # call _do_send directly, not go through the queue.
        await manager.send_execution_update(
            execution_id, "token", {"content": "direct"}
        )

        # Message should be sent immediately (not deferred)
        ws.send_text.assert_called_once()

        # Queue should be empty
        assert manager._send_queue.qsize() == 0
        manager.shutdown()

    @pytest.mark.asyncio
    async def test_no_main_loop_sends_directly(self, manager):
        """Test that without set_main_loop, sends work normally."""
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.accept = AsyncMock()
        execution_id = "exec-noloop"

        await manager.connect(ws, execution_id)

        # _main_loop is None, so this should go directly to _do_send
        await manager.send_execution_update(execution_id, "token", {"content": "test"})

        ws.send_text.assert_called_once()

    def test_shutdown_noop_without_drain_task(self, manager):
        """Test that shutdown is safe when set_main_loop was never called."""
        # Should not raise
        manager.shutdown()
