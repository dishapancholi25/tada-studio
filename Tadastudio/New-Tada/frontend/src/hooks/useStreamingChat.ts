"use client";

import { useCallback, useRef, useState } from "react";
import type {
	ContentChunkEvent,
	GuardrailViolationEvent,
	SubAgentCompleteEvent,
	SubAgentStartEvent,
	ToolCallCompleteEvent,
	ToolCallErrorEvent,
	ToolCallStartEvent,
} from "@/hooks/useExecutionWebSocket";

// ============================================================================
// Block Types
// ============================================================================

/** A text block accumulating streamed LLM tokens */
export interface TextBlock {
	type: "text";
	content: string;
	isStreaming: boolean;
}

/** An inline tool call card */
export interface ToolCallBlock {
	type: "tool_call";
	callId: string;
	toolName: string;
	toolArgs?: Record<string, any>;
	status: "running" | "complete" | "error";
	resultPreview?: string;
	error?: string;
	durationMs?: number;
	agentName?: string;
	toolNodeType?: string;
	toolNodeName?: string;
}

/** A sub-agent delegation card */
export interface SubAgentBlock {
	type: "subagent";
	subagentId: string;
	subagentName: string;
	taskDescription?: string;
	parentAgentName?: string;
	status: "running" | "complete" | "error";
	durationMs?: number;
	toolsUsed?: string[];
	nestedToolCalls: ToolCallBlock[];
}

/** Thinking indicator before first token */
export interface ThinkingBlock {
	type: "thinking";
	agentName?: string;
}

/** Guardrail violation inline warning */
export interface GuardrailBlock {
	type: "guardrail";
	category: string;
	ruleName: string;
	message: string;
	severity: string;
	agentName?: string;
}

/** Agent section divider — marks the start of an agent's output section */
export interface AgentDividerBlock {
	type: "agent_divider";
	agentNodeId: string;
	agentName: string;
	status: "running" | "complete" | "error";
	startedAt: number;
}

export type StreamingBlock =
	| TextBlock
	| ToolCallBlock
	| SubAgentBlock
	| ThinkingBlock
	| GuardrailBlock
	| AgentDividerBlock;

/** The streaming message being built during execution */
export interface StreamingMessage {
	blocks: StreamingBlock[];
	isComplete: boolean;
}

// ============================================================================
// Hook
// ============================================================================

