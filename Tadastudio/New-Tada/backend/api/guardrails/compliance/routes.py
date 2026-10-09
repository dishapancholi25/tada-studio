"""API routes for guardrail compliance overview.

Provides endpoints to view enforcement breakdown and identify
unprotected workflows and agent nodes with criticality levels.

- Admin endpoint: full org-wide view
- User endpoint: scoped to workflows the user owns or has membership in

Criticality levels:
- critical: No guardrail coverage at all (no assignments, no compulsory).
- high: Guardrails explicitly disabled on the workflow or node.
- medium: Only compulsory coverage, no specific policy assigned.
- low: Covered by specific assignment (fully protected).
"""

import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends
from sqlalchemy import func as sa_func, or_
from sqlalchemy.orm import Session

from backend.api.auth.dependencies import (
    get_current_user,
    require_active_user,
    require_admin,
)
from backend.models.auth.user import User
from backend.models.execution.graph_execution import GraphExecution
from backend.models.guardrails.guardrail_assignment import GuardrailAssignment
from backend.models.guardrails.guardrail_policy import GuardrailPolicy
from backend.models.workflows.graph_definition import GraphDefinition
from backend.models.workflows.membership import WorkflowMembership
from backend.models.workflows.publishing.published_workflow import PublishedWorkflow
from backend.models.workflows.workflow import Workflow
from backend.models.workflows.workflow_template import WorkflowTemplate
from backend.services.database import get_db

logger = logging.getLogger(__name__)

# Admin router — org-wide compliance view
admin_router = APIRouter(
    prefix="/api/guardrails",
    tags=["guardrail-compliance"],
    dependencies=[Depends(require_active_user), Depends(require_admin)],
)

# User router — scoped to workflows the caller can access
user_router = APIRouter(
    prefix="/api/guardrails/compliance",
    tags=["guardrail-compliance"],
    dependencies=[Depends(require_active_user)],
)

# Keep the original variable name so app.py import doesn't break
router = admin_router


def _get_node_guardrails_disabled(node: dict) -> bool:
    """Check if a node has guardrails explicitly disabled in its config."""
    config = node.get("config") or {}
    guardrails = config.get("guardrails") or {}
    return guardrails.get("enabled") is False


