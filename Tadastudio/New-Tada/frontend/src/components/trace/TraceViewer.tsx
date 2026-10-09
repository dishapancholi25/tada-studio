"use client";

import {
	ChevronLeft,
	ChevronRight,
	Clock,
	DollarSign,
	ExternalLink,
	Eye,
	EyeOff,
	Filter,
	Hash,
	RefreshCw,
	Search,
	ShieldAlert,
	Zap,
} from "lucide-react";
import React, {
	forwardRef,
	useCallback,
	useEffect,
	useImperativeHandle,
	useMemo,
	useState,
} from "react";
import { useNotification } from "@/contexts/NotificationContext";
import { api } from "@/lib/api";
import type { ExecutionGuardrailViolation } from "@/types/guardrail-policies";
import { usePhoenixConfig, usePhoenixProjectUrl, sanitizeProjectName } from "@/lib/phoenix-url";
import { traceStyles } from "./styles/traceStyles";
import TraceDetails from "./TraceDetails";
import TraceMetadataPanel from "./TraceMetadataPanel";
import TraceStats from "./TraceStats";
import TraceTree from "./TraceTree";

interface TraceViewerProps {
	executionId: string;
	onClose?: () => void;
	initialMode?: "standalone" | "embedded";
	onLoadingChange?: (isLoading: boolean) => void;
	onStatusChange?: (status: string) => void;
	suppressLoader?: boolean;
	showStats?: boolean;
	autoRefresh?: boolean;
}

export interface TraceViewerHandle {
	refresh: () => void;
}

interface TraceData {
	executionId: string;
	graphName: string;
	status: string;
	startTime: string | null;
	endTime: string | null;
	duration: number;
	nodes: TraceNode[];
	metadata: {
		totalNodes: number;
		totalTokens: number;
		totalCost: number;
		nodeTypeCounts: Record<string, number>;
		inputData: any;
		outputData: any;
		error: string | null;
	};
}

interface TraceNode {
	id: string;
	name: string;
	type:
		| "agent"
		| "tool"
		| "llm"
		| "condition"
		| "orchestrator"
		| "subgraph"
		| "human"
		| "start"
		| "end"
		| "checkpoint"
		| "unknown";
	status: "pending" | "running" | "completed" | "failed";
	startTime: string | null;
	endTime: string | null;
	duration: number | null;
	executionOrder: number;
	children: TraceNode[];
	metadata: any;
	input: any;
	output: any;
	error: string | null;
	messages?: any[];
}

