"""API routes for guardrail policy management.

Provides CRUD, sharing, assignment, resolution, admin, and template endpoints.
Phase 3: Violations dashboard, compliance view, compulsory enforcement.
Phase 4: Policy versioning, test sandbox, effectiveness metrics, built-in packs.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.auth.dependencies import (
    get_current_user,
    require_active_user,
    require_admin,
)
from backend.api.guardrails.models import (
    ClonePolicyRequest,
    CreateAssignmentRequest,
    CreatePolicyRequest,
    PolicyTestRequest,
    RollbackPolicyRequest,
    SetCompulsoryRequest,
    SharePolicyRequest,
    UpdateAssignmentRequest,
    UpdatePolicyRequest,
    UpdateVisibilityRequest,
    ViolationFeedbackRequest,
)
from backend.models.workflows.graph_definition import GraphDefinition
from backend.services.authorization.helpers import (
    filter_accessible_workflow_ids,
    require_workflow_access_by_id,
)
from backend.services.database import get_db
from backend.services.guardrails.policy_service import GuardrailPolicyService
from backend.services.guardrails.resolver import LayeredPolicyResolver
from backend.services.guardrails.serialization import config_to_pipeline_entry

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/guardrails",
    tags=["guardrails"],
    dependencies=[Depends(require_active_user)],
)


def _get_user_id(current_user: Dict[str, Any]) -> str:
    return current_user.get("sub") or current_user.get("email", "")


def _is_admin(current_user: Dict[str, Any]) -> bool:
    return bool(current_user.get("is_admin"))


def _graph_definition_contains_node(definition_json: Dict[str, Any], node_id: str) -> bool:
    """Return whether a graph definition contains a node with the given ID."""
    for node in definition_json.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_data = node.get("data") if isinstance(node.get("data"), dict) else {}
        candidate_ids = {
            node.get("id"),
            node.get("uniq_id"),
            node.get("node_id"),
            node_data.get("id"),
            node_data.get("uniq_id"),
            node_data.get("node_id"),
        }
        if node_id in candidate_ids:
            return True
    return False


def _resolve_agent_node_workflow_id(node_id: str, workflow_id: Optional[str] = None) -> str:
    """Resolve the workflow that owns an agent node ID from latest graph definitions."""
    with get_db() as db:
        query = db.query(GraphDefinition).filter(
            GraphDefinition.is_latest == True,  # noqa: E712
            GraphDefinition.workflow_id.isnot(None),
        )
        if workflow_id:
            query = query.filter(GraphDefinition.workflow_id == workflow_id)

        workflow_ids = []
        for graph_definition in query.all():
            if _graph_definition_contains_node(
                graph_definition.definition_json or {},
                node_id,
            ):
                workflow_ids.append(graph_definition.workflow_id)

    unique_workflow_ids = list(dict.fromkeys(workflow_ids))
    if not unique_workflow_ids:
        raise HTTPException(status_code=404, detail="Agent node target not found")
    if len(unique_workflow_ids) > 1:
        raise HTTPException(
            status_code=400,
            detail="workflow_id is required to disambiguate this agent node target",
        )
    return unique_workflow_ids[0]


def _authorize_assignment_target(
    current_user: Dict[str, Any],
    target_type: str,
    target_id: str,
    workflow_id: Optional[str],
    is_admin: bool,
) -> None:
    """Authorize assignment to the actual target resource."""
    if target_type == "workflow":
        require_workflow_access_by_id(current_user, target_id)
        return

    if target_type == "agent_node":
        owner_workflow_id = _resolve_agent_node_workflow_id(target_id, workflow_id)
        require_workflow_access_by_id(current_user, owner_workflow_id)
        return

    if target_type in {"model", "tool"}:
        if not is_admin:
            raise HTTPException(
                status_code=403,
                detail=f"Only admins can assign guardrails to global {target_type} targets",
            )
        return

    raise HTTPException(status_code=400, detail="Invalid target_type")


def _filter_assignments_by_target_access(
    assignments: list[dict[str, Any]],
    user_id: str,
) -> list[dict[str, Any]]:
    """Drop assignments whose target the caller cannot access.

    Global model/tool assignments apply to every user, so they stay visible.
    Workflow targets require workflow access (ownership or membership);
    agent-node targets are checked via their owning workflow. Assignments the
    caller created are always visible. Agent-node assignments without a
    recorded workflow_id cannot be verified, so they are hidden from everyone
    except their creator.
    """
    candidate_workflow_ids = set()
    for assignment in assignments:
        if assignment["target_type"] == "workflow":
            candidate_workflow_ids.add(assignment["target_id"])
        elif assignment["target_type"] == "agent_node":
            candidate_workflow_ids.add(assignment.get("workflow_id"))

    accessible_workflow_ids = filter_accessible_workflow_ids(
        user_id, candidate_workflow_ids
    )

    def _target_visible(assignment: dict[str, Any]) -> bool:
        if assignment.get("assigned_by") == user_id:
            return True
        target_type = assignment["target_type"]
        if target_type in {"model", "tool"}:
            return True
        if target_type == "workflow":
            return assignment["target_id"] in accessible_workflow_ids
        if target_type == "agent_node":
            return assignment.get("workflow_id") in accessible_workflow_ids
        return False

    return [assignment for assignment in assignments if _target_visible(assignment)]


# Policy CRUD


@router.post("/policies", status_code=201)
async def create_policy(
    request: CreatePolicyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new guardrail policy."""
    user_id = _get_user_id(current_user)
    if request.is_compulsory and not _is_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Only admins can create compulsory policies"
        )
    if request.scope == "global" and not _is_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Only admins can create global policies"
        )

    result = GuardrailPolicyService.create_policy(
        name=request.name,
        config=request.config,
        user_id=user_id,
        description=request.description,
        scope=request.scope,
        is_compulsory=request.is_compulsory,
        applies_to=request.applies_to,
        visible_to_groups=request.visible_to_groups or request.shared_with,
        is_template=request.is_template,
        tags=request.tags,
    )
    return {"success": True, "policy": result}


