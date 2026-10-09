import { useCallback, useEffect, useRef, useState } from "react";
import { ExecutionResult, ExecutionStatus } from "@/lib/api";
import { runtimeConfig } from "@/lib/runtime-config";
import { NodeExecution } from "@/types/api";

interface WebSocketMessage {
	type:
		| "node_update"
		| "execution_status"
		| "node_start"
		| "node_complete"
		| "execution_complete"
		| "reconnected"
		| "initial_status"
		| "token"
		| "ping"
		| "pong"
		| "custom"
		| "replay_complete" // Marker sent after buffered message replay on reconnect
		// Granular streaming event types
		| "tool_call_start"
		| "tool_call_progress"
		| "tool_call_complete"
		| "tool_call_error"
		| "subagent_start"
		| "subagent_complete"
		| "content_chunk"
		| "for_each_progress"
		| "guardrail_violation";
	execution_id: string;
	timestamp: string;
	data: {
		node_id?: string;
		nodeId?: string; // Alternative casing for token events
		node_name?: string;
		node_type?: string;
		status?: string;
		output?: any;
		error?: string;
		result?: any;
		duration_seconds?: number;
		is_sub_agent?: boolean;
		parent_agent_id?: string;
		input_data?: any;
		start_time?: string;
		end_time?: string;
		input_tokens?: number;
		output_tokens?: number;
		total_tokens?: number;
		database_node_id?: string;
		db_execution_id?: string;
		node_executions?: Record<string, any>;
		execution_order?: number;
		step?: number; // LangGraph step for iteration discrimination
		// Generic payload for streaming events
		payload?: any;
		metadata?: Record<string, any>;
		path?: string[]; // LangGraph path metadata for streaming modes
		// Tool call streaming fields
		call_id?: string;
		tool_name?: string;
		tool_args?: Record<string, any>;
		agent_id?: string;
		agent_name?: string;
		message?: string;
		progress?: number;
		result_preview?: string;
		full_result?: string;
		tool_input?: Record<string, any>;
		result_truncated?: boolean;
		duration_ms?: number;
		// Tool node info for timeline status updates
		tool_node_id?: string;
		tool_node_name?: string;
		tool_node_type?: string;
		// Review iteration for tool-to-iteration association
		review_iteration?: number;
		node_execution_id?: string;
		// Invocation index for multi-call subagent tracking
		invocation_index?: number;
		// Unique ID of parent subagent invocation for precise tool-to-subagent association
		parent_subagent_id?: string;
		// Sub-agent streaming fields
		subagent_id?: string;
		subagent_name?: string;
		task_description?: string;
		parent_agent_name?: string;
		success?: boolean;
		response_preview?: string;
		tools_used?: string[];
		iteration?: number; // Iteration number for distinguishing multiple subagent invocations
		subagent_node_type?: string; // Node type of subagent ("AGENT", "TOOL", etc.)
		// Timestamp from streaming events
		timestamp?: string;
		// Content chunk streaming fields (for subagent token streaming)
		content?: string;
		db_node_id?: string; // Database node execution ID for precise tracking
		// For Each progress fields
		completed?: number;
		failed?: number;
		total?: number;
		// Guardrail violation fields
		category?: string;
		rule_name?: string;
		severity?: string;
		violation_db_id?: string;
		policy_name?: string;
		details?: Record<string, unknown> | null;
		enforcement_mode?: string | null;
	};
}

// Exported types for streaming events
export interface ToolCallStartEvent {
	call_id: string;
	tool_name: string;
	tool_args: Record<string, any>;
	agent_id: string;
	agent_name: string;
	timestamp: string;
	// Tool node info for timeline status updates
	tool_node_id?: string;
	tool_node_name?: string;
	tool_node_type?: string;
	// Review and subagent tracking
	review_iteration?: number;
	node_execution_id?: string;
	invocation_index?: number;
	parent_subagent_id?: string;
}

export interface ToolCallProgressEvent {
	call_id: string;
	tool_name: string;
	message: string;
	progress?: number;
	metadata?: Record<string, any>;
	timestamp: string;
}

