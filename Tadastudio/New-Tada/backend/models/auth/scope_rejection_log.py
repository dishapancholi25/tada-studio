"""Scope rejection audit log model.

Each row records one PAT scope enforcement failure, enabling per-token and
global audit views.
"""

from sqlalchemy import Column, DateTime, ForeignKey, String, func

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin


class ScopeRejectionLog(Base, UUIDPrimaryKeyMixin):
    """Audit log entry for PAT scope enforcement failures.

    Attributes:
        token_id: FK to the UserAPIToken that was used (nullable — survives deletion).
        token_prefix: Denormalised prefix for display after token deletion.
        user_id: Owner of the token.
        resource: Route that was requested, e.g. "GET /api/graph/list".
        scope_required: Scope string that was required but absent.
        scopes_held: JSON-encoded snapshot of the scopes the token held.
        client_ip: Client IP address.
        timestamp: When the rejection occurred.
    """

    __tablename__ = "scope_rejection_log"

    token_id = Column(
        String,
        ForeignKey("user_api_tokens.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    token_prefix = Column(String(12), nullable=True)
    user_id = Column(String, nullable=True, index=True)
    resource = Column(String, nullable=False)
    scope_required = Column(String, nullable=False)
    scopes_held = Column(String, nullable=True)  # JSON-encoded list
    client_ip = Column(String, nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
