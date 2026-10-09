"""
Code Executor Node.

This module handles execution of CODE_EXECUTOR nodes, which run
Python or JavaScript code within workflows.
"""

import json
import time
from typing import Any, Dict, Optional

from backend.models.workflow import EnhancedNodeData
from backend.models.workflow.configs import CodeExecutorConfig
from backend.services.code_execution import CodeExecutionService, get_code_execution_service
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState

from ..base import BaseNodeExecutor
from ..handlers import NodeDatabaseTracker, NodeNotificationHandler


code_executor_logger = get_logger("nodes.executors.code")


class CodeNodeExecutor(BaseNodeExecutor):
    """
    Executor for CODE_EXECUTOR nodes.

    Handles code execution including:
    - Input variable mapping from workflow state
    - Python and JavaScript execution
    - Output capture and state updates
    - Database tracking and WebSocket notifications
    - Error handling with detailed messages
    """

    def __init__(
        self,
        execution_history_service: Any = None,
        ws_notifier: Any = None,
        subgraph_executor: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
    ):
        """Initialize code node executor."""
        super().__init__(
            execution_history_service, ws_notifier, subgraph_executor, graph_manager
        )
        self.database_tracker = NodeDatabaseTracker(execution_history_service)
        self.notification_handler = NodeNotificationHandler(ws_notifier)
        self.code_service = get_code_execution_service()

    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a code executor node.

        Args:
            node: The code executor node to execute
            state: Current workflow state
            graph: The graph definition
            execution_id: Execution identifier
            user_id: Optional user identifier

        Returns:
            State updates with code execution output
        """
        code_executor_logger.info(f"Executing CODE_EXECUTOR node: {node.name}")
        execution_start_time = time.time()

        node_exec_id = await self._create_tracking_record(node, state, graph)

        try:
            config = self._validate_config(node)

            variables = self._extract_input_variables(config, state, graph)

            code_executor_logger.info(
                f"Executing {config.language} code for {node.name} "
                f"with {len(variables)} input variables"
            )

            result = await self.code_service.execute(
                language=config.language,
                code=config.code,
                variables=variables,
                output_variable=config.output_variable,
                timeout_seconds=config.timeout_seconds,
                memory_limit_mb=config.memory_limit_mb,
                allow_network=config.allow_network,
                allow_filesystem=config.allow_filesystem,
                allow_subprocess=config.allow_subprocess,
                allowed_packages=config.allowed_packages,
                working_directory=config.working_directory,
                environment_variables=config.environment_variables,
                capture_stdout=config.capture_stdout,
                capture_stderr=config.capture_stderr,
            )

            node_output = self._build_node_output(result, config)

            execution_duration = time.time() - execution_start_time
            await self._complete_tracking(
                node, state, node_exec_id, node_output, execution_duration, graph
            )

            return self._build_state_update(node_output, state)

        except Exception as e:
            code_executor_logger.error(
                f"Code execution error for {node.name}: {e}", exc_info=True
            )
            return await self._handle_error(node, state, node_exec_id, str(e))

    def _validate_config(self, node: EnhancedNodeData) -> CodeExecutorConfig:
        """
        Validate and extract code executor configuration.

        Args:
            node: The code executor node

        Returns:
            CodeExecutorConfig instance

        Raises:
            ValueError: If configuration is missing or invalid
        """
        config = getattr(node, "code_executor_config", None)

        if not config:
            raise ValueError("Code executor configuration is missing")

        if isinstance(config, dict):
            config = CodeExecutorConfig.from_dict(config)

        if not config.code or not config.code.strip():
            raise ValueError("No code provided for execution")

        if config.language not in ("python", "javascript"):
            raise ValueError(f"Unsupported language: {config.language}")

        return config

    def _extract_input_variables(
        self,
        config: CodeExecutorConfig,
        state: WorkflowState,
        graph: Any,
    ) -> Dict[str, Any]:
        """
        Extract input variables from workflow state based on mappings.

        Args:
            config: Code executor configuration
            state: Current workflow state
            graph: The graph definition

        Returns:
            Dictionary of variable names to values
        """
        from backend.services.io import MappingValueExtractor

        variables = {}
        mapping_extractor = MappingValueExtractor()

        for mapping in config.input_variables:
            if isinstance(mapping, dict):
                var_name = mapping.get("variable_name")
                source_mode = mapping.get("source_mode", "previous")
                source_node_id = mapping.get("source_node_id")
                source_field_path = mapping.get("source_field_path")
                static_value = mapping.get("static_value")
                default_value = mapping.get("default_value")
            else:
                var_name = getattr(mapping, "variable_name", None)
                source_mode = getattr(mapping, "source_mode", "previous")
                source_node_id = getattr(mapping, "source_node_id", None)
                source_field_path = getattr(mapping, "source_field_path", None)
                static_value = getattr(mapping, "static_value", None)
                default_value = getattr(mapping, "default_value", None)

            if not var_name:
                continue

            value = mapping_extractor.extract(
                source_mode=source_mode,
                state=state,
                static_value=static_value,
                default_value=default_value,
                source_node_id=source_node_id,
                source_field_path=source_field_path,
                idx=0,
                sql_expressions=[],
            )

            variables[var_name] = value
            code_executor_logger.debug(
                f"Mapped variable '{var_name}' = {type(value).__name__}"
            )

        if not config.input_variables:
            node_outputs = state.get("node_outputs", {})
            if node_outputs:
                last_output = list(node_outputs.values())[-1] if node_outputs else {}
                if isinstance(last_output, dict):
                    if "raw" in last_output:
                        variables["input"] = last_output.get("raw", "")
                    if "structured" in last_output and last_output["structured"]:
                        variables["input_data"] = last_output["structured"]

        code_executor_logger.info(
            f"Extracted {len(variables)} input variables: {list(variables.keys())}"
        )

        return variables

    def _build_node_output(
        self,
        result: Any,
        config: CodeExecutorConfig,
    ) -> Dict[str, Any]:
        """
        Build node output from code execution result.

        Args:
            result: CodeExecutionResult from code service
            config: Code executor configuration

        Returns:
            Node output dictionary
        """
        output_data = {
            "success": result.success,
            "output": result.output,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
            "language": config.language,
        }

        if not result.success:
            code_executor_logger.warning(
                f"Code execution failed: {result.error}"
            )

        return output_data

    async def _create_tracking_record(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
    ) -> Optional[int]:
        """
        Create database tracking record and send start notification.

        Args:
            node: The code executor node
            state: Current workflow state
            graph: The graph definition

        Returns:
            Node execution ID, or None if tracking disabled
        """
        from backend.services.io import InputBuilder

        input_builder = InputBuilder()
        input_message = input_builder.build(node, state, graph)

        review_iteration = state.get("current_review_iteration")

        node_exec_id = await self.database_tracker.create_node_execution(
            node,
            state,
            "CODE_EXECUTOR",
            {"message": input_message},
            review_iteration=review_iteration,
        )

        if node_exec_id:
            current_order = self.database_tracker.get_execution_order(state)
            await self.notification_handler.notify_start(
                node,
                state,
                "CODE_EXECUTOR",
                node_exec_id=node_exec_id,
                execution_order=current_order,
            )

        return node_exec_id

    async def _complete_tracking(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        node_output: Dict[str, Any],
        duration_seconds: float,
        graph: Any,
    ) -> None:
        """
        Complete database tracking and send completion notification.

        Args:
            node: The code executor node
            state: Current workflow state
            node_exec_id: Database node execution ID
            node_output: Output data from code execution
            duration_seconds: Execution duration
            graph: The graph definition
        """
        await self.database_tracker.complete_node_execution(
            node_exec_id, node_output, None
        )

        if node_exec_id:
            from backend.services.io import InputBuilder

            input_builder = InputBuilder()
            input_message = input_builder.build(node, state, graph)

            current_order = self.database_tracker.get_execution_order(state)
            await self.notification_handler.notify_complete(
                node,
                state,
                node_output,
                "CODE_EXECUTOR",
                node_exec_id=node_exec_id,
                duration_seconds=duration_seconds,
                input_data={"message": input_message},
                execution_order=current_order,
            )

    def _build_state_update(
        self,
        node_output: Dict[str, Any],
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """
        Build state update dictionary.

        Args:
            node_output: Output from code execution
            state: Current workflow state

        Returns:
            State update dictionary
        """
        order_update = self.database_tracker.increment_execution_order(state)

        output_value = node_output.get("output")
        if output_value is None:
            raw_output = node_output.get("stdout", "")
        elif isinstance(output_value, (dict, list)):
            raw_output = json.dumps(output_value)
        else:
            raw_output = str(output_value)

        return {
            "node_output": {
                "raw": raw_output,
                "structured": node_output,
                "fields": node_output,
            },
            **order_update,
        }

    async def _handle_error(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        error_message: str,
    ) -> Dict[str, Any]:
        """
        Handle code execution error.

        Args:
            node: The code executor node
            state: Current workflow state
            node_exec_id: Database node execution ID
            error_message: Error message

        Returns:
            Error state update
        """
        error_output = {"error": error_message, "success": False}

        if node_exec_id:
            await self.database_tracker.complete_node_execution(
                node_exec_id, error_output, None
            )

        await self.notification_handler.notify_error(
            node, state, error_message, "CODE_EXECUTOR"
        )

        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_output": {
                "raw": json.dumps(error_output),
                "structured": error_output,
                "fields": error_output,
            },
            **order_update,
        }
