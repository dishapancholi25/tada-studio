"""
Executor for running subgraphs with proper async patterns.

This module provides the SubgraphExecutor class that handles state passing
between parent graphs and subgraphs during execution.
"""

from collections import deque
from datetime import datetime, timezone
from copy import copy
from typing import Any, Dict, List, Optional, Set

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from backend.models.workflow import EnhancedNodeData, NodeType
from backend.services.config import get_logger
from backend.services.nodes.registry import NodeExecutorRegistry

from .builder import SubgraphBuilder
from .models import SubAgentState


executor_logger = get_logger("subgraph.executor")


# Node types that are tools bound to an agent rather than standalone steps.
# The agent invokes them internally, so they are never walked as the next
# node in a flow. Mirrors the list GraphBuilder excludes from the main graph
# (see GraphBuilder._add_nodes_to_workflow).
TOOL_NODE_TYPES = frozenset(
    {
        NodeType.DOCUMENT_SEARCH,
        NodeType.DATABASE_QUERY,
        NodeType.HTTP_REQUEST,
        NodeType.WEB_SEARCH,
        NodeType.MCP_SERVER,
        NodeType.DOCUMENT_RETRIEVE,
    }
)


class SubgraphExecutor:
    """Executor for running subgraphs with proper async patterns.

    Handles state passing between parent and subgraph.
    """

    def __init__(self, subgraph_builder: SubgraphBuilder):
        """
        Initialize the executor.

        Args:
            subgraph_builder: The SubgraphBuilder instance
        """
        self.subgraph_builder = subgraph_builder

    async def execute_subagent(
        self,
        agent_node: EnhancedNodeData,
        task: str,
        parent_state: Dict[str, Any],
        checkpointer: Optional[BaseCheckpointSaver] = None,
    ) -> Dict[str, Any]:
        """
        Execute a sub-agent as a subgraph.

        Args:
            agent_node: The agent to execute
            task: The task description
            parent_state: The parent graph's state
            checkpointer: Optional checkpointer

        Returns:
            Updated state from subgraph execution containing:
                - execution_order: Updated execution order
                - subagent_response: The agent's response
                - subagent_error: Error message if execution failed
                - tool_executions: List of tool executions performed
        """
        executor_logger.info(f"Executing sub-agent {agent_node.name} as subgraph")

        # Get or create the subgraph
        subgraph = self.subgraph_builder.create_subagent_graph(agent_node, checkpointer)

        # Prepare initial subgraph state
        initial_state: SubAgentState = {
            "task_description": task,
            "task_id": f"task_{datetime.now(timezone.utc).timestamp()}",
            "parent_execution_id": parent_state.get("execution_id", ""),
            "parent_db_execution_id": parent_state.get("db_execution_id"),
            "parent_node_id": parent_state.get("current_node", ""),
            "parent_node_name": parent_state.get("metadata", {}).get(
                "current_node_name", ""
            ),
            "execution_order": parent_state.get("execution_order", 0),
            "start_time": None,
            "end_time": None,
            "agent_node_id": agent_node.uniq_id,
            "agent_node_name": agent_node.name,
            "agent_config": agent_node.agent_config.__dict__
            if agent_node.agent_config
            else None,
            "user_id": parent_state.get("user_id"),
            "graph_name": parent_state.get("graph_name"),
            "tool_node_mapping": parent_state.get("tool_node_mapping"),
            "response": None,
            "structured_output": None,
            "tool_executions": [],
            "error": None,
            "messages": [HumanMessage(content=task)],
            "metadata": {},
        }

        # Execute the subgraph
        try:
            # Use async invoke
            result = await subgraph.ainvoke(initial_state)

            executor_logger.info(f"Sub-agent {agent_node.name} completed successfully")

            # Extract relevant fields for parent state update
            return {
                "execution_order": result.get("execution_order"),
                "subagent_response": result.get("response"),
                "subagent_error": result.get("error"),
                "tool_executions": result.get("tool_executions", []),
            }

        except Exception as e:
            executor_logger.error(f"Subgraph execution failed: {str(e)}", exc_info=True)
            return {
                "execution_order": parent_state.get("execution_order", 0),
                "subagent_error": str(e),
            }

    async def execute_for_each_body(
        self,
        for_each_node: EnhancedNodeData,
        iteration_state: Dict[str, Any],
        index: int,
        graph: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Execute the body nodes of a For Each iteration.

        The graph builder identifies the body of a For Each node (the nodes
        reachable from it that are excluded from the main graph) and stores
        `body_node_ids` / `body_entry_node_id` on `node.for_each_config` at
        build time (see `GraphBuilder._identify_for_each_internal_nodes`).
        This method walks that body starting at `body_entry_node_id`,
        dispatching each node to its registered executor (the same
        `NodeExecutorRegistry` used by the main graph), so a For Each body
        can contain any node type (AGENT, HTTP, CONDITION, DATABASE, etc.).

        Args:
            for_each_node: The For Each node whose body should run
            iteration_state: Isolated per-iteration state (contains the
                virtual "__for_each_current" node output plus the parent's
                context, see `ForEachNodeExecutor._build_iteration_state`)
            index: Iteration index (used for logging only)
            graph: The parent GraphData, used to resolve body node
                definitions by id. Required for body execution.

        Returns:
            The NodeOutput of the last executed body node (or the last
            node's raw result if it has no NodeOutput, e.g. CONDITION),
            or None if there is no body to run.
        """
        config = for_each_node.for_each_config
        if not config or not config.body_node_ids or not config.body_entry_node_id:
            return None

        if graph is None or not getattr(graph, "nodes", None):
            executor_logger.warning(
                f"For Each '{for_each_node.name}' body execution requires graph "
                f"context; none was provided for iteration {index}"
            )
            return None

        body_ids: Set[str] = set(config.body_node_ids)
        nodes_by_id = {n.uniq_id: n for n in graph.nodes if n.uniq_id in body_ids}

        execution_id = iteration_state.get("execution_id", "")
        user_id = iteration_state.get("user_id")

        working_state: Dict[str, Any] = dict(iteration_state)
        working_state["node_outputs"] = dict(iteration_state.get("node_outputs", {}))

        last_output: Optional[Dict[str, Any]] = None
        visited: Set[str] = set()

        # Predecessors within the body, over flow edges only, so a node that
        # joins two branches does not run on the first one to arrive.
        predecessors: Dict[str, Set[str]] = {nid: set() for nid in nodes_by_id}
        for nid, candidate in nodes_by_id.items():
            for succ in self._flow_successor_ids(candidate, nodes_by_id):
                predecessors[succ].add(nid)

        condition_routes = self._build_condition_routes(graph)

        worklist: deque = deque([config.body_entry_node_id])
        queued: Set[str] = {config.body_entry_node_id}
        deferrals = 0

        while worklist:
            current_id = worklist.popleft()
            if current_id in visited or current_id not in nodes_by_id:
                continue

            body_node = nodes_by_id[current_id]
            if body_node.type == NodeType.END:
                continue

            # Hold a node back while a branch that feeds it is still pending.
            # The deferral budget guarantees progress: once every remaining
            # entry has been rotated without executing, run the head anyway
            # rather than deadlock on an unreachable predecessor.
            blocked_by = {
                pred
                for pred in predecessors.get(current_id, set())
                if pred in queued and pred not in visited
            }
            if blocked_by and deferrals <= len(worklist):
                deferrals += 1
                worklist.append(current_id)
                continue
            deferrals = 0

            visited.add(current_id)

            # Create a per-iteration copy of the node so each iteration gets
            # its own DB record and distinguishable name in the UI.
            iter_index = working_state.get("__for_each_iteration_index")
            iter_total = working_state.get("__for_each_total")
            if iter_index is not None:
                body_node = copy(body_node)
                body_node.name = f"{body_node.name} [Run {iter_index + 1}/{iter_total or '?'}]"

            try:
                executor = NodeExecutorRegistry.get_executor(body_node.type)
            except Exception as exc:
                executor_logger.error(
                    f"For Each '{for_each_node.name}' body node '{body_node.name}' "
                    f"(type={body_node.type}) has no registered executor: {exc}"
                )
                continue

            result = await executor.execute(
                body_node, working_state, graph, execution_id, user_id
            )

            node_output = self._apply_body_result(body_node, working_state, result)
            if node_output is not None:
                last_output = node_output

            if result.get("execution_order") is not None:
                working_state["execution_order"] = result["execution_order"]

            for next_id in self._next_body_node_ids(
                body_node, working_state, nodes_by_id, condition_routes
            ):
                if next_id not in visited:
                    queued.add(next_id)
                    worklist.append(next_id)

        return last_output

    @staticmethod
    def _apply_body_result(
        body_node: EnhancedNodeData,
        working_state: Dict[str, Any],
        result: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Merge a body node's execution result into the iteration-local state.

        Mirrors the merge behaviour used for the main graph (see
        `NodeFunctionFactory._merge_node_outputs`) so body nodes can
        reference each other's outputs (via `state["node_outputs"]`) the
        same way main-graph nodes do.

        Returns the resolved NodeOutput for `body_node` (or its raw result
        if it doesn't produce a NodeOutput, e.g. CONDITION nodes).
        """
        node_outputs = working_state.setdefault("node_outputs", {})

        if "node_outputs" in result:
            node_outputs.update(result["node_outputs"])

        node_output = result.get("node_output")
        if node_output is not None:
            node_outputs[body_node.uniq_id] = node_output
            return node_output

        if body_node.uniq_id in node_outputs:
            return node_outputs[body_node.uniq_id]

        # Nodes such as CONDITION don't produce a NodeOutput; surface their
        # raw result so a body that ends on one still has something to
        # aggregate on.
        return result or None

    @staticmethod
    def _flow_successor_ids(
        body_node: EnhancedNodeData,
        nodes_by_id: Dict[str, EnhancedNodeData],
    ) -> List[str]:
        """Return the body successors of `body_node` along flow edges.

        ``nexts`` mixes three kinds of target: the actual next step, tool
        nodes attached to an agent, and delegated sub-agents. Only the first
        is a sequential step - tools and sub-agents are invoked inside the
        agent that owns them, exactly as the main graph treats them (see
        ``EdgeBuilder._should_skip_connection``). Ids that no longer resolve
        to a node (for example a deleted node still referenced in ``nexts``)
        are dropped, since following one would silently end the body.

        Args:
            body_node: The node whose successors are wanted
            nodes_by_id: Resolvable body nodes, keyed by id

        Returns:
            Ids of the body nodes that follow `body_node` in the flow
        """
        successors: List[str] = []
        for next_id in body_node.nexts or []:
            target = nodes_by_id.get(next_id)
            if target is None:
                continue
            if target.type in TOOL_NODE_TYPES or getattr(
                target, "is_sub_agent", False
            ):
                continue
            successors.append(next_id)
        return successors

    @staticmethod
    def _build_condition_routes(graph: Any) -> Dict[str, Dict[str, str]]:
        """Map each condition node's routing keys to their target node ids.

        Mirrors ``EdgeBuilder._get_condition_targets`` so a condition inside a
        loop body routes exactly as it does in the main graph. Connections are
        the source of truth: a node's ``true_next``/``false_next`` fields can
        be stale relative to the edges actually drawn on the canvas.

        Args:
            graph: The parent GraphData

        Returns:
            ``{condition_node_id: {routing_key: target_node_id}}``
        """
        routes: Dict[str, Dict[str, str]] = {}
        for conn in getattr(graph, "connections", None) or []:
            source_id = getattr(conn, "source_id", None)
            target_id = getattr(conn, "target_id", None)
            if not source_id or not target_id:
                continue
            handle = getattr(conn, "source_handle", None)
            label = getattr(conn, "label", None)
            if handle:
                routing_key = handle.replace("branch-", "")
            elif label:
                routing_key = label
            else:
                routing_key = "default"
            routes.setdefault(source_id, {})[routing_key] = target_id
        return routes

    @staticmethod
    def _next_body_node_ids(
        body_node: EnhancedNodeData,
        working_state: Dict[str, Any],
        nodes_by_id: Dict[str, EnhancedNodeData],
        condition_routes: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> List[str]:
        """Determine which body nodes to execute after `body_node`.

        CONDITION nodes follow only the branch taken, resolved from the result
        stored by ``ConditionNodeExecutor`` at
        ``state[f"__condition_result_{node.uniq_id}"]``. Branch targets come
        from the graph's connections (binary mode keys the true branch "0" and
        the false branch "1"), falling back to the node's
        ``true_next``/``false_next`` when no connection matches. Every other
        node fans out to all of its flow successors, matching how the main
        graph runs parallel branches.

        Args:
            body_node: The node that just executed
            working_state: Iteration-local state, holding condition results
            nodes_by_id: Resolvable body nodes, keyed by id
            condition_routes: Routing map from ``_build_condition_routes``

        Returns:
            Ids of the body nodes to execute next
        """
        if body_node.type != NodeType.CONDITION:
            return SubgraphExecutor._flow_successor_ids(body_node, nodes_by_id)

        branch_result = working_state.get(f"__condition_result_{body_node.uniq_id}")

        # Accept the several forms a result can take: the raw routing key, a
        # branch handle, or the true/false wording used by binary conditions.
        candidate_keys: List[str] = []
        if branch_result is not None:
            raw = str(branch_result)
            candidate_keys.extend([raw, raw.replace("branch-", "")])
            if raw.lower() == "true":
                candidate_keys.append("0")
            elif raw.lower() == "false":
                candidate_keys.append("1")

        routes = (condition_routes or {}).get(body_node.uniq_id, {})
        for key in candidate_keys:
            target = routes.get(key)
            if target and target in nodes_by_id:
                return [target]

        # Fall back to the node's own branch fields
        fallback = (
            body_node.true_next
            if str(branch_result).lower() == "true"
            else body_node.false_next
        )
        if fallback and fallback in nodes_by_id:
            return [fallback]

        executor_logger.warning(
            f"Condition '{body_node.name}' in For Each body produced result "
            f"{branch_result!r} with no matching branch target; "
            f"body traversal stops here"
        )
        return []
