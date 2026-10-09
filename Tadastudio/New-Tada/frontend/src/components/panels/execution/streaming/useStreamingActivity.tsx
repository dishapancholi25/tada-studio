"use client";

import { useCallback, useRef, useState } from "react";
import type {
	GuardrailViolationEvent,
	SubAgentCompleteEvent,
	SubAgentStartEvent,
	ToolCallCompleteEvent,
	ToolCallErrorEvent,
	ToolCallProgressEvent,
	ToolCallStartEvent,
} from "@/hooks/useExecutionWebSocket";
import type {
	ActivityItem,
	GuardrailViolationActivityItem,
	SubAgentActivityItem,
	ToolCallActivity,
} from "./ActivityFeed";

interface UseStreamingActivityOptions {
	maxActivities?: number; // Limit to prevent memory growth
}

interface UseStreamingActivityReturn {
	activities: ActivityItem[];
	handleToolCallStart: (event: ToolCallStartEvent) => void;
	handleToolCallProgress: (event: ToolCallProgressEvent) => void;
	handleToolCallComplete: (event: ToolCallCompleteEvent) => void;
	handleToolCallError: (event: ToolCallErrorEvent) => void;
	handleSubAgentStart: (event: SubAgentStartEvent) => void;
	handleSubAgentComplete: (event: SubAgentCompleteEvent) => void;
	handleGuardrailViolation: (event: GuardrailViolationEvent) => void;
	clearActivities: () => void;
}

