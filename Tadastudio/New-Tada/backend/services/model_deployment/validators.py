"""Validation utilities for model deployment data.

This module provides validation functions for model deployment
configurations, settings, and credentials.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ...models import ModelDeployment
from .exceptions import (
    DuplicateDeploymentNameError,
    InvalidCredentialError,
    InvalidSettingsError,
)


logger = logging.getLogger(__name__)


def validate_unique_name(
    db: Session, name: str, exclude_id: Optional[str] = None
) -> None:
    """Validate that deployment name is unique.

    Args:
        db: Database session
        name: Deployment name to validate
        exclude_id: Optional deployment ID to exclude from check (for updates)

    Raises:
        DuplicateDeploymentNameError: If name already exists
    """
    query = db.query(ModelDeployment).filter(ModelDeployment.name == name.strip())
    if exclude_id:
        query = query.filter(ModelDeployment.id != exclude_id)
    if query.first():
        raise DuplicateDeploymentNameError(name)


def normalize_settings(settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize and validate settings dictionary.

    Args:
        settings: Settings dictionary to normalize

    Returns:
        Normalized settings dictionary (trimmed strings)

    Raises:
        InvalidSettingsError: If settings is not a dictionary
    """
    if not settings:
        return {}

    if not isinstance(settings, dict):
        raise InvalidSettingsError("Settings must be an object/dictionary")

    # Trim string values
    normalized = {}
    for key, value in settings.items():
        if isinstance(value, str):
            normalized[key] = value.strip()
        else:
            normalized[key] = value

    return normalized


def validate_deployment_create_payload(payload: Dict[str, Any]) -> None:
    """Validate deployment creation payload.

    Args:
        payload: Create deployment payload

    Raises:
        InvalidSettingsError: If required fields are missing or invalid
    """
    required_fields = ["name", "provider", "model_name"]
    for field in required_fields:
        if field not in payload or not payload[field]:
            raise InvalidSettingsError(f"Required field '{field}' is missing or empty")

        if not isinstance(payload[field], str):
            raise InvalidSettingsError(
                f"Field '{field}' must be a string, got {type(payload[field]).__name__}"
            )


def validate_provider_string(provider: str) -> str:
    """Validate and normalize provider string.

    Args:
        provider: Provider identifier

    Returns:
        Normalized provider string (lowercase, trimmed)

    Raises:
        InvalidSettingsError: If provider is empty or invalid
    """
    if not provider or not isinstance(provider, str):
        raise InvalidSettingsError("Provider must be a non-empty string")

    normalized = provider.strip().lower()
    if not normalized:
        raise InvalidSettingsError("Provider cannot be empty or whitespace only")

    return normalized


def validate_model_type(model_type: Optional[str]) -> str:
    """Validate and normalize model type field.

    Args:
        model_type: Model type ('llm' or 'embedding')

    Returns:
        Normalized model type string (lowercase, trimmed)

    Raises:
        InvalidSettingsError: If model_type is invalid
    """
    if not model_type:
        return "llm"  # default

    if not isinstance(model_type, str):
        raise InvalidSettingsError("Model type must be a string")

    normalized = model_type.strip().lower()
    if normalized not in ["llm", "embedding"]:
        raise InvalidSettingsError(
            f"Invalid model_type '{model_type}'. Must be 'llm' or 'embedding'"
        )

    return normalized


def validate_credentials_or_managed_identity(
    provider: str, encrypted_credentials: Optional[Dict], settings: Dict[str, Any]
) -> None:
    """Validate that either credentials are provided OR managed identity is enabled.

    For Azure OpenAI, allows empty credentials if use_managed_identity is True.
    For other providers, credentials are required.

    Args:
        provider: Provider identifier (normalized)
        encrypted_credentials: Encrypted credentials dict (or None)
        settings: Provider settings dict

    Raises:
        InvalidCredentialError: If neither credentials nor managed identity is configured
    """
    use_managed_identity = settings.get("use_managed_identity", False)

    # Azure OpenAI can use managed identity
    if provider == "azure_openai":
        if not encrypted_credentials and not use_managed_identity:
            logger.warning(
                "Creating Azure OpenAI deployment without credentials - will attempt DefaultAzureCredential"
            )
        # Allow creation - will validate at runtime
        return

    # Other providers require credentials
    if not encrypted_credentials:
        raise InvalidCredentialError(
            f"Credentials are required for provider '{provider}'"
        )
