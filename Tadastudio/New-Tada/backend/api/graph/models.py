"""Pydantic models for Graph API requests and responses.

This module defines all request and response models for the Graph API endpoints,
providing data validation and serialization.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Graph Management Models
# ============================================================================


class CreateGraphRequest(BaseModel):
    """Request model for creating a new graph."""

    name: str = Field(..., description="Graph name")
    description: str = Field("", description="Graph description")


class ImportRawWorkflowRequest(BaseModel):
    """Request model for importing a raw workflow JSON."""

    name: str = Field(..., description="Workflow name")
    description: str = Field("", description="Workflow description")
    workflow_json: Dict[str, Any] = Field(
        ..., description="Complete workflow JSON definition"
    )


class UpdateWorkflowNameRequest(BaseModel):
    """Request model for updating a workflow name."""

    new_name: str = Field(..., description="New workflow name")


class UpdateWorkflowDescriptionRequest(BaseModel):
    """Request model for updating a workflow description."""

    description: str = Field(..., description="New workflow description")


class DuplicateWorkflowRequest(BaseModel):
    """Request model for duplicating a workflow."""

    new_name: str = Field(..., description="Name for the duplicated workflow")


# ============================================================================
# Node Management Models
# ============================================================================


class CreateNodeRequest(BaseModel):
    """Request model for creating a new node."""

    graph_name: str = Field(..., description="Target graph name")
    node_type: str = Field(..., description="Type of node to create")
    name: str = Field(..., description="Node name")
    position: Optional[Dict[str, float]] = Field(
        None, description="Node position {x, y}"
    )
    tool_template: Optional[str] = Field(
        None, description="Tool template name for TOOL nodes"
    )
    agent_template: Optional[str] = Field(
        None, description="Agent template name for AGENT nodes"
    )
    description: Optional[str] = Field("", description="Node description")
    llm_type: Optional[str] = Field(
        None, description="LLM provider type (azure_openai, openai, anthropic)"
    )
    model_name: Optional[str] = Field(
        None, description="Model name (gpt-4, claude-3-sonnet, etc.)"
    )
    document_search_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for DOCUMENT_SEARCH nodes"
    )
    database_query_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for DATABASE_QUERY nodes"
    )
    http_request_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for HTTP_REQUEST nodes"
    )
    web_search_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for WEB_SEARCH nodes"
    )
    mcp_server_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for MCP_SERVER nodes"
    )
    subworkflow_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for SUBWORKFLOW nodes"
    )
    agent_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for AGENT nodes"
    )
    condition_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for CONDITION nodes"
    )
    input_source_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for INPUT_SOURCE nodes"
    )
    email_send_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for EMAIL_SEND nodes"
    )
    email_send_tool_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for EMAIL_SEND_TOOL nodes"
    )
    file_read_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for FILE_READ nodes"
    )
    checkpoint_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for CHECKPOINT nodes"
    )
    database_insert_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for DATABASE_INSERT nodes"
    )
    database_query_action_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for DATABASE_QUERY_ACTION nodes"
    )
    http_request_action_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for HTTP_REQUEST_ACTION nodes"
    )
    end_node_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for END nodes"
    )
    for_each_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for FOR_EACH nodes"
    )
    code_executor_config: Optional[Dict[str, Any]] = Field(
        None, description="Configuration for CODE_EXECUTOR nodes"
    )
    prompt_template: Optional[str] = Field(
        None, description="Prompt template for nodes that support it"
    )


class CreateSubAgentRequest(BaseModel):
    """Request model for creating a sub-agent node."""

    graph_name: str = Field(..., description="Target graph name")
    parent_agent_id: str = Field(..., description="Parent agent (orchestrator) ID")
    name: Optional[str] = Field(None, description="Sub-agent name")
    position: Optional[Dict[str, float]] = Field(
        None, description="Node position {x, y}"
    )
    delegation_description: str = Field(
        "", description="Description of when/how to use this sub-agent"
    )
    agent_template: Optional[str] = Field(None, description="Agent template to use")


class UpdateNodeRequest(BaseModel):
    """Request model for updating a node."""

    graph_name: str = Field(..., description="Target graph name")
    node_id: str = Field(..., description="Node ID to update")
    updates: Dict[str, Any] = Field(..., description="Updates to apply")


class NodeConfigRequest(BaseModel):
    """Request model for configuring node-specific settings."""

    graph_name: str = Field(..., description="Target graph name")
    node_id: str = Field(..., description="Node ID to configure")
    config: Dict[str, Any] = Field(..., description="Node configuration")


# ============================================================================
# Connection Management Models
# ============================================================================


class CreateConnectionRequest(BaseModel):
    """Request model for creating a connection between nodes."""

    graph_name: str = Field(..., description="Target graph name")
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    source_handle: Optional[str] = Field(
        None, description="Source handle (for condition nodes)"
    )
    target_handle: Optional[str] = Field(None, description="Target handle")
    label: Optional[str] = Field(None, description="Connection label")
    connection_type: Optional[str] = Field(
        "workflow", description="Connection type (workflow, tool, delegation)"
    )


class DeleteConnectionRequest(BaseModel):
    """Request model for deleting a connection."""

    graph_name: str = Field(..., description="Target graph name")
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")


# ============================================================================
# LLM Configuration Models
# ============================================================================


class LLMConfigRequest(BaseModel):
    """Request model for configuring LLM settings for an agent node."""

    graph_name: str = Field(..., description="Target graph name")
    node_id: str = Field(..., description="Agent node ID to configure")
    llm_config: Dict[str, Any] = Field(..., description="LLM configuration")


class TestLLMRequest(BaseModel):
    """Request model for testing LLM connection."""

    llm_config: Dict[str, Any] = Field(..., description="LLM configuration to test")
    test_message: str = Field(
        "Hello, please respond to test the connection.", description="Test message"
    )


# ============================================================================
# Execution Models
# ============================================================================


class GraphExecutionRequest(BaseModel):
    """Request model for executing a graph."""

    graph_name: str = Field(..., description="Graph to execute")
    initial_input: Dict[str, Any] = Field(
        default_factory=dict, description="Initial input data"
    )
    username: Optional[str] = Field("default", description="Username")
    async_execution: bool = Field(
        True, description="Whether to run execution asynchronously"
    )
    file_info: Optional[Dict[str, Any]] = Field(
        None, description="File information for FILE_READ nodes"
    )


class ChatRequest(BaseModel):
    """Request model for chatting with an agent."""

    message: str = Field(..., description="User message")


# ============================================================================
# Batch Update Models
# ============================================================================


class BatchUpdateChange(BaseModel):
    """Single change in a batch update."""

    type: str = Field(..., description="Type of change")
    data: Dict[str, Any] = Field(..., description="Change data")


class BatchUpdateRequest(BaseModel):
    """Request model for batch updating a graph."""

    graph_name: str = Field(..., description="Target graph name")
    changes: List[Dict[str, Any]] = Field(..., description="List of changes to apply")


# ============================================================================
# Response Models
# ============================================================================


class GraphResponse(BaseModel):
    """Response model for graph operations."""

    success: bool
    message: str
    graph: Optional[Dict[str, Any]] = None


class NodeResponse(BaseModel):
    """Response model for node operations."""

    success: bool
    message: str
    node: Optional[Dict[str, Any]] = None
    graph: Optional[Dict[str, Any]] = None


class ConnectionResponse(BaseModel):
    """Response model for connection operations."""

    success: bool
    message: str


class ExecutionResponse(BaseModel):
    """Response model for execution operations."""

    success: bool
    message: str
    execution_id: str
    async_execution: bool = Field(alias="async")
    status_endpoint: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None


class ExecutionStatusResponse(BaseModel):
    """Response model for execution status."""

    success: bool
    execution_status: Dict[str, Any]


class HealthResponse(BaseModel):
    """Response model for health check."""

    success: bool
    status: str
    timestamp: str
    active_graphs: int
    active_executions: int
    total_executions: int


class ValidationResponse(BaseModel):
    """Response model for graph validation."""

    success: bool
    validation: Dict[str, Any]


class ExportResponse(BaseModel):
    """Response model for graph export."""

    success: bool
    format: str
    data: Dict[str, Any]


class LLMProvidersResponse(BaseModel):
    """Response model for LLM providers."""

    success: bool
    providers: List[Dict[str, Any]]


class LLMModelsResponse(BaseModel):
    """Response model for LLM models."""

    success: bool
    provider: str
    models: List[Dict[str, Any]]


class LLMTestResponse(BaseModel):
    """Response model for LLM connection test."""

    success: bool
    test_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None


class TemplatesResponse(BaseModel):
    """Response model for templates."""

    success: bool
    templates: Dict[str, Any]


class NodeTypesResponse(BaseModel):
    """Response model for available node types."""

    success: bool
    node_types: List[Dict[str, str]]


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    success: bool
    file_info: Dict[str, Any]


class FileMetadataResponse(BaseModel):
    """Response model for file metadata."""

    success: bool
    metadata: Dict[str, Any]


class FileProcessingResponse(BaseModel):
    """Response model for file processing."""

    success: bool
    content: str
    metadata: Dict[str, Any]
    extraction_method: str


class ExecutionHistoryResponse(BaseModel):
    """Response model for execution history."""

    success: bool
    execution_id: str
    execution_history: Dict[str, Any]


class ExecutionsListResponse(BaseModel):
    """Response model for listing executions."""

    success: bool
    active_executions: List[Dict[str, Any]]
    recent_executions: List[Dict[str, Any]]


class AgentToolExecutionsResponse(BaseModel):
    """Response model for agent tool executions."""

    success: bool
    agent_id: str
    execution_id: str
    total_tool_executions: int
    grouped_executions: Dict[str, List[Dict[str, Any]]]
    tool_executions: List[Dict[str, Any]]


class StructuredOutputValidationResponse(BaseModel):
    """Response model for structured output schema validation."""

    success: bool
    validation_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class StructuredOutputPreviewResponse(BaseModel):
    """Response model for structured output code preview."""

    success: bool
    model_code: Optional[str] = None
    tool_code: Optional[str] = None
    errors: Optional[List[str]] = None
    error: Optional[str] = None
