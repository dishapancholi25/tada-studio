"""Wiki page models.

This module contains models for wiki pages and revision history.
"""

from .page import WikiPage
from .revision import WikiRevision


__all__ = [
    "WikiPage",
    "WikiRevision",
]
