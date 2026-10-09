import { Bot, MessageSquare, User } from "lucide-react";
import type React from "react";
import type { ConversationMessage } from "@/types/api";
import SimpleMarkdown from "../../../utils/SimpleMarkdown";

interface ConversationHistoryTabProps {
	messages: ConversationMessage[];
}

const ConversationHistoryTab: React.FC<ConversationHistoryTabProps> = ({
	messages,
}) => {
	const processedMessages = messages
		.map((msg) => {
			let content = msg.content;
			if (msg.role === "user" && content.includes("Current Message:")) {
				const parts = content.split("Current Message:");
				content = parts[parts.length - 1].trim();
			}
			return { ...msg, content };
		})
		.sort((a, b) => {
			if (!a.timestamp || !b.timestamp) return 0;
			return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
		});

	return (
		<section className="h-[calc(90vh-230px)] rounded-2xl border border-gray-200 bg-white shadow-sm">
			<div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
				<div>
					<p className="text-[0.65rem] capitalize text-gray-500">
						Conversation History
					</p>
					<p className="text-xs text-gray-600">Chronological dialogue</p>
				</div>
				<span className="inline-flex items-center gap-2 rounded-full border border-orange-300 bg-white px-3 py-1 text-xs font-medium text-orange-800">
					<MessageSquare className="h-3.5 w-3.5" />
					{processedMessages.length}
				</span>
			</div>
			<div className="custom-scrollbar h-[calc(90vh-290px)] space-y-4 overflow-y-auto px-6 py-5">
				{processedMessages.map((msg, idx) => {
					const isUser = msg.role === "user";
					return (
						<div
							key={msg.timestamp || `msg-${idx}`}
							className={`flex gap-4 ${isUser ? "justify-start" : "justify-end"}`}
						>
							{isUser && (
								<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-gray-200 bg-white shadow-sm">
									<User className="h-5 w-5 text-orange-600" />
								</div>
							)}

							<div
								className={`max-w-[70%] rounded-2xl border px-4 py-3 shadow-sm ${
									isUser
										? "border-gray-200 bg-white text-gray-900"
										: "border-gray-200 bg-slate-50 text-gray-900"
								}`}
							>
								<div className="mb-2 flex items-center gap-2 text-[11px] capitalize text-gray-500">
									<span>{isUser ? "User" : "Assistant"}</span>
									{msg.timestamp && (
										<span className="font-mono normal-case tracking-normal text-gray-600">
											{new Date(msg.timestamp).toLocaleTimeString()}
										</span>
									)}
								</div>
								<div className="text-sm leading-relaxed">
									<SimpleMarkdown content={msg.content} variant="light" />
								</div>
							</div>

							{!isUser && (
								<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-gray-200 bg-white shadow-sm">
									<Bot className="h-5 w-5 text-gray-600" />
								</div>
							)}
						</div>
					);
				})}
			</div>
		</section>
	);
};

export default ConversationHistoryTab;
