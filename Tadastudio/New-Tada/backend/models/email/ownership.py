"""Persistent ownership records for provider-managed email resources."""

from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.sql import func

from ...services.database import Base


class EmailInboxOwnership(Base):
    """Owner mapping for provider-side email inbox identifiers."""

    __tablename__ = "email_inbox_ownership"
    __table_args__ = (Index("idx_email_inbox_ownership_owner_id", "owner_id"),)

    inbox_id = Column(String, primary_key=True)
    owner_id = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EmailWebhookOwnership(Base):
    """Owner mapping for provider-side email webhook identifiers."""

    __tablename__ = "email_webhook_ownership"
    __table_args__ = (
        Index("idx_email_webhook_ownership_owner_id", "owner_id"),
        Index("idx_email_webhook_ownership_inbox_id", "inbox_id"),
    )

    webhook_id = Column(String, primary_key=True)
    owner_id = Column(String, nullable=False)
    inbox_id = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
