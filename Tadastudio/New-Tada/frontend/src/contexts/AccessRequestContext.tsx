"use client";

import React, {
	createContext,
	useContext,
	useEffect,
	useState,
	useCallback,
	useRef,
	type ReactNode,
} from "react";
import { runtimeConfig } from "@/lib/runtime-config";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { debugWebSocket, warnWebSocket } from "@/lib/websocket-debug";

export interface AccessRequestNotification {
	type: "access_request" | "access_approved" | "access_rejected";
	request_id: string;
	workflow_id: string;
	workflow_name?: string;
	requester_id?: string;
	requester_email?: string;
	message?: string;
	created_at?: string;
	approved_by?: string;
	rejected_by?: string;
	new_role?: string;
}

export interface AccessRequest {
	id: string;
	workflow_id: string;
	workflow_name?: string;
	requester_id: string;
	requester_email?: string;
	requested_role: string;
	status: string;
	message?: string;
	created_at: string;
	resolved_at?: string;
	resolved_by?: string;
}

interface AccessRequestContextType {
	isConnected: boolean;
	pendingCount: number;
	notifications: AccessRequestNotification[];
	pendingRequests: AccessRequest[];
	refreshPendingRequests: () => Promise<void>;
	approveRequest: (requestId: string) => Promise<void>;
	rejectRequest: (requestId: string) => Promise<void>;
	requestAccess: (workflowId: string, message?: string) => Promise<void>;
	clearNotification: (requestId: string) => void;
}

const AccessRequestContext = createContext<AccessRequestContextType | null>(null);

async function getNotificationWsUrl(): Promise<string> {
	const config = await runtimeConfig.getConfig();

	if (config.deployment === "separate-domains" && config.apiUrl) {
		const backendUrl = new URL(config.apiUrl);
		const protocol = backendUrl.protocol === "https:" ? "wss:" : "ws:";
		return `${protocol}//${backendUrl.host}/api/ws/notifications/ws`;
	} else {
		const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
		const host = window.location.host;
		return `${protocol}//${host}/api/ws/notifications/ws`;
	}
}

async function getApiBaseUrl(): Promise<string> {
	const config = await runtimeConfig.getConfig();
	if (config.deployment === "separate-domains" && config.apiUrl) {
		return config.apiUrl;
	}
	return "";
}

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
	const contentType = response.headers.get("content-type") ?? "";
	if (contentType.includes("application/json")) {
		const error = await response.json().catch(() => null);
		return error?.detail || fallback;
	}

	const text = await response.text().catch(() => "");
	return text || fallback;
}

