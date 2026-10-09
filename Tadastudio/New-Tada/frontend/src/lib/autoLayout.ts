import dagre from "dagre";
import type { Edge, Node } from "reactflow";

export type LayoutDirection = "TB" | "BT" | "LR" | "RL";

export interface LayoutOptions {
	direction?: LayoutDirection;
	nodeWidth?: number;
	nodeHeight?: number;
	nodeSeparation?: number;
	rankSeparation?: number;
}

interface NodePosition {
	id: string;
	x: number;
	y: number;
	width: number;
	height: number;
	layer: number;
	type: string;
}

interface ChildCluster {
	parentId: string;
	children: NodePosition[];
	minX: number;
	maxX: number;
	width: number;
}

/**
 * Clean hierarchical layout algorithm
 * - Nodes arranged in horizontal layers by hierarchy depth
 * - Children positioned directly below parents
 * - Children grouped by type (tools, sub-agents, workflows)
 * - No overlapping clusters
 */
export function getLayoutedElements(
	nodes: Node[],
	edges: Edge[],
	options: LayoutOptions = {},
): { nodes: Node[]; edges: Edge[] } {
	const {
		direction = "LR",
		nodeWidth = 250,
		nodeHeight = 150,
		nodeSeparation = 150,
		rankSeparation = 150,
	} = options;

	const LAYER_VERTICAL_SPACING = 400; // Vertical space between layers
	const NODE_HORIZONTAL_SPACING = 150; // Horizontal space between nodes (agents, workflows)
	const TOOL_HORIZONTAL_SPACING = 30; // Horizontal space between tools (very tight)
	const CLUSTER_PADDING = 30; // Padding around child clusters
	const CHILD_GROUP_SPACING = 50; // Space between different child types

	// Step 1: Identify parent-child relationships
	const delegationEdges = edges.filter(
		(e) => e.data?.connection_type === "delegation",
	);
	const toolEdges = edges.filter((e) => e.data?.connection_type === "tool");

	// Build node map first
	const nodeMap = new Map<string, Node>();
	nodes.forEach((node) => nodeMap.set(node.id, node));

	// Identify sub-workflow nodes by type (handles both 'subworkflow' and 'subWorkflowNode')
	const subworkflowNodeIds = new Set(
		nodes
			.filter((n) => n.type?.toLowerCase().includes("subworkflow"))
			.map((n) => n.id),
	);

	// Workflow edges TO or FROM sub-workflows should be treated as parent-child relationships
	const subworkflowRelatedEdges = edges.filter((edge) => {
		const isWorkflowEdge =
			edge.data?.connection_type !== "delegation" &&
			edge.data?.connection_type !== "tool";
		if (!isWorkflowEdge) return false;

		// Include if target is a sub-workflow (parent -> sub-workflow)
		const targetIsSubworkflow = subworkflowNodeIds.has(edge.target);
		// Include if source is a sub-workflow (sub-workflow -> child agent)
		const sourceIsSubworkflow = subworkflowNodeIds.has(edge.source);

		if (targetIsSubworkflow || sourceIsSubworkflow) {
			console.log("Subworkflow edge:", {
				source: edge.source,
				target: edge.target,
				connectionType: edge.data?.connection_type,
				targetIsSubworkflow,
				sourceIsSubworkflow,
			});
		}

		return targetIsSubworkflow || sourceIsSubworkflow;
	});

	console.log("Sub-workflow node IDs:", Array.from(subworkflowNodeIds));
	console.log("Delegation edges:", delegationEdges.length);
	console.log("Tool edges:", toolEdges.length);
	console.log("Subworkflow-related edges:", subworkflowRelatedEdges.length);

	const childEdges = [
		...delegationEdges,
		...toolEdges,
		...subworkflowRelatedEdges,
	];

	const childNodeIds = new Set(childEdges.map((e) => e.target));
	console.log("Child node IDs:", Array.from(childNodeIds));

	const toolNodeIds = new Set(toolEdges.map((e) => e.target)); // Identify tool nodes specifically
	const parentToChildren = new Map<string, string[]>();

	childEdges.forEach((edge) => {
		const children = parentToChildren.get(edge.source) || [];
		children.push(edge.target);
		parentToChildren.set(edge.source, children);
	});

	// Step 2: Build hierarchy - assign layer depth to each node
	const nodeLayerMap = new Map<string, number>();

	function assignLayer(nodeId: string, visited = new Set<string>()): number {
		if (nodeLayerMap.has(nodeId)) {
			return nodeLayerMap.get(nodeId)!;
		}

		if (visited.has(nodeId)) {
			return 0; // Circular reference, break cycle
		}

		visited.add(nodeId);

		// Check if this node is a child of another node
		const parentEdge = childEdges.find((e) => e.target === nodeId);

		if (!parentEdge) {
			// Top-level node
			nodeLayerMap.set(nodeId, 0);
			return 0;
		}

		// Layer = parent's layer + 1
		const parentLayer = assignLayer(parentEdge.source, visited);
		const layer = parentLayer + 1;
		nodeLayerMap.set(nodeId, layer);
		return layer;
	}

	// Assign layers to all nodes
	nodes.forEach((node) => assignLayer(node.id));

	// Debug: Log layer assignments for sub-workflows
	console.log("Layer assignments:");
	nodes.forEach((node) => {
		const layer = nodeLayerMap.get(node.id);
		if (node.type?.toLowerCase() === "subworkflow" || layer === 0) {
			console.log(`  ${node.id} (${node.type}): layer ${layer}`);
		}
	});

	// Step 3: Layout top-level nodes (layer 0) using dagre
	const layer0Nodes = nodes.filter((node) => nodeLayerMap.get(node.id) === 0);
	console.log(
		"Layer 0 nodes:",
		layer0Nodes.map((n) => `${n.id} (${n.type})`),
	);

	const workflowEdges = edges.filter(
		(e) =>
			e.data?.connection_type !== "delegation" &&
			e.data?.connection_type !== "tool",
	);

	const dagreGraph = new dagre.graphlib.Graph();
	dagreGraph.setDefaultEdgeLabel(() => ({}));
	dagreGraph.setGraph({
		rankdir: direction,
		nodesep: nodeSeparation,
		ranksep: rankSeparation,
		marginx: 50,
		marginy: 50,
	});

	// Add layer 0 nodes to dagre
	layer0Nodes.forEach((node) => {
		const width = node.width || nodeWidth;
		const height = node.height || nodeHeight;
		dagreGraph.setNode(node.id, { width, height });
	});

	// Add workflow edges
	workflowEdges.forEach((edge) => {
		dagreGraph.setEdge(edge.source, edge.target);
	});

	// Calculate dagre layout
	dagre.layout(dagreGraph);

	// Step 4: Create initial positions for layer 0 nodes
	const positions = new Map<string, NodePosition>();

	layer0Nodes.forEach((node) => {
		const nodeWithPosition = dagreGraph.node(node.id);
		const width = node.width || nodeWidth;
		const height = node.height || nodeHeight;
		const nodeType =
			(node.type as string) || (node.data as any)?.type || "unknown";

		positions.set(node.id, {
			id: node.id,
			x: nodeWithPosition.x - width / 2,
			y: 100, // All layer 0 nodes at Y=100
			width,
			height,
			layer: 0,
			type: nodeType,
		});
	});

	// Step 5: Layout children recursively for each layer
	function layoutChildren(parentId: string, parentLayer: number) {
		const childIds = parentToChildren.get(parentId) || [];
		if (childIds.length === 0) return;

		const parent = positions.get(parentId)!;
		const childLayer = parentLayer + 1;
		const childY = 100 + childLayer * LAYER_VERTICAL_SPACING;

		// Group children by type
		const childrenByType = new Map<string, Node[]>();

		childIds.forEach((childId) => {
			const childNode = nodeMap.get(childId);
			if (!childNode) return;

			const childType =
				(childNode.type as string) ||
				(childNode.data as any)?.type ||
				"unknown";
			const typeGroup = childrenByType.get(childType) || [];
			typeGroup.push(childNode);
			childrenByType.set(childType, typeGroup);
		});

		// Sort types for consistent ordering: tools, sub-agents, workflows
		const typeOrder = ["TOOL", "AGENT", "WORKFLOW", "SUBWORKFLOW"];
		const sortedTypes = Array.from(childrenByType.keys()).sort((a, b) => {
			const aIdx = typeOrder.indexOf(a.toUpperCase());
			const bIdx = typeOrder.indexOf(b.toUpperCase());
			return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx);
		});

		// Calculate total width needed for all children
		let totalWidth = 0;
		const typeWidths: number[] = [];

		sortedTypes.forEach((type) => {
			const typeChildren = childrenByType.get(type)!;

			// Check if any child in this group is a tool node (by edge type, not node type)
			const isToolGroup = typeChildren.some((node) => toolNodeIds.has(node.id));
			const spacing = isToolGroup
				? TOOL_HORIZONTAL_SPACING
				: NODE_HORIZONTAL_SPACING;

			const typeWidth = typeChildren.reduce((sum, node) => {
				return sum + (node.width || nodeWidth) + spacing;
			}, 0);
			typeWidths.push(typeWidth);
			totalWidth += typeWidth + CHILD_GROUP_SPACING;
		});

		// Position children centered below parent
		const parentCenterX = parent.x + parent.width / 2;
		let currentX = parentCenterX - totalWidth / 2;

		let typeIndex = 0;
		sortedTypes.forEach((type) => {
			const typeChildren = childrenByType.get(type)!;

			// Check if any child in this group is a tool node (by edge type, not node type)
			const isToolGroup = typeChildren.some((node) => toolNodeIds.has(node.id));
			const spacing = isToolGroup
				? TOOL_HORIZONTAL_SPACING
				: NODE_HORIZONTAL_SPACING;

			typeChildren.forEach((childNode) => {
				const width = childNode.width || nodeWidth;
				const height = childNode.height || nodeHeight;

				positions.set(childNode.id, {
					id: childNode.id,
					x: currentX,
					y: childY,
					width,
					height,
					layer: childLayer,
					type: type,
				});

				currentX += width + spacing;

				// Recursively layout this child's children
				layoutChildren(childNode.id, childLayer);
			});

			currentX += CHILD_GROUP_SPACING;
			typeIndex++;
		});
	}

	// Layout children for all layer 0 nodes
	layer0Nodes.forEach((node) => layoutChildren(node.id, 0));

	// Step 6: Calculate cluster bounds including all descendants
	const clusterBounds = new Map<string, ChildCluster>();

	function calculateClusterBounds(
		parentId: string,
	): { minX: number; maxX: number } | null {
		const parent = positions.get(parentId);
		if (!parent) return null;

		const childIds = parentToChildren.get(parentId) || [];

		// If no children, cluster is just the parent node
		if (childIds.length === 0) {
			return {
				minX: parent.x,
				maxX: parent.x + parent.width,
			};
		}

		// Collect all descendants recursively
		const allDescendants: NodePosition[] = [];

		function collectDescendants(nodeId: string) {
			const children = parentToChildren.get(nodeId) || [];
			children.forEach((childId) => {
				const childPos = positions.get(childId);
				if (childPos) {
					allDescendants.push(childPos);
					collectDescendants(childId); // Recurse for grandchildren
				}
			});
		}

		collectDescendants(parentId);

		if (allDescendants.length === 0) {
			return {
				minX: parent.x,
				maxX: parent.x + parent.width,
			};
		}

		// Calculate bounds including parent and all descendants
		const minX = Math.min(parent.x, ...allDescendants.map((c) => c.x));
		const maxX = Math.max(
			parent.x + parent.width,
			...allDescendants.map((c) => c.x + c.width),
		);

		clusterBounds.set(parentId, {
			parentId,
			children: allDescendants,
			minX: minX - CLUSTER_PADDING,
			maxX: maxX + CLUSTER_PADDING,
			width: maxX - minX + 2 * CLUSTER_PADDING,
		});

		return { minX: minX - CLUSTER_PADDING, maxX: maxX + CLUSTER_PADDING };
	}

	// Step 7: Adjust parent positions to prevent cluster overlaps
	const layer0Array = Array.from(positions.values()).filter(
		(p) => p.layer === 0,
	);
	layer0Array.sort((a, b) => a.x - b.x);

	// Calculate bounds for all parents
	layer0Array.forEach((parent) => calculateClusterBounds(parent.id));

	// Adjust positions to prevent overlaps
	for (let i = 0; i < layer0Array.length - 1; i++) {
		const current = layer0Array[i];
		const next = layer0Array[i + 1];

		const currentBounds = calculateClusterBounds(current.id);
		const nextBounds = calculateClusterBounds(next.id);

		if (!currentBounds || !nextBounds) continue;

		// Calculate gap between clusters
		const gap = nextBounds.minX - currentBounds.maxX;

		if (gap < 0) {
			// Clusters overlap - shift next parent (and all following) right
			const shiftAmount = -gap + CLUSTER_PADDING;

			function shiftNode(nodeId: string, shift: number) {
				const pos = positions.get(nodeId);
				if (pos) {
					pos.x += shift;

					// Shift all children recursively
					const children = parentToChildren.get(nodeId) || [];
					children.forEach((childId) => shiftNode(childId, shift));
				}
			}

			// Shift this parent and all following parents
			for (let j = i + 1; j < layer0Array.length; j++) {
				shiftNode(layer0Array[j].id, shiftAmount);
			}

			// Recalculate bounds after shift
			calculateClusterBounds(next.id);
		}
	}

	// Step 7: Convert positions to React Flow format
	const layoutedNodes = nodes.map((node) => {
		const pos = positions.get(node.id);
		if (!pos) {
			// Fallback for any missing nodes
			return {
				...node,
				position: { x: 0, y: 0 },
			};
		}

		return {
			...node,
			position: { x: pos.x, y: pos.y },
		};
	});

	return {
		nodes: layoutedNodes,
		edges,
	};
}
