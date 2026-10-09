"""Service for managing admin-managed (system-level) external service configurations.

Implements the org-tier external services proposed in issue #217.

Credentials stored in ``encrypted_credentials`` (JSON) are encrypted at rest
using ``CredentialEncryption``; individual keys in the JSON blob are each
encrypted independently so the blob can be safely read back field-by-field.

Scope:      System / organisation-wide (no user_id)
Who writes: Admin only (enforced at the API layer)
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.dialects.postgresql import insert

from ...encryption_utils import decrypt_credential, encrypt_credential
from ...models.configuration.system_external_service import (
    ExternalServiceAuthType,
    SystemExternalService,
)
from ...services.config import get_logger
from ...services.database import get_db

logger = get_logger(__name__)
LOG_PREFIX = "[SYS-EXT-SVC]"


class SystemExternalServiceService:
    """CRUD service for system-level (admin-managed) external service configurations.

    All credential values stored in ``encrypted_credentials`` are individually
    encrypted.  The service never returns raw credential values to callers —
    call :meth:`get_decrypted_credentials` only where the credentials are
    actively needed (e.g. inside a document-extraction service constructor).
    """

    @staticmethod
    def get_service(service_name: str) -> Optional[SystemExternalService]:
        """Return the service record for *service_name*, or ``None`` if absent.

        Args:
            service_name: Stable machine identifier (e.g. ``azure_document_intelligence``).

        Returns:
            Detached :class:`SystemExternalService` ORM object, or ``None``.
        """
        with get_db() as db:
            svc = (
                db.query(SystemExternalService)
                .filter(SystemExternalService.service_name == service_name)
                .first()
            )
            if svc:
                db.expunge(svc)
            return svc

    @staticmethod
    def list_services() -> List[SystemExternalService]:
        """List all configured system external services (detached ORM objects).

        Returns:
            List of :class:`SystemExternalService` ordered by ``service_name``.
        """
        with get_db() as db:
            services = (
                db.query(SystemExternalService)
                .order_by(SystemExternalService.service_name)
                .all()
            )
            for svc in services:
                db.expunge(svc)
            return services

    @staticmethod
    def save_service(
        service_name: str,
        *,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        service_url: Optional[str] = None,
        auth_type: ExternalServiceAuthType = ExternalServiceAuthType.API_KEY_HEADER,
        credentials: Optional[Dict[str, str]] = None,
        settings: Optional[Dict[str, Any]] = None,
        is_active: bool = True,
    ) -> SystemExternalService:
        """Create or update a system external service configuration.

        Each value in *credentials* is encrypted individually before being
        stored in the ``encrypted_credentials`` JSON column.

        Args:
            service_name:  Stable machine identifier.
            display_name:  Human-readable label.
            description:   Optional description.
            service_url:   Base URL / endpoint (non-sensitive).
            auth_type:     Credential application method.
            credentials:   Dict of plaintext credential values to encrypt and store.
                           Pass ``None`` (or omit) to preserve existing credentials.
            settings:      Non-sensitive config dict.
            is_active:     Whether the service is enabled.

        Returns:
            Saved/updated detached :class:`SystemExternalService` object.
        """
        # Encrypt each credential value independently
        encrypted_creds: Optional[Dict[str, str]] = None
        if credentials is not None:
            encrypted_creds = {
                key: encrypt_credential(val) if val else ""
                for key, val in credentials.items()
            }

        with get_db() as db:
            existing = (
                db.query(SystemExternalService)
                .filter(SystemExternalService.service_name == service_name)
                .first()
            )

            if existing:
                # Partial update: only overwrite fields that were explicitly supplied
                if display_name is not None:
                    existing.display_name = display_name
                if description is not None:
                    existing.description = description
                if service_url is not None:
                    existing.service_url = service_url
                existing.auth_type = auth_type
                if encrypted_creds is not None:
                    existing.encrypted_credentials = encrypted_creds
                if settings is not None:
                    existing.settings = settings
                existing.is_active = is_active
                db.commit()
                db.refresh(existing)
                db.expunge(existing)
                logger.info("%s Updated %s", LOG_PREFIX, service_name)
                return existing
            else:
                # Insert new record
                stmt = insert(SystemExternalService).values(
                    service_name=service_name,
                    display_name=display_name,
                    description=description,
                    service_url=service_url,
                    auth_type=auth_type,
                    encrypted_credentials=encrypted_creds or {},
                    settings=settings or {},
                    is_active=is_active,
                )
                db.execute(stmt)
                db.commit()

                svc = (
                    db.query(SystemExternalService)
                    .filter(SystemExternalService.service_name == service_name)
                    .first()
                )
                if svc is None:
                    raise RuntimeError(
                        f"Failed to save/retrieve system external service '{service_name}'"
                    )
                db.expunge(svc)
                logger.info("%s Created %s", LOG_PREFIX, service_name)
                return svc

    @staticmethod
    def delete_service(service_name: str) -> bool:
        """Delete a system external service configuration.

        Args:
            service_name: Stable machine identifier.

        Returns:
            ``True`` if deleted, ``False`` if not found.
        """
        with get_db() as db:
            svc = (
                db.query(SystemExternalService)
                .filter(SystemExternalService.service_name == service_name)
                .first()
            )
            if not svc:
                return False
            db.delete(svc)
            db.commit()
            logger.info("%s Deleted %s", LOG_PREFIX, service_name)
            return True

    @staticmethod
    def get_decrypted_credentials(service_name: str) -> Optional[Dict[str, str]]:
        """Return the decrypted credentials dict for *service_name*.

        This method is intended for **internal use only** (e.g. service
        constructors that need to pass credentials to an SDK client).
        Never return the result of this method directly from an API endpoint.

        Args:
            service_name: Stable machine identifier.

        Returns:
            Dict mapping credential field names to their plaintext values, or
            ``None`` if the service is not configured or not active.
        """
        svc = SystemExternalServiceService.get_service(service_name)
        if not svc or not svc.is_active:
            return None

        encrypted_creds = svc.encrypted_credentials or {}
        if not encrypted_creds:
            return {}

        decrypted: Dict[str, str] = {}
        for key, enc_val in encrypted_creds.items():
            if not enc_val:
                decrypted[key] = ""
                continue
            try:
                decrypted[key] = decrypt_credential(enc_val)
            except Exception as exc:
                logger.error(
                    "%s Failed to decrypt credential '%s' for '%s': %s",
                    LOG_PREFIX,
                    key,
                    service_name,
                    exc,
                )
                decrypted[key] = ""
        return decrypted

    @staticmethod
    def _mask_credential(value: str) -> str:
        """Mask a credential value for display, showing only the last 4 characters."""
        if not value or len(value) < 4:
            return "****"
        return f"****...{value[-4:]}"

    @staticmethod
    def build_metadata_dict(svc: SystemExternalService) -> Dict[str, Any]:
        """Return a safe metadata dict suitable for API responses.

        Credentials are decrypted and masked (last-4-chars hint) so the UI
        can display dots-with-hint for configured secret fields.

        Args:
            svc: Detached ORM object.

        Returns:
            Dict with non-sensitive fields only.
        """
        cred_keys = list((svc.encrypted_credentials or {}).keys())
        credentials_masked: Dict[str, str] = {}
        for key, enc_val in (svc.encrypted_credentials or {}).items():
            if enc_val:
                try:
                    decrypted = decrypt_credential(enc_val)
                    credentials_masked[key] = (
                        SystemExternalServiceService._mask_credential(decrypted)
                    )
                except Exception:
                    credentials_masked[key] = "****"
        return {
            "service_name": svc.service_name,
            "display_name": svc.display_name,
            "description": svc.description,
            "service_url": svc.service_url,
            "auth_type": svc.auth_type.value if svc.auth_type else None,
            "credential_fields_configured": cred_keys,
            "credentials_configured": bool(
                any(v for v in (svc.encrypted_credentials or {}).values())
            ),
            "credentials_masked": credentials_masked,
            "settings": svc.settings,
            "is_active": svc.is_active,
            "created_at": svc.created_at.isoformat() if svc.created_at else None,
            "updated_at": svc.updated_at.isoformat() if svc.updated_at else None,
        }
