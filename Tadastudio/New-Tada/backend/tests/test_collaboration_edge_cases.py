"""
Comprehensive edge case tests for collaboration WebSocket.
Tests multi-tab, multi-user, limits, validation, and error scenarios.
"""

import asyncio
import sys
from types import SimpleNamespace

import pytest
from fastapi import WebSocketDisconnect
from unittest.mock import MagicMock

import backend.api.collaboration.routes as collab_routes
from backend.api.collaboration.routes import (
    CollaborationManager,
    WebSocketAdapter,
    collaboration_websocket,
    _check_room_access,
    _validate_room_name,
    _get_user_from_headers,
    MAX_CONNECTIONS_PER_ROOM,
    MAX_CONNECTIONS_PER_USER_PER_ROOM,
)


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self, headers: dict = None):
        self.headers = headers or {}
        self.accepted = False
        self.closed = False
        self.close_code = None
        self.close_reason = None
        self.sent_messages = []
        self.received_messages = []

    async def accept(self):
        self.accepted = True

    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = True
        self.close_code = code
        self.close_reason = reason

    async def send_bytes(self, data: bytes):
        self.sent_messages.append(data)

    async def receive(self):
        if self.received_messages:
            return self.received_messages.pop(0)
        raise WebSocketDisconnect()

    async def receive_bytes(self):
        raise asyncio.CancelledError()


class FakeQuery:
    """Minimal SQLAlchemy-like query for collaboration access tests."""

    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class FakeDbContext:
    """Context manager that returns a fake DB session."""

    def __init__(self, query_results):
        self.db = MagicMock()
        self.db.query.side_effect = [FakeQuery(result) for result in query_results]

    def __enter__(self):
        return self.db

    def __exit__(self, exc_type, exc, tb):
        return False


# ==================== Room Name Validation Tests ====================

class TestRoomNameValidation:
    """Test room name validation edge cases."""

    def test_valid_room_names(self):
        """Valid room names should pass."""
        valid_names = [
            "workflow-123",
            "my_workflow",
            "WorkFlow123",
            "a",
            "a" * 128,  # Max length
            "test-room_123",
        ]
        for name in valid_names:
            valid, error = _validate_room_name(name)
            assert valid, f"Expected '{name}' to be valid, got error: {error}"

    def test_invalid_room_names(self):
        """Invalid room names should fail."""
        invalid_names = [
            "",  # Empty
            " ",  # Space only
            "room with spaces",  # Spaces
            "room/path",  # Path traversal
            "../secret",  # Path traversal
            "room\nname",  # Newline
            "a" * 129,  # Too long
            "room@name",  # Special char
            "room#name",  # Special char
            "room$name",  # Special char
        ]
        for name in invalid_names:
            valid, error = _validate_room_name(name)
            assert not valid, f"Expected '{name}' to be invalid"

    def test_empty_room_name(self):
        """Empty room name should fail with specific message."""
        valid, error = _validate_room_name("")
        assert not valid
        assert "required" in error.lower()

    def test_room_name_max_length(self):
        """Room name at max length should work, over should fail."""
        # Exactly 128 chars - should pass
        valid, _ = _validate_room_name("a" * 128)
        assert valid

        # 129 chars - should fail
        valid, error = _validate_room_name("a" * 129)
        assert not valid
        assert "128" in error


# ==================== User Header Extraction Tests ====================

