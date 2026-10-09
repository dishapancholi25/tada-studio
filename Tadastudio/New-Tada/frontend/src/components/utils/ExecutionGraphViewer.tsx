"use client";

import {
	lazy,
	Suspense,
	useCallback,
	useEffect,
	useMemo,
	useState,
} from "react";
import { Background, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import {
	Activity,
	AlertTriangle,
	Clock,
	Info,
	Maximize2,
	TrendingUp,
	X,
} from "lucide-react";
import {
	convertExecutionToReactFlow,
	formatExecutionDuration,
	getExecutionStats,
} from "@/lib/executionGraphUtils";
import type { GraphExecution, NodeExecution } from "@/types/api";
import { defaultSmoothEdgeOptions } from "../core/shared/defaultEdgeOptions";
import GraphCanvas from "../core/shared/GraphCanvas";
import {
	builderEdgeTypes,
	executionNodeTypes,
} from "../core/shared/nodeRegistry";
import { createReadOnlyGraphAdapter } from "../core/shared/readOnlyGraphAdapter";
import { useGraphHistory } from "../core/shared/useGraphHistory";
import { usePropertyPanels } from "../core/shared/usePropertyPanels";
import { useSelectionPanels } from "../core/shared/useSelectionPanels";
import CustomMinimap from "../ui/CustomMinimap";
import CustomZoomControls from "../ui/CustomZoomControls";
import ViewToggle from "../execution/ViewToggle";

// Execution panels are now loaded via the shared usePropertyPanels hook

type ExecutionPanelData = {
	id: string;
	nodeName: string;
	nodeExecution?: NodeExecution;
	graphExecutionId?: string;
	memoryEnabled?: boolean;
	nodeType?: string;
};

interface ExecutionGraphViewerProps {
	execution: GraphExecution;
	onClose: () => void;
	workflowId?: string;
	returnParam?: string | null;
}

export default function ExecutionGraphViewer({
	execution,
	onClose,
	workflowId,
	returnParam,
}: ExecutionGraphViewerProps) {
	const [nodes, setNodes] = useState<Node[]>([]);
	const [edges, setEdges] = useState<Edge[]>([]);
	const [showStats, setShowStats] = useState(true);

	const selectionPanels = useSelectionPanels();
	const { selection, openPanel, closePanel, resetPanels } = selectionPanels;
	const selectedNodeDetails =
		selection?.key === "execution"
			? (selection.data as ExecutionPanelData)
			: null;

	// Create read-only graph adapter
	const graphOperations = useMemo(
		() =>
			createReadOnlyGraphAdapter({
				initialNodes: nodes,
				initialEdges: edges,
				currentGraph: execution,
				onNodesChange: setNodes,
				onEdgesChange: setEdges,
			}),
		[nodes, edges, execution],
	);

	// Use shared property panels hook for execution mode
	const { renderExecutionPanels } = usePropertyPanels({
		graphOperations,
		selectionPanels,
		nodes,
		edges,
		mode: "execution",
		currentExecution: execution,
	});

	const { handleUndo, handleRedo } = useGraphHistory({
		reactFlowNodes: nodes,
		reactFlowEdges: edges,
		setReactFlowNodes: setNodes,
		setReactFlowEdges: setEdges,
		resetKey: execution.id,
	});

	// Convert execution data to React Flow format
	useEffect(() => {
		const { nodes: flowNodes, edges: flowEdges } =
			convertExecutionToReactFlow(execution);
		setNodes(flowNodes);
		setEdges(flowEdges);
	}, [execution]);

	const handleShowNodeDetails = useCallback(
		(event: CustomEvent) => {
			setTimeout(() => {
				openPanel("execution", {
					id: event.detail.nodeId,
					nodeName: event.detail.nodeName,
					nodeExecution: event.detail.nodeExecution,
					graphExecutionId: event.detail.graphExecutionId,
					memoryEnabled: event.detail.memoryEnabled,
					nodeType: event.detail.nodeType,
				});
			}, 0);
		},
		[openPanel],
	);

	// Listen for node double-click events
	useEffect(() => {
		window.addEventListener(
			"showExecutionNodeDetails",
			handleShowNodeDetails as EventListener,
		);

		return () => {
			window.removeEventListener(
				"showExecutionNodeDetails",
				handleShowNodeDetails as EventListener,
			);
		};
	}, [handleShowNodeDetails]);

	// Handle double-click on nodes in ReactFlow
	const onNodeDoubleClick = useCallback(
		(event: React.MouseEvent, node: Node) => {
			// Prevent default zoom behavior and event bubbling
			event.stopPropagation();
			event.preventDefault();
			if (event.nativeEvent.stopImmediatePropagation) {
				event.nativeEvent.stopImmediatePropagation();
			}

			const nodeExecution = execution.node_executions?.find(
				(ne) => ne.node_id === node.id,
			);

			// Better node type detection
			let nodeType = node.data?.type?.toLowerCase();
			if (!nodeType && node.type) {
				// Convert from node component name to type
				const typeMap: Record<string, string> = {
					webSearchNode: "web_search",
					documentSearchNode: "document_search",
					databaseQueryNode: "database_query",
					databaseInsertNode: "database_insert",
					httpRequestNode: "http_request",
					httpRequestActionNode: "http_request_action",
					mcpServerNode: "mcp_server",
					executionAgentNode: "agent",
					executionConditionNode: "condition",
					flowNode: "flow",
					agentNode: "agent",
				};
				nodeType =
					typeMap[node.type] || node.type?.replace("Node", "").toLowerCase();
			}

			console.log("[ExecutionGraphViewer] Node double-clicked:", {
				nodeId: node.id,
				nodeName: node.data?.name || node.data?.label,
				nodeType: nodeType,
				originalNodeType: node.type,
				dataType: node.data?.type,
				hasNodeExecution: !!nodeExecution,
				nodeExecutionType: nodeExecution?.node_type,
				nodeExecutionMetadata: nodeExecution?.node_metadata,
			});

			openPanel("execution", {
				id: node.id,
				nodeName: node.data?.name || node.data?.label || "Node",
				nodeExecution,
				graphExecutionId: execution.id,
				memoryEnabled: node.data?.agent_config?.memory_enabled || false,
				nodeType,
			});
		},
		[execution, openPanel],
	);

	// Get execution statistics
	const stats = getExecutionStats(execution.node_executions ?? []);

	const handleStatsToggle = useCallback(() => {
		setShowStats(!showStats);
	}, [showStats]);

	const handleToggleFullscreen = useCallback(() => {
		if (!document.fullscreenElement) {
			document.documentElement.requestFullscreen().catch(() => {});
		} else {
			document.exitFullscreen().catch(() => {});
		}
	}, []);

	const getNodeColor = useCallback((node: Node) => {
		const status = node.data?.executionStatus;
		switch (status) {
			case "completed":
				return "#0DA931"; // green
			case "failed":
				return "#ef4444"; // red
			case "skipped":
				return "#6b7280"; // gray
			case "running":
				return "#f59e0b"; // orange
			default:
				return "#374151"; // dark gray
		}
	}, []);

	useEffect(() => {
		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.ctrlKey && event.key === "z" && !event.shiftKey) {
				event.preventDefault();
				handleUndo();
			} else if (
				(event.ctrlKey && event.key === "y") ||
				(event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "z")
			) {
				event.preventDefault();
				handleRedo();
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [handleUndo, handleRedo]);

	useEffect(() => {
		resetPanels();
	}, [execution.id, resetPanels]);

	return (
		<div data-tutorial="execution-graph-viewer" className="fixed inset-0 z-50 flex flex-col bg-white text-slate-900">
			{/* Header */}
			<div className="flex items-center justify-between border-b border-orange-300 bg-white p-4">
				<div className="flex items-center gap-4">
					<h2 className="text-xl font-semibold text-slate-900">
						Execution View: {execution.graph_name}
					</h2>
					<span
						className={`px-3 py-1 rounded text-sm font-medium ${
							execution.status === "completed"
								? "border border-orange-300 bg-white text-orange-700"
								: execution.status === "failed"
									? "border border-red-300 bg-white text-red-700"
									: "border border-slate-300 bg-white text-slate-700"
						}`}
					>
						{execution.status}
					</span>
					<span className="text-sm text-[color:var(--color-text-muted)]">
						ID: {execution.id}
					</span>
				</div>

				<div className="flex items-center gap-2">
					{/* View Toggle */}
					{workflowId && (
						<>
							<ViewToggle
								workflowId={workflowId}
								executionId={execution.id}
								currentView="graph"
								isDarkMode={false}
								returnParam={returnParam}
							/>
							<div className="h-8 w-px bg-orange-200" />
						</>
					)}
					<button
						onClick={handleToggleFullscreen}
						className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-white hover:text-slate-900"
						title="Fullscreen"
					>
						<Maximize2 className="w-5 h-5" />
					</button>
					<button
						onClick={handleStatsToggle}
						className={`p-2 rounded-lg transition-colors ${
							showStats
								? "bg-white text-orange-700 ring-1 ring-orange-300"
								: "text-slate-500 hover:bg-white hover:text-slate-900"
						}`}
						title="Toggle Statistics"
					>
						<Info className="w-5 h-5" />
					</button>
					<button
						onClick={onClose}
						className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-white hover:text-slate-900"
						title="Close"
					>
						<X className="w-5 h-5" />
					</button>
				</div>
			</div>

			{/* Statistics Bar - Horizontal under header */}
			{showStats && (
				<div className="border-b border-orange-200 bg-white shadow-lg">
					<div className="px-6 py-3">
						<div className="flex items-center justify-between gap-6">
							{/* Left Section - Key Metrics */}
							<div className="flex items-center gap-6">
								{/* Total Nodes */}
								<div className="flex items-center gap-3">
									<div className="rounded-lg border border-orange-300 bg-white p-2">
										<Activity className="h-5 w-5 text-orange-600" />
									</div>
									<div>
										<p className="text-xs text-[color:var(--color-text-muted)]">
											Total Nodes
										</p>
										<p className="text-lg font-bold text-slate-900">
											{stats.totalNodes}
										</p>
									</div>
								</div>

								{/* Success Rate with Visual Bar */}
								<div className="flex items-center gap-3">
									<div className="rounded-lg border border-emerald-300 bg-white p-2">
										<TrendingUp className="w-5 h-5 text-[#0DA931]" />
									</div>
									<div>
										<p className="text-xs text-[color:var(--color-text-muted)]">
											Success Rate
										</p>
										<div className="flex items-center gap-2">
											<p
												className={`text-lg font-bold ${
													stats.successRate === 100
														? "text-[#0DA931]"
														: stats.successRate >= 50
															? "text-orange-600"
															: "text-red-400"
												}`}
											>
												{stats.successRate.toFixed(0)}%
											</p>
											<div className="w-24 h-2 bg-[color:var(--color-border)] rounded-full overflow-hidden">
												<div
													className={`h-full transition-all duration-500 ${
														stats.successRate === 100
															? "bg-[#0DA931]"
															: stats.successRate >= 50
																? "bg-orange-500"
																: "bg-red-500"
													}`}
													style={{ width: `${stats.successRate}%` }}
												/>
											</div>
										</div>
									</div>
								</div>

								{/* Duration */}
								<div className="flex items-center gap-3">
									<div className="rounded-lg border border-slate-300 bg-white p-2">
										<Clock className="w-5 h-5 text-[color:var(--color-text-muted)]" />
									</div>
									<div>
										<p className="text-xs text-[color:var(--color-text-muted)]">
											Duration
										</p>
										<p className="text-lg font-bold text-slate-900">
											{formatExecutionDuration(execution.duration_seconds)}
										</p>
									</div>
								</div>
							</div>

							{/* Center Section - Node Status */}
							<div className="flex items-center gap-4">
								<div className="flex items-center gap-2">
									<div className="w-2 h-2 bg-[#0DA931] rounded-full" />
									<span className="text-xs text-[color:var(--color-text-muted)]">
										Completed
									</span>
									<span className="text-sm font-semibold text-[#0DA931]">
										{stats.completedNodes}
									</span>
								</div>

								{stats.failedNodes > 0 && (
									<div className="flex items-center gap-2">
										<div className="w-2 h-2 bg-red-500 rounded-full" />
										<span className="text-xs text-[color:var(--color-text-muted)]">
											Failed
										</span>
										<span className="text-sm font-semibold text-red-400">
											{stats.failedNodes}
										</span>
									</div>
								)}

								{stats.skippedNodes > 0 && (
									<div className="flex items-center gap-2">
										<div className="w-2 h-2 bg-[color:var(--color-text-muted)] rounded-full" />
										<span className="text-xs text-[color:var(--color-text-muted)]">
											Skipped
										</span>
										<span className="text-sm font-semibold text-[color:var(--color-text-muted)]">
											{stats.skippedNodes}
										</span>
									</div>
								)}
							</div>

							{/* Right Section - Longest Node Info */}
							{stats.longestNode && (
								<div className="flex items-center gap-3 ml-auto">
									<div className="rounded-lg border border-orange-300 bg-white p-2">
										<AlertTriangle className="h-5 w-5 text-orange-600" />
									</div>
									<div className="text-right">
										<p className="text-xs text-[color:var(--color-text-muted)]">
											Longest Node
										</p>
										<p
											className="max-w-[200px] truncate text-sm font-medium text-slate-900"
											title={stats.longestNode.node_name}
										>
											{stats.longestNode.node_name}
										</p>
										<p className="text-xs text-orange-700">
											{formatExecutionDuration(
												stats.longestNode.duration_seconds,
											)}
										</p>
									</div>
								</div>
							)}
						</div>
					</div>
				</div>
			)}

			{/* Main Content */}
			<GraphCanvas
				wrapperClassName="flex-1 relative"
				nodes={nodes}
				edges={edges}
				nodeTypes={executionNodeTypes}
				edgeTypes={builderEdgeTypes}
				defaultEdgeOptions={defaultSmoothEdgeOptions}
				onNodeDoubleClick={onNodeDoubleClick}
				fitView
				className="bg-white"
				isReadOnly
				flowExtras={
					<>
						<CustomZoomControls />
						<CustomMinimap
							className="!overflow-hidden !rounded-2xl !border-2 !border-orange-300 !bg-white !shadow-2xl"
							nodeColor={getNodeColor}
							maskColor="rgba(30, 30, 30, 0.4)"
							maskStrokeColor="rgba(var(--color-primary-rgb), 0.5)"
							maskStrokeWidth={2}
							nodeBorderRadius={4}
							width={200}
							height={150}
						/>
						<Background gap={12} size={1} color="#4B5563" />
					</>
				}
				overlays={
					<div className="absolute bottom-4 right-4 max-w-xs rounded-lg border border-orange-300 bg-white px-3 py-2 shadow-lg">
						<p className="text-xs text-[color:var(--color-text-muted)] mb-2">
							Double-click on any node to view its execution details
						</p>
						<div className="text-xs space-y-2">
							<div>
								<p className="text-[color:var(--color-text-muted)] font-medium mb-1">
									Path Highlighting:
								</p>
								<div className="flex items-center gap-2 mb-1">
									<div className="w-3 h-0.5 bg-[#0DA931]"></div>
									<span className="text-[color:var(--color-text-muted)]">
										Path taken by condition nodes
									</span>
								</div>
								<div className="flex items-center gap-2">
									<div className="w-3 h-0.5 bg-[color:var(--color-text-muted)] opacity-30"></div>
									<span className="text-[color:var(--color-text-muted)]">
										Path not taken
									</span>
								</div>
							</div>
							<div className="pt-2 border-t border-[color:var(--color-border)]">
								<p className="text-[color:var(--color-text-muted)] font-medium mb-1">
									Controls:
								</p>
								<p className="text-[color:var(--color-text-muted)]">
									• Mouse wheel to zoom
								</p>
								<p className="text-[color:var(--color-text-muted)]">
									• Drag to pan
								</p>
							</div>
						</div>
					</div>
				}
			/>

			{/* Execution Panels - Rendered via shared hook */}
			{renderExecutionPanels()}
		</div>
	);
}
