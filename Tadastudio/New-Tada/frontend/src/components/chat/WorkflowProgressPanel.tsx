"use client";

import { type CSSProperties, useEffect, useMemo, useRef, useState } from "react";
import { ChevronRight, PanelRightClose, Sparkles } from "lucide-react";

import type { TimelineEntry } from "@/components/panels/execution/streaming/useTimelineState";
import MiniNodeCard from "./MiniNodeCard";
import MiniToolCard from "./MiniToolCard";
import VerticalConnector from "./VerticalConnector";
import { useWorkflowProgress } from "./useWorkflowProgress";
import { formatDuration } from "./MiniNodeCard";

/** Scoped tokens so chat workflow panel reads orange/white with dark text (panel is chat-only). */
const CHAT_WORKFLOW_PANEL_THEME: CSSProperties = {
	"--wp-panel-top": "rgba(255,247,237,0.98)",
	"--wp-panel-bottom": "rgba(255,237,213,0.88)",
	"--wp-border": "rgba(249,115,22,0.28)",
	"--wp-card-completed-bg": "rgba(241,248,233,0.95)",
	"--wp-card-completed-border": "rgba(13,169,49,0.5)",
	"--wp-card-running-bg": "rgba(255,237,213,0.98)",
	"--wp-card-running-border": "rgba(249,115,22,0.7)",
	"--wp-card-pending-bg": "rgba(248,250,252,0.9)",
	"--wp-card-pending-border": "rgba(148,163,184,0.5)",
	"--wp-card-error-bg": "rgba(254,242,242,0.95)",
	"--wp-card-error-border": "rgba(239,68,68,0.5)",
	"--color-text-primary": "#0f172a",
	"--color-text-secondary": "#334155",
	"--color-text-disabled": "#64748b",
	"--color-text-muted": "#64748b",
} as CSSProperties;

const TRACE_PANEL_THEME: CSSProperties = {
	"--wp-panel-top": "rgba(255,255,255,1)",
	"--wp-panel-bottom": "rgba(248,250,252,1)",
	"--wp-border": "rgba(203,213,225,0.60)",
	"--wp-card-completed-bg": "rgba(241,248,233,1)",
	"--wp-card-completed-border": "rgba(13,169,49,0.5)",
	"--wp-card-running-bg": "rgba(255,247,237,1)",
	"--wp-card-running-border": "rgba(249,115,22,0.6)",
	"--wp-card-pending-bg": "rgba(248,250,252,1)",
	"--wp-card-pending-border": "rgba(148,163,184,0.5)",
	"--wp-card-error-bg": "rgba(254,242,242,1)",
	"--wp-card-error-border": "rgba(239,68,68,0.5)",
	"--color-text-primary": "#0f172a",
	"--color-text-secondary": "#1e293b",
	"--color-text-disabled": "#334155",
	"--color-text-muted": "#334155",
} as CSSProperties;

/* ── Props ─────────────────────────────────────────── */

interface WorkflowProgressPanelProps {
	workflowId: string | undefined;
	wsNodeExecutions: Map<string, TimelineEntry>;
	runningNodes: Set<string>;
	isExecuting: boolean;
	/** Whether viewing a historical trace (not live) */
	isTrace?: boolean;
	onCollapse: () => void;
}

/* ── Constants ─────────────────────────────────────── */

const PANEL_WIDTH_EXPANDED = 320;
const PANEL_WIDTH_COLLAPSED = 48;

/* ── Empty state ghost cards ───────────────────────── */

function EmptyState() {
	return (
		<div className="flex flex-1 flex-col items-center justify-center gap-2 px-4">
			{[0, 1, 2].map((i) => (
				<div key={i} className="flex w-full flex-col items-center">
					<div
						className="h-12 w-full rounded-xl border border-dashed border-orange-200/50 bg-orange-50/30"
					/>
					{i < 2 && (
						<div
							className="my-1 h-4 w-[2px] rounded-full bg-[repeating-linear-gradient(to_bottom,rgba(148,163,184,0.45)_0px,rgba(148,163,184,0.45)_3px,transparent_3px,transparent_6px)]"
						/>
					)}
				</div>
			))}
			<p className="mt-4 text-center text-xs text-slate-500">
				Run a workflow to see execution progress
			</p>
		</div>
	);
}

