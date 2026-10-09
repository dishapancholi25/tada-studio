import type { NodeExecution } from "@/types/api";
import { parseDocumentSearchResults } from "../../utils/parseDocumentSearchResults";
import type {
	CombinedNodeExecution,
	DatabaseQueryExecution,
	DocumentRetrieveExecution,
	DocumentSearchExecution,
	EmailSendExecution,
	FileWriteExecution,
	HttpRequestExecution,
	McpProvider,
	McpResultType,
	McpServerExecution,
	ToolExecution,
	ToolType,
	WebSearchExecution,
} from "../types/execution.types";

/**
 * Parse tool executions from node execution data
 */
export function parseToolExecutions(
	nodeExecution: NodeExecution | CombinedNodeExecution | null,
	toolType: ToolType,
): ToolExecution[] {
	console.log("[DEBUG DB_QUERY] parseToolExecutions called:", {
		toolType,
		hasNodeExecution: !!nodeExecution,
		nodeId: nodeExecution?.node_id,
		nodeType: nodeExecution?.node_type,
	});

	if (!nodeExecution) {
		console.log("[DEBUG DB_QUERY] No node execution, returning empty");
		return [];
	}

	const combinedNode = nodeExecution as CombinedNodeExecution;

	// Check for combined nodes with multiple tool executions
	if (combinedNode.all_tool_nodes) {
		console.log("[DEBUG DB_QUERY] Found all_tool_nodes, parsing multiple");
		return parseMultipleNodes(combinedNode.all_tool_nodes, toolType);
	}

	// Check for specific combined node types
	if (combinedNode.all_query_nodes && toolType === "database_query") {
		console.log(
			"[DEBUG DB_QUERY] Found all_query_nodes, parsing multiple DB queries",
		);
		return parseMultipleNodes(combinedNode.all_query_nodes, toolType);
	}

	if (
		combinedNode.all_search_nodes &&
		(toolType === "document_search" || toolType === "web_search")
	) {
		console.log("[DEBUG DB_QUERY] Found all_search_nodes");
		return parseMultipleNodes(combinedNode.all_search_nodes, toolType);
	}

	if (combinedNode.all_request_nodes && toolType === "http_request") {
		console.log("[DEBUG DB_QUERY] Found all_request_nodes");
		return parseMultipleNodes(combinedNode.all_request_nodes, toolType);
	}

	// Parse single node execution
	console.log("[DEBUG DB_QUERY] Parsing single node");
	return parseSingleNode(nodeExecution, toolType);
}

/**
 * Parse multiple tool nodes
 */
function parseMultipleNodes(
	nodes: NodeExecution[],
	toolType: ToolType,
): ToolExecution[] {
	const executions: ToolExecution[] = [];

	nodes.forEach((node, index) => {
		const nodeExecutions = parseSingleNode(node, toolType);
		// Add execution index and review iteration for tracking
		nodeExecutions.forEach((exec) => {
			exec.execution_index = index;
			// Inherit review_iteration from the node
			if (node.review_iteration !== undefined && node.review_iteration !== null) {
				exec.review_iteration = node.review_iteration;
			}
		});
		executions.push(...nodeExecutions);
	});

	return executions;
}

/**
 * Parse single node execution
 */
function parseSingleNode(
	node: NodeExecution,
	toolType: ToolType,
): ToolExecution[] {
	console.log("[DEBUG DB_QUERY] parseSingleNode:", {
		nodeId: node.node_id,
		nodeType: node.node_type,
		toolType,
		review_iteration: node.review_iteration,
		isDirectTool: isDirectToolNode(node, toolType),
		hasToolExecutions: !!node.output_data?.tool_executions,
		hasInputData: !!node.input_data,
		hasOutputData: !!node.output_data,
		outputDataKeys: node.output_data ? Object.keys(node.output_data) : [],
	});

	let executions: ToolExecution[] = [];

	// Check for direct tool node execution
	if (isDirectToolNode(node, toolType)) {
		console.log("[DEBUG DB_QUERY] Is direct tool node, parsing directly");
		executions = parseDirectToolNode(node, toolType);
	}
	// Parse from tool_executions in output_data
	else if (node.output_data?.tool_executions) {
		console.log("[DEBUG DB_QUERY] Has tool_executions in output_data");
		executions = parseToolExecutionsFromOutput(
			node.output_data.tool_executions,
			node,
			toolType,
		);
	} else {
		console.log("[DEBUG DB_QUERY] No tool executions found, returning empty");
		return [];
	}

	// Add review_iteration from node to all executions
	if (node.review_iteration !== undefined && node.review_iteration !== null) {
		executions.forEach((exec) => {
			exec.review_iteration = node.review_iteration!;
		});
	}

	return executions;
}

/**
 * Check if node is a direct tool node
 */