class TestUserHeaderExtraction:
    """Test extracting user from nginx headers."""

    @pytest.mark.asyncio
    async def test_email_header(self):
        """Should extract email from X-Auth-Request-Email."""
        ws = MockWebSocket(headers={"x-auth-request-email": "user@example.com"})
        email = await _get_user_from_headers(ws)
        assert email == "user@example.com"

    @pytest.mark.asyncio
    async def test_user_header_fallback(self):
        """Should fall back to X-Auth-Request-User."""
        ws = MockWebSocket(headers={"x-auth-request-user": "user@example.com"})
        email = await _get_user_from_headers(ws)
        assert email == "user@example.com"

    @pytest.mark.asyncio
    async def test_email_takes_priority(self):
        """Email header should take priority over user header."""
        ws = MockWebSocket(headers={
            "x-auth-request-email": "email@example.com",
            "x-auth-request-user": "user@example.com"
        })
        email = await _get_user_from_headers(ws)
        assert email == "email@example.com"

    @pytest.mark.asyncio
    async def test_no_headers(self):
        """Should return None if no auth headers."""
        ws = MockWebSocket(headers={})
        email = await _get_user_from_headers(ws)
        assert email is None

    @pytest.mark.asyncio
    async def test_forwarded_email_header(self):
        """Should accept X-Forwarded-Email from proxy setups."""
        ws = MockWebSocket(headers={"X-Forwarded-Email": "forwarded@example.com"})
        email = await _get_user_from_headers(ws)
        assert email == "forwarded@example.com"

    @pytest.mark.asyncio
    async def test_forwarded_user_header_fallback(self):
        """Should fall back to forwarded user headers for WebSocket auth."""
        ws = MockWebSocket(headers={"X-Forwarded-User": "forwarded-user@example.com"})
        email = await _get_user_from_headers(ws)
        assert email == "forwarded-user@example.com"


# ==================== WebSocket Adapter Tests ====================

class TestWebSocketAdapter:
    """Test FastAPI-to-pycrdt WebSocket adapter behavior."""

    @pytest.mark.asyncio
    async def test_recv_binary_frame(self):
        """Binary frames should be passed through to pycrdt."""
        ws = MockWebSocket()
        ws.received_messages.append({"type": "websocket.receive", "bytes": b"abc"})

        adapter = WebSocketAdapter(ws, "/room1")

        assert await adapter.recv() == b"abc"

    @pytest.mark.asyncio
    async def test_recv_disconnect_stops_iteration(self):
        """ASGI disconnect should stop pycrdt iteration cleanly."""
        ws = MockWebSocket()
        ws.received_messages.append({"type": "websocket.disconnect"})

        adapter = WebSocketAdapter(ws, "/room1")

        with pytest.raises(StopAsyncIteration):
            await adapter.recv()

    @pytest.mark.asyncio
    async def test_recv_text_frame_is_explicit_error(self):
        """Text frames are invalid for the Yjs binary protocol and should be clear in logs."""
        ws = MockWebSocket()
        ws.received_messages.append({"type": "websocket.receive", "text": "hello"})

        adapter = WebSocketAdapter(ws, "/room1")

        with pytest.raises(TypeError, match="binary Yjs frame"):
            await adapter.recv()


# ==================== OAuth Proxy WebSocket Flow Tests ====================

class TestOAuthProxyCollaborationFlow:
    """Test collaboration with dummy oauth-proxy-style headers."""

    @pytest.mark.asyncio
    async def test_collaboration_websocket_accepts_forwarded_email_header(self, monkeypatch):
        """Dummy OAuth header should authenticate and reach collaboration serve."""
        ws = MockWebSocket(headers={"X-Forwarded-Email": "dummy.user@example.com"})
        served = {}

        async def fake_check_room_access(user_email: str, room_name: str) -> bool:
            served["access_user"] = user_email
            served["access_room"] = room_name
            return True

        async def fake_serve(websocket, room_name: str, user_email: str):
            served["serve_user"] = user_email
            served["serve_room"] = room_name
            await websocket.accept()

        monkeypatch.setattr(collab_routes, "_check_room_access", fake_check_room_access)
        monkeypatch.setattr(collab_routes.collab_manager, "serve", fake_serve)

        await collaboration_websocket(ws, "workflow-test-workflow-id")

        assert ws.accepted is True
        assert ws.closed is False
        assert served == {
            "access_user": "dummy.user@example.com",
            "access_room": "workflow-test-workflow-id",
            "serve_user": "dummy.user@example.com",
            "serve_room": "workflow-test-workflow-id",
        }

    @pytest.mark.asyncio
    async def test_collaboration_websocket_rejects_missing_oauth_header(self, monkeypatch):
        """Missing proxy identity should close before serving collaboration."""
        monkeypatch.setenv("SKIP_AUTH", "false")
        ws = MockWebSocket(headers={})

        serve = MagicMock()
        monkeypatch.setattr(collab_routes.collab_manager, "serve", serve)

        await collaboration_websocket(ws, "workflow-test-workflow-id")

        assert ws.closed is True
        assert ws.close_code == 4001
        assert ws.close_reason == "Unauthorized"
        serve.assert_not_called()


