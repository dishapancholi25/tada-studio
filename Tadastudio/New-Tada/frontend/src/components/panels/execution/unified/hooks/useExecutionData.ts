import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { NodeExecution, NodeType } from "@/types/api";
import type {
	CombinedNodeExecution,
	ExecutionDataOptions,
	ExecutionDataResult,
	ToolExecution,
	ToolType,
} from "../types/execution.types";
import { parseToolExecutions } from "../utils/executionParser";

// Node type mapping
const NODE_TYPE_MAP: Record<ToolType, NodeType> = {
	database_query: "DATABASE_QUERY",
	document_search: "DOCUMENT_SEARCH",
	document_retrieve: "DOCUMENT_RETRIEVE",
	email_send: "EMAIL_SEND_TOOL",
	file_write: "FILE_WRITE",
	http_request: "HTTP_REQUEST",
	web_search: "WEB_SEARCH",
	mcp_server: "MCP_SERVER",
};

/**
 * Creates an empty placeholder node for when no execution data is found
 */
function createEmptyNode(
	nodeId: string,
	nodeName: string,
	toolType: ToolType,
): CombinedNodeExecution {
	console.log("[useExecutionData] No tool executions found");
	return {
		id: `empty-${nodeId}`,
		node_id: nodeId,
		node_name: nodeName,
		node_type: NODE_TYPE_MAP[toolType],
		execution_order: 1,
		status: "pending",
		output_data: {},
		start_time: null,
		end_time: null,
		duration_seconds: null,
		input_data: null,
		error_message: null,
		node_metadata: null,
		is_sub_agent: false,
		input_tokens: null,
		output_tokens: null,
		total_tokens: null,
		token_metadata: null,
		created_at: null,
	};
}

/**
 * Creates a synthetic node from tool executions found in agent nodes
 */
function createSyntheticNode(
	nodeId: string,
	nodeName: string,
	toolType: ToolType,
	toolExecs: unknown,
	agentNodeData?: Record<string, unknown>,
): CombinedNodeExecution {
	return {
		id: `synthetic-${nodeId}`,
		node_id: nodeId,
		node_name: nodeName,
		node_type: NODE_TYPE_MAP[toolType],
		execution_order: 1,
		status: "completed",
		output_data: {
			tool_executions: toolExecs,
			[`${toolType}_config`]: agentNodeData?.[`${toolType}_config`],
		},
		start_time: null,
		end_time: null,
		duration_seconds: null,
		input_data: null,
		error_message: null,
		node_metadata: null,
		is_sub_agent: false,
		input_tokens: null,
		output_tokens: null,
		total_tokens: null,
		token_metadata: null,
		created_at: null,
	};
}

/**
 * Creates a combined node that includes all related tool executions
 */
function createCombinedNode(
	baseNode: NodeExecution,
	allToolNodes: NodeExecution[],
	toolType: ToolType,
	nodeName: string,
): CombinedNodeExecution {
	return {
		...baseNode,
		id: `combined-${toolType}`,
		node_name: nodeName || baseNode.node_name,
		all_tool_nodes: allToolNodes,
	};
}

/**
 * Searches agent nodes for embedded tool executions
 */
function findToolExecutionsInAgents(
	nodeExecutions: NodeExecution[],
	nodeId: string,
	nodeName: string,
	toolType: ToolType,
): { node: CombinedNodeExecution; executions: ToolExecution[] } | null {
	console.log("[useExecutionData] Looking for tool executions in agent nodes");

	const agentExecutions = nodeExecutions.filter(
		(ne: NodeExecution) => ne.node_type === "AGENT",
	);

	for (const agentExec of agentExecutions) {
		const toolExecs = agentExec.output_data?.tool_executions;
		if (toolExecs) {
			const syntheticNode = createSyntheticNode(
				nodeId,
				nodeName,
				toolType,
				toolExecs,
				agentExec.input_data ?? undefined,
			);
			const executions = parseToolExecutions(syntheticNode, toolType);

			if (executions.length > 0) {
				console.log(
					`[useExecutionData] Found ${executions.length} tool executions in agent node`,
				);
				return { node: syntheticNode, executions };
			}
		}
	}

	return null;
}

/**
 * Finds MCP tool executions using the parent agent's node ID.
 * MCP_SERVER nodes don't get their own execution records — tool calls are stored
 * as TOOL-type records under the parent agent's node_id. This function uses graph
 * connection info to find the correct agent and its tool records.
 */
