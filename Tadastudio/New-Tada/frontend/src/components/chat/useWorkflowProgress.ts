import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import type { TimelineEntry } from "@/components/panels/execution/streaming/useTimelineState";
import {
	type ProgressNode,
	type WorkflowStep,
	mapExecutionStatus,
	topologicalSort,
} from "./workflowProgressUtils";

interface UseWorkflowProgressOptions {
	workflowId: string | undefined;
	wsNodeExecutions: Map<string, TimelineEntry>;
	runningNodes: Set<string>;
	isExecuting: boolean;
}

interface UseWorkflowProgressReturn {
	/** Ordered nodes with live execution status merged in */
	progressNodes: ProgressNode[];
	/** The currently running node ID (most recent if multiple) */
	currentRunningNodeId: string | null;
	/** Whether the graph definition loaded successfully */
	graphLoaded: boolean;
	/** Error loading the graph */
	graphError: string | null;
}

export function useWorkflowProgress({
	workflowId,
	wsNodeExecutions,
	runningNodes,
	isExecuting,
}: UseWorkflowProgressOptions): UseWorkflowProgressReturn {
	const [steps, setSteps] = useState<WorkflowStep[]>([]);
	const [graphLoaded, setGraphLoaded] = useState(false);
	const [graphError, setGraphError] = useState<string | null>(null);

	// Fetch graph definition when workflowId changes
	useEffect(() => {
		if (!workflowId) {
			setSteps([]);
			setGraphLoaded(true);
			setGraphError(null);
			return;
		}

		let cancelled = false;
		setGraphLoaded(false);
		setGraphError(null);

		async function loadGraph() {
			try {
				const result = await api.getGraphByWorkflowId(workflowId!);
				if (cancelled) return;

				if (result.success && result.graph) {
					const sorted = topologicalSort(result.graph as any);
					setSteps(sorted);
					setGraphLoaded(true);
					setGraphError(null);
				} else {
					setGraphError("Failed to load workflow graph");
				}
			} catch (err) {
				if (cancelled) return;
				setGraphError(
					err instanceof Error ? err.message : "Failed to load graph",
				);
			}
		}

		loadGraph();
		return () => {
			cancelled = true;
		};
	}, [workflowId]);

	// Merge static steps with live timeline data
	const progressNodes = useMemo<ProgressNode[]>(() => {
		if (steps.length === 0) return [];

		// Build a lookup: node_id -> best matching TimelineEntry
		// A node may have multiple entries (sub-agent re-executions), take the most recent
		const timelineByNodeId = new Map<string, TimelineEntry>();
		for (const [, entry] of wsNodeExecutions) {
			const existing = timelineByNodeId.get(entry.node_id);
			if (
				!existing ||
				(entry.timestamp && (!existing.timestamp || entry.timestamp > existing.timestamp))
			) {
				timelineByNodeId.set(entry.node_id, entry);
			}
		}

		// Determine if we have any running/completed nodes (execution has started)
		const hasActivity = timelineByNodeId.size > 0;

		// Find the position of the first running node in our ordered list
		let firstRunningIdx = -1;
		if (isExecuting) {
			firstRunningIdx = steps.findIndex((s) => {
				const entry = timelineByNodeId.get(s.nodeId);
				return entry?.status === "running";
			});
		}

		return steps.map((step, idx) => {
			const entry = timelineByNodeId.get(step.nodeId);

			let status: ProgressNode["status"];
			if (entry) {
				status = mapExecutionStatus(entry.status);
			} else if (isExecuting && hasActivity) {
				// Nodes after the current running node are "pending"
				// Nodes before with no entry are likely skipped (condition branch not taken)
				if (firstRunningIdx >= 0 && idx > firstRunningIdx) {
					status = "pending";
				} else if (firstRunningIdx >= 0 && idx < firstRunningIdx) {
					// Before the running node but no entry — skipped (condition branch)
					// Only mark as skipped if it's not a START/END node
					status =
						step.nodeType === "START" || step.nodeType === "END"
							? "idle"
							: "skipped";
				} else {
					status = "idle";
				}
			} else {
				status = "idle";
			}

			return {
				...step,
				status,
				durationSeconds: entry?.duration_seconds ?? undefined,
				activeBranch: undefined, // Could be enriched later
			};
		});
	}, [steps, wsNodeExecutions, isExecuting]);

	// Find the most recently started running node
	const currentRunningNodeId = useMemo(() => {
		if (runningNodes.size === 0) return null;
		// Return the last one in the ordered steps that is running
		for (let i = progressNodes.length - 1; i >= 0; i--) {
			if (progressNodes[i].status === "running") {
				return progressNodes[i].nodeId;
			}
		}
		return null;
	}, [progressNodes, runningNodes]);

	return {
		progressNodes,
		currentRunningNodeId,
		graphLoaded,
		graphError,
	};
}
