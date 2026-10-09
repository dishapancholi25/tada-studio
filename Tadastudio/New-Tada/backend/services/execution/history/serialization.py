"""JSON serialization utilities for execution history.

This module provides utilities for converting non-JSON serializable types
(Decimal, datetime, custom objects) into JSON-compatible formats.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any


def make_json_serializable(obj: Any) -> Any:
    """Convert non-JSON serializable types to serializable formats.

    Recursively processes objects to ensure they can be serialized to JSON.
    Handles common types like Decimal, datetime, dict, list, tuple, and custom objects.

    Args:
        obj: The object to make JSON serializable

    Returns:
        JSON-serializable version of the object

    Examples:
        >>> from decimal import Decimal
        >>> make_json_serializable(Decimal("123.45"))
        123.45

        >>> from datetime import datetime
        >>> dt = datetime(2024, 1, 1, 12, 0, 0)
        >>> make_json_serializable(dt)
        '2024-01-01T12:00:00'

        >>> make_json_serializable({"value": Decimal("10"), "time": dt})
        {'value': 10.0, 'time': '2024-01-01T12:00:00'}
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(make_json_serializable(item) for item in obj)
    elif hasattr(obj, "__dict__"):
        # Handle custom objects by converting to dict
        return make_json_serializable(obj.__dict__)
    else:
        return obj