function findMcpToolExecutionsForAgent(
	nodeExecutions: NodeExecution[],
	mcpNodeId: string,
	nodeName: string,
	parentAgentNodeId: string,
): { node: CombinedNodeExecution; executions: ToolExecution[] } | null {
	console.log(
		`[useExecutionData] Finding MCP tool executions for agent ${parentAgentNodeId}`,
	);

	// Strategy 1: Find TOOL records with node_id matching the MCP node
	// (properly mapped tools where tool_node_mapping points to the MCP node)
	const directMcpRecords = nodeExecutions.filter(
		(ne: NodeExecution) =>
			ne.node_id === mcpNodeId &&
			(ne.node_type === "TOOL" || ne.node_type === "MCP_SERVER"),
	);

	if (directMcpRecords.length > 0) {
		console.log(
			`[useExecutionData] Found ${directMcpRecords.length} TOOL records directly for MCP node ${mcpNodeId}`,
		);
		const executions: ToolExecution[] = [];
		for (const record of directMcpRecords) {
			const parsed = parseToolExecutions(record, "mcp_server");
			executions.push(...parsed);
		}
		if (executions.length > 0) {
			const syntheticNode = createEmptyNode(mcpNodeId, nodeName, "mcp_server");
			syntheticNode.status = "completed";
			return { node: syntheticNode, executions };
		}
	}

	// Strategy 2: Find TOOL records with node_id matching the parent agent
	const agentToolRecords = nodeExecutions.filter(
		(ne: NodeExecution) =>
			ne.node_id === parentAgentNodeId &&
			(ne.node_type === "TOOL" || ne.node_type === "MCP_SERVER"),
	);

	if (agentToolRecords.length > 0) {
		console.log(
			`[useExecutionData] Found ${agentToolRecords.length} TOOL records under parent agent ${parentAgentNodeId}`,
		);
		const executions: ToolExecution[] = [];
		for (const record of agentToolRecords) {
			const parsed = parseToolExecutions(record, "mcp_server");
			executions.push(...parsed);
		}
		if (executions.length > 0) {
			const syntheticNode = createEmptyNode(mcpNodeId, nodeName, "mcp_server");
			syntheticNode.status = "completed";
			return { node: syntheticNode, executions };
		}
	}

	// Strategy 3: Check parent agent's output_data.tool_executions
	const agentExecution = nodeExecutions.find(
		(ne: NodeExecution) =>
			ne.node_type === "AGENT" && ne.node_id === parentAgentNodeId,
	);

	if (agentExecution?.output_data?.tool_executions) {
		console.log(
			`[useExecutionData] Found tool_executions in parent agent ${parentAgentNodeId} output_data`,
		);
		const toolExecs = agentExecution.output_data.tool_executions;
		// Parse each tool execution individually as MCP tool calls
		const executions: ToolExecution[] = [];
		const toolExecsArray = Array.isArray(toolExecs) ? toolExecs : [];
		for (const exec of toolExecsArray) {
			// Create a synthetic TOOL-like node for each tool execution
			const singleNode: NodeExecution = {
				id: exec.call_id || exec.id || `mcp-${Date.now()}`,
				node_id: mcpNodeId,
				node_name: exec.tool || "mcp_tool",
				node_type: "TOOL",
				execution_order: 1,
				status: "completed",
				output_data: { result: exec.result || exec.results || exec.output },
				start_time: null,
				end_time: null,
				duration_seconds: null,
				input_data: exec.args || exec.input || null,
				error_message: null,
				node_metadata: { synthetic_tool_name: exec.tool },
				is_sub_agent: false,
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: exec.timestamp
					? new Date(exec.timestamp * 1000).toISOString()
					: null,
			};
			const parsed = parseToolExecutions(singleNode, "mcp_server");
			executions.push(...parsed);
		}

		if (executions.length > 0) {
			const syntheticNode = createEmptyNode(mcpNodeId, nodeName, "mcp_server");
			syntheticNode.status = "completed";
			return { node: syntheticNode, executions };
		}
	}

	console.log(
		`[useExecutionData] No MCP tool executions found for agent ${parentAgentNodeId}`,
	);
	return null;
}

/**
 * Finds all tool nodes of a specific type in execution history
 */
