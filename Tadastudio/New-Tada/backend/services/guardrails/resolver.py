"""Layered policy resolver for guardrail configuration.

Resolves guardrails pipelines by collecting compulsory (admin-enforced)
policies and user/org/workflow/tool/model/node assignment layers into
ordered lists of GuardrailsConfig instances.  Each config in the pipeline
retains its policy_id, policy_name, and priority so that downstream
evaluators can attribute violations to specific policies.

Includes a TTL cache for compulsory policies to avoid per-execution DB queries.
"""

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import joinedload

from backend.models.guardrails.guardrail_assignment import GuardrailAssignment
from backend.models.guardrails.guardrail_policy import GuardrailPolicy
from backend.models.workflow.configs.guardrails import GuardrailsConfig
from backend.services.database import get_db

logger = logging.getLogger(__name__)

# Module-level TTL cache for compulsory policies
_compulsory_cache: Dict[str, Any] = {}
_COMPULSORY_TTL_SECONDS = 60


class LayeredPolicyResolver:
    """Resolves guardrails pipelines through layered policy collection."""

    @staticmethod
    def _get_compulsory_policies() -> List[Dict[str, Any]]:
        """Fetch compulsory policies, using a TTL cache to reduce DB load.

        On DB failure the cache is NOT overwritten with an empty list:
        - If a previous cached value exists it is served as a stale fallback.
        - If no cached value exists the empty result is returned *without*
          populating the cache so the next call retries immediately.
        """
        global _compulsory_cache

        if (
            _compulsory_cache
            and "fetched_at" in _compulsory_cache
            and time.time() - _compulsory_cache["fetched_at"] < _COMPULSORY_TTL_SECONDS
        ):
            policies = _compulsory_cache["policies"]
            logger.debug(
                "[GUARDRAILS-COMPULSORY] Cache hit — returning %d compulsory policies",
                len(policies),
            )
            return policies

        try:
            with get_db() as db:
                rows = (
                    db.query(GuardrailPolicy)
                    .filter(
                        GuardrailPolicy.is_compulsory.is_(True),
                        GuardrailPolicy.scope == "global",
                    )
                    .all()
                )
                policies = [
                    {"source": "compulsory", "policy_id": p.id, "policy_name": p.name, "config": p.config, "applies_to": p.applies_to or []}
                    for p in rows
                ]
        except Exception as e:
            logger.warning("[GUARDRAILS-COMPULSORY] DB fetch failed: %s", e)
            # Serve stale cached value if available; otherwise return uncached empty list
            if _compulsory_cache and "policies" in _compulsory_cache:
                logger.info(
                    "[GUARDRAILS-COMPULSORY] Serving %d stale cached policies after DB failure",
                    len(_compulsory_cache["policies"]),
                )
                return _compulsory_cache["policies"]
            logger.warning(
                "[GUARDRAILS-COMPULSORY] No cached fallback available — returning empty (will retry next call)"
            )
            return []

        _compulsory_cache = {"policies": policies, "fetched_at": time.time()}
        logger.info(
            "[GUARDRAILS-COMPULSORY] Cache miss — fetched %d compulsory policies from DB",
            len(policies),
        )
        return policies

    @staticmethod
    def _merge_compulsory(
        compulsory_layers: List[Dict[str, Any]],
        user_layers: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Prepend compulsory layers before user layers.

        Compulsory rules are additive and non-weakening by virtue of being
        first in the pipeline order.
        """
        return compulsory_layers + user_layers

    @staticmethod
    def resolve_as_pipeline(
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> List[GuardrailsConfig]:
        """Resolve an ordered pipeline of GuardrailsConfig instances for an agent.

        Collects configs from all applicable layers without merging them:
        1. Admin compulsory policies (scope=global, is_compulsory=true) — cached
        2. Organization-level policies (scope=organization)
        3. Workflow-level assignments (target_type=workflow)
        4. Model-specific policies (target_type=model)
        5. Agent-node assignments (target_type=agent_node)

        Compulsory configs are placed first (priority=0).  User-assigned configs
        are sorted by their assignment priority ascending.

        Returns:
            Ordered list of GuardrailsConfig instances, each stamped with
            policy_id, policy_name, and priority.
        """
        # Determine which compulsory applies_to types are relevant
        target_types: List[str] = []
        if node_id:
            target_types.append("agent")
        if workflow_id:
            target_types.append("workflow")
        if model_id:
            target_types.append("model")

        # Layer 1: Compulsory (cached), filtered by applies_to
        all_compulsory = LayeredPolicyResolver._get_compulsory_policies()
        compulsory_configs: List[GuardrailsConfig] = []
        for layer in all_compulsory:
            if layer.get("applies_to") and not any(t in layer["applies_to"] for t in target_types):
                continue
            cfg = GuardrailsConfig.from_dict(layer.get("config", {}))
            cfg.priority = 0
            cfg.policy_id = layer.get("policy_id", "")
            cfg.policy_name = layer.get("policy_name", "")
            compulsory_configs.append(cfg)

        # Layers 2–5: User/org/assignment layers
        user_configs: List[GuardrailsConfig] = []

        with get_db() as db:
            # Layer 2: Organization-level
            org_policies = (
                db.query(GuardrailPolicy)
                .filter(
                    GuardrailPolicy.scope == "organization",
                    GuardrailPolicy.is_compulsory.is_(False),
                )
                .all()
            )
            for p in org_policies:
                cfg = GuardrailsConfig.from_dict(p.config or {})
                cfg.priority = 0
                cfg.policy_id = p.id
                cfg.policy_name = p.name
                user_configs.append(cfg)

            # Layer 3: Workflow-level assignments
            if workflow_id:
                wf_assignments = (
                    db.query(GuardrailAssignment)
                    .options(joinedload(GuardrailAssignment.policy))
                    .filter(
                        GuardrailAssignment.target_type == "workflow",
                        GuardrailAssignment.target_id == workflow_id,
                    )
                    .order_by(GuardrailAssignment.priority.asc())
                    .all()
                )
                for a in wf_assignments:
                    if a.policy:
                        cfg = GuardrailsConfig.from_dict(a.policy.config or {})
                        cfg.priority = a.priority
                        cfg.policy_id = a.policy_id
                        cfg.policy_name = a.policy.name
                        user_configs.append(cfg)

            # Layer 4: Model-specific
            if model_id:
                model_assignments = (
                    db.query(GuardrailAssignment)
                    .options(joinedload(GuardrailAssignment.policy))
                    .filter(
                        GuardrailAssignment.target_type == "model",
                        GuardrailAssignment.target_id == model_id,
                    )
                    .order_by(GuardrailAssignment.priority.asc())
                    .all()
                )
                for a in model_assignments:
                    if a.policy:
                        cfg = GuardrailsConfig.from_dict(a.policy.config or {})
                        cfg.priority = a.priority
                        cfg.policy_id = a.policy_id
                        cfg.policy_name = a.policy.name
                        user_configs.append(cfg)

            # Layer 5: Agent-node assignments
            if node_id:
                node_assignments = (
                    db.query(GuardrailAssignment)
                    .options(joinedload(GuardrailAssignment.policy))
                    .filter(
                        GuardrailAssignment.target_type == "agent_node",
                        GuardrailAssignment.target_id == node_id,
                    )
                    .order_by(GuardrailAssignment.priority.asc())
                    .all()
                )
                for a in node_assignments:
                    if a.policy:
                        cfg = GuardrailsConfig.from_dict(a.policy.config or {})
                        cfg.priority = a.priority
                        cfg.policy_id = a.policy_id
                        cfg.policy_name = a.policy.name
                        user_configs.append(cfg)

        # Sort user configs by priority ascending
        user_configs.sort(key=lambda c: c.priority)

        return compulsory_configs + user_configs

    @staticmethod
    def resolve_tool_pipelines(
        tool_names: List[str],
    ) -> Dict[str, List[GuardrailsConfig]]:
        """Resolve per-tool pipelines of GuardrailsConfig instances.

        Uses a single batched query for all tools. Compulsory policies with
        ``applies_to`` containing ``"tool"`` are prepended to each tool's
        pipeline.

        Returns:
            Mapping of tool_node_id → ordered list of GuardrailsConfig instances.
            Tools with no assignments are absent from the result.
        """
        if not tool_names:
            return {}

        # Build compulsory configs that apply to tools
        all_compulsory = LayeredPolicyResolver._get_compulsory_policies()
        tool_compulsory: List[GuardrailsConfig] = []
        for layer in all_compulsory:
            if layer.get("applies_to") and "tool" not in layer["applies_to"]:
                continue
            cfg = GuardrailsConfig.from_dict(layer.get("config", {}))
            cfg.priority = 0
            cfg.policy_id = layer.get("policy_id", "")
            cfg.policy_name = layer.get("policy_name", "")
            tool_compulsory.append(cfg)

        tool_pipelines: Dict[str, List[GuardrailsConfig]] = defaultdict(list)

        with get_db() as db:
            all_assignments = (
                db.query(GuardrailAssignment)
                .options(joinedload(GuardrailAssignment.policy))
                .filter(
                    GuardrailAssignment.target_type == "tool",
                    GuardrailAssignment.target_id.in_(tool_names),
                )
                .order_by(
                    GuardrailAssignment.target_id.asc(),
                    GuardrailAssignment.priority.asc(),
                )
                .all()
            )
            for a in all_assignments:
                if a.policy:
                    cfg = GuardrailsConfig.from_dict(a.policy.config or {})
                    cfg.priority = a.priority
                    cfg.policy_id = a.policy_id
                    cfg.policy_name = a.policy.name
                    tool_pipelines[a.target_id].append(cfg)

        # Prepend tool-applicable compulsory configs to each tool
        if tool_compulsory:
            for tool_id in tool_pipelines:
                tool_pipelines[tool_id] = list(tool_compulsory) + tool_pipelines[tool_id]

        return dict(tool_pipelines)

    @staticmethod
    def invalidate_cache() -> None:
        """Clear the compulsory policy cache."""
        global _compulsory_cache
        _compulsory_cache = {}
        logger.info("[GUARDRAILS-COMPULSORY] Cache invalidated")
