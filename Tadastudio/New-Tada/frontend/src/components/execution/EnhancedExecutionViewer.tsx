"use client";

import { XCircle } from "lucide-react";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNotification } from "@/contexts/NotificationContext";
import { api } from "@/lib/api";
import type { GraphExecution, NodeExecution } from "@/types/api";
import TraceViewer, { type TraceViewerHandle } from "../trace/TraceViewer";
import ExecutionViewerHeader from "./ExecutionViewerHeader";

interface EnhancedExecutionViewerProps {
	executionId: string;
	onClose?: () => void;
	workflowId?: string;
	returnParam?: string | null;
}

export default function EnhancedExecutionViewer({
	executionId,
	onClose,
	workflowId,
	returnParam,
}: EnhancedExecutionViewerProps) {
	const [execution, setExecution] = useState<GraphExecution | null>(null);
	const [isFullscreen, setIsFullscreen] = useState(false);
	const [isDarkMode] = useState(false);
	const [isLoading, setIsLoading] = useState(true);
	const [loadError, setLoadError] = useState(false);
	const [showStats, setShowStats] = useState(false);
	const [autoRefresh, setAutoRefresh] = useState(true);
	const traceRef = useRef<TraceViewerHandle>(null);
	const { showNotification } = useNotification();

	console.log("[EnhancedExecutionViewer] Render state:", {
		executionId,
		hasExecution: !!execution,
		isLoading,
		loadError,
	});

	// Load execution data
	useEffect(() => {
		const loadExecution = async () => {
			console.log("[EnhancedExecutionViewer] Starting loadExecution");
			try {
				setExecution(null);
				setLoadError(false);
				setIsLoading(true);
				console.log(
					"[EnhancedExecutionViewer] Reset state - isLoading: true, execution: null",
				);
				console.log(
					"[EXECUTION-ORDER] Opening Enhanced Execution Viewer for execution:",
					executionId,
				);

				// First try to load from localStorage for quick initial render
				const cachedData = localStorage.getItem("execution-viewer-data");
				if (cachedData) {
					const parsed = JSON.parse(cachedData);
					console.log(
						"[EnhancedExecutionViewer] Found cached data for execution:",
						parsed.dbExecutionId,
					);
					if (parsed.dbExecutionId === executionId) {
						// Use cached data for initial render
						console.log(
							"[EnhancedExecutionViewer] Using cached data for initial render",
						);
						setExecution({
							id: parsed.dbExecutionId,
							graph_name: parsed.graphName,
							status: parsed.status?.status || "running",
							node_executions: parsed.results || [],
							// Add dummy values for required fields
							graph_id: "",
							graph_definition: {
								name: parsed.graphName,
								nodes: [],
								edges: [],
							},
							start_time: null,
							end_time: null,
							duration_seconds: null,
							input_data: null,
							output_data: null,
							error_message: null,
							user_id: null,
							created_at: null,
						} as GraphExecution);
					}
				}

				// Fetch fresh data from API
				console.log("[EnhancedExecutionViewer] Fetching fresh data from API");
				const data = await api.get(
					`/api/execution-history/executions/${encodeURIComponent(executionId)}`,
				);
				console.log("[EnhancedExecutionViewer] API response received:", {
					hasData: !!data,
				});
				if (data) {
					// Sort node executions by actual execution flow
					if (data.node_executions) {
						data.node_executions.sort((a: NodeExecution, b: NodeExecution) => {
							// Primary sort by execution_order (now properly assigned in backend)
							const orderA = a.execution_order ?? 999;
							const orderB = b.execution_order ?? 999;

							if (orderA !== orderB) {
								return orderA - orderB;
							}

							// Secondary sort by start_time as fallback
							if (a.start_time && b.start_time) {
								return (
									new Date(a.start_time).getTime() -
									new Date(b.start_time).getTime()
								);
							}

							// If only one has start_time, prioritize it
							if (a.start_time && !b.start_time) return -1;
							if (!a.start_time && b.start_time) return 1;

							// Fallback: maintain original order
							return 0;
						});

						// Log the sorted execution order
						console.log(
							"[EXECUTION-ORDER] Sorted node executions:",
							data.node_executions.map((n: NodeExecution) => ({
								name: n.node_name,
								type: n.node_type,
								execution_order: n.execution_order,
								start_time: n.start_time,
							})),
						);
					}
					console.log(
						"[EnhancedExecutionViewer] Setting execution data, keeping isLoading: true",
					);
					setExecution(data);
					// Don't change loading state here - wait for TraceViewer to signal it's ready
				} else {
					console.log(
						"[EnhancedExecutionViewer] No data received, setting error state",
					);
					setExecution(null);
					setLoadError(true);
					setIsLoading(false);
				}
			} catch (error) {
				console.error(
					"[EnhancedExecutionViewer] Failed to load execution:",
					error,
				);
				showNotification("error", "Failed to load execution data");
				setLoadError(true);
				setIsLoading(false);
			} finally {
				// Clear cached data after loading
				console.log("[EnhancedExecutionViewer] Clearing cached data");
				localStorage.removeItem("execution-viewer-data");
			}
		};

		loadExecution().catch((error) => {
			console.error("Failed to load execution:", error);
		});
	}, [executionId, showNotification]);

	// Export functions
	const exportAsJSON = () => {
		if (!execution) return;
		const blob = new Blob([JSON.stringify(execution, null, 2)], {
			type: "application/json",
		});
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `execution-${executionId}.json`;
		a.click();
		URL.revokeObjectURL(url);
		showNotification("success", "Exported as JSON");
	};

	const exportAsMarkdown = () => {
		if (!execution) return;
		let markdown = `# Execution Report: ${execution.graph_name}\n\n`;
		markdown += `**Execution ID:** ${execution.id}\n`;
		markdown += `**Status:** ${execution.status}\n`;
		markdown += `**Duration:** ${execution.duration_seconds?.toFixed(2) || "N/A"} seconds\n\n`;

		const blob = new Blob([markdown], { type: "text/markdown" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `execution-${executionId}.md`;
		a.click();
		URL.revokeObjectURL(url);
		showNotification("success", "Exported as Markdown");
	};

	// Keyboard navigation
	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if (e.key === "Escape" && isFullscreen) {
				setIsFullscreen(false);
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [isFullscreen]);

	// Toggle fullscreen
	const toggleFullscreen = () => {
		if (!document.fullscreenElement) {
			document.documentElement.requestFullscreen().catch((error) => {
				console.error("Failed to enter fullscreen:", error);
			});
			setIsFullscreen(true);
		} else {
			document.exitFullscreen().catch((error) => {
				console.error("Failed to exit fullscreen:", error);
			});
			setIsFullscreen(false);
		}
	};

	const handleTraceLoadingChange = useCallback(
		(isLoadingTrace: boolean) => {
			console.log(
				"[EnhancedExecutionViewer] TraceViewer loading state changed:",
				{
					isLoadingTrace,
					hasExecution: !!execution,
					currentIsLoading: isLoading,
				},
			);
			// Only update loading state when TraceViewer signals it's done loading
			if (!isLoadingTrace && execution) {
				console.log(
					"[EnhancedExecutionViewer] TraceViewer finished loading, setting isLoading: false",
				);
				setIsLoading(false);
			}
		},
		[execution, isLoading],
	);

	const handleStatusChange = useCallback(
		async (status: string) => {
			// Re-fetch execution data when status changes to get updated duration, end_time, etc.
			if (execution && status !== execution.status) {
				try {
					const data = await api.get(
						`/api/execution-history/executions/${encodeURIComponent(executionId)}`,
					);
					if (data) {
						setExecution(data);
					}
				} catch {
					// Silently ignore - the header will just show stale data
				}
			}
		},
		[execution, executionId],
	);

	return (
		<div
			className="relative min-h-screen bg-white text-gray-800"
		>
			{execution && (
				<div style={{ visibility: isLoading ? "hidden" : "visible" }}>
					<ExecutionViewerHeader
						execution={execution}
						isDarkMode={isDarkMode}
						isFullscreen={isFullscreen}
						showStats={showStats}
						autoRefresh={autoRefresh}
						isRunning={execution.status === "running"}
						onClose={onClose}
						onRefresh={() => traceRef.current?.refresh()}
						onToggleAutoRefresh={() => setAutoRefresh(!autoRefresh)}
						onExportJSON={exportAsJSON}
						onExportMarkdown={exportAsMarkdown}
						onToggleFullscreen={toggleFullscreen}
						onToggleStats={() => setShowStats(!showStats)}
						workflowId={workflowId}
						returnParam={returnParam}
					/>

					<div className="flex-1 overflow-hidden">
						<TraceViewer
							ref={traceRef}
							executionId={executionId}
							initialMode="embedded"
							suppressLoader={true}
							onLoadingChange={handleTraceLoadingChange}
							onStatusChange={handleStatusChange}
							showStats={showStats}
							autoRefresh={autoRefresh}
						/>
					</div>
				</div>
			)}

			{!execution && !isLoading && loadError && (
				<div className="flex min-h-screen items-center justify-center">
					<div className="text-center">
						<XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
						<p className="text-[color:var(--color-text-muted)] text-lg">
							Execution not found
						</p>
					</div>
				</div>
			)}

			{isLoading && (
				<div className="absolute inset-0 z-50 flex items-center justify-center bg-white/95 backdrop-blur-sm">
					<div className="text-center space-y-2">
						<div className="mx-auto h-16 w-16 animate-spin rounded-full border-4 border-slate-200 border-t-orange-500"></div>
						<p className="text-[color:var(--color-text-muted)] text-lg">
							{!execution
								? "Loading execution data..."
								: "Preparing trace visualization..."}
						</p>
						{execution && (
							<p className="text-sm text-[color:var(--color-text-muted)] opacity-80">
								This may take a moment while we assemble the trace.
							</p>
						)}
					</div>
				</div>
			)}
		</div>
	);
}
