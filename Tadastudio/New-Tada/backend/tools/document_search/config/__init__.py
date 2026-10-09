"""Configuration module for document search tool.

This module provides configuration validation, description building,
and default configurations for the document search tool.

The module is split into focused submodules to maintain low complexity:
- builders: Tool description generation
- validators: Configuration validation
- validation_rules: Individual validation functions
- defaults: Preset configurations

Public API:
    - ToolDescriptionBuilder: Builds dynamic tool descriptions
    - ConfigValidator: Validates configuration
    - DEFAULT_SIMILARITY_CONFIG: Vector similarity search preset
    - DEFAULT_HYBRID_CONFIG: Hybrid vector+keyword search preset
    - DEFAULT_FULL_DOCUMENT_CONFIG: Full document retrieval preset
"""

from .builders import ToolDescriptionBuilder
from .defaults import (
    DEFAULT_FULL_DOCUMENT_CONFIG,
    DEFAULT_HYBRID_CONFIG,
    DEFAULT_SIMILARITY_CONFIG,
)
from .validators import ConfigValidator


__all__ = [
    "ToolDescriptionBuilder",
    "ConfigValidator",
    "DEFAULT_SIMILARITY_CONFIG",
    "DEFAULT_HYBRID_CONFIG",
    "DEFAULT_FULL_DOCUMENT_CONFIG",
]
