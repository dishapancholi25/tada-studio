"""Context building for agent execution.

This module handles building system prompts with MCP context, citation instructions,
and other context enhancements.
"""

import logging
from typing import Any, Dict, Optional

from backend.models.workflow import (
    ConnectionType,
    EnhancedNodeData,
    GraphData,
    NodeType,
)
from .prompt_variables import replace_prompt_variables


logger = logging.getLogger("mcp_context")


class ContextBuilder:
    """Builds execution context for agents."""

    @staticmethod
    def build_system_prompt(
        agent_node: EnhancedNodeData,
        graph: Optional[GraphData] = None,
    ) -> str:
        """Build enhanced system prompt with context additions.

        Args:
            agent_node: The agent node
            graph: Optional graph containing the agent (for MCP context)

        Returns:
            Enhanced system prompt string
        """
        if not agent_node.agent_config:
            return ""

        system_prompt = agent_node.agent_config.system_prompt

        # Replace template variables ({{$today}}, {{$now}})
        system_prompt = replace_prompt_variables(system_prompt)

        # Add citation instructions if document search is enabled
        if (
            agent_node.agent_config.document_search_enabled
            and agent_node.agent_config.citation_format != "none"
        ):
            citation_instruction = (
                "\n\nIMPORTANT: When using information from document search "
                "results, always preserve and include the citations exactly as "
                "provided. Citations are formatted in square brackets and must be "
                "included in your response to show the source of information."
            )
            system_prompt = system_prompt + citation_instruction
            logger.info("Added citation preservation instruction to system prompt")

        # Add MCP server context if available
        if graph:
            mcp_context = ContextBuilder.get_mcp_context(agent_node, graph)
            if mcp_context:
                system_prompt = system_prompt + "\n\n" + mcp_context
                logger.info("Added MCP server context to system prompt")

        return system_prompt

    @staticmethod
    def get_mcp_context(
        agent_node: EnhancedNodeData,
        graph: GraphData,
    ) -> Optional[str]:
        """Get MCP server context information for an agent.

        Args:
            agent_node: The agent node to get MCP context for
            graph: The graph containing the agent and MCP servers

        Returns:
            Formatted string with MCP server context, or None if no MCP servers
        """
        try:
            mcp_contexts = []

            # Find all MCP server connections from this agent
            for connection in graph.connections:
                if (
                    connection.source_id == agent_node.uniq_id
                    and connection.connection_type == ConnectionType.TOOL
                ):
                    target_node = graph.get_node_by_id(connection.target_id)
                    if (
                        target_node
                        and target_node.type == NodeType.MCP_SERVER
                        and target_node.mcp_server_config
                    ):
                        logger.info(
                            f"Found connected MCP server for context: {target_node.name}"
                        )

                        mcp_config = target_node.mcp_server_config

                        # Extract configuration details
                        server_info = _extract_mcp_server_info(mcp_config)
                        context_parts = _build_mcp_context_parts(server_info)
                        mcp_contexts.append("\n".join(context_parts))

            # Format the final context message
            if mcp_contexts:
                context_message = (
                    "MCP SERVER CONTEXT:\n"
                    "You have access to the following MCP (Model Context Protocol) "
                    "servers through your tools:\n\n"
                )
                for i, context in enumerate(mcp_contexts, 1):
                    context_message += f"{i}. {context}\n\n"

                context_message += (
                    "Use the 'discover' action first if you need to see available "
                    "tools. Then use 'tool_call' with the appropriate tool name and "
                    "arguments."
                )

                logger.info(f"Generated MCP context for {len(mcp_contexts)} server(s)")
                return context_message

            return None

        except Exception as e:
            logger.error(f"Error generating MCP context: {str(e)}", exc_info=True)
            return None


