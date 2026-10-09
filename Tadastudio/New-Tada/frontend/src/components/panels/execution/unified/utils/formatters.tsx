import { AlertCircle, CheckCircle, Clock, FileText } from "lucide-react";
import React from "react";

/**
 * Format duration in human-readable format
 */
export function formatDuration(seconds?: number | null): string {
	if (seconds === null || seconds === undefined) return "-";
	if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
	if (seconds < 60) return `${seconds.toFixed(2)}s`;
	const minutes = Math.floor(seconds / 60);
	const remainingSeconds = seconds % 60;
	return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}

/**
 * Get status icon component
 */
export function getStatusIcon(status?: string | number) {
	// Handle HTTP status codes
	if (typeof status === "number") {
		if (status >= 200 && status < 300) {
			return <CheckCircle className="w-5 h-5 text-[#0DA931]" />;
		} else if (status >= 400) {
			return <AlertCircle className="w-5 h-5 text-red-500" />;
		}
	}

	// Handle execution status strings
	switch (status) {
		case "completed":
		case "success":
			return <CheckCircle className="w-5 h-5 text-[#0DA931]" />;
		case "failed":
		case "error":
			return <AlertCircle className="w-5 h-5 text-red-500" />;
		case "running":
		case "in_progress":
			return (
				<Clock className="w-5 h-5 text-[color:var(--color-accent)] animate-spin" />
			);
		case "skipped":
		case "pending":
			return (
				<FileText className="w-5 h-5 text-[color:var(--color-text-muted)]" />
			);
		default:
			return <Clock className="w-5 h-5 text-[color:var(--color-text-muted)]" />;
	}
}

/**
 * Get HTTP method color class
 */
export function getMethodColor(method: string): string {
	const colors: Record<string, string> = {
		GET: "text-[#0DA931]",
		POST: "text-[color:var(--color-accent)]",
		PUT: "text-[color:var(--color-accent)]",
		DELETE: "text-red-400",
		PATCH: "text-purple-400",
		HEAD: "text-[color:var(--color-text-muted)]",
		OPTIONS: "text-orange-400",
	};
	return colors[method.toUpperCase()] || "text-[color:var(--color-text-muted)]";
}

/**
 * Get HTTP status code color class
 */
export function getStatusColor(status?: number): string {
	if (!status) return "text-[color:var(--color-text-muted)]";
	if (status >= 200 && status < 300) return "text-[#0DA931]";
	if (status >= 300 && status < 400) return "text-[color:var(--color-accent)]";
	if (status >= 400 && status < 500) return "text-orange-400";
	if (status >= 500) return "text-red-400";
	return "text-[color:var(--color-text-muted)]";
}

/**
 * Format timestamp to locale string
 */
export function formatTimestamp(timestamp: string | Date): string {
	const date = typeof timestamp === "string" ? new Date(timestamp) : timestamp;
	return date.toLocaleString();
}

/**
 * Mask sensitive data in strings
 */
export function maskSensitiveData(
	text: string,
	showSecrets = false,
	patterns: string[] = ["auth", "key", "token", "password", "secret"],
): string {
	if (showSecrets) return text;

	// Check if the text contains any sensitive patterns
	const lowerText = text.toLowerCase();
	const hasSensitive = patterns.some((pattern) => lowerText.includes(pattern));

	return hasSensitive ? "••••••••" : text;
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text: string): Promise<boolean> {
	try {
		await navigator.clipboard.writeText(text);
		return true;
	} catch (err) {
		console.error("Failed to copy to clipboard:", err);
		return false;
	}
}

/**
 * Format MCP tool name to human-readable form
 * Examples:
 *   "notion-search" → "Notion Search"
 *   "mcp_adapter_github_search_issues" → "GitHub Search Issues"
 *   "create_page" → "Create Page"
 */
export function formatToolName(toolName: string): string {
	if (!toolName) return "MCP Tool";

	// Remove common prefixes
	const cleaned = toolName
		.replace(/^mcp_adapter_/i, "")
		.replace(/^mcp_/i, "")
		.replace(/^notion[_-]/i, "notion ")
		.replace(/^github[_-]/i, "github ");

	// Convert separators to spaces and capitalize each word
	return cleaned
		.replace(/[-_]/g, " ")
		.replace(/\b\w/g, (c) => c.toUpperCase())
		.trim();
}
