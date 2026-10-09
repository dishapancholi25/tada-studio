"""User service for admin user management operations."""

import logging
from typing import List, Tuple, Optional
from sqlalchemy import func, or_

from backend.models.auth import User, Group, GroupMembership
from backend.models.auth.role import UserRole
from backend.services.database import get_db
from backend.services.auth.rbac import clear_admin_group_cache, _redact_email
from backend.services.auth.config import ADMINISTRATORS_GROUP_NAME, get_auth_config

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations."""

    def get_users_list(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Tuple[List[Tuple[User, str, int]], int]:
        """Get paginated list of users with their roles and group counts.

        Args:
            limit: Maximum number of users to return (default 50)
            offset: Number of users to skip (default 0)
            search: Optional search query to filter by name, email, or role
            role: Optional role filter (PENDING, USER, or ADMIN)

        Returns:
            Tuple of (list of (User, role, group_count), total_count)
            where role is 'admin' or 'user'
        """
        with get_db() as session:
            # Build base query
            query = (
                session.query(
                    User, func.count(GroupMembership.group_id).label("group_count")
                )
                .outerjoin(GroupMembership, GroupMembership.user_id == User.id)
                .group_by(User.id)
            )

            # Apply search filter if provided
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    or_(
                        User.name.ilike(search_pattern),
                        User.email.ilike(search_pattern),
                        User.role.ilike(search_pattern),
                    )
                )

            # Apply role filter if provided
            if role:
                query = query.filter(User.role == role.upper())

            # Get total count before pagination
            total_count = query.count()

            # Apply sorting: ADMIN first, then USER, then SYSTEM, then PENDING, then by created_at desc
            # Use CASE statement to create custom sort order
            from sqlalchemy import case

            role_order = case(
                (User.role == "ADMIN", 1),
                (User.role == "USER", 2),
                (User.role == "SYSTEM", 3),
                (User.role == "PENDING", 4),
                else_=5,
            )
            query = query.order_by(role_order, User.created_at.desc())
            query = query.limit(limit).offset(offset)

            results = query.all()

            # Build response with role from database
            user_data = []
            for user, group_count in results:
                # Use role directly from database (PENDING, USER, or ADMIN)
                role = user.role
                user_data.append((user, role, group_count))

            return user_data, total_count

    def get_user_detail(self, user_id: str) -> Tuple[User, str, List[Group]]:
        """Get detailed user information including all group memberships.

        Args:
            user_id: The user's ID

        Returns:
            Tuple of (User, role, list of Groups)
            where role is 'admin' or 'user'

        Raises:
            ValueError: If user not found
        """
        with get_db() as session:
            # Get user
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Get user's groups
            groups = (
                session.query(Group)
                .join(GroupMembership, GroupMembership.group_id == Group.id)
                .filter(GroupMembership.user_id == user_id)
                .order_by(Group.is_system.desc(), Group.name)
                .all()
            )

            # Use role directly from database (PENDING, USER, or ADMIN)
            role = user.role

            return user, role, groups

    def update_user_groups(
        self, user_id: str, group_ids: List[str], current_user: dict
    ) -> None:
        """Update user's group memberships.

        This replaces all existing group memberships with the provided list.

        Args:
            user_id: The user's ID
            group_ids: List of group IDs to assign
            current_user: Current user performing the operation (for audit)

        Raises:
            ValueError: If user not found or invalid group IDs
            PermissionError: If current user is not admin
        """
        # Verify current user is admin
        if not current_user.get("is_admin", False):
            raise PermissionError("Only administrators can update user groups")

        with get_db() as session:
            # Verify user exists
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Verify all groups exist
            if group_ids:
                existing_groups = (
                    session.query(Group).filter(Group.id.in_(group_ids)).all()
                )
                if len(existing_groups) != len(group_ids):
                    found_ids = {g.id for g in existing_groups}
                    invalid_ids = set(group_ids) - found_ids
                    raise ValueError(f"Invalid group IDs: {invalid_ids}")

                # Check if Administrators group is being modified
                admin_group = (
                    session.query(Group)
                    .filter(Group.name == ADMINISTRATORS_GROUP_NAME)
                    .first()
                )
                admin_group_modified = admin_group and (
                    admin_group.id in group_ids
                    or any(
                        m.group_id == admin_group.id
                        for m in session.query(GroupMembership).filter(
                            GroupMembership.user_id == user_id
                        )
                    )
                )
            else:
                # Empty group list - check if user was in Administrators group
                admin_group = (
                    session.query(Group)
                    .filter(Group.name == ADMINISTRATORS_GROUP_NAME)
                    .first()
                )
                admin_group_modified = (
                    admin_group
                    and session.query(GroupMembership)
                    .filter(
                        GroupMembership.user_id == user_id,
                        GroupMembership.group_id == admin_group.id,
                    )
                    .first()
                    is not None
                )

            # Remove all existing memberships
            session.query(GroupMembership).filter(
                GroupMembership.user_id == user_id
            ).delete()

            # Add new memberships
            for group_id in group_ids:
                membership = GroupMembership(user_id=user_id, group_id=group_id)
                session.add(membership)

            session.commit()

            # Clear admin cache if Administrators group was modified
            if admin_group_modified:
                clear_admin_group_cache()

            # Audit logging
            user_email = current_user.get("email", "unknown")
            logger.info(
                f"[AUDIT] User groups updated by {_redact_email(user_email)}: "
                f"user_id={user_id}, new_groups={len(group_ids)}"
            )

    def delete_user(self, user_id: str, current_user: dict) -> None:
        """Delete a user permanently.

        Removes the user from all group memberships before deleting the user record.

        Args:
            user_id: The user's ID
            current_user: Current user performing the operation (for audit)

        Raises:
            ValueError: If user not found
            PermissionError: If current user is not admin, trying to self-delete,
                             or trying to delete an env-protected admin
        """
        # Verify current user is admin
        if not current_user.get("is_admin", False):
            raise PermissionError("Only administrators can delete users")

        # Prevent self-deletion: compare by sub (user ID) and email
        current_user_sub = current_user.get("sub", "")
        current_user_email = current_user.get("email", "")

        with get_db() as session:
            # Verify user exists
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Self-deletion check: compare DB user ID and email against current user
            if user.id == current_user_sub or (
                user.email
                and current_user_email
                and user.email.lower() == current_user_email.lower()
            ):
                raise PermissionError("Cannot delete your own account")

            # Check if user is env-protected admin
            if user.role == "ADMIN":
                auth_config = get_auth_config()
                is_env_protected = False

                # Check ADMIN_USERS
                if user.email and user.email.lower() in auth_config.admin_users:
                    is_env_protected = True

                # Check ADMIN_GROUP
                if not is_env_protected and auth_config.admin_group:
                    if (
                        isinstance(user.groups, list)
                        and auth_config.admin_group in user.groups
                    ):
                        is_env_protected = True

                if is_env_protected:
                    raise PermissionError(
                        "Cannot delete environment-protected admin user. "
                        "User is configured as admin via ADMIN_USERS or ADMIN_GROUP environment variable."
                    )

            # Store info for audit log before deletion
            deleted_email = user.email or "N/A"

            # Remove all group memberships
            session.query(GroupMembership).filter(
                GroupMembership.user_id == user_id
            ).delete()

            # Delete the user record
            session.delete(user)
            session.commit()

            # Clear admin cache in case user was an admin
            clear_admin_group_cache(user_id)

            # Audit logging
            admin_email = current_user.get("email", "unknown")
            logger.info(
                f"[AUDIT] User deleted by {_redact_email(admin_email)}: "
                f"user_id={user_id}, user_email={_redact_email(deleted_email)}"
            )

    def update_user_role(self, user_id: str, new_role: str, current_user: dict) -> None:
        """Update user's role.

        This updates the user's role and syncs with Administrators group membership.

        Args:
            user_id: The user's ID
            new_role: New role ('PENDING', 'USER', or 'ADMIN')
            current_user: Current user performing the operation (for audit)

        Raises:
            ValueError: If user not found or invalid role
            PermissionError: If current user is not admin or trying to modify env-protected admin
        """
        # Verify current user is admin
        if not current_user.get("is_admin", False):
            raise PermissionError("Only administrators can update user roles")

        # Validate role
        new_role = new_role.upper()
        if new_role not in UserRole.values():
            raise ValueError(
                f"Invalid role: {new_role}. Must be one of: {', '.join(UserRole.values())}"
            )

        with get_db() as session:
            # Verify user exists
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Check if user is env-protected admin (cannot be changed from ADMIN)
            if user.role == "ADMIN" and new_role != "ADMIN":
                # Check if user is protected by ADMIN_USERS or ADMIN_GROUP env vars
                auth_config = get_auth_config()
                is_env_protected = False

                # Check ADMIN_USERS
                if user.email and user.email.lower() in auth_config.admin_users:
                    is_env_protected = True

                # Check ADMIN_GROUP
                if not is_env_protected and auth_config.admin_group:
                    if (
                        isinstance(user.groups, list)
                        and auth_config.admin_group in user.groups
                    ):
                        is_env_protected = True

                if is_env_protected:
                    raise PermissionError(
                        "Cannot change role for environment-protected admin user. "
                        "User is configured as admin via ADMIN_USERS or ADMIN_GROUP environment variable."
                    )

            # Store old role for logging
            old_role = user.role

            # Update role
            user.role = new_role

            # Sync with Administrators group
            admin_group = (
                session.query(Group)
                .filter(Group.name == ADMINISTRATORS_GROUP_NAME)
                .first()
            )

            if admin_group:
                # Check current membership
                current_membership = (
                    session.query(GroupMembership)
                    .filter(
                        GroupMembership.user_id == user_id,
                        GroupMembership.group_id == admin_group.id,
                    )
                    .first()
                )

                if new_role == "ADMIN":
                    # Add to Administrators group if not already member
                    if not current_membership:
                        membership = GroupMembership(
                            user_id=user_id, group_id=admin_group.id
                        )
                        session.add(membership)
                        logger.info(
                            f"[RBAC] Added user to {ADMINISTRATORS_GROUP_NAME} group (role=ADMIN)"
                        )
                else:
                    # Remove from Administrators group if currently member
                    if current_membership:
                        session.delete(current_membership)
                        logger.info(
                            f"[RBAC] Removed user from {ADMINISTRATORS_GROUP_NAME} group (role={new_role})"
                        )

            session.commit()

            # Clear admin cache
            clear_admin_group_cache(user_id)

            # Audit logging
            user_email = current_user.get("email", "unknown")
            logger.info(
                f"[AUDIT] User role updated by {_redact_email(user_email)}: "
                f"user_id={user_id}, old_role={old_role}, new_role={new_role}"
            )
