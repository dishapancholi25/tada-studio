"""Enhanced node data structure for workflow graphs.

This module defines the main EnhancedNodeData class that represents
individual workflow nodes with comprehensive configuration support.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import InputSourceConfig, Position
from .configs import (
    AgentConfig,
    CheckpointConfig,
    CodeExecutorConfig,
    ConditionConfig,
    DatabaseInsertConfig,
    DatabaseQueryActionConfig,
    DatabaseQueryConfig,
    DocumentLoadConfig,
    DocumentRetrieveConfig,
    DocumentSearchConfig,
    EmailSendConfig,
    EmailSendToolConfig,
    EndNodeConfig,
    FileReadConfig,
    FileWriteConfig,
    ForEachConfig,
    HttpRequestActionConfig,
    HttpRequestConfig,
    MCPServerConfig,
    SubWorkflowConfig,
    ToolConfig,
    WebSearchConfig,
)
from .enums import NodeType
from .serialization import NodeDeserializer, NodeSerializer
from .validation import NodeValidator


@dataclass
class EnhancedNodeData:
    """Enhanced node data with comprehensive configuration support.

    Main data structure for workflow nodes supporting all node types
    with validation, serialization, and type-specific configurations.

    Attributes:
        uniq_id: Unique identifier for the node
        name: Display name of the node
        type: Node type (START, AGENT, TOOL, etc.)
        position: Canvas position
        nexts: List of next node IDs
        inputs: List of incoming connection node IDs
        description: Node description
        prompt_template: Template for node prompts
        tool_config: Tool node configuration
        agent_config: Agent node configuration
        condition_config: Condition node configuration
        document_search_config: Document search configuration
        database_query_config: Database query configuration
        database_insert_config: Database insert configuration
        http_request_config: HTTP request tool configuration
        http_request_action_config: HTTP request action configuration
        web_search_config: Web search configuration
        mcp_server_config: MCP server configuration
        end_node_config: END node configuration
        checkpoint_config: Checkpoint configuration
        email_send_config: Email send configuration
        file_read_config: File read configuration
        subworkflow_config: Subworkflow configuration
        input_source_config: Input source configuration
        true_next: [Deprecated] True branch target for conditions
        false_next: [Deprecated] False branch target for conditions
        ext: Extension metadata dictionary
        created_at: Creation timestamp
        updated_at: Last update timestamp
        is_enabled: Whether node is enabled
        execution_timeout: Execution timeout in seconds
        retry_count: Current retry count
        max_retries: Maximum retry attempts
        validation_errors: List of validation errors
        is_valid: Whether node passed validation
        subgraph_name: Subgraph name for SUBGRAPH nodes
        is_sub_agent: Whether this is a sub-agent
        is_subworkflow: Whether this is a sub-workflow
        parent_agent_id: Parent agent ID for delegation
        delegation_description: Description for delegation
    """

    # Core identification
    uniq_id: str = ""
    name: str = ""
    type: NodeType = NodeType.START

    # Position
    position: Position = field(default_factory=Position)

    # Connections
    nexts: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)

    # General configuration
    description: str = ""
    prompt_template: str = ""

    # Type-specific configurations
    tool_config: Optional[ToolConfig] = None
    agent_config: Optional[AgentConfig] = None
    condition_config: Optional[ConditionConfig] = None
    document_search_config: Optional[DocumentSearchConfig] = None
    database_query_config: Optional[DatabaseQueryConfig] = None
    database_query_action_config: Optional[DatabaseQueryActionConfig] = None
    database_insert_config: Optional[DatabaseInsertConfig] = None
    http_request_config: Optional[HttpRequestConfig] = None
    http_request_action_config: Optional[HttpRequestActionConfig] = None
    web_search_config: Optional[WebSearchConfig] = None
    mcp_server_config: Optional[MCPServerConfig] = None
    end_node_config: Optional[EndNodeConfig] = None
    checkpoint_config: Optional[CheckpointConfig] = None
    email_send_config: Optional[EmailSendConfig] = None
    email_send_tool_config: Optional[EmailSendToolConfig] = None
    file_read_config: Optional[FileReadConfig] = None
    file_write_config: Optional[FileWriteConfig] = None
    subworkflow_config: Optional[SubWorkflowConfig] = None
    for_each_config: Optional[ForEachConfig] = None
    document_retrieve_config: Optional[DocumentRetrieveConfig] = None
    document_load_config: Optional[DocumentLoadConfig] = None
    code_executor_config: Optional[CodeExecutorConfig] = None

    # Input source configuration
    input_source_config: Optional[InputSourceConfig] = None

    # Condition-specific (backward compatibility)
    true_next: Optional[str] = None
    false_next: Optional[str] = None

    # Additional metadata
    ext: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Execution state
    is_enabled: bool = True
    execution_timeout: int = 300
    retry_count: int = 0
    max_retries: int = 3

    # Validation and error handling
    validation_errors: List[str] = field(default_factory=list)
    is_valid: bool = True

    # Subgraph support
    subgraph_name: Optional[str] = None

    # Sub-agent and sub-workflow support
    is_sub_agent: bool = False
    is_subworkflow: bool = False
    parent_agent_id: Optional[str] = None
    delegation_description: str = ""

    def validate(self) -> bool:
        """Validate node configuration.

        Returns:
            True if validation passed, False otherwise
        """
        self.validation_errors.clear()

        # Use validator to get errors
        errors = NodeValidator.validate_node(self)
        self.validation_errors.extend(errors)

        self.is_valid = len(self.validation_errors) == 0
        return self.is_valid

    def get_connected_tool_nodes(
        self, graph_nodes: List["EnhancedNodeData"]
    ) -> List["EnhancedNodeData"]:
        """Get all tool nodes connected to this node.

        Args:
            graph_nodes: List of all nodes in the graph

        Returns:
            List of connected tool nodes
        """
        if self.type != NodeType.AGENT:
            return []

        tool_nodes = []
        for next_id in self.nexts:
            next_node = next((n for n in graph_nodes if n.uniq_id == next_id), None)
            if next_node and next_node.type == NodeType.TOOL:
                tool_nodes.append(next_node)

        return tool_nodes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization.

        Returns:
            Dictionary representation of the node
        """
        return NodeSerializer.node_to_dict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnhancedNodeData":
        """Create instance from dictionary.

        Args:
            data: Dictionary data to deserialize

        Returns:
            EnhancedNodeData instance
        """
        # Deserialize the data
        deserialized_data = NodeDeserializer.deserialize_node_data(data.copy())

        # Create and return instance
        return cls(**deserialized_data)
