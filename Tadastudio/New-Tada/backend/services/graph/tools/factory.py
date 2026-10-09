"""
Tool Node Factory.

Creates native LangGraph ToolNodes for tool nodes.
"""

import os

from langgraph.prebuilt import ToolNode
from backend.models.workflow import EnhancedNodeData, GraphData, NodeType
from backend.services.config import get_logger


tool_factory_logger = get_logger("graph.tools.factory")


class ToolNodeFactory:
    """
    Factory for creating native LangGraph ToolNodes.

    Supports:
    - WEB_SEARCH
    - DOCUMENT_SEARCH
    - DATABASE_QUERY
    - HTTP_REQUEST
    - MCP_SERVER
    """

    @staticmethod
    def should_use_native_tool_nodes() -> bool:
        """
        Check if native ToolNode integration should be used.

        Returns:
            True if native tool nodes are enabled
        """
        # Native tool nodes are now enabled by default (Phase 4)
        return os.getenv("ENABLE_NATIVE_TOOL_NODES", "true").lower() == "true"

    @staticmethod
    def create_tool_node(node: EnhancedNodeData, graph: GraphData):
        """
        Create a native LangGraph ToolNode for a tool node.

        Args:
            node: The tool node definition
            graph: The complete graph

        Returns:
            A ToolNode instance or None if not supported
        """
        try:
            if node.type == NodeType.WEB_SEARCH:
                return ToolNodeFactory._create_web_search_tool_node(node)
            elif node.type == NodeType.DOCUMENT_SEARCH:
                return ToolNodeFactory._create_document_search_tool_node(node)
            elif node.type == NodeType.DATABASE_QUERY:
                return ToolNodeFactory._create_database_query_tool_node(node)
            elif node.type == NodeType.HTTP_REQUEST:
                return ToolNodeFactory._create_http_request_tool_node(node)
            elif node.type == NodeType.MCP_SERVER:
                return ToolNodeFactory._create_mcp_tool_node(node)
            else:
                tool_factory_logger.warning(
                    f"No ToolNode implementation for type: {node.type}"
                )
                return None

        except ImportError as e:
            tool_factory_logger.error(f"Failed to import tool for {node.type}: {e}")
            return None
        except Exception as e:
            tool_factory_logger.error(f"Failed to create ToolNode for {node.name}: {e}")
            return None

    @staticmethod
    def _create_web_search_tool_node(node: EnhancedNodeData):
        """Create web search tool node."""
        from backend.tools.web_search import create_web_search_tool

        tool = create_web_search_tool(node.uniq_id)
        return ToolNode([tool])

    @staticmethod
    def _create_document_search_tool_node(node: EnhancedNodeData):
        """Create document search tool node."""
        from backend.tools.document_search import create_document_search_tool

        # Extract configuration from node
        config = node.document_search_config or {}

        # Handle both dict and object configs
        if isinstance(config, dict):
            collection_names = config.get("document_collections", [])
            document_ids = config.get("document_ids", [])
            search_k = config.get("search_k", 6)
            search_type = config.get("search_type", "similarity")
            similarity_threshold = config.get("similarity_threshold", 0.5)
            include_metadata = config.get("include_metadata", True)
            citation_format = config.get("citation_format", "structured")
            hybrid_search_enabled = config.get("hybrid_search_enabled", True)
            search_mode = config.get("search_mode", "hybrid")
            keyword_weight = config.get("keyword_weight", 0.5)
            rrf_k = config.get("rrf_k", 60)
            text_config = config.get("full_text_config", "english")
            return_full_document = config.get("return_full_document", False)
        else:
            collection_names = getattr(config, "document_collections", [])
            document_ids = getattr(config, "document_ids", [])
            search_k = getattr(config, "search_k", 6)
            search_type = getattr(config, "search_type", "similarity")
            similarity_threshold = getattr(config, "similarity_threshold", 0.5)
            include_metadata = getattr(config, "include_metadata", True)
            citation_format = getattr(config, "citation_format", "structured")
            hybrid_search_enabled = getattr(config, "hybrid_search_enabled", True)
            search_mode = getattr(config, "search_mode", "hybrid")
            keyword_weight = getattr(config, "keyword_weight", 0.5)
            rrf_k = getattr(config, "rrf_k", 60)
            text_config = getattr(config, "full_text_config", "english")
            return_full_document = getattr(config, "return_full_document", False)

        tool = create_document_search_tool(
            collection_names=collection_names,
            document_ids=document_ids,
            search_k=search_k,
            search_type=search_type,
            similarity_threshold=similarity_threshold,
            include_metadata=include_metadata,
            citation_format=citation_format,
            hybrid_search_enabled=hybrid_search_enabled,
            search_mode=search_mode,
            keyword_weight=keyword_weight,
            rrf_k=rrf_k,
            text_config=text_config,
            return_full_document=return_full_document,
        )
        return ToolNode([tool])

    @staticmethod
    def _create_database_query_tool_node(node: EnhancedNodeData):
        """Create database query tool node."""
        from backend.services.graph.agent_tools.creators.database_query import (
            create_database_query_tool_from_node,
        )

        tool = create_database_query_tool_from_node(node)
        if tool is None:
            return None
        return ToolNode([tool])

    @staticmethod
    def _create_http_request_tool_node(node: EnhancedNodeData):
        """Create HTTP request tool node."""
        from backend.tools.http_request import create_http_request_tool

        tool = create_http_request_tool(node.uniq_id)
        return ToolNode([tool])

    @staticmethod
    def _create_mcp_tool_node(node: EnhancedNodeData):
        """Create MCP server tool node."""
        mcp_config = getattr(node, "mcp_server_config", {}) or {}

        # Convert config to dict
        config_dict = ToolNodeFactory._parse_mcp_config(mcp_config)

        # Check if this is an OAuth-configured MCP server
        # OAuth servers require user_id which isn't available at graph build time.
        # Skip native tool loading here - it will happen during agent execution.
        auth_type = config_dict.get("auth_type", "none")
        if auth_type == "oauth":
            tool_factory_logger.info(
                f"[MCP] Skipping graph-time tool discovery for OAuth MCP server: "
                f"{node.name} (tools will be loaded during agent execution)"
            )
            return None

        config_dict.setdefault("node_id", node.uniq_id)
        config_dict.setdefault("node_name", node.name)

        # Try native MCP tools first
        native_tools = ToolNodeFactory._try_native_mcp_tools(config_dict, node.name)
        if native_tools:
            return ToolNode(native_tools)

        # Fall back to adapter tool
        return ToolNodeFactory._try_mcp_adapter_tool(config_dict, node.name)

    @staticmethod
    def _parse_mcp_config(mcp_config) -> dict:
        """
        Parse MCP configuration to dictionary.

        Args:
            mcp_config: MCP configuration (dict or dataclass)

        Returns:
            Configuration dictionary
        """
        if isinstance(mcp_config, dict):
            return dict(mcp_config)
        elif hasattr(mcp_config, "dict"):
            return dict(mcp_config.dict())
        else:
            # Extract attributes from dataclass
            return {
                "server_name": getattr(mcp_config, "server_name", "MCP Server"),
                "connection_type": getattr(mcp_config, "connection_type", "stdio"),
                "server_url": getattr(mcp_config, "server_url", ""),
                "command": getattr(mcp_config, "command", ""),
                "args": getattr(mcp_config, "args", []),
                "working_directory": getattr(mcp_config, "working_directory", ""),
                "environment_variables": getattr(
                    mcp_config, "environment_variables", {}
                ),
                "auth_type": getattr(mcp_config, "auth_type", "none"),
                "auth_config": getattr(mcp_config, "auth_config", {}),
                "timeout_seconds": getattr(mcp_config, "timeout_seconds", 30),
                "max_retries": getattr(mcp_config, "max_retries", 3),
                "retry_delay": getattr(mcp_config, "retry_delay", 1.0),
                "capabilities_filter": getattr(mcp_config, "capabilities_filter", []),
                "resource_access": getattr(mcp_config, "resource_access", {}),
                "tool_permissions": getattr(mcp_config, "tool_permissions", {}),
            }

    @staticmethod
    def _try_native_mcp_tools(config_dict: dict, node_name: str):
        """
        Try to create native MCP tools.

        Args:
            config_dict: MCP configuration
            node_name: Name of the node

        Returns:
            List of tools or None
        """
        try:
            from backend.tools.mcp_config_utils import prepare_mcp_config_for_execution
            from backend.tools.mcp_native_tools import create_mcp_native_tools

            config_dict = prepare_mcp_config_for_execution(
                config_dict,
                node_id=config_dict.get("node_id"),
                node_name=node_name,
                logger=tool_factory_logger,
            )

            native_tools = create_mcp_native_tools(**config_dict)
            if not isinstance(native_tools, list):
                native_tools = list(native_tools)

            if native_tools:
                return native_tools
            else:
                tool_factory_logger.warning(
                    f"No tools discovered for MCP server node {node_name} "
                    f"using native loader"
                )
                return None

        except ImportError:
            tool_factory_logger.warning(
                f"mcp_native_tools module unavailable; "
                f"falling back to adapter for {node_name}"
            )
            return None
        except Exception as exc:
            tool_factory_logger.error(
                f"Failed to create native MCP tools for {node_name}: {exc}"
            )
            return None

    @staticmethod
    def _try_mcp_adapter_tool(config_dict: dict, node_name: str):
        """
        Try to create MCP adapter tool.

        Args:
            config_dict: MCP configuration
            node_name: Name of the node

        Returns:
            ToolNode or None
        """
        try:
            from backend.tools.mcp_adapter_tool import create_mcp_adapter_tool

            adapter_tool = create_mcp_adapter_tool(**config_dict)
            return ToolNode([adapter_tool])
        except Exception as exc:
            tool_factory_logger.error(
                f"Failed to create MCP adapter tool for {node_name}: {exc}"
            )
            return None
