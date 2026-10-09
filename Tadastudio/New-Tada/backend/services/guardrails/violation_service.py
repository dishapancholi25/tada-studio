"""Service layer for guardrail violation management.

Provides queries for the violation dashboard, execution history tab,
violation detail with feedback, and compliance view.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import joinedload

from backend.services.database import get_db

logger = logging.getLogger(__name__)


class ViolationService:
    """Service for querying and managing guardrail violations."""

    # ── Violations ───────────────────────────────────────────────

    @staticmethod
    def list_violations(
        user_id: str,
        is_admin: bool = False,
        policy_id: Optional[str] = None,
        rule_name: Optional[str] = None,
        severity: Optional[str] = None,
        workflow_id: Optional[str] = None,
        agent_node_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List violations with scoped access control and filters."""
        from backend.models.guardrails.violation_event import GuardrailViolationEvent
        from backend.models.guardrails.violation_feedback import GuardrailViolationFeedback
        from backend.models.workflows.workflow import Workflow

        with get_db() as db:
            q = db.query(GuardrailViolationEvent, Workflow.name.label("workflow_name")).outerjoin(
                Workflow, GuardrailViolationEvent.workflow_id == Workflow.id
            )

            # Scoped access: non-admins only see their own violations
            if not is_admin:
                q = q.filter(GuardrailViolationEvent.user_id == user_id)

            # Mandatory time range (enables composite index)
            if from_ts is None:
                from_ts = datetime.now(timezone.utc) - timedelta(days=30)
            q = q.filter(GuardrailViolationEvent.created_at >= from_ts)
            if to_ts:
                q = q.filter(GuardrailViolationEvent.created_at <= to_ts)

            if policy_id:
                q = q.filter(GuardrailViolationEvent.policy_id == policy_id)
            if rule_name:
                q = q.filter(GuardrailViolationEvent.rule_name.ilike(f"%{rule_name}%"))
            if severity:
                q = q.filter(GuardrailViolationEvent.severity == severity)
            if workflow_id:
                q = q.filter(GuardrailViolationEvent.workflow_id == workflow_id)
            if agent_node_id:
                q = q.filter(GuardrailViolationEvent.agent_node_id == agent_node_id)
            if execution_id:
                q = q.filter(GuardrailViolationEvent.graph_execution_id == execution_id)

            total = q.count()
            rows = q.order_by(GuardrailViolationEvent.created_at.desc()).offset(offset).limit(limit).all()

            # Fetch feedback counts per violation
            violation_ids = [row[0].id for row in rows]
            feedback_counts: Dict[str, Dict[str, int]] = {}
            if violation_ids:
                fb_rows = (
                    db.query(
                        GuardrailViolationFeedback.violation_event_id,
                        GuardrailViolationFeedback.rating,
                        sa_func.count(GuardrailViolationFeedback.id).label("cnt"),
                    )
                    .filter(GuardrailViolationFeedback.violation_event_id.in_(violation_ids))
                    .group_by(
                        GuardrailViolationFeedback.violation_event_id,
                        GuardrailViolationFeedback.rating,
                    )
                    .all()
                )
                for fb_row in fb_rows:
                    if fb_row.violation_event_id not in feedback_counts:
                        feedback_counts[fb_row.violation_event_id] = {"total": 0, "negative": 0}
                    feedback_counts[fb_row.violation_event_id]["total"] += fb_row.cnt
                    if fb_row.rating == "negative":
                        feedback_counts[fb_row.violation_event_id]["negative"] += fb_row.cnt

            result_list = []
            for v, wf_name in rows:
                d = v.to_dict()
                d["workflow_name"] = wf_name
                fc = feedback_counts.get(v.id, {"total": 0, "negative": 0})
                d["feedback_count"] = fc["total"]
                d["false_positive_count"] = fc["negative"]
                result_list.append(d)

            return {
                "violations": result_list,
                "total": total,
                "has_more": (offset + limit) < total,
                "limit": limit,
                "offset": offset,
            }

    @staticmethod
    def get_violation(
        violation_id: str,
        user_id: str,
        is_admin: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Get a single violation with feedback list."""
        from backend.models.guardrails.violation_event import GuardrailViolationEvent
        from backend.models.workflows.workflow import Workflow

        with get_db() as db:
            row = (
                db.query(GuardrailViolationEvent, Workflow.name.label("workflow_name"))
                .outerjoin(Workflow, GuardrailViolationEvent.workflow_id == Workflow.id)
                .options(joinedload(GuardrailViolationEvent.feedback))
                .filter(GuardrailViolationEvent.id == violation_id)
                .first()
            )
            if not row:
                return None
            violation, wf_name = row
            if not is_admin and violation.user_id != user_id:
                return None

            d = violation.to_dict()
            d["workflow_name"] = wf_name
            d["feedbacks"] = [f.to_dict() for f in violation.feedback]
            # Aggregate counts
            d["feedback_count"] = len(violation.feedback)
            d["false_positive_count"] = sum(1 for f in violation.feedback if f.rating == "negative")
            return d

    # ── Feedback ─────────────────────────────────────────────────

    @staticmethod
    def upsert_feedback(
        violation_id: str,
        user_id: str,
        rating: str,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit or update feedback on a violation (upsert)."""
        from backend.models.guardrails.violation_event import GuardrailViolationEvent
        from backend.models.guardrails.violation_feedback import GuardrailViolationFeedback

        if rating not in ("positive", "negative"):
            return {"error": "invalid_rating"}

        with get_db() as db:
            # Verify violation exists
            violation = db.query(GuardrailViolationEvent).filter(GuardrailViolationEvent.id == violation_id).first()
            if not violation:
                return {"error": "not_found"}

            existing = (
                db.query(GuardrailViolationFeedback)
                .filter(
                    GuardrailViolationFeedback.violation_event_id == violation_id,
                    GuardrailViolationFeedback.user_id == user_id,
                )
                .first()
            )
            if existing:
                existing.rating = rating
                existing.comment = comment
                db.flush()
                feedback_id = existing.id
            else:
                feedback = GuardrailViolationFeedback(
                    id=str(uuid.uuid4()),
                    violation_event_id=violation_id,
                    user_id=user_id,
                    rating=rating,
                    comment=comment,
                )
                db.add(feedback)
                db.flush()
                feedback_id = feedback.id

            logger.info(
                "[GUARDRAILS] Feedback upserted: violation=%s user=%s rating=%s",
                violation_id,
                user_id,
                rating,
            )
            return {"success": True, "feedback_id": feedback_id}

    # ── Compliance view ──────────────────────────────────────────

    @staticmethod
    def get_compliance_summary() -> Dict[str, Any]:
        """Return enforcement summary and unprotected assets for admin compliance view."""
        from backend.models.guardrails.guardrail_policy import GuardrailPolicy

        with get_db() as db:
            # Enforcement summary
            enforce_count = db.query(sa_func.count(GuardrailPolicy.id)).scalar() or 0
            # Count by enforcement_mode within config JSONB
            compulsory_count = (
                db.query(sa_func.count(GuardrailPolicy.id))
                .filter(GuardrailPolicy.is_compulsory.is_(True))
                .scalar()
                or 0
            )

            # For simplicity, aggregate config enforcement_mode as text extraction
            from sqlalchemy import text

            rows = db.execute(
                text("""
                    SELECT
                        COALESCE(config->>'enforcement_mode', 'enforce') as mode,
                        COUNT(*) as cnt
                    FROM guardrail_policies
                    GROUP BY COALESCE(config->>'enforcement_mode', 'enforce')
                """)
            ).fetchall()
            mode_counts = {row[0]: row[1] for row in rows}

            # Unprotected workflows: workflows with no guardrail_assignments targeting them
            # and no compulsory policy exists
            if compulsory_count > 0:
                # All workflows are covered by the compulsory layer
                unprotected_workflows = []
                unprotected_nodes = []
            else:
                # Find workflows without any assignment
                wf_rows = db.execute(
                    text("""
                        SELECT w.id, w.name, w.created_by_user_id
                        FROM workflows w
                        WHERE NOT EXISTS (
                            SELECT 1 FROM guardrail_assignments ga
                            WHERE ga.workflow_id = w.id
                               OR (ga.target_type = 'workflow' AND ga.target_id = w.id)
                        )
                        ORDER BY w.name
                        LIMIT 100
                    """)
                ).fetchall()
                unprotected_workflows = [
                    {"workflow_id": r[0], "workflow_name": r[1], "created_by": r[2]}
                    for r in wf_rows
                ]

                # Unprotected agent nodes: agent nodes in workflows without node-level assignments
                node_rows = db.execute(
                    text("""
                        SELECT DISTINCT
                            w.id as workflow_id,
                            w.name as workflow_name,
                            ne.node_id,
                            ne.node_name
                        FROM node_executions ne
                        JOIN graph_executions ge ON ne.graph_execution_id = ge.id
                        JOIN workflows w ON ge.workflow_id = w.id
                        WHERE ne.node_type = 'AGENT'
                          AND NOT EXISTS (
                              SELECT 1 FROM guardrail_assignments ga
                              WHERE ga.target_type = 'agent_node'
                                AND ga.target_id = ne.node_id
                          )
                        ORDER BY w.name, ne.node_name
                        LIMIT 100
                    """)
                ).fetchall()
                unprotected_nodes = [
                    {
                        "workflow_id": r[0],
                        "workflow_name": r[1],
                        "node_id": r[2],
                        "node_name": r[3],
                    }
                    for r in node_rows
                ]

            return {
                "enforcement_summary": {
                    "enforce_count": mode_counts.get("enforce", 0),
                    "audit_count": mode_counts.get("audit", 0),
                    "disabled_count": mode_counts.get("disabled", 0),
                    "compulsory_count": compulsory_count,
                    "total_policies": enforce_count,
                },
                "unprotected_workflows": unprotected_workflows,
                "unprotected_agent_nodes": unprotected_nodes,
            }

    # ── Policy versions ──────────────────────────────────────────

    @staticmethod
    def list_policy_versions(
        policy_id: str,
        user_id: str,
        is_admin: bool = False,
    ) -> Optional[List[Dict[str, Any]]]:
        """List all version records for a policy."""
        from backend.models.guardrails.guardrail_policy import GuardrailPolicy
        from backend.models.guardrails.policy_version import GuardrailPolicyVersion

        with get_db() as db:
            policy = db.query(GuardrailPolicy).filter(GuardrailPolicy.id == policy_id).first()
            if not policy:
                return None
            if not is_admin and policy.created_by != user_id:
                return None

            versions = (
                db.query(GuardrailPolicyVersion)
                .filter(GuardrailPolicyVersion.policy_id == policy_id)
                .order_by(GuardrailPolicyVersion.version.desc())
                .all()
            )
            return [v.to_dict() for v in versions]

    @staticmethod
    def get_policy_version(
        policy_id: str,
        version_number: int,
        user_id: str,
        is_admin: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific version snapshot for a policy."""
        from backend.models.guardrails.guardrail_policy import GuardrailPolicy
        from backend.models.guardrails.policy_version import GuardrailPolicyVersion

        with get_db() as db:
            policy = db.query(GuardrailPolicy).filter(GuardrailPolicy.id == policy_id).first()
            if not policy:
                return None
            if not is_admin and policy.created_by != user_id:
                return None

            version = (
                db.query(GuardrailPolicyVersion)
                .filter(
                    GuardrailPolicyVersion.policy_id == policy_id,
                    GuardrailPolicyVersion.version == version_number,
                )
                .first()
            )
            return version.to_dict() if version else None

    @staticmethod
    def rollback_policy(
        policy_id: str,
        target_version: int,
        user_id: str,
        is_admin: bool = False,
        change_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Restore policy config to the specified version snapshot.

        Rollback is implemented as a new save with incremented version.
        """
        from backend.models.guardrails.guardrail_policy import GuardrailPolicy
        from backend.models.guardrails.policy_version import GuardrailPolicyVersion

        with get_db() as db:
            policy = db.query(GuardrailPolicy).filter(GuardrailPolicy.id == policy_id).first()
            if not policy:
                return {"error": "not_found"}
            if not is_admin and policy.created_by != user_id:
                return {"error": "forbidden"}
            if policy.is_builtin:
                return {"error": "builtin_readonly"}

            target = (
                db.query(GuardrailPolicyVersion)
                .filter(
                    GuardrailPolicyVersion.policy_id == policy_id,
                    GuardrailPolicyVersion.version == target_version,
                )
                .first()
            )
            if not target:
                return {"error": "version_not_found"}

            # Apply the snapshot config
            policy.config = target.config_snapshot
            policy.name = target.name_snapshot
            if target.description_snapshot is not None:
                policy.description = target.description_snapshot
            new_version = (policy.version or 1) + 1
            policy.version = new_version

            # Insert a new version record
            summary = change_summary or f"Rolled back to version {target_version}"
            version_row = GuardrailPolicyVersion(
                id=str(uuid.uuid4()),
                policy_id=policy_id,
                version=new_version,
                config_snapshot=dict(policy.config) if policy.config else {},
                name_snapshot=policy.name,
                description_snapshot=policy.description,
                changed_by=user_id,
                change_summary=summary,
            )
            db.add(version_row)
            db.flush()

            logger.info(
                "[GUARDRAILS] Policy %s rolled back to version %d (new version=%d)",
                policy_id,
                target_version,
                new_version,
            )
            return {
                "success": True,
                "policy": policy.to_dict(),
                "new_version": new_version,
            }

    # ── Effectiveness metrics ────────────────────────────────────

    @staticmethod
    def get_policy_metrics(
        policy_id: str,
        user_id: str,
        is_admin: bool = False,
        window: str = "30d",
    ) -> Optional[Dict[str, Any]]:
        """Return aggregated violation metrics for a policy."""
        from backend.models.guardrails.guardrail_policy import GuardrailPolicy
        from backend.models.guardrails.violation_event import GuardrailViolationEvent
        from backend.models.guardrails.violation_feedback import GuardrailViolationFeedback

        with get_db() as db:
            policy = db.query(GuardrailPolicy).filter(GuardrailPolicy.id == policy_id).first()
            if not policy:
                return None
            if not is_admin and policy.created_by != user_id:
                return None

            # Determine time window
            now = datetime.now(timezone.utc)
            if window == "7d":
                period_start = now - timedelta(days=7)
            elif window == "all":
                period_start = datetime(2000, 1, 1, tzinfo=timezone.utc)
            else:  # 30d default
                period_start = now - timedelta(days=30)

            base_q = db.query(GuardrailViolationEvent).filter(
                GuardrailViolationEvent.policy_id == policy_id,
                GuardrailViolationEvent.created_at >= period_start,
            )
            total = base_q.count()

            if total == 0:
                return {
                    "policy_id": policy_id,
                    "window": window,
                    "total_violations": 0,
                    "block_count": 0,
                    "warn_count": 0,
                    "block_rate": 0.0,
                    "warn_rate": 0.0,
                    "top_rules": [],
                    "false_positive_count": 0,
                    "false_positive_rate": 0.0,
                    "per_rule_feedback": [],
                    "period_start": period_start.isoformat(),
                    "period_end": now.isoformat(),
                }

            # Counts by severity
            severity_rows = (
                db.query(
                    GuardrailViolationEvent.severity,
                    sa_func.count(GuardrailViolationEvent.id).label("cnt"),
                )
                .filter(
                    GuardrailViolationEvent.policy_id == policy_id,
                    GuardrailViolationEvent.created_at >= period_start,
                )
                .group_by(GuardrailViolationEvent.severity)
                .all()
            )
            severity_counts = {r.severity: r.cnt for r in severity_rows}
            block_count = severity_counts.get("block", 0)
            warn_count = severity_counts.get("warn", 0)

            # Top 5 rules
            rule_rows = (
                db.query(
                    GuardrailViolationEvent.rule_name,
                    GuardrailViolationEvent.severity,
                    sa_func.count(GuardrailViolationEvent.id).label("hit_count"),
                )
                .filter(
                    GuardrailViolationEvent.policy_id == policy_id,
                    GuardrailViolationEvent.created_at >= period_start,
                )
                .group_by(GuardrailViolationEvent.rule_name, GuardrailViolationEvent.severity)
                .order_by(sa_func.count(GuardrailViolationEvent.id).desc())
                .limit(5)
                .all()
            )
            top_rules = [
                {"rule_name": r.rule_name, "count": r.hit_count}
                for r in rule_rows
            ]

            # False positive rate
            violation_ids = [v.id for v in base_q.all()]
            feedback_rows = (
                db.query(
                    GuardrailViolationFeedback.rating,
                    sa_func.count(GuardrailViolationFeedback.id).label("cnt"),
                )
                .filter(GuardrailViolationFeedback.violation_event_id.in_(violation_ids))
                .group_by(GuardrailViolationFeedback.rating)
                .all()
            ) if violation_ids else []

            feedback_total = sum(r.cnt for r in feedback_rows)
            negative_count = next((r.cnt for r in feedback_rows if r.rating == "negative"), 0)
            false_positive_rate = (negative_count / feedback_total) if feedback_total > 0 else 0.0

            # Per-rule feedback breakdown
            per_rule_feedback = []
            if violation_ids:
                rule_feedback_rows = (
                    db.query(
                        GuardrailViolationEvent.rule_name,
                        GuardrailViolationFeedback.rating,
                        sa_func.count(GuardrailViolationFeedback.id).label("cnt"),
                    )
                    .join(
                        GuardrailViolationFeedback,
                        GuardrailViolationFeedback.violation_event_id == GuardrailViolationEvent.id,
                    )
                    .filter(GuardrailViolationEvent.id.in_(violation_ids))
                    .group_by(GuardrailViolationEvent.rule_name, GuardrailViolationFeedback.rating)
                    .all()
                )
                rule_fb_map: Dict[str, Dict[str, int]] = {}
                for row in rule_feedback_rows:
                    fb = rule_fb_map.setdefault(row.rule_name, {"positive": 0, "negative": 0})
                    fb[row.rating] = row.cnt
                per_rule_feedback = [
                    {
                        "rule_name": rn,
                        "positive_count": counts.get("positive", 0),
                        "negative_count": counts.get("negative", 0),
                    }
                    for rn, counts in rule_fb_map.items()
                ]

            return {
                "policy_id": policy_id,
                "window": window,
                "total_violations": total,
                "block_count": block_count,
                "warn_count": warn_count,
                "block_rate": block_count / total if total > 0 else 0.0,
                "warn_rate": warn_count / total if total > 0 else 0.0,
                "top_rules": top_rules,
                "false_positive_count": negative_count,
                "false_positive_rate": false_positive_rate,
                "per_rule_feedback": per_rule_feedback,
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
            }

    # ── Admin platform metrics ───────────────────────────────────

    @staticmethod
    def get_platform_metrics(window: str = "30d") -> Dict[str, Any]:
        """Return platform-wide aggregated violation metrics (admin only)."""
        from backend.models.guardrails.violation_event import GuardrailViolationEvent

        now = datetime.now(timezone.utc)
        if window == "7d":
            period_start = now - timedelta(days=7)
        elif window == "all":
            period_start = datetime(2000, 1, 1, tzinfo=timezone.utc)
        else:
            period_start = now - timedelta(days=30)

        with get_db() as db:
            total = (
                db.query(sa_func.count(GuardrailViolationEvent.id))
                .filter(GuardrailViolationEvent.created_at >= period_start)
                .scalar()
                or 0
            )

            severity_rows = (
                db.query(
                    GuardrailViolationEvent.severity,
                    sa_func.count(GuardrailViolationEvent.id).label("cnt"),
                )
                .filter(GuardrailViolationEvent.created_at >= period_start)
                .group_by(GuardrailViolationEvent.severity)
                .all()
            )
            severity_counts = {r.severity: r.cnt for r in severity_rows}

            rule_rows = (
                db.query(
                    GuardrailViolationEvent.rule_name,
                    GuardrailViolationEvent.policy_name,
                    GuardrailViolationEvent.severity,
                    sa_func.count(GuardrailViolationEvent.id).label("hit_count"),
                )
                .filter(GuardrailViolationEvent.created_at >= period_start)
                .group_by(
                    GuardrailViolationEvent.rule_name,
                    GuardrailViolationEvent.policy_name,
                    GuardrailViolationEvent.severity,
                )
                .order_by(sa_func.count(GuardrailViolationEvent.id).desc())
                .limit(10)
                .all()
            )
            top_rules = [
                {
                    "rule_name": r.rule_name,
                    "policy_name": r.policy_name,
                    "hit_count": r.hit_count,
                    "severity": r.severity,
                }
                for r in rule_rows
            ]

            return {
                "window": window,
                "total_violations": total,
                "block_count": severity_counts.get("block", 0),
                "warn_count": severity_counts.get("warn", 0),
                "top_rules": top_rules,
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
            }
