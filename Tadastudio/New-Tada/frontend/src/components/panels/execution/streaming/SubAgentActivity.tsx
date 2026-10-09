"use client";

import {
	Bot,
	CheckCircle2,
	ChevronRight,
	Loader2,
	XCircle,
} from "lucide-react";
import React, { useState } from "react";

export interface SubAgentActivityProps {
	subagentId: string;
	subagentName: string;
	status: "running" | "complete" | "error";
	taskDescription?: string;
	parentAgentName?: string;
	durationMs?: number;
	toolsUsed?: string[];
	children?: React.ReactNode; // Nested tool calls
}

export const SubAgentActivity: React.FC<SubAgentActivityProps> = ({
	subagentName,
	status,
	taskDescription,
	parentAgentName,
	durationMs,
	toolsUsed,
	children,
}) => {
	const [expanded, setExpanded] = useState(status === "running");

	const statusIcon = {
		running: (
			<Loader2 className="h-4 w-4 animate-spin text-[color:var(--color-primary)]" />
		),
		complete: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
		error: <XCircle className="h-4 w-4 text-red-400" />,
	}[status];

	// Format duration
	const formatDuration = (ms: number) => {
		if (ms < 1000) return `${Math.round(ms)}ms`;
		return `${(ms / 1000).toFixed(1)}s`;
	};

	const hasChildren = React.Children.count(children) > 0;

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
			className={`rounded-lg border transition-colors ${getContainerStyles()}`}
		>
			<button
				onClick={() => hasChildren && setExpanded(!expanded)}
				className={`w-full flex items-center gap-3 px-3 py-2 transition-colors ${
					hasChildren
						? "hover:bg-[rgba(var(--color-primary-rgb),0.1)] cursor-pointer"
						: "cursor-default"
				}`}
				disabled={!hasChildren}
			>
				{hasChildren && (
					<ChevronRight
							className={`h-4 w-4 text-[color:var(--color-primary)] transition-transform flex-shrink-0 ${
							expanded ? "rotate-90" : ""
						}`}
					/>
				)}
					<Bot className="h-4 w-4 text-[color:var(--color-primary)] flex-shrink-0" />
				<div className="flex-1 min-w-0 text-left">
					<div className="flex items-center gap-2">
						<span className="text-sm font-medium text-[color:var(--color-text-primary)] truncate">
							{subagentName}
						</span>
						{parentAgentName && (
								<span className="text-xs text-[color:var(--color-text-muted)]">
								delegated from {parentAgentName}
							</span>
						)}
					</div>
					{taskDescription && (
						<p className="text-xs text-[color:var(--color-text-muted)] truncate mt-0.5">
							{taskDescription}
						</p>
					)}
				</div>
				<div className="flex items-center gap-2 flex-shrink-0">
					{toolsUsed && toolsUsed.length > 0 && (
						<span className="text-xs text-[color:var(--color-text-muted)]">
							{toolsUsed.length} tool{toolsUsed.length !== 1 ? "s" : ""}
						</span>
					)}
					{durationMs !== undefined && status !== "running" && (
						<span className="text-xs text-[color:var(--color-text-muted)]">
							{formatDuration(durationMs)}
						</span>
					)}
					{statusIcon}
				</div>
			</button>
			{expanded && hasChildren && (
				<div className="border-t border-[color:var(--color-border)]/20 px-3 py-2 space-y-2">
					{children}
				</div>
			)}
		</div>
	);
};

export default SubAgentActivity;
