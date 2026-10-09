"""
Performance tracking for tool executions.

This module provides performance monitoring and statistics collection
for tool usage across the system.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..config import get_logger
from .models import PerformanceStats, ToolBinding


logger = get_logger("tool-performance")


class PerformanceTracker:
    """
    Tracks performance metrics for tool executions.

    Maintains per-tool statistics and provides aggregation capabilities.
    """

    def __init__(self):
        """Initialize the performance tracker."""
        self._stats: Dict[str, PerformanceStats] = {}
        logger.info("[TOOL-PERFORMANCE] Initialized performance tracker")

    def track_execution(
        self,
        tool_id: str,
        execution_time: float,
        success: bool = True,
    ) -> None:
        """
        Track a single tool execution.

        Args:
            tool_id: Identifier of the tool that was executed
            execution_time: Execution time in seconds
            success: Whether the execution succeeded
        """
        # Initialize stats if needed
        if tool_id not in self._stats:
            self._stats[tool_id] = PerformanceStats(tool_id=tool_id)

        # Update statistics
        self._stats[tool_id].update(execution_time, success)

        # Log if execution was slow or failed
        if execution_time > 5.0:
            logger.warning(
                f"[TOOL-PERFORMANCE] Slow execution for '{tool_id}': {execution_time:.2f}s"
            )
        if not success:
            logger.warning(f"[TOOL-PERFORMANCE] Failed execution for '{tool_id}'")

    def update_binding_stats(
        self,
        binding: ToolBinding,
        execution_time: float,
        success: bool = True,
    ) -> None:
        """
        Update performance stats for a tool binding.

        Args:
            binding: Tool binding to update
            execution_time: Execution time in seconds
            success: Whether execution succeeded
        """
        # Update binding-level stats
        binding.execution_count += 1
        binding.total_execution_time += execution_time
        binding.last_used = datetime.now(timezone.utc).isoformat()

        if not success:
            binding.error_count += 1

        # Also track in global stats
        self.track_execution(binding.tool_id, execution_time, success)

        logger.debug(
            f"[TOOL-PERFORMANCE] Updated binding stats for '{binding.tool_id}': "
            f"count={binding.execution_count}, avg={binding.average_execution_time:.3f}s"
        )

    def get_tool_stats(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """
        Get performance statistics for a specific tool.

        Args:
            tool_id: Tool identifier

        Returns:
            Statistics dictionary or None if not found
        """
        if tool_id not in self._stats:
            return None

        return self._stats[tool_id].to_dict()

    def get_all_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for all tools.

        Returns:
            Dictionary mapping tool_id to statistics
        """
        return {tool_id: stats.to_dict() for tool_id, stats in self._stats.items()}

    def get_top_performers(self, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Get top performing tools by execution count.

        Args:
            limit: Maximum number of tools to return

        Returns:
            List of tool statistics, sorted by execution count
        """
        sorted_stats = sorted(
            self._stats.values(),
            key=lambda s: s.total_executions,
            reverse=True,
        )

        return [stats.to_dict() for stats in sorted_stats[:limit]]

    def get_slowest_tools(self, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Get slowest tools by average execution time.

        Args:
            limit: Maximum number of tools to return

        Returns:
            List of tool statistics, sorted by average time
        """
        sorted_stats = sorted(
            self._stats.values(),
            key=lambda s: s.avg_time,
            reverse=True,
        )

        return [stats.to_dict() for stats in sorted_stats[:limit]]

    def get_error_prone_tools(self, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Get tools with highest error rates.

        Args:
            limit: Maximum number of tools to return

        Returns:
            List of tool statistics, sorted by error count
        """
        sorted_stats = sorted(
            self._stats.values(),
            key=lambda s: s.error_count,
            reverse=True,
        )

        # Only include tools that have errors
        error_stats = [s for s in sorted_stats if s.error_count > 0]

        return [stats.to_dict() for stats in error_stats[:limit]]

    def get_summary(self) -> Dict[str, Any]:
        """
        Get overall performance summary.

        Returns:
            Dictionary with aggregated statistics
        """
        if not self._stats:
            return {
                "total_tools_tracked": 0,
                "total_executions": 0,
                "total_errors": 0,
                "average_execution_time": 0.0,
                "total_execution_time": 0.0,
            }

        total_executions = sum(s.total_executions for s in self._stats.values())
        total_errors = sum(s.error_count for s in self._stats.values())
        total_time = sum(s.total_time for s in self._stats.values())
        avg_time = total_time / total_executions if total_executions > 0 else 0.0

        return {
            "total_tools_tracked": len(self._stats),
            "total_executions": total_executions,
            "total_errors": total_errors,
            "error_rate": total_errors / total_executions
            if total_executions > 0
            else 0.0,
            "average_execution_time": avg_time,
            "total_execution_time": total_time,
        }

    def reset_stats(self, tool_id: Optional[str] = None) -> None:
        """
        Reset performance statistics.

        Args:
            tool_id: Optional specific tool to reset (resets all if None)
        """
        if tool_id:
            if tool_id in self._stats:
                del self._stats[tool_id]
                logger.info(f"[TOOL-PERFORMANCE] Reset stats for tool: {tool_id}")
        else:
            tool_count = len(self._stats)
            self._stats.clear()
            logger.info(f"[TOOL-PERFORMANCE] Reset all stats ({tool_count} tools)")

    def export_stats(self) -> Dict[str, Any]:
        """
        Export all statistics for persistence.

        Returns:
            Dictionary of all statistics
        """
        return {
            "summary": self.get_summary(),
            "per_tool": self.get_all_stats(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
