"""
Central tool registry for managing tool lifecycle and bindings.

This module provides the ToolRegistry class which manages tool metadata,
agent-tool bindings, and integrates with performance tracking.
"""

from typing import Any, Dict, List, Optional, Union

from langchain_core.tools import BaseTool

from ..config import get_logger
from .factory import ToolFactory
from .models import ToolBinding, ToolMetadata, ToolType
from .performance import PerformanceTracker


logger = get_logger("tool-registry")


class ToolRegistry:
    """
    Central registry for all tools in the system.

    Manages tool metadata, lifecycle, agent bindings, and integrates
    with performance tracking.
    """

    def __init__(self):
        """Initialize the tool registry."""
        self.factory = ToolFactory()
        self.performance_tracker = PerformanceTracker()

        self._registry: Dict[str, ToolMetadata] = {}
        self._bindings: Dict[str, List[ToolBinding]] = {}  # agent_id -> bindings

        self._initialize_default_tools()
        logger.info("[TOOL-REGISTRY] Initialized tool registry")

    def _initialize_default_tools(self) -> None:
        """Initialize registry with default tool metadata."""
        default_tools = [
            ToolMetadata(
                tool_id="web_search",
                name="Web Search",
                description="Search the web for information",
                tool_type=ToolType.WEB_SEARCH,
                cache_results=True,
            ),
            ToolMetadata(
                tool_id="arxiv",
                name="arXiv Search",
                description="Search academic papers on arXiv",
                tool_type=ToolType.WEB_SEARCH,
                cache_results=True,
                cache_ttl=3600,
            ),
            ToolMetadata(
                tool_id="wikipedia",
                name="Wikipedia Search",
                description="Search Wikipedia for information",
                tool_type=ToolType.WEB_SEARCH,
                cache_results=True,
                cache_ttl=3600,
            ),
            ToolMetadata(
                tool_id="database_query",
                name="Database Query",
                description="Query databases with SQL",
                tool_type=ToolType.DATABASE,
                requires_auth=True,
                auth_env_vars=["DATABASE_URL"],
            ),
            ToolMetadata(
                tool_id="calculator",
                name="Calculator",
                description="Perform mathematical calculations",
                tool_type=ToolType.CALCULATION,
                cache_results=False,
            ),
            ToolMetadata(
                tool_id="file_read",
                name="File Read",
                description="Read files from the filesystem",
                tool_type=ToolType.FILE_SYSTEM,
                requires_auth=False,
            ),
            ToolMetadata(
                tool_id="file_write",
                name="File Write",
                description="Write files to the filesystem",
                tool_type=ToolType.FILE_SYSTEM,
                requires_auth=False,
            ),
            ToolMetadata(
                tool_id="http_request",
                name="HTTP Request",
                description="Make HTTP requests to APIs",
                tool_type=ToolType.API_CALL,
                timeout=30,
                max_retries=3,
            ),
        ]

        for metadata in default_tools:
            self.register_tool(metadata)

        logger.info(f"[TOOL-REGISTRY] Registered {len(default_tools)} default tools")

    def register_tool(self, metadata: ToolMetadata) -> None:
        """
        Register a tool in the registry.

        Args:
            metadata: Tool metadata
        """
        self._registry[metadata.tool_id] = metadata
        logger.info(
            f"[TOOL-REGISTRY] Registered tool: {metadata.tool_id} ({metadata.name})"
        )

    def get_tool_metadata(self, tool_id: str) -> Optional[ToolMetadata]:
        """
        Get metadata for a tool.

        Args:
            tool_id: Tool identifier

        Returns:
            Tool metadata or None if not found
        """
        return self._registry.get(tool_id)

    def bind_tools_for_agent(
        self,
        agent_id: str,
        agent_name: str,
        tool_configs: List[Union[str, Any]],
        agent_config: Optional[Any] = None,
    ) -> List[ToolBinding]:
        """
        Bind tools to an agent at compile time.

        Args:
            agent_id: Agent identifier
            agent_name: Agent display name
            tool_configs: List of tool names or ToolConfig objects
            agent_config: Optional agent configuration for context

        Returns:
            List of tool bindings
        """
        bindings = []

        for tool_config in tool_configs:
            # Handle string tool names vs ToolConfig objects
            if isinstance(tool_config, str):
                tool_name = tool_config
                config = {}
            else:
                # Handle ToolConfig objects
                tool_name = (
                    tool_config.name
                    if hasattr(tool_config, "name")
                    else str(tool_config)
                )
                config = tool_config.config if hasattr(tool_config, "config") else {}

            # Create tool instance
            tool_instance = self.factory.create_tool(tool_name, config)
            if not tool_instance:
                logger.warning(
                    f"[TOOL-REGISTRY] Failed to create tool '{tool_name}' for agent '{agent_name}'"
                )
                continue

            # Get or create metadata
            metadata = self._registry.get(tool_name)
            if not metadata:
                metadata = ToolMetadata(
                    tool_id=tool_name,
                    name=tool_name,
                    description=getattr(tool_instance, "description", ""),
                    tool_type=ToolType.CUSTOM,
                )
                self.register_tool(metadata)

            # Create binding
            binding = ToolBinding(
                agent_id=agent_id,
                agent_name=agent_name,
                tool_id=tool_name,
                tool_instance=tool_instance,
                metadata=metadata,
            )

            bindings.append(binding)

            # Store binding
            if agent_id not in self._bindings:
                self._bindings[agent_id] = []
            self._bindings[agent_id].append(binding)

            logger.info(
                f"[TOOL-REGISTRY] Bound tool '{tool_name}' to agent '{agent_name}'"
            )

        return bindings

    def get_agent_tools(self, agent_id: str) -> List[BaseTool]:
        """
        Get tool instances for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of tool instances
        """
        bindings = self._bindings.get(agent_id, [])
        return [binding.tool_instance for binding in bindings]

    def get_agent_bindings(self, agent_id: str) -> List[ToolBinding]:
        """
        Get all bindings for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of tool bindings
        """
        return self._bindings.get(agent_id, [])

    def track_tool_execution(
        self, agent_id: str, tool_id: str, execution_time: float, success: bool = True
    ) -> None:
        """
        Track tool execution for performance monitoring.

        Args:
            agent_id: Agent that executed the tool
            tool_id: Tool that was executed
            execution_time: Time taken in seconds
            success: Whether execution succeeded
        """
        # Find the binding and update it
        if agent_id in self._bindings:
            for binding in self._bindings[agent_id]:
                if binding.tool_id == tool_id:
                    self.performance_tracker.update_binding_stats(
                        binding, execution_time, success
                    )
                    break

    def get_performance_stats(self, tool_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics for tools.

        Args:
            tool_id: Optional specific tool ID

        Returns:
            Performance statistics
        """
        if tool_id:
            return self.performance_tracker.get_tool_stats(tool_id) or {}
        return self.performance_tracker.get_all_stats()

    def optimize_bindings(self, agent_id: str) -> None:
        """
        Optimize tool bindings based on usage patterns.

        Reorders tools by execution frequency for better performance.

        Args:
            agent_id: Agent to optimize
        """
        if agent_id not in self._bindings:
            return

        # Sort bindings by execution count (most used first)
        self._bindings[agent_id].sort(key=lambda b: b.execution_count, reverse=True)

        logger.info(f"[TOOL-REGISTRY] Optimized tool bindings for agent '{agent_id}'")

    def clear_bindings(self, agent_id: Optional[str] = None) -> None:
        """
        Clear tool bindings.

        Args:
            agent_id: Optional specific agent to clear (clears all if None)
        """
        if agent_id:
            if agent_id in self._bindings:
                del self._bindings[agent_id]
                logger.info(f"[TOOL-REGISTRY] Cleared bindings for agent '{agent_id}'")
        else:
            self._bindings.clear()
            logger.info("[TOOL-REGISTRY] Cleared all tool bindings")

    def export_bindings(self) -> Dict[str, Any]:
        """
        Export all bindings for persistence.

        Returns:
            Dictionary of all bindings
        """
        export_data = {}
        for agent_id, bindings in self._bindings.items():
            export_data[agent_id] = [binding.to_dict() for binding in bindings]
        return export_data

    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get overall registry statistics.

        Returns:
            Dictionary of registry statistics
        """
        total_tools = len(self._registry)
        total_bindings = sum(len(bindings) for bindings in self._bindings.values())
        total_executions = sum(
            binding.execution_count
            for bindings in self._bindings.values()
            for binding in bindings
        )

        cache_stats = self.factory.get_cache_stats()

        return {
            "total_tools": total_tools,
            "total_bindings": total_bindings,
            "total_agents": len(self._bindings),
            "total_executions": total_executions,
            "cache_stats": cache_stats,
            "performance_summary": self.performance_tracker.get_summary(),
        }


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
        logger.info("[TOOL-REGISTRY] Initialized global tool registry")
    return _global_registry


def reset_tool_registry() -> None:
    """Reset the global tool registry."""
    global _global_registry
    if _global_registry:
        _global_registry.factory.clear_cache()
        _global_registry.clear_bindings()
    _global_registry = None
    logger.info("[TOOL-REGISTRY] Reset global tool registry")