def _extract_mcp_server_info(mcp_config) -> Dict[str, Any]:
    """Extract server information from MCP config.

    Args:
        mcp_config: MCP server configuration (dict or object)

    Returns:
        Dictionary with server info fields
    """
    if isinstance(mcp_config, dict):
        return {
            "server_name": mcp_config.get("server_name", "MCP Server"),
            "connection_type": mcp_config.get("connection_type", "stdio"),
            "command": mcp_config.get("command", ""),
            "args": mcp_config.get("args", []),
            "working_directory": mcp_config.get("working_directory", ""),
            "metadata": mcp_config.get("metadata", {}),
            "environment_variables": mcp_config.get("environment_variables", {}),
        }
    else:
        return {
            "server_name": mcp_config.server_name,
            "connection_type": mcp_config.connection_type,
            "command": mcp_config.command,
            "args": mcp_config.args,
            "working_directory": mcp_config.working_directory,
            "metadata": getattr(mcp_config, "metadata", {}),
            "environment_variables": getattr(mcp_config, "environment_variables", {}),
        }


def _build_mcp_context_parts(server_info: Dict[str, str]) -> list:
    """Build context description for an MCP server.

    Args:
        server_info: Dictionary with server information

    Returns:
        List of context description strings
    """
    context_parts = [f"**{server_info['server_name']}**"]

    # For filesystem servers, provide detailed path information
    if (
        "filesystem" in server_info["command"].lower()
        or "filesystem" in str(server_info["args"]).lower()
    ):
        allowed_dir = None
        if server_info["args"]:
            # The last argument is typically the allowed directory
            allowed_dir = (
                server_info["args"][-1]
                if isinstance(server_info["args"], list)
                else server_info["working_directory"]
            )

        if allowed_dir:
            context_parts.append("   - Type: File System Server")
            context_parts.append(f"   - Allowed directory: {allowed_dir}")
            context_parts.append(
                "   - **IMPORTANT**: When accessing files, always use the full "
                "path within the allowed directory"
            )
            context_parts.append(
                f"   - Example: To read a file 'example.txt', use path: "
                f"{allowed_dir}\\example.txt"
            )
            context_parts.append(
                "   - Available operations: read_file, read_text_file, write_file, "
                "list_directory, create_directory, etc."
            )
    elif _is_sharepoint_server(server_info):
        context_parts.extend(_build_sharepoint_context(server_info))
    elif _is_onedrive_server(server_info):
        context_parts.extend(_build_onedrive_context())
    else:
        # Generic MCP server
        context_parts.append(
            f"   - Type: {server_info['connection_type'].upper()} Server"
        )
        if server_info["working_directory"]:
            context_parts.append(
                f"   - Working directory: {server_info['working_directory']}"
            )

    return context_parts


def _is_sharepoint_server(server_info: Dict[str, str]) -> bool:
    """Check if the MCP server is a SharePoint server."""
    name = server_info.get("server_name", "").lower()
    args = str(server_info.get("args", [])).lower()
    return "sharepoint" in name or "sharepoint_mcp" in args


