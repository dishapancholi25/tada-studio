import { detectProviderFromNodeName } from "@/components/icons/McpProviderIcons";

/** Node shape as returned by the API (uses uniq_id, has nexts array) */
interface ApiNode {
	uniq_id: string;
	id?: string;
	name: string;
	type: string;
	nexts?: string[];
	mcp_server_config?: { provider?: string; server_name?: string };
	[key: string]: any;
}

/** Connection shape as returned by the API */
interface GraphConnection {
	source?: string;
	target?: string;
	source_id?: string;
	target_id?: string;
	label?: string;
	connection_type?: string;
	data?: { label?: string; branch_label?: string };
}

/** Graph shape from the API */
interface GraphShape {
	nodes: ApiNode[];
	edges?: GraphConnection[];
	connections?: GraphConnection[];
}

/** A node in the expected execution order */
export interface WorkflowStep {
	nodeId: string;
	nodeName: string;
	nodeType: string;
	order: number;
	branches?: { label: string; targetNodeId: string }[];
	/** Whether this node is a tool attached to an agent (e.g. MCP_SERVER tool) */
	isTool?: boolean;
	/** The parent agent node ID when isTool is true */
	parentNodeId?: string;
	/** Detected MCP provider key for native icon lookup (e.g. "onedrive", "github") */
	mcpProvider?: string | null;
}

/** A workflow step enriched with live execution status */
export type ProgressNodeStatus =
	| "idle"
	| "pending"
	| "running"
	| "completed"
	| "failed"
	| "stopped"
	| "skipped";

export interface ProgressNode extends WorkflowStep {
	status: ProgressNodeStatus;
	durationSeconds?: number;
	activeBranch?: string;
	forEachProgress?: { completed: number; total: number; failed: number };
}

/**
 * BFS topological sort from the START node, producing a linear execution order.
 *
 * - Follows edges from source -> target
 * - Visited set prevents infinite loops from cycles (review loops, etc.)
 * - For CONDITION nodes, records branch info (edge labels)
 * - Disconnected nodes (unreachable from START) are excluded
 */
export function topologicalSort(graph: GraphShape): WorkflowStep[] {
	// Resolve node ID — API uses uniq_id, some contexts use id
	const getNodeId = (node: ApiNode) => node.uniq_id || node.id || "";

	const nodeMap = new Map<string, ApiNode>();
	for (const node of graph.nodes) {
		nodeMap.set(getNodeId(node), node);
	}

	// Build tool connection lookup from edges/connections (target → source parent)
	const rawConns: GraphConnection[] =
		graph.edges || graph.connections || [];
	const toolTargets = new Map<string, string>();
	for (const conn of rawConns) {
		if (conn.connection_type === "tool") {
			const source = conn.source || conn.source_id;
			const target = conn.target || conn.target_id;
			if (source && target) {
				toolTargets.set(target, source);
			}
		}
	}

	// Build adjacency from node.nexts (preferred) or connections/edges
	const adjacency = new Map<string, { target: string; label?: string }[]>();

	const hasNexts = graph.nodes.some((n) => n.nexts && n.nexts.length > 0);

	if (hasNexts) {
		// Use the built-in nexts arrays on each node, excluding tool targets
		for (const node of graph.nodes) {
			const nodeId = getNodeId(node);
			if (node.nexts && node.nexts.length > 0) {
				adjacency.set(
					nodeId,
					node.nexts
						.filter((targetId) => !toolTargets.has(targetId))
						.map((targetId) => ({ target: targetId })),
				);
			}
		}
	} else {
		// Fall back to connections/edges
		const rawEdges: GraphConnection[] =
			graph.edges || graph.connections || [];
		for (const edge of rawEdges) {
			const source = edge.source || edge.source_id;
			const target = edge.target || edge.target_id;
			if (!source || !target) continue;
			if (edge.connection_type === "tool") continue;

			if (!adjacency.has(source)) {
				adjacency.set(source, []);
			}
			adjacency.get(source)!.push({
				target,
				label: edge.label || edge.data?.label || edge.data?.branch_label,
			});
		}
	}

	// Also build a connection label lookup for condition branches
	const connectionLabels = new Map<string, string>();
	for (const conn of rawConns) {
		const source = conn.source || conn.source_id;
		const target = conn.target || conn.target_id;
		const label = conn.label || conn.data?.label || conn.data?.branch_label;
		if (source && target && label) {
			connectionLabels.set(`${source}->${target}`, label);
		}
	}

	// Helper to detect MCP provider for a node
	const getMcpProvider = (node: ApiNode): string | null => {
		if (node.type.toUpperCase() !== "MCP_SERVER") return null;
		return (
			node.mcp_server_config?.provider ||
			detectProviderFromNodeName(node.name) ||
			null
		);
	};

	// Find START node
	const startNode = graph.nodes.find((n) => n.type === "START");
	if (!startNode) return [];

	const startId = getNodeId(startNode);
	const result: WorkflowStep[] = [];
	const visited = new Set<string>();
	const queue: string[] = [startId];
	let order = 0;

	while (queue.length > 0) {
		const nodeId = queue.shift()!;
		if (visited.has(nodeId)) continue;
		visited.add(nodeId);

		const node = nodeMap.get(nodeId);
		if (!node) continue;

		const targets = adjacency.get(nodeId) || [];

		// For CONDITION nodes, record branch labels
		const isCondition =
			node.type === "CONDITION" || node.type === "CONDITIONAL";
		const branches = isCondition
			? targets.map((t) => ({
					label:
						t.label ||
						connectionLabels.get(`${nodeId}->${t.target}`) ||
						"Branch",
					targetNodeId: t.target,
				}))
			: undefined;

		result.push({
			nodeId: getNodeId(node),
			nodeName: node.name,
			nodeType: node.type.toUpperCase(),
			order: order++,
			branches,
			mcpProvider: getMcpProvider(node),
		});

		for (const t of targets) {
			if (!visited.has(t.target)) {
				queue.push(t.target);
			}
		}
	}

	// Inject tool nodes after their parent agents
	const toolSteps: WorkflowStep[] = [];
	for (const [targetId, sourceId] of toolTargets) {
		const toolNode = nodeMap.get(targetId);
		if (!toolNode) continue;

		toolSteps.push({
			nodeId: getNodeId(toolNode),
			nodeName: toolNode.name,
			nodeType: toolNode.type.toUpperCase(),
			order: -1,
			isTool: true,
			parentNodeId: sourceId,
			mcpProvider: getMcpProvider(toolNode),
		});
	}

	// Insert tool nodes right after their parent in the result
	const finalResult: WorkflowStep[] = [];
	for (const step of result) {
		finalResult.push(step);
		const children = toolSteps.filter((t) => t.parentNodeId === step.nodeId);
		for (const child of children) {
			finalResult.push(child);
		}
	}

	// Re-number orders
	finalResult.forEach((s, i) => {
		s.order = i;
	});

	return finalResult;
}

/**
 * Map an execution status string (from WebSocket/DB) to a ProgressNodeStatus.
 */
export function mapExecutionStatus(status: string): ProgressNodeStatus {
	switch (status) {
		case "running":
			return "running";
		case "completed":
			return "completed";
		case "failed":
			return "failed";
		case "stopped":
		case "stopping":
		case "stop_requested":
		case "cancelled":
			return "stopped";
		case "paused":
		case "pause_pending":
		case "pending":
			return "pending";
		case "skipped":
			return "skipped";
		default:
			return "idle";
	}
}
