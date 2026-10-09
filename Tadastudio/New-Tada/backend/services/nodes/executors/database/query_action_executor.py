"""
Database Query Action Node Executor.

Executes DATABASE_QUERY_ACTION nodes as sequential workflow steps.
Reuses DatabaseConnectionManager for connection handling.
Config shape mirrors DatabaseQueryConfig (same UI).
"""

from typing import Any, Dict, List, Optional

import json

from backend.models.workflow import EnhancedNodeData
from backend.models.workflow.configs import DatabaseQueryActionConfig
from backend.services.config import get_logger
from backend.services.execution.history.serialization import make_json_serializable
from backend.services.io.input import InputBuilder
from backend.services.workflow.state import WorkflowState

from ...base import BaseNodeExecutor
from ...handlers import NodeDatabaseTracker, NodeNotificationHandler
from .connection_manager import DatabaseConnectionManager
from .exceptions import DatabaseConnectionError, DatabaseNodeError, QueryExecutionError


logger = get_logger("nodes.executors.database.query_action")


class DatabaseQueryActionNodeExecutor(BaseNodeExecutor):
    """
    Executor for DATABASE_QUERY_ACTION nodes.

    Runs a SQL query directly in the workflow sequence (not via an AI agent).
    The config shape is identical to DatabaseQueryConfig so the same frontend
    panel (DatabaseQueryPropertiesPanel) can be reused.
    """

    def __init__(
        self,
        execution_history_service: Any = None,
        ws_notifier: Any = None,
        subgraph_executor: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
        input_builder: Optional[InputBuilder] = None,
    ):
        super().__init__(
            execution_history_service, ws_notifier, subgraph_executor, graph_manager
        )
        self.database_tracker = NodeDatabaseTracker(execution_history_service)
        self.notification_handler = NodeNotificationHandler(ws_notifier)
        self.connection_manager = DatabaseConnectionManager()
        self.input_builder = input_builder or InputBuilder()

    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a DATABASE_QUERY_ACTION node."""
        logger.info(f"[DB-QUERY-ACTION] Executing node: {node.name}")

        node_exec_id = await self._create_tracking_record(node, state, graph)
        await self.notification_handler.notify_start(
            node, state, "DATABASE_QUERY_ACTION", node_exec_id
        )

        try:
            config = self._get_config(node)
            connection_details = self.connection_manager.get_connection_details(
                config.connection_id
            )
            rows = self._run_query(connection_details, config)
            rows = make_json_serializable(rows)

            output = {
                "success": True,
                "rows_returned": len(rows),
                "data": rows,
            }

            logger.info(
                f"[DB-QUERY-ACTION] Query completed: {output['rows_returned']} rows"
            )

            await self._complete_tracking(node, state, node_exec_id, output)
            return self._build_state_update(state, output)

        except DatabaseNodeError as e:
            logger.error(f"[DB-QUERY-ACTION] Database error in {node.name}: {e}")
            return await self._handle_error(node, state, node_exec_id, str(e))

        except Exception as e:
            logger.error(
                f"[DB-QUERY-ACTION] Unexpected error in {node.name}: {e}",
                exc_info=True,
            )
            return await self._handle_error(
                node, state, node_exec_id, f"Unexpected error: {e}"
            )

    # ── private helpers ───────────────────────────────────────────────────────

    def _get_config(self, node: EnhancedNodeData) -> DatabaseQueryActionConfig:
        """Extract and validate node configuration."""
        cfg = node.database_query_action_config
        if not cfg:
            raise ValueError("database_query_action_config is missing")
        if isinstance(cfg, dict):
            valid_fields = {f.name for f in __import__("dataclasses").fields(DatabaseQueryActionConfig)}
            cfg = DatabaseQueryActionConfig(**{k: v for k, v in cfg.items() if k in valid_fields})
        if not cfg.connection_id:
            raise ValueError("connection_id is required")
        return cfg

    def _run_query(
        self,
        connection_details: Any,
        config: DatabaseQueryActionConfig,
    ) -> List[Dict[str, Any]]:
        """Open connection, run the query, close connection, return rows."""
        # Determine query — use table_names/allowed_operations when no explicit
        # custom query is provided (mirrors how the tool node works).
        tables = config.table_names or ([config.table_name] if config.table_name else [])
        if tables:
            table_str = ", ".join(tables)
            if config.selected_columns:
                # Quote identifiers defensively; column names come from the
                # schema introspection endpoint, not free-form user text.
                column_str = ", ".join(f'"{col}"' for col in config.selected_columns)
            else:
                column_str = "*"
            query = f"SELECT {column_str} FROM {table_str} LIMIT {config.max_rows}"
        else:
            raise QueryExecutionError("", "No table specified for query")

        logger.debug(f"[DB-QUERY-ACTION] Query: {query}")

        conn = None
        try:
            conn = self.connection_manager.create_psycopg2_connection(connection_details)
            rows = self.connection_manager.execute_select_with_limit(
                conn, query, {}, config.max_rows
            )
            return rows
        except DatabaseConnectionError:
            raise
        except Exception as e:
            logger.error(f"[DB-QUERY-ACTION] Query failed: {e}", exc_info=True)
            raise QueryExecutionError(query, str(e)) from e
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    async def _create_tracking_record(
        self, node: EnhancedNodeData, state: WorkflowState, graph: Any
    ) -> Optional[int]:
        try:
            input_data = {"message": self.input_builder.build(node, state, graph)}
            review_iteration = state.get("current_review_iteration")
            return await self.database_tracker.create_node_execution(
                node=node,
                state=state,
                node_type="DATABASE_QUERY_ACTION",
                input_data=input_data,
                review_iteration=review_iteration,
            )
        except Exception as e:
            logger.error(f"[DB-QUERY-ACTION] Failed to create tracking record: {e}")
            return None

    async def _complete_tracking(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        output: Dict[str, Any],
    ) -> None:
        try:
            await self.database_tracker.complete_node_execution(
                node_exec_id=node_exec_id,
                output_data=output,
            )
            await self.notification_handler.notify_complete(
                node=node,
                state=state,
                output=output,
                node_type="DATABASE_QUERY_ACTION",
                node_exec_id=node_exec_id,
            )
        except Exception as e:
            logger.error(f"[DB-QUERY-ACTION] Failed to complete tracking: {e}")

    async def _handle_error(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        error_msg: str,
    ) -> Dict[str, Any]:
        error_output = {"success": False, "error": error_msg, "rows_returned": 0}
        try:
            await self.database_tracker.fail_node_execution(
                node_exec_id=node_exec_id,
                error_message=error_msg,
                error_output=error_output,
            )
            await self.notification_handler.notify_error(
                node, state, error_msg, "DATABASE_QUERY_ACTION", node_exec_id
            )
        except Exception:
            pass
        return self._build_state_update(state, error_output)

    def _build_state_update(
        self, state: WorkflowState, output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build state update dictionary, mirroring DatabaseNodeExecutor's shape."""
        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_output": {
                "raw": json.dumps(output, default=str),
                "structured": output,
                "fields": output,
            },
            **order_update,
        }