def _build_compliance_data(
    db: Session, *, scope_to_user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Build compliance data, optionally scoped to a specific user's workflows.

    Args:
        db: Database session.
        scope_to_user_id: If provided, only include workflows where this user
            has a WorkflowMembership record (owner, editor, or viewer).
    """
    # 1. Enforcement breakdown (always org-wide — these are global policy counts)
    policies = db.query(GuardrailPolicy).all()
    enforce_count = 0
    audit_count = 0
    disabled_count = 0
    compulsory_count = 0
    policy_mode_map: Dict[str, str] = {}
    for policy in policies:
        mode = (policy.config or {}).get("enforcement_mode", "enforce")
        policy_mode_map[str(policy.id)] = mode
        if mode == "enforce":
            enforce_count += 1
        elif mode == "audit":
            audit_count += 1
        elif mode == "disabled":
            disabled_count += 1
        if getattr(policy, "is_compulsory", False):
            compulsory_count += 1

    has_compulsory_coverage = compulsory_count > 0

    # 2. Build assignment lookup maps in a single pass
    assignments = db.query(GuardrailAssignment).all()
    workflow_assigned_ids: Set[str] = set()
    agent_node_assignments: Set[tuple] = set()
    workflow_policy_ids: Dict[str, List[str]] = {}
    for a in assignments:
        if a.target_type == "workflow":
            workflow_assigned_ids.add(a.target_id)
            workflow_policy_ids.setdefault(a.target_id, []).append(a.policy_id)
        if a.workflow_id:
            workflow_assigned_ids.add(a.workflow_id)
        if a.target_type == "agent_node" and a.workflow_id:
            agent_node_assignments.add((a.workflow_id, a.target_id))

    # 3. Query workflows with their graph definitions in one go
    # Filter: non-deleted, has active member, has latest graph with active workspace_id
    workflows_with_active_members = (
        db.query(WorkflowMembership.workflow_id)
        .join(User, WorkflowMembership.user_id == User.id)
        .filter(User.role.in_(["USER", "ADMIN"]))
        .distinct()
        .subquery()
    )
    active_user_ids = (
        db.query(User.id).filter(User.role.in_(["USER", "ADMIN"])).subquery()
    )
    active_user_emails = (
        db.query(User.email)
        .filter(
            User.role.in_(["USER", "ADMIN"]),
            User.email.isnot(None),
        )
        .subquery()
    )

    # Join Workflow with GraphDefinition to avoid N+1 queries
    wf_graph_query = (
        db.query(Workflow, GraphDefinition)
        .join(GraphDefinition, GraphDefinition.workflow_id == Workflow.id)
        .filter(
            Workflow.is_deleted == False,  # noqa: E712
            Workflow.id.in_(db.query(workflows_with_active_members.c.workflow_id)),
            GraphDefinition.is_latest == True,  # noqa: E712
            or_(
                GraphDefinition.workspace_id.in_(db.query(active_user_ids.c.id)),
                GraphDefinition.workspace_id.in_(db.query(active_user_emails.c.email)),
            ),
        )
    )

    # Scope to user's accessible workflows if requested
    if scope_to_user_id:
        user_wf_ids = (
            db.query(WorkflowMembership.workflow_id)
            .filter(WorkflowMembership.user_id == scope_to_user_id)
            .distinct()
            .subquery()
        )
        wf_graph_query = wf_graph_query.filter(
            Workflow.id.in_(db.query(user_wf_ids.c.workflow_id))
        )

    workflow_graph_pairs = wf_graph_query.all()

    # 4. Batch-fetch related data
    # Published and library workflow IDs
    published_wf_ids = set(
        row.workflow_id
        for row in db.query(PublishedWorkflow.workflow_id)
        .filter(
            PublishedWorkflow.is_published == True,  # noqa: E712
            PublishedWorkflow.workflow_id.isnot(None),
        )
        .all()
    )
    library_wf_ids = set(
        row.workflow_id
        for row in db.query(WorkflowTemplate.workflow_id)
        .filter(
            WorkflowTemplate.is_active == True,  # noqa: E712
            WorkflowTemplate.is_latest_version == True,  # noqa: E712
        )
        .all()
    )

    # Workflow owner lookup (OWNER membership → user name/email)
    owner_rows = (
        db.query(WorkflowMembership.workflow_id, User.name, User.email)
        .join(User, WorkflowMembership.user_id == User.id)
        .filter(
            WorkflowMembership.role == "OWNER",
            User.role.in_(["USER", "ADMIN"]),
            or_(User.name.isnot(None), User.email.isnot(None)),
        )
        .all()
    )
    workflow_owner_map: Dict[str, Dict[str, Optional[str]]] = {
        row.workflow_id: {"name": row.name, "email": row.email} for row in owner_rows
    }

    # Fallback: creator from Workflow.created_by_user_id
    creator_ids = {
        str(w.created_by_user_id)
        for w, _ in workflow_graph_pairs
        if w.created_by_user_id is not None
    }
    creator_map: Dict[str, Dict[str, Optional[str]]] = {}
    if creator_ids:
        creator_rows = (
            db.query(User.id, User.name, User.email)
            .filter(
                User.id.in_(creator_ids),
                User.role.in_(["USER", "ADMIN"]),
                or_(User.name.isnot(None), User.email.isnot(None)),
            )
            .all()
        )
        creator_map = {
            row.id: {"name": row.name, "email": row.email} for row in creator_rows
        }

    # Last execution time per workflow
    last_exec_rows = (
        db.query(
            GraphExecution.workflow_id,
            sa_func.max(GraphExecution.start_time).label("last_executed_at"),
            sa_func.count(GraphExecution.id).label("execution_count"),
        )
        .filter(GraphExecution.workflow_id.isnot(None))
        .group_by(GraphExecution.workflow_id)
        .all()
    )
    last_exec_map: Dict[str, Dict[str, Any]] = {
        row.workflow_id: {
            "last_executed_at": row.last_executed_at.isoformat()
            if row.last_executed_at
            else None,
            "execution_count": row.execution_count,
        }
        for row in last_exec_rows
    }

    # 5. Process workflows
    unprotected_workflows: List[Dict[str, Any]] = []
    inactive_workflows: List[Dict[str, Any]] = []
    unprotected_agent_nodes: List[Dict[str, Any]] = []

    for workflow, graph_def in workflow_graph_pairs:
        wf_id = str(workflow.id)

        # Skip ghost/orphan workflows without basic metadata
        if workflow.created_at is None:
            continue

        # Skip workflows with no graph definition or no nodes
        if graph_def.definition_json is None:
            continue

        # Handle definition_json being a string (legacy data) or dict
        definition = graph_def.definition_json
        if isinstance(definition, str):
            try:
                import json

                definition = json.loads(definition)
            except (json.JSONDecodeError, TypeError):
                continue

        all_nodes = definition.get("nodes", []) if isinstance(definition, dict) else []
        if not all_nodes:
            continue

        # Extract agent nodes
        agent_nodes = []
        agent_node_raw = []
        for node in all_nodes:
            if node.get("type") == "AGENT":
                agent_nodes.append(
                    {
                        "node_id": node.get("uniq_id"),
                        "node_name": node.get("name"),
                    }
                )
                agent_node_raw.append(node)

        # Skip workflows with no agent nodes - no LLM activity = no guardrail risk
        if not agent_nodes:
            continue

        # Resolve owner info
        owner_info = workflow_owner_map.get(wf_id)
        if not owner_info and workflow.created_by_user_id is not None:
            owner_info = creator_map.get(str(workflow.created_by_user_id))
        exec_info = last_exec_map.get(wf_id, {})
        is_shared = wf_id in published_wf_ids or wf_id in library_wf_ids
        has_owner = owner_info is not None and bool(
            owner_info.get("name") or owner_info.get("email")
        )
        has_executed = exec_info.get("execution_count", 0) > 0

        # Skip ghost workflows without owner, not shared, never executed
        if not has_owner and not is_shared and not has_executed:
            continue

        has_workflow_assignment = wf_id in workflow_assigned_ids

        # Check if all assigned policies are disabled
        assigned_policy_ids = workflow_policy_ids.get(wf_id, [])
        all_assignments_disabled = (
            has_workflow_assignment
            and assigned_policy_ids
            and all(
                policy_mode_map.get(pid) == "disabled" for pid in assigned_policy_ids
            )
        )

        # Determine workflow-level criticality
        if not has_workflow_assignment and not has_compulsory_coverage:
            # No coverage at all
            criticality = "critical"
        elif all_assignments_disabled and not has_compulsory_coverage:
            # Has assignments but they're all disabled, no compulsory fallback
            criticality = "high"
        elif all_assignments_disabled and has_compulsory_coverage:
            # Disabled assignments but compulsory provides baseline
            criticality = "medium"
        elif not has_workflow_assignment and has_compulsory_coverage:
            # Only compulsory coverage, no specific assignment
            criticality = "medium"
        else:
            # Has active specific assignment
            criticality = None  # fully protected, skip

        if criticality:
            wf_entry = {
                "workflow_id": wf_id,
                "workflow_name": workflow.name,
                "workflow_description": workflow.description,
                "criticality": criticality,
                "has_compulsory_coverage": has_compulsory_coverage,
                "unprotected_node_ids": [n["node_id"] for n in agent_nodes],
                "is_published": wf_id in published_wf_ids,
                "is_library": wf_id in library_wf_ids,
                "owner_name": owner_info["name"] if owner_info else None,
                "owner_email": owner_info["email"] if owner_info else None,
                "created_at": workflow.created_at.isoformat()
                if workflow.created_at
                else None,
                "updated_at": workflow.updated_at.isoformat()
                if workflow.updated_at
                else None,
                "last_executed_at": exec_info.get("last_executed_at"),
                "execution_count": exec_info.get("execution_count", 0),
                "agent_node_count": len(agent_nodes),
                "graph_version": graph_def.version if graph_def else None,
            }

            # Published and library workflows always appear in the main
            # list — they represent production risk regardless of execution
            # count.  Draft workflows that have never been executed are
            # separated as inactive (tutorials, experiments, abandoned drafts).
            is_never_executed = exec_info.get("execution_count", 0) == 0
            if is_never_executed and not is_shared:
                inactive_workflows.append(wf_entry)
                continue  # skip agent-node analysis for inactive workflows
            else:
                unprotected_workflows.append(wf_entry)

        # Check individual agent nodes
        for i, n in enumerate(agent_nodes):
            raw_node = agent_node_raw[i] if i < len(agent_node_raw) else {}
            node_has_assignment = (wf_id, n["node_id"]) in agent_node_assignments
            node_guardrails_disabled = _get_node_guardrails_disabled(raw_node)

            if node_has_assignment and not node_guardrails_disabled:
                # Fully covered by a specific assignment
                if has_workflow_assignment and not all_assignments_disabled:
                    continue  # workflow + node both covered
                if has_compulsory_coverage:
                    continue  # node assigned + compulsory
                continue  # node has its own assignment

            # Determine node-level criticality
            if node_guardrails_disabled and not has_compulsory_coverage:
                node_criticality = "high"
            elif node_guardrails_disabled and has_compulsory_coverage:
                node_criticality = "medium"
            elif (
                not node_has_assignment
                and not has_workflow_assignment
                and not has_compulsory_coverage
            ):
                node_criticality = "critical"
            elif (
                not node_has_assignment
                and has_compulsory_coverage
                and not has_workflow_assignment
            ):
                node_criticality = "medium"
            elif (
                not node_has_assignment
                and has_workflow_assignment
                and not all_assignments_disabled
            ):
                continue  # covered by workflow assignment
            else:
                node_criticality = "medium"

            # Resolve node-level model info from raw node config
            raw_model = (raw_node.get("config") or {}).get("model", None)

            unprotected_agent_nodes.append(
                {
                    "workflow_id": wf_id,
                    "node_id": n["node_id"],
                    "node_name": n["node_name"],
                    "workflow_name": workflow.name,
                    "criticality": node_criticality,
                    "has_compulsory_coverage": has_compulsory_coverage,
                    "guardrails_disabled": node_guardrails_disabled,
                    "is_published": wf_id in published_wf_ids,
                    "is_library": wf_id in library_wf_ids,
                    "owner_name": owner_info["name"] if owner_info else None,
                    "owner_email": owner_info["email"] if owner_info else None,
                    "model": raw_model,
                    "created_at": workflow.created_at.isoformat()
                    if workflow.created_at
                    else None,
                    "last_executed_at": exec_info.get("last_executed_at"),
                }
            )

    return {
        "success": True,
        "enforcement_breakdown": {
            "enforce": enforce_count,
            "audit": audit_count,
            "disabled": disabled_count,
            "compulsory": compulsory_count,
        },
        "unprotected_workflows": unprotected_workflows,
        "inactive_workflows": inactive_workflows,
        "unprotected_agent_nodes": unprotected_agent_nodes,
    }


@admin_router.get("/admin/compliance")
async def get_compliance_overview() -> Dict[str, Any]:
    """Compliance overview: enforcement breakdown, unprotected workflows and agent nodes (admin, org-wide)."""
    with get_db() as db:
        return _build_compliance_data(db)


@user_router.get("/my")
async def get_my_compliance(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compliance overview scoped to workflows the caller owns or has access to."""
    user_id = current_user.get("sub")
    if not user_id:
        return {
            "success": True,
            "enforcement_breakdown": {
                "enforce": 0,
                "audit": 0,
                "disabled": 0,
                "compulsory": 0,
            },
            "unprotected_workflows": [],
            "inactive_workflows": [],
            "unprotected_agent_nodes": [],
        }
    with get_db() as db:
        return _build_compliance_data(db, scope_to_user_id=user_id)
