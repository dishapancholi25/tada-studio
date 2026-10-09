import {
	Database,
	FileOutput,
	FileText,
	Globe,
	Mail,
	Search,
	Terminal,
} from "lucide-react";
import { useMemo } from "react";
import McpLogo from "../../../../icons/McpLogo";
import type { ToolConfig, ToolType } from "../types/execution.types";

// Tool configuration registry
const TOOL_REGISTRY: Record<ToolType, ToolConfig> = {
	database_query: {
		icon: Database,
		title: "Database Query",
		gradientFrom: "from-[color:var(--color-border)]",
		gradientTo: "to-[color:var(--color-accent)]/40",
		toolNames: ["database_query", "query_database", "sql_query"],
		nodeType: "DATABASE_QUERY",
	},
	document_search: {
		icon: FileText,
		title: "Document Search",
		gradientFrom: "from-[color:var(--color-border)]",
		gradientTo: "to-[color:var(--color-accent)]/40",
		toolNames: ["document_search", "search_documents", "doc_search"],
		nodeType: "DOCUMENT_SEARCH",
	},
	document_retrieve: {
		icon: FileText,
		title: "Document Retrieve",
		gradientFrom: "from-teal-600",
		gradientTo: "to-teal-500/40",
		toolNames: ["retrieve_document", "document_retrieve"],
		nodeType: "DOCUMENT_RETRIEVE",
	},
	email_send: {
		icon: Mail,
		title: "Email Send",
		gradientFrom: "from-emerald-600",
		gradientTo: "to-emerald-500/40",
		toolNames: ["email_send", "send_email"],
		nodeType: "EMAIL_SEND",
	},
	file_write: {
		icon: FileOutput,
		title: "File Write",
		gradientFrom: "from-amber-600",
		gradientTo: "to-amber-500/40",
		toolNames: ["file_write", "write_file"],
		nodeType: "FILE_WRITE",
	},
	http_request: {
		icon: Globe,
		title: "HTTP Request",
		gradientFrom: "from-[color:var(--color-border)]",
		gradientTo: "to-[color:var(--color-accent)]/40",
		toolNames: ["http_request", "http_call", "api_call"],
		nodeType: "HTTP_REQUEST",
	},
	web_search: {
		icon: Search,
		title: "Web Search",
		gradientFrom: "from-[color:var(--color-border)]",
		gradientTo: "to-[color:var(--color-accent)]/40",
		toolNames: ["web_search", "search_web", "search_and_summarize"],
		nodeType: "WEB_SEARCH",
	},
	mcp_server: {
		icon: McpLogo as any,
		title: "MCP Server",
		gradientFrom: "from-[color:var(--color-border)]",
		gradientTo: "to-[color:var(--color-accent)]/40",
		toolNames: ["mcp_server", "mcp_adapter", "mcp_call"],
		nodeType: "MCP_SERVER",
	},
};

/**
 * Hook to get tool configuration
 */
export function useToolRegistry(toolType: ToolType) {
	const config = useMemo(() => {
		return TOOL_REGISTRY[toolType];
	}, [toolType]);

	return config;
}