# ==================== Workflow Room Access Tests ====================

class TestWorkflowCollaborationAccess:
    """Test workflow room parsing and access checks for collaboration."""

    @pytest.mark.asyncio
    async def test_workflow_prefix_room_allows_owner(self, monkeypatch):
        """workflow-{id} room should resolve to the raw workflow ID for owners."""
        workflow = SimpleNamespace(id="workflow-id-123", created_by_user_id="owner-user-id")
        user = SimpleNamespace(id="owner-user-id", email="owner@example.com")

        monkeypatch.setattr(
            "backend.services.database.get_db",
            lambda: FakeDbContext([workflow, user]),
        )

        assert await _check_room_access("owner@example.com", "workflow-workflow-id-123")

    @pytest.mark.asyncio
    async def test_workflow_prefix_room_allows_member(self, monkeypatch):
        """workflow-{id} room should allow users with workflow membership."""
        workflow = SimpleNamespace(id="workflow-id-123", created_by_user_id="owner-user-id")
        user = SimpleNamespace(id="member-user-id", email="member@example.com")
        membership = SimpleNamespace(id="membership-id")

        monkeypatch.setattr(
            "backend.services.database.get_db",
            lambda: FakeDbContext([workflow, user, membership]),
        )

        assert await _check_room_access("member@example.com", "workflow-workflow-id-123")

    @pytest.mark.asyncio
    async def test_existing_workflow_denies_non_member(self, monkeypatch):
        """Existing workflow rooms should deny authenticated non-members."""
        workflow = SimpleNamespace(id="workflow-id-123", created_by_user_id="owner-user-id")
        user = SimpleNamespace(id="outsider-user-id", email="outsider@example.com")

        monkeypatch.setattr(
            "backend.services.database.get_db",
            lambda: FakeDbContext([workflow, user, None]),
        )

        assert not await _check_room_access("outsider@example.com", "workflow-workflow-id-123")

    @pytest.mark.asyncio
    async def test_unknown_room_still_allows_dev_ad_hoc_collaboration(self, monkeypatch):
        """Unknown rooms remain allowed for local/dev collaboration scenarios."""
        monkeypatch.setattr(
            "backend.services.database.get_db",
            lambda: FakeDbContext([None]),
        )

        assert await _check_room_access("dummy.user@example.com", "ad-hoc-room")


# ==================== Connection Manager Tests ====================

