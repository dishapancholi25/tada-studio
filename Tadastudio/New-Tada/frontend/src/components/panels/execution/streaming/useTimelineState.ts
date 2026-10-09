"use client";

import { useCallback, useRef, useState } from "react";
import type {
	ToolCallCompleteEvent,
	ToolCallErrorEvent,
	ToolCallStartEvent,
} from "@/hooks/useExecutionWebSocket";
import type { ExecutionStatusType, NodeExecution, NodeType } from "@/types/api";

// ============================================================================
// Types
// ============================================================================

/** Metadata passed with node update events */
export interface NodeUpdateMetadata {
	node_name?: string;
	node_type?: string;
	duration_seconds?: number;
	input_data?: any;
	start_time?: string;
	end_time?: string;
	input_tokens?: number;
	output_tokens?: number;
	total_tokens?: number;
	execution_id?: string;
	execution_order?: number;
	is_sub_agent?: boolean;
	parent_agent_id?: string;
	database_node_id?: string;
	step?: number; // LangGraph step for iteration discrimination
	error?: string; // Error message for failed nodes
}

/** Timeline entry stored in the Map (extends NodeExecution with runtime fields) */
export interface TimelineEntry {
	id: string;
	node_id: string;
	node_name: string;
	node_type: NodeType | string;
	status: ExecutionStatusType | string;
	execution_order?: number;
	start_time?: string | null;
	end_time?: string | null;
	duration_seconds?: number | null;
	input_data?: Record<string, any> | null;
	output_data?: Record<string, any> | null;
	error_message?: string | null;
	node_metadata?: Record<string, any> | null;
	is_sub_agent?: boolean;
	parent_agent_id?: string | null;
	parent_agent_name?: string | null;
	input_tokens?: number | null;
	output_tokens?: number | null;
	total_tokens?: number | null;
	token_metadata?: Record<string, any> | null;
	created_at?: string | null;
	timestamp?: string;
	step?: number;
	map_key?: string;
}

/** Execution data sent to parent component */
export interface ExecutionData {
	id: string | null;
	db_execution_id: string | null;
	status: string;
	node_executions: TimelineEntry[];
}

/** Options for the hook */
export interface UseTimelineStateOptions {
	/** Callback when execution data changes (for parent component) */
	onExecutionChange?: (executionData: ExecutionData) => void;
	/** WebSocket execution ID */
	executionId?: string | null;
	/** Database execution ID */
	dbExecutionId?: string | null;
	/** Whether execution is currently running */
	isExecuting?: boolean;
	/** Callback when a node starts running */
	onNodeRunning?: (nodeId: string) => void;
	/** Callback when a node stops running */
	onNodeStopped?: (nodeId: string | null) => void;
}

/** Return type of the hook */
export interface UseTimelineStateReturn {
	// State
	wsNodeExecutions: Map<string, TimelineEntry>;
	wsNodeExecutionsRef: React.MutableRefObject<Map<string, TimelineEntry>>;
	runningNodes: Set<string>;

	// Event handlers
	handleNodeUpdate: (
		nodeId: string,
		status: string,
		output?: any,
		metadata?: NodeUpdateMetadata,
	) => void;
	handleToolCallStart: (event: ToolCallStartEvent) => void;
	handleToolCallComplete: (event: ToolCallCompleteEvent) => void;
	handleToolCallError: (event: ToolCallErrorEvent) => void;
	handleTokenStream: (params: {
		nodeId?: string | null;
		step?: number;
		content: string;
	}) => void;
	loadInitialData: (nodes: NodeExecution[]) => void;

