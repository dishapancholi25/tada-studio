"use client";

import { Activity } from "lucide-react";
import React from "react";
import type { GraphExecution } from "@/types/api";
import ExecutionMetadata from "./ExecutionMetadata";
import ExecutionStatusBadge from "./ExecutionStatusBadge";
import ViewerToolbar from "./ViewerToolbar";

interface ExecutionViewerHeaderProps {
	execution: GraphExecution;
	isDarkMode: boolean;
	isFullscreen: boolean;
	showStats?: boolean;
	autoRefresh?: boolean;
	isRunning?: boolean;
	onClose?: () => void;
	onRefresh?: () => void;
	onToggleAutoRefresh?: () => void;
	onExportJSON: () => void;
	onExportMarkdown: () => void;
	onToggleFullscreen: () => void;
	onToggleStats?: () => void;
	workflowId?: string;
	returnParam?: string | null;
}

export default function ExecutionViewerHeader({
	execution,
	isDarkMode,
	isFullscreen,
	showStats,
	autoRefresh,
	isRunning,
	onClose,
	onRefresh,
	onToggleAutoRefresh,
	onExportJSON,
	onExportMarkdown,
	onToggleFullscreen,
	onToggleStats,
	workflowId,
	returnParam,
}: ExecutionViewerHeaderProps) {
	return (
		<header
			className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 shadow-[0_14px_36px_rgba(15,23,42,0.10)] backdrop-blur-md"
		>
			<div className="px-4 sm:px-6 lg:px-8 py-4">
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-4">
						<div>
							<h1
								className={`text-2xl font-bold text-gray-900 flex items-center gap-2`}
							>
								<Activity className="h-6 w-6 text-orange-600" />
								{execution.graph_name}
							</h1>
							<div className="flex items-center gap-4">
								<ExecutionMetadata
									execution={execution}
									isDarkMode={isDarkMode}
								/>
								<ExecutionStatusBadge
									status={execution.status}
									isDarkMode={isDarkMode}
								/>
							</div>
						</div>
					</div>

					<ViewerToolbar
						execution={execution}
						isDarkMode={isDarkMode}
						isFullscreen={isFullscreen}
						showStats={showStats}
						autoRefresh={autoRefresh}
						isRunning={isRunning}
						onClose={onClose}
						onRefresh={onRefresh}
						onToggleAutoRefresh={onToggleAutoRefresh}
						onExportJSON={onExportJSON}
						onExportMarkdown={onExportMarkdown}
						onToggleFullscreen={onToggleFullscreen}
						onToggleStats={onToggleStats}
						workflowId={workflowId}
						returnParam={returnParam}
					/>
				</div>
			</div>
		</header>
	);
}
