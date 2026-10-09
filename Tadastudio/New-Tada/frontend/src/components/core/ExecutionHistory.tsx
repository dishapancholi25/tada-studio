import { formatDistanceToNow } from "date-fns";
import {
	AlertCircle,
	CheckCircle,
	ChevronDown,
	ChevronRight,
	Clock,
	Eye,
	FileText,
	GitBranch,
	Play,
	RefreshCw,
	Search,
	Square,
} from "lucide-react";
import { useRouter } from "next/navigation";
import type React from "react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import Button from "@/components/ui/Button";
import FormInput from "@/components/ui/FormInput";
import { api } from "@/lib/api";

import type {
	GraphExecution as GraphExecutionType,
	NodeExecution as NodeExecutionType,
} from "@/types/api";

// Use type aliases for backward compatibility
type NodeExecution = NodeExecutionType;
type GraphExecution = GraphExecutionType;

const ExecutionHistory = memo(function ExecutionHistory() {
	const router = useRouter();
	const [executions, setExecutions] = useState<GraphExecution[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [searchTerm, setSearchTerm] = useState("");
	const [statusFilter, setStatusFilter] = useState<string>("all");
	const [expandedExecutions, setExpandedExecutions] = useState<Set<string>>(
		new Set(),
	);

	// Fetch execution history
	const fetchExecutions = async () => {
		try {
			setLoading(true);
			setError(null);
			const data = await api.get("/api/execution-history/executions?limit=50");
			// console.log('[ExecutionHistory] Fetched executions:', data);
			setExecutions(Array.isArray(data) ? data : []);
		} catch (err) {
			// console.error('[ExecutionHistory] Failed to fetch executions:', err);
			setError(
				err instanceof Error
					? err.message
					: "Failed to fetch execution history",
			);
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		fetchExecutions().catch((error) => {
			console.error("Failed to fetch execution history:", error);
		});
	}, []);

	// Memoize filtered executions for better performance
	const filteredExecutions = useMemo(() => {
		return executions.filter((execution) => {
			const matchesSearch =
				searchTerm === "" ||
				execution.graph_name.toLowerCase().includes(searchTerm.trim().toLowerCase()) ||
				execution.id.toLowerCase().includes(searchTerm.trim().toLowerCase());

			const matchesStatus =
				statusFilter === "all" || execution.status === statusFilter;

			return matchesSearch && matchesStatus;
		});
	}, [executions, searchTerm, statusFilter]);

	const toggleExpanded = useCallback((executionId: string) => {
		setExpandedExecutions((prev) => {
			const newExpanded = new Set(prev);
			if (newExpanded.has(executionId)) {
				newExpanded.delete(executionId);
			} else {
				newExpanded.add(executionId);
			}
			return newExpanded;
		});
	}, []);

	const getStatusIcon = (status: string) => {
		switch (status) {
			case "completed":
				return <CheckCircle className="w-4 h-4 text-[#0DA931]" />;
			case "failed":
				return <AlertCircle className="w-4 h-4 text-red-500" />;
			case "running":
				return (
					<Play className="w-4 h-4 text-[color:var(--color-accent)] animate-pulse" />
				);
			default:
				return (
					<Clock className="w-4 h-4 text-[color:var(--color-text-muted)]" />
				);
		}
	};

	const getStatusColor = (status: string) => {
		switch (status) {
			case "completed":
				return "text-[#0DA931] bg-[#0DA931]/10";
			case "failed":
				return "text-red-400 bg-red-400/10";
			case "running":
				return "text-[color:var(--color-accent)] bg-[color:var(--color-accent)]/15";
			default:
				return "text-[color:var(--color-text-muted)] bg-[color:var(--color-text-muted)]/10";
		}
	};

	const formatDuration = (seconds?: number | null) => {
		if (seconds === null || seconds === undefined) return "-";
		if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
		if (seconds < 60) return `${seconds.toFixed(1)}s`;
		return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
	};

	const formatTimestamp = (timestamp: string | null | undefined) => {
		if (!timestamp) return "Unknown";
		try {
			return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
		} catch {
			return new Date(timestamp).toLocaleString();
		}
	};

	const getWorkflowIdentifier = (execution: GraphExecution) => {
		if (execution.workflow_id) {
			return execution.workflow_id;
		}
		return encodeURIComponent(execution.graph_id);
	};

	const viewEnhancedExecution = (execution: GraphExecution) => {
		// Navigate to the new URL structure: /workflow/[workflowId]/[executionId]
		// Pass return=executions to indicate we should return to executions page
		const workflowIdentifier = getWorkflowIdentifier(execution);
		router.push(
			`/workflow/${workflowIdentifier}/${execution.id}?return=executions`,
		);
	};

	const viewExecutionGraph = (execution: GraphExecution) => {
		// Navigate to the graph view: /workflow/[workflowId]/[executionId]/graph
		// Pass return=executions to indicate we should return to executions page
		const workflowIdentifier = getWorkflowIdentifier(execution);
		router.push(
			`/workflow/${workflowIdentifier}/${execution.id}/graph?return=executions`,
		);
	};

	// useCallback handlers for event handling optimization
	const handleSearchChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setSearchTerm(e.target.value);
		},
		[],
	);

	const handleStatusFilterChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			setStatusFilter(e.target.value);
		},
		[],
	);

	// Factory functions for dynamic handlers
	const createToggleExpandedHandler = useCallback(
		(executionId: string) => () => {
			toggleExpanded(executionId);
		},
		[],
	);

	const createViewEnhancedHandler = useCallback(
		(execution: GraphExecution) => (e: React.MouseEvent) => {
			e.stopPropagation();
			viewEnhancedExecution(execution);
		},
		[],
	);

	const createViewGraphHandler = useCallback(
		(execution: GraphExecution) => (e: React.MouseEvent) => {
			e.stopPropagation();
			viewExecutionGraph(execution);
		},
		[],
	);

	if (loading) {
		return (
			<div className="h-full bg-transparent text-slate-700 flex items-center justify-center">
				<div className="text-center">
					<RefreshCw className="w-8 h-8 text-[color:var(--color-accent)] animate-spin mx-auto mb-2" />
					<p className="text-[color:var(--color-text-muted)]">
						Loading execution history...
					</p>
				</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="h-full bg-transparent text-slate-700 flex items-center justify-center">
				<div className="text-center">
					<AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
					<p className="text-red-400 mb-2">Error loading execution history</p>
					<p className="text-[color:var(--color-text-muted)] text-sm mb-4">
						{error}
					</p>
					<button
						onClick={fetchExecutions}
						className="px-4 py-2 bg-[color:var(--color-primary)] hover:bg-[color:var(--color-primary-light)] btn-primary-text font-medium rounded-lg transition-colors"
					>
						Retry
					</button>
				</div>
			</div>
		);
	}

	return (
		<div className="h-full bg-transparent text-slate-700 flex flex-col">
			{/* Header */}
			<div className="p-6 border-b border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
				<div className="flex items-center justify-between mb-4">
					<h1 className="text-2xl font-bold text-slate-900">Execution History</h1>
					<Button
						onClick={fetchExecutions}
						icon={<RefreshCw className="w-4 h-4" />}
					>
						Refresh
					</Button>
				</div>

				{/* Search and Filters */}
				<div className="flex gap-4">
					<div className="flex-1 relative">
						<Search
							className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2"
							style={{ color: "var(--color-text-secondary)" }}
						/>
						<FormInput
							className="pl-10"
							placeholder="Search by graph name or execution ID..."
							value={searchTerm}
							onChange={handleSearchChange}
						/>
					</div>
					<select
						value={statusFilter}
						onChange={handleStatusFilterChange}
						className="px-4 py-2 rounded-lg focus:outline-none"
						style={{
							background: "var(--color-surface)",
							color: "var(--color-text-primary)",
							border: "1px solid var(--color-border)",
						}}
					>
						<option value="all">All Status</option>
						<option value="completed">Completed</option>
						<option value="failed">Failed</option>
						<option value="running">Running</option>
					</select>
				</div>
			</div>

			{/* Execution List */}
			<div className="flex-1 overflow-auto p-6">
				{filteredExecutions.length === 0 ? (
					<div className="text-center py-12">
						<FileText className="w-12 h-12 text-[color:var(--color-text-muted)] mx-auto mb-4" />
						<p className="text-[color:var(--color-text-muted)] mb-2">
							No execution history found
						</p>
						<p className="text-[color:var(--color-text-muted)] text-sm">
							{searchTerm || statusFilter !== "all"
								? "Try adjusting your search or filters"
								: "Execute some workflows to see their history here"}
						</p>
					</div>
				) : (
					<div className="space-y-4">
						{filteredExecutions.map((execution) => {
							const isExpanded = expandedExecutions.has(execution.id);
							const nodeExecs = execution.node_executions ?? [];
							const completedNodes = nodeExecs.filter(
								(ne) => ne.status === "completed",
							).length;
							const totalNodes = nodeExecs.length;

							return (
								<div
									key={execution.id}
									className="bg-[color:var(--color-surface)] rounded-lg overflow-hidden shadow-md border border-[color:var(--color-surface-hover)]"
								>
									{/* Execution Header */}
									<div className="p-4 cursor-pointer hover:bg-[color:var(--color-border)]/50 transition-colors">
										<div className="flex items-center justify-between">
											<div className="flex items-center gap-3">
												<button
													onClick={createToggleExpandedHandler(execution.id)}
													className="text-[color:var(--color-text-muted)] hover:text-slate-900 transition-colors"
												>
													{isExpanded ? (
														<ChevronDown className="w-4 h-4" />
													) : (
														<ChevronRight className="w-4 h-4" />
													)}
												</button>
												{getStatusIcon(execution.status)}
												<div>
													<h3 className="font-medium text-slate-900">
														{execution.graph_name}
													</h3>
													<p className="text-sm text-[color:var(--color-text-muted)]">
														ID: {execution.id}
													</p>
												</div>
											</div>

											<div className="flex items-center gap-4">
												<div className="text-right">
													<p className="text-sm text-[color:var(--color-text-muted)]">
														{formatTimestamp(execution.start_time)}
													</p>
													<p className="text-xs text-[color:var(--color-text-muted)]">
														Duration:{" "}
														{formatDuration(execution.duration_seconds)}
													</p>
												</div>

												<div className="flex items-center gap-2">
													<span
														className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(execution.status)}`}
													>
														{execution.status}
													</span>
													<span className="text-xs text-[color:var(--color-text-muted)]">
														{completedNodes}/{totalNodes} nodes
													</span>
												</div>

												<div className="flex items-center gap-1">
													<button
														onClick={createViewEnhancedHandler(execution)}
														className="p-2 text-[color:var(--color-text-muted)] hover:text-slate-900 hover:bg-[color:var(--color-border)] rounded transition-colors"
														title="View Enhanced Details"
													>
														<Eye className="w-4 h-4" />
													</button>
													<button
														onClick={createViewGraphHandler(execution)}
														className="p-2 text-[color:var(--color-text-muted)] hover:text-slate-900 hover:bg-[color:var(--color-border)] rounded transition-colors"
														title="View Graph"
													>
														<GitBranch className="w-4 h-4" />
													</button>
												</div>
											</div>
										</div>
									</div>

									{/* Expanded Content */}
									{isExpanded && (
										<div className="border-t border-[color:var(--color-surface-hover)] p-4 bg-[color:var(--color-bg-secondary)]">
											{/* Execution Metadata */}
											<div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 text-sm">
												<div>
													<p className="text-[color:var(--color-text-muted)]">
														Start Time
													</p>
													<p className="text-slate-900">
														{execution.start_time
															? new Date(execution.start_time).toLocaleString()
															: "Unknown"}
													</p>
												</div>
												{execution.end_time && (
													<div>
														<p className="text-[color:var(--color-text-muted)]">
															End Time
														</p>
														<p className="text-slate-900">
															{new Date(execution.end_time).toLocaleString()}
														</p>
													</div>
												)}
												{execution.user_id && (
													<div>
														<p className="text-[color:var(--color-text-muted)]">
															User
														</p>
														<p className="text-slate-900">{execution.user_id}</p>
													</div>
												)}
												<div>
													<p className="text-[color:var(--color-text-muted)]">
														Nodes Executed
													</p>
													<p className="text-slate-900">
														{completedNodes} of {totalNodes}
													</p>
												</div>
											</div>

											{/* Node Executions */}
											{(execution.node_executions ?? []).length > 0 && (
												<div>
													<h4 className="font-medium text-slate-900 mb-2">
														Node Executions
													</h4>
													<div className="space-y-2">
														{(execution.node_executions ?? [])
															.sort(
																(a, b) => a.execution_order - b.execution_order,
															)
															.map((nodeExec) => (
																<div
																	key={nodeExec.id}
																	className="bg-[color:var(--color-bg-secondary)] rounded p-3 flex items-center justify-between border border-[color:var(--color-surface-hover)]"
																>
																	<div className="flex items-center gap-3">
																		{getStatusIcon(nodeExec.status)}
																		<div>
																			<p className="text-slate-900 text-sm font-medium">
																				{nodeExec.node_name} (
																				{nodeExec.node_type})
																			</p>
																			<p className="text-xs text-[color:var(--color-text-muted)]">
																				Order: {nodeExec.execution_order} •
																				Duration:{" "}
																				{formatDuration(
																					nodeExec.duration_seconds,
																				)}
																			</p>
																		</div>
																	</div>
																	<span
																		className={`px-2 py-1 rounded text-xs ${getStatusColor(nodeExec.status)}`}
																	>
																		{nodeExec.status}
																	</span>
																</div>
															))}
													</div>
												</div>
											)}
										</div>
									)}
								</div>
							);
						})}
					</div>
				)}
			</div>
		</div>
	);
});

export default ExecutionHistory;
