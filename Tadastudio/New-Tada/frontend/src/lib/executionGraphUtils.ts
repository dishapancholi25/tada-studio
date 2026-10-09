import type { Edge, Node } from "reactflow";
import type { GraphExecution, NodeExecution } from "@/types/api";
import { getConditionPathEdgeStyle } from "./conditionPathStyling";

/**
 * Convert an execution with its graph definition to React Flow format
 */
export function convertExecutionToReactFlow(execution: GraphExecution): {
	nodes: Node[];
	edges: Edge[];
} {
	const { graph_definition, node_executions } = execution;

	// Type guard to ensure graph_definition has the required structure
	if (!graph_definition || typeof graph_definition !== "object") {
		// console.error('Invalid graph_definition structure');
		return { nodes: [], edges: [] };
	}

	const graphDef = graph_definition as any;

	// Create a map of node executions by node_id for quick lookup
	const nodeExecutionMap = new Map<string, NodeExecution>();
	(node_executions ?? []).forEach((ne) => {
		nodeExecutionMap.set(ne.node_id, ne);
	});

	// Helper function to get the correct node type for React Flow
	const getNodeType = (node: any): string => {
		const nodeType = node.type?.toUpperCase();

		// Handle flow control nodes
		if (nodeType === "START" || nodeType === "END") {
			return "flowNode";
		}

		// Handle CHECKPOINT nodes
		if (nodeType === "CHECKPOINT") {
			return "flowNode"; // FlowNode handles checkpoint rendering
		}

		// Use shared ConditionNode for condition nodes
		if (nodeType === "CONDITION") {
			return "conditionNode";
		}

		// Handle specific node types directly (new format)
		switch (nodeType) {
			case "EMAIL_SEND":
				return "emailSendNode";
			case "EMAIL_SEND_TOOL":
				return "emailSendToolNode";
			case "FILE_READ":
				return "fileReadNode";
			case "FILE_WRITE":
				return "fileWriteNode";
			case "WEB_SEARCH":
				return "webSearchNode";
			case "DOCUMENT_SEARCH":
				return "documentSearchNode";
			case "DOCUMENT_RETRIEVE":
				return "documentRetrieveNode";
			case "DOCUMENT_LOAD":
				return "documentLoadNode";
			case "DATABASE_QUERY":
				return "databaseQueryNode";
			case "DATABASE_QUERY_ACTION":
				return "databaseQueryActionNode";
			case "DATABASE_INSERT":
				return "databaseInsertNode";
			case "HTTP_REQUEST":
				return "httpRequestNode";
			case "HTTP_REQUEST_ACTION":
				return "httpRequestActionNode";
			case "MCP_SERVER":
				return "mcpServerNode";
			case "TOOL": {
				// Handle old format with tool_config
				const toolType =
					node.tool_config?.tool_type ||
					node.data?.tool_config?.tool_type ||
					"";

				switch (toolType.toUpperCase()) {
					case "WEB_SEARCH":
						return "webSearchNode";
					case "DOCUMENT_SEARCH":
						return "documentSearchNode";
					case "DATABASE_QUERY":
						return "databaseQueryNode";
					case "DATABASE_INSERT":
						return "databaseInsertNode";
					case "DATABASE_QUERY_ACTION":
						return "databaseQueryActionNode";
					case "HTTP_REQUEST": {
						// Check if it's an action node
						const isAction =
							node.tool_config?.is_action || node.data?.tool_config?.is_action;
						return isAction ? "httpRequestActionNode" : "httpRequestNode";
					}
					case "MCP_SERVER":
						return "mcpServerNode";
					default:
						// Fallback to shared agent node for unknown tool types
						return "agentNode";
				}
			}
			case "AGENT":
				return "agentNode";
			default:
				// Default to shared agent node for unknown types
				return "agentNode";
		}
	};

	// Convert nodes (including TOOL nodes now with proper components)
	const nodes: Node[] = (graphDef.nodes || []).map((node: any) => {
		// Handle both 'id' and 'uniq_id' fields
		const nodeId = node.uniq_id || node.id;
		const nodeExecution = nodeExecutionMap.get(nodeId);
		const isSubAgent =
			node.is_sub_agent ||
			node.data?.is_sub_agent ||
			nodeExecution?.is_sub_agent ||
			false;

		// Extract config data based on node type
		const agentConfig = node.agent_config || node.data?.agent_config;
		const toolConfig = node.tool_config || node.data?.tool_config;
		const conditionConfig =
			node.condition_config || node.data?.condition_config;
		const checkpointConfig =
			node.checkpoint_config || node.data?.checkpoint_config;
		// Extract tool-specific configurations
		const databaseQueryConfig =
			node.database_query_config || node.data?.database_query_config;
		const databaseInsertConfig =
			node.database_insert_config || node.data?.database_insert_config;
		const databaseQueryActionConfig =
			node.database_query_action_config || node.data?.database_query_action_config;
		const httpRequestConfig =
			node.http_request_config || node.data?.http_request_config;
		const httpRequestActionConfig =
			node.http_request_action_config || node.data?.http_request_action_config;
		const webSearchConfig =
			node.web_search_config || node.data?.web_search_config;
		const documentSearchConfig =
			node.document_search_config || node.data?.document_search_config;
		const mcpServerConfig =
			node.mcp_server_config || node.data?.mcp_server_config;
		const emailSendConfig =
			node.email_send_config || node.data?.email_send_config;
		const fileReadConfig = node.file_read_config || node.data?.file_read_config;
		const prompt =
			agentConfig?.system_prompt ||
			node.prompt ||
			node.data?.prompt ||
			node.description ||
			"";

		// Get the appropriate node type
		const reactFlowNodeType = getNodeType(node);

		return {
			id: nodeId,
			type: reactFlowNodeType,
			position: node.position || { x: 0, y: 0 },
			data: {
				...node.data,
				id: nodeId,
				name: node.name,
				prompt: prompt,
				type: node.type,
				isSubAgent,
				agent_config: agentConfig,
				tool_config: toolConfig,
				condition_config: conditionConfig, // Include condition config
				checkpoint_config: checkpointConfig, // Include checkpoint config
				// Include tool-specific configurations
				database_query_config: databaseQueryConfig,
				database_insert_config: databaseInsertConfig,
				database_query_action_config: databaseQueryActionConfig,
				http_request_config: httpRequestConfig,
				http_request_action_config: httpRequestActionConfig,
				web_search_config: webSearchConfig,
				document_search_config: documentSearchConfig,
				mcp_server_config: mcpServerConfig,
				email_send_config: emailSendConfig, // Include email send config
				file_read_config: fileReadConfig, // Include file read config
				// Add execution-specific data
				executionStatus: nodeExecution?.status || "skipped",
				executionDuration: nodeExecution?.duration_seconds,
				isExecuting: false, // Never executing in history view
				nodeExecution, // Include full execution data for details
				isReadOnlyPreview: true, // Mark as read-only for execution viewer
				nexts: node.nexts, // Include nexts array from node data
				graphExecutionId: execution.id, // Add graph execution ID for memory queries
				// Add condition-specific execution data
				branchTaken: nodeExecution?.output_data?.branch_taken,
				branchLabel: nodeExecution?.output_data?.branch_label,
			},
		};
	});

	// Convert edges/connections
	const connections = graphDef.connections || graphDef.edges || [];
	const edges: Edge[] = connections.map((conn: any, index: number) => {
		// Handle both edge and connection formats
		const sourceId = conn.source_id || conn.source;
		const targetId = conn.target_id || conn.target;
		const connectionType = conn.connection_type || conn.data?.connection_type;

		// Determine source handle with backwards compatibility
		let sourceHandle = conn.source_handle || conn.sourceHandle;

		// Extract branch label for condition edges
		let branchLabel = null;
		const sourceNode = (graphDef.nodes || []).find(
			(n: any) => (n.uniq_id || n.id) === sourceId,
		);
		if (sourceNode?.type?.toUpperCase() === "CONDITION" && sourceHandle) {
			const conditionConfig =
				sourceNode.condition_config || sourceNode.data?.condition_config;
			if (conditionConfig?.branches) {
				// Find matching branch by handle_id
				const branch = conditionConfig.branches.find(
					(b: any) => b.handle_id === sourceHandle,
				);
				if (branch) {
					branchLabel = branch.label;
				} else {
					// Fallback to branch_labels array for older format
					const handleIndex = sourceHandle.match(/branch-(\d+)/)?.[1];
					if (handleIndex && conditionConfig.branch_labels) {
						branchLabel = conditionConfig.branch_labels[parseInt(handleIndex)];
					}
				}
			}
		}

		// Get source and target nodes for handle determination
		const sourceNodeFlow = nodes.find((n) => n.id === sourceId);
		const targetNode = nodes.find((n) => n.id === targetId);
		const isSourceSubAgent =
			sourceNodeFlow?.data?.isSubAgent || sourceNodeFlow?.data?.is_sub_agent;

		// If no source handle specified, infer from connection type and target node
		if (!sourceHandle) {
			if (connectionType === "delegation") {
				sourceHandle = "delegation";
			} else {
				// Check if target is a tool node (for backwards compatibility)
				if (
					targetNode &&
					[
						"webSearchNode",
						"documentSearchNode",
						"documentRetrieveNode",

						"databaseQueryNode",
						"databaseInsertNode",
						"httpRequestNode",
						"httpRequestActionNode",
						"mcpServerNode",
					].includes(targetNode.type || "")
				) {
					sourceHandle = "tools";
				}
			}
		}

		// Handle old connections that might have incorrect handles
		if (sourceHandle === "default" || sourceHandle === "source") {
			// Check if this is a tool or delegation connection based on target
			if (targetNode?.data?.isSubAgent || targetNode?.data?.is_sub_agent) {
				sourceHandle = "delegation";
			} else if (
				targetNode &&
				[
					"webSearchNode",
					"documentSearchNode",
					"documentRetrieveNode",
					"databaseQueryNode",
					"databaseInsertNode",
					"databaseQueryActionNode",
					"httpRequestNode",
					"httpRequestActionNode",
					"mcpServerNode",
				].includes(targetNode.type || "")
			) {
				sourceHandle = "tools";
			}
		}

		// CRITICAL FIX: Sub-agents have a single "tools" handle at the bottom (centered)
		// If the source is a sub-agent and handle is "delegation", change it to "tools"
		if (isSourceSubAgent && sourceHandle === "delegation") {
			// Sub-agents only have a "tools" handle, not a "delegation" handle
			sourceHandle = "tools";
		}

		const targetHandle =
			connectionType === "delegation"
				? "top"
				: conn.target_handle || conn.targetHandle;

		let edgeStyle;
		const sourceNodeExecution = nodeExecutionMap.get(sourceId);

		const conditionStyle = getConditionPathEdgeStyle({
			conditionNode: sourceNode,
			execution: sourceNodeExecution,
			sourceHandle: sourceHandle ?? null,
		});

		if (conditionStyle) {
			edgeStyle = { ...conditionStyle };
		}

		// Handle delegation connections (keep existing logic)
		if (connectionType === "delegation") {
			edgeStyle = {
				strokeDasharray: "5 5",
				stroke: "#3b82f6",
				strokeWidth: 1.5,
				opacity: 0.6,
			};
		}

		// Determine edge type based on source node
		let edgeType = "default";
		if (sourceNode?.type?.toUpperCase() === "CONDITION") {
			edgeType = "condition";
		}

		return {
			id: conn.id || `edge-${sourceId}-${targetId}-${index}`,
			source: sourceId,
			target: targetId,
			type: edgeType,
			sourceHandle,
			targetHandle,
			style: edgeStyle,
			label: branchLabel,
			data: {
				branchLabel,
				isExecutionMode: true,
			},
		};
	});

	return { nodes, edges };
}

