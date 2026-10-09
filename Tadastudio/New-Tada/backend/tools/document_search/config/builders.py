"""Tool description builder for document search.

Dynamically builds tool descriptions based on configuration
to provide context-aware documentation to LLM agents.
"""

import logging

from ..schemas import DocumentSearchConfig


logger = logging.getLogger(__name__)


class ToolDescriptionBuilder:
    """Builds dynamic tool descriptions based on configuration."""

    @staticmethod
    def build_description(config: DocumentSearchConfig) -> str:
        """Build tool description from configuration.

        Args:
            config: Document search configuration

        Returns:
            Human-readable tool description
        """
        desc_parts = []

        # Describe what's being searched
        if config.collection_names:
            desc_parts.append(f"{len(config.collection_names)} collection(s)")
        if config.document_ids:
            desc_parts.append(f"{len(config.document_ids)} specific document(s)")

        if desc_parts:
            search_scope = " and ".join(desc_parts)
        else:
            search_scope = "configured documents"

        # Build full description
        if (
            config.return_full_document
            and config.document_ids
            and len(config.document_ids) == 1
        ):
            description = (
                "Retrieve the full content of a document. "
                "Returns the complete document with all chunks."
            )
        else:
            description = (
                f"Search through {search_scope} to find relevant information. "
                f"Returns up to {config.search_k} most relevant excerpts with citations."
            )

        # Add search mode info
        if config.hybrid_search_enabled:
            if config.search_mode == "hybrid":
                description += (
                    " Uses hybrid vector + keyword search for better results."
                )
            elif config.search_mode == "keyword":
                description += " Uses keyword-based full-text search."
            else:
                description += " Uses vector similarity search."

        return description
