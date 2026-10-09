"""Service layer for group and membership business logic."""

import logging
from typing import Optional, Tuple, List
from ...models.auth.user import User
from ...services.auth.config import ADMINISTRATORS_GROUP_NAME, get_auth_config
from ...services.auth.rbac import clear_admin_group_cache, is_user_admin
from .repository import GroupRepository

logger = logging.getLogger(__name__)


class GroupService:
    def __init__(self):
        self.repo = GroupRepository()

    def create_group(self, name, description, user_claims):
        if not is_user_admin(user_claims):
            logger.error("Permission denied: user is not admin")
            raise PermissionError("Only administrators can create groups")
        group = self.repo.create_group(name, description, False, user_claims["sub"])
        logger.info(f"Group '{name}' created")
        return group

    def update_group(self, group_id, name, description, user_claims):
        if not is_user_admin(user_claims):
            logger.error("Permission denied: user is not admin")
            raise PermissionError("Only administrators can update groups")
        group = self.repo.get_group(group_id)
        if not group:
            raise ValueError("Group not found")
        if group.is_system:
            logger.error(f"System group '{group.name}' cannot be modified")
            raise PermissionError("System groups cannot be modified")
        updated = self.repo.update_group(group_id, name, description)
        logger.info(f"Group '{group.name}' updated")
        return updated

    def delete_group(self, group_id, user_claims):
        if not is_user_admin(user_claims):
            logger.error("Permission denied: user is not admin")
            raise PermissionError("Only administrators can delete groups")
        group = self.repo.get_group(group_id)
        if not group:
            raise ValueError("Group not found")
        if group.is_system:
            logger.error(f"System group '{group.name}' cannot be deleted")
            raise PermissionError("System groups cannot be deleted")
        result = self.repo.delete_group(group_id)
        logger.info(f"Group '{group.name}' deleted")
        return result

    def manage_members(self, group_id, add_users, remove_users, admin_user_claims):
        if not is_user_admin(admin_user_claims):
            logger.error("Permission denied: user is not admin")
            raise PermissionError("Only administrators can manage group members")
        group = self.repo.get_group(group_id)
        if not group:
            raise ValueError("Group not found")
        # Allow member management on the Administrators group even though
        # it is a system group; block all other system groups.
        if group.is_system and group.name != ADMINISTRATORS_GROUP_NAME:
            logger.error(f"System group '{group.name}' cannot be modified")
            raise PermissionError("System groups cannot be modified")
        is_admin_group = group.name == ADMINISTRATORS_GROUP_NAME
        for user_id in add_users:
            self.repo.add_member(group_id, user_id)
            if is_admin_group:
                clear_admin_group_cache(user_id)
        for user_id in remove_users:
            if is_admin_group and self._is_env_var_admin(user_id):
                raise PermissionError(
                    "Cannot remove environment-configured admin from the Administrators group"
                )
            self.repo.remove_member(group_id, user_id)
            logger.info(f"User removed from group '{group.name}'")
            if is_admin_group:
                clear_admin_group_cache(user_id)
        return True

    def get_groups(
        self, limit: int = 50, offset: int = 0, search: Optional[str] = None
    ) -> Tuple[List, int]:
        """Get paginated list of groups.

        Args:
            limit: Maximum number of groups to return
            offset: Number of groups to skip
            search: Optional search query to filter by group name

        Returns:
            Tuple of (groups_data, total_count)
        """
        return self.repo.get_groups(limit, offset, search)

    def get_all_users(self):
        return self.repo.get_all_users()

    def get_group_members(self, group_id):
        group = self.repo.get_group(group_id)
        if not group:
            raise ValueError("Group not found")
        return self.repo.get_group_members(group_id)

    def get_user_groups(self, user_id):
        """Get manually created groups that the user is a member of.

        Note: This does NOT include Azure AD groups, which are only used for admin role checks.
        """
        custom_groups = self.repo.get_user_custom_groups(user_id)
        custom_group_names = [g.name for g in custom_groups]
        return custom_group_names

    def get_user_group_ids(self, user_id):
        """Get manually created group IDs that the user is a member of.

        Note: This does NOT include Azure AD groups, which are only used for admin role checks.
        """
        custom_groups = self.repo.get_user_custom_groups(user_id)
        custom_group_ids = [str(g.id) for g in custom_groups]
        return custom_group_ids

    def _is_env_var_admin(self, user_id: str) -> bool:
        """Check if a user is an admin via ADMIN_USERS or ADMIN_GROUP env vars."""
        auth_config = get_auth_config()
        from ...services.database import get_db

        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return False
            # Check ADMIN_USERS
            if (
                auth_config.admin_users
                and user.email
                and user.email.lower() in auth_config.admin_users
            ):
                return True
            # Check ADMIN_GROUP against the user's stored OAuth groups
            if auth_config.admin_group and user.groups:
                if (
                    isinstance(user.groups, list)
                    and auth_config.admin_group in user.groups
                ):
                    return True
        return False

    def get_protected_member_ids(self, group_id: str) -> set:
        """Return user IDs that cannot be removed from the Administrators group.

        These are users whose admin status comes from ADMIN_USERS or ADMIN_GROUP env vars.
        """
        group = self.repo.get_group(group_id)
        if not group or group.name != ADMINISTRATORS_GROUP_NAME:
            return set()
        auth_config = get_auth_config()
        if not auth_config.admin_users and not auth_config.admin_group:
            return set()
        members = self.repo.get_group_members(group_id)
        protected = set()
        for membership, user in members:
            # Check ADMIN_USERS
            if (
                auth_config.admin_users
                and user.email
                and user.email.lower() in auth_config.admin_users
            ):
                protected.add(user.id)
                continue
            # Check ADMIN_GROUP
            if auth_config.admin_group and user.groups:
                if (
                    isinstance(user.groups, list)
                    and auth_config.admin_group in user.groups
                ):
                    protected.add(user.id)
        return protected

    def validate_groups_exist(self, group_names):
        missing = []
        for name in group_names:
            if not self.repo.group_exists(name):
                missing.append(name)
        if missing:
            raise ValueError(f"Groups not found: {', '.join(missing)}")
