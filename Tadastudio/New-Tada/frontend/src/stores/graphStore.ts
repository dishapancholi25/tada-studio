/**
 * Local-first graph store using Zustand
 * This is the single source of truth for graph state during editing sessions
 */

import type { Edge, Node } from "reactflow";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import type { GraphData } from "@/lib/api";
import type { SyncStatus, TypedGraphChange } from "@/types/graphChanges";
import { normalizeNodeDataForBackend } from "@/utils/graphDiff";

// Import sync service (will be called after mutations)
let scheduleSyncFn: (() => void) | null = null;

// Export function to set sync scheduler (called from sync service)
export function setSyncScheduler(fn: () => void) {
	scheduleSyncFn = fn;
}

// Helper to trigger sync after mutation
function triggerSync() {
	// Skip auto-sync when viewing a historical version
	if (useGraphStore?.getState?.()?.isHistoricalVersion) {
		return;
	}
	if (scheduleSyncFn) {
		scheduleSyncFn();
	}
}

// PHASE 2: Temp ID generation for optimistic creates
// Using timestamp + random string for uniqueness
export function generateTempId(prefix: string = "temp"): string {
	return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// PHASE 2: Mapping from temp IDs to real IDs
interface TempIdMapping {
	tempId: string;
	realId: string | null;
	type: "node" | "edge";
}

// Store temp ID mappings for ID resolution
const tempIdMappings: Map<string, TempIdMapping> = new Map();

interface GraphState {
	// Current graph being edited (local state)
	currentGraph: GraphData | null;

	// React Flow representation
	nodes: Node[];
	edges: Edge[];

	// Change tracking for sync
	localChanges: TypedGraphChange[];
	pendingSyncChanges: TypedGraphChange[];

	// Sync status
	syncStatus: SyncStatus;
	lastSyncedAt: number | null;
	lastSyncError: string | null;

	// Dirty flag
	isDirty: boolean;

	// Loading states
	isLoading: boolean;
	isSyncing: boolean;

	// PHASE 5: Conflict detection
	graphVersion: number; // Incremented on each successful sync
	lastServerVersion: number | null; // Version from last server response
	hasConflict: boolean; // Whether a conflict was detected
	conflictData: {
		localVersion: number;
		serverVersion: number;
		localChanges: TypedGraphChange[];
		serverState: { nodes: Node[]; edges: Edge[] } | null;
	} | null;

	// Version viewing state
	isHistoricalVersion: boolean;
	loadedVersion: number | null;
	loadedGraphDefinitionId: string | null;
	currentVersion: number | null; // The DB version number of the currently loaded graph

	// Clipboard for copy/paste
	clipboard: {
		nodes: Node[];
		edges: Edge[];
		copyOffset: { x: number; y: number };
	} | null;

	// Actions - Graph Loading
	loadGraph: (graph: GraphData, nodes: Node[], edges: Edge[], version?: number | null) => void;
	loadHistoricalVersion: (
		graph: GraphData,
		nodes: Node[],
		edges: Edge[],
		version: number,
		graphDefinitionId: string,
	) => void;
	exitHistoricalVersion: () => void;
	setCurrentVersion: (version: number) => void;
	clearGraph: () => void;

	// Actions - Node Operations
	addNode: (node: Node) => void;
	updateNode: (nodeId: string, updates: Partial<Node["data"]>) => void;
	deleteNode: (nodeId: string) => void;
	updateNodePosition: (
		nodeId: string,
		position: { x: number; y: number },
	) => void;
	setNodes: (nodes: Node[] | ((prev: Node[]) => Node[])) => void;
	// Clear all nodes and edges with proper change tracking (for reset functionality)
	clearAllNodesAndEdges: () => void;
	// PHASE 2: Replace temp ID with real ID after backend confirms
	replaceNodeId: (tempId: string, realId: string) => void;
	// Remove ADD_NODE change after direct API creation (prevents sync service duplicate)
	removeNodeChange: (nodeId: string) => void;
	// PHASE 6: Batch execution status updates
	batchUpdateNodeStatus: (
		updates: Array<{ nodeId: string; status: string; duration?: number }>,
	) => void;
	// Batch position updates for multi-node drag operations
	batchUpdateNodePositions: (
		updates: Array<{ nodeId: string; position: { x: number; y: number } }>,
	) => void;

	// Actions - Connection Operations
	addConnection: (edge: Edge) => void;
	deleteConnection: (sourceId: string, targetId: string) => void;
	setEdges: (edges: Edge[] | ((prev: Edge[]) => Edge[])) => void;
	// PHASE 2: Replace temp ID with real ID after backend confirms
	replaceEdgeId: (tempId: string, realId: string) => void;

	// Actions - Sync Operations
	markAsSyncing: () => void;
	markAsSynced: () => void;
	markAsSyncError: (error: string) => void;
	markAsOffline: () => void;
	getChangesSinceLastSync: () => TypedGraphChange[];
	clearSyncedChanges: () => void;
	getPendingSyncChanges: () => TypedGraphChange[];

	// PHASE 5: Conflict resolution actions
	detectConflict: (
		serverVersion: number,
		serverNodes: Node[],
		serverEdges: Edge[],
	) => boolean;
	resolveConflict: (strategy: "keep-local" | "use-server" | "merge") => void;
	clearConflict: () => void;

	// Actions - Clipboard
	copySelectedNodes: (selectedNodeIds: string[]) => void;
	pasteNodes: (offset?: { x: number; y: number }) => {
		nodeIdMap: Map<string, string>;
		newNodes: Node[];
		newEdges: Edge[];
	};
	clearClipboard: () => void;

	// Actions - Helpers
	setLoading: (loading: boolean) => void;
	setIsDirty: (dirty: boolean) => void;

	// Actions - Undo/Redo Persistence
	applyUndoRedoChanges: (changes: TypedGraphChange[]) => void;
}

export const useGraphStore = create<GraphState>()(
	persist(
		immer((set, get) => ({
			// Initial state
			currentGraph: null,
			nodes: [],
			edges: [],
			localChanges: [],
			pendingSyncChanges: [],
			syncStatus: "saved",
			lastSyncedAt: null,
			lastSyncError: null,
			isDirty: false,
			isLoading: false,
			isSyncing: false,
			// PHASE 5: Conflict tracking
			graphVersion: 0,
			lastServerVersion: null,
			hasConflict: false,
			conflictData: null,
			// Version viewing
			isHistoricalVersion: false,
			loadedVersion: null,
			loadedGraphDefinitionId: null,
			currentVersion: null,
			// Clipboard
			clipboard: null,

			// Graph Loading
			loadGraph: (graph, nodes, edges, version) =>
				set((state) => {
					console.log("[GraphStore] loadGraph called:", {
						graphName: graph.name,
						nodeCount: nodes.length,
						edgeCount: edges.length,
					});
					state.currentGraph = graph;
					state.nodes = nodes;
					state.edges = edges;
					state.localChanges = [];
					state.pendingSyncChanges = [];
					state.isDirty = false;
					state.syncStatus = "saved";
					state.lastSyncedAt = Date.now();
					state.lastSyncError = null;
					state.isHistoricalVersion = false;
					state.loadedVersion = null;
					state.loadedGraphDefinitionId = null;
					state.currentVersion = version ?? null;
					state.clipboard = null; // Clear clipboard to prevent memory accumulation
					console.log("[GraphStore] Graph loaded successfully");
				}),

			loadHistoricalVersion: (graph, nodes, edges, version, graphDefinitionId) =>
				set((state) => {
					console.log("[GraphStore] loadHistoricalVersion called:", {
						graphName: graph.name,
						version,
						graphDefinitionId,
					});
					state.currentGraph = graph;
					state.nodes = nodes;
					state.edges = edges;
					state.localChanges = [];
					state.pendingSyncChanges = [];
					state.isDirty = false;
					state.syncStatus = "saved";
					state.lastSyncedAt = Date.now();
					state.lastSyncError = null;
					state.isHistoricalVersion = true;
					state.loadedVersion = version;
					state.loadedGraphDefinitionId = graphDefinitionId;
					state.currentVersion = version;
					state.clipboard = null;
				}),

			exitHistoricalVersion: () =>
				set((state) => {
					state.isHistoricalVersion = false;
					state.loadedVersion = null;
					state.loadedGraphDefinitionId = null;
				}),

			setCurrentVersion: (version) =>
				set((state) => {
					state.currentVersion = version;
				}),

			clearGraph: () =>
				set((state) => {
					console.log(
						"[GraphStore] clearGraph called - clearing:",
						state.currentGraph?.name || "no graph",
					);
					state.currentGraph = null;
					state.nodes = [];
					state.edges = [];
					state.localChanges = [];
					state.pendingSyncChanges = [];
					state.isDirty = false;
					state.syncStatus = "saved";
					state.isHistoricalVersion = false;
					state.loadedVersion = null;
					state.loadedGraphDefinitionId = null;
					state.currentVersion = null;
					state.clipboard = null; // Clear clipboard
					console.log("[GraphStore] Graph cleared successfully");
				}),

			// Node Operations
			addNode: (node) => {
				set((state) => {
					state.nodes.push(node);
					state.localChanges.push({
						type: "ADD_NODE",
						timestamp: Date.now(),
						data: {
							node: node.data,
							tempId: node.id,
						},
					});
					state.isDirty = true;
					state.syncStatus = "unsaved";
				});
				triggerSync(); // Schedule debounced sync
			},

			updateNode: (nodeId, updates) => {
				set((state) => {
					const node = state.nodes.find((n) => n.id === nodeId);
					if (node && node.data) {
						Object.assign(node.data, updates);
						state.localChanges.push({
							type: "UPDATE_NODE",
							timestamp: Date.now(),
							data: { nodeId, updates },
						});
						state.isDirty = true;
						state.syncStatus = "unsaved";
					}
				});
				triggerSync();
			},

			deleteNode: (nodeId) => {
				set((state) => {
					state.nodes = state.nodes.filter((n) => n.id !== nodeId);
					state.edges = state.edges.filter(
						(e) => e.source !== nodeId && e.target !== nodeId,
					);
					state.localChanges.push({
						type: "DELETE_NODE",
						timestamp: Date.now(),
						data: { nodeId },
					});
					state.isDirty = true;
					state.syncStatus = "unsaved";
				});
				triggerSync();
			},

			// Clear all nodes and edges with proper change tracking
			// Use this for "reset" functionality - it tracks deletions for backend sync
			clearAllNodesAndEdges: () => {
				set((state) => {
					const timestamp = Date.now();

					// Track deletion of each node (skip START node as it's required)
					state.nodes.forEach((node) => {
						const nodeType =
							node.data?.type?.toUpperCase?.() || node.type?.toUpperCase?.();
						if (nodeType !== "START") {
							state.localChanges.push({
								type: "DELETE_NODE",
								timestamp,
								data: { nodeId: node.id },
							});
						}
					});

					// Track deletion of each connection
					state.edges.forEach((edge) => {
						state.localChanges.push({
							type: "DELETE_CONNECTION",
							timestamp,
							data: { sourceId: edge.source, targetId: edge.target },
						});
					});

					// Keep only START node
					state.nodes = state.nodes.filter((node) => {
						const nodeType =
							node.data?.type?.toUpperCase?.() || node.type?.toUpperCase?.();
						return nodeType === "START";
					});
					state.edges = [];
					state.isDirty = true;
					state.syncStatus = "unsaved";
				});
				triggerSync();
			},

			updateNodePosition: (nodeId, position) => {
				set((state) => {
					const node = state.nodes.find((n) => n.id === nodeId);
					if (node) {
						node.position = position;
						// Position updates are tracked separately for debouncing
						state.localChanges.push({
							type: "UPDATE_NODE_POSITION",
							timestamp: Date.now(),
							data: { nodeId, position },
						});
						state.isDirty = true;
						state.syncStatus = "unsaved";
					}
				});
				triggerSync();
			},

			setNodes: (nodesOrUpdater) =>
				set((state) => {
					if (typeof nodesOrUpdater === "function") {
						state.nodes = nodesOrUpdater(state.nodes);
					} else {
						state.nodes = nodesOrUpdater;
					}
					// PHASE 4 FIX: Note - this is used for ReactFlow internal updates
					// We don't track changes here because specific operations (add/update/delete) handle that
				}),

			// PHASE 2: Replace temp node ID with real ID from backend
			replaceNodeId: (tempId, realId) =>
				set((state) => {
					// Update the node ID
					const nodeIndex = state.nodes.findIndex((n) => n.id === tempId);
					if (nodeIndex >= 0) {
						state.nodes[nodeIndex].id = realId;
						if (state.nodes[nodeIndex].data) {
							state.nodes[nodeIndex].data.id = realId;
						}
					}

					// Update any edges that reference this node
					state.edges.forEach((edge) => {
						if (edge.source === tempId) {
							edge.source = realId;
						}
						if (edge.target === tempId) {
							edge.target = realId;
						}
					});

					// Update any pending changes that reference this temp ID
					state.localChanges.forEach((change) => {
						if (change.type === "ADD_NODE" && change.data.tempId === tempId) {
							change.data.tempId = realId;
						} else if (
							change.type === "UPDATE_NODE" &&
							change.data.nodeId === tempId
						) {
							change.data.nodeId = realId;
						} else if (
							change.type === "UPDATE_NODE_POSITION" &&
							change.data.nodeId === tempId
						) {
							change.data.nodeId = realId;
						} else if (change.type === "ADD_CONNECTION") {
							if (change.data.sourceId === tempId) {
								change.data.sourceId = realId;
							}
							if (change.data.targetId === tempId) {
								change.data.targetId = realId;
							}
						} else if (change.type === "DELETE_CONNECTION") {
							if (change.data.sourceId === tempId) {
								change.data.sourceId = realId;
							}
							if (change.data.targetId === tempId) {
								change.data.targetId = realId;
							}
						}
					});

					console.log(
						`[GraphStore] Replaced temp ID ${tempId} with real ID ${realId}`,
					);
				}),

			// Remove ADD_NODE change after direct API creation succeeds
			// This prevents the sync service from creating a duplicate node
			removeNodeChange: (nodeId: string) =>
				set((state) => {
					const initialLength = state.localChanges.length;
					state.localChanges = state.localChanges.filter(
						(change) =>
							!(
								change.type === "ADD_NODE" &&
								(change.data.tempId === nodeId || change.data.node?.id === nodeId)
							),
					);
					const removed = initialLength - state.localChanges.length;
					if (removed > 0) {
						console.log(
							`[GraphStore] Removed ${removed} ADD_NODE change(s) for node ${nodeId}`,
						);
					}
				}),

			// PHASE 6: Batch update node execution status
			// Useful for updating multiple nodes during execution without triggering multiple re-renders
			batchUpdateNodeStatus: (updates) =>
				set((state) => {
					console.log(
						`[GraphStore] Batch updating ${updates.length} node statuses`,
					);
					updates.forEach(({ nodeId, status, duration }) => {
						const node = state.nodes.find((n) => n.id === nodeId);
						if (node && node.data) {
							node.data.executionStatus = status;
							if (duration !== undefined) {
								node.data.executionDuration = duration;
							}
						}
					});
					// Don't trigger sync - execution status is ephemeral
				}),

			// Batch update node positions for multi-node drag operations
			// Single store update instead of N updates when dragging parent + children
			batchUpdateNodePositions: (updates) => {
				set((state) => {
					const timestamp = Date.now();
					updates.forEach(({ nodeId, position }) => {
						const node = state.nodes.find((n) => n.id === nodeId);
						if (node) {
							node.position = position;
							state.localChanges.push({
								type: "UPDATE_NODE_POSITION",
								timestamp,
								data: { nodeId, position },
							});
						}
					});
					state.isDirty = true;
					state.syncStatus = "unsaved";
				});
				triggerSync();
			},

			// Connection Operations
			addConnection: (edge) => {
				console.log("[GraphStore] addConnection called:", {
					edgeId: edge.id,
					source: edge.source,
					target: edge.target,
					sourceHandle: edge.sourceHandle || "none",
					targetHandle: edge.targetHandle || "none",
					currentEdgeCount: get().edges.length,
				});

				set((state) => {
					state.edges.push(edge);
					state.localChanges.push({
						type: "ADD_CONNECTION",
						timestamp: Date.now(),
						data: {
							sourceId: edge.source,
							targetId: edge.target,
							sourceHandle: edge.sourceHandle || undefined,
							targetHandle: edge.targetHandle || undefined,
							label: typeof edge.label === "string" ? edge.label : undefined,
							connectionType: edge.data?.connection_type || "workflow",
							tempId: edge.id,
						},
					});
					state.isDirty = true;
					state.syncStatus = "unsaved";
				});

				console.log("[GraphStore] After addConnection:", {
					newEdgeCount: get().edges.length,
					allEdges: get().edges.map((e) => ({
						id: e.id,
						source: e.source,
						target: e.target,
						sourceHandle: e.sourceHandle || "none",
					})),
				});

				triggerSync();
			},

			deleteConnection: (sourceId, targetId) => {
				set((state) => {
					state.edges = state.edges.filter(
						(e) => !(e.source === sourceId && e.target === targetId),
					);
					state.localChanges.push({
						type: "DELETE_CONNECTION",
						timestamp: Date.now(),
						data: { sourceId, targetId },
					});
					state.isDirty = true;
					state.syncStatus = "unsaved";
				});
				triggerSync();
			},

			setEdges: (edgesOrUpdater) =>
				set((state) => {
					if (typeof edgesOrUpdater === "function") {
						state.edges = edgesOrUpdater(state.edges);
					} else {
						state.edges = edgesOrUpdater;
					}
					// PHASE 4 FIX: Note - this is used for ReactFlow internal updates
					// We don't track changes here because specific operations (add/delete) handle that
				}),

			// PHASE 2: Replace temp edge ID with real ID from backend
			replaceEdgeId: (tempId, realId) =>
				set((state) => {
					// Update the edge ID
					const edgeIndex = state.edges.findIndex((e) => e.id === tempId);
					if (edgeIndex >= 0) {
						state.edges[edgeIndex].id = realId;
					}

					// Update any pending changes that reference this temp edge ID
					state.localChanges.forEach((change) => {
						if (
							change.type === "ADD_CONNECTION" &&
							change.data.tempId === tempId
						) {
							change.data.tempId = realId;
						}
					});

					console.log(
						`[GraphStore] Replaced temp edge ID ${tempId} with real ID ${realId}`,
					);
				}),

			// Sync Operations
			markAsSyncing: () =>
				set((state) => {
					state.syncStatus = "saving";
					state.isSyncing = true;
					// Move current changes to pending sync
					state.pendingSyncChanges = [...state.localChanges];
				}),

			markAsSynced: () =>
				set((state) => {
					state.syncStatus = "saved";
					state.lastSyncedAt = Date.now();
					state.isSyncing = false;
					state.lastSyncError = null;

					// PHASE 5: Increment version on successful sync
					state.graphVersion += 1;
					state.lastServerVersion = state.graphVersion;

					// PHASE 1 FIX: Only clear the changes that were in pendingSyncChanges
					// Keep any new changes that arrived during sync
					const syncedChangeKeys = new Set(
						state.pendingSyncChanges.map((c) => `${c.type}:${c.timestamp}`),
					);
					state.localChanges = state.localChanges.filter(
						(c) => !syncedChangeKeys.has(`${c.type}:${c.timestamp}`),
					);
					state.pendingSyncChanges = [];

					// Only mark as not dirty if no local changes remain
					state.isDirty = state.localChanges.length > 0;
					if (state.isDirty) {
						state.syncStatus = "unsaved";
					}
				}),

			markAsSyncError: (error) =>
				set((state) => {
					state.syncStatus = "error";
					state.lastSyncError = error;
					state.isSyncing = false;
					// Restore pending changes back to local changes for retry
					state.localChanges = [
						...state.pendingSyncChanges,
						...state.localChanges,
					];
					state.pendingSyncChanges = [];
				}),

			markAsOffline: () =>
				set((state) => {
					state.syncStatus = "offline";
					state.isSyncing = false;
				}),

			getChangesSinceLastSync: () => get().localChanges,

			getPendingSyncChanges: () => get().pendingSyncChanges,

			clearSyncedChanges: () =>
				set((state) => {
					state.localChanges = [];
					state.pendingSyncChanges = [];
				}),

			// PHASE 5: Conflict Resolution
			detectConflict: (serverVersion, serverNodes, serverEdges) => {
				const state = get();

				// No conflict if we're in sync with server
				if (state.lastServerVersion === serverVersion) {
					return false;
				}

				// Conflict detected: server has changed since our last sync
				console.log("[GraphStore] ⚠️ Conflict detected!", {
					localVersion: state.graphVersion,
					serverVersion,
					localChanges: state.localChanges.length,
				});

				set((draft) => {
					draft.hasConflict = true;
					draft.conflictData = {
						localVersion: state.graphVersion,
						serverVersion,
						localChanges: [...state.localChanges],
						serverState: {
							nodes: serverNodes,
							edges: serverEdges,
						},
					};
				});

				return true;
			},

			resolveConflict: (strategy) =>
				set((state) => {
					if (!state.conflictData) {
						console.warn("[GraphStore] No conflict to resolve");
						return;
					}

					console.log(
						`[GraphStore] Resolving conflict with strategy: ${strategy}`,
					);

					switch (strategy) {
						case "keep-local":
							// Keep local changes, discard server state
							// Force sync will push local changes to server
							console.log("[GraphStore] Keeping local changes");
							state.lastServerVersion = state.conflictData.serverVersion;
							break;

						case "use-server":
							// Discard local changes, use server state
							console.log("[GraphStore] Using server state");
							if (state.conflictData.serverState) {
								state.nodes = state.conflictData.serverState.nodes;
								state.edges = state.conflictData.serverState.edges;
								state.localChanges = [];
								state.isDirty = false;
								state.graphVersion = state.conflictData.serverVersion;
								state.lastServerVersion = state.conflictData.serverVersion;
							}
							break;

						case "merge":
							// Attempt automatic merge
							console.log("[GraphStore] Attempting merge");
							// Simple merge: apply local changes on top of server state
							if (state.conflictData.serverState) {
								// Start with server state
								state.nodes = [...state.conflictData.serverState.nodes];
								state.edges = [...state.conflictData.serverState.edges];

								// Apply local changes that don't conflict
								// For now, just log - full merge logic would be complex
								console.log(
									"[GraphStore] Merge: keeping local changes, may need manual review",
								);
								state.lastServerVersion = state.conflictData.serverVersion;
							}
							break;
					}

					// Clear conflict
					state.hasConflict = false;
					state.conflictData = null;
				}),

			clearConflict: () =>
				set((state) => {
					state.hasConflict = false;
					state.conflictData = null;
				}),

			// Clipboard Operations
			copySelectedNodes: (selectedNodeIds) => {
				set((state) => {
					// Filter out START and END nodes - they cannot be copied
					const nodesToCopy = state.nodes.filter((node) => {
						const nodeType =
							node.data?.type?.toUpperCase?.() || node.type?.toUpperCase?.();
						return (
							selectedNodeIds.includes(node.id) &&
							nodeType !== "START" &&
							nodeType !== "END"
						);
					});

					if (nodesToCopy.length === 0) {
						console.warn(
							"[GraphStore] No valid nodes to copy (START/END excluded)",
						);
						return;
					}

					// Find edges that connect ONLY copied nodes (internal edges)
					const copiedNodeIds = new Set(nodesToCopy.map((n) => n.id));
					const edgesToCopy = state.edges.filter(
						(edge) =>
							copiedNodeIds.has(edge.source) && copiedNodeIds.has(edge.target),
					);

					// Calculate bounding box origin for offset reference
					const minX = Math.min(...nodesToCopy.map((n) => n.position.x));
					const minY = Math.min(...nodesToCopy.map((n) => n.position.y));

					// Deep copy nodes and edges to avoid reference issues
					// Using JSON parse/stringify for true deep clone of nested configs
					state.clipboard = {
						nodes: nodesToCopy.map((n) => ({
							...n,
							data: JSON.parse(JSON.stringify(n.data)),
							position: { ...n.position },
						})),
						edges: edgesToCopy.map((e) => ({
							...e,
							data: e.data ? JSON.parse(JSON.stringify(e.data)) : undefined,
						})),
						copyOffset: { x: minX, y: minY },
					};

					console.log(
						`[GraphStore] Copied ${nodesToCopy.length} nodes, ${edgesToCopy.length} edges`,
					);
				});
			},

			pasteNodes: (offset = { x: 100, y: 100 }) => {
				const state = get();
				if (!state.clipboard || state.clipboard.nodes.length === 0) {
					console.warn("[GraphStore] Nothing to paste");
					return { nodeIdMap: new Map(), newNodes: [], newEdges: [] };
				}

				const nodeIdMap = new Map<string, string>();
				const timestamp = Date.now();
				const newNodes: Node[] = [];
				const newEdges: Edge[] = [];

				// Create new nodes with new IDs and offset positions
				// Deep clone data to ensure each paste creates independent copies
				state.clipboard.nodes.forEach((node, index) => {
					const newId = `paste-${timestamp}-${index}-${Math.random().toString(36).substr(2, 9)}`;
					nodeIdMap.set(node.id, newId);

					const clonedData = JSON.parse(JSON.stringify(node.data));
					const newNode: Node = {
						...node,
						id: newId,
						position: {
							x: node.position.x - state.clipboard!.copyOffset.x + offset.x,
							y: node.position.y - state.clipboard!.copyOffset.y + offset.y,
						},
						selected: true, // Select pasted nodes
						data: {
							...clonedData,
							id: newId,
							name: `${clonedData?.name || "Node"} (copy)`,
						},
					};
					newNodes.push(newNode);
				});

				// Create new edges with updated source/target IDs
				state.clipboard.edges.forEach((edge, index) => {
					const newSource = nodeIdMap.get(edge.source);
					const newTarget = nodeIdMap.get(edge.target);

					if (newSource && newTarget) {
						const newEdge: Edge = {
							...edge,
							id: `paste-edge-${timestamp}-${index}-${Math.random().toString(36).substr(2, 9)}`,
							source: newSource,
							target: newTarget,
						};
						newEdges.push(newEdge);
					}
				});

				// Add to store
				set((draft) => {
					// Deselect existing nodes
					draft.nodes.forEach((n) => {
						n.selected = false;
					});

					// Add new nodes and track changes
					newNodes.forEach((node) => {
						draft.nodes.push(node);
						draft.localChanges.push({
							type: "ADD_NODE",
							timestamp: Date.now(),
							data: { node: normalizeNodeDataForBackend(node.data), tempId: node.id },
						});
					});

					// Add new edges and track changes
					newEdges.forEach((edge) => {
						draft.edges.push(edge);
						draft.localChanges.push({
							type: "ADD_CONNECTION",
							timestamp: Date.now(),
							data: {
								sourceId: edge.source,
								targetId: edge.target,
								sourceHandle: edge.sourceHandle || undefined,
								targetHandle: edge.targetHandle || undefined,
								tempId: edge.id,
							},
						});
					});

					draft.isDirty = true;
					draft.syncStatus = "unsaved";
				});

				// Trigger sync to backend
				triggerSync();

				console.log(
					`[GraphStore] Pasted ${newNodes.length} nodes, ${newEdges.length} edges`,
				);
				return { nodeIdMap, newNodes, newEdges };
			},

			clearClipboard: () =>
				set((state) => {
					state.clipboard = null;
				}),

			// Helpers
			setLoading: (loading) =>
				set((state) => {
					state.isLoading = loading;
				}),

			setIsDirty: (dirty) =>
				set((state) => {
					state.isDirty = dirty;
				}),

			// Apply changes from undo/redo operations
			// Unlike setNodes/setEdges, this DOES track changes for sync
			applyUndoRedoChanges: (changes) => {
				if (changes.length === 0) {
					return;
				}

				set((state) => {
					state.localChanges.push(...changes);
					state.isDirty = true;
					state.syncStatus = "unsaved";
					console.log(
						`[GraphStore] Applied ${changes.length} undo/redo change(s) for sync`,
					);
				});

				// Trigger debounced sync
				triggerSync();
			},
		})),
		{
			name: "agenticstudio-graph-storage",
			partialize: (state) => ({
				// Only persist essential data to localStorage
				currentGraph: state.currentGraph,
				nodes: state.nodes, // Persist nodes for page refresh
				edges: state.edges, // Persist edges for page refresh
				lastSyncedAt: state.lastSyncedAt,
				// Persist unsaved changes for recovery
				localChanges: state.localChanges,
			}),
			onRehydrateStorage: () => (state) => {
				if (state) {
					console.log("[GraphStore] Hydrated from localStorage:", {
						hasGraph: !!state.currentGraph,
						graphName: state.currentGraph?.name,
						nodeCount: state.nodes?.length || 0,
						edgeCount: state.edges?.length || 0,
						staleChangesCleared: state.localChanges?.length || 0,
					});
					// Clear stale localChanges from previous session.
					// The API load will provide authoritative state from the backend.
					// Keeping stale changes risks syncing outdated/temp-ID changes.
					state.localChanges = [];
					state.pendingSyncChanges = [];
					state.isDirty = false;
					state.syncStatus = "saved";
				} else {
					console.log("[GraphStore] No persisted state found in localStorage");
				}
			},
		},
	),
);
