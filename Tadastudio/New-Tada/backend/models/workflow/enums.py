"""Enumeration types for workflow nodes and connections.

This module defines all enum types used in workflow graph definitions,
including node types and connection types.
"""

from enum import Enum


class NodeType(str, Enum):
    """Types of nodes available in workflow graphs.

    Attributes:
        START: Entry point for workflow execution
        STEP: Generic processing step
        TOOL: Custom tool execution
        AGENT: AI agent with LLM capabilities
        CONDITION: Conditional branching logic
        INFO: Information/documentation node
        SUBGRAPH: Nested subgraph execution
        END: Terminal node for workflow
        CHECKPOINT: Human-in-the-loop checkpoint
        DOCUMENT_SEARCH: Document/knowledge base search
        DATABASE_QUERY: Database query operation (AI-callable tool)
        DATABASE_QUERY_ACTION: Database query action (sequential node)
        DATABASE_INSERT: Database insert operation
        HTTP_REQUEST: HTTP request tool (AI-callable)
        HTTP_REQUEST_ACTION: HTTP request action (static)
        WEB_SEARCH: Web search operation
        MCP_SERVER: Model Context Protocol server
        EMAIL_SEND: Email sending action
        FILE_READ: File reading and extraction
        SUBWORKFLOW: Sub-workflow execution
        REVIEW: Agent output review (human or LLM)
        CODE_EXECUTOR: Execute Python or JavaScript code
    """

    START = "START"
    STEP = "STEP"
    TOOL = "TOOL"
    AGENT = "AGENT"
    CONDITION = "CONDITION"
    INFO = "INFO"
    SUBGRAPH = "SUBGRAPH"
    END = "END"
    CHECKPOINT = "CHECKPOINT"
    DOCUMENT_SEARCH = "DOCUMENT_SEARCH"
    DATABASE_QUERY = "DATABASE_QUERY"
    DATABASE_QUERY_ACTION = "DATABASE_QUERY_ACTION"
    DATABASE_INSERT = "DATABASE_INSERT"
    HTTP_REQUEST = "HTTP_REQUEST"
    HTTP_REQUEST_ACTION = "HTTP_REQUEST_ACTION"
    WEB_SEARCH = "WEB_SEARCH"
    MCP_SERVER = "MCP_SERVER"
    EMAIL_SEND = "EMAIL_SEND"
    EMAIL_SEND_TOOL = "EMAIL_SEND_TOOL"
    FILE_READ = "FILE_READ"
    FILE_WRITE = "FILE_WRITE"
    SUBWORKFLOW = "SUBWORKFLOW"
    REVIEW = "REVIEW"
    FOR_EACH = "FOR_EACH"
    DOCUMENT_RETRIEVE = "DOCUMENT_RETRIEVE"
    DOCUMENT_LOAD = "DOCUMENT_LOAD"
    CODE_EXECUTOR = "CODE_EXECUTOR"


class ConnectionType(str, Enum):
    """Types of connections between nodes.

    Attributes:
        WORKFLOW: Normal workflow progression between nodes
        DELEGATION: Orchestrator to sub-agent delegation
        TOOL: Agent to tool node connection
    """

    WORKFLOW = "workflow"
    DELEGATION = "delegation"
    TOOL = "tool"
