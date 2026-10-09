"use client";

import {
	AlertCircle,
	CheckCircle,
	ExternalLink,
	FolderTree,
	Info,
	Library,
	Link2,
	Loader2,
	MapPin,
	Unlink,
	X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import type { McpToolInfo } from "@/components/dialogs/McpToolsViewerModal";
import { OneDriveIcon } from "@/components/icons/McpProviderIcons";
import { runtimeConfig } from "@/lib/runtime-config";
import McpToolSelectionCard from "./McpToolSelectionCard";
import SearchablePicker from "./SearchablePicker";
import SharePointFolderTree from "./SharePointFolderTree";

interface OAuthStatus {
	is_authenticated: boolean;
	has_token: boolean;
	has_client_registration: boolean;
	token_expired: boolean;
	expires_at: string | null;
	scope: string | null;
}

interface OneDriveDrive {
	id: string;
	name: string;
	description: string;
	web_url: string;
	drive_type: string;
	is_default: boolean;
}

interface OneDriveMcpConfig {
	server_name: string;
	connection_type: "stdio";
	command: string;
	args: string[];
	auth_type: "oauth";
	auth_config: {
		provider: "microsoft";
	};
	environment_variables?: Record<string, string>;
	provider?: string;
	description?: string;
	metadata?: {
		drive_id?: string;
		drive_name?: string;
		folder_paths?: string;
	};
	tool_permissions?: Record<string, boolean>;
}

interface OneDriveMcpConfigSectionProps {
	config: OneDriveMcpConfig | null;
	onConfigChange: (config: OneDriveMcpConfig) => void;
	isConfigured: boolean;
	onAuthStatusChange?: (isAuthenticated: boolean) => void;
}

export default function OneDriveMcpConfigSection({
	config,
	onConfigChange,
	isConfigured,
	onAuthStatusChange,
}: OneDriveMcpConfigSectionProps) {
	// OAuth state
	const [oauthStatus, setOauthStatus] = useState<OAuthStatus | null>(null);
	const [isConnecting, setIsConnecting] = useState(false);
	const [isDisconnecting, setIsDisconnecting] = useState(false);
	const [statusLoading, setStatusLoading] = useState(true);

	// Drive picker state
	const [drives, setDrives] = useState<OneDriveDrive[]>([]);
	const [drivesLoading, setDrivesLoading] = useState(false);
	const [selectedDriveId, setSelectedDriveId] = useState(
		config?.metadata?.drive_id || config?.environment_variables?.ONEDRIVE_DRIVE_ID || "",
	);
	const [selectedDriveName, setSelectedDriveName] = useState(
		config?.metadata?.drive_name || "",
	);

	// Folder tree state
	const [selectedFolderIds, setSelectedFolderIds] = useState<Set<string>>(new Set());
	const [selectedFolderPaths, setSelectedFolderPaths] = useState<string[]>(
		config?.metadata?.folder_paths ? config.metadata.folder_paths.split(",").filter(Boolean) : [],
	);

	// Test & tools state
	const [testStatus, setTestStatus] = useState<
		"idle" | "testing" | "success" | "error"
	>("idle");
	const [testMessage, setTestMessage] = useState("");
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
			const response = await fetch(
				`${apiBaseUrl}/api/microsoft-oauth/status`,
				{ method: "GET", credentials: "include" },
			);
			if (response.ok) {
				const data = await response.json();
				setOauthStatus(data);
			} else {
				setOauthStatus(null);
			}
		} catch {
			setOauthStatus(null);
		} finally {
			setStatusLoading(false);
		}
	};

	// Load drives when authenticated
	useEffect(() => {
		if (oauthStatus?.is_authenticated) {
			loadDrives();
		}
	}, [oauthStatus?.is_authenticated]);

	const loadDrives = async () => {
		setDrivesLoading(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const resp = await fetch(
				`${apiBaseUrl}/api/microsoft-oauth/onedrive/drives`,
				{ credentials: "include" },
			);
			if (resp.ok) {
				const data = await resp.json();
				setDrives(data.drives || []);
				// Auto-select default drive if none selected
				if (!selectedDriveId && data.drives?.length > 0) {
					const defaultDrive = data.drives.find((d: OneDriveDrive) => d.is_default) || data.drives[0];
					setSelectedDriveId(defaultDrive.id);
					setSelectedDriveName(defaultDrive.name);
				}
			}
		} catch {
			// Silently fail
		} finally {
			setDrivesLoading(false);
		}
	};

	const handleConnect = async () => {
		setIsConnecting(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const response = await fetch(
				`${apiBaseUrl}/api/microsoft-oauth/initiate`,
				{ method: "POST", credentials: "include" },
			);
			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || "Failed to initiate OAuth");
			}
			const data = await response.json();
			const popup = window.open(
				data.authorization_url,
				"microsoft_oauth",
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
					} else {
						setTestStatus("error");
						setTestMessage(event.data.error || "OAuth authorization failed");
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
			setIsConnecting(false);
			setTestStatus("error");
			setTestMessage(
				error instanceof Error ? error.message : "Failed to connect to Microsoft",
			);
		}
	};

	const handleDisconnect = async () => {
		setIsDisconnecting(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const response = await fetch(
				`${apiBaseUrl}/api/microsoft-oauth/revoke`,
				{ method: "DELETE", credentials: "include" },
			);
			if (response.ok) {
				setOauthStatus(null);
				setTestStatus("idle");
				setTestMessage("");
			}
		} catch {
			// Silently fail
		} finally {
			setIsDisconnecting(false);
			checkOAuthStatus();
		}
	};

	const handleTestConnection = async () => {
		if (!oauthStatus?.is_authenticated) {
			setTestStatus("error");
			setTestMessage("Please connect to Microsoft first");
			return;
		}
		setTestStatus("testing");
		setTestMessage("");
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const response = await fetch(
				`${apiBaseUrl}/api/microsoft-oauth/test`,
				{ method: "POST", credentials: "include" },
			);
			const data = await response.json();
			if (data.status === "success") {
				setTestStatus("success");
				setTestMessage(data.message);
				try {
					const envVars = buildEnvVars();
					const discoverResponse = await fetch(
						`${apiBaseUrl}/api/graph/test-mcp-server`,
						{
							method: "POST",
							headers: { "Content-Type": "application/json" },
							credentials: "include",
							body: JSON.stringify({
								server_name: "OneDrive MCP Server",
								connection_type: "stdio",
								command: "python",
								args: ["-m", "backend.tools.onedrive_mcp"],
								auth_type: "oauth",
								auth_config: { provider: "microsoft" },
								environment_variables: envVars,
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
					// Non-critical
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

	const buildEnvVars = useCallback(() => {
		const env: Record<string, string> = {};
		if (selectedDriveId) env.ONEDRIVE_DRIVE_ID = selectedDriveId;
		if (selectedFolderPaths.length > 0) {
			env.ONEDRIVE_FOLDER_PATHS = selectedFolderPaths.join(",");
		}
		return env;
	}, [selectedDriveId, selectedFolderPaths]);

	const updateConfig = useCallback(() => {
		const envVars = buildEnvVars();
		const newConfig: OneDriveMcpConfig = {
			server_name: "OneDrive MCP Server",
			connection_type: "stdio",
			command: "python",
			args: ["-m", "backend.tools.onedrive_mcp"],
			auth_type: "oauth",
			auth_config: { provider: "microsoft" },
			provider: "onedrive",
			description: "OneDrive integration for personal and shared file access",
			environment_variables: envVars,
			metadata: {
				drive_id: selectedDriveId,
				drive_name: selectedDriveName,
				folder_paths: selectedFolderPaths.join(","),
			},
		};
		onConfigChange(newConfig);
	}, [buildEnvVars, onConfigChange, selectedDriveId, selectedDriveName, selectedFolderPaths]);

	useEffect(() => {
		if (oauthStatus?.is_authenticated) {
			updateConfig();
		}
	}, [selectedDriveId, selectedFolderPaths, oauthStatus?.is_authenticated, updateConfig]);

	const handleDriveChange = (driveId: string) => {
		const drive = drives.find((d) => d.id === driveId);
		setSelectedDriveId(driveId);
		setSelectedDriveName(drive?.name || "");
		setSelectedFolderIds(new Set());
		setSelectedFolderPaths([]);
	};

	const handleFolderSelectionChange = (ids: Set<string>, paths: string[]) => {
		setSelectedFolderIds(ids);
		setSelectedFolderPaths(paths);
	};

	const handleToolPermissionsChange = useCallback(
		(permissions: Record<string, boolean>) => {
			setToolPermissions(permissions);
			onConfigChange({ tool_permissions: permissions } as any);
		},
		[onConfigChange],
	);

	const isAuthenticated = oauthStatus?.is_authenticated ?? false;

	const scopeSummary = (() => {
		const parts: string[] = [];
		if (selectedDriveName) parts.push(selectedDriveName);
		if (selectedFolderPaths.length > 0) {
			parts.push(`${selectedFolderPaths.length} folder(s)`);
		}
		return parts.length > 0 ? parts.join(" / ") : "All files";
	})();

	return (
		<div className="space-y-5">
			<div className="text-[0.6rem] font-semibold capitalize text-gray-600">
				OneDrive Configuration
			</div>

			{/* Info Card */}
			<div className="rounded-[4px] border border-blue-200 bg-white p-4 shadow-sm">
				<div className="flex items-start gap-3">
					<div className="rounded-[4px] border border-blue-200 bg-gray-50 p-2">
						<Info className="h-4 w-4 text-blue-800" />
					</div>
					<div className="flex-1">
						<h4 className="mb-1 text-sm font-medium text-blue-900">
							About OneDrive MCP
						</h4>
						<p className="mb-2 text-xs text-gray-600">
							Connect to OneDrive using your Microsoft account.
							Select a drive and folders to scope what the agent
							can search and access.
						</p>
						<a
							href="https://learn.microsoft.com/en-us/graph/onedrive-concept-overview"
							target="_blank"
							rel="noopener noreferrer"
							className="flex items-center gap-1 text-xs text-blue-900 transition-colors hover:text-slate-900"
						>
							Learn more about OneDrive Graph API
							<ExternalLink className="w-3 h-3" />
						</a>
					</div>
				</div>
			</div>

			{/* OAuth Connection Status Card */}
			<div
				className={`rounded-[4px] border bg-white p-4 shadow-sm ${
					isAuthenticated ? "border-[#0DA931]" : "border-amber-300"
				}`}
			>
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-3">
						{statusLoading ? (
							<div className="rounded-[4px] border border-gray-200 bg-gray-50 p-2">
								<Loader2 className="h-5 w-5 animate-spin text-gray-600" />
							</div>
						) : isAuthenticated ? (
							<div className="rounded-[4px] border border-[#0DA931] bg-[#F1F8E9] p-2">
								<CheckCircle className="h-5 w-5 text-[#0DA931]" />
							</div>
						) : (
							<div className="rounded-[4px] border border-amber-200 bg-gray-50 p-2">
								<AlertCircle className="h-5 w-5 text-amber-800" />
							</div>
						)}
						<div>
							<p
								className={`text-sm font-medium ${isAuthenticated ? "text-[#0DA931]" : "text-amber-900"}`}
							>
								{statusLoading
									? "Checking connection..."
									: isAuthenticated
										? "Connected to Microsoft"
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

			{/* Scope Configuration */}
			{isAuthenticated && (
				<div className="space-y-4 rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
					<div className="flex items-center gap-2">
						<MapPin className="h-3.5 w-3.5 text-blue-800" />
						<span className="text-xs font-medium text-gray-800">
							Search Scope
						</span>
					</div>

					{/* Drive Picker */}
					<div>
						<label className="mb-2 flex items-center gap-1.5 text-xs font-medium text-gray-800">
							<Library className="w-3 h-3" />
							OneDrive
						</label>
						<SearchablePicker
							value={selectedDriveId}
							onChange={handleDriveChange}
							options={drives.map((d) => ({
								value: d.id,
								label: d.name + (d.is_default ? " (default)" : ""),
								description: d.description || d.drive_type,
							}))}
							placeholder="Default drive"
							searchPlaceholder="Search drives..."
							emptyMessage="No drives found"
							loading={drivesLoading}
							loadingMessage="Loading drives..."
						/>
					</div>

					{/* Folder Tree */}
					{selectedDriveId && (
						<div>
							<label className="mb-2 flex items-center gap-1.5 text-xs font-medium text-gray-800">
								<FolderTree className="w-3 h-3" />
								Scope to Folders
								<span className="text-[10px] font-normal text-gray-600">
									(optional)
								</span>
							</label>
							<div className="overflow-hidden rounded-[4px] border border-gray-200 bg-gray-50">
								<SharePointFolderTree
									driveId={selectedDriveId}
									selectedFolderIds={selectedFolderIds}
									onSelectionChange={handleFolderSelectionChange}
									apiBasePath="/api/microsoft-oauth/onedrive"
								/>
							</div>
							{selectedFolderPaths.length > 0 && (
								<div className="mt-2 flex flex-wrap gap-1.5">
									{selectedFolderPaths.map((path) => {
										const folderName = path.split("/").filter(Boolean).pop() || path;
										return (
											<span
												key={path}
												className="inline-flex items-center gap-1 rounded-[4px] border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] text-blue-900"
											>
												{folderName}
												<button
													type="button"
													onClick={() => {
														const newPaths = selectedFolderPaths.filter((p) => p !== path);
														setSelectedFolderPaths(newPaths);
														setSelectedFolderIds(new Set());
													}}
													className="hover:text-slate-900 transition-colors"
												>
													<X className="w-2.5 h-2.5" />
												</button>
											</span>
										);
									})}
								</div>
							)}
							<p className="mt-1 text-[10px] text-gray-600">
								Select folders to narrow the agent&apos;s search scope.
								Leave empty to search the entire drive.
							</p>
						</div>
					)}

					{/* Scope summary */}
					<div className="border-t border-gray-200 pt-2">
						<p className="text-[10px] text-gray-600">
							<span className="font-medium">Scope:</span> {scopeSummary}
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
								Verify Microsoft Graph API access
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
					providerColor="#0078D4"
					providerColorRgb="0, 120, 212"
					providerIcon={OneDriveIcon}
					serverName="OneDrive"
				/>
			)}

			{/* Not connected message */}
			{!isAuthenticated && !statusLoading && (
				<div className="text-center py-4">
					<p className="text-xs text-gray-600">
						Connect to Microsoft to configure OneDrive access
					</p>
				</div>
			)}
		</div>
	);
}
