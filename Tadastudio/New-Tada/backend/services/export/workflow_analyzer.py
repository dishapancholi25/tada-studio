"""Workflow analyzer for Python export.

Performs a single-pass analysis of a GraphData object to determine
what components need to be included in the generated Python file.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from backend.models.workflow import EnhancedNodeData, GraphData, NodeType


# Node types supported in V1 export
SUPPORTED_NODE_TYPES = {
    NodeType.START,
    NodeType.END,
    NodeType.AGENT,
    NodeType.CONDITION,
    NodeType.HTTP_REQUEST,
    NodeType.WEB_SEARCH,
    NodeType.DOCUMENT_SEARCH,
}

# Node types that are tools bound to agents (not standalone graph nodes)
TOOL_NODE_TYPES = {
    NodeType.HTTP_REQUEST,
    NodeType.WEB_SEARCH,
    NodeType.DOCUMENT_SEARCH,
}


@dataclass
class EdgeTopology:
    """Analyzed edge topology of the workflow."""

    sequential_edges: List[Tuple[str, str]] = field(default_factory=list)
    conditional_edges: Dict[str, Dict[str, str]] = field(default_factory=dict)
    parallel_sources: Dict[str, List[str]] = field(default_factory=dict)
    entry_node_id: str = ""


@dataclass
class WorkflowAnalysis:
    """Complete analysis of a workflow for export."""

    # Node categorization
    agent_nodes: List[EnhancedNodeData] = field(default_factory=list)
    condition_nodes: List[EnhancedNodeData] = field(default_factory=list)
    tool_nodes: List[EnhancedNodeData] = field(default_factory=list)
    start_node: EnhancedNodeData = None
    end_nodes: List[EnhancedNodeData] = field(default_factory=list)

    # What's actually used
    llm_providers_used: Set[str] = field(default_factory=set)
    tool_types_used: Set[str] = field(default_factory=set)
    input_modes_used: Set[str] = field(default_factory=set)
    condition_types_used: Set[str] = field(default_factory=set)

    # Tool-agent binding map: agent_id -> [tool_nodes]
    agent_tool_map: Dict[str, List[EnhancedNodeData]] = field(default_factory=dict)

    # Edge topology
    edge_topology: EdgeTopology = field(default_factory=EdgeTopology)

    # Required environment variables: env_var -> [node_names]
    env_vars_required: Dict[str, List[str]] = field(default_factory=dict)

    # Unsupported nodes (warnings)
    unsupported_nodes: List[EnhancedNodeData] = field(default_factory=list)

    # Node lookup map: node_id -> node
    node_map: Dict[str, EnhancedNodeData] = field(default_factory=dict)

    # Workflow name
    workflow_name: str = ""

    @property
    def has_parallel_edges(self) -> bool:
        return bool(self.edge_topology.parallel_sources)

    @property
    def has_conditional_edges(self) -> bool:
        return bool(self.edge_topology.conditional_edges)

    @property
    def workflow_nodes(self) -> List[EnhancedNodeData]:
        """All nodes that become graph nodes (agents + conditions)."""
        return self.agent_nodes + self.condition_nodes


class WorkflowAnalyzer:
    """Analyzes a GraphData object for Python export."""

    def analyze(self, graph: GraphData) -> WorkflowAnalysis:
        """Analyze a workflow and return a WorkflowAnalysis."""
        analysis = WorkflowAnalysis()
        analysis.workflow_name = graph.name or "workflow"

        # Build node lookup map
        for node in graph.nodes:
            analysis.node_map[node.uniq_id] = node

        # Phase 1: Categorize nodes
        self._categorize_nodes(graph, analysis)

        # Phase 2: Analyze tool-agent bindings
        self._analyze_tool_bindings(graph, analysis)

        # Phase 3: Analyze LLM providers
        self._analyze_llm_providers(analysis)

        # Phase 4: Analyze input modes
        self._analyze_input_modes(analysis)

        # Phase 5: Analyze condition types
        self._analyze_condition_types(analysis)

        # Phase 6: Analyze edge topology
        self._analyze_edges(graph, analysis)

        # Phase 7: Collect environment variables
        self._collect_env_vars(analysis)

        return analysis

    def _categorize_nodes(self, graph: GraphData, analysis: WorkflowAnalysis) -> None:
        """Categorize nodes by type."""
        for node in graph.nodes:
            if not node.is_enabled:
                continue

            if node.type == NodeType.START:
                analysis.start_node = node
            elif node.type == NodeType.END:
                analysis.end_nodes.append(node)
            elif node.type == NodeType.AGENT:
                if not node.is_sub_agent:
                    analysis.agent_nodes.append(node)
            elif node.type == NodeType.CONDITION:
                analysis.condition_nodes.append(node)
            elif node.type in TOOL_NODE_TYPES:
                analysis.tool_nodes.append(node)
                type_val = (
                    node.type.value if hasattr(node.type, "value") else str(node.type)
                )
                analysis.tool_types_used.add(type_val)
            elif node.type not in SUPPORTED_NODE_TYPES:
                analysis.unsupported_nodes.append(node)

    def _analyze_tool_bindings(
        self, graph: GraphData, analysis: WorkflowAnalysis
    ) -> None:
        """Map tools to their parent agents via tool connections."""
        for conn in graph.connections:
            if conn.connection_type == "tool":
                agent_id = conn.source_id
                tool_id = conn.target_id
                tool_node = analysis.node_map.get(tool_id)
                if tool_node and tool_node.type in TOOL_NODE_TYPES:
                    if agent_id not in analysis.agent_tool_map:
                        analysis.agent_tool_map[agent_id] = []
                    analysis.agent_tool_map[agent_id].append(tool_node)

    def _analyze_llm_providers(self, analysis: WorkflowAnalysis) -> None:
        """Collect LLM providers used by agent nodes."""
        for node in analysis.agent_nodes:
            if node.agent_config and node.agent_config.llm_config:
                provider = node.agent_config.llm_config.provider
                if provider:
                    analysis.llm_providers_used.add(provider)

        # Also check condition nodes with LLM evaluation
        for node in analysis.condition_nodes:
            if node.condition_config:
                cc = node.condition_config
                ctype = getattr(cc, "condition_type", None) or (
                    cc.get("condition_type") if isinstance(cc, dict) else None
                )
                if ctype == "llm" and hasattr(cc, "llm_config") and cc.llm_config:
                    provider = cc.llm_config.provider
                    if provider:
                        analysis.llm_providers_used.add(provider)

    def _analyze_input_modes(self, analysis: WorkflowAnalysis) -> None:
        """Collect input source modes used by nodes."""
        for node in analysis.agent_nodes + analysis.condition_nodes:
            if node.input_source_config:
                mode = getattr(node.input_source_config, "source_mode", "previous")
                analysis.input_modes_used.add(mode)
            else:
                analysis.input_modes_used.add("previous")

    def _analyze_condition_types(self, analysis: WorkflowAnalysis) -> None:
        """Collect condition evaluation types."""
        for node in analysis.condition_nodes:
            if node.condition_config:
                cc = node.condition_config
                if hasattr(cc, "__dict__"):
                    ctype = getattr(cc, "condition_type", "simple")
                    bmode = getattr(cc, "branch_mode", "binary")
                else:
                    ctype = cc.get("condition_type", "simple")
                    bmode = cc.get("branch_mode", "binary")
                analysis.condition_types_used.add(ctype)
                analysis.condition_types_used.add(bmode)

    def _analyze_edges(self, graph: GraphData, analysis: WorkflowAnalysis) -> None:
        """Analyze connection topology."""
        if not analysis.start_node:
            return

        end_node_ids = {n.uniq_id for n in analysis.end_nodes}
        tool_node_ids = {n.uniq_id for n in analysis.tool_nodes}
        sub_agent_ids = {
            n.uniq_id for n in graph.nodes if getattr(n, "is_sub_agent", False)
        }
        condition_node_ids = {n.uniq_id for n in analysis.condition_nodes}

        # Find entry node (first node after START)
        for conn in graph.connections:
            if conn.source_id == analysis.start_node.uniq_id:
                analysis.edge_topology.entry_node_id = conn.target_id
                break

        # Count targets per source for parallel detection
        source_to_targets: Dict[str, List[Tuple[str, str, str]]] = {}

        for conn in graph.connections:
            # Skip non-workflow connections
            if conn.connection_type == "tool" or conn.connection_type == "delegation":
                continue
            if conn.source_id in tool_node_ids or conn.target_id in tool_node_ids:
                continue
            if conn.source_id in sub_agent_ids or conn.target_id in sub_agent_ids:
                continue
            if conn.source_id == analysis.start_node.uniq_id:
                continue

            target = "__end__" if conn.target_id in end_node_ids else conn.target_id

            if conn.source_id not in source_to_targets:
                source_to_targets[conn.source_id] = []
            source_to_targets[conn.source_id].append(
                (target, conn.source_handle or "", conn.label or "")
            )

        # Classify edges
        for source_id, targets in source_to_targets.items():
            if source_id in condition_node_ids:
                # Conditional edges
                routing_map = {}
                for target, handle, label in targets:
                    if handle:
                        key = handle.replace("branch-", "")
                    elif label:
                        key = label
                    else:
                        key = "default"
                    routing_map[key] = target
                analysis.edge_topology.conditional_edges[source_id] = routing_map
            elif len(targets) > 1:
                # Parallel fan-out
                analysis.edge_topology.parallel_sources[source_id] = [
                    t[0] for t in targets
                ]
            else:
                # Sequential
                analysis.edge_topology.sequential_edges.append(
                    (source_id, targets[0][0])
                )

    def _collect_env_vars(self, analysis: WorkflowAnalysis) -> None:
        """Collect required environment variables."""
        for node in analysis.agent_nodes:
            if node.agent_config and node.agent_config.llm_config:
                llm = node.agent_config.llm_config
                if llm.api_key_env_var:
                    env_list = analysis.env_vars_required.setdefault(
                        llm.api_key_env_var, []
                    )
                    if node.name not in env_list:
                        env_list.append(node.name)
                if llm.base_url_env_var:
                    env_list = analysis.env_vars_required.setdefault(
                        llm.base_url_env_var, []
                    )
                    if node.name not in env_list:
                        env_list.append(node.name)

        # Web search API keys
        for node in analysis.tool_nodes:
            if node.type == NodeType.WEB_SEARCH and node.web_search_config:
                wsc = node.web_search_config
                provider = getattr(wsc, "search_provider", "duckduckgo")
                if provider == "tavily":
                    analysis.env_vars_required.setdefault("TAVILY_API_KEY", []).append(
                        node.name
                    )

        # Document search needs database
        for node in analysis.tool_nodes:
            if node.type == NodeType.DOCUMENT_SEARCH:
                analysis.env_vars_required.setdefault("DATABASE_URL", []).append(
                    node.name
                )
