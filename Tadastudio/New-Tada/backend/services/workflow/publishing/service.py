"""
Service layer for managing published workflows.

This service provides database persistence for workflow publishing functionality.
Authentication is now handled via Personal Access Tokens (PATs) only.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_

from ...database import get_db
from ....models import (
    PublishedWorkflow,
    Workflow,
    WorkflowAccessLog,
    WorkflowMembership,
)
from ....services.config import get_logger
from ....services.graph.storage import resolve_user_id


logger = get_logger(__name__)


class WorkflowPublishingService:
    """Service for managing published workflows.

    Authentication is handled via user-created Personal Access Tokens (PATs).
    """

    @staticmethod
    def publish_workflow(
        graph_name: str,
        user_identifier: str,
        custom_slug: Optional[str] = None,
        description: str = "",
        require_authentication: bool = True,
        rate_limit: Optional[Dict[str, int]] = None,
        allowed_origins: Optional[List[str]] = None,
        webhook_url: Optional[str] = None,
        input_schema: Optional[Dict[str, Any]] = None,
    ) -> PublishedWorkflow:
        """
        Publish a workflow or update existing publication settings.

        Args:
            graph_name: Name of the workflow to publish
            user_identifier: User publishing the workflow
            custom_slug: Custom URL slug (optional)
            description: Description of the workflow
            require_authentication: Whether authentication is required
            rate_limit: Rate limiting configuration
            allowed_origins: CORS allowed origins
            webhook_url: Webhook URL for completion callbacks
            input_schema: JSON schema for input validation

        Returns:
            PublishedWorkflow: The created or updated published workflow record

        Raises:
            ValueError: If custom_slug conflicts with existing workflow or user doesn't own workflow
        """
        with get_db() as db:
            # Resolve user and workflow
            user_id = resolve_user_id(user_identifier, db)
            workflow = (
                db.query(Workflow)
                .filter(
                    Workflow.name == graph_name,
                    Workflow.created_by_user_id == user_id,
                    Workflow.is_deleted == False,  # noqa: E712
                )
                .first()
            )

            if not workflow:
                raise ValueError(
                    f"Workflow '{graph_name}' not found or you don't have permission to publish it"
                )
            # Check if workflow is already published (by this user)
            existing = (
                db.query(PublishedWorkflow)
                .filter(
                    and_(
                        PublishedWorkflow.workflow_id == workflow.id,
                        PublishedWorkflow.user_id == user_id,
                    )
                )
                .first()
            )

            if existing:
                # Update existing publication (including graph_name in case workflow was renamed)
                existing.graph_name = graph_name
                existing.custom_slug = custom_slug
                existing.description = description
                existing.require_authentication = require_authentication
                existing.rate_limit = rate_limit
                existing.allowed_origins = allowed_origins or []
                existing.webhook_url = webhook_url
                existing.input_schema = input_schema
                existing.is_published = True
                existing.workflow_id = workflow.id
                existing.user_id = user_id
                existing.updated_at = datetime.utcnow()

                published_workflow = existing
            else:
                # Check for slug conflicts
                if custom_slug:
                    slug_conflict = (
                        db.query(PublishedWorkflow)
                        .filter(
                            and_(
                                PublishedWorkflow.custom_slug == custom_slug,
                                PublishedWorkflow.graph_name != graph_name,
                            )
                        )
                        .first()
                    )
                    if slug_conflict:
                        raise ValueError(
                            f"Custom slug '{custom_slug}' is already in use by workflow '{slug_conflict.graph_name}'"
                        )

                # Create new publication
                published_workflow = PublishedWorkflow(
                    graph_name=graph_name,
                    custom_slug=custom_slug,
                    description=description,
                    require_authentication=require_authentication,
                    rate_limit=rate_limit,
                    allowed_origins=allowed_origins or [],
                    webhook_url=webhook_url,
                    input_schema=input_schema,
                    is_published=True,
                    workflow_id=workflow.id,
                    user_id=user_id,
                )
                db.add(published_workflow)

            db.flush()  # Ensure we have the ID

            # Note: Authentication tokens are no longer auto-generated.
            # Users must create Personal Access Tokens via Settings → API Tokens.

            # Refresh the object to ensure all attributes are loaded
            db.refresh(published_workflow)

            # Make the object detached from the session so it can be used outside
            db.expunge(published_workflow)

            # Fire evaluation trigger (non-blocking, best-effort)
            try:
                import asyncio

                from backend.services.evaluation.trigger import EvaluationTriggerService

                trigger_service = EvaluationTriggerService()
                loop = asyncio.get_event_loop()
                loop.create_task(
                    trigger_service.trigger_on_publish(
                        workflow_id=str(workflow.id),
                        revision=str(workflow.latest_version or ""),
                        user_id=str(user_id),
                    )
                )
            except Exception as e:
                logger.warning("Failed to trigger evaluation on publish: %s", e)

            return published_workflow

    @staticmethod
    def unpublish_workflow(
        graph_name: str, user_identifier: Optional[str] = None
    ) -> bool:
        """
        Unpublish a workflow (mark as not published and revoke tokens).

        Args:
            graph_name: Name of the workflow to unpublish
            user_identifier: Optional user identifier to scope the operation to a
                specific user, preventing cross-user modifications in multi-tenant setups

        Returns:
            bool: True if workflow was unpublished, False if not found
        """
        with get_db() as db:
            user_id = resolve_user_id(user_identifier, db) if user_identifier else None

            query = db.query(PublishedWorkflow).filter(
                PublishedWorkflow.graph_name == graph_name
            )
            if user_id:
                query = query.filter(PublishedWorkflow.user_id == user_id)

            published_workflows = query.all()

            if not published_workflows:
                return False

            # Mark all matching records as unpublished (handles duplicates)
            for pw in published_workflows:
                pw.is_published = False
                pw.updated_at = datetime.utcnow()

            # Note: Personal Access Tokens are not deactivated when unpublishing.
            # Users maintain control of their own tokens.

            return True

    @staticmethod
    def check_publication_status(graph_name: str) -> bool:
        """Check if a workflow is currently published.

        Lightweight check that only queries the published_workflows table.
        Does NOT load the full graph definition.
        """
        with get_db() as db:
            exists = (
                db.query(PublishedWorkflow.id)
                .filter(
                    and_(
                        PublishedWorkflow.graph_name == graph_name,
                        PublishedWorkflow.is_published,
                    )
                )
                .first()
            )
            return exists is not None

    @staticmethod
    def get_published_workflow(graph_name: str) -> Optional[PublishedWorkflow]:
        """Get published workflow by graph name.

        DEPRECATED: Use get_published_workflow_by_identifier() instead.
        This method is kept for backward compatibility.
        """
        with get_db() as db:
            published_workflow = (
                db.query(PublishedWorkflow)
                .filter(
                    and_(
                        PublishedWorkflow.graph_name == graph_name,
                        PublishedWorkflow.is_published,
                    )
                )
                .first()
            )

            if published_workflow:
                # Detach from session to avoid session errors
                db.expunge(published_workflow)

            return published_workflow

    @staticmethod
    def get_published_workflow_by_identifier(
        identifier: str,
    ) -> Optional[PublishedWorkflow]:
        """Get published workflow by workflow_id or custom_slug.

        Args:
            identifier: Either a workflow UUID or a custom slug

        Returns:
            Published workflow if found, None otherwise
        """
        import uuid

        with get_db() as db:
            # Try to parse as UUID first
            is_uuid = False
            try:
                uuid.UUID(identifier)
                is_uuid = True
            except (ValueError, AttributeError):
                pass

            if is_uuid:
                # Look up by workflow_id
                published_workflow = (
                    db.query(PublishedWorkflow)
                    .filter(
                        and_(
                            PublishedWorkflow.workflow_id == identifier,
                            PublishedWorkflow.is_published,
                        )
                    )
                    .first()
                )
            else:
                # Look up by custom_slug
                published_workflow = (
                    db.query(PublishedWorkflow)
                    .filter(
                        and_(
                            PublishedWorkflow.custom_slug == identifier,
                            PublishedWorkflow.is_published,
                        )
                    )
                    .first()
                )

            if published_workflow:
                # Detach from session to avoid session errors
                db.expunge(published_workflow)

            return published_workflow

    @staticmethod
    def get_published_workflow_by_slug(slug: str) -> Optional[PublishedWorkflow]:
        """Get published workflow by custom slug or graph name."""
        with get_db() as db:
            published_workflow = (
                db.query(PublishedWorkflow)
                .filter(
                    and_(
                        or_(
                            PublishedWorkflow.custom_slug == slug,
                            PublishedWorkflow.graph_name == slug,
                        ),
                        PublishedWorkflow.is_published,
                    )
                )
                .first()
            )

            if published_workflow:
                # Detach from session to avoid session errors
                db.expunge(published_workflow)

            return published_workflow

    @staticmethod
    def list_published_workflows() -> List[PublishedWorkflow]:
        """Get list of all published workflows (deprecated - use list_published_workflows_for_user)."""
        with get_db() as db:
            published_workflows = (
                db.query(PublishedWorkflow).filter(PublishedWorkflow.is_published).all()
            )

            # Detach all objects from session to avoid session errors
            for workflow in published_workflows:
                db.expunge(workflow)

            return published_workflows

    @staticmethod
    def list_published_workflows_for_user(
        user_identifier: str,
    ) -> List[PublishedWorkflow]:
        """
        Get list of published workflows accessible to a user.

        Users can access published workflows they:
        - Created (via workflow ownership)
        - Have membership to (via workflow_memberships)

        Args:
            user_identifier: User ID or identifier

        Returns:
            List of accessible published workflows
        """
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        with get_db() as db:
            # Resolve user
            user_id = resolve_user_id(user_identifier, db)

            # Build subquery for accessible workflow IDs (excluding soft-deleted workflows)
            accessible_workflow_ids = (
                select(Workflow.id)
                .select_from(Workflow)
                .outerjoin(
                    WorkflowMembership, WorkflowMembership.workflow_id == Workflow.id
                )
                .where(
                    and_(
                        or_(
                            Workflow.created_by_user_id == user_id,
                            WorkflowMembership.user_id == user_id,
                        ),
                        Workflow.is_deleted == False,  # noqa: E712
                    )
                )
            )

            # Get published workflows linked to accessible workflows
            # Eagerly load the workflow relationship to access updated_at
            published_workflows = (
                db.query(PublishedWorkflow)
                .options(joinedload(PublishedWorkflow.workflow))
                .filter(
                    and_(
                        PublishedWorkflow.is_published,
                        PublishedWorkflow.workflow_id.in_(accessible_workflow_ids),
                    )
                )
                .all()
            )

            # Detach all objects from session to avoid session errors
            for workflow in published_workflows:
                db.expunge(workflow)

            return published_workflows

    @staticmethod
    def list_public_published_workflows() -> List[PublishedWorkflow]:
        """Get list of published workflows that do not require authentication.

        These are workflows that any caller can discover without presenting a token,
        mirroring the access policy already applied by the HTTP execution trigger
        endpoints (where require_authentication=False workflows accept anonymous calls).

        Returns:
            List of published workflows with require_authentication=False
        """
        from sqlalchemy.orm import joinedload

        with get_db() as db:
            published_workflows = (
                db.query(PublishedWorkflow)
                .options(joinedload(PublishedWorkflow.workflow))
                .join(Workflow, PublishedWorkflow.workflow_id == Workflow.id)
                .filter(
                    and_(
                        PublishedWorkflow.is_published,
                        PublishedWorkflow.require_authentication == False,  # noqa: E712
                        Workflow.is_deleted == False,  # noqa: E712
                    )
                )
                .all()
            )

            for workflow in published_workflows:
                db.expunge(workflow)

            return published_workflows

    @staticmethod
    def log_access(
        published_workflow: PublishedWorkflow,
        client_ip: Optional[str],
        user_agent: Optional[str],
        request_method: str,
        request_path: str,
        token_used: Optional[str],
        authentication_status: str,
        response_status: int,
        execution_id: Optional[str] = None,
        execution_status: Optional[str] = None,
        execution_duration_ms: Optional[int] = None,
        response_size_bytes: Optional[int] = None,
        error_message: Optional[str] = None,
        rate_limit_hit: bool = False,
        rate_limit_remaining: Optional[int] = None,
    ) -> None:
        """Log access to a published workflow."""
        with get_db() as db:
            # Update workflow access statistics
            published_workflow.last_accessed = datetime.utcnow()
            published_workflow.access_count += 1

            # Ensure the updated workflow is tracked in the session
            db.add(published_workflow)

            # Create access log entry
            access_log = WorkflowAccessLog(
                published_workflow_id=published_workflow.id,
                client_ip=client_ip,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                token_used=token_used,
                authentication_status=authentication_status,
                execution_id=execution_id,
                execution_status=execution_status,
                execution_duration_ms=execution_duration_ms,
                response_status=response_status,
                response_size_bytes=response_size_bytes,
                error_message=error_message,
                rate_limit_hit=rate_limit_hit,
                rate_limit_remaining=rate_limit_remaining,
            )
            db.add(access_log)
            db.commit()
