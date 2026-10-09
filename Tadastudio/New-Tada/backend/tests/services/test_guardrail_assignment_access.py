"""Tests for guardrail assignment listing access control.

GET /api/guardrails/assignments must not disclose assignment targets
(workflows / agent nodes) the caller cannot access. Global model/tool
assignments apply to everyone and remain visible.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.api.guardrails.routes import (
    _filter_assignments_by_target_access,
    list_assignments,
)
from backend.services.authorization.helpers import filter_accessible_workflow_ids


def _assignment(**overrides):
    base = {
        "id": "a-1",
        "policy_id": "p-1",
        "target_type": "workflow",
        "target_id": "wf-1",
        "workflow_id": None,
        "assigned_by": "someone-else",
    }
    base.update(overrides)
    return base


class TestFilterAccessibleWorkflowIds:
    """Batch workflow access check in authorization helpers."""

    def test_empty_input_returns_empty_set(self):
        assert filter_accessible_workflow_ids("user-1", []) == set()

    def test_falsy_ids_are_ignored(self):
        assert filter_accessible_workflow_ids("user-1", [None, ""]) == set()

    def test_admin_gets_all_candidates(self):
        result = filter_accessible_workflow_ids(
            "admin", ["wf-1", "wf-2"], is_admin=True
        )
        assert result == {"wf-1", "wf-2"}

    @patch("backend.services.authorization.helpers.resolve_user_id")
    @patch("backend.services.authorization.helpers.get_db")
    def test_unresolved_user_gets_nothing(self, mock_get_db, mock_resolve):
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_resolve.return_value = None

        assert filter_accessible_workflow_ids("ghost-user", ["wf-1"]) == set()

    @patch("backend.services.authorization.helpers.resolve_user_id")
    @patch("backend.services.authorization.helpers.get_db")
    def test_returns_union_of_owned_and_member_workflows(
        self, mock_get_db, mock_resolve
    ):
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_resolve.return_value = "user-1"

        owned_query = MagicMock()
        owned_query.filter.return_value.all.return_value = [("wf-owned",)]
        member_query = MagicMock()
        member_query.filter.return_value.all.return_value = [("wf-member",)]
        mock_db.query.side_effect = [owned_query, member_query]

        result = filter_accessible_workflow_ids(
            "user-1", ["wf-owned", "wf-member", "wf-other"]
        )
        assert result == {"wf-owned", "wf-member"}


class TestFilterAssignmentsByTargetAccess:
    """Route-level filtering of assignments by target access."""

    @patch("backend.api.guardrails.routes.filter_accessible_workflow_ids")
    def test_workflow_target_hidden_without_access(self, mock_accessible):
        mock_accessible.return_value = set()
        result = _filter_assignments_by_target_access([_assignment()], "caller")
        assert result == []

    @patch("backend.api.guardrails.routes.filter_accessible_workflow_ids")
    def test_workflow_target_visible_with_access(self, mock_accessible):
        mock_accessible.return_value = {"wf-1"}
        assignment = _assignment()
        result = _filter_assignments_by_target_access([assignment], "caller")
        assert result == [assignment]

    @patch("backend.api.guardrails.routes.filter_accessible_workflow_ids")
    def test_agent_node_target_checked_via_owning_workflow(self, mock_accessible):
        assignment = _assignment(
            target_type="agent_node", target_id="node-1", workflow_id="wf-1"
        )
        mock_accessible.return_value = {"wf-1"}
        assert _filter_assignments_by_target_access([assignment], "caller") == [
            assignment
        ]

        mock_accessible.return_value = set()
        assert _filter_assignments_by_target_access([assignment], "caller") == []

    @patch("backend.api.guardrails.routes.filter_accessible_workflow_ids")
    def test_agent_node_without_workflow_visible_only_to_creator(
        self, mock_accessible
    ):
        mock_accessible.return_value = set()
        assignment = _assignment(
            target_type="agent_node", target_id="node-1", workflow_id=None
        )
        assert _filter_assignments_by_target_access([assignment], "caller") == []

        own_assignment = _assignment(
            target_type="agent_node",
            target_id="node-1",
            workflow_id=None,
            assigned_by="caller",
        )
        assert _filter_assignments_by_target_access([own_assignment], "caller") == [
            own_assignment
        ]

    @patch("backend.api.guardrails.routes.filter_accessible_workflow_ids")
    def test_global_model_and_tool_targets_stay_visible(self, mock_accessible):
        mock_accessible.return_value = set()
        assignments = [
            _assignment(id="a-model", target_type="model", target_id="gpt-x"),
            _assignment(id="a-tool", target_type="tool", target_id="web_search"),
        ]
        result = _filter_assignments_by_target_access(assignments, "caller")
        assert result == assignments

    @patch("backend.api.guardrails.routes.filter_accessible_workflow_ids")
    def test_creator_always_sees_own_assignment(self, mock_accessible):
        mock_accessible.return_value = set()
        assignment = _assignment(assigned_by="caller")
        assert _filter_assignments_by_target_access([assignment], "caller") == [
            assignment
        ]

    @patch("backend.api.guardrails.routes.filter_accessible_workflow_ids")
    def test_only_relevant_workflow_ids_are_checked(self, mock_accessible):
        mock_accessible.return_value = set()
        assignments = [
            _assignment(target_type="workflow", target_id="wf-a"),
            _assignment(target_type="agent_node", target_id="n-1", workflow_id="wf-b"),
            _assignment(target_type="model", target_id="gpt-x"),
        ]
        _filter_assignments_by_target_access(assignments, "caller")
        candidates = mock_accessible.call_args.args[1]
        assert set(candidates) == {"wf-a", "wf-b"}


class TestListAssignmentsEndpoint:
    """Endpoint wiring: query gating and non-admin filtering."""

    @patch("backend.api.guardrails.routes.GuardrailPolicyService")
    @patch("backend.api.guardrails.routes.require_workflow_access_by_id")
    async def test_workflow_filter_requires_workflow_access(
        self, mock_require, mock_service
    ):
        mock_require.side_effect = HTTPException(status_code=403, detail="denied")

        with pytest.raises(HTTPException) as exc_info:
            await list_assignments(
                target_type=None,
                target_id=None,
                workflow_id="wf-1",
                policy_id=None,
                current_user={"sub": "user-1"},
            )
        assert exc_info.value.status_code == 403
        mock_service.list_assignments.assert_not_called()

    @patch("backend.api.guardrails.routes._filter_assignments_by_target_access")
    @patch("backend.api.guardrails.routes.GuardrailPolicyService")
    async def test_non_admin_filtered_by_policy_visibility_and_target_access(
        self, mock_service, mock_target_filter
    ):
        mock_service.list_assignments.return_value = [
            _assignment(policy_id="p-visible"),
            _assignment(id="a-2", policy_id="p-hidden"),
        ]
        mock_service.get_visible_policy_ids.return_value = {"p-visible"}
        mock_target_filter.side_effect = lambda assignments, user_id: assignments

        result = await list_assignments(
            target_type=None,
            target_id=None,
            workflow_id=None,
            policy_id=None,
            current_user={"sub": "user-1"},
        )

        assert [a["policy_id"] for a in result["assignments"]] == ["p-visible"]
        mock_target_filter.assert_called_once()

    @patch("backend.api.guardrails.routes._filter_assignments_by_target_access")
    @patch("backend.api.guardrails.routes.GuardrailPolicyService")
    async def test_admin_results_are_not_filtered(
        self, mock_service, mock_target_filter
    ):
        mock_service.list_assignments.return_value = [_assignment()]

        result = await list_assignments(
            target_type=None,
            target_id=None,
            workflow_id=None,
            policy_id=None,
            current_user={"sub": "admin-user", "is_admin": True},
        )

        assert len(result["assignments"]) == 1
        mock_target_filter.assert_not_called()
        mock_service.get_visible_policy_ids.assert_not_called()
