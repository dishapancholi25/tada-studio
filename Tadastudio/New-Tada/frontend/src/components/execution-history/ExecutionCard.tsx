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
	Loader2,
	Play,
	ShieldCheck,
	ThumbsDown,
	ThumbsUp,
	Trash2,
} from "lucide-react";
import type React from "react";
import { memo, useCallback, useMemo, useState } from "react";
import { api } from "@/lib/api";
import TabContainer from "@/components/ui/TabContainer";
import ViolationFeedbackControl from "@/components/core/ViolationFeedbackControl";
import { formatViolationLocation } from "@/components/panels/execution/streaming/GuardrailViolationActivity";
import type { ExecutionGuardrailViolation } from "@/types/guardrail-policies";
import NodeExecutionRow from "./NodeExecutionRow";
import {
	SOURCE_STYLES,
	formatDuration,
	type GraphExecution,
	getStatusStyle,
} from "./types";

interface ExecutionCardProps {
	execution: GraphExecution;
	isExpanded: boolean;
	onToggleExpand: (executionId: string) => void;
	onViewDetails: (execution: GraphExecution) => void;
	onViewGraph: (execution: GraphExecution) => void;
	onDelete: (execution: GraphExecution | null) => void;
	isFirst?: boolean;
}

const StatusIcon = ({ status }: { status: string }) => {
	const style = getStatusStyle(status);
	const iconClass = `w-4 h-4 ${style.iconClass}`;

	switch (status) {
		case "completed":
			return <CheckCircle className={iconClass} />;
		case "failed":
			return <AlertCircle className={iconClass} />;
		case "running":
			return <Play className={iconClass} />;
		default:
			return <Clock className={iconClass} />;
	}
};

const formatTimestamp = (timestamp: string | null | undefined): string => {
	if (!timestamp) return "Unknown";
	try {
		return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
	} catch {
		return new Date(timestamp).toLocaleString();
	}
};

