"""Microsoft SQL Server connection string builder."""

import logging
from urllib.parse import quote_plus

from backend.models import DataSourceConnection
from backend.services.datasource.config import DEFAULT_MSSQL_DRIVER

from .base import ConnectionStringBuilder


logger = logging.getLogger(__name__)


class MSSQLConnectionStringBuilder(ConnectionStringBuilder):
    """Build connection strings for Microsoft SQL Server databases.

    Uses PyODBC driver with configurable ODBC driver.

    Supports SSL configuration with parameters:
    - driver: ODBC driver to use (default: ODBC Driver 17 for SQL Server)
    - encrypt: Enable connection encryption (yes/no/optional)
    - trustServerCertificate: Trust server certificate without validation (yes/no)
    - certificate: Path to certificate file
    """

    def build(self, connection: DataSourceConnection) -> str:
        """Build MSSQL connection string.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            MSSQL connection string with PyODBC

        Example:
            mssql+pyodbc://user:pass@host:1433/dbname?driver={ODBC+Driver+17+for+SQL+Server}&encrypt=yes
        """
        password = self.get_decrypted_password(connection)
        ssl_config = self.get_ssl_config(connection)

        # Get and encode ODBC driver
        driver = ssl_config.get("driver", DEFAULT_MSSQL_DRIVER)
        driver_encoded = quote_plus(driver)

        # Build base connection string
        conn_str = (
            f"mssql+pyodbc://{quote_plus(connection.username)}:{quote_plus(password)}@"
            f"{connection.host}:{connection.port}/{connection.database_name}"
            f"?driver={driver_encoded}"
        )

        # Add SSL/TLS configuration if enabled
        if connection.use_ssl or connection.ssl_config:
            ssl_params = self._build_ssl_params(connection)
            if ssl_params:
                params_str = self.build_params_string(ssl_params)
                conn_str += f"&{params_str}"

        return conn_str

    def _build_ssl_params(self, connection: DataSourceConnection) -> dict:
        """Build SSL parameters for MSSQL.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            Dictionary of SSL parameters
        """
        ssl_params = {}
        ssl_config = self.get_ssl_config(connection)

        # Encryption settings
        encrypt = ssl_config.get("encrypt", "yes")
        trust_cert = ssl_config.get("trustServerCertificate", "no")

        ssl_params["encrypt"] = encrypt
        ssl_params["trustServerCertificate"] = trust_cert

        # Certificate path if provided
        if ssl_config.get("certificate"):
            ssl_params["certificate"] = ssl_config["certificate"]

        return ssl_params
