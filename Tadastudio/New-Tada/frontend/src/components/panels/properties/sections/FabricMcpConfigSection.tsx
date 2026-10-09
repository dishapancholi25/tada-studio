"use client";

import {
	AlertCircle,
	CheckCircle,
	ExternalLink,
	Eye,
	EyeOff,
	Info,
	Key,
	Link2,
	Loader2,
	Unlink,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import type { McpToolInfo } from "@/components/dialogs/McpToolsViewerModal";
import { FabricIcon } from "@/components/icons/McpProviderIcons";
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

interface FabricMcpConfig {
	server_name: string;
	connection_type: "stdio";
	command: string;
	args: string[];
	auth_type: "oauth";
	auth_config: {
		provider: "fabric";
	};
	provider?: string;
	description?: string;
	tool_permissions?: Record<string, boolean>;
}

interface FabricMcpConfigSectionProps {
	config: FabricMcpConfig | null;
	onConfigChange: (config: FabricMcpConfig) => void;
	isConfigured: boolean;
	onAuthStatusChange?: (isAuthenticated: boolean) => void;
}

export default function FabricMcpConfigSection({
	config,
	onConfigChange,
	isConfigured,
	onAuthStatusChange,
}: FabricMcpConfigSectionProps) {
	const [authMode, setAuthMode] = useState<"oauth" | "token">("oauth");
	const [manualToken, setManualToken] = useState("");
	const [sqlToken, setSqlToken] = useState("");
	const [showToken, setShowToken] = useState(false);
	const [showSqlToken, setShowSqlToken] = useState(false);
	const [tokenSaving, setTokenSaving] = useState(false);
	const [oauthStatus, setOauthStatus] = useState<OAuthStatus | null>(null);
	const [isConnecting, setIsConnecting] = useState(false);
	const [isDisconnecting, setIsDisconnecting] = useState(false);
	const [testStatus, setTestStatus] = useState<
		"idle" | "testing" | "success" | "error"
	>("idle");
	const [testMessage, setTestMessage] = useState("");
	const [statusLoading, setStatusLoading] = useState(true);
	const [discoveredTools, setDiscoveredTools] = useState<McpToolInfo[]>([]);
	const [toolPermissions, setToolPermissions] = useState<
		Record<string, boolean>
	>(config?.tool_permissions || {});

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
			const response = await fetch(
				`${apiBaseUrl}/api/microsoft-oauth/status?provider=fabric`,
				{
					method: "GET",
					credentials: "include",
				},
			);

			if (response.ok) {
				const data = await response.json();
				setOauthStatus(data);
			} else {
				setOauthStatus(null);
			}
		} catch (error) {
			console.error("Error checking Fabric OAuth status:", error);
			setOauthStatus(null);
		} finally {
			setStatusLoading(false);
		}
	};

	const updateConfig = useCallback(() => {
		const newConfig: FabricMcpConfig = {
			server_name: "Microsoft Fabric MCP",
			connection_type: "stdio",
			command: "python",
			args: ["-m", "backend.tools.fabric_mcp"],
			auth_type: "oauth",
			auth_config: { provider: "fabric" },
			provider: "fabric",
			description:
				"Microsoft Fabric MCP Server for workspaces, lakehouses, notebooks, and pipelines",
		};
		onConfigChange(newConfig);
	}, [onConfigChange]);

	const handleConnect = async () => {
		setIsConnecting(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const response = await fetch(
				`${apiBaseUrl}/api/microsoft-oauth/initiate?provider=fabric`,
				{
					method: "POST",
					credentials: "include",
				},
			);

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || "Failed to initiate OAuth");
			}

			const data = await response.json();
			const { authorization_url } = data;

			const popup = window.open(
				authorization_url,
				"fabric_oauth",
				"width=600,height=700,left=200,top=100",
			);

			const handleMessage = (event: MessageEvent) => {
				if (event.data?.type === "microsoft_oauth_complete") {
					window.removeEventListener("message", handleMessage);
					popup?.close();
					setIsConnecting(false);

					if (event.data.success) {
						checkOAuthStatus();
						setTestStatus("idle");
						setTestMessage("");
						updateConfig();
					} else {
						setTestStatus("error");
						setTestMessage(
							event.data.error || "OAuth authorization failed",
						);
					}
				}
			};

			window.addEventListener("message", handleMessage);

			const checkPopupClosed = setInterval(() => {
				if (popup?.closed) {
					clearInterval(checkPopupClosed);
					window.removeEventListener("message", handleMessage);
					setIsConnecting(false);
					checkOAuthStatus();
				}
			}, 500);
		} catch (error) {
			console.error("Error initiating Fabric OAuth:", error);
			setIsConnecting(false);
			setTestStatus("error");
			setTestMessage(
				error instanceof Error
					? error.message
					: "Failed to connect to Microsoft",
			);
		}
	};

	const handleDisconnect = async () => {
		setIsDisconnecting(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const response = await fetch(
				`${apiBaseUrl}/api/microsoft-oauth/revoke?provider=fabric`,
				{
					method: "DELETE",
					credentials: "include",
				},
			);

			if (response.ok) {
				setOauthStatus(null);
				setTestStatus("idle");
				setTestMessage("");
			} else {
				const error = await response.json();
				throw new Error(error.detail || "Failed to disconnect");
			}
		} catch (error) {
			console.error("Error disconnecting Fabric:", error);
		} finally {
			setIsDisconnecting(false);
		}
	};

	const handleSaveManualToken = async () => {
		if (!manualToken.trim()) return;
		setTokenSaving(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();

			// Store the Fabric REST API token
			const response = await fetch(
				`${apiBaseUrl}/api/microsoft-oauth/store-token`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					credentials: "include",
					body: JSON.stringify({
						access_token: manualToken.trim(),
						provider: "fabric",
					}),
				},
			);

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || "Failed to store API token");
			}

			// Store the SQL token if provided
			if (sqlToken.trim()) {
				const sqlResponse = await fetch(
					`${apiBaseUrl}/api/microsoft-oauth/store-token`,
					{
						method: "POST",
						headers: { "Content-Type": "application/json" },
						credentials: "include",
						body: JSON.stringify({
							access_token: sqlToken.trim(),
							provider: "fabric_sql",
						}),
					},
				);

				if (!sqlResponse.ok) {
					const error = await sqlResponse.json();
					throw new Error(
						error.detail || "Failed to store SQL token",
					);
				}
			}

			await checkOAuthStatus();
			setTestStatus("idle");
			setTestMessage("");
			updateConfig();
		} catch (error) {
			setTestStatus("error");
			setTestMessage(
				error instanceof Error
					? error.message
					: "Failed to store token",
			);
		} finally {
			setTokenSaving(false);
		}
	};

	const handleToolPermissionsChange = useCallback(
		(permissions: Record<string, boolean>) => {
			setToolPermissions(permissions);
			onConfigChange({ tool_permissions: permissions } as any);
		},
		[onConfigChange],
	);

	const handleTestConnection = async () => {
		setTestStatus("testing");
		setTestMessage("Testing Fabric API connection...");
		setDiscoveredTools([]);

		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const response = await fetch(
				`${apiBaseUrl}/api/microsoft-oauth/test?provider=fabric`,
				{
					method: "POST",
					credentials: "include",
				},
			);

			const result = await response.json();

			if (result.status === "success") {
				setTestStatus("success");
				setTestMessage(result.message);

				// Also discover tools via the MCP server test
				try {
					const mcpResponse = await fetch(
						"/api/graph/test-mcp-server",
						{
							method: "POST",
							headers: { "Content-Type": "application/json" },
							body: JSON.stringify({
								server_name: "Microsoft Fabric MCP",
								connection_type: "stdio",
								command: "python",
								args: ["-m", "backend.tools.fabric_mcp"],
								auth_type: "none",
							}),
						},
					);

					const mcpResult = await mcpResponse.json();
					if (mcpResult.success && mcpResult.capabilities?.tools) {
						const tools: McpToolInfo[] =
							mcpResult.capabilities.tools.map(
								(tool: {
									name?: string;
									description?: string;
									input_schema?: Record<string, unknown>;
								}) => ({
									name: tool.name || "Unknown Tool",
									description:
										tool.description ||
										"No description available",
									input_schema:
										tool.input_schema || undefined,
								}),
							);
						setDiscoveredTools(tools);
					}
				} catch {
					// Tool discovery is non-critical
				}
			} else {
				setTestStatus("error");
				setTestMessage(result.message || "Connection test failed");
			}
		} catch (error) {
			setTestStatus("error");
			setTestMessage(
				`Connection test failed: ${error instanceof Error ? error.message : "Unknown error"}`,
			);
		}
	};

	const isAuthenticated = oauthStatus?.is_authenticated ?? false;

	return (
		<div className="space-y-5">
			{/* Section Label */}
			<div className="text-[0.6rem] font-semibold capitalize text-gray-600">
				Microsoft Fabric Configuration
			</div>

			{/* Info Card */}
			<div className="rounded-[4px] border border-teal-600/30 bg-white p-4 shadow-sm">
				<div className="flex items-start gap-3">
					<div className="rounded-[4px] border border-teal-600/25 bg-gray-50 p-2">
						<Info className="h-4 w-4 text-teal-800" />
					</div>
					<div className="flex-1">
						<h4 className="mb-1 text-sm font-medium text-teal-900">
							About Microsoft Fabric MCP
						</h4>
						<p className="mb-2 text-xs text-gray-600">
							Connect your Microsoft account to access 57+ Fabric
							tools including workspaces, lakehouses, notebooks,
							pipelines, semantic models, and more.
						</p>
						<a
							href="https://github.com/bablulawrence/ms-fabric-mcp-server"
							target="_blank"
							rel="noopener noreferrer"
							className="flex items-center gap-1 text-xs text-teal-900 transition-colors hover:text-slate-900"
						>
							View on GitHub
							<ExternalLink className="w-3 h-3" />
						</a>
					</div>
				</div>
			</div>

			{/* Auth Mode Tabs */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
				<div className="mb-4 flex gap-2">
					<button
						type="button"
						onClick={() => setAuthMode("oauth")}
						className={`flex-1 rounded-[4px] border px-3 py-1.5 text-xs font-medium transition-colors ${
							authMode === "oauth"
								? "border-teal-600 bg-gray-100 text-teal-900"
								: "border-gray-200 bg-white text-gray-600 hover:border-orange-300 hover:text-slate-900"
						}`}
					>
						<Link2 className="mr-1.5 inline h-3 w-3" />
						OAuth Sign-In
					</button>
					<button
						type="button"
						onClick={() => setAuthMode("token")}
						className={`flex-1 rounded-[4px] border px-3 py-1.5 text-xs font-medium transition-colors ${
							authMode === "token"
								? "border-teal-600 bg-gray-100 text-teal-900"
								: "border-gray-200 bg-white text-gray-600 hover:border-orange-300 hover:text-slate-900"
						}`}
					>
						<Key className="mr-1.5 inline h-3 w-3" />
						Manual Token
					</button>
				</div>

				{authMode === "oauth" ? (
					<>
						<div className="mb-3 flex items-center justify-between">
							<div>
								<h4 className="text-sm font-medium text-gray-900">
									Microsoft Account
								</h4>
								<p className="text-[10px] text-gray-600">
									{isAuthenticated
										? "Connected — Fabric API access granted"
										: "Sign in to grant Fabric API access"}
								</p>
							</div>
							{isAuthenticated ? (
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
									{isDisconnecting
										? "Disconnecting..."
										: "Disconnect"}
								</Button>
							) : (
								<Button
									onClick={handleConnect}
									disabled={isConnecting || statusLoading}
									variant="primary"
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
							)}
						</div>

						{isAuthenticated && oauthStatus?.expires_at && (
							<div className="rounded-[4px] border border-gray-200 bg-gray-50 px-3 py-1.5 text-[10px] text-gray-700">
								Token expires:{" "}
								{new Date(
									oauthStatus.expires_at,
								).toLocaleString()}
							</div>
						)}
					</>
				) : (
					<>
						<p className="mb-3 text-xs text-gray-600">
							Run these commands in your terminal:
						</p>
						<div className="mb-3 rounded-[4px] border border-gray-200 bg-gray-100 p-2.5 font-mono text-[11px] leading-relaxed text-gray-900">
							<div>az login</div>
							<div className="mt-1 text-gray-600">
								<span className="text-teal-800"># API token</span>
							</div>
							<div>
								az account get-access-token --resource
								https://api.fabric.microsoft.com --query
								accessToken -o tsv
							</div>
							<div className="mt-1 text-gray-600">
								<span className="text-teal-800"># SQL token (for warehouse/lakehouse queries)</span>
							</div>
							<div>
								az account get-access-token --resource
								https://database.windows.net --query
								accessToken -o tsv
							</div>
						</div>
						<label className="mb-2 block text-xs font-medium text-gray-800">
							Fabric API Token
						</label>
						<div className="relative mb-3">
							<input
								type={showToken ? "text" : "password"}
								value={manualToken}
								onChange={(e) => setManualToken(e.target.value)}
								className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 pr-12 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								placeholder="eyJ0eXAiOiJKV1Qi..."
							/>
							<button
								type="button"
								onClick={() => setShowToken((p) => !p)}
								className="absolute right-3 top-1/2 -translate-y-1/2 transform text-gray-600 transition-colors hover:text-slate-900"
							>
								{showToken ? (
									<EyeOff className="w-4 h-4" />
								) : (
									<Eye className="w-4 h-4" />
								)}
							</button>
						</div>
						<label className="mb-2 mt-3 block text-xs font-medium text-gray-800">
							SQL Token{" "}
							<span className="font-normal text-gray-600">
								(optional — for warehouse/lakehouse queries)
							</span>
						</label>
						<div className="relative mb-3">
							<input
								type={showSqlToken ? "text" : "password"}
								value={sqlToken}
								onChange={(e) => setSqlToken(e.target.value)}
								className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 pr-12 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								placeholder="eyJ0eXAiOiJKV1Qi..."
							/>
							<button
								type="button"
								onClick={() => setShowSqlToken((p) => !p)}
								className="absolute right-3 top-1/2 -translate-y-1/2 transform text-gray-600 transition-colors hover:text-slate-900"
							>
								{showSqlToken ? (
									<EyeOff className="w-4 h-4" />
								) : (
									<Eye className="w-4 h-4" />
								)}
							</button>
						</div>
						<Button
							onClick={handleSaveManualToken}
							disabled={
								tokenSaving || !manualToken.trim()
							}
							variant="primary"
							size="sm"
							icon={
								tokenSaving ? (
									<Loader2 className="w-4 h-4 animate-spin" />
								) : (
									<CheckCircle className="w-4 h-4" />
								)
							}
						>
							{tokenSaving ? "Saving..." : "Save Token"}
						</Button>

						{isAuthenticated && (
							<div className="mt-3 rounded-[4px] border border-[#0DA931] bg-[#F1F8E9] px-3 py-1.5 text-[10px] text-[#0DA931]">
								Token saved and active
								{oauthStatus?.expires_at &&
									` — expires ${new Date(oauthStatus.expires_at).toLocaleString()}`}
							</div>
						)}
					</>
				)}
			</div>

			{/* Test Connection Card */}
			{isAuthenticated && (
				<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
					<div className="mb-4 flex items-center justify-between">
						<div>
							<h4 className="text-sm font-medium text-gray-900">
								Connection Test
							</h4>
							<p className="text-[10px] text-gray-600">
								Verify Fabric API access and discover tools
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
									? "Connected"
									: testStatus === "error"
										? "Failed"
										: "Test Connection"}
						</Button>
					</div>

					{testMessage && (
						<div
							className={`mb-3 rounded-[4px] border p-3 text-xs ${
								testStatus === "success"
									? "border-[#0DA931] bg-[#F1F8E9] text-[#0DA931]"
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
					providerColor="#2AAC94"
					providerColorRgb="42, 172, 148"
					providerIcon={FabricIcon}
					serverName="Microsoft Fabric"
				/>
			)}
		</div>
	);
}
