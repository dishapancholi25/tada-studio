"""Service for managing API endpoint configurations."""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import cast, literal, or_, text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import Session
from sqlalchemy.types import Text

from backend.encryption_utils import default_encryptor
from backend.models.configuration.api_endpoint import ApiEndpoint


logger = logging.getLogger(__name__)

LOG_PREFIX = "[API_ENDPOINTS]"


def _get_user_groups(user_id: str) -> List[str]:
    """Get groups for a user, returning empty list on failure."""
    try:
        from backend.services.groups.service import GroupService

        return GroupService().get_user_groups(user_id)
    except Exception:
        return []


class ApiEndpointService:
    """Service for CRUD operations on API endpoint configurations.

    Manages creation, retrieval, updates, and deletion of API endpoint
    configurations with proper encryption of auth credentials and
    group-based visibility enforcement.
    """

    def create_endpoint(
        self,
        db: Session,
        name: str,
        url_template: str,
        method: str = "GET",
        description: Optional[str] = None,
        service_type: str = "generic",
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
        request_body_template: Optional[str] = None,
        content_type: Optional[str] = None,
        parameter_schema: Optional[Dict[str, Any]] = None,
        auth_type: str = "none",
        auth_config: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_on_status: Optional[List[int]] = None,
        response_format: str = "auto",
        extract_path: Optional[str] = None,
        success_status_codes: Optional[List[int]] = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        max_redirects: int = 10,
        user_id: Optional[str] = None,
        visible_to_groups: Optional[List[str]] = None,
    ) -> ApiEndpoint:
        """Create a new API endpoint configuration."""
        if visible_to_groups is None:
            visible_to_groups = []

        # Validate groups exist (skip __all__ special token)
        groups_to_validate = [g for g in visible_to_groups if g != "__all__"]
        if groups_to_validate:
            try:
                from backend.services.groups.service import GroupService

                GroupService().validate_groups_exist(groups_to_validate)
            except Exception as e:
                logger.warning(f"{LOG_PREFIX} Could not validate groups: {e}")

        # Check for duplicate name
        existing = db.query(ApiEndpoint).filter_by(name=name, user_id=user_id).first()
        if existing:
            raise ValueError(f"API endpoint with name '{name}' already exists")

        endpoint = ApiEndpoint(
            name=name,
            description=description,
            service_type=service_type,
            url_template=url_template,
            method=method.upper(),
            headers=headers,
            query_params=query_params,
            request_body_template=request_body_template,
            content_type=content_type,
            parameter_schema=parameter_schema,
            auth_type=auth_type,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_on_status=retry_on_status,
            response_format=response_format,
            extract_path=extract_path,
            success_status_codes=success_status_codes,
            verify_ssl=verify_ssl,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            user_id=user_id,
            visible_to_groups=visible_to_groups,
        )

        # Encrypt auth config if provided
        if auth_config:
            endpoint.encrypted_auth_config = (
                default_encryptor.encrypt_connection_string(json.dumps(auth_config))
            )

        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)

        logger.info(f"{LOG_PREFIX} Created endpoint '{name}' (ID: {endpoint.id})")
        return endpoint

    def get_endpoint(self, db: Session, endpoint_id: str) -> Optional[ApiEndpoint]:
        """Get an endpoint by ID."""
        return db.query(ApiEndpoint).filter_by(id=endpoint_id).first()

    def get_endpoint_for_user(
        self, db: Session, endpoint_id: str, user_id: str
    ) -> Optional[ApiEndpoint]:
        """Get an endpoint by ID, enforcing visibility rules."""
        endpoint = self.get_endpoint(db, endpoint_id)
        if not endpoint:
            return None
        if endpoint.user_id == user_id:
            return endpoint
        groups = endpoint.visible_to_groups or []
        if "__all__" in groups:
            return endpoint
        if groups:
            user_groups = _get_user_groups(user_id)
            if any(g in groups for g in user_groups):
                return endpoint
        return None

    def list_endpoints(
        self,
        db: Session,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None,
        filter_type: str = "all",
    ) -> List[ApiEndpoint]:
        """List endpoints with visibility filtering."""
        query = db.query(ApiEndpoint)

        if active_only:
            query = query.filter_by(is_active=True)

        if user_id:
            user_groups = _get_user_groups(user_id)

            # JSONB GIN visibility conditions
            all_visible = ApiEndpoint.visible_to_groups.op("@>")(
                text("'[\"__all__\"]'::jsonb")
            )

            if user_groups:
                groups_overlap = ApiEndpoint.visible_to_groups.op("?|")(
                    cast(literal(user_groups), PG_ARRAY(Text))
                )
                shared_condition = or_(all_visible, groups_overlap)
            else:
                shared_condition = all_visible

            owned_condition = ApiEndpoint.user_id == user_id

            if filter_type == "owned":
                query = query.filter(owned_condition)
            elif filter_type == "shared":
                query = query.filter(shared_condition, ApiEndpoint.user_id != user_id)
            else:  # 'all' - owned + shared
                query = query.filter(or_(owned_condition, shared_condition))

        return query.offset(skip).limit(limit).all()

    def update_endpoint(
        self, db: Session, endpoint_id: str, user_id: str, **kwargs
    ) -> Optional[ApiEndpoint]:
        """Update an endpoint configuration. Only the owner can update."""
        endpoint = self.get_endpoint(db, endpoint_id)
        if not endpoint:
            return None

        if endpoint.user_id != user_id:
            raise PermissionError("Only the owner can update this endpoint")

        # Handle auth_config encryption
        auth_config = kwargs.pop("auth_config", None)
        if auth_config is not None:
            endpoint.encrypted_auth_config = (
                default_encryptor.encrypt_connection_string(json.dumps(auth_config))
            )

        # Update remaining fields
        for key, value in kwargs.items():
            if hasattr(endpoint, key) and key not in (
                "id",
                "user_id",
                "encrypted_auth_config",
            ):
                setattr(endpoint, key, value)

        db.commit()
        db.refresh(endpoint)

        logger.info(f"{LOG_PREFIX} Updated endpoint {endpoint_id}")
        return endpoint

    def update_visibility(
        self,
        db: Session,
        endpoint_id: str,
        visible_to_groups: List[str],
        user_id: str,
    ) -> Optional[ApiEndpoint]:
        """Update endpoint visibility groups. Only the owner can update."""
        endpoint = self.get_endpoint(db, endpoint_id)
        if not endpoint:
            return None

        if endpoint.user_id != user_id:
            raise PermissionError("Only the owner can change visibility")

        # Validate groups exist
        groups_to_validate = [g for g in visible_to_groups if g != "__all__"]
        if groups_to_validate:
            try:
                from backend.services.groups.service import GroupService

                GroupService().validate_groups_exist(groups_to_validate)
            except ValueError:
                raise
            except Exception as e:
                logger.warning(f"{LOG_PREFIX} Could not validate groups: {e}")

        endpoint.visible_to_groups = visible_to_groups
        db.commit()
        db.refresh(endpoint)

        logger.info(
            f"{LOG_PREFIX} Updated visibility for endpoint {endpoint_id} to {visible_to_groups}"
        )
        return endpoint

    def delete_endpoint(self, db: Session, endpoint_id: str, user_id: str) -> bool:
        """Delete an endpoint. Only the owner can delete."""
        endpoint = self.get_endpoint(db, endpoint_id)
        if not endpoint:
            return False

        if endpoint.user_id != user_id:
            raise PermissionError("Only the owner can delete this endpoint")

        db.delete(endpoint)
        db.commit()

        logger.info(f"{LOG_PREFIX} Deleted endpoint {endpoint_id}")
        return True

    def get_endpoint_config_dict(
        self, db: Session, endpoint_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get endpoint config as a dictionary with decrypted auth.

        Used by the HTTP node executor to resolve endpoint_id references.
        When user_id is provided, enforces visibility rules.
        """
        if user_id:
            endpoint = self.get_endpoint_for_user(db, endpoint_id, user_id)
        else:
            logger.warning(
                f"{LOG_PREFIX} get_endpoint_config_dict called without user_id "
                f"for endpoint {endpoint_id} — skipping visibility check"
            )
            endpoint = self.get_endpoint(db, endpoint_id)
        if not endpoint:
            return None

        config = {
            "url_template": endpoint.url_template,
            "method": endpoint.method,
            "headers": endpoint.headers or {},
            "query_params": endpoint.query_params or {},
            "request_body_template": endpoint.request_body_template or "",
            "body_template": endpoint.request_body_template or "",
            "content_type": endpoint.content_type,
            "parameter_schema": endpoint.parameter_schema or {},
            "auth_type": endpoint.auth_type or "none",
            "timeout_seconds": endpoint.timeout_seconds or 30,
            "max_retries": endpoint.max_retries or 3,
            "retry_delay": endpoint.retry_delay or 1.0,
            "retry_on_status": endpoint.retry_on_status or [429, 500, 502, 503, 504],
            "response_format": endpoint.response_format or "auto",
            "extract_path": endpoint.extract_path or "",
            "response_path": endpoint.extract_path or "",
            "success_status_codes": endpoint.success_status_codes
            or [200, 201, 202, 204],
            "verify_ssl": endpoint.verify_ssl
            if endpoint.verify_ssl is not None
            else True,
            "follow_redirects": endpoint.follow_redirects
            if endpoint.follow_redirects is not None
            else True,
            "max_redirects": endpoint.max_redirects or 10,
        }

        # Decrypt auth config
        if endpoint.encrypted_auth_config:
            try:
                decrypted = default_encryptor.decrypt_connection_string(
                    endpoint.encrypted_auth_config
                )
                config["auth_config"] = json.loads(decrypted)
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX} Failed to decrypt auth config for {endpoint_id}: {e}"
                )
                config["auth_config"] = {}
        else:
            config["auth_config"] = {}

        return config

    async def test_endpoint(
        self, db: Session, endpoint_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Test connectivity to an API endpoint.

        Makes a lightweight request to validate the endpoint is reachable
        and authentication works. The HTTP request runs in a thread to
        avoid blocking the async event loop.

        Args:
            db: Database session
            endpoint_id: Endpoint ID to test
            user_id: User ID for visibility checks

        Returns:
            Dict with success, status_code, response_time_ms, error fields
        """
        endpoint = self.get_endpoint_for_user(db, endpoint_id, user_id)
        if not endpoint:
            return {"success": False, "error": "Endpoint not found"}

        config = self.get_endpoint_config_dict(db, endpoint_id, user_id=user_id)
        if not config:
            return {
                "success": False,
                "error": "Could not resolve endpoint configuration",
            }

        url = config.get("url_template", "")
        method = config.get("method", "GET")
        headers = dict(config.get("headers", {}))
        auth_type = config.get("auth_type", "none")
        auth_config = config.get("auth_config", {})
        verify_ssl = config.get("verify_ssl", True)

        # Apply auth headers
        if auth_type == "bearer" and auth_config.get("token"):
            headers["Authorization"] = f"Bearer {auth_config['token']}"
        elif auth_type in ("api_key", "api_key_header"):
            key = auth_config.get("key") or auth_config.get("api_key")
            header = auth_config.get("header") or auth_config.get(
                "header_name", "X-API-Key"
            )
            if key:
                headers[header] = key

        import asyncio

        import requests as http_requests

        def _do_request() -> Dict[str, Any]:
            test_method = "HEAD" if method.upper() == "GET" else method.upper()
            return {
                "response": http_requests.request(
                    test_method,
                    url,
                    headers=headers,
                    timeout=10,
                    verify=verify_ssl,
                    allow_redirects=True,
                    auth=(
                        http_requests.auth.HTTPBasicAuth(
                            auth_config.get("username", ""),
                            auth_config.get("password", ""),
                        )
                        if auth_type == "basic"
                        else None
                    ),
                ),
            }

        try:
            start = time.monotonic()
            result = await asyncio.to_thread(_do_request)
            elapsed_ms = round((time.monotonic() - start) * 1000)

            response = result["response"]
            success = response.status_code < 500
            status = "success" if success else "failed"

            # Update health tracking
            endpoint.last_connection_test = datetime.now(timezone.utc)
            endpoint.last_connection_status = status
            db.commit()

            return {
                "success": success,
                "status_code": response.status_code,
                "response_time_ms": elapsed_ms,
            }

        except http_requests.exceptions.Timeout:
            endpoint.last_connection_test = datetime.now(timezone.utc)
            endpoint.last_connection_status = "timeout"
            db.commit()
            return {"success": False, "error": "Connection timed out"}

        except http_requests.exceptions.ConnectionError:
            logger.error(
                f"{LOG_PREFIX} Connection failed for endpoint {endpoint_id}",
                exc_info=True,
            )
            endpoint.last_connection_test = datetime.now(timezone.utc)
            endpoint.last_connection_status = "failed"
            db.commit()
            return {"success": False, "error": "Connection failed"}

        except Exception:
            logger.error(
                f"{LOG_PREFIX} Test failed for endpoint {endpoint_id}", exc_info=True
            )
            endpoint.last_connection_test = datetime.now(timezone.utc)
            endpoint.last_connection_status = "failed"
            db.commit()
            return {"success": False, "error": "Test failed"}
