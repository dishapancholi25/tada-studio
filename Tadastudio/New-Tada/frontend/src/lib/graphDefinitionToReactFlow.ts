"use client";

import type { Edge, Node } from "reactflow";
import { builderEdgeStroke } from "@/components/core/shared/defaultEdgeOptions";
import {
	isConditionNode,
	resolveConditionEdgeData,
} from "@/lib/conditionEdgeHelpers";

interface GraphLikeDefinition {
	nodes?: any[];
	edges?: any[];
	connections?: any[];
	[key: string]: any;
}

interface ConvertResult {
	nodes: Node[];
	edges: Edge[];
}

function normalizeNodes(rawNodes: any[] = []): {
	nodes: Node[];
	lookup: Map<string, any>;
} {
	const nodeLookup = new Map<string, any>();

	const nodes: Node[] = rawNodes
		.filter((node) => (node.type?.toUpperCase() || "") !== "TOOL")
		.map((node, index) => {
			const nodeId = node.uniq_id || node.id || `node-${index}`;

			nodeLookup.set(nodeId, node);

			let position = { x: 100 + index * 150, y: 100 };
			if (node.position && typeof node.position === "object") {
				const { x, y } = node.position;
				if (typeof x === "number" && typeof y === "number") {
					position = { x, y };
				}
			}

			const upperType = (node.type || "").toUpperCase();
			let reactFlowType = "agentNode";

			switch (upperType) {
				case "START":
				case "END":
				case "CHECKPOINT":
					reactFlowType = "flowNode";
					break;
				case "CONDITION":
					reactFlowType = "conditionNode";
					break;
				case "SUBWORKFLOW":
					reactFlowType = "subWorkflowNode";
					break;
				case "DOCUMENT_SEARCH":
					reactFlowType = "documentSearchNode";
					break;
				case "DOCUMENT_RETRIEVE":
					reactFlowType = "documentRetrieveNode";
					break;
				case "DOCUMENT_LOAD":
					reactFlowType = "documentLoadNode";
					break;
				case "DATABASE_QUERY":
					reactFlowType = "databaseQueryNode";
					break;
				case "DATABASE_QUERY_ACTION":
					reactFlowType = "databaseQueryActionNode";
					break;
				case "DATABASE_INSERT":
					reactFlowType = "databaseInsertNode";
					break;
				case "HTTP_REQUEST":
					reactFlowType = "httpRequestNode";
					break;
				case "HTTP_REQUEST_ACTION":
					reactFlowType = "httpRequestActionNode";
					break;
				case "WEB_SEARCH":
					reactFlowType = "webSearchNode";
					break;
				case "MCP_SERVER":
					reactFlowType = "mcpServerNode";
					break;
				case "EMAIL_SEND":
					reactFlowType = "emailSendNode";
					break;
				case "EMAIL_SEND_TOOL":
					reactFlowType = "emailSendToolNode";
					break;
				case "FILE_READ":
					reactFlowType = "fileReadNode";
					break;
				case "FILE_WRITE":
					reactFlowType = "fileWriteNode";
					break;
				case "FOR_EACH":
					reactFlowType = "forEachNode";
					break;
				case "CODE_EXECUTOR":
					reactFlowType = "codeExecutorNode";
					break;
				default:
					break;
			}

			const nodeData: Record<string, any> = {
				id: nodeId,
				name: node.name || "Unnamed Node",
				prompt: node.agent_config?.system_prompt || node.description || "",
				type: node.type || "agent",
				...node,
				isOrchestrator: node.agent_config?.is_orchestrator || false,
			};
			// Deduplicate document_collections to prevent stale duplicate entries
		if (nodeData.document_search_config?.document_collections) {
			nodeData.document_search_config = {
				...nodeData.document_search_config,
				document_collections: [
					...new Set(nodeData.document_search_config.document_collections),
				],
			};
		}

			if (upperType === "MCP_SERVER" && node.mcp_server_config) {
				nodeData.label = node.name || "MCP Server";
				nodeData.server_name =
					node.mcp_server_config.server_name || "MCP Server";
				nodeData.connection_type =
					node.mcp_server_config.connection_type || "stdio";
				nodeData.isConfigured = true;
			}

			return {
				id: nodeId,
				type: reactFlowType,
				position,
				data: nodeData,
			};
		});

	return { nodes, lookup: nodeLookup };
}

function resolveEdgeStyle(connection: any) {
	if (connection.connection_type === "delegation") {
		return {
			strokeDasharray: "5 5",
			stroke: builderEdgeStroke,
			strokeWidth: 1.5,
			opacity: 0.6,
		};
	}

	if (connection.connection_type === "tool") {
		return {
			stroke: builderEdgeStroke,
			strokeWidth: 2.5,
			opacity: 1,
			strokeDasharray: "4 2",
		};
	}

	return {
		stroke: builderEdgeStroke,
		strokeWidth: 3,
		opacity: 0.7,
	};
}

