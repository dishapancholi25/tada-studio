/**
 * Pure utility functions for formatting tool call data in the chat window.
 * No React imports — data transformation only.
 */

// ============================================================================
// Tool Display Info
// ============================================================================

interface ToolDisplayInfo {
	displayName: string;
	toolAction?: string;
}

/**
 * Extract a human-friendly display name and optional specific tool action.
 * For MCP tools, splits the generic node name from the specific tool target.
 */
export function getToolDisplayInfo(
	toolName: string,
	toolNodeName?: string,
	toolNodeType?: string,
	toolArgs?: Record<string, unknown>,
): ToolDisplayInfo {
	// MCP tools: extract the specific tool target from args
	// McpAdapterInput uses `tool_name`, McpServerInput uses `target`
	if (toolNodeType === "MCP_SERVER" && toolArgs) {
		const target = (toolArgs.tool_name || toolArgs.target) as string | undefined;
		if (target) {
			const displayName = toolNodeName || formatRawToolName(toolName);
			const toolAction = formatToolAction(target);
			return { displayName, toolAction };
		}
	}

	// Non-MCP or MCP without target: use node name or format the raw tool name
	if (toolNodeName) return { displayName: toolNodeName };
	return { displayName: formatRawToolName(toolName) };
}

/** Format a raw tool name (e.g., "search_web_abc123") into title case. */
function formatRawToolName(toolName: string): string {
	return toolName
		.replace(/^(search_|http_request_|database_query_|mcp_server_|mcp_adapter_)/, "")
		.replace(/_/g, " ")
		.replace(/\b\w/g, (l) => l.toUpperCase());
}

/** Format a tool action/target (e.g., "search_content") into title case. */
function formatToolAction(target: string): string {
	return target
		.replace(/_/g, " ")
		.replace(/\b\w/g, (l) => l.toUpperCase());
}

// ============================================================================
// Argument Unwrapping
// ============================================================================

/**
 * Unwrap MCP argument wrappers to show the actual user-facing parameters.
 * For MCP_SERVER tools, strips the `action`/`target` wrapper and returns
 * the inner `arguments` object.
 */
export function unwrapToolArgs(
	toolArgs: Record<string, unknown>,
	toolNodeType?: string,
): Record<string, unknown> {
	if (toolNodeType !== "MCP_SERVER") return toolArgs;

	// If there's an inner `arguments` object, return it directly
	const inner = toolArgs.arguments;
	if (inner && typeof inner === "object" && !Array.isArray(inner)) {
		return inner as Record<string, unknown>;
	}

	// Otherwise strip the MCP wrapper keys and return the rest
	const mcpWrapperKeys = new Set(["action", "target", "tool_name", "arguments"]);
	const rest: Record<string, unknown> = {};
	for (const [key, value] of Object.entries(toolArgs)) {
		if (!mcpWrapperKeys.has(key)) {
			rest[key] = value;
		}
	}
	return Object.keys(rest).length > 0 ? rest : toolArgs;
}

// ============================================================================
// Inline Preview Generation
// ============================================================================

/**
 * Generate a smart one-line preview for the collapsed tool call card.
 * Parses the result JSON and extracts a meaningful summary.
 */
export function generateInlinePreview(
	resultPreview: string,
): string {
	// Try to parse as JSON
	let parsed: unknown;
	try {
		parsed = JSON.parse(resultPreview);
		// Handle double-encoded JSON strings
		if (typeof parsed === "string") {
			try {
				parsed = JSON.parse(parsed);
			} catch {
				// Single string result — use it directly
				return truncate(parsed as string, 80);
			}
		}
	} catch {
		// JSON.parse failed — could be truncated JSON or plain text.
		const trimmed = resultPreview.trim();

		// Plain text (doesn't look like JSON at all) — use directly
		if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) {
			return truncate(trimmed, 80);
		}

		// Truncated JSON — try regex-based heuristics
		return extractPreviewFromTruncatedJson(trimmed);
	}

	if (parsed === null || parsed === undefined) return "Result received";

	// --- Object-based heuristics ---
	if (typeof parsed === "object" && !Array.isArray(parsed)) {
		const obj = parsed as Record<string, unknown>;
		return extractObjectPreview(obj);
	}

	// --- Array result ---
	if (Array.isArray(parsed)) {
		return describeArray(parsed, "items");
	}

	// --- Primitive ---
	return truncate(String(parsed), 80);
}

