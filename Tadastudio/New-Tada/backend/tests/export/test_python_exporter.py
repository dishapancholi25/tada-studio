"""Tests for the Python workflow exporter.

Tests the complete export pipeline from GraphData to valid Python source code.
"""

import ast
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Minimal dataclass stubs matching the actual models for testing
@dataclass
class LLMConfig:
    provider: str = "openai"
    model_name: str = "gpt-4o"
    model_type: str = "llm"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    deployment_name: Optional[str] = None
    api_key_env_var: str = "OPENAI_API_KEY"
    base_url_env_var: str = ""
    model_deployment_id: Optional[str] = None
    credentials: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    supports_function_calling: bool = True
    supports_streaming: bool = True
    timeout: int = 60
    max_retries: int = 3


@dataclass
class AgentConfig:
    agent_type: str = "conversational"
    system_prompt: str = ""
    max_iterations: int = 10
    temperature: float = 0.7
    tools: List[str] = field(default_factory=list)
    memory_enabled: bool = False
    llm_config: Optional[LLMConfig] = None
    tool_binding_mode: str = "automatic"
    is_orchestrator: bool = False
    structured_outputs: List[Dict[str, Any]] = field(default_factory=list)
    review_config: Optional[Any] = None


@dataclass
class ConditionConfig:
    branch_mode: str = "binary"
    branches: List[Any] = field(default_factory=list)
    condition_type: str = "simple"
    simple_conditions: List[Dict[str, Any]] = field(default_factory=list)
    expression: str = ""
    llm_prompt: str = ""
    llm_config: Optional[LLMConfig] = None
    logic_operator: str = "AND"
    input_source: str = "previous"
    source_node_id: Optional[str] = None
    field_path: str = ""


@dataclass
class InputSourceConfig:
    source_mode: str = "previous"
    source_node_id: Optional[str] = None
    source_node_ids: List[str] = field(default_factory=list)
    use_structured_field: bool = False
    selected_fields: List[str] = field(default_factory=list)
    custom_template: Optional[str] = None


@dataclass
class WebSearchConfig:
    search_provider: str = "duckduckgo"
    api_key: str = ""
    max_results: int = 5
    search_depth: str = "basic"
    include_answer: bool = False
    include_raw_content: bool = False
    include_images: bool = False
    timeout_seconds: int = 10
    region: str = "wt-wt"
    safe_search: str = "moderate"
    time_range: str = ""
    parent_agent_id: Optional[str] = None


@dataclass
class HttpRequestConfig:
    url_template: str = ""
    method: str = "GET"
    parameter_schema: Dict = field(default_factory=dict)
    headers: Dict = field(default_factory=dict)
    query_params: Dict = field(default_factory=dict)
    auth_type: str = "none"
    auth_config: Dict = field(default_factory=dict)
    request_body_template: str = ""
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    response_format: str = "auto"
    error_handling: str = "fail"
    follow_redirects: bool = True
    verify_ssl: bool = True
    extract_path: str = ""
    success_status_codes: List[int] = field(default_factory=lambda: [200, 201])


@dataclass
class Position:
    x: float = 0.0
    y: float = 0.0


@dataclass
class Connection:
    source_id: str = ""
    target_id: str = ""
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None
    label: Optional[str] = None
    connection_type: str = "workflow"


class NodeType:
    """Enum stub for testing."""

    START = "START"
    END = "END"
    AGENT = "AGENT"
    CONDITION = "CONDITION"
    HTTP_REQUEST = "HTTP_REQUEST"
    WEB_SEARCH = "WEB_SEARCH"
    DOCUMENT_SEARCH = "DOCUMENT_SEARCH"
    SUBWORKFLOW = "SUBWORKFLOW"


@dataclass
class EnhancedNodeData:
    uniq_id: str = ""
    name: str = ""
    type: str = "AGENT"
    position: Position = field(default_factory=Position)
    nexts: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    description: str = ""
    prompt_template: str = ""
    agent_config: Optional[AgentConfig] = None
    condition_config: Optional[ConditionConfig] = None
    http_request_config: Optional[HttpRequestConfig] = None
    web_search_config: Optional[WebSearchConfig] = None
    document_search_config: Optional[Any] = None
    input_source_config: Optional[InputSourceConfig] = None
    is_enabled: bool = True
    is_sub_agent: bool = False
    is_subworkflow: bool = False
    parent_agent_id: Optional[str] = None
    ext: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphData:
    name: str = "test_workflow"
    description: str = ""
    nodes: List[EnhancedNodeData] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_subgraph: bool = False
    max_execution_time: int = 3600
    enable_parallel_execution: bool = False
    default_llm_config: Optional[LLMConfig] = None


# ============================================================================
# Fixtures
# ============================================================================


def make_simple_workflow() -> GraphData:
    """START -> AGENT -> END"""
    return GraphData(
        name="Simple Workflow",
        nodes=[
            EnhancedNodeData(uniq_id="start_1", name="Start", type=NodeType.START),
            EnhancedNodeData(
                uniq_id="agent_1",
                name="Research Agent",
                type=NodeType.AGENT,
                agent_config=AgentConfig(
                    system_prompt="You are a research assistant.",
                    llm_config=LLMConfig(
                        provider="openai",
                        model_name="gpt-4o",
                        api_key_env_var="OPENAI_API_KEY",
                    ),
                ),
            ),
            EnhancedNodeData(uniq_id="end_1", name="End", type=NodeType.END),
        ],
        connections=[
            Connection(source_id="start_1", target_id="agent_1"),
            Connection(source_id="agent_1", target_id="end_1"),
        ],
    )


def make_condition_workflow() -> GraphData:
    """START -> AGENT -> CONDITION -> AGENT_A / AGENT_B -> END"""
    return GraphData(
        name="Condition Workflow",
        nodes=[
            EnhancedNodeData(uniq_id="start_1", name="Start", type=NodeType.START),
            EnhancedNodeData(
                uniq_id="agent_1",
                name="Analyzer",
                type=NodeType.AGENT,
                agent_config=AgentConfig(
                    system_prompt="Analyze the input.",
                    llm_config=LLMConfig(provider="openai", model_name="gpt-4o"),
                ),
            ),
            EnhancedNodeData(
                uniq_id="cond_1",
                name="Quality Check",
                type=NodeType.CONDITION,
                condition_config=ConditionConfig(
                    branch_mode="binary",
                    condition_type="simple",
                    simple_conditions=[
                        {
                            "operator": "contains",
                            "value": "good",
                            "input_source": "previous",
                        },
                    ],
                ),
            ),
            EnhancedNodeData(
                uniq_id="agent_2",
                name="Good Path Agent",
                type=NodeType.AGENT,
                agent_config=AgentConfig(
                    system_prompt="Handle the good case.",
                    llm_config=LLMConfig(provider="openai", model_name="gpt-4o"),
                ),
            ),
            EnhancedNodeData(
                uniq_id="agent_3",
                name="Bad Path Agent",
                type=NodeType.AGENT,
                agent_config=AgentConfig(
                    system_prompt="Handle the bad case.",
                    llm_config=LLMConfig(provider="openai", model_name="gpt-4o"),
                ),
            ),
            EnhancedNodeData(uniq_id="end_1", name="End", type=NodeType.END),
        ],
        connections=[
            Connection(source_id="start_1", target_id="agent_1"),
            Connection(source_id="agent_1", target_id="cond_1"),
            Connection(
                source_id="cond_1",
                target_id="agent_2",
                source_handle="branch-0",
            ),
            Connection(
                source_id="cond_1",
                target_id="agent_3",
                source_handle="branch-1",
            ),
            Connection(source_id="agent_2", target_id="end_1"),
            Connection(source_id="agent_3", target_id="end_1"),
        ],
    )