function isDirectToolNode(node: NodeExecution, toolType: ToolType): boolean {
	const nodeTypeMap: Record<ToolType, string[]> = {
		database_query: ["DATABASE_QUERY"],
		document_search: ["DOCUMENT_SEARCH"],
		document_retrieve: ["DOCUMENT_RETRIEVE"],
		email_send: ["EMAIL_SEND", "EMAIL_SEND_TOOL"],
		file_write: ["FILE_WRITE"],
		http_request: ["HTTP_REQUEST"],
		web_search: ["WEB_SEARCH"],
		mcp_server: ["MCP_SERVER"],
	};

	// Also check if it's a legacy TOOL node (for backwards compatibility)
	// This handles old executions that were stored with node_type='TOOL'
	if (node.node_type === "TOOL" && node.node_metadata?.tool_type) {
		// Use the tool_type from metadata if available
		return nodeTypeMap[toolType].includes(node.node_metadata.tool_type);
	}

	// For MCP tools stored as TOOL type without explicit tool_type metadata,
	// check if node_metadata has synthetic_tool_name (indicates MCP tool execution)
	if (
		toolType === "mcp_server" &&
		node.node_type === "TOOL" &&
		node.node_metadata?.synthetic_tool_name
	) {
		return true;
	}

	return nodeTypeMap[toolType].includes(node.node_type);
}

/**
 * Parse direct tool node execution
 */
function parseDirectToolNode(
	node: NodeExecution,
	toolType: ToolType,
): ToolExecution[] {
	switch (toolType) {
		case "database_query":
			return parseDatabaseQueryNode(node);
		case "document_search":
			return parseDocumentSearchNode(node);
		case "document_retrieve":
			return parseDocumentRetrieveNode(node);
		case "email_send":
			return parseEmailSendNode(node);
		case "file_write":
			return parseFileWriteNode(node);
		case "http_request":
			return parseHttpRequestNode(node);
		case "web_search":
			return parseWebSearchNode(node);
		case "mcp_server":
			return parseMcpServerNode(node);
		default:
			return [];
	}
}

/**
 * Parse database query node
 */
function parseDatabaseQueryNode(node: NodeExecution): DatabaseQueryExecution[] {
	console.log("[DEBUG DB_QUERY Parser] parseDatabaseQueryNode called with:", {
		nodeId: node.node_id,
		nodeType: node.node_type,
		hasInputData: !!node.input_data,
		inputDataType: typeof node.input_data,
		hasOutputData: !!node.output_data,
		outputDataType: typeof node.output_data,
		inputDataPreview: JSON.stringify(node.input_data)?.substring(0, 100),
	});

	// Parse input_data if it's a JSON string
	let inputData = node.input_data as any;
	if (typeof inputData === "string") {
		console.log(
			"[DEBUG DB_QUERY Parser] input_data is string, attempting parse:",
			inputData.substring(0, 100),
		);
		try {
			inputData = JSON.parse(inputData);
			console.log(
				"[DEBUG DB_QUERY Parser] Successfully parsed input_data:",
				inputData,
			);
		} catch (e) {
			console.log(
				"[DEBUG DB_QUERY Parser] Failed to parse input_data as JSON:",
				e,
			);
			// If it's not valid JSON, use as-is
		}
	}

	// Extract query from parsed input or use input directly
	const query = inputData?.query || inputData || "";
	console.log("[DEBUG DB_QUERY Parser] Extracted query:", query);

	// Parse output_data if it's a JSON string
	let outputData = node.output_data;
	if (typeof outputData === "string") {
		console.log(
			"[DEBUG DB_QUERY Parser] output_data is string, attempting parse",
		);
		try {
			outputData = JSON.parse(outputData);
			console.log("[DEBUG DB_QUERY Parser] Successfully parsed output_data");
		} catch (e) {
			console.log(
				"[DEBUG DB_QUERY Parser] Failed to parse output_data as JSON:",
				e,
			);
			// If it's not valid JSON, use as-is
		}
	}

	const results = outputData?.result || outputData?.results || outputData || "";
	console.log(
		"[DEBUG DB_QUERY Parser] Extracted results:",
		typeof results,
		"hasResults:",
		!!results,
	);

	if (!query) {
		console.log(
			"[DEBUG DB_QUERY Parser] No query found, returning empty array",
		);
		return [];
	}

	const execution = {
		tool: "database_query",
		query: typeof query === "string" ? query : JSON.stringify(query),
		results: results,
		timestamp: node.created_at || new Date().toISOString(),
		call_id: node.id || "direct_execution",
		duration: node.duration_seconds || undefined,
		parsed_results: parseQueryResults(outputData),
	};

	console.log("[DEBUG DB_QUERY Parser] Returning execution:", execution);
	return [execution];
}

/**
 * Parse document search node
 */
