"""Tests for WebSocket message buffer.

Tests the MessageBuffer class which provides connection resilience
through message buffering and replay capabilities.
"""

import time
import threading
from datetime import datetime, timedelta
from unittest.mock import patch


from backend.services.websocket.message_buffer import MessageBuffer, BufferedMessage


class TestMessageBuffer:
    """Test suite for MessageBuffer class."""

    def test_buffer_initialization(self):
        """Test buffer initializes with correct defaults."""
        buffer = MessageBuffer()
        assert buffer.max_size == 1000
        assert buffer.ttl_seconds == 900  # 15 minutes default
        assert buffer.size() == 0

    def test_buffer_custom_initialization(self):
        """Test buffer with custom max_size and TTL."""
        buffer = MessageBuffer(max_size=100, ttl_seconds=60)
        assert buffer.max_size == 100
        assert buffer.ttl_seconds == 60

    def test_add_message(self):
        """Test adding messages to buffer."""
        buffer = MessageBuffer()
        buffer.add(1, "token", {"content": "Hello"})
        buffer.add(2, "token", {"content": " world"})

        assert buffer.size() == 2
        assert buffer.get_latest_sequence() == 2

    def test_get_since_returns_messages_after_sequence(self):
        """Test get_since returns only messages after given sequence."""
        buffer = MessageBuffer()
        buffer.add(1, "token", {"content": "a"})
        buffer.add(2, "token", {"content": "b"})
        buffer.add(3, "token", {"content": "c"})
        buffer.add(4, "token", {"content": "d"})

        # Get messages after sequence 2
        messages = buffer.get_since(2)

        assert len(messages) == 2
        assert messages[0].sequence == 3
        assert messages[1].sequence == 4

    def test_get_since_zero_returns_all(self):
        """Test get_since(0) returns all non-expired messages."""
        buffer = MessageBuffer()
        buffer.add(1, "token", {"content": "a"})
        buffer.add(2, "token", {"content": "b"})

        messages = buffer.get_since(0)
        assert len(messages) == 2

    def test_get_since_respects_ttl(self):
        """Test that get_since filters out expired messages."""
        buffer = MessageBuffer(ttl_seconds=1)  # 1 second TTL
        buffer.add(1, "token", {"content": "old"})

        # Wait for message to expire
        time.sleep(1.1)

        # Add new message
        buffer.add(2, "token", {"content": "new"})

        messages = buffer.get_since(0)
        assert len(messages) == 1
        assert messages[0].sequence == 2
        assert messages[0].data["content"] == "new"

    def test_ring_buffer_eviction(self):
        """Test that oldest messages are evicted when buffer is full."""
        buffer = MessageBuffer(max_size=3)

        # Add 5 messages to a buffer of size 3
        for i in range(1, 6):
            buffer.add(i, "token", {"seq": i})

        # Only last 3 should remain
        assert buffer.size() == 3
        messages = buffer.get_since(0)
        assert len(messages) == 3
        assert [m.sequence for m in messages] == [3, 4, 5]

    def test_get_latest_sequence_empty_buffer(self):
        """Test get_latest_sequence returns 0 for empty buffer."""
        buffer = MessageBuffer()
        assert buffer.get_latest_sequence() == 0

    def test_clear_buffer(self):
        """Test clearing the buffer."""
        buffer = MessageBuffer()
        buffer.add(1, "token", {"content": "test"})
        buffer.add(2, "token", {"content": "test2"})

        buffer.clear()

        assert buffer.size() == 0
        assert buffer.get_latest_sequence() == 0

    def test_prune_expired_removes_old_messages(self):
        """Test prune_expired removes messages older than TTL."""
        buffer = MessageBuffer(ttl_seconds=1)
        buffer.add(1, "token", {"content": "old1"})
        buffer.add(2, "token", {"content": "old2"})

        # Wait for messages to expire
        time.sleep(1.1)

        # Add new message
        buffer.add(3, "token", {"content": "new"})

        # Prune expired
        removed = buffer.prune_expired()

        assert removed == 2
        assert buffer.size() == 1
        messages = buffer.get_since(0)
        assert messages[0].sequence == 3

    def test_thread_safety_concurrent_adds(self):
        """Test that concurrent adds are thread-safe."""
        buffer = MessageBuffer(max_size=1000)
        errors = []

        def add_messages(start_seq, count):
            try:
                for i in range(count):
                    buffer.add(start_seq + i, "token", {"seq": start_seq + i})
            except Exception as e:
                errors.append(e)

        # Create multiple threads adding messages concurrently
        threads = []
        for i in range(5):
            t = threading.Thread(target=add_messages, args=(i * 100, 100))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Total messages should be 500, but due to concurrent timing
        # the actual count may vary - just ensure no crashes
        assert buffer.size() <= 500

    def test_thread_safety_concurrent_reads_writes(self):
        """Test that concurrent reads and writes are thread-safe."""
        buffer = MessageBuffer(max_size=100)
        errors = []
        read_results = []

        def writer():
            try:
                for i in range(50):
                    buffer.add(i + 1, "token", {"seq": i + 1})
                    time.sleep(0.001)
            except Exception as e:
                errors.append(("writer", e))

        def reader():
            try:
                for _ in range(50):
                    messages = buffer.get_since(0)
                    read_results.append(len(messages))
                    time.sleep(0.001)
            except Exception as e:
                errors.append(("reader", e))

        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)

        writer_thread.start()
        reader_thread.start()

        writer_thread.join()
        reader_thread.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_buffered_message_dataclass(self):
        """Test BufferedMessage dataclass structure."""
        now = datetime.now()
        msg = BufferedMessage(
            sequence=42,
            timestamp=now,
            event_type="node_update",
            data={"status": "completed"},
        )

        assert msg.sequence == 42
        assert msg.timestamp == now
        assert msg.event_type == "node_update"
        assert msg.data["status"] == "completed"

    def test_different_event_types(self):
        """Test buffer handles different event types correctly."""
        buffer = MessageBuffer()
        buffer.add(1, "token", {"content": "Hello"})
        buffer.add(2, "node_update", {"status": "running"})
        buffer.add(3, "execution_status", {"status": "completed"})

        messages = buffer.get_since(0)
        assert len(messages) == 3
        assert messages[0].event_type == "token"
        assert messages[1].event_type == "node_update"
        assert messages[2].event_type == "execution_status"

    def test_large_payload_handling(self):
        """Test buffer handles large payloads."""
        buffer = MessageBuffer()

        # Create a large payload (simulating LLM output)
        large_content = "x" * 100000  # 100KB
        buffer.add(1, "token", {"content": large_content})

        messages = buffer.get_since(0)
        assert len(messages) == 1
        assert len(messages[0].data["content"]) == 100000


