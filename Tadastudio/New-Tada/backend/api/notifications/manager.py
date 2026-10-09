"""WebSocket connection manager for real-time notifications."""

import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket
from backend.services.config import get_logger

logger = get_logger(__name__)


class NotificationManager:
    """Manages WebSocket connections for real-time notifications.

    Maintains a mapping of user IDs to their active WebSocket connections,
    allowing targeted notification delivery.
    """

    def __init__(self):
        # Map of user_id -> set of WebSocket connections (user may have multiple tabs)
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str):
        """Register a new WebSocket connection for a user."""
        await websocket.accept()
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = set()
            self._connections[user_id].add(websocket)
        logger.info(f"[Notifications] User {user_id} connected, total connections: {len(self._connections[user_id])}, all users: {list(self._connections.keys())}")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection for a user."""
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].discard(websocket)
                if not self._connections[user_id]:
                    del self._connections[user_id]
        logger.info(f"[Notifications] User {user_id} disconnected")

    async def send_to_user(self, user_id: str, message: dict):
        """Send a notification to all connections of a specific user."""
        async with self._lock:
            connections = self._connections.get(user_id, set()).copy()
            # Try case-insensitive match if exact match not found (email addresses)
            if not connections and user_id:
                user_id_lower = user_id.lower()
                for connected_id, connected_sockets in self._connections.items():
                    if connected_id.lower() == user_id_lower:
                        connections = connected_sockets.copy()
                        logger.info(f"[Notifications] Case-insensitive match: {user_id} -> {connected_id}")
                        break

        logger.info(f"[Notifications] send_to_user called for {user_id}, connections found: {len(connections)}")

        if not connections:
            logger.warning(f"[Notifications] User {user_id} not connected - cannot deliver real-time notification")
            logger.info(f"[Notifications] Currently connected users: {list(self._connections.keys())}")
            return False

        disconnected = []
        sent_count = 0
        for websocket in connections:
            try:
                # Check WebSocket state before sending
                ws_state = getattr(websocket, 'client_state', None) or getattr(websocket, 'application_state', None)
                logger.info(f"[Notifications] WebSocket state for {user_id}: {ws_state}")
                logger.info(f"[Notifications] Sending message to {user_id}: type={message.get('type')}, workflow_id={message.get('workflow_id')}")
                await websocket.send_json(message)
                sent_count += 1
                logger.info(f"[Notifications] Successfully sent WebSocket message to {user_id} (sent: {sent_count})")
            except Exception as e:
                logger.warning(f"[Notifications] Failed to send to {user_id}: {e}, exception type: {type(e).__name__}")
                disconnected.append(websocket)

        # Clean up disconnected sockets
        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    if user_id in self._connections:
                        self._connections[user_id].discard(ws)

        return True

    async def broadcast_to_users(self, user_ids: list, message: dict):
        """Send a notification to multiple users."""
        logger.info(f"[Notifications] Broadcasting to users: {user_ids}, message type: {message.get('type', 'unknown')}")
        tasks = [self.send_to_user(uid, message) for uid in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        delivered = sum(1 for r in results if r is True)
        logger.info(f"[Notifications] Broadcast complete: {delivered}/{len(user_ids)} users received notification")

    def is_user_online(self, user_id: str) -> bool:
        """Check if a user has any active connections."""
        return user_id in self._connections and len(self._connections[user_id]) > 0

    def get_online_user_count(self) -> int:
        """Get the number of users with active connections."""
        return len(self._connections)


# Global notification manager instance
notification_manager = NotificationManager()
