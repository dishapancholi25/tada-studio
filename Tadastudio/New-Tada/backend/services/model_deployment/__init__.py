"""Model deployment service module.

This module provides comprehensive model deployment management including:
- CRUD operations for LLM deployments
- Runtime configuration enrichment
- Credential encryption and security
- Validation and serialization

The module follows clean architecture with separation between:
- Service: Main business logic and CRUD operations
- Enrichment: Runtime configuration enrichment
- Encryption: Credential security
- Validators: Input validation
- Serializers: Data formatting and masking
- Exceptions: Custom error types

Example usage:
    from backend.services.model_deployment import ModelDeploymentService

    service = ModelDeploymentService()
    deployments = service.list_deployments()
    enriched_config = service.enrich_llm_config(llm_config)
"""

from .encryption import CredentialEncryption
from .enrichment import ConfigEnricher
from .exceptions import (
    DefaultModelConflictError,
    DeploymentNotFoundError,
    DuplicateDeploymentNameError,
    EncryptionError,
    InvalidCredentialError,
    InvalidSettingsError,
    ModelDeploymentError,
)
from .service import ModelDeploymentService


__all__ = [
    "ModelDeploymentService",
    "ConfigEnricher",
    "CredentialEncryption",
    "ModelDeploymentError",
    "DeploymentNotFoundError",
    "DuplicateDeploymentNameError",
    "DefaultModelConflictError",
    "InvalidCredentialError",
    "InvalidSettingsError",
    "EncryptionError",
]
