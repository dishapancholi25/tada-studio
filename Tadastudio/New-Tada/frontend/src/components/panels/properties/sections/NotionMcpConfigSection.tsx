"use client";

import {
	AlertCircle,
	CheckCircle,
	ExternalLink,
	Info,
	Link2,
	Loader2,
	Unlink,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import type { McpToolInfo } from "@/components/dialogs/McpToolsViewerModal";
import { NotionIcon } from "@/components/icons/McpProviderIcons";
import { runtimeConfig } from "@/lib/runtime-config";
import McpToolSelectionCard from "./McpToolSelectionCard";

interface OAuthStatus {
	is_authenticated: boolean;
	has_token: boolean;
	has_client_registration: boolean;
	token_expired: boolean;
	expires_at: string | null;
	scope: string | null;
}

interface NotionMcpConfig {
	server_name: string;
	connection_type: "http";
	server_url: string;
	auth_type: "oauth";
	auth_config: {
		provider: "notion";
	};
	provider?: string;
	description?: string;
	workspace_label?: string;
	tool_permissions?: Record<string, boolean>;
}

interface NotionMcpConfigSectionProps {
	config: NotionMcpConfig | null;
	onConfigChange: (config: NotionMcpConfig) => void;
	isConfigured: boolean;
	onAuthStatusChange?: (isAuthenticated: boolean) => void;
}

export default function NotionMcpConfigSection({
	config,
	onConfigChange,
	isConfigured,
	onAuthStatusChange,
}: NotionMcpConfigSectionProps) {
	const [description, setDescription] = useState(
		config?.description ||
			"Notion workspace integration for accessing databases, pages, and content",
	);
	const [workspaceLabel, setWorkspaceLabel] = useState(
		config?.workspace_label || "",
	);
	const [oauthStatus, setOauthStatus] = useState<OAuthStatus | null>(null);
	const [isConnecting, setIsConnecting] = useState(false);
	const [isDisconnecting, setIsDisconnecting] = useState(false);
	const [testStatus, setTestStatus] = useState<
		"idle" | "testing" | "success" | "error"
	>("idle");
	const [testMessage, setTestMessage] = useState("");
	const [statusLoading, setStatusLoading] = useState(true);
	const [discoveredTools, setDiscoveredTools] = useState<McpToolInfo[]>([]);
	const [toolPermissions, setToolPermissions] = useState<Record<string, boolean>>(
		config?.tool_permissions || {},
	);

	// Check OAuth status on mount
	useEffect(() => {
		checkOAuthStatus();
	}, []);

	// Notify parent of auth status changes
	useEffect(() => {
		if (!statusLoading && onAuthStatusChange) {
			onAuthStatusChange(oauthStatus?.is_authenticated ?? false);
		}
	}, [oauthStatus?.is_authenticated, statusLoading, onAuthStatusChange]);

	const checkOAuthStatus = async () => {
		setStatusLoading(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const response = await fetch(`${apiBaseUrl}/api/notion-oauth/status`, {
				method: "GET",
				credentials: "include",
			});

			if (response.ok) {
				const data = await response.json();
				setOauthStatus(data);
			} else {
				console.error("Failed to check OAuth status:", response.status);
				setOauthStatus(null);
			}
		} catch (error) {
			console.error("Error checking OAuth status:", error);
			setOauthStatus(null);
		} finally {
			setStatusLoading(false);
		}
	};

	const handleConnect = async () => {
		setIsConnecting(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const response = await fetch(`${apiBaseUrl}/api/notion-oauth/initiate`, {
				method: "POST",
				credentials: "include",
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || "Failed to initiate OAuth");
			}

			const data = await response.json();
			const { authorization_url } = data;

			// Open popup window
			const popup = window.open(
				authorization_url,
				"notion_oauth",
				"width=600,height=700,left=200,top=100",
			);

			// Listen for completion message from callback page
			const handleMessage = (event: MessageEvent) => {
				if (event.data?.type === "notion_oauth_complete") {
					window.removeEventListener("message", handleMessage);
					popup?.close();
					setIsConnecting(false);

					if (event.data.success) {
						checkOAuthStatus();
						setTestStatus("idle");
						setTestMessage("");
						// Update config
						updateConfig();
					} else {
						setTestStatus("error");
						setTestMessage(event.data.error || "OAuth authorization failed");
					}
				}
			};

			window.addEventListener("message", handleMessage);

			// Check if popup is closed without completing
			const checkPopupClosed = setInterval(() => {
				if (popup?.closed) {
					clearInterval(checkPopupClosed);
					window.removeEventListener("message", handleMessage);
					setIsConnecting(false);
					checkOAuthStatus();
				}
			}, 500);
		} catch (error) {
			console.error("Error initiating OAuth:", error);
			setIsConnecting(false);
			setTestStatus("error");
			setTestMessage(
				error instanceof Error ? error.message : "Failed to connect to Notion",
			);
		}
	};

	const handleDisconnect = async () => {
		setIsDisconnecting(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const response = await fetch(`${apiBaseUrl}/api/notion-oauth/revoke`, {
				method: "DELETE",
				credentials: "include",
			});

			if (response.ok) {
				setOauthStatus(null);
				setTestStatus("idle");
				setTestMessage("");
			} else {
				const error = await response.json();
				throw new Error(error.detail || "Failed to disconnect");
			}
		} catch (error) {
			console.error("Error disconnecting:", error);
			setTestStatus("error");
			setTestMessage(
				error instanceof Error ? error.message : "Failed to disconnect",
			);
		} finally {
			setIsDisconnecting(false);
			checkOAuthStatus();
		}
	};

	const handleTestConnection = async () => {
		if (!oauthStatus?.is_authenticated) {
			setTestStatus("error");
			setTestMessage("Please connect to Notion first");
			return;
		}

		setTestStatus("testing");
		setTestMessage("");

		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const response = await fetch(`${apiBaseUrl}/api/notion-oauth/test`, {
				method: "POST",
				credentials: "include",
			});

			const data = await response.json();

			if (data.status === "success") {
				setTestStatus("success");
				setTestMessage(data.message);
				// Update config on successful test
				updateConfig();

				// Discover tools via MCP test endpoint
				try {
					const discoverResponse = await fetch(
						`${apiBaseUrl}/api/graph/test-mcp-server`,
						{
							method: "POST",
							headers: { "Content-Type": "application/json" },
							credentials: "include",
							body: JSON.stringify({
								server_name: "Notion MCP Server",
								connection_type: "http",
								server_url: "https://mcp.notion.com/mcp",
								auth_type: "oauth",
								auth_config: { provider: "notion" },
								timeout_seconds: 60,
							}),
						},
					);
					const discoverData = await discoverResponse.json();
					if (discoverData.success && discoverData.capabilities?.tools) {
						const tools: McpToolInfo[] = discoverData.capabilities.tools.map(
							(tool: { name?: string; description?: string; input_schema?: Record<string, unknown> }) => ({
								name: tool.name || "Unknown Tool",
								description: tool.description || "No description available",
								input_schema: tool.input_schema || undefined,
							}),
						);
						setDiscoveredTools(tools);
						setTestMessage(`Connected successfully. Found ${tools.length} tools.`);
					}
				} catch {
					// Non-critical: tool discovery failure doesn't block config
				}
			} else {
				setTestStatus("error");
				setTestMessage(data.message || "Connection test failed");
			}
		} catch (error) {
			setTestStatus("error");
			setTestMessage(
				error instanceof Error ? error.message : "Connection test failed",
			);
		}
	};

	const updateConfig = useCallback(() => {
		const newConfig: NotionMcpConfig = {
			server_name: "Notion MCP Server",
			connection_type: "http",
			server_url: "https://mcp.notion.com/mcp",
			auth_type: "oauth",
			auth_config: { provider: "notion" },
			provider: "notion",
			description,
			workspace_label: workspaceLabel,
		};
		onConfigChange(newConfig);
	}, [description, workspaceLabel, onConfigChange]);

	// Update config when description/workspace changes
	useEffect(() => {
		if (oauthStatus?.is_authenticated) {
			updateConfig();
		}
	}, [
		description,
		workspaceLabel,
		oauthStatus?.is_authenticated,
		updateConfig,
	]);

	const handleToolPermissionsChange = useCallback(
		(permissions: Record<string, boolean>) => {
			setToolPermissions(permissions);
			onConfigChange({ tool_permissions: permissions } as any);
		},
		[onConfigChange],
	);

	const isAuthenticated = oauthStatus?.is_authenticated ?? false;

	return (
		<div className="space-y-5">
			{/* Section Label */}
			<div className="text-[0.6rem] font-semibold capitalize text-gray-600">
				Notion Configuration
			</div>

			{/* Info Card */}
			<div className="rounded-[4px] border border-cyan-700/25 bg-white p-4 shadow-sm">
				<div className="flex items-start gap-3">
					<div className="rounded-[4px] border border-cyan-700/20 bg-cyan-50 p-2">
						<Info className="h-4 w-4 text-cyan-800" />
					</div>
					<div className="flex-1">
						<h4 className="mb-1 text-sm font-medium text-cyan-900">
							About Notion MCP
						</h4>
						<p className="mb-2 text-xs text-gray-600">
							Connect to Notion&apos;s official MCP server to access databases,
							pages, and workspace content.
						</p>
						<a
							href="https://developers.notion.com/"
							target="_blank"
							rel="noopener noreferrer"
							className="flex items-center gap-1 text-xs text-cyan-900 transition-colors hover:text-slate-900"
						>
							Learn more about Notion API
							<ExternalLink className="w-3 h-3" />
						</a>
					</div>
				</div>
			</div>

			{/* OAuth Connection Status Card */}
			<div
				className={`rounded-[4px] border bg-white p-4 shadow-sm ${
					isAuthenticated ? "border-emerald-300" : "border-amber-300"
				}`}
			>
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-3">
						{statusLoading ? (
							<div className="rounded-[4px] border border-gray-200 bg-gray-50 p-2">
								<Loader2 className="h-5 w-5 animate-spin text-gray-600" />
							</div>
						) : isAuthenticated ? (
							<div className="rounded-[4px] border border-emerald-200 bg-gray-50 p-2">
								<CheckCircle className="h-5 w-5 text-emerald-700" />
							</div>
						) : (
							<div className="rounded-[4px] border border-amber-200 bg-gray-50 p-2">
								<AlertCircle className="h-5 w-5 text-amber-800" />
							</div>
						)}
						<div>
							<p
								className={`text-sm font-medium ${isAuthenticated ? "text-emerald-900" : "text-amber-900"}`}
							>
								{statusLoading
									? "Checking connection..."
									: isAuthenticated
										? "Connected to Notion"
										: "Not connected"}
							</p>
							{isAuthenticated && oauthStatus?.expires_at && (
								<p className="mt-0.5 text-[10px] text-gray-600">
									Token expires:{" "}
									{new Date(oauthStatus.expires_at).toLocaleString()}
								</p>
							)}
						</div>
					</div>

					{!statusLoading &&
						(isAuthenticated ? (
							<Button
								onClick={handleDisconnect}
								disabled={isDisconnecting}
								variant="danger"
								size="sm"
								icon={
									isDisconnecting ? (
										<Loader2 className="w-4 h-4 animate-spin" />
									) : (
										<Unlink className="w-4 h-4" />
									)
								}
							>
								Disconnect
							</Button>
						) : (
							<Button
								onClick={handleConnect}
								disabled={isConnecting}
								size="sm"
								icon={
									isConnecting ? (
										<Loader2 className="w-4 h-4 animate-spin" />
									) : (
										<Link2 className="w-4 h-4" />
									)
								}
							>
								{isConnecting ? "Connecting..." : "Connect"}
							</Button>
						))}
				</div>
			</div>

			{/* Configuration Fields */}
			{isAuthenticated && (
				<div className="grid grid-cols-1 gap-4 rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm sm:grid-cols-2">
					{/* Description */}
					<div>
						<label className="mb-2 block text-xs font-medium text-gray-800">
							Description
						</label>
						<textarea
							value={description}
							onChange={(e) => setDescription(e.target.value)}
							placeholder="Describe what this Notion integration will be used for..."
							className="w-full resize-none rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
							rows={2}
						/>
					</div>

					{/* Workspace Label */}
					<div>
						<label className="mb-2 block text-xs font-medium text-gray-800">
							Workspace Label (Optional)
						</label>
						<input
							type="text"
							value={workspaceLabel}
							onChange={(e) => setWorkspaceLabel(e.target.value)}
							placeholder="e.g., My Company Workspace"
							className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
						/>
						<p className="mt-1 text-[10px] text-gray-600">
							Optional label to help identify this workspace in your workflows
						</p>
					</div>
				</div>
			)}

			{/* Test Connection Card */}
			{isAuthenticated && (
				<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
					<div className="mb-3 flex items-center justify-between">
						<div>
							<h4 className="text-sm font-medium text-gray-900">
								Test Connection
							</h4>
							<p className="text-[10px] text-gray-600">
								Verify Notion MCP access
							</p>
						</div>
						<Button
							onClick={handleTestConnection}
							disabled={testStatus === "testing"}
							variant={
								testStatus === "success"
									? "success"
									: testStatus === "error"
										? "danger"
										: "primary"
							}
							size="sm"
							icon={
								testStatus === "testing" ? (
									<Loader2 className="w-4 h-4 animate-spin" />
								) : testStatus === "success" ? (
									<CheckCircle className="w-4 h-4" />
								) : testStatus === "error" ? (
									<AlertCircle className="w-4 h-4" />
								) : undefined
							}
						>
							{testStatus === "testing"
								? "Testing..."
								: testStatus === "success"
									? "Success"
									: testStatus === "error"
										? "Failed"
										: "Test"}
						</Button>
					</div>

					{testMessage && (
						<div
							className={`rounded-[4px] border p-3 text-xs ${
								testStatus === "success"
									? "border-emerald-200 bg-emerald-50 text-emerald-900"
									: testStatus === "error"
										? "border-red-200 bg-red-50 text-red-900"
										: "border-gray-200 bg-white text-gray-700"
							}`}
						>
							{testMessage}
						</div>
					)}
				</div>
			)}

			{/* Discovered Tools */}
			{discoveredTools.length > 0 && (
				<McpToolSelectionCard
					tools={discoveredTools}
					toolPermissions={toolPermissions}
					onToolPermissionsChange={handleToolPermissionsChange}
					providerColor="#00a3bf"
					providerColorRgb="0, 163, 191"
					providerIcon={NotionIcon}
					serverName="Notion"
				/>
			)}

			{/* Not connected message */}
			{!isAuthenticated && !statusLoading && (
				<div className="text-center py-4">
					<p className="text-xs text-gray-600">
						Connect to Notion to configure this integration
					</p>
				</div>
			)}
		</div>
	);
}