function findToolNodesInHistory(
	nodeExecutions: NodeExecution[],
	nodeId: string,
	expectedNodeType: NodeType,
): NodeExecution[] {
	const allToolNodes = nodeExecutions.filter(
		(ne: NodeExecution) =>
			ne.node_type === expectedNodeType && ne.node_id === nodeId,
	);

	console.log(
		`[useExecutionData] Found ${allToolNodes.length} ${expectedNodeType} nodes`,
	);
	console.log(
		`[useExecutionData] Tool nodes with review_iteration:`,
		allToolNodes.map((n: NodeExecution) => ({
			id: n.node_id,
			name: n.node_name,
			type: n.node_type,
			review_iteration: n.review_iteration,
		})),
	);

	return allToolNodes;
}

/**
 * Finds a specific tool node in execution history, including synthetic tool IDs
 */
function findToolNodeInHistory(
	nodeExecutions: NodeExecution[],
	nodeId: string,
	expectedNodeType: NodeType,
): NodeExecution | null {
	// First check if there's a tool node with our ID
	let toolNode = nodeExecutions.find(
		(ne: NodeExecution) =>
			ne.node_id === nodeId && ne.node_type === expectedNodeType,
	);

	// If not found, try to find synthetic tool IDs (for sub-agent executions)
	if (!toolNode && nodeId.includes("tool_")) {
		console.log("[useExecutionData] Looking for synthetic tool ID");
		toolNode = nodeExecutions.find(
			(ne: NodeExecution) => ne.node_id === nodeId && ne.node_type === "TOOL",
		);
	}

	return toolNode || null;
}

/**
 * Fetches all related tool executions from execution history
 */
async function fetchAllToolNodes(
	executionId: string,
	nodeId: string,
	expectedNodeType: NodeType,
): Promise<NodeExecution[]> {
	const executionData = await api.getExecutionHistory(executionId);
	console.log(
		`[useExecutionData] Fetching all executions from history for type: ${expectedNodeType}`,
	);
	console.log(
		`[useExecutionData] Total node_executions in history:`,
		executionData.node_executions?.length || 0,
	);
	console.log(
		`[useExecutionData] Node types in history:`,
		executionData.node_executions?.map((ne: NodeExecution) => ne.node_type) ||
			[],
	);

	return findToolNodesInHistory(
		executionData.node_executions || [],
		nodeId,
		expectedNodeType,
	);
}

/**
 * Processes a tool node and fetches all related executions
 */
async function processToolNodeWithRelated(
	toolNode: NodeExecution,
	executionId: string,
	nodeId: string,
	nodeName: string,
	toolType: ToolType,
	expectedNodeType: NodeType,
): Promise<{ node: CombinedNodeExecution; executions: ToolExecution[] }> {
	try {
		const allToolNodes = await fetchAllToolNodes(
			executionId,
			nodeId,
			expectedNodeType,
		);

		if (allToolNodes.length > 0) {
			const combinedNode = createCombinedNode(
				toolNode,
				allToolNodes,
				toolType,
				nodeName,
			);
			const executions = parseToolExecutions(combinedNode, toolType);
			return { node: combinedNode, executions };
		} else {
			console.log(
				"[DEBUG DB_QUERY Hook] No related nodes found, using single node",
			);
			const executions = parseToolExecutions(toolNode, toolType);
			console.log(
				"[DEBUG DB_QUERY Hook] Parsed executions:",
				executions.length,
			);
			return { node: toolNode, executions };
		}
	} catch (historyError) {
		console.warn(
			"[DEBUG DB_QUERY Hook] Failed to fetch related executions, using single node",
			historyError,
		);
		const executions = parseToolExecutions(toolNode, toolType);
		console.log(
			"[DEBUG DB_QUERY Hook] Parsed executions (fallback):",
			executions.length,
		);
		return { node: toolNode, executions };
	}
}

/**
 * Attempts to fetch node execution data directly from the API
 */
