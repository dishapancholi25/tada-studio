"use client";

import { useEffect, useRef } from "react";

import SimpleMarkdown from "@/components/utils/SimpleMarkdown";
import type { ChatMessage } from "@/lib/chat-api";
import type { StreamingMessage } from "@/hooks/useStreamingChat";
import ChatPdfAttachment from "./ChatPdfAttachment";
import StreamingAssistantMessage from "./StreamingAssistantMessage";
import SuggestionChips from "./SuggestionChips";
import { parseSuggestions } from "./utils/parseSuggestions";

interface ChatMessageListProps {
	messages: ChatMessage[];
	streamingMessage?: StreamingMessage | null;
	workflowId?: string;
	workflowName?: string;
	onSuggestionClick?: (text: string) => void;
}

export default function ChatMessageList({
	messages,
	streamingMessage,
	workflowName,
	onSuggestionClick,
}: ChatMessageListProps) {
	const endRef = useRef<HTMLDivElement>(null);
	const seenCountRef = useRef(0);

	const blockCount = streamingMessage?.blocks.length ?? 0;

	const displayMessages = (() => {
		if (!streamingMessage?.isComplete || messages.length === 0) return messages;
		// Only suppress the last assistant message if the streaming message has real
		// text content that replaces it. If it only contains a guardrail block (no
		// text), the previous assistant response should remain visible.
		const hasText = streamingMessage.blocks.some((b) => b.type === "text");
		if (!hasText) return messages;
		const lastAssistantIdx = messages.findLastIndex((m) => m.role === "assistant");
		if (lastAssistantIdx === -1) return messages;
		return messages.filter((_, idx) => idx !== lastAssistantIdx);
	})();

	useEffect(() => {
		endRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [messages.length, blockCount]);

	const prevSeenCount = seenCountRef.current;
	useEffect(() => {
		seenCountRef.current = messages.length;
	}, [messages.length]);

	if (displayMessages.length === 0 && !streamingMessage) {
		return (
			<div className="flex min-h-0 flex-1 flex-col items-center justify-center bg-white">
				<div className="animate-fadeInUp text-center">
					<div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-[10px] border border-gray-200 bg-white shadow-sm">
						<svg width="14" height="14" viewBox="0 0 14 14">
							<polygon
								points="7,1 13,7 7,13 1,7"
								fill="none"
								stroke="rgb(234 88 12)"
								strokeWidth="1.2"
							/>
							<circle cx="7" cy="7" r="2" fill="rgb(234 88 12)" />
						</svg>
					</div>
					<p className="text-sm text-slate-600">
						Send a message to start the conversation.
					</p>
				</div>
			</div>
		);
	}

	const formatTimestamp = (dateStr: string) => {
		return new Date(dateStr).toLocaleTimeString([], {
			hour: "2-digit",
			minute: "2-digit",
		});
	};

	const getDateLabel = (dateStr: string) => {
		const d = new Date(dateStr);
		const today = new Date();
		const yesterday = new Date();
		yesterday.setDate(yesterday.getDate() - 1);
		if (d.toDateString() === today.toDateString()) return "Today";
		if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
		return d.toLocaleDateString([], { month: "short", day: "numeric" });
	};

	return (
		<div className="relative flex min-h-0 flex-1 flex-col bg-white">
			<div className="chat-scrollbar absolute inset-0 overflow-y-auto px-6 py-6">
				<div className="space-y-6">
					{displayMessages.map((msg, idx) => {
						const isUser = msg.role === "user";
						const isNew = idx >= prevSeenCount;

						const prevMsg = idx > 0 ? displayMessages[idx - 1] : null;
						const showDateSep =
							msg.created_at &&
							(!prevMsg?.created_at ||
								new Date(msg.created_at).toDateString() !==
									new Date(prevMsg.created_at).toDateString());

						return (
							<div key={`${msg.execution_id || "msg"}-${idx}`}>
								{showDateSep && msg.created_at && (
									<div className="chat-system-divider mb-6">
										<span>{getDateLabel(msg.created_at)}</span>
									</div>
								)}

								<div
									className={`flex flex-col ${isUser ? "items-end" : "items-start"} ${isNew ? "animate-fadeInUp" : ""}`}
									style={
										isNew ? { animationDuration: "0.35s" } : undefined
									}
								>
									<div
										className={`mb-1.5 ${!isUser ? "ml-[44px]" : "mr-[44px]"}`}
									>
										<span
											className={`block max-w-[200px] truncate text-[0.6rem] font-semibold capitalize ${
												isUser ? "text-slate-500" : "text-orange-800"
											}`}
										>
											{isUser ? "YOU" : workflowName || "AGENT"}
										</span>
									</div>

									<div
										className={`flex max-w-[720px] gap-3 ${isUser ? "flex-row-reverse" : ""}`}
									>
										{!isUser && (
											<div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] border border-gray-200 bg-white shadow-sm">
												<svg width="14" height="14" viewBox="0 0 14 14">
													<polygon
														points="7,1 13,7 7,13 1,7"
														fill="none"
														stroke="rgb(234 88 12)"
														strokeWidth="1.2"
													/>
													<circle cx="7" cy="7" r="2" fill="rgb(234 88 12)" />
												</svg>
											</div>
										)}

										<div
											className={`px-[18px] py-[14px] transition-colors ${
												isUser
													? "chat-bubble-user border border-gray-200 bg-white shadow-[0_4px_16px_rgb(15_23_42_/_0.06)] hover:border-orange-400"
													: "chat-bubble-assistant border border-gray-200 bg-white shadow-[0_4px_16px_rgb(15_23_42_/_0.06)]"
											}`}
										>
											{isUser ? (
												<div>
													{msg.content && (
														<p className="text-sm text-slate-900">{msg.content}</p>
													)}
													{msg.attachment?.type.includes("pdf") &&
													msg.attachment.blobUrl ? (
														<ChatPdfAttachment
															name={msg.attachment.name}
															blobUrl={msg.attachment.blobUrl}
															size={msg.attachment.size}
														/>
													) : (
														!msg.content && (
															<p className="text-sm italic text-slate-400">
																File attached
															</p>
														)
													)}
												</div>
											) : (() => {
												const { mainContent, suggestions } = parseSuggestions(msg.content);
												return (
													<>
														<div className="text-sm text-slate-900">
															<SimpleMarkdown content={mainContent || msg.content} variant="light" />
														</div>
														{suggestions.length > 0 && onSuggestionClick && (
															<SuggestionChips suggestions={suggestions} onSelect={onSuggestionClick} />
														)}
													</>
												);
											})()}
										</div>

										{isUser && (
											<div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-gray-200 bg-white shadow-sm">
												<span className="text-xs font-semibold text-orange-800">
													U
												</span>
											</div>
										)}
									</div>

									{msg.created_at && (
										<p
											className={`mt-1 text-[10px] text-slate-500 ${isUser ? "mr-[44px] text-right" : "ml-[44px]"}`}
										>
											{formatTimestamp(msg.created_at)}
										</p>
									)}
								</div>
							</div>
						);
					})}

					{streamingMessage && (
						<StreamingAssistantMessage
							streamingMessage={streamingMessage}
							workflowName={workflowName}
							onSuggestionClick={onSuggestionClick}
						/>
					)}

					<div ref={endRef} />
				</div>
			</div>
		</div>
	);
}
