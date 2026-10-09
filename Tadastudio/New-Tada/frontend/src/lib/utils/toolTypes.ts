/**
 * Utility functions for tool node type checking
 */

export const TOOL_NODE_TYPES = [
	"DATABASE_QUERY",
	"WEB_SEARCH",
	"DOCUMENT_SEARCH",
	"DOCUMENT_RETRIEVE",
	"HTTP_REQUEST",
	"MCP_SERVER",
	"EMAIL_SEND_TOOL",
	"FILE_WRITE",
	"TOOL", // For backwards compatibility with old executions
] as const;

export type ToolNodeType = (typeof TOOL_NODE_TYPES)[number];

/**
 * Check if a node type is a tool node
 */
export function isToolNode(nodeType: string): boolean {
	return TOOL_NODE_TYPES.includes(nodeType as ToolNodeType);
}
