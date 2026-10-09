"""Agent compiler for compile-time tool binding and optimization.

This module provides the main AgentCompiler class that compiles agents
with all dependencies resolved at compilation time, eliminating runtime
lookups for better performance.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from backend.models.workflow import (
    AgentConfig,
    EnhancedNodeData,
    GraphData,
    LLMConfig,
    NodeType,
)
from backend.services.config import ExecutionConfig, get_logger
from backend.services.llm_models import LLMFactory
from backend.services.tools import ToolBinding, get_tool_registry

from .cache import CompilationCache
from .models import CompiledAgent, CompilationResult, CompilationStats
from .performance import PerformanceAnalyzer
from .utils import compile_structured_output, find_connected_tools, generate_cache_key
from .validators import ConfigValidator


logger = get_logger("agent.compiler")


class AgentCompiler:
    """Compiles agents with all tools and dependencies at compile time.

    This compiler eliminates runtime lookups by resolving all agent
    dependencies (LLM, tools, configurations) during compilation,
    resulting in better execution performance.

    The compiler also provides:
    - Configuration validation before compilation
    - Intelligent caching with TTL
    - Performance analysis and optimization hints
    - Detailed compilation statistics
    """

    def __init__(self):
        """Initialize agent compiler with dependencies."""
        self.tool_registry = get_tool_registry()
        self.llm_factory = LLMFactory()
        self.cache = CompilationCache()
        self.performance_analyzer = PerformanceAnalyzer()
        self.validator = ConfigValidator()
        self._stats = CompilationStats()
        logger.info("Initialized AgentCompiler")

    async def compile_agent(
        self, node: EnhancedNodeData, graph: Optional[GraphData] = None
    ) -> CompilationResult:
        """Compile an agent with all dependencies resolved.

        Args:
            node: Agent node to compile
            graph: Optional graph for context (e.g., connected tools)

        Returns:
            CompilationResult with compiled agent or errors
        """
        start_time = asyncio.get_event_loop().time()
        self._stats.total_compilations += 1

        # Check cache first
        cache_key = generate_cache_key(node)
        cached_agent = self.cache.get(cache_key)
        if cached_agent:
            self._stats.cache_hits += 1
            logger.debug(f"Using cached compiled agent: {node.name}")
            compilation_time = (asyncio.get_event_loop().time() - start_time) * 1000
            return CompilationResult(
                success=True,
                agent=cached_agent,
                compilation_time_ms=compilation_time,
            )

        self._stats.cache_misses += 1
        logger.info(f"Compiling agent: {node.name}")

        errors: List[str] = []
        warnings: List[str] = []

        # Validate configuration
        validation_result = self.validator.validate_node(node)
        if not validation_result.valid:
            self._stats.failed_compilations += 1
            return self._create_error_result(validation_result.errors, start_time)

        warnings.extend(validation_result.warnings)

        # Compile LLM
        llm = self._compile_llm(node.agent_config, errors)
        if not llm:
            self._stats.failed_compilations += 1
            return self._create_error_result(errors, start_time)

        # Compile tools
        tools, tool_bindings = await self._compile_tools(node, graph, warnings)

        # Analyze performance
        performance_hints = self.performance_analyzer.analyze_agent(node, tools)

        # Create compiled agent
        compiled_agent = CompiledAgent(
            agent_id=node.uniq_id,
            agent_name=node.name,
            agent_type="orchestrator"
            if (node.agent_config and node.agent_config.is_orchestrator)
            else "agent",
            llm=llm,
            tools=tools,
            tool_bindings=tool_bindings,
            system_prompt=node.agent_config.system_prompt,
            structured_output_schema=compile_structured_output(node.agent_config),
            memory_enabled=node.agent_config.memory_enabled,
            delegation_enabled=(
                node.agent_config and node.agent_config.is_orchestrator
            ),
            cache_key=cache_key,
            performance_hints=performance_hints,
        )

        # Cache the compiled agent
        self.cache.set(cache_key, compiled_agent)

        # Update statistics
        compilation_time = (asyncio.get_event_loop().time() - start_time) * 1000
        self._stats.total_time_ms += compilation_time
        self._stats.successful_compilations += 1

        logger.info(
            f"Successfully compiled agent {node.name} with {len(tools)} tools "
            f"in {compilation_time:.2f}ms"
        )

        return CompilationResult(
            success=True,
            agent=compiled_agent,
            warnings=warnings,
            compilation_time_ms=compilation_time,
        )

    def _compile_llm(
        self, config: AgentConfig, errors: List[str]
    ) -> Optional[BaseChatModel]:
        """Compile LLM from configuration.

        Args:
            config: Agent configuration
            errors: List to append errors to

        Returns:
            Compiled LLM instance or None on failure
        """
        try:
            if not config.llm_config:
                errors.append("No LLM configuration provided")
                return None

            # Convert dict to LLMConfig if needed
            llm_config = config.llm_config
            if isinstance(llm_config, dict):
                llm_config = LLMConfig(**llm_config)

            llm_instance = self.llm_factory.create_llm_instance(llm_config)
            if not llm_instance or not llm_instance.llm:
                error_msg = f"Failed to create LLM: {llm_config.provider}/{llm_config.model_name}"
                errors.append(error_msg)
                logger.error(error_msg)
                return None

            return llm_instance.llm

        except Exception as e:
            error_msg = (
                f"LLM compilation error "
                f"({config.llm_config.provider if config.llm_config else 'unknown'}/"
                f"{config.llm_config.model_name if config.llm_config else 'unknown'}): "
                f"{str(e)}"
            )
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
            return None

    async def _compile_tools(
        self, node: EnhancedNodeData, graph: Optional[GraphData], warnings: List[str]
    ) -> Tuple[List[BaseTool], List[ToolBinding]]:
        """Compile tools for the agent.

        Args:
            node: Agent node
            graph: Optional graph for finding connected tools
            warnings: List to append warnings to

        Returns:
            Tuple of (compiled tools, tool bindings)
        """
        tool_configs = []

        # Get configured tools
        if node.agent_config and node.agent_config.tools:
            tool_configs.extend(node.agent_config.tools)

        # Get connected tools from graph
        if graph and ExecutionConfig.get_features().use_compile_time_tools:
            connected_tools = find_connected_tools(node, graph)
            for tool_node in connected_tools:
                tool_configs.append(
                    {
                        "name": tool_node.name,
                        "connected_node_id": tool_node.uniq_id,
                        "node_type": tool_node.type.value,
                        "description": f"Execute {tool_node.name}",
                    }
                )

        # Bind tools through registry
        bindings = self.tool_registry.bind_tools_for_agent(
            agent_id=node.uniq_id,
            agent_name=node.name,
            tool_configs=tool_configs,
            agent_config=node.agent_config,
        )

        # Extract tool instances
        tools = [binding.tool_instance for binding in bindings]

        if len(tools) < len(tool_configs):
            warning_msg = (
                f"Some tools could not be bound: expected {len(tool_configs)}, "
                f"got {len(tools)}"
            )
            warnings.append(warning_msg)
            logger.warning(warning_msg)

        return tools, bindings

    async def compile_graph(self, graph: GraphData) -> Dict[str, CompilationResult]:
        """Compile all agents in a graph.

        Args:
            graph: Graph containing agents to compile

        Returns:
            Dictionary mapping agent_id to CompilationResult
        """
        logger.info(f"Compiling graph: {graph.name}")

        results = {}
        agent_nodes = [n for n in graph.nodes if n.type == NodeType.AGENT]

        # Compile agents in parallel for performance
        compilation_tasks = [self.compile_agent(node, graph) for node in agent_nodes]
        compiled_results = await asyncio.gather(*compilation_tasks)

        for node, result in zip(agent_nodes, compiled_results):
            results[node.uniq_id] = result

            if result.success:
                logger.info(f"Compiled agent {node.name} successfully")
            else:
                logger.error(f"Failed to compile agent {node.name}: {result.errors}")

        # Log compilation statistics
        successful = sum(1 for r in results.values() if r.success)
        logger.info(
            f"Graph compilation complete: {successful}/{len(agent_nodes)} "
            f"agents compiled successfully"
        )

        return results

    def get_compiled_agent(self, agent_id: str) -> Optional[CompiledAgent]:
        """Get a compiled agent by ID from cache.

        Args:
            agent_id: Agent identifier

        Returns:
            Compiled agent or None if not found
        """
        # Search by agent_id in cached agents
        for cache_key in list(self.cache._cache.keys()):
            entry = self.cache._cache.get(cache_key)
            if entry and entry.agent.agent_id == agent_id:
                # Return via cache.get to update statistics
                return self.cache.get(cache_key)
        return None

    def clear_cache(self) -> None:
        """Clear all caches."""
        self.cache.clear()
        self.tool_registry.factory.clear_cache()
        logger.info("Cleared all compilation caches")

    def optimize_cache(self) -> None:
        """Optimize compilation cache by removing expired entries."""
        self.cache.optimize()

    def get_compilation_stats(self) -> Dict[str, Any]:
        """Get compilation statistics.

        Returns:
            Dictionary containing compilation statistics
        """
        stats = self._stats.to_dict()
        cache_stats = self.cache.get_stats()
        stats["cache"] = cache_stats.to_dict()
        return stats

    def _create_error_result(
        self, errors: List[str], start_time: float
    ) -> CompilationResult:
        """Create error compilation result.

        Args:
            errors: List of error messages
            start_time: Compilation start time

        Returns:
            CompilationResult indicating failure
        """
        compilation_time = (asyncio.get_event_loop().time() - start_time) * 1000
        return CompilationResult(
            success=False,
            agent=None,
            errors=errors,
            compilation_time_ms=compilation_time,
        )


# Global compiler instance
_global_compiler: Optional[AgentCompiler] = None


def get_agent_compiler() -> AgentCompiler:
    """Get the global agent compiler instance.

    Returns:
        Global AgentCompiler instance
    """
    global _global_compiler
    if _global_compiler is None:
        _global_compiler = AgentCompiler()
        logger.info("Initialized global agent compiler")
    return _global_compiler


def reset_agent_compiler() -> None:
    """Reset the global agent compiler.

    Clears the cache and creates a new compiler instance.
    """
    global _global_compiler
    if _global_compiler:
        _global_compiler.clear_cache()
    _global_compiler = None
    logger.info("Reset agent compiler")
