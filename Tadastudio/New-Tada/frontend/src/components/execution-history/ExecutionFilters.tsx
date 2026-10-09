import { ChevronDown, Search } from "lucide-react";
import type React from "react";
import { memo, useCallback, useEffect, useRef, useState } from "react";
import type { FeedbackFilter, SourceFilter, StatusFilter } from "./types";

interface ExecutionFiltersProps {
	searchTerm: string;
	onSearchChange: (value: string) => void;
	statusFilter: StatusFilter;
	onStatusFilterChange: (value: StatusFilter) => void;
	sourceFilter: SourceFilter;
	onSourceFilterChange: (value: SourceFilter) => void;
	feedbackFilter: FeedbackFilter;
	onFeedbackFilterChange: (value: FeedbackFilter) => void;
}

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
	{ value: "all", label: "All Status" },
	{ value: "completed", label: "Completed" },
	{ value: "failed", label: "Failed" },
	{ value: "running", label: "Running" },
];

const SOURCE_OPTIONS: { value: SourceFilter; label: string }[] = [
	{ value: "all", label: "All Sources" },
	{ value: "editor", label: "Editor" },
	{ value: "api", label: "API" },
	{ value: "evaluation", label: "Evaluation" },
	{ value: "scheduler", label: "Scheduler" },
];

const FEEDBACK_OPTIONS: { value: FeedbackFilter; label: string }[] = [
	{ value: "all", label: "All Feedback" },
	{ value: "positive", label: "Positive" },
	{ value: "negative", label: "Negative" },
];

