"""Group-level external service (MCP tool) configuration service.

Provides CRUD operations for group-scoped MCP tool configurations and
membership lookups for the three-tier credential resolution chain:
  personal → group → system
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_

from ...encryption_utils import decrypt_credential, encrypt_credential
from ...models.auth.group import Group, GroupMembership
from ...models.configuration.group_external_service import (
    GroupExternalServiceAssignment,
    GroupExternalServiceConfig,
)
from ...services.config import get_logger
from ...services.database import get_db

logger = get_logger(__name__)
LOG_PREFIX = "[GROUP-EXT-SVC]"


class GroupExternalServiceService:
    """Service for admin-managed group-scoped external service configurations."""

    # ── CRUD ─────────────────────────────────────────────────────────────

    @staticmethod
    def create_config(
        *,
        service_name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        service_url: Optional[str] = None,
        auth_type: str = "api_key_header",
        api_key: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        settings: Optional[Dict[str, Any]] = None,
        group_ids: Optional[List[str]] = None,
        is_active: bool = True,
    ) -> GroupExternalServiceConfig:
        """Create a new group MCP tool configuration.

        Args:
            service_name:  Stable identifier (e.g. ``mcp_preset_github``).
            display_name:  Human-readable label.
            description:   Optional description.
            service_url:   Non-sensitive base URL.
            auth_type:     Credential application method.
            api_key:       Plaintext API key or JSON-encoded credentials blob.
            credentials:   Structured credentials dict (each value encrypted individually).
            settings:      Non-sensitive config.
            group_ids:     Groups to assign this config to.
            is_active:     Whether the config is enabled.

        Returns:
            Newly created :class:`GroupExternalServiceConfig`.
        """
        from ...models.base import generate_uuid

        with get_db() as db:
            encrypted_key = encrypt_credential(api_key) if api_key else ""
            encrypted_creds = None
            if credentials:
                encrypted_creds = {
                    k: encrypt_credential(v) for k, v in credentials.items()
                }

            config = GroupExternalServiceConfig(
                id=generate_uuid(),
                service_name=service_name,
                display_name=display_name,
                description=description,
                service_url=service_url,
                auth_type=auth_type,
                encrypted_api_key=encrypted_key,
                encrypted_credentials=json.dumps(encrypted_creds)
                if encrypted_creds
                else None,
                settings=settings or {},
                is_active=is_active,
            )
            db.add(config)
            db.flush()  # get config.id

            # Create assignments
            for gid in group_ids or []:
                assignment = GroupExternalServiceAssignment(
                    id=generate_uuid(),
                    config_id=config.id,
                    group_id=gid,
                )
                db.add(assignment)

            db.commit()
            db.refresh(config)
            db.expunge(config)

            logger.info("%s Created group MCP config '%s'", LOG_PREFIX, service_name)
            return config

    @staticmethod
    def update_config(
        config_id: str,
        *,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        service_url: Optional[str] = None,
        auth_type: Optional[str] = None,
        api_key: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        settings: Optional[Dict[str, Any]] = None,
        group_ids: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
    ) -> GroupExternalServiceConfig:
        """Update an existing group MCP tool configuration.

        Pass ``None`` for any field to leave it unchanged.
        Pass ``group_ids`` to replace all group assignments atomically.

        Args:
            config_id:    ID of the config to update.
            ...           (see create_config for field descriptions)

        Returns:
            Updated :class:`GroupExternalServiceConfig`.

        Raises:
            ValueError: If the config does not exist.
        """
        from ...models.base import generate_uuid

        with get_db() as db:
            config = (
                db.query(GroupExternalServiceConfig)
                .filter(GroupExternalServiceConfig.id == config_id)
                .first()
            )

            if not config:
                raise ValueError(f"Group MCP config '{config_id}' not found")

            if display_name is not None:
                config.display_name = display_name
            if description is not None:
                config.description = description
            if service_url is not None:
                config.service_url = service_url
            if auth_type is not None:
                config.auth_type = auth_type
            if api_key is not None:
                config.encrypted_api_key = encrypt_credential(api_key)
            if credentials is not None:
                encrypted_creds = {
                    k: encrypt_credential(v) for k, v in credentials.items()
                }
                config.encrypted_credentials = json.dumps(encrypted_creds)
            if settings is not None:
                config.settings = settings
            if is_active is not None:
                config.is_active = is_active

            # Replace group assignments if provided
            if group_ids is not None:
                db.query(GroupExternalServiceAssignment).filter(
                    GroupExternalServiceAssignment.config_id == config_id
                ).delete()
                for gid in group_ids:
                    db.add(
                        GroupExternalServiceAssignment(
                            id=generate_uuid(),
                            config_id=config_id,
                            group_id=gid,
                        )
                    )

            db.commit()
            db.refresh(config)
            db.expunge(config)

            logger.info("%s Updated group MCP config '%s'", LOG_PREFIX, config_id)
            return config

    @staticmethod
    def delete_config(config_id: str) -> bool:
        """Delete a group MCP config and all its group assignments.

        Args:
            config_id: ID of the config to delete.

        Returns:
            True if deleted, False if not found.
        """
        with get_db() as db:
            config = (
                db.query(GroupExternalServiceConfig)
                .filter(GroupExternalServiceConfig.id == config_id)
                .first()
            )

            if not config:
                return False

            db.delete(config)
            db.commit()

            logger.info("%s Deleted group MCP config '%s'", LOG_PREFIX, config_id)
            return True

    @staticmethod
    def get_config(config_id: str) -> Optional[GroupExternalServiceConfig]:
        """Get a single group MCP config by ID."""
        with get_db() as db:
            config = (
                db.query(GroupExternalServiceConfig)
                .filter(GroupExternalServiceConfig.id == config_id)
                .first()
            )
            if config:
                db.expunge(config)
            return config

    @staticmethod
    def list_configs() -> List[GroupExternalServiceConfig]:
        """List all group MCP configs (admin use)."""
        with get_db() as db:
            configs = (
                db.query(GroupExternalServiceConfig)
                .order_by(GroupExternalServiceConfig.service_name)
                .all()
            )
            for c in configs:
                db.expunge(c)
            return configs

    @staticmethod
    def get_group_ids_for_config(config_id: str) -> List[str]:
        """Return the list of group IDs assigned to a config."""
        with get_db() as db:
            rows = (
                db.query(GroupExternalServiceAssignment.group_id)
                .filter(GroupExternalServiceAssignment.config_id == config_id)
                .all()
            )
            return [r[0] for r in rows]

    # ── User-facing lookups ───────────────────────────────────────────────

    @staticmethod
    def get_configs_for_user(
        user_id: str,
    ) -> List[Tuple[GroupExternalServiceConfig, List[str]]]:
        """Return all active group MCP configs available to a user.

        A config is available when the user is a member of at least one group
        the config is assigned to.

        Args:
            user_id: The requesting user's identifier.

        Returns:
            List of (config, [group_names]) tuples for each reachable config.
        """
        with get_db() as db:
            # Find all group IDs the user belongs to
            memberships = (
                db.query(GroupMembership.group_id)
                .filter(GroupMembership.user_id == user_id)
                .all()
            )
            user_group_ids = {row[0] for row in memberships}

            if not user_group_ids:
                return []

            # Find all assignments for those groups
            assignments = (
                db.query(GroupExternalServiceAssignment)
                .filter(GroupExternalServiceAssignment.group_id.in_(user_group_ids))
                .all()
            )

            config_ids = list({a.config_id for a in assignments})
            if not config_ids:
                return []

            # Fetch active configs
            configs = (
                db.query(GroupExternalServiceConfig)
                .filter(
                    and_(
                        GroupExternalServiceConfig.id.in_(config_ids),
                        GroupExternalServiceConfig.is_active,
                    )
                )
                .all()
            )

            # Build group name mapping
            group_names_by_id: Dict[str, str] = {}
            groups = db.query(Group).filter(Group.id.in_(user_group_ids)).all()
            for g in groups:
                group_names_by_id[g.id] = g.name

            result = []
            for config in configs:
                # Which of the user's groups does this config serve?
                serving_group_ids = {
                    a.group_id for a in assignments if a.config_id == config.id
                } & user_group_ids
                serving_group_names = [
                    group_names_by_id.get(gid, gid) for gid in serving_group_ids
                ]
                db.expunge(config)
                result.append((config, serving_group_names))

            return result

    @staticmethod
    def get_config_for_user_service(
        user_id: str, service_name: str
    ) -> Optional[GroupExternalServiceConfig]:
        """Return the first active group config matching service_name for a user.

        Used in the credential resolution chain (personal → group → system).

        Args:
            user_id:      The requesting user's identifier.
            service_name: Stable machine identifier (e.g. ``mcp_preset_github``).

        Returns:
            Active :class:`GroupExternalServiceConfig` if found, else None.
        """
        configs_with_groups = GroupExternalServiceService.get_configs_for_user(user_id)
        for config, _ in configs_with_groups:
            if config.service_name == service_name and config.is_active:
                return config
        return None

    # ── Credential helpers ────────────────────────────────────────────────

    @staticmethod
    def get_decrypted_api_key(config: GroupExternalServiceConfig) -> Optional[str]:
        """Decrypt and return the primary API key from a config."""
        if not config.encrypted_api_key:
            return None
        try:
            return decrypt_credential(config.encrypted_api_key)
        except Exception as exc:
            logger.error(
                "%s Failed to decrypt api_key for config '%s': %s",
                LOG_PREFIX,
                config.id,
                exc,
            )
            return None

    @staticmethod
    def get_decrypted_credentials(
        config: GroupExternalServiceConfig,
    ) -> Optional[Dict[str, str]]:
        """Decrypt and return the structured credentials dict from a config."""
        if not config.encrypted_credentials:
            return None
        try:
            raw = config.encrypted_credentials
            if isinstance(raw, str):
                raw = json.loads(raw)
            return {k: decrypt_credential(v) for k, v in raw.items() if v}
        except Exception as exc:
            logger.error(
                "%s Failed to decrypt credentials for config '%s': %s",
                LOG_PREFIX,
                config.id,
                exc,
            )
            return None

    @staticmethod
    def build_metadata_dict(
        config: GroupExternalServiceConfig,
        group_ids: Optional[List[str]] = None,
        group_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Return a safe (credential-free) dict suitable for API responses.

        Args:
            config:      Detached ORM object.
            group_ids:   List of group IDs this config is assigned to.
            group_names: Human-readable group names (parallel to group_ids).

        Returns:
            Dict with non-sensitive fields only.
        """
        return {
            "id": config.id,
            "service_name": config.service_name,
            "display_name": config.display_name,
            "description": config.description,
            "service_url": config.service_url,
            "auth_type": config.auth_type
            if isinstance(config.auth_type, str)
            else config.auth_type.value,
            "settings": config.settings or {},
            "is_active": config.is_active,
            "credentials_configured": bool(
                config.encrypted_api_key or config.encrypted_credentials
            ),
            "group_ids": group_ids or [],
            "group_names": group_names or [],
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }
