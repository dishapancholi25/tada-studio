"""MongoDB connection string builder."""

import logging
from urllib.parse import quote_plus

from backend.models import DataSourceConnection

from .base import ConnectionStringBuilder


logger = logging.getLogger(__name__)


class MongoDBConnectionStringBuilder(ConnectionStringBuilder):
    """Build connection strings for MongoDB databases.

    Note: MongoDB support is experimental.

    Supports SSL configuration with parameters:
    - ssl_ca: Path to CA certificate file (ssl_ca_certs in connection string)
    - ssl_certfile: Path to client certificate file
    - ssl_keyfile: Path to client private key file
    - ssl_cert_reqs: Certificate verification requirement (CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED)
    """

    def build(self, connection: DataSourceConnection) -> str:
        """Build MongoDB connection string.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            MongoDB connection string

        Example:
            mongodb://user:pass@host:27017/admin?ssl=true
        """
        password = self.get_decrypted_password(connection)
        database_name = connection.database_name or "admin"

        # Build base connection string with or without authentication
        if connection.username and password:
            conn_str = (
                f"mongodb://{quote_plus(connection.username)}:{quote_plus(password)}@"
                f"{connection.host}:{connection.port}/{database_name}"
            )
        else:
            conn_str = f"mongodb://{connection.host}:{connection.port}/{database_name}"

        # Add SSL configuration if enabled
        if connection.use_ssl or connection.ssl_config:
            ssl_params = self._build_ssl_params(connection)
            if ssl_params:
                params_str = self.build_params_string(ssl_params)
                conn_str += f"?{params_str}"

        logger.warning(
            "MongoDB support is experimental. "
            "Use SQLAlchemy or direct PyMongo for production."
        )

        return conn_str

    def _build_ssl_params(self, connection: DataSourceConnection) -> dict:
        """Build SSL parameters for MongoDB.

        Args:
            connection: DataSourceConnection model instance

        Returns:
            Dictionary of SSL parameters
        """
        ssl_params = {"ssl": "true"}
        ssl_config = self.get_ssl_config(connection)

        # Certificate paths
        if ssl_config.get("ssl_ca"):
            ssl_params["ssl_ca_certs"] = ssl_config["ssl_ca"]
        if ssl_config.get("ssl_certfile"):
            ssl_params["ssl_certfile"] = ssl_config["ssl_certfile"]
        if ssl_config.get("ssl_keyfile"):
            ssl_params["ssl_keyfile"] = ssl_config["ssl_keyfile"]

        # Certificate verification
        ssl_verify = ssl_config.get("ssl_cert_reqs", "CERT_REQUIRED")
        ssl_params["ssl_cert_reqs"] = ssl_verify

        return ssl_params