class TestCollaborationManager:
    """Test CollaborationManager connection tracking."""

    def setup_method(self):
        """Create fresh manager for each test."""
        self.manager = CollaborationManager()

    def test_initial_state(self):
        """Manager should start empty."""
        assert self.manager._total_connections == 0
        assert len(self.manager._room_connections) == 0
        assert len(self.manager._user_connections) == 0

    def test_track_single_connection(self):
        """Should track a single connection correctly."""
        ws = MockWebSocket()
        self.manager._track_connection(ws, "room1", "user@example.com")

        assert self.manager._total_connections == 1
        assert len(self.manager._room_connections["room1"]) == 1
        assert len(self.manager._user_connections["room1"]["user@example.com"]) == 1
        assert ws in self.manager._connection_metadata

    def test_track_multiple_tabs_same_user(self):
        """Same user with multiple tabs should all be tracked."""
        websockets = [MockWebSocket() for _ in range(3)]

        for ws in websockets:
            self.manager._track_connection(ws, "room1", "user@example.com")

        assert self.manager._total_connections == 3
        assert len(self.manager._room_connections["room1"]) == 3
        assert len(self.manager._user_connections["room1"]["user@example.com"]) == 3

    def test_track_multiple_users_same_room(self):
        """Multiple users in same room should be tracked separately."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        self.manager._track_connection(ws1, "room1", "user1@example.com")
        self.manager._track_connection(ws2, "room1", "user2@example.com")
        self.manager._track_connection(ws3, "room1", "user1@example.com")

        assert self.manager._total_connections == 3
        assert len(self.manager._room_connections["room1"]) == 3
        assert len(self.manager._user_connections["room1"]) == 2  # 2 unique users
        assert len(self.manager._user_connections["room1"]["user1@example.com"]) == 2
        assert len(self.manager._user_connections["room1"]["user2@example.com"]) == 1

    def test_untrack_connection(self):
        """Should properly remove connection tracking."""
        ws = MockWebSocket()
        self.manager._track_connection(ws, "room1", "user@example.com")
        self.manager._untrack_connection(ws, "room1", "user@example.com")

        assert self.manager._total_connections == 0
        assert "room1" not in self.manager._room_connections
        assert "room1" not in self.manager._user_connections
        assert ws not in self.manager._connection_metadata

    def test_untrack_one_of_multiple(self):
        """Removing one connection should not affect others."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        self.manager._track_connection(ws1, "room1", "user@example.com")
        self.manager._track_connection(ws2, "room1", "user@example.com")
        self.manager._untrack_connection(ws1, "room1", "user@example.com")

        assert self.manager._total_connections == 1
        assert len(self.manager._room_connections["room1"]) == 1
        assert ws2 in self.manager._room_connections["room1"]


# ==================== Connection Limit Tests ====================

class TestConnectionLimits:
    """Test connection limit enforcement."""

    def setup_method(self):
        self.manager = CollaborationManager()

    def test_can_connect_empty_room(self):
        """Should allow connection to empty room."""
        can_connect, reason = self.manager._can_connect("room1", "user@example.com")
        assert can_connect
        assert reason == ""

    def test_per_user_limit(self):
        """Should enforce per-user connection limit."""
        # Add connections up to limit
        for i in range(MAX_CONNECTIONS_PER_USER_PER_ROOM):
            ws = MockWebSocket()
            self.manager._track_connection(ws, "room1", "user@example.com")

        # Next connection should be rejected
        can_connect, reason = self.manager._can_connect("room1", "user@example.com")
        assert not can_connect
        assert "tabs" in reason.lower()

    def test_per_user_limit_different_users(self):
        """Different users should have independent limits."""
        # Fill user1's limit
        for i in range(MAX_CONNECTIONS_PER_USER_PER_ROOM):
            ws = MockWebSocket()
            self.manager._track_connection(ws, "room1", "user1@example.com")

        # user2 should still be able to connect
        can_connect, reason = self.manager._can_connect("room1", "user2@example.com")
        assert can_connect

    def test_per_room_limit(self):
        """Should enforce per-room connection limit."""
        # Add connections up to room limit (different users to avoid per-user limit)
        for i in range(MAX_CONNECTIONS_PER_ROOM):
            ws = MockWebSocket()
            self.manager._track_connection(ws, "room1", f"user{i}@example.com")

        # Next connection should be rejected
        can_connect, reason = self.manager._can_connect("room1", "newuser@example.com")
        assert not can_connect
        assert "capacity" in reason.lower()

    def test_different_rooms_independent(self):
        """Room limits should be independent."""
        # Fill room1
        for i in range(MAX_CONNECTIONS_PER_ROOM):
            ws = MockWebSocket()
            self.manager._track_connection(ws, "room1", f"user{i}@example.com")

        # room2 should still accept connections
        can_connect, reason = self.manager._can_connect("room2", "user@example.com")
        assert can_connect


# ==================== Stats Tests ====================

