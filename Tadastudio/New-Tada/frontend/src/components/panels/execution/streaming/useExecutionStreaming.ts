"use client";

import { useCallback, useMemo } from "react";
import type {
	ContentChunkEvent,
	GuardrailViolationEvent,
	SubAgentCompleteEvent,
	SubAgentStartEvent,
	ToolCallCompleteEvent,
	ToolCallErrorEvent,
	ToolCallProgressEvent,
	ToolCallStartEvent,
} from "@/hooks/useExecutionWebSocket";
import type { NodeExecution } from "@/types/api";
import type { ActivityItem } from "./ActivityFeed";
import { useStreamingActivity } from "./useStreamingActivity";
import {
	type ExecutionData,
	type NodeUpdateMetadata,
	type TimelineEntry,
	type UseTimelineStateOptions,
	useTimelineState,
} from "./useTimelineState";

// ============================================================================
// Types
// ============================================================================

/** Options for the coordinator hook */
export interface UseExecutionStreamingOptions {
	// Timeline-specific options
	executionId?: string | null;
	dbExecutionId?: string | null;
	isExecuting?: boolean;
	onExecutionChange?: (executionData: ExecutionData) => void;
	onNodeRunning?: (nodeId: string) => void;
	onNodeStopped?: (nodeId: string | null) => void;

	// Activity feed options
	maxActivities?: number;

	// Guardrail violation severity callbacks
	onGuardrailBlock?: (event: GuardrailViolationEvent) => void;
	onGuardrailWarn?: (event: GuardrailViolationEvent) => void;
}

/** Unified event handlers for WebSocket integration */
export interface ExecutionStreamingHandlers {
	onNodeUpdate: (
		nodeId: string,
		status: string,
		output?: any,
		metadata?: NodeUpdateMetadata,
	) => void;
	onTokenStream: (params: {
		nodeId?: string | null;
		step?: number;
		content: string;
	}) => void;
	onToolCallStart: (event: ToolCallStartEvent) => void;
	onToolCallProgress: (event: ToolCallProgressEvent) => void;
	onToolCallComplete: (event: ToolCallCompleteEvent) => void;
	onToolCallError: (event: ToolCallErrorEvent) => void;
	onSubAgentStart: (event: SubAgentStartEvent) => void;
	onSubAgentComplete: (event: SubAgentCompleteEvent) => void;
	onContentChunk: (event: ContentChunkEvent) => void;
	onGuardrailViolation: (event: GuardrailViolationEvent) => void;
}

/** Return type of the coordinator hook */
export interface UseExecutionStreamingReturn {
	// Timeline state (exposed for UI)
	wsNodeExecutions: Map<string, TimelineEntry>;
	wsNodeExecutionsRef: React.MutableRefObject<Map<string, TimelineEntry>>;
	runningNodes: Set<string>;

	// Activity state (exposed for UI)
	activities: ActivityItem[];

	// Unified event handlers
	handlers: ExecutionStreamingHandlers;

