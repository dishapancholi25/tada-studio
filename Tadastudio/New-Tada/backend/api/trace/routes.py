"""REST API endpoints for trace visualization.

Provides tree transformation, node details, statistics, and export functionality.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.services.database import get_db
from ...services.execution.history import ExecutionHistoryService
from ...models import NodeExecution
from ...services.config import get_logger
from ...services.trace import ExportService, StatisticsService, TraceTreeBuilder


from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.services.auth.scope_enforcer import require_scope
from backend.services.authorization.helpers import require_execution_access

logger = get_logger("trace_api")

router = APIRouter(
    prefix="/api/trace",
    tags=["trace"],
    dependencies=[Depends(require_active_user), Depends(require_scope("execution:*:read"))],
)


@router.get("/{execution_id}/tree")
async def get_trace_tree(
    execution_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get hierarchical trace tree for an execution."""
    try:
        require_execution_access(current_user, execution_id)
        # Fetch execution data with all node executions
        execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)

        if not execution_data:
            raise HTTPException(status_code=404, detail="Execution not found")

        # Build and return trace tree
        trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
        return trace_tree

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building trace tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/nodes/{node_id}")
async def get_node_details(
    execution_id: str,
    node_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get detailed information for a specific node."""
    try:
        require_execution_access(current_user, execution_id)
        node_data = ExecutionHistoryService.get_node_execution(execution_id, node_id)

        if not node_data:
            raise HTTPException(status_code=404, detail="Node not found")

        # Enrich with any additional details
        return {
            "node": node_data,
            "metadata": {
                "hasLLMData": bool(node_data.get("llm_metadata")),
                "hasToolData": bool(node_data.get("tool_metadata")),
                "hasMessages": bool(node_data.get("message_structure")),
                "hasOrchestration": bool(node_data.get("orchestration_metadata")),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching node details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/stats")
async def get_execution_stats(
    execution_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get aggregated statistics for an execution."""
    try:
        require_execution_access(current_user, execution_id)
        with get_db() as db:
            # Get all nodes for this execution
            nodes = (
                db.query(NodeExecution)
                .filter(NodeExecution.graph_execution_id == execution_id)
                .all()
            )

            if not nodes:
                raise HTTPException(status_code=404, detail="Execution not found")

            # Calculate statistics using StatisticsService
            stats = StatisticsService.calculate_execution_stats(nodes)
            return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating execution stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/export")
async def export_trace(
    execution_id: str,
    export_format: str = Query("json", enum=["json", "yaml", "opentelemetry"]),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Export trace in various formats."""
    try:
        require_execution_access(current_user, execution_id)
        # Get trace tree
        execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)

        if not execution_data:
            raise HTTPException(status_code=404, detail="Execution not found")

        trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

        # Export in requested format
        if export_format == "json":
            return ExportService.export_as_json(trace_tree)
        elif export_format == "yaml":
            return ExportService.export_as_yaml(trace_tree)
        elif export_format == "opentelemetry":
            return ExportService.export_as_opentelemetry(trace_tree)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))