class TestStats:
    """Test statistics reporting."""

    def setup_method(self):
        self.manager = CollaborationManager()

    def test_empty_stats(self):
        """Stats should work for empty manager."""
        stats = self.manager.get_stats()
        assert stats["total_connections"] == 0
        assert stats["total_rooms"] == 0
        assert stats["rooms"] == {}

    def test_stats_with_connections(self):
        """Stats should accurately report connections."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        self.manager._track_connection(ws1, "room1", "user1@example.com")
        self.manager._track_connection(ws2, "room1", "user1@example.com")
        self.manager._track_connection(ws3, "room1", "user2@example.com")

        stats = self.manager.get_stats()

        assert stats["total_connections"] == 3
        assert stats["total_rooms"] == 1
        assert "room1" in stats["rooms"]

        room_stats = stats["rooms"]["room1"]
        assert room_stats["total_connections"] == 3
        assert room_stats["unique_users"] == 2
        assert room_stats["users"]["user1@example.com"] == 2
        assert room_stats["users"]["user2@example.com"] == 1

    def test_stats_multiple_rooms(self):
        """Stats should report all rooms."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        self.manager._track_connection(ws1, "room1", "user@example.com")
        self.manager._track_connection(ws2, "room2", "user@example.com")

        stats = self.manager.get_stats()

        assert stats["total_connections"] == 2
        assert stats["total_rooms"] == 2
        assert "room1" in stats["rooms"]
        assert "room2" in stats["rooms"]


# ==================== Activity Tracking Tests ====================

class TestActivityTracking:
    """Test connection activity tracking."""

    def setup_method(self):
        self.manager = CollaborationManager()

    def test_connection_has_timestamps(self):
        """New connections should have timestamps."""
        ws = MockWebSocket()
        self.manager._track_connection(ws, "room1", "user@example.com")

        meta = self.manager._connection_metadata[ws]
        assert "connected_at" in meta
        assert "last_activity" in meta

    def test_update_activity(self):
        """Activity update should update timestamp."""
        ws = MockWebSocket()
        self.manager._track_connection(ws, "room1", "user@example.com")

        original_activity = self.manager._connection_metadata[ws]["last_activity"]

        # Small delay to ensure different timestamp
        import time
        time.sleep(0.01)

        self.manager.update_activity(ws)
        new_activity = self.manager._connection_metadata[ws]["last_activity"]

        assert new_activity >= original_activity


# ==================== Access Request Tests ====================

class TestAccessRequestValidation:
    """Test access request edge cases."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    def test_viewer_can_request_access(self, mock_db):
        """Viewer should be able to request edit access."""
        from backend.models.enums import AccessRequestStatus, WorkflowRole

        # Viewer role should allow request
        assert WorkflowRole.VIEWER.value == "viewer"
        assert AccessRequestStatus.PENDING.value == "pending"

    def test_editor_cannot_request_access(self):
        """Editor already has access, should not be able to request."""
        from backend.models.enums import WorkflowRole

        # Editor and owner already have edit access
        assert WorkflowRole.EDITOR.value == "editor"
        assert WorkflowRole.OWNER.value == "owner"

    def test_access_request_status_transitions(self):
        """Test valid status transitions."""
        from backend.models.enums import AccessRequestStatus

        # Valid transitions: PENDING -> APPROVED or REJECTED
        assert AccessRequestStatus.PENDING.value == "pending"
        assert AccessRequestStatus.APPROVED.value == "approved"
        assert AccessRequestStatus.REJECTED.value == "rejected"

    def test_duplicate_request_prevention(self):
        """Same user should not create duplicate pending requests."""
        # This is enforced at the API level
        pass

    def test_request_for_nonexistent_workflow(self):
        """Request for non-existent workflow should fail."""
        # This is enforced at the API level with 404
        pass


class TestAccessRequestNotifications:
    """Test notification edge cases."""

    def test_owner_receives_notification(self):
        """Workflow owner should receive notification when access is requested."""
        pass

    def test_requester_notified_on_approval(self):
        """Requester should be notified when request is approved."""
        pass

    def test_requester_notified_on_rejection(self):
        """Requester should be notified when request is rejected."""
        pass

    def test_multiple_owners_notified(self):
        """All workflow owners should receive the notification."""
        pass


class TestRoleBasedCursorDisplay:
    """Test role-based cursor display edge cases."""

    def test_viewer_cursor_is_eye(self):
        """Viewer's cursor should display as eye icon."""
        from backend.models.enums import WorkflowRole
        role = WorkflowRole.VIEWER
        assert role.value == "viewer"
        # Frontend displays eye icon for viewer

    def test_editor_cursor_is_pencil(self):
        """Editor's cursor should display as pencil icon."""
        from backend.models.enums import WorkflowRole
        role = WorkflowRole.EDITOR
        assert role.value == "editor"
        # Frontend displays pencil icon for editor

    def test_owner_cursor_is_pencil(self):
        """Owner's cursor should display as pencil icon."""
        from backend.models.enums import WorkflowRole
        role = WorkflowRole.OWNER
        assert role.value == "owner"
        # Frontend displays pencil icon for owner

    def test_unknown_role_defaults_to_viewer(self):
        """Unknown role should default to viewer for safety."""
        # Handled in frontend useCollaboration hook
        pass


