"""
Database Node Executor (Refactored).

This module handles execution of DATABASE_INSERT nodes using a clean,
modular architecture with proper separation of concerns.
"""

import json
from typing import Any, Dict, Optional

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.io.extractors import MappingValueExtractor
from backend.services.io.input import InputBuilder
from backend.services.workflow.state import WorkflowState

from ...base import BaseNodeExecutor
from ...handlers import NodeDatabaseTracker, NodeNotificationHandler
from .config import DatabaseInsertConfig
from .connection_manager import DatabaseConnectionManager
from .exceptions import (
    DatabaseConnectionError,
    DatabaseNodeError,
    QueryExecutionError,
)
from .query_builder import DatabaseQueryBuilder


database_executor_logger = get_logger("nodes.executors.database")


class DatabaseNodeExecutor(BaseNodeExecutor):
    """
    Executor for DATABASE_INSERT nodes.

    This refactored executor uses:
    - NodeDatabaseTracker for execution history
    - NodeNotificationHandler for WebSocket notifications
    - DatabaseConnectionManager for connection handling
    - DatabaseQueryBuilder for query construction
    - MappingValueExtractor for value extraction
    - InputBuilder for input formatting

    Handles database insertions with column mapping, connection management,
    and proper error handling using a clean service-oriented architecture.
    """

    def __init__(
        self,
        execution_history_service: Any = None,
        ws_notifier: Any = None,
        subgraph_executor: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
        mapping_extractor: Optional[MappingValueExtractor] = None,
        input_builder: Optional[InputBuilder] = None,
    ):
        """
        Initialize database node executor with dependencies.

        Args:
            execution_history_service: Service for tracking execution history
            ws_notifier: WebSocket notifier for real-time updates
            subgraph_executor: Executor for handling subgraphs
            graph_manager: Manager for graph operations
            mapping_extractor: Service for extracting values from mappings
            input_builder: Service for building node inputs
        """
        super().__init__(
            execution_history_service, ws_notifier, subgraph_executor, graph_manager
        )

        # Use existing handler infrastructure
        self.database_tracker = NodeDatabaseTracker(execution_history_service)
        self.notification_handler = NodeNotificationHandler(ws_notifier)

        # Inject IO services (removes circular dependency on engine)
        self.mapping_extractor = mapping_extractor or MappingValueExtractor()
        self.input_builder = input_builder or InputBuilder()

        # Database-specific services
        self.connection_manager = DatabaseConnectionManager()
        self.query_builder = DatabaseQueryBuilder(self.mapping_extractor)

    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a database insert node.

        Args:
            node: The database insert node to execute
            state: Current workflow state
            graph: The graph definition
            execution_id: Execution identifier
            user_id: Optional user identifier

        Returns:
            State updates with insertion results
        """
        database_executor_logger.info(
            f"[DATABASE-EXECUTOR] Executing DATABASE_INSERT node: {node.name}"
        )

        # Create database tracking record
        node_exec_id = await self._create_tracking_record(node, state, graph)

        # Send start notification
        await self.notification_handler.notify_start(
            node, state, "DATABASE_INSERT", node_exec_id
        )

        try:
            # Validate and extract configuration
            config = self._validate_and_parse_config(node)

            database_executor_logger.info(
                f"[DATABASE-EXECUTOR] Insert configuration: "
                f"table={config.table_name}, "
                f"columns={len(config.column_mappings)}"
            )

            # Get database connection details
            connection_details = self.connection_manager.get_connection_details(
                config.connection_id
            )

            # Build INSERT query
            query, values = self.query_builder.build_insert_query(config, state)

            # Execute the query
            node_output = self._execute_insert(
                connection_details, query, values, config
            )

            database_executor_logger.info(
                f"[DATABASE-EXECUTOR] Insert completed successfully: "
                f"{node_output.get('rows_inserted', 0)} rows inserted"
            )

            # Complete tracking
            await self._complete_tracking(node, state, node_exec_id, node_output)

            # Return state updates
            return self._build_state_update(state, node_output)

        except DatabaseNodeError as e:
            # Database-specific errors (already logged in services)
            database_executor_logger.error(
                f"[DATABASE-EXECUTOR] Database error in {node.name}: {e}"
            )
            return await self._handle_error(node, state, node_exec_id, str(e))

        except Exception as e:
            # Unexpected errors
            database_executor_logger.error(
                f"[DATABASE-EXECUTOR] Unexpected error in {node.name}: {e}",
                exc_info=True,
            )
            return await self._handle_error(
                node, state, node_exec_id, f"Unexpected error: {e}"
            )

    def _validate_and_parse_config(
        self, node: EnhancedNodeData
    ) -> DatabaseInsertConfig:
        """
        Validate and parse database insert configuration.

        Args:
            node: The node to validate

        Returns:
            Validated DatabaseInsertConfig

        Raises:
            ValueError: If configuration is missing or invalid
        """
        database_executor_logger.debug(
            f"[DATABASE-EXECUTOR] Validating configuration for {node.name}"
        )

        config = node.database_insert_config
        if not config:
            raise ValueError("Database insert configuration is missing")

        # Parse into typed configuration
        return DatabaseInsertConfig.from_node_config(config)

    def _execute_insert(
        self,
        connection_details: Any,
        query: str,
        values: list,
        config: DatabaseInsertConfig,
    ) -> Dict[str, Any]:
        """
        Execute the INSERT query and return results.

        Args:
            connection_details: Database connection parameters
            query: SQL query to execute
            values: Values for query placeholders
            config: Database insert configuration

        Returns:
            Dictionary with success status and inserted data

        Raises:
            QueryExecutionError: If query execution fails
        """
        database_executor_logger.info(
            f"[DATABASE-EXECUTOR] Executing INSERT query with {len(values)} parameters"
        )

        conn = None
        try:
            # Create connection
            conn = self.connection_manager.create_psycopg2_connection(
                connection_details
            )

            # Execute query with cursor
            if config.return_inserted_rows:
                inserted_rows = self.connection_manager.execute_with_cursor(
                    conn, query, values, return_results=True
                )
                return {
                    "success": True,
                    "rows_inserted": len(inserted_rows),
                    "data": inserted_rows,
                }
            else:
                rows_affected = self.connection_manager.execute_with_cursor(
                    conn, query, values, return_results=False
                )
                return {
                    "success": True,
                    "rows_inserted": rows_affected,
                }

        except DatabaseConnectionError:
            raise
        except Exception as e:
            database_executor_logger.error(
                f"[DATABASE-EXECUTOR] Query execution failed: {e}", exc_info=True
            )
            raise QueryExecutionError(query, str(e)) from e
        finally:
            if conn:
                try:
                    conn.close()
                    database_executor_logger.debug(
                        "[DATABASE-EXECUTOR] Connection closed"
                    )
                except Exception as e:
                    database_executor_logger.warning(
                        f"[DATABASE-EXECUTOR] Failed to close connection: {e}"
                    )

    async def _create_tracking_record(
        self, node: EnhancedNodeData, state: WorkflowState, graph: Any
    ) -> Optional[int]:
        """
        Create database tracking record for node execution.

        Uses NodeDatabaseTracker for consistent tracking across all executors.

        Args:
            node: The node being executed
            state: Current workflow state
            graph: Graph definition

        Returns:
            Node execution ID, or None if tracking disabled
        """
        try:
            # Build input data using InputBuilder
            input_data = {"message": self.input_builder.build(node, state, graph)}

            # Get review iteration from state (set by upstream agent nodes)
            review_iteration = state.get("current_review_iteration")

            # Create tracking record
            return await self.database_tracker.create_node_execution(
                node=node,
                state=state,
                node_type="DATABASE_INSERT",
                input_data=input_data,
                review_iteration=review_iteration,
            )

        except Exception as e:
            database_executor_logger.error(
                f"[DATABASE-EXECUTOR] Failed to create tracking record: {e}",
                exc_info=True,
            )
            return None

    async def _complete_tracking(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        output: Dict[str, Any],
    ) -> None:
        """
        Complete database tracking record.

        Uses NodeDatabaseTracker and NodeNotificationHandler.

        Args:
            node: The node that completed
            state: Current workflow state
            node_exec_id: Database node execution ID
            output: Node output data
        """
        # Complete database tracking
        await self.database_tracker.complete_node_execution(
            node_exec_id=node_exec_id,
            output_data=output,
        )

        # Send WebSocket notification
        await self.notification_handler.notify_complete(
            node=node,
            state=state,
            output=output,
            node_type="DATABASE_INSERT",
            node_exec_id=node_exec_id,
        )

    async def _handle_error(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        error_msg: str,
    ) -> Dict[str, Any]:
        """
        Handle execution error.

        Uses NodeDatabaseTracker and NodeNotificationHandler.

        Args:
            node: The node that failed
            state: Current workflow state
            node_exec_id: Database node execution ID
            error_msg: Error message

        Returns:
            Error state update
        """
        error_output = {"error": error_msg, "success": False}

        # Mark as failed in database
        await self.database_tracker.fail_node_execution(
            node_exec_id=node_exec_id,
            error_message=error_msg,
            error_output=error_output,
        )

        # Send WebSocket error notification
        await self.notification_handler.notify_error(
            node=node,
            state=state,
            error_message=error_msg,
            node_type="DATABASE_INSERT",
            node_exec_id=node_exec_id,
        )

        # Return error state update
        return self._build_state_update(state, error_output)

    def _build_state_update(
        self, state: WorkflowState, output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build state update dictionary.

        Uses NodeDatabaseTracker for execution order management.

        Args:
            state: Current workflow state
            output: Node output data

        Returns:
            State update dictionary
        """
        # Increment execution order
        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_output": {
                "raw": json.dumps(output),
                "structured": output,
                "fields": output,
            },
            **order_update,
        }
