import type { NodeExecution } from "@/types/api";

// Tool types
export type ToolType =
	| "database_query"
	| "document_search"
	| "document_retrieve"
	| "email_send"
	| "file_write"
	| "http_request"
	| "web_search"
	| "mcp_server";

// Tool configuration
export interface ToolConfig {
	icon: React.ComponentType<any>;
	title: string;
	gradientFrom: string;
	gradientTo: string;
	toolNames: string[]; // Multiple possible tool names
	nodeType: string; // Expected node type in execution data
}

// Base execution interface
export interface BaseToolExecution {
	tool: string;
	timestamp: string;
	call_id: string;
	duration?: number;
	execution_index?: number; // For multi-execution tracking
	review_iteration?: number; // For agent review iteration tracking
}

// Database Query execution
export interface DatabaseQueryExecution extends BaseToolExecution {
	query: string;
	results: string | any;
	parsed_results?: {
		rowCount?: number;
		columns?: string[];
		data?: Record<string, any>[];
		schema?: Record<string, { type: string; nullable: boolean }>;
		error?: string;
		hasMoreRows?: boolean;
	};
}

// Document Search execution
export interface DocumentSearchExecution extends BaseToolExecution {
	query: string;
	results: string | any;
	parsed_results?: {
		content: string;
		source?: string;
		metadata?: {
			page?: number;
			relevance?: number;
			confidence?: number;
			source?: string;
		};
		isStructured?: boolean;
		raw?: Record<string, any>;
	}[];
	embedding_tokens?: number;
	embedding_cost?: number;
	embedding_model?: string;
}

// Document Retrieve execution
export interface DocumentRetrieveExecution extends BaseToolExecution {
	document_name?: string;
	document_id?: string;
	page_range?: string;
	content: string;
	content_length: number;
	word_count: number;
	line_count: number;
	status: "success" | "failed";
	error?: string;
}

// HTTP Request execution
export interface HttpRequestExecution extends BaseToolExecution {
	request: {
		method: string;
		url: string;
		headers?: Record<string, string>;
		query_params?: Record<string, string>;
		body?: any;
		parameters?: Record<string, any>;
	};
	response: {
		status_code?: number;
		headers?: Record<string, string>;
		data?: any;
		error?: string;
		elapsed?: number;
	};
	config?: {
		auth_type?: string;
		timeout_seconds?: number;
		max_retries?: number;
		follow_redirects?: boolean;
		verify_ssl?: boolean;
	};
}

// Email Send execution
export interface EmailSendExecution extends BaseToolExecution {
	to_address: string;
	subject: string;
	body?: string;
	message_id?: string;
	status: "sent" | "failed";
	error?: string;
	provider?: string;
	attachments_sent?: number;
}

// Web Search execution
export interface WebSearchExecution extends BaseToolExecution {
	query: string;
	provider: string;
	search_engine?: string;
	results?: {
		results?: Array<{
			title: string;
			url: string;
			snippet: string;
			score?: number;
			position: number;
		}>;
		answer?: string;
		images?: Array<{
			title: string;
			url: string;
			image_url: string;
			thumbnail: string;
		}>;
		error?: string;
	};
	formatted_output?: string;
	formatted_results?: string;
	raw_results?: any;
}

// MCP result types for smart rendering
export type McpResultType =
	| "search"
	| "content"
	| "table"
	| "list"
	| "object"
	| "text"
	| "raw";

// MCP provider types
export type McpProvider = "notion" | "github" | "databricks" | "sharepoint" | "atlassian" | "onedrive" | "fabric" | "generic";

// File Write execution
export interface FileWriteExecution extends BaseToolExecution {
	filename: string;
	filepath?: string; // Full path where file was written
	file_id?: string; // Database file ID (UUID)
	file_url?: string; // API URL for file download
	content_type: "text" | "base64";
	file_size?: number;
	subdirectory?: string;
	status: "success" | "failed";
	error?: string;
	content?: string; // Full content for text files (for preview)
}

// MCP Server execution
export interface McpServerExecution extends BaseToolExecution {
	action: string;
	target: string;
	arguments?: Record<string, any>;
	server?: string;
	connection_type?: string;
	provider?: McpProvider; // Provider detection: 'notion', 'github', 'generic'
	resultType?: McpResultType; // Result type for smart rendering
	resultWarning?: string; // Warning for malformed JSON
	capabilities?: {
		tools?: Array<{ name: string; description?: string }>;
		resources?: Array<{ uri: string; name?: string; description?: string }>;
		prompts?: Array<{ name: string; description?: string }>;
	};
	result?: any;
	formatted_output?: string;
}

// Union type for all executions
export type ToolExecution =
	| DatabaseQueryExecution
	| DocumentSearchExecution
	| DocumentRetrieveExecution
	| EmailSendExecution
	| FileWriteExecution
	| HttpRequestExecution
	| WebSearchExecution
	| McpServerExecution;

// Extended node execution with combined data
export interface CombinedNodeExecution extends NodeExecution {
	all_tool_nodes?: NodeExecution[]; // All related tool nodes from same parent
	all_query_nodes?: NodeExecution[]; // For database queries
	all_search_nodes?: NodeExecution[]; // For document/web searches
	all_request_nodes?: NodeExecution[]; // For HTTP requests
}

// Execution data fetcher options
export interface ExecutionDataOptions {
	executionId: string; // Can be WebSocket ID or Database UUID
	nodeId: string;
	nodeName: string;
	toolType: ToolType;
	nodeExecution?: NodeExecution; // Optional pre-loaded data
	parentAgentNodeId?: string; // For MCP nodes: the agent connected to this MCP node
	isExecuting?: boolean; // Whether the workflow is currently running (enables polling)
}

// Execution data result
export interface ExecutionDataResult {
	nodeExecution: CombinedNodeExecution | null;
	toolExecutions: ToolExecution[];
	loading: boolean;
	error: string | null;
}
