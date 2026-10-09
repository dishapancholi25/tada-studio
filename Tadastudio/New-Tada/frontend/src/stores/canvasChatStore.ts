import { create } from "zustand";
import type { ChatMessage } from "@/lib/chat-api";

interface WorkflowChatState {
	messages: ChatMessage[];
	sessionId: string | null;
}

interface CanvasChatStore {
	// Keyed by workflowId so each workflow has its own isolated history
	chats: Record<string, WorkflowChatState>;
	addMessage: (workflowId: string, message: ChatMessage) => void;
	setSessionId: (workflowId: string, sessionId: string) => void;
	getChat: (workflowId: string) => WorkflowChatState;
}

const DEFAULT_CHAT: WorkflowChatState = { messages: [], sessionId: null };

export const useCanvasChatStore = create<CanvasChatStore>((set, get) => ({
	chats: {},

	getChat: (workflowId) => get().chats[workflowId] ?? DEFAULT_CHAT,

	addMessage: (workflowId, message) =>
		set((state) => {
			const prev = state.chats[workflowId] ?? DEFAULT_CHAT;
			return {
				chats: {
					...state.chats,
					[workflowId]: { ...prev, messages: [...prev.messages, message] },
				},
			};
		}),

	setSessionId: (workflowId, sessionId) =>
		set((state) => {
			const prev = state.chats[workflowId] ?? DEFAULT_CHAT;
			return {
				chats: {
					...state.chats,
					[workflowId]: { ...prev, sessionId },
				},
			};
		}),
}));