def _build_sharepoint_context(server_info: Dict[str, Any]) -> list:
    """Build SharePoint-specific agent guidance.

    Provides the agent with strategic context on how to use SharePoint
    search tools effectively for business knowledge discovery.
    When scope metadata is available, includes specific scope constraints.
    """
    parts = ["   - Type: SharePoint Document & Knowledge Server"]

    # Add scope context when metadata is available
    metadata = server_info.get("metadata", {}) or {}
    env_vars = server_info.get("environment_variables", {}) or {}

    site_name = metadata.get("site_name", "")
    drive_names = metadata.get("drive_names", "")
    folder_paths = metadata.get("folder_paths", "")
    has_site_scope = bool(env_vars.get("SHAREPOINT_SITE_ID") or metadata.get("site_id"))
    has_drive_scope = bool(
        env_vars.get("SHAREPOINT_DRIVE_IDS") or metadata.get("drive_ids")
    )

    if has_site_scope or has_drive_scope:
        parts.append("")
        parts.append("   **SCOPE CONFIGURATION:**")
        if site_name:
            parts.append(
                f'   - This SharePoint connection is scoped to site: "{site_name}"'
            )
        if drive_names:
            parts.append(f'   - Document library: "{drive_names}"')
        if folder_paths:
            parts.append(f'   - Folder paths: "{folder_paths}"')
        parts.append(
            "   - **IMPORTANT**: All search results are automatically filtered to the "
            "configured library. You do NOT need to call `list_sites` to discover sites. "
            "Use default (empty) values for site_id and drive_id parameters "
            "unless the user explicitly asks to search a different location."
        )

    parts.extend(
        [
            "",
            "   **Search Strategy Guide:**",
            "   - Use `search_files` for finding documents (Word, PowerPoint, Excel, PDF).",
            "   - Use `search_content` for broad knowledge discovery across files, "
            "list items, and site pages — ideal for questions like "
            '"What do we know about Client X?"',
            "   - Use `list_drive_items` only for browsing a known folder path.",
            "",
            "   **Effective Search Tips:**",
            "   - Start broad, then narrow using filters. Review the `snippet` field "
            "in results to understand relevance before downloading files.",
            "   - Use `file_types` to filter by document type "
            '(e.g., "pptx,docx" for proposals, "xlsx" for data).',
            "   - Use `date_from`/`date_to` for time-scoped queries "
            '(e.g., "What have we done this year?").',
            "   - Use `author` to find work by a specific person.",
            '   - Use `sort_by` with "lastModifiedDateTime desc" to see '
            "most recent results first.",
            "   - Check the `facets` in results — they show breakdowns by file type "
            "and date that help you suggest ways to narrow the search.",
            "",
            "   **Recommended Workflow:**",
            "   1. Search with `search_files` or `search_content` using filters",
            "   2. Review `snippet` highlights and `facets` in results",
            "   3. Suggest narrowing filters to the user if results are broad",
            "   4. Use `get_file_content` only on the most relevant results",
        ]
    )

    if not (has_site_scope or has_drive_scope):
        parts.append(
            "   5. If the user asks about a specific site, use `list_sites` first "
            "to get the site_id, then scope searches with it"
        )

    return parts


def _is_onedrive_server(server_info: Dict[str, str]) -> bool:
    """Check if the MCP server is a OneDrive server."""
    name = server_info.get("server_name", "").lower()
    args = str(server_info.get("args", [])).lower()
    return "onedrive" in name or "onedrive_mcp" in args


def _build_onedrive_context() -> list:
    """Build OneDrive-specific agent guidance."""
    return [
        "   - Type: OneDrive File Storage Server",
        "",
        "   **Search Strategy Guide:**",
        "   - Use `search_files` for broad, filtered searches across OneDrive "
        "(supports KQL, file type/author/date filters, pagination, and snippets).",
        "   - Use `find_file_or_folder` for quick name lookups in the user's "
        "personal drive.",
        "   - Use `list_drive_items` only for browsing a known folder path.",
        "",
        "   **Effective Search Tips:**",
        "   - Start broad, then narrow using filters. Review the `snippet` field "
        "in results to understand relevance before downloading files.",
        "   - Use `file_types` to filter by document type "
        '(e.g., "pptx,docx" for proposals, "xlsx" for data).',
        "   - Use `date_from`/`date_to` for time-scoped queries.",
        "   - Use `author` to find work by a specific person.",
        '   - Use `sort_by` with "lastModifiedDateTime desc" to see '
        "most recent results first.",
        "   - Check the `facets` in results — they show breakdowns by file type "
        "and date that help you suggest ways to narrow the search.",
        "",
        "   **Recommended Workflow:**",
        "   1. Search with `search_files` using filters",
        "   2. Review `snippet` highlights and `facets` in results",
        "   3. Suggest narrowing filters to the user if results are broad",
        "   4. Use `get_file_content` only on the most relevant results",
    ]
