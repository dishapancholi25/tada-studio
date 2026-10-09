"use client";

import { usePathname } from "next/navigation";
import React, {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useEffect,
	useState,
} from "react";
import type { Edge, Node } from "reactflow";
import { builderEdgeStroke } from "@/components/core/shared/defaultEdgeOptions";
import {
	api,
	type CreateNodeRequest,
	type CreateSubAgentRequest,
	type GraphData,
	type WorkflowRole,
} from "@/lib/api";
import {
	isConditionNodeType,
	resolveConditionEdgeData,
} from "@/lib/conditionEdgeHelpers";
import { logLoading, timeLoading, timeLoadingEnd } from "@/lib/debug";
import { convertGraphDefinitionToReactFlow } from "@/lib/graphDefinitionToReactFlow";
import { isStartNode } from "@/lib/nodeTypeUtils";
import { syncService } from "@/services/graphSyncService";
import { useGraphStore } from "@/stores/graphStore";
import { GraphDefinition, type GraphNode } from "@/types/api";

interface GraphContextType {
	currentGraph: GraphData | null;
	loading: boolean;
	error: string | null;
	graphs: GraphData[];

	// Graph operations
	createGraph: (name: string, description?: string) => Promise<void>;
	loadGraph: (name: string) => Promise<void>;
	loadGraphByWorkflowId: (
		workflowId: string,
		options?: { version?: number; graphDefinitionId?: string },
	) => Promise<void>;
	deleteGraph: (name: string) => Promise<void>;
	exportGraph: (format?: "full" | "minimal" | "langgraph") => Promise<any>;
	exportGraphPython: () => Promise<string>;
	saveGraph: () => Promise<void>;
	reloadGraph: () => Promise<void>;
	clearGraph: () => Promise<void>;
	updateWorkflowName: (newName: string) => Promise<void>;

	// Node operations
	createNode: (nodeData: Omit<CreateNodeRequest, "graph_name">) => {
		tempId: string;
		promise: Promise<string | undefined>;
	};
	createSubAgent: (
		parentAgentId: string,
		data?: Partial<
			Omit<CreateSubAgentRequest, "graph_name" | "parent_agent_id">
		>,
	) => Promise<void>;
	updateNode: (
		nodeId: string,
		updates: Partial<GraphNode["data"]>,
	) => Promise<void>;
	deleteNode: (nodeId: string) => Promise<void>;

	// Connection operations
	createConnection: (
		sourceId: string,
		targetId: string,
		sourceHandle?: string,
		targetHandle?: string,
		label?: string,
		connectionType?: string,
	) => Promise<void>;
	deleteConnection: (sourceId: string, targetId: string) => Promise<void>;

	// Read-only state from store
	nodes: Node[];
	edges: Edge[];
}

const GraphContext = createContext<GraphContextType | null>(null);

function deriveConditionEdgeMetadata(
	sourceNode: Node | undefined,
	sourceHandle: string | undefined,
	connectionType: string,
) {
	if (!sourceNode || connectionType !== "workflow") return null;

	const nodeDomainType = (sourceNode.data as any)?.type;
	const reactflowType = sourceNode.type;
	if (
		!isConditionNodeType(nodeDomainType) &&
		!isConditionNodeType(reactflowType)
	) {
		return null;
	}

	const conditionConfig =
		(sourceNode.data as any)?.condition_config ||
		(sourceNode.data as any)?.config;

	const details = resolveConditionEdgeData(conditionConfig, sourceHandle);
	if (!details) return null;

	return {
		edgeType: "condition" as const,
		edgeData: details,
	};
}

