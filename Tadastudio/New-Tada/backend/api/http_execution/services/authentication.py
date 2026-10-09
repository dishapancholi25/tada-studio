"""Authentication and authorization service for HTTP execution API.

This module handles workflow publishing validation, token authentication,
and rate limiting for HTTP-triggered executions.

Supports three authentication methods via the Authorization: Bearer header:
1. Workflow tokens (wf_xxx) — auto-generated per workflow
2. Personal Access Tokens (na_xxx) — user-scoped PATs
3. Azure AD / local JWTs — session-based tokens
"""

import hmac
from typing import Any, Optional, Tuple

import jwt as pyjwt
from sqlalchemy import and_

from backend.models import Workflow, WorkflowMembership
from backend.services.auth.config import get_auth_config
from backend.services.auth.providers.oauth2_proxy import get_oauth_proxy_auth
from backend.services.auth.user_api_token_service import UserAPITokenService
from backend.services.config import get_logger
from backend.services.database import get_db
from backend.services.rate_limiting import rate_limiting_service
from backend.services.workflow.publishing import WorkflowPublishingService

from ..exceptions import (
    AuthenticationRequiredException,
    InvalidAuthenticationTokenException,
    RateLimitExceededException,
    WorkflowNotPublishedException,
)
from ..models import ClientContext


logger = get_logger(__name__)


