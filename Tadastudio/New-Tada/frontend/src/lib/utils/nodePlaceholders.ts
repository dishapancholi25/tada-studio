/**
* Node-type-specific placeholder messages for the execution panel.
* These are shown when a node is "In Progress" and has no output yet.
*/
 
export const NODE_TYPE_PLACEHOLDERS: Record<string, string> = {
	START: "Starting workflow...",
	END: "Completing workflow...",
	AGENT: "Thinking...",
	CONDITION: "Evaluating condition...",
	CONDITIONAL: "Evaluating condition...",
	EMAIL_SEND: "Sending email...",
	EMAIL_SEND_TOOL: "Sending email...",
	FILE_READ: "Reading file...",
	FILE_WRITE: "Writing file...",
	HTTP_REQUEST: "Sending request...",
	HTTP_REQUEST_ACTION: "Sending request...",
	DATABASE_INSERT: "Saving to database...",
	DATABASE_QUERY: "Querying database...",
	DATABASE_QUERY_ACTION: "Querying database...",
	CHECKPOINT: "Waiting for approval...",
	REVIEW: "Reviewing response...",
	DOCUMENT_SEARCH: "Searching documents...",
	WEB_SEARCH: "Searching the web...",
	TOOL: "Running tool...",
	MCP_SERVER: "Calling MCP service...",
	SUBWORKFLOW: "Running subworkflow...",
	SUBGRAPH: "Running subworkflow...",
	FOR_EACH: "Iterating over items...",
	INFO: "Processing...",
};
 
export const DEFAULT_PLACEHOLDER = "Processing...";
 
/**
* Gets the appropriate placeholder text for a node type.
*/
export function getNodePlaceholder(nodeType?: string): string {
	if (!nodeType) return DEFAULT_PLACEHOLDER;
	return NODE_TYPE_PLACEHOLDERS[nodeType.toUpperCase()] || DEFAULT_PLACEHOLDER;
}
 
/**
* Checks if a node should show a placeholder instead of output.
* A node shows a placeholder when it's running and has no meaningful output.
*/
export function shouldShowPlaceholder(
	status?: string,
	outputData?: Record<string, unknown> | null
): boolean {
	if (status !== "running") return false;
	if (!outputData) return true;
	if (typeof outputData === "object" && Object.keys(outputData).length === 0)
		return true;
	return false;
}