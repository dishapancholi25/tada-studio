"""Tool security policy model for admin-configurable SSRF allow-lists."""

import uuid

from sqlalchemy import Boolean, Column, String
from sqlalchemy.types import JSON

from ...services.database import Base
from ..base import TimestampMixin


class ToolSecurityPolicy(Base, TimestampMixin):
    """Per-tool/service security policy for outbound-request protection.

    Stores an admin-managed allow-list of endpoints for a given tool or
    service, keyed by a canonical tool identifier (e.g. ``"HTTP_REQUEST"``).
    Each entry is an exact IP/host, optionally scoped to a specific port
    and/or path (e.g. ``10.0.0.1``, ``10.0.0.1:5005``, ``10.0.0.1/get``,
    ``10.0.0.1:5005/get``, a domain, or a full URL). An empty list fails
    closed (nothing is allowed). ``allowed_ip_ranges`` always holds the
    full, effective allow-list used by SSRF validation.

    ``fixed_ips`` is a purely informational subset of ``allowed_ip_ranges``
    listing which entries were seeded from the ``<TOOL_ID>_ALLOWED_IPS``
    environment variable. It exists only so the frontend can render those
    entries as non-removable (no delete/cross icon); it is never read by the
    SSRF validator and has no effect on request matching/blocking behavior.

    Designed to scale to other services later by adding new ``tool_id`` rows.
    """

    __tablename__ = "tool_security_policies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tool_id = Column(String, unique=True, nullable=False, index=True)
    allowed_ip_ranges = Column(JSON, nullable=False, default=list)
    fixed_ips = Column(JSON, nullable=False, default=list)
    enabled = Column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "tool_id": self.tool_id,
            "allowed_ip_ranges": self.allowed_ip_ranges or [],
            "fixed_ips": self.fixed_ips or [],
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