function parseDocumentSearchNode(
	node: NodeExecution,
): DocumentSearchExecution[] {
	// Parse input_data if it's a JSON string
	let inputData = node.input_data;
	if (typeof inputData === "string") {
		try {
			inputData = JSON.parse(inputData);
		} catch {
			// If it's not valid JSON, use as-is
		}
	}

	const query = inputData?.query || inputData || "";

	// Parse output_data if it's a JSON string
	let outputData = node.output_data;
	if (typeof outputData === "string") {
		try {
			outputData = JSON.parse(outputData);
		} catch {
			// If it's not valid JSON, use as-is
		}
	}

	const results = outputData?.result || outputData?.results || outputData || "";

	if (!query) return [];

	const parsedResults = parseDocumentSearchResults(results);

	return [
		{
			tool: "document_search",
			query: typeof query === "string" ? query : JSON.stringify(query),
			results: results,
			parsed_results: parsedResults,
			timestamp: node.created_at || new Date().toISOString(),
			call_id: node.id || "direct_execution",
			duration: node.duration_seconds || undefined,
			embedding_tokens: node.node_metadata?.embedding_tokens || 0,
			embedding_cost: node.node_metadata?.embedding_cost || 0,
			embedding_model: node.node_metadata?.embedding_model || "",
		},
	];
}

/**
 * Parse document retrieve node
 */
function parseDocumentRetrieveNode(
	node: NodeExecution,
): DocumentRetrieveExecution[] {
	let inputData = node.input_data;
	if (typeof inputData === "string") {
		try {
			inputData = JSON.parse(inputData);
		} catch {
			// keep as-is
		}
	}

	let outputData = node.output_data;
	if (typeof outputData === "string") {
		try {
			outputData = JSON.parse(outputData);
		} catch {
			// keep as-is
		}
	}

	const rawContent =
		outputData?.result ||
		outputData?.results ||
		(typeof outputData === "string" ? outputData : "") ||
		"";
	const contentStr =
		typeof rawContent === "string" ? rawContent : JSON.stringify(rawContent);
	const isError = contentStr.startsWith("Error:");

	return [
		{
			tool: "document_retrieve",
			document_name: inputData?.document_name,
			document_id: inputData?.document_id,
			page_range: inputData?.page_range,
			content: contentStr,
			content_length: contentStr.length,
			word_count: contentStr.split(/\s+/).filter(Boolean).length,
			line_count: contentStr.split("\n").length,
			status: isError ? "failed" : "success",
			error: isError ? contentStr : undefined,
			timestamp: node.created_at || new Date().toISOString(),
			call_id: node.id || "direct_execution",
			duration: node.duration_seconds || undefined,
		},
	];
}

/**
 * Parse email send node
 */
function parseEmailSendNode(node: NodeExecution): EmailSendExecution[] {
	let inputData = node.input_data as any;
	if (typeof inputData === "string") {
		try {
			inputData = JSON.parse(inputData);
		} catch {
			// keep as-is
		}
	}

	let outputData = node.output_data as any;
	if (typeof outputData === "string") {
		try {
			outputData = JSON.parse(outputData);
		} catch {
			// keep as-is
		}
	}

	// Result may be nested in 'result' field as a JSON string
	let resultData = outputData?.result || outputData;
	if (typeof resultData === "string") {
		try {
			resultData = JSON.parse(resultData);
		} catch {
			// keep as-is
		}
	}

	const toAddress = inputData?.to_address || resultData?.to_address || "";
	const subject = inputData?.subject || resultData?.subject || "";
	const body = inputData?.body || "";
	const messageId = resultData?.message_id || "";
	const status = resultData?.success === false ? "failed" : "sent";
	const error = resultData?.error;
	const attachmentsSent = resultData?.attachments_sent || 0;

	if (!toAddress && !subject) return [];

	return [
		{
			tool: "email_send",
			to_address: toAddress,
			subject: subject,
			body: body,
			message_id: messageId,
			status: status as "sent" | "failed",
			error: error,
			attachments_sent: attachmentsSent,
			timestamp: node.created_at || new Date().toISOString(),
			call_id: node.id || "direct_execution",
			duration: node.duration_seconds || undefined,
		},
	];
}

/**
 * Parse file write node
 */