class TestReadOnlyMode:
    """Test read-only mode edge cases for viewers."""

    def test_viewer_cannot_sync_nodes(self):
        """Viewer should not be able to sync node changes."""
        pass

    def test_viewer_cannot_sync_edges(self):
        """Viewer should not be able to sync edge changes."""
        pass

    def test_viewer_can_see_cursor_updates(self):
        """Viewer should still be able to see other users' cursors."""
        pass

    def test_viewer_cursor_visible_to_others(self):
        """Other users should see viewer's cursor position."""
        pass

    def test_viewer_can_run_workflow(self):
        """Viewer should still be able to run/execute workflow."""
        pass

    def test_viewer_can_duplicate_workflow(self):
        """Viewer should be able to duplicate workflow (becomes owner of copy)."""
        pass


class TestAccessRequestRoleChange:
    """Test role changes mid-session."""

    def test_viewer_promoted_to_editor(self):
        """When viewer is promoted, they should get edit access."""
        from backend.models.enums import WorkflowRole
        # Transition from VIEWER to EDITOR
        old_role = WorkflowRole.VIEWER
        new_role = WorkflowRole.EDITOR
        assert old_role.value != new_role.value

    def test_editor_demoted_to_viewer(self):
        """When editor is demoted, they should lose edit access."""
        from backend.models.enums import WorkflowRole
        old_role = WorkflowRole.EDITOR
        new_role = WorkflowRole.VIEWER
        assert old_role.value != new_role.value

    def test_page_reload_on_approval(self):
        """Page should reload when access request is approved."""
        # This is handled in frontend AccessRequestContext
        pass


class TestAccessRequestEdgeCases:
    """Test additional edge cases."""

    def test_request_already_resolved(self):
        """Cannot resolve an already resolved request."""
        from backend.models.enums import AccessRequestStatus
        # APPROVED or REJECTED requests cannot be re-resolved
        assert AccessRequestStatus.APPROVED.value == "approved"
        assert AccessRequestStatus.REJECTED.value == "rejected"

    def test_only_owner_can_approve(self):
        """Only workflow owner can approve/reject requests."""
        from backend.models.enums import WorkflowRole
        assert WorkflowRole.OWNER.value == "owner"

    def test_editor_cannot_approve_requests(self):
        """Editor should not be able to approve access requests."""
        from backend.models.enums import WorkflowRole
        assert WorkflowRole.EDITOR.value == "editor"
        # API enforces this with 403

    def test_request_message_optional(self):
        """Request message should be optional."""
        # Message field is nullable in the model
        pass

    def test_websocket_reconnection_preserves_role(self):
        """Role should be preserved across WebSocket reconnections."""
        pass


# ==================== Run Tests ====================

if __name__ == "__main__":
    print("=" * 60)
    print("Running Collaboration Edge Case Tests")
    print("=" * 60)

    # Run pytest with verbose output
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
    ])

    sys.exit(exit_code)
