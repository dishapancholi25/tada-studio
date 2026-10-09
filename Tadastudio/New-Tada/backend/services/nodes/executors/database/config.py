"""
Database Node Configuration Classes.

This module provides strongly-typed configuration dataclasses for database
node execution, improving type safety and validation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .exceptions import ConfigurationError


@dataclass
class ColumnMappingConfig:
    """
    Configuration for a single column mapping.

    Defines how to map a value from workflow state to a database column.
    Supports multiple source modes for flexibility.

    Attributes:
        column_name: Name of the database column
        source_mode: How to get the value ("static", "previous", "specific", "start")
        static_value: Static value to use if source_mode is "static"
        default_value: Default value to use if extraction fails
        source_node_id: ID of node to extract from if source_mode is "specific"
        source_field_path: Path to field in node output (e.g., "data.user.name")
    """

    column_name: str
    source_mode: str = "static"
    static_value: Optional[Any] = None
    default_value: Optional[Any] = None
    source_node_id: Optional[str] = None
    source_field_path: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.column_name:
            raise ConfigurationError("column_name", "Column name cannot be empty")

        valid_modes = ["static", "previous", "specific", "start"]
        if self.source_mode not in valid_modes:
            raise ConfigurationError(
                "source_mode",
                f"Invalid source mode '{self.source_mode}'. "
                f"Must be one of: {', '.join(valid_modes)}",
            )

        if self.source_mode == "specific" and not self.source_node_id:
            raise ConfigurationError(
                "source_node_id",
                "source_node_id is required when source_mode is 'specific'",
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ColumnMappingConfig":
        """
        Create ColumnMappingConfig from dictionary.

        Args:
            data: Dictionary with mapping configuration

        Returns:
            ColumnMappingConfig instance

        Raises:
            ConfigurationError: If required fields are missing
        """
        return cls(
            column_name=data.get("column_name", ""),
            source_mode=data.get("source_mode", "static"),
            static_value=data.get("static_value"),
            default_value=data.get("default_value"),
            source_node_id=data.get("source_node_id"),
            source_field_path=data.get("source_field_path"),
        )


@dataclass
class DatabaseInsertConfig:
    """
    Configuration for database INSERT operation.

    Defines the complete configuration for inserting data into a database,
    including connection details, table name, column mappings, and options.

    Attributes:
        connection_id: ID of the database connection to use
        table_name: Name of the table to insert into
        column_mappings: List of column mapping configurations
        return_inserted_rows: Whether to return inserted rows (RETURNING *)
    """

    connection_id: str
    table_name: str
    column_mappings: List[ColumnMappingConfig] = field(default_factory=list)
    return_inserted_rows: bool = True

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.connection_id:
            raise ConfigurationError("connection_id", "Connection ID cannot be empty")

        if not self.table_name:
            raise ConfigurationError("table_name", "Table name cannot be empty")

        if not self.column_mappings:
            raise ConfigurationError(
                "column_mappings", "At least one column mapping is required"
            )

        # Convert dict mappings to ColumnMappingConfig if needed
        validated_mappings = []
        for i, mapping in enumerate(self.column_mappings):
            if isinstance(mapping, dict):
                try:
                    validated_mappings.append(ColumnMappingConfig.from_dict(mapping))
                except (ConfigurationError, Exception) as e:
                    raise ConfigurationError(
                        f"column_mappings[{i}]", f"Invalid mapping: {e}"
                    ) from e
            elif isinstance(mapping, ColumnMappingConfig):
                validated_mappings.append(mapping)
            else:
                # Handle object with attributes (dataclass from frontend)
                validated_mappings.append(
                    ColumnMappingConfig(
                        column_name=getattr(mapping, "column_name", ""),
                        source_mode=getattr(mapping, "source_mode", "static"),
                        static_value=getattr(mapping, "static_value", None),
                        default_value=getattr(mapping, "default_value", None),
                        source_node_id=getattr(mapping, "source_node_id", None),
                        source_field_path=getattr(mapping, "source_field_path", None),
                    )
                )

        self.column_mappings = validated_mappings

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatabaseInsertConfig":
        """
        Create DatabaseInsertConfig from dictionary.

        Args:
            data: Dictionary with database insert configuration

        Returns:
            DatabaseInsertConfig instance

        Raises:
            ConfigurationError: If required fields are missing or invalid
        """
        return cls(
            connection_id=data.get("connection_id", ""),
            table_name=data.get("table_name", ""),
            column_mappings=data.get("column_mappings", []),
            return_inserted_rows=data.get("return_inserted_rows", True),
        )

    @classmethod
    def from_node_config(cls, config: Any) -> "DatabaseInsertConfig":
        """
        Create DatabaseInsertConfig from node configuration.

        Handles both dict and object-style configurations from the frontend.

        Args:
            config: Configuration from node (dict or object)

        Returns:
            DatabaseInsertConfig instance

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if isinstance(config, dict):
            return cls.from_dict(config)
        else:
            # Handle object with attributes
            return cls(
                connection_id=getattr(config, "connection_id", ""),
                table_name=getattr(config, "table_name", ""),
                column_mappings=list(getattr(config, "column_mappings", [])),
                return_inserted_rows=getattr(config, "return_inserted_rows", True),
            )


@dataclass
class DatabaseConnectionDetails:
    """
    Database connection details.

    Contains all information needed to establish a database connection,
    including decrypted credentials.

    Attributes:
        host: Database server hostname or IP
        port: Database server port
        database: Database name
        username: Database username
        password: Decrypted database password
        use_ssl: Whether to use SSL/TLS connection
    """

    host: str
    port: int
    database: str
    username: str
    password: str
    use_ssl: bool = False

    def get_sslmode(self) -> str:
        """
        Get SSL mode for psycopg2 connection.

        Returns:
            "prefer" if use_ssl is True, "disable" otherwise
        """
        return "prefer" if self.use_ssl else "disable"

    def to_psycopg2_kwargs(self) -> Dict[str, Any]:
        """
        Convert to psycopg2 connection kwargs.

        Returns:
            Dictionary of connection parameters for psycopg2.connect()
        """
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.username,
            "password": self.password,
            "sslmode": self.get_sslmode(),
        }
