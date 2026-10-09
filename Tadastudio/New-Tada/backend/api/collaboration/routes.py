"""WebSocket endpoint for real-time collaboration using Yjs/pycrdt."""

import asyncio
import re
import traceback
from builtins import BaseExceptionGroup
from datetime import datetime, timedelta
from typing import Dict, Optional, Set

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pycrdt.websocket import WebsocketServer
from pycrdt.websocket.websocket_server import Channel

from backend.api.auth.dependencies import (
    _extract_websocket_user_email,
    _get_websocket_auth_header_names,
    require_admin,
)

from ...services.config import get_logger

logger = get_logger("collaboration")

router = APIRouter(prefix="/api/collab", tags=["collaboration"])

# Configuration
MAX_CONNECTIONS_PER_ROOM = 50
MAX_CONNECTIONS_PER_USER_PER_ROOM = 5  # Prevents one user from exhausting room limit
MAX_TOTAL_CONNECTIONS = 500
ROOM_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]{1,128}\Z')
STALE_CONNECTION_TIMEOUT = timedelta(minutes=30)  # Consider connection stale after 30 min of no activity


def _format_exception_trace(exc: BaseException) -> str:
    """Format an exception with traceback, including ExceptionGroup members."""
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def _log_exception_details(context: str, exc: BaseException) -> None:
    """Log full exception details so TaskGroup sub-errors are visible in pod logs."""
    logger.error("%s: %s\n%s", context, exc, _format_exception_trace(exc))

    if isinstance(exc, BaseExceptionGroup):
        for index, sub_exc in enumerate(exc.exceptions, start=1):
            logger.error(
                "%s sub-exception %d/%d: %s\n%s",
                context,
                index,
                len(exc.exceptions),
                sub_exc,
                _format_exception_trace(sub_exc),
            )


def _pycrdt_exception_handler(exc: Exception, _pycrdt_logger) -> bool:
    """Log pycrdt internal exceptions but let pycrdt re-raise them."""
    _log_exception_details("pycrdt WebsocketServer exception", exc)
    return False


class WebSocketAdapter(Channel):
    """Adapter to make FastAPI WebSocket work with pycrdt-websocket."""

    def __init__(self, websocket: WebSocket, path: str):
        self._websocket = websocket
        self._path = path

    @property
    def path(self) -> str:
        return self._path

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            return await self.recv()
        except StopAsyncIteration:
            raise
        except WebSocketDisconnect as exc:
            raise StopAsyncIteration() from exc

    async def send(self, message: bytes) -> None:
        try:
            await self._websocket.send_bytes(message)
        except Exception as exc:
            _log_exception_details(f"Failed sending pycrdt message to {self._path}", exc)
            raise

    async def recv(self) -> bytes:
        try:
            message = await self._websocket.receive()
        except WebSocketDisconnect as exc:
            raise StopAsyncIteration() from exc

        message_type = message.get("type")
        if message_type == "websocket.receive":
            data = message.get("bytes")
            if data is not None:
                return data

            text = message.get("text")
            if text is not None:
                raise TypeError(
                    "Collaboration websocket expected a binary Yjs frame but "
                    f"received a text frame ({len(text)} chars)"
                )

            raise TypeError(
                "Collaboration websocket receive message had no bytes/text payload; "
                f"keys={sorted(message.keys())}"
            )

        if message_type == "websocket.disconnect":
            raise StopAsyncIteration()

        raise RuntimeError(f"Unexpected ASGI websocket message type: {message_type}")


