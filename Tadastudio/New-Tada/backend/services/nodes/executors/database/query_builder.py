"""
Database Query Builder.

This module handles building SQL queries for database operations,
including INSERT queries with column mappings and value extraction.
"""

from typing import Any, List, Optional, Tuple

from backend.services.config import get_logger
from backend.services.io.extractors import MappingValueExtractor
from backend.services.workflow.state import WorkflowState

from .config import ColumnMappingConfig, DatabaseInsertConfig
from .exceptions import QueryBuildError


query_builder_logger = get_logger("nodes.executors.database.query_builder")


class DatabaseQueryBuilder:
    """
    Builds SQL queries for database operations.

    Handles:
    - Building INSERT queries with RETURNING clause
    - Processing column mappings from workflow state
    - Extracting values using MappingValueExtractor
    - Handling SQL expressions (CURRENT_TIMESTAMP, etc.)

    Example:
        >>> builder = DatabaseQueryBuilder(mapping_extractor)
        >>> query, values = builder.build_insert_query(config, state)
        >>> # Returns: ("INSERT INTO users (name, email) VALUES (%s, %s) RETURNING *", ["John", "john@example.com"])
    """

    def __init__(self, mapping_extractor: Optional[MappingValueExtractor] = None):
        """
        Initialize query builder.

        Args:
            mapping_extractor: Service for extracting values from mappings
        """
        self.mapping_extractor = mapping_extractor or MappingValueExtractor()

    def build_insert_query(
        self,
        config: DatabaseInsertConfig,
        state: WorkflowState,
    ) -> Tuple[str, List[Any]]:
        """
        Build INSERT query from configuration and state.

        Args:
            config: Database insert configuration
            state: Current workflow state

        Returns:
            Tuple of (query_string, values_list)

        Raises:
            QueryBuildError: If query building fails
        """
        query_builder_logger.info(
            f"[QUERY-BUILDER] Building INSERT query for table: {config.table_name}"
        )

        try:
            # Process column mappings to extract columns, values, and SQL expressions
            column_names, values, sql_expression_indices = (
                self._process_column_mappings(config.column_mappings, state)
            )

            query_builder_logger.debug(
                f"[QUERY-BUILDER] Processed {len(column_names)} column mappings: "
                f"{', '.join(column_names)}"
            )

            # Build query string
            query = self._build_insert_statement(
                config.table_name,
                column_names,
                values,
                sql_expression_indices,
                config.return_inserted_rows,
            )

            # Extract actual values (excluding SQL expressions)
            actual_values = self._extract_actual_values(values, sql_expression_indices)

            query_builder_logger.info(
                f"[QUERY-BUILDER] Built INSERT query with {len(actual_values)} parameters"
            )
            query_builder_logger.debug(f"[QUERY-BUILDER] Query: {query}")

            return query, actual_values

        except QueryBuildError:
            raise
        except Exception as e:
            query_builder_logger.error(
                f"[QUERY-BUILDER] Failed to build INSERT query: {e}", exc_info=True
            )
            raise QueryBuildError(
                config.table_name, f"Failed to build query: {e}"
            ) from e

    def _process_column_mappings(
        self,
        mappings: List[ColumnMappingConfig],
        state: WorkflowState,
    ) -> Tuple[List[str], List[Any], List[int]]:
        """
        Process column mappings to extract columns, values, and SQL expressions.

        Args:
            mappings: List of column mapping configurations
            state: Current workflow state

        Returns:
            Tuple of (column_names, values, sql_expression_indices)

        Raises:
            QueryBuildError: If mapping processing fails
        """
        column_names = []
        values = []
        sql_expression_indices = []

        for idx, mapping in enumerate(mappings):
            try:
                # Extract value using mapping extractor
                value = self.mapping_extractor.extract(
                    source_mode=mapping.source_mode,
                    state=state,
                    static_value=mapping.static_value,
                    default_value=mapping.default_value,
                    source_node_id=mapping.source_node_id,
                    source_field_path=mapping.source_field_path,
                    idx=idx,
                    sql_expressions=sql_expression_indices,
                )

                column_names.append(mapping.column_name)
                values.append(value)

                query_builder_logger.debug(
                    f"[QUERY-BUILDER] Mapped column '{mapping.column_name}': "
                    f"mode={mapping.source_mode}, "
                    f"is_sql_expr={idx in sql_expression_indices}"
                )

            except Exception as e:
                query_builder_logger.error(
                    f"[QUERY-BUILDER] Failed to process mapping for column "
                    f"'{mapping.column_name}': {e}",
                    exc_info=True,
                )
                raise QueryBuildError(
                    "unknown",
                    f"Failed to process mapping for column '{mapping.column_name}': {e}",
                ) from e

        return column_names, values, sql_expression_indices

    def _build_insert_statement(
        self,
        table_name: str,
        column_names: List[str],
        values: List[Any],
        sql_expression_indices: List[int],
        return_inserted_rows: bool,
    ) -> str:
        """
        Build INSERT SQL statement.

        Args:
            table_name: Name of the table
            column_names: List of column names
            values: List of values (may include SQL expressions)
            sql_expression_indices: Indices of SQL expressions in values
            return_inserted_rows: Whether to add RETURNING clause

        Returns:
            SQL INSERT statement string
        """
        # Build column list
        columns_str = ", ".join(column_names)

        # Build placeholders, using SQL expressions where needed
        placeholders = []
        for idx, val in enumerate(values):
            if idx in sql_expression_indices:
                # Use the SQL expression directly (e.g., CURRENT_TIMESTAMP)
                placeholders.append(val)
            else:
                # Use a placeholder for parameterized query
                placeholders.append("%s")

        placeholders_str = ", ".join(placeholders)

        # Build query
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders_str})"

        if return_inserted_rows:
            query += " RETURNING *"

        return query

    def _extract_actual_values(
        self, values: List[Any], sql_expression_indices: List[int]
    ) -> List[Any]:
        """
        Extract actual values for query execution.

        Filters out SQL expressions, returning only values that need to be
        passed to cursor.execute().

        Args:
            values: List of all values (including SQL expressions)
            sql_expression_indices: Indices of SQL expressions

        Returns:
            List of actual values (excluding SQL expressions)
        """
        actual_values = []
        for idx, val in enumerate(values):
            if idx not in sql_expression_indices:
                actual_values.append(val)

        return actual_values

    def validate_query(self, query: str) -> bool:
        """
        Validate SQL query for basic safety checks.

        This is a simple validation - production systems should use
        more comprehensive validation and parameterized queries.

        Args:
            query: SQL query to validate

        Returns:
            True if query passes basic validation

        Raises:
            QueryBuildError: If query is invalid
        """
        if not query or not query.strip():
            raise QueryBuildError("unknown", "Query cannot be empty")

        # Basic SQL injection prevention check
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER"]
        query_upper = query.upper()

        for keyword in dangerous_keywords:
            if keyword in query_upper and not query_upper.startswith("INSERT"):
                query_builder_logger.warning(
                    f"[QUERY-BUILDER] Potentially dangerous keyword '{keyword}' "
                    "found in query"
                )

        return True