function parseFileWriteNode(node: NodeExecution): FileWriteExecution[] {
	console.log("[DEBUG FILE_WRITE Parser] parseFileWriteNode called with:", {
		nodeId: node.node_id,
		nodeType: node.node_type,
		hasInputData: !!node.input_data,
		hasOutputData: !!node.output_data,
		inputDataType: typeof node.input_data,
		outputDataType: typeof node.output_data,
		inputDataPreview: JSON.stringify(node.input_data)?.substring(0, 300),
		outputDataPreview: JSON.stringify(node.output_data)?.substring(0, 300),
	});

	// Parse input_data if it's a JSON string
	let inputData = node.input_data;
	if (typeof inputData === "string") {
		try {
			inputData = JSON.parse(inputData);
		} catch {
			// If it's not valid JSON, use as-is
		}
	}

	// Parse output_data if it's a JSON string
	let outputData = node.output_data;
	if (typeof outputData === "string") {
		try {
			outputData = JSON.parse(outputData);
		} catch {
			// If it's not valid JSON, use as-is
		}
	}

	// Output may be nested in 'result' field from tool execution
	let resultData = outputData?.result || outputData;

	// Result might also be a JSON string that needs parsing
	if (typeof resultData === "string") {
		try {
			resultData = JSON.parse(resultData);
		} catch {
			// If it's not valid JSON, use as-is
		}
	}

	console.log("[DEBUG FILE_WRITE Parser] Parsed data:", {
		inputData,
		outputData,
		resultData,
		hasResult: !!outputData?.result,
		file_id: resultData?.file_id,
		filename: resultData?.filename || inputData?.filename,
	});

	const filename = inputData?.filename || resultData?.filename || "";
	const filepath = resultData?.filepath || inputData?.filepath;
	const fileId = resultData?.file_id;
	const fileUrl = resultData?.file_url;
	const contentType = inputData?.content_type || resultData?.content_type || "text";
	const fileSize = resultData?.file_size || resultData?.size;
	const subdirectory = inputData?.subdirectory || resultData?.subdirectory;
	const status = resultData?.error || resultData?.success === false ? "failed" : "success";
	const error = resultData?.error;
	// Get content from output (for text files, backend includes it for preview)
	const content = resultData?.content;

	console.log("[DEBUG FILE_WRITE Parser] Final values:", {
		filename,
		file_id: fileId,
		contentType,
		fileSize,
		status,
		hasContent: !!content,
	});

	if (!filename) return [];

	return [
		{
			tool: "file_write",
			filename: filename,
			filepath: filepath,
			file_id: fileId,
			file_url: fileUrl,
			content_type: contentType,
			file_size: fileSize,
			subdirectory: subdirectory,
			status: status,
			error: error,
			content: content,
			timestamp: node.created_at || new Date().toISOString(),
			call_id: node.id || "direct_execution",
			duration: node.duration_seconds || undefined,
		},
	];
}

/**
 * Parse HTTP request node
 */
function parseHttpRequestNode(node: NodeExecution): HttpRequestExecution[] {
	console.log("[parseHttpRequestNode] Called with node:", {
		nodeId: node.node_id,
		hasInputData: !!node.input_data,
		hasOutputData: !!node.output_data,
		inputDataKeys: node.input_data ? Object.keys(node.input_data) : [],
		outputDataKeys: node.output_data ? Object.keys(node.output_data) : [],
	});

	// Parse input_data if it's a JSON string
	let inputData = node.input_data;
	if (typeof inputData === "string") {
		try {
			inputData = JSON.parse(inputData);
		} catch {
			// If it's not valid JSON, use as-is
		}
	}

	console.log("[parseHttpRequestNode] Parsed input_data:", inputData);

	// CRITICAL: Check if input_data has a nested 'request' object (new backend structure)
	let request: any = {};
	let response: any = {};

	if (inputData?.request && typeof inputData.request === "object") {
		// New structure: input_data contains nested request object
		console.log(
			"[parseHttpRequestNode] Found nested request in input_data:",
			inputData.request,
		);
		request = inputData.request;
	} else {
		// Old structure: extract from parameters
		const parameters = inputData?.parameters || inputData || {};
		console.log(
			"[parseHttpRequestNode] Using old structure, parameters:",
			parameters,
		);

		// Parse request from parameters
		let parsedParams = parameters;
		if (typeof parameters === "string") {
			try {
				parsedParams = JSON.parse(parameters);
			} catch {
				parsedParams = { url: parameters };
			}
		}

		request = {
			method: parsedParams.method || "GET",
			url: parsedParams.url || "",
			headers: parsedParams.headers || {},
			body: parsedParams.body || parsedParams.data || undefined,
		};
	}

	// Parse output_data if it's a JSON string
	let outputData = node.output_data;
	if (typeof outputData === "string") {
		try {
			outputData = JSON.parse(outputData);
		} catch {
			// If it's not valid JSON, use as-is
		}
	}

	console.log("[parseHttpRequestNode] Parsed output_data:", outputData);

	// Check if output_data has the full HTTP metadata structure
	if (outputData?.tool === "http_request" && outputData?.response) {
		console.log(
			"[parseHttpRequestNode] Found full HTTP metadata in output_data",
		);
		response = outputData.response;
		// Also use request from output if not found in input
		if (!request.url && outputData.request) {
			request = outputData.request;
		}
	} else {
		// Extract response from various possible locations
		const results =
			outputData?.result ||
			outputData?.results ||
			outputData?.response ||
			outputData ||
			{};

		// Extract response data
		let responseData = results;
		if (typeof results === "string") {
			try {
				responseData = JSON.parse(results);
			} catch {
				responseData = { body: results };
			}
		}

		response = responseData;
	}

	const execution: HttpRequestExecution = {
		tool: "http_request",
		request: {
			method: request.method || "GET",
			url: request.url || "",
			headers: request.headers || {},
			body: request.body || null,
		},
		response: {
			status_code: response.status_code || response.status || 200,
			data: response.data || response.body || response.result || response,
			headers: response.headers || {},
			elapsed:
				response.elapsed || response.execution_time || node.duration_seconds,
		},
		timestamp: node.created_at || new Date().toISOString(),
		call_id: node.id || "direct_execution",
		duration: node.duration_seconds || undefined,
	};

	console.log("[parseHttpRequestNode] Final execution object:", execution);

	return [execution];
}

