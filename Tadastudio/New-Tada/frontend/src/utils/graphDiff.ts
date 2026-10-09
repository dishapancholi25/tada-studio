/**
 * Utility for computing diffs between graph states.
 * Used by undo/redo to generate change entries for database sync.
 */

import type { Edge, Node } from "reactflow";
import type { TypedGraphChange } from "@/types/graphChanges";

interface DiffResult {
	changes: TypedGraphChange[];
	summary: {
		nodesAdded: number;
		nodesDeleted: number;
		nodesUpdated: number;
		positionsUpdated: number;
		connectionsAdded: number;
		connectionsDeleted: number;
	};
}

/**
 * Normalizes React Flow node data to backend-expected format.
 * Maps frontend-specific field names to backend field names.
 */
export function normalizeNodeDataForBackend(nodeData: Record<string, unknown>): Record<string, unknown> {
	if (!nodeData) return nodeData;

	const normalized = { ...nodeData };

	// prompt -> prompt_template (backend uses prompt_template)
	if ("prompt" in normalized) {
		normalized.prompt_template = normalized.prompt;
		delete normalized.prompt;
	}

	// id -> uniq_id (backend uses uniq_id)
	if ("id" in normalized) {
		normalized.uniq_id = normalized.id;
		delete normalized.id;
	}

	// Remove frontend-only ephemeral fields
	delete normalized.isOrchestrator; // Derived from agent_config
	delete normalized.executionStatus; // Ephemeral execution state
	delete normalized.executionDuration; // Ephemeral execution state

	return normalized;
}

/**
 * Compares two graph states and generates the appropriate TypedGraphChange entries.
 * Changes are ordered: deletes first, then adds, then updates (to avoid constraint violations).
 *
 * @param beforeNodes - Nodes before the change (current state)
 * @param beforeEdges - Edges before the change (current state)
 * @param afterNodes - Nodes after the change (target state)
 * @param afterEdges - Edges after the change (target state)
 * @returns DiffResult with changes and summary
 */
export function diffGraphStates(
	beforeNodes: Node[],
	beforeEdges: Edge[],
	afterNodes: Node[],
	afterEdges: Edge[],
): DiffResult {
	const changes: TypedGraphChange[] = [];
	const timestamp = Date.now();

	// Create lookup maps
	const beforeNodeMap = new Map(beforeNodes.map((n) => [n.id, n]));
	const afterNodeMap = new Map(afterNodes.map((n) => [n.id, n]));

	// For edges, use source-target as key since that's how connections are identified
	const getEdgeKey = (e: Edge) => `${e.source}:${e.target}`;
	const beforeEdgeMap = new Map(beforeEdges.map((e) => [getEdgeKey(e), e]));
	const afterEdgeMap = new Map(afterEdges.map((e) => [getEdgeKey(e), e]));

	// Track counts for summary
	let nodesDeleted = 0;
	let nodesAdded = 0;
	let nodesUpdated = 0;
	let positionsUpdated = 0;
	let connectionsDeleted = 0;
	let connectionsAdded = 0;

	// --- DELETES FIRST (to avoid foreign key issues) ---

	// Find deleted connections (in before but not in after)
	for (const [edgeKey, edge] of beforeEdgeMap) {
		if (!afterEdgeMap.has(edgeKey)) {
			changes.push({
				type: "DELETE_CONNECTION",
				timestamp,
				data: { sourceId: edge.source, targetId: edge.target },
			});
			connectionsDeleted++;
		}
	}

	// Find deleted nodes (in before but not in after)
	for (const [nodeId] of beforeNodeMap) {
		if (!afterNodeMap.has(nodeId)) {
			changes.push({
				type: "DELETE_NODE",
				timestamp,
				data: { nodeId },
			});
			nodesDeleted++;
		}
	}

	// --- ADDS SECOND ---

	// Find added nodes (in after but not in before)
	for (const [nodeId, node] of afterNodeMap) {
		if (!beforeNodeMap.has(nodeId)) {
			changes.push({
				type: "ADD_NODE",
				timestamp,
				data: {
					node: normalizeNodeDataForBackend(node.data as Record<string, unknown>),
					tempId: nodeId,
				},
			});
			nodesAdded++;
		}
	}

	// Find added connections (in after but not in before)
	for (const [edgeKey, edge] of afterEdgeMap) {
		if (!beforeEdgeMap.has(edgeKey)) {
			changes.push({
				type: "ADD_CONNECTION",
				timestamp,
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
			connectionsAdded++;
		}
	}

	// --- UPDATES LAST ---

	// Find updated nodes (in both, but data or position changed)
	for (const [nodeId, afterNode] of afterNodeMap) {
		const beforeNode = beforeNodeMap.get(nodeId);
		if (beforeNode) {
			// Check position change
			const positionChanged =
				beforeNode.position.x !== afterNode.position.x ||
				beforeNode.position.y !== afterNode.position.y;

			if (positionChanged) {
				changes.push({
					type: "UPDATE_NODE_POSITION",
					timestamp,
					data: { nodeId, position: afterNode.position },
				});
				positionsUpdated++;
			}

			// Check data changes (deep comparison via JSON stringify)
			// Skip if both are null/undefined
			const beforeData = beforeNode.data;
			const afterData = afterNode.data;

			if (beforeData || afterData) {
				const beforeJson = JSON.stringify(beforeData ?? {});
				const afterJson = JSON.stringify(afterData ?? {});

				if (beforeJson !== afterJson) {
					changes.push({
						type: "UPDATE_NODE",
						timestamp,
						data: {
							nodeId,
							updates: normalizeNodeDataForBackend(afterData as Record<string, unknown>),
						},
					});
					nodesUpdated++;
				}
			}
		}
	}

	return {
		changes,
		summary: {
			nodesAdded,
			nodesDeleted,
			nodesUpdated,
			positionsUpdated,
			connectionsAdded,
			connectionsDeleted,
		},
	};
}
