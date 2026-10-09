"""Configuration validation for document search tool.

This module orchestrates multiple validation rules to ensure
configuration is valid and safe to use.
"""

import logging
from typing import List, Tuple

from ..schemas import DocumentSearchConfig
from .validation_rules import (
    validate_citation_format,
    validate_conflicting_settings,
    validate_full_document_retrieval,
    validate_keyword_weight,
    validate_search_k,
    validate_search_mode,
    validate_search_sources,
    validate_search_type,
    validate_similarity_threshold,
)


logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates document search configurations.

    Uses focused validation rules to check configuration,
    keeping complexity low and responsibilities clear.
    """

    @staticmethod
    def validate(
        config: DocumentSearchConfig,
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate configuration and return status with errors/warnings.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Run all validation rules
        validate_search_sources(config, errors, warnings)
        validate_search_type(config, errors, warnings)
        validate_citation_format(config, errors, warnings)
        validate_search_mode(config, errors, warnings)
        validate_full_document_retrieval(config, errors, warnings)
        validate_search_k(config, errors, warnings)
        validate_similarity_threshold(config, errors, warnings)
        validate_keyword_weight(config, errors, warnings)
        validate_conflicting_settings(config, errors, warnings)

        is_valid = len(errors) == 0
        return is_valid, errors, warnings