async function fetchNodeDirectly(
	executionId: string,
	nodeId: string,
	nodeName: string,
	toolType: ToolType,
	expectedNodeType: NodeType,
): Promise<{
	node: CombinedNodeExecution;
	executions: ToolExecution[];
} | null> {
	try {
		const initialData = await api.getNodeExecution(executionId, nodeId);
		console.log(
			`[DEBUG DB_QUERY Hook] Direct fetch successful for node ${nodeId}`,
		);
		console.log("[DEBUG DB_QUERY Hook] Initial data:", {
			nodeType: initialData.node_type,
			hasInputData: !!initialData.input_data,
			hasOutputData: !!initialData.output_data,
			hasParentAgent: !!initialData.node_metadata?.parent_agent_id,
		});

		// Check if this is a tool node of the expected type
		if (initialData.node_type === expectedNodeType) {
			console.log(
				`[useExecutionData] Found ${toolType} node, fetching all executions of this type`,
			);
			return await processToolNodeWithRelated(
				initialData,
				executionId,
				nodeId,
				nodeName,
				toolType,
				expectedNodeType,
			);
		} else {
			// Not a tool node of expected type, use single node
			console.log(
				"[DEBUG DB_QUERY Hook] Not the expected tool type, using single node",
			);
			const executions = parseToolExecutions(initialData, toolType);
			console.log(
				"[DEBUG DB_QUERY Hook] Parsed executions (single):",
				executions.length,
			);
			return { node: initialData, executions };
		}
	} catch (error) {
		console.log(
			"[useExecutionData] Direct fetch failed, will try fallback approach",
			error,
		);
		return null;
	}
}

/**
 * Fetches execution data from history when direct fetch fails
 */
async function fetchFromHistory(
	executionId: string,
	nodeId: string,
	nodeName: string,
	toolType: ToolType,
	expectedNodeType: NodeType,
	parentAgentNodeId?: string,
): Promise<{
	node: CombinedNodeExecution;
	executions: ToolExecution[];
} | null> {
	console.log("[useExecutionData] Trying fallback approach");

	const executionData = await api.getExecutionHistory(executionId);
	const nodeExecutions = executionData.node_executions || [];

	// Try to find the tool node in history
	const toolNode = findToolNodeInHistory(
		nodeExecutions,
		nodeId,
		expectedNodeType,
	);

	if (toolNode) {
		console.log(
			`[useExecutionData] Found ${toolType} node in execution history`,
		);
		console.log(
			`[useExecutionData] Fallback: Looking for all ${expectedNodeType} nodes`,
		);
		console.log(
			`[useExecutionData] Total nodes in execution:`,
			nodeExecutions.length,
		);
		console.log(
			`[useExecutionData] Node types:`,
			nodeExecutions.map((ne: NodeExecution) => ne.node_type),
		);

		const allToolNodes = findToolNodesInHistory(
			nodeExecutions,
			nodeId,
			expectedNodeType,
		);

		if (allToolNodes.length > 0) {
			console.log(
				`[useExecutionData] Creating combined node with ${allToolNodes.length} ${toolType} executions`,
			);
			const combinedNode = createCombinedNode(
				toolNode,
				allToolNodes,
				toolType,
				nodeName,
			);
			const executions = parseToolExecutions(combinedNode, toolType);
			return { node: combinedNode, executions };
		} else {
			const executions = parseToolExecutions(toolNode, toolType);
			return { node: toolNode, executions };
		}
	}

	// For MCP nodes with a known parent agent, use targeted resolution
	if (toolType === "mcp_server" && parentAgentNodeId) {
		const mcpResult = findMcpToolExecutionsForAgent(
			nodeExecutions,
			nodeId,
			nodeName,
			parentAgentNodeId,
		);
		if (mcpResult) {
			return mcpResult;
		}
	}

	// Look in agent nodes for tool executions (generic fallback)
	const agentResult = findToolExecutionsInAgents(
		nodeExecutions,
		nodeId,
		nodeName,
		toolType,
	);
	if (agentResult) {
		return agentResult;
	}

	return null;
}

/**
 * Enhanced hook for fetching execution data with dual ID support
 * Handles both WebSocket execution IDs and Database UUIDs
 */
