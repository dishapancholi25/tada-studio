"""MySQL connection string builder."""

import logging
from urllib.parse import quote_plus

from backend.models import DataSourceConnection

from .base import ConnectionStringBuilder


logger = logging.getLogger(__name__)


class MySQLConnectionStringBuilder(ConnectionStringBuilder):
    """Build connection strings for MySQL databases.

    Uses PyMySQL driver for better SSL support.

    Supports SSL configuration with parameters:
    - ssl_ca: Path to CA certificate file
    - ssl_cert: Path to client certificate file
    - ssl_key: Path to client private key file
    - ssl_verify_cert: Verify server certificate (boolean)
    - ssl_verify_identity: Verify server identity (boolean)
    """

    def build(self, connection: DataSourceConnection) -> str:
        """Build MySQL connection string.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            MySQL connection string using PyMySQL driver

        Example:
            mysql+pymysql://user:pass@host:3306/dbname?ssl=true
        """
        password = self.get_decrypted_password(connection)

        # Build base connection string with PyMySQL driver
        conn_str = (
            f"mysql+pymysql://{quote_plus(connection.username)}:{quote_plus(password)}@"
            f"{connection.host}:{connection.port}/{connection.database_name}"
        )

        # Add SSL configuration if enabled
        if connection.use_ssl or connection.ssl_config:
            ssl_params = self._build_ssl_params(connection)
            if ssl_params:
                params_str = self.build_params_string(ssl_params)
                conn_str += f"?{params_str}"

        return conn_str

    def _build_ssl_params(self, connection: DataSourceConnection) -> dict:
        """Build SSL parameters for MySQL.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            Dictionary of SSL parameters
        """
        ssl_params = {}
        ssl_config = self.get_ssl_config(connection)

        # Certificate paths
        if ssl_config.get("ssl_ca"):
            ssl_params["ssl_ca"] = ssl_config["ssl_ca"]
        if ssl_config.get("ssl_cert"):
            ssl_params["ssl_cert"] = ssl_config["ssl_cert"]
        if ssl_config.get("ssl_key"):
            ssl_params["ssl_key"] = ssl_config["ssl_key"]

        # If SSL is enabled but no specific config, enable basic SSL
        if connection.use_ssl and not ssl_params:
            ssl_params["ssl"] = "true"

        return ssl_params
