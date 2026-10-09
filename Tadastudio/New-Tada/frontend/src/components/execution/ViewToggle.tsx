"use client";

import { List, Network } from "lucide-react";
import { useRouter } from "next/navigation";
import React from "react";

interface ViewToggleProps {
	workflowId: string;
	executionId: string;
	currentView: "enhanced" | "graph";
	isDarkMode?: boolean;
	returnParam?: string | null;
}

export default function ViewToggle({
	workflowId,
	executionId,
	currentView,
	isDarkMode = true,
	returnParam,
}: ViewToggleProps) {
	const router = useRouter();

	const handleViewChange = (view: "enhanced" | "graph") => {
		if (view === currentView) return;

		// Build the base URL - encode both workflowId and executionId
		const baseUrl = `/workflow/${encodeURIComponent(workflowId)}/${encodeURIComponent(executionId)}`;
		const url = view === "graph" ? `${baseUrl}/graph` : baseUrl;

		// Preserve the return query parameter if it exists
		const finalUrl = returnParam ? `${url}?return=${returnParam}` : url;

		router.push(finalUrl);
	};

	const buttonBaseClass = `p-2 rounded-lg transition-colors flex items-center gap-1.5`;
	const activeClass = "bg-[color:var(--color-primary)]/20 text-[color:var(--color-primary)]";
	const inactiveClass = isDarkMode
		? "hover:bg-[color:var(--color-surface)] text-[color:var(--color-text-muted)]"
		: "hover:bg-gray-100 text-[color:var(--color-text-muted)]";

	return (
		<div data-tutorial="view-toggle" className="flex items-center gap-1 bg-[color:var(--color-surface)]/50 rounded-lg p-1">
			<button
				data-tutorial="view-toggle-trace"
				onClick={() => handleViewChange("enhanced")}
				className={`${buttonBaseClass} ${currentView === "enhanced" ? activeClass : inactiveClass}`}
				title="Enhanced Trace View"
			>
				<List className="w-4 h-4" />
				<span className="text-xs font-medium">Trace</span>
			</button>
			<button
				data-tutorial="view-toggle-graph"
				onClick={() => handleViewChange("graph")}
				className={`${buttonBaseClass} ${currentView === "graph" ? activeClass : inactiveClass}`}
				title="Graph View"
			>
				<Network className="w-4 h-4" />
				<span className="text-xs font-medium">Graph</span>
			</button>
		</div>
	);
}