export function useExecutionData({
	executionId,
	nodeId,
	nodeName,
	toolType,
	nodeExecution: preloadedData,
	parentAgentNodeId,
	isExecuting,
}: ExecutionDataOptions): ExecutionDataResult {
	const [nodeExecution, setNodeExecution] =
		useState<CombinedNodeExecution | null>(preloadedData || null);
	const [toolExecutions, setToolExecutions] = useState<ToolExecution[]>([]);
	const [loading, setLoading] = useState(!preloadedData);
	const [error, setError] = useState<string | null>(null);
	const foundDataRef = useRef(!!preloadedData);

	// Handle preloaded (streaming) data — update state whenever it changes
	useEffect(() => {
		if (!preloadedData) return;
		console.log("[DEBUG DB_QUERY Hook] Using preloaded data");
		setNodeExecution(preloadedData);

		// Only parse completed entries — "running" entries have no output_data
		// and would produce partial/empty results that hide the spinner
		const combinedNode = preloadedData as CombinedNodeExecution;
		const dataToParse = combinedNode.all_tool_nodes
			? (() => {
					const completed = combinedNode.all_tool_nodes.filter(
						(n: any) => n.status !== "running",
					);
					if (completed.length === 0) return null;
					return {
						...preloadedData,
						all_tool_nodes: completed,
					} as CombinedNodeExecution;
				})()
			: (preloadedData as any).status === "running"
				? null // Single running entry — don't parse
				: preloadedData;

		const executions = dataToParse
			? parseToolExecutions(dataToParse, toolType)
			: [];
		console.log(
			"[DEBUG DB_QUERY Hook] Parsed executions from preloaded:",
			executions.length,
		);
		setToolExecutions(executions);
		setLoading(false);
		foundDataRef.current = true;
	}, [preloadedData, toolType]);

	// Fetch from API with polling fallback when workflow is executing
	useEffect(() => {
		// During execution with streaming data: skip (streaming handles it)
		if (isExecuting && preloadedData) return;
		// No execution ID: skip
		if (!executionId) return;

		console.log("[DEBUG DB_QUERY Hook] useExecutionData effect triggered:", {
			executionId,
			nodeId,
			nodeName,
			toolType,
			isExecuting,
		});

		let cancelled = false;
		let pollTimer: ReturnType<typeof setTimeout> | null = null;

		const doFetch = async (isRetry = false) => {
			if (cancelled) return;
			if (!isRetry) {
				setLoading(true);
				setError(null);
			}

			try {
				console.log(
					`[useExecutionData] Fetching execution data for ${toolType} node ${nodeId}`,
				);
				console.log(
					`[useExecutionData] Execution ID: ${executionId} (type: ${executionId.startsWith("exec_") ? "WebSocket" : "UUID"})`,
				);

				const expectedNodeType = NODE_TYPE_MAP[toolType];
				console.log(`[DEBUG EMAIL_SEND useExecutionData] expectedNodeType=${expectedNodeType}, toolType=${toolType}`);

				// Try direct fetch first
				const directResult = await fetchNodeDirectly(
					executionId,
					nodeId,
					nodeName,
					toolType,
					expectedNodeType,
				);
				console.log(`[DEBUG EMAIL_SEND useExecutionData] directResult:`, directResult ? {
					nodeType: directResult.node.node_type,
					nodeId: directResult.node.node_id,
					executionsCount: directResult.executions.length,
				} : null);
				if (!cancelled && directResult) {
					setNodeExecution(directResult.node);
					setToolExecutions(directResult.executions);
					setLoading(false);
					foundDataRef.current = true;
					return;
				}

				// Fallback: fetch from execution history
				const historyResult = await fetchFromHistory(
					executionId,
					nodeId,
					nodeName,
					toolType,
					expectedNodeType,
					parentAgentNodeId,
				);
				console.log(`[DEBUG EMAIL_SEND useExecutionData] historyResult:`, historyResult ? {
					nodeType: historyResult.node.node_type,
					executionsCount: historyResult.executions.length,
				} : null);
				if (!cancelled && historyResult) {
					setNodeExecution(historyResult.node);
					setToolExecutions(historyResult.executions);
					setLoading(false);
					foundDataRef.current = true;
					return;
				}

				if (cancelled) return;

				// No data found
				if (isExecuting) {
					// Workflow still running — poll for data every 3 seconds
					console.log(
						"[useExecutionData] No data yet, will retry in 3s (workflow executing)",
					);
					setLoading(false);
					pollTimer = setTimeout(() => doFetch(true), 3000);
				} else {
					// Workflow not running — show empty state
					const emptyNode = createEmptyNode(nodeId, nodeName, toolType);
					setNodeExecution(emptyNode);
					setToolExecutions([]);
					setLoading(false);
				}
			} catch (err) {
				if (!cancelled) {
					console.error("[useExecutionData] Error fetching execution data:", err);
					setError(
						err instanceof Error ? err.message : "Failed to fetch execution data",
					);
					setLoading(false);
				}
			}
		};

		doFetch().catch((error) => {
			console.error("Failed to fetch execution data:", error);
		});

		return () => {
			cancelled = true;
			if (pollTimer) clearTimeout(pollTimer);
		};
	}, [executionId, nodeId, nodeName, toolType, preloadedData, parentAgentNodeId, isExecuting]);

	return {
		nodeExecution,
		toolExecutions,
		loading,
		error,
	};
}