def make_tool_workflow() -> GraphData:
    """START -> AGENT[WEB_SEARCH] -> END"""
    return GraphData(
        name="Tool Workflow",
        nodes=[
            EnhancedNodeData(uniq_id="start_1", name="Start", type=NodeType.START),
            EnhancedNodeData(
                uniq_id="agent_1",
                name="Research Agent",
                type=NodeType.AGENT,
                agent_config=AgentConfig(
                    system_prompt="Search the web for information.",
                    llm_config=LLMConfig(provider="openai", model_name="gpt-4o"),
                ),
            ),
            EnhancedNodeData(
                uniq_id="ws_1",
                name="Web Search",
                type=NodeType.WEB_SEARCH,
                web_search_config=WebSearchConfig(
                    search_provider="duckduckgo",
                    max_results=5,
                ),
            ),
            EnhancedNodeData(uniq_id="end_1", name="End", type=NodeType.END),
        ],
        connections=[
            Connection(source_id="start_1", target_id="agent_1"),
            Connection(
                source_id="agent_1",
                target_id="ws_1",
                connection_type="tool",
            ),
            Connection(source_id="agent_1", target_id="end_1"),
        ],
    )


# ============================================================================
# Tests
# ============================================================================


class TestPythonExporter:
    """Integration tests for the PythonExporter."""

    def _get_exporter(self):
        """Create exporter using real models, but with test data."""
        from backend.services.export.python_exporter import PythonExporter

        return PythonExporter()

    def test_simple_workflow_generates_valid_python(self):
        """Test that a simple START->AGENT->END workflow generates valid Python."""
        exporter = self._get_exporter()
        code = exporter.export(make_simple_workflow())

        # Must parse as valid Python
        ast.parse(code)

        # Must contain key elements
        assert "class WorkflowState" in code
        assert "def build_graph" in code
        assert "app = graph.compile()" in code
        assert "node_research_agent" in code
        assert "create_llm_research_agent" in code
        assert "OPENAI_API_KEY" in code

    def test_condition_workflow_generates_valid_python(self):
        """Test that a workflow with conditions generates valid Python."""
        exporter = self._get_exporter()
        code = exporter.export(make_condition_workflow())

        ast.parse(code)

        assert "node_quality_check" in code
        assert "route_quality_check" in code
        assert "add_conditional_edges" in code
        assert "node_good_path_agent" in code
        assert "node_bad_path_agent" in code

    def test_tool_workflow_generates_valid_python(self):
        """Test that a workflow with tools generates valid Python."""
        exporter = self._get_exporter()
        code = exporter.export(make_tool_workflow())

        ast.parse(code)

        assert "create_tool_web_search" in code
        assert "DuckDuckGoSearchResults" in code
        assert "bind_tools" in code

    def test_header_contains_env_vars(self):
        """Test that the header lists required environment variables."""
        exporter = self._get_exporter()
        code = exporter.export(make_simple_workflow())

        assert "OPENAI_API_KEY" in code

    def test_header_contains_workflow_name(self):
        """Test that the header contains the workflow name."""
        exporter = self._get_exporter()
        code = exporter.export(make_simple_workflow())

        assert "Simple Workflow" in code

    def test_reducers_are_included(self):
        """Test that state reducers are included in the output."""
        exporter = self._get_exporter()
        code = exporter.export(make_simple_workflow())

        assert "def merge_node_outputs" in code
        assert "def last_value_reducer" in code
        assert "def merge_results" in code

    def test_main_block_included(self):
        """Test that __main__ block is included."""
        exporter = self._get_exporter()
        code = exporter.export(make_simple_workflow())

        assert 'if __name__ == "__main__"' in code
        assert "asyncio.run(main())" in code

    def test_imports_include_langgraph(self):
        """Test that LangGraph imports are included."""
        exporter = self._get_exporter()
        code = exporter.export(make_simple_workflow())

        assert "from langgraph.graph import END, StateGraph" in code
        assert "from langgraph.graph.message import add_messages" in code

    def test_azure_openai_provider(self):
        """Test Azure OpenAI LLM factory generation."""
        graph = make_simple_workflow()
        graph.nodes[1].agent_config.llm_config = LLMConfig(
            provider="azure_openai",
            model_name="gpt-4o",
            deployment_name="gpt-4o-deploy",
            api_key_env_var="AZURE_OPENAI_API_KEY",
            base_url_env_var="AZURE_OPENAI_ENDPOINT",
            api_version="2024-02-01",
        )

        exporter = self._get_exporter()
        code = exporter.export(graph)

        ast.parse(code)
        assert "AzureChatOpenAI" in code
        assert "AZURE_OPENAI_API_KEY" in code
        assert "AZURE_OPENAI_ENDPOINT" in code

    def test_anthropic_provider(self):
        """Test Anthropic LLM factory generation."""
        graph = make_simple_workflow()
        graph.nodes[1].agent_config.llm_config = LLMConfig(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            api_key_env_var="ANTHROPIC_API_KEY",
        )

        exporter = self._get_exporter()
        code = exporter.export(graph)

        ast.parse(code)
        assert "ChatAnthropic" in code
        assert "ANTHROPIC_API_KEY" in code


