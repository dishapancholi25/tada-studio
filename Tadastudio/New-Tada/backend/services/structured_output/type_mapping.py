"""
Type mapping utilities for converting field type enums to Python types.

This module provides functions to map FieldType enums to actual Python type objects
for use in Pydantic model generation.
"""

from typing import Any, Dict, List, Optional, Type, Union

from .schemas import FieldType


def get_python_type(field_type: FieldType, required: bool = True) -> Type:
    """
    Convert field type enum to Python type.

    Automatically wraps types in Optional[] when required=False for better type safety.

    Args:
        field_type: The FieldType enum value
        required: Whether the field is required (default: True)

    Returns:
        The corresponding Python type annotation, wrapped in Optional[] if not required

    Examples:
        >>> get_python_type(FieldType.STR, required=True)
        <class 'str'>
        >>> get_python_type(FieldType.STR, required=False)
        typing.Optional[str]
        >>> get_python_type(FieldType.LIST_STR, required=False)
        typing.Optional[typing.List[str]]
    """
    type_mapping = {
        FieldType.STR: str,
        FieldType.INT: int,
        FieldType.FLOAT: float,
        FieldType.BOOL: bool,
        FieldType.LIST_STR: List[str],
        FieldType.LIST_INT: List[int],
        FieldType.LIST_FLOAT: List[float],
        FieldType.DICT_STR_ANY: Dict[str, Any],
        FieldType.LIST_DICT_STR_ANY: List[Dict[str, Any]],
        # Optional types are kept for backward compatibility
        FieldType.OPTIONAL_STR: Optional[str],
        FieldType.OPTIONAL_INT: Optional[int],
        FieldType.OPTIONAL_FLOAT: Optional[float],
    }

    base_type = type_mapping.get(field_type, str)

    # If field is not required and not already Optional, wrap it in Optional[]
    if not required and not is_optional_type(base_type):
        return Optional[base_type]

    return base_type


def is_optional_type(python_type: Type) -> bool:
    """
    Check if a Python type is an Optional type.

    Args:
        python_type: The Python type to check

    Returns:
        True if the type is Optional[T] (Union[T, None])
    """
    return hasattr(python_type, "__origin__") and python_type.__origin__ is Union


def is_list_type(python_type: Type) -> bool:
    """
    Check if a Python type is a List type.

    Args:
        python_type: The Python type to check

    Returns:
        True if the type is List[T]
    """
    return hasattr(python_type, "__origin__") and python_type.__origin__ is list


def is_dict_type(python_type: Type) -> bool:
    """
    Check if a Python type is a Dict type.

    Args:
        python_type: The Python type to check

    Returns:
        True if the type is Dict[K, V]
    """
    return hasattr(python_type, "__origin__") and python_type.__origin__ is dict


def get_inner_type(python_type: Type) -> Type:
    """
    Get the inner type from Optional, List, or Dict types.

    Args:
        python_type: The Python type to extract from

    Returns:
        The inner type (e.g., str from Optional[str])

    Examples:
        >>> get_inner_type(Optional[str])
        <class 'str'>
        >>> get_inner_type(List[int])
        <class 'int'>
    """
    if hasattr(python_type, "__args__") and python_type.__args__:
        return python_type.__args__[0]
    return python_type
