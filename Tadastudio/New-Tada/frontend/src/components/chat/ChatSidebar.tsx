"use client";

import { LayoutGrid, MessageSquare, Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import Dropdown from "@/components/ui/Dropdown";
import type { DropdownOption } from "@/components/ui/Dropdown";
import { chatAPI } from "@/lib/chat-api";
import type { ChatSession, ChatWorkflow } from "@/lib/chat-api";

interface ChatSidebarProps {
	activeSessionId?: string;
	initialWorkflowId?: string;
}

export default function ChatSidebar({ activeSessionId, initialWorkflowId }: ChatSidebarProps) {
	const router = useRouter();
	const [workflows, setWorkflows] = useState<ChatWorkflow[]>([]);
	const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>("");
	const [sessions, setSessions] = useState<ChatSession[]>([]);
	const [loading, setLoading] = useState(true);
	const dropdownTriggerClassName =
		"!bg-white !border-slate-200 !text-slate-900 hover:!bg-slate-50 hover:!border-slate-300 focus:!border-orange-400 focus:!ring-orange-500/20";
	const dropdownMenuClassName =
		"!bg-white !border-slate-200 !shadow-[0_20px_55px_rgba(15,23,42,0.12)]";
	const dropdownOptionClassName =
		"!text-slate-700 hover:!bg-slate-50 hover:!text-slate-900 aria-selected:!bg-orange-50 aria-selected:!text-slate-900";

	const loadWorkflows = useCallback(async () => {
		try {
			const wfs = await chatAPI.listChatWorkflows();
			setWorkflows(wfs);
			if (wfs.length > 0) {
				setSelectedWorkflowId((prev) => {
					if (initialWorkflowId) {
						const match = wfs.find((w) => w.workflow_id === initialWorkflowId);
						if (match) return match.workflow_id;
					}
					if (prev) return prev;
					return wfs[0].workflow_id;
				});
			}
		} catch (err) {
			console.error("Failed to load workflows:", err);
		}
	}, [initialWorkflowId]);

	const loadSessions = useCallback(async () => {
		if (!selectedWorkflowId) {
			setSessions([]);
			setLoading(false);
			return;
		}
		try {
			setLoading(true);
			const list = await chatAPI.listSessions(selectedWorkflowId);
			setSessions(list);
		} catch (err) {
			console.error("Failed to load sessions:", err);
		} finally {
			setLoading(false);
		}
	}, [selectedWorkflowId]);

	useEffect(() => {
		loadWorkflows();
	}, [loadWorkflows]);

	useEffect(() => {
		loadSessions();
	}, [loadSessions]);

	const handleNewChat = async () => {
		if (!selectedWorkflowId) return;
		try {
			const session = await chatAPI.createSession(selectedWorkflowId);
			setSessions((prev) => [session, ...prev]);
			window.dispatchEvent(new CustomEvent("collapseSidebar"));
			router.push(`/chat/${session.id}?wf=${selectedWorkflowId}`);
		} catch (err) {
			console.error("Failed to create session:", err);
		}
	};

	const handleDeleteSession = async (sessionId: string) => {
		try {
			await chatAPI.deleteSession(sessionId);
			setSessions((prev) => prev.filter((s) => s.id !== sessionId));
			if (activeSessionId === sessionId) {
				router.push("/chat");
			}
		} catch (err) {
			console.error("Failed to delete session:", err);
		}
	};

	const workflowOptions: DropdownOption[] = workflows.map((wf) => ({
		value: wf.workflow_id,
		label: wf.graph_name,
	}));

	const formatTime = (dateStr: string | null) => {
		if (!dateStr) return "";
		const date = new Date(dateStr);
		const now = new Date();
		const diff = now.getTime() - date.getTime();
		const days = Math.floor(diff / 86400000);
		if (days === 0) return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
		if (days === 1) return "Yesterday";
		if (days < 7) return `${days}d ago`;
		return date.toLocaleDateString();
	};

	return (
		<div className="relative flex h-full w-72 flex-col border-r border-slate-200 bg-white">
			{/* Workflow selector */}
			<div className="flex h-[60px] min-w-0 items-center border-b border-black/10 bg-[rgb(249,115,22)] px-3">
				<div className="flex min-w-0 flex-1 items-center gap-2">
					<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/30 bg-transparent">
						<LayoutGrid size={16} className="text-white" />
					</div>
					<div className="min-w-0 flex-1">
						<Dropdown
							value={selectedWorkflowId}
							onChange={(val) => setSelectedWorkflowId(val as string)}
							options={workflowOptions}
							placeholder="Select workflow..."
							menuAppearance="light"
							menuMinWidthPx={288}
							triggerClassName={dropdownTriggerClassName}
							dropdownClassName={dropdownMenuClassName}
							optionClassName={dropdownOptionClassName}
						/>
					</div>
				</div>
			</div>

			{/* New chat button */}
			<div className="p-3">
				<button
					type="button"
					onClick={handleNewChat}
					disabled={!selectedWorkflowId}
					className="flex w-full items-center justify-center gap-2 rounded-xl bg-orange-500 border border-orange-500 px-3 py-2.5 text-sm font-medium text-white transition-all duration-200 hover:bg-orange-600 hover:border-orange-600 disabled:cursor-not-allowed disabled:opacity-40"
				>
					<Plus size={16} />
					New Chat
				</button>
			</div>

			{/* RECENT label */}
			{sessions.length > 0 && (
				<div className="px-3 mb-2">
					<span className="text-[0.6rem] capitalize text-slate-500 font-semibold">
						RECENT
					</span>
				</div>
			)}

			{/* Session list */}
			<div className="flex-1 overflow-y-auto chat-scrollbar px-2 pb-2">
				{loading ? (
					<div className="flex items-center justify-center py-8 text-xs text-slate-500">
						Loading...
					</div>
				) : sessions.length === 0 ? (
					<div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
						<MessageSquare size={24} className="text-slate-400" />
						<p className="text-xs text-slate-500">
							{selectedWorkflowId
								? "No chats yet. Start a new conversation."
								: "Select a workflow to begin."}
						</p>
					</div>
				) : (
					sessions.map((session) => {
						const isActive = session.id === activeSessionId;
						return (
							<button
								key={session.id}
								type="button"
								onClick={() => {
									// Set workflow immediately to prevent dropdown flicker
									if (session.workflow_id && session.workflow_id !== selectedWorkflowId) {
										setSelectedWorkflowId(session.workflow_id);
									}
									router.push(`/chat/${session.id}`);
								}}
								className={`group mb-1 flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left transition-all duration-200 ${
									isActive
										? "border-l-[3px] border-l-orange-500 border border-orange-200 bg-orange-50"
										: "border border-transparent hover:bg-slate-50 hover:border-slate-200"
								}`}
							>
								<MessageSquare
									size={14}
									className={`shrink-0 ${
										isActive
											? "text-orange-700"
											: "text-slate-400"
									}`}
								/>
								<div className="min-w-0 flex-1">
									<p className={`truncate text-sm font-medium ${
										isActive
											? "text-slate-900"
											: "text-slate-700"
									}`}>
										{session.title}
									</p>
									<p className="mt-0.5 font-mono text-[11px] text-slate-500">
										{formatTime(session.last_message_at)}
										{session.message_count > 0 && ` · ${session.message_count} msgs`}
									</p>
								</div>
								<button
									type="button"
									onClick={(e) => {
										e.stopPropagation();
										handleDeleteSession(session.id);
									}}
									className="ml-1 shrink-0 rounded p-1 opacity-0 transition-opacity duration-200 hover:bg-red-50 group-hover:opacity-100"
									title="Delete"
								>
									<Trash2 size={14} className="text-red-600" />
								</button>
							</button>
						);
					})
				)}
			</div>
		</div>
	);
}
