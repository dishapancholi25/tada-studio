"""Oracle connection string builder."""

import logging
from urllib.parse import quote_plus

from backend.models import DataSourceConnection

from .base import ConnectionStringBuilder


logger = logging.getLogger(__name__)


class OracleConnectionStringBuilder(ConnectionStringBuilder):
    """Build connection strings for Oracle databases.

    Uses python-oracledb driver (thin mode by default, no Oracle Client required).

    Supports SSL configuration with parameters:
    - service_name: Oracle service name (alternative to database_name)
    - wallet_location: Path to Oracle Wallet directory
    - wallet_password: Oracle Wallet password
    """

    def build(self, connection: DataSourceConnection) -> str:
        """Build Oracle connection string.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            Oracle connection string with oracledb

        Example:
            oracle+oracledb://user:pass@host:1521/?service_name=ORCL
        """
        password = self.get_decrypted_password(connection)
        ssl_config = self.get_ssl_config(connection)

        # Build base connection string
        conn_str = (
            f"oracle+oracledb://{quote_plus(connection.username)}:{quote_plus(password)}@"
            f"{connection.host}:{connection.port}/"
        )

        # Add service name parameter
        service_name = ssl_config.get("service_name") or connection.database_name
        if service_name:
            conn_str += f"?service_name={quote_plus(service_name)}"

        # Add SSL/wallet configuration if enabled
        if connection.use_ssl or connection.ssl_config:
            ssl_params = self._build_ssl_params(connection)
            if ssl_params:
                separator = "&" if "?" in conn_str else "?"
                params_str = self.build_params_string(ssl_params)
                conn_str += f"{separator}{params_str}"

        return conn_str

    def _build_ssl_params(self, connection: DataSourceConnection) -> dict:
        """Build SSL/wallet parameters for Oracle.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            Dictionary of SSL parameters
        """
        ssl_params = {}
        ssl_config = self.get_ssl_config(connection)

        # Wallet configuration
        if ssl_config.get("wallet_location"):
            ssl_params["wallet_location"] = quote_plus(ssl_config["wallet_location"])
        if ssl_config.get("wallet_password"):
            ssl_params["wallet_password"] = quote_plus(ssl_config["wallet_password"])

        return ssl_params
