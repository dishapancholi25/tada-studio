"""User role enumeration and helper functions."""

from enum import Enum


class UserRole(str, Enum):
    """User role enumeration.

    Defines the possible user roles in the system:
    - PENDING: User awaiting admin approval
    - USER: Standard authenticated user with access to the system
    - ADMIN: Administrator with full system access
    - SYSTEM: Service account / managed identity (auto-assigned, non-human)
    """

    PENDING = "PENDING"
    USER = "USER"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"

    def is_admin(self) -> bool:
        """Check if role is admin.

        Returns:
            bool: True if role is ADMIN
        """
        return self == UserRole.ADMIN

    def is_pending(self) -> bool:
        """Check if role is pending.

        Returns:
            bool: True if role is PENDING
        """
        return self == UserRole.PENDING

    def is_system(self) -> bool:
        """Check if role is a system/service account.

        Returns:
            bool: True if role is SYSTEM
        """
        return self == UserRole.SYSTEM

    def can_access_system(self) -> bool:
        """Check if role allows system access.

        Returns:
            bool: True if role is not PENDING
        """
        return self != UserRole.PENDING

    @classmethod
    def values(cls) -> list[str]:
        """Get all valid role values.

        Returns:
            list[str]: List of role values
        """
        return [role.value for role in cls]
