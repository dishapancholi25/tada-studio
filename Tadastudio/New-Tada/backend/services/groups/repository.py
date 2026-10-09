"""Repository for group and group membership operations."""

import logging
from typing import Optional, Tuple, List
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from ...models.auth import Group, GroupMembership, User
from ...services.database import get_db

logger = logging.getLogger(__name__)


class GroupRepository:
    def create_group(self, name, description, is_system, created_by_user_id):
        with get_db() as db:
            group = Group(
                name=name,
                description=description,
                is_system=is_system,
                created_by_user_id=created_by_user_id,
            )
            db.add(group)
            try:
                db.commit()
                db.refresh(group)
                return group
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to create group: {e}")
                return None

    def get_group(self, group_id):
        with get_db() as db:
            return db.query(Group).filter(Group.id == group_id).first()

    def update_group(self, group_id, name, description):
        with get_db() as db:
            group = db.query(Group).filter(Group.id == group_id).first()
            if not group or group.is_system:
                return None
            if name:
                group.name = name
            if description is not None:
                group.description = description
            try:
                db.commit()
                db.refresh(group)
                return group
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to update group: {e}")
                return None

    def delete_group(self, group_id):
        with get_db() as db:
            group = db.query(Group).filter(Group.id == group_id).first()
            if not group or group.is_system:
                return False
            db.delete(group)
            try:
                db.commit()
                return True
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to delete group: {e}")
                return False

    def group_exists(self, group_name):
        with get_db() as db:
            return db.query(Group).filter(Group.name == group_name).first() is not None

    def get_groups(
        self, limit: int = 50, offset: int = 0, search: Optional[str] = None
    ) -> Tuple[List, int]:
        """Get paginated list of groups with member counts.

        Args:
            limit: Maximum number of groups to return (default 50)
            offset: Number of groups to skip (default 0)
            search: Optional search query to filter by group name (case-insensitive)

        Returns:
            Tuple of (list of (Group, member_count, created_by_name), total_count)
        """
        with get_db() as db:
            q = (
                db.query(
                    Group,
                    func.count(GroupMembership.id).label("member_count"),
                    User.name.label("created_by_name"),
                )
                .outerjoin(GroupMembership, Group.id == GroupMembership.group_id)
                .outerjoin(User, Group.created_by_user_id == User.id)
                .group_by(Group.id, User.name)
            )

            # Apply search filter if provided
            if search:
                search_pattern = f"%{search}%"
                q = q.filter(Group.name.ilike(search_pattern))

            # Get total count before pagination
            total_count = q.count()

            # Apply ordering and pagination
            q = q.order_by(Group.is_system.desc(), Group.name.asc())
            q = q.limit(limit).offset(offset)

            return q.all(), total_count

    def add_member(self, group_id=None, user_id=None, group_name=None):
        """Add a user to a group by group_id or group_name.
        
        Idempotent - safely handles the case where membership already exists.
        Logs only when a new membership is created.
        """
        with get_db() as db:
            if group_id is None and group_name is not None:
                group = db.query(Group).filter_by(name=group_name).first()
                if not group:
                    raise ValueError(f"Group with name {group_name} not found")
                group_id = group.id
                group_name_for_log = group.name
            else:
                group_name_for_log = None
                
            if group_id is None or user_id is None:
                raise ValueError("group_id (or group_name) and user_id are required")
            exists = (
                db.query(GroupMembership)
                .filter_by(group_id=group_id, user_id=user_id)
                .first()
            )
            if exists:
                return exists
                
            membership = GroupMembership(group_id=group_id, user_id=user_id)
            db.add(membership)
            try:
                db.commit()
                db.refresh(membership)
                # Log only when successfully created
                if group_name_for_log:
                    logger.info(f"Added user to group '{group_name_for_log}'")
                else:
                    logger.info(f"Added user to group (id={group_id})")
                return membership
            except IntegrityError:
                db.rollback()
                logger.debug(
                    "Membership already exists (concurrent insert), returning existing row"
                )
                return (
                    db.query(GroupMembership)
                    .filter_by(group_id=group_id, user_id=user_id)
                    .first()
                )
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to add member: {e}")
                return None

    def remove_member(self, group_id, user_id):
        with get_db() as db:
            membership = (
                db.query(GroupMembership)
                .filter_by(group_id=group_id, user_id=user_id)
                .first()
            )
            if not membership:
                return False
            db.delete(membership)
            try:
                db.commit()
                return True
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to remove member: {e}")
                return False

    def get_group_members(self, group_id):
        with get_db() as db:
            q = (
                db.query(GroupMembership, User)
                .join(User, GroupMembership.user_id == User.id)
                .filter(GroupMembership.group_id == group_id)
            )
            return q.all()

    def get_all_users(self):
        """Return all users in the system."""
        with get_db() as db:
            return db.query(User).order_by(User.name.asc()).all()

    def get_user_custom_groups(self, user_id):
        with get_db() as db:
            q = (
                db.query(Group)
                .join(GroupMembership, Group.id == GroupMembership.group_id)
                .filter(GroupMembership.user_id == user_id, Group.is_system.is_(False))
            )
            return q.all()