	// Utilities
	loadInitialData: (nodes: NodeExecution[]) => void;
	clearState: () => void;
	getNodeExecutions: () => TimelineEntry[];
	markAllNodesAsStopped: () => void;
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Coordinator hook that composes useTimelineState and useStreamingActivity.
 *
 * This hook provides unified event handlers that update both the timeline state
 * (for node execution tracking) and activity feed (for streaming UI) atomically.
 *
 * Usage:
 * ```tsx
 * const streaming = useExecutionStreaming({
 *   executionId,
 *   isExecuting,
 *   onExecutionChange,
 *   maxActivities: 50,
 * });
 *
 * useExecutionWebSocket(executionId, {
 *   onNodeUpdate: streaming.handlers.onNodeUpdate,
 *   onToolCallStart: streaming.handlers.onToolCallStart,
 *   // ... other handlers from streaming.handlers
 * });
 * ```
 */
export function useExecutionStreaming(
	options: UseExecutionStreamingOptions = {},
): UseExecutionStreamingReturn {
	const {
		executionId,
		dbExecutionId,
		isExecuting = false,
		onExecutionChange,
		onNodeRunning,
		onNodeStopped,
		maxActivities = 50,
		onGuardrailBlock,
		onGuardrailWarn,
	} = options;

	// Compose the underlying hooks
	const timeline = useTimelineState({
		executionId,
		dbExecutionId,
		isExecuting,
		onExecutionChange,
		onNodeRunning,
		onNodeStopped,
	});

	const streamingActivity = useStreamingActivity({
		maxActivities,
	});

	// -------------------------------------------------------------------------
	// Unified handlers that coordinate both hooks
	// -------------------------------------------------------------------------

	/**
	 * Unified handler for tool call start events.
	 * Updates both timeline (node execution) and activity feed.
	 */
	const handleToolCallStart = useCallback(
		(event: ToolCallStartEvent) => {
			streamingActivity.handleToolCallStart(event);
			timeline.handleToolCallStart(event);
		},
		[streamingActivity, timeline],
	);

	/**
	 * Unified handler for tool call complete events.
	 * Updates both timeline (marks completed) and activity feed.
	 */
	const handleToolCallComplete = useCallback(
		(event: ToolCallCompleteEvent) => {
			streamingActivity.handleToolCallComplete(event);
			timeline.handleToolCallComplete(event);
		},
		[streamingActivity, timeline],
	);

	/**
	 * Unified handler for tool call error events.
	 * Updates both timeline (marks failed) and activity feed.
	 */
	const handleToolCallError = useCallback(
		(event: ToolCallErrorEvent) => {
			streamingActivity.handleToolCallError(event);
			timeline.handleToolCallError(event);
		},
		[streamingActivity, timeline],
	);

	/**
	 * Handler for tool call progress events.
	 * Only affects activity feed - timeline doesn't track progress.
	 */
	const handleToolCallProgress = useCallback(
		(event: ToolCallProgressEvent) => {
			streamingActivity.handleToolCallProgress(event);
		},
		[streamingActivity],
	);

	/**
	 * Handler for sub-agent start events.
	 * Only affects activity feed - timeline gets sub-agent updates via handleNodeUpdate.
	 */
	const handleSubAgentStart = useCallback(
		(event: SubAgentStartEvent) => {
			streamingActivity.handleSubAgentStart(event);
		},
		[streamingActivity],
	);

	/**
	 * Handler for sub-agent complete events.
	 * Only affects activity feed.
	 */
	const handleSubAgentComplete = useCallback(
		(event: SubAgentCompleteEvent) => {
			streamingActivity.handleSubAgentComplete(event);
		},
		[streamingActivity],
	);

	/**
	 * Handler for content chunk events (subagent token streaming).
	 * Routes to handleTokenStream for consistent token accumulation.
	 * This handles streaming from subagents running in isolated contexts.
	 *
	 * The execution_order field is passed as step for iteration discrimination
	 * in review loops (ensures tokens go to correct iteration).
	 */
	const handleContentChunk = useCallback(
		(event: ContentChunkEvent) => {
			// Route content chunks to token stream handler
			// The node_id in content_chunk events is the subagent's node ID
			// execution_order is passed as step for iteration discrimination
			timeline.handleTokenStream({
				nodeId: event.node_id || null,
				step: event.execution_order,
				content: event.content,
			});
		},
		[timeline],
	);

	/**
	 * Handler for guardrail violation events.
	 * Routes to activity feed and severity-specific callbacks.
	 */
	const handleGuardrailViolation = useCallback(
		(event: GuardrailViolationEvent) => {
			streamingActivity.handleGuardrailViolation(event);

			// Only show block modal when enforcement_mode is "enforce" (or
			// unset for backward compat).  In "audit" mode, block-severity
			// violations are logged but not enforced — treat them as warnings.
			const isEnforced =
				!event.enforcement_mode || event.enforcement_mode === "enforce";

			if (event.severity === "block" && isEnforced) {
				onGuardrailBlock?.(event);
			} else if (
				event.severity === "warn" ||
				(event.severity === "block" && !isEnforced)
			) {
				onGuardrailWarn?.(event);
			}
		},
		[streamingActivity, onGuardrailBlock, onGuardrailWarn],
	);

	/**
	 * Combined clear function that resets both hooks.
	 */
	const clearState = useCallback(() => {
		timeline.clearState();
		streamingActivity.clearActivities();
	}, [timeline, streamingActivity]);

	// -------------------------------------------------------------------------
	// Bundle handlers for easy WebSocket integration
	// -------------------------------------------------------------------------

	const handlers = useMemo<ExecutionStreamingHandlers>(
		() => ({
			onNodeUpdate: timeline.handleNodeUpdate,
			onTokenStream: timeline.handleTokenStream,
			onToolCallStart: handleToolCallStart,
			onToolCallProgress: handleToolCallProgress,
			onToolCallComplete: handleToolCallComplete,
			onToolCallError: handleToolCallError,
			onSubAgentStart: handleSubAgentStart,
			onSubAgentComplete: handleSubAgentComplete,
			onContentChunk: handleContentChunk,
			onGuardrailViolation: handleGuardrailViolation,
		}),
		[
			timeline.handleNodeUpdate,
			timeline.handleTokenStream,
			handleToolCallStart,
			handleToolCallProgress,
			handleToolCallComplete,
			handleToolCallError,
			handleSubAgentStart,
			handleSubAgentComplete,
			handleContentChunk,
			handleGuardrailViolation,
		],
	);

	return {
		// Timeline state
		wsNodeExecutions: timeline.wsNodeExecutions,
		wsNodeExecutionsRef: timeline.wsNodeExecutionsRef,
		runningNodes: timeline.runningNodes,

		// Activity state
		activities: streamingActivity.activities,

		// Unified handlers
		handlers,

		// Utilities
		loadInitialData: timeline.loadInitialData,
		clearState,
		getNodeExecutions: timeline.getNodeExecutions,
		markAllNodesAsStopped: timeline.markAllNodesAsStopped,
	};
}