/**
 * Extract a preview from truncated/invalid JSON using regex heuristics.
 * The backend truncates resultPreview to 500 chars, so JSON.parse often fails.
 */
function extractPreviewFromTruncatedJson(raw: string): string {
	const trimmed = raw.trim();
	if (trimmed === "{" || trimmed === "[") return "Result received";

	// Count array items by looking for object boundaries in array fields
	// e.g. `{ "results": [ { "id": ... }, { "id": ... }, ...`
	for (const key of ["results", "items", "files", "documents", "records", "entries", "matches"]) {
		const pattern = new RegExp(`"${key}"\\s*:\\s*\\[`);
		if (pattern.test(trimmed)) {
			// Count occurrences of `{ "` after the array start as a proxy for item count
			const arrayStart = trimmed.search(pattern);
			const afterArray = trimmed.slice(arrayStart);
			const itemMatches = afterArray.match(/\{\s*"/g);
			const count = itemMatches ? itemMatches.length : 0;
			if (count > 0) {
				const label = key === "data" ? "items" : key;
				// Check for a "total" field
				const totalMatch = trimmed.match(/"total"\s*:\s*(\d+)/);
				if (totalMatch) {
					return `Found ${count}+ of ${totalMatch[1]} ${label}`;
				}
				return `Found ${count}+ ${label}`;
			}
		}
	}

	// Look for "error" field
	const errorMatch = trimmed.match(/"error"\s*:\s*"([^"]{1,80})"/);
	if (errorMatch) return truncate(`Error: ${errorMatch[1]}`, 80);

	// Look for "message" field
	const messageMatch = trimmed.match(/"message"\s*:\s*"([^"]{1,80})"/);
	if (messageMatch) return truncate(messageMatch[1], 80);

	// Look for "status": "success"
	if (/"status"\s*:\s*"success"/.test(trimmed)) return "Completed successfully";

	// Look for "name" field
	const nameMatch = trimmed.match(/"name"\s*:\s*"([^"]{1,80})"/);
	if (nameMatch) return truncate(nameMatch[1], 80);

	// Look for "content" field
	const contentMatch = trimmed.match(/"content"\s*:\s*"([^"]{1,80})"/);
	if (contentMatch) return truncate(contentMatch[1], 80);

	return "Result received";
}

/** Extract a preview line from a parsed JSON object. */
function extractObjectPreview(obj: Record<string, unknown>): string {
	// Table-like structure (check before array fields since "rows" is also in the array list)
	if (Array.isArray(obj.columns) && (Array.isArray(obj.rows) || typeof obj.row_count === "number")) {
		const rowCount = Array.isArray(obj.rows) ? obj.rows.length : obj.row_count;
		return `${rowCount} rows, ${(obj.columns as unknown[]).length} columns`;
	}

	// Array-based result fields
	for (const key of ["results", "items", "files", "documents", "records", "data", "entries", "rows", "values", "matches"]) {
		const arr = obj[key];
		if (Array.isArray(arr)) {
			const total = typeof obj.total === "number" ? obj.total : undefined;
			const label = key === "data" ? "items" : key;
			if (total !== undefined && total > arr.length) {
				return `Found ${arr.length} of ${total} ${label}`;
			}
			return describeArray(arr, label);
		}
	}

	// Count/total fields
	if (typeof obj.total === "number" && typeof obj.count === "number") {
		return `${obj.count} of ${obj.total} results`;
	}
	if (typeof obj.count === "number") return `${obj.count} results`;
	if (typeof obj.total === "number") return `${obj.total} results`;

	// Error field
	if (typeof obj.error === "string") {
		return truncate(`Error: ${obj.error}`, 80);
	}

	// Status/message
	if (typeof obj.message === "string") {
		return truncate(obj.message, 80);
	}
	if (obj.status === "success" || obj.success === true) {
		return typeof obj.message === "string" ? truncate(obj.message, 80) : "Completed successfully";
	}

	// Content field (file content, document text, etc.)
	if (typeof obj.content === "string") {
		return truncate(obj.content.replace(/\n/g, " "), 80);
	}

	// Object with a name field
	if (typeof obj.name === "string") {
		return truncate(obj.name, 80);
	}

	// Object with a title field
	if (typeof obj.title === "string") {
		return truncate(obj.title, 80);
	}

	// Try first meaningful string value
	for (const value of Object.values(obj)) {
		if (typeof value === "string" && value.length > 2 && value.length < 100) {
			return truncate(value, 80);
		}
	}

	return "Result received";
}

