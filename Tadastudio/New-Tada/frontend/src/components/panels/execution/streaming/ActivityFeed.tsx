"use client";

import { Activity } from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useRef } from "react";
import { GuardrailViolationActivity } from "./GuardrailViolationActivity";
import { SubAgentActivity, SubAgentActivityProps } from "./SubAgentActivity";
import { ToolCallActivity, ToolCallActivityProps } from "./ToolCallActivity";

// Activity item types
export interface ToolCallActivity {
	type: "tool_call";
	id: string; // call_id
	toolName: string;
	status: "running" | "complete" | "error";
	toolArgs?: Record<string, any>;
	progressMessage?: string;
	progressPercent?: number;
	durationMs?: number;
	agentName?: string;
	agentId?: string;
	error?: string;
	timestamp: string;
	// Review iteration for tool-to-iteration association
	reviewIteration?: number;
	nodeExecutionId?: string;
	// Invocation index for multi-call subagent tracking
	invocationIndex?: number;
	// Unique ID of parent subagent invocation for precise tool-to-subagent association
	parentSubagentId?: string;
	// MCP provider detection fields
	toolNodeType?: string;
	toolNodeName?: string;
}

export interface SubAgentActivityItem {
	type: "subagent";
	id: string; // Unique ID (subagent_id + iteration)
	subagentId?: string; // Original subagent node ID
	subagentName: string;
	status: "running" | "complete" | "error";
	taskDescription?: string;
	parentAgentId?: string;
	parentAgentName?: string;
	durationMs?: number;
	toolsUsed?: string[];
	timestamp: string;
	iteration?: number; // Iteration number for distinguishing multiple invocations
	// Nested activities (tool calls made by this sub-agent)
	nestedActivities?: ToolCallActivity[];
	// Node type of subagent (e.g., "AGENT", "TOOL", "SUBWORKFLOW")
	subagentNodeType?: string;
}

export interface GuardrailViolationActivityItem {
	type: "guardrail_violation";
	id: string;
	category: string;
	ruleName: string;
	message: string;
	severity: string;
	agentId?: string;
	agentName?: string;
	toolName?: string;
	violationDbId?: string;
	policyName?: string;
	details?: Record<string, unknown> | null;
	enforcementMode?: string | null;
	timestamp: string;
}

export type ActivityItem =
	| ToolCallActivity
	| SubAgentActivityItem
	| GuardrailViolationActivityItem;

export interface ActivityFeedProps {
	activities: ActivityItem[];
	maxHeight?: string;
	showHeader?: boolean;
	emptyMessage?: string;
	/** If provided, only show activities matching this review iteration */
	currentIteration?: number;
	/** If provided, only show activities for this agent */
	agentId?: string;
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({
	activities,
	maxHeight = "300px",
	showHeader = true,
	emptyMessage = "No activity yet",
	currentIteration,
	agentId,
}) => {
	const scrollRef = useRef<HTMLDivElement>(null);

	// Auto-scroll to bottom when new activities are added
	useEffect(() => {
		if (scrollRef.current) {
			scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
		}
	}, [activities.length]);

	// Filter and sort activities - memoized for performance
	const sortedActivities = useMemo(() => {
		// Filter by iteration and agent if specified
		const filtered = activities.filter((activity) => {
			// Filter by iteration if specified
			if (currentIteration !== undefined && activity.type === "tool_call") {
				if (activity.reviewIteration != null && activity.reviewIteration !== currentIteration) {
					return false;
				}
			}
			// Filter by agent if specified
			if (agentId !== undefined && activity.type === "tool_call") {
				if (activity.agentId !== agentId) {
					return false;
				}
			}
			return true;
		});

		// Sort by timestamp (most recent last)
		return filtered.sort(
			(a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
		);
	}, [activities, currentIteration, agentId]);

	// Count running activities (from filtered set for accuracy)
	const runningCount = useMemo(
		() =>
			sortedActivities.filter(
				(a) => a.type !== "guardrail_violation" && a.status === "running",
			).length,
		[sortedActivities],
	);

	if (activities.length === 0) {
		return (
			<div className="flex items-center justify-center py-4 text-[color:var(--color-text-muted)] text-sm">
				{emptyMessage}
			</div>
		);
	}

	return (
		<div className="flex flex-col">
			{showHeader && (
				<div className="flex items-center gap-2 mb-2">
					<Activity className="h-4 w-4 text-[color:var(--color-text-muted)]" />
					<span className="text-sm font-medium text-[color:var(--color-text-secondary)]">
						Live Activity
					</span>
					{runningCount > 0 && (
							<span className="text-xs bg-[rgba(var(--color-primary-rgb),0.2)] text-[color:var(--color-primary)] px-1.5 py-0.5 rounded">
							{runningCount} running
						</span>
					)}
				</div>
			)}
			<div
				ref={scrollRef}
				className="space-y-2 overflow-y-auto pr-1"
				style={{ maxHeight }}
			>
				{sortedActivities.map((activity) => {
					if (activity.type === "tool_call") {
						return (
							<ToolCallActivity
								key={activity.id}
								callId={activity.id}
								toolName={activity.toolName}
								status={activity.status}
								toolArgs={activity.toolArgs}
								progressMessage={activity.progressMessage}
								progressPercent={activity.progressPercent}
								durationMs={activity.durationMs}
								agentName={activity.agentName}
								error={activity.error}
								toolNodeType={activity.toolNodeType}
								toolNodeName={activity.toolNodeName}
							/>
						);
					}

					if (activity.type === "guardrail_violation") {
						return (
							<GuardrailViolationActivity
								key={activity.id}
								category={activity.category}
								ruleName={activity.ruleName}
								message={activity.message}
								severity={activity.severity}
								agentName={activity.agentName}
								toolName={activity.toolName}
								details={activity.details}
								enforcementMode={activity.enforcementMode}
							/>
						);
					}

					if (activity.type === "subagent") {
						return (
							<SubAgentActivity
								key={activity.id}
								subagentId={activity.id}
								subagentName={activity.subagentName}
								status={activity.status}
								taskDescription={activity.taskDescription}
								parentAgentName={activity.parentAgentName}
								durationMs={activity.durationMs}
								toolsUsed={activity.toolsUsed}
							>
								{/* Render nested tool calls */}
								{activity.nestedActivities?.map((nested) => (
									<ToolCallActivity
										key={nested.id}
										callId={nested.id}
										toolName={nested.toolName}
										status={nested.status}
										toolArgs={nested.toolArgs}
										progressMessage={nested.progressMessage}
										progressPercent={nested.progressPercent}
										durationMs={nested.durationMs}
										error={nested.error}
										toolNodeType={nested.toolNodeType}
										toolNodeName={nested.toolNodeName}
									/>
								))}
							</SubAgentActivity>
						);
					}

					return null;
				})}
			</div>
		</div>
	);
};

export default ActivityFeed;
