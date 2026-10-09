import { ChevronDown, RefreshCw } from "lucide-react";
import { memo, useCallback, useRef, useState } from "react";
import ExecutionFilters from "./ExecutionFilters";
import type { FeedbackFilter, SourceFilter, StatusFilter } from "./types";

interface ExecutionHistoryHeaderProps {
	onRefresh: () => void;
	isLoading: boolean;
	totalCount: number;
	displayedCount: number;
	searchTerm: string;
	onSearchChange: (value: string) => void;
	statusFilter: StatusFilter;
	onStatusFilterChange: (value: StatusFilter) => void;
	sourceFilter: SourceFilter;
	onSourceFilterChange: (value: SourceFilter) => void;
	feedbackFilter: FeedbackFilter;
	onFeedbackFilterChange: (value: FeedbackFilter) => void;
	workflowNames: string[];
	selectedWorkflow: string;
	onWorkflowSelect: (workflow: string) => void;
}

const ExecutionHistoryHeader = memo(function ExecutionHistoryHeader({
	onRefresh,
	isLoading,
	totalCount,
	displayedCount,
	searchTerm,
	onSearchChange,
	statusFilter,
	onStatusFilterChange,
	sourceFilter,
	onSourceFilterChange,
	feedbackFilter,
	onFeedbackFilterChange,
	workflowNames,
	selectedWorkflow,
	onWorkflowSelect,
}: ExecutionHistoryHeaderProps) {
	const [showWorkflowDropdown, setShowWorkflowDropdown] = useState(false);
	const dropdownRef = useRef<HTMLDivElement>(null);

	const handleWorkflowClick = useCallback(
		(workflow: string) => {
			onWorkflowSelect(workflow);
			setShowWorkflowDropdown(false);
		},
		[onWorkflowSelect],
	);

	return (
		<div
			data-tutorial="executions-header"
			className="p-6 border-b border-slate-200 bg-white"
		>
			<div className="flex items-center justify-between mb-1">
				<div>
					<p className="text-[0.65rem] capitalize text-slate-500 mb-1">
						Workflow Runs
					</p>
					<h1 className="text-2xl font-semibold text-slate-900">
						Execution History
					</h1>
				</div>
				<div className="flex items-center gap-4">
					{totalCount > 0 && (
						<span
							className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
								border border-slate-200
								bg-white
								text-xs font-medium text-orange-800"
						>
							{displayedCount < totalCount
								? `${displayedCount} of ${totalCount}`
								: totalCount}{" "}
							execution{totalCount !== 1 ? "s" : ""}
						</span>
					)}
					<button
						data-tutorial="executions-refresh"
						onClick={onRefresh}
						disabled={isLoading}
						className="flex items-center gap-2 px-4 py-2 rounded-xl
							bg-white
							border border-slate-200
							text-slate-700 text-sm font-medium
								hover:border-orange-400 hover:bg-white hover:text-slate-900
							focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25
							disabled:opacity-50 disabled:cursor-not-allowed
							transition-all"
					>
						<RefreshCw
							className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`}
						/>
						Refresh
					</button>
				</div>
			</div>

			<div className="flex flex-wrap items-center gap-3 mt-4">
				{/* Workflow Dropdown Filter */}
				{workflowNames.length > 0 && (
					<div className="relative flex-1 min-w-[150px]" ref={dropdownRef}>
						<button
							onClick={() => setShowWorkflowDropdown(!showWorkflowDropdown)}
							className="flex items-center gap-2 px-4 py-2.5 rounded-xl
								bg-white
								border border-slate-200
								text-sm text-slate-700
								hover:border-orange-400 hover:bg-white hover:text-slate-900
								focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25
								transition-all w-full"
						>
							<span className="flex-1 text-left truncate">
								{selectedWorkflow || "All Workflows"}
							</span>
							<ChevronDown className="w-4 h-4 flex-shrink-0" />
						</button>

						{showWorkflowDropdown && (
							<div
								className="absolute top-full left-0 mt-1 w-full min-w-[220px] max-h-[300px] overflow-auto
									bg-white
									border border-slate-200
									rounded-lg shadow-[0_10px_40px_rgba(15,23,42,0.12)]
									z-50"
							>
								<button
									onClick={() => handleWorkflowClick("")}
									className={`w-full px-3 py-2 text-left text-sm
										hover:bg-white hover:text-slate-900
										transition-colors ${!selectedWorkflow ? "text-orange-700 font-medium" : "text-slate-700"}`}
								>
									All Workflows
								</button>
								{workflowNames.map((name) => (
									<button
										key={name}
										onClick={() => handleWorkflowClick(name)}
										className={`w-full px-3 py-2 text-left text-sm truncate
											hover:bg-white hover:text-slate-900
											transition-colors ${selectedWorkflow === name ? "text-orange-700 font-medium" : "text-slate-700"}`}
									>
										{name}
									</button>
								))}
							</div>
						)}
					</div>
				)}

				<ExecutionFilters
					searchTerm={searchTerm}
					onSearchChange={onSearchChange}
					statusFilter={statusFilter}
					onStatusFilterChange={onStatusFilterChange}
					sourceFilter={sourceFilter}
					onSourceFilterChange={onSourceFilterChange}
					feedbackFilter={feedbackFilter}
					onFeedbackFilterChange={onFeedbackFilterChange}
				/>
			</div>
		</div>
	);
});

export default ExecutionHistoryHeader;