export interface ToolCallCompleteEvent {
	call_id: string;
	tool_name: string;
	result_preview?: string;
	full_result?: string;
	tool_input?: Record<string, any>;
	result_truncated?: boolean;
	duration_ms: number;
	timestamp: string;
	// Tool node info for timeline status updates
	tool_node_id?: string;
	tool_node_name?: string;
	tool_node_type?: string;
	// Review and subagent tracking
	review_iteration?: number;
	node_execution_id?: string;
	invocation_index?: number;
	agent_id?: string;
	agent_name?: string;
	parent_subagent_id?: string;
}

export interface ToolCallErrorEvent {
	call_id: string;
	tool_name: string;
	error: string;
	duration_ms: number;
	timestamp: string;
	// Tool node info for timeline status updates
	tool_node_id?: string;
	tool_node_name?: string;
	tool_node_type?: string;
	// Review and subagent tracking
	review_iteration?: number;
	node_execution_id?: string;
	invocation_index?: number;
	agent_id?: string;
	agent_name?: string;
	parent_subagent_id?: string;
}

export interface SubAgentStartEvent {
	subagent_id: string;
	subagent_name: string;
	task_description: string;
	parent_agent_id: string;
	parent_agent_name: string;
	timestamp: string;
	iteration?: number;
	subagent_node_type?: string;
}

export interface SubAgentCompleteEvent {
	subagent_id: string;
	subagent_name: string;
	success: boolean;
	response_preview?: string;
	duration_ms: number;
	tools_used: string[];
	timestamp: string;
	iteration?: number;
}

export interface ContentChunkEvent {
	content: string;
	agent_name: string;
	node_id?: string;
	execution_order?: number; // Iteration discrimination for review loops
	db_node_id?: string; // Database node execution ID for precise tracking
	timestamp: string;
}

export interface GuardrailViolationEvent {
	category: string;
	rule_name: string;
	message: string;
	severity: string;
	agent_id: string;
	agent_name: string;
	tool_name?: string;
	node_execution_id?: string;
	violation_db_id?: string;
	policy_name?: string;
	details?: Record<string, unknown> | null;
	enforcement_mode?: string | null;
	timestamp: string;
}

export interface ForEachProgressEvent {
	node_id: string;
	node_name: string;
	completed: number;
	failed: number;
	total: number;
	timestamp: string;
}

// Batched node update for performance optimization
export interface BatchedNodeUpdate {
	nodeId: string;
	status: string;
	output?: any;
	metadata?: {
		node_name?: string;
		node_type?: string;
		duration_seconds?: number;
		input_data?: any;
		start_time?: string;
		end_time?: string;
		input_tokens?: number;
		output_tokens?: number;
		total_tokens?: number;
		is_sub_agent?: boolean;
		parent_agent_id?: string;
		database_node_id?: string;
		execution_order?: number;
		step?: number;
		error?: string;
	};
}

