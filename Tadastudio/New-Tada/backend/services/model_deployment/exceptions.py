"""Custom exceptions for model deployment operations."""

from typing import Optional


class ModelDeploymentError(Exception):
    """Base exception for model deployment errors."""

    pass


class DeploymentNotFoundError(ModelDeploymentError):
    """Raised when a model deployment is not found."""

    def __init__(self, deployment_id: str):
        """Initialize deployment not found error."""
        self.deployment_id = deployment_id
        super().__init__(f"Model deployment '{deployment_id}' not found or inactive")


class DuplicateDeploymentNameError(ModelDeploymentError):
    """Raised when attempting to create a deployment with a duplicate name."""

    def __init__(self, name: str):
        """Initialize duplicate deployment name error."""
        self.name = name
        super().__init__(f"Model deployment with name '{name}' already exists")


class DefaultModelConflictError(ModelDeploymentError):
    """Raised when marking a deployment as default would conflict with an
    existing default deployment of the same model type.

    Only one deployment per model type (e.g. ``llm`` or ``embedding``) may be
    marked as default at any given time, regardless of provider. Callers must
    unset the existing default before selecting a new one.
    """

    def __init__(self, model_type: str, existing_name: Optional[str] = None):
        """Initialize default model conflict error.

        Args:
            model_type: The model type ('llm' or 'embedding') with a conflict
            existing_name: Name of the deployment currently marked as default
        """
        self.model_type = model_type
        self.existing_name = existing_name
        message = (
            "Only one model can be set as default for each model type. "
            "Please unset the existing default model before selecting a new one."
        )
        if existing_name:
            message = (
                f"'{existing_name}' is already set as the default {model_type} model. "
                "Only one model can be set as default for each model type. "
                "Please unset the existing default model before selecting a new one."
            )
        super().__init__(message)


class InvalidCredentialError(ModelDeploymentError):
    """Raised when credential validation fails."""

    def __init__(self, message: str):
        """Initialize invalid credential error."""
        super().__init__(f"Invalid credential: {message}")


class InvalidSettingsError(ModelDeploymentError):
    """Raised when settings validation fails."""

    def __init__(self, message: str):
        """Initialize invalid settings error."""
        super().__init__(f"Invalid settings: {message}")


class EncryptionError(ModelDeploymentError):
    """Raised when encryption/decryption operations fail."""

    def __init__(self, key: str, operation: str, original_error: Exception):
        """Initialize encryption error."""
        self.key = key
        self.operation = operation
        self.original_error = original_error
        super().__init__(
            f"Failed to {operation} credential '{key}': {str(original_error)}"
        )