class HttpAuthService:
    """Service for authenticating and authorizing HTTP execution requests.

    This service centralizes all security checks including:
    - Workflow publishing validation
    - Token authentication (both new and legacy systems)
    - Rate limiting enforcement
    """

    @staticmethod
    def validate_workflow_published(workflow_identifier: str) -> Any:
        """Validate that a workflow is published and can be executed via HTTP.

        Args:
            workflow_identifier: Workflow UUID or custom slug to validate

        Returns:
            Published workflow object

        Raises:
            WorkflowNotPublishedException: If workflow is not published

        Example:
            >>> published_wf = HttpAuthService.validate_workflow_published("9d04ad87-4762-4ab4-b35f-85a1b002d8e3")
            >>> print(f"Workflow is published: {published_wf.name}")
        """
        logger.debug(
            f"[HTTP-AUTH] Validating workflow '{workflow_identifier}' is published"
        )

        published_workflow = (
            WorkflowPublishingService.get_published_workflow_by_identifier(
                workflow_identifier
            )
        )

        if not published_workflow:
            logger.warning(
                f"[HTTP-AUTH] Workflow '{workflow_identifier}' is not published"
            )
            raise WorkflowNotPublishedException(workflow_identifier)

        logger.info(f"[HTTP-AUTH] Workflow '{workflow_identifier}' is published")
        return published_workflow

    @staticmethod
    def validate_authentication(
        published_workflow: Any,
        graph_name: str,
        token: Optional[str],
    ) -> None:
        """Validate authentication for a workflow.

        Supports three authentication methods via Authorization: Bearer header:
        1. Workflow tokens (wf_xxx) — auto-generated per workflow
        2. Personal Access Tokens (na_xxx) — user-scoped PATs
        3. Azure AD / local JWTs — session-based tokens

        Args:
            published_workflow: Published workflow object
            graph_name: Name of the workflow
            token: Pre-extracted token value, or None if not supplied

        Raises:
            AuthenticationRequiredException: If auth is required but not provided
            InvalidAuthenticationTokenException: If token/credentials are invalid
        """
        # Check if authentication is required
        if not published_workflow.require_authentication:
            logger.debug(
                f"[HTTP-AUTH] No authentication required for workflow '{graph_name}'"
            )
            return

        # No credentials provided at all
        if not token:
            logger.warning(
                f"[HTTP-AUTH] Authentication required but no credentials provided for '{graph_name}'"
            )
            raise AuthenticationRequiredException(graph_name)

        # Dispatch on token value:
        # - "na_..." prefix → Personal Access Token
        # - "wf_..." prefix → Workflow trigger token
        # - anything else  → Azure AD / local JWT
        if token.startswith("na_"):
            logger.debug(
                f"[HTTP-AUTH] Validating Personal Access Token for '{graph_name}'"
            )

            result = UserAPITokenService.validate_token(token, graph_name)

            if result:
                token_obj, user_id = result
                logger.info(
                    f"[HTTP-AUTH] Personal Access Token validated successfully for "
                    f"user '{user_id}' on workflow '{graph_name}' "
                    f"(token: {token_obj.token_prefix}...)"
                )
                return

            logger.warning(
                f"[HTTP-AUTH] Invalid or expired Personal Access Token for workflow '{graph_name}'"
            )
            raise InvalidAuthenticationTokenException()

        if token.startswith("wf_"):
            # Workflow trigger token
            HttpAuthService._validate_workflow_token(
                token, graph_name, published_workflow
            )
            return

        # JWT (Azure AD or local backend-signed)
        HttpAuthService._validate_bearer_token(token, graph_name, published_workflow)

    @staticmethod
    def _validate_bearer_token(
        jwt_token: str, graph_name: str, published_workflow: Any
    ) -> None:
        """Validate a JWT Bearer token for HTTP execution.

        Tries two validation strategies in order:
        1. Local backend-signed JWT (HS256, iss=agenticstudio) — generated by /api/auth/access-token
        2. Azure AD JWKS validation (RS256) — for production Azure AD tokens

        Args:
            jwt_token: The JWT string (value only, without "Bearer " prefix)
            graph_name: Name of the workflow to check access for
            published_workflow: Published workflow object (for ownership check)

        Raises:
            InvalidAuthenticationTokenException: If token is invalid or user lacks access
        """

        # 1. Try local backend-signed JWT (HS256, iss=agenticstudio)
        auth_config = get_auth_config()
        try:
            claims = pyjwt.decode(
                jwt_token,
                auth_config.jwt_secret,
                algorithms=["HS256"],
                audience="http-execution",
                issuer="agenticstudio",
            )
            email = claims.get("email") or claims.get("sub")
            # "sub" is the system user_id (e.g. "dev-..." in dev mode)
            user_id = claims.get("sub", email)
            if user_id and HttpAuthService._check_bearer_access(
                user_id, graph_name, published_workflow
            ):
                logger.info(
                    f"[HTTP-AUTH] Local JWT validated for user '{email}' on '{graph_name}'"
                )
                return
            logger.warning(
                f"[HTTP-AUTH] Local JWT valid but user lacks access to '{graph_name}'"
            )
            raise InvalidAuthenticationTokenException()
        except pyjwt.PyJWTError:
            pass  # Not a locally-signed token, try Azure AD

        # 2. Fall back to Azure AD JWKS validation (RS256)
        oauth_auth = get_oauth_proxy_auth()
        try:
            claims = oauth_auth._decode_token(jwt_token)
        except Exception as e:
            logger.warning(f"[HTTP-AUTH] Bearer token validation failed: {e}")
            raise InvalidAuthenticationTokenException()

        email = (
            claims.get("email") or claims.get("upn") or claims.get("preferred_username")
        )
        if not email:
            logger.warning("[HTTP-AUTH] Bearer token missing email/upn claim")
            raise InvalidAuthenticationTokenException()

        if not HttpAuthService._check_bearer_access(
            email, graph_name, published_workflow
        ):
            logger.warning(
                f"[HTTP-AUTH] User '{email}' does not have access to workflow '{graph_name}'"
            )
            raise InvalidAuthenticationTokenException()

        logger.info(
            f"[HTTP-AUTH] Azure AD Bearer validated for user '{email}' on '{graph_name}'"
        )

    @staticmethod
    def _validate_workflow_token(
        token: str, graph_name: str, published_workflow: Any
    ) -> None:
        """Validate a per-workflow trigger token (wf_xxx).

        Looks up the parent Workflow record via the published workflow and
        compares the supplied token against the stored ``http_trigger_token``.

        Args:
            token: The wf_-prefixed token string from the Bearer header
            graph_name: Workflow identifier (for logging)
            published_workflow: Published workflow object

        Raises:
            InvalidAuthenticationTokenException: If token is invalid
        """
        workflow_id = published_workflow.workflow_id
        if not workflow_id:
            logger.warning(
                f"[HTTP-AUTH] Published workflow '{graph_name}' has no workflow_id"
            )
            raise InvalidAuthenticationTokenException()

        with get_db() as db:
            workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

            if not workflow or not workflow.http_trigger_token:
                logger.warning(
                    f"[HTTP-AUTH] Workflow '{graph_name}' not found or has no trigger token"
                )
                raise InvalidAuthenticationTokenException()

            if not hmac.compare_digest(token, workflow.http_trigger_token):
                logger.warning(
                    f"[HTTP-AUTH] Invalid workflow trigger token for '{graph_name}'"
                )
                raise InvalidAuthenticationTokenException()

        logger.info(f"[HTTP-AUTH] Workflow trigger token validated for '{graph_name}'")

    @staticmethod
    def _check_bearer_access(
        email: str, graph_name: str, published_workflow: Any
    ) -> bool:
        """Check if a Bearer token user has access to a workflow.

        First checks ownership via the published_workflow record (avoiding a
        redundant DB lookup), then falls back to the membership table.

        Args:
            email: User email from the JWT
            graph_name: Workflow identifier (UUID or name)
            published_workflow: Published workflow object

        Returns:
            True if user has access, False otherwise
        """
        # Publisher owns the workflow — direct comparison, no DB query needed
        if published_workflow.user_id and email == published_workflow.user_id:
            return True

        # Fall back to DB membership check
        return HttpAuthService._check_user_workflow_access(email, graph_name)

    @staticmethod
    def _check_user_workflow_access(user_id: str, workflow_identifier: str) -> bool:
        """Check if a user has access to a workflow by ownership or membership.

        Args:
            user_id: User email/identifier
            workflow_identifier: Workflow UUID or name

        Returns:
            True if user has access, False otherwise
        """
        import uuid as uuid_module

        with get_db() as db:
            # Try to parse as UUID first, then fall back to name lookup
            is_uuid = False
            try:
                uuid_module.UUID(workflow_identifier)
                is_uuid = True
            except (ValueError, AttributeError):
                pass

            if is_uuid:
                workflow = (
                    db.query(Workflow)
                    .filter(Workflow.id == workflow_identifier)
                    .first()
                )
            else:
                workflow = (
                    db.query(Workflow)
                    .filter(Workflow.name == workflow_identifier)
                    .first()
                )

            if not workflow:
                logger.warning(
                    f"[HTTP-AUTH] Workflow '{workflow_identifier}' not found"
                )
                return False

            is_owner = workflow.created_by_user_id == user_id

            is_member = (
                db.query(WorkflowMembership)
                .filter(
                    and_(
                        WorkflowMembership.workflow_id == workflow.id,
                        WorkflowMembership.user_id == user_id,
                    )
                )
                .first()
                is not None
            )

            return is_owner or is_member

    @staticmethod
    def check_rate_limits(
        published_workflow: Any,
        graph_name: str,
        client_ip: Optional[str],
        token: Optional[str],
    ) -> None:
        """Check and enforce rate limits for a workflow execution.

        Args:
            published_workflow: Published workflow object
            graph_name: Name of the workflow
            client_ip: Client IP address
            token: Authentication token (can be None)

        Raises:
            RateLimitExceededException: If rate limit is exceeded

        Example:
            >>> HttpAuthService.check_rate_limits(workflow, "my-workflow", "1.2.3.4", None)
            >>> # Raises exception if rate limit exceeded
        """
        if not published_workflow.rate_limit:
            logger.debug(f"[HTTP-AUTH] No rate limits configured for '{graph_name}'")
            return

        logger.debug(f"[HTTP-AUTH] Checking rate limits for workflow '{graph_name}'")

        # Get client identifier for rate limiting
        client_identifier = rate_limiting_service.get_client_identifier(
            client_ip, token
        )

        # Check rate limits
        is_allowed, rate_info = rate_limiting_service.check_rate_limit(
            workflow_name=graph_name,
            client_identifier=client_identifier,
            rate_limit_config=published_workflow.rate_limit,
        )

        if not is_allowed:
            limit_type = rate_info.get("limit_type_hit", "requests")
            retry_after = rate_info.get("retry_after", 60)
            reset_time = rate_info.get("reset_time")
            remaining = rate_info.get("remaining", 0)

            logger.warning(
                f"[HTTP-AUTH] Rate limit exceeded for '{graph_name}': {limit_type}, retry after {retry_after}s"
            )

            raise RateLimitExceededException(
                limit_type=limit_type,
                retry_after=retry_after,
                reset_time=reset_time,
                remaining=remaining,
            )

        logger.debug(
            f"[HTTP-AUTH] Rate limit check passed for '{graph_name}' (remaining: {rate_info.get('remaining', 'N/A')})"
        )

    @staticmethod
    def log_access_attempt(
        published_workflow: Any,
        graph_name: str,
        client_context: ClientContext,
        response_status: int,
        execution_id: Optional[str] = None,
        error_message: Optional[str] = None,
        rate_limit_hit: bool = False,
        rate_limit_remaining: Optional[int] = None,
    ) -> None:
        """Log an access attempt for audit purposes.

        Args:
            published_workflow: Published workflow object
            graph_name: Name of the workflow
            client_context: Client request context information
            response_status: HTTP response status code
            execution_id: Optional execution ID
            error_message: Optional error message
            rate_limit_hit: Whether a rate limit was hit
            rate_limit_remaining: Remaining rate limit quota

        Example:
            >>> context = ClientContext(
            ...     client_ip="1.2.3.4",
            ...     user_agent="curl/7.0",
            ...     graph_name="my-workflow",
            ...     execution_id="exec_123"
            ... )
            >>> HttpAuthService.log_access_attempt(workflow, "my-workflow", context, 200)
        """
        try:
            WorkflowPublishingService.log_access(
                published_workflow=published_workflow,
                client_ip=client_context.get("client_ip"),
                user_agent=client_context.get("user_agent"),
                request_method="POST",
                request_path=f"/api/http-execution/trigger/{graph_name}",
                token_used=client_context.get("token"),
                authentication_status="success"
                if published_workflow.require_authentication
                else "none",
                response_status=response_status,
                execution_id=execution_id,
                error_message=error_message,
                rate_limit_hit=rate_limit_hit,
                rate_limit_remaining=rate_limit_remaining,
            )
            logger.debug(
                f"[HTTP-AUTH] Access logged for workflow '{graph_name}' (status: {response_status})"
            )
        except Exception as e:
            logger.warning(
                f"[HTTP-AUTH] Failed to log access for workflow '{graph_name}': {e}"
            )

    @staticmethod
    def perform_full_security_check(
        graph_name: str,
        token: Optional[str],
        client_ip: Optional[str],
        log_success: bool = True,
    ) -> Tuple[Any, Optional[ClientContext]]:
        """Perform all security checks for an HTTP execution request.

        This is a convenience method that combines all security checks:
        - Workflow publishing validation
        - Token authentication (Bearer or PAT)
        - Rate limiting

        Args:
            graph_name: Name of the workflow
            token: Authentication token (can be None)
            client_ip: Client IP address
            log_success: Whether to log successful access (default: True)

        Returns:
            Tuple of (published_workflow, client_context)

        Raises:
            Various security exceptions if checks fail

        Example:
            >>> published_wf, context = HttpAuthService.perform_full_security_check(
            ...     "my-workflow", "token123", "1.2.3.4"
            ... )
            >>> # All security checks passed
        """
        logger.info(
            f"[HTTP-AUTH] Performing security checks for workflow '{graph_name}'"
        )

        # Validate workflow is published
        published_workflow = HttpAuthService.validate_workflow_published(graph_name)

        # Validate authentication
        HttpAuthService.validate_authentication(published_workflow, graph_name, token)

        # Check rate limits
        HttpAuthService.check_rate_limits(
            published_workflow, graph_name, client_ip, token
        )

        logger.info(f"[HTTP-AUTH] All security checks passed for '{graph_name}'")

        # Build client context for logging
        client_context: ClientContext = {
            "client_ip": client_ip,
            "user_agent": None,  # Will be set by caller if available
            "token": token,
            "graph_name": graph_name,
            "execution_id": "",  # Will be set by caller
        }

        return published_workflow, client_context


# Singleton instance
http_auth_service = HttpAuthService()


def get_http_auth_service() -> HttpAuthService:
    """Get the HTTP authentication service instance.

    Returns:
        HttpAuthService instance

    Example:
        >>> from backend.api.http_execution.services.authentication import get_http_auth_service
        >>> auth_service = get_http_auth_service()
        >>> published_wf = auth_service.validate_workflow_published("my-workflow")
    """
    return http_auth_service