/* ── Main component ────────────────────────────────── */

export default function WorkflowProgressPanel({
	workflowId,
	wsNodeExecutions,
	runningNodes,
	isExecuting,
	isTrace,
	onCollapse,
}: WorkflowProgressPanelProps) {
	const { progressNodes, currentRunningNodeId, graphLoaded, graphError } =
		useWorkflowProgress({
			workflowId,
			wsNodeExecutions,
			runningNodes,
			isExecuting: isExecuting || !!isTrace,
		});

	const [isCollapsed, setIsCollapsed] = useState(false);

	// Auto-scroll to running node
	const runningRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (runningRef.current) {
			runningRef.current.scrollIntoView({
				behavior: "smooth",
				block: "center",
			});
		}
	}, [currentRunningNodeId]);

	// Derived stats
	const { stepCount, totalDuration, workflowComplete } = useMemo(() => {
		const mainNodes = progressNodes.filter((n) => !n.isTool);
		const activeNodes = mainNodes.filter(
			(n) => n.status !== "idle" && n.status !== "pending" && n.status !== "skipped",
		);
		const total = activeNodes.reduce(
			(sum, n) => sum + (n.durationSeconds ?? 0),
			0,
		);
		const allDone = mainNodes.length > 0 && mainNodes.every(
			(n) => n.status === "completed" || n.status === "skipped",
		);
		return {
			stepCount: activeNodes.length,
			totalDuration: total,
			workflowComplete: allDone,
		};
	}, [progressNodes]);

	const showStats = stepCount > 0;
	const showEmptyState = graphLoaded && progressNodes.length === 0 && !isExecuting;

	// Panel width
	const panelWidth = isCollapsed ? PANEL_WIDTH_COLLAPSED : PANEL_WIDTH_EXPANDED;

	// Panel base styles
	const panelStyle: CSSProperties = {
		width: panelWidth,
		transition: "width 250ms ease-in-out",
	};

	// Loading state
	if (!graphLoaded && !graphError) {
		return (
			<div
				className="flex shrink-0 items-center justify-center border-l border-orange-200/50"
				style={{
					...panelStyle,
					...(isTrace ? TRACE_PANEL_THEME : CHAT_WORKFLOW_PANEL_THEME),
					background: "linear-gradient(to bottom, var(--wp-panel-top), var(--wp-panel-bottom))",
					backdropFilter: "blur(20px) saturate(170%)",
					boxShadow: "inset 1px 0 0 rgba(255,255,255,0.8)",
				}}
			>
				<div className="rounded-2xl border border-orange-200/70 bg-white/75 px-4 py-3 text-center shadow-[0_14px_34px_rgba(249,115,22,0.16)] backdrop-blur-xl">
					<Sparkles className="mx-auto mb-2 h-4 w-4 animate-pulse text-orange-500" />
					<span className="text-xs font-semibold text-slate-700">Loading workflow...</span>
				</div>
			</div>
		);
	}

	// Error state
	if (graphError) {
		return (
			<div
				className="flex shrink-0 items-center justify-center border-l border-orange-200/50 p-4"
				style={{
					...panelStyle,
					...(isTrace ? TRACE_PANEL_THEME : CHAT_WORKFLOW_PANEL_THEME),
					background: "linear-gradient(to bottom, var(--wp-panel-top), var(--wp-panel-bottom))",
					backdropFilter: "blur(20px) saturate(170%)",
					boxShadow: "inset 1px 0 0 rgba(255,255,255,0.8)",
				}}
			>
				<p className="rounded-2xl border border-orange-200/70 bg-white/75 px-4 py-3 text-center text-xs font-medium text-slate-700 shadow-[0_14px_34px_rgba(249,115,22,0.14)]">
					{graphError}
				</p>
			</div>
		);
	}

	/* ── Collapsed mode ─────────────────── */

	if (isCollapsed) {
		return (
			<div
				className="flex shrink-0 flex-col border-l border-orange-200/50"
				style={{
					...panelStyle,
					...(isTrace ? TRACE_PANEL_THEME : CHAT_WORKFLOW_PANEL_THEME),
					background: "linear-gradient(to bottom, var(--wp-panel-top), var(--wp-panel-bottom))",
					backdropFilter: "blur(20px) saturate(170%)",
					boxShadow: "inset 1px 0 0 rgba(255,255,255,0.8)",
				}}
			>
				{/* Expand button */}
				<div className="flex h-[52px] items-center justify-center border-b border-orange-200/60 bg-gradient-to-r from-orange-100/75 via-white/55 to-orange-50/60">
					<button
						type="button"
						onClick={() => setIsCollapsed(false)}
						className="rounded-lg border border-orange-200/70 bg-white/70 p-1 text-orange-700 shadow-sm transition-colors hover:bg-orange-50"
					>
						<ChevronRight className="h-3.5 w-3.5 rotate-180" />
					</button>
				</div>

				{/* Icon strip */}
				<div className="flex flex-1 flex-col items-center gap-0 overflow-y-auto bg-gradient-to-b from-orange-50/25 via-white/25 to-orange-50/35 py-3">
					{(() => {
						let connIdx = 0;
						return progressNodes.map((node, idx) => {
							if (node.isTool) return null;

							let nextMainNode = null;
							for (let j = idx + 1; j < progressNodes.length; j++) {
								if (!progressNodes[j].isTool) {
									nextMainNode = progressNodes[j];
									break;
								}
							}

							return (
								<div key={node.nodeId} className="flex flex-col items-center">
									<MiniNodeCard
										ref={node.nodeId === currentRunningNodeId ? runningRef : undefined}
										node={node}
										collapsed
									/>
									{nextMainNode && (
										<VerticalConnector
											topStatus={node.status}
											bottomStatus={nextMainNode.status}
											workflowComplete={workflowComplete}
											connectorIndex={connIdx++}
											collapsed
											tone="light"
										/>
									)}
								</div>
							);
						});
					})()}
				</div>
			</div>
		);
	}

	/* ── Expanded mode ──────────────────── */

	return (
		<div
			className="flex shrink-0 flex-col border-l border-orange-200/60"
			style={{
				...panelStyle,
				...(isTrace ? TRACE_PANEL_THEME : CHAT_WORKFLOW_PANEL_THEME),
				background: "linear-gradient(to bottom, var(--wp-panel-top), var(--wp-panel-bottom))",
				backdropFilter: "blur(20px) saturate(170%)",
				boxShadow: "inset 1px 0 0 rgba(255,255,255,0.8)",
			}}
		>
			{/* Header */}
			<div className={`px-5 pb-0 pt-5 ${isTrace ? "bg-gradient-to-r from-slate-100/90 via-white/80 to-slate-50/90 shadow-[0_12px_30px_rgba(15,23,42,0.06)]" : "bg-gradient-to-r from-orange-100/80 via-white/60 to-orange-50/70 shadow-[0_12px_30px_rgba(249,115,22,0.08)]"}`}>
				<div className={`flex items-center justify-between rounded-2xl border px-3 py-2 backdrop-blur-xl ${isTrace ? "border-slate-200/80 bg-white/90 shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_10px_26px_rgba(15,23,42,0.06)]" : "border-white/70 bg-white/70 shadow-[inset_0_1px_0_rgba(255,255,255,0.9),0_10px_26px_rgba(249,115,22,0.12)]"}`}>
					<div className="flex items-center gap-2">
						<span className={`flex h-7 w-7 items-center justify-center rounded-xl text-white ${isTrace ? "bg-gradient-to-br from-slate-500 to-slate-400 shadow-[0_8px_18px_rgba(15,23,42,0.18)]" : "bg-gradient-to-br from-orange-500 to-orange-400 shadow-[0_8px_18px_rgba(249,115,22,0.28)]"}`}>
							<Sparkles className="h-3.5 w-3.5 animate-wpSparklePulse" />
						</span>
						<span className={`text-sm font-semibold ${isTrace ? "text-slate-700" : "text-slate-800"}`}>
							{isTrace ? "Execution Trace" : "Workflow Progress"}
						</span>
					</div>
					<div className="flex items-center gap-1">
						<button
							type="button"
							onClick={() => setIsCollapsed(true)}
							className={`rounded-lg p-1 transition-colors ${isTrace ? "text-slate-500 hover:bg-slate-100 hover:text-slate-700" : "text-orange-700 hover:bg-orange-50 hover:text-slate-900"}`}
							title="Collapse panel"
						>
							<ChevronRight className="h-3.5 w-3.5" />
						</button>
						<button
							type="button"
							onClick={onCollapse}
							className={`rounded-lg p-1 transition-colors ${isTrace ? "text-slate-500 hover:bg-slate-100 hover:text-slate-700" : "text-orange-700 hover:bg-orange-50 hover:text-slate-900"}`}
							title="Hide panel"
						>
							<PanelRightClose className="h-3.5 w-3.5" />
						</button>
					</div>
				</div>

				{/* Stats row */}
				{showStats && (
					<p className="ml-[46px] mt-2 text-xs font-medium text-orange-700/80">
						{stepCount} step{stepCount !== 1 ? "s" : ""}
						{totalDuration > 0 && ` · ${formatDuration(totalDuration)} total`}
					</p>
				)}

				{/* Divider */}
				<div className="mt-4 border-b border-orange-200/60" />
			</div>

			{/* Node list */}
			<div className={`chat-scrollbar flex-1 overflow-y-auto px-4 py-4 ${isTrace ? "bg-gradient-to-b from-slate-50/60 via-white/70 to-slate-50/60" : "bg-gradient-to-b from-orange-50/30 via-white/35 to-orange-50/40"}`}>
				{showEmptyState ? (
					<EmptyState />
				) : (
					<div className="flex flex-col items-stretch gap-2">
						{(() => {
							let mainIdx = 0;
							let connIdx = 0;

							return progressNodes.map((node, idx) => {
								if (node.isTool) return null;

								const staggerIdx = mainIdx++;
								const isRunning = node.nodeId === currentRunningNodeId;

								// Collect tool children
								const toolChildren = progressNodes.filter(
									(n) => n.isTool && n.parentNodeId === node.nodeId,
								);

								// Find next non-tool node
								let nextMainNode = null;
								for (let j = idx + 1; j < progressNodes.length; j++) {
									if (!progressNodes[j].isTool) {
										nextMainNode = progressNodes[j];
										break;
									}
								}
								const hasNextMainNode = nextMainNode !== null;

								// Branch label for condition nodes
								let branchLabel: string | undefined;
								if (
									(node.nodeType === "CONDITION" || node.nodeType === "CONDITIONAL") &&
									node.branches &&
									nextMainNode &&
									node.status === "completed"
								) {
									const takenBranch = node.branches.find(
										(b) => b.targetNodeId === nextMainNode!.nodeId,
									);
									if (takenBranch) branchLabel = takenBranch.label;
								}

								return (
									<div
										key={node.nodeId}
										className="animate-wpStepEntrance"
										style={{ "--step-index": staggerIdx } as CSSProperties}
									>
										<MiniNodeCard
											ref={isRunning ? runningRef : undefined}
											node={node}
										/>

										{/* Tool children */}
										{toolChildren.length > 0 && (
											<div className="ml-6 my-1.5 flex flex-col gap-1.5 rounded-l-2xl border-l-2 border-orange-300/70 bg-orange-50/35 py-1 pl-3">
												{toolChildren.map((tool) => (
													<MiniToolCard
														key={tool.nodeId}
														ref={
															tool.nodeId === currentRunningNodeId
																? runningRef
																: undefined
														}
														node={tool}
													/>
												))}
											</div>
										)}

										{/* Connector to next node */}
										{hasNextMainNode && (
											<VerticalConnector
												topStatus={node.status}
												bottomStatus={nextMainNode!.status}
												branchLabel={branchLabel}
												workflowComplete={workflowComplete}
												connectorIndex={connIdx++}
												tone="light"
											/>
										)}
									</div>
								);
							});
						})()}
					</div>
				)}
			</div>
		</div>
	);
}