export function useStreamingChat() {
	const [streamingMessage, setStreamingMessage] =
		useState<StreamingMessage | null>(null);

	// Mutable ref for synchronous access in rapid WebSocket callbacks.
	// setState is batched via requestAnimationFrame to limit re-renders.
	const blocksRef = useRef<StreamingBlock[]>([]);
	const rafRef = useRef<number | null>(null);
	const isCompleteRef = useRef(false);

	// Track the currently active agent for multi-agent section grouping
	const currentAgentRef = useRef<{ nodeId: string; name: string } | null>(null);
	// Map nodeId → display name (populated from node_update and other events)
	const agentNameMapRef = useRef<Record<string, string>>({});

	/** Schedule a batched state update */
	const scheduleUpdate = useCallback(() => {
		if (rafRef.current !== null) return;
		rafRef.current = requestAnimationFrame(() => {
			rafRef.current = null;
			setStreamingMessage({
				blocks: [...blocksRef.current],
				isComplete: isCompleteRef.current,
			});
		});
	}, []);

	/** Force an immediate state update (for important transitions) */
	const flushUpdate = useCallback(() => {
		if (rafRef.current !== null) {
			cancelAnimationFrame(rafRef.current);
			rafRef.current = null;
		}
		setStreamingMessage({
			blocks: [...blocksRef.current],
			isComplete: isCompleteRef.current,
		});
	}, []);

	// ---------- Helpers ----------

	/** Get the last block or null */
	const lastBlock = (): StreamingBlock | null => {
		const blocks = blocksRef.current;
		return blocks.length > 0 ? blocks[blocks.length - 1] : null;
	};

	/** Replace the ThinkingBlock (if it's the last block) when real content arrives */
	const removeTrailingThinking = () => {
		const blocks = blocksRef.current;
		if (blocks.length > 0 && blocks[blocks.length - 1].type === "thinking") {
			blocks.pop();
		}
	};

	/** Close the current streaming TextBlock so a new block can follow */
	const closeCurrentTextBlock = () => {
		const last = lastBlock();
		if (last?.type === "text" && last.isStreaming) {
			last.isStreaming = false;
		}
	};

	/** Ensure there is an active streaming TextBlock to write into */
	const ensureTextBlock = (): TextBlock => {
		const last = lastBlock();
		if (last?.type === "text" && last.isStreaming) {
			return last;
		}
		// Create a new text block
		const textBlock: TextBlock = { type: "text", content: "", isStreaming: true };
		blocksRef.current.push(textBlock);
		return textBlock;
	};

	/** Find a ToolCallBlock by callId across all blocks (including nested in subagents) */
	const findToolCallBlock = (
		callId: string,
	): ToolCallBlock | null => {
		for (const block of blocksRef.current) {
			if (block.type === "tool_call" && block.callId === callId) {
				return block;
			}
			if (block.type === "subagent") {
				const nested = block.nestedToolCalls.find((tc) => tc.callId === callId);
				if (nested) return nested;
			}
		}
		return null;
	};

	/** Find a SubAgentBlock by subagentId */
	const findSubAgentBlock = (
		subagentId: string,
	): SubAgentBlock | null => {
		for (const block of blocksRef.current) {
			if (block.type === "subagent" && block.subagentId === subagentId) {
				return block;
			}
		}
		return null;
	};

	/** Find an AgentDividerBlock by nodeId */
	const findAgentDividerBlock = (
		nodeId: string,
	): AgentDividerBlock | null => {
		for (const block of blocksRef.current) {
			if (block.type === "agent_divider" && block.agentNodeId === nodeId) {
				return block;
			}
		}
		return null;
	};

	/** Fallback agent detection — inserts a divider if the active agent changed */
	const maybeInsertAgentDivider = (
		agentNodeId: string | null | undefined,
		agentName: string | null | undefined,
	) => {
		if (!agentName || !agentNodeId) return;

		agentNameMapRef.current[agentNodeId] = agentName;

		// Same agent — no transition
		if (currentAgentRef.current?.nodeId === agentNodeId) return;

		// Mark previous agent as complete
		if (currentAgentRef.current) {
			const prevDivider = findAgentDividerBlock(currentAgentRef.current.nodeId);
			if (prevDivider && prevDivider.status === "running") {
				prevDivider.status = "complete";
			}
		}

		// Insert divider if not already present
		if (!findAgentDividerBlock(agentNodeId)) {
			closeCurrentTextBlock();
			blocksRef.current.push({
				type: "agent_divider",
				agentNodeId,
				agentName,
				status: "running",
				startedAt: Date.now(),
			});
		}

		currentAgentRef.current = { nodeId: agentNodeId, name: agentName };
	};

	// ---------- Public Handlers ----------

	const startStreaming = useCallback(() => {
		blocksRef.current = [{ type: "thinking" }];
		isCompleteRef.current = false;
		flushUpdate();
	}, [flushUpdate]);

	const handleTokenStream = useCallback(
		(info: { nodeId?: string | null; step?: number; content: string }) => {
			// Fallback agent detection from nodeId (if name was previously registered)
			if (info.nodeId && agentNameMapRef.current[info.nodeId]) {
				maybeInsertAgentDivider(info.nodeId, agentNameMapRef.current[info.nodeId]);
			}
			removeTrailingThinking();
			const textBlock = ensureTextBlock();
			textBlock.content += info.content;
			scheduleUpdate();
		},
		[scheduleUpdate],
	);

	const handleContentChunk = useCallback(
		(event: ContentChunkEvent) => {
			maybeInsertAgentDivider(event.node_id, event.agent_name);
			removeTrailingThinking();
			const textBlock = ensureTextBlock();
			textBlock.content += event.content;
			scheduleUpdate();
		},
		[scheduleUpdate],
	);

	const handleToolCallStart = useCallback(
		(event: ToolCallStartEvent) => {
			maybeInsertAgentDivider(event.agent_id, event.agent_name);

			// Skip delegation tools — subagent_start handles these
			if (
				event.tool_name?.startsWith("delegate_to_") ||
				event.tool_node_type === "AGENT"
			) {
				return;
			}

			const toolBlock: ToolCallBlock = {
				type: "tool_call",
				callId: event.call_id,
				toolName: event.tool_name,
				status: "running",
				toolArgs: event.tool_args,
				agentName: event.agent_name,
				toolNodeType: event.tool_node_type,
				toolNodeName: event.tool_node_name,
			};

			// If this tool call belongs to a sub-agent, nest it
			if (event.parent_subagent_id) {
				const parentSubAgent = findSubAgentBlock(event.parent_subagent_id);
				if (parentSubAgent) {
					parentSubAgent.nestedToolCalls.push(toolBlock);
					scheduleUpdate();
					return;
				}
			}

			// Top-level tool call: close current text and insert
			removeTrailingThinking();
			closeCurrentTextBlock();
			blocksRef.current.push(toolBlock);
			flushUpdate();
		},
		[scheduleUpdate, flushUpdate],
	);

	const handleToolCallComplete = useCallback(
		(event: ToolCallCompleteEvent) => {
			const block = findToolCallBlock(event.call_id);
			if (block) {
				block.status = "complete";
				block.resultPreview = event.result_preview;
				block.durationMs = event.duration_ms;
			}
			scheduleUpdate();
		},
		[scheduleUpdate],
	);

	const handleToolCallError = useCallback(
		(event: ToolCallErrorEvent) => {
			const block = findToolCallBlock(event.call_id);
			if (block) {
				block.status = "error";
				block.error = event.error;
				block.durationMs = event.duration_ms;
			}
			scheduleUpdate();
		},
		[scheduleUpdate],
	);

	const handleSubAgentStart = useCallback(
		(event: SubAgentStartEvent) => {
			removeTrailingThinking();
			closeCurrentTextBlock();

			const subAgentBlock: SubAgentBlock = {
				type: "subagent",
				subagentId: event.subagent_id,
				subagentName: event.subagent_name,
				taskDescription: event.task_description,
				parentAgentName: event.parent_agent_name,
				status: "running",
				nestedToolCalls: [],
			};

			blocksRef.current.push(subAgentBlock);
			flushUpdate();
		},
		[flushUpdate],
	);

	const handleSubAgentComplete = useCallback(
		(event: SubAgentCompleteEvent) => {
			const block = findSubAgentBlock(event.subagent_id);
			if (block) {
				block.status = event.success ? "complete" : "error";
				block.durationMs = event.duration_ms;
				block.toolsUsed = event.tools_used;
			}
			scheduleUpdate();
		},
		[scheduleUpdate],
	);

	const handleGuardrailViolation = useCallback(
		(event: GuardrailViolationEvent) => {
			removeTrailingThinking();
			closeCurrentTextBlock();

			blocksRef.current.push({
				type: "guardrail",
				category: event.category,
				ruleName: event.rule_name,
				message: event.message,
				severity: event.severity,
				agentName: event.agent_name,
			});
			flushUpdate();
		},
		[flushUpdate],
	);

	const handleNodeUpdate = useCallback(
		(
			nodeId: string,
			status: string,
			_output?: any,
			metadata?: {
				node_name?: string;
				node_type?: string;
				is_sub_agent?: boolean;
				[key: string]: any;
			},
		) => {
			// Only process AGENT type nodes for section dividers
			if (metadata?.node_type !== "AGENT") return;

			const agentName = metadata.node_name || nodeId;
			agentNameMapRef.current[nodeId] = agentName;

			if (status === "running") {
				// Mark previous agent's divider complete if different agent
				if (currentAgentRef.current && currentAgentRef.current.nodeId !== nodeId) {
					const prevDivider = findAgentDividerBlock(currentAgentRef.current.nodeId);
					if (prevDivider && prevDivider.status === "running") {
						prevDivider.status = "complete";
					}
				}

				// Insert divider + thinking if not already present
				if (!findAgentDividerBlock(nodeId)) {
					removeTrailingThinking();
					closeCurrentTextBlock();
					blocksRef.current.push({
						type: "agent_divider",
						agentNodeId: nodeId,
						agentName,
						status: "running",
						startedAt: Date.now(),
					});
					blocksRef.current.push({ type: "thinking", agentName });
				}

				currentAgentRef.current = { nodeId, name: agentName };
				flushUpdate();
			} else if (status === "completed" || status === "complete") {
				const divider = findAgentDividerBlock(nodeId);
				if (divider) {
					divider.status = "complete";
				}
				if (currentAgentRef.current?.nodeId === nodeId) {
					currentAgentRef.current = null;
				}
				scheduleUpdate();
			} else if (status === "failed" || status === "error") {
				const divider = findAgentDividerBlock(nodeId);
				if (divider) {
					divider.status = "error";
				}
				if (currentAgentRef.current?.nodeId === nodeId) {
					currentAgentRef.current = null;
				}
				scheduleUpdate();
			}
		},
		[flushUpdate, scheduleUpdate],
	);

	const finalize = useCallback((): StreamingMessage => {
		removeTrailingThinking();
		closeCurrentTextBlock();

		// Mark last running agent divider as complete
		for (let i = blocksRef.current.length - 1; i >= 0; i--) {
			const block = blocksRef.current[i];
			if (block.type === "agent_divider" && block.status === "running") {
				block.status = "complete";
				break;
			}
		}

		isCompleteRef.current = true;
		// Return the finalized message directly from refs to avoid React state batching issues
		const finalMsg: StreamingMessage = { blocks: [...blocksRef.current], isComplete: true };
		setStreamingMessage(finalMsg);
		return finalMsg;
	}, []);

	const reset = useCallback(() => {
		blocksRef.current = [];
		isCompleteRef.current = false;
		currentAgentRef.current = null;
		agentNameMapRef.current = {};
		if (rafRef.current !== null) {
			cancelAnimationFrame(rafRef.current);
			rafRef.current = null;
		}
		setStreamingMessage(null);
	}, []);

	return {
		streamingMessage,
		startStreaming,
		handleTokenStream,
		handleContentChunk,
		handleToolCallStart,
		handleToolCallComplete,
		handleToolCallError,
		handleSubAgentStart,
		handleSubAgentComplete,
		handleGuardrailViolation,
		handleNodeUpdate,
		finalize,
		reset,
	};
}