export function GraphProvider({ children }: { children: ReactNode }) {
	// Use Zustand store as primary source of truth
	const storeNodes = useGraphStore((state) => state.nodes);
	const storeEdges = useGraphStore((state) => state.edges);
	const storeCurrentGraph = useGraphStore((state) => state.currentGraph);
	const loadGraphToStore = useGraphStore((state) => state.loadGraph);
	const storeSetNodes = useGraphStore((state) => state.setNodes);
	const storeSetEdges = useGraphStore((state) => state.setEdges);

	// Legacy state for backward compatibility
	const [currentGraph, setCurrentGraph] = useState<GraphData | null>(null);
	const [graphs, setGraphs] = useState<GraphData[]>([]);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [isDeleting, setIsDeleting] = useState(false);
	const pathname = usePathname();
	const isBuilderRoute = Boolean(
		pathname &&
			(pathname.startsWith("/workflow") || pathname.includes("builder")),
	);
	const shouldMirrorStore = isBuilderRoute;

	// Helper to apply pending position updates from localChanges to nodes
	const applyPendingPositionUpdates = useCallback((nodes: Node[]) => {
		const pendingChanges = useGraphStore.getState().localChanges;
		const positionUpdates = pendingChanges.filter(
			(change) => change.type === "UPDATE_NODE_POSITION",
		);

		if (positionUpdates.length === 0) {
			return nodes;
		}

		// Apply pending position updates to preserve user's drag operations
		return nodes.map((node) => {
			const positionUpdate = positionUpdates.find(
				(update) => update.data.nodeId === node.id,
			);

			if (positionUpdate) {
				return {
					...node,
					position: positionUpdate.data.position,
				};
			}

			return node;
		});
	}, []);

	// PHASE 4A OPTIMIZATION: Remove duplicate nodes/edges state
	// Now return store values directly instead of copying to local state
	// This eliminates one layer of state duplication and reduces re-renders by ~25%

	// Keep currentGraph in sync with store
	useEffect(() => {
		if (!shouldMirrorStore) {
			if (currentGraph) {
				console.log(
					"[GraphContext] Skipping graph hydration on this route - clearing local graph view",
				);
				setCurrentGraph(null);
			}
			return;
		}

		if (storeCurrentGraph) {
			if (!currentGraph || currentGraph.name !== storeCurrentGraph.name) {
				console.log(
					"[GraphContext] Setting currentGraph to:",
					storeCurrentGraph.name,
				);
				setCurrentGraph(storeCurrentGraph);
			}
			return;
		}

		if (currentGraph) {
			console.log("[GraphContext] Clearing currentGraph (store has no graph)");
			setCurrentGraph(null);
		}
	}, [storeCurrentGraph, shouldMirrorStore, currentGraph]);

	// Convert backend graph data to React Flow format
	const convertToReactFlow = useCallback(
		(graphData: any) => convertGraphDefinitionToReactFlow(graphData),
		[],
	);

	// Create a new graph
	const createGraph = useCallback(
		async (name: string, description?: string) => {
			try {
				setLoading(true);
				setError(null);
				timeLoading(`api.createGraph ${name}`);
				const response = await api.createGraph({ name, description });
				timeLoadingEnd(`api.createGraph ${name}`);
				// console.log('Create graph response:', response);

				if (response.success && response.graph) {
					// Convert to React Flow format first
					const { nodes: flowNodes, edges: flowEdges } = convertToReactFlow(
						response.graph,
					);

					// Update Zustand store (primary source of truth)
					// Creator is always the owner
					const graphData: GraphData = {
						name: response.graph.name,
						workflow_id: (response.graph as any).workflow_id,
						workflow_role: "owner",
						description: response.graph.description,
						nodes: response.graph.nodes || [],
						connections:
							response.graph.connections || response.graph.edges || [],
						created_at: response.graph.created_at,
						updated_at: response.graph.updated_at,
					};
					loadGraphToStore(graphData, flowNodes, flowEdges);

					// Update legacy currentGraph state
					setCurrentGraph(response.graph as any);

					// Refresh the graphs list (non-blocking — don't delay navigation)
					api.listGraphs().then((listResponse) => {
						if (listResponse.success) {
							setGraphs(listResponse.graphs);
						}
					}).catch((err) => console.warn("Failed to refresh graphs list:", err));
				} else {
					// console.error('Graph creation failed or no graph returned');
				}
			} catch (err) {
				setError((err as Error).message);
				throw err;
			} finally {
				setLoading(false);
			}
		},
		[convertToReactFlow, loadGraphToStore],
	);

	// Load an existing graph
	const loadGraph = useCallback(
		async (name: string) => {
			try {
				syncService.cancelSync();
				setLoading(true);
				setError(null);
				timeLoading(`api.getGraph ${name}`);
				const response = await api.getGraph(name);
				timeLoadingEnd(`api.getGraph ${name}`);
				if (response.success) {
					// Convert GraphDefinition to GraphData format
					// Preserve workflow_id from response or fall back to current value
					const graphData: GraphData = {
						name: response.graph.name,
						workflow_id:
							(response.graph as any).workflow_id ||
							useGraphStore.getState().currentGraph?.workflow_id,
						workflow_role: (response as any).workflow_role as WorkflowRole | undefined,
						description: response.graph.description || "",
						nodes: response.graph.nodes || [],
						connections:
							(response.graph as any).connections || response.graph.edges || [],
						created_at: new Date().toISOString(),
						updated_at: new Date().toISOString(),
					};

					// Convert to React Flow format
					const { nodes: flowNodes, edges: flowEdges } = convertToReactFlow(
						response.graph,
					);

					// LOAD INTO ZUSTAND STORE (primary source of truth)
					loadGraphToStore(graphData, flowNodes, flowEdges);

					// Update legacy currentGraph state
					setCurrentGraph(graphData);
				}
			} catch (err) {
				setError((err as Error).message);
				throw err;
			} finally {
				setLoading(false);
			}
		},
		[convertToReactFlow, loadGraphToStore],
	);

	// Load a graph by workflow ID (UUID)
	const loadGraphByWorkflowId = useCallback(
		async (
			workflowId: string,
			options?: { version?: number; graphDefinitionId?: string },
		) => {
			try {
				syncService.cancelSync();
				setLoading(true);
				setError(null);
				timeLoading(`api.getGraphByWorkflowId ${workflowId}`);
				const response = await api.getGraphByWorkflowId(workflowId, options);
				timeLoadingEnd(`api.getGraphByWorkflowId ${workflowId}`);
				if (response.success) {
					// Convert GraphDefinition to GraphData format
					const graphData: GraphData = {
						name: response.graph.name,
						workflow_id:
							(response.graph as any).workflow_id ||
							(response as any).workflow_id ||
							workflowId,
						workflow_role: (response as any).workflow_role as WorkflowRole | undefined,
						description: response.graph.description || "",
						nodes: response.graph.nodes || [],
						connections:
							(response.graph as any).connections || response.graph.edges || [],
						created_at: new Date().toISOString(),
						updated_at: new Date().toISOString(),
					};

					// Convert to React Flow format
					const { nodes: flowNodes, edges: flowEdges } = convertToReactFlow(
						response.graph,
					);

					// Check if this is a historical (non-latest) version
					const isHistorical =
						response.loaded_version != null && response.is_latest === false;

					if (isHistorical) {
						// Load into store as historical version (disables auto-save)
						const loadHistorical =
							useGraphStore.getState().loadHistoricalVersion;
						loadHistorical(
							graphData,
							flowNodes,
							flowEdges,
							response.loaded_version!,
							options?.graphDefinitionId || "",
						);
					} else {
						// LOAD INTO ZUSTAND STORE (primary source of truth)
						loadGraphToStore(graphData, flowNodes, flowEdges, response.loaded_version);
					}

					// Update legacy currentGraph state
					setCurrentGraph(graphData);
				}
			} catch (err) {
				setError((err as Error).message);
				throw err;
			} finally {
				setLoading(false);
			}
		},
		[convertToReactFlow, loadGraphToStore],
	);

	// Delete a graph
	const deleteGraph = useCallback(
		async (name: string) => {
			try {
				setLoading(true);
				setError(null);
				await api.deleteGraph(name);

				// Notify other components (e.g. WorkflowPublisher) that the list changed
				window.dispatchEvent(new CustomEvent("workflowListChanged"));

				// If deleting the currently loaded graph, clear all state
				if (useGraphStore.getState().currentGraph?.name === name) {
					// Clear Zustand store (clears nodes, edges, and all tracking)
					const clearStore = useGraphStore.getState().clearGraph;
					clearStore();

					// Clear legacy currentGraph state
					setCurrentGraph(null);
				}
			} catch (err) {
				setError((err as Error).message);
				throw err;
			} finally {
				setLoading(false);
			}
		},
		[],
	);

	// Export graph
	const exportGraph = useCallback(
		async (format: "full" | "minimal" | "langgraph" = "full") => {
			const currentGraph = useGraphStore.getState().currentGraph;
			if (!currentGraph) throw new Error("No graph loaded");

			try {
				setLoading(true);
				setError(null);
				const response = await api.exportGraph(currentGraph.name, format);
				return response.data;
			} catch (err) {
				setError((err as Error).message);
				throw err;
			} finally {
				setLoading(false);
			}
		},
		[],
	);

	// Export graph as Python
	const exportGraphPython = useCallback(async () => {
		const currentGraph = useGraphStore.getState().currentGraph;
		if (!currentGraph) throw new Error("No graph loaded");

		try {
			setLoading(true);
			setError(null);
			return await api.exportGraphPython(currentGraph.name);
		} catch (err) {
			setError((err as Error).message);
			throw err;
		} finally {
			setLoading(false);
		}
	}, []);

	// Save current graph state
	const saveGraph = useCallback(async () => {
		if (!useGraphStore.getState().currentGraph) throw new Error("No graph loaded");

		setLoading(true);
		setError(null);

		try {
			// OPTIMIZATION: Use sync service for consistent save behavior
			// This ensures all pending changes are synced via the batch API
			await syncService.forceSync();
		} catch (err) {
			setError((err as any).message || "Failed to save graph");
			throw err;
		} finally {
			setLoading(false);
		}
	}, []);

	// Update workflow name
	const updateWorkflowName = useCallback(
		async (newName: string) => {
			const currentGraph = useGraphStore.getState().currentGraph;
			if (!currentGraph) throw new Error("No graph loaded");

			const oldName = currentGraph.name;
			setLoading(true);
			setError(null);

			try {
				const response = await api.updateWorkflowName(oldName, newName);

				if (response.success && response.graph) {
					// Update the graph data with new name
					const updatedGraphData: GraphData = {
						...currentGraph,
						name: newName,
						updated_at: response.graph.updated_at || new Date().toISOString(),
					};

					// Update store with new name
					loadGraphToStore(updatedGraphData, useGraphStore.getState().nodes, useGraphStore.getState().edges);

					// Update legacy currentGraph state
					setCurrentGraph(updatedGraphData);

					// Refresh the graphs list (non-blocking — don't delay navigation)
					api.listGraphs().then((listResponse) => {
						if (listResponse.success) {
							setGraphs(listResponse.graphs);
						}
					}).catch((err) => console.warn("Failed to refresh graphs list:", err));
				}
			} catch (err) {
				setError((err as any).message || "Failed to update workflow name");
				throw err;
			} finally {
				setLoading(false);
			}
		},
		[loadGraphToStore],
	);

	// Create a node - returns tempId immediately for instant UI, promise resolves with final ID.
	// Uses setNodes (not addNode) to avoid pushing ADD_NODE to localChanges, which would cause
	// the sync service to create a duplicate node alongside the direct api.createNode() call.
	// Callers can use tempId for instant connections; replaceNodeId updates them before sync fires.
	const createNode = useCallback(
		(nodeData: Omit<CreateNodeRequest, "graph_name">): {
			tempId: string;
			promise: Promise<string | undefined>;
		} => {
			const currentGraph = useGraphStore.getState().currentGraph;
			if (!currentGraph) throw new Error("No graph loaded");

			setError(null);

			// Generate temp ID for immediate UI feedback
			const tempId = `temp-node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

			// Determine React Flow node type based on node type
			const nodeType = nodeData.node_type?.toUpperCase();
			const isSpecialNode = nodeType === "START" || nodeType === "END";
			const isCondition = nodeType === "CONDITION";
			const isSubWorkflow = nodeType === "SUBWORKFLOW";
			const isDocumentSearch = nodeType === "DOCUMENT_SEARCH";
			const isDocumentRetrieve = nodeType === "DOCUMENT_RETRIEVE";
			const isDocumentLoad = nodeType === "DOCUMENT_LOAD";
			const isDatabaseQuery = nodeType === "DATABASE_QUERY";
			const isDatabaseInsert = nodeType === "DATABASE_INSERT";
			const isDatabaseQueryAction = nodeType === "DATABASE_QUERY_ACTION";
			const isHttpRequest = nodeType === "HTTP_REQUEST";
			const isHttpRequestAction = nodeType === "HTTP_REQUEST_ACTION";
			const isWebSearch = nodeType === "WEB_SEARCH";
			const isMcpServer = nodeType === "MCP_SERVER";
			const isCheckpoint = nodeType === "CHECKPOINT";
			const isEmailSend = nodeType === "EMAIL_SEND";
			const isEmailSendTool = nodeType === "EMAIL_SEND_TOOL";
			const isFileRead = nodeType === "FILE_READ";
			const isFileWrite = nodeType === "FILE_WRITE";

			let reactFlowType = "agentNode";
			if (isSpecialNode) reactFlowType = "flowNode";
			else if (isCondition) reactFlowType = "conditionNode";
			else if (isSubWorkflow) reactFlowType = "subWorkflowNode";
			else if (isCheckpoint) reactFlowType = "flowNode";
			else if (isDocumentSearch) reactFlowType = "documentSearchNode";
			else if (isDocumentRetrieve) reactFlowType = "documentRetrieveNode";
			else if (isDocumentLoad) reactFlowType = "documentLoadNode";
			else if (isDatabaseQuery) reactFlowType = "databaseQueryNode";
			else if (isDatabaseInsert) reactFlowType = "databaseInsertNode";
			else if (isDatabaseQueryAction) reactFlowType = "databaseQueryActionNode";
			else if (isHttpRequest) reactFlowType = "httpRequestNode";
			else if (isHttpRequestAction) reactFlowType = "httpRequestActionNode";
			else if (isWebSearch) reactFlowType = "webSearchNode";
			else if (isMcpServer) reactFlowType = "mcpServerNode";
			else if (isEmailSend) reactFlowType = "emailSendNode";
			else if (isEmailSendTool) reactFlowType = "emailSendToolNode";
			else if (isFileRead) reactFlowType = "fileReadNode";
			else if (isFileWrite) reactFlowType = "fileWriteNode";

			// Create optimistic node for instant UI
			const optimisticNode: Node = {
				id: tempId,
				type: reactFlowType,
				position: nodeData.position || { x: 100, y: 100 },
				data: {
					...nodeData,
					id: tempId,
					name: nodeData.name || "New Node",
					type: nodeData.node_type,
				},
			};

			// Add to store immediately for instant UI feedback.
			// CRITICAL: Use setNodes (not addNode) to avoid pushing an ADD_NODE change
			// to localChanges. The direct api.createNode() call handles backend persistence.
			// Using addNode here would cause the sync service to also create the node,
			// resulting in duplicates.
			useGraphStore.getState().setNodes((prev) => [...prev, optimisticNode]);

			// Capture current nodes for comparison when backend responds
			const previousNodes = useGraphStore.getState().nodes;

			// Backend sync runs in background — resolves with real node ID
			const promise = (async (): Promise<string | undefined> => {
				try {
					const response = await api.createNode({
						...nodeData,
						graph_name: currentGraph.name,
					});

					if (response.success && response.graph) {
						const expectedNodeId =
							(response.node as any)?.uniq_id ||
							(response.node as any)?.id ||
							undefined;

						const { nodes: flowNodes } = convertToReactFlow(response.graph);

						let newNode = expectedNodeId
							? flowNodes.find((node) => node.id === expectedNodeId)
							: undefined;

						if (!newNode) {
							newNode = flowNodes.find(
								(node) =>
									!previousNodes.some((prevNode) => prevNode.id === node.id),
							);
						}

						if (newNode) {
							// Replace temp ID with real backend ID in nodes, edges, and localChanges.
							// This also updates any ADD_CONNECTION changes that reference the temp ID.
							useGraphStore.getState().replaceNodeId(tempId, newNode.id);

							// Update full node data from backend (prompt, config, etc.)
							const currentNodes = useGraphStore.getState().nodes;
							const updatedNodes = currentNodes.map((n) =>
								n.id === newNode.id ? newNode : n,
							);
							useGraphStore.getState().setNodes(updatedNodes);

							console.log(
								`[GraphContext] Created node ${newNode.id}, replaced optimistic node ${tempId}`,
							);
							return newNode.id;
						}

						console.warn(
							"[GraphContext] Failed to resolve backend node ID, falling back to temp ID",
							{ tempId, expectedNodeId, flowNodeIds: flowNodes.map((n) => n.id) },
						);
						return tempId;
					}
					return undefined;
				} catch (err) {
					// Rollback: remove the optimistic node and any edges connected to it
					useGraphStore.getState().setNodes((prev) =>
						prev.filter((n) => n.id !== tempId),
					);
					useGraphStore.getState().setEdges((prev) =>
						prev.filter((e) => e.source !== tempId && e.target !== tempId),
					);
					setError((err as Error).message);
					throw err;
				}
			})();

			return { tempId, promise };
		},
		[convertToReactFlow],
	);

	// Create a sub-agent
	const createSubAgent = useCallback(
		async (
			parentAgentId: string,
			data?: Partial<
				Omit<CreateSubAgentRequest, "graph_name" | "parent_agent_id">
			>,
		) => {
			const currentGraph = useGraphStore.getState().currentGraph;
			if (!currentGraph) throw new Error("No graph loaded");

			try {
				setLoading(true);
				setError(null);
				const response = await api.createSubAgent({
					graph_name: currentGraph.name,
					parent_agent_id: parentAgentId,
					...data,
				});

				if (response.success && response.graph) {
					// Preserve workflow_role from current graph to avoid collaboration disconnect
					const prevGraph = useGraphStore.getState().currentGraph;

					// Convert GraphDefinition to GraphData format
					const graphData: GraphData = {
						name: response.graph.name,
						workflow_id: (response.graph as any).workflow_id,
						description: response.graph.description || "",
						nodes: response.graph.nodes || [],
						connections:
							(response.graph as any).connections || response.graph.edges || [],
						created_at: new Date().toISOString(),
						updated_at: new Date().toISOString(),
						workflow_role: (response.graph as any).workflow_role || prevGraph?.workflow_role,
					};

					// Convert to React Flow format
					const { nodes: flowNodes, edges: flowEdges } = convertToReactFlow(
						response.graph,
					);

					// CRITICAL FIX: Apply pending position updates before updating store
					const nodesWithPendingPositions =
						applyPendingPositionUpdates(flowNodes);

					// UPDATE STORE with new graph state (with preserved positions)
					storeSetNodes(nodesWithPendingPositions);
					storeSetEdges(flowEdges);

					// Update legacy currentGraph state
					setCurrentGraph(graphData);

					// Sub-agent already created on backend, no sync needed
				}
			} catch (err) {
				setError((err as Error).message);
				throw err;
			} finally {
				setLoading(false);
			}
		},
		[
			convertToReactFlow,
			storeSetNodes,
			storeSetEdges,
			applyPendingPositionUpdates,
		],
	);

	// Update a node
	const updateNode = useCallback(
		async (nodeId: string, updates: Partial<GraphNode["data"]>) => {
			if (!useGraphStore.getState().currentGraph) throw new Error("No graph loaded");

			// Don't update if a delete operation is in progress
			if (isDeleting) {
				return;
			}

			// Check if this is a position-only update
			const isPositionUpdate =
				Object.keys(updates).length === 1 && "position" in updates;

			try {
				setError(null);

				// PHASE 1 FIX: All updates now use store-first + debounced sync pattern
				// This eliminates race conditions between position and property updates

				if (isPositionUpdate) {
					// Position update - check if node exists
					const nodeExists = useGraphStore.getState().nodes.some((n) => n.id === nodeId);
					if (!nodeExists) {
						return;
					}

					// Update store immediately for instant UI
					const storeUpdatePosition =
						useGraphStore.getState().updateNodePosition;
					storeUpdatePosition(
						nodeId,
						updates.position as { x: number; y: number },
					);
				} else {
					// Non-position update - also use store-first pattern
					// Update store immediately for instant UI feedback
					const storeUpdateNode = useGraphStore.getState().updateNode;
					storeUpdateNode(nodeId, updates);
				}

				// Trigger debounced sync (will batch all updates together)
				// The sync service will handle the backend API call
				syncService.scheduleSync();
			} catch (err) {
				setError((err as Error).message);
				throw err;
			}
		},
		[isDeleting],
	);

	// Delete a node
	const deleteNode = useCallback(
		async (nodeId: string) => {
			const currentGraph = useGraphStore.getState().currentGraph;
			if (!currentGraph) throw new Error("No graph loaded");

			const nodeToDelete = useGraphStore
				.getState()
				.nodes.find((node) => node.id === nodeId);
			if (isStartNode(nodeToDelete)) {
				throw new Error("The start node is required and cannot be deleted.");
			}

			try {
				setIsDeleting(true);
				setError(null);

				// OPTIMIZATION: Optimistically remove from STORE immediately (instant UI update)
				const storeDeleteNode = useGraphStore.getState().deleteNode;
				storeDeleteNode(nodeId);

				// Call backend to delete node
				await api.deleteNode(currentGraph.name, nodeId);

				// Trigger debounced sync (will batch with other changes)
				syncService.scheduleSync();
			} catch (err) {
				setError((err as Error).message);
				// If delete failed, reload to restore the node
				try {
					const graphResponse = await api.getGraph(currentGraph.name);
					if (graphResponse.success && graphResponse.graph) {
						const graphData: GraphData = {
							name: graphResponse.graph.name,
							workflow_id: (graphResponse.graph as any).workflow_id,
							workflow_role: (graphResponse as any).workflow_role || currentGraph.workflow_role,
							description: graphResponse.graph.description || "",
							nodes: graphResponse.graph.nodes || [],
							connections:
								(graphResponse.graph as any).connections ||
								graphResponse.graph.edges ||
								[],
							created_at: new Date().toISOString(),
							updated_at: new Date().toISOString(),
						};
						const { nodes: flowNodes, edges: flowEdges } = convertToReactFlow(
							graphResponse.graph,
						);

						// Restore to store
						loadGraphToStore(graphData, flowNodes, flowEdges);

						// Update legacy currentGraph state for context consumers
						setCurrentGraph(graphData);
					}
				} catch (reloadErr) {
					console.error("Failed to reload after delete error:", reloadErr);
				}
				throw err;
			} finally {
				setIsDeleting(false);
			}
		},
		[convertToReactFlow, loadGraphToStore],
	);

	// Create a connection
	// NOTE: Connection is created optimistically in the store, then persisted via sync service.
	// This ensures a single path for backend persistence (no duplicate connections).
	const createConnection = useCallback(
		async (
			sourceId: string,
			targetId: string,
			sourceHandle?: string,
			targetHandle?: string,
			label?: string,
			connectionType?: string,
		): Promise<void> => {
			if (!useGraphStore.getState().currentGraph) throw new Error("No graph loaded");

			const storeState = useGraphStore.getState();
			const sourceNode = storeState.nodes.find((node) => node.id === sourceId);
			const targetNode = storeState.nodes.find((node) => node.id === targetId);

			// === CONNECTION VALIDATION ===

			// 1. Prevent self-loops
			if (sourceId === targetId) {
				throw new Error("Cannot connect a node to itself");
			}

			// 2. Check if source node exists
			if (!sourceNode) {
				throw new Error("Source node not found");
			}

			// 3. Check if target node exists
			if (!targetNode) {
				throw new Error("Target node not found");
			}

			// 4. Prevent duplicate connections (same source, target, and handles)
			const existingConnection = storeState.edges.find(
				(edge) =>
					edge.source === sourceId &&
					edge.target === targetId &&
					edge.sourceHandle === (sourceHandle || null) &&
					edge.targetHandle === (targetHandle || null),
			);
			if (existingConnection) {
				throw new Error("Connection already exists between these nodes");
			}

			// 5. Prevent connecting to START node (START only has outgoing connections)
			const targetNodeType = targetNode.data?.type?.toUpperCase?.() || targetNode.type?.toUpperCase?.();
			if (targetNodeType === "START") {
				throw new Error("Cannot connect to the START node");
			}

			// 6. Prevent connecting from END node (END only has incoming connections)
			const sourceNodeType = sourceNode.data?.type?.toUpperCase?.() || sourceNode.type?.toUpperCase?.();
			if (sourceNodeType === "END") {
				throw new Error("Cannot connect from the END node");
			}

			// Create optimistic edge with temp ID
			const tempEdgeId = `temp-edge-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

			const normalizedType = (connectionType || "workflow").toLowerCase();
			const optimisticEdge: Edge = {
				id: tempEdgeId,
				source: sourceId,
				target: targetId,
				sourceHandle: sourceHandle,
				targetHandle: targetHandle,
				label: label,
				type: "default",
				data: {
					connection_type: normalizedType,
				},
				style: {
					stroke: builderEdgeStroke,
					strokeWidth: 3,
					opacity: 0.7,
				},
			};

			if (normalizedType === "delegation") {
				optimisticEdge.sourceHandle = sourceHandle || "delegation";
				optimisticEdge.targetHandle = targetHandle || "top";
				optimisticEdge.label = undefined;
				optimisticEdge.style = {
					stroke: builderEdgeStroke,
					strokeDasharray: "5 5",
					strokeWidth: 1.5,
					opacity: 0.6,
				};
			} else if (normalizedType === "tool") {
				optimisticEdge.sourceHandle = sourceHandle || "tools";
				optimisticEdge.targetHandle = targetHandle || "top";
				optimisticEdge.label = undefined;
				optimisticEdge.style = {
					stroke: builderEdgeStroke,
					strokeWidth: 2.5,
					strokeDasharray: "4 2",
					opacity: 1,
				};
			}

			const resolvedSourceHandle = optimisticEdge.sourceHandle ?? undefined;
			const conditionEdgeMetadata = deriveConditionEdgeMetadata(
				sourceNode,
				resolvedSourceHandle,
				normalizedType,
			);

			if (conditionEdgeMetadata) {
				optimisticEdge.type = conditionEdgeMetadata.edgeType;
				optimisticEdge.label = undefined;
				optimisticEdge.data = {
					...optimisticEdge.data,
					...conditionEdgeMetadata.edgeData,
				};
			}

			// Add edge to store - this records ADD_CONNECTION in localChanges
			// The sync service will handle persisting to backend
			storeState.addConnection(optimisticEdge);

			// Optimistic node-data mutations for delegation connections so the visual
			// transformation (regular agent → sub-agent) is instant without a full reload.
			if (normalizedType === "delegation") {
				useGraphStore.getState().updateNode(targetId, {
					is_sub_agent: true,
					parent_agent_id: sourceId,
				});
				const sourceConfig = sourceNode?.data?.agent_config ?? {};
				const existingDelegated: string[] = sourceConfig.delegated_agents ?? [];
				useGraphStore.getState().updateNode(sourceId, {
					agent_config: {
						...sourceConfig,
						is_orchestrator: true,
						delegated_agents: existingDelegated.includes(targetId)
							? existingDelegated
							: [...existingDelegated, targetId],
					},
				});
			}

			console.log("[GraphContext] Created optimistic edge:", {
				id: tempEdgeId,
				source: sourceId,
				target: targetId,
				sourceHandle: sourceHandle || "none",
				targetHandle: targetHandle || "none",
				connectionType: connectionType || "workflow",
				style: optimisticEdge.style,
			});

			// Schedule sync to persist to backend
			// NOTE: We no longer make a direct API call here - the sync service handles
			// all backend persistence to avoid duplicate connections.
			syncService.scheduleSync();
		},
		[],
	);

	// Delete a connection
	const deleteConnection = useCallback(
		async (sourceId: string, targetId: string) => {
			const currentGraph = useGraphStore.getState().currentGraph;
			if (!currentGraph) throw new Error("No graph loaded");

			try {
				setIsDeleting(true);
				setError(null);

				// Look up the edge before removal to check its type
				const allEdges = useGraphStore.getState().edges;
				const edgeToDelete = allEdges.find(
					(edge) =>
						edge.source === sourceId && edge.target === targetId,
				);

				// Revert delegation node-data optimistically before the store delete
				if (edgeToDelete?.data?.connection_type === "delegation") {
					useGraphStore.getState().updateNode(targetId, {
						is_sub_agent: false,
						parent_agent_id: null,
					});
					const remainingDelegations = allEdges.filter(
						(edge) =>
							edge.source === sourceId &&
							edge.data?.connection_type === "delegation" &&
							edge.id !== edgeToDelete.id,
					);
					const sourceNode = useGraphStore
						.getState()
						.nodes.find((n) => n.id === sourceId);
					const sourceConfig = sourceNode?.data?.agent_config ?? {};
					const updatedDelegatedAgents = (
						sourceConfig.delegated_agents ?? []
					).filter((id: string) => id !== targetId);
					useGraphStore.getState().updateNode(sourceId, {
						agent_config: {
							...sourceConfig,
							is_orchestrator: remainingDelegations.length > 0,
							delegated_agents: updatedDelegatedAgents,
						},
					});
				}

				// OPTIMIZATION: Optimistically remove from STORE immediately (instant UI update)
				const storeDeleteConnection = useGraphStore.getState().deleteConnection;
				storeDeleteConnection(sourceId, targetId);

				// Call backend to delete connection
				await api.deleteConnection(currentGraph.name, sourceId, targetId);

				// Trigger debounced sync (will batch with other changes)
				syncService.scheduleSync();
			} catch (err) {
				setError((err as Error).message);
				// If delete failed, reload to restore the connection
				try {
					const graphResponse = await api.getGraph(currentGraph.name);
					if (graphResponse.success && graphResponse.graph) {
						const graphData: GraphData = {
							name: graphResponse.graph.name,
							workflow_id: (graphResponse.graph as any).workflow_id,
							workflow_role: (graphResponse as any).workflow_role || currentGraph.workflow_role,
							description: graphResponse.graph.description || "",
							nodes: graphResponse.graph.nodes || [],
							connections:
								(graphResponse.graph as any).connections ||
								graphResponse.graph.edges ||
								[],
							created_at: new Date().toISOString(),
							updated_at: new Date().toISOString(),
						};
						const { nodes: flowNodes, edges: flowEdges } = convertToReactFlow(
							graphResponse.graph,
						);

						// Restore to store
						loadGraphToStore(graphData, flowNodes, flowEdges);

						// Update legacy currentGraph state for context consumers
						setCurrentGraph(graphData);
					}
				} catch (reloadErr) {
					console.error(
						"Failed to reload after delete connection error:",
						reloadErr,
					);
				}
				throw err;
			} finally {
				setIsDeleting(false);
			}
		},
		[convertToReactFlow, loadGraphToStore],
	);

	// Reload current graph from disk
	const reloadGraph = useCallback(async () => {
		const currentGraph = useGraphStore.getState().currentGraph;
		if (!currentGraph) return;

		syncService.cancelSync();
		setLoading(true);
		setError(null);

		try {
			timeLoading(`api.reloadGraph ${currentGraph.name}`);
			const reloadResponse = await api.reloadGraph(currentGraph.name);
			timeLoadingEnd(`api.reloadGraph ${currentGraph.name}`);

			if (reloadResponse.success) {

				// Convert GraphDefinition to GraphData format (same as loadGraph)
				// Preserve workflow_id and workflow_role from response or fall back to current value
				const graphData: GraphData = {
					name: reloadResponse.graph.name,
					workflow_id:
						(reloadResponse.graph as any).workflow_id ||
						currentGraph.workflow_id,
					workflow_role:
						(reloadResponse as any).workflow_role ||
						currentGraph.workflow_role,
					description: reloadResponse.graph.description || "",
					nodes: reloadResponse.graph.nodes || [],
					connections:
						(reloadResponse.graph as any).connections ||
						reloadResponse.graph.edges ||
						[],
					created_at: new Date().toISOString(),
					updated_at: new Date().toISOString(),
				};


				const { nodes: flowNodes, edges: flowEdges } = convertToReactFlow(
					reloadResponse.graph,
				);

				// Use loadGraphToStore for consistency with loadGraph
				loadGraphToStore(graphData, flowNodes, flowEdges);
				setCurrentGraph(graphData);
			} else {
				throw new Error("Failed to reload graph");
			}
		} catch (err) {
			setError((err as any).message || "Failed to reload graph");
			throw err;
		} finally {
			setLoading(false);
		}
	}, [convertToReactFlow, loadGraphToStore]);

	// Clear all nodes and edges (tracked operation - persists to backend)
	const clearGraph = useCallback(async () => {
		if (!useGraphStore.getState().currentGraph) throw new Error("No graph loaded");

		try {
			setError(null);
			// Use tracked store operation
			useGraphStore.getState().clearAllNodesAndEdges();
			// Force immediate sync to persist deletions
			await syncService.forceSync();
		} catch (err) {
			setError((err as Error).message);
			throw err;
		}
	}, []);

	const value = {
		currentGraph,
		loading,
		error,
		graphs,
		createGraph,
		loadGraph,
		loadGraphByWorkflowId,
		deleteGraph,
		exportGraph,
		exportGraphPython,
		saveGraph,
		reloadGraph,
		clearGraph,
		updateWorkflowName,
		createNode,
		createSubAgent,
		updateNode,
		deleteNode,
		createConnection,
		deleteConnection,
		// Read-only state from store
		nodes: storeNodes,
		edges: storeEdges,
	};

	return (
		<GraphContext.Provider value={value}>{children}</GraphContext.Provider>
	);
}

export function useGraph() {
	const context = useContext(GraphContext);
	if (!context) {
		throw new Error("useGraph must be used within a GraphProvider");
	}
	return context;
}