/**
 * Parse web search node
 */
function parseWebSearchNode(node: NodeExecution): WebSearchExecution[] {
	// Parse input_data if it's a JSON string
	let inputData = node.input_data;
	if (typeof inputData === "string") {
		try {
			inputData = JSON.parse(inputData);
		} catch {
			// If it's not valid JSON, use as-is
		}
	}

	const query =
		inputData?.query || (typeof inputData === "string" ? inputData : "");

	// Parse output_data if it's a JSON string
	let outputData = node.output_data;
	if (typeof outputData === "string") {
		try {
			outputData = JSON.parse(outputData);
		} catch {
			// If it's not valid JSON, use as-is
		}
	}

	// Extract results - could be in result or results field
	let results = outputData?.results || outputData?.result || outputData || {};

	// If result is a formatted string, parse it into structured data
	if (typeof results === "string") {
		const parsedResults = parseWebSearchResultsString(results);
		if (parsedResults) {
			results = parsedResults;
		}
	}

	if (!query) return [];

	return [
		{
			tool: "web_search",
			query: query,
			provider: outputData?.provider || "web",
			results: results,
			timestamp: node.created_at || new Date().toISOString(),
			call_id: node.id || "direct_execution",
			duration: node.duration_seconds || undefined,
		},
	];
}

/**
 * Parse web search results from formatted text string
 * Handles formats like:
 * "Search Results (5 found):
 *
 * 1. GPT-5 arrives...
 *    URL: https://...
 *    [content...]
 *    Relevance: 0.71"
 */
function parseWebSearchResultsString(text: string): { results: any[] } | null {
	if (!text || typeof text !== "string") return null;

	// Check if this looks like a formatted search results string
	if (!text.includes("Search Results") && !text.match(/^\d+\./m)) {
		return null;
	}

	const results: any[] = [];
	const lines = text.split("\n");
	let currentResult: any = null;
	let currentContent = "";

	for (let i = 0; i < lines.length; i++) {
		const line = lines[i];

		// Check for result number (e.g., "1. Title")
		const resultMatch = line.match(/^(\d+)\.\s+(.+)$/);
		if (resultMatch) {
			// Save previous result if exists
			if (currentResult) {
				currentResult.snippet = currentContent.trim();
				results.push(currentResult);
			}

			// Start new result
			currentResult = {
				position: parseInt(resultMatch[1]),
				title: resultMatch[2],
				url: "",
				snippet: "",
				score: null,
			};
			currentContent = "";
			continue;
		}

		// Check for URL
		const urlMatch = line.match(/^\s+URL:\s+(.+)$/);
		if (urlMatch && currentResult) {
			currentResult.url = urlMatch[1];
			continue;
		}

		// Check for Relevance/Score
		const relevanceMatch = line.match(/^\s+Relevance:\s+([\d.]+)$/);
		if (relevanceMatch && currentResult) {
			currentResult.score = parseFloat(relevanceMatch[1]);
			continue;
		}

		// Otherwise, it's content for the snippet
		if (currentResult && line.trim() && !line.startsWith("Search Results")) {
			// Skip the "Search Results" header line
			currentContent += line.trim() + " ";
		}
	}

	// Save last result
	if (currentResult) {
		currentResult.snippet = currentContent.trim();
		results.push(currentResult);
	}

	return results.length > 0 ? { results } : null;
}

/**
 * Detect MCP provider from tool name or server URL
 */
function detectMcpProvider(toolName: string, serverUrl?: string): McpProvider {
	const lowerToolName = toolName.toLowerCase();
	const lowerUrl = serverUrl?.toLowerCase() || "";

	if (lowerToolName.includes("notion") || lowerUrl.includes("notion"))
		return "notion";
	if (lowerToolName.includes("github") || lowerUrl.includes("github"))
		return "github";
	if (
		lowerToolName.includes("databricks") ||
		lowerUrl.includes("databricks")
	)
		return "databricks";
	if (
		lowerToolName.includes("sharepoint") ||
		lowerUrl.includes("sharepoint")
	)
		return "sharepoint";
	if (
		lowerToolName.includes("atlassian") ||
		lowerToolName.includes("jira") ||
		lowerToolName.includes("confluence") ||
		lowerUrl.includes("atlassian")
	)
		return "atlassian";
	if (lowerToolName.includes("onedrive") || lowerUrl.includes("onedrive"))
		return "onedrive";
	if (lowerToolName.includes("fabric") || lowerUrl.includes("fabric"))
		return "fabric";
	return "generic";
}

