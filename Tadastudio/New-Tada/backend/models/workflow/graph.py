"""Graph data structure for complete workflows.

This module defines the GraphData class that represents complete
workflow graphs with nodes, connections, and metadata.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .base import Connection
from .configs import LLMConfig
from .enums import ConnectionType, NodeType
from .node import EnhancedNodeData
from .publication import WorkflowPublicationConfig
from .validation import GraphValidator


@dataclass
class GraphData:
    """Represents a complete graph/workflow.

    Attributes:
        name: Workflow name
        description: Workflow description
        nodes: List of nodes in the workflow
        connections: List of connections between nodes
        metadata: Additional metadata dictionary
        created_at: Creation timestamp
        updated_at: Last update timestamp
        is_subgraph: Whether this is a subgraph
        max_execution_time: Maximum execution time in seconds
        enable_parallel_execution: Enable parallel node execution
        default_llm_config: Fallback LLM configuration
        publication_config: Publication configuration
        workflow_id: Database workflow ID
        definition_id: Database definition ID
    """

    name: str = ""
    description: str = ""
    nodes: List[EnhancedNodeData] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_subgraph: bool = False

    # Execution configuration
    max_execution_time: int = 3600
    enable_parallel_execution: bool = False
    default_llm_config: Optional[LLMConfig] = None

    # Publication configuration
    publication_config: Optional[WorkflowPublicationConfig] = None

    # Database tracking fields
    workflow_id: Optional[str] = None
    definition_id: Optional[str] = None

    def get_node_by_id(self, node_id: str) -> Optional[EnhancedNodeData]:
        """Get node by ID.

        Args:
            node_id: Node identifier

        Returns:
            Node if found, None otherwise
        """
        return next((node for node in self.nodes if node.uniq_id == node_id), None)

    def get_nodes_by_type(self, node_type: NodeType) -> List[EnhancedNodeData]:
        """Get all nodes of a specific type.

        Args:
            node_type: Type of nodes to retrieve

        Returns:
            List of nodes matching the type
        """
        return [node for node in self.nodes if node.type == node_type]

    def get_tool_nodes_for_agent(self, agent_node_id: str) -> List[EnhancedNodeData]:
        """Get all tool nodes that should be available to a specific agent.

        This includes:
        1. Tool nodes connected via TOOL connections
        2. Tool nodes with matching parent_agent_id (WEB_SEARCH, DOCUMENT_SEARCH, etc.)
        3. Legacy: Tool nodes referenced in agent.tools list

        Args:
            agent_node_id: ID of the agent node

        Returns:
            List of tool nodes available to the agent
        """
        agent_node = self.get_node_by_id(agent_node_id)
        if not agent_node or agent_node.type != NodeType.AGENT:
            return []

        tool_nodes = []

        # Method 1: Tool connections
        tool_nodes.extend(self._get_tools_by_connection(agent_node_id))

        # Method 2: Parent agent ID matching
        tool_nodes.extend(self._get_tools_by_parent_id(agent_node_id, tool_nodes))

        # Method 3: Legacy tool name matching
        if not tool_nodes and agent_node.agent_config:
            tool_nodes.extend(
                self._get_tools_by_name(agent_node.agent_config.tools, tool_nodes)
            )

        return tool_nodes

    def _get_tools_by_connection(self, agent_node_id: str) -> List[EnhancedNodeData]:
        """Get tools connected via TOOL connections.

        Args:
            agent_node_id: Agent node ID

        Returns:
            List of connected tool nodes
        """
        tools = []

        for conn in self.connections:
            if (
                conn.source_id == agent_node_id
                and conn.connection_type == ConnectionType.TOOL
            ):
                target_node = self.get_node_by_id(conn.target_id)
                if target_node:
                    tools.append(target_node)

        return tools

    def _get_tools_by_parent_id(
        self, agent_node_id: str, existing_tools: List[EnhancedNodeData]
    ) -> List[EnhancedNodeData]:
        """Get tools by parent_agent_id attribute.

        Args:
            agent_node_id: Agent node ID
            existing_tools: Tools already found

        Returns:
            List of additional tool nodes
        """
        tools = []
        tool_types_with_parent = [
            (NodeType.WEB_SEARCH, "web_search_config"),
            (NodeType.DOCUMENT_SEARCH, "document_search_config"),
            (NodeType.DATABASE_QUERY, "database_query_config"),
            (NodeType.HTTP_REQUEST, "http_request_config"),
        ]

        for node in self.nodes:
            for node_type, config_attr in tool_types_with_parent:
                if node.type == node_type:
                    config = getattr(node, config_attr, None)
                    if config:
                        parent_id = self._get_parent_agent_id(config)
                        if parent_id == agent_node_id and node not in existing_tools:
                            tools.append(node)
                            break

        return tools

    @staticmethod
    def _get_parent_agent_id(config: Any) -> Optional[str]:
        """Get parent_agent_id from config (dict or object).

        Args:
            config: Configuration object or dict

        Returns:
            Parent agent ID if found
        """
        if isinstance(config, dict):
            return config.get("parent_agent_id")
        return getattr(config, "parent_agent_id", None)

    def _get_tools_by_name(
        self, tool_names: List[str], existing_tools: List[EnhancedNodeData]
    ) -> List[EnhancedNodeData]:
        """Get tools by name from agent config (legacy).

        Args:
            tool_names: List of tool names
            existing_tools: Tools already found

        Returns:
            List of additional tool nodes
        """
        tools = []
        tool_name_set = set(tool_names)

        for node in self.nodes:
            if node.type == NodeType.TOOL and node.tool_config:
                if (
                    node.tool_config.tool_name in tool_name_set
                    and node not in existing_tools
                ):
                    tools.append(node)

        return tools

    def validate(self) -> Dict[str, Any]:
        """Validate the entire graph.

        Returns:
            Dictionary with validation results:
                - is_valid: bool
                - errors: List[str]
                - warnings: List[str]
        """
        return GraphValidator.validate_graph(self)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation of the graph
        """
        result = {
            "name": self.name,
            "description": self.description,
            "nodes": [node.to_dict() for node in self.nodes],
            "connections": [
                {
                    **asdict(conn),
                    "connection_type": (
                        conn.connection_type.value
                        if isinstance(conn.connection_type, ConnectionType)
                        else (
                            str(conn.connection_type)
                            if conn.connection_type is not None
                            else ConnectionType.WORKFLOW.value
                        )
                    ),
                }
                for conn in self.connections
            ],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_subgraph": self.is_subgraph,
            "max_execution_time": self.max_execution_time,
            "enable_parallel_execution": self.enable_parallel_execution,
        }

        if self.default_llm_config:
            result["default_llm_config"] = asdict(self.default_llm_config)

        if self.publication_config:
            result["publication_config"] = self.publication_config.to_dict()

        if self.workflow_id:
            result["workflow_id"] = self.workflow_id
        if self.definition_id:
            result["definition_id"] = self.definition_id

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphData":
        """Create from dictionary.

        Args:
            data: Dictionary data

        Returns:
            GraphData instance
        """
        # Deserialize nodes
        node_list = [
            EnhancedNodeData.from_dict(node_data) for node_data in data.get("nodes", [])
        ]

        # Deserialize connections
        connection_list = []
        for conn_data in data.get("connections", []):
            conn_kwargs = conn_data.copy()
            connection_type = conn_kwargs.get("connection_type")

            if isinstance(connection_type, str):
                try:
                    conn_kwargs["connection_type"] = ConnectionType(connection_type)
                except ValueError:
                    conn_kwargs["connection_type"] = ConnectionType.WORKFLOW
            elif connection_type is None:
                conn_kwargs["connection_type"] = ConnectionType.WORKFLOW

            connection_list.append(Connection(**conn_kwargs))

        # Handle default LLM config
        default_llm = None
        if "default_llm_config" in data and data["default_llm_config"]:
            default_llm = LLMConfig(**data["default_llm_config"])

        # Handle publication config
        publication_config = None
        if "publication_config" in data and data["publication_config"]:
            publication_config = WorkflowPublicationConfig.from_dict(
                data["publication_config"]
            )

        # Ensure metadata is a dict
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            nodes=node_list,
            connections=connection_list,
            metadata=metadata,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            is_subgraph=data.get("is_subgraph", False),
            max_execution_time=data.get("max_execution_time", 3600),
            enable_parallel_execution=data.get("enable_parallel_execution", False),
            default_llm_config=default_llm,
            publication_config=publication_config,
            workflow_id=data.get("workflow_id"),
            definition_id=data.get("definition_id"),
        )
