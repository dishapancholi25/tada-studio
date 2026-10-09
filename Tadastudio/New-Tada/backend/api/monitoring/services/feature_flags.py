"""
Feature flags service.

This module provides feature flag configuration and status information.
"""

from datetime import datetime, timezone

from ....services.config import ExecutionConfig, get_logger
from ..models import FeatureFlagsResponse


logger = get_logger("monitoring.feature_flags")


def get_feature_flags() -> FeatureFlagsResponse:
    """
    Get current feature flag configuration.

    Returns:
        FeatureFlagsResponse with all feature flag states
    """
    try:
        logger.debug("[MONITORING-FLAGS] Retrieving feature flags")

        config = ExecutionConfig.get_features()

        return FeatureFlagsResponse(
            use_unified_state=config.use_unified_state,
            use_compile_time_tools=config.use_compile_time_tools,
            cache_subgraphs=config.cache_subgraphs,
            enable_performance_tracking=config.enable_performance_tracking,
            parallel_tool_execution=config.parallel_tool_execution,
            use_memory=ExecutionConfig.use_memory(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error(f"[MONITORING-FLAGS] Failed to get feature flags: {e}")
        # Return default flags on error
        return FeatureFlagsResponse(
            use_unified_state=False,
            use_compile_time_tools=False,
            cache_subgraphs=False,
            enable_performance_tracking=False,
            parallel_tool_execution=False,
            use_memory=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