const TraceViewer = forwardRef<TraceViewerHandle, TraceViewerProps>(
	function TraceViewer(
		{
			executionId,
			initialMode = "embedded",
			onLoadingChange,
			onStatusChange,
			suppressLoader = false,
			showStats: showStatsProp,
			autoRefresh = false,
		},
		ref,
	) {
	const [traceData, setTraceData] = useState<TraceData | null>(null);
	const [selectedNode, setSelectedNode] = useState<TraceNode | null>(null);
	const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
	const [searchQuery, setSearchQuery] = useState("");
	const [filterType, setFilterType] = useState<string>("all");
	const [leftPanelWidth, setLeftPanelWidth] = useState(420);
	const [isDragging, setIsDragging] = useState(false);
	const [isFullscreen] = useState(
		initialMode === "standalone",
	);
	const [isLoading, setIsLoading] = useState(true);
	const [showStatsInternal] = useState(false);
	const showStats = showStatsProp ?? showStatsInternal;
	const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(
		null,
	);
	const [violations, setViolations] = useState<ExecutionGuardrailViolation[]>([]);
	const { showNotification } = useNotification();
	const phoenixConfig = usePhoenixConfig();
	const phoenixProjectName = traceData?.graphName ? sanitizeProjectName(traceData.graphName) : null;
	const phoenixProjectUrl = usePhoenixProjectUrl(phoenixConfig, phoenixProjectName);

	console.log("[TraceViewer] Render state:", {
		executionId,
		isLoading,
		suppressLoader,
		hasTraceData: !!traceData,
		hasOnLoadingChange: !!onLoadingChange,
	});

	// Fetch trace data from API and update state
	const fetchTraceData = useCallback(async (silent: boolean) => {
		try {
			if (!silent) {
				setIsLoading(true);
			}
			const data = await api.get(
				`/api/trace/${encodeURIComponent(executionId)}/tree`,
			);
			setTraceData(data);

			// Auto-expand first few levels on initial load
			if (data.nodes && !expandedNodes.size) {
				const nodesToExpand = new Set<string>();
				const expandToLevel = (
					nodes: TraceNode[],
					level: number,
					maxLevel: number,
				) => {
					if (level >= maxLevel) return;
					nodes.forEach((node) => {
						if (node.children && node.children.length > 0) {
							nodesToExpand.add(node.id);
							expandToLevel(node.children, level + 1, maxLevel);
						}
					});
				};
				expandToLevel(data.nodes, 0, 4);
				setExpandedNodes(nodesToExpand);
			}

			if (!silent) {
				setIsLoading(false);
			}
		} catch (error) {
			console.error("[TraceViewer] Failed to load trace data:", error);
			showNotification("error", "Failed to load trace data");
			if (!silent) {
				setIsLoading(false);
			}
		}
	}, [executionId, showNotification]);

	// Initial load (with loading state)
	const loadTraceData = useCallback(() => fetchTraceData(false), [fetchTraceData]);

	// Silent refresh (data only, no loading overlay)
	const refreshTraceData = useCallback(() => fetchTraceData(true), [fetchTraceData]);

	useImperativeHandle(ref, () => ({
		refresh: refreshTraceData,
	}), [refreshTraceData]);

	// Fetch violations for the execution
	useEffect(() => {
		api.getExecutionGuardrailViolations(executionId)
			.then(setViolations)
			.catch(() => setViolations([]));
	}, [executionId]);

	// Initial load
	useEffect(() => {
		loadTraceData();
	}, [loadTraceData]);

	// Auto-refresh
	useEffect(() => {
		if (autoRefresh && traceData?.status === "running") {
			const interval = setInterval(refreshTraceData, 2000);
			setRefreshInterval(interval);
			return () => clearInterval(interval);
		} else if (refreshInterval) {
			clearInterval(refreshInterval);
			setRefreshInterval(null);
		}
	}, [autoRefresh, traceData?.status, refreshTraceData]);

	// Notify parent when execution status changes
	useEffect(() => {
		if (traceData?.status) {
			onStatusChange?.(traceData.status);
		}
	}, [traceData?.status, onStatusChange]);

	// Toggle node expansion
	const toggleNode = useCallback((nodeId: string) => {
		setExpandedNodes((prev) => {
			const next = new Set(prev);
			if (next.has(nodeId)) {
				next.delete(nodeId);
			} else {
				next.add(nodeId);
			}
			return next;
		});
	}, []);

	// Expand/collapse all nodes
	const expandAll = useCallback(() => {
		const allNodeIds = new Set<string>();
		const collectIds = (nodes: TraceNode[]) => {
			nodes.forEach((node) => {
				allNodeIds.add(node.id);
				if (node.children) collectIds(node.children);
			});
		};
		if (traceData?.nodes) collectIds(traceData.nodes);
		setExpandedNodes(allNodeIds);
	}, [traceData]);

	const collapseAll = useCallback(() => {
		setExpandedNodes(new Set());
	}, []);

	const { expandButtonActive, collapseButtonActive } = useMemo(() => {
		if (!traceData?.nodes?.length) {
			return { expandButtonActive: false, collapseButtonActive: false };
		}
		const allIds = new Set<string>();
		const collect = (nodes: TraceNode[]) => {
			for (const node of nodes) {
				allIds.add(node.id);
				if (node.children?.length) collect(node.children);
			}
		};
		collect(traceData.nodes);
		if (allIds.size === 0) {
			return { expandButtonActive: false, collapseButtonActive: false };
		}
		const everyExpanded = [...allIds].every((id) => expandedNodes.has(id));
		const fullyCollapsed = expandedNodes.size === 0;
		return {
			expandButtonActive: everyExpanded,
			collapseButtonActive: fullyCollapsed && !everyExpanded,
		};
	}, [traceData?.nodes, expandedNodes]);

	// Filter nodes
	const filteredNodes = useMemo(() => {
		if (!traceData?.nodes) return [];

		const filterNode = (node: TraceNode): TraceNode | null => {
			// Check type filter
			if (filterType !== "all" && node.type !== filterType) {
				// Still check children
				const filteredChildren = node.children
					?.map(filterNode)
					.filter(Boolean) as TraceNode[];

				if (filteredChildren?.length > 0) {
					return { ...node, children: filteredChildren };
				}
				return null;
			}

			// Check search query
			if (searchQuery) {
				const query = searchQuery.trim().toLowerCase();
				const matches =
					node.name.toLowerCase().includes(query) ||
					node.type.toLowerCase().includes(query) ||
					JSON.stringify(node.input).toLowerCase().includes(query) ||
					JSON.stringify(node.output).toLowerCase().includes(query);

				if (!matches) {
					const filteredChildren = node.children
						?.map(filterNode)
						.filter(Boolean) as TraceNode[];

					if (filteredChildren?.length > 0) {
						return { ...node, children: filteredChildren };
					}
					return null;
				}
			}

			// Filter children
			const filteredChildren = node.children
				?.map(filterNode)
				.filter(Boolean) as TraceNode[];

			return { ...node, children: filteredChildren || [] };
		};

		return traceData.nodes.map(filterNode).filter(Boolean) as TraceNode[];
	}, [traceData, filterType, searchQuery]);

	// Build a map of node execution ID -> violations for tree/details
	const violationsByNodeId = useMemo(() => {
		const map = new Map<string, ExecutionGuardrailViolation[]>();
		for (const v of violations) {
			if (v.node_execution_id) {
				const list = map.get(v.node_execution_id) ?? [];
				list.push(v);
				map.set(v.node_execution_id, list);
			}
		}
		return map;
	}, [violations]);

	const handleSearchChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setSearchQuery(e.target.value);
		},
		[],
	);

	const handleFilterChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			setFilterType(e.target.value);
		},
		[],
	);

	// Resize handle drag logic
	const handleResizeStart = useCallback(
		(e: React.MouseEvent) => {
			e.preventDefault();
			setIsDragging(true);
			const startX = e.clientX;
			const startWidth = leftPanelWidth;

			const handleMouseMove = (moveEvent: MouseEvent) => {
				const newWidth = startWidth + (moveEvent.clientX - startX);
				setLeftPanelWidth(Math.max(180, Math.min(newWidth, 600)));
			};

			const handleMouseUp = () => {
				setIsDragging(false);
				document.removeEventListener("mousemove", handleMouseMove);
				document.removeEventListener("mouseup", handleMouseUp);
			};

			document.addEventListener("mousemove", handleMouseMove);
			document.addEventListener("mouseup", handleMouseUp);
		},
		[leftPanelWidth],
	);

	useEffect(() => {
		console.log("[TraceViewer] Loading state changed, notifying parent:", {
			isLoading,
			willNotifyParent: !!onLoadingChange,
		});
		onLoadingChange?.(isLoading);
	}, [isLoading, onLoadingChange]);

	if (isLoading) {
		console.log(
			"[TraceViewer] Rendering loading state, suppressLoader:",
			suppressLoader,
		);
		if (suppressLoader) {
			return null;
		}
		return (
			<div
				className={`flex items-center justify-center h-full ${traceStyles.panelGradient}`}
			>
				<div className="flex flex-col items-center gap-4">
					<div className={traceStyles.iconCapsule}>
						<RefreshCw className="h-4 w-4 animate-spin text-orange-600" />
					</div>
					<span className="text-sm text-slate-600">
						Loading trace data...
					</span>
				</div>
			</div>
		);
	}

	if (!traceData) {
		return (
			<div
				className={`flex items-center justify-center h-full ${traceStyles.panelGradient}`}
			>
				<div className="text-sm text-[color:var(--color-text-muted)]">
					No trace data available
				</div>
			</div>
		);
	}

	const outlineExpandCollapseButton =
		"rounded-[4px] border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium capitalize tracking-wide text-slate-700 transition-all duration-200 hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30";
	const activeExpandCollapseButton =
		"rounded-[4px] border border-orange-500 bg-orange-500 px-3 py-1.5 text-xs font-medium capitalize tracking-wide text-white transition-all duration-200 hover:border-orange-600 hover:bg-orange-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30";

	return (
		<div
			className={`trace-viewer flex flex-col ${traceStyles.panelGradient} ${
				isFullscreen ? "fixed inset-0 z-50" : "h-screen"
			}`}
		>
			{/* Summary Stats Bar */}
			<div
				className={`flex flex-wrap items-center gap-4 lg:gap-6 px-6 py-3 border-b ${traceStyles.divider} ${traceStyles.statsBarGradient}`}
			>
				<div className={traceStyles.statPill}>
					<Clock className="h-4 w-4 text-orange-600" />
					<span className={traceStyles.inlineLabel}>Duration</span>
					<span className="text-sm font-mono font-medium text-gray-800">
						{traceData.duration
							? `${(traceData.duration || 0).toFixed(2)}s`
							: "N/A"}
					</span>
				</div>

				<div className={traceStyles.statPill}>
					<Hash className="h-4 w-4 text-orange-600" />
					<span className={traceStyles.inlineLabel}>Nodes</span>
					<span className="text-sm font-mono font-medium text-gray-800">
						{traceData.metadata.totalNodes}
					</span>
				</div>

				{traceData.metadata.totalTokens > 0 && (
					<div className={traceStyles.statPill}>
						<Zap className="h-4 w-4 text-orange-600" />
						<span className={traceStyles.inlineLabel}>Tokens</span>
						<span className="text-sm font-mono font-medium text-gray-800">
							{traceData.metadata.totalTokens.toLocaleString()}
						</span>
					</div>
				)}

				{traceData.metadata.totalCost > 0 && (
					<div className={traceStyles.statPill}>
						<DollarSign className="h-4 w-4 text-orange-600" />
						<span className={traceStyles.inlineLabel}>Cost</span>
						<span className="font-mono text-sm font-medium text-orange-800">
							${(traceData.metadata.totalCost || 0).toFixed(4)}
						</span>
					</div>
				)}

				{violations.length > 0 && (
					<div className="flex items-center gap-2.5 rounded-[4px] border border-red-200 bg-white px-3 py-1.5">
						<ShieldAlert className="h-4 w-4 text-red-600" />
						<span className={traceStyles.inlineLabel}>Violations</span>
						<span className="font-mono text-sm font-medium text-red-800">
							{violations.length}
						</span>
					</div>
				)}
			</div>

			{/* Toolbar */}
			<div
				className={`flex flex-wrap items-center gap-4 border-b px-6 py-3 ${traceStyles.divider} bg-white`}
			>
				<div className="flex items-center gap-2">
					<button
						type="button"
						onClick={expandAll}
						className={
							expandButtonActive
								? activeExpandCollapseButton
								: outlineExpandCollapseButton
						}
					>
						<Eye className="w-3.5 h-3.5 inline mr-1.5" />
						Expand All
					</button>
					<button
						type="button"
						onClick={collapseAll}
						className={
							collapseButtonActive
								? activeExpandCollapseButton
								: outlineExpandCollapseButton
						}
					>
						<EyeOff className="w-3.5 h-3.5 inline mr-1.5" />
						Collapse All
					</button>
				</div>

				{/* Search */}
				<div className="flex-1 max-w-md">
					<div className="relative">
						<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
						<input
							type="text"
							value={searchQuery}
							onChange={handleSearchChange}
							placeholder="Search nodes..."
							aria-label="Search trace nodes"
							className={`w-full pl-9 pr-3 py-2 text-sm ${traceStyles.searchInput} focus:outline-none`}
						/>
					</div>
				</div>

				{/* Type Filter */}
				<div className="flex items-center gap-2">
					<Filter className="h-4 w-4 text-slate-600" />
					<select
						value={filterType}
						onChange={handleFilterChange}
						className="rounded-[4px] border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 transition-all duration-200 hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/20"
					>
						<option value="all">All Types</option>
						<option value="agent">Agents</option>
						<option value="tool">Tools</option>
						<option value="llm">LLM Calls</option>
						<option value="condition">Conditions</option>
						<option value="orchestrator">Orchestrators</option>
					</select>
				</div>

				{phoenixProjectUrl && (
						<a
							href={phoenixProjectUrl}
							target="_blank"
							rel="noopener noreferrer"
							className="inline-flex items-center gap-1.5 rounded-[4px] px-3 py-1.5 text-xs font-medium capitalize tracking-wide text-slate-700 transition-all duration-200 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30"
						>
							<ExternalLink className="w-3.5 h-3.5" />
							Open in Phoenix
						</a>
					)}
			</div>

			{/* Main Content */}
			<div
				className={`flex-1 flex overflow-hidden ${traceStyles.panelGradient} ${isDragging ? "select-none" : ""}`}
			>
				{/* Left Panel: Tree View */}
				<div
					className="flex flex-col shrink-0"
					style={{ width: leftPanelWidth }}
					data-tutorial="trace-tree-panel"
				>
					<div className="flex-1 overflow-auto custom-scrollbar">
						<TraceTree
							nodes={filteredNodes}
							expandedNodes={expandedNodes}
							selectedNode={selectedNode}
							onToggleNode={toggleNode}
							onSelectNode={setSelectedNode}
							searchQuery={searchQuery}
							violationsByNodeId={violationsByNodeId}
						/>
					</div>
				</div>

				{/* Resize Handle */}
				<div
					onMouseDown={handleResizeStart}
					className={`w-1 shrink-0 cursor-col-resize transition-colors ${
						isDragging
							? "bg-[color:var(--color-accent)]"
							: `bg-[color:var(--color-border)]/60 hover:bg-[color:var(--color-accent)]/60`
					}`}
				/>

				{/* Middle Panel: Node Details */}
				<div className={`flex-1 min-w-0 border-r ${traceStyles.divider} flex flex-col`} data-tutorial="trace-details-panel">
					<div className="flex-1 overflow-auto custom-scrollbar">
						{selectedNode ? (
							<TraceDetails node={selectedNode} executionId={executionId} violations={violationsByNodeId.get(selectedNode.id)} />
						) : (
							<div className="flex flex-col items-center justify-center h-full gap-3">
								<div className={`${traceStyles.iconCapsuleSm} opacity-50`}>
									<ChevronLeft className="w-3 h-3 text-[color:var(--color-text-muted)]" />
								</div>
								<span className="text-sm text-[color:var(--color-text-muted)]">
									Select a node to view details
								</span>
							</div>
						)}
					</div>
				</div>

				{/* Right Panel: Metadata/Stats */}
				<div className="flex w-1/3 min-w-[220px] max-w-[320px] flex-col lg:min-w-[280px] lg:max-w-[420px]">
					<div className="min-w-0 flex-1 overflow-auto custom-scrollbar">
						{showStats ? (
							<TraceStats executionId={executionId} traceData={traceData} />
						) : selectedNode ? (
							<TraceMetadataPanel node={selectedNode} />
						) : (
							<div className="flex flex-col items-center justify-center h-full gap-3">
								<div className={`${traceStyles.iconCapsuleSm} opacity-50`}>
									<ChevronRight className="w-3 h-3 text-[color:var(--color-text-muted)]" />
								</div>
								<span className="text-sm text-[color:var(--color-text-muted)]">
									Select a node to view metadata
								</span>
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	);
	},
);

export default TraceViewer;