export function useStreamingActivity(
	options: UseStreamingActivityOptions = {},
): UseStreamingActivityReturn {
	const { maxActivities = 50 } = options;
	const [activities, setActivities] = useState<ActivityItem[]>([]);

	// Track which sub-agent a tool call belongs to (for fallback matching)
	// Use ref for synchronous access in callbacks to avoid stale closure issues
	const activeSubAgentRef = useRef<string | null>(null);

	const handleToolCallStart = useCallback(
		(event: ToolCallStartEvent) => {
			// Skip activity creation for delegation tools - subagent_start handles these
			if (
				event.tool_name?.startsWith("delegate_to_") ||
				event.tool_node_type === "AGENT"
			) {
				return;
			}

			const newActivity: ToolCallActivity = {
				type: "tool_call",
				id: event.call_id,
				toolName: event.tool_name,
				status: "running",
				toolArgs: event.tool_args,
				agentId: event.agent_id,
				agentName: event.agent_name,
				timestamp: event.timestamp,
				// Review iteration for tool-to-iteration association
				reviewIteration: event.review_iteration,
				nodeExecutionId: event.node_execution_id,
				// Invocation index for multi-call subagent tracking
				invocationIndex: event.invocation_index,
				// Unique ID of parent subagent invocation for precise matching
				parentSubagentId: event.parent_subagent_id,
				// MCP provider detection
				toolNodeType: event.tool_node_type,
				toolNodeName: event.tool_node_name,
			};

			setActivities((prev) => {
				const toolParentSubagentId = newActivity.parentSubagentId;
				const toolInvocationIndex = newActivity.invocationIndex;

				// PRIMARY MATCHING: Use parent_subagent_id for precise matching
				// This ensures tools go to the correct subagent even with out-of-order events
				// Format matches subagent's uniqueId: "{node_id}_iter_{iteration}"
				if (toolParentSubagentId) {
					let nested = false;
					const mappedActivities = prev.map((activity) => {
						// Match by unique subagent ID (format: "{node_id}_iter_{iteration}")
						// Note: We match ALL subagent types since parent_subagent_id provides precise matching
						if (
							activity.type === "subagent" &&
							activity.id === toolParentSubagentId
						) {
							nested = true;
							return {
								...activity,
								nestedActivities: [
									...(activity.nestedActivities || []),
									newActivity,
								],
							};
						}
						return activity;
					});

					if (nested) {
						return mappedActivities;
					}
					// parent_subagent_id provided but no matching subagent found yet
					// Continue to fallback matching
				}

				// FALLBACK MATCHING: Only use invocation_index if parent_subagent_id not provided
				// (for backward compatibility with older backend versions)
				if (toolInvocationIndex != null && !toolParentSubagentId) {
					let nested = false;
					const mappedActivities = prev.map((activity) => {
						// Match subagent by iteration (which corresponds to invocation_index)
						if (
							activity.type === "subagent" &&
							activity.iteration === toolInvocationIndex
						) {
							nested = true;
							return {
								...activity,
								nestedActivities: [
									...(activity.nestedActivities || []),
									newActivity,
								],
							};
						}
						return activity;
					});

					if (nested) {
						return mappedActivities;
					}
				}

				// LAST RESORT FALLBACK: Use currently active subagent
				// Only used when neither parent_subagent_id nor invocation_index available
				const currentActiveSubAgent = activeSubAgentRef.current;
				const shouldNestByActive = currentActiveSubAgent && !toolParentSubagentId;
				if (shouldNestByActive) {
					let nested = false;
					const mappedActivities = prev.map((activity) => {
						if (
							activity.type === "subagent" &&
							activity.id === currentActiveSubAgent
						) {
							nested = true;
							return {
								...activity,
								nestedActivities: [
									...(activity.nestedActivities || []),
									newActivity,
								],
							};
						}
						return activity;
					});

					if (nested) {
						return mappedActivities;
					}
				}

				// Add as top-level activity (will be filtered by agentId to correct card)
				const updated = [...prev, newActivity];
				// Limit activities to prevent memory growth
				if (updated.length > maxActivities) {
					return updated.slice(-maxActivities);
				}
				return updated;
			});
		},
		[maxActivities],
	);

	const handleToolCallProgress = useCallback((event: ToolCallProgressEvent) => {
		setActivities((prev) =>
			prev.map((activity) => {
				// Check top-level tool calls
				if (activity.type === "tool_call" && activity.id === event.call_id) {
					return {
						...activity,
						progressMessage: event.message,
						progressPercent: event.progress,
					};
				}

				// Check nested tool calls in sub-agents
				if (activity.type === "subagent" && activity.nestedActivities) {
					return {
						...activity,
						nestedActivities: activity.nestedActivities.map((nested) =>
							nested.id === event.call_id
								? {
										...nested,
										progressMessage: event.message,
										progressPercent: event.progress,
									}
								: nested,
						),
					};
				}

				return activity;
			}),
		);
	}, []);

	const handleToolCallComplete = useCallback((event: ToolCallCompleteEvent) => {
		setActivities((prev) =>
			prev.map((activity) => {
				// Check top-level tool calls
				if (activity.type === "tool_call" && activity.id === event.call_id) {
					return {
						...activity,
						status: "complete",
						durationMs: event.duration_ms,
						progressMessage: undefined,
						progressPercent: undefined,
					};
				}

				// Check nested tool calls in sub-agents
				if (activity.type === "subagent" && activity.nestedActivities) {
					return {
						...activity,
						nestedActivities: activity.nestedActivities.map((nested) =>
							nested.id === event.call_id
								? {
										...nested,
										status: "complete" as const,
										durationMs: event.duration_ms,
										progressMessage: undefined,
										progressPercent: undefined,
									}
								: nested,
						),
					};
				}

				return activity;
			}),
		);
	}, []);

	const handleToolCallError = useCallback((event: ToolCallErrorEvent) => {
		setActivities((prev) =>
			prev.map((activity) => {
				// Check top-level tool calls
				if (activity.type === "tool_call" && activity.id === event.call_id) {
					return {
						...activity,
						status: "error",
						error: event.error,
						durationMs: event.duration_ms,
						progressMessage: undefined,
						progressPercent: undefined,
					};
				}

				// Check nested tool calls in sub-agents
				if (activity.type === "subagent" && activity.nestedActivities) {
					return {
						...activity,
						nestedActivities: activity.nestedActivities.map((nested) =>
							nested.id === event.call_id
								? {
										...nested,
										status: "error" as const,
										error: event.error,
										durationMs: event.duration_ms,
										progressMessage: undefined,
										progressPercent: undefined,
									}
								: nested,
						),
					};
				}

				return activity;
			}),
		);
	}, []);

	const handleSubAgentStart = useCallback(
		(event: SubAgentStartEvent) => {
			// Create unique ID combining subagent_id and iteration to distinguish
			// multiple invocations of the same subagent
			const iteration = event.iteration || 1;
			const uniqueId = `${event.subagent_id}_iter_${iteration}`;

			const newActivity: SubAgentActivityItem = {
				type: "subagent",
				id: uniqueId, // Unique per iteration
				subagentId: event.subagent_id, // Original subagent ID
				subagentName: event.subagent_name,
				status: "running",
				taskDescription: event.task_description,
				parentAgentId: event.parent_agent_id,
				parentAgentName: event.parent_agent_name,
				timestamp: event.timestamp,
				iteration: iteration,
				nestedActivities: [],
				subagentNodeType: event.subagent_node_type, // Store node type for nesting decisions
			};

			// Set ref for synchronous access in callbacks
			activeSubAgentRef.current = uniqueId;

			setActivities((prev) => {
				const updated = [...prev, newActivity];
				if (updated.length > maxActivities) {
					return updated.slice(-maxActivities);
				}
				return updated;
			});
		},
		[maxActivities],
	);

	const handleSubAgentComplete = useCallback((event: SubAgentCompleteEvent) => {
		// Create unique ID matching the format used in handleSubAgentStart
		const iteration = event.iteration || 1;
		const uniqueId = `${event.subagent_id}_iter_${iteration}`;

		// Clear active sub-agent if this one completed
		if (activeSubAgentRef.current === uniqueId) {
			activeSubAgentRef.current = null;
		}

		setActivities((prev) =>
			prev.map((activity) => {
				if (activity.type === "subagent" && activity.id === uniqueId) {
					return {
						...activity,
						status: event.success ? "complete" : "error",
						durationMs: event.duration_ms,
						toolsUsed: event.tools_used,
					};
				}
				return activity;
			}),
		);
	}, []);

	const handleGuardrailViolation = useCallback(
		(event: GuardrailViolationEvent) => {
			const newActivity: GuardrailViolationActivityItem = {
				type: "guardrail_violation",
				id: `guardrail_${event.category}_${Date.now()}`,
				category: event.category,
				ruleName: event.rule_name,
				message: event.message,
				severity: event.severity,
				agentId: event.agent_id,
				agentName: event.agent_name,
				toolName: event.tool_name,
				violationDbId: event.violation_db_id,
				policyName: event.policy_name,
				details: event.details,
				enforcementMode: event.enforcement_mode,
				timestamp: event.timestamp,
			};

			setActivities((prev) => {
				const updated = [...prev, newActivity];
				if (updated.length > maxActivities) {
					return updated.slice(-maxActivities);
				}
				return updated;
			});
		},
		[maxActivities],
	);

	const clearActivities = useCallback(() => {
		setActivities([]);
		activeSubAgentRef.current = null;
	}, []);

	return {
		activities,
		handleToolCallStart,
		handleToolCallProgress,
		handleToolCallComplete,
		handleToolCallError,
		handleSubAgentStart,
		handleSubAgentComplete,
		handleGuardrailViolation,
		clearActivities,
	};
}
