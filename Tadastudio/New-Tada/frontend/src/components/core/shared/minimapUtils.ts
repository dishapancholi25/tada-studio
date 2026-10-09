/**
 * Minimap Utilities
 *
 * Centralized color mapping and utilities for the custom minimap component.
 * Provides consistent node and edge coloring based on type.
 */

import type { Edge, Node } from "reactflow";
import { nodeColors } from "@/components/nodes/shared/nodeStyles";

/**
 * Convert RGB string (e.g., "13, 169, 49") to hex (e.g., "#0DA931")
 */
const rgbToHex = (rgb: string): string => {
	const parts = rgb.split(",").map((n) => parseInt(n.trim(), 10));
	if (parts.length !== 3 || parts.some(isNaN)) {
		return "#6b7280"; // fallback gray
	}
	const [r, g, b] = parts;
	return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
};

/**
 * Pre-computed hex colors from nodeColors
 */
export const minimapColors = {
	green: rgbToHex(nodeColors.green), // #0DA931
	red: rgbToHex(nodeColors.red), // #ef4444
	rose: rgbToHex(nodeColors.rose), // #f43f5e
	orange: rgbToHex(nodeColors.orange), // #f97316
	amber: rgbToHex(nodeColors.amber), // #f59e0b
	purple: rgbToHex(nodeColors.purple), // #a855f7
	violet: rgbToHex(nodeColors.violet), // #8b5cf6
	blue: rgbToHex(nodeColors.blue), // #3b82f6
	indigo: rgbToHex(nodeColors.indigo), // #6366f1
	teal: rgbToHex(nodeColors.teal), // #14b8a6
	cyan: rgbToHex(nodeColors.cyan), // #06b6d4
	emerald: rgbToHex(nodeColors.emerald), // #0DA931
	gray: rgbToHex(nodeColors.gray), // #6b7280
};

/**
 * Comprehensive node type to color mapping
 * Note: AGENT uses CSS variable to match theme (yellow or purple)
 */
export const NODE_TYPE_MINIMAP_COLORS: Record<string, string> = {
	// Flow control nodes
	START: minimapColors.green,
	END: minimapColors.red,

	// Core agent/workflow nodes - AGENT uses theme primary color
	AGENT: "var(--color-primary)",
	CONDITION: minimapColors.orange,
	CONDITIONAL: minimapColors.orange,
	CHECKPOINT: minimapColors.purple,

	// Tool nodes
	TOOL: minimapColors.blue,
	DOCUMENT_SEARCH: minimapColors.cyan,
	DATABASE_QUERY: minimapColors.violet,
	DATABASE_INSERT: minimapColors.emerald,
	DATABASE_QUERY_ACTION: minimapColors.emerald,
	HTTP_REQUEST: minimapColors.indigo,
	HTTP_REQUEST_ACTION: minimapColors.indigo,
	WEB_SEARCH: minimapColors.amber,
	MCP_SERVER: minimapColors.teal,
	EMAIL_SEND: minimapColors.emerald,
	EMAIL_SEND_TOOL: minimapColors.emerald,
	FILE_READ: minimapColors.orange,
	FILE_WRITE: minimapColors.amber,

	// Workflow composition nodes
	SUBWORKFLOW: minimapColors.teal,
	SUBGRAPH: minimapColors.teal,

	// Human/Review nodes
	REVIEW: minimapColors.purple,
	HUMAN: minimapColors.rose,

	// Info/Step nodes
	INFO: minimapColors.blue,
	STEP: minimapColors.blue,
};

/**
 * Get the minimap color for a node based on its type.
 * Handles various node type formats (uppercase, lowercase, React Flow component names).
 */
export function getMinimapNodeColor(node: Node): string {
	// Try to get node type from various sources
	const rawType =
		node.data?.type || node.type || node.data?.nodeType || "";

	// Normalize: remove "Node" suffix and convert to uppercase
	const normalizedType = String(rawType)
		.replace(/Node$/i, "")
		.toUpperCase();

	return NODE_TYPE_MINIMAP_COLORS[normalizedType] || minimapColors.gray;
}

/**
 * Get the minimap color for an edge based on its type and data.
 */
export function getMinimapEdgeColor(edge: Edge): string {
	// Check for branch color in edge data (used by ConditionEdge)
	if (edge.data?.branchColor) {
		return edge.data.branchColor;
	}

	// Check for label-based coloring (condition edges)
	const label = String(edge.data?.label || edge.label || "").toLowerCase();

	if (label) {
		// Success/approve paths
		if (["approve", "approved", "success", "yes", "true"].includes(label)) {
			return minimapColors.green;
		}
		// Failure/reject paths
		if (["reject", "rejected", "fail", "failed", "no", "false"].includes(label)) {
			return minimapColors.red;
		}
		// Review/pending paths
		if (["review", "pending", "wait", "hold"].includes(label)) {
			return minimapColors.purple;
		}
		// Default/else paths
		if (["default", "else", "otherwise"].includes(label)) {
			return minimapColors.gray;
		}
	}

	// Check edge type
	if (edge.type === "condition" || edge.type === "loopback") {
		return minimapColors.violet;
	}

	// Default edge color
	return "#4a4a4a";
}

/**
 * Calculate the bounding box of all nodes
 */
export function calculateNodesBoundingBox(nodes: Node[]): {
	minX: number;
	minY: number;
	maxX: number;
	maxY: number;
	width: number;
	height: number;
} {
	if (nodes.length === 0) {
		return { minX: 0, minY: 0, maxX: 100, maxY: 100, width: 100, height: 100 };
	}

	let minX = Infinity;
	let minY = Infinity;
	let maxX = -Infinity;
	let maxY = -Infinity;

	for (const node of nodes) {
		const x = node.position.x;
		const y = node.position.y;
		const width = node.width || node.data?.width || 200;
		const height = node.height || node.data?.height || 100;

		minX = Math.min(minX, x);
		minY = Math.min(minY, y);
		maxX = Math.max(maxX, x + width);
		maxY = Math.max(maxY, y + height);
	}

	// Add padding
	const padding = 50;
	minX -= padding;
	minY -= padding;
	maxX += padding;
	maxY += padding;

	return {
		minX,
		minY,
		maxX,
		maxY,
		width: maxX - minX,
		height: maxY - minY,
	};
}
