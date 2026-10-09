"""Performance analysis utilities for agent compilation.

This module provides tools for analyzing agent configurations and generating
performance optimization hints.
"""

from typing import Any, Dict, List

from langchain_core.tools import BaseTool

from backend.models.workflow import EnhancedNodeData

from .config import (
    DEFAULT_TIMEOUT,
    EXPENSIVE_TIMEOUT,
    EXPENSIVE_TOOLS,
    PARALLEL_EXECUTION_THRESHOLD,
)


class PerformanceAnalyzer:
    """Analyzes agent configurations for performance optimization.

    Provides recommendations for timeout values, parallel execution,
    and other performance-related settings based on agent configuration.
    """

    @staticmethod
    def analyze_agent(node: EnhancedNodeData, tools: List[BaseTool]) -> Dict[str, Any]:
        """Analyze agent and generate performance hints.

        Args:
            node: Agent node to analyze
            tools: List of compiled tools for the agent

        Returns:
            Dictionary containing performance hints and recommendations
        """
        hints = {
            "tool_count": len(tools),
            "has_expensive_tools": False,
            "has_cached_tools": False,
            "recommended_timeout": DEFAULT_TIMEOUT,
            "parallel_tool_execution": False,
        }

        # Check for expensive tools
        if PerformanceAnalyzer._has_expensive_tools(tools):
            hints["has_expensive_tools"] = True
            hints["recommended_timeout"] = EXPENSIVE_TIMEOUT

        # Check for cached tools
        if PerformanceAnalyzer._has_cached_tools(tools):
            hints["has_cached_tools"] = True

        # Recommend parallel execution for many tools
        if len(tools) > PARALLEL_EXECUTION_THRESHOLD:
            hints["parallel_tool_execution"] = True

        return hints

    @staticmethod
    def _has_expensive_tools(tools: List[BaseTool]) -> bool:
        """Check if any tools are considered expensive.

        Args:
            tools: List of tools to check

        Returns:
            True if any expensive tools are present
        """
        for tool in tools:
            tool_name_lower = tool.name.lower()
            if any(expensive in tool_name_lower for expensive in EXPENSIVE_TOOLS):
                return True
        return False

    @staticmethod
    def _has_cached_tools(tools: List[BaseTool]) -> bool:
        """Check if any tools have caching enabled.

        Args:
            tools: List of tools to check

        Returns:
            True if any tools have caching
        """
        for tool in tools:
            if hasattr(tool, "cache_results") and tool.cache_results:
                return True
        return False

    @staticmethod
    def get_recommended_timeout(tools: List[BaseTool]) -> int:
        """Get recommended timeout based on tools.

        Args:
            tools: List of tools

        Returns:
            Recommended timeout in seconds
        """
        if PerformanceAnalyzer._has_expensive_tools(tools):
            return EXPENSIVE_TIMEOUT
        return DEFAULT_TIMEOUT

    @staticmethod
    def should_use_parallel_execution(tools: List[BaseTool]) -> bool:
        """Determine if parallel execution should be used.

        Args:
            tools: List of tools

        Returns:
            True if parallel execution is recommended
        """
        return len(tools) > PARALLEL_EXECUTION_THRESHOLD
