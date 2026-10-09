"""PostgreSQL connection string builder."""

import logging
from urllib.parse import quote_plus

from backend.models import DataSourceConnection
from backend.services.datasource.config import DEFAULT_POSTGRES_SSL_MODE

from .base import ConnectionStringBuilder


logger = logging.getLogger(__name__)


class PostgreSQLConnectionStringBuilder(ConnectionStringBuilder):
    """Build connection strings for PostgreSQL databases.

    Supports SSL configuration with parameters:
    - sslmode: Connection SSL mode (disable, allow, prefer, require, verify-ca, verify-full)
    - sslcert: Path to client certificate file
    - sslkey: Path to client private key file
    - sslrootcert: Path to CA certificate file
    """

    def build(self, connection: DataSourceConnection) -> str:
        """Build PostgreSQL connection string.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            PostgreSQL connection string

        Example:
            postgresql://user:pass@host:5432/dbname?sslmode=require
        """
        password = self.get_decrypted_password(connection)

        # Build base connection string
        conn_str = (
            f"postgresql://{quote_plus(connection.username)}:{quote_plus(password)}@"
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
        """Build SSL parameters for PostgreSQL.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            Dictionary of SSL parameters
        """
        ssl_params = {}
        ssl_config = self.get_ssl_config(connection)

        # SSL mode
        sslmode = ssl_config.get("sslmode")
        if not sslmode and connection.use_ssl:
            sslmode = DEFAULT_POSTGRES_SSL_MODE
        if sslmode:
            ssl_params["sslmode"] = sslmode

        # Certificate paths
        if ssl_config.get("sslcert"):
            ssl_params["sslcert"] = ssl_config["sslcert"]
        if ssl_config.get("sslkey"):
            ssl_params["sslkey"] = ssl_config["sslkey"]
        if ssl_config.get("sslrootcert"):
            ssl_params["sslrootcert"] = ssl_config["sslrootcert"]

        return ssl_params