/**
 * Format execution duration for display
 */
export function formatExecutionDuration(seconds?: number | null): string {
	if (!seconds) return "";

	if (seconds < 1) {
		return `${(seconds * 1000).toFixed(0)}ms`;
	} else if (seconds < 60) {
		return `${seconds.toFixed(1)}s`;
	} else {
		const minutes = Math.floor(seconds / 60);
		const remainingSeconds = seconds % 60;
		return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
	}
}

/**
 * Get execution statistics from node executions
 */
export function getExecutionStats(nodeExecutions: NodeExecution[]) {
	const totalNodes = nodeExecutions.length;
	const completedNodes = nodeExecutions.filter(
		(ne) => ne.status === "completed",
	).length;
	const failedNodes = nodeExecutions.filter(
		(ne) => ne.status === "failed",
	).length;
	const skippedNodes = 0; // 'skipped' status not in ExecutionStatusType

	const totalDuration = nodeExecutions.reduce((sum, ne) => {
		return sum + (ne.duration_seconds || 0);
	}, 0);

	const longestNode = nodeExecutions.reduce(
		(longest, ne) => {
			if (
				!longest ||
				(ne.duration_seconds || 0) > (longest.duration_seconds || 0)
			) {
				return ne;
			}
			return longest;
		},
		null as NodeExecution | null,
	);

	return {
		totalNodes,
		completedNodes,
		failedNodes,
		skippedNodes,
		totalDuration,
		longestNode,
		successRate: totalNodes > 0 ? (completedNodes / totalNodes) * 100 : 0,
	};
}