/**
 * Detect MCP result type for smart rendering
 */
function detectMcpResultType(result: any): McpResultType {
	if (!result) return "raw";

	// Search results (array with title/url)
	if (result?.results && Array.isArray(result.results)) {
		const firstResult = result.results[0];
		if (firstResult?.title && firstResult?.url) return "search";
		// SharePoint search_content: has query + total metadata with url results
		if (result.query !== undefined && result.total !== undefined && firstResult?.url)
			return "search";
	}

	// SharePoint search_files: uses files[] instead of results[]
	if (result?.files && Array.isArray(result.files)) {
		const firstFile = result.files[0];
		if (result.query !== undefined && result.total !== undefined && firstFile?.url)
			return "search";
	}

	// Page/document content
	if (result?.content || result?.body || result?.text) return "content";

	// Table/database results
	if (
		result?.rows ||
		result?.records ||
		(Array.isArray(result) && result[0]?.properties)
	)
		return "table";

	// Databricks SQL MCP results (manifest + data_array structure)
	if (result?.manifest?.schema?.columns && result?.result?.data_array)
		return "table";

	// List of items
	if (Array.isArray(result) && result.length > 0) return "list";

	// Single object
	if (typeof result === "object" && result !== null && !Array.isArray(result))
		return "object";

	// Plain text
	if (typeof result === "string") return "text";

	return "raw";
}

/**
 * Parse MCP result with handling for double-encoded JSON
 */
function parseMcpResult(result: any): { data: any; warning?: string } {
	if (result === null || result === undefined) return { data: result };
	if (typeof result !== "string") return { data: result };

	try {
		const parsed = JSON.parse(result);
		// Check if it's still a string (double-encoded)
		if (typeof parsed === "string") {
			try {
				return {
					data: JSON.parse(parsed),
					warning: "Result was double-encoded JSON",
				};
			} catch {
				return { data: parsed };
			}
		}
		return { data: parsed };
	} catch {
		return {
			data: result,
			warning: "Result is not valid JSON, displaying as text",
		};
	}
}

/**
 * Clean input arguments - remove internal fields
 */
function cleanMcpArguments(inputData: any): Record<string, any> {
	if (!inputData || typeof inputData !== "object") return {};

	// Remove internal/meta fields that aren't actual arguments
	const { action, target, tool, server_url, server, connection_type, ...args } =
		inputData;

	// If there's an arguments field, use that
	if (inputData.arguments && typeof inputData.arguments === "object") {
		return inputData.arguments;
	}

	return args;
}

/**
 * Parse MCP server node
 */
function parseMcpServerNode(node: NodeExecution): McpServerExecution[] {
	// Extract metadata
	const metadata = node.node_metadata || {};
	const syntheticToolName =
		metadata.synthetic_tool_name || node.node_name || "mcp_tool";

	// Parse input_data if it's a JSON string
	let inputData = node.input_data;
	if (typeof inputData === "string") {
		try {
			inputData = JSON.parse(inputData);
		} catch {
			// If it's not valid JSON, use as-is
		}
	}

	// Parse output_data if it's a JSON string
	let outputData = node.output_data;
	if (typeof outputData === "string") {
		try {
			outputData = JSON.parse(outputData);
		} catch {
			// If it's not valid JSON, use as-is
		}
	}

	// Extract and parse result with double-encoding handling
	const rawResult = outputData?.result || outputData?.results || outputData;
	const { data: parsedResult, warning: resultWarning } =
		parseMcpResult(rawResult);

	// Detect provider and result type
	const serverUrl = inputData?.server_url || inputData?.server;
	const provider = detectMcpProvider(syntheticToolName, serverUrl);
	const resultType = detectMcpResultType(parsedResult);

	// Extract action and target
	const action = inputData?.action || "tool";
	const target = inputData?.target || inputData?.tool || syntheticToolName;

	// Clean arguments
	const args = cleanMcpArguments(inputData);

	return [
		{
			tool: syntheticToolName,
			action: action,
			target: target,
			arguments: args,
			result: parsedResult,
			resultType: resultType,
			resultWarning: resultWarning,
			provider: provider,
			server: serverUrl,
			connection_type: inputData?.connection_type,
			timestamp: node.created_at || new Date().toISOString(),
			call_id: node.id || "direct_execution",
			duration: node.duration_seconds || undefined,
		},
	];
}