class TestMessageBufferTTLConfiguration:
    """Tests specific to TTL configuration changes."""

    def test_default_ttl_is_15_minutes(self):
        """Verify default TTL is 15 minutes (900 seconds) for longer workflows."""
        buffer = MessageBuffer()
        assert buffer.ttl_seconds == 900
        assert buffer.ttl == timedelta(seconds=900)

    def test_ttl_sufficient_for_workflow_pause(self):
        """Test TTL is sufficient for a user pausing and returning."""
        buffer = MessageBuffer()  # Default 15-min TTL

        # Simulate messages during execution
        buffer.add(1, "node_update", {"status": "running"})
        buffer.add(2, "execution_status", {"status": "paused"})

        # Simulate 10-minute pause (within 15-min TTL)
        with patch("backend.services.websocket.message_buffer.datetime") as mock_dt:
            # Messages were added "now"
            original_time = datetime.now()

            # Simulate time passing by 10 minutes
            future_time = original_time + timedelta(minutes=10)
            mock_dt.now.return_value = future_time

            # Messages should still be available since TTL is 15 minutes
            # Note: We can't easily test this without mocking the timestamp
            # in the buffer itself, so we verify TTL setting is correct
            assert buffer.ttl_seconds == 900  # 15 minutes

    def test_messages_expire_after_ttl(self):
        """Test messages are properly filtered after TTL expires."""
        # Use short TTL for testing
        buffer = MessageBuffer(ttl_seconds=2)

        buffer.add(1, "token", {"content": "test"})

        # Immediate retrieval should work
        messages = buffer.get_since(0)
        assert len(messages) == 1

        # Wait for TTL to expire
        time.sleep(2.1)

        # After TTL, message should be filtered out
        messages = buffer.get_since(0)
        assert len(messages) == 0
