"""Database configuration for query and insert operations.

This module defines configurations for database operations including
queries, inserts, and column mappings.
"""

from typing import TYPE_CHECKING

from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .guardrails import GuardrailsConfig
from typing import Any, List, Optional


@dataclass
class ColumnMapping:
    """Mapping configuration for a database column.

    Defines how data flows into database columns from workflow state.

    Attributes:
        column_name: Name of the database column
        column_type: SQL type of the column (VARCHAR, INTEGER, etc.)
        is_required: Whether the column is required (NOT NULL)
        is_nullable: Whether the column accepts NULL values
        default_value: Default value if any
        is_primary_key: Whether the column is a primary key
        is_autoincrement: Whether the column auto-increments
        source_mode: Input source mode (static, previous, specific, start, field)
        static_value: Value for static mode
        source_node_id: Node ID for specific mode
        source_field_path: Field path for structured output
        custom_template: Template for complex mappings
    """

    column_name: str
    column_type: str
    is_required: bool = False
    is_nullable: bool = True
    default_value: Optional[Any] = None
    is_primary_key: bool = False
    is_autoincrement: bool = False
    source_mode: str = "static"
    static_value: Optional[Any] = None
    source_node_id: Optional[str] = None
    source_field_path: Optional[str] = None
    custom_template: Optional[str] = None


@dataclass
class DatabaseQueryConfig:
    """Configuration for database query tool nodes.

    Enables SQL query execution with configurable permissions and
    result formatting.

    Attributes:
        connection_id: ID of database connection from datasources
        table_name: [Deprecated] Use table_names
        table_names: List of tables that can be queried
        allowed_operations: Operations allowed (SELECT, INSERT, etc.)
        max_rows: Maximum rows to return for SELECT
        timeout_seconds: Query timeout
        enable_read_only: Force read-only mode
        return_format: Result format (json, csv, markdown)
        include_schema: Include column types in response
        parent_agent_id: ID of the agent this tool belongs to
    """

    connection_id: str = ""
    table_name: str = ""
    table_names: List[str] = field(default_factory=list)
    allowed_operations: List[str] = field(default_factory=lambda: ["SELECT", "INSERT"])
    max_rows: int = 100
    timeout_seconds: int = 30
    enable_read_only: bool = False
    return_format: str = "json"
    include_schema: bool = True
    parent_agent_id: Optional[str] = None
    guardrails_config: Optional["GuardrailsConfig"] = None


@dataclass
class DatabaseQueryActionConfig:
    """Configuration for database query action nodes (sequential execution).

    Identical fields to DatabaseQueryConfig but used for sequential workflow
    nodes rather than AI-callable tool nodes.

    Attributes:
        connection_id: ID of database connection from datasources
        table_name: [Deprecated] Use table_names
        table_names: List of tables that can be queried
        allowed_operations: Operations allowed (SELECT, INSERT, etc.)
        max_rows: Maximum rows to return for SELECT
        timeout_seconds: Query timeout
        enable_read_only: Force read-only mode
        return_format: Result format (json, csv, markdown)
        include_schema: Include column types in response
        selected_columns: Specific columns to SELECT (empty = all columns).
            When set, the executor builds "SELECT col1, col2 FROM table"
            instead of "SELECT * FROM table", so the output only contains
            the chosen fields for downstream iteration (e.g. For Each).
    """

    connection_id: str = ""
    table_name: str = ""
    table_names: List[str] = field(default_factory=list)
    allowed_operations: List[str] = field(default_factory=lambda: ["SELECT", "INSERT"])
    max_rows: int = 100
    timeout_seconds: int = 30
    enable_read_only: bool = False
    return_format: str = "json"
    include_schema: bool = True
    selected_columns: List[str] = field(default_factory=list)
    guardrails_config: Optional["GuardrailsConfig"] = None


@dataclass
class DatabaseInsertConfig:
    """Configuration for database insert action nodes.

    Enables structured data insertion with conflict handling and
    column mapping from workflow state.

    Attributes:
        connection_id: ID of database connection from datasources
        table_name: Table to insert into
        column_mappings: Column to input mappings
        return_inserted_rows: Whether to return the inserted rows
        on_conflict_strategy: Conflict handling (fail, ignore, update)
        conflict_columns: Columns for ON CONFLICT clause
        timeout_seconds: Insert timeout
        batch_size: Number of rows to insert at once
        transaction_mode: Transaction mode (auto, manual)
    """

    connection_id: str = ""
    table_name: str = ""
    column_mappings: List[ColumnMapping] = field(default_factory=list)
    return_inserted_rows: bool = True
    on_conflict_strategy: str = "fail"
    conflict_columns: List[str] = field(default_factory=list)
    timeout_seconds: int = 30
    batch_size: int = 1
    transaction_mode: str = "auto"
    guardrails_config: Optional["GuardrailsConfig"] = None
