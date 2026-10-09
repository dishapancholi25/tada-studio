"""
Condition Node Executor.

This module handles execution of CONDITION nodes, evaluating conditions
and determining which branch to take in the workflow.
"""

from typing import Any, Dict, Optional

from backend.models.workflow import EnhancedNodeData
from backend.services.execution.history import ExecutionHistoryService
from backend.services.conditions import ConditionEvaluator
from backend.services.config import get_logger
from backend.services.execution.state import StateExecutionTracker
from backend.services.websocket import notifier as ws_notifier
from backend.services.workflow.state import WorkflowState

from ..base import BaseNodeExecutor


condition_executor_logger = get_logger("nodes.executors.condition")


class ConditionNodeExecutor(BaseNodeExecutor):
    """
    Executor for CONDITION nodes.

    Evaluates conditions (binary, multi-branch, expression, LLM) and determines
    the next node to execute based on the condition result.
    """

    def __init__(self, **kwargs):
        """Initialize condition node executor with dependencies."""
        super().__init__(**kwargs)
        # Initialize condition evaluator with graph_manager
        self.condition_evaluator = ConditionEvaluator(kwargs.get("graph_manager"))

    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a condition node and track which branch was taken.

        Args:
            node: The condition node to execute
            state: Current workflow state
            graph: The graph definition
            execution_id: Execution identifier
            user_id: Optional user identifier

        Returns:
            Output data with branch information
        """
        condition_executor_logger.info(
            f"Processing CONDITION node: {node.name} (id={node.uniq_id})"
        )

        # Log the condition config summary
        condition_config = node.condition_config
        if condition_config:
            if hasattr(condition_config, "__dict__"):
                branch_mode = getattr(condition_config, "branch_mode", "binary")
                condition_type = getattr(condition_config, "condition_type", "simple")
                input_source = getattr(condition_config, "input_source", "previous")
                field_path = getattr(condition_config, "field_path", "")
            else:
                branch_mode = condition_config.get("branch_mode", "binary")
                condition_type = condition_config.get("condition_type", "simple")
                input_source = condition_config.get("input_source", "previous")
                field_path = condition_config.get("field_path", "")
            condition_executor_logger.info(
                f"  Config: branch_mode={branch_mode}, condition_type={condition_type}, "
                f"input_source={input_source}, field_path={field_path!r}"
            )
        else:
            condition_executor_logger.info("  Config: None (using defaults)")

        # Evaluate the condition
        output_data = self._evaluate_condition(node, state, graph)

        condition_executor_logger.info(
            f"  Result: branch_taken={output_data.get('branch_taken')}, "
            f"source_handle={output_data.get('source_handle')!r}, "
            f"branch_label={output_data.get('branch_label')!r}, "
            f"condition_result={output_data.get('condition_result')!r}"
        )

        # Store result in state for condition function to use
        state[f"__condition_result_{node.uniq_id}"] = output_data["condition_result"]

        # Track in database
        await self._track_condition(node, state, graph, output_data)

        return output_data

    def _evaluate_condition(
        self, node: EnhancedNodeData, state: WorkflowState, graph: Any
    ) -> Dict[str, Any]:
        """
        Evaluate the condition and determine branch.

        Args:
            node: The condition node
            state: Current workflow state
            graph: Graph definition

        Returns:
            Dictionary with branch information
        """
        condition_config = node.condition_config
        if not condition_config:
            return self._default_branch()

        # Extract configuration (handle dict or dataclass)
        if hasattr(condition_config, "__dict__"):
            branch_mode = getattr(condition_config, "branch_mode", "binary")
            condition_type = getattr(condition_config, "condition_type", "simple")
        else:
            branch_mode = condition_config.get("branch_mode", "binary")
            condition_type = condition_config.get("condition_type", "simple")

        # Evaluate based on mode
        if branch_mode == "multi":
            return self._evaluate_multi_branch(node, state, condition_config)
        elif condition_type == "expression":
            return self._evaluate_expression(state, condition_config)
        elif condition_type == "llm":
            return self._evaluate_llm(state, condition_config, graph)
        else:
            return self._evaluate_binary(state, condition_config)

    def _evaluate_multi_branch(
        self, node: EnhancedNodeData, state: WorkflowState, condition_config: Any
    ) -> Dict[str, Any]:
        """
        Evaluate multi-branch condition.

        Args:
            node: The condition node
            state: Current workflow state
            condition_config: Condition configuration

        Returns:
            Branch information dictionary
        """
        branches = (
            getattr(condition_config, "branches", [])
            if hasattr(condition_config, "__dict__")
            else condition_config.get("branches", [])
        )

        condition_executor_logger.info(
            f"Evaluating multi-branch condition with {len(branches)} branches"
        )

        # Use new condition evaluator, passing parent config for source fallback
        result_str = self.condition_evaluator.evaluate_multi_branch(
            state, branches, condition_config
        )
        result_idx = int(result_str) if result_str.isdigit() else 0

        # Get branch information
        if result_idx < len(branches):
            branch = branches[result_idx]
            if hasattr(branch, "__dict__"):
                handle_id = getattr(branch, "handle_id", f"branch-{result_idx}")
                label = getattr(branch, "label", handle_id)
            else:
                handle_id = branch.get("handle_id", f"branch-{result_idx}")
                label = branch.get("label", handle_id)
        else:
            handle_id = f"branch-{result_idx}"
            label = "Default"

        condition_executor_logger.info(
            f"Condition {node.name} evaluated to branch {label} (index {result_idx})"
        )

        return {
            "branch_taken": result_idx,
            "source_handle": handle_id,
            "branch_label": label,
            "condition_result": result_str,
        }

    def _evaluate_expression(
        self, state: WorkflowState, condition_config: Any
    ) -> Dict[str, Any]:
        """
        Evaluate expression-based condition.

        Args:
            state: Current workflow state
            condition_config: Condition configuration

        Returns:
            Branch information dictionary
        """
        # Use new condition evaluator
        result = self.condition_evaluator.evaluate_expression(state, condition_config)

        return {
            "branch_taken": 0 if result else 1,
            "source_handle": "true" if result else "false",
            "branch_label": "True" if result else "False",
            "condition_result": "true" if result else "false",
        }

    def _evaluate_llm(
        self, state: WorkflowState, condition_config: Any, graph: Any
    ) -> Dict[str, Any]:
        """
        Evaluate LLM-based condition.

        Args:
            state: Current workflow state
            condition_config: Condition configuration
            graph: Graph definition

        Returns:
            Branch information dictionary
        """
        # Use new condition evaluator
        condition_result = self.condition_evaluator.evaluate_llm(
            state, condition_config, graph
        )

        return {
            "branch_taken": None,
            "source_handle": condition_result,
            "branch_label": condition_result.title(),
            "condition_result": condition_result,
        }

    def _evaluate_binary(
        self, state: WorkflowState, condition_config: Any
    ) -> Dict[str, Any]:
        """
        Evaluate binary (true/false) condition.

        Args:
            state: Current workflow state
            condition_config: Condition configuration

        Returns:
            Branch information dictionary
        """
        # Use new condition evaluator
        result = self.condition_evaluator.evaluate_binary_condition(
            state, condition_config
        )

        return {
            "branch_taken": 0 if result else 1,
            "source_handle": "true" if result else "false",
            "branch_label": "True" if result else "False",
            "condition_result": "true" if result else "false",
        }

    def _default_branch(self) -> Dict[str, Any]:
        """Return default branch information when no condition is configured."""
        return {
            "branch_taken": 0,
            "source_handle": "true",
            "branch_label": "True",
            "condition_result": "true",
        }

    async def _track_condition(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        output_data: Dict[str, Any],
    ) -> None:
        """
        Track condition execution in database and send WebSocket notifications.

        Args:
            node: The condition node
            state: Current workflow state
            graph: Graph definition
            output_data: Condition evaluation output
        """
        db_execution_id = state.get("db_execution_id")
        if not db_execution_id:
            return

        try:
            from backend.services.execution import get_executor

            executor = get_executor()

            current_order = StateExecutionTracker.get_execution_order(state)

            # Build input data once and reuse for DB record + WebSocket completion payload,
            # so the frontend receives the same input snapshot over both channels.
            input_data = {
                "message": executor._build_node_input(node, state, graph)
            }

            # Create node execution record
            node_exec = ExecutionHistoryService.create_node_execution(
                graph_execution_id=db_execution_id,
                node_id=node.uniq_id,
                node_name=node.name,
                node_type="CONDITION",
                execution_order=current_order,
                input_data=input_data,
            )
            node_exec_id = node_exec["id"]
            ExecutionHistoryService.start_node_execution(node_exec_id)

            # Send WebSocket notification for start
            ws_execution_id = state.get("execution_id")
            if ws_notifier and ws_execution_id:
                await ws_notifier.on_node_start(
                    ws_execution_id,
                    node.uniq_id,
                    node.name,
                    "CONDITION",
                    False,
                    None,
                    node_exec_id,
                    current_order,
                )

            # Complete the execution
            ExecutionHistoryService.complete_node_execution(
                node_exec_id, output_data=output_data, status="completed"
            )

            # Send WebSocket notification for completion
            if ws_notifier and ws_execution_id:
                await ws_notifier.on_node_complete(
                    ws_execution_id,
                    node.uniq_id,
                    node.name,
                    output_data,
                    "CONDITION",
                    0.1,  # duration_seconds
                    input_data,  # input_data
                    None,  # start_time
                    None,  # end_time
                    None,  # input_tokens
                    None,  # output_tokens
                    None,  # total_tokens
                    False,  # is_sub_agent
                    None,  # parent_agent_id
                    node_exec_id,  # database_node_id
                    current_order,  # execution_order
                )

        except Exception as e:
            condition_executor_logger.error(
                f"Failed to track CONDITION node execution: {e}"
            )