/**
 * Parse tool executions from output data
 */
function parseToolExecutionsFromOutput(
	toolExecs: any,
	node: NodeExecution,
	toolType: ToolType,
): ToolExecution[] {
	const executions: ToolExecution[] = [];
	const toolNames = getToolNames(toolType);

	// Find executions for this tool type
	for (const [toolName, toolData] of Object.entries(toolExecs)) {
		if (toolNames.some((name) => toolName.includes(name))) {
			const dataArray = Array.isArray(toolData) ? toolData : [toolData];

			for (const exec of dataArray) {
				const parsed = parseToolExecution(exec, toolType, toolName, node);
				if (parsed) {
					executions.push(parsed);
				}
			}
		}
	}

	// Also check if it's an array format
	if (Array.isArray(toolExecs)) {
		const filtered = toolExecs.filter(
			(e: any) => e.tool && toolNames.some((name) => e.tool.includes(name)),
		);

		for (const exec of filtered) {
			const parsed = parseToolExecution(exec, toolType, exec.tool, node);
			if (parsed) {
				executions.push(parsed);
			}
		}
	}

	return executions;
}

/**
 * Get tool names for a tool type
 */
function getToolNames(toolType: ToolType): string[] {
	const toolNameMap: Record<ToolType, string[]> = {
		database_query: ["database_query", "query_database", "sql_query"],
		document_search: ["document_search", "search_documents", "doc_search"],
		document_retrieve: ["retrieve_document", "document_retrieve"],
		email_send: ["email_send", "send_email", "email"],
		file_write: ["file_write", "write_file"],
		http_request: ["http_request", "http_call", "api_call"],
		web_search: ["web_search", "search_web", "search_and_summarize"],
		mcp_server: ["mcp_server", "mcp_adapter", "mcp_call"],
	};

	return toolNameMap[toolType];
}

/**
 * Parse individual tool execution
 */
function parseToolExecution(
	exec: any,
	toolType: ToolType,
	toolName: string,
	node: NodeExecution,
): ToolExecution | null {
	const baseExecution = {
		tool: toolName,
		timestamp: exec.timestamp || new Date().toISOString(),
		call_id: exec.call_id || exec.execution_id || `${toolName}_${Date.now()}`,
		duration: exec.duration,
	};

	switch (toolType) {
		case "database_query":
			return {
				...baseExecution,
				query: exec.query || exec.input || "",
				results: exec.results || exec.output || "",
				parsed_results: parseQueryResults(exec.results || exec.output),
			} as DatabaseQueryExecution;

		case "document_search":
			return {
				...baseExecution,
				query: exec.query || exec.input || "",
				results: exec.results || exec.output || "",
			} as DocumentSearchExecution;

		case "document_retrieve": {
			const input = exec.input || {};
			const rawContent =
				typeof exec.results === "string"
					? exec.results
					: exec.result || exec.output || "";
			const contentStr =
				typeof rawContent === "string"
					? rawContent
					: JSON.stringify(rawContent);
			const isError = contentStr.startsWith("Error:");

			return {
				...baseExecution,
				document_name: input.document_name,
				document_id: input.document_id,
				page_range: input.page_range,
				content: contentStr,
				content_length: contentStr.length,
				word_count: contentStr.split(/\s+/).filter(Boolean).length,
				line_count: contentStr.split("\n").length,
				status: isError ? "failed" : "success",
				error: isError ? contentStr : undefined,
			} as DocumentRetrieveExecution;
		}

		case "file_write": {
			// Parse results if it's a JSON string (tool result from agent execution)
			let fileData = exec;
			if (typeof exec.results === "string") {
				try {
					fileData = { ...exec, ...JSON.parse(exec.results) };
				} catch {
					// If parse fails, use exec as-is
				}
			}
			return {
				...baseExecution,
				filename: fileData.filename || exec.input?.filename || "",
				file_id: fileData.file_id,
				file_url: fileData.file_url,
				content_type: fileData.content_type || "text",
				file_size: fileData.file_size || fileData.size,
				subdirectory: fileData.subdirectory,
				status: fileData.error || fileData.success === false ? "failed" : "success",
				error: fileData.error,
				content: fileData.content,
			} as FileWriteExecution;
		}

		case "http_request":
			if (exec.request && exec.response) {
				return {
					...baseExecution,
					request: exec.request,
					response: exec.response,
					config: exec.config,
				} as HttpRequestExecution;
			}
			return null;

		case "web_search":
			return {
				...baseExecution,
				query: exec.input || exec.query || "",
				provider:
					exec.provider ||
					node.output_data?.web_search_config?.search_provider ||
					"web",
				results: exec.results,
				formatted_output: exec.output || exec.result || "",
				raw_results: exec.raw_results,
			} as WebSearchExecution;

		case "mcp_server": {
			const mcpToolName = exec.tool || toolName || "mcp_tool";
			const serverUrl = exec.server_url || exec.server;
			const rawResult = exec.result || exec.results;
			const { data: parsedResult, warning: resultWarning } =
				parseMcpResult(rawResult);

			return {
				...baseExecution,
				tool: mcpToolName,
				action: exec.action || exec.input?.action || "tool",
				target: exec.target || exec.input?.target || mcpToolName,
				arguments:
					exec.arguments ||
					exec.input?.arguments ||
					cleanMcpArguments(exec.input),
				server: serverUrl,
				connection_type: exec.connection_type || "stdio",
				provider: (exec.provider as McpProvider) || detectMcpProvider(mcpToolName, serverUrl),
				result: parsedResult,
				resultType: detectMcpResultType(parsedResult),
				resultWarning: resultWarning,
				formatted_output: exec.formatted_output || exec.output,
				capabilities: exec.capabilities,
			} as McpServerExecution;
		}

		default:
			return null;
	}
}

