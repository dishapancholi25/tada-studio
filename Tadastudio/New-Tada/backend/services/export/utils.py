"""Utility functions for the export service."""

import re


def safe_name(name: str) -> str:
    """Convert a node name to a valid Python identifier."""
    s = re.sub(r"[^a-zA-Z0-9]", "_", name)
    s = re.sub(r"^[0-9]+", "", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    return s.lower() or "node"
