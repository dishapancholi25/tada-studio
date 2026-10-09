"""Configuration management service for handling environment settings."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import psycopg2
from dotenv import dotenv_values, load_dotenv, set_key
from sqlalchemy import text

from .encryption_utils import CredentialEncryption
from backend.models.workflow import LLMConfig
from .services.configuration.system_external_service_service import (
    SystemExternalServiceService,
)
from .services.database.session import get_db
from .services.document_storage.config import EMBEDDING_DIMENSIONS
from .services.llm_models import LLMFactory


logger = logging.getLogger(__name__)


class ConfigurationService:
    """Service for managing application configuration."""

    def __init__(self):
        """Initialize the configuration service."""
        self.env_file = Path(".env")
        self.encryption = CredentialEncryption()
        self.llm_factory = LLMFactory()
        load_dotenv()

    def get_environment_config(self, sanitize: bool = True) -> Dict[str, Any]:
        """
        Get current environment configuration.

        Args:
            sanitize: If True, mask sensitive values

        Returns:
            Dictionary of configuration values
        """
        config = {
            "llm_providers": self._get_llm_config(sanitize),
            "database": self._get_database_config(sanitize),
            "external_services": self._get_external_services_config(sanitize),
            "mcp": self._get_mcp_config(sanitize),
            "security": self._get_security_config(sanitize),
            "system": self._get_system_config(),
        }
        return config

    def _get_llm_config(self, sanitize: bool = True) -> Dict[str, Any]:
        """Get LLM provider configuration."""
        return {
            "azure_openai": {
                "enabled": bool(os.getenv("AZURE_OPENAI_API_KEY")),
                "api_key": self._sanitize_value(
                    os.getenv("AZURE_OPENAI_API_KEY"), sanitize
                ),
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
                "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", ""),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
                "status": "connected"
                if os.getenv("AZURE_OPENAI_API_KEY")
                else "not_configured",
            },
            "openai": {
                "enabled": bool(os.getenv("OPENAI_API_KEY")),
                "api_key": self._sanitize_value(os.getenv("OPENAI_API_KEY"), sanitize),
                "base_url": os.getenv("OPENAI_BASE", "https://api.openai.com/v1"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                "status": "connected"
                if os.getenv("OPENAI_API_KEY")
                else "not_configured",
            },
            "anthropic": {
                "enabled": bool(os.getenv("ANTHROPIC_API_KEY")),
                "api_key": self._sanitize_value(
                    os.getenv("ANTHROPIC_API_KEY"), sanitize
                ),
                "model": os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                "status": "connected"
                if os.getenv("ANTHROPIC_API_KEY")
                else "not_configured",
            },
            "google_gemini": {
                "enabled": False,
                "status": "coming_soon",
                "api_key": "",
                "model": "gemini-pro",
            },
            "mistral": {
                "enabled": False,
                "status": "coming_soon",
                "api_key": "",
                "model": "mistral-large",
            },
            "cohere": {
                "enabled": False,
                "status": "coming_soon",
                "api_key": "",
                "model": "command-r",
            },
        }

    def _get_database_config(self, sanitize: bool = True) -> Dict[str, Any]:
        """Get database configuration."""
        return {
            "postgresql": {
                "host": os.getenv("KEY_POSTGRES_HOST", "localhost"),
                "port": os.getenv("KEY_POSTGRES_PORT", "5432"),
                "database": os.getenv("KEY_POSTGRES_DBNAME", "langgraph"),
                "username": os.getenv("KEY_POSTGRES_USER", "postgres"),
                "password": self._sanitize_value(
                    os.getenv("KEY_POSTGRES_PASSWORD"), sanitize
                ),
                "sslmode": os.getenv("KEY_POSTGRES_SSLMODE", "prefer"),
                "status": "unknown",
                "pool_size": 10,
                "max_overflow": 20,
            },
            "pgvector": {
                "enabled": True,
                "dimensions": EMBEDDING_DIMENSIONS,
                "index_type": "ivfflat",
            },
            "future_databases": {
                "mongodb": {"status": "coming_soon"},
                "redis": {"status": "coming_soon"},
                "pinecone": {"status": "coming_soon"},
            },
        }

    def _get_mcp_config(self, sanitize: bool = True) -> Dict[str, Any]:
        """Get MCP-related configuration (secrets, etc.)."""
        secrets = []
        try:
            env_values = dotenv_values(self.env_file) if self.env_file.exists() else {}
        except Exception:
            env_values = {}

        for env_key, value in (env_values or {}).items():
            if env_key.startswith("MCP_SECRET_"):
                secret_name = env_key[len("MCP_SECRET_") :]
                secrets.append(
                    {
                        "name": secret_name,
                        "id": secret_name.lower(),
                        "env_key": env_key,
                        "value": self._sanitize_value(value, sanitize),
                    }
                )

        secrets.sort(key=lambda item: item["name"])
        return {"secrets": secrets}

    def _get_external_services_config(self, sanitize: bool = True) -> Dict[str, Any]:
        """Get external services configuration.

        Provider selection and non-credential settings are read from the
        system_settings table (key-value store).  External service credentials
        and URLs (Tika, Azure Document Intelligence) are read from the
        system_external_services table where they are stored encrypted.
        Both fall back to environment variables when no DB record exists.
        """
        doc_extraction_provider = self._get_db_setting(
            "DOCUMENT_EXTRACTION_PROVIDER",
            os.getenv("DOCUMENT_EXTRACTION_PROVIDER", "model_ocr"),
        )
        model_ocr_deployment_id = self._get_db_setting(
            "DOCUMENT_EXTRACTION_MODEL_DEPLOYMENT_ID",
            os.getenv("DOCUMENT_EXTRACTION_MODEL_DEPLOYMENT_ID", ""),
        )

        # --- Tika: read URL from system_external_services, fall back to env ---
        tika_url = os.getenv("TIKA_SERVER_URL", "")
        tika_timeout = int(os.getenv("TIKA_TIMEOUT_SECONDS", "60"))
        tika_svc = SystemExternalServiceService.get_service("tika")
        if tika_svc:
            tika_url = tika_svc.service_url or tika_url
            tika_timeout = int(
                (tika_svc.settings or {}).get("timeout_seconds", tika_timeout)
            )

        # --- Azure Document Intelligence: read from system_external_services ---
        azure_di_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
        azure_di_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")
        azure_di_managed_identity = (
            os.getenv("AZURE_DOCUMENT_INTELLIGENCE_MANAGED_IDENTITY", "false").lower()
            == "true"
        )
        azure_di_model_id = os.getenv("AZURE_DI_MODEL_ID", "prebuilt-read")
        azure_di_svc = SystemExternalServiceService.get_service(
            "azure_document_intelligence"
        )
        if azure_di_svc:
            azure_di_endpoint = azure_di_svc.service_url or azure_di_endpoint
            azure_di_managed_identity = bool(
                (azure_di_svc.settings or {}).get(
                    "use_managed_identity", azure_di_managed_identity
                )
            )
            azure_di_model_id = (azure_di_svc.settings or {}).get(
                "model_id", azure_di_model_id
            )
            # Credentials are stored encrypted — decrypt only to check configuration status
            azure_di_creds = SystemExternalServiceService.get_decrypted_credentials(
                "azure_document_intelligence"
            )
            if azure_di_creds:
                azure_di_key = azure_di_creds.get("api_key", azure_di_key)

        # --- Model OCR detail level ---
        model_ocr_detail = self._get_db_setting(
            "DOCUMENT_EXTRACTION_MODEL_OCR_DETAIL",
            os.getenv("DOCUMENT_EXTRACTION_MODEL_OCR_DETAIL", "high"),
        )

        return {
            "document_extraction": {
                "provider": doc_extraction_provider,
                "model_ocr_deployment_id": model_ocr_deployment_id or "",
                "model_ocr_detail": model_ocr_detail or "high",
                "tika": {
                    "server_url": tika_url,
                    "timeout_seconds": tika_timeout,
                    "enabled": bool(tika_url),
                    "status": "configured" if tika_url else "not_configured",
                },
                "azure_document_intelligence": {
                    "endpoint": azure_di_endpoint,
                    "api_key": self._sanitize_value(azure_di_key, sanitize),
                    "use_managed_identity": azure_di_managed_identity,
                    "model_id": azure_di_model_id,
                    "enabled": bool(azure_di_endpoint),
                    "status": "configured" if azure_di_endpoint else "not_configured",
                },
            },
            "tavily": {
                "enabled": bool(os.getenv("TAVILY_API_KEY")),
                "api_key": self._sanitize_value(os.getenv("TAVILY_API_KEY"), sanitize),
                "status": "connected"
                if os.getenv("TAVILY_API_KEY")
                else "not_configured",
            },
            "langchain": {
                "enabled": (
                    self._get_db_setting(
                        "LANGCHAIN_TRACING_V2",
                        os.getenv("LANGCHAIN_TRACING_V2", "false"),
                    )
                    or "false"
                ).lower()
                == "true",
                "api_key": self._sanitize_value(
                    self._get_db_setting(
                        "LANGCHAIN_API_KEY", os.getenv("LANGCHAIN_API_KEY")
                    ),
                    sanitize,
                ),
                "tracing_v2": (
                    self._get_db_setting(
                        "LANGCHAIN_TRACING_V2",
                        os.getenv("LANGCHAIN_TRACING_V2", "false"),
                    )
                    or "false"
                ).lower()
                == "true",
                "project": self._get_db_setting(
                    "LANGCHAIN_PROJECT", os.getenv("LANGCHAIN_PROJECT", "default")
                ),
                "status": "connected"
                if self._get_db_setting(
                    "LANGCHAIN_API_KEY", os.getenv("LANGCHAIN_API_KEY")
                )
                else "not_configured",
            },
            "phoenix": {
                "enabled": (
                    self._get_db_setting(
                        "PHOENIX_ENABLED",
                        os.getenv("PHOENIX_ENABLED", "false"),
                    )
                    or "false"
                ).lower()
                == "true",
                "endpoint": self._get_db_setting(
                    "PHOENIX_ENDPOINT", os.getenv("PHOENIX_ENDPOINT")
                ),
                "project_name": self._get_db_setting(
                    "PHOENIX_PROJECT_NAME",
                    os.getenv("PHOENIX_PROJECT_NAME", "agentic-studio"),
                ),
                "api_key": self._sanitize_value(
                    self._get_db_setting(
                        "PHOENIX_API_KEY", os.getenv("PHOENIX_API_KEY")
                    ),
                    sanitize,
                ),
                "ui_url": self._get_db_setting(
                    "PHOENIX_UI_URL", os.getenv("PHOENIX_UI_URL")
                ),
                "eval_penalty_enabled": (
                    self._get_db_setting(
                        "PHOENIX_EVAL_PENALTY_ENABLED",
                        os.getenv("PHOENIX_EVAL_PENALTY_ENABLED", "false"),
                    )
                    or "false"
                ).lower()
                == "true",
                "eval_model_deployment_id": self._get_db_setting(
                    "PHOENIX_EVAL_MODEL_DEPLOYMENT_ID",
                    os.getenv("PHOENIX_EVAL_MODEL_DEPLOYMENT_ID"),
                ),
                "eval_faithfulness_enabled": (
                    self._get_db_setting(
                        "PHOENIX_EVAL_FAITHFULNESS_ENABLED",
                        os.getenv("PHOENIX_EVAL_FAITHFULNESS_ENABLED", "true"),
                    )
                    or "true"
                ).lower()
                != "false",
                "eval_tool_selection_enabled": (
                    self._get_db_setting(
                        "PHOENIX_EVAL_TOOL_SELECTION_ENABLED",
                        os.getenv("PHOENIX_EVAL_TOOL_SELECTION_ENABLED", "true"),
                    )
                    or "true"
                ).lower()
                != "false",
                "eval_llm_judge_enabled": (
                    self._get_db_setting(
                        "PHOENIX_EVAL_LLM_JUDGE_ENABLED",
                        os.getenv("PHOENIX_EVAL_LLM_JUDGE_ENABLED", "false"),
                    )
                    or "false"
                ).lower()
                == "true",
                "status": "connected"
                if self._get_db_setting(
                    "PHOENIX_ENDPOINT", os.getenv("PHOENIX_ENDPOINT")
                )
                else "not_configured",
            },
            "langfuse": {
                "enabled": (
                    self._get_db_setting(
                        "LANGFUSE_ENABLED",
                        os.getenv("LANGFUSE_ENABLED", "false"),
                    )
                    or "false"
                ).lower()
                == "true",
                "host": self._get_db_setting(
                    "LANGFUSE_HOST", os.getenv("LANGFUSE_HOST")
                ),
                "public_key": self._sanitize_value(
                    self._get_db_setting(
                        "LANGFUSE_PUBLIC_KEY", os.getenv("LANGFUSE_PUBLIC_KEY")
                    ),
                    sanitize,
                ),
                "secret_key": self._sanitize_value(
                    self._get_db_setting(
                        "LANGFUSE_SECRET_KEY", os.getenv("LANGFUSE_SECRET_KEY")
                    ),
                    sanitize,
                ),
                "status": "connected"
                if self._get_db_setting(
                    "LANGFUSE_HOST", os.getenv("LANGFUSE_HOST")
                )
                else "not_configured",
            },
            "embeddings": {
                "dimensions": EMBEDDING_DIMENSIONS,
            },
            "future_services": {
                "slack": {"status": "coming_soon", "webhook_url": ""},
                "email": {"status": "coming_soon", "smtp_host": "", "smtp_port": 587},
                "s3": {"status": "coming_soon", "bucket": "", "region": ""},
                "azure_blob": {"status": "coming_soon", "container": "", "account": ""},
                "webhooks": {"status": "coming_soon", "endpoints": []},
            },
        }

    def _get_security_config(self, sanitize: bool = True) -> Dict[str, Any]:
        """Get security configuration."""
        return {
            "encryption": {
                "enabled": bool(os.getenv("CREDENTIAL_ENCRYPTION_KEY")),
                "key": self._sanitize_value(
                    os.getenv("CREDENTIAL_ENCRYPTION_KEY"), sanitize, mask_length=10
                ),
                "algorithm": "Fernet",
            },
            "api_key_rotation": {
                "enabled": False,
                "status": "coming_soon",
                "last_rotation": None,
                "rotation_interval_days": 90,
            },
            "audit_logging": {
                "enabled": False,
                "status": "coming_soon",
                "retention_days": 90,
            },
            "rate_limiting": {
                "enabled": False,
                "status": "coming_soon",
                "requests_per_minute": 100,
            },
        }

    @staticmethod
    def _get_system_config() -> Dict[str, Any]:
        """Get system configuration."""
        # Get default user role with validation
        default_role = os.getenv("DEFAULT_USER_ROLE", "USER").upper()
        valid_roles = ["PENDING", "USER", "ADMIN"]
        if default_role not in valid_roles:
            logger.warning(
                f"Invalid DEFAULT_USER_ROLE '{default_role}', defaulting to 'USER'. "
                f"Valid values: {', '.join(valid_roles)}"
            )
            default_role = "USER"

        return {
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "debug_mode": os.getenv("DEBUG", "false").lower() == "true",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "timezone": os.getenv("TZ", "UTC"),
            "cloud_provider": os.getenv("CLOUD_PROVIDER", "none").lower(),
            "default_user_role": default_role,
            "performance": {
                "enable_caching": True,
                "cache_ttl_seconds": 3600,
                "max_workers": 4,
            },
        }

    @staticmethod
    def _sanitize_value(
        value: Optional[str], sanitize: bool = True, mask_length: int = 4
    ) -> Optional[str]:
        """
        Sanitize sensitive values.

        Args:
            value: Value to sanitize
            sanitize: If True, mask the value
            mask_length: Number of characters to show at the end

        Returns:
            Sanitized value or original if not sanitizing
        """
        if not value or not sanitize:
            return value

        if len(value) <= mask_length:
            return "****"

        return f"****...{value[-mask_length:]}"

    def _get_db_setting(
        self, env_key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Read a setting from the system_settings table (cross-pod persistent).

        Falls back to the provided default if the key is not in the database.
        """
        try:
            with get_db() as db:
                result = db.execute(
                    text("SELECT value FROM system_settings WHERE key = :key"),
                    {"key": env_key},
                )
                row = result.fetchone()
                if row is not None:
                    return str(row[0])  # type: ignore[index]
        except Exception as e:
            logger.debug("Could not read system_settings for %s: %s", env_key, e)
        return default

    def _set_db_setting(self, env_key: str, value: str) -> None:
        """Write a setting to the system_settings table (cross-pod persistent).

        Uses an upsert so subsequent saves overwrite the previous value.
        """
        try:
            with get_db() as db:
                db.execute(
                    text("""
                        INSERT INTO system_settings (key, value, updated_at)
                        VALUES (:key, :value, NOW())
                        ON CONFLICT (key) DO UPDATE
                            SET value = EXCLUDED.value,
                                updated_at = NOW()
                    """),
                    {"key": env_key, "value": value},
                )
        except Exception as e:
            logger.error("Could not write system_settings for %s: %s", env_key, e)

    def update_configuration(self, section: str, key: str, value: Any) -> bool:
        """
        Update a configuration value.

        Persists to the shared PostgreSQL system_settings table (read by all pods)
        and also updates the current process environment for the remainder of this
        pod's lifetime.

        Args:
            section: Configuration section
            key: Configuration key
            value: New value

        Returns:
            True if successful, False otherwise
        """
        try:
            env_key = self._get_env_key(section, key)
            if env_key:
                str_value = str(value)
                # Primary persistence: shared DB (survives pod restarts, visible to all replicas)
                self._set_db_setting(env_key, str_value)
                # Secondary: update current pod's env and .env file (local dev / same-pod reads)
                set_key(self.env_file, env_key, str_value)
                os.environ[env_key] = str_value
                logger.info(f"Updated configuration: {env_key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False

    def sync_db_settings_to_env(self) -> None:
        """Load persisted settings into os.environ on startup.

        1. Loads all rows from system_settings into os.environ so that code
           reading os.getenv() (e.g. get_extraction_provider()) picks up
           DB-persisted values without per-call-site changes.

        2. Loads Azure Document Intelligence and Tika credentials from
           system_external_services (decrypted) so that the extraction service
           constructors that read os.getenv() continue to work.
        """
        # 1. system_settings → os.environ
        try:
            with get_db() as db:
                result = db.execute(text("SELECT key, value FROM system_settings"))
                rows = result.fetchall()
                count = 0
                for row in rows:
                    env_key, value = str(row[0]), str(row[1])  # type: ignore[index]
                    if value.strip():
                        os.environ[env_key] = value
                        count += 1
                logger.info("Synced %d system_settings entries into os.environ", count)
        except Exception as e:
            logger.warning(
                "Could not sync system_settings to env (table may not exist yet): %s", e
            )

        # 2. system_external_services credentials → os.environ (Azure DI, Tika)
        try:
            tika_svc = SystemExternalServiceService.get_service("tika")
            if tika_svc and tika_svc.service_url:
                os.environ["TIKA_SERVER_URL"] = tika_svc.service_url
            if tika_svc:
                timeout = (tika_svc.settings or {}).get("timeout_seconds")
                if timeout:
                    os.environ["TIKA_TIMEOUT_SECONDS"] = str(timeout)

            azure_di_svc = SystemExternalServiceService.get_service(
                "azure_document_intelligence"
            )
            if azure_di_svc:
                if azure_di_svc.service_url:
                    os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = (
                        azure_di_svc.service_url
                    )
                use_mi = bool(
                    (azure_di_svc.settings or {}).get("use_managed_identity", False)
                )
                os.environ["AZURE_DOCUMENT_INTELLIGENCE_MANAGED_IDENTITY"] = str(
                    use_mi
                ).lower()
                model_id = (azure_di_svc.settings or {}).get("model_id")
                if model_id:
                    os.environ["AZURE_DI_MODEL_ID"] = model_id
                creds = SystemExternalServiceService.get_decrypted_credentials(
                    "azure_document_intelligence"
                )
                if creds and creds.get("api_key"):
                    os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = creds["api_key"]
        except Exception as e:
            logger.warning(
                "Could not sync system_external_services to env "
                "(table may not exist yet): %s",
                e,
            )

    @staticmethod
    def _get_env_key(section: str, key: str) -> Optional[str]:
        """Map section and key to environment variable name."""
        mapping = {
            "llm_providers.azure_openai.api_key": "AZURE_OPENAI_API_KEY",
            "llm_providers.azure_openai.endpoint": "AZURE_OPENAI_ENDPOINT",
            "llm_providers.azure_openai.deployment_name": "AZURE_OPENAI_DEPLOYMENT_NAME",
            "llm_providers.openai.api_key": "OPENAI_API_KEY",
            "llm_providers.openai.base_url": "OPENAI_BASE",
            "llm_providers.anthropic.api_key": "ANTHROPIC_API_KEY",
            "database.postgresql.host": "KEY_POSTGRES_HOST",
            "database.postgresql.port": "KEY_POSTGRES_PORT",
            "database.postgresql.database": "KEY_POSTGRES_DBNAME",
            "database.postgresql.username": "KEY_POSTGRES_USER",
            "database.postgresql.password": "KEY_POSTGRES_PASSWORD",
            "database.postgresql.sslmode": "KEY_POSTGRES_SSLMODE",
            # Document extraction — provider selection and non-credential options only.
            # Azure DI and Tika URLs/credentials are managed via
            # /api/admin/settings/external-services/{service_name} and stored in
            # system_external_services (encrypted); they must NOT go through this path.
            "external_services.document_extraction.provider": "DOCUMENT_EXTRACTION_PROVIDER",
            "external_services.document_extraction.model_ocr_deployment_id": "DOCUMENT_EXTRACTION_MODEL_DEPLOYMENT_ID",
            "external_services.document_extraction.model_ocr_detail": "DOCUMENT_EXTRACTION_MODEL_OCR_DETAIL",
            "external_services.tavily.api_key": "TAVILY_API_KEY",
            "external_services.langchain.api_key": "LANGCHAIN_API_KEY",
            "external_services.langchain.tracing_v2": "LANGCHAIN_TRACING_V2",
            "external_services.langchain.project": "LANGCHAIN_PROJECT",
            "external_services.langfuse.enabled": "LANGFUSE_ENABLED",
            "external_services.langfuse.host": "LANGFUSE_HOST",
            "external_services.langfuse.base_url": "LANGFUSE_BASE_URL",
            "external_services.langfuse.public_key": "LANGFUSE_PUBLIC_KEY",
            "external_services.langfuse.secret_key": "LANGFUSE_SECRET_KEY",
            # "external_services.langfuse.client_id": "LANGFUSE_CLIENT_ID",
            "external_services.phoenix.enabled": "PHOENIX_ENABLED",
            "external_services.phoenix.endpoint": "PHOENIX_ENDPOINT",
            "external_services.phoenix.project_name": "PHOENIX_PROJECT_NAME",
            "external_services.phoenix.api_key": "PHOENIX_API_KEY",
            "external_services.phoenix.ui_url": "PHOENIX_UI_URL",
            "external_services.phoenix.eval_penalty_enabled": "PHOENIX_EVAL_PENALTY_ENABLED",
            "external_services.phoenix.eval_model_deployment_id": "PHOENIX_EVAL_MODEL_DEPLOYMENT_ID",
            "external_services.phoenix.eval_faithfulness_enabled": "PHOENIX_EVAL_FAITHFULNESS_ENABLED",
            "external_services.phoenix.eval_tool_selection_enabled": "PHOENIX_EVAL_TOOL_SELECTION_ENABLED",
            "external_services.phoenix.eval_llm_judge_enabled": "PHOENIX_EVAL_LLM_JUDGE_ENABLED",
            "security.encryption.key": "CREDENTIAL_ENCRYPTION_KEY",
        }
        key_path = f"{section}.{key}"
        if key_path in mapping:
            return mapping[key_path]
        if section == "mcp.secrets":
            env_safe_key = key.upper().replace("-", "_")
            return f"MCP_SECRET_{env_safe_key}"
        return None

    def test_llm_connection(self, provider: str) -> Dict[str, Any]:
        """
        Test LLM provider connection.

        Args:
            provider: Provider name (azure_openai, openai, anthropic)

        Returns:
            Test result with status and details
        """
        try:
            if provider == "azure_openai":
                config = LLMConfig(
                    provider="azure_openai",
                    model_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
                    temperature=0.7,
                )
            elif provider == "openai":
                config = LLMConfig(
                    provider="openai", model_name="gpt-4", temperature=0.7
                )
            elif provider == "anthropic":
                config = LLMConfig(
                    provider="anthropic",
                    model_name="claude-3-sonnet-20240229",
                    temperature=0.7,
                )
            else:
                return {
                    "success": False,
                    "provider": provider,
                    "error": f"Unknown provider: {provider}",
                    "status": "error",
                }

            result = self.llm_factory.test_llm_connection(config)
            result["status"] = "connected" if result["success"] else "error"
            return result

        except Exception as e:
            logger.error("LLM connection test failed for provider %s: %s", provider, e)
            return {
                "success": False,
                "provider": provider,
                "error": f"{type(e).__name__}: connection test failed",
                "status": "error",
            }

    @staticmethod
    def test_database_connection() -> Dict[str, Any]:
        """
        Test database connection.

        Returns:
            Test result with status and details
        """
        try:
            import time

            start_time = time.time()

            conn = psycopg2.connect(
                host=os.getenv("KEY_POSTGRES_HOST", "localhost"),
                port=os.getenv("KEY_POSTGRES_PORT", "5432"),
                database=os.getenv("KEY_POSTGRES_DBNAME", "langgraph"),
                user=os.getenv("KEY_POSTGRES_USER", "postgres"),
                password=os.getenv("KEY_POSTGRES_PASSWORD", "postgres"),
                sslmode=os.getenv("KEY_POSTGRES_SSLMODE", "prefer"),
            )

            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            # Check pgvector extension
            cursor.execute(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            )
            pgvector_version = cursor.fetchone()

            cursor.close()
            conn.close()

            response_time = (time.time() - start_time) * 1000  # Convert to ms

            return {
                "success": True,
                "status": "connected",
                "version": version,
                "pgvector_enabled": pgvector_version is not None,
                "pgvector_version": pgvector_version[0] if pgvector_version else None,
                "response_time_ms": round(response_time, 2),
            }

        except Exception as e:
            logger.error("Database connection test failed: %s", e)
            return {
                "success": False,
                "status": "error",
                "error": f"{type(e).__name__}: database connection test failed",
                "response_time_ms": None,
            }

    def get_env_file_content(self) -> str:
        """
        Get the content of the .env file.

        Returns:
            Content of the .env file
        """
        try:
            if self.env_file.exists():
                with open(self.env_file, "r") as f:
                    return f.read()
            return ""
        except Exception as e:
            logger.error(f"Failed to read .env file: {e}")
            return ""

    def export_configuration(self) -> Dict[str, Any]:
        """
        Export configuration for backup.

        Returns:
            Exportable configuration dictionary
        """
        return {
            "version": "1.0.0",
            "exported_at": datetime.now().isoformat(),
            "configuration": self.get_environment_config(sanitize=False),
            "env_values": dict(dotenv_values(self.env_file)),
        }

    def import_configuration(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import configuration from backup.

        Args:
            config_data: Configuration data to import

        Returns:
            Import result with status
        """
        try:
            if "env_values" in config_data:
                for key, value in config_data["env_values"].items():
                    set_key(self.env_file, key, value)
                    os.environ[key] = value

                load_dotenv(override=True)

                return {
                    "success": True,
                    "message": "Configuration imported successfully",
                    "imported_keys": len(config_data["env_values"]),
                }
            else:
                return {"success": False, "error": "Invalid configuration format"}

        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return {
                "success": False,
                "error": "Configuration import failed. Check server logs for details.",
            }

    def get_service_status(self) -> Dict[str, Any]:
        """
        Get status of all configured services.

        Returns:
            Dictionary with service statuses
        """
        status = {"llm_providers": {}, "database": {}, "external_services": {}}

        # Check LLM providers
        for provider in ["azure_openai", "openai", "anthropic"]:
            if self._is_provider_configured(provider):
                result = self.test_llm_connection(provider)
                status["llm_providers"][provider] = {
                    "status": "connected" if result["success"] else "error",
                    "error": result.get("error"),
                }
            else:
                status["llm_providers"][provider] = {"status": "not_configured"}

        # Check database
        db_result = self.test_database_connection()
        status["database"]["postgresql"] = {
            "status": "connected" if db_result["success"] else "error",
            "error": db_result.get("error"),
            "response_time_ms": db_result.get("response_time_ms"),
        }

        # Check external services
        status["external_services"]["tavily"] = {
            "status": "connected" if os.getenv("TAVILY_API_KEY") else "not_configured"
        }
        status["external_services"]["langchain"] = {
            "status": "connected"
            if os.getenv("LANGCHAIN_API_KEY")
            else "not_configured"
        }
        phoenix_endpoint = self._get_db_setting(
            "PHOENIX_ENDPOINT", os.getenv("PHOENIX_ENDPOINT")
        )
        status["external_services"]["phoenix"] = {
            "status": "connected" if phoenix_endpoint else "not_configured"
        }

        return status

    @staticmethod
    def _is_provider_configured(provider: str) -> bool:
        """Check if a provider is configured."""
        if provider == "azure_openai":
            return bool(os.getenv("AZURE_OPENAI_API_KEY"))
        elif provider == "openai":
            return bool(os.getenv("OPENAI_API_KEY"))
        elif provider == "anthropic":
            return bool(os.getenv("ANTHROPIC_API_KEY"))
        return False


# Singleton instance
_config_service = None


def get_config_service() -> ConfigurationService:
    """Get the singleton configuration service instance."""
    global _config_service
    if _config_service is None:
        _config_service = ConfigurationService()
    return _config_service
