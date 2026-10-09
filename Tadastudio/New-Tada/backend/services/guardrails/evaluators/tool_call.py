"""Tool call guardrail evaluator.

Validates tool call arguments against configured policies including
SSRF protection, SQL operation restrictions, and file path sanitization.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

from backend.models.workflow.configs.guardrails import ToolCallPolicy
from backend.services.guardrails.models import GuardrailResult, Violation
from backend.services.guardrails.ssrf import validate_url

logger = logging.getLogger(__name__)

# SQL operations that modify data
DESTRUCTIVE_SQL_OPERATIONS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "MERGE",
}

# Tool names that map to each category
HTTP_TOOL_NAMES = {"http_request", "make_http_request", "http"}
DATABASE_TOOL_NAMES = {"database_query", "query_database", "sql_query", "db_query"}
FILE_WRITE_TOOL_NAMES = {"file_write", "write_file", "save_file"}


class ToolCallGuardrailEvaluator:
    """Evaluates tool calls against configured policies.

    Routes validation to the appropriate checker based on tool type:
    - HTTP tools → SSRF protection + URL pattern validation
    - Database tools → SQL operation + table restrictions
    - File write tools → path traversal + extension + size validation
    - All tools → tool call count limits
    """

    def evaluate(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        policy: ToolCallPolicy,
        tool_call_count: int = 0,
        tool_node_type: Optional[str] = None,
    ) -> GuardrailResult:
        """Evaluate a tool call against the tool call policy.

        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments passed to the tool
            policy: Tool call policy to enforce
            tool_call_count: Current cumulative tool call count for this execution
            tool_node_type: Optional node type (e.g. "HTTP_REQUEST") for more precise routing

        Returns:
            GuardrailResult with any violations found
        """
        violations: List[Violation] = []

        # Check tool call count limit
        if tool_call_count >= policy.max_tool_calls_per_execution:
            violations.append(
                Violation(
                    category="tool_call",
                    rule_name="max_tool_calls_exceeded",
                    severity="block",
                    message=(
                        f"Tool call limit exceeded "
                        f"({tool_call_count} >= {policy.max_tool_calls_per_execution})"
                    ),
                    details={
                        "tool_name": tool_name,
                        "current_count": tool_call_count,
                        "max_count": policy.max_tool_calls_per_execution,
                    },
                )
            )
            return GuardrailResult(
                passed=False, violations=violations, action_taken="blocked"
            )

        # Route to type-specific validation
        tool_name_lower = tool_name.lower()
        node_type_upper = (tool_node_type or "").upper()

        if node_type_upper == "HTTP_REQUEST" or tool_name_lower in HTTP_TOOL_NAMES:
            result = self._check_http_tool(tool_args, policy)
            if not result.passed:
                return result
            violations.extend(result.violations)

        elif (
            node_type_upper == "DATABASE_QUERY"
            or tool_name_lower in DATABASE_TOOL_NAMES
        ):
            result = self._check_database_tool(tool_args, policy)
            if not result.passed:
                return result
            violations.extend(result.violations)

        elif (
            node_type_upper == "FILE_WRITE" or tool_name_lower in FILE_WRITE_TOOL_NAMES
        ):
            result = self._check_file_write_tool(tool_args, policy)
            if not result.passed:
                return result
            violations.extend(result.violations)

        if violations:
            return GuardrailResult(
                passed=True, violations=violations, action_taken="warned"
            )

        return GuardrailResult(passed=True)

    def _check_http_tool(
        self, tool_args: Dict[str, Any], policy: ToolCallPolicy
    ) -> GuardrailResult:
        """Validate HTTP request tool arguments.

        Checks the URL against SSRF protections and URL pattern restrictions.
        """
        url = tool_args.get("url", "") or tool_args.get("url_template", "") or ""
        if not url:
            return GuardrailResult(passed=True)

        return validate_url(url, policy)

    def _check_database_tool(
        self, tool_args: Dict[str, Any], policy: ToolCallPolicy
    ) -> GuardrailResult:
        """Validate database query tool arguments.

        Checks SQL operations and table names against policy restrictions.
        """
        query = tool_args.get("query", "") or tool_args.get("sql", "") or ""
        if not query:
            return GuardrailResult(passed=True)

        violations: List[Violation] = []
        query_upper = query.strip().upper()

        # Check SQL operation type
        if policy.allowed_sql_operations:
            allowed_ops = {op.upper() for op in policy.allowed_sql_operations}
            # Extract the first SQL keyword
            first_word_match = re.match(r"^\s*(\w+)", query_upper)
            if first_word_match:
                operation = first_word_match.group(1)
                if operation not in allowed_ops:
                    violations.append(
                        Violation(
                            category="tool_call",
                            rule_name="sql_operation_blocked",
                            severity="block",
                            message=f"SQL operation '{operation}' is not allowed (allowed: {', '.join(sorted(allowed_ops))})",
                            details={
                                "operation": operation,
                                "allowed": list(allowed_ops),
                            },
                        )
                    )

        # Check blocked tables
        if policy.blocked_tables:
            for table in policy.blocked_tables:
                if table.upper() in query_upper:
                    violations.append(
                        Violation(
                            category="tool_call",
                            rule_name="sql_blocked_table",
                            severity="block",
                            message=f"Query references blocked table: {table}",
                            details={"table": table},
                        )
                    )

        if any(v.severity == "block" for v in violations):
            return GuardrailResult(
                passed=False, violations=violations, action_taken="blocked"
            )

        return GuardrailResult(passed=True, violations=violations)

    def _check_file_write_tool(
        self, tool_args: Dict[str, Any], policy: ToolCallPolicy
    ) -> GuardrailResult:
        """Validate file write tool arguments.

        Checks for path traversal, blocked paths, allowed extensions, and file size.
        """
        filename = tool_args.get("filename", "") or ""
        subdirectory = tool_args.get("subdirectory", "") or ""
        content = tool_args.get("content", "") or ""

        violations: List[Violation] = []

        # Check path traversal
        full_path = os.path.join(subdirectory, filename) if subdirectory else filename
        if ".." in full_path or full_path.startswith("/"):
            violations.append(
                Violation(
                    category="tool_call",
                    rule_name="file_path_traversal",
                    severity="block",
                    message=f"Path traversal detected in file path: {full_path}",
                    details={"filename": filename, "subdirectory": subdirectory},
                )
            )

        # Check blocked file paths
        if policy.blocked_file_paths:
            for blocked_path in policy.blocked_file_paths:
                if blocked_path in full_path:
                    violations.append(
                        Violation(
                            category="tool_call",
                            rule_name="file_path_blocked",
                            severity="block",
                            message=f"File path matches blocked pattern: {blocked_path}",
                            details={
                                "path": full_path,
                                "blocked_pattern": blocked_path,
                            },
                        )
                    )

        # Check allowed extensions
        if policy.allowed_file_extensions and filename:
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            allowed = [
                e.lower() if e.startswith(".") else f".{e.lower()}"
                for e in policy.allowed_file_extensions
            ]
            if ext not in allowed:
                violations.append(
                    Violation(
                        category="tool_call",
                        rule_name="file_extension_blocked",
                        severity="block",
                        message=f"File extension '{ext}' is not allowed (allowed: {', '.join(allowed)})",
                        details={"extension": ext, "allowed": allowed},
                    )
                )

        # Check file size
        content_size_mb = len(content.encode("utf-8", errors="ignore")) / (1024 * 1024)
        if content_size_mb > policy.max_file_size_mb:
            violations.append(
                Violation(
                    category="tool_call",
                    rule_name="file_size_exceeded",
                    severity="block",
                    message=f"File size ({content_size_mb:.2f} MB) exceeds limit ({policy.max_file_size_mb} MB)",
                    details={
                        "size_mb": content_size_mb,
                        "max_mb": policy.max_file_size_mb,
                    },
                )
            )

        if any(v.severity == "block" for v in violations):
            return GuardrailResult(
                passed=False, violations=violations, action_taken="blocked"
            )

        return GuardrailResult(passed=True, violations=violations)
