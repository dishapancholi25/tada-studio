"""Query execution functionality."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models import DatabaseType, DataSourceConnection, DataSourceQueryHistory
from backend.services.datasource.config import (
    DDL_OPERATIONS,
    DEFAULT_QUERY_ROW_LIMIT,
    DEFAULT_QUERY_TIMEOUT_SECONDS,
    LOG_PREFIX,
    WRITE_OPERATIONS,
)
from backend.services.datasource.connection.builders import (
    ConnectionStringBuilderFactory,
)
from backend.services.datasource.exceptions import (
    InvalidQueryError,
    ReadOnlyViolationError,
)

from .formatters import ResultFormatter
from .validator import QueryValidator


logger = logging.getLogger(__name__)


class QueryExecutor:
    """Executes queries on datasource connections with safety measures."""

    def __init__(self):
        """Initialize query executor."""
        self.builder_factory = ConnectionStringBuilderFactory()
        self.validator = QueryValidator()
        self.formatter = ResultFormatter()

    async def execute_query(
        self,
        db: Session,
        connection: DataSourceConnection,
        query: str,
        allowed_operations: List[str],
        table_names: Optional[List[str]] = None,
        max_rows: int = DEFAULT_QUERY_ROW_LIMIT,
        timeout_seconds: int = DEFAULT_QUERY_TIMEOUT_SECONDS,
        enable_read_only: bool = False,
        return_format: str = "json",
        include_schema: bool = True,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a database query with safety measures.

        Args:
            db: Database session
            connection: DataSourceConnection instance
            query: SQL query to execute
            allowed_operations: List of allowed SQL operations
            table_names: Optional list of allowed table names
            max_rows: Maximum number of rows to return
            timeout_seconds: Query timeout in seconds
            enable_read_only: Whether to enable read-only mode
            return_format: Output format (json/csv/markdown)
            include_schema: Whether to include schema information
            user_id: User ID executing the query
            context: Additional context information

        Returns:
            Dictionary with query results or error information
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Validate the query
            self.validator.validate(
                query, allowed_operations, table_names, enable_read_only
            )

            # Extract operation
            operation = self.validator.extract_operation(query)

            # Check read-only mode
            if connection.read_only:
                self._check_read_only_compliance(operation, connection.id)

            # Build connection string and create engine
            conn_str = self.builder_factory.build_connection_string(connection)
            connect_args = self._get_connect_args(
                connection.database_type, timeout_seconds
            )
            engine = create_engine(conn_str, connect_args=connect_args)

            # Execute the query
            result = self._execute_with_engine(
                db=db,
                engine=engine,
                connection=connection,
                query=query,
                operation=operation,
                max_rows=max_rows,
                enable_read_only=enable_read_only,
                return_format=return_format,
                include_schema=include_schema,
                table_names=table_names,
                user_id=user_id,
                context=context,
                start_time=start_time,
            )

            # Update connection usage stats
            connection.query_count += 1
            connection.last_used = datetime.now(timezone.utc)
            db.commit()

            return result

        except InvalidQueryError as e:
            return self._handle_error(
                db,
                connection.id,
                query,
                "validation",
                str(e),
                start_time,
                user_id,
                context,
            )
        except ReadOnlyViolationError as e:
            return self._handle_error(
                db,
                connection.id,
                query,
                "permission",
                str(e),
                start_time,
                user_id,
                context,
            )
        except SQLAlchemyError as e:
            return self._handle_error(
                db,
                connection.id,
                query,
                "database",
                str(e),
                start_time,
                user_id,
                context,
            )
        except Exception as e:
            return self._handle_error(
                db,
                connection.id,
                query,
                "unknown",
                str(e),
                start_time,
                user_id,
                context,
            )

    def _check_read_only_compliance(self, operation: str, connection_id: str) -> None:
        """Check if operation is allowed on read-only connection."""
        write_operations = WRITE_OPERATIONS + DDL_OPERATIONS
        if operation in write_operations:
            raise ReadOnlyViolationError(connection_id, operation)

    def _get_connect_args(
        self, database_type: DatabaseType, timeout_seconds: int
    ) -> dict:
        """Get driver-specific connect_args for the given database type."""
        if database_type == DatabaseType.ORACLE:
            return {"tcp_connect_timeout": timeout_seconds}
        return {"connect_timeout": timeout_seconds}

    def _execute_with_engine(
        self,
        db: Session,
        engine,
        connection: DataSourceConnection,
        query: str,
        operation: str,
        max_rows: int,
        enable_read_only: bool,
        return_format: str,
        include_schema: bool,
        table_names: Optional[List[str]],
        user_id: Optional[str],
        context: Optional[Dict[str, Any]],
        start_time: datetime,
    ) -> Dict[str, Any]:
        """Execute query with SQLAlchemy engine."""
        with engine.connect() as conn:
            # Set read-only mode if enabled
            if enable_read_only:
                conn.execute(text("SET TRANSACTION READ ONLY"))

            # Execute the query
            result = conn.execute(text(query))

            if operation == "SELECT":
                return self._handle_select_result(
                    db,
                    connection,
                    result,
                    query,
                    operation,
                    max_rows,
                    return_format,
                    include_schema,
                    table_names,
                    engine,
                    user_id,
                    context,
                    start_time,
                )
            elif operation == "INSERT":
                # Capture RETURNING rows before commit; some drivers (e.g.
                # SQLite) forbid committing while an unconsumed result is open.
                returning_data = self._extract_returning_data(result)
                conn.commit()
                return self._handle_insert_result(
                    db,
                    connection.id,
                    query,
                    operation,
                    result,
                    start_time,
                    user_id,
                    context,
                    returning_data,
                )
            else:
                returning_data = self._extract_returning_data(result)
                conn.commit()
                return self._handle_other_result(
                    db,
                    connection.id,
                    query,
                    operation,
                    result,
                    start_time,
                    user_id,
                    context,
                    returning_data,
                )

    def _handle_select_result(
        self,
        db: Session,
        connection: DataSourceConnection,
        result,
        query: str,
        operation: str,
        max_rows: int,
        return_format: str,
        include_schema: bool,
        table_names: Optional[List[str]],
        engine,
        user_id: Optional[str],
        context: Optional[Dict[str, Any]],
        start_time: datetime,
    ) -> Dict[str, Any]:
        """Handle SELECT query result."""
        rows = result.fetchmany(max_rows)
        columns = list(result.keys())

        # Convert rows to dictionaries
        results = []
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                row_dict[col] = self.formatter.normalize_value(value)
            results.append(row_dict)

        # Get schema information if requested
        schema_info = self._get_schema_info(include_schema, table_names, engine)

        # Format results
        formatted_results = self.formatter.format_results(
            results, columns, return_format, include_schema, schema_info
        )

        # Check if more rows exist
        if len(rows) == max_rows:
            formatted_results["has_more_rows"] = True
            formatted_results["message"] = f"Results limited to {max_rows} rows"

        # Calculate execution time
        execution_time_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )
        formatted_results["execution_time_ms"] = execution_time_ms

        # Log query history
        self._log_query_history(
            db,
            connection.id,
            query,
            operation,
            "success",
            None,
            len(results),
            execution_time_ms,
            user_id,
            context,
        )

        logger.info(
            f"{LOG_PREFIX} Executed SELECT query on {connection.name}: "
            f"{len(results)} rows in {execution_time_ms}ms"
        )

        return formatted_results

    def _handle_insert_result(
        self,
        db: Session,
        connection_id: str,
        query: str,
        operation: str,
        result,
        start_time: datetime,
        user_id: Optional[str],
        context: Optional[Dict[str, Any]],
        returning_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle INSERT query result."""
        execution_time_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        response = {
            "success": True,
            "operation": "INSERT",
            "rows_affected": result.rowcount,
            "execution_time_ms": execution_time_ms,
            "message": f"Successfully inserted {result.rowcount} row(s)",
        }

        # Include RETURNING clause results if present
        if returning_data:
            response["data"] = returning_data["data"]
            response["columns"] = returning_data["columns"]

        self._log_query_history(
            db,
            connection_id,
            query,
            operation,
            "success",
            None,
            result.rowcount,
            execution_time_ms,
            user_id,
            context,
        )

        logger.info(
            f"{LOG_PREFIX} Executed INSERT query: {result.rowcount} rows affected"
        )

        return response

    def _handle_other_result(
        self,
        db: Session,
        connection_id: str,
        query: str,
        operation: str,
        result,
        start_time: datetime,
        user_id: Optional[str],
        context: Optional[Dict[str, Any]],
        returning_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle other query types (UPDATE, DELETE, etc.)."""
        execution_time_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        response = {
            "success": True,
            "operation": operation,
            "rows_affected": result.rowcount,
            "execution_time_ms": execution_time_ms,
            "message": f"Query executed successfully. {result.rowcount} row(s) affected",
        }

        # Include RETURNING clause results if present
        if returning_data:
            response["data"] = returning_data["data"]
            response["columns"] = returning_data["columns"]

        self._log_query_history(
            db,
            connection_id,
            query,
            operation,
            "success",
            None,
            result.rowcount,
            execution_time_ms,
            user_id,
            context,
        )

        logger.info(
            f"{LOG_PREFIX} Executed {operation} query: {result.rowcount} rows affected"
        )

        return response

    def _extract_returning_data(self, result) -> Optional[Dict[str, Any]]:
        """Capture RETURNING clause rows from a query result.

        Must be called before committing the transaction, because some drivers
        (e.g. SQLite) refuse to commit while an unconsumed result set is open.

        Args:
            result: SQLAlchemy CursorResult from the executed statement.

        Returns:
            Dict with ``data`` (list of row dicts) and ``columns`` (list of
            column names) if RETURNING rows are present, otherwise ``None``.
        """
        if not getattr(result, "returns_rows", False):
            return None

        try:
            columns = list(result.keys())
            rows = result.fetchall()
        except Exception as e:
            logger.warning(f"{LOG_PREFIX} Failed to read RETURNING rows: {e}")
            return None

        if not rows:
            return None

        data = [
            {col: self.formatter.normalize_value(row[i]) for i, col in enumerate(columns)}
            for row in rows
        ]
        logger.debug(f"{LOG_PREFIX} Captured {len(data)} RETURNING row(s)")
        return {"data": data, "columns": columns}

    def _get_schema_info(
        self, include_schema: bool, table_names: Optional[List[str]], engine
    ) -> Optional[Dict[str, Any]]:
        """Get schema information for the result."""
        if not include_schema or not table_names or not table_names[0]:
            return None

        try:
            inspector = inspect(engine)
            columns_info = inspector.get_columns(table_names[0])
            return {
                col["name"]: {
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": str(col["default"]) if col["default"] else None,
                }
                for col in columns_info
            }
        except Exception as e:
            logger.warning(f"{LOG_PREFIX} Could not retrieve schema info: {e}")
            return None

    def _handle_error(
        self,
        db: Session,
        connection_id: str,
        query: str,
        error_type: str,
        error_message: str,
        start_time: datetime,
        user_id: Optional[str],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Handle query execution error."""
        execution_time_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        logger.error(
            f"{LOG_PREFIX} Query execution failed ({error_type}): {error_message}"
        )

        # Log query history
        operation = (
            self.validator.extract_operation(query) if query.strip() else "UNKNOWN"
        )
        self._log_query_history(
            db,
            connection_id,
            query,
            operation,
            "failed",
            error_message,
            0,
            execution_time_ms,
            user_id,
            context,
        )

        return {
            "success": False,
            "error": error_message,
            "error_type": error_type,
            "execution_time_ms": execution_time_ms,
        }

    def _log_query_history(
        self,
        db: Session,
        connection_id: str,
        query: str,
        operation: str,
        status: str,
        error_message: Optional[str],
        rows_affected: int,
        execution_time_ms: int,
        user_id: Optional[str],
        context: Optional[Dict[str, Any]],
    ) -> None:
        """Log query execution to history."""
        try:
            history = DataSourceQueryHistory(
                connection_id=connection_id,
                query_text=query[:1000],  # Truncate long queries
                query_type=operation,
                status=status,
                error_message=error_message,
                rows_affected=rows_affected,
                execution_time_ms=execution_time_ms,
                executed_by=user_id,
                execution_context=context,
            )
            db.add(history)
            db.commit()
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to log query history: {e}")