interface UseExecutionWebSocketOptions {
	enabled?: boolean;
	onNodeUpdate?: (
		nodeId: string,
		status: string,
		output?: any,
		metadata?: {
			node_name?: string;
			node_type?: string;
			duration_seconds?: number;
			input_data?: any;
			start_time?: string;
			end_time?: string;
			input_tokens?: number;
			output_tokens?: number;
			total_tokens?: number;
			is_sub_agent?: boolean;
			parent_agent_id?: string;
			database_node_id?: string; // Database UUID for this node execution
			execution_order?: number; // Order for determining latest execution
			step?: number; // LangGraph step for iteration discrimination
			error?: string; // Error message for failed nodes
		},
	) => void;
	// Batched callback for performance - receives multiple updates at once
	onNodeUpdateBatch?: (updates: BatchedNodeUpdate[]) => void;
	onExecutionComplete?: (result: any) => void;
	onExecutionError?: (error: string) => void;
	onConnectionChange?: (connected: boolean) => void;
	onInitialStatus?: (dbExecutionId: string | null) => void;
	onPaused?: (info: {
		checkpoint_id?: string;
		thread_id?: string;
		node_id?: string;
		node_name?: string;
		prompt?: any;
		db_execution_id?: string | null;
		inbox_address?: string;
		manual?: boolean;
	}) => void;
	onResumed?: () => void; // Called when execution resumes from paused state
	onPausePending?: (info: {
		db_execution_id?: string | null;
		requested_at?: string;
	}) => void;
	onStopRequested?: (info: {
		db_execution_id?: string | null;
		requested_at?: string;
		status: string;
	}) => void;
	onStopped?: (info: {
		db_execution_id?: string | null;
		timestamp?: string;
		graph_name?: string;
	}) => void;
	onTokenStream?: (info: {
		nodeId?: string | null;
		step?: number; // LangGraph step for iteration discrimination
		content: string;
		rawChunk: any;
	}) => void;
	fallbackToPolling?: () => void;
	// Reconnection support for loading existing executions
	reconnectData?: {
		threadId: string;
		dbExecutionId: string;
	};
	// Granular streaming event callbacks
	onToolCallStart?: (event: ToolCallStartEvent) => void;
	onToolCallProgress?: (event: ToolCallProgressEvent) => void;
	onToolCallComplete?: (event: ToolCallCompleteEvent) => void;
	onToolCallError?: (event: ToolCallErrorEvent) => void;
	onSubAgentStart?: (event: SubAgentStartEvent) => void;
	onSubAgentComplete?: (event: SubAgentCompleteEvent) => void;
	onContentChunk?: (event: ContentChunkEvent) => void;
	onForEachProgress?: (event: ForEachProgressEvent) => void;
	onGuardrailViolation?: (event: GuardrailViolationEvent) => void;
	// Called on reconnection to clear stale timeline state before authoritative DB data arrives
	onReconnectionStateReset?: () => void;
}

