"""Configuration for Document Load action nodes.

This module defines the configuration dataclass for Document Load nodes,
which deterministically load full document content from collections
into the workflow state.
"""

from dataclasses import dataclass, field
from typing import List, Literal, Optional


@dataclass
class DocumentLoadConfig:
    """Configuration for a Document Load action node.

    Attributes:
        collection_id: Source collection ID
        document_ids: Specific document IDs to load (empty = load all from collection)
        max_document_size_tokens: Per-document safety cap on token count
        truncation_strategy: How to handle documents exceeding the token limit
        output_mode: Single document or batch array output
        chunk_output_mode: How to structure output for large documents
        chunk_token_limit: Token limit per chunk when using by_token_limit mode
        output_format: Format for returned document content
        include_metadata: Whether to include document metadata in results
    """

    collection_id: Optional[str] = None
    document_ids: List[str] = field(default_factory=list)
    max_document_size_tokens: int = 100000
    truncation_strategy: Literal["end", "start"] = "end"
    output_mode: Literal["single", "batch"] = "batch"
    chunk_output_mode: Literal["full", "by_page", "by_token_limit"] = "full"
    chunk_token_limit: int = 50000
    output_format: Literal["markdown", "plain", "json"] = "markdown"
    include_metadata: bool = True
