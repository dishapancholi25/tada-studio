"""Violation persistence service for recording guardrail violations to the database.

Provides fire-and-forget async insertion of violation events alongside
the WebSocket emission path. DB insert failures are logged but never
propagated to the execution path.
"""

import logging
import uuid
from typing import Any, Dict, Optional

from backend.services.database import get_db

logger = logging.getLogger(__name__)


class ViolationPersistenceService:
    """Persists violation events to the database asynchronously.

    Called from the guardrail evaluators alongside the WebSocket emit.
    Uses synchronous DB access wrapped in a try/except so that any
    failure is swallowed -- violation persistence is non-critical to
    execution correctness.
    """

    @staticmethod
    def record(
        rule_name: str,
        category: str,
        severity: str,
        action_taken: str,
        execution_id: str,
        policy_id: Optional[str] = None,
        policy_name: Optional[str] = None,
        message: Optional[str] = None,
        node_execution_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_node_id: Optional[str] = None,
        agent_node_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[str]:
        """Insert a violation record. Returns the new violation UUID or None on failure.

        This method is synchronous and designed for fire-and-forget use inside
        async contexts via asyncio.create_task or BackgroundTasks.
        """
        try:
            from backend.models.guardrails.violation import GuardrailViolation

            violation_id = str(uuid.uuid4())
            with get_db() as db:
                violation = GuardrailViolation(
                    id=violation_id,
                    policy_id=policy_id,
                    policy_name=policy_name,
                    rule_name=rule_name,
                    category=category,
                    severity=severity,
                    action_taken=action_taken,
                    message=message,
                    execution_id=execution_id,
                    node_execution_id=node_execution_id,
                    workflow_id=workflow_id,
                    agent_node_id=agent_node_id,
                    agent_node_name=agent_node_name,
                    tool_name=tool_name,
                    user_id=user_id,
                )
                db.add(violation)
                db.flush()
            logger.info(
                "[GUARDRAIL-PERSIST] Recorded violation: id=%s policy=%s rule=%s severity=%s execution=%s",
                violation_id,
                policy_id,
                rule_name,
                severity,
                execution_id,
            )
            return violation_id
        except Exception as e:
            logger.warning(
                "[GUARDRAIL-PERSIST] Failed to record violation: rule=%s execution=%s error=%s",
                rule_name,
                execution_id,
                e,
            )
            return None

    @staticmethod
    def persist_violation(
        violation=None,
        *,
        category: Optional[str] = None,
        rule_name: Optional[str] = None,
        severity: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        action_taken: Optional[str] = None,
        graph_execution_id: Optional[str] = None,
        node_execution_id: Optional[str] = None,
        policy_id: Optional[str] = None,
        policy_name: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_node_id: Optional[str] = None,
        agent_node_name: Optional[str] = None,
        user_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        is_compulsory: bool = False,
        sandbox: bool = False,
    ) -> Optional[str]:
        """Persist a guardrail violation event to the database.

        Accepts either a Violation dataclass as the first positional arg,
        or individual field kwargs. Explicit kwargs take precedence over
        violation object fields.

        Args:
            violation: Optional Violation dataclass instance.
            category: Violation category override (e.g. "input", "tool_egress").
            rule_name: Rule name (fallback if no violation object).
            severity: Severity level (fallback if no violation object).
            message: Human-readable message (fallback if no violation object).
            details: Additional details dict (fallback if no violation object).
            action_taken: Action taken (blocked, warned, redacted, none).
            graph_execution_id: Parent graph execution ID.
            node_execution_id: Node execution ID.
            policy_id: Guardrail policy ID.
            policy_name: Guardrail policy name.
            workflow_id: Workflow ID.
            agent_node_id: Agent node ID.
            agent_node_name: Agent node name.
            user_id: User ID.
            tool_name: Tool name (stored in details JSONB for location display).
            is_compulsory: Whether the violated policy is compulsory.
            sandbox: If True, skip persistence (sandbox evaluation).

        Returns:
            The UUID of the persisted event, or None on skip/error.
        """
        if sandbox:
            logger.info("[GUARDRAILS-PERSIST] Skipping persistence for sandbox evaluation")
            return None

        # Resolve fields: explicit kwargs take precedence over violation object fields.
        # This allows callers to override the category (e.g. "input" instead of
        # the generic "behavioral" that scanners produce) while still falling back
        # to the violation object for fields that weren't explicitly provided.
        if violation is not None:
            v_category = category or getattr(violation, "category", None)
            v_rule_name = rule_name or getattr(violation, "rule_name", None)
            v_severity = severity or getattr(violation, "severity", None)
            v_message = message or getattr(violation, "message", None)
            v_details = details or getattr(violation, "details", None)
        else:
            v_category = category
            v_rule_name = rule_name
            v_severity = severity
            v_message = message
            v_details = details

        # Inject tool_name into details so it's available when loading from DB
        if tool_name:
            if isinstance(v_details, dict):
                v_details = {**v_details, "tool_name": tool_name}
            else:
                v_details = {"tool_name": tool_name}

        try:
            from backend.models.guardrails.violation_event import GuardrailViolationEvent

            with get_db() as db:
                event = GuardrailViolationEvent(
                    graph_execution_id=graph_execution_id,
                    node_execution_id=node_execution_id,
                    policy_id=policy_id,
                    policy_name=policy_name,
                    rule_name=v_rule_name,
                    category=v_category,
                    severity=v_severity,
                    action_taken=action_taken,
                    message=v_message,
                    details=v_details if isinstance(v_details, dict) else None,
                    workflow_id=workflow_id,
                    agent_node_id=agent_node_id,
                    agent_node_name=agent_node_name,
                    user_id=user_id,
                    is_compulsory_policy=is_compulsory,
                )
                db.add(event)
                db.flush()
                event_id = str(event.id)
                logger.info(
                    "[GUARDRAILS-PERSIST] Persisted violation id=%s rule=%s severity=%s",
                    event_id,
                    v_rule_name,
                    v_severity,
                )
                return event_id
        except Exception as e:
            logger.warning("[GUARDRAILS-PERSIST] DB write failed: %s", e)
            return None
