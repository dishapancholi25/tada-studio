"""Individual validation rules for document search configuration.

Each function validates a specific aspect of the configuration,
keeping complexity low and responsibilities focused.
"""

import logging
from typing import List

from ..schemas import DocumentSearchConfig


logger = logging.getLogger(__name__)


def validate_search_sources(
    config: DocumentSearchConfig,
    errors: List[str],
    warnings: List[str],
) -> None:
    """Validate collection names and document IDs configuration.

    Args:
        config: Configuration to validate
        errors: List to append errors to
        warnings: List to append warnings to
    """
    if not config.collection_names and not config.document_ids:
        warnings.append(
            "No collections or documents specified. "
            "Tool will search all available documents."
        )


def validate_search_type(
    config: DocumentSearchConfig,
    errors: List[str],
    warnings: List[str],
) -> None:
    """Validate search type configuration.

    Args:
        config: Configuration to validate
        errors: List to append errors to
        warnings: List to append warnings to
    """
    valid_search_types = ["similarity", "mmr", "similarity_score_threshold"]
    if config.search_type not in valid_search_types:
        warnings.append(
            f"Unknown search type '{config.search_type}'. "
            f"Valid types: {', '.join(valid_search_types)}. "
            "Defaulting to 'similarity'."
        )


def validate_citation_format(
    config: DocumentSearchConfig,
    errors: List[str],
    warnings: List[str],
) -> None:
    """Validate citation format configuration.

    Args:
        config: Configuration to validate
        errors: List to append errors to
        warnings: List to append warnings to
    """
    valid_citation_formats = ["structured", "inline", "footnote", "none"]
    if config.citation_format not in valid_citation_formats:
        warnings.append(
            f"Unknown citation format '{config.citation_format}'. "
            f"Valid formats: {', '.join(valid_citation_formats)}. "
            "Defaulting to 'structured'."
        )


def validate_search_mode(
    config: DocumentSearchConfig,
    errors: List[str],
    warnings: List[str],
) -> None:
    """Validate search mode configuration.

    Args:
        config: Configuration to validate
        errors: List to append errors to
        warnings: List to append warnings to
    """
    valid_search_modes = ["vector", "keyword", "hybrid"]
    if config.search_mode not in valid_search_modes:
        warnings.append(
            f"Unknown search mode '{config.search_mode}'. "
            f"Valid modes: {', '.join(valid_search_modes)}. "
            "Defaulting to 'hybrid'."
        )


def validate_full_document_retrieval(
    config: DocumentSearchConfig,
    errors: List[str],
    warnings: List[str],
) -> None:
    """Validate full document retrieval constraints.

    Args:
        config: Configuration to validate
        errors: List to append errors to
        warnings: List to append warnings to
    """
    if not config.return_full_document:
        return

    if not config.document_ids:
        errors.append(
            "Full document retrieval requires at least one document ID to be specified."
        )
    elif len(config.document_ids) > 1:
        errors.append(
            "Full document retrieval only works with a single document ID. "
            f"Found {len(config.document_ids)} document IDs."
        )

    if config.collection_names:
        warnings.append(
            "Full document retrieval ignores collection_names. "
            "Only the specified document_id will be used."
        )


def validate_search_k(
    config: DocumentSearchConfig,
    errors: List[str],
    warnings: List[str],
) -> None:
    """Validate search_k parameter.

    Args:
        config: Configuration to validate
        errors: List to append errors to
        warnings: List to append warnings to
    """
    if config.search_k < 1:
        errors.append(f"search_k must be at least 1, got {config.search_k}")
    elif config.search_k > 50:
        warnings.append(
            f"search_k is very high ({config.search_k}). "
            "This may result in large responses and slow performance."
        )


def validate_similarity_threshold(
    config: DocumentSearchConfig,
    errors: List[str],
    warnings: List[str],
) -> None:
    """Validate similarity threshold parameter.

    Args:
        config: Configuration to validate
        errors: List to append errors to
        warnings: List to append warnings to
    """
    if not (0.0 <= config.similarity_threshold <= 1.0):
        errors.append(
            f"similarity_threshold must be between 0.0 and 1.0, "
            f"got {config.similarity_threshold}"
        )


def validate_keyword_weight(
    config: DocumentSearchConfig,
    errors: List[str],
    warnings: List[str],
) -> None:
    """Validate keyword weight parameter.

    Args:
        config: Configuration to validate
        errors: List to append errors to
        warnings: List to append warnings to
    """
    if not (0.0 <= config.keyword_weight <= 1.0):
        errors.append(
            f"keyword_weight must be between 0.0 and 1.0, got {config.keyword_weight}"
        )


def validate_conflicting_settings(
    config: DocumentSearchConfig,
    errors: List[str],
    warnings: List[str],
) -> None:
    """Validate for conflicting configuration settings.

    Args:
        config: Configuration to validate
        errors: List to append errors to
        warnings: List to append warnings to
    """
    if config.search_mode == "keyword" and not config.hybrid_search_enabled:
        warnings.append(
            "search_mode is 'keyword' but hybrid_search_enabled is False. "
            "Keyword search requires hybrid_search_enabled=True."
        )