export function AccessRequestProvider({ children }: { children: ReactNode }) {
	const { user } = useAuth();
	const { showSuccess, showInfo, showWarning } = useToast();
	const [isConnected, setIsConnected] = useState(false);
	const [pendingCount, setPendingCount] = useState(0);
	const [notifications, setNotifications] = useState<AccessRequestNotification[]>([]);
	const [pendingRequests, setPendingRequests] = useState<AccessRequest[]>([]);
	const wsRef = useRef<WebSocket | null>(null);
	const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

	const fetchPendingRequests = useCallback(async () => {
		try {
			const baseUrl = await getApiBaseUrl();
			const response = await fetch(`${baseUrl}/api/ws/notifications/access-requests?status=pending`, {
				credentials: "include",
			});
			if (response.ok) {
				const data = (await response.json()) as AccessRequest[];
				console.groupCollapsed(`%c[AccessRequests] Fetched Pending Requests`, "color: #6366f1; font-weight: bold");
				console.log("Count:", data.length);
				if (data.length > 0) {
					console.table(data.map((r) => ({
						id: r.id.slice(0, 8) + "...",
						workflow_id: r.workflow_id.slice(0, 8) + "...",
						workflow_name: r.workflow_name,
						requester: r.requester_email,
						status: r.status
					})));
				}
				console.groupEnd();
				setPendingRequests(data);
				setPendingCount(data.length);
			} else {
				console.error("[AccessRequests] Failed to fetch, status:", response.status);
			}
		} catch (error) {
			console.error("[AccessRequests] Failed to fetch pending requests:", error);
		}
	}, []);

	const connectWebSocket = useCallback(async () => {
		if (wsRef.current?.readyState === WebSocket.OPEN) {
			return;
		}

		try {
			const wsUrl = await getNotificationWsUrl();
			debugWebSocket("AccessRequestsWS", "Connecting", { wsUrl });
			const ws = new WebSocket(wsUrl);

			ws.onopen = () => {
				debugWebSocket("AccessRequestsWS", "Connected", { wsUrl });
				setIsConnected(true);
			};

			ws.onmessage = (event) => {
				try {
					const data = JSON.parse(event.data);

					if (data.type === "init") {
						console.groupCollapsed(`%c[AccessRequests] WebSocket Init`, "color: #3b82f6; font-weight: bold");
						console.log("Initial pending_count:", data.pending_count);
						console.groupEnd();
						setPendingCount(data.pending_count || 0);
					} else if (data.type === "pong") {
						// Keepalive response - don't log
					} else if (data.type === "access_request") {
						console.group(`%c[AccessRequests] NEW ACCESS REQUEST RECEIVED`, "color: #f59e0b; font-weight: bold; font-size: 14px");
						console.log("Request ID:", data.request_id);
						console.log("Workflow ID:", data.workflow_id);
						console.log("Workflow Name:", data.workflow_name);
						console.log("Requester:", data.requester_email);
						console.log("Message:", data.message || "(none)");
						console.log("Timestamp:", data.created_at);
						console.groupEnd();
						setNotifications((prev) => [data, ...prev]);
						setPendingCount((prev) => prev + 1);
						fetchPendingRequests();
						// Show toast to owner
						const requesterName = data.requester_email?.split("@")[0] || "Someone";
						const workflowName = data.workflow_name || "your workflow";
						showInfo(
							"New Access Request",
							`${requesterName} wants editor access to "${workflowName}"`
						);
					} else if (data.type === "access_approved" || data.type === "access_rejected") {
						const isApproved = data.type === "access_approved";
						console.group(`%c[AccessRequests] ACCESS ${isApproved ? "APPROVED" : "REJECTED"}`, `color: ${isApproved ? "#10b981" : "#ef4444"}; font-weight: bold; font-size: 14px`);
						console.log("Request ID:", data.request_id);
						console.log("Workflow ID:", data.workflow_id);
						console.log("Workflow Name:", data.workflow_name);
						console.log(isApproved ? "New Role:" : "Rejected by:", isApproved ? data.new_role : data.rejected_by);
						console.groupEnd();
						setNotifications((prev) => [data, ...prev]);
						// Show toast to requester
						const workflowName = data.workflow_name || "the workflow";
						if (isApproved) {
							showSuccess(
								"Access Granted!",
								`You now have editor access to "${workflowName}"`
							);
						} else {
							showWarning(
								"Access Declined",
								`Your request for "${workflowName}" was declined`
							);
						}
						// Dispatch custom event so GraphContext can reload with new role
						if (isApproved) {
							console.log(`%c[AccessRequests] Dispatching accessRoleChanged event`, "color: #8b5cf6");
							window.dispatchEvent(new CustomEvent("accessRoleChanged", {
								detail: { workflowId: data.workflow_id, newRole: data.new_role }
							}));
						}
					} else if (data.type === "workflow_shared") {
						// Someone shared a workflow with this user
						const sharedBy = data.shared_by?.split("@")[0] || "Someone";
						const workflowName = data.workflow_name || "a workflow";
						const role = data.role || "viewer";
						showSuccess(
							"Workflow Shared With You",
							`${sharedBy} shared "${workflowName}" with you as ${role}`
						);
						// Dispatch event so the workflow list can refresh without page reload
						window.dispatchEvent(new CustomEvent("workflowShared", {
							detail: { workflowId: data.workflow_id, role: data.role, workflowName: data.workflow_name }
						}));
					}
				} catch (error) {
					console.error("[AccessRequests] Failed to parse message:", error);
				}
			};

			ws.onclose = (event) => {
				warnWebSocket("AccessRequestsWS", "Disconnected", {
					wsUrl,
					code: event.code,
					reason: event.reason,
					wasClean: event.wasClean,
				});
				setIsConnected(false);
				wsRef.current = null;

				// Reconnect after delay
				reconnectTimeoutRef.current = setTimeout(() => {
					connectWebSocket();
				}, 5000);
			};

			ws.onerror = (error) => {
				warnWebSocket("AccessRequestsWS", "Connection error", { wsUrl, error });
			};

			wsRef.current = ws;

			// Send ping every 30 seconds to keep connection alive
			const pingInterval = setInterval(() => {
				if (ws.readyState === WebSocket.OPEN) {
					ws.send(JSON.stringify({ type: "ping" }));
				}
			}, 30000);

			ws.addEventListener("close", () => {
				clearInterval(pingInterval);
			});
		} catch (error) {
			console.error("[AccessRequests] Failed to connect WebSocket:", error);
		}
	}, [fetchPendingRequests, showInfo, showSuccess, showWarning]);

	// Connect when user is available
	useEffect(() => {
		if (user) {
			connectWebSocket();
			fetchPendingRequests();
		}

		return () => {
			if (reconnectTimeoutRef.current) {
				clearTimeout(reconnectTimeoutRef.current);
			}
			if (wsRef.current) {
				wsRef.current.close();
			}
		};
	}, [user, connectWebSocket, fetchPendingRequests]);

	const approveRequest = useCallback(async (requestId: string) => {
		try {
			const baseUrl = await getApiBaseUrl();
			const response = await fetch(`${baseUrl}/api/ws/notifications/access-requests/${requestId}/resolve`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				credentials: "include",
				body: JSON.stringify({ action: "approve" }),
			});

			if (response.ok) {
				setPendingRequests((prev) => prev.filter((r) => r.id !== requestId));
				setPendingCount((prev) => Math.max(0, prev - 1));
			} else {
				throw new Error(
					await getErrorMessage(response, "Failed to approve request"),
				);
			}
		} catch (error) {
			console.error("[AccessRequests] Failed to approve request:", error);
			throw error;
		}
	}, []);

	const rejectRequest = useCallback(async (requestId: string) => {
		try {
			const baseUrl = await getApiBaseUrl();
			const response = await fetch(`${baseUrl}/api/ws/notifications/access-requests/${requestId}/resolve`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				credentials: "include",
				body: JSON.stringify({ action: "reject" }),
			});

			if (response.ok) {
				setPendingRequests((prev) => prev.filter((r) => r.id !== requestId));
				setPendingCount((prev) => Math.max(0, prev - 1));
			} else {
				throw new Error(
					await getErrorMessage(response, "Failed to reject request"),
				);
			}
		} catch (error) {
			console.error("[AccessRequests] Failed to reject request:", error);
			throw error;
		}
	}, []);

	const requestAccess = useCallback(async (workflowId: string, message?: string) => {
		try {
			const baseUrl = await getApiBaseUrl();
			const response = await fetch(`${baseUrl}/api/ws/notifications/access-requests`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				credentials: "include",
				body: JSON.stringify({
					workflow_id: workflowId,
					message,
					requested_role: "editor",
				}),
			});

			if (!response.ok) {
				throw new Error(
					await getErrorMessage(response, "Failed to request access"),
				);
			}
		} catch (error) {
			console.error("[AccessRequests] Failed to request access:", error);
			throw error;
		}
	}, []);

	const clearNotification = useCallback((requestId: string) => {
		setNotifications((prev) => prev.filter((n) => n.request_id !== requestId));
	}, []);

	const value = {
		isConnected,
		pendingCount,
		notifications,
		pendingRequests,
		refreshPendingRequests: fetchPendingRequests,
		approveRequest,
		rejectRequest,
		requestAccess,
		clearNotification,
	};

	return (
		<AccessRequestContext.Provider value={value}>
			{children}
		</AccessRequestContext.Provider>
	);
}

export function useAccessRequests() {
	const context = useContext(AccessRequestContext);
	if (!context) {
		throw new Error("useAccessRequests must be used within an AccessRequestProvider");
	}
	return context;
}