/**
 * Parse query results for database queries
 * Accepts either the full outputData object (with rowCount, columns metadata)
 * or just the results array
 */
function parseQueryResults(data: any): any {
	if (!data) return undefined;

	// If it's already a structured result with metadata (columns, data, rowCount)
	if (
		typeof data === "object" &&
		!Array.isArray(data) &&
		(data.columns || data.data || data.rowCount !== undefined)
	) {
		// Check if this is output_data with results/result inside
		const results = data.results || data.result;
		if (results) {
			// Extract metadata from the parent object
			return {
				rowCount:
					data.rowCount ??
					(Array.isArray(results) ? results.length : undefined),
				columns:
					data.columns ||
					(Array.isArray(results) && results.length > 0
						? Object.keys(results[0])
						: []),
				data: results,
			};
		}
		return data;
	}

	// If it's an array, compute metadata from it
	if (Array.isArray(data)) {
		return {
			rowCount: data.length,
			columns: data.length > 0 ? Object.keys(data[0]) : [],
			data: data,
		};
	}

	// Try to parse from string
	if (typeof data === "string") {
		// First try JSON parse
		try {
			const parsed = JSON.parse(data);
			return parseQueryResults(parsed); // Recurse with parsed object
		} catch {
			// Not JSON, try to parse the text format
			return parseTextQueryResults(data);
		}
	}

	return data;
}

/**
 * Parse text-formatted query results (e.g., "Found 3 rows\nColumns: id, name\nData preview:\n  Row 1: id: 1, name: test")
 */
function parseTextQueryResults(text: string): any {
	const result: any = { rawText: text };

	try {
		// Extract row count
		const rowCountMatch = text.match(/Found (\d+) rows?/);
		if (rowCountMatch) {
			result.rowCount = parseInt(rowCountMatch[1]);
		}

		// Extract columns
		const columnsMatch = text.match(/Columns:\s*([^\n]+)/);
		if (columnsMatch) {
			result.columns = columnsMatch[1].split(",").map((col) => col.trim());
		}

		// Extract data rows
		const dataMatch = text.match(
			/Data preview:\s*([\s\S]*?)(?:Table schema:|$)/,
		);
		if (dataMatch && result.columns) {
			const dataLines = dataMatch[1].trim().split("\n");
			result.data = [];

			for (const line of dataLines) {
				// Match "Row N: key1: value1, key2: value2, ..."
				const rowMatch = line.match(/Row \d+:\s*(.+)/);
				if (rowMatch) {
					const rowData: Record<string, any> = {};
					const rowContent = rowMatch[1];

					// Parse key-value pairs - handle values that may contain commas
					// Split by ", " but only when followed by a key pattern (word followed by colon)
					const pairs = rowContent.split(/,\s*(?=\w+:)/);

					for (const pair of pairs) {
						const colonIndex = pair.indexOf(":");
						if (colonIndex > 0) {
							const key = pair.substring(0, colonIndex).trim();
							const value = pair.substring(colonIndex + 1).trim();
							rowData[key] = value;
						}
					}

					result.data.push(rowData);
				}
			}
		}

		// Extract schema if present
		const schemaMatch = text.match(/Table schema:\s*([\s\S]*?)$/);
		if (schemaMatch) {
			result.schema = {};
			const schemaLines = schemaMatch[1].trim().split("\n");
			for (const line of schemaLines) {
				const match = line.match(/\s*(\w+):\s*(\w+)\s*\((not null|nullable)\)/);
				if (match) {
					result.schema[match[1]] = {
						type: match[2],
						nullable: match[3] === "nullable",
					};
				}
			}
		}

		// Check for "more rows" indicator
		if (text.includes("... and") && text.includes("more rows")) {
			result.hasMoreRows = true;
		}
	} catch (e) {
		console.error("[parseTextQueryResults] Error parsing text format:", e);
	}

	return result;
}
