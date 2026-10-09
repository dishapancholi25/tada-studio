"""Agent configuration for AI agent nodes.

This module defines the AgentConfig dataclass for configuring
agent behavior, tools, memory, and orchestration.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .llm import LLMConfig

if TYPE_CHECKING:
    from .guardrails import GuardrailsConfig
    from .review import ReviewConfig


@dataclass
class AgentConfig:
    """Configuration for agent nodes.

    Comprehensive configuration for AI agents including LLM settings,
    tool bindings, memory management, document search, and orchestration.

    Attributes:
        agent_type: Type of agent (conversational, react, plan_and_execute)
        system_prompt: System instructions for the agent
        max_iterations: Maximum reasoning iterations
        temperature: Sampling temperature override
        tools: List of available tool names
        memory_enabled: Enable conversation memory
        memory_window_size: Number of recent messages in context
        memory_strategy: Memory scope (thread_scoped, agent_scoped, cross_execution)
        memory_persistence: Memory duration (execution, permanent)
        cross_execution_memory: Allow memory across different executions
        memory_summarization_enabled: Auto-summarize long conversations
        memory_summarization_threshold: Message count before summarization
        custom_instructions: Additional instructions for the agent
        llm_config: LLM connection configuration
        tool_binding_mode: How tools are bound (none, automatic, manual)
        tool_choice: Tool selection mode (auto, none, or specific tool name)
        parallel_tool_calls: Allow parallel tool execution
        max_tool_calls_per_iteration: Maximum tools per iteration
        tool_call_timeout: Tool execution timeout in seconds
        structured_outputs: Structured output schemas
        document_search_enabled: Enable document search capability
        document_collections: Collections to search
        document_ids: Specific documents to search
        search_k: Number of documents to retrieve
        search_type: Search algorithm (similarity, mmr, similarity_score_threshold)
        similarity_threshold: Minimum similarity score
        distance_strategy: Distance metric (cosine, innerProduct, euclidean)
        include_metadata: Include document metadata in results
        citation_format: Citation style (inline, footnote, none, structured)
        hybrid_search_enabled: Enable hybrid vector + keyword search
        search_mode: Search mode (vector, keyword, hybrid)
        keyword_weight: Weight for keyword search (0-1)
        rrf_k: Reciprocal Rank Fusion constant
        full_text_config: PostgreSQL text search config
        min_keyword_relevance: Minimum relevance score for keyword results
        use_reranking: Enable cross-encoder reranking
        rerank_top_k: Number of documents to rerank
        is_orchestrator: Whether this agent orchestrates others
        orchestrator_mode: Orchestration pattern (supervisor, hierarchical, collaborative)
        delegated_agents: List of agent node IDs for delegation
        delegation_strategy: Delegation approach (dynamic, sequential, parallel)
        include_delegation_tools: Auto-generate delegation tools
        handoff_pattern: Handoff mechanism (tool_based, command_based, hybrid)
        share_context: Share execution context with delegated agents
        max_delegation_depth: Maximum nesting depth for delegations
        delegation_timeout: Timeout for delegated tasks in seconds
        guardrails_enabled: Enable guardrails for this agent
        guardrails_config: Complete guardrails configuration (resolved at runtime or export)
        review_config: Configuration for output review gating
    """

    agent_type: str = "conversational"
    system_prompt: str = ""
    max_iterations: int = 50
    temperature: float = 0.0
    tools: List[str] = field(default_factory=list)
    memory_enabled: bool = False
    memory_window_size: int = 10
    memory_strategy: str = "thread_scoped"
    memory_persistence: str = "execution"
    cross_execution_memory: bool = False
    memory_summarization_enabled: bool = False
    memory_summarization_threshold: int = 20
    custom_instructions: str = ""
    llm_config: Optional[LLMConfig] = None
    tool_binding_mode: str = "none"
    tool_choice: str = "auto"
    parallel_tool_calls: bool = False
    max_tool_calls_per_iteration: int = 5
    tool_call_timeout: int = 30
    structured_outputs: List[Dict[str, Any]] = field(default_factory=list)
    document_search_enabled: bool = False
    document_collections: List[str] = field(default_factory=list)
    document_ids: List[str] = field(default_factory=list)
    search_k: int = 3
    search_type: str = "similarity"
    similarity_threshold: float = 0.5
    distance_strategy: str = "cosine"
    include_metadata: bool = True
    citation_format: str = "structured"
    hybrid_search_enabled: bool = False
    search_mode: str = "vector"
    keyword_weight: float = 0.3
    rrf_k: int = 60
    full_text_config: str = "english"
    min_keyword_relevance: float = 0.1
    use_reranking: bool = False
    rerank_top_k: int = 10
    is_orchestrator: bool = False
    orchestrator_mode: str = "supervisor"
    delegated_agents: List[str] = field(default_factory=list)
    delegation_strategy: str = "dynamic"
    include_delegation_tools: bool = True
    handoff_pattern: str = "tool_based"
    share_context: bool = True
    max_delegation_depth: int = 3
    delegation_timeout: int = 300
    guardrails_enabled: bool = True
    guardrails_config: Optional["GuardrailsConfig"] = None
    review_config: Optional["ReviewConfig"] = None
