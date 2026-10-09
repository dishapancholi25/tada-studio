"""Execution History Service - Main facade.

This service provides a unified interface for tracking workflow execution history.
It delegates to specialized modules while maintaining backward compatibility with
the original API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from . import graph_execution, node_execution, queries


class ExecutionHistoryService:
    """Service for managing execution history.

    This class provides a facade over the modularized execution history components.
    All methods are static to maintain backward compatibility with existing code.

    The service handles:
    - Creating and updating graph execution records
    - Creating and updating node execution records
    - Querying execution history with various filters
    - Formatting execution data for API responses
    - Tracking execution statistics and summaries

    Examples:
        >>> # Create a graph execution
        >>> exec_data = ExecutionHistoryService.create_graph_execution(
        ...     graph_id="my_graph",
        ...     graph_name="My Workflow",
        ...     graph_definition={},
        ...     user_id="user@example.com"
        ... )
        >>> exec_id = exec_data["id"]

        >>> # Create a node execution
        >>> node_data = ExecutionHistoryService.create_node_execution(
        ...     graph_execution_id=exec_id,
        ...     node_id="node_1",
        ...     node_name="First Node",
        ...     node_type="AGENT"
        ... )

        >>> # Query execution history
        >>> executions = ExecutionHistoryService.get_graph_executions_dict(
        ...     user_id="user@example.com",
        ...     limit=10
        ... )
    """

    # ==================== Graph Execution Methods ====================

    @staticmethod
    def create_graph_execution(
        graph_id: str,
        graph_name: str,
        graph_definition: Dict[str, Any],
        input_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        websocket_execution_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        graph_definition_id: Optional[str] = None,
        evaluation_run_id: Optional[str] = None,
        trigger_type: Optional[str] = None,
        chat_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new graph execution record and return its data.

        Args:
            graph_id: Unique identifier for the graph
            graph_name: Human-readable graph name
            graph_definition: Graph structure definition
            input_data: Initial input data for execution
            user_id: User executing the graph
            thread_id: Thread ID for checkpoint tracking
            websocket_execution_id: WebSocket execution identifier
            workflow_id: Associated workflow UUID
            graph_definition_id: Graph definition UUID
            evaluation_run_id: Associated evaluation run UUID
            trigger_type: Execution trigger type (editor, api, evaluation, scheduler, chat)
            chat_session_id: Optional chat session ID for chat-triggered executions

        Returns:
            Dictionary with key execution fields (id, graph_id, status, etc.)
        """
        return graph_execution.create_graph_execution(
            graph_id=graph_id,
            graph_name=graph_name,
            graph_definition=graph_definition,
            input_data=input_data,
            user_id=user_id,
            thread_id=thread_id,
            websocket_execution_id=websocket_execution_id,
            workflow_id=workflow_id,
            graph_definition_id=graph_definition_id,
            evaluation_run_id=evaluation_run_id,
            trigger_type=trigger_type,
            chat_session_id=chat_session_id,
        )

    @staticmethod
    def update_graph_execution(
        execution_id: str,
        status: Optional[str] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        end_time: Optional[datetime] = None,
    ):
        """Update a graph execution record.

        Args:
            execution_id: Graph execution ID
            status: New status (e.g., "completed", "failed")
            output_data: Final output data
            error_message: Error message if execution failed
            end_time: Execution end time

        Returns:
            Updated GraphExecution object, or None if not found
        """
        return graph_execution.update_graph_execution(
            execution_id=execution_id,
            status=status,
            output_data=output_data,
            error_message=error_message,
            end_time=end_time,
        )

    @staticmethod
    def get_graph_execution(execution_id: str):
        """Get a graph execution by ID with eagerly loaded node executions.

        Args:
            execution_id: Graph execution ID

        Returns:
            GraphExecution object with node_executions loaded, or None if not found
        """
        return graph_execution.get_graph_execution(execution_id)

    @staticmethod
    def get_graph_executions(
        graph_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ):
        """Get graph executions with optional filtering.

        Args:
            graph_id: Filter by specific graph ID (optional)
            limit: Maximum number of results (default: 100)
            offset: Number of results to skip (default: 0)

        Returns:
            List of GraphExecution objects with node_executions eagerly loaded
        """
        return graph_execution.get_graph_executions(
            graph_id=graph_id, limit=limit, offset=offset
        )

    @staticmethod
    def delete_graph_execution(execution_id: str) -> bool:
        """Delete a graph execution and all associated data.

        Args:
            execution_id: Graph execution ID

        Returns:
            True if execution was found and deleted, False if not found
        """
        return graph_execution.delete_graph_execution(execution_id)

    @staticmethod
    def get_execution_summary(graph_id: str):
        """Get execution summary statistics for a graph.

        Args:
            graph_id: Graph ID

        Returns:
            ExecutionSummary object, or None if not found
        """
        return graph_execution.get_execution_summary(graph_id)

    @staticmethod
    def update_execution_summary(graph_id: str, execution_id: str):
        """Update execution summary statistics.

        Args:
            graph_id: Graph ID
            execution_id: Execution ID to include in statistics
        """
        return graph_execution.update_execution_summary(graph_id, execution_id)

    # ==================== Node Execution Methods ====================

    @staticmethod
    def create_node_execution(
        graph_execution_id: str,
        node_id: str,
        node_name: str,
        node_type: str,
        execution_order: Optional[int] = None,
        input_data: Optional[Dict[str, Any]] = None,
        node_metadata: Optional[Dict[str, Any]] = None,
        is_sub_agent: bool = False,
        parent_agent_id: Optional[str] = None,
        review_iteration: Optional[int] = None,
        invocation_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new node execution record and return its data.

        Args:
            graph_execution_id: Parent graph execution ID
            node_id: Unique node identifier
            node_name: Human-readable node name
            node_type: Type of node (e.g., "AGENT", "HTTP_REQUEST")
            execution_order: Execution order (auto-generated if None)
            input_data: Input data for the node
            node_metadata: Additional metadata
            is_sub_agent: Whether this is a sub-agent node
            parent_agent_id: Parent agent's node ID (for sub-agents)
            review_iteration: Review iteration number (1-indexed) for tool-to-iteration association
            invocation_index: Invocation index (for multi-call subagent flows)

        Returns:
            Dictionary with key node execution fields (id, node_id, status, execution_order)
        """
        return node_execution.create_node_execution(
            graph_execution_id=graph_execution_id,
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            execution_order=execution_order,
            input_data=input_data,
            node_metadata=node_metadata,
            is_sub_agent=is_sub_agent,
            parent_agent_id=parent_agent_id,
            review_iteration=review_iteration,
            invocation_index=invocation_index,
        )

    @staticmethod
    def start_node_execution(node_execution_id: str):
        """Mark a node execution as started.

        Args:
            node_execution_id: Node execution ID

        Returns:
            Updated NodeExecution object, or None if not found
        """
        return node_execution.start_node_execution(node_execution_id)

    @staticmethod
    def complete_node_execution(
        node_execution_id: str,
        status: str = "completed",
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        token_counts: Optional[Dict[str, Any]] = None,
        llm_metadata: Optional[Dict[str, Any]] = None,
        message_structure: Optional[Dict[str, Any]] = None,
        tool_metadata: Optional[Dict[str, Any]] = None,
        orchestration_metadata: Optional[Dict[str, Any]] = None,
        memory_metadata: Optional[Dict[str, Any]] = None,
        environment_metadata: Optional[Dict[str, Any]] = None,
        node_metadata: Optional[Dict[str, Any]] = None,
    ):
        """Mark a node execution as completed with enhanced metadata.

        Args:
            node_execution_id: Node execution ID
            status: Final status (default: "completed")
            output_data: Output data from node execution
            error_message: Error message if execution failed
            token_counts: Token usage counts
            llm_metadata: LLM-specific metadata (model, costs, performance)
            message_structure: Message structure metadata
            tool_metadata: Tool usage metadata
            orchestration_metadata: Orchestration metadata
            memory_metadata: Memory usage metadata
            environment_metadata: Environment metadata
            node_metadata: Additional node-specific metadata (e.g., interrupt payload)

        Returns:
            Updated NodeExecution object, or None if not found
        """
        return node_execution.complete_node_execution(
            node_execution_id=node_execution_id,
            status=status,
            output_data=output_data,
            error_message=error_message,
            token_counts=token_counts,
            llm_metadata=llm_metadata,
            message_structure=message_structure,
            tool_metadata=tool_metadata,
            orchestration_metadata=orchestration_metadata,
            memory_metadata=memory_metadata,
            environment_metadata=environment_metadata,
            node_metadata=node_metadata,
        )

    @staticmethod
    def mark_node_failed(
        node_execution_id: str,
        error: Optional[str] = None,
        output_data: Optional[Dict[str, Any]] = None,
    ):
        """Mark a node execution as failed.

        Convenience wrapper around complete_node_execution with status='failed'.

        Args:
            node_execution_id: Node execution ID
            error: Error message describing the failure
            output_data: Optional output data to store with the failure
        """
        return node_execution.complete_node_execution(
            node_execution_id=node_execution_id,
            status="failed",
            output_data=output_data,
            error_message=error,
        )

    @staticmethod
    def get_node_executions(graph_execution_id: str) -> List[Dict[str, Any]]:
        """Get all node executions for a graph execution.

        Args:
            graph_execution_id: Parent graph execution ID

        Returns:
            List of node execution dictionaries
        """
        return node_execution.get_node_executions(graph_execution_id)

    @staticmethod
    def get_running_sub_agents(graph_execution_id: str) -> List[Dict[str, Any]]:
        """Get all running sub-agents for a graph execution.

        Args:
            graph_execution_id: Parent graph execution ID

        Returns:
            List of running sub-agent dictionaries
        """
        return node_execution.get_running_sub_agents(graph_execution_id)

    @staticmethod
    def get_all_running_nodes(graph_execution_id: str) -> List[Dict[str, Any]]:
        """Get all running nodes (including sub-agents) for a graph execution.

        Args:
            graph_execution_id: Parent graph execution ID

        Returns:
            List of running node dictionaries
        """
        return node_execution.get_all_running_nodes(graph_execution_id)

    @staticmethod
    def get_node_execution_by_node_id(
        graph_execution_id: str, node_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a node execution by graph execution ID and node ID.

        Args:
            graph_execution_id: Parent graph execution ID
            node_id: Node identifier

        Returns:
            Node execution dictionary, or None if not found
        """
        return node_execution.get_node_execution_by_node_id(graph_execution_id, node_id)

    @staticmethod
    def update_node_execution_metadata(
        node_execution_id: str, update_data: Dict[str, Any]
    ):
        """Update node execution metadata without completing it.

        This allows updating status, output_data, and node_metadata fields
        without setting end_time or marking the execution as completed.
        Useful for tracking pending review state.

        Args:
            node_execution_id: Node execution ID
            update_data: Dictionary with fields to update. Supported fields:
                - status: New status (e.g., "pending_review", "running")
                - output_data: Output data dictionary
                - node_metadata: Metadata dictionary (merged with existing)

        Returns:
            Updated NodeExecution object, or None if not found
        """
        return node_execution.update_node_execution_metadata(
            node_execution_id=node_execution_id,
            update_data=update_data,
        )

    # ==================== Query Methods (with formatting) ====================

    @staticmethod
    def get_graph_execution_dict(execution_id: str) -> Optional[Dict[str, Any]]:
        """Get a graph execution by ID as a dictionary.

        Supports lookup by either database UUID or WebSocket execution ID.

        Args:
            execution_id: Either the database UUID or the WebSocket execution ID

        Returns:
            Dictionary representation of the graph execution, or None if not found
        """
        return queries.get_graph_execution_dict(execution_id)

    @staticmethod
    def get_graph_executions_dict(
        graph_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        graph_name: Optional[str] = None,
        status: Optional[str] = None,
        include_nodes: bool = True,
        trigger_type: Optional[str] = None,
        feedback_rating: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get graph executions as dictionaries with optional filtering.

        Includes user-based access control via workflow ownership/membership.

        Args:
            graph_id: Filter by specific graph ID (optional)
            user_id: Filter by user's accessible workflows (optional)
            limit: Maximum number of results (default: 100)
            offset: Number of results to skip (default: 0)
            graph_name: Filter by graph name (partial, case-insensitive) (optional)
            status: Filter by execution status (optional)
            include_nodes: Whether to include node_executions (default: True)
            trigger_type: Filter by trigger type (editor, api, evaluation, scheduler) (optional)

        Returns:
            Dictionary with 'executions', 'total_count', and 'has_more' fields
        """
        executions, total_count = queries.get_graph_executions_dict(
            graph_id=graph_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
            graph_name=graph_name,
            status=status,
            include_nodes=include_nodes,
            trigger_type=trigger_type,
            feedback_rating=feedback_rating,
            workflow_id=workflow_id,
        )
        return {
            "executions": executions,
            "total_count": total_count,
            "has_more": offset + len(executions) < total_count,
        }

    @staticmethod
    def get_distinct_workflow_names(user_id: Optional[str] = None) -> List[str]:
        """Get distinct workflow names accessible to a user.

        Args:
            user_id: Filter by user's accessible workflows (optional)

        Returns:
            List of distinct workflow names, sorted alphabetically
        """
        return queries.get_distinct_workflow_names(user_id=user_id)

    @staticmethod
    def get_node_execution(execution_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific node execution by execution_id and node_id.

        Supports execution_id as either WebSocket ID or database UUID.

        Args:
            execution_id: Graph execution ID (WebSocket or UUID)
            node_id: Node identifier

        Returns:
            Dictionary representation of the node execution, or None if not found
        """
        return queries.get_node_execution(execution_id, node_id)

    @staticmethod
    def get_node_execution_by_id(node_exec_id: str) -> Optional[Dict[str, Any]]:
        """Get a node execution by its primary key ID.

        Args:
            node_exec_id: Node execution database ID

        Returns:
            Dictionary representation of the node execution, or None if not found
        """
        return queries.get_node_execution_by_id(node_exec_id)
