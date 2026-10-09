"""Synchronous delegation tool factory.

This module provides the main factory for creating delegation tools
that can be used by orchestrator agents.
"""

from typing import List, Optional

from langchain_core.tools import Tool
from langgraph.errors import GraphInterrupt

from backend.models.workflow import EnhancedNodeData, NodeType
from backend.services.config import get_logger
from backend.services.delegation.executors import (
    SimpleDelegationExecutor,
)
from backend.services.delegation.factories.base import BaseDelegationToolFactory
from backend.services.delegation.factories.subworkflow import create_subworkflow_tool
from backend.services.delegation.models import DelegationRequest
from backend.services.execution.context import (
    get_current_db_execution_id,
    get_current_execution_id,
    get_node_execution_id,
)

logger = get_logger("delegation.factory.sync")


def _prepare_file_reference_task_description(task_description: str) -> str:
    """Add tool-use instructions when the delegated task is only a file ref."""

    try:
        from backend.services.file_content_references import (
            get_file_content_reference_metadata,
            get_file_content_reference_token,
        )

        stripped_task = task_description.strip()
        token = get_file_content_reference_token(stripped_task)
        if not token:
            return task_description

        metadata = get_file_content_reference_metadata(stripped_task) or {}
        filename = str(metadata.get("filename") or "uploaded_file.pdf")
        return (
            "Use the uploaded file for this delegated task.\n"
            f"Filename: {filename}\n"
            f"File/base64 payload: {token}\n"
            "When calling a tool, pass the File/base64 payload value exactly as "
            "the base64/file input and pass the filename as fileName. Do not "
            "decode, summarize, regenerate, or replace the payload."
        )
    except Exception as exc:
        logger.warning(f"Failed to prepare file reference delegation task: {exc}")
        return task_description