class CollaborationManager:
    """Manages collaboration rooms and their Yjs documents."""

    def __init__(self):
        self._websocket_server: WebsocketServer | None = None
        self._started = False
        self._server_task: asyncio.Task | None = None
        self._init_lock = asyncio.Lock()
        self._room_connections: Dict[str, Set[WebSocket]] = {}
        self._total_connections = 0
        # Track user connections: {room_name: {user_email: set of websockets}}
        self._user_connections: Dict[str, Dict[str, Set[WebSocket]]] = {}
        # Track connection metadata: {websocket: {user, room, connected_at, last_activity}}
        self._connection_metadata: Dict[WebSocket, Dict] = {}
        # Cleanup task reference
        self._cleanup_task: asyncio.Task | None = None

    async def _ensure_started(self):
        """Lazily start the WebSocket server on first connection (thread-safe)."""
        if self._started:
            return

        async with self._init_lock:
            if self._started:
                return
            # rooms_ready=True ensures Yjs document observers activate immediately for live sync
            self._websocket_server = WebsocketServer(
                rooms_ready=True,
                auto_clean_rooms=True,
                exception_handler=_pycrdt_exception_handler,
                log=logger,
            )
            self._server_task = asyncio.create_task(self._websocket_server.start())
            await self._websocket_server.started.wait()
            self._started = True
            logger.info("Collaboration server started (lazy init)")

    def _can_connect(self, room_name: str, user_email: str) -> tuple[bool, str]:
        """Check if a new connection is allowed."""
        if self._total_connections >= MAX_TOTAL_CONNECTIONS:
            return False, "Server at maximum capacity"

        room_conns = len(self._room_connections.get(room_name, set()))
        if room_conns >= MAX_CONNECTIONS_PER_ROOM:
            return False, f"Room '{room_name}' at maximum capacity"

        # Check per-user limit
        user_conns = len(
            self._user_connections.get(room_name, {}).get(user_email, set())
        )
        if user_conns >= MAX_CONNECTIONS_PER_USER_PER_ROOM:
            return False, f"Too many tabs open for this room (max {MAX_CONNECTIONS_PER_USER_PER_ROOM})"

        return True, ""

    def _track_connection(self, websocket: WebSocket, room_name: str, user_email: str):
        """Track a new connection."""
        now = datetime.utcnow()

        # Track room connections
        if room_name not in self._room_connections:
            self._room_connections[room_name] = set()
        self._room_connections[room_name].add(websocket)

        # Track user connections
        if room_name not in self._user_connections:
            self._user_connections[room_name] = {}
        if user_email not in self._user_connections[room_name]:
            self._user_connections[room_name][user_email] = set()
        self._user_connections[room_name][user_email].add(websocket)

        # Track connection metadata
        self._connection_metadata[websocket] = {
            "user": user_email,
            "room": room_name,
            "connected_at": now,
            "last_activity": now,
        }

        self._total_connections += 1

        user_tabs = len(self._user_connections[room_name][user_email])
        unique_users = len(self._user_connections[room_name])
        logger.info(
            f"Connection added: room='{room_name}', user='{user_email}', "
            f"user_tabs={user_tabs}, unique_users={unique_users}, total={self._total_connections}"
        )

    def _untrack_connection(self, websocket: WebSocket, room_name: str, user_email: str):
        """Remove connection tracking."""
        # Untrack room connection
        if room_name in self._room_connections:
            self._room_connections[room_name].discard(websocket)
            if not self._room_connections[room_name]:
                del self._room_connections[room_name]

        # Untrack user connection
        if room_name in self._user_connections:
            if user_email in self._user_connections[room_name]:
                self._user_connections[room_name][user_email].discard(websocket)
                if not self._user_connections[room_name][user_email]:
                    del self._user_connections[room_name][user_email]
            if not self._user_connections[room_name]:
                del self._user_connections[room_name]

        # Remove metadata
        self._connection_metadata.pop(websocket, None)

        self._total_connections = max(0, self._total_connections - 1)
        logger.info(
            f"Connection removed: room='{room_name}', user='{user_email}', "
            f"total={self._total_connections}"
        )

    def update_activity(self, websocket: WebSocket):
        """Update last activity timestamp for a connection."""
        if websocket in self._connection_metadata:
            self._connection_metadata[websocket]["last_activity"] = datetime.utcnow()

    def get_stats(self) -> Dict:
        """Get connection statistics."""
        now = datetime.utcnow()
        room_stats = {}

        for room, conns in self._room_connections.items():
            users_in_room = self._user_connections.get(room, {})

            # Calculate connection health
            active_count = 0
            stale_count = 0
            for ws in conns:
                meta = self._connection_metadata.get(ws, {})
                last_activity = meta.get("last_activity", now)
                if now - last_activity > STALE_CONNECTION_TIMEOUT:
                    stale_count += 1
                else:
                    active_count += 1

            room_stats[room] = {
                "total_connections": len(conns),
                "active_connections": active_count,
                "stale_connections": stale_count,
                "unique_users": len(users_in_room),
                "users": {
                    user: len(ws_set) for user, ws_set in users_in_room.items()
                }
            }

        return {
            "total_connections": self._total_connections,
            "total_rooms": len(self._room_connections),
            "server_started": self._started,
            "rooms": room_stats
        }

    async def serve(self, websocket: WebSocket, room_name: str, user_email: str):
        """Handle a WebSocket connection for a collaboration room."""
        await self._ensure_started()

        # Check connection limits (including per-user limit)
        can_connect, reason = self._can_connect(room_name, user_email)
        if not can_connect:
            logger.warning(f"Connection rejected for room '{room_name}', user '{user_email}': {reason}")
            await websocket.close(code=4029, reason=reason)
            return

        await websocket.accept()
        self._track_connection(websocket, room_name, user_email)

        ws_adapter = WebSocketAdapter(websocket, f"/{room_name}")

        try:
            await self._websocket_server.serve(ws_adapter)
        except WebSocketDisconnect:
            logger.info(f"User '{user_email}' disconnected from room: {room_name}")
        except Exception as e:
            _log_exception_details(
                f"WebSocket error in room '{room_name}' for user '{user_email}'",
                e,
            )
        finally:
            self._untrack_connection(websocket, room_name, user_email)


