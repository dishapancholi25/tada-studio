"""Configuration for Document Retrieve tool nodes.

This module defines the configuration dataclass for Document Retrieve nodes,
which allow agents to fetch full document content from collections.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DocumentRetrieveConfig:
    """Configuration for a Document Retrieve tool node.

    Attributes:
        collection_ids: Collection IDs the agent can retrieve from
        parent_agent_id: ID of the parent agent node
    """

    collection_ids: List[str] = field(default_factory=list)
    parent_agent_id: Optional[str] = None
