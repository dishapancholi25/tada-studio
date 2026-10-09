"use client";

import { Calendar, Clock, Hash } from "lucide-react";
import React from "react";
import type { GraphExecution } from "@/types/api";

interface ExecutionMetadataProps {
	execution: GraphExecution;
	isDarkMode: boolean;
}

export default function ExecutionMetadata({
	execution,
	isDarkMode,
}: ExecutionMetadataProps) {
	return (
		<div className="flex items-center gap-4 mt-2 text-sm">
			<span
				className={`flex items-center gap-1 ${isDarkMode ? "text-[color:var(--color-text-muted)]" : "text-[color:var(--color-text-muted)]"}`}
			>
				<Hash className="w-4 h-4" />
				{execution.id.slice(0, 8)}...
			</span>

			{execution.duration_seconds && (
				<span
					className={`flex items-center gap-1 ${isDarkMode ? "text-[color:var(--color-text-muted)]" : "text-[color:var(--color-text-muted)]"}`}
				>
					<Clock className="w-4 h-4" />
					{execution.duration_seconds.toFixed(2)}s
				</span>
			)}

			{execution.start_time && (
				<span
					className={`flex items-center gap-1 ${isDarkMode ? "text-[color:var(--color-text-muted)]" : "text-[color:var(--color-text-muted)]"}`}
				>
					<Calendar className="w-4 h-4" />
					{new Date(execution.start_time).toLocaleString()}
				</span>
			)}
		</div>
	);
}
