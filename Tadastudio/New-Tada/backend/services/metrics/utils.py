"""
Utility functions for metrics collection.

This module provides helper functions for validation, calculations,
and metric manipulation.
"""

import math
import re
from typing import List

from .config import (
    MAX_LABEL_COUNT,
    MAX_LABEL_KEY_LENGTH,
    MAX_LABEL_VALUE_LENGTH,
    MAX_METRIC_NAME_LENGTH,
    METRIC_NAME_PATTERN,
)
from .models import InvalidMetricError


def validate_metric_name(name: str) -> None:
    """
    Validate metric name.

    Args:
        name: Metric name to validate

    Raises:
        InvalidMetricError: If name is invalid
    """
    if not name:
        raise InvalidMetricError("Metric name cannot be empty")

    if len(name) > MAX_METRIC_NAME_LENGTH:
        raise InvalidMetricError(
            f"Metric name too long: {len(name)} > {MAX_METRIC_NAME_LENGTH}"
        )

    if not re.match(METRIC_NAME_PATTERN, name):
        raise InvalidMetricError(
            f"Invalid metric name '{name}'. Must match pattern: {METRIC_NAME_PATTERN}"
        )


def validate_metric_value(value: float) -> None:
    """
    Validate metric value.

    Args:
        value: Metric value to validate

    Raises:
        InvalidMetricError: If value is invalid (NaN or infinite)
    """
    if not isinstance(value, (int, float)):
        raise InvalidMetricError(f"Metric value must be numeric, got {type(value)}")

    if math.isnan(value):
        raise InvalidMetricError("Metric value cannot be NaN")

    if math.isinf(value):
        raise InvalidMetricError("Metric value cannot be infinite")


def validate_labels(labels: dict) -> None:
    """
    Validate metric labels.

    Args:
        labels: Dictionary of labels to validate

    Raises:
        InvalidMetricError: If labels are invalid
    """
    if not isinstance(labels, dict):
        raise InvalidMetricError(f"Labels must be a dictionary, got {type(labels)}")

    if len(labels) > MAX_LABEL_COUNT:
        raise InvalidMetricError(f"Too many labels: {len(labels)} > {MAX_LABEL_COUNT}")

    for key, value in labels.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise InvalidMetricError("Label keys and values must be strings")

        if len(key) > MAX_LABEL_KEY_LENGTH:
            raise InvalidMetricError(
                f"Label key too long: {len(key)} > {MAX_LABEL_KEY_LENGTH}"
            )

        if len(value) > MAX_LABEL_VALUE_LENGTH:
            raise InvalidMetricError(
                f"Label value too long: {len(value)} > {MAX_LABEL_VALUE_LENGTH}"
            )


def calculate_percentile(sorted_values: List[float], percentile: float) -> float:
    """
    Calculate percentile from sorted values using linear interpolation.

    This implementation uses bisect for efficient percentile calculation
    and provides more accurate results than simple index-based approach.

    Args:
        sorted_values: List of values in sorted order
        percentile: Percentile to calculate (0.0 to 1.0)

    Returns:
        Percentile value

    Raises:
        ValueError: If percentile is not between 0 and 1
    """
    if not sorted_values:
        return 0.0

    if not 0.0 <= percentile <= 1.0:
        raise ValueError(f"Percentile must be between 0 and 1, got {percentile}")

    if len(sorted_values) == 1:
        return sorted_values[0]

    # Calculate position (using R-7 method, same as NumPy default)
    position = percentile * (len(sorted_values) - 1)
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))

    if lower_index == upper_index:
        return sorted_values[lower_index]

    # Linear interpolation
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    weight = position - lower_index

    return lower_value + weight * (upper_value - lower_value)


def sanitize_metric_name_for_prometheus(name: str) -> str:
    """
    Sanitize metric name for Prometheus format.

    Prometheus requires metric names to use underscores instead of dots
    and follow specific naming conventions.

    Args:
        name: Original metric name

    Returns:
        Prometheus-compatible metric name
    """
    return name.replace(".", "_")
