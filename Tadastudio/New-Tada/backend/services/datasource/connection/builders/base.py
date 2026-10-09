"""Base connection string builder."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from backend.encryption_utils import default_encryptor
from backend.models import DataSourceConnection


class ConnectionStringBuilder(ABC):
    """Abstract base class for building database connection strings.

    Each database type should implement its own builder subclass that
    handles the specific connection string format and SSL configuration
    for that database.
    """

    @abstractmethod
    def build(self, connection: DataSourceConnection) -> str:
        """Build a connection string from the connection configuration.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            Formatted connection string

        Raises:
            ValueError: If connection configuration is invalid
        """
        pass

    def get_decrypted_password(self, connection: DataSourceConnection) -> str:
        """Get decrypted password from connection.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            Decrypted password or empty string if not set
        """
        if connection.encrypted_password:
            return default_encryptor.decrypt_password(connection.encrypted_password)
        return ""

    def get_ssl_config(self, connection: DataSourceConnection) -> Dict[str, Any]:
        """Get SSL configuration dictionary.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            SSL configuration dictionary (may be empty)
        """
        return connection.ssl_config or {}

    def build_params_string(self, params: Dict[str, str], separator: str = "&") -> str:
        """Build URL parameter string from dictionary.

        Args:
            params: Dictionary of parameter key-value pairs
            separator: Separator to use between parameters (default: &)

        Returns:
            Formatted parameter string
        """
        if not params:
            return ""
        return separator.join(f"{key}={value}" for key, value in params.items())
