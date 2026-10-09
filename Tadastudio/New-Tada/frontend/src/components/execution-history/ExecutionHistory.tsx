import { AlertCircle, FileText, Loader2, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { lazy, memo, Suspense, useCallback, useEffect, useRef, useState } from "react";
import ConfirmDialog from "@/components/dialogs/ConfirmDialog";
import EnhancedExecutionViewerModal from "@/components/execution/EnhancedExecutionViewerModal";
import type { GraphExecution as FullGraphExecution } from "@/types/api";

const ExecutionGraphViewer = lazy(() => import("@/components/utils/ExecutionGraphViewer"));
import { api } from "@/lib/api";
import type { ExecutionsListResponse } from "@/types/api";
import ExecutionCard from "./ExecutionCard";
import ExecutionHistoryHeader from "./ExecutionHistoryHeader";
import {
	type FeedbackFilter,
	type GraphExecution,
	type SourceFilter,
	type StatusFilter,
} from "./types";

const ITEMS_PER_PAGE = 20;
const SEARCH_DEBOUNCE_MS = 300;

const ExecutionHistory = memo(function ExecutionHistory() {
	const router = useRouter();

	// Data state
	const [executions, setExecutions] = useState<GraphExecution[]>([]);
	const [loading, setLoading] = useState(true);
	const [loadingMore, setLoadingMore] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [totalCount, setTotalCount] = useState(0);
	const [hasMore, setHasMore] = useState(false);
	const [initialLoadComplete, setInitialLoadComplete] = useState(false);
	const [isFiltering, setIsFiltering] = useState(false);

	// Filter state
	const [searchTerm, setSearchTerm] = useState("");
	const [debouncedSearchTerm, setDebouncedSearchTerm] = useState("");
	const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
	const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all");
	const [feedbackFilter, setFeedbackFilter] = useState<FeedbackFilter>("all");
	const [workflowNames, setWorkflowNames] = useState<string[]>([]);
	const [selectedWorkflow, setSelectedWorkflow] = useState<string>("");
	const searchDebounceRef = useRef<NodeJS.Timeout | null>(null);

	// UI state
	const [expandedExecutions, setExpandedExecutions] = useState<Set<string>>(
		new Set(),
	);
	const [deleteTarget, setDeleteTarget] = useState<GraphExecution | null>(
		null,
	);

	// Tutorial-only viewer modals (opens trace/graph view without navigating away)
	const [tutorialViewerExecution, setTutorialViewerExecution] = useState<GraphExecution | null>(null);
	const [tutorialGraphExecution, setTutorialGraphExecution] = useState<FullGraphExecution | null>(null);

	// Check if a string looks like a UUID (full or partial)
	const isLikelyExecutionId = useCallback((term: string) => {
		// UUID format: 8-4-4-4-12 hex chars with dashes
		const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
		return uuidRegex.test(term);
	}, []);

	// Build query params for API
	const buildQueryParams = useCallback(
		(offset: number = 0) => {
			const params = new URLSearchParams();
			params.set("limit", ITEMS_PER_PAGE.toString());
			params.set("offset", offset.toString());
			params.set("include_nodes", "false");

			if (selectedWorkflow) {
				params.set("graph_name", selectedWorkflow);
			} else if (debouncedSearchTerm) {
				params.set("graph_name", debouncedSearchTerm);
			}

			if (statusFilter !== "all") {
				params.set("status", statusFilter);
			}

			if (sourceFilter !== "all") {
				params.set("trigger_type", sourceFilter);
			}

			if (feedbackFilter !== "all") {
				params.set("feedback_rating", feedbackFilter);
			}

			return params.toString();
		},
		[debouncedSearchTerm, statusFilter, sourceFilter, feedbackFilter, selectedWorkflow],
	);

	// Fetch workflow names for dropdown
	const fetchWorkflowNames = useCallback(async () => {
		try {
			const data = await api.get("/api/execution-history/workflow-names");
			setWorkflowNames(Array.isArray(data) ? data : []);
		} catch (err) {
			console.error("Failed to fetch workflow names:", err);
		}
	}, []);

	// Fetch execution history
	const fetchExecutions = useCallback(
		async (append: boolean = false, isInitial: boolean = false) => {
			try {
				if (append) {
					setLoadingMore(true);
				} else if (isInitial) {
					setLoading(true);
					setError(null);
				} else {
					// Filter change - use subtle indicator
					setIsFiltering(true);
					setError(null);
				}

				// Check if searching by execution ID (UUID format)
				const trimmedSearch = debouncedSearchTerm.trim();
				if (trimmedSearch && isLikelyExecutionId(trimmedSearch) && !append) {
					try {
						const execution = await api.getExecutionHistory(trimmedSearch);
						if (execution) {
							setExecutions([execution as GraphExecution]);
							setTotalCount(1);
							setHasMore(false);
							if (!initialLoadComplete) {
								setInitialLoadComplete(true);
							}
							return;
						}
					} catch {
						// If direct lookup fails, fall through to normal search
						// (execution might not exist or user doesn't have access)
					}
				}

				const offset = append ? executions.length : 0;
				const queryParams = buildQueryParams(offset);
				const data: ExecutionsListResponse = await api.get(
					`/api/execution-history/executions?${queryParams}`,
				);

				if (append) {
					setExecutions((prev) => [...prev, ...data.executions]);
				} else {
					setExecutions(data.executions);
				}
				setTotalCount(data.total_count);
				setHasMore(data.has_more);
				if (!initialLoadComplete) {
					setInitialLoadComplete(true);
				}
			} catch (err) {
				setError(
					err instanceof Error
						? err.message
						: "Failed to fetch execution history",
				);
			} finally {
				setLoading(false);
				setLoadingMore(false);
				setIsFiltering(false);
			}
		},
		[buildQueryParams, executions.length, initialLoadComplete, debouncedSearchTerm, isLikelyExecutionId],
	);

	// Initial load
	useEffect(() => {
		fetchWorkflowNames().catch((error) => {
			console.error("Failed to fetch workflow names:", error);
		});
		// Initial fetch with isInitial flag
		fetchExecutions(false, true).catch((error) => {
			console.error("Failed to fetch execution history:", error);
		});
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	// Listen for tutorial-triggered refresh
	useEffect(() => {
		const handler = () => {
			fetchExecutions(false, false).catch(() => {});
		};
		window.addEventListener("tutorialRefreshExecutions", handler);
		return () => window.removeEventListener("tutorialRefreshExecutions", handler);
	}, [fetchExecutions]);

	// Listen for tutorial-triggered trace viewer (opens modal without navigation)
	useEffect(() => {
		const openHandler = () => {
			const first = executions[0];
			if (first) {
				setTutorialViewerExecution(first);
			}
		};
		const closeHandler = () => {
			setTutorialViewerExecution(null);
		};
		const switchToGraphHandler = async () => {
			// Close trace viewer and open graph viewer for the first execution
			setTutorialViewerExecution(null);
			const first = executions[0];
			if (first) {
				try {
					const full = await api.getExecutionHistory(first.id) as FullGraphExecution;
					setTutorialGraphExecution(full);
				} catch {
					console.warn("Failed to load full execution for graph viewer");
				}
			}
		};
		const closeGraphHandler = () => {
			setTutorialGraphExecution(null);
		};
		window.addEventListener("tutorialOpenTraceViewer", openHandler);
		window.addEventListener("tutorialCloseTraceViewer", closeHandler);
		window.addEventListener("tutorialSwitchToGraphView", switchToGraphHandler);
		window.addEventListener("tutorialCloseGraphViewer", closeGraphHandler);
		return () => {
			window.removeEventListener("tutorialOpenTraceViewer", openHandler);
			window.removeEventListener("tutorialCloseTraceViewer", closeHandler);
			window.removeEventListener("tutorialSwitchToGraphView", switchToGraphHandler);
			window.removeEventListener("tutorialCloseGraphViewer", closeGraphHandler);
		};
	}, [executions]);

	// Debounce search term
	useEffect(() => {
		if (searchDebounceRef.current) {
			clearTimeout(searchDebounceRef.current);
		}
		searchDebounceRef.current = setTimeout(() => {
			setDebouncedSearchTerm(searchTerm);
		}, SEARCH_DEBOUNCE_MS);

		return () => {
			if (searchDebounceRef.current) {
				clearTimeout(searchDebounceRef.current);
			}
		};
	}, [searchTerm]);

	// Refetch when filters change (using debounced search term)
	useEffect(() => {
		// Skip if this is the initial load (handled above)
		if (!initialLoadComplete) return;

		fetchExecutions(false, false).catch((error) => {
			console.error("Failed to fetch execution history:", error);
		});
		// Reset expanded state when filters change
		setExpandedExecutions(new Set());
	}, [debouncedSearchTerm, statusFilter, sourceFilter, feedbackFilter, selectedWorkflow]);

	// Load more handler
	const handleLoadMore = useCallback(() => {
		if (!loadingMore && hasMore) {
			fetchExecutions(true).catch((error) => {
				console.error("Failed to load more executions:", error);
			});
		}
	}, [fetchExecutions, loadingMore, hasMore]);

	// Handlers
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

	const getWorkflowIdentifier = useCallback((execution: GraphExecution) => {
		if (execution.workflow_id) {
			return execution.workflow_id;
		}
		return encodeURIComponent(execution.graph_id);
	}, []);

	const viewEnhancedExecution = useCallback(
		(execution: GraphExecution) => {
			const workflowIdentifier = getWorkflowIdentifier(execution);
			router.push(
				`/workflow/${workflowIdentifier}/${execution.id}?return=executions`,
			);
		},
		[router, getWorkflowIdentifier],
	);

	const viewExecutionGraph = useCallback(
		(execution: GraphExecution) => {
			const workflowIdentifier = getWorkflowIdentifier(execution);
			router.push(
				`/workflow/${workflowIdentifier}/${execution.id}/graph?return=executions`,
			);
		},
		[router, getWorkflowIdentifier],
	);

	// Handle search term change with workflow filter reset
	const handleSearchChange = useCallback((value: string) => {
		setSearchTerm(value);
		// Clear workflow selection when typing a search
		if (value) {
			setSelectedWorkflow("");
		}
	}, []);

	// Handle workflow selection
	const handleWorkflowSelect = useCallback((workflow: string) => {
		setSelectedWorkflow(workflow);
		// Clear search term when selecting a workflow
		if (workflow) {
			setSearchTerm("");
			setDebouncedSearchTerm("");
			// Clear any pending debounce
			if (searchDebounceRef.current) {
				clearTimeout(searchDebounceRef.current);
			}
		}
	}, []);

	// Delete handler
	const handleDeleteExecution = useCallback(async () => {
		if (!deleteTarget) return;
		try {
			await api.deleteExecution(deleteTarget.id);
			setExecutions((prev) => prev.filter((e) => e.id !== deleteTarget.id));
			setTotalCount((prev) => prev - 1);
		} catch (err) {
			console.error("Failed to delete execution:", err);
		}
	}, [deleteTarget]);

	// Loading state - only show full-page loader on initial load
	if (loading && !initialLoadComplete) {
		return (
			<div className="h-full bg-white text-slate-900 flex items-center justify-center p-6">
				<div
					className="flex flex-col items-center justify-center gap-4
						rounded-2xl
						bg-white
						px-8 py-16 w-full max-w-md"
				>
					<div
						className="h-10 w-10 rounded-full
							border-2 border-transparent
							border-t-orange-500
							animate-spin"
					/>
					<p className="text-sm text-slate-600">
						Loading execution history...
					</p>
				</div>
			</div>
		);
	}

	// Error state
	if (error) {
		return (
			<div className="h-full bg-white text-slate-900 flex items-center justify-center p-6">
				<div
					className="flex flex-col items-center gap-4
						rounded-2xl border border-red-500/40
						bg-red-500/5
						shadow-[0_20px_60px_rgba(153,27,27,0.15)]
						px-8 py-12 text-center w-full max-w-md"
				>
					<AlertCircle className="h-10 w-10 text-red-400" />
					<p className="text-sm font-semibold text-slate-900">
						Error loading execution history
					</p>
					<p className="text-xs text-red-700">{error}</p>
					<button
						onClick={() => fetchExecutions(false)}
						className="mt-4 px-5 py-2.5 rounded-xl font-medium
							bg-orange-500
							text-white
							shadow-[0_15px_40px_rgba(15,23,42,0.12)]
							hover:bg-orange-600
							focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]
							transition-all"
					>
						Retry
					</button>
				</div>
			</div>
		);
	}

	return (
		<div className="h-full bg-white text-slate-900 flex flex-col">
			{/* Header with filters */}
			<ExecutionHistoryHeader
				onRefresh={() => fetchExecutions(false, false)}
				isLoading={isFiltering || loading}
				totalCount={totalCount}
				displayedCount={executions.length}
				searchTerm={searchTerm}
				onSearchChange={handleSearchChange}
				statusFilter={statusFilter}
				onStatusFilterChange={setStatusFilter}
				sourceFilter={sourceFilter}
				onSourceFilterChange={setSourceFilter}
				feedbackFilter={feedbackFilter}
				onFeedbackFilterChange={setFeedbackFilter}
				workflowNames={workflowNames}
				selectedWorkflow={selectedWorkflow}
				onWorkflowSelect={handleWorkflowSelect}
			/>

			{/* Execution List */}
			<div className="flex-1 overflow-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
				<div className="mx-auto max-w-screen-2xl">
				{executions.length === 0 ? (
					<div
						className="flex flex-col items-center justify-center gap-4
							rounded-2xl border border-slate-200
							bg-white
							shadow-[0_20px_55px_rgba(15,23,42,0.10)]
							px-8 py-16 text-center"
					>
						<FileText className="w-14 h-14 text-slate-400 opacity-60" />
						<p className="text-sm font-medium text-slate-700">
							No execution history found
						</p>
						<p className="text-xs text-slate-500">
							{searchTerm || statusFilter !== "all" || sourceFilter !== "all" || feedbackFilter !== "all" || selectedWorkflow
								? "Try adjusting your search or filters"
								: "Execute some workflows to see their history here"}
						</p>
					</div>
				) : (
					<>
						<div className="space-y-4">
							{executions.map((execution, index) => (
								<ExecutionCard
									key={execution.id}
									execution={execution}
									isFirst={index === 0}
									isExpanded={expandedExecutions.has(execution.id)}
									onToggleExpand={toggleExpanded}
									onViewDetails={viewEnhancedExecution}
									onViewGraph={viewExecutionGraph}
									onDelete={setDeleteTarget}
								/>
							))}
						</div>

						{/* Load More Button */}
						{hasMore && (
							<div className="flex justify-center mt-6">
								<button
									onClick={handleLoadMore}
									disabled={loadingMore}
									className="flex items-center gap-2 px-6 py-3 rounded-xl font-medium
										bg-white
										border border-slate-200
										text-slate-700
										hover:border-orange-400
										hover:bg-white
										hover:text-slate-900
										focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20
										disabled:opacity-50 disabled:cursor-not-allowed
										transition-all"
								>
									{loadingMore ? (
										<>
											<Loader2 className="w-4 h-4 animate-spin text-orange-500" />
											Loading...
										</>
									) : (
										<>
											Load More
											<span className="text-xs text-[color:var(--color-text-muted)]">
												({executions.length} of {totalCount})
											</span>
										</>
									)}
								</button>
							</div>
						)}

						{/* End of results indicator */}
						{!hasMore && executions.length > 0 && (
							<div className="flex justify-center mt-6">
								<span className="text-xs text-[color:var(--color-text-muted)]">
									Showing all {executions.length} execution
									{executions.length !== 1 ? "s" : ""}
								</span>
							</div>
						)}
					</>
				)}
				</div>
			</div>

			{/* Delete Confirmation Dialog */}
			<ConfirmDialog
				isOpen={deleteTarget !== null}
				title="Delete Execution"
				message={`Are you sure you want to delete the execution for "${deleteTarget?.graph_name ?? ""}"? This will permanently remove the execution and all associated node data.`}
				confirmText="Delete"
				cancelText="Cancel"
				type="danger"
				onConfirm={handleDeleteExecution}
				onCancel={() => setDeleteTarget(null)}
			/>

			{/* Tutorial-only trace viewer modal */}
			<EnhancedExecutionViewerModal
				isOpen={tutorialViewerExecution !== null}
				executionId={tutorialViewerExecution?.id ?? null}
				onClose={() => setTutorialViewerExecution(null)}
				workflowId={tutorialViewerExecution?.workflow_id ?? undefined}
			/>

			{/* Tutorial-only graph viewer modal */}
			{tutorialGraphExecution && (
				<div className="fixed inset-0 z-[9999] bg-black/30 backdrop-blur-sm animate-fadeIn">
					<div className="fixed inset-4 bg-white rounded-xl border border-slate-200 shadow-2xl overflow-hidden animate-slideUp">
						<button
							data-tutorial="graph-view-close-btn"
							onClick={() => setTutorialGraphExecution(null)}
								className="absolute top-4 right-4 z-50 p-2 bg-white hover:bg-white border border-slate-200 hover:border-orange-400 rounded-lg transition-colors group"
							title="Close Graph Viewer"
						>
								<X className="w-6 h-6 text-slate-500 group-hover:text-slate-900 transition-colors" />
						</button>
						<div className="h-full overflow-hidden">
							<Suspense fallback={
								<div className="flex items-center justify-center h-full">
									<Loader2 className="w-8 h-8 animate-spin text-[color:var(--color-primary)]" />
								</div>
							}>
								<ExecutionGraphViewer
									execution={tutorialGraphExecution}
									onClose={() => setTutorialGraphExecution(null)}
									workflowId={tutorialGraphExecution.workflow_id ?? undefined}
								/>
							</Suspense>
						</div>
					</div>
				</div>
			)}
		</div>
	);
});

export default ExecutionHistory;
