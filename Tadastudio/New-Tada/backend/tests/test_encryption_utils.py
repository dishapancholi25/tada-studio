"""Tests for encryption utilities."""

import os
import pytest
from unittest.mock import patch

from cryptography.fernet import Fernet

from backend.encryption_utils import (
    CredentialEncryption,
    decrypt_credential,
    encrypt_credential,
)


class TestCredentialEncryption:
    """Tests for CredentialEncryption class."""

    def test_init_with_key(self):
        """Test initialization with provided encryption key."""
        key = Fernet.generate_key().decode()
        encryptor = CredentialEncryption(encryption_key=key)
        assert encryptor.cipher is not None

    @patch.dict(os.environ, {"CREDENTIAL_ENCRYPTION_KEY": ""}, clear=True)
    def test_init_without_key_raises_error(self):
        """Test initialization without key raises RuntimeError."""
        with pytest.raises(
            RuntimeError,
            match="CREDENTIAL_ENCRYPTION_KEY environment variable is required",
        ):
            CredentialEncryption()

    @patch.dict(os.environ, {"CREDENTIAL_ENCRYPTION_KEY": ""}, clear=True)
    def test_get_or_create_encryption_key_missing(self):
        """Test _get_or_create_encryption_key raises error when env var missing."""
        with pytest.raises(RuntimeError, match="CREDENTIAL_ENCRYPTION_KEY"):
            CredentialEncryption._get_or_create_encryption_key()

    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip."""
        key = Fernet.generate_key().decode()
        encryptor = CredentialEncryption(encryption_key=key)

        plaintext = "my-secret-api-key"
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext

    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        key = Fernet.generate_key().decode()
        encryptor = CredentialEncryption(encryption_key=key)

        result = encryptor.encrypt("")
        assert result == ""

    def test_decrypt_empty_string(self):
        """Test decrypting empty string."""
        key = Fernet.generate_key().decode()
        encryptor = CredentialEncryption(encryption_key=key)

        result = encryptor.decrypt("")
        assert result == ""

    def test_decrypt_invalid_ciphertext(self):
        """Test decrypting invalid ciphertext raises error."""
        key = Fernet.generate_key().decode()
        encryptor = CredentialEncryption(encryption_key=key)

        with pytest.raises(ValueError, match="Failed to decrypt"):
            encryptor.decrypt("invalid_ciphertext")

    def test_encrypt_password(self):
        """Test encrypt_password method."""
        key = Fernet.generate_key().decode()
        encryptor = CredentialEncryption(encryption_key=key)

        password = "my-secure-password"
        encrypted = encryptor.encrypt_password(password)
        decrypted = encryptor.decrypt_password(encrypted)

        assert decrypted == password

    def test_encrypt_connection_string(self):
        """Test encrypt_connection_string method."""
        key = Fernet.generate_key().decode()
        encryptor = CredentialEncryption(encryption_key=key)

        conn_string = "postgresql://user:pass@localhost/db"
        encrypted = encryptor.encrypt_connection_string(conn_string)
        decrypted = encryptor.decrypt_connection_string(encrypted)

        assert decrypted == conn_string

    def test_generate_key_from_password(self):
        """Test key generation from password."""
        password = "my-password"
        key1, salt = CredentialEncryption.generate_key_from_password(password)

        # Same password and salt should generate same key
        key2, _ = CredentialEncryption.generate_key_from_password(password, salt)
        assert key1 == key2

        # Different salt should generate different key
        key3, _ = CredentialEncryption.generate_key_from_password(password)
        assert key1 != key3


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @patch("backend.encryption_utils._get_default_encryptor")
    def test_encrypt_credential(self, mock_get_encryptor):
        """Test encrypt_credential convenience function."""
        mock_encryptor = mock_get_encryptor.return_value
        mock_encryptor.encrypt.return_value = "encrypted_value"

        result = encrypt_credential("my-credential")

        assert result == "encrypted_value"
        mock_encryptor.encrypt.assert_called_once_with("my-credential")

    @patch("backend.encryption_utils._get_default_encryptor")
    def test_decrypt_credential(self, mock_get_encryptor):
        """Test decrypt_credential convenience function."""
        mock_encryptor = mock_get_encryptor.return_value
        mock_encryptor.decrypt.return_value = "decrypted_value"

        result = decrypt_credential("encrypted_value")

        assert result == "decrypted_value"
        mock_encryptor.decrypt.assert_called_once_with("encrypted_value")