/** Describe an array result concisely. */
function describeArray(arr: unknown[], label: string): string {
	if (arr.length === 0) return `No ${label} found`;
	if (arr.length === 1) return `Found 1 ${label.replace(/s$/, "")}`;
	return `Found ${arr.length} ${label}`;
}

// ============================================================================
// Expanded Result Formatting
// ============================================================================

const MAX_FORMATTED_LINES = 15;

/**
 * Format a result preview for the expanded view.
 * Tries to pretty-print JSON, falling back to raw text.
 */
export function formatExpandedResult(resultPreview: string): string {
	try {
		let parsed = JSON.parse(resultPreview);
		// Handle double-encoded JSON
		if (typeof parsed === "string") {
			try {
				parsed = JSON.parse(parsed);
			} catch {
				return parsed;
			}
		}
		const formatted = JSON.stringify(parsed, null, 2);
		const lines = formatted.split("\n");
		if (lines.length > MAX_FORMATTED_LINES) {
			return `${lines.slice(0, MAX_FORMATTED_LINES).join("\n")}\n  ... (${lines.length - MAX_FORMATTED_LINES} more lines)`;
		}
		return formatted;
	} catch {
		return resultPreview;
	}
}

// ============================================================================
// Tool Group Summary
// ============================================================================

/**
 * Generate a summary string for a group of tool calls.
 * E.g., "Used 5 tools (3 SharePoint, 2 HTTP)"
 */
export function summarizeToolGroup(
	tools: Array<{ toolNodeName?: string; toolNodeType?: string; status: string }>,
): { label: string; isRunning: boolean } {
	const hasRunning = tools.some((t) => t.status === "running");
	const verb = hasRunning ? "Using" : "Used";

	// Group by display name
	const counts = new Map<string, number>();
	for (const t of tools) {
		const name = t.toolNodeName || t.toolNodeType || "Tool";
		counts.set(name, (counts.get(name) || 0) + 1);
	}

	// If all same type, use that name
	if (counts.size === 1) {
		const [name, count] = [...counts.entries()][0];
		return { label: `${verb} ${count} ${name} ${count === 1 ? "call" : "calls"}`, isRunning: hasRunning };
	}

	// Build breakdown
	const parts = [...counts.entries()]
		.sort((a, b) => b[1] - a[1])
		.slice(0, 3)
		.map(([name, count]) => `${count} ${name}`);

	const suffix = counts.size > 3 ? `, +${counts.size - 3} more` : "";
	return {
		label: `${verb} ${tools.length} tools (${parts.join(", ")}${suffix})`,
		isRunning: hasRunning,
	};
}

// ============================================================================
// Shared Helpers
// ============================================================================

function truncate(text: string, max: number): string {
	if (text.length <= max) return text;
	return `${text.slice(0, max)}...`;
}
