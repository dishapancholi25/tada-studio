"""Serialization utilities for model deployment data.

This module provides functions for serializing model deployments,
masking sensitive data, and formatting responses.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...models import ModelDeployment
from .encryption import CredentialEncryption


def mask_credential_value(value: Optional[str], mask_length: int = 4) -> Optional[str]:
    """Mask a credential value, showing only the last few characters.

    Args:
        value: Credential value to mask
        mask_length: Number of characters to show at the end

    Returns:
        Masked value or None if input is None/empty

    Examples:
        >>> mask_credential_value("my_secret_key_12345", 4)
        '***************2345'
        >>> mask_credential_value("short", 4)
        '*****'
    """
    if not value:
        return None
    if len(value) <= mask_length * 2:
        return "*" * len(value)
    return f"{'*' * (len(value) - mask_length)}{value[-mask_length:]}"


def serialize_deployment(
    deployment: ModelDeployment,
    include_credentials: bool = False,
    credential_encryption: Optional[CredentialEncryption] = None,
) -> Dict[str, Any]:
    """Serialize a model deployment to a dictionary.

    Args:
        deployment: ModelDeployment instance to serialize
        include_credentials: Whether to include decrypted credentials
        credential_encryption: Encryption handler (uses default if None)

    Returns:
        Dictionary representation of the deployment
    """
    if credential_encryption is None:
        credential_encryption = CredentialEncryption()

    # Decrypt credentials
    decrypted = credential_encryption.decrypt_credentials(
        deployment.encrypted_credentials or {}
    )

    # Format credentials based on include_credentials flag
    if include_credentials:
        credentials_payload = decrypted
    else:
        credentials_payload = (
            {k: mask_credential_value(v) for k, v in decrypted.items()}
            if decrypted
            else None
        )

    return {
        "id": deployment.id,
        "name": deployment.name,
        "description": deployment.description,
        "provider": deployment.provider,
        "model_name": deployment.model_name,
        "model_type": getattr(deployment, "model_type", "llm") or "llm",
        "display_name": deployment.display_name or deployment.name,
        "settings": deployment.settings or {},
        "credentials": credentials_payload,
        "has_credentials": bool(deployment.encrypted_credentials),
        "is_default": bool(deployment.is_default),
        "is_active": bool(deployment.is_active),
        "input_cost_per_million": getattr(deployment, "input_cost_per_million", None),
        "output_cost_per_million": getattr(deployment, "output_cost_per_million", None),
        "created_at": deployment.created_at.isoformat()
        if deployment.created_at
        else None,
        "updated_at": deployment.updated_at.isoformat()
        if deployment.updated_at
        else None,
    }


def serialize_deployment_option(deployment: ModelDeployment) -> Dict[str, Any]:
    """Serialize a deployment to a safe, non-sensitive projection.

    This projection is intended for non-admin consumers (e.g. workflow builder
    model dropdowns). It exposes ONLY non-sensitive selection metadata and
    deployment-level model parameter defaults. It deliberately excludes:

    - credentials / has_credentials
    - settings (endpoint, api_base, api_version, deployment_name, etc.)
    - description and cost fields

    Args:
        deployment: ModelDeployment instance to serialize

    Returns:
        Dictionary with a safe, allow-listed set of fields only
    """
    settings = deployment.settings or {}
    return {
        "id": deployment.id,
        "name": deployment.name,
        "provider": deployment.provider,
        "model_name": deployment.model_name,
        "model_type": getattr(deployment, "model_type", "llm") or "llm",
        "display_name": deployment.display_name or deployment.name,
        "is_default": bool(deployment.is_default),
        "is_active": bool(deployment.is_active),
        # Non-sensitive model parameter defaults used to pre-fill agent config.
        "default_temperature": settings.get("default_temperature"),
        "default_max_tokens": settings.get("default_max_tokens"),
        "default_top_p": settings.get("default_top_p"),
        "default_reasoning_effort": settings.get("default_reasoning_effort"),
    }


def serialize_deployment_options(
    deployments: list[ModelDeployment],
) -> list[Dict[str, Any]]:
    """Serialize a list of deployments to safe, non-sensitive projections.

    Args:
        deployments: List of ModelDeployment instances

    Returns:
        List of safe deployment option dictionaries
    """
    return [serialize_deployment_option(deployment) for deployment in deployments]


def serialize_deployments(
    deployments: list[ModelDeployment],
    include_credentials: bool = False,
    credential_encryption: Optional[CredentialEncryption] = None,
) -> list[Dict[str, Any]]:
    """Serialize a list of model deployments.

    Args:
        deployments: List of ModelDeployment instances
        include_credentials: Whether to include decrypted credentials
        credential_encryption: Encryption handler (uses default if None)

    Returns:
        List of serialized deployments
    """
    return [
        serialize_deployment(deployment, include_credentials, credential_encryption)
        for deployment in deployments
    ]
