"""Encryption utilities for model deployment credentials.

This module provides utilities for encrypting and decrypting sensitive
credential information stored in model deployments.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ...encryption_utils import default_encryptor
from .exceptions import EncryptionError, InvalidCredentialError


logger = logging.getLogger(__name__)


class CredentialEncryption:
    """Handles encryption and decryption of model deployment credentials."""

    def __init__(self, encryptor=None):
        """Initialize credential encryption handler.

        Args:
            encryptor: Encryption service. Defaults to default_encryptor.
        """
        self.encryptor = encryptor or default_encryptor

    def encrypt_credentials(
        self, credentials: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, str]]:
        """Encrypt credential dictionary.

        Args:
            credentials: Dictionary of credential key-value pairs

        Returns:
            Dictionary of encrypted credentials or None if input is empty

        Raises:
            InvalidCredentialError: If credential value is not a string
            EncryptionError: If encryption fails
        """
        if not credentials:
            return None

        encrypted: Dict[str, str] = {}
        for key, value in credentials.items():
            if not value:
                continue
            if not isinstance(value, str):
                raise InvalidCredentialError(
                    f"Credential '{key}' must be a string, got {type(value).__name__}"
                )
            try:
                encrypted[key] = self.encryptor.encrypt(value)
            except Exception as exc:
                logger.error(
                    "[MODEL-DEPLOYMENT] Failed to encrypt credential '%s': %s", key, exc
                )
                raise EncryptionError(key, "encrypt", exc) from exc

        return encrypted or None

    def decrypt_credentials(
        self, encrypted: Optional[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Decrypt credential dictionary.

        Args:
            encrypted: Dictionary of encrypted credential key-value pairs

        Returns:
            Dictionary of decrypted credentials (empty dict if input is None)

        Note:
            Failed decryptions are logged but not raised to avoid breaking operations.
            The key will be omitted from the result.
        """
        if not encrypted:
            return {}

        decrypted: Dict[str, str] = {}
        for key, value in encrypted.items():
            if not value:
                continue
            try:
                decrypted[key] = self.encryptor.decrypt(value)
            except Exception as exc:
                logger.error(
                    "[MODEL-DEPLOYMENT] Failed to decrypt credential '%s': %s", key, exc
                )
                # Don't raise - allow partial decryption for robustness

        return decrypted

    def merge_credentials(
        self,
        existing_encrypted: Optional[Dict[str, Any]],
        updates: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, str]]:
        """Merge credential updates with existing credentials.

        Args:
            existing_encrypted: Current encrypted credentials
            updates: Updates to apply (None/empty string values remove keys)

        Returns:
            Updated encrypted credentials or None if result is empty

        Raises:
            InvalidCredentialError: If update value is not a string
            EncryptionError: If encryption fails
        """
        if updates is None:
            return existing_encrypted or None

        # Decrypt existing
        current = self.decrypt_credentials(existing_encrypted or {})

        # Apply updates
        for key, value in updates.items():
            if value in (None, ""):
                current.pop(key, None)
            else:
                if not isinstance(value, str):
                    raise InvalidCredentialError(
                        f"Credential '{key}' must be a string, got {type(value).__name__}"
                    )
                current[key] = value

        # Re-encrypt
        return self.encrypt_credentials(current)


# Global instance for backward compatibility
default_credential_encryption = CredentialEncryption()
