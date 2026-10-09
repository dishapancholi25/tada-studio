"""Service layer for guardrail policy CRUD, assignment, and resolution.

Provides business logic for managing shared guardrail policies,
assigning them to targets, and resolving the effective configuration
for a given execution context.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import cast, literal, or_, text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import joinedload
from sqlalchemy.types import Text

from backend.models.guardrails.guardrail_assignment import GuardrailAssignment
from backend.models.guardrails.guardrail_policy import GuardrailPolicy
from backend.services.database import get_db

logger = logging.getLogger(__name__)

try:
    from backend.models.guardrails.policy_version import GuardrailPolicyVersion
except ImportError:
    logger.error(
        "Failed to import GuardrailPolicyVersion — policy version history will be disabled. "
        "Ensure backend/models/guardrails/policy_version.py exists and is importable."
    )
    GuardrailPolicyVersion = None  # type: ignore[assignment,misc]


def _warm_python_filter_sandboxes(config: Dict[str, Any]) -> None:
    """Pre-build sandbox caches for any Python code filters in *config*.

    Runs in a background thread so it never blocks the request.
    """
    import concurrent.futures

    from backend.services.guardrails.filters.executors.python_sandbox import (
        get_shared_sandbox_executor,
    )

    filters = config.get("custom_filters", [])
    code_strings = [
        f.get("python_code", "").strip()
        for f in filters
        if f.get("filter_type") == "python_code" and f.get("python_code", "").strip()
    ]
    if not code_strings:
        return

    executor = get_shared_sandbox_executor()

    def _warm() -> None:
        for code in code_strings:
            try:
                executor._get_or_build_sandbox(code)
            except Exception:
                logger.debug("Sandbox warm on save failed for a filter", exc_info=True)

    # Fire-and-forget in a thread so the save response isn't delayed
    concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(_warm)


class GuardrailPolicyService:
    """Service for managing guardrail policies and their assignments."""

    @staticmethod
    def _policy_visible_to_user(
        policy: GuardrailPolicy,
        user_id: str,
        is_admin: bool,
        user_groups: Optional[List[str]] = None,
    ) -> bool:
        """Return whether a policy is visible to a user."""
        if is_admin or policy.created_by == user_id:
            return True

        visible = policy.visible_to_groups or []
        if "__all__" in visible:
            return True
        if policy.scope == "global":
            return True
        if policy.is_template:
            return True

        groups = user_groups if user_groups is not None else []
        return any(group in visible for group in groups)

    # ── Policy CRUD ──────────────────────────────────────────────

    @staticmethod
    def create_policy(
        name: str,
        config: Dict[str, Any],
        user_id: str,
        description: Optional[str] = None,
        scope: str = "user",
        is_compulsory: bool = False,
        applies_to: Optional[List[str]] = None,
        visible_to_groups: Optional[List[str]] = None,
        # Legacy alias – accepted but mapped to visible_to_groups
        shared_with: Optional[List[str]] = None,
        is_template: bool = False,
        tags: Optional[List[str]] = None,
        is_builtin: bool = False,
        change_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new guardrail policy."""
        from backend.models.guardrails.policy_version import GuardrailPolicyVersion
        from backend.services.groups.service import GroupService

        groups = visible_to_groups or shared_with or []

        # Validate groups exist (skip __all__ special token)
        groups_to_validate = [g for g in groups if g != "__all__"]
        if groups_to_validate:
            GroupService().validate_groups_exist(groups_to_validate)

        # Compulsory policies must have global scope so the resolver can find them
        if is_compulsory:
            scope = "global"

        with get_db() as db:
            policy = GuardrailPolicy(
                name=name,
                description=description,
                config=config,
                scope=scope,
                is_compulsory=is_compulsory,
                applies_to=applies_to or [],
                created_by=user_id,
                visible_to_groups=groups,
                shared_with=groups,
                is_template=is_template,
                is_builtin=is_builtin,
                tags=tags or [],
                version=1,
            )
            db.add(policy)
            db.flush()

            # Record initial version snapshot
            version_row = GuardrailPolicyVersion(
                id=str(uuid.uuid4()),
                policy_id=policy.id,
                version=1,
                config_snapshot=dict(config) if config else {},
                name_snapshot=name,
                description_snapshot=description,
                changed_by=user_id,
                change_summary=change_summary or "Initial version",
            )
            db.add(version_row)
            db.flush()

            result = policy.to_dict()
            logger.info("[GUARDRAILS] Policy created: %s (id=%s)", name, policy.id)

        _warm_python_filter_sandboxes(config)
        return result

    @staticmethod
    def list_policies(
        user_id: str,
        is_admin: bool = False,
        scope: Optional[str] = None,
        tags: Optional[List[str]] = None,
        applies_to: Optional[str] = None,
        is_template: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List policies visible to the user.

        Visibility mirrors the collections pattern:
          - Owner always sees their policies
          - Policies with visible_to_groups containing "__all__" are visible to everyone
          - Policies with visible_to_groups overlapping the user's groups are visible
          - Global-scope policies are visible to everyone (backwards compat)
          - Templates are visible to everyone
          - Admins see everything
        """
        from backend.services.groups.service import GroupService

        with get_db() as db:
            # Check whether the visible_to_groups column exists yet
            has_vtg = bool(
                db.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name='guardrail_policies' "
                        "AND column_name='visible_to_groups'"
                    )
                ).fetchone()
            )

            query = db.query(GuardrailPolicy).options(
                joinedload(GuardrailPolicy.creator)
            )

            if not is_admin:
                if has_vtg:
                    # Group-based visibility (same JSONB operators as collections)
                    all_visible = GuardrailPolicy.visible_to_groups.op("@>")(
                        text("'[\"__all__\"]'::jsonb")
                    )

                    user_groups = GroupService().get_user_groups(user_id)
                    if user_groups:
                        groups_overlap = GuardrailPolicy.visible_to_groups.op("?|")(
                            cast(literal(user_groups), PG_ARRAY(Text))
                        )
                        shared_condition = or_(all_visible, groups_overlap)
                    else:
                        shared_condition = all_visible

                    query = query.filter(
                        or_(
                            GuardrailPolicy.created_by == user_id,
                            GuardrailPolicy.scope == "global",
                            GuardrailPolicy.is_template.is_(True),
                            shared_condition,
                        )
                    )
                else:
                    # Legacy fallback before migration runs
                    query = query.filter(
                        or_(
                            GuardrailPolicy.created_by == user_id,
                            GuardrailPolicy.scope == "global",
                            GuardrailPolicy.is_template.is_(True),
                            GuardrailPolicy.shared_with.op("@>")(f'["{user_id}"]'),
                            GuardrailPolicy.shared_with.op("@>")('["all"]'),
                        )
                    )

            if scope:
                query = query.filter(GuardrailPolicy.scope == scope)
            if is_template is not None:
                query = query.filter(GuardrailPolicy.is_template == is_template)
            if search:
                query = query.filter(GuardrailPolicy.name.ilike(f"%{search}%"))
            if applies_to:
                query = query.filter(
                    or_(
                        GuardrailPolicy.applies_to.op("@>")(f'["{applies_to}"]'),
                        GuardrailPolicy.applies_to == cast(literal("[]"), GuardrailPolicy.applies_to.type),
                    )
                )

            query = query.order_by(GuardrailPolicy.created_at.desc())
            return [p.to_dict() for p in query.all()]

    @staticmethod
    def get_policy(
        policy_id: str, user_id: str, is_admin: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a single policy by ID."""
        from backend.services.groups.service import GroupService

        with get_db() as db:
            policy = (
                db.query(GuardrailPolicy)
                .options(joinedload(GuardrailPolicy.creator))
                .filter(GuardrailPolicy.id == policy_id)
                .first()
            )
            if not policy:
                return None
            user_groups = (
                None
                if is_admin or policy.created_by == user_id
                else GroupService().get_user_groups(user_id)
            )
            if not GuardrailPolicyService._policy_visible_to_user(
                policy,
                user_id,
                is_admin,
                user_groups,
            ):
                return None
            return policy.to_dict()

    @staticmethod
    def get_visible_policy_ids(
        policy_ids: List[str],
        user_id: str,
        is_admin: bool = False,
    ) -> set[str]:
        """Return the subset of policy IDs visible to the user."""
        unique_policy_ids = list({policy_id for policy_id in policy_ids if policy_id})
        if not unique_policy_ids:
            return set()
        if is_admin:
            return set(unique_policy_ids)

        from backend.services.groups.service import GroupService

        user_groups = GroupService().get_user_groups(user_id)
        with get_db() as db:
            policies = (
                db.query(GuardrailPolicy)
                .filter(GuardrailPolicy.id.in_(unique_policy_ids))
                .all()
            )
            return {
                policy.id
                for policy in policies
                if GuardrailPolicyService._policy_visible_to_user(
                    policy,
                    user_id,
                    is_admin,
                    user_groups,
                )
            }

    @staticmethod
    def update_policy(
        policy_id: str,
        user_id: str,
        is_admin: bool = False,
        changed_by: Optional[str] = None,
        change_summary: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """Update a policy. Creator, or admin for builtin policies, may update."""
        from backend.models.guardrails.policy_version import GuardrailPolicyVersion

        with get_db() as db:
            policy = (
                db.query(GuardrailPolicy)
                .filter(GuardrailPolicy.id == policy_id)
                .first()
            )
            if not policy:
                return None

            # Authorization check
            if not is_admin and policy.created_by != user_id:
                return None

            # Builtin policies can only be edited by admins
            if (
                policy.is_builtin or policy.created_by == "__system__"
            ) and not is_admin:
                return {"error": "builtin_readonly"}

            allowed_fields = {
                "name",
                "description",
                "config",
                "scope",
                "is_compulsory",
                "applies_to",
                "visible_to_groups",
                "shared_with",
                "is_template",
                "tags",
            }
            for key, value in kwargs.items():
                if key in allowed_fields and value is not None:
                    setattr(policy, key, value)

            new_version = (policy.version or 1) + 1
            policy.version = new_version

            # Record version snapshot
            version_row = GuardrailPolicyVersion(
                id=str(uuid.uuid4()),
                policy_id=policy_id,
                version=new_version,
                config_snapshot=dict(policy.config) if policy.config else {},
                name_snapshot=policy.name,
                description_snapshot=policy.description,
                changed_by=changed_by or user_id,
                change_summary=change_summary,
            )
            db.add(version_row)

            # Increment version tracking columns if they exist on the model
            if hasattr(policy, "version_count"):
                policy.version_count = new_version
            if hasattr(policy, "current_version"):
                policy.current_version = new_version
            db.flush()

            result = policy.to_dict()
            logger.info(
                "[GUARDRAILS] Policy updated: %s (id=%s)", policy.name, policy.id
            )

        if "config" in kwargs:
            _warm_python_filter_sandboxes(result.get("config", {}))
        return result

    @staticmethod
    def delete_policy(
        policy_id: str, user_id: str, is_admin: bool = False
    ) -> Dict[str, Any]:
        """Delete a policy. Blocked if compulsory (must deactivate first), builtin, or non-owner."""
        with get_db() as db:
            policy = (
                db.query(GuardrailPolicy)
                .filter(GuardrailPolicy.id == policy_id)
                .first()
            )
            if not policy:
                return {"error": "not_found"}
            if policy.is_builtin or policy.created_by == "__system__":
                return {"error": "builtin_cannot_delete"}
            if policy.is_compulsory and not is_admin:
                return {"error": "compulsory_cannot_delete"}
            if policy.is_compulsory:
                return {"error": "compulsory_active"}
            if not is_admin and policy.created_by != user_id:
                return {"error": "forbidden"}

            db.delete(policy)
            logger.info("[GUARDRAILS] Policy deleted: id=%s", policy_id)
            return {"success": True}

    # ── Visibility ───────────────────────────────────────────────

    @staticmethod
    def update_visibility(
        policy_id: str,
        user_id: str,
        visible_to_groups: List[str],
        is_admin: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Update which groups can see the policy.

        Mirrors the collections pattern:
          []            → private
          ["__all__"]   → visible to everyone
          ["grp", …]   → visible to specific groups

        Only the policy creator (or an admin) may change visibility.
        """
        from backend.services.groups.service import GroupService

        with get_db() as db:
            policy = (
                db.query(GuardrailPolicy)
                .options(joinedload(GuardrailPolicy.creator))
                .filter(GuardrailPolicy.id == policy_id)
                .first()
            )
            if not policy:
                return None
            if not is_admin and policy.created_by != user_id:
                return None

            # Validate groups exist (skip __all__ special token)
            groups_to_validate = [g for g in visible_to_groups if g != "__all__"]
            if groups_to_validate:
                GroupService().validate_groups_exist(groups_to_validate)

            policy.visible_to_groups = visible_to_groups
            # Keep legacy column in sync
            policy.shared_with = visible_to_groups
            db.flush()

            logger.info(
                "[GUARDRAILS] Policy visibility updated: id=%s, groups=%s",
                policy_id,
                visible_to_groups,
            )
            return policy.to_dict()

    # Legacy aliases kept for backwards compat
    @staticmethod
    def share_policy(
        policy_id: str, user_id: str, share_with: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Legacy: Add groups to policy visibility."""
        with get_db() as db:
            policy = (
                db.query(GuardrailPolicy)
                .filter(GuardrailPolicy.id == policy_id)
                .first()
            )
            if not policy or policy.created_by != user_id:
                return None
            current = list(policy.visible_to_groups or [])
            for entry in share_with:
                if entry not in current:
                    current.append(entry)
            policy.visible_to_groups = current
            policy.shared_with = current
            db.flush()
            return policy.to_dict()

    @staticmethod
    def unshare_policy(
        policy_id: str, user_id: str, remove_user: str
    ) -> Optional[Dict[str, Any]]:
        """Legacy: Remove a group from policy visibility."""
        with get_db() as db:
            policy = (
                db.query(GuardrailPolicy)
                .filter(GuardrailPolicy.id == policy_id)
                .first()
            )
            if not policy or policy.created_by != user_id:
                return None
            current = list(policy.visible_to_groups or [])
            if remove_user in current:
                current.remove(remove_user)
            policy.visible_to_groups = current
            policy.shared_with = current
            db.flush()
            return policy.to_dict()

    # ── Clone ────────────────────────────────────────────────────

    @staticmethod
    def clone_policy(
        policy_id: str,
        user_id: str,
        name_override: Optional[str] = None,
        is_admin: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Clone a policy for the current user."""
        from backend.models.guardrails.policy_version import GuardrailPolicyVersion

        if not GuardrailPolicyService.get_policy(policy_id, user_id, is_admin):
            return None

        with get_db() as db:
            source = (
                db.query(GuardrailPolicy)
                .filter(GuardrailPolicy.id == policy_id)
                .first()
            )
            if not source:
                return None
            clone_name = name_override or f"{source.name} (Copy)"
            clone = GuardrailPolicy(
                name=clone_name,
                description=source.description,
                config=dict(source.config) if source.config else {},
                scope="user",
                is_compulsory=False,
                is_builtin=False,
                applies_to=list(source.applies_to) if source.applies_to else [],
                created_by=user_id,
                visible_to_groups=[],
                shared_with=[],
                is_template=False,
                tags=list(source.tags) if source.tags else [],
                version=1,
            )
            db.add(clone)
            db.flush()

            # Record initial version snapshot for clone
            version_row = GuardrailPolicyVersion(
                id=str(uuid.uuid4()),
                policy_id=clone.id,
                version=1,
                config_snapshot=dict(clone.config) if clone.config else {},
                name_snapshot=clone.name,
                description_snapshot=clone.description,
                changed_by=user_id,
                change_summary=f"Cloned from policy {policy_id}",
            )
            db.add(version_row)
            db.flush()

            result = clone.to_dict()
            logger.info("[GUARDRAILS] Policy cloned from %s to %s", policy_id, clone.id)
            return result

    # ── Assignments ──────────────────────────────────────────────

    @staticmethod
    def create_assignment(
        policy_id: str,
        target_type: str,
        target_id: str,
        assigned_by: str,
        workflow_id: Optional[str] = None,
        priority: int = 0,
        override_mode: str = "merge",
    ) -> Dict[str, Any]:
        """Create a policy assignment to a target."""
        with get_db() as db:
            assignment = GuardrailAssignment(
                policy_id=policy_id,
                target_type=target_type,
                target_id=target_id,
                workflow_id=workflow_id,
                priority=priority,
                override_mode=override_mode,
                assigned_by=assigned_by,
            )
            db.add(assignment)
            db.flush()
            result = assignment.to_dict()
            logger.info(
                "[GUARDRAILS] Assignment created: policy=%s -> %s/%s",
                policy_id,
                target_type,
                target_id,
            )
            return result

    @staticmethod
    def update_assignment(
        assignment_id: str,
        user_id: str,
        is_admin: bool = False,
        priority: Optional[int] = None,
        override_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing policy assignment (priority and/or override_mode)."""
        with get_db() as db:
            assignment = (
                db.query(GuardrailAssignment)
                .options(joinedload(GuardrailAssignment.policy))
                .filter(GuardrailAssignment.id == assignment_id)
                .first()
            )
            if not assignment:
                return {"error": "not_found"}
            if not is_admin and assignment.assigned_by != user_id:
                return {"error": "forbidden"}
            if priority is not None:
                assignment.priority = priority
            if override_mode is not None:
                assignment.override_mode = override_mode
            db.flush()
            result = assignment.to_dict()
            logger.info(
                "[GUARDRAILS] Assignment updated: id=%s priority=%s",
                assignment_id,
                priority,
            )
            return result

    @staticmethod
    def delete_assignment(
        assignment_id: str, user_id: str, is_admin: bool = False
    ) -> Dict[str, Any]:
        """Delete a policy assignment."""
        with get_db() as db:
            assignment = (
                db.query(GuardrailAssignment)
                .options(joinedload(GuardrailAssignment.policy))
                .filter(GuardrailAssignment.id == assignment_id)
                .first()
            )
            if not assignment:
                return {"error": "not_found"}
            if not is_admin and assignment.assigned_by != user_id:
                return {"error": "forbidden"}
            db.delete(assignment)
            logger.info("[GUARDRAILS] Assignment deleted: id=%s", assignment_id)
            return {"success": True}

    @staticmethod
    def list_assignments(
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        policy_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List assignments with optional filters."""
        with get_db() as db:
            query = (
                db.query(GuardrailAssignment)
                .options(joinedload(GuardrailAssignment.policy))
                .order_by(GuardrailAssignment.priority.asc())
            )
            if target_type:
                query = query.filter(GuardrailAssignment.target_type == target_type)
            if target_id:
                query = query.filter(GuardrailAssignment.target_id == target_id)
            if workflow_id:
                query = query.filter(GuardrailAssignment.workflow_id == workflow_id)
            if policy_id:
                query = query.filter(GuardrailAssignment.policy_id == policy_id)
            return [a.to_dict() for a in query.all()]

    # ── Admin compulsory ─────────────────────────────────────────

    @staticmethod
    def list_compulsory_policies() -> List[Dict[str, Any]]:
        """List all compulsory (admin-enforced) policies."""
        with get_db() as db:
            policies = (
                db.query(GuardrailPolicy)
                .options(joinedload(GuardrailPolicy.creator))
                .filter(
                    GuardrailPolicy.is_compulsory.is_(True),
                    GuardrailPolicy.scope == "global",
                )
                .order_by(GuardrailPolicy.created_at.asc())
                .all()
            )
            return [p.to_dict() for p in policies]

    @staticmethod
    def set_compulsory(policy_id: str, is_compulsory: bool) -> Optional[Dict[str, Any]]:
        """Set or unset a policy as compulsory (admin only)."""
        with get_db() as db:
            policy = (
                db.query(GuardrailPolicy)
                .filter(GuardrailPolicy.id == policy_id)
                .first()
            )
            if not policy:
                return None
            policy.is_compulsory = is_compulsory
            if is_compulsory:
                policy.scope = "global"
            db.flush()
            result = policy.to_dict()
            logger.info(
                "[GUARDRAILS] Policy compulsory status changed: id=%s, compulsory=%s",
                policy_id,
                is_compulsory,
            )
            return result

    # ── Templates ────────────────────────────────────────────────

    @staticmethod
    def list_templates() -> List[Dict[str, Any]]:
        """List all policies marked as templates."""
        with get_db() as db:
            policies = (
                db.query(GuardrailPolicy)
                .options(joinedload(GuardrailPolicy.creator))
                .filter(GuardrailPolicy.is_template.is_(True))
                .order_by(GuardrailPolicy.name.asc())
                .all()
            )
            return [p.to_dict() for p in policies]

    # ── Resolution ─────────────────────────────────────────────
    # Pipeline resolution is handled by LayeredPolicyResolver directly.
    # See backend/services/guardrails/resolver.py for resolve_as_pipeline()
    # and resolve_tool_pipelines().
