"""
Input building services for node execution.

This module provides comprehensive input building functionality:
- Multiple input sources (start, previous, specific nodes, custom templates)
- Multi-source combination
- Field extraction and structured data handling
"""

from .builder import InputBuilder
from .combiners import MultiSourceCombiner
from .sources import (
    CustomTemplateInputSource,
    FieldInputSource,
    InputSource,
    PreviousInputSource,
    SpecificNodeInputSource,
    StartInputSource,
)


__all__ = [
    "InputBuilder",
    "InputSource",
    "StartInputSource",
    "PreviousInputSource",
    "SpecificNodeInputSource",
    "CustomTemplateInputSource",
    "FieldInputSource",
    "MultiSourceCombiner",
]