const ExecutionCard = memo(function ExecutionCard({
	execution,
	isExpanded,
	onToggleExpand,
	onViewDetails,
	onViewGraph,
	onDelete,
	isFirst,
}: ExecutionCardProps) {
	const statusStyle = getStatusStyle(execution.status);
	const [userRating, setUserRating] = useState<
		"positive" | "negative" | null
	>(execution.feedback_rating ?? null);
	const [feedbackLoading, setFeedbackLoading] = useState(false);
	const [activeTab, setActiveTab] = useState("overview");
	const [nodeExecutions, setNodeExecutions] = useState<GraphExecution["node_executions"]>(execution.node_executions);
	const [nodesLoading, setNodesLoading] = useState(false);
	const [nodesFetched, setNodesFetched] = useState(!!execution.node_executions);
	const [violations, setViolations] = useState<ExecutionGuardrailViolation[]>([]);
	const [violationsLoading, setViolationsLoading] = useState(false);
	const [violationsFetched, setViolationsFetched] = useState(false);

	const handleFeedback = useCallback(
		async (rating: "positive" | "negative", e: React.MouseEvent) => {
			e.stopPropagation();
			if (feedbackLoading) return;

			setFeedbackLoading(true);
			try {
				if (userRating === rating) {
					// Toggle off - delete feedback
					await api.deleteExecutionFeedback(execution.id);
					setUserRating(null);
				} else {
					// Set or change rating
					await api.submitExecutionFeedback(execution.id, rating);
					setUserRating(rating);
				}
			} catch (err) {
				console.error("[ExecutionCard] Feedback error:", err);
			} finally {
				setFeedbackLoading(false);
			}
		},
		[execution.id, userRating, feedbackLoading],
	);

	const nodeExecs = nodeExecutions ?? [];

	const { completedNodes, totalNodes } = useMemo(() => {
		if (execution.node_executions) {
			const completed = execution.node_executions.filter(
				(ne) => ne.status === "completed",
			).length;
			return {
				completedNodes: completed,
				totalNodes: execution.node_executions.length,
			};
		}
		return {
			completedNodes: execution.completed_node_count ?? 0,
			totalNodes: execution.node_count ?? 0,
		};
	}, [execution]);

	const sortedNodeExecutions = useMemo(() => {
		return [...nodeExecs].sort(
			(a, b) => a.execution_order - b.execution_order,
		);
	}, [nodeExecs]);

	const handleToggleExpand = useCallback(() => {
		onToggleExpand(execution.id);
	}, [onToggleExpand, execution.id]);

	const handleViewDetails = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			onViewDetails(execution);
		},
		[onViewDetails, execution],
	);

	const handleViewGraph = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			onViewGraph(execution);
		},
		[onViewGraph, execution],
	);

	const handleDelete = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			onDelete(execution);
		},
		[onDelete, execution],
	);

	const handleTabChange = useCallback(
		(tabId: string) => {
			setActiveTab(tabId);
			if (tabId === "nodes" && !nodesFetched) {
				setNodesLoading(true);
				api.getExecutionHistory(execution.id)
					.then((result: Record<string, unknown>) => {
						const nodes = (result.node_executions ?? []) as GraphExecution["node_executions"];
						setNodeExecutions(nodes);
						setNodesFetched(true);
					})
					.catch(() => {
						setNodeExecutions([]);
						setNodesFetched(true);
					})
					.finally(() => setNodesLoading(false));
			}
			if (tabId === "guardrails" && !violationsFetched) {
				setViolationsLoading(true);
				api.getExecutionGuardrailViolations(execution.id)
					.then((result) => {
						setViolations(result);
						setViolationsFetched(true);
					})
					.catch(() => {
						setViolations([]);
						setViolationsFetched(true);
					})
					.finally(() => setViolationsLoading(false));
			}
		},
		[execution.id, nodesFetched, violationsFetched],
	);

	const guardrailsTabLabel = violations.length > 0 ? `Guardrails ${violations.length}` : "Guardrails";

	const tabs = useMemo(
		() => [
			{
				id: "overview",
				label: "Overview",
				icon: <FileText className="w-4 h-4" />,
				content: (
					<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
						<div className="rounded-xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_72%,#f59e0b_190%)] p-4 shadow-sm transition-colors hover:border-orange-400">
							<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
								Start Time
							</p>
							<p className="text-sm font-mono text-slate-900 mt-1">
								{execution.start_time
									? new Date(execution.start_time).toLocaleString()
									: "Unknown"}
							</p>
						</div>
						{execution.end_time && (
							<div className="rounded-xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_72%,#f59e0b_190%)] p-4 shadow-sm transition-colors hover:border-orange-400">
								<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
									End Time
								</p>
								<p className="text-sm font-mono text-slate-900 mt-1">
									{new Date(execution.end_time).toLocaleString()}
								</p>
							</div>
						)}
						{execution.user_id && (
							<div className="rounded-xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_72%,#f59e0b_190%)] p-4 shadow-sm transition-colors hover:border-orange-400 min-w-0">
								<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
									User
								</p>
								<p className="text-sm text-slate-900 mt-1 break-words" title={execution.user_id}>{execution.user_id}</p>
							</div>
						)}
						<div className="rounded-xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_72%,#f59e0b_190%)] p-4 shadow-sm transition-colors hover:border-orange-400">
							<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
								Nodes Executed
							</p>
							<p className="text-sm font-mono text-slate-900 mt-1">
								{completedNodes} of {totalNodes}
							</p>
						</div>
					</div>
				),
			},
			{
				id: "nodes",
				label: "Nodes",
				icon: <GitBranch className="w-4 h-4" />,
				content: nodesLoading ? (
						<div className="flex items-center justify-center py-8">
							<Loader2 className="w-5 h-5 animate-spin text-[color:var(--color-text-muted)]" />
						</div>
					) : nodeExecs.length > 0 ? (
						<div className="space-y-2">
							{sortedNodeExecutions.map((nodeExec) => (
								<NodeExecutionRow
									key={nodeExec.id}
									nodeExecution={nodeExec}
									executionId={execution.id}
								/>
							))}
						</div>
					) : (
						<p className="text-sm text-[color:var(--color-text-muted)] text-center py-4">
							No node executions recorded.
						</p>
					),
			},
			{
				id: "guardrails",
				label: guardrailsTabLabel,
				icon: <ShieldCheck className="w-4 h-4" />,
				content: violationsLoading ? (
					<div className="flex items-center justify-center py-8">
						<Loader2 className="w-5 h-5 animate-spin text-[color:var(--color-text-muted)]" />
					</div>
				) : violations.length === 0 && violationsFetched ? (
					<div className="flex flex-col items-center justify-center py-8 text-[color:var(--color-text-muted)]">
						<ShieldCheck className="w-8 h-8 mb-2" />
						<p className="text-sm">No guardrail violations recorded for this execution.</p>
					</div>
				) : (
					<div className="space-y-2">
						{violations.map((v) => (
							<div
								key={v.id}
								className="flex items-center gap-3 px-3 py-2 rounded-lg border border-slate-200 bg-white transition-colors hover:border-orange-400"
							>
								<span
									className={`px-2 py-0.5 rounded text-[10px] font-semibold capitalize border ${
										v.severity === "block"
											? "border-red-300 bg-white text-red-700"
											: v.severity === "warn"
												? "border-amber-400 bg-white text-amber-700"
												: "border-slate-300 bg-white text-slate-700"
									}`}
								>
									{v.severity}
								</span>
								<span className="text-sm text-slate-900">{v.rule_name}</span>
								{v.category && (
									<span className="text-xs text-[color:var(--color-text-secondary)] font-mono">
										{formatViolationLocation(v.category, v.agent_node_name, v.details?.tool_name as string)}
									</span>
								)}
								<span className="text-xs text-[color:var(--color-text-muted)]">{v.policy_name}</span>
								{v.timestamp && (
									<span className="text-xs text-[color:var(--color-text-muted)]">
										{formatTimestamp(v.timestamp)}
									</span>
								)}
								<div className="ml-auto">
									<ViolationFeedbackControl violationId={v.id} size="sm" />
								</div>
							</div>
						))}
					</div>
				),
			},
		],
		[
			execution,
			completedNodes,
			totalNodes,
			nodesLoading,
			nodeExecs.length,
			sortedNodeExecutions,
			guardrailsTabLabel,
			violationsLoading,
			violations,
			violationsFetched,
		],
	);

	return (
		<div
			data-tutorial={isFirst ? "execution-row" : undefined}
			className="rounded-2xl border border-slate-200
				bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_82%,#f59e0b_180%)]
				shadow-sm overflow-hidden
				transition-all duration-200
				hover:border-orange-400
				hover:shadow-[0_18px_44px_rgba(15,23,42,0.10)]"
		>
			{/* Card Header */}
			<div
				data-tutorial={isFirst ? "execution-row-header" : undefined}
				className="p-5 cursor-pointer transition-colors hover:bg-white"
				onClick={handleToggleExpand}
				onKeyDown={(e) => e.key === "Enter" && handleToggleExpand()}
				tabIndex={0}
				role="button"
				aria-expanded={isExpanded}
			>
				<div className="flex flex-wrap items-center justify-between gap-3">
					<div className="flex items-center gap-3 min-w-0 flex-1">
						<button
							onClick={(e) => {
								e.stopPropagation();
								handleToggleExpand();
							}}
							className="text-slate-500 hover:text-slate-800 transition-colors
								focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400 rounded"
							aria-label={isExpanded ? "Collapse" : "Expand"}
						>
							{isExpanded ? (
								<ChevronDown className="w-4 h-4" />
							) : (
								<ChevronRight className="w-4 h-4" />
							)}
						</button>
						<StatusIcon status={execution.status} />
						<div className="min-w-0">
							<h3 className="font-semibold text-slate-900 inline-flex items-center gap-2">
								{execution.graph_name}
								{execution.graph_version != null && (
									<span className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-mono font-normal text-orange-700">
										v{execution.graph_version}
									</span>
								)}
							</h3>
							<p className="text-xs font-mono text-slate-500 truncate">
								ID: {execution.id}
							</p>
						</div>
					</div>

					<div className="flex flex-wrap items-center justify-end gap-x-4 gap-y-2">
						{/* Timestamp & Duration */}
						<div className="text-right">
							<p className="text-sm text-slate-700">
								{formatTimestamp(execution.start_time)}
							</p>
							<p className="text-xs font-mono text-slate-500">
								Duration: {formatDuration(execution.duration_seconds)}
							</p>
						</div>

						{/* Status & Node Count */}
						<div className="flex items-center gap-2">
							<span
								className={`px-3 py-1 rounded-full text-[11px] font-medium border ${statusStyle.badgeClass}`}
							>
								{execution.status}
							</span>
							{execution.trigger_type &&
								SOURCE_STYLES[execution.trigger_type] && (
									<span
										className={`px-2.5 py-1 rounded-full text-[11px] font-medium border ${SOURCE_STYLES[execution.trigger_type].badgeClass}`}
									>
										{SOURCE_STYLES[execution.trigger_type].label}
									</span>
								)}
							<span
								className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
									text-[11px] font-medium
									border border-slate-200
									bg-white
									text-orange-700"
							>
								{completedNodes}/{totalNodes} nodes
							</span>
						</div>

						{/* Action Buttons */}
						<div data-tutorial={isFirst ? "execution-actions" : undefined} className="flex items-center gap-1">
							{/* Feedback Buttons */}
							{execution.status !== "running" && (
								<>
									<button
										onClick={(e) =>
											handleFeedback("positive", e)
										}
										disabled={feedbackLoading}
										className={`p-2.5 rounded-xl border transition-all focus-visible:outline-none focus-visible:ring-2
											${
												userRating === "positive"
													? "text-[#0DA931] bg-white border-[#0DA931]"
													: "text-slate-500 hover:text-[#0DA931] hover:bg-white border-transparent hover:border-[#0DA931]/50"
											}
											focus-visible:ring-[#0DA931]/45`}
										title="Good result"
									>
										<ThumbsUp
											className={`w-4 h-4 ${userRating === "positive" ? "fill-current" : ""}`}
										/>
									</button>
									<button
										onClick={(e) =>
											handleFeedback("negative", e)
										}
										disabled={feedbackLoading}
										className={`p-2.5 rounded-xl border transition-all focus-visible:outline-none focus-visible:ring-2
											${
												userRating === "negative"
													? "text-red-700 bg-white border-red-300"
													: "text-slate-500 hover:text-red-700 hover:bg-white border-transparent hover:border-red-300"
											}
											focus-visible:ring-red-400/45`}
										title="Bad result"
									>
										<ThumbsDown
											className={`w-4 h-4 ${userRating === "negative" ? "fill-current" : ""}`}
										/>
									</button>
									<div className="w-px h-5 bg-slate-200 mx-0.5" />
								</>
							)}
							<button
								data-tutorial={isFirst ? "export-btn" : undefined}
								onClick={handleViewDetails}
								className="p-2.5 rounded-xl
									text-slate-500
									hover:text-slate-900
									hover:bg-white
									border border-transparent hover:border-orange-300
									focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400
									transition-all"
								title="View Enhanced Details"
							>
								<Eye className="w-4 h-4" />
							</button>
							<button
								data-tutorial={isFirst ? "graph-view-btn" : undefined}
								onClick={handleViewGraph}
								className="p-2.5 rounded-xl
									text-slate-500
									hover:text-slate-900
									hover:bg-white
									border border-transparent hover:border-orange-300
									focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400
									transition-all"
								title="View Graph"
							>
								<GitBranch className="w-4 h-4" />
							</button>
							<button
								onClick={handleDelete}
								className="p-2.5 rounded-xl
									text-slate-500
									hover:text-red-700
									hover:bg-white
									border border-transparent hover:border-red-300
									focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400
									transition-all"
								title="Delete Execution"
							>
								<Trash2 className="w-4 h-4" />
							</button>
						</div>
					</div>
				</div>
			</div>

			{/* Expanded Content */}
			{isExpanded && (
				<div
					className="border-t border-slate-200
						bg-white"
				>
					<TabContainer
						tabs={tabs}
						activeTab={activeTab}
						onTabChange={handleTabChange}
						isDarkMode={false}
					/>
				</div>
			)}
		</div>
	);
});

export default ExecutionCard;
