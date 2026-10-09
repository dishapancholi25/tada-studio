"use client";

import { MessageCircle } from "lucide-react";

import ChatSidebar from "@/components/chat/ChatSidebar";

export default function ChatPage() {
	return (
		<>
			<ChatSidebar />
			<div className="flex flex-1 items-center justify-center">
				<div className="text-center animate-fadeInUp">
					<div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-[rgba(var(--color-primary-rgb),0.25)] bg-[rgba(var(--color-primary-rgb),0.06)] shadow-[0_0_30px_rgba(var(--color-primary-rgb),0.08)]">
						<MessageCircle
							size={28}
							className="text-[color:var(--color-text-muted)]"
						/>
					</div>
					<h2 className="text-lg font-semibold text-[color:var(--color-text-primary)]">
						Chat with Workflows
					</h2>
					<p className="mt-1 max-w-sm text-sm text-[color:var(--color-text-muted)]">
						Select a workflow and start a new chat, or pick an existing conversation
						from the sidebar.
					</p>
				</div>
			</div>
		</>
	);
}
