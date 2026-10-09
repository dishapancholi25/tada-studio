"""Workflow publication configuration.

This module defines the configuration for publishing workflows
as HTTP endpoints.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowPublicationConfig:
    """Configuration for publishing workflows as HTTP endpoints.

    Attributes:
        is_published: Whether the workflow is published
        custom_slug: Custom URL slug for the endpoint
        description: Workflow description for documentation
        require_authentication: Require authentication for access
        rate_limit: Rate limiting configuration
        allowed_origins: CORS allowed origins
        webhook_url: Callback URL for execution completion
        input_schema: JSON schema for input validation
        published_at: Publication timestamp
        last_accessed: Last access timestamp
        access_count: Number of times accessed
    """

    is_published: bool = False
    custom_slug: Optional[str] = None
    description: str = ""
    require_authentication: bool = True
    rate_limit: Optional[Dict[str, int]] = None
    allowed_origins: List[str] = field(default_factory=list)
    webhook_url: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    published_at: Optional[str] = None
    last_accessed: Optional[str] = None
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowPublicationConfig":
        """Create instance from dictionary.

        Args:
            data: Dictionary data

        Returns:
            WorkflowPublicationConfig instance
        """
        return cls(**data)
