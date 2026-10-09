"""
Monitoring API routes.

This module defines all monitoring endpoints including health checks,
metrics, diagnostics, and system status endpoints.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.auth.dependencies import require_active_user, require_admin
from backend.services.auth.rbac import _redact_email

from ...services.config import get_logger
from ...services.metrics import get_metrics_manager
from .models import (
    CacheClearResponse,
    DashboardMetricsResponse,
    DetailedHealthCheckResponse,
    DiagnosticsResponse,
    FeatureFlagsResponse,
    HealthCheckResponse,
    OptimizationResponse,
    SystemStatusResponse,
)
from .services.diagnostics import run_diagnostics
from .services.feature_flags import get_feature_flags
from .services.health import get_basic_health, get_detailed_health
from .services.system_info import get_system_status
from .utils import (
    clear_system_caches,
    get_metrics_export,
    handle_monitoring_errors,
    optimize_system_performance,
)

logger = get_logger("monitoring.routes")

# Create router for monitoring endpoints
router = APIRouter(
    prefix="/api/monitoring",
    tags=["monitoring"],
    dependencies=[Depends(require_active_user)],
)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Check basic system health.

    Returns:
        HealthCheckResponse: Health status and component information
    """
    return get_basic_health()


@router.get(
    "/health/detailed",
    response_model=DetailedHealthCheckResponse,
    dependencies=[Depends(require_admin)],
)
async def detailed_health_check() -> DetailedHealthCheckResponse:
    """
    Detailed health check with comprehensive system information.

    Returns:
        DetailedHealthCheckResponse: Detailed health status including metrics and config
    """
    return get_detailed_health()


@router.get("/metrics")
@handle_monitoring_errors("metrics_export")
async def get_metrics(
    export_format: str = Query(
        "json", description="Export format: json, prometheus, or statsd"
    ),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> Any:
    """
    Export metrics in various formats.

    Args:
        export_format: Export format (json, prometheus, statsd)

    Returns:
        Metrics in requested format

    Raises:
        HTTPException: If format is invalid or export fails
    """
    try:
        return get_metrics_export(export_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/metrics/dashboard", response_model=DashboardMetricsResponse)
@handle_monitoring_errors("metrics_dashboard")
async def metrics_dashboard(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> DashboardMetricsResponse:
    """
    Get metrics formatted for dashboard display.

    Returns:
        DashboardMetricsResponse: Dashboard-ready metrics data
    """
    metrics_manager = get_metrics_manager()
    dashboard_data = metrics_manager.get_dashboard_data()

    # Convert to response model
    from .models import Alert, AlertLevel, ApplicationMetrics, SystemMetrics

    system_metrics = SystemMetrics(
        cpu_percent=dashboard_data.get("system", {}).get("cpu_percent", 0.0),
        memory_percent=dashboard_data.get("system", {}).get("memory_percent", 0.0),
        process_memory_mb=dashboard_data.get("system", {}).get(
            "process_memory_mb", 0.0
        ),
    )

    app_metrics_data = dashboard_data.get("application", {})
    application_metrics = ApplicationMetrics(
        agent_executions=app_metrics_data.get("agent_executions"),
        tool_executions=app_metrics_data.get("tool_executions"),
        avg_execution_time_ms=app_metrics_data.get("avg_execution_time_ms"),
        cache_hit_rate=app_metrics_data.get("cache_hit_rate", 0.0),
    )

    # Parse alerts
    alerts = []
    for alert_data in dashboard_data.get("alerts", []):
        try:
            alert = Alert(
                level=AlertLevel(alert_data.get("level", "info")),
                message=alert_data.get("message", ""),
                timestamp=alert_data.get("timestamp", ""),
            )
            alerts.append(alert)
        except (ValueError, KeyError) as e:
            logger.warning(f"[MONITORING-DASHBOARD] Failed to parse alert: {e}")

    return DashboardMetricsResponse(
        timestamp=dashboard_data.get("timestamp", ""),
        system=system_metrics,
        application=application_metrics,
        alerts=alerts,
    )


@router.get("/status", response_model=SystemStatusResponse)
@handle_monitoring_errors("system_status")
async def system_status(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> SystemStatusResponse:
    """
    Get current system status and configuration.

    Returns:
        SystemStatusResponse: System status information
    """
    return get_system_status()


@router.get("/diagnostics", response_model=DiagnosticsResponse)
@handle_monitoring_errors("diagnostics")
async def diagnostics(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> DiagnosticsResponse:
    """
    Run system diagnostics and return results.

    Returns:
        DiagnosticsResponse: Diagnostic information
    """
    return run_diagnostics()


@router.post("/cache/clear", response_model=CacheClearResponse)
@handle_monitoring_errors("cache_clear")
async def clear_caches(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> CacheClearResponse:
    """
    Clear all system caches.

    Returns:
        CacheClearResponse: Cache clear status
    """
    result = clear_system_caches()

    # Audit logging for security events
    user_email = current_user.get("email", "unknown")
    logger.info(f"[AUDIT] System caches cleared by {_redact_email(user_email)}")

    return result


@router.post("/optimize", response_model=OptimizationResponse)
@handle_monitoring_errors("optimize")
async def optimize_performance(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> OptimizationResponse:
    """
    Trigger performance optimization.

    Returns:
        OptimizationResponse: Optimization status
    """
    result = optimize_system_performance()

    # Audit logging for security events
    user_email = current_user.get("email", "unknown")
    logger.info(
        f"[AUDIT] Performance optimization triggered by {_redact_email(user_email)}"
    )

    return result


@router.get("/feature-flags", response_model=FeatureFlagsResponse)
@handle_monitoring_errors("feature_flags")
async def get_feature_flags_endpoint(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> FeatureFlagsResponse:
    """
    Get current feature flag status.

    Returns:
        FeatureFlagsResponse: Feature flag configuration
    """
    return get_feature_flags()


@router.get("/scope-rejections")
async def get_scope_rejections(
    token_id: str = Query(None, description="Filter by token ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    """Return paginated scope rejection audit log entries. Admin only.

    Args:
        token_id: Optional filter by token ID
        limit: Max entries to return
        offset: Pagination offset
        current_user: Must be an admin

    Returns:
        Paginated list of scope rejection log entries
    """
    import json

    from backend.models.auth.scope_rejection_log import ScopeRejectionLog
    from backend.services.database import get_db

    try:
        with get_db() as db:
            query = db.query(ScopeRejectionLog)
            if token_id:
                query = query.filter(ScopeRejectionLog.token_id == token_id)
            total_count = query.count()
            rows = (
                query.order_by(ScopeRejectionLog.timestamp.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            entries = [
                {
                    "id": str(r.id),
                    "token_id": r.token_id,
                    "token_prefix": r.token_prefix,
                    "user_id": r.user_id,
                    "resource": r.resource,
                    "scope_required": r.scope_required,
                    "scopes_held": json.loads(r.scopes_held) if r.scopes_held else [],
                    "client_ip": r.client_ip,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                }
                for r in rows
            ]

        return {"entries": entries, "total_count": total_count}

    except Exception as exc:
        logger.error(f"[MONITORING] Error fetching scope rejections: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch scope rejections")
