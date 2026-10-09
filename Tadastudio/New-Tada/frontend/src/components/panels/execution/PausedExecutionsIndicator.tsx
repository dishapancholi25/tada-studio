"use client";

import {
	AlertCircle,
	ArrowRight,
	ChevronRight,
	Clock,
	Maximize2,
	Pause,
	Play,
	RefreshCw,
	Search,
	SlidersHorizontal,
	Sparkles,
	Trash2,
	Workflow,
	X,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import JsonViewerEnhanced from "@/components/JsonViewerEnhanced";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import Dropdown from "@/components/ui/Dropdown";
import StyledMarkdown from "@/components/utils/StyledMarkdown";
import { api } from "@/lib/api";
import type { ReviewInterruptPayload } from "@/types/review";
import ResumeExecutionDialog from "./ResumeExecutionDialog";
import ReviewResumeDialog from "./ReviewResumeDialog";

interface PausedExecutionsIndicatorProps {
	graphName: string;
	onSelectExecution: (
		executionId: string,
		threadId: string,
		dbExecutionId: string,
	) => void;
	className?: string;
}

interface PausedExecution {
	execution_id: string;
	thread_id: string;
	websocket_execution_id: string;
	graph_name: string;
	paused_at: string;
	checkpoint: {
		node_id: string;
		node_name: string;
		checkpoint_id: string;
		last_input: any;
		last_output?: any;
		type?: string; // "checkpoint" | "agent_review"
		review_payload?: ReviewInterruptPayload;
	} | null;
	progress: {
		completed_nodes: number;
		total_nodes: number;
		percentage: number;
	};
}

export default function PausedExecutionsIndicator({
	graphName,
	onSelectExecution,
	className = "",
}: PausedExecutionsIndicatorProps) {
	const [pausedExecutions, setPausedExecutions] = useState<PausedExecution[]>(
		[],
	);
	const [isLoading, setIsLoading] = useState(false);
	const [showList, setShowList] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [pagination, setPagination] = useState({
		skip: 0,
		limit: 20,
		total: 0,
		hasMore: false,
	});
	const [searchQuery, setSearchQuery] = useState("");
	const [sortBy, setSortBy] = useState<"newest" | "oldest" | "progress">(
		"newest",
	);
	const [hasInitialized, setHasInitialized] = useState(false);
	const [expandedInputs, setExpandedInputs] = useState<Set<string>>(new Set());
	const [resumeDialogState, setResumeDialogState] = useState<{
		isOpen: boolean;
		execution: PausedExecution | null;
	}>({ isOpen: false, execution: null });
	const [cancelConfirmState, setCancelConfirmState] = useState<{
		isOpen: boolean;
		execution: PausedExecution | null;
	}>({ isOpen: false, execution: null });

	// Fetch paused executions
	const fetchPausedExecutions = async (skip = 0) => {
		if (!graphName) return;

		setIsLoading(true);
		setError(null);

		try {
			const response = await api.getPausedExecutions(
				graphName,
				skip,
				pagination.limit,
			);

			if (skip === 0) {
				setPausedExecutions(response.executions || []);
			} else {
				setPausedExecutions((prev) => [
					...prev,
					...(response.executions || []),
				]);
			}

			setPagination({
				skip: response.pagination?.skip || 0,
				limit: response.pagination?.limit || 20,
				total: response.pagination?.total || 0,
				hasMore: response.pagination?.has_more || false,
			});

			if (!hasInitialized) {
				setHasInitialized(true);
			}
		} catch (err) {
			console.error("Failed to fetch paused executions:", err);
			setError("Failed to load paused executions");
			if (skip === 0) {
				setPausedExecutions([]);
			}
		} finally {
			setIsLoading(false);
			if (!hasInitialized) {
				setHasInitialized(true);
			}
		}
	};

	const loadMore = () => {
		if (!isLoading && pagination.hasMore) {
			void fetchPausedExecutions(pagination.skip + pagination.limit);
		}
	};

	// Fetch on mount and when graph changes
	useEffect(() => {
		fetchPausedExecutions().catch((error) => {
			console.error("Failed to fetch paused executions on mount:", error);
		});
	}, [graphName]);

	// Auto-refresh every 60 seconds (reduced from 30s for less backend load)
	useEffect(() => {
		const interval = setInterval(() => {
			fetchPausedExecutions().catch((error) => {
				console.error("Failed to auto-refresh paused executions:", error);
			});
		}, 60000);
		return () => clearInterval(interval);
	}, [graphName]);

	const formatTimeSince = (dateString: string) => {
		const date = new Date(dateString);
		const now = new Date();
		const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

		if (seconds < 60) return `${seconds}s ago`;
		const minutes = Math.floor(seconds / 60);
		if (minutes < 60) return `${minutes}m ago`;
		const hours = Math.floor(minutes / 60);
		if (hours < 24) return `${hours}h ago`;
		const days = Math.floor(hours / 24);
		return `${days}d ago`;
	};

	const toggleInputExpansion = (executionId: string) => {
		const newExpanded = new Set(expandedInputs);
		if (newExpanded.has(executionId)) {
			newExpanded.delete(executionId);
		} else {
			newExpanded.add(executionId);
		}
		setExpandedInputs(newExpanded);
	};

	const renderContent = (content: any) => {
		if (!content) return null;

		// Check if it's a string that might be markdown
		if (typeof content === "string") {
			// Simple heuristic for markdown detection
			const hasMarkdown =
				content.includes("#") ||
				content.includes("**") ||
				content.includes("*") ||
				content.includes("```") ||
				content.includes("[") ||
				content.includes("](");

			if (hasMarkdown) {
				return <StyledMarkdown content={content} className="text-xs" />;
			}

			// Plain text
			return (
				<div className="text-xs text-[color:var(--color-text-muted)] font-mono">
					{content.length > 150 && !expandedInputs.has("preview")
						? `${content.substring(0, 150)}...`
						: content}
				</div>
			);
		}

		// For objects/arrays, use the JSON viewer
		return (
			<div className="max-h-[200px] overflow-auto">
				<JsonViewerEnhanced data={content} maxHeight="200px" />
			</div>
		);
	};

	// Filter and sort executions
	const filteredAndSortedExecutions = useMemo(() => {
		let filtered = [...pausedExecutions];

		// Apply search filter
		if (searchQuery.trim()) {
			const query = searchQuery.toLowerCase();
			filtered = filtered.filter(
				(exec) =>
					exec.checkpoint?.node_name?.toLowerCase().includes(query) ||
					exec.thread_id?.toLowerCase().includes(query) ||
					exec.execution_id?.toLowerCase().includes(query) ||
					exec.graph_name?.toLowerCase().includes(query),
			);
		}

		// Apply sorting
		filtered.sort((a, b) => {
			switch (sortBy) {
				case "newest":
					return (
						new Date(b.paused_at).getTime() - new Date(a.paused_at).getTime()
					);
				case "oldest":
					return (
						new Date(a.paused_at).getTime() - new Date(b.paused_at).getTime()
					);
				case "progress":
					return b.progress.percentage - a.progress.percentage;
				default:
					return 0;
			}
		});

		return filtered;
	}, [pausedExecutions, searchQuery, sortBy]);

	const shouldHideIndicator =
		!hasInitialized || isLoading || pagination.total === 0;

	// useCallback handlers for event handling optimization
	const handleShowList = useCallback(() => {
		setShowList(true);
	}, []);

	const handleHideList = useCallback(() => {
		setShowList(false);
	}, []);

	const handleSearchChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setSearchQuery(e.target.value);
		},
		[],
	);

	const handleSortByChange = useCallback((value: string) => {
		setSortBy(value as typeof sortBy);
	}, []);

	const handleRefreshClick = useCallback(() => {
		fetchPausedExecutions(0).catch((error) => {
			console.error("Failed to refresh paused executions:", error);
		});
	}, []);

	const loadPausedExecutions = useCallback(async () => {
		return fetchPausedExecutions(0);
	}, []);

	const handleSelectExecution = useCallback(
		(execution: PausedExecution) => {
			onSelectExecution(
				execution.websocket_execution_id || execution.thread_id,
				execution.thread_id,
				execution.execution_id,
			);
			setShowList(false);
		},
		[onSelectExecution],
	);

	const handleResumeExecution = useCallback((execution: PausedExecution) => {
		setResumeDialogState({
			isOpen: true,
			execution: execution,
		});
	}, []);

	// Factory function for toggle input expansion handlers
	const createToggleInputExpansionHandler = useCallback(
		(executionId: string) => () => {
			toggleInputExpansion(executionId);
		},
		[],
	);

	// Factory function for select execution handlers
	const createSelectExecutionHandler = useCallback(
		(execution: PausedExecution) => (e: React.MouseEvent) => {
			e.stopPropagation();
			e.preventDefault();
			handleSelectExecution(execution);
		},
		[handleSelectExecution],
	);

	// Factory function for resume execution handlers
	const createResumeExecutionHandler = useCallback(
		(execution: PausedExecution) => (e: React.MouseEvent) => {
			e.stopPropagation();
			handleResumeExecution(execution);
		},
		[handleResumeExecution],
	);

	// Factory function for cancel execution handlers
	const createCancelExecutionHandler = useCallback(
		(execution: PausedExecution) => (e: React.MouseEvent) => {
			e.stopPropagation();
			setCancelConfirmState({ isOpen: true, execution });
		},
		[],
	);

	// Handle confirmed cancel
	const handleConfirmCancel = useCallback(async () => {
		const execution = cancelConfirmState.execution;
		if (!execution) return;
		
		setCancelConfirmState({ isOpen: false, execution: null });
		
		try {
			// Optimistically remove from UI
			setPausedExecutions((prev) =>
				prev.filter((exec) => exec.execution_id !== execution.execution_id),
			);

			// Update pagination count
			setPagination((prev) => ({
				...prev,
				total: Math.max(0, prev.total - 1),
			}));

			// Make API call
			await api.cancelPausedExecution(execution.execution_id);

			// Optional: Do a silent refresh in background after a delay
			setTimeout(() => {
				fetchPausedExecutions(0).catch((error) => {
					console.error("Failed to refresh after cancel:", error);
				});
			}, 2000);
		} catch (error) {
			console.error("Failed to cancel execution:", error);
			// Revert optimistic update on error
			fetchPausedExecutions(0).catch((error) => {
				console.error("Failed to revert optimistic update:", error);
			});
		}
	}, [cancelConfirmState.execution]);

	if (shouldHideIndicator) {
		return null;
	}

	return (
		<>
			{/* Indicator Badge - Design System Aligned */}
			<button
				onClick={handleShowList}
				className={`group flex items-center gap-2.5 px-4 py-2.5
					rounded-full border border-[color:var(--color-warning)]/45
					bg-[color:var(--color-warning)]/12
					text-[color:var(--color-warning)]
					hover:border-[color:var(--color-warning)]/60 hover:bg-[color:var(--color-warning)]/18
					transition-all duration-300
					hover:shadow-[0_0_30px_rgba(251,191,36,0.25)]
					focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-warning)]/45
					${className}`}
				title={`${pagination.total || pausedExecutions.length} paused execution${(pagination.total || pausedExecutions.length) > 1 ? "s" : ""}`}
			>
				<div className="relative">
					<Pause className="w-4 h-4" />
					<div className="absolute -top-1 -right-1 w-2 h-2 bg-[color:var(--color-warning)] rounded-full animate-pulse" />
				</div>
				<span className="font-bold text-sm">
					{pagination.total || pausedExecutions.length}
				</span>
				<span className="text-xs opacity-90 font-medium">Paused</span>
				<ChevronRight className="w-3 h-3 opacity-60 group-hover:translate-x-0.5 transition-transform" />
			</button>

				{/* Paused Executions List Modal - Design System Aligned */}
			{showList && (
				<div
						className="fixed inset-0 z-[110] flex items-center justify-center bg-black/40 backdrop-blur-sm px-4 py-8"
					onClick={handleHideList}
				>
					{/* Gradient border wrapper - creates "glass halo" effect */}
					<div
							className="w-full max-w-5xl max-h-[90vh] rounded-[32px] p-[1px] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.3)] via-transparent to-[rgba(var(--color-primary-rgb),0.12)] shadow-[0_35px_120px_rgba(0,0,0,0.25)]"
						onClick={(e) => e.stopPropagation()}
					>
						{/* Inner shell */}
							<div className="rounded-[30px] border border-[color:var(--color-border)] bg-[color:var(--color-surface)] overflow-hidden flex flex-col max-h-[90vh]">
							{/* Header - Design System Aligned */}
								<div className="flex flex-wrap items-center gap-4 border-b border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] px-6 py-5">
								{/* Icon capsule */}
									<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[color:var(--color-warning)]/35 bg-[color:var(--color-warning)]/12 shadow-[0_0_30px_rgba(251,191,36,0.15)]">
									<Pause className="h-5 w-5 text-[color:var(--color-warning)]" />
								</div>

								<div className="flex-1">
									{/* Section label */}
									<p className="text-[0.65rem] capitalize text-[color:var(--color-text-muted)] font-semibold">
										Paused Executions
									</p>
									{/* Title */}
										<h2 className="text-2xl font-semibold text-[color:var(--color-text-primary)]">
										{graphName}
									</h2>
								</div>

								{/* Status badge */}
								<span className="inline-flex items-center gap-2 rounded-full border border-[color:var(--color-warning)]/45 bg-[color:var(--color-warning)]/12 px-3 py-1.5 text-[11px] font-medium text-[color:var(--color-warning)]">
									{pausedExecutions.length} Active
								</span>

								{/* Close button */}
								<button
									onClick={handleHideList}
										className="rounded-xl border border-[color:var(--color-border)] p-2 text-[color:var(--color-text-secondary)] transition hover:border-[rgba(var(--color-primary-rgb),0.5)] hover:text-[color:var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
									aria-label="Close paused executions panel"
								>
									<X className="h-4 w-4" />
								</button>
							</div>

							{/* Search and Filter Bar - Design System Aligned */}
								<div className="px-6 py-4 border-b border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
								<div className="flex items-center gap-3">
									{/* Search Input */}
									<div className="flex-1 relative">
										<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
										<input
											type="text"
											placeholder="Search by workflow, node name, or ID..."
											aria-label="Search paused executions"
											value={searchQuery}
											onChange={handleSearchChange}
											className="w-full pl-10 pr-4 py-2.5
												bg-[color:var(--color-bg-secondary)]
												border border-[color:var(--color-border)] rounded-xl
												text-sm text-[color:var(--color-text-primary)]
											placeholder-[color:var(--color-text-muted)]
											focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)]
											focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.2)]
											transition-all duration-200"
										/>
									</div>

									{/* Filter Dropdown */}
									<div className="w-48">
										<Dropdown
											value={sortBy}
											onChange={handleSortByChange}
											options={[
												{
													value: "newest",
													label: "Newest First",
													icon: <Clock className="w-4 h-4" />,
												},
												{
													value: "oldest",
													label: "Oldest First",
													icon: <Clock className="w-4 h-4" />,
												},
												{
													value: "progress",
													label: "By Progress",
													icon: <SlidersHorizontal className="w-4 h-4" />,
												},
											]}
											className="h-[42px]"
										/>
									</div>

									{/* Refresh Button */}
									<button
										onClick={handleRefreshClick}
										disabled={isLoading}
										className="p-2.5 rounded-xl
											border border-[color:var(--color-border)]
											bg-[color:var(--color-bg-secondary)]
										text-[color:var(--color-text-muted)]
										hover:border-[rgba(var(--color-primary-rgb),0.4)]
											hover:text-[color:var(--color-text-primary)]
										transition-all duration-200
										disabled:opacity-50
										focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
										title="Refresh"
									>
										<RefreshCw
											className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`}
										/>
									</button>

									{/* Results Counter */}
										<div className="px-3 py-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)]">
										<span className="text-xs font-medium text-[color:var(--color-text-muted)]">
											{filteredAndSortedExecutions.length} results
										</span>
									</div>
								</div>
							</div>

							{/* Content */}
							<div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar bg-[color:var(--color-bg-secondary)]">
								{error ? (
										<div className="flex flex-col items-center gap-3 rounded-2xl border border-red-500/40 bg-red-500/5 px-6 py-10 text-center shadow-lg">
										<AlertCircle className="h-10 w-10 text-red-400" />
											<p className="text-sm font-semibold text-[color:var(--color-text-primary)]">
											Unable to load paused executions
										</p>
										<p className="text-xs text-red-600">{error}</p>
									</div>
								) : isLoading && pausedExecutions.length === 0 ? (
										<div className="flex flex-col items-center gap-4 rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-6 py-12 text-center shadow-lg">
										<div className="h-12 w-12 rounded-full border-2 border-[rgba(var(--color-primary-rgb),0.35)] border-t-[color:var(--color-primary)] animate-spin" />
										<div>
												<p className="text-sm font-medium text-[color:var(--color-text-primary)]">
												Loading paused executions
											</p>
											<p className="text-xs text-[color:var(--color-text-muted)]">
												Fetching workflow data...
											</p>
										</div>
									</div>
								) : (
									<div className="space-y-4">
										{filteredAndSortedExecutions.map((execution) => (
											<div
												key={execution.execution_id}
													className="group rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-5
													shadow-md
												hover:border-[rgba(var(--color-primary-rgb),0.4)]
												transition-all duration-300"
											>
												{/* Card Header */}
												<div className="flex items-start justify-between mb-4">
													<div className="flex-1 space-y-3">
														{/* Badges Row */}
														<div className="flex items-center gap-2 flex-wrap">
															{/* Workflow Name Badge */}
															<span
																className="inline-flex items-center gap-1.5 px-2.5 py-1
															rounded-full border border-[rgba(var(--color-primary-rgb),0.45)]
															bg-[rgba(var(--color-primary-rgb),0.12)]
															text-[11px] font-medium text-[color:var(--color-primary)]"
															>
																<Workflow className="w-3 h-3" />
																{execution.graph_name}
															</span>

															{/* Time Badge */}
															<span
																className="inline-flex items-center gap-1.5 px-2.5 py-1
															rounded-full border border-[color:var(--color-border)]/50
															bg-[color:var(--color-surface)]/40
															text-[11px] font-medium text-[color:var(--color-text-muted)]"
															>
																<Clock className="w-3 h-3" />
																{formatTimeSince(execution.paused_at)}
															</span>
														</div>

														{/* Node Information */}
														<div className="flex items-center gap-3">
															<div className="flex h-8 w-8 items-center justify-center rounded-xl border border-[color:var(--color-warning)]/35 bg-[color:var(--color-warning)]/12">
																<Pause className="w-4 h-4 text-[color:var(--color-warning)]" />
															</div>
															<div>
																	<span className="text-sm font-semibold text-[color:var(--color-text-primary)]">
																	{execution.checkpoint?.node_name ||
																		"Unknown Checkpoint"}
																</span>
																<div className="text-[0.65rem] capitalize text-[color:var(--color-text-muted)] font-mono mt-0.5">
																	ID:{" "}
																	{execution.thread_id ||
																		execution.execution_id.slice(0, 8)}
																	...
																</div>
															</div>
														</div>
													</div>

													{/* Progress Visualization */}
													<div className="flex items-center gap-4">
														{/* Progress Text */}
														<div className="text-right">
															<div className="text-sm font-bold text-[color:var(--color-text-primary)]">
																{execution.progress.completed_nodes}/
																{execution.progress.total_nodes}
															</div>
															<div className="text-[0.65rem] capitalize text-[color:var(--color-text-muted)]">
																nodes
															</div>
														</div>

														{/* Circular Progress */}
														<div className="relative w-14 h-14">
															<svg className="w-14 h-14 transform -rotate-90">
																<circle
																	cx="28"
																	cy="28"
																	r="24"
																	stroke="currentColor"
																	strokeWidth="4"
																	fill="none"
																	className="text-[color:var(--color-border)]/50"
																/>
																<circle
																	cx="28"
																	cy="28"
																	r="24"
																	stroke="url(#progressGradient)"
																	strokeWidth="4"
																	fill="none"
																	strokeDasharray={`${execution.progress.percentage * 1.51} 151`}
																	strokeLinecap="round"
																	className="transition-all duration-500"
																/>
																<defs>
																	<linearGradient id="progressGradient">
																		<stop
																			offset="0%"
																			stopColor="rgba(var(--color-primary-rgb),1)"
																		/>
																		<stop
																			offset="100%"
																			stopColor="rgba(var(--color-primary-rgb),0.7)"
																		/>
																	</linearGradient>
																</defs>
															</svg>
															<div className="absolute inset-0 flex items-center justify-center">
																<span className="text-sm font-bold text-[color:var(--color-primary)]">
																	{Math.round(execution.progress.percentage)}%
																</span>
															</div>
														</div>
													</div>
												</div>

												{/* Last Input Section */}
												{execution.checkpoint?.last_input && (
													<div className="mt-4">
														<button
															onClick={createToggleInputExpansionHandler(
																execution.execution_id,
															)}
															className="w-full text-left"
														>
															<div
																className="flex items-center justify-between p-3
															rounded-xl border border-[color:var(--color-border)]/50
															bg-[color:var(--color-surface)]/30
															hover:bg-[color:var(--color-surface)]/50
															transition-all duration-200"
															>
																<div className="flex items-center gap-2">
																	<span className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
																		Last Input
																	</span>
																	{!expandedInputs.has(
																		execution.execution_id,
																	) && (
																		<span className="text-xs text-[color:var(--color-text-muted)] opacity-60">
																			(Click to expand)
																		</span>
																	)}
																</div>
																<Maximize2
																	className={`w-3 h-3 text-[color:var(--color-text-muted)] transition-transform ${
																		expandedInputs.has(execution.execution_id)
																			? "rotate-180"
																			: ""
																	}`}
																/>
															</div>
														</button>

														{expandedInputs.has(execution.execution_id) && (
															<div className="mt-2 p-3 rounded-xl border border-[color:var(--color-border)]/50 bg-[color:var(--color-bg-secondary)]/60 max-h-[300px] overflow-auto custom-scrollbar">
																{renderContent(execution.checkpoint.last_input)}
															</div>
														)}
													</div>
												)}

												{/* Action Buttons */}
												<div className="flex items-center justify-end gap-2 mt-4">
													{/* Resume with Input - Secondary button */}
													<button
														onClick={createResumeExecutionHandler(execution)}
														className="px-4 py-2 rounded-xl
														border border-[color:var(--color-border)]
														bg-[color:var(--color-bg-secondary)]
														hover:border-[rgba(var(--color-primary-rgb),0.4)]
														text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-text-primary)]
														text-xs font-semibold
														flex items-center gap-2
														transition-all duration-200
														focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
														title="Resume with custom input"
													>
														<Sparkles className="w-3.5 h-3.5" />
														Resume with Input
													</button>

													{/* Quick Resume - Primary CTA */}
													<button
														onClick={createSelectExecutionHandler(execution)}
														className="px-4 py-2 rounded-xl
														bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)]
														text-[color:var(--button-primary-text)]
														shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.35)]
														hover:shadow-[0_20px_50px_rgba(var(--color-primary-rgb),0.45)]
														text-xs font-semibold
														flex items-center gap-2
														transition-all duration-200
														focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
														title="Resume this execution"
													>
														<Play className="w-3.5 h-3.5" />
														Resume
													</button>

													{/* Cancel Button */}
													<button
														onClick={createCancelExecutionHandler(execution)}
														className="p-2 rounded-xl
														border border-red-500/30
														bg-red-500/10
														text-red-400
														hover:border-red-500/50 hover:bg-red-500/20
														transition-all duration-200
														focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/45"
														title="Cancel this execution"
													>
														<Trash2 className="w-3.5 h-3.5" />
													</button>
												</div>
											</div>
										))}

										{filteredAndSortedExecutions.length === 0 && (
												<div className="flex flex-col items-center justify-center py-16 rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
													<div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] mb-4">
													<Pause className="w-8 h-8 text-[color:var(--color-text-muted)] opacity-50" />
												</div>
												<p className="text-sm font-medium text-[color:var(--color-text-secondary)]">
													No paused executions found
												</p>
												<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
													All workflows are running or completed
												</p>
											</div>
										)}
									</div>
								)}
							</div>

							{/* Footer */}
							<div
								className="flex items-center gap-3 px-6 py-4
							border-t border-[color:var(--color-border)]
							bg-[color:var(--color-bg-secondary)]"
							>
								<div className="flex-1 flex items-center gap-3">
									{pagination.hasMore && (
										<button
											onClick={loadMore}
											disabled={isLoading}
											className="px-4 py-2 rounded-xl
											bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)]
											text-[color:var(--button-primary-text)]
											shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.35)]
											text-sm font-semibold
											transition-all duration-200
											disabled:opacity-50
											focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
										>
											Load More ({pagination.total - pausedExecutions.length}{" "}
											remaining)
										</button>
									)}
								</div>

								<button
									onClick={handleHideList}
									className="px-4 py-2 rounded-xl
									border border-[color:var(--color-border)]
									bg-[color:var(--color-surface)]
									text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-text-primary)]
									hover:border-[rgba(var(--color-primary-rgb),0.4)]
									font-medium
									transition-all duration-200
									focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
								>
									Close
								</button>
							</div>
						</div>
					</div>
				</div>
			)}

			{/* Resume Execution Dialog - Standard checkpoint or Review */}
			{resumeDialogState.isOpen && resumeDialogState.execution && (
				<>
					{/* Check if this is an agent review pause */}
					{resumeDialogState.execution.checkpoint?.type === "agent_review" &&
					resumeDialogState.execution.checkpoint?.review_payload ? (
						<ReviewResumeDialog
							execution={{
								execution_id: resumeDialogState.execution.execution_id,
								thread_id: resumeDialogState.execution.thread_id,
								graph_name: resumeDialogState.execution.graph_name,
							}}
							reviewPayload={
								resumeDialogState.execution.checkpoint.review_payload
							}
							onClose={() =>
								setResumeDialogState({ isOpen: false, execution: null })
							}
							onResume={async (executionId, response) => {
								try {
									const executionToResume = resumeDialogState.execution;

									// Optimistically remove from UI
									setPausedExecutions((prev) =>
										prev.filter((exec) => exec.execution_id !== executionId),
									);

									// Update pagination count
									setPagination((prev) => ({
										...prev,
										total: Math.max(0, prev.total - 1),
									}));

									// Close dialogs
									setResumeDialogState({ isOpen: false, execution: null });
									setShowList(false);

									// Call API to resume with review response
									await api.resumePausedExecution(
										executionId,
										JSON.stringify(response),
									);

									// Open the execution view
									if (executionToResume) {
										onSelectExecution(
											executionToResume.websocket_execution_id ||
												executionToResume.thread_id,
											executionToResume.thread_id,
											executionToResume.execution_id,
										);
									}

									// Silent refresh after a delay to sync state
									setTimeout(() => {
										fetchPausedExecutions(0).catch((error) => {
											console.error("Failed to refresh after resume:", error);
										});
									}, 3000);
								} catch (error) {
									console.error("Failed to resume review execution:", error);
									fetchPausedExecutions(0).catch((error) => {
										console.error(
											"Failed to revert after resume error:",
											error,
										);
									});
									alert("Failed to submit review. Please try again.");
								}
							}}
						/>
					) : (
						<ResumeExecutionDialog
							execution={resumeDialogState.execution}
							onClose={() =>
								setResumeDialogState({ isOpen: false, execution: null })
							}
							onResume={async (executionId, userInput) => {
								try {
									// Store execution data before removing
									const executionToResume = resumeDialogState.execution;

									// Optimistically remove from UI
									setPausedExecutions((prev) =>
										prev.filter((exec) => exec.execution_id !== executionId),
									);

									// Update pagination count
									setPagination((prev) => ({
										...prev,
										total: Math.max(0, prev.total - 1),
									}));

									// Close dialogs
									setResumeDialogState({ isOpen: false, execution: null });
									setShowList(false);

									// Call API to resume with user input
									await api.resumePausedExecution(executionId, userInput);

									// Open the execution view
									if (executionToResume) {
										onSelectExecution(
											executionToResume.websocket_execution_id ||
												executionToResume.thread_id,
											executionToResume.thread_id,
											executionToResume.execution_id,
										);
									}

									// Silent refresh after a delay to sync state
									setTimeout(() => {
										fetchPausedExecutions(0).catch((error) => {
											console.error("Failed to refresh after resume:", error);
										});
									}, 3000);
								} catch (error) {
									console.error(
										"Failed to resume execution with input:",
										error,
									);
									// Revert optimistic update on error
									fetchPausedExecutions(0).catch((error) => {
										console.error(
											"Failed to revert after resume error:",
											error,
										);
									});
									alert("Failed to resume execution. Please try again.");
								}
							}}
						/>
					)}
				</>
			)}

			{/* Cancel Execution Confirmation Dialog */}
			<ConfirmDialog
				isOpen={cancelConfirmState.isOpen}
				onClose={() =>
					setCancelConfirmState({ isOpen: false, execution: null })
				}
				onConfirm={handleConfirmCancel}
				title="Cancel Execution?"
				message="Are you sure you want to cancel this execution? This action cannot be undone."
				confirmText="Cancel Execution"
				cancelText="Keep"
				variant="danger"
				surface="light"
			/>
		</>
	);
}
