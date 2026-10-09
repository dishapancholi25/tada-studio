"""Service for runtime execution control (stop and pause)."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.services.common.utils.websocket_notifier import ws_notifier
from backend.services.config import get_logger
from backend.services.dependency_injection.types import ExecutionEngineProtocol
from backend.services.execution.history import ExecutionHistoryService

from ..paused.queries import get_execution_by_id
from ....models.execution.node_execution import NodeExecution


logger = get_logger(__name__)


class ExecutionControlService:
    """Service responsible for controlling active workflow executions."""

    def __init__(self, execution_engine: ExecutionEngineProtocol):
        self.execution_engine = execution_engine

    def _resolve_thread_id(self, execution: Any) -> str:
        thread_id = execution.thread_id or execution.websocket_execution_id
        if not thread_id:
            raise ValueError(
                f"Execution {execution.id} does not have an active thread identifier"
            )
        return thread_id

    async def request_stop(self, db: Session, execution_id: str) -> Dict[str, Any]:
        """Forcefully stop an execution immediately."""
        execution = get_execution_by_id(db, execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")

        if execution.status in {"completed", "failed", "cancelled"}:
            raise ValueError(
                f"Execution {execution_id} is already finished with status {execution.status}"
            )
        if execution.status == "stopped":
            return {
                "status": "stopped",
                "execution_id": execution_id,
                "thread_id": self._resolve_thread_id(execution),
            }

        thread_id = self._resolve_thread_id(execution)
        logger.info(
            "[EXEC-CONTROL] Stop requested for execution %s (thread %s)",
            execution_id,
            thread_id,
        )

        result = self.execution_engine.request_stop(
            thread_id, reason="User requested stop"
        )

        try:
            ExecutionHistoryService.update_graph_execution(
                execution_id=execution_id,
                status="stopping",
            )
        except Exception as exc:
            logger.warning(
                "[EXEC-CONTROL] Failed to mark execution %s stopping: %s",
                execution_id,
                exc,
            )

        if ws_notifier:
            try:
                await ws_notifier.on_execution_stop_requested(
                    thread_id,
                    {
                        "db_execution_id": execution_id,
                        "requested_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception as exc:
                logger.warning(
                    "[EXEC-CONTROL] Failed to broadcast stop request for %s: %s",
                    execution_id,
                    exc,
                )

        return {
            "status": result.get("status", "stop_requested"),
            "execution_id": execution_id,
            "thread_id": thread_id,
        }

    async def request_pause(self, db: Session, execution_id: str) -> Dict[str, Any]:
        """Pause an execution once the current node completes."""
        execution = get_execution_by_id(db, execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")

        if execution.status in {"completed", "failed", "cancelled", "stopped"}:
            raise ValueError(
                f"Execution {execution_id} is already finished with status {execution.status}"
            )
        if execution.status == "paused":
            return {
                "status": "paused",
                "execution_id": execution_id,
                "thread_id": self._resolve_thread_id(execution),
            }
        if execution.status == "pause_pending":
            return {
                "status": "pause_pending",
                "execution_id": execution_id,
                "thread_id": self._resolve_thread_id(execution),
            }

        thread_id = self._resolve_thread_id(execution)
        logger.info(
            "[EXEC-CONTROL] Pause requested for execution %s (thread %s)",
            execution_id,
            thread_id,
        )

        result = self.execution_engine.request_pause(thread_id)

        try:
            ExecutionHistoryService.update_graph_execution(
                execution_id=execution_id,
                status="pause_pending",
            )
        except Exception as exc:
            logger.warning(
                "[EXEC-CONTROL] Failed to mark pause pending for %s: %s",
                execution_id,
                exc,
            )

        if ws_notifier:
            try:
                await ws_notifier.on_execution_pause_requested(
                    thread_id,
                    {
                        "db_execution_id": execution_id,
                        "requested_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception as exc:
                logger.warning(
                    "[EXEC-CONTROL] Failed to broadcast pause request for %s: %s",
                    execution_id,
                    exc,
                )

        return {
            "status": result.get("status", "pause_pending"),
            "execution_id": execution_id,
            "thread_id": thread_id,
        }

    async def resume_manual_pause(
        self, db: Session, execution_id: str
    ) -> Dict[str, Any]:
        """Resume an execution that was manually paused."""

        execution = get_execution_by_id(db, execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")

        if execution.status != "paused":
            raise ValueError(
                f"Execution {execution_id} is not paused (status={execution.status})"
            )

        thread_id = self._resolve_thread_id(execution)
        checkpoint_id = self._get_manual_pause_checkpoint(execution, thread_id, db)
        if not checkpoint_id:
            raise ValueError(
                f"No manual pause checkpoint found for execution {execution_id}"
            )

        logger.info(
            "[EXEC-CONTROL] Resuming manual pause for execution %s (thread %s, checkpoint %s)",
            execution_id,
            thread_id,
            checkpoint_id,
        )

        active = self.execution_engine.active_executions.get(thread_id)
        if active:
            control = active.setdefault("control", {})
            control["pause_requested"] = False
            control["pause_ready"] = False
            control["pause_finalized"] = False
            control["pause_is_manual"] = False
            active.pop("paused", None)
            logger.info(
                "[EXEC-CONTROL] Cleared pause control state for execution %s before resume",
                execution_id,
            )

        resume_result = await self.execution_engine.resume_from_checkpoint(
            graph_name=execution.graph_name,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            new_input=None,
        )

        if active:
            active["status"] = "running"
            logger.info(
                "[EXEC-CONTROL] Execution %s resumed; status set to running",
                execution_id,
            )

        try:
            ExecutionHistoryService.update_graph_execution(
                execution_id=execution_id,
                status="running",
            )
        except Exception as exc:
            logger.warning(
                "[EXEC-CONTROL] Failed to mark execution %s running after resume: %s",
                execution_id,
                exc,
            )

        if ws_notifier:
            try:
                await ws_notifier.on_execution_resumed(
                    thread_id,
                    {"db_execution_id": execution_id, "manual": True},
                )
            except Exception as exc:
                logger.warning(
                    "[EXEC-CONTROL] Failed to broadcast manual resume for %s: %s",
                    execution_id,
                    exc,
                )

        return {
            "status": resume_result.get("status", "running"),
            "execution_id": execution_id,
            "thread_id": thread_id,
            "result": resume_result,
        }

    def _get_manual_pause_checkpoint(
        self, execution: Any, thread_id: str, db: Session
    ) -> Optional[str]:
        """Determine checkpoint ID associated with a manual pause."""

        active = self.execution_engine.active_executions.get(thread_id)
        if active:
            paused_state = active.get("paused") or {}
            control = active.get("control") or {}
            if paused_state.get("checkpoint_id") and (
                paused_state.get("manual") or control.get("pause_is_manual")
            ):
                return paused_state.get("checkpoint_id")

        try:
            manual_node = (
                db.query(NodeExecution)
                .filter(
                    NodeExecution.graph_execution_id == execution.id,
                    NodeExecution.node_type == "CHECKPOINT",
                    NodeExecution.status == "paused",
                )
                .order_by(NodeExecution.execution_order.desc())
                .first()
            )
            if manual_node and manual_node.node_metadata:
                metadata = manual_node.node_metadata or {}
                checkpoint = metadata.get("checkpoint_id")
                if checkpoint and (
                    metadata.get("manual_pause")
                    or manual_node.node_id == "__user_pause__"
                ):
                    return checkpoint
        except Exception as exc:
            logger.warning(
                "[EXEC-CONTROL] Failed to lookup manual pause checkpoint for %s: %s",
                execution.id,
                exc,
            )

        return None
