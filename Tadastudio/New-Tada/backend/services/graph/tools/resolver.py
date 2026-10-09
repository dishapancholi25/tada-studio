"""
Tool Resolver.

Resolves tool nodes from tool executions.
"""

from typing import Any, Dict, Optional

from backend.models.workflow import EnhancedNodeData, GraphData, NodeType
from backend.services.config import get_logger
from backend.services.graph.agent_tools.utils import sanitize_tool_name


tool_resolver_logger = get_logger("graph.tools.resolver")


class ToolResolver:
    """
    Resolves tool nodes from tool executions.

    Finds the corresponding tool node for a given tool execution by:
    - Execution hints (node_id in tool_exec)
    - Tool name patterns (with embedded node IDs)
    - Type-based matching (connected tool nodes)
    """

    # Map common tool names to node types
    TOOL_TYPE_MAP = {
        "search_documents": NodeType.DOCUMENT_SEARCH,
        "query_database": NodeType.DATABASE_QUERY,
        "http_request": NodeType.HTTP_REQUEST,
        "web_search": NodeType.WEB_SEARCH,
        "mcp_server": NodeType.MCP_SERVER,
    }

    # Map tool name prefixes to node types (for semantic naming)
    TOOL_PREFIX_MAP = {
        "document_search_": NodeType.DOCUMENT_SEARCH,
        "database_query_": NodeType.DATABASE_QUERY,
        "http_request_": NodeType.HTTP_REQUEST,
        "web_search_": NodeType.WEB_SEARCH,
        "mcp_server_": NodeType.MCP_SERVER,
    }

    @staticmethod
    def find_tool_node(
        graph: GraphData,
        agent_node_id: str,
        tool_name: str,
        tool_exec: Optional[Dict[str, Any]] = None,
    ) -> Optional[EnhancedNodeData]:
        """
        Find the tool node that corresponds to a tool execution.

        Args:
            graph: The workflow graph
            agent_node_id: ID of the agent that executed the tool
            tool_name: Name of the tool that was executed
            tool_exec: Optional tool execution data with hints

        Returns:
            The corresponding tool node if found, None otherwise
        """
        # Try execution hint first
        tool_node = ToolResolver._find_by_execution_hint(graph, tool_exec, tool_name)
        if tool_node:
            return tool_node

        # Try pattern-based resolution
        tool_node = ToolResolver._find_by_tool_name_pattern(graph, tool_name)
        if tool_node:
            return tool_node

        # Fall back to type-based matching
        return ToolResolver._find_by_type(graph, agent_node_id, tool_name)

    @staticmethod
    def _find_by_execution_hint(
        graph: GraphData, tool_exec: Optional[Dict[str, Any]], tool_name: str
    ) -> Optional[EnhancedNodeData]:
        """
        Find tool node using execution hint.

        Args:
            graph: The workflow graph
            tool_exec: Tool execution data
            tool_name: Name of the tool

        Returns:
            Tool node if found via hint, None otherwise
        """
        if not tool_exec:
            return None

        hinted_node_id = tool_exec.get("node_id")
        if not hinted_node_id:
            return None

        target_node = next(
            (n for n in graph.nodes if n.uniq_id == hinted_node_id), None
        )
        if target_node:
            tool_resolver_logger.info(
                f"Found tool node via execution hint: {target_node.name} "
                f"({target_node.uniq_id}) for tool {tool_name}"
            )
        return target_node

    @staticmethod
    def _find_by_tool_name_pattern(
        graph: GraphData, tool_name: str
    ) -> Optional[EnhancedNodeData]:
        """
        Find tool node by analyzing tool name patterns.

        Supports both legacy ID-based naming and semantic naming:
        - Legacy: document_search_f70424aa (ID prefix)
        - Semantic: document_search_amex_fraud_hub_api (sanitized name)

        Args:
            graph: The workflow graph
            tool_name: Name of the tool

        Returns:
            Tool node if found by pattern, None otherwise
        """
        # HTTP Request pattern: http_request_{suffix}
        if tool_name.startswith("http_request_") and len(tool_name) > 13:
            suffix = tool_name[13:]  # Remove "http_request_"
            # First try exact ID match, then fall back to suffix matching
            result = ToolResolver._find_by_exact_id(
                graph, suffix, "HTTP request", tool_name
            )
            if result:
                return result
            return ToolResolver._find_by_suffix(
                graph, suffix, "HTTP request", tool_name, NodeType.HTTP_REQUEST
            )

        # Database Query pattern: database_query_{suffix} (new) or query_db_{suffix} (legacy)
        elif tool_name.startswith("database_query_") and len(tool_name) > 15:
            suffix = tool_name[15:]  # Remove "database_query_"
            return ToolResolver._find_by_suffix(
                graph, suffix, "database query", tool_name, NodeType.DATABASE_QUERY
            )
        elif tool_name.startswith("query_db_") and len(tool_name) > 9:
            suffix = tool_name[9:]  # Remove "query_db_"
            return ToolResolver._find_by_suffix(
                graph, suffix, "database query", tool_name, NodeType.DATABASE_QUERY
            )

        # Web Search pattern: web_search_{suffix}
        elif tool_name.startswith("web_search_") and len(tool_name) > 11:
            suffix = tool_name[11:]  # Remove "web_search_"
            return ToolResolver._find_by_suffix(
                graph, suffix, "web search", tool_name, NodeType.WEB_SEARCH
            )

        # Document Search pattern: document_search_{suffix}
        elif tool_name.startswith("document_search_") and len(tool_name) > 16:
            suffix = tool_name[16:]  # Remove "document_search_"
            return ToolResolver._find_by_suffix(
                graph, suffix, "document search", tool_name, NodeType.DOCUMENT_SEARCH
            )

        # MCP Server pattern: mcp_server_{node_id}
        elif tool_name.startswith("mcp_server_") and len(tool_name) > 11:
            return ToolResolver._find_by_exact_id(
                graph, tool_name[11:], "MCP server", tool_name
            )

        return None

    @staticmethod
    def _find_by_exact_id(
        graph: GraphData, node_id: str, node_type_desc: str, tool_name: str
    ) -> Optional[EnhancedNodeData]:
        """
        Find tool node by exact node ID.

        Args:
            graph: The workflow graph
            node_id: The node ID
            node_type_desc: Description of node type for logging
            tool_name: Name of the tool

        Returns:
            Tool node if found, None otherwise
        """
        tool_resolver_logger.info(
            f"Extracted node ID from {node_type_desc} tool: {node_id}"
        )

        target_node = next((n for n in graph.nodes if n.uniq_id == node_id), None)

        if target_node:
            tool_resolver_logger.info(
                f"Found exact {node_type_desc} node by ID: "
                f"{target_node.name} ({target_node.uniq_id}) "
                f"for tool execution: {tool_name}"
            )
        else:
            tool_resolver_logger.warning(
                f"No node found with ID {node_id} extracted from tool {tool_name}"
            )

        return target_node

    @staticmethod
    def _find_by_suffix(
        graph: GraphData,
        suffix: str,
        node_type_desc: str,
        tool_name: str,
        expected_type: NodeType = None,
    ) -> Optional[EnhancedNodeData]:
        """
        Find tool node by suffix (either node ID prefix or sanitized node name).

        Tries multiple resolution strategies:
        1. Match by node ID prefix (backward compatibility)
        2. Match by sanitized node name (semantic naming)

        Args:
            graph: The workflow graph
            suffix: The suffix extracted from tool name (ID prefix or sanitized name)
            node_type_desc: Description of node type for logging
            tool_name: Name of the tool
            expected_type: Optional expected NodeType to filter candidates

        Returns:
            Tool node if found, None otherwise
        """
        tool_resolver_logger.info(
            f"Resolving {node_type_desc} tool with suffix: {suffix}"
        )

        # Strategy 1: Try to match by node ID prefix
        target_node = next(
            (n for n in graph.nodes if n.uniq_id.startswith(suffix)), None
        )

        if target_node:
            tool_resolver_logger.info(
                f"Found {node_type_desc} node by ID prefix: "
                f"{target_node.name} ({target_node.uniq_id}) "
                f"for tool execution: {tool_name}"
            )
            return target_node

        # Strategy 2: Try to match by sanitized node name
        for node in graph.nodes:
            # Filter by expected type if provided
            if expected_type and node.type != expected_type:
                continue

            # Compare sanitized node name with suffix
            if node.name and sanitize_tool_name(node.name) == suffix:
                tool_resolver_logger.info(
                    f"Found {node_type_desc} node by name match: "
                    f"{node.name} ({node.uniq_id}) "
                    f"for tool execution: {tool_name}"
                )
                return node

        tool_resolver_logger.warning(
            f"No {node_type_desc} node found with suffix '{suffix}' "
            f"extracted from tool {tool_name}"
        )

        return None

    @staticmethod
    def _find_by_type(
        graph: GraphData, agent_node_id: str, tool_name: str
    ) -> Optional[EnhancedNodeData]:
        """
        Find tool node by type-based matching.

        Args:
            graph: The workflow graph
            agent_node_id: ID of the agent node
            tool_name: Name of the tool

        Returns:
            Tool node if found, None otherwise
        """
        # Determine expected type from exact match first
        expected_type = ToolResolver.TOOL_TYPE_MAP.get(tool_name)

        # If no exact match, try prefix-based matching
        if not expected_type:
            for prefix, node_type in ToolResolver.TOOL_PREFIX_MAP.items():
                if tool_name.startswith(prefix):
                    expected_type = node_type
                    break

        if not expected_type:
            tool_resolver_logger.debug(f"No node type mapping for tool: {tool_name}")
            return None

        # Find connected tool nodes of the expected type
        for conn in graph.connections:
            if conn.source_id == agent_node_id and conn.connection_type == "tool":
                # Find the target node
                target_node = next(
                    (n for n in graph.nodes if n.uniq_id == conn.target_id), None
                )
                if target_node and target_node.type == expected_type:
                    tool_resolver_logger.info(
                        f"Found tool node by type: {target_node.name} "
                        f"({target_node.uniq_id}) for tool execution: {tool_name}"
                    )
                    return target_node

        tool_resolver_logger.debug(
            f"No tool node found for {tool_name} connected to agent {agent_node_id}"
        )
        return None
