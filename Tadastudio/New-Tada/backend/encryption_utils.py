"""Encryption utilities for secure credential storage with key rotation support."""

import base64
import logging
import os
from typing import Dict, Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


logger = logging.getLogger(__name__)


class CredentialEncryption:
    """Handles encryption and decryption of sensitive credentials with key rotation support.

    Supports multiple encryption keys for rotation. Keys are versioned to allow
    decryption of old data while encrypting new data with the latest key.
    """

    def __init__(
        self,
        encryption_key: Optional[str] = None,
        rotation_keys: Optional[Dict[int, str]] = None,
        key_env_var: str = "CREDENTIAL_ENCRYPTION_KEY",
    ):
        """
        Initialize the encryption handler.

        Args:
            encryption_key: Base64 encoded encryption key. If not provided,
                          will use ``key_env_var`` from environment.
            rotation_keys: Optional dict mapping key versions to keys for rotation support.
                         Format: {1: "old_key", 2: "newer_key", 3: "current_key"}
            key_env_var: Base name of the environment variable holding the key.
                         Its ``_VERSION`` and ``_V{n}`` variants drive rotation.
                         Defaults to ``CREDENTIAL_ENCRYPTION_KEY``.
        """
        self.key_env_var = key_env_var
        if encryption_key:
            self.cipher = Fernet(encryption_key.encode())
            self.current_version = 1
            self.rotation_ciphers = {}
        else:
            # Get or generate encryption key
            key = self._get_or_create_encryption_key(key_env_var)
            self.cipher = Fernet(key)
            self.current_version = self._get_current_key_version(key_env_var)

            # Load rotation keys if available
            self.rotation_ciphers = self._load_rotation_keys(key_env_var)

    @staticmethod
    def _get_or_create_encryption_key(
        base_env_var: str = "CREDENTIAL_ENCRYPTION_KEY",
    ) -> bytes:
        """Get encryption key from environment.

        For test environments (when PYTEST_CURRENT_TEST is set), generates a key
        automatically. For production, requires ``base_env_var`` to be set.

        Raises:
            RuntimeError: If ``base_env_var`` is not set in non-test environment.
            ValueError: If ``base_env_var`` is not a valid Fernet key.
        """
        key_str = os.getenv(base_env_var)

        if not key_str:
            # Allow auto-generation for test environments only
            if os.getenv("PYTEST_CURRENT_TEST"):
                # Generate a key for testing
                return Fernet.generate_key()

            raise RuntimeError(
                f"{base_env_var} environment variable is required but not set. "
                'Generate one with: python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )

        # Validate that the key is a valid Fernet key
        key_bytes = key_str.encode()
        try:
            # Fernet keys must be 32 URL-safe base64-encoded bytes
            # First validate base64 format
            try:
                decoded = base64.urlsafe_b64decode(key_bytes)
            except Exception as decode_err:
                raise ValueError(f"Key is not valid base64 encoding: {decode_err}")

            # Check length (Fernet requires exactly 32 bytes)
            if len(decoded) != 32:
                raise ValueError(
                    f"Fernet key must be 32 bytes, got {len(decoded)} bytes"
                )

            # Finally, try to create a Fernet instance to fully validate
            Fernet(key_bytes)
        except ValueError:
            # Re-raise ValueError as-is (our custom messages)
            raise
        except Exception as e:
            raise ValueError(
                f"{base_env_var} is not a valid Fernet key: {str(e)}. "
                'Generate a new one with: python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )

        return key_bytes

    @staticmethod
    def _get_current_key_version(
        base_env_var: str = "CREDENTIAL_ENCRYPTION_KEY",
    ) -> int:
        """Get the current key version from environment.

        Returns:
            Current key version (defaults to 1 if not set).
        """
        version_var = f"{base_env_var}_VERSION"
        version_str = os.getenv(version_var, "1")
        try:
            return int(version_str)
        except ValueError:
            logger.warning(
                f"Invalid {version_var} '{version_str}', defaulting to 1"
            )
            return 1

    @staticmethod
    def _load_rotation_keys(
        base_env_var: str = "CREDENTIAL_ENCRYPTION_KEY",
    ) -> Dict[int, Fernet]:
        """Load rotation keys from environment for backward compatibility.

        Looks for environment variables like:
        - {base_env_var}_V1
        - {base_env_var}_V2
        - etc.

        Returns:
            Dict mapping version numbers to Fernet ciphers.
        """
        rotation_ciphers = {}
        for i in range(1, 10):  # Support up to 9 historical versions
            key_name = f"{base_env_var}_V{i}"
            key_str = os.getenv(key_name)
            if key_str:
                try:
                    rotation_ciphers[i] = Fernet(key_str.encode())
                    logger.info(
                        f"Loaded encryption key version {i} for rotation support"
                    )
                except Exception as e:
                    logger.error(f"Failed to load rotation key {key_name}: {e}")

        return rotation_ciphers

    @staticmethod
    def generate_key_from_password(
        password: str, salt: Optional[bytes] = None
    ) -> Tuple[bytes, bytes]:
        """
        Generate an encryption key from a password.

        Args:
            password: The password to derive the key from
            salt: Optional salt. If not provided, a new one will be generated.

        Returns:
            Tuple of (key, salt)
        """
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

        return key, salt

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string with version prefix.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64 encoded encrypted string with version prefix (v{version}:encrypted_data)
        """
        if not plaintext:
            return ""

        encrypted = self.cipher.encrypt(plaintext.encode())
        encrypted_b64 = base64.b64encode(encrypted).decode()

        # Prefix with version for rotation support
        return f"v{self.current_version}:{encrypted_b64}"

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string, supporting versioned keys.

        Args:
            ciphertext: Base64 encoded encrypted string, optionally prefixed with v{version}:

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""

        try:
            # Check if ciphertext has version prefix
            if ciphertext.startswith("v") and ":" in ciphertext:
                version_str, encrypted_b64 = ciphertext.split(":", 1)
                try:
                    version = int(version_str[1:])  # Strip 'v' prefix
                except ValueError:
                    # Invalid version format, treat as legacy (no version)
                    encrypted_b64 = ciphertext
                    version = None
            else:
                # Legacy format (no version prefix)
                encrypted_b64 = ciphertext
                version = None

            # Select appropriate cipher for decryption
            if version and version != self.current_version:
                # Try to use rotation key
                cipher = self.rotation_ciphers.get(version)
                if not cipher:
                    raise ValueError(
                        f"Encryption key version {version} not available for decryption. "
                        f"Set CREDENTIAL_ENCRYPTION_KEY_V{version} environment variable."
                    )
            else:
                # Use current cipher
                cipher = self.cipher

            encrypted = base64.b64decode(encrypted_b64)
            decrypted = cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt: {str(e)}")

    def encrypt_connection_string(self, connection_string: str) -> str:
        """
        Encrypt a database connection string.

        Args:
            connection_string: The connection string to encrypt

        Returns:
            Encrypted connection string
        """
        return self.encrypt(connection_string)

    def decrypt_connection_string(self, encrypted_connection_string: str) -> str:
        """
        Decrypt a database connection string.

        Args:
            encrypted_connection_string: The encrypted connection string

        Returns:
            Decrypted connection string
        """
        return self.decrypt(encrypted_connection_string)

    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a password.

        Args:
            password: The password to encrypt

        Returns:
            Encrypted password
        """
        return self.encrypt(password)

    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt a password.

        Args:
            encrypted_password: The encrypted password

        Returns:
            Decrypted password
        """
        return self.decrypt(encrypted_password)


# Lazy initialization of the default encryptor to avoid import-time errors
_default_encryptor: Optional[CredentialEncryption] = None


def _get_default_encryptor() -> CredentialEncryption:
    """Get or create the default encryptor instance (lazy initialization)."""
    global _default_encryptor
    if _default_encryptor is None:
        _default_encryptor = CredentialEncryption()
    return _default_encryptor


def encrypt_credential(credential: str) -> str:
    """Encrypt a credential using the default encryptor."""
    return _get_default_encryptor().encrypt(credential)


def decrypt_credential(encrypted_credential: str) -> str:
    """Decrypt a credential using the default encryptor."""
    return _get_default_encryptor().decrypt(encrypted_credential)


class _LazyEncryptor:
    """Lazy proxy for the default encryptor to maintain backwards compatibility."""

    def __getattr__(self, name: str):
        return getattr(_get_default_encryptor(), name)


# Backwards-compatible alias - use lazy initialization to avoid import-time errors
default_encryptor = _LazyEncryptor()