	// Utilities
	clearState: () => void;
	getNodeExecutions: () => TimelineEntry[];
	markAllNodesAsStopped: () => void;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useTimelineState(
	options: UseTimelineStateOptions = {},
): UseTimelineStateReturn {
	const {
		onExecutionChange,
		executionId,
		dbExecutionId,
		isExecuting = false,
		onNodeRunning,
		onNodeStopped,
	} = options;

	// Primary state - the Map of timeline entries
	const [wsNodeExecutions, setWsNodeExecutions] = useState<
		Map<string, TimelineEntry>
	>(new Map());
	const wsNodeExecutionsRef = useRef<Map<string, TimelineEntry>>(new Map());

	// Running nodes tracking
	const [runningNodes, setRunningNodes] = useState<Set<string>>(new Set());

	// Last running node for fallback token targeting
	const lastRunningNodeRef = useRef<string | null>(null);

	// Notify parent component of execution data changes
	const notifyExecutionChange = useCallback(
		(updated: Map<string, TimelineEntry>, hasRunningNodes: boolean) => {
			if (onExecutionChange) {
				const nodeExecutions = Array.from(updated.values());
				const executionStatus =
					hasRunningNodes || isExecuting ? "running" : "completed";

				onExecutionChange({
					id: executionId || null,
					db_execution_id: dbExecutionId || null,
					status: executionStatus,
					node_executions: nodeExecutions,
				});
			}
		},
		[onExecutionChange, executionId, dbExecutionId, isExecuting],
	);

	// -------------------------------------------------------------------------
	// handleNodeUpdate - Main handler for node_update WebSocket messages
	// -------------------------------------------------------------------------
	const handleNodeUpdate = useCallback(
		(
			nodeId: string,
			status: string,
			output?: any,
			metadata?: NodeUpdateMetadata,
		) => {
			// Track running nodes
			if (status === "running") {
				lastRunningNodeRef.current = nodeId;
				onNodeRunning?.(nodeId);
				setRunningNodes((prev) => {
					const next = new Set(prev);
					next.add(nodeId);
					return next;
				});
			} else if (status === "completed" || status === "failed") {
				onNodeStopped?.(null);
				setRunningNodes((prev) => {
					const next = new Set(prev);
					next.delete(nodeId);
					return next;
				});
			}

			setWsNodeExecutions((prev) => {
				const updated = new Map(prev);

				// Use database_node_id as primary key when available
				const mapKey =
					metadata?.database_node_id ||
					`${nodeId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

				// Check if we need to update an existing entry
				let existing: Partial<TimelineEntry> = {};
				let keyToUpdate: string | null = null;

				// Look for existing entry by database_node_id OR node_id with running status
				if (metadata?.database_node_id) {
					for (const [key, value] of updated.entries()) {
						if (
							value.id === metadata.database_node_id ||
							(value.node_id === nodeId && value.status === "running")
						) {
							existing = value;
							keyToUpdate = key;
							break;
						}
					}
				}

				// If still no match and this is a sub-agent, try matching by node_id + running status
				// Only match running entries to allow multiple executions of the same sub-agent
				if (!keyToUpdate && metadata?.is_sub_agent) {
					for (const [key, value] of updated.entries()) {
						if (value.node_id === nodeId && value.status === "running") {
							existing = value;
							keyToUpdate = key;
							break;
						}
					}
				}

				// Fallback: for terminal events without db_node_id, find running entry by node_id
				// This prevents phantom "In Progress" entries when error/complete events lack database_node_id
				if (!keyToUpdate && (status === "failed" || status === "completed")) {
					for (const [key, value] of updated.entries()) {
						if (value.node_id === nodeId && value.status === "running") {
							existing = value;
							keyToUpdate = key;
							break;
						}
					}
				}

				// If no existing entry found and this is "running", create a new entry
				if (!keyToUpdate && status === "running") {
					existing = {};
					keyToUpdate = mapKey;
				}

				const finalKey = keyToUpdate || mapKey;

				// For AGENT or REVIEW nodes starting execution, set isThinking flag
				const nodeType = metadata?.node_type || existing.node_type || "AGENT";
				const isNodeStarting =
					status === "running" &&
					(nodeType === "AGENT" || nodeType === "REVIEW") &&
					!existing.output_data?.raw;

				// Build output_data preserving accumulated streaming content
				let outputData = existing.output_data;
				if (isNodeStarting) {
					// Node starting: set thinking state
					outputData = { ...existing.output_data, isThinking: true, raw: "" };
				} else if (status === "failed") {
					// Node failed: clear thinking state, preserve any accumulated content
					outputData = {
						...existing.output_data,
						...output,
						isThinking: false,
					};
				} else if (output) {
					// For completed AGENT or REVIEW nodes, preserve accumulated streaming content
					if (
						status === "completed" &&
						existing.output_data?.raw &&
						(nodeType === "AGENT" || nodeType === "REVIEW")
					) {
						// Merge completion output but preserve accumulated raw content
						outputData = {
							...output,
							...existing.output_data,
							raw: existing.output_data.raw, // Preserve accumulated content
							isThinking: false,
						};
					} else {
						outputData = output;
					}
				}

				updated.set(finalKey, {
					...existing,
					id: metadata?.database_node_id || existing.id || mapKey,
					node_id: nodeId,
					node_name: metadata?.node_name || existing.node_name || nodeId,
					node_type: nodeType,
					status: status,
					input_data: metadata?.input_data || existing.input_data,
					output_data: outputData,
					timestamp: new Date().toISOString(),
					duration_seconds:
						metadata?.duration_seconds || existing.duration_seconds,
					start_time: metadata?.start_time || existing.start_time,
					end_time: metadata?.end_time || existing.end_time,
					is_sub_agent: metadata?.is_sub_agent || existing.is_sub_agent,
					parent_agent_id:
						metadata?.parent_agent_id || existing.parent_agent_id,
					input_tokens: metadata?.input_tokens || existing.input_tokens,
					output_tokens: metadata?.output_tokens || existing.output_tokens,
					total_tokens: metadata?.total_tokens || existing.total_tokens,
					execution_order:
						metadata?.execution_order || existing.execution_order,
					step: metadata?.step ?? existing.step,
					error_message: metadata?.error || existing.error_message,
					map_key: finalKey,
				});

				// Update ref to avoid stale closures
				wsNodeExecutionsRef.current = updated;

				// Notify parent of changes
				notifyExecutionChange(
					updated,
					runningNodes.size > 0 || status === "running",
				);

				return updated;
			});
		},
		[onNodeRunning, onNodeStopped, notifyExecutionChange, runningNodes.size],
	);

	// -------------------------------------------------------------------------
	// handleTokenStream - Accumulates streaming LLM tokens
	// -------------------------------------------------------------------------
	const handleTokenStream = useCallback(
		({
			nodeId,
			step,
			content,
		}: {
			nodeId?: string | null;
			step?: number;
			content: string;
		}) => {
			// Only use lastRunningNodeRef as fallback if that node is still actively
			// running. After a tool call completes the tool node is removed from
			// runningNodes, so we must not misroute agent tokens to it — doing so
			// creates a spurious "running" timeline entry that forces executionStatus
			// to "running" and hides the tool-usage badge on the canvas node.
			const lastRunningStillActive =
				lastRunningNodeRef.current !== null &&
				runningNodes.has(lastRunningNodeRef.current)
					? lastRunningNodeRef.current
					: null;

			const targetNodeId =
				nodeId ||
				lastRunningStillActive ||
				(runningNodes.size === 1 ? Array.from(runningNodes)[0] : null);

			if (!targetNodeId) {
				return;
			}

			setWsNodeExecutions((prev) => {
				const updated = new Map(prev);
				let matched = false;

				for (const [key, value] of updated.entries()) {
					if (value.node_id === targetNodeId) {
						// If step is provided, match by step for precise iteration targeting
						// Use != null to treat both null and undefined as "no step specified"
						if (step != null && value.step != null) {
							if (value.step !== step) {
								continue; // Skip entries from different iterations
							}
						} else if (step != null && value.step == null) {
							// Claim the entry: assign step if entry doesn't have one
							value.step = step;
						}

						matched = true;
						const newRaw = (value.output_data?.raw || "") + content;
						updated.set(key, {
							...value,
							step: value.step, // Ensure the claimed step is persisted
							status: value.status || "running",
							output_data: {
								...(value.output_data || {}),
								isThinking: false, // Clear thinking state on first token
								raw: newRaw,
							},
						});
						break;
					}
				}

				if (!matched) {
					// Create new entry with step for future matching
					const mapKey =
						step !== undefined
							? `${targetNodeId}_step_${step}`
							: `${targetNodeId}_stream_${Date.now()}`;

					updated.set(mapKey, {
						id: mapKey,
						node_id: targetNodeId,
						node_name: targetNodeId,
						node_type: "AGENT",
						status: "running",
						step: step,
						output_data: { raw: content },
						timestamp: new Date().toISOString(),
					});
				}

				wsNodeExecutionsRef.current = updated;
				return updated;
			});
		},
		[runningNodes],
	);

	// -------------------------------------------------------------------------
	// Tool call handlers
	// -------------------------------------------------------------------------
	const handleToolCallStart = useCallback(
		(event: ToolCallStartEvent) => {
			if (!event.tool_node_id) return;

			// Trigger visual update - same pattern as handleNodeUpdate for running nodes
			lastRunningNodeRef.current = event.tool_node_id;
			onNodeRunning?.(event.tool_node_id);
			setRunningNodes((prev) => {
				const next = new Set(prev);
				next.add(event.tool_node_id!);
				return next;
			});

			setWsNodeExecutions((prev) => {
				const updated = new Map(prev);

				// Use call_id as unique key - each tool invocation gets its own entry
				// This is critical because multiple calls to the same tool node should
				// NOT overwrite each other (e.g., 6 WEB_SEARCH calls from subagent)
				const mapKey = `tool_${event.call_id}`;

				updated.set(mapKey, {
					id: mapKey,
					node_id: event.tool_node_id!,
					node_name: event.tool_node_name || event.tool_name,
					node_type: event.tool_node_type || "TOOL",
					status: "running",
					input_data: event.tool_args,
					node_metadata: { synthetic_tool_name: event.tool_name },
					parent_agent_id: event.agent_id,
					step: event.invocation_index,
					timestamp: event.timestamp,
					map_key: mapKey,
				});

				wsNodeExecutionsRef.current = updated;

				// Notify parent of changes - tool is now running
				notifyExecutionChange(updated, true);

				return updated;
			});
		},
		[onNodeRunning, notifyExecutionChange],
	);

	const handleToolCallComplete = useCallback(
		(event: ToolCallCompleteEvent) => {
			if (!event.tool_node_id) return;

			// Clear running state - same pattern as handleNodeUpdate for completed nodes
			onNodeStopped?.(null);
			setRunningNodes((prev) => {
				const next = new Set(prev);
				next.delete(event.tool_node_id!);
				return next;
			});

			setWsNodeExecutions((prev) => {
				const updated = new Map(prev);

				// Use call_id to find the exact entry (matches handleToolCallStart)
				const mapKey = `tool_${event.call_id}`;
				const existing = updated.get(mapKey);

				if (existing) {
					// Build output_data: prefer full_result for execution panel, fall back to preview
					const outputData = event.full_result
						? { result: event.full_result }
						: event.result_preview
							? { raw: event.result_preview }
							: existing.output_data;

					// Update existing entry created by handleToolCallStart
					updated.set(mapKey, {
						...existing,
						status: "completed",
						duration_seconds: event.duration_ms / 1000,
						output_data: outputData,
						input_data: event.tool_input || existing.input_data,
						end_time: event.timestamp,
						parent_agent_id: existing.parent_agent_id || event.agent_id,
						step: existing.step ?? event.invocation_index,
					});
				} else if (event.tool_node_name) {
					// Build output_data for new entry
					const outputData = event.full_result
						? { result: event.full_result }
						: event.result_preview
							? { raw: event.result_preview }
							: undefined;

					// Create new entry if start event was missed
					updated.set(mapKey, {
						id: mapKey,
						node_id: event.tool_node_id!, // Non-null - checked at function start
						node_name: event.tool_node_name,
						node_type: event.tool_node_type || "TOOL",
						status: "completed",
						output_data: outputData,
						input_data: event.tool_input,
						node_metadata: { synthetic_tool_name: event.tool_name },
						timestamp: event.timestamp,
						duration_seconds: event.duration_ms / 1000,
						end_time: event.timestamp,
						parent_agent_id: event.agent_id,
						step: event.invocation_index,
						map_key: mapKey,
					});
				}

				wsNodeExecutionsRef.current = updated;

				// Notify parent of changes - check if other nodes are still running
				notifyExecutionChange(updated, runningNodes.size > 1);

				return updated;
			});
		},
		[onNodeStopped, notifyExecutionChange, runningNodes.size],
	);

	const handleToolCallError = useCallback(
		(event: ToolCallErrorEvent) => {
			if (!event.tool_node_id) return;

			// Clear running state - same pattern as handleNodeUpdate for failed nodes
			onNodeStopped?.(null);
			setRunningNodes((prev) => {
				const next = new Set(prev);
				next.delete(event.tool_node_id!);
				return next;
			});

			setWsNodeExecutions((prev) => {
				const updated = new Map(prev);

				// Use call_id to find the exact entry (matches handleToolCallStart)
				const mapKey = `tool_${event.call_id}`;
				const existing = updated.get(mapKey);

				if (existing) {
					updated.set(mapKey, {
						...existing,
						status: "failed",
						duration_seconds: event.duration_ms / 1000,
						error_message: event.error,
						end_time: event.timestamp,
					});
				} else if (event.tool_node_name) {
					// Create new entry if start event was missed
					updated.set(mapKey, {
						id: mapKey,
						node_id: event.tool_node_id!, // Non-null - checked at function start
						node_name: event.tool_node_name,
						node_type: event.tool_node_type || "TOOL",
						status: "failed",
						error_message: event.error,
						timestamp: event.timestamp,
						duration_seconds: event.duration_ms / 1000,
						end_time: event.timestamp,
						parent_agent_id: event.agent_id,
						step: event.invocation_index,
						map_key: mapKey,
					});
				}

				wsNodeExecutionsRef.current = updated;

				// Notify parent of changes - check if other nodes are still running
				notifyExecutionChange(updated, runningNodes.size > 1);

				return updated;
			});
		},
		[onNodeStopped, notifyExecutionChange, runningNodes.size],
	);

	// -------------------------------------------------------------------------
	// loadInitialData - Hydrates state from API when loading existing execution
	// -------------------------------------------------------------------------
	const loadInitialData = useCallback((nodes: NodeExecution[]) => {
		const newMap = new Map<string, TimelineEntry>();

		// Deduplicate checkpoint nodes only - keep all other nodes (including multiple sub-agent executions)
		const checkpointByNodeId = new Map<string, NodeExecution>();
		const nonCheckpointNodes: NodeExecution[] = [];

		nodes.forEach((node) => {
			if (node.node_type === "CHECKPOINT") {
				const existing = checkpointByNodeId.get(node.node_id);
				if (existing) {
					// Prefer completed over paused for checkpoints
					if (node.status === "completed" && existing.status === "paused") {
						checkpointByNodeId.set(node.node_id, node);
					}
					// If current is paused and existing is completed, keep existing (do nothing)
				} else {
					checkpointByNodeId.set(node.node_id, node);
				}
			} else {
				// Keep all non-checkpoint nodes (allows multiple sub-agent executions)
				nonCheckpointNodes.push(node);
			}
		});

		// Combine checkpoint nodes with all other nodes
		const allNodes = [
			...nonCheckpointNodes,
			...Array.from(checkpointByNodeId.values()),
		];

		// Build map from all nodes
		allNodes.forEach((node) => {
			const mapKey = node.id || `${node.node_id}_${Date.now()}`;
			newMap.set(mapKey, {
				id: node.id,
				node_id: node.node_id,
				node_name: node.node_name,
				node_type: node.node_type,
				status: node.status,
				execution_order: node.execution_order,
				start_time: node.start_time,
				end_time: node.end_time,
				duration_seconds: node.duration_seconds,
				input_data: node.input_data,
				output_data: node.output_data,
				error_message: node.error_message,
				is_sub_agent: node.is_sub_agent,
				parent_agent_id: node.parent_agent_id,
				input_tokens: node.input_tokens,
				output_tokens: node.output_tokens,
				total_tokens: node.total_tokens,
			});
		});

		setWsNodeExecutions(newMap);
		wsNodeExecutionsRef.current = newMap;
	}, []);

	// -------------------------------------------------------------------------
	// Utilities
	// -------------------------------------------------------------------------

	/**
	 * Mark all running nodes as stopped.
	 * Used when execution is hard stopped to immediately update the timeline UI.
	 */
	const markAllNodesAsStopped = useCallback(() => {
		const timestamp = new Date().toISOString();

		setWsNodeExecutions((prev) => {
			const updated = new Map(prev);
			let updatedCount = 0;
			for (const [key, value] of updated.entries()) {
				if (value.status === "running") {
					updated.set(key, {
						...value,
						status: "stopped",
						end_time: timestamp,
						error_message: "Execution hard stopped by user",
						// Clear thinking state to stop the "Thinking..." spinner
						output_data: value.output_data
							? { ...value.output_data, isThinking: false }
							: undefined,
					});
					updatedCount++;
				}
			}
			wsNodeExecutionsRef.current = updated;
			return updated;
		});

		// Clear running nodes set
		setRunningNodes(new Set());
		lastRunningNodeRef.current = null;

		// Notify callbacks
		onNodeStopped?.(null);
	}, [onNodeStopped]);

	const clearState = useCallback(() => {
		setWsNodeExecutions(new Map());
		wsNodeExecutionsRef.current = new Map();
		setRunningNodes(new Set());
		lastRunningNodeRef.current = null;
	}, []);

	const getNodeExecutions = useCallback(() => {
		return Array.from(wsNodeExecutionsRef.current.values());
	}, []);

	return {
		// State
		wsNodeExecutions,
		wsNodeExecutionsRef,
		runningNodes,

		// Event handlers
		handleNodeUpdate,
		handleToolCallStart,
		handleToolCallComplete,
		handleToolCallError,
		handleTokenStream,
		loadInitialData,

		// Utilities
		clearState,
		getNodeExecutions,
		markAllNodesAsStopped,
	};
}
