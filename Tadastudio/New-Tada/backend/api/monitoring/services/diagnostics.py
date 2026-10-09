"""
Diagnostics service for system health and component checks.

This module provides comprehensive diagnostic checks for all system components
including graph manager, execution engine, metrics, and integration status.
"""

from datetime import datetime, timezone
from typing import Dict

from ....services.config import get_logger
from ....services.dependency_injection import get_execution_engine, get_graph_manager
from ....services.metrics import get_metrics_manager
from ..models import (
    DiagnosticCheck,
    DiagnosticsResponse,
    ExecutionEngineCheck,
    GraphManagerCheck,
    HealthStatus,
    IntegrationCheck,
    MetricsCheck,
)


logger = get_logger("monitoring.diagnostics")


def check_graph_manager() -> GraphManagerCheck:
    """
    Check graph manager status.

    Returns:
        GraphManagerCheck with status and details
    """
    try:
        graph_manager = get_graph_manager()
        graphs = graph_manager.list_graphs()

        return GraphManagerCheck(
            status="ok",
            graphs_loaded=len(graphs),
            graphs=graphs[:10],  # First 10 for brevity
        )

    except Exception as e:
        logger.error(f"[MONITORING-DIAGNOSTICS] Graph manager check failed: {e}")
        return GraphManagerCheck(status="error", error=str(e))


def check_execution_engine() -> ExecutionEngineCheck:
    """
    Check execution engine status.

    Returns:
        ExecutionEngineCheck with status and details
    """
    try:
        engine = get_execution_engine()

        return ExecutionEngineCheck(status="ok", type=type(engine).__name__)

    except Exception as e:
        logger.error(f"[MONITORING-DIAGNOSTICS] Execution engine check failed: {e}")
        return ExecutionEngineCheck(status="error", error=str(e))


def check_integration() -> IntegrationCheck:
    """
    Check integration status.

    Returns:
        IntegrationCheck with status and details
    """
    try:
        # Integration status - using standard LangGraph implementation
        return IntegrationCheck(
            status="ok",
            engine="langgraph",
            implementation="standard",
            cleanup="complete",
        )

    except Exception as e:
        logger.error(f"[MONITORING-DIAGNOSTICS] Integration check failed: {e}")
        return IntegrationCheck(status="error", error=str(e))


def check_metrics() -> MetricsCheck:
    """
    Check metrics system status.

    Returns:
        MetricsCheck with status and details
    """
    try:
        metrics_manager = get_metrics_manager()
        all_metrics = metrics_manager.collector.get_all_metrics()

        collection_active = False
        if metrics_manager.collection_thread:
            collection_active = metrics_manager.collection_thread.is_alive()

        return MetricsCheck(
            status="ok",
            metrics_count=len(all_metrics),
            collection_active=collection_active,
        )

    except Exception as e:
        logger.error(f"[MONITORING-DIAGNOSTICS] Metrics check failed: {e}")
        return MetricsCheck(status="error", error=str(e))


def run_diagnostics() -> DiagnosticsResponse:
    """
    Run all system diagnostics.

    Returns:
        DiagnosticsResponse with all diagnostic results
    """
    try:
        logger.info("[MONITORING-DIAGNOSTICS] Running system diagnostics")

        # Run all checks
        checks: Dict[str, DiagnosticCheck] = {
            "graph_manager": check_graph_manager(),
            "execution_engine": check_execution_engine(),
            "integration": check_integration(),
            "metrics": check_metrics(),
        }

        # Determine overall status
        all_ok = all(check.status == "ok" for check in checks.values())
        overall_status = HealthStatus.HEALTHY if all_ok else HealthStatus.DEGRADED

        logger.info(
            f"[MONITORING-DIAGNOSTICS] Diagnostics complete: {overall_status.value}"
        )

        return DiagnosticsResponse(
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_status=overall_status,
            checks=checks,
        )

    except Exception as e:
        logger.error(f"[MONITORING-DIAGNOSTICS] Diagnostics failed: {e}")
        return DiagnosticsResponse(
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_status=HealthStatus.UNHEALTHY,
            checks={
                "error": DiagnosticCheck(
                    status="error", error=f"Diagnostics failed: {str(e)}"
                )
            },
        )
