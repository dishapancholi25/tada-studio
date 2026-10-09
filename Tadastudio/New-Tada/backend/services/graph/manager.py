"""Workflow graph management facade.

This module provides the main GraphManager class, which serves as a facade
coordinating all graph-related operations through specialized service modules.

This is a lightweight coordinator that delegates to specialized services rather
than containing complex logic itself, following the same pattern as ExecutionEngine.

Example:
    >>> from backend.services.graph import GraphManager
    >>> manager = GraphManager()
    >>> graph = manager.create_graph("my-workflow", "A test workflow")
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.models.workflow import (
    AgentConfig,
    ConnectionType,
    EnhancedNodeData,
    GraphData,
    NodeType,
    Position,
)
from backend.services.config import get_logger
from backend.services.delegation import AgentDelegationToolFactory
from backend.services.execution.agent import SyncAgentExecutor
from backend.services.execution.async_agent import create_async_agent_executor
from backend.services.graph.agent_tools import AgentToolFactory
from backend.services.llm_models import LLMFactory
from backend.services.model_deployment import ModelDeploymentService

from .compilation import CompilationService
from .connection_manager import ConnectionManager
from .constants import LOG_PREFIX_GRAPH_MANAGER
from .export import ExportService
from .graph_crud import GraphCRUDService
from .node_manager import NodeManager
from .orchestrator_manager import OrchestratorManager
from .validation import ValidationService


logger = get_logger(__name__)


class GraphManager:
    """Facade for managing workflow graphs and their operations.

    This class serves as the main entry point for all graph-related operations,
    delegating to specialized service modules for specific functionality.

    Architecture:
        - NodeManager: Node CRUD operations
        - ConnectionManager: Connection management
        - GraphCRUDService: Graph persistence and loading
        - OrchestratorManager: Orchestrator and delegation logic
        - ValidationService: Graph and node validation
        - ExportService: Graph export to various formats
        - CompilationService: Compile-time tool binding

    Methods:
        Graph CRUD: create_graph, get_graph, list_graphs, save_graph, load_graph
        Node Operations: create_node, update_node, delete_node, add_node_to_graph
        Connections: add_connection, remove_connection
        Orchestration: create_sub_agent, detect_and_configure_orchestrators
        Validation: validate_graph, validate_agent_llm_config
        Export: export_to_langgraph_format
        Compilation: compile_graph, get_compiled_agent
        Execution: execute_agent_async, execute_simple_chat
        Tools: get_tools, get_delegation_tools
    """

    def __init__(self, workspace_dir: str = "./workspace", lazy_compile: bool = True):
        """Initialize graph manager and all service dependencies.

        Args:
            workspace_dir: Directory for workspace files
            lazy_compile: Whether to use lazy compilation
        """
        logger.info(f"{LOG_PREFIX_GRAPH_MANAGER} Initializing GraphManager")

        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)

        # Managed model deployments
        self.model_service = ModelDeploymentService()

        # Initialize specialized service modules
        self.node_manager = NodeManager(model_service=self.model_service)
        self.connection_manager = ConnectionManager()
        self.graph_crud = GraphCRUDService(workspace_dir=workspace_dir)
        self.validation_service = ValidationService()
        self.export_service = ExportService()
        self.compilation_service = CompilationService(
            use_compile_time_tools=True, lazy_compile=lazy_compile
        )

        # Agent delegation tools factory (needed by orchestrator manager)
        self.delegation_factory = AgentDelegationToolFactory(self)

        # Orchestrator manager (requires delegation factory, node manager, connection manager)
        self.orchestrator_manager = OrchestratorManager(
            delegation_factory=self.delegation_factory,
            node_manager=self.node_manager,
            connection_manager=self.connection_manager,
        )

        # Agent tool factory (for creating tool instances for agents)
        self.tool_factory = AgentToolFactory(self, self.delegation_factory)

        # LLM factory
        self.llm_factory = LLMFactory(
            graph_manager=self, model_service=self.model_service
        )

        # Async agent executor
        self.async_executor = create_async_agent_executor(
            llm_factory=self.llm_factory,
            model_service=self.model_service,
            get_tools_callback=self.get_tools,
        )

        # Sync agent executor (for execute_simple_chat)
        self.sync_executor = SyncAgentExecutor(graph_manager=self)

        # Compile-time features (always enabled after Phase 4)
        self.use_compile_time_tools = True
        self.lazy_compile = lazy_compile

        # Expose active_graphs for backward compatibility
        self.active_graphs = self.graph_crud.active_graphs

        logger.info(f"{LOG_PREFIX_GRAPH_MANAGER} Initialized successfully")

    # ============================================================================
    # GRAPH CRUD OPERATIONS (delegate to GraphCRUDService)
    # ============================================================================

    def create_graph(
        self,
        name: str,
        description: str = "",
        username: str = "default",
        default_llm_config: Optional[str] = None,
    ) -> GraphData:
        """Create a new graph. Delegates to GraphCRUDService."""
        return self.graph_crud.create_graph(
            name,
            description,
            username,
            default_llm_config,
            node_manager=self.node_manager,
        )

    def get_graph(self, graph_name: str) -> Optional[GraphData]:
        """Get a graph from active graphs. Delegates to GraphCRUDService."""
        return self.graph_crud.get_graph(graph_name)

    def list_graphs(self, username: str = "default") -> List[Dict[str, Any]]:
        """List all graphs for a user. Delegates to GraphCRUDService."""
        return self.graph_crud.list_graphs(username)

    def save_graph(self, graph: GraphData, username: str = "default") -> bool:
        """Save a graph to storage. Delegates to GraphCRUDService."""
        return self.graph_crud.save_graph(graph, username)

    def load_graph(
        self, graph_name: str, username: str = "default"
    ) -> Optional[GraphData]:
        """Load a graph from storage. Delegates to GraphCRUDService."""
        return self.graph_crud.load_graph(
            graph_name, username, orchestrator_manager=self.orchestrator_manager
        )

    def load_graph_by_workflow_id(
        self, workflow_id: str, username: str = "default"
    ) -> Optional[GraphData]:
        """Load a graph by workflow ID. Delegates to GraphCRUDService."""
        return self.graph_crud.load_graph_by_workflow_id(
            workflow_id, username, orchestrator_manager=self.orchestrator_manager
        )

    # ============================================================================
    # NODE OPERATIONS (delegate to NodeManager)
    # ============================================================================

    def create_node(
        self,
        node_type: NodeType,
        name: str,
        position: Position = None,
        tool_template: Optional[str] = None,
        agent_template: Optional[str] = None,
        condition_prompt: Optional[str] = None,
        llm_config_override: Optional[str] = None,
        **kwargs,
    ) -> EnhancedNodeData:
        """Create a new node. Delegates to NodeManager."""
        return self.node_manager.create_node(
            node_type,
            name,
            position,
            tool_template,
            agent_template,
            condition_prompt,
            llm_config_override,
            **kwargs,
        )

    def update_node(
        self, graph_name: str, node_id: str, updates: Dict[str, Any]
    ) -> bool:
        """Update a node. Delegates to NodeManager."""
        graph = self.get_graph(graph_name)
        if not graph:
            return False
        return self.node_manager.update_node(graph, node_id, updates)

    def delete_node(self, graph_name: str, node_id: str) -> bool:
        """Delete a node. Delegates to NodeManager."""
        graph = self.get_graph(graph_name)
        if not graph:
            return False
        return self.node_manager.delete_node(graph, node_id)

    def add_node_to_graph(self, graph_name: str, node: EnhancedNodeData) -> bool:
        """Add a node to a graph. Delegates to NodeManager."""
        graph = self.get_graph(graph_name)
        if not graph:
            return False
        return self.node_manager.add_node_to_graph(graph, node)

    # ============================================================================
    # CONNECTION OPERATIONS (delegate to ConnectionManager)
    # ============================================================================

    def add_connection(
        self,
        graph_name: str,
        source_id: str,
        target_id: str,
        source_handle: Optional[str] = None,
        target_handle: Optional[str] = None,
        connection_type: ConnectionType = ConnectionType.WORKFLOW,
        label: str = "",
        true_condition: bool = False,
    ) -> bool:
        """Add a connection. Delegates to ConnectionManager."""
        graph = self.get_graph(graph_name)
        if not graph:
            return False

        result = self.connection_manager.add_connection(
            graph,
            source_id,
            target_id,
            source_handle,
            target_handle,
            connection_type,
            label,
            true_condition,
        )

        # Save the graph after adding connection
        if result:
            self.save_graph(graph)

        return result

    def remove_connection(
        self, graph_name: str, source_id: str, target_id: str
    ) -> bool:
        """Remove a connection. Delegates to ConnectionManager."""
        graph = self.get_graph(graph_name)
        if not graph:
            return False

        result = self.connection_manager.remove_connection(graph, source_id, target_id)

        # Save the graph after removing connection
        if result:
            self.save_graph(graph)

        return result

    # ============================================================================
    # ORCHESTRATOR OPERATIONS (delegate to OrchestratorManager)
    # ============================================================================

    @staticmethod
    def get_connected_agents(
        graph: GraphData, orchestrator_id: str
    ) -> List[EnhancedNodeData]:
        """Get connected agents. Delegates to OrchestratorManager."""
        return OrchestratorManager.get_connected_agents(graph, orchestrator_id)

    def get_delegation_tools(
        self, graph: GraphData, orchestrator_node: EnhancedNodeData
    ) -> List[Any]:
        """Get delegation tools. Delegates to OrchestratorManager."""
        return self.orchestrator_manager.get_delegation_tools(graph, orchestrator_node)

    def detect_and_configure_orchestrators(self, graph: GraphData) -> int:
        """Detect orchestrators. Delegates to OrchestratorManager."""
        return self.orchestrator_manager.detect_and_configure_orchestrators(graph)

    def create_sub_agent(
        self,
        graph_name: str,
        parent_agent_id: str,
        name: Optional[str] = None,
        position: Optional[Position] = None,
        delegation_description: str = "",
        agent_template: Optional[str] = None,
    ) -> Optional[EnhancedNodeData]:
        """Create a sub-agent. Delegates to OrchestratorManager."""
        return self.orchestrator_manager.create_sub_agent(
            graph_name,
            self.active_graphs,
            parent_agent_id,
            name,
            position,
            delegation_description,
            agent_template,
        )

    # ============================================================================
    # VALIDATION OPERATIONS (delegate to ValidationService)
    # ============================================================================

    def validate_graph(self, graph_name: str) -> Dict[str, Any]:
        """Validate a graph. Delegates to ValidationService."""
        graph = self.get_graph(graph_name)
        if not graph:
            return {
                "valid": False,
                "errors": [f"Graph '{graph_name}' not found"],
                "warnings": [],
            }
        return self.validation_service.validate_graph(graph)

    @staticmethod
    def validate_agent_llm_config(agent_config: AgentConfig):
        """Validate LLM config. Delegates to ValidationService."""
        validator = ValidationService()
        return validator.validate_agent_llm_config(agent_config)

    # ============================================================================
    # EXPORT OPERATIONS (delegate to ExportService)
    # ============================================================================

    def export_to_langgraph_format(self, graph_name: str) -> Dict[str, Any]:
        """Export to LangGraph format. Delegates to ExportService."""
        graph = self.get_graph(graph_name)
        if not graph:
            return {}
        return self.export_service.export_to_langgraph_format(graph)

    # ============================================================================
    # COMPILATION OPERATIONS (delegate to CompilationService)
    # ============================================================================

    async def compile_graph(self, graph: GraphData) -> Dict[str, Any]:
        """Compile a graph. Delegates to CompilationService."""
        return await self.compilation_service.compile_graph(graph)

    def get_compiled_agent(self, agent_id: str) -> Optional[Any]:
        """Get compiled agent. Delegates to CompilationService."""
        return self.compilation_service.get_compiled_agent(agent_id)

    def get_compilation_status(self, graph_name: str) -> str:
        """Get compilation status. Delegates to CompilationService."""
        return self.compilation_service.get_compilation_status(graph_name)

    def get_compilation_stats(self) -> Dict[str, Any]:
        """Get compilation stats. Delegates to CompilationService."""
        return self.compilation_service.get_compilation_stats(
            total_graphs=len(self.active_graphs)
        )

    # ============================================================================
    # TOOL OPERATIONS (delegate to AgentToolFactory)
    # ============================================================================

    def get_tools(
        self,
        tool_list: Optional[List[str]] = None,
        agent_config=None,
        graph_name: str = None,
        agent_node_id: str = None,
        user_id: Optional[str] = None,
    ) -> List[Any]:
        """Get tools for an agent. Delegates to AgentToolFactory."""
        return self.tool_factory.get_tools(
            tool_list=tool_list,
            agent_config=agent_config,
            graph_name=graph_name,
            agent_node_id=agent_node_id,
            user_id=user_id,
        )

    def _create_serializable_tools(self, tools, tool_execution_tracker=None):
        """Create serializable tools. Delegates to AgentToolFactory."""
        return self.tool_factory.create_serializable_tools(
            tools, tool_execution_tracker
        )

    # ============================================================================
    # AGENT EXECUTION (delegate to executors)
    # ============================================================================

    async def execute_agent_async(
        self,
        agent_node: EnhancedNodeData,
        user_message: str,
        format_output: bool = True,
        db_execution_id: Optional[str] = None,
        tool_execution_tracker: Optional[list] = None,
        return_token_counts: bool = False,
        graph_name: Optional[str] = None,
        execution_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tool_node_mapping: Optional[Dict[str, Dict[str, str]]] = None,
        review_iteration: Optional[int] = None,
        node_execution_id: Optional[str] = None,
        execution_order: Optional[int] = None,
        db_node_id: Optional[str] = None,
        is_subagent: bool = False,
        invocation_index: Optional[int] = None,
        parent_subagent_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
        workflow_id: Optional[str] = None,
    ) -> Any:
        """Execute agent asynchronously. Delegates to async executor."""
        from backend.services.execution.async_agent import ExecutionConfig

        config = ExecutionConfig(
            format_output=format_output,
            db_execution_id=db_execution_id,
            tool_execution_tracker=tool_execution_tracker,
            return_token_counts=return_token_counts,
            execution_id=execution_id,
            graph_name=graph_name,
            node_id=getattr(agent_node, "uniq_id", None),
            user_id=user_id,
            tool_node_mapping=tool_node_mapping,
            review_iteration=review_iteration,
            node_execution_id=node_execution_id,
            execution_order=execution_order,
            db_node_id=db_node_id,
            is_subagent=is_subagent,
            invocation_index=invocation_index,
            parent_subagent_id=parent_subagent_id,
            conversation_history=conversation_history,
            workflow_id=workflow_id,
        )

        result = await self.async_executor.execute_agent(
            agent_node, user_message, config, graph_name=graph_name
        )

        if return_token_counts:
            return result.to_tuple()
        return result.response

    def execute_simple_chat(
        self,
        agent_node: EnhancedNodeData,
        user_message: str,
        format_output: bool = True,
        db_execution_id: Optional[str] = None,
        tool_execution_tracker: Optional[list] = None,
        return_token_counts: bool = False,
        return_raw_response: bool = False,
    ):
        """Execute chat synchronously. Delegates to sync executor."""
        return self.sync_executor.execute_simple_chat(
            agent_node=agent_node,
            user_message=user_message,
            format_output=format_output,
            db_execution_id=db_execution_id,
            tool_execution_tracker=tool_execution_tracker,
            return_token_counts=return_token_counts,
            return_raw_response=return_raw_response,
        )

    # ============================================================================
    # UTILITY METHODS (for backward compatibility)
    # ============================================================================

    @staticmethod
    def _store_agent_memory(
        agent_node: EnhancedNodeData,
        user_message: str,
        agent_response: str,
        db_execution_id: Optional[str] = None,
    ):
        """Store agent memory. Delegates to MemoryHandler."""
        from backend.services.execution.agent import MemoryHandler

        MemoryHandler.store_memory_sync(
            agent_node, user_message, agent_response, db_execution_id
        )

    @staticmethod
    def _normalise_mcp_tool_input(input_data: Any, primary_arg: str) -> Any:
        """Normalize MCP tool input. Delegates to serialization module."""
        from backend.services.graph.agent_tools.serialization import (
            normalize_mcp_tool_input,
        )

        return normalize_mcp_tool_input(input_data, primary_arg)

    def _get_mcp_context_for_agent(self, agent_node: EnhancedNodeData) -> Optional[str]:
        """Get MCP context for agent. Delegates to ContextBuilder."""
        from backend.services.execution.agent import ContextBuilder

        # Find the graph containing this agent
        graph = None
        for graph_name, g in self.active_graphs.items():
            if any(n.uniq_id == agent_node.uniq_id for n in g.nodes):
                graph = g
                break

        if not graph:
            return None

        return ContextBuilder.get_mcp_context(agent_node, graph)

    def _create_llm_from_config(self, llm_config):
        """Create LLM from config. Delegates to LLMFactory."""
        enriched_config = self.model_service.enrich_llm_config(llm_config)
        llm_instance = self.llm_factory.create_llm_instance(enriched_config)
        return llm_instance.llm

    # ============================================================================
    # DEPRECATED METHODS (kept for backward compatibility)
    # ============================================================================

    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get available tool templates. DEPRECATED - returns empty dict."""
        return {}

    def get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get available agent templates. DEPRECATED - returns empty dict."""
        return {}

    def _ensure_agent_tools_exist(self, graph_name: str, agent_node: EnhancedNodeData):
        """Ensure agent tools exist. DEPRECATED - no-op."""
        pass

    def _init_compile_time_features(self):
        """Initialize compile-time features. DEPRECATED - handled in __init__."""
        pass

    # Expose compilation service attributes for backward compatibility
    @property
    def compiled_agents(self):
        """Access compiled agents from compilation service."""
        return self.compilation_service.compiled_agents

    @property
    def compilation_status(self):
        """Access compilation status from compilation service."""
        return self.compilation_service.compilation_status

    @property
    def tool_registry(self):
        """Access tool registry from compilation service."""
        return self.compilation_service.tool_registry

    @property
    def agent_compiler(self):
        """Access agent compiler from compilation service."""
        return self.compilation_service.agent_compiler