const ExecutionFilters = memo(function ExecutionFilters({
	searchTerm,
	onSearchChange,
	statusFilter,
	onStatusFilterChange,
	sourceFilter,
	onSourceFilterChange,
	feedbackFilter,
	onFeedbackFilterChange,
}: ExecutionFiltersProps) {
	const [showStatusDropdown, setShowStatusDropdown] = useState(false);
	const [showSourceDropdown, setShowSourceDropdown] = useState(false);
	const [showFeedbackDropdown, setShowFeedbackDropdown] = useState(false);
	const statusDropdownRef = useRef<HTMLDivElement>(null);
	const sourceDropdownRef = useRef<HTMLDivElement>(null);
	const feedbackDropdownRef = useRef<HTMLDivElement>(null);

	const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		onSearchChange(e.target.value);
	};

	const handleStatusSelect = useCallback(
		(value: StatusFilter) => {
			onStatusFilterChange(value);
			setShowStatusDropdown(false);
		},
		[onStatusFilterChange],
	);

	const handleSourceSelect = useCallback(
		(value: SourceFilter) => {
			onSourceFilterChange(value);
			setShowSourceDropdown(false);
		},
		[onSourceFilterChange],
	);

	const handleFeedbackSelect = useCallback(
		(value: FeedbackFilter) => {
			onFeedbackFilterChange(value);
			setShowFeedbackDropdown(false);
		},
		[onFeedbackFilterChange],
	);

	// Close dropdowns when clicking outside
	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (
				statusDropdownRef.current &&
				!statusDropdownRef.current.contains(event.target as Node)
			) {
				setShowStatusDropdown(false);
			}
			if (
				sourceDropdownRef.current &&
				!sourceDropdownRef.current.contains(event.target as Node)
			) {
				setShowSourceDropdown(false);
			}
			if (
				feedbackDropdownRef.current &&
				!feedbackDropdownRef.current.contains(event.target as Node)
			) {
				setShowFeedbackDropdown(false);
			}
		};

		if (showStatusDropdown || showSourceDropdown || showFeedbackDropdown) {
			document.addEventListener("mousedown", handleClickOutside);
		}

		return () => {
			document.removeEventListener("mousedown", handleClickOutside);
		};
	}, [showStatusDropdown, showSourceDropdown, showFeedbackDropdown]);

	const selectedStatusLabel =
		STATUS_OPTIONS.find((opt) => opt.value === statusFilter)?.label ||
		"All Status";

	const selectedSourceLabel =
		SOURCE_OPTIONS.find((opt) => opt.value === sourceFilter)?.label ||
		"All Sources";

	const selectedFeedbackLabel =
		FEEDBACK_OPTIONS.find((opt) => opt.value === feedbackFilter)?.label ||
		"All Feedback";

	return (
		<div data-tutorial="executions-filters" className="contents">
			{/* Search Input */}
			<div className="relative flex-1 min-w-[200px]">
				<Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
				<input
					data-tutorial="executions-search"
					type="text"
					placeholder="Search by graph name or execution ID..."
					value={searchTerm}
					onChange={handleSearchChange}
					className="w-full pl-10 pr-4 py-2.5 rounded-xl
						bg-white
						border border-slate-200
						text-slate-900 placeholder:text-slate-400
						hover:border-orange-400
						focus:outline-none focus:border-orange-500
						focus:ring-2 focus:ring-orange-500/15
						transition-all text-sm"
				/>
			</div>

			{/* Status Filter - Custom Dropdown */}
			<div className="relative flex-1 min-w-[150px]" ref={statusDropdownRef}>
				<button
					onClick={() => setShowStatusDropdown(!showStatusDropdown)}
					className="flex items-center gap-2 px-4 py-2.5 rounded-xl
						bg-white
						border border-slate-200
						text-sm text-slate-700
						hover:border-orange-400
						hover:bg-white hover:text-slate-900
						focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/45
						transition-all w-full"
				>
					<span className="flex-1 text-left">{selectedStatusLabel}</span>
					<ChevronDown
						className={`w-4 h-4 flex-shrink-0 transition-transform ${showStatusDropdown ? "rotate-180" : ""}`}
					/>
				</button>

				{showStatusDropdown && (
					<div
						className="absolute top-full left-0 mt-1 w-full min-w-[140px]
							bg-white
							border border-slate-200
							rounded-xl shadow-lg
							z-50 overflow-hidden"
					>
						{STATUS_OPTIONS.map((option) => (
							<button
								key={option.value}
								onClick={() => handleStatusSelect(option.value)}
								className={`w-full px-4 py-2 text-left text-sm
									hover:bg-white hover:text-slate-900
									transition-colors ${
										statusFilter === option.value
											? "text-orange-700 font-medium bg-white"
											: "text-slate-700"
									}`}
							>
								{option.label}
							</button>
						))}
					</div>
				)}
			</div>

			{/* Source Filter - Custom Dropdown */}
			<div className="relative flex-1 min-w-[150px]" ref={sourceDropdownRef}>
				<button
					onClick={() => setShowSourceDropdown(!showSourceDropdown)}
					className="flex items-center gap-2 px-4 py-2.5 rounded-xl
						bg-white
						border border-slate-200
						text-sm text-slate-700
						hover:border-orange-400
						hover:bg-white hover:text-slate-900
						focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/45
						transition-all w-full"
				>
					<span className="flex-1 text-left">{selectedSourceLabel}</span>
					<ChevronDown
						className={`w-4 h-4 flex-shrink-0 transition-transform ${showSourceDropdown ? "rotate-180" : ""}`}
					/>
				</button>

				{showSourceDropdown && (
					<div
						className="absolute top-full left-0 mt-1 w-full min-w-[140px]
							bg-white
							border border-slate-200
							rounded-xl shadow-lg
							z-50 overflow-hidden"
					>
						{SOURCE_OPTIONS.map((option) => (
							<button
								key={option.value}
								onClick={() => handleSourceSelect(option.value)}
								className={`w-full px-4 py-2 text-left text-sm
									hover:bg-white hover:text-slate-900
									transition-colors ${
										sourceFilter === option.value
											? "text-orange-700 font-medium bg-white"
											: "text-slate-700"
									}`}
							>
								{option.label}
							</button>
						))}
					</div>
				)}
			</div>

			{/* Feedback Filter - Custom Dropdown */}
			<div className="relative flex-1 min-w-[150px]" ref={feedbackDropdownRef}>
				<button
					onClick={() => setShowFeedbackDropdown(!showFeedbackDropdown)}
					className="flex items-center gap-2 px-4 py-2.5 rounded-xl
						bg-white
						border border-slate-200
						text-sm text-slate-700
						hover:border-orange-400
						hover:bg-white hover:text-slate-900
						focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/45
						transition-all w-full"
				>
					<span className="flex-1 text-left">{selectedFeedbackLabel}</span>
					<ChevronDown
						className={`w-4 h-4 flex-shrink-0 transition-transform ${showFeedbackDropdown ? "rotate-180" : ""}`}
					/>
				</button>

				{showFeedbackDropdown && (
					<div
						className="absolute top-full left-0 mt-1 w-full min-w-[140px]
							bg-white
							border border-slate-200
							rounded-xl shadow-lg
							z-50 overflow-hidden"
					>
						{FEEDBACK_OPTIONS.map((option) => (
							<button
								key={option.value}
								onClick={() => handleFeedbackSelect(option.value)}
								className={`w-full px-4 py-2 text-left text-sm
									hover:bg-white hover:text-slate-900
									transition-colors ${
										feedbackFilter === option.value
											? "text-orange-700 font-medium bg-white"
											: "text-slate-700"
									}`}
							>
								{option.label}
							</button>
						))}
					</div>
				)}
			</div>
		</div>
	);
});

export default ExecutionFilters;
