"use client";

import { CheckCircle2, Loader2, Wrench, XCircle } from "lucide-react";
import type React from "react";
import {
	detectProviderFromNodeName,
	getProviderVisuals,
} from "@/components/icons/McpProviderIcons";

export interface ToolCallActivityProps {
	callId: string;
	toolName: string;
	status: "running" | "complete" | "error";
	toolArgs?: Record<string, any>;
	progressMessage?: string;
	progressPercent?: number;
	durationMs?: number;
	agentName?: string;
	error?: string;
	toolNodeType?: string;
	toolNodeName?: string;
}

export const ToolCallActivity: React.FC<ToolCallActivityProps> = ({
	toolName,
	status,
	toolArgs,
	progressMessage,
	progressPercent,
	durationMs,
	agentName,
	error,
	toolNodeType,
	toolNodeName,
}) => {
	const statusIcon = {
		running: (
			<Loader2 className="h-4 w-4 animate-spin text-[color:var(--color-primary)]" />
		),
		complete: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
		error: <XCircle className="h-4 w-4 text-red-400" />,
	}[status];

	// Format tool name for display - prefer the actual node name from the canvas
	const displayName =
		toolNodeName ||
		toolName
			.replace(/^(search_|http_request_|database_query_)/, "")
			.replace(/_/g, " ")
			.replace(/\b\w/g, (l) => l.toUpperCase());

	// Format duration
	const formatDuration = (ms: number) => {
		if (ms < 1000) return `${Math.round(ms)}ms`;
		return `${(ms / 1000).toFixed(1)}s`;
	};

	// Resolve MCP provider icon
	const mcpProvider =
		toolNodeType === "MCP_SERVER" && toolNodeName
			? detectProviderFromNodeName(toolNodeName)
			: null;
	const providerVisuals = mcpProvider ? getProviderVisuals(mcpProvider) : null;

	// Get container styles based on status
	const getContainerStyles = () => {
		switch (status) {
			case "running":
				return "border-[rgba(var(--color-primary-rgb),0.3)] bg-[rgba(var(--color-primary-rgb),0.05)]";
			case "error":
				return "border-red-500/30 bg-red-500/5";
			case "complete":
				return "border-emerald-500/30 bg-emerald-500/5";
			default:
				return "border-[color:var(--color-border)]/30 bg-[color:var(--color-surface)]/30";
		}
	};

	return (
		<div
			className={`flex flex-col rounded-lg border px-3 py-2 transition-colors ${getContainerStyles()}`}
		>
			{/* Main row with tool info */}
			<div className="flex items-center gap-3">
				{providerVisuals ? (
					<providerVisuals.icon
						className="h-4 w-4 flex-shrink-0"
						size={16}
						style={{ color: providerVisuals.color }}
					/>
				) : (
					<Wrench className="h-4 w-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
				)}
				<div className="flex-1 min-w-0">
					<div className="flex items-center gap-2">
						<span className="text-sm font-medium text-[color:var(--color-text-primary)] truncate">
							{displayName}
						</span>
						{agentName && (
							<span className="text-xs text-[color:var(--color-text-muted)]">
								via {agentName}
							</span>
						)}
					</div>
					{progressMessage && status === "running" && (
						<p className="text-xs text-[color:var(--color-text-muted)] truncate mt-0.5">
							{progressMessage}
						</p>
					)}
					{error && status === "error" && (
						<p className="text-xs text-red-400 truncate mt-0.5">{error}</p>
					)}
					{progressPercent !== undefined && status === "running" && (
						<div className="mt-1.5 h-1 bg-[color:var(--color-surface)] rounded-full overflow-hidden">
							<div
								className="h-full bg-[color:var(--color-primary)] transition-all duration-300 ease-out"
								style={{ width: `${Math.min(100, progressPercent)}%` }}
							/>
						</div>
					)}
				</div>
				<div className="flex items-center gap-2 flex-shrink-0">
					{durationMs !== undefined && status !== "running" && (
						<span className="text-xs text-[color:var(--color-text-muted)]">
							{formatDuration(durationMs)}
						</span>
					)}
					{statusIcon}
				</div>
			</div>

			{/* Tool Arguments section */}
			{toolArgs && Object.keys(toolArgs).length > 0 && (
				<div className="mt-2 pt-2 border-t border-[color:var(--color-border)]/30">
					<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] mb-1">
						Arguments
					</div>
					<div className="text-xs font-mono text-[color:var(--color-text-secondary)] bg-[color:var(--color-surface)]/30 rounded px-2 py-1 overflow-x-auto">
						{/* For tools with a query, show it prominently */}
						{toolArgs.query && (
							<div className="mb-1">
								<span className="text-[color:var(--color-text-muted)]">
									query:{" "}
								</span>
									<span className="text-[color:var(--color-primary)]">
									&ldquo;{toolArgs.query}&rdquo;
								</span>
							</div>
						)}
						{/* Show other args in compact format */}
						{Object.entries(toolArgs)
							.filter(([key]) => key !== "query")
							.slice(0, 3)
							.map(([key, value]) => (
								<div key={key} className="truncate">
									<span className="text-[color:var(--color-text-muted)]">
										{key}:{" "}
									</span>
										<span className="text-[color:var(--color-text-primary)]">
										{typeof value === "object"
											? JSON.stringify(value).slice(0, 50) +
												(JSON.stringify(value).length > 50 ? "..." : "")
											: String(value)}
									</span>
								</div>
							))}
						{Object.keys(toolArgs).filter((k) => k !== "query").length > 3 && (
							<div className="text-[color:var(--color-text-muted)] mt-1">
								+{Object.keys(toolArgs).filter((k) => k !== "query").length - 3}{" "}
								more...
							</div>
						)}
					</div>
				</div>
			)}
		</div>
	);
};

export default ToolCallActivity;