export function useExecutionWebSocket(
	executionId: string | null,
	options: UseExecutionWebSocketOptions = {},
) {
	const {
		enabled = true,
		onNodeUpdate,
		onExecutionComplete,
		onExecutionError,
		onConnectionChange,
		fallbackToPolling,
	} = options;

	const [isConnected, setIsConnected] = useState(false);
	const [connectionError, setConnectionError] = useState<string | null>(null);
	const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

	const wsRef = useRef<WebSocket | null>(null);
	const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
	const reconnectAttemptsRef = useRef(0);
	const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
	// Track last received sequence number for replay on reconnection
	const lastSequenceRef = useRef(0);
	// Track last pong time for zombie connection detection
	const lastPongRef = useRef<number>(Date.now());
	const maxReconnectAttempts = 5;
	const baseReconnectDelay = 1000; // Start with 1 second
	const pingTimeoutMs = 300000; // 300 seconds without pong = zombie connection (increased for slow PTU responses)

	// PERFORMANCE: Batching for node updates to prevent re-render storms
	// Collects updates within a 16ms window (one animation frame) before flushing
	const pendingNodeUpdatesRef = useRef<BatchedNodeUpdate[]>([]);
	const flushScheduledRef = useRef<number | null>(null);

	// Flush pending node updates - called via requestAnimationFrame
	const flushNodeUpdates = useCallback(() => {
		flushScheduledRef.current = null;
		const updates = pendingNodeUpdatesRef.current;
		if (updates.length === 0) return;

		// Clear pending updates before processing to avoid race conditions
		pendingNodeUpdatesRef.current = [];

		// If batch callback is provided, use it (preferred for performance)
		if (options.onNodeUpdateBatch) {
			options.onNodeUpdateBatch(updates);
		} else if (onNodeUpdate) {
			// Fallback: call individual callback for each update
			updates.forEach((update) => {
				onNodeUpdate(update.nodeId, update.status, update.output, update.metadata);
			});
		}
	}, [onNodeUpdate, options.onNodeUpdateBatch]);

	// Queue a node update for batched processing
	const queueNodeUpdate = useCallback(
		(update: BatchedNodeUpdate) => {
			pendingNodeUpdatesRef.current.push(update);

			// Schedule flush if not already scheduled
			// Use setTimeout instead of requestAnimationFrame because rAF is
			// completely suspended in background tabs, causing updates to pile up
			if (flushScheduledRef.current === null) {
				flushScheduledRef.current = window.setTimeout(
					flushNodeUpdates,
					16,
				) as unknown as number;
			}
		},
		[flushNodeUpdates],
	);

	// Calculate reconnect delay with exponential backoff and jitter
	// Jitter prevents thundering herd when multiple clients reconnect simultaneously
	const getReconnectDelay = useCallback(() => {
		const attempt = reconnectAttemptsRef.current;
		const baseDelay = Math.min(baseReconnectDelay * 2 ** attempt, 30000); // Max 30 seconds
		// Add jitter: 50-100% of base delay to spread out reconnection attempts
		return baseDelay * (0.5 + Math.random() * 0.5);
	}, []);

	// Connect to WebSocket
	const connect = useCallback(async () => {
		if (
			!executionId ||
			!enabled ||
			wsRef.current?.readyState === WebSocket.OPEN
		) {
			return;
		}

		// Validate executionId to defend against SSRF/path attacks.
		// const executionIdPattern = /^[a-zA-Z0-9_-]{1,64}$/;
		// if (!executionIdPattern.test(executionId)) {
		// 	setConnectionError("Invalid execution ID");
		// 	console.error("[WebSocket] Invalid executionId value, aborting connection:", executionId);
		// 	return;
		// }

		try {
			// Clean up existing connection
			if (wsRef.current) {
				wsRef.current.close();
			}

			// Get runtime configuration to determine WebSocket URL
			const config = await runtimeConfig.getConfig();
			let wsUrl: string;

			if (config.deployment === "separate-domains" && config.apiUrl) {
				// For separate domains deployment (like Azure), use the backend URL directly
				const backendUrl = new URL(config.apiUrl);
				const protocol = backendUrl.protocol === "https:" ? "wss:" : "ws:";
				wsUrl = `${protocol}//${backendUrl.host}/api/ws/execution/${encodeURIComponent(executionId)}`;
			} else {
				// For reverse proxy deployment, use current host
				const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
				const host = window.location.host;
				wsUrl = `${protocol}//${host}/api/ws/execution/${encodeURIComponent(executionId)}`;
			}

			const ws = new WebSocket(wsUrl);
			wsRef.current = ws;

			ws.onopen = () => {
				setIsConnected(true);
				setConnectionError(null);
				reconnectAttemptsRef.current = 0;
				onConnectionChange?.(true);

				// If reconnection data is provided, send reconnect message with last sequence
				if (options.reconnectData) {
					const reconnectMsg = {
						type: "reconnect",
						thread_id: options.reconnectData.threadId,
						db_execution_id: options.reconnectData.dbExecutionId,
						last_seq: lastSequenceRef.current,
					};
					ws.send(JSON.stringify(reconnectMsg));
				}

				// Reset pong tracker when connection opens
				lastPongRef.current = Date.now();

				// Start heartbeat to keep connection alive during long workflows
				// Also detect zombie connections (appear OPEN but are actually dead)
				heartbeatIntervalRef.current = setInterval(() => {
					if (ws.readyState === WebSocket.OPEN) {
						// Check for zombie connection - no pong received in pingTimeoutMs
						const timeSinceLastPong = Date.now() - lastPongRef.current;
						if (timeSinceLastPong > pingTimeoutMs) {
							console.warn(
								`[WebSocket] Connection appears dead (no pong in ${Math.round(timeSinceLastPong / 1000)}s), forcing reconnect`,
							);
							ws.close(4000, "Ping timeout");
							return;
						}
						ws.send(JSON.stringify({ type: "ping" }));
					}
				}, 25000); // Every 25 seconds (under 30s backend timeout)
			};

			ws.onmessage = (event) => {
				try {
					const message: WebSocketMessage & { seq?: number } = JSON.parse(
						event.data,
					);

					// Track sequence numbers for replay on reconnection
					if (message.seq !== undefined) {
						lastSequenceRef.current = Math.max(
							lastSequenceRef.current,
							message.seq,
						);
					}

					// Respond to server ping to keep connection alive
					if (message.type === "ping") {
						ws.send(JSON.stringify({ type: "pong" }));
						return;
					}

					// Track pong responses for zombie connection detection
					if (message.type === "pong") {
						lastPongRef.current = Date.now();
						return;
					}
					setLastMessage(message);

					// Handle different message types
					switch (message.type) {
						case "reconnected":
							// Clear stale timeline state before authoritative DB data arrives
							options.onReconnectionStateReset?.();
							if (message.data.db_execution_id) {
								options.onInitialStatus?.(message.data.db_execution_id);
							}
							break;

						case "replay_complete":
							// Marker indicating buffered message replay is complete
							// Any subsequent messages are new real-time updates
							break;

						case "initial_status":
							// Extract and notify about the database execution ID
							if (message.data.db_execution_id) {
								options.onInitialStatus?.(message.data.db_execution_id);
							}

							// Process initial node executions with complete data
							// Using batched updates to prevent re-render storms with many nodes
							if (message.data.node_executions) {
								Object.entries(message.data.node_executions).forEach(
									([nodeId, nodeData]: [string, any]) => {
										const metadata = {
											node_name: nodeData.node_name,
											node_type: nodeData.node_type,
											duration_seconds: nodeData.duration_seconds,
											input_data: nodeData.input_data,
											start_time: nodeData.start_time,
											end_time: nodeData.end_time,
											input_tokens: nodeData.input_tokens,
											output_tokens: nodeData.output_tokens,
											total_tokens: nodeData.total_tokens,
											is_sub_agent: nodeData.is_sub_agent,
											parent_agent_id: nodeData.parent_agent_id,
											database_node_id: nodeData.id, // The actual database ID is in the 'id' field
										};

										queueNodeUpdate({
											nodeId,
											status: nodeData.status || "pending",
											output: nodeData.output_data,
											metadata,
										});
									},
								);
							}
							break;

						case "node_update":
						case "node_start":
						case "node_complete":
							if (message.data.node_id && message.data.status) {
								const metadata = {
									node_name: message.data.node_name,
									node_type: message.data.node_type,
									duration_seconds: message.data.duration_seconds,
									input_data: message.data.input_data,
									start_time: message.data.start_time,
									end_time: message.data.end_time,
									input_tokens: message.data.input_tokens,
									output_tokens: message.data.output_tokens,
									total_tokens: message.data.total_tokens,
									is_sub_agent: message.data.is_sub_agent,
									parent_agent_id: message.data.parent_agent_id,
									database_node_id: message.data.database_node_id,
									execution_order: message.data.execution_order,
									step: message.data.step,
									error: message.data.error,
								};

								// Queue update for batched processing (prevents re-render storms)
								queueNodeUpdate({
									nodeId: message.data.node_id,
									status: message.data.status,
									output: message.data.output,
									metadata,
								});
							} else {
								console.warn(
									"[WebSocket] Skipping node update - missing required fields:",
									{
										has_node_id: !!message.data.node_id,
										has_status: !!message.data.status,
									},
								);
							}
							break;

						case "token":
							{
								const payload = message.data?.payload ?? message.data;
								const content =
									typeof payload === "string"
										? payload
										: payload?.content ||
											payload?.text ||
											payload?.delta ||
											JSON.stringify(payload);

								// Try to derive node id from multiple hints
								const nodeId =
									message.data.nodeId || // camelCase from notifier
									message.data.node_id ||
									message.data?.metadata?.node_id ||
									message.data?.path?.[message.data?.path.length - 1] ||
									null;

								// Extract step for iteration discrimination
								const step = message.data.step;

								if (content) {
									options.onTokenStream?.({
										nodeId,
										step,
										content,
										rawChunk: payload,
									});
								}
							}
							break;

						case "custom":
							// Custom events are passed through to the caller for future use
							options.onTokenStream?.({
								nodeId: message.data.node_id || null,
								content:
									typeof message.data?.payload === "string"
										? message.data.payload
										: JSON.stringify(message.data?.payload ?? message.data),
								rawChunk: message.data,
							});
							break;

						case "execution_status":
							if (message.data.status === "completed") {
								onExecutionComplete?.(message.data.result);
							} else if (message.data.status === "failed") {
								onExecutionError?.(message.data.error || "Execution failed");
							} else if (message.data.status === "paused") {
								options.onPaused?.(message.data.result || {});
							} else if (message.data.status === "running") {
								options.onResumed?.();
							} else if (message.data.status === "pause_pending") {
								options.onPausePending?.({
									db_execution_id: message.data.result?.db_execution_id ?? null,
									requested_at: message.data.result?.requested_at,
								});
							} else if (
								message.data.status === "stop_requested" ||
								message.data.status === "stopping"
							) {
								options.onStopRequested?.({
									db_execution_id: message.data.result?.db_execution_id ?? null,
									requested_at: message.data.result?.requested_at,
									status: message.data.status,
								});
							} else if (message.data.status === "stopped") {
								options.onStopped?.({
									db_execution_id: message.data.result?.db_execution_id ?? null,
									timestamp: message.data.result?.timestamp,
									graph_name: message.data.result?.graph_name,
								});
							}
							break;

						case "execution_complete":
							onExecutionComplete?.(message.data.result);
							break;

						// Granular streaming event handlers
						case "tool_call_start":
							options.onToolCallStart?.({
								call_id: message.data.call_id || "",
								tool_name: message.data.tool_name || "",
								tool_args: message.data.tool_args || {},
								agent_id: message.data.agent_id || "",
								agent_name: message.data.agent_name || "",
								timestamp: message.data.timestamp || message.timestamp,
								tool_node_id: message.data.tool_node_id,
								tool_node_name: message.data.tool_node_name,
								tool_node_type: message.data.tool_node_type,
								review_iteration: message.data.review_iteration,
								node_execution_id: message.data.node_execution_id,
								invocation_index: message.data.invocation_index,
								parent_subagent_id: message.data.parent_subagent_id,
							});
							break;

						case "tool_call_progress":
							options.onToolCallProgress?.({
								call_id: message.data.call_id || "",
								tool_name: message.data.tool_name || "",
								message: message.data.message || "",
								progress: message.data.progress,
								metadata: message.data.metadata,
								timestamp: message.data.timestamp || message.timestamp,
							});
							break;

						case "tool_call_complete":
							options.onToolCallComplete?.({
								call_id: message.data.call_id || "",
								tool_name: message.data.tool_name || "",
								result_preview: message.data.result_preview,
								full_result: message.data.full_result,
								tool_input: message.data.tool_input,
								result_truncated: message.data.result_truncated,
								duration_ms: message.data.duration_ms || 0,
								timestamp: message.data.timestamp || message.timestamp,
								tool_node_id: message.data.tool_node_id,
								tool_node_name: message.data.tool_node_name,
								tool_node_type: message.data.tool_node_type,
								review_iteration: message.data.review_iteration,
								node_execution_id: message.data.node_execution_id,
								invocation_index: message.data.invocation_index,
								agent_id: message.data.agent_id,
								agent_name: message.data.agent_name,
								parent_subagent_id: message.data.parent_subagent_id,
							});
							break;

						case "tool_call_error":
							options.onToolCallError?.({
								call_id: message.data.call_id || "",
								tool_name: message.data.tool_name || "",
								error: message.data.error || "Unknown error",
								duration_ms: message.data.duration_ms || 0,
								timestamp: message.data.timestamp || message.timestamp,
								tool_node_id: message.data.tool_node_id,
								tool_node_name: message.data.tool_node_name,
								tool_node_type: message.data.tool_node_type,
								review_iteration: message.data.review_iteration,
								node_execution_id: message.data.node_execution_id,
								invocation_index: message.data.invocation_index,
								agent_id: message.data.agent_id,
								agent_name: message.data.agent_name,
								parent_subagent_id: message.data.parent_subagent_id,
							});
							break;

						case "subagent_start":
							options.onSubAgentStart?.({
								subagent_id: message.data.subagent_id || "",
								subagent_name: message.data.subagent_name || "",
								task_description: message.data.task_description || "",
								parent_agent_id: message.data.parent_agent_id || "",
								parent_agent_name: message.data.parent_agent_name || "",
								timestamp: message.data.timestamp || message.timestamp,
								iteration: message.data.iteration,
								subagent_node_type: message.data.subagent_node_type,
							});
							break;

						case "subagent_complete":
							options.onSubAgentComplete?.({
								subagent_id: message.data.subagent_id || "",
								subagent_name: message.data.subagent_name || "",
								success: message.data.success ?? true,
								response_preview: message.data.response_preview,
								duration_ms: message.data.duration_ms || 0,
								tools_used: message.data.tools_used || [],
								timestamp: message.data.timestamp || message.timestamp,
								iteration: message.data.iteration,
							});
							break;

						case "content_chunk":
							options.onContentChunk?.({
								content: message.data.content || "",
								agent_name: message.data.agent_name || "",
								node_id: message.data.node_id,
								execution_order: message.data.execution_order,
								db_node_id: message.data.db_node_id,
								timestamp: message.data.timestamp || message.timestamp,
							});
							break;

						case "for_each_progress":
							options.onForEachProgress?.({
								node_id: message.data.node_id || "",
								node_name: message.data.node_name || "",
								completed: message.data.completed || 0,
								failed: message.data.failed || 0,
								total: message.data.total || 0,
								timestamp: message.data.timestamp || message.timestamp,
							});
							break;

						case "guardrail_violation":
							options.onGuardrailViolation?.({
								category: message.data.category || "",
								rule_name: message.data.rule_name || "",
								message: message.data.message || "",
								severity: message.data.severity || "block",
								agent_id: message.data.agent_id || "",
								agent_name: message.data.agent_name || "",
								tool_name: message.data.tool_name,
								node_execution_id: message.data.node_execution_id,
								violation_db_id: message.data.violation_db_id,
								policy_name: message.data.policy_name,
								details: message.data.details,
								enforcement_mode: message.data.enforcement_mode,
								timestamp:
									message.data.timestamp || message.timestamp,
							});
							break;
					}
				} catch (error) {
					console.error("[WebSocket] Error parsing message:", error);
				}
			};

			ws.onerror = (error) => {
				console.error("[WebSocket] Error:", error);
				setConnectionError("WebSocket connection error");
			};

			ws.onclose = (event) => {
				setIsConnected(false);
				onConnectionChange?.(false);
				wsRef.current = null;

				// Clear heartbeat interval
				if (heartbeatIntervalRef.current) {
					clearInterval(heartbeatIntervalRef.current);
					heartbeatIntervalRef.current = null;
				}

				// Attempt reconnection if not manually closed
				if (
					event.code !== 1000 &&
					reconnectAttemptsRef.current < maxReconnectAttempts &&
					enabled
				) {
					const delay = getReconnectDelay();
					reconnectTimeoutRef.current = setTimeout(() => {
						reconnectAttemptsRef.current++;
						connect();
					}, delay);
				} else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
					setConnectionError("Unable to establish WebSocket connection");
					fallbackToPolling?.();
				}
			};
		} catch (error) {
			console.error("[WebSocket] Failed to create connection:", error);
			setConnectionError("Failed to create WebSocket connection");
			fallbackToPolling?.();
		}
	}, [
		executionId,
		enabled,
		queueNodeUpdate,
		onExecutionComplete,
		onExecutionError,
		onConnectionChange,
		fallbackToPolling,
		getReconnectDelay,
	]);

	// Disconnect WebSocket
	const disconnect = useCallback(() => {
		if (reconnectTimeoutRef.current) {
			clearTimeout(reconnectTimeoutRef.current);
			reconnectTimeoutRef.current = null;
		}

		// Clear heartbeat interval
		if (heartbeatIntervalRef.current) {
			clearInterval(heartbeatIntervalRef.current);
			heartbeatIntervalRef.current = null;
		}

		// Clear any pending batched updates and flush timeout
		if (flushScheduledRef.current !== null) {
			clearTimeout(flushScheduledRef.current);
			flushScheduledRef.current = null;
		}
		// Flush any remaining updates before disconnecting
		if (pendingNodeUpdatesRef.current.length > 0) {
			flushNodeUpdates();
		}

		if (wsRef.current) {
			wsRef.current.close(1000, "Client disconnect");
			wsRef.current = null;
		}

		setIsConnected(false);
		setConnectionError(null);
		reconnectAttemptsRef.current = 0;
	}, [flushNodeUpdates]);

	// Send message through WebSocket
	const sendMessage = useCallback((message: any) => {
		if (wsRef.current?.readyState === WebSocket.OPEN) {
			wsRef.current.send(JSON.stringify(message));
			return true;
		}
		return false;
	}, []);

	// Effect to manage connection lifecycle
	useEffect(() => {
		if (executionId && enabled) {
			// Reset sequence tracking for new execution
			lastSequenceRef.current = 0;
			connect();
		}

		return () => {
			disconnect();
		};
	}, [executionId, enabled]); // Only reconnect if executionId or enabled changes

	// Handle tab visibility changes to prevent zombie connections
	// Browsers throttle background tab timers, causing heartbeat pings to be delayed
	// past the server's receive timeout, killing the WebSocket connection silently.
	useEffect(() => {
		const handleVisibilityChange = () => {
			if (document.hidden) {
				// Tab hidden: pause heartbeat to prevent server timeout from delayed pings
				if (heartbeatIntervalRef.current) {
					clearInterval(heartbeatIntervalRef.current);
					heartbeatIntervalRef.current = null;
				}
			} else {
				// Tab visible: check connection health immediately
				const ws = wsRef.current;
				if (ws?.readyState === WebSocket.OPEN) {
					// Send immediate ping to verify connection is alive
					try {
						ws.send(JSON.stringify({ type: "ping" }));
					} catch {
						// Connection dead, trigger reconnect
						ws.close(4001, "Tab resume - connection dead");
						return;
					}
					// Reset pong tracker and restart heartbeat
					lastPongRef.current = Date.now();
					if (heartbeatIntervalRef.current) {
						clearInterval(heartbeatIntervalRef.current);
					}
					heartbeatIntervalRef.current = setInterval(() => {
						if (wsRef.current?.readyState === WebSocket.OPEN) {
							const timeSinceLastPong =
								Date.now() - lastPongRef.current;
							if (timeSinceLastPong > pingTimeoutMs) {
								wsRef.current?.close(4000, "Ping timeout");
								return;
							}
							wsRef.current?.send(
								JSON.stringify({ type: "ping" }),
							);
						}
					}, 25000);
				} else if (
					!ws ||
					ws.readyState === WebSocket.CLOSED ||
					ws.readyState === WebSocket.CLOSING
				) {
					// Connection already dead, reconnect immediately
					reconnectAttemptsRef.current = 0;
					connect();
				}
			}
		};

		document.addEventListener("visibilitychange", handleVisibilityChange);
		return () => {
			document.removeEventListener(
				"visibilitychange",
				handleVisibilityChange,
			);
		};
	}, [connect]);

	// Manual reconnect function
	const reconnect = useCallback(() => {
		reconnectAttemptsRef.current = 0;
		disconnect();
		setTimeout(connect, 100);
	}, [connect, disconnect]);

	return {
		isConnected,
		connectionError,
		lastMessage,
		sendMessage,
		reconnect,
		disconnect,
	};
}
