"""Query validation functionality."""

import logging
import re
from typing import List, Optional

from backend.services.datasource.config import ALL_OPERATIONS, DANGEROUS_KEYWORDS, LOG_PREFIX
from backend.services.datasource.exceptions import InvalidQueryError


logger = logging.getLogger(__name__)


class QueryValidator:
    """Validates SQL queries for safety and permissions.

    Checks queries for dangerous operations, proper table references,
    and adherence to allowed operations.
    """

    def __init__(self):
        """Initialize query validator."""
        self.dangerous_keywords = DANGEROUS_KEYWORDS

    def validate(
        self,
        query: str,
        allowed_operations: List[str],
        table_names: Optional[List[str]] = None,
        enable_read_only: bool = False,
    ) -> None:
        """Validate a SQL query.

        Args:
            query: SQL query to validate
            allowed_operations: List of allowed SQL operations
            table_names: Optional list of allowed table names
            enable_read_only: Whether read-only mode is enabled

        Raises:
            InvalidQueryError: If query fails validation
        """
        # Basic checks
        self._check_not_empty(query)

        # Extract operation
        operation = self._extract_operation(query)

        # Validate operation
        self._check_operation_allowed(operation, allowed_operations)

        # Check for dangerous keywords in all queries
        self._check_dangerous_keywords(query, allowed_operations)

        # Check table references
        if table_names:
            self._check_table_references(query, table_names)

        # Validate specific operation requirements
        if operation == "SELECT":
            self._validate_select_query(query, table_names)
        elif operation == "INSERT":
            self._validate_insert_query(query, table_names)

        logger.debug(f"{LOG_PREFIX} Query validation passed for {operation} operation")

    def extract_operation(self, query: str) -> str:
        """Extract the main SQL operation from a query.

        Public method for extracting operation type.

        Args:
            query: The SQL query string

        Returns:
            The main operation keyword (SELECT, INSERT, UPDATE, etc.)
        """
        return self._extract_operation(query)

    def _check_not_empty(self, query: str) -> None:
        """Check if query is empty."""
        if not query.strip():
            raise InvalidQueryError(query, "Query cannot be empty")

    def _extract_operation(self, query: str) -> str:
        """Extract the main SQL operation."""
        # Remove comments
        query_no_comments = re.sub(r"--[^\n]*", "", query)
        query_no_comments = re.sub(r"/\*.*?\*/", "", query_no_comments, flags=re.DOTALL)

        # Strip and get first word
        cleaned = query_no_comments.strip().upper().lstrip("(").strip()
        if not cleaned:
            raise InvalidQueryError(query, "Could not determine query operation type")

        words = cleaned.split()
        if not words:
            raise InvalidQueryError(query, "Could not determine query operation type")

        # Handle CTEs (WITH clauses)
        if words[0] == "WITH":
            return self._extract_cte_operation(query_no_comments, words)

        return words[0]

    def _extract_cte_operation(self, query: str, words: List[str]) -> str:
        """Extract operation from CTE query."""
        main_operations = ALL_OPERATIONS

        for i, word in enumerate(words):
            if word in main_operations and i > 2:
                return word

        # Default to SELECT for CTEs
        return "SELECT"

    def _check_operation_allowed(
        self, operation: str, allowed_operations: List[str]
    ) -> None:
        """Check if operation is in allowed list."""
        if operation not in allowed_operations:
            raise InvalidQueryError(
                operation,
                f"Operation '{operation}' is not allowed. "
                f"Allowed: {', '.join(allowed_operations)}",
            )

    def _check_dangerous_keywords(
        self, query: str, allowed_operations: List[str]
    ) -> None:
        """Check for dangerous keywords not in allowed operations."""
        # Blank out dollar-quoted and regular quoted literals so keywords inside data values
        scrubbed = re.sub(r"\$(\w*)\$.*?\$\1\$", "$$$$", query, flags=re.DOTALL)  # $$...$$ / $tag$...$tag$
        scrubbed = re.sub(r"'(?:[^']|'')*'", "''", scrubbed)
        scrubbed = re.sub(r'"(?:[^"]|"")*"', '""', scrubbed).upper()

        for keyword in self.dangerous_keywords:
            if keyword not in allowed_operations and re.search(rf"\b{keyword}\b", scrubbed):
                raise InvalidQueryError(
                    query, f"Query contains restricted keyword: {keyword}"
                )

    def _check_table_references(self, query: str, table_names: List[str]) -> None:
        """Check if query references allowed tables."""
        # Allow information_schema queries
        info_schema_pattern = r"\binformation_schema\b"
        if re.search(info_schema_pattern, query, re.IGNORECASE):
            return

        # Check if any allowed table is referenced
        for table in table_names:
            table_pattern = rf"\b{re.escape(table)}\b"
            if re.search(table_pattern, query, re.IGNORECASE):
                return

        # No allowed table found
        if len(table_names) == 1:
            raise InvalidQueryError(
                query,
                f"Query must reference table '{table_names[0]}' or information_schema",
            )
        else:
            table_list = ", ".join(table_names[:3])
            if len(table_names) > 3:
                table_list += f" (and {len(table_names) - 3} more)"
            raise InvalidQueryError(
                query,
                f"Query must reference one of: {table_list} or information_schema",
            )

    def _check_single_statement(self, query: str) -> None:
        """Check for multiple statements."""
        semicolon_count = query.count(";")
        if semicolon_count > 1 or (query.strip().endswith(";") and semicolon_count > 1):
            raise InvalidQueryError(query, "Multiple statements are not allowed")

    def _validate_select_query(
        self, query: str, table_names: Optional[List[str]]
    ) -> None:
        """Validate SELECT query requirements."""
        if not table_names:
            return

        # Allow information_schema
        if re.search(r"FROM\s+information_schema\.", query, re.IGNORECASE):
            return

        # Check for FROM clause with allowed table
        for table in table_names:
            from_pattern = rf"FROM\s+{re.escape(table)}"
            if re.search(from_pattern, query, re.IGNORECASE):
                return

        # No valid FROM clause found
        if len(table_names) == 1:
            raise InvalidQueryError(
                query, f"SELECT must be FROM '{table_names[0]}' or information_schema"
            )
        else:
            raise InvalidQueryError(
                query, "SELECT must be FROM one of the configured tables"
            )

    def _validate_insert_query(
        self, query: str, table_names: Optional[List[str]]
    ) -> None:
        """Validate INSERT query requirements."""
        query_upper = query.upper()

        # Check for VALUES clause
        if "VALUES" not in query_upper:
            raise InvalidQueryError(query, "INSERT query must include VALUES clause")

        # Check table name if specified
        if table_names:
            for table in table_names:
                if f"INTO {table.upper()}" in query_upper:
                    return

            # No valid INTO clause found
            if len(table_names) == 1:
                raise InvalidQueryError(
                    query, f"INSERT must specify 'INTO {table_names[0]}'"
                )
            else:
                raise InvalidQueryError(
                    query, "INSERT must specify INTO one of the configured tables"
                )
