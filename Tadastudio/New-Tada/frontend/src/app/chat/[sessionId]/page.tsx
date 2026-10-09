"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Activity } from "lucide-react";

import ChatInput, { type ChatInputHandle } from "@/components/chat/ChatInput";
import ChatMessageList from "@/components/chat/ChatMessageList";
import ChatSidebar from "@/components/chat/ChatSidebar";
import WorkflowProgressPanel from "@/components/chat/WorkflowProgressPanel";
import GuardrailBlockModal from "@/components/core/GuardrailBlockModal";
import { useTimelineState } from "@/components/panels/execution/streaming/useTimelineState";
import { useExecutionWebSocket } from "@/hooks/useExecutionWebSocket";
import type { GuardrailViolationEvent } from "@/hooks/useExecutionWebSocket";
import { useStreamingChat } from "@/hooks/useStreamingChat";
import { api } from "@/lib/api";
import { chatAPI } from "@/lib/chat-api";
import type { ChatMessage, ChatSession } from "@/lib/chat-api";
import type { StreamingMessage, TextBlock } from "@/hooks/useStreamingChat";

export default function ChatSessionPage() {
	const params = useParams();
	const sessionId = params?.sessionId as string;
	const router = useRouter();
	const searchParams = useSearchParams();
	const wfParam = searchParams.get("wf");
	const wfParamRef = useRef(wfParam);
	const chatInputRef = useRef<ChatInputHandle>(null);

	const [session, setSession] = useState<ChatSession | null>(null);
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [loading, setLoading] = useState(true);
	const [executionId, setExecutionId] = useState<string | null>(null);
	const [isExecuting, setIsExecuting] = useState(false);
	const [showProgressPanel, setShowProgressPanel] = useState(false);
	const [completedStreamingMessage, setCompletedStreamingMessage] = useState<StreamingMessage | null>(null);
	const [guardrailBlockViolation, setGuardrailBlockViolation] = useState<GuardrailViolationEvent | null>(null);

	// Timeline state for execution tracking (feeds WorkflowProgressPanel)
	const timeline = useTimelineState({
		executionId,
		isExecuting,
	});

	// Streaming chat state (feeds ChatMessageList with real-time content)
	const streamingChat = useStreamingChat();

	// Load session and messages
	useEffect(() => {
		if (!sessionId) return;

		const fastPath = wfParamRef.current;
		wfParamRef.current = null;

		// Fast path: freshly created session — skip loading spinner
		if (fastPath && !session) {
			setSession({
				id: sessionId,
				title: "New Chat",
				workflow_id: fastPath,
				workflow_name: "",
				message_count: 0,
				last_message_at: null,
				created_at: new Date().toISOString(),
			});
			setMessages([]);
			setLoading(false);

			// Fetch full session in background for workflow_name
			chatAPI
				.getSession(sessionId)
				.then((sess) => setSession(sess))
				.catch((err) => console.error("Failed to load session details:", err));

			router.replace(`/chat/${sessionId}`, { scroll: false });
			return;
		}

		// Normal load (direct navigation, bookmark, refresh)
		const load = async () => {
			try {
				setLoading(true);
				const [sess, msgs] = await Promise.all([
					chatAPI.getSession(sessionId),
					chatAPI.getMessages(sessionId),
				]);
				setSession(sess);
				setMessages(msgs);
			} catch (err) {
				console.error("Failed to load chat:", err);
			} finally {
				setLoading(false);
			}
		};

		load();
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [sessionId]);

	// WebSocket connection for streaming execution progress
	useExecutionWebSocket(executionId, {
		enabled: !!executionId,
		onNodeUpdate: (nodeId, status, output, metadata) => {
			timeline.handleNodeUpdate(nodeId, status, output, metadata);
			streamingChat.handleNodeUpdate(nodeId, status, output, metadata);
		},
		onToolCallStart: (event) => {
			timeline.handleToolCallStart(event);
			streamingChat.handleToolCallStart(event);
		},
		onToolCallComplete: (event) => {
			timeline.handleToolCallComplete(event);
			streamingChat.handleToolCallComplete(event);
		},
		onToolCallError: (event) => {
			timeline.handleToolCallError(event);
			streamingChat.handleToolCallError(event);
		},
		onTokenStream: (info) => {
			timeline.handleTokenStream({
				nodeId: info.nodeId,
				step: info.step,
				content: info.content,
			});
			streamingChat.handleTokenStream(info);
		},
		onContentChunk: (event) => {
			streamingChat.handleContentChunk(event);
		},
		onSubAgentStart: (event) => {
			streamingChat.handleSubAgentStart(event);
		},
		onSubAgentComplete: (event) => {
			streamingChat.handleSubAgentComplete(event);
		},
		onGuardrailViolation: (event) => {
			streamingChat.handleGuardrailViolation(event);
			const isEnforced = !event.enforcement_mode || event.enforcement_mode === "enforce";
			if (event.severity === "block" && isEnforced) {
				setGuardrailBlockViolation(event);
			}
		},
		onExecutionComplete: async () => {
			const finalMsg = streamingChat.finalize();
			setCompletedStreamingMessage(finalMsg);
			setExecutionId(null);

			// Extract only the last agent section's text (mirrors getDisplayBlocks in StreamingAssistantMessage)
			const blocks = finalMsg.blocks;
			let lastDividerIdx = -1;
			for (let i = blocks.length - 1; i >= 0; i--) {
				if (blocks[i].type === "agent_divider") { lastDividerIdx = i; break; }
			}
			const sectionBlocks = lastDividerIdx >= 0 ? blocks.slice(lastDividerIdx + 1) : blocks;
			const assistantText = sectionBlocks
				.filter((b): b is TextBlock => b.type === "text")
				.map((b) => b.content)
				.join("");
			if (assistantText) {
				setMessages((prev) => [
					...prev,
					{ role: "assistant", content: assistantText, execution_id: null, created_at: new Date().toISOString() },
				]);
			}

			try {
				const msgs = await chatAPI.getMessages(sessionId);
				// Keep the clean streaming text for the last assistant message.
				// The DB may store the full node-output formatted content
				// (e.g. "**File read 1**\n...\n**Agent 2**\nresponse").
				setMessages(
					assistantText
						? msgs.map((m, i) =>
								i === msgs.length - 1 && m.role === "assistant"
									? { ...m, content: assistantText }
									: m,
						  )
						: msgs,
				);
			} catch (err) {
				console.error("Failed to refresh messages:", err);
			} finally {
				setIsExecuting(false);
			}
		},
		onExecutionError: () => {
			const finalMsg = streamingChat.finalize();
			setCompletedStreamingMessage(finalMsg);
			setIsExecuting(false);
			setExecutionId(null);
		},
		onStopped: () => {
			const finalMsg = streamingChat.finalize();
			setCompletedStreamingMessage(finalMsg);
			setIsExecuting(false);
			setExecutionId(null);
		},
	});

	// Auto-show progress panel when execution starts
	useEffect(() => {
		if (isExecuting) {
			setShowProgressPanel(true);
		}
	}, [isExecuting]);

	const handleStop = useCallback(async () => {
		if (executionId) {
			try {
				await api.stopExecution(executionId);
			} catch (err) {
				console.error("Failed to stop execution:", err);
			}
		}
	}, [executionId]);

	const handleSend = useCallback(
		async (message: string, files?: File[]) => {
			if (!sessionId || isExecuting) return;

			timeline.clearState();
			streamingChat.reset();
			setCompletedStreamingMessage(null);
			streamingChat.startStreaming();

			setMessages((prev) => [
				...prev,
				{ role: "user", content: message, execution_id: null, created_at: new Date().toISOString() },
			]);
			setIsExecuting(true);

			try {
				const response = files && files.length > 0
					? await chatAPI.sendMessageWithFile(sessionId, message, files)
					: await chatAPI.sendMessage(sessionId, message);
				setExecutionId(response.execution_id);
			} catch (err) {
				console.error("Failed to send message:", err);
				setIsExecuting(false);
				setMessages((prev) => [
					...prev,
					{ role: "assistant", content: `Error: ${err instanceof Error ? err.message : "Failed to send message"}`, execution_id: null, created_at: new Date().toISOString() },
				]);
			}
		},
		[sessionId, isExecuting, timeline, streamingChat],
	);

	const handleEndExecution = useCallback(async () => {
		setGuardrailBlockViolation(null);
		const currentId = executionId;
		if (currentId) { try { await api.stopExecution(currentId); } catch {} }
		const finalMsg = streamingChat.finalize();
		setCompletedStreamingMessage(finalMsg);
		setIsExecuting(false);
		setExecutionId(null);
	}, [executionId, streamingChat]);

	const handleCollapsePanel = useCallback(() => {
		setShowProgressPanel(false);
	}, []);

	const toggleProgressPanel = useCallback(() => {
		if (showProgressPanel) {
			handleCollapsePanel();
		} else {
			setShowProgressPanel(true);
		}
	}, [showProgressPanel, handleCollapsePanel]);

	if (loading) {
		return (
			<>
				<ChatSidebar activeSessionId={sessionId} initialWorkflowId={session?.workflow_id || wfParam || undefined} />
				<div className="flex flex-1 items-center justify-center">
					<p className="text-sm text-[color:var(--color-text-muted)]">Loading...</p>
				</div>
			</>
		);
	}

	return (
		<>
			<GuardrailBlockModal
				violation={guardrailBlockViolation}
				onEndExecution={handleEndExecution}
			/>
			<ChatSidebar activeSessionId={sessionId} initialWorkflowId={session?.workflow_id || wfParam || undefined} />
			<div className="flex min-h-0 flex-1 flex-col min-w-0">
				{/* Header */}
				<div className="flex h-[60px] shrink-0 min-w-0 items-center gap-3 border-b border-black/10 bg-[rgb(249,115,22)] px-5">
					<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] border border-white/30 bg-transparent">
						<svg width="14" height="14" viewBox="0 0 14 14">
							<polygon points="7,1 13,7 7,13 1,7" fill="none" stroke="rgba(255,255,255,0.9)" strokeWidth="1.2"/>
							<circle cx="7" cy="7" r="2" fill="rgba(255,255,255,0.7)"/>
						</svg>
					</div>
					<div className="min-w-0 flex-1 overflow-hidden">
						<h1 className="truncate text-[0.9rem] font-semibold text-white">
							{session?.title || "Chat"}
						</h1>
						<div className="mt-0.5 flex min-w-0 items-center gap-1.5">
							<span className={`h-1.5 w-1.5 shrink-0 rounded-full ${isExecuting ? "status-dot-executing" : "status-dot-ready"}`} />
							<p className="min-w-0 truncate text-[11px] text-white/85">
								{session?.workflow_name}
							</p>
						</div>
					</div>
					{/* Progress panel toggle */}
					<button
						type="button"
						onClick={toggleProgressPanel}
						className={`p-2 rounded-lg transition-all ${
							showProgressPanel
								? "border border-slate-300 bg-slate-100 text-slate-900"
								: "border border-transparent text-slate-800 hover:bg-slate-100"
						}`}
						title={showProgressPanel ? "Hide workflow progress" : "Show workflow progress"}
					>
						<Activity className="h-4 w-4" />
					</button>
				</div>

				{/* Messages */}
				<ChatMessageList
					messages={messages}
					streamingMessage={isExecuting ? streamingChat.streamingMessage : completedStreamingMessage}
					workflowId={session?.workflow_id}
					workflowName={session?.workflow_name}
					onSuggestionClick={(text) => chatInputRef.current?.setValue(text)}
				/>

				{/* Input — shrink-0 keeps the composer pinned inside the viewport */}
				<div className="shrink-0">
					<ChatInput
						ref={chatInputRef}
						onSend={handleSend}
						onStop={handleStop}
						disabled={loading}
						isExecuting={isExecuting}
					/>
				</div>
			</div>

			{/* Workflow Progress Panel */}
			{showProgressPanel && (
				<WorkflowProgressPanel
					workflowId={session?.workflow_id}
					wsNodeExecutions={timeline.wsNodeExecutions}
					runningNodes={timeline.runningNodes}
					isExecuting={isExecuting}
					isTrace={false}
					onCollapse={handleCollapsePanel}
				/>
			)}
		</>
	);
}
