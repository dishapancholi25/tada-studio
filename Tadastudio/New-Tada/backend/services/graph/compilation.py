"""Graph compilation services.

This module provides compile-time tool binding and agent compilation services,
allowing graphs to be pre-compiled with their tool bindings for improved performance.

Example:
    >>> from backend.services.graph.compilation import CompilationService
    >>> compiler = CompilationService()
    >>> compiled_agents = await compiler.compile_graph(graph)
"""

from typing import Any, Dict, Optional

from backend.models.workflow import GraphData
from backend.services.config import get_logger

from .constants import DEFAULT_LAZY_COMPILE, LOG_PREFIX_COMPILATION
from .exceptions import CompilationError


logger = get_logger(__name__)


class CompilationService:
    """Service for compiling graphs with their tool bindings.

    This service manages compile-time tool binding and agent compilation,
    caching compiled agents for improved execution performance.

    Attributes:
        use_compile_time_tools: Whether compile-time tools are enabled
        compiled_agents: Cache of compiled agents
        compilation_status: Status of graph compilations
        tool_registry: Registry of available tools
        agent_compiler: Agent compiler instance

    Methods:
        initialize: Initialize compile-time features
        compile_graph: Compile all agents in a graph
        get_compiled_agent: Get a cached compiled agent
        get_compilation_status: Get compilation status for a graph
        get_compilation_stats: Get compilation statistics
    """

    def __init__(
        self,
        use_compile_time_tools: bool = True,
        lazy_compile: bool = DEFAULT_LAZY_COMPILE,
    ):
        """Initialize compilation service.

        Args:
            use_compile_time_tools: Whether to enable compile-time tools
            lazy_compile: Whether to use lazy compilation
        """
        self.use_compile_time_tools = use_compile_time_tools
        self.lazy_compile = lazy_compile
        self.compiled_agents: Dict[str, Any] = {}
        self.compilation_status: Dict[str, str] = {}
        self.tool_registry: Optional[Any] = None
        self.agent_compiler: Optional[Any] = None

        # Initialize if enabled
        if self.use_compile_time_tools and not lazy_compile:
            self.initialize()

    def initialize(self) -> bool:
        """Initialize compile-time tool binding components.

        Loads the tool registry and agent compiler if available.

        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            from backend.services.agent import get_agent_compiler
            from backend.services.tools import get_tool_registry

            self.tool_registry = get_tool_registry()
            self.agent_compiler = get_agent_compiler()

            logger.info(
                f"{LOG_PREFIX_COMPILATION} Compile-time features initialized successfully"
            )
            return True

        except ImportError as e:
            logger.warning(
                f"{LOG_PREFIX_COMPILATION} Could not initialize compile-time features: {e}"
            )
            logger.info(
                f"{LOG_PREFIX_COMPILATION} Falling back to runtime tool discovery"
            )
            self.use_compile_time_tools = False
            self.tool_registry = None
            self.agent_compiler = None
            return False

    async def compile_graph(self, graph: GraphData) -> Dict[str, Any]:
        """Compile all agents in a graph with their tools.

        Pre-compiles agents with their tool bindings for improved execution
        performance. Results are cached for subsequent use.

        Args:
            graph: Graph to compile

        Returns:
            Dictionary mapping agent_id -> CompiledAgent
            Returns empty dict if compile-time tools disabled

        Raises:
            CompilationError: If compilation fails

        Example:
            >>> compiled_agents = await compiler.compile_graph(my_graph)
            >>> print(f"Compiled {len(compiled_agents)} agents")
        """
        if not self.use_compile_time_tools:
            logger.debug(
                f"{LOG_PREFIX_COMPILATION} Compile-time tools disabled, skipping compilation"
            )
            return {}

        if not self.agent_compiler:
            logger.warning(f"{LOG_PREFIX_COMPILATION} Agent compiler not available")
            return {}

        logger.info(f"{LOG_PREFIX_COMPILATION} Compiling graph: {graph.name}")
        self.compilation_status[graph.name] = "compiling"

        try:
            # Compile all agents in the graph
            compilation_results = await self.agent_compiler.compile_graph(graph)

            compiled_agents = {}
            has_errors = False
            error_messages = []

            for agent_id, result in compilation_results.items():
                if result.success and result.agent:
                    compiled_agents[agent_id] = result.agent
                    # Cache the compiled agent
                    self.compiled_agents[agent_id] = result.agent
                    logger.info(
                        f"{LOG_PREFIX_COMPILATION} Compiled agent {result.agent.agent_name} "
                        f"with {len(result.agent.tools)} tools"
                    )
                else:
                    logger.error(
                        f"{LOG_PREFIX_COMPILATION} Failed to compile agent {agent_id}: {result.errors}"
                    )
                    has_errors = True
                    error_messages.extend(result.errors)

            # Update compilation status
            if has_errors:
                self.compilation_status[graph.name] = "partial"
                logger.warning(
                    f"{LOG_PREFIX_COMPILATION} Graph '{graph.name}' partially compiled "
                    f"({len(compiled_agents)}/{len(compilation_results)} agents)"
                )
            else:
                self.compilation_status[graph.name] = "compiled"
                logger.info(
                    f"{LOG_PREFIX_COMPILATION} Graph '{graph.name}' fully compiled "
                    f"({len(compiled_agents)} agents)"
                )

            return compiled_agents

        except Exception as e:
            logger.error(
                f"{LOG_PREFIX_COMPILATION} Failed to compile graph {graph.name}: {e}"
            )
            self.compilation_status[graph.name] = "failed"
            raise CompilationError(graph.name, [str(e)])

    def get_compiled_agent(self, agent_id: str) -> Optional[Any]:
        """Get a compiled agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Compiled agent or None if not found/disabled

        Example:
            >>> agent = compiler.get_compiled_agent("agent-123")
            >>> if agent:
            ...     print(f"Using compiled agent with {len(agent.tools)} tools")
        """
        if not self.use_compile_time_tools:
            return None

        # Check cache first
        if agent_id in self.compiled_agents:
            logger.debug(
                f"{LOG_PREFIX_COMPILATION} Retrieved compiled agent from cache: {agent_id}"
            )
            return self.compiled_agents[agent_id]

        # Try to get from compiler
        if self.agent_compiler:
            compiled = self.agent_compiler.get_compiled_agent(agent_id)
            if compiled:
                # Cache for future use
                self.compiled_agents[agent_id] = compiled
                logger.debug(
                    f"{LOG_PREFIX_COMPILATION} Retrieved and cached compiled agent: {agent_id}"
                )
            return compiled

        return None

    def get_compilation_status(self, graph_name: str) -> str:
        """Get compilation status for a graph.

        Args:
            graph_name: Graph name

        Returns:
            Status string: "pending", "compiling", "compiled", "partial",
                          "failed", or "disabled"
        """
        if not self.use_compile_time_tools:
            return "disabled"

        return self.compilation_status.get(graph_name, "pending")

    def get_compilation_stats(self, total_graphs: int = 0) -> Dict[str, Any]:
        """Get compilation statistics.

        Args:
            total_graphs: Total number of graphs (for rate calculation)

        Returns:
            Dictionary containing:
                - enabled: bool - Whether compilation is enabled
                - total_graphs: int - Total graphs
                - compiled_agents: int - Number of compiled agents
                - status_counts: Dict - Count of each status
                - compilation_rate: float - Ratio of compiled graphs

        Example:
            >>> stats = compiler.get_compilation_stats(10)
            >>> print(f"Compilation rate: {stats['compilation_rate']:.2%}")
        """
        if not self.use_compile_time_tools:
            return {"enabled": False, "message": "Compile-time tools disabled"}

        status_counts = {
            "pending": 0,
            "compiling": 0,
            "compiled": 0,
            "partial": 0,
            "failed": 0,
        }

        for status in self.compilation_status.values():
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "enabled": True,
            "total_graphs": total_graphs,
            "compiled_agents": len(self.compiled_agents),
            "status_counts": status_counts,
            "compilation_rate": (
                status_counts["compiled"] / total_graphs if total_graphs else 0
            ),
        }

    def clear_cache(self, agent_id: Optional[str] = None) -> None:
        """Clear compiled agent cache.

        Args:
            agent_id: Specific agent to clear, or None to clear all

        Example:
            >>> compiler.clear_cache("agent-123")  # Clear one agent
            >>> compiler.clear_cache()  # Clear all
        """
        if agent_id:
            if agent_id in self.compiled_agents:
                del self.compiled_agents[agent_id]
                logger.debug(
                    f"{LOG_PREFIX_COMPILATION} Cleared cache for agent: {agent_id}"
                )
        else:
            self.compiled_agents.clear()
            logger.info(f"{LOG_PREFIX_COMPILATION} Cleared all compiled agent cache")
