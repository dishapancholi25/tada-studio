"""Runtime configuration enrichment for LLM configs.

This module handles enriching LLM configurations with deployment-specific
settings and credentials at runtime.
"""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from ...models import ModelDeployment
from .encryption import CredentialEncryption
from .exceptions import DeploymentNotFoundError

if TYPE_CHECKING:
    from backend.models.workflow.configs.llm import LLMConfig

logger = logging.getLogger(__name__)


class ConfigEnricher:
    """Handles enrichment of LLM configs with deployment data."""

    def __init__(self, credential_encryption: CredentialEncryption | None = None):
        """Initialize config enricher.

        Args:
            credential_encryption: Encryption handler (uses default if None)
        """
        self.credential_encryption = credential_encryption or CredentialEncryption()

    def enrich_llm_config(self, db: Session, llm_config: LLMConfig) -> LLMConfig:
        """Attach provider settings and decrypted credentials to LLM config.

        Args:
            db: Database session
            llm_config: Base LLM configuration

        Returns:
            Enriched LLM configuration (deepcopy to avoid side effects)

        Raises:
            DeploymentNotFoundError: If deployment not found or inactive

        Note:
            Returns original config if no model_deployment_id is specified.
        """
        if not llm_config or not llm_config.model_deployment_id:
            logger.debug(
                "[MODEL-DEPLOYMENT] No deployment ID in config, skipping enrichment"
            )
            return llm_config

        deployment = self._get_deployment(db, llm_config.model_deployment_id)
        if not deployment or not deployment.is_active:
            raise DeploymentNotFoundError(llm_config.model_deployment_id)

        logger.info(
            "[MODEL-DEPLOYMENT] Enriching config with deployment %s (%s)",
            deployment.id,
            deployment.name,
        )

        # Create deep copy to avoid side effects
        enriched = copy.deepcopy(llm_config)

        # Apply deployment settings
        enriched.provider = deployment.provider
        enriched.model_name = deployment.model_name
        enriched.model_type = (
            deployment.model_type or "llm"
        )  # Default to 'llm' for backward compatibility
        enriched.display_name = deployment.display_name or deployment.name

        # Decrypt and attach credentials
        enriched.credentials = self.credential_encryption.decrypt_credentials(
            deployment.encrypted_credentials or {}
        )

        # Merge settings (runtime config overrides deployment settings)
        deployment_settings = deployment.settings or {}
        runtime_config = enriched.config or {}
        enriched.config = {**deployment_settings, **runtime_config}

        # Apply deployment-level model parameter defaults when the
        # agent config hasn't set an explicit override.
        self._apply_model_param_defaults(enriched, deployment)

        # Fill legacy fields for backwards compatibility
        self._fill_legacy_fields(enriched, deployment)

        logger.debug(
            "[MODEL-DEPLOYMENT] Config enriched: provider=%s, model=%s, "
            "temperature=%s, max_tokens=%s, top_p=%s, reasoning_effort=%s, "
            "deployment_name=%s, api_version=%s",
            enriched.provider,
            enriched.model_name,
            enriched.temperature,
            enriched.max_tokens,
            enriched.top_p,
            enriched.reasoning_effort,
            enriched.deployment_name,
            enriched.api_version,
        )

        return enriched

    @staticmethod
    def _get_deployment(db: Session, deployment_id: str) -> ModelDeployment | None:
        """Retrieve deployment by ID.

        Args:
            db: Database session
            deployment_id: Deployment ID to retrieve

        Returns:
            ModelDeployment instance or None if not found
        """
        if not deployment_id:
            return None
        return (
            db.query(ModelDeployment)
            .filter(ModelDeployment.id == deployment_id)
            .first()
        )

    @staticmethod
    def _apply_model_param_defaults(
        enriched: LLMConfig, deployment: ModelDeployment
    ) -> None:
        """Apply deployment-level model parameter defaults.

        Deployment settings can contain ``default_temperature``,
        ``default_max_tokens``, ``default_top_p``, and
        ``default_reasoning_effort``.  These act as fallbacks — agent-level
        values take precedence when explicitly set.
        """
        settings = deployment.settings or {}

        # Temperature: apply deployment default only when agent value is the
        # dataclass default (0.0) — meaning the agent never chose a value.
        default_temp = settings.get("default_temperature")
        if default_temp is not None and enriched.temperature == 0.0:
            enriched.temperature = float(default_temp)

        # Max tokens: apply when agent hasn't set one
        default_max = settings.get("default_max_tokens")
        if default_max is not None and enriched.max_tokens is None:
            enriched.max_tokens = int(default_max)

        # Top-p: apply when agent hasn't set one
        default_top_p = settings.get("default_top_p")
        if default_top_p is not None and enriched.top_p is None:
            enriched.top_p = float(default_top_p)

        # Reasoning effort: apply when agent hasn't set one
        default_reasoning = settings.get("default_reasoning_effort")
        if default_reasoning is not None and enriched.reasoning_effort is None:
            enriched.reasoning_effort = str(default_reasoning)

    @staticmethod
    def _fill_legacy_fields(enriched: LLMConfig, deployment: ModelDeployment) -> None:
        """Fill legacy fields for backward compatibility.

        Args:
            enriched: LLM config to update (modified in place)
            deployment: Deployment with settings to use
        """
        merged_settings = enriched.config or {}

        # deployment_name fallback
        if not enriched.deployment_name:
            enriched.deployment_name = merged_settings.get(
                "deployment_name", deployment.model_name
            )

        # api_version fallback
        if not enriched.api_version:
            enriched.api_version = merged_settings.get("api_version")

        # api_base fallback (check both api_base and base_url)
        if not enriched.api_base:
            enriched.api_base = merged_settings.get("api_base") or merged_settings.get(
                "base_url"
            )
