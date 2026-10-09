"""Database query tool creator for agents.

This module creates database query tool instances that agents can use
to query databases.
"""

from typing import Any, Optional, Set

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.graph.agent_tools.utils import build_tool_name


logger = get_logger(__name__)


def create_database_query_tool_from_node(
    target_node: EnhancedNodeData,
    used_tool_names: Optional[Set[str]] = None,
) -> Optional[Any]:
    """
    Create a database query tool from a DATABASE_QUERY node.

    Args:
        target_node: The DATABASE_QUERY node configuration
        used_tool_names: Optional set to track used tool names for collision detection

    Returns:
        Database query tool instance, or None if configuration is invalid

    Raises:
        ImportError: If database query tool module is not available
    """
    if not target_node.database_query_config:
        logger.warning(f"Node {target_node.name} missing database_query_config")
        return None

    logger.info(f"Creating database query tool from node: {target_node.name}")

    from backend.tools.database_query import create_database_query_tool

    db_config = target_node.database_query_config

    # Handle both dict and DatabaseQueryConfig object
    if isinstance(db_config, dict):
        # Extract values from dict
        connection_id = db_config.get("connection_id", "")
        table_name = db_config.get("table_name", "")
        table_names = db_config.get("table_names", [])
        allowed_operations = db_config.get("allowed_operations", ["SELECT"])
        max_rows = db_config.get("max_rows", 100)
        timeout_seconds = db_config.get("timeout_seconds", 30)
        enable_read_only = db_config.get("enable_read_only", False)
        return_format = db_config.get("return_format", "json")
        include_schema = db_config.get("include_schema", True)
    else:
        # Use object attributes
        connection_id = db_config.connection_id
        table_name = db_config.table_name
        table_names = db_config.table_names if hasattr(db_config, "table_names") else []
        allowed_operations = db_config.allowed_operations
        max_rows = db_config.max_rows
        timeout_seconds = db_config.timeout_seconds
        enable_read_only = db_config.enable_read_only
        return_format = db_config.return_format
        include_schema = db_config.include_schema

    # Use table_names if available, otherwise fall back to table_name
    if not table_names and table_name:
        table_names = [table_name]

    from backend.services.datasource.config import DDL_OPERATIONS

    has_ddl = allowed_operations and any(op in DDL_OPERATIONS for op in allowed_operations)
    if not connection_id or (not table_names and not has_ddl):
        logger.warning(
            f"Database query node {target_node.name} missing connection_id or table_names"
        )
        return None

    # Build semantic tool name from node name
    tool_name = build_tool_name(
        tool_type_prefix="database_query",
        node_name=target_node.name,
        node_id=target_node.uniq_id,
        default_name="Database Query",
        used_names=used_tool_names,
    )

    # Look up connection to get database type for context
    database_type = None
    try:
        from backend.services.database import SessionLocal
        from backend.services.datasource.service import DataSourceService

        db = SessionLocal()
        try:
            ds_service = DataSourceService()
            connection = ds_service.get_connection(db, connection_id)
            if connection:
                database_type = connection.database_type.value if connection.database_type else None
        finally:
            db.close()
    except Exception as e:
        logger.debug(f"Could not resolve database type for connection {connection_id}: {e}")

    # Build description prefix from node name if not default
    description_prefix = None
    if target_node.name and target_node.name != "Database Query":
        description_prefix = f"Database query '{target_node.name}'"
        if target_node.description:
            description_prefix = f"{description_prefix} - {target_node.description}"

    db_query_tool = create_database_query_tool(
        connection_id=connection_id,
        table_names=table_names,
        allowed_operations=allowed_operations,
        max_rows=max_rows,
        timeout_seconds=timeout_seconds,
        enable_read_only=enable_read_only,
        return_format=return_format,
        include_schema=include_schema,
        tool_name=tool_name,
        description_prefix=description_prefix,
        database_type=database_type,
    )

    logger.info(f"Created database query tool: {tool_name} for tables: {table_names}")
    return db_query_tool
