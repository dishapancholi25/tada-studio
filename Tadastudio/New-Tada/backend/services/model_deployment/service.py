"""Service layer for managing LLM model deployments.

This module provides CRUD operations and runtime configuration
enrichment for persisted model deployments.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.services.database import get_db
from ...models import ModelDeployment
from .encryption import CredentialEncryption
from .enrichment import ConfigEnricher
from .exceptions import DefaultModelConflictError
from .serializers import (
    serialize_deployment,
    serialize_deployment_options,
    serialize_deployments,
)
from .validators import (
    normalize_settings,
    validate_credentials_or_managed_identity,
    validate_deployment_create_payload,
    validate_model_type,
    validate_provider_string,
    validate_unique_name,
)

if TYPE_CHECKING:
    from backend.models.workflow.configs.llm import LLMConfig

logger = logging.getLogger(__name__)


class ModelDeploymentService:
    """Encapsulates persistence and runtime enrichment for model deployments."""

    def __init__(
        self,
        credential_encryption: CredentialEncryption | None = None,
        config_enricher: ConfigEnricher | None = None,
    ):
        """Initialize model deployment service.

        Args:
            credential_encryption: Encryption handler (uses default if None)
            config_enricher: Config enricher (uses default if None)
        """
        self.credential_encryption = credential_encryption or CredentialEncryption()
        self.config_enricher = config_enricher or ConfigEnricher(
            self.credential_encryption
        )

    # ----- Public CRUD operations ---------------------------------------------

    def list_deployments(
        self, include_credentials: bool = False, model_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all active model deployments.

        Args:
            include_credentials: Whether to include decrypted credentials
            model_type: Optional filter by model type ('llm' or 'embedding')

        Returns:
            List of serialized deployments
        """
        logger.debug(
            "[MODEL-DEPLOYMENT] Listing active deployments (model_type=%s)", model_type
        )
        with get_db() as db:
            query = db.query(ModelDeployment).filter(
                ModelDeployment.is_active.is_(True)
            )

            # Filter by model_type if specified
            if model_type:
                validated_type = validate_model_type(model_type)
                query = query.filter(ModelDeployment.model_type == validated_type)

            deployments = query.order_by(ModelDeployment.name.asc()).all()

            logger.info(
                "[MODEL-DEPLOYMENT] Found %d active deployments", len(deployments)
            )
            return serialize_deployments(
                deployments, include_credentials, self.credential_encryption
            )

    def list_deployment_options(
        self, model_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List active deployments as safe, non-sensitive selection options.

        Returns a projection suitable for non-admin consumers (e.g. workflow
        builder model dropdowns). Credentials, settings, and other sensitive
        deployment configuration are never included.

        Args:
            model_type: Optional filter by model type ('llm' or 'embedding')

        Returns:
            List of safe deployment option dictionaries
        """
        logger.debug(
            "[MODEL-DEPLOYMENT] Listing deployment options (model_type=%s)",
            model_type,
        )
        with get_db() as db:
            query = db.query(ModelDeployment).filter(
                ModelDeployment.is_active.is_(True)
            )

            if model_type:
                validated_type = validate_model_type(model_type)
                query = query.filter(ModelDeployment.model_type == validated_type)

            deployments = query.order_by(ModelDeployment.name.asc()).all()
            logger.info(
                "[MODEL-DEPLOYMENT] Found %d deployment options", len(deployments)
            )
            return serialize_deployment_options(deployments)

    def get_deployment(
        self, deployment_id: str, include_credentials: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a single model deployment by ID.

        Args:
            deployment_id: Deployment ID to retrieve
            include_credentials: Whether to include decrypted credentials

        Returns:
            Serialized deployment or None if not found
        """
        logger.debug("[MODEL-DEPLOYMENT] Getting deployment %s", deployment_id)
        with get_db() as db:
            deployment = self._get_by_id(db, deployment_id)
            if not deployment:
                logger.warning(
                    "[MODEL-DEPLOYMENT] Deployment %s not found", deployment_id
                )
                return None
            return serialize_deployment(
                deployment, include_credentials, self.credential_encryption
            )

    def create_deployment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new model deployment.

        Args:
            payload: Deployment creation data

        Returns:
            Serialized created deployment

        Raises:
            DuplicateDeploymentNameError: If name already exists
            InvalidSettingsError: If validation fails
            InvalidCredentialError: If credential validation fails
            EncryptionError: If encryption fails
        """
        # Validate payload
        validate_deployment_create_payload(payload)

        # Normalize and validate fields
        provider = validate_provider_string(payload["provider"])
        model_type = validate_model_type(payload.get("model_type", "llm"))
        settings = normalize_settings(payload.get("settings"))

        # Enhanced logging with managed identity flag
        use_managed_identity = settings.get("use_managed_identity", False)
        logger.info(
            "[MODEL-DEPLOYMENT] Creating deployment '%s' (provider: %s, model_type: %s, use_managed_identity: %s)",
            payload.get("name"),
            provider,
            model_type,
            use_managed_identity,
        )

        with get_db() as db:
            # Validate unique name
            validate_unique_name(db, payload["name"])

            # Encrypt credentials
            encrypted_credentials = self.credential_encryption.encrypt_credentials(
                payload.get("credentials")
            )

            # Validate credentials or managed identity
            validate_credentials_or_managed_identity(
                provider, encrypted_credentials, settings
            )

            # Create deployment
            deployment = ModelDeployment(
                name=payload["name"].strip(),
                description=payload.get("description"),
                provider=provider,
                model_name=payload["model_name"].strip(),
                model_type=model_type,
                display_name=(payload.get("display_name") or payload["name"]).strip(),
                settings=settings,
                encrypted_credentials=encrypted_credentials,
                is_default=bool(payload.get("is_default", False)),
                is_active=True,
                input_cost_per_million=payload.get("input_cost_per_million"),
                output_cost_per_million=payload.get("output_cost_per_million"),
            )

            # Only one deployment per model type may be default. Reject rather
            # than silently overriding an existing default of the same type.
            if deployment.is_default:
                self._assert_no_default_conflict(db, deployment.model_type)

            db.add(deployment)
            db.commit()
            db.refresh(deployment)

            logger.info(
                "[MODEL-DEPLOYMENT] Created deployment %s (%s)",
                deployment.id,
                deployment.provider,
            )
            return serialize_deployment(
                deployment,
                include_credentials=False,
                credential_encryption=self.credential_encryption,
            )

    def update_deployment(
        self, deployment_id: str, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an existing model deployment.

        Args:
            deployment_id: Deployment ID to update
            payload: Update data (only provided fields are updated)

        Returns:
            Serialized updated deployment or None if not found

        Raises:
            DuplicateDeploymentNameError: If name change conflicts
            InvalidSettingsError: If validation fails
            InvalidCredentialError: If credential validation fails
            EncryptionError: If encryption fails
        """
        if not payload:
            logger.debug("[MODEL-DEPLOYMENT] Empty update payload, returning current")
            return self.get_deployment(deployment_id)

        logger.info("[MODEL-DEPLOYMENT] Updating deployment %s", deployment_id)

        with get_db() as db:
            deployment = self._get_by_id(db, deployment_id)
            if not deployment:
                logger.warning(
                    "[MODEL-DEPLOYMENT] Deployment %s not found for update",
                    deployment_id,
                )
                return None

            # Apply updates using helper methods
            self._update_name(db, deployment, payload)
            self._update_display_name(deployment, payload)
            self._update_description(deployment, payload)
            self._update_provider(deployment, payload)
            self._update_model_name(deployment, payload)
            self._update_model_type(deployment, payload)
            self._update_settings(deployment, payload)
            self._update_credentials(deployment, payload)
            self._update_pricing(deployment, payload)
            self._update_default_flag(db, deployment, payload)
            self._update_active_flag(deployment, payload)

            db.commit()
            db.refresh(deployment)

            logger.info("[MODEL-DEPLOYMENT] Updated deployment %s", deployment.id)
            return serialize_deployment(
                deployment,
                include_credentials=False,
                credential_encryption=self.credential_encryption,
            )

    def delete_deployment(self, deployment_id: str, hard_delete: bool = False) -> bool:
        """Delete a model deployment (soft or hard delete).

        Args:
            deployment_id: Deployment ID to delete
            hard_delete: If True, permanently delete; if False, mark as inactive

        Returns:
            True if deleted, False if not found
        """
        logger.info(
            "[MODEL-DEPLOYMENT] Deleting deployment %s (hard=%s)",
            deployment_id,
            hard_delete,
        )

        with get_db() as db:
            deployment = self._get_by_id(db, deployment_id)
            if not deployment:
                logger.warning(
                    "[MODEL-DEPLOYMENT] Deployment %s not found for deletion",
                    deployment_id,
                )
                return False

            if hard_delete:
                db.delete(deployment)
            else:
                deployment.is_active = False
                deployment.is_default = False

            db.commit()
            logger.info(
                "[MODEL-DEPLOYMENT] Deleted deployment %s (hard=%s)",
                deployment_id,
                hard_delete,
            )
            return True

    # ----- Runtime helpers ----------------------------------------------------

    def enrich_llm_config(self, llm_config: LLMConfig) -> LLMConfig:
        """Attach provider settings and decrypted credentials to LLM config.

        Args:
            llm_config: Base LLM configuration

        Returns:
            Enriched LLM configuration (deepcopy to avoid side effects)

        Raises:
            exceptions.DeploymentNotFoundError: If deployment not found or inactive
        """
        with get_db() as db:
            return self.config_enricher.enrich_llm_config(db, llm_config)

    def get_default_deployment(
        self, model_type: str = "llm", include_credentials: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get the default model deployment for a specific model type.

        Resolution order for embeddings (first match wins):
          1. Deployment explicitly marked ``is_default=True`` in the DB.
          2. Active embedding deployment whose ``model_name`` matches the
             ``KEY_OPENAI_API_EMBEDDING_MODEL`` environment variable — bridges
             env-var-only setups to a registered DB record.
          3. The first active embedding deployment in the DB.

        For non-embedding model types only step 1 is attempted.

        Args:
            model_type: Type of model ('llm' or 'embedding')
            include_credentials: Whether to include decrypted credentials

        Returns:
            Serialized deployment or None if no suitable deployment is found
        """
        validated_type = validate_model_type(model_type)
        logger.debug(
            "[MODEL-DEPLOYMENT] Getting default deployment for model_type=%s",
            validated_type,
        )

        with get_db() as db:
            # 1. Explicitly marked default
            deployment = (
                db.query(ModelDeployment)
                .filter(
                    ModelDeployment.is_active.is_(True),
                    ModelDeployment.is_default.is_(True),
                    ModelDeployment.model_type == validated_type,
                )
                .first()
            )

            # 2 & 3. Env-var fallback (embeddings only)
            if not deployment and validated_type == "embedding":
                deployment = self._find_env_var_embedding_deployment(db)

            if not deployment:
                logger.debug(
                    "[MODEL-DEPLOYMENT] No default deployment found for model_type=%s",
                    validated_type,
                )
                return None

            logger.info(
                "[MODEL-DEPLOYMENT] Resolved default deployment %s (%s) for model_type=%s",
                deployment.id,
                deployment.name,
                validated_type,
            )
            return serialize_deployment(
                deployment, include_credentials, self.credential_encryption
            )

    @staticmethod
    def _find_env_var_embedding_deployment(db: Session) -> Optional[ModelDeployment]:
        """Find the active embedding deployment that best matches env var config.

        Tries to match ``KEY_OPENAI_API_EMBEDDING_MODEL`` against
        ``model_name`` of active embedding deployments, then falls back to
        returning the first active embedding deployment in the DB.

        Args:
            db: Active database session

        Returns:
            Matching ModelDeployment or None if no embedding deployments exist
        """
        active_embeddings = db.query(ModelDeployment).filter(
            ModelDeployment.is_active.is_(True),
            ModelDeployment.model_type == "embedding",
        )

        env_name = os.getenv("KEY_OPENAI_API_EMBEDDING_MODEL")
        if env_name:
            match = active_embeddings.filter(
                ModelDeployment.model_name == env_name
            ).first()
            if match:
                logger.debug(
                    "[MODEL-DEPLOYMENT] Env-var embedding '%s' matched deployment %s (%s)",
                    env_name,
                    match.id,
                    match.name,
                )
                return match

        # Final fallback: any active embedding deployment
        fallback = active_embeddings.first()
        if fallback:
            logger.debug(
                "[MODEL-DEPLOYMENT] Using first active embedding deployment %s (%s) as default",
                fallback.id,
                fallback.name,
            )
        return fallback

    # ----- Internal helper methods --------------------------------------------

    @staticmethod
    def _get_by_id(db: Session, deployment_id: str) -> Optional[ModelDeployment]:
        """Retrieve deployment by ID."""
        if not deployment_id:
            return None
        return (
            db.query(ModelDeployment)
            .filter(ModelDeployment.id == deployment_id)
            .first()
        )

    @staticmethod
    def _get_default_deployment_of_type(
        db: Session,
        model_type: Optional[str],
        exclude_id: Optional[str] = None,
    ) -> Optional[ModelDeployment]:
        """Fetch the active deployment currently marked default for a model type.

        Args:
            db: Database session
            model_type: Model type to filter by ('llm' or 'embedding')
            exclude_id: Deployment ID to exclude from the lookup (optional)

        Returns:
            The conflicting default deployment, or ``None`` if none exists.
        """
        query = db.query(ModelDeployment).filter(
            ModelDeployment.is_default.is_(True),
            ModelDeployment.is_active.is_(True),
        )
        if model_type:
            query = query.filter(ModelDeployment.model_type == model_type)
        if exclude_id:
            query = query.filter(ModelDeployment.id != exclude_id)
        return query.first()

    @classmethod
    def _assert_no_default_conflict(
        cls,
        db: Session,
        model_type: Optional[str],
        exclude_id: Optional[str] = None,
    ) -> None:
        """Ensure no other deployment of the same model type is already default.

        Only one deployment per model type (independent of provider) may be
        marked as default at any given time. Rather than silently clearing
        the previous default, this raises ``DefaultModelConflictError`` so
        the caller (API/UI) can surface a confirmation/warning prompt asking
        the user to unset the existing default first.

        Args:
            db: Database session
            model_type: Model type of the deployment being marked default
            exclude_id: Deployment ID to exclude from the conflict check
                (used on update, where the deployment itself may already be
                default)

        Raises:
            DefaultModelConflictError: If another deployment of the same
                model type is already marked as default.
        """
        existing = cls._get_default_deployment_of_type(
            db, model_type, exclude_id=exclude_id
        )
        if existing is not None:
            raise DefaultModelConflictError(
                model_type=model_type or "llm", existing_name=existing.name
            )

    @staticmethod
    def _clear_default(
        db: Session,
        provider: Optional[str],
        model_type: Optional[str] = None,
        exclude_id: Optional[str] = None,
    ) -> None:
        """Clear default flag from deployments.

        Args:
            db: Database session
            provider: Provider to filter by (optional)
            model_type: Model type to filter by (optional)
            exclude_id: Deployment ID to exclude from clearing (optional)
        """
        query = db.query(ModelDeployment).filter(ModelDeployment.is_default.is_(True))
        if provider:
            query = query.filter(ModelDeployment.provider == provider)
        if model_type:
            query = query.filter(ModelDeployment.model_type == model_type)
        if exclude_id:
            query = query.filter(ModelDeployment.id != exclude_id)

        for row in query.all():
            row.is_default = False

    def _update_name(
        self, db: Session, deployment: ModelDeployment, payload: Dict[str, Any]
    ) -> None:
        """Update deployment name if provided."""
        if (
            "name" in payload
            and payload["name"]
            and payload["name"].strip() != deployment.name
        ):
            validate_unique_name(db, payload["name"].strip(), exclude_id=deployment.id)
            deployment.name = payload["name"].strip()

    @staticmethod
    def _update_display_name(
        deployment: ModelDeployment, payload: Dict[str, Any]
    ) -> None:
        """Update display name if provided."""
        if "display_name" in payload and payload["display_name"] is not None:
            deployment.display_name = (
                payload["display_name"].strip()
                if payload["display_name"].strip()
                else None
            )

    @staticmethod
    def _update_description(
        deployment: ModelDeployment, payload: Dict[str, Any]
    ) -> None:
        """Update description if provided."""
        if "description" in payload:
            deployment.description = payload["description"]

    @staticmethod
    def _update_provider(deployment: ModelDeployment, payload: Dict[str, Any]) -> None:
        """Update provider if provided."""
        if "provider" in payload and payload["provider"]:
            deployment.provider = validate_provider_string(payload["provider"])

    @staticmethod
    def _update_model_name(
        deployment: ModelDeployment, payload: Dict[str, Any]
    ) -> None:
        """Update model name if provided."""
        if "model_name" in payload and payload["model_name"]:
            deployment.model_name = payload["model_name"].strip()

    @staticmethod
    def _update_model_type(
        deployment: ModelDeployment, payload: Dict[str, Any]
    ) -> None:
        """Update model type if provided."""
        if "model_type" in payload and payload["model_type"]:
            deployment.model_type = validate_model_type(payload["model_type"])

    @staticmethod
    def _update_settings(deployment: ModelDeployment, payload: Dict[str, Any]) -> None:
        """Update settings if provided."""
        if "settings" in payload:
            deployment.settings = normalize_settings(payload.get("settings"))

    def _update_credentials(
        self, deployment: ModelDeployment, payload: Dict[str, Any]
    ) -> None:
        """Update credentials if provided."""
        if "credentials" in payload:
            updated_credentials = self.credential_encryption.merge_credentials(
                deployment.encrypted_credentials or {},
                payload["credentials"],
            )
            deployment.encrypted_credentials = updated_credentials or None

    def _update_default_flag(
        self, db: Session, deployment: ModelDeployment, payload: Dict[str, Any]
    ) -> None:
        """Update default flag if provided.

        Only one deployment per model type may be marked as default. If the
        deployment is being switched to default while another active
        deployment of the same model type already holds the default flag,
        the update is rejected with ``DefaultModelConflictError`` instead of
        silently clearing the existing default.
        """
        if "is_default" in payload:
            is_default = bool(payload["is_default"])
            if is_default and not deployment.is_default:
                self._assert_no_default_conflict(
                    db, deployment.model_type, exclude_id=deployment.id
                )
            deployment.is_default = is_default

    @staticmethod
    def _update_pricing(deployment: ModelDeployment, payload: Dict[str, Any]) -> None:
        """Update token pricing fields if provided."""
        if "input_cost_per_million" in payload:
            deployment.input_cost_per_million = payload["input_cost_per_million"]
        if "output_cost_per_million" in payload:
            deployment.output_cost_per_million = payload["output_cost_per_million"]

    @staticmethod
    def _update_active_flag(
        deployment: ModelDeployment, payload: Dict[str, Any]
    ) -> None:
        """Update active flag if provided."""
        if "is_active" in payload:
            deployment.is_active = bool(payload["is_active"])