@router.get("/policies")
async def list_policies(
    scope: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    applies_to: Optional[str] = Query(None),
    is_template: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List guardrail policies visible to the current user."""
    user_id = _get_user_id(current_user)
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    policies = GuardrailPolicyService.list_policies(
        user_id=user_id,
        is_admin=_is_admin(current_user),
        scope=scope,
        tags=tag_list,
        applies_to=applies_to,
        is_template=is_template,
        search=search,
    )
    return {"success": True, "policies": policies}


@router.get("/policies/{policy_id}")
async def get_policy(
    policy_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a single guardrail policy by ID."""
    user_id = _get_user_id(current_user)
    policy = GuardrailPolicyService.get_policy(
        policy_id=policy_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"success": True, "policy": policy}


@router.put("/policies/{policy_id}")
async def update_policy(
    policy_id: str,
    request: UpdatePolicyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update a guardrail policy. Admins can edit builtin templates."""
    user_id = _get_user_id(current_user)
    is_admin = _is_admin(current_user)

    if request.is_compulsory and not is_admin:
        raise HTTPException(
            status_code=403, detail="Only admins can set compulsory status"
        )
    if request.scope == "global" and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can set global scope")

    # Check if this is a built-in system policy
    existing = GuardrailPolicyService.get_policy(policy_id, user_id, is_admin)
    if existing and (
        existing.get("is_builtin") or existing.get("created_by") == "__system__"
    ):
        if not is_admin:
            raise HTTPException(
                status_code=403,
                detail="Built-in policies can only be modified by administrators. Clone to create an editable copy.",
            )
        # Admin is editing builtin - allow it
        logger.info(f"[GUARDRAILS] Admin {user_id} editing builtin policy {policy_id}")

    result = GuardrailPolicyService.update_policy(
        policy_id=policy_id,
        user_id=user_id,
        is_admin=is_admin,
        **request.model_dump(exclude_none=True),
    )
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found or access denied")
    if isinstance(result, dict) and result.get("error") == "builtin_readonly":
        raise HTTPException(
            status_code=403,
            detail="Built-in policy packs can only be modified by administrators.",
        )
    # Invalidate compulsory cache so updated config propagates immediately
    if isinstance(result, dict) and result.get("is_compulsory"):
        LayeredPolicyResolver.invalidate_cache()
    return {"success": True, "policy": result}


@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete a guardrail policy."""
    user_id = _get_user_id(current_user)
    result = GuardrailPolicyService.delete_policy(
        policy_id=policy_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Policy not found")
    if result.get("error") == "builtin_cannot_delete":
        raise HTTPException(
            status_code=403,
            detail="Built-in policy packs cannot be deleted. Clone to create an editable copy.",
        )
    if result.get("error") == "compulsory_active":
        raise HTTPException(
            status_code=409,
            detail="Policy is currently enforced as compulsory. Deactivate compulsory status before deleting.",
        )
    if result.get("error") == "compulsory_cannot_delete":
        raise HTTPException(
            status_code=403, detail="Compulsory policies can only be deleted by admins"
        )
    if result.get("error") == "system_policy":
        raise HTTPException(status_code=409, detail="System policies cannot be deleted")
    if result.get("error") == "forbidden":
        raise HTTPException(status_code=403, detail="You do not own this policy")
    return {"success": True, "message": "Policy deleted"}


# Visibility (mirrors collections pattern)


@router.patch("/policies/{policy_id}/visibility")
async def update_policy_visibility(
    policy_id: str,
    request: UpdateVisibilityRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update group-based visibility for a policy.

    Uses the same pattern as collections:
      [] = private, ["__all__"] = everyone, ["grp"] = specific groups.
    """
    user_id = _get_user_id(current_user)
    result = GuardrailPolicyService.update_visibility(
        policy_id=policy_id,
        user_id=user_id,
        visible_to_groups=request.visible_to_groups,
        is_admin=_is_admin(current_user),
    )
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found or access denied")
    return {"success": True, "policy": result}


# Legacy sharing endpoints (kept for backwards compat)


@router.post("/policies/{policy_id}/share")
async def share_policy(
    policy_id: str,
    request: SharePolicyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Share a policy with users or groups."""
    user_id = _get_user_id(current_user)
    result = GuardrailPolicyService.share_policy(
        policy_id=policy_id,
        user_id=user_id,
        share_with=request.share_with,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found or access denied")
    return {"success": True, "policy": result}


@router.delete("/policies/{policy_id}/share/{target_user}")
async def unshare_policy(
    policy_id: str,
    target_user: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Remove a user from policy sharing."""
    user_id = _get_user_id(current_user)
    result = GuardrailPolicyService.unshare_policy(
        policy_id=policy_id,
        user_id=user_id,
        remove_user=target_user,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found or access denied")
    return {"success": True, "policy": result}


# Clone


@router.post("/policies/{policy_id}/clone", status_code=201)
async def clone_policy(
    policy_id: str,
    request: ClonePolicyRequest = ClonePolicyRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Clone a policy for the current user."""
    user_id = _get_user_id(current_user)
    result = GuardrailPolicyService.clone_policy(
        policy_id=policy_id,
        user_id=user_id,
        name_override=request.name,
        is_admin=_is_admin(current_user),
    )
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"success": True, "policy": result}


# Assignments


@router.post("/assignments", status_code=201)
async def create_assignment(
    request: CreateAssignmentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Assign a guardrail policy to a target."""
    user_id = _get_user_id(current_user)
    is_admin = _is_admin(current_user)
    valid_types = {"agent_node", "model", "tool", "workflow"}
    if request.target_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target_type. Must be one of: {', '.join(sorted(valid_types))}",
        )
    if not GuardrailPolicyService.get_policy(request.policy_id, user_id, is_admin):
        raise HTTPException(
            status_code=403,
            detail="Policy not found or access denied",
        )
    _authorize_assignment_target(
        current_user=current_user,
        target_type=request.target_type,
        target_id=request.target_id,
        workflow_id=request.workflow_id,
        is_admin=is_admin,
    )
    if request.workflow_id:
        require_workflow_access_by_id(current_user, request.workflow_id)
    result = GuardrailPolicyService.create_assignment(
        policy_id=request.policy_id,
        target_type=request.target_type,
        target_id=request.target_id,
        assigned_by=user_id,
        workflow_id=request.workflow_id,
        priority=request.priority,
        override_mode=request.override_mode,
    )
    return {"success": True, "assignment": result}


@router.patch("/assignments/{assignment_id}")
async def update_assignment(
    assignment_id: str,
    request: UpdateAssignmentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update an existing guardrail policy assignment (priority, override_mode)."""
    user_id = _get_user_id(current_user)
    result = GuardrailPolicyService.update_assignment(
        assignment_id=assignment_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
        priority=request.priority,
        override_mode=request.override_mode,
    )
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Assignment not found")
    if result.get("error") == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied")
    return {"success": True, "assignment": result}


@router.delete("/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Remove a guardrail policy assignment."""
    user_id = _get_user_id(current_user)
    result = GuardrailPolicyService.delete_assignment(
        assignment_id=assignment_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Assignment not found")
    if result.get("error") == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied")
    return {"success": True, "message": "Assignment deleted"}


@router.get("/assignments")
async def list_assignments(
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    workflow_id: Optional[str] = Query(None),
    policy_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List guardrail policy assignments visible to the caller.

    Non-admins only see assignments whose policy is visible to them AND whose
    target they can access (their workflows/nodes, global model/tool targets,
    or assignments they created themselves).
    """
    user_id = _get_user_id(current_user)
    is_admin = _is_admin(current_user)
    if workflow_id:
        require_workflow_access_by_id(current_user, workflow_id)
    assignments = GuardrailPolicyService.list_assignments(
        target_type=target_type,
        target_id=target_id,
        workflow_id=workflow_id,
        policy_id=policy_id,
    )
    if not is_admin:
        visible_policy_ids = GuardrailPolicyService.get_visible_policy_ids(
            [assignment["policy_id"] for assignment in assignments],
            user_id,
            is_admin,
        )
        assignments = [
            assignment
            for assignment in assignments
            if assignment["policy_id"] in visible_policy_ids
        ]
        assignments = _filter_assignments_by_target_access(assignments, user_id)
    return {"success": True, "assignments": assignments}


# Resolution


@router.get("/resolve")
async def resolve_config(
    workflow_id: Optional[str] = Query(None),
    node_id: Optional[str] = Query(None),
    model_id: Optional[str] = Query(None),
    tool_names: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Preview the resolved guardrails pipeline for a context.

    Returns backward-compatible ``layers`` / ``effective_config`` keys
    expected by the current frontend (EffectiveConfigPreview, resolveConfig).
    Internally uses the new pipeline-based resolver.

    TODO(T5): Migrate frontend consumers to read ``pipeline`` / ``tool_pipelines``
    directly and remove this compatibility mapping.
    """
    if workflow_id:
        require_workflow_access_by_id(current_user, workflow_id)
    elif not _is_admin(current_user):
        raise HTTPException(
            status_code=400,
            detail="workflow_id is required unless caller is admin",
        )

    pipeline = LayeredPolicyResolver.resolve_as_pipeline(
        workflow_id=workflow_id,
        node_id=node_id,
        model_id=model_id,
    )

    # -- Backward-compatible mapping for existing frontend consumers --
    # Build ``layers`` list: one entry per pipeline config
    layers = []
    for cfg in pipeline:
        layers.append(
            {
                "source": "compulsory" if cfg.priority == 0 else "policy",
                "policy_id": cfg.policy_id or "",
                "policy_name": cfg.policy_name or "",
                "config": cfg.to_dict(),
            }
        )

    # Build ``effective_config``: merge enabled pipeline configs into a
    # single flat dict that the EffectiveConfigPreview sections can read.
    effective_config: Dict[str, Any] = {}
    for cfg in pipeline:
        if not cfg.enabled or cfg.enforcement_mode == "disabled":
            continue
        d = cfg.to_dict()
        if not effective_config:
            effective_config = d
        else:
            # Merge additive collection fields from subsequent layers
            for list_key in ("pattern_rules", "custom_filters"):
                if d.get(list_key):
                    effective_config.setdefault(list_key, []).extend(d[list_key])
            # Escalate enforcement mode to strictest
            if d.get("enforcement_mode") == "enforce":
                effective_config["enforcement_mode"] = "enforce"
            # Fill in sections that the first layer didn't provide
            for section_key in (
                "tool_call_policy",
                "token_budget",
                "output_scanners",
                "provider_content_filter",
            ):
                if d.get(section_key) and not effective_config.get(section_key):
                    effective_config[section_key] = d[section_key]
            # Behavioral fields are top-level and merge naturally as first-wins
            for bh_key in (
                "detect_prompt_injection", "detect_jailbreak_attempts",
                "system_prompt_protection", "max_input_length", "max_output_length",
                "detect_toxicity", "anonymize_pii", "use_faker", "pii_entity_types",
                "detect_secrets", "ban_topics", "allowed_languages", "detect_gibberish",
                "ban_code", "max_input_tokens", "prompt_injection_threshold",
                "jailbreak_threshold", "toxicity_threshold", "judge_llm_config",
            ):
                if d.get(bh_key) and not effective_config.get(bh_key):
                    effective_config[bh_key] = d[bh_key]

    response: Dict[str, Any] = {
        "success": True,
        "layers": layers,
        "effective_config": effective_config,
        # Also include the raw pipeline for forward-compatible consumers
        "pipeline": [cfg.to_dict() for cfg in pipeline],
        # Decomposed: each policy lists individually named guardrails
        "decomposed_pipeline": [config_to_pipeline_entry(cfg) for cfg in pipeline],
    }

    # Per-tool configs (if requested)
    tools = [t.strip() for t in tool_names.split(",")] if tool_names else None
    if tools:
        tool_pipelines_map = LayeredPolicyResolver.resolve_tool_pipelines(tools)
        # Backward-compatible: tool_configs maps tool_id -> first active config dict
        tool_configs: Dict[str, Any] = {}
        for tid, cfgs in tool_pipelines_map.items():
            for tc in cfgs:
                if tc.enabled and tc.enforcement_mode != "disabled":
                    tool_configs[tid] = tc.to_dict()
                    break
        response["tool_configs"] = tool_configs
        # Also include raw tool pipelines for forward-compatible consumers
        response["tool_pipelines"] = {
            tid: [cfg.to_dict() for cfg in cfgs]
            for tid, cfgs in tool_pipelines_map.items()
        }
        # Decomposed tool pipelines
        response["decomposed_tool_pipelines"] = {
            tid: [config_to_pipeline_entry(cfg) for cfg in cfgs]
            for tid, cfgs in tool_pipelines_map.items()
        }

    return response


# Admin compulsory


@router.get("/admin/compulsory", dependencies=[Depends(require_admin)])
async def list_compulsory_policies(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Admin: List all compulsory policies."""
    policies = GuardrailPolicyService.list_compulsory_policies()
    return {"success": True, "policies": policies}


@router.post("/admin/compulsory", dependencies=[Depends(require_admin)])
async def set_compulsory_policy(
    request: SetCompulsoryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Admin: Set or unset a policy as compulsory."""
    result = GuardrailPolicyService.set_compulsory(
        policy_id=request.policy_id,
        is_compulsory=request.is_compulsory,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    LayeredPolicyResolver.invalidate_cache()
    return {"success": True, "policy": result}


@router.delete("/admin/compulsory/{policy_id}", dependencies=[Depends(require_admin)])
async def deactivate_compulsory_policy(
    policy_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Admin: Deactivate compulsory status on a policy (sets is_compulsory=False)."""
    result = GuardrailPolicyService.set_compulsory(
        policy_id=policy_id, is_compulsory=False
    )
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"success": True}


# Templates


@router.get("/templates")
async def list_templates(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all guardrail policy templates."""
    templates = GuardrailPolicyService.list_templates()
    return {"success": True, "templates": templates}


# Phase 3: Violations


@router.get("/violations")
async def list_violations(
    policy_id: Optional[str] = Query(None),
    rule_name: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    workflow_id: Optional[str] = Query(None),
    agent_node_id: Optional[str] = Query(None),
    execution_id: Optional[str] = Query(None),
    from_ts: Optional[datetime] = Query(None),
    to_ts: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List guardrail violations (scoped: admins see all, users see own)."""
    from backend.services.guardrails.violation_service import ViolationService

    user_id = _get_user_id(current_user)
    return ViolationService.list_violations(
        user_id=user_id,
        is_admin=_is_admin(current_user),
        policy_id=policy_id,
        rule_name=rule_name,
        severity=severity,
        workflow_id=workflow_id,
        agent_node_id=agent_node_id,
        execution_id=execution_id,
        from_ts=from_ts,
        to_ts=to_ts,
        limit=limit,
        offset=offset,
    )


@router.get("/violations/summary", dependencies=[Depends(require_admin)])
async def get_violations_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Admin summary of guardrail violations and policy enforcement modes."""
    from datetime import timedelta, timezone

    from sqlalchemy import func

    from backend.models.guardrails.guardrail_policy import GuardrailPolicy
    from backend.models.guardrails.violation_event import GuardrailViolationEvent
    from backend.services.database import get_db

    with get_db() as db:
        # Enforcement breakdown from policies
        policies = db.query(GuardrailPolicy).all()
        enforce_count = 0
        audit_count = 0
        disabled_count = 0
        compulsory_count = 0
        for policy in policies:
            mode = (policy.config or {}).get("enforcement_mode", "enforce")
            if mode == "enforce":
                enforce_count += 1
            elif mode == "audit":
                audit_count += 1
            elif mode == "disabled":
                disabled_count += 1
            if getattr(policy, "is_compulsory", False):
                compulsory_count += 1

        # Violations in last 24 hours
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
        total_violations_24h = (
            db.query(func.count(GuardrailViolationEvent.id))
            .filter(GuardrailViolationEvent.created_at >= cutoff)
            .scalar()
        )

        # Most triggered rules (top 5)
        most_triggered_rules = (
            db.query(
                GuardrailViolationEvent.rule_name,
                func.count(GuardrailViolationEvent.id).label("count"),
            )
            .group_by(GuardrailViolationEvent.rule_name)
            .order_by(func.count(GuardrailViolationEvent.id).desc())
            .limit(5)
            .all()
        )

    return {
        "success": True,
        "summary": {
            "enforcement_breakdown": {
                "enforce": enforce_count,
                "audit": audit_count,
                "disabled": disabled_count,
                "compulsory": compulsory_count,
            },
            "total_violations_24h": total_violations_24h,
            "most_triggered_rules": [
                {"rule_name": rule_name, "count": count}
                for rule_name, count in most_triggered_rules
            ],
        },
    }


@router.get("/violations/{violation_id}")
async def get_violation(
    violation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a single violation with feedback."""
    from backend.services.guardrails.violation_service import ViolationService

    user_id = _get_user_id(current_user)
    result = ViolationService.get_violation(
        violation_id=violation_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if not result:
        raise HTTPException(status_code=404, detail="Violation not found")
    return {"success": True, "violation": result}


@router.post("/violations/{violation_id}/feedback")
async def submit_violation_feedback(
    violation_id: str,
    request: ViolationFeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Submit or update feedback on a violation."""
    from backend.services.guardrails.violation_service import ViolationService

    user_id = _get_user_id(current_user)
    result = ViolationService.upsert_feedback(
        violation_id=violation_id,
        user_id=user_id,
        rating=request.rating,
        comment=request.comment,
    )
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Violation not found")
    if result.get("error") == "invalid_rating":
        raise HTTPException(
            status_code=400, detail="Rating must be positive or negative"
        )
    return result


# Phase 3: Compliance view moved to backend/api/guardrails/compliance/routes.py
# (with proper filters for active workflows, agent nodes, owners, etc.)


# Phase 4: Admin platform metrics


@router.get("/admin/metrics", dependencies=[Depends(require_admin)])
async def get_platform_metrics(
    window: str = Query("30d"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Admin: Get platform-wide violation metrics."""
    from backend.services.guardrails.violation_service import ViolationService

    return {"success": True, **ViolationService.get_platform_metrics(window=window)}


# Phase 4: Policy versioning


@router.get("/policies/{policy_id}/versions")
async def list_policy_versions(
    policy_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all version records for a policy."""
    from backend.services.guardrails.violation_service import ViolationService

    user_id = _get_user_id(current_user)
    versions = ViolationService.list_policy_versions(
        policy_id=policy_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if versions is None:
        raise HTTPException(status_code=404, detail="Policy not found or access denied")
    return {"success": True, "versions": versions}


@router.get("/policies/{policy_id}/versions/{version_number}")
async def get_policy_version(
    policy_id: str,
    version_number: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a specific version snapshot for a policy."""
    from backend.services.guardrails.violation_service import ViolationService

    user_id = _get_user_id(current_user)
    version = ViolationService.get_policy_version(
        policy_id=policy_id,
        version_number=version_number,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"success": True, "version": version}


@router.post("/policies/{policy_id}/rollback")
async def rollback_policy(
    policy_id: str,
    request: RollbackPolicyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Rollback a policy to a prior version (creates a new version)."""
    from backend.services.guardrails.violation_service import ViolationService

    user_id = _get_user_id(current_user)
    result = ViolationService.rollback_policy(
        policy_id=policy_id,
        target_version=request.target_version,
        user_id=user_id,
        is_admin=_is_admin(current_user),
        change_summary=request.change_summary,
    )
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Policy not found")
    if result.get("error") == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied")
    if result.get("error") == "builtin_readonly":
        raise HTTPException(
            status_code=403,
            detail="Built-in policy packs cannot be modified. Clone to create an editable copy.",
        )
    if result.get("error") == "version_not_found":
        raise HTTPException(status_code=404, detail="Target version not found")
    return result


# Phase 4: Policy testing sandbox


@router.post("/policies/{policy_id}/test")
async def test_policy(
    policy_id: str,
    request: PolicyTestRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Test a policy config against sample content (no side effects)."""
    from backend.services.guardrails.policy_test_service import PolicyTestService

    user_id = _get_user_id(current_user)
    # Resolve policy config
    policy = GuardrailPolicyService.get_policy(
        policy_id=policy_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found or access denied")

    config = request.config_override or policy.get("config", {})

    try:
        result = await PolicyTestService.test(
            config=config,
            sample_input=request.sample_input,
            sample_output=request.sample_output,
            include_behavioral=request.include_behavioral,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.warning("[GUARDRAILS] Policy test sandbox error: %s", e)
        raise HTTPException(status_code=503, detail=f"Test evaluation failed: {e}")


# Phase 4: Effectiveness metrics


@router.get("/policies/{policy_id}/metrics")
async def get_policy_metrics(
    policy_id: str,
    window: str = Query("30d"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get effectiveness metrics for a policy."""
    from backend.services.guardrails.violation_service import ViolationService

    user_id = _get_user_id(current_user)
    result = ViolationService.get_policy_metrics(
        policy_id=policy_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
        window=window,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Policy not found or access denied")
    return {"success": True, **result}