# Global collaboration manager instance
collab_manager = CollaborationManager()


def _validate_room_name(room_name: str) -> tuple[bool, str]:
    """Validate room name format."""
    if not room_name:
        return False, "Room name is required"
    if not ROOM_NAME_PATTERN.match(room_name):
        return False, "Invalid room name format (alphanumeric, underscore, hyphen only, max 128 chars)"
    return True, ""


async def _get_user_from_headers(websocket: WebSocket) -> Optional[str]:
    """Extract user email from nginx-forwarded headers."""
    return _extract_websocket_user_email(websocket)


async def _check_room_access(user_email: str, room_name: str) -> bool:
    """
    Check if user has access to the room (workflow).
    Room names are typically workflow IDs or names.
    """
    from backend.models import User, Workflow, WorkflowMembership
    from backend.services.database import get_db

    try:
        workflow_identifiers = {room_name}
        if room_name.startswith("workflow-"):
            workflow_identifiers.add(room_name.removeprefix("workflow-"))

        with get_db() as db:
            # Room name could be "workflow-{id}", a raw workflow ID, or a name.
            workflow = db.query(Workflow).filter(
                (Workflow.id.in_(workflow_identifiers))
                | (Workflow.name.in_(workflow_identifiers))
            ).first()

            if not workflow:
                # Preserve ad-hoc rooms for local/dev collaboration scenarios.
                logger.debug(f"Room '{room_name}' not found as workflow, allowing access")
                return True

            user_ids = {user_email}
            user = db.query(User).filter(
                (User.email == user_email) | (User.id == user_email)
            ).first()
            if user:
                user_ids.add(user.id)
                if user.email:
                    user_ids.add(user.email)

            # Check if user owns or has access to the workflow
            if workflow.created_by_user_id in user_ids:
                return True

            membership = db.query(WorkflowMembership.id).filter(
                WorkflowMembership.workflow_id == workflow.id,
                WorkflowMembership.user_id.in_(user_ids),
            ).first()
            if membership:
                return True

            logger.warning(
                f"User '{user_email}' denied collaboration access to workflow '{workflow.id}'"
            )
            return False

    except Exception as e:
        logger.error(f"Error checking room access: {e}")
        return False


@router.websocket("/{room_name}")
async def collaboration_websocket(
    websocket: WebSocket,
    room_name: str,
    token: Optional[str] = Query(None, description="Auth token for WebSocket"),
    test_user: Optional[str] = Query(None, description="Test user email (only works with SKIP_AUTH=true)")
):
    """
    WebSocket endpoint for real-time collaboration.

    Connect to: ws://localhost:8000/api/collab/{workflow-name}

    Uses Yjs CRDT protocol for conflict-free syncing between clients.

    Authentication is handled by nginx + oauth2-proxy in production.
    For local development with SKIP_AUTH=true, authentication is bypassed.

    Local Testing with Multiple Users:
        ws://localhost:8000/api/collab/my-room?test_user=alice@test.com
        ws://localhost:8000/api/collab/my-room?test_user=bob@test.com
    """
    import os
    SKIP_AUTH = os.getenv("SKIP_AUTH", "false").lower() in {"1", "true", "yes"}

    # Validate room name
    valid, error = _validate_room_name(room_name)
    if not valid:
        logger.warning(f"Invalid room name rejected: {room_name}")
        await websocket.close(code=4000, reason=error)
        return

    # Get user from headers (set by nginx after oauth2-proxy auth)
    user_email = await _get_user_from_headers(websocket)

    if not user_email:
        if SKIP_AUTH:
            # Allow test_user override in dev mode
            if test_user:
                user_email = test_user
                logger.info(f"SKIP_AUTH: Using test user '{user_email}' for collaboration")
            else:
                user_email = os.getenv("DEV_USER_EMAIL", "dev@localhost")
                logger.debug(f"SKIP_AUTH: Using default dev user '{user_email}' for collaboration")
        else:
            logger.warning(
                "Unauthorized WebSocket connection attempt to room '%s'; auth_header_names=%s",
                room_name,
                _get_websocket_auth_header_names(websocket),
            )
            await websocket.close(code=4001, reason="Unauthorized")
            return

    # Check room access
    has_access = await _check_room_access(user_email, room_name)
    if not has_access:
        logger.warning(f"Access denied for user '{user_email}' to room: {room_name}")
        await websocket.close(code=4003, reason="Access denied to this room")
        return

    await collab_manager.serve(websocket, room_name, user_email)


@router.get("/stats", dependencies=[Depends(require_admin)])
async def get_collaboration_stats():
    """Get current collaboration connection statistics."""
    return collab_manager.get_stats()