class TestWorkflowAnalyzer:
    """Tests for the WorkflowAnalyzer."""

    def _get_analyzer(self):
        from backend.services.export.workflow_analyzer import WorkflowAnalyzer

        return WorkflowAnalyzer()

    def test_categorizes_nodes_correctly(self):
        """Test that nodes are categorized by type."""
        analyzer = self._get_analyzer()
        analysis = analyzer.analyze(make_condition_workflow())

        assert len(analysis.agent_nodes) == 3
        assert len(analysis.condition_nodes) == 1
        assert analysis.start_node is not None
        assert len(analysis.end_nodes) == 1

    def test_detects_tool_bindings(self):
        """Test that tool-agent bindings are detected."""
        analyzer = self._get_analyzer()
        analysis = analyzer.analyze(make_tool_workflow())

        assert "agent_1" in analysis.agent_tool_map
        assert len(analysis.agent_tool_map["agent_1"]) == 1
        assert analysis.agent_tool_map["agent_1"][0].type == NodeType.WEB_SEARCH

    def test_detects_llm_providers(self):
        """Test that LLM providers are detected."""
        analyzer = self._get_analyzer()
        analysis = analyzer.analyze(make_simple_workflow())

        assert "openai" in analysis.llm_providers_used

    def test_detects_condition_types(self):
        """Test that condition types are detected."""
        analyzer = self._get_analyzer()
        analysis = analyzer.analyze(make_condition_workflow())

        assert "simple" in analysis.condition_types_used
        assert "binary" in analysis.condition_types_used

    def test_analyzes_edge_topology(self):
        """Test that edge topology is correctly analyzed."""
        analyzer = self._get_analyzer()
        analysis = analyzer.analyze(make_condition_workflow())

        # Should have conditional edges from condition node
        assert "cond_1" in analysis.edge_topology.conditional_edges
        targets = analysis.edge_topology.conditional_edges["cond_1"]
        assert "0" in targets
        assert "1" in targets

        # Should have entry node
        assert analysis.edge_topology.entry_node_id == "agent_1"

    def test_collects_env_vars(self):
        """Test that environment variables are collected."""
        analyzer = self._get_analyzer()
        analysis = analyzer.analyze(make_simple_workflow())

        assert "OPENAI_API_KEY" in analysis.env_vars_required

    def test_detects_unsupported_nodes(self):
        """Test that unsupported node types are flagged."""
        graph = make_simple_workflow()
        graph.nodes.append(
            EnhancedNodeData(
                uniq_id="sub_1",
                name="Sub Workflow",
                type=NodeType.SUBWORKFLOW,
            )
        )

        analyzer = self._get_analyzer()
        analysis = analyzer.analyze(graph)

        assert len(analysis.unsupported_nodes) == 1
        assert analysis.unsupported_nodes[0].name == "Sub Workflow"
