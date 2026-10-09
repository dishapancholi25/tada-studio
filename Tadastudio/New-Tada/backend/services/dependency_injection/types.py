"""
Type definitions and protocols for dependency injection.

This module defines protocols (interfaces) for the main application dependencies,
allowing for better type checking and easier mocking in tests.
"""

from typing import Any, Dict, List, Optional, Protocol


class GraphManagerProtocol(Protocol):
    """
    Protocol defining the interface for GraphManager.

    This protocol documents the expected interface without coupling to
    the concrete implementation, making it easier to test and swap implementations.
    """

    active_graphs: Dict[str, Any]
    workspace_dir: Any

    def load_graph(self, graph_name: str, username: str = "default") -> Any:
        """Load a graph from storage."""
        ...

    def get_graph(self, graph_name: str) -> Any:
        """Get a graph from active graphs."""
        ...

    def save_graph(self, graph: Any, user: str) -> bool:
        """Save a graph to storage."""
        ...

    def create_graph(self, **kwargs) -> Any:
        """Create a new graph."""
        ...

    def list_graphs(self, username: Optional[str] = None) -> List[Any]:
        """List available graphs."""
        ...

    def create_node(self, **kwargs) -> Any:
        """Create a new node."""
        ...

    def add_node_to_graph(self, graph_name: str, node: Any) -> bool:
        """Add a node to a graph."""
        ...

    def update_node(self, graph_name: str, node_id: str, **kwargs) -> bool:
        """Update a node in a graph."""
        ...

    def delete_node(self, graph_name: str, node_id: str) -> bool:
        """Delete a node from a graph."""
        ...

    def add_connection(
        self, graph_name: str, source: str, target: str, **kwargs
    ) -> bool:
        """Add a connection between nodes."""
        ...

    def remove_connection(self, graph_name: str, source: str, target: str) -> bool:
        """Remove a connection between nodes."""
        ...

    def create_sub_agent(self, **kwargs) -> Any:
        """Create a sub-agent node."""
        ...

    def export_to_langgraph_format(self, graph_name: str) -> Dict[str, Any]:
        """Export graph to LangGraph format."""
        ...

    def get_available_tools(self) -> Dict[str, Any]:
        """Get available tool templates.

        Note: Returns empty dict as tool templates have been removed.
        Tools are now added via explicit node types or direct references.
        """
        ...

    def get_available_agents(self) -> List[Any]:
        """Get available agent templates."""
        ...

    def execute_simple_chat(self, node: Any, message: str) -> Any:
        """Execute a simple chat with an agent."""
        ...


class ExecutionEngineProtocol(Protocol):
    """
    Protocol defining the interface for ExecutionEngine.

    This protocol documents the expected interface for the execution engine,
    supporting both sync and async execution patterns.
    """

    active_executions: Dict[str, Any]
    execution_history: List[Any]

    async def execute_graph(self, *args, **kwargs) -> Any:
        """Execute a graph asynchronously."""
        ...

    def get_execution_status(self, execution_id: str) -> Any:
        """Get the status of an execution."""
        ...

    def get_execution_history(self, execution_id: str) -> Any:
        """Get the execution history for a specific execution."""
        ...

    async def resume_from_checkpoint(self, *args, **kwargs) -> Any:
        """Resume execution from a checkpoint."""
        ...

    def get_checkpoints(self, thread_id: str) -> Any:
        """Get checkpoints for a thread."""
        ...

    def request_stop(self, execution_id: str, reason: Optional[str] = None) -> Any:
        """Request an immediate stop for an execution."""
        ...

    def request_pause(self, execution_id: str) -> Any:
        """Request a graceful pause for an execution."""
        ...
