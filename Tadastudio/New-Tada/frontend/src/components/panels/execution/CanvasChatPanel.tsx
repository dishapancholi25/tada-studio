"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Globe } from "lucide-react";
import ChatInput, { type ChatInputHandle } from "@/components/chat/ChatInput";
import ChatMessageList from "@/components/chat/ChatMessageList";
import { useStreamingChat, type TextBlock } from "@/hooks/useStreamingChat";
import { useExecutionWebSocket } from "@/hooks/useExecutionWebSocket";
import type { GuardrailViolationEvent } from "@/hooks/useExecutionWebSocket";
import GuardrailBlockModal from "@/components/core/GuardrailBlockModal";
import { api } from "@/lib/api";
import { chatAPI } from "@/lib/chat-api";
import { useCanvasChatStore } from "@/stores/canvasChatStore";

interface CanvasChatPanelProps {
	workflowId: string;
	graphName: string;
}

export default function CanvasChatPanel({ workflowId, graphName }: CanvasChatPanelProps) {
	// History lives in the Zustand store keyed by workflowId — survives
	// the execution panel being opened/closed while the canvas is mounted.
	const { getChat, addMessage, setSessionId } = useCanvasChatStore();
	const { messages, sessionId } = getChat(workflowId);

	const chatInputRef = useRef<ChatInputHandle>(null);
	const [executionId, setExecutionId] = useState<string | null>(null);
	const [isExecuting, setIsExecuting] = useState(false);
	const [isPublished, setIsPublished] = useState<boolean | null>(null);
	const [guardrailBlockViolation, setGuardrailBlockViolation] = useState<GuardrailViolationEvent | null>(null);

	const streamingChat = useStreamingChat();

	useEffect(() => {
		let cancelled = false;
		api.getWorkflowPublicationStatus(graphName)
			.then((r) => { if (!cancelled) setIsPublished(r?.is_published === true); })
			.catch(() => { if (!cancelled) setIsPublished(false); });
		return () => { cancelled = true; };
	}, [graphName]);

	const handleStop = useCallback(async () => {
		if (executionId) { try { await api.stopExecution(executionId); } catch {} }
	}, [executionId]);

	useExecutionWebSocket(executionId, {
		enabled: !!executionId,
		onNodeUpdate: (n, s, o, m) => streamingChat.handleNodeUpdate(n, s, o, m),
		onToolCallStart: (e) => streamingChat.handleToolCallStart(e),
		onToolCallComplete: (e) => streamingChat.handleToolCallComplete(e),
		onToolCallError: (e) => streamingChat.handleToolCallError(e),
		onTokenStream: (i) => streamingChat.handleTokenStream(i),
		onContentChunk: (e) => streamingChat.handleContentChunk(e),
		onSubAgentStart: (e) => streamingChat.handleSubAgentStart(e),
		onSubAgentComplete: (e) => streamingChat.handleSubAgentComplete(e),
		onGuardrailViolation: (e) => {
			streamingChat.handleGuardrailViolation(e);
			const isEnforced = !e.enforcement_mode || e.enforcement_mode === "enforce";
			if (e.severity === "block" && isEnforced) {
				setGuardrailBlockViolation(e);
			}
		},
		onExecutionComplete: () => {
			const finalMsg = streamingChat.finalize();
			setExecutionId(null);
			const text = finalMsg.blocks
				.filter((b): b is TextBlock => b.type === "text")
				.map((b) => b.content)
				.join("");
			if (text) {
				addMessage(workflowId, {
					role: "assistant",
					content: text,
					execution_id: null,
					created_at: new Date().toISOString(),
				});
			}
			setIsExecuting(false);
		},
		onExecutionError: () => { streamingChat.finalize(); setIsExecuting(false); setExecutionId(null); },
		onStopped:         () => { streamingChat.finalize(); setIsExecuting(false); setExecutionId(null); },
	});

	const handleSend = useCallback(
		async (message: string, files?: File[]) => {
			if (isExecuting || isPublished !== true) return;

			streamingChat.reset();
			streamingChat.startStreaming();

			addMessage(workflowId, {
				role: "user",
				content: message,
				execution_id: null,
				created_at: new Date().toISOString(),
			});
			setIsExecuting(true);

			try {
				let sid = sessionId;
				if (!sid) {
					const session = await chatAPI.createSession(workflowId);
					sid = session.id;
					setSessionId(workflowId, sid);
				}
				const resp = files && files.length > 0
					? await chatAPI.sendMessageWithFile(sid, message, files)
					: await chatAPI.sendMessage(sid, message);
				setExecutionId(resp.execution_id);
			} catch (err) {
				console.error("Canvas chat send failed:", err);
				setIsExecuting(false);
			}
		},
		[isExecuting, isPublished, sessionId, workflowId, streamingChat, addMessage, setSessionId],
	);

	const handleEndExecution = useCallback(async () => {
		setGuardrailBlockViolation(null);
		if (executionId) { try { await api.stopExecution(executionId); } catch {} }
		streamingChat.finalize();
		setIsExecuting(false);
		setExecutionId(null);
	}, [executionId, streamingChat]);

	return (
		<div className="flex flex-col h-full">
			<GuardrailBlockModal
				violation={guardrailBlockViolation}
				onEndExecution={handleEndExecution}
			/>
			{isPublished === false && (
				<div className="flex shrink-0 items-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2.5">
					<Globe className="h-4 w-4 shrink-0 text-amber-500" />
					<p className="text-xs text-amber-800">
						Publish this workflow using the <strong>Publish</strong> button to use Chat.
					</p>
				</div>
			)}
			<ChatMessageList
				messages={messages}
				streamingMessage={streamingChat.streamingMessage}
				workflowId={workflowId}
				workflowName={graphName}
				onSuggestionClick={(text) => chatInputRef.current?.setValue(text)}
			/>
			<div className="shrink-0">
				<ChatInput
					ref={chatInputRef}
					onSend={handleSend}
					onStop={handleStop}
					isExecuting={isExecuting}
					disabled={isPublished !== true}
				/>
			</div>
		</div>
	);
}
