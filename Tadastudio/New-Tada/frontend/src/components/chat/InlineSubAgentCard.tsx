"use client";

import { CheckCircle2, ChevronRight, Loader2, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import type { ToolCallBlock } from "@/hooks/useStreamingChat";
import InlineToolCallCard from "./InlineToolCallCard";

interface InlineSubAgentCardProps {
	subagentId: string;
	subagentName: string;
	taskDescription?: string;
	parentAgentName?: string;
	status: "running" | "complete" | "error";
	durationMs?: number;
	toolsUsed?: string[];
	nestedToolCalls: ToolCallBlock[];
}

const AGENT_COLORS = [
	{ border: "#2563eb", text: "#1e40af" },
	{ border: "#7c3aed", text: "#6d28d9" },
	{ border: "#db2777", text: "#9d174d" },
	{ border: "#059669", text: "#047857" },
	{ border: "#ea580c", text: "#9a3412" },
	{ border: "#0891b2", text: "#155e75" },
	{ border: "#dc2626", text: "#991b1b" },
	{ border: "#ca8a04", text: "#854d0e" },
];

function getAgentColor(name: string) {
	let hash = 0;
	for (const ch of name) hash = ((hash << 5) - hash + ch.charCodeAt(0)) | 0;
	return AGENT_COLORS[Math.abs(hash) % AGENT_COLORS.length];
}

function formatDuration(ms: number): string {
	if (ms < 1000) return `${Math.round(ms)}ms`;
	return `${(ms / 1000).toFixed(1)}s`;
}

export default function InlineSubAgentCard({
	subagentName,
	taskDescription,
	status,
	durationMs,
	toolsUsed,
	nestedToolCalls,
}: InlineSubAgentCardProps) {
	const [expanded, setExpanded] = useState(status === "running");
	const color = getAgentColor(subagentName);
	const initial = subagentName.charAt(0).toUpperCase();

	useEffect(() => {
		if (status === "running") setExpanded(true);
	}, [status]);

	const statusIcon = {
		running: (
			<Loader2
				className="h-3.5 w-3.5 animate-spin text-orange-600"
			/>
		),
		complete: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />,
		error: <XCircle className="h-3.5 w-3.5 text-red-600" />,
	}[status];

	const hasChildren = nestedToolCalls.length > 0;
	const toolCount = toolsUsed?.length ?? nestedToolCalls.length;

	return (
		<div
			className="animate-toolCardIn my-2 w-full overflow-hidden rounded-xl border border-y border-r border-gray-200 bg-white shadow-sm transition-colors"
			style={{ borderLeft: `4px solid ${color.border}` }}
		>
			<button
				type="button"
				onClick={() => hasChildren && setExpanded(!expanded)}
				className={`flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left text-gray-800 transition-colors ${
					hasChildren ? "cursor-pointer hover:bg-slate-50" : "cursor-default"
				}`}
			>
				{hasChildren && (
					<ChevronRight
						className={`h-3 w-3 shrink-0 text-gray-500 transition-transform duration-200 ${
							expanded ? "rotate-90" : ""
						}`}
					/>
				)}

				<div
					className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border-2 bg-white text-[10px] font-bold"
					style={{ borderColor: color.border, color: color.text }}
				>
					{initial}
				</div>

				<div className="min-w-0 flex-1">
					<span
						className="block truncate text-[13px] font-medium"
						style={{ color: color.text }}
					>
						{status === "running"
							? `Delegating to ${subagentName}...`
							: subagentName}
					</span>
					{taskDescription && (
						<span className="mt-0.5 line-clamp-2 block truncate text-[11px] text-gray-500">
							{taskDescription}
						</span>
					)}
				</div>

				{toolCount > 0 && status !== "running" && (
					<span
						className="rounded-full border border-gray-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-gray-700"
					>
						{toolCount} tool{toolCount !== 1 ? "s" : ""}
					</span>
				)}

				{durationMs !== undefined && status !== "running" && (
					<span className="text-[10px] tabular-nums text-gray-500">
						{formatDuration(durationMs)}
					</span>
				)}
				{statusIcon}
			</button>

			{status === "running" && (
				<div className="tool-progress-bar mx-3.5 mb-2" />
			)}

			{expanded && nestedToolCalls.length > 0 && (
				<div className="animate-expandContent border-t border-gray-100 px-2.5 py-1.5">
					{nestedToolCalls.map((tc) => (
						<InlineToolCallCard
							key={tc.callId}
							callId={tc.callId}
							toolName={tc.toolName}
							status={tc.status}
							toolArgs={tc.toolArgs}
							resultPreview={tc.resultPreview}
							error={tc.error}
							durationMs={tc.durationMs}
							toolNodeType={tc.toolNodeType}
							toolNodeName={tc.toolNodeName}
						/>
					))}
				</div>
			)}
		</div>
	);
}
