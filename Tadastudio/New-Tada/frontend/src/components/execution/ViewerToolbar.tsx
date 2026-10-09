"use client";

import {
	FileJson,
	FileText,
	Info,
	Maximize2,
	Minimize2,
	RefreshCw,
	RotateCw,
	X,
} from "lucide-react";
import React from "react";
import type { GraphExecution } from "@/types/api";
import ViewToggle from "./ViewToggle";

interface ViewerToolbarProps {
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

export default function ViewerToolbar({
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
}: ViewerToolbarProps) {
	const handleClose = () => {
		if (onClose) {
			onClose();
		} else {
			// Store state to restore the execution panel
			if (execution) {
				localStorage.setItem(
					"return-from-viewer",
					JSON.stringify({
						graphName: execution.graph_name,
						executionId: execution.id,
						showExecutionPanel: true,
					}),
				);
			}
			// Navigate back to workflow builder
			window.location.href = "/";
		}
	};

	const buttonClass = `p-2 rounded-lg transition-colors ${
		isDarkMode
			? "text-slate-500 hover:bg-white hover:text-slate-900"
			: "text-gray-500 hover:bg-white hover:text-slate-900 hover:ring-1 hover:ring-orange-400"
	}`;
	const separatorClass = "w-px h-8 bg-gray-300";

	return (
		<div className="flex items-center gap-2">
			{/* Auto-refresh (only when running) */}
			{isRunning && onToggleAutoRefresh && (
				<button
					onClick={onToggleAutoRefresh}
					className={`p-2 rounded-lg transition-colors ${
						autoRefresh
							? isDarkMode
								? "bg-white text-orange-700 ring-1 ring-orange-300"
								: "bg-white text-orange-700 ring-1 ring-orange-400"
							: isDarkMode
								? "text-slate-500 hover:bg-white hover:text-slate-900"
								: "hover:bg-white text-gray-500 hover:text-slate-900 hover:ring-1 hover:ring-orange-400"
					}`}
					title={autoRefresh ? "Stop auto-refresh" : "Auto-refresh"}
				>
					<RefreshCw className={`w-5 h-5 ${autoRefresh ? "animate-spin" : ""}`} />
				</button>
			)}

			{/* Refresh (only when running) */}
			{isRunning && onRefresh && (
				<button
					onClick={onRefresh}
					className={buttonClass}
					title="Refresh"
				>
					<RotateCw className="w-5 h-5" />
				</button>
			)}

			{isRunning && <div className={separatorClass} />}

			{/* Export buttons */}
			<button
				onClick={onExportJSON}
				className={buttonClass}
				title="Export as JSON"
			>
				<FileJson className="w-5 h-5" />
			</button>

			<button
				onClick={onExportMarkdown}
				className={buttonClass}
				title="Export as Markdown"
			>
				<FileText className="w-5 h-5" />
			</button>

			<div className={separatorClass} />

			{/* View Toggle */}
			{workflowId && (
				<>
					<ViewToggle
						workflowId={workflowId}
						executionId={execution.id}
						currentView="enhanced"
						isDarkMode={isDarkMode}
						returnParam={returnParam}
					/>
					<div className={separatorClass} />
				</>
			)}

			{/* Maximize */}
			<button
				onClick={onToggleFullscreen}
				className={buttonClass}
				title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
			>
				{isFullscreen ? (
					<Minimize2 className="w-5 h-5" />
				) : (
					<Maximize2 className="w-5 h-5" />
				)}
			</button>

			{/* Info / Stats toggle */}
			{onToggleStats && (
				<button
					onClick={onToggleStats}
					className={`p-2 rounded-lg transition-colors ${
						showStats
							? isDarkMode
								? "bg-white text-orange-700 ring-1 ring-orange-300"
								: "bg-white text-orange-700 ring-1 ring-orange-400"
							: isDarkMode
								? "text-slate-500 hover:bg-white hover:text-slate-900"
								: "hover:bg-white text-gray-500 hover:text-slate-900 hover:ring-1 hover:ring-orange-400"
					}`}
					title="Toggle Statistics"
				>
					<Info className="w-5 h-5" />
				</button>
			)}

			{/* Close */}
			<button
				onClick={handleClose}
				className={buttonClass}
				title="Close"
			>
				<X className="w-5 h-5" />
			</button>
		</div>
	);
}
