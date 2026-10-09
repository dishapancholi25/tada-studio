import type { Edge } from "reactflow";

/**
 * Get all descendant node IDs for a given node.
 * @param nodeId The ID of the starting node.
 * @param edges The list of all edges in the graph.
 * @returns A Set of descendant node IDs.
 */
export function getDescendants(nodeId: string, edges: Edge[]): Set<string> {
	const descendants = new Set<string>();
	const queue = [nodeId];
	const visited = new Set<string>();

	while (queue.length > 0) {
		const current = queue.shift()!;
		if (visited.has(current)) continue;
		visited.add(current);

		const outgoingEdges = edges.filter((edge) => edge.source === current);
		for (const edge of outgoingEdges) {
			if (!descendants.has(edge.target)) {
				descendants.add(edge.target);
				queue.push(edge.target);
			}
		}
	}

	return descendants;
}

/**
 * Get all ancestor node IDs for a given node.
 * @param nodeId The ID of the starting node.
 * @param edges The list of all edges in the graph.
 * @returns A Set of ancestor node IDs.
 */
export function getAncestors(nodeId: string, edges: Edge[]): Set<string> {
	const ancestors = new Set<string>();
	const queue = [nodeId];
	const visited = new Set<string>();

	while (queue.length > 0) {
		const current = queue.shift()!;
		if (visited.has(current)) continue;
		visited.add(current);

		const incomingEdges = edges.filter((edge) => edge.target === current);
		for (const edge of incomingEdges) {
			if (!ancestors.has(edge.source)) {
				ancestors.add(edge.source);
				queue.push(edge.source);
			}
		}
	}

	return ancestors;
}
