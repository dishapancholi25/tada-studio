/**
 * Chat API client for conversational workflow interaction.
 */

import { runtimeConfig } from "./runtime-config";

export interface ChatSession {
	id: string;
	title: string;
	workflow_id: string;
	workflow_name: string;
	message_count: number;
	last_message_at: string | null;
	created_at: string;
}

export interface ChatAttachment {
	name: string;
	type: string;
	blobUrl: string;
	size?: number;
}

export interface ChatMessage {
	role: "user" | "assistant";
	content: string;
	execution_id: string | null;
	created_at: string | null;
	attachment?: ChatAttachment;
}

export interface ChatWorkflow {
	id: string;
	workflow_id: string;
	graph_name: string;
	description: string | null;
}

export interface SendMessageResponse {
	success: boolean;
	execution_id: string;
	chat_session_id: string;
	status: string;
	message: string;
}

class ChatAPI {
	private async getBaseUrl(): Promise<string> {
		return runtimeConfig.getApiBaseUrl();
	}

	private async request<T>(path: string, options?: RequestInit): Promise<T> {
		const baseUrl = await this.getBaseUrl();
		const response = await fetch(`${baseUrl}${path}`, {
			...options,
			headers: {
				"Content-Type": "application/json",
				...(options?.headers || {}),
			},
			credentials: "include",
		});

		if (!response.ok) {
			let detail = response.statusText;
			try {
				const payload = await response.json();
				detail = payload.detail || payload.message || detail;
			} catch {
				// Ignore parse errors
			}
			throw new Error(detail || "Request failed");
		}

		// Handle 204 No Content
		if (response.status === 204) {
			return {} as T;
		}

		return response.json();
	}

	async listChatWorkflows(): Promise<ChatWorkflow[]> {
		return this.request<ChatWorkflow[]>("/api/chat/workflows");
	}

	async listSessions(workflowId?: string, limit = 50, offset = 0): Promise<ChatSession[]> {
		const params = new URLSearchParams();
		if (workflowId) params.set("workflow_id", workflowId);
		params.set("limit", String(limit));
		params.set("offset", String(offset));
		return this.request<ChatSession[]>(`/api/chat/sessions?${params}`);
	}

	async createSession(workflowId: string): Promise<ChatSession> {
		return this.request<ChatSession>("/api/chat/sessions", {
			method: "POST",
			body: JSON.stringify({ workflow_id: workflowId }),
		});
	}

	async getSession(sessionId: string): Promise<ChatSession> {
		return this.request<ChatSession>(`/api/chat/sessions/${sessionId}`);
	}

	async renameSession(sessionId: string, title: string): Promise<ChatSession> {
		return this.request<ChatSession>(`/api/chat/sessions/${sessionId}`, {
			method: "PATCH",
			body: JSON.stringify({ title }),
		});
	}

	async deleteSession(sessionId: string): Promise<void> {
		await this.request<Record<string, never>>(`/api/chat/sessions/${sessionId}`, {
			method: "DELETE",
		});
	}

	async getMessages(sessionId: string, limit = 100, offset = 0): Promise<ChatMessage[]> {
		const params = new URLSearchParams();
		params.set("limit", String(limit));
		params.set("offset", String(offset));
		return this.request<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages?${params}`);
	}

	async sendMessage(sessionId: string, message: string): Promise<SendMessageResponse> {
		return this.request<SendMessageResponse>(
			`/api/chat/sessions/${sessionId}/messages`,
			{
				method: "POST",
				body: JSON.stringify({ message }),
			},
		);
	}

	async sendMessageWithFile(sessionId: string, message: string, files: File | File[]): Promise<SendMessageResponse> {
		const baseUrl = await this.getBaseUrl();
		const formData = new FormData();
		formData.append("msg", message);
		for (const f of Array.isArray(files) ? files : [files]) formData.append("file", f);

		const response = await fetch(`${baseUrl}/api/chat/sessions/${sessionId}/messages-with-file`, {
			method: "POST",
			body: formData,
			credentials: "include",
		});

		if (!response.ok) {
			const err = await response.json().catch(() => ({}));
			throw new Error(err.detail ?? "Failed to send message with file");
		}
		return response.json();
	}
}

export const chatAPI = new ChatAPI();
