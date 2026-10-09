"""Message buffer for WebSocket connection resilience.

Provides a ring buffer with TTL for storing recent messages per execution,
enabling replay of missed messages after reconnection.
"""

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..config import get_logger


logger = get_logger("websocket.message_buffer")


@dataclass
class BufferedMessage:
    """A buffered WebSocket message with metadata."""

    sequence: int
    timestamp: datetime
    event_type: str
    data: Dict[str, Any]


class MessageBuffer:
    """Ring buffer for recent execution messages with TTL.

    Stores recent WebSocket messages for an execution, allowing replay
    of missed messages when a client reconnects. Uses a fixed-size ring
    buffer to prevent unbounded memory growth.

    Args:
        max_size: Maximum number of messages to buffer (default: 1000)
        ttl_seconds: Time-to-live for messages in seconds (default: 300)

    Example:
        >>> buffer = MessageBuffer(max_size=100, ttl_seconds=60)
        >>> buffer.add(1, "token", {"content": "Hello"})
        >>> buffer.add(2, "token", {"content": " world"})
        >>> missed = buffer.get_since(0)  # Get all messages
        >>> len(missed)
        2
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 900):
        """Initialize the message buffer.

        Args:
            max_size: Maximum number of messages to store
            ttl_seconds: Time-to-live for messages in seconds (default: 15 minutes)
        """
        self.buffer: deque[BufferedMessage] = deque(maxlen=max_size)
        self.ttl = timedelta(seconds=ttl_seconds)
        self._lock = threading.Lock()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

    def add(self, sequence: int, event_type: str, data: Dict[str, Any]) -> None:
        """Add a message to the buffer.

        Messages are automatically evicted when the buffer reaches max_size
        (oldest messages are removed first).

        Args:
            sequence: Monotonic sequence number for ordering
            event_type: Type of the event (e.g., "token", "node_update")
            data: Event data payload
        """
        with self._lock:
            self.buffer.append(
                BufferedMessage(
                    sequence=sequence,
                    timestamp=datetime.now(),
                    event_type=event_type,
                    data=data,
                )
            )

    def get_since(self, sequence: int) -> List[BufferedMessage]:
        """Get all messages with sequence number greater than the given value.

        Filters out messages older than TTL to prevent replaying stale data.

        Args:
            sequence: The last sequence number received by the client

        Returns:
            List of BufferedMessage objects with sequence > given sequence,
            ordered by sequence number (oldest first)
        """
        cutoff = datetime.now() - self.ttl
        with self._lock:
            return [
                msg
                for msg in self.buffer
                if msg.sequence > sequence and msg.timestamp > cutoff
            ]

    def get_latest_sequence(self) -> int:
        """Get the highest sequence number in the buffer.

        Returns:
            The highest sequence number, or 0 if buffer is empty
        """
        with self._lock:
            if not self.buffer:
                return 0
            return self.buffer[-1].sequence

    def size(self) -> int:
        """Get the current number of messages in the buffer.

        Returns:
            Number of messages currently buffered
        """
        with self._lock:
            return len(self.buffer)

    def clear(self) -> None:
        """Clear all messages from the buffer."""
        with self._lock:
            self.buffer.clear()

    def prune_expired(self) -> int:
        """Remove messages older than TTL.

        This is called automatically by get_since(), but can be called
        manually for proactive cleanup.

        Returns:
            Number of messages removed
        """
        cutoff = datetime.now() - self.ttl
        removed = 0
        with self._lock:
            # Create new deque with only valid messages
            valid_messages = [msg for msg in self.buffer if msg.timestamp > cutoff]
            removed = len(self.buffer) - len(valid_messages)
            if removed > 0:
                self.buffer.clear()
                self.buffer.extend(valid_messages)
        return removed
