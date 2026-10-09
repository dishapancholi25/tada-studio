"""User external service credentials management.

This service provides CRUD operations for user-specific external service
API keys and settings, with encryption for security.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from backend.services.groups.service import GroupService

from ...encryption_utils import decrypt_credential, encrypt_credential
from ...models.auth import McpVisibility, UserExternalService
from ...services.config import get_logger
from ...services.database import get_db

logger = get_logger(__name__)
LOG_PREFIX = "[USER-EXTERNAL-SERVICE]"


class UserExternalServiceService:
    """Service for managing user external service credentials."""

    # Known service names
    SERVICE_TAVILY = "tavily"

    @staticmethod
    def get_service(user_id: str, service_name: str) -> Optional[UserExternalService]:
        """Get a user's external service configuration.

        Args:
            user_id: User identifier
            service_name: Name of the external service (e.g., 'tavily')

        Returns:
            UserExternalService object or None if not found
        """
        with get_db() as db:
            service = (
                db.query(UserExternalService)
                .filter(
                    and_(
                        UserExternalService.user_id == user_id,
                        UserExternalService.service_name == service_name,
                    )
                )
                .first()
            )

            if service:
                db.expunge(service)

            return service

    @staticmethod
    def get_decrypted_api_key(user_id: str, service_name: str) -> Optional[str]:
        """Get a user's decrypted API key for a service.

        Args:
            user_id: User identifier
            service_name: Name of the external service

        Returns:
            Decrypted API key or None if not configured
        """
        service = UserExternalServiceService.get_service(user_id, service_name)

        if not service or not service.is_active:
            return None

        try:
            return decrypt_credential(service.encrypted_api_key)
        except Exception as e:
            logger.error(
                f"{LOG_PREFIX} Failed to decrypt API key for user '{user_id}' "
                f"service '{service_name}': {e}"
            )
            return None

    @staticmethod
    def get_tavily_api_key(user_id: str) -> Optional[str]:
        """Convenience method to get a user's Tavily API key.

        Args:
            user_id: User identifier

        Returns:
            Decrypted Tavily API key or None if not configured
        """
        return UserExternalServiceService.get_decrypted_api_key(
            user_id, UserExternalServiceService.SERVICE_TAVILY
        )

    @staticmethod
    def list_user_services(user_id: str) -> List[UserExternalService]:
        """List all external services configured for a user.

        Args:
            user_id: User identifier

        Returns:
            List of UserExternalService objects
        """
        with get_db() as db:
            services = (
                db.query(UserExternalService)
                .filter(UserExternalService.user_id == user_id)
                .order_by(UserExternalService.service_name)
                .all()
            )

            for service in services:
                db.expunge(service)

            return services

    @staticmethod
    def save_service(
        user_id: str,
        service_name: str,
        api_key: str,
        settings: Optional[Dict[str, Any]] = None,
        display_name: Optional[str] = None,
        service_url: Optional[str] = None,
        auth_type: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ) -> UserExternalService:
        """Save or update a user's external service configuration.

        Note: For some services (like MCP servers), the api_key parameter may contain
        a JSON string encoding multiple credentials rather than a single API key.
        This entire value is encrypted as a single unit.

        Args:
            user_id: User identifier
            service_name: Name of the external service (e.g., 'tavily')
            api_key: Plaintext API key or JSON string of credentials (will be encrypted)
            settings: Optional additional settings
            display_name: Optional human-readable display name
            service_url: Optional service URL / endpoint
            auth_type: Optional authentication type string
            credentials: Optional structured credentials dict (encrypted as JSON)

        Returns:
            UserExternalService object
        """
        import json

        from sqlalchemy.dialects.postgresql import insert

        with get_db() as db:
            # Encrypt the API key
            encrypted_key = encrypt_credential(api_key) if api_key else ""

            # Encrypt structured credentials if provided
            encrypted_creds = None
            if credentials:
                encrypted_creds = {
                    k: encrypt_credential(v) for k, v in credentials.items()
                }

            # Build values dict
            values = {
                "user_id": user_id,
                "service_name": service_name,
                "encrypted_api_key": encrypted_key,
                "settings": settings or {},
                "is_active": True,
            }
            update_set = {
                "encrypted_api_key": encrypted_key,
                "is_active": True,
                "settings": settings if settings is not None else {},
            }

            if display_name is not None:
                values["display_name"] = display_name
                update_set["display_name"] = display_name
            if service_url is not None:
                values["service_url"] = service_url
                update_set["service_url"] = service_url
            if auth_type is not None:
                values["auth_type"] = auth_type
                update_set["auth_type"] = auth_type
            if encrypted_creds is not None:
                values["encrypted_credentials"] = json.dumps(encrypted_creds)
                update_set["encrypted_credentials"] = json.dumps(encrypted_creds)

            # Use PostgreSQL's INSERT ... ON CONFLICT to handle race conditions atomically
            stmt = insert(UserExternalService).values(**values)

            # On conflict (user_id, service_name), update the values
            stmt = stmt.on_conflict_do_update(
                index_elements=["user_id", "service_name"],
                set_=update_set,
            )

            db.execute(stmt)
            db.commit()

            # Fetch the saved/updated record
            service = (
                db.query(UserExternalService)
                .filter(
                    and_(
                        UserExternalService.user_id == user_id,
                        UserExternalService.service_name == service_name,
                    )
                )
                .first()
            )

            if service:
                db.expunge(service)
                logger.info(
                    f"{LOG_PREFIX} Saved {service_name} configuration "
                    f"for user '{user_id}'"
                )
                return service
            else:
                raise RuntimeError(
                    f"Failed to save/retrieve service {service_name} for user {user_id}"
                )

    @staticmethod
    def save_service_preserve_credentials(
        user_id: str,
        service_name: str,
        settings: Optional[Dict[str, Any]] = None,
    ) -> UserExternalService:
        """Update a user's external service configuration while preserving existing credentials.

        This is used when updating MCP server settings without changing credentials.

        Args:
            user_id: User identifier
            service_name: Name of the external service
            settings: Optional additional settings

        Returns:
            UserExternalService object

        Raises:
            RuntimeError: If the service doesn't exist (cannot preserve non-existent credentials)
        """

        with get_db() as db:
            # First, check if the service exists
            existing_service = (
                db.query(UserExternalService)
                .filter(
                    and_(
                        UserExternalService.user_id == user_id,
                        UserExternalService.service_name == service_name,
                    )
                )
                .first()
            )

            if not existing_service:
                raise RuntimeError(
                    f"Cannot preserve credentials for non-existent service {service_name} for user {user_id}"
                )

            # Update only the settings, preserve encrypted_api_key
            existing_service.settings = settings if settings is not None else {}
            existing_service.is_active = True
            db.commit()
            db.refresh(existing_service)
            db.expunge(existing_service)

            logger.info(
                f"{LOG_PREFIX} Updated {service_name} configuration (preserved credentials) "
                f"for user '{user_id}'"
            )

            return existing_service

    @staticmethod
    def delete_service(user_id: str, service_name: str) -> bool:
        """Delete a user's external service configuration.

        Args:
            user_id: User identifier
            service_name: Name of the external service

        Returns:
            True if deleted, False if not found
        """
        with get_db() as db:
            service = (
                db.query(UserExternalService)
                .filter(
                    and_(
                        UserExternalService.user_id == user_id,
                        UserExternalService.service_name == service_name,
                    )
                )
                .first()
            )

            if not service:
                return False

            db.delete(service)
            db.commit()

            logger.info(
                f"{LOG_PREFIX} Deleted {service_name} configuration "
                f"for user '{user_id}'"
            )

            return True

    @staticmethod
    def delete_service_by_id(user_id: str, service_id: str) -> bool:
        """Delete a user's external service configuration by ID.

        Args:
            user_id: User identifier
            service_id: Unique ID of the external service

        Returns:
            True if deleted, False if not found
        """
        with get_db() as db:
            service = (
                db.query(UserExternalService)
                .filter(
                    and_(
                        UserExternalService.user_id == user_id,
                        UserExternalService.id == service_id,
                    )
                )
                .first()
            )

            if not service:
                return False

            service_name = service.service_name
            db.delete(service)
            db.commit()

            logger.info(
                f"{LOG_PREFIX} Deleted service {service_id} ({service_name}) "
                f"for user '{user_id}'"
            )

            return True

    @staticmethod
    def deactivate_service(user_id: str, service_name: str) -> bool:
        """Deactivate a user's external service configuration (soft delete).

        Args:
            user_id: User identifier
            service_name: Name of the external service

        Returns:
            True if deactivated, False if not found
        """
        with get_db() as db:
            service = (
                db.query(UserExternalService)
                .filter(
                    and_(
                        UserExternalService.user_id == user_id,
                        UserExternalService.service_name == service_name,
                    )
                )
                .first()
            )

            if not service:
                return False

            service.is_active = False
            db.commit()

            logger.info(
                f"{LOG_PREFIX} Deactivated {service_name} configuration "
                f"for user '{user_id}'"
            )

            return True

    @staticmethod
    def mask_api_key(api_key: str) -> str:
        """Mask an API key for display, showing only last 4 characters.

        Args:
            api_key: Full API key

        Returns:
            Masked key like "****...abcd"
        """
        if not api_key or len(api_key) < 4:
            return "****"

        return f"****...{api_key[-4:]}"

    @staticmethod
    def list_shared_mcp_servers_for_user(
        user_id: str,
    ) -> List[UserExternalService]:
        """List MCP servers shared with the user (via groups or everyone).

        Returns servers owned by OTHER users that are shared either with
        everyone (__all__) or with groups the user belongs to.
        Excludes the user's own servers.

        Args:
            user_id: The current user's ID

        Returns:
            List of shared MCP servers visible to this user
        """
        from sqlalchemy import cast, or_
        from sqlalchemy.types import String as SAString

        from backend.models.auth.group import GroupMembership

        with get_db() as db:
            # Get group IDs the user belongs to
            user_group_ids = [
                row.group_id
                for row in db.query(GroupMembership.group_id)
                .filter(GroupMembership.user_id == user_id)
                .all()
            ]

            # Build filter: shared with everyone OR shared with user's groups
            sharing_filters = [
                # shared_with_group_ids contains "__all__"
                cast(UserExternalService.shared_with_group_ids, SAString).contains('"__all__"'),
            ]

            # Add filter for each group the user belongs to
            for group_id in user_group_ids:
                sharing_filters.append(
                    cast(UserExternalService.shared_with_group_ids, SAString).contains(f'"{group_id}"')
                )

            servers = (
                db.query(UserExternalService)
                .options(joinedload(UserExternalService.user))
                .filter(
                    and_(
                        UserExternalService.visibility == McpVisibility.PUBLIC,
                        UserExternalService.is_active,
                        UserExternalService.service_name.like("mcp_server_%"),
                        UserExternalService.user_id != user_id,  # Exclude own servers
                        or_(*sharing_filters),
                    )
                )
                .order_by(UserExternalService.created_at.desc())
                .all()
            )

            for server in servers:
                db.expunge(server)

            logger.debug(
                f"{LOG_PREFIX} Listed {len(servers)} shared MCP servers for user '{user_id}' "
                f"(groups: {user_group_ids})"
            )

            return servers

    @staticmethod
    def list_public_mcp_servers(
        exclude_user_id: Optional[str] = None,
    ) -> List[UserExternalService]:
        """List all public MCP servers, optionally excluding a specific user.

        Args:
            exclude_user_id: Optional user ID to exclude from results

        Returns:
            List of public MCP servers ordered by popularity
        """
        with get_db() as db:
            query = (
                db.query(UserExternalService)
                .options(joinedload(UserExternalService.user))
                .filter(
                    and_(
                        UserExternalService.visibility == McpVisibility.PUBLIC,
                        UserExternalService.is_active,
                        UserExternalService.service_name.like("mcp_server_%"),
                    )
                )
            )

            if exclude_user_id:
                query = query.filter(UserExternalService.user_id != exclude_user_id)

            servers = query.order_by(
                UserExternalService.clone_count.desc(),  # Most popular first
                UserExternalService.created_at.desc(),
            ).all()

            for server in servers:
                db.expunge(server)

            logger.debug(
                f"{LOG_PREFIX} Listed {len(servers)} public MCP servers "
                f"(excluding user '{exclude_user_id or 'none'}')"
            )

            return servers

    @staticmethod
    def get_public_server_by_id(server_id: str) -> Optional[UserExternalService]:
        """Get a public server by ID (for cloning).

        Args:
            server_id: Server ID to retrieve

        Returns:
            UserExternalService if found and public, None otherwise
        """
        with get_db() as db:
            server = (
                db.query(UserExternalService)
                .filter(
                    and_(
                        UserExternalService.id == server_id,
                        UserExternalService.visibility == McpVisibility.PUBLIC,
                        UserExternalService.is_active,
                    )
                )
                .first()
            )

            if server:
                db.expunge(server)

            return server

    @staticmethod
    def clone_mcp_server(
        source_server_id: str, target_user_id: str, new_server_name: str
    ) -> UserExternalService:
        """Clone a public MCP server for a user.

        Args:
            source_server_id: ID of public server to clone
            target_user_id: User who is cloning the server
            new_server_name: Name for the new server

        Returns:
            Newly created server

        Raises:
            ValueError: If source server not found or not public
            RuntimeError: If clone operation fails
        """
        import uuid

        with get_db() as db:
            # Get source server
            source = (
                db.query(UserExternalService)
                .filter(UserExternalService.id == source_server_id)
                .first()
            )

            if not source:
                raise ValueError(f"Source server {source_server_id} not found")

            if source.visibility != McpVisibility.PUBLIC:
                raise ValueError("Can only clone public servers")

            shared_group_ids = source.shared_with_group_ids or []
            if shared_group_ids and "__all__" not in shared_group_ids:
                target_user_group_ids = GroupService().get_user_group_ids(
                    target_user_id
                )
                if not {str(group_id) for group_id in shared_group_ids}.intersection(
                    target_user_group_ids
                ):
                    raise ValueError("You do not have access to clone this server")

            # Generate unique service name with deduplication
            base_service_name = f"mcp_server_{new_server_name}"
            service_name = base_service_name
            counter = 1

            while True:
                existing = (
                    db.query(UserExternalService)
                    .filter(
                        and_(
                            UserExternalService.user_id == target_user_id,
                            UserExternalService.service_name == service_name,
                        )
                    )
                    .first()
                )

                if not existing:
                    break

                service_name = f"{base_service_name}_copy_{counter}"
                counter += 1

                if counter > 100:
                    # Fallback to UUID
                    service_name = f"{base_service_name}_{uuid.uuid4().hex[:8]}"
                    break

            # Create cloned server (copy settings, no credentials)
            cloned_server = UserExternalService(
                user_id=target_user_id,
                service_name=service_name,
                encrypted_api_key="",  # No credentials - user must provide
                settings=source.settings.copy() if source.settings else {},
                is_active=False,  # Start inactive until credentials are added
                visibility=McpVisibility.PRIVATE,
                is_template=True,
                original_server_id=source.id,
            )

            db.add(cloned_server)

            # Increment clone count on source
            source.clone_count += 1

            db.commit()
            db.refresh(cloned_server)
            db.expunge(cloned_server)

            logger.info(
                f"{LOG_PREFIX} Cloned server '{source.service_name}' to "
                f"'{service_name}' for user '{target_user_id}'"
            )

            return cloned_server

    @staticmethod
    def update_server_visibility(
        user_id: str,
        service_name: str,
        visibility: str,
        shared_with_group_ids: list | None = None,
    ) -> UserExternalService:
        """Update visibility and sharing of an MCP server.

        Args:
            user_id: Owner of the server
            service_name: Service name
            visibility: New visibility ('private' or 'shared')
            shared_with_group_ids: Group IDs to share with.
                When visibility is 'shared': empty/None or ['__all__'] means everyone,
                specific IDs means shared with those groups only.
                When visibility is 'private': ignored.

        Returns:
            Updated server

        Raises:
            ValueError: If server not found or visibility invalid
        """
        from sqlalchemy.sql import func

        with get_db() as db:
            server = (
                db.query(UserExternalService)
                .filter(
                    and_(
                        UserExternalService.user_id == user_id,
                        UserExternalService.service_name == service_name,
                    )
                )
                .first()
            )

            if not server:
                raise ValueError(f"Server '{service_name}' not found for user")

            # Map API visibility to DB enum
            # API: "private" / "shared"  →  DB: PRIVATE / PUBLIC
            visibility_lower = visibility.lower()
            if visibility_lower == "private":
                new_visibility = McpVisibility.PRIVATE
                new_group_ids: list = []
            elif visibility_lower in ("shared", "public"):
                new_visibility = McpVisibility.PUBLIC
                if shared_with_group_ids and len(shared_with_group_ids) > 0:
                    new_group_ids = shared_with_group_ids
                else:
                    new_group_ids = ["__all__"]
            else:
                raise ValueError(f"Invalid visibility: {visibility}")

            # When making shared, set shared_at timestamp
            if (
                new_visibility == McpVisibility.PUBLIC
                and server.visibility == McpVisibility.PRIVATE
            ):
                server.shared_at = func.now()
                logger.info(
                    f"{LOG_PREFIX} Server '{service_name}' made shared - "
                    "credentials will be masked for non-owners"
                )

            server.visibility = new_visibility
            server.shared_with_group_ids = new_group_ids

            db.commit()
            db.refresh(server)
            db.expunge(server)

            logger.info(
                f"{LOG_PREFIX} Updated visibility for server '{service_name}' to "
                f"'{visibility}' (groups={new_group_ids}) for user '{user_id}'"
            )

            return server
