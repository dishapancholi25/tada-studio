"use client";

import { CheckCircle2, ChevronRight, Loader2, Wrench, XCircle } from "lucide-react";
import { useMemo, useState } from "react";
import {
	detectProviderFromNodeName,
	getProviderVisuals,
} from "@/components/icons/McpProviderIcons";
import {
	getToolDisplayInfo,
	unwrapToolArgs,
	generateInlinePreview,
	formatExpandedResult,
} from "./utils/toolCallDisplayUtils";

interface InlineToolCallCardProps {
	callId: string;
	toolName: string;
	status: "running" | "complete" | "error";
	toolArgs?: Record<string, unknown>;
	resultPreview?: string;
	error?: string;
	durationMs?: number;
	agentName?: string;
	toolNodeType?: string;
	toolNodeName?: string;
}

/** Format duration */
function formatDuration(ms: number): string {
	if (ms < 1000) return `${Math.round(ms)}ms`;
	return `${(ms / 1000).toFixed(1)}s`;
}

export default function InlineToolCallCard({
	toolName,
	status,
	toolArgs,
	resultPreview,
	error,
	durationMs,
	toolNodeType,
	toolNodeName,
}: InlineToolCallCardProps) {
	const [expanded, setExpanded] = useState(false);

	// Compute display info (stable across streaming since these props don't change after start)
	const { displayName, toolAction } = useMemo(
		() => getToolDisplayInfo(toolName, toolNodeName, toolNodeType, toolArgs),
		[toolName, toolNodeName, toolNodeType, toolArgs],
	);

	// Unwrap MCP argument wrappers for display
	const displayArgs = useMemo(
		() => (toolArgs ? unwrapToolArgs(toolArgs, toolNodeType) : undefined),
		[toolArgs, toolNodeType],
	);

	// Smart inline preview for collapsed state
	const inlinePreview = useMemo(
		() =>
			status === "complete" && resultPreview
				? generateInlinePreview(resultPreview)
				: null,
		[status, resultPreview],
	);

	// Formatted result for expanded view
	const formattedResult = useMemo(
		() => (expanded && resultPreview ? formatExpandedResult(resultPreview) : null),
		[expanded, resultPreview],
	);

	// MCP provider icon
	const mcpProvider =
		toolNodeType === "MCP_SERVER" && toolNodeName
			? detectProviderFromNodeName(toolNodeName)
			: null;
	const providerVisuals = mcpProvider ? getProviderVisuals(mcpProvider) : null;

	const statusIcon = {
		running: (
			<Loader2 className="h-3.5 w-3.5 animate-spin text-orange-600" />
		),
		complete: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />,
		error: <XCircle className="h-3.5 w-3.5 text-red-600" />,
	}[status];

	const borderStyle =
		status === "running"
			? "border-orange-500"
			: status === "error"
				? "border-red-300"
				: "border-emerald-200";

	const bgColor = {
		running: "bg-white",
		complete: "bg-white",
		error: "bg-white",
	}[status];

	const hasExpandableContent =
		(displayArgs && Object.keys(displayArgs).length > 0) || resultPreview || error;

	return (
		<div
			className={`animate-toolCardIn my-2 w-full rounded-xl border shadow-sm backdrop-blur-[4px] transition-colors ${borderStyle} ${bgColor}`}
		>
			{/* Header row */}
			<button
				type="button"
				onClick={() => hasExpandableContent && setExpanded(!expanded)}
				className={`flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left text-gray-800 transition-colors ${
					hasExpandableContent
						? "cursor-pointer hover:bg-slate-50"
						: "cursor-default"
				}`}
			>
				{hasExpandableContent && (
					<ChevronRight
						className={`h-3 w-3 shrink-0 text-gray-500 transition-transform duration-200 ${
							expanded ? "rotate-90" : ""
						}`}
					/>
				)}
				{providerVisuals ? (
					<providerVisuals.icon
						className="h-3.5 w-3.5 shrink-0"
						size={14}
						style={{ color: providerVisuals.color }}
					/>
				) : (
					<Wrench className="h-3.5 w-3.5 shrink-0 text-gray-500" />
				)}
				<span className="flex-1 truncate text-[13px] font-medium text-gray-800">
					{status === "running" ? "Calling " : ""}
					{toolAction ? (
						<>
							<span className="text-gray-500">{displayName}</span>
							<span className="mx-1 text-gray-400">/</span>
							<span>{toolAction}</span>
						</>
					) : (
						displayName
					)}
					{status === "running" ? "..." : ""}
				</span>
				{durationMs !== undefined && status !== "running" && (
					<span className="text-[10px] tabular-nums text-gray-500">
						{formatDuration(durationMs)}
					</span>
				)}
				{statusIcon}
			</button>

			{/* Inline result preview (without expanding) */}
			{inlinePreview && !expanded && (
				<div className="-mt-1 px-3.5 pb-2">
					<p className="truncate text-[11px] text-gray-500">{inlinePreview}</p>
				</div>
			)}

			{/* Progress bar for running state */}
			{status === "running" && (
				<div className="tool-progress-bar mx-3.5 mb-2" />
			)}

			{/* Expanded content */}
			{expanded && (
				<div className="animate-expandContent space-y-2 border-t border-gray-100 px-3.5 py-2.5">
					{/* Tool arguments */}
					{displayArgs && Object.keys(displayArgs).length > 0 && (
						<div>
							<div className="mb-1 text-[0.55rem] capitalize text-gray-500">
								Arguments
							</div>
							<div className="overflow-x-auto rounded border border-gray-100 bg-slate-50 px-2 py-1.5 font-mono text-[11px] text-gray-800">
								{typeof displayArgs.query === "string" && (
									<div className="mb-0.5">
										<span className="text-gray-500">query: </span>
										<span className="text-orange-800">
											&ldquo;{displayArgs.query}&rdquo;
										</span>
									</div>
								)}
								{Object.entries(displayArgs)
									.filter(([key]) => key !== "query")
									.slice(0, 5)
									.map(([key, value]) => (
										<div key={key} className="truncate">
											<span className="text-gray-500">{key}: </span>
											<span>
												{typeof value === "object"
													? JSON.stringify(value).slice(0, 80) +
														(JSON.stringify(value).length > 80 ? "..." : "")
													: String(value)}
											</span>
										</div>
									))}
							</div>
						</div>
					)}

					{/* Result preview */}
					{formattedResult && status === "complete" && (
						<div>
							<div className="mb-1 text-[0.55rem] capitalize text-gray-500">
								Result
							</div>
							<pre className="custom-scrollbar max-h-[200px] overflow-auto whitespace-pre-wrap rounded border border-gray-100 bg-slate-50 px-2 py-1.5 font-mono text-[11px] text-gray-800">
								{formattedResult}
							</pre>
						</div>
					)}

					{/* Error */}
					{error && status === "error" && (
						<div>
							<div className="mb-1 text-[0.55rem] capitalize text-red-700">
								Error
							</div>
							<p className="rounded border border-red-200 bg-white px-2 py-1.5 text-[11px] text-red-800">
								{error}
							</p>
						</div>
					)}
				</div>
			)}
		</div>
	);
}
