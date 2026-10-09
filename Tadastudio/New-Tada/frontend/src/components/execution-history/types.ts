import type {
	GraphExecution as GraphExecutionType,
	NodeExecution as NodeExecutionType,
} from "@/types/api";

// Re-export types for convenience
export type NodeExecution = NodeExecutionType;
export type GraphExecution = GraphExecutionType;

// Status filter options
export type StatusFilter = "all" | "completed" | "failed" | "running";

// Source (trigger type) filter options
export type SourceFilter =
	| "all"
	| "editor"
	| "api"
	| "evaluation"
	| "scheduler";

// Feedback filter options
export type FeedbackFilter = "all" | "positive" | "negative";

// Source badge styling
export interface SourceStyle {
	label: string;
	badgeClass: string;
}

export const SOURCE_STYLES: Record<string, SourceStyle> = {
	editor: {
		label: "Editor",
		badgeClass: "border-[#F7971C] bg-white text-[#F7971C]",
	},
	api: {
		label: "API",
		badgeClass: "border-slate-200 bg-white text-orange-700",
	},
	evaluation: {
		label: "Evaluation",
		badgeClass: "border-amber-400 bg-white text-amber-700",
	},
	scheduler: {
		label: "Scheduler",
		badgeClass: "border-slate-200 bg-white text-orange-700",
	},
};

// Pagination config
export const ITEMS_PER_PAGE = 20;

// Status styling configuration
export interface StatusStyle {
	icon: string;
	iconClass: string;
	badgeClass: string;
}

export const STATUS_STYLES: Record<string, StatusStyle> = {
	completed: {
		icon: "CheckCircle",
		iconClass: "text-[#0DA931]",
		badgeClass: "border-[#0DA931] bg-[#F1F8E9] text-[#0DA931]",
	},
	failed: {
		icon: "AlertCircle",
		iconClass: "text-red-600",
		badgeClass: "border-red-400 bg-red-50 text-red-600",
	},
	running: {
		icon: "Play",
		iconClass: "text-orange-600 animate-pulse",
		badgeClass: "border-orange-400 bg-orange-50 text-orange-600",
	},
	default: {
		icon: "Clock",
		iconClass: "text-slate-500",
		badgeClass: "border-slate-300 bg-slate-50 text-slate-600",
	},
};

// Helper to get status style
export const getStatusStyle = (status: string): StatusStyle => {
	return STATUS_STYLES[status] || STATUS_STYLES.default;
};

// Format duration helper
export const formatDuration = (seconds?: number | null): string => {
	if (seconds === null || seconds === undefined) return "-";
	if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
	if (seconds < 60) return `${seconds.toFixed(1)}s`;
	return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
};