function normalizeConnections(graphData: GraphLikeDefinition): any[] {
	if (
		Array.isArray(graphData.connections) &&
		graphData.connections.length > 0
	) {
		return graphData.connections;
	}
	if (Array.isArray(graphData.edges)) {
		return graphData.edges;
	}
	return [];
}

export function convertGraphDefinitionToReactFlow(
	graphData: GraphLikeDefinition,
): ConvertResult {
	const rawNodes = Array.isArray(graphData.nodes) ? graphData.nodes : [];
	const toolNodeIds = new Set(
		rawNodes
			.filter((node) => (node.type?.toUpperCase() || "") === "TOOL")
			.map((node) => node.uniq_id || node.id),
	);

	const { nodes: flowNodes, lookup: nodeLookup } = normalizeNodes(rawNodes);
	const connections = normalizeConnections(graphData);

	if (typeof window !== "undefined") {
		const connectionSummary = connections.reduce<Record<string, number>>(
			(acc, conn) => {
				const type = conn.connection_type || "workflow";
				acc[type] = (acc[type] || 0) + 1;
				return acc;
			},
			{},
		);
		// eslint-disable-next-line no-console
		console.debug("[AgentPreview] Connection summary", connectionSummary);
	}

	if (process.env.NODE_ENV !== "production") {
		const connectionSummary = connections.reduce<Record<string, number>>(
			(acc, conn) => {
				const type = conn.connection_type || "workflow";
				acc[type] = (acc[type] || 0) + 1;
				return acc;
			},
			{},
		);
		// eslint-disable-next-line no-console
		console.debug("[GraphPreview] Connection summary", connectionSummary);
	}

	const edges: Edge[] = connections
		.filter((conn: any) => {
			const connectionType = conn.connection_type || "workflow";
			if (connectionType === "tool") {
				return true;
			}

			const sourceId = conn.source || conn.source_id;
			const targetId = conn.target || conn.target_id;
			const include = !toolNodeIds.has(sourceId) && !toolNodeIds.has(targetId);
			if (!include && typeof window !== "undefined") {
				// eslint-disable-next-line no-console
				console.debug("[GraphPreview] Filtering connection (tool exclusion)", {
					connectionType,
					sourceId,
					targetId,
				});
			}
			return include;
		})
		.map((conn: any, index: number) => {
			const sourceId = conn.source || conn.source_id;
			const targetId = conn.target || conn.target_id;
			const sourceHandle = conn.source_handle || conn.sourceHandle;

			const sourceNode = nodeLookup.get(sourceId);
			const targetNode = flowNodes.find((n) => n.id === targetId);

			const isToolConnection = conn.connection_type === "tool";
			const isDelegationConnection = conn.connection_type === "delegation";

			const isLoopback =
				!isToolConnection &&
				!isDelegationConnection &&
				sourceNode &&
				targetNode &&
				sourceNode.position &&
				targetNode.position &&
				sourceNode.position.x > targetNode.position.x;

			let edgeType: Edge["type"] = isLoopback ? "loopback" : "default";
			let edgeData: Record<string, any> = {
				connection_type: conn.connection_type || "workflow",
			};

			const conditionConfig =
				sourceNode?.condition_config ||
				sourceNode?.config ||
				sourceNode?.data?.condition_config;

			const conditionDetails = isConditionNode(sourceNode)
				? resolveConditionEdgeData(conditionConfig, sourceHandle)
				: null;

			if (conditionDetails) {
				edgeType = "condition";
				edgeData = {
					...edgeData,
					...conditionDetails,
				};
			}

			return {
				id: conn.id || `edge-${sourceId}-${targetId}-${index}`,
				source: sourceId,
				target: targetId,
				sourceHandle:
					conn.connection_type === "delegation"
						? "delegation"
						: conn.connection_type === "tool"
							? conn.source_handle === "workflow"
								? "workflow"
								: conn.source_handle === "delegation" || !conn.source_handle
									? "tools"
									: conn.source_handle
							: conn.source_handle === "branch-undefined"
								? undefined
								: conn.source_handle || conn.sourceHandle,
				targetHandle:
					conn.connection_type === "delegation"
						? "top"
						: conn.connection_type === "tool"
							? conn.target_handle || "top"
							: conn.target_handle || conn.targetHandle,
				label:
					conn.connection_type === "delegation" ||
					conn.connection_type === "tool"
						? undefined
						: conn.label,
				type: edgeType,
				data: edgeData,
				style: resolveEdgeStyle(conn),
			};
		});

	if (typeof window !== "undefined") {
		const delegationCount = connections.filter(
			(conn) => conn.connection_type === "delegation",
		).length;
		// eslint-disable-next-line no-console
		console.debug("[GraphPreview] Final edge stats", {
			totalEdges: edges.length,
			delegationConnections: delegationCount,
		});
	}

	return {
		nodes: flowNodes,
		edges,
	};
}