class AgentDelegationToolFactory(BaseDelegationToolFactory):
    """Factory for creating synchronous delegation tools.

    This factory creates tools that wrap agent nodes, allowing orchestrator
    agents to delegate tasks to sub-agents.
    """

    def create_delegation_tool(
        self,
        agent_node: EnhancedNodeData,
        orchestrator_id: str,
        description: Optional[str] = None,
        parent_execution_id: Optional[str] = None,
        parent_db_execution_id: Optional[str] = None,
    ) -> Tool:
        """Create a delegation tool that wraps an agent node.

        Args:
            agent_node: The agent node to wrap as a tool
            orchestrator_id: ID of the orchestrator agent
            description: Optional custom description for the tool
            parent_execution_id: Optional parent execution ID
            parent_db_execution_id: Optional parent database execution ID

        Returns:
            Tool instance that can be used by the orchestrator

        Raises:
            ValueError: If agent_node is not an AGENT type
        """
        if agent_node.type != NodeType.AGENT:
            raise ValueError(f"Node {agent_node.name} is not an AGENT node")

        tool_name, tool_description = self._get_tool_name_and_description(
            agent_node, description
        )

        logger.info(
            f"Creating delegation tool: {tool_name} for agent {agent_node.name}"
        )

        # Capture the Phoenix project name at tool-creation time so it can
        # be restored inside the delegation thread / fresh context.  The
        # ContextVar is lost when LangChain runs a sync tool via
        # run_in_executor and again when run_async_in_sync_isolated creates
        # a fresh contextvars.Context().
        try:
            from backend.services.phoenix.project_routing import get_current_project

            _captured_phoenix_project = get_current_project()
        except Exception:
            _captured_phoenix_project = None

        # Create delegation function
        def delegate_to_agent(task_description: str) -> str:
            """Delegate a task to the wrapped agent.

            Args:
                task_description: Description of the task to delegate

            Returns:
                Response from the delegated agent
            """
            logger.info("=== DELEGATION START ===")
            logger.info(f"Orchestrator: {orchestrator_id}")
            logger.info(f"Delegating to: {agent_node.name} ({agent_node.uniq_id})")
            logger.info(f"Task: {task_description}")
            delegation_task_description = _prepare_file_reference_task_description(
                task_description
            )

            # Restore Phoenix project routing.  This sync function may run
            # in a thread pool (LangChain's run_in_executor for sync tools)
            # where the parent's ContextVar is not inherited.
            _project_ctx = None
            if _captured_phoenix_project:
                try:
                    from backend.services.phoenix.project_routing import using_project

                    _project_ctx = using_project(_captured_phoenix_project)
                    _project_ctx.__enter__()
                except Exception:
                    _project_ctx = None

            try:
                # Get execution context
                context = self._get_execution_context(
                    parent_execution_id, parent_db_execution_id
                )

                # Update context with current values if needed
                if not context["execution_id"]:
                    context["execution_id"] = get_current_execution_id()
                if not context["db_execution_id"]:
                    context["db_execution_id"] = get_current_db_execution_id()

                # Lookup parent's node execution ID from context map
                parent_node_exec_id = get_node_execution_id(orchestrator_id)
                context["parent_node_execution_id"] = parent_node_exec_id

                exec_id = context["execution_id"]
                db_exec_id = context["db_execution_id"]

                logger.info(
                    f"Execution context - parent_execution_id: {exec_id}, "
                    f"parent_db_execution_id: {db_exec_id}, "
                    f"parent_node_execution_id: {parent_node_exec_id}"
                )

                # Propagate Phoenix project to sub-agent context so spans
                # created inside run_async_in_sync_isolated (which uses a
                # fresh contextvars.Context) are still routed correctly.
                if _captured_phoenix_project:
                    context["phoenix_project"] = _captured_phoenix_project

                # Build delegation request
                request = DelegationRequest(
                    agent_node=agent_node,
                    task_description=delegation_task_description,
                    orchestrator_id=orchestrator_id,
                    context=context,
                )

                # Choose executor based on execution context
                if exec_id and db_exec_id:
                    result = self._execute_with_tracking(request)
                else:
                    result = self._execute_simple(request)

                # Format and return result
                return result.format_for_agent(agent_node.name)

            except GraphInterrupt:
                # Re-raise GraphInterrupt to propagate pause to parent workflow
                # This allows sub-agent review interrupts to pause the entire workflow
                logger.info(
                    f"[DELEGATION] GraphInterrupt received for {agent_node.name}, "
                    "propagating to parent workflow"
                )
                raise
            except Exception as e:
                logger.error(f"Delegation failed: {str(e)}", exc_info=True)
                return f"Error delegating to {agent_node.name}: {str(e)}"
            finally:
                if _project_ctx is not None:
                    try:
                        _project_ctx.__exit__(None, None, None)
                    except Exception:
                        pass

        # Create and return the tool
        tool = Tool(
            name=tool_name, description=tool_description, func=delegate_to_agent
        )
        logger.info(f"Created delegation tool: {tool_name}")
        return tool

    def _execute_with_tracking(self, request: DelegationRequest):
        """Execute delegation with execution tracking.

        Args:
            request: Delegation request

        Returns:
            DelegationResult
        """
        # Get the execution engine
        from backend.services.execution import get_executor

        executor = get_executor()

        # Check if we have subgraph support
        use_subgraph = (
            hasattr(executor, "subgraph_builder")
            and executor.subgraph_builder is not None
        )

        if use_subgraph:
            # Build context with tool mapping
            context = request.context
            context["graph_name"] = self._get_graph_name()
            context["tool_node_mapping"] = self._build_tool_mapping(
                request.agent_node.uniq_id
            )

            # Use subgraph executor (lazy import to avoid circular dependency)
            from backend.services.delegation.executors import SubgraphDelegationExecutor

            logger.info(f"Using subgraph executor for {request.agent_node.name}")
            subgraph_executor = SubgraphDelegationExecutor(self.graph_manager)
            return subgraph_executor.execute(request)
        else:
            # Fall back to simple execution
            logger.info(
                f"Subgraph builder not available, using simple executor "
                f"for {request.agent_node.name}"
            )
            return self._execute_simple(request)

    def _execute_simple(self, request: DelegationRequest):
        """Execute delegation without tracking.

        Args:
            request: Delegation request

        Returns:
            DelegationResult
        """
        # Lazy import to avoid circular dependency

        simple_executor = SimpleDelegationExecutor(self.graph_manager)
        return simple_executor.execute(request)

    def create_delegation_tools_for_orchestrator(
        self,
        orchestrator_node: EnhancedNodeData,
        connected_agents: List[EnhancedNodeData],
    ) -> List[Tool]:
        """Create delegation tools for all agents connected to an orchestrator.

        Args:
            orchestrator_node: The orchestrator agent node
            connected_agents: List of agent nodes connected to the orchestrator

        Returns:
            List of delegation tools

        Raises:
            ValueError: If orchestrator_node is not an AGENT type
        """
        if orchestrator_node.type != NodeType.AGENT:
            raise ValueError(f"Node {orchestrator_node.name} is not an AGENT node")

        logger.info(
            f"Creating delegation tools for orchestrator: {orchestrator_node.name}"
        )
        logger.info(f"Connected agents: {[a.name for a in connected_agents]}")

        tools = []

        # Create tools for agent nodes
        for agent in connected_agents:
            if agent.type == NodeType.AGENT:
                try:
                    tool = self.create_delegation_tool(
                        agent_node=agent, orchestrator_id=orchestrator_node.uniq_id
                    )
                    tools.append(tool)
                except Exception as e:
                    logger.error(
                        f"Failed to create delegation tool for {agent.name}: {e}"
                    )

        # Create tools for subworkflow nodes
        for subworkflow in connected_agents:
            if subworkflow.type == NodeType.SUBWORKFLOW:
                try:
                    tool = create_subworkflow_tool(
                        subworkflow_node=subworkflow,
                        orchestrator_id=orchestrator_node.uniq_id,
                        graph_manager=self.graph_manager,
                    )
                    tools.append(tool)
                except Exception as e:
                    logger.error(
                        f"Failed to create subworkflow tool for {subworkflow.name}: {e}"
                    )

        logger.info(f"Created {len(tools)} delegation tools for orchestrator")
        return tools

    def create_subworkflow_tool(
        self,
        subworkflow_node: EnhancedNodeData,
        orchestrator_id: str,
        description: Optional[str] = None,
        parent_execution_id: Optional[str] = None,
        parent_db_execution_id: Optional[str] = None,
        parent_user_id: Optional[str] = None,
    ) -> Tool:
        """Create a tool that executes a sub-workflow.

        This is a convenience method that delegates to the subworkflow factory.

        Args:
            subworkflow_node: The SUBWORKFLOW node to wrap as a tool
            orchestrator_id: ID of the orchestrator agent
            description: Optional custom description for the tool
            parent_execution_id: Parent execution ID for tracking
            parent_db_execution_id: Parent database execution ID

        Returns:
            Tool instance that can execute the sub-workflow
        """
        return create_subworkflow_tool(
            subworkflow_node=subworkflow_node,
            orchestrator_id=orchestrator_id,
            graph_manager=self.graph_manager,
            description=description,
            parent_execution_id=parent_execution_id,
            parent_db_execution_id=parent_db_execution_id,
            parent_user_id=parent_user_id,
        )
