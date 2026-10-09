"use client";

import { AlertCircle, CheckCircle, Loader2, Save, Settings, ShieldCheck, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
	getProviderVisuals,
} from "@/components/icons/McpProviderIcons";
import type { McpToolInfo } from "@/components/dialogs/McpToolsViewerModal";
import Button from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { runtimeConfig } from "@/lib/runtime-config";
import ConfigSidebar from "./ConfigSidebar";
import McpToolSelectionCard from "./sections/McpToolSelectionCard";
import DatabricksMcpConfigSection from "./sections/DatabricksMcpConfigSection";
import GitHubMcpConfigSection from "./sections/GitHubMcpConfigSection";
import NotionMcpConfigSection from "./sections/NotionMcpConfigSection";
import AtlassianMcpConfigSection from "./sections/AtlassianMcpConfigSection";
import SharePointMcpConfigSection from "./sections/SharePointMcpConfigSection";
import DatabricksDevOpsMcpConfigSection from "./sections/DatabricksDevOpsMcpConfigSection";
import OneDriveMcpConfigSection from "./sections/OneDriveMcpConfigSection";
import FabricMcpConfigSection from "./sections/FabricMcpConfigSection";
import ToolGuardrailsSection from "@/components/core/guardrails/ToolGuardrailsSection";

interface MCPServerConfig {
	provider?: string;
	server_name?: string;
	connection_type?: string;
	server_url?: string;
	command?: string;
	args?: string[];
	auth_type?: string;
	auth_config?: Record<string, string>;
	environment_variables?: Record<string, string>;
	timeout_seconds?: number;
	sse_timeout_seconds?: number;
	max_retries?: number;
	retry_delay?: number;
	parent_agent_id?: string;
	description?: string;
	workspace_label?: string;
	metadata?: Record<string, string>;
	tool_permissions?: Record<string, boolean>;
}

interface McpServerNodeData {
	id: string;
	name: string;
	mcp_server_config?: MCPServerConfig;
	isConfigured?: boolean;
}

interface McpServerPropertiesPanelProps {
	node: {
		id: string;
		data: McpServerNodeData;
		position?: { x: number; y: number };
	};
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
}

type McpServerTabId = "configuration" | "guardrails";

export default function McpServerPropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}: McpServerPropertiesPanelProps) {
	const config = node.data.mcp_server_config || {};
	const provider = config.provider || "";
	const providerVisuals = getProviderVisuals(provider);

	// Track if configuration has been modified
	const [hasChanges, setHasChanges] = useState(false);
	const [currentConfig, setCurrentConfig] = useState<MCPServerConfig>(config);
	const [activeTab, setActiveTab] = useState<McpServerTabId>("configuration");
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
	// Track actual OAuth status for providers that use OAuth
	const [notionOAuthStatus, setNotionOAuthStatus] = useState(false);
	const [atlassianOAuthStatus, setAtlassianOAuthStatus] = useState(false);
	const [sharepointOAuthStatus, setSharepointOAuthStatus] = useState(false);
	const [onedriveOAuthStatus, setOnedriveOAuthStatus] = useState(false);
	const [fabricOAuthStatus, setFabricOAuthStatus] = useState(false);
	// Generic MCP server tool discovery
	const [genericDiscoveredTools, setGenericDiscoveredTools] = useState<McpToolInfo[]>([]);
	const [genericToolPermissions, setGenericToolPermissions] = useState<Record<string, boolean>>(
		config.tool_permissions || {},
	);
	const [genericTestStatus, setGenericTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
	const [genericTestMessage, setGenericTestMessage] = useState("");

	const contentRef = useRef<HTMLDivElement>(null);

	// Responsive sidebar collapse
	useEffect(() => {
		const el = contentRef.current;
		if (!el || typeof ResizeObserver === "undefined") return;
		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				setSidebarCollapsed(entry.contentRect.width < 400);
			}
		});
		observer.observe(el);
		return () => observer.disconnect();
	}, []);

	// Check MCP OAuth status for Atlassian on mount
	useEffect(() => {
		if (provider !== "atlassian") return;
		(async () => {
			try {
				const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
				const res = await fetch(
					`${apiBaseUrl}/api/mcp-oauth/status?server_name=Atlassian`,
					{ credentials: "include" },
				);
				if (res.ok) {
					const data = await res.json();
					setAtlassianOAuthStatus(data.is_authenticated === true);
				}
			} catch (err) {
				console.error("Failed to check Atlassian OAuth status:", err);
			}
		})();
	}, [provider]);

	// Check if provider is configured (uses actual OAuth status for OAuth providers)
	const isConfigured = Boolean(
		(provider === "github" && config.auth_config?.access_token) ||
			(provider === "notion" && notionOAuthStatus) ||
			(provider === "atlassian" && atlassianOAuthStatus) ||
			(provider === "databricks" &&
				config.server_url &&
				(config.auth_config?.access_token || config.auth_config?.client_id)) ||
			(provider === "sharepoint" && sharepointOAuthStatus) ||
			(provider === "onedrive" && onedriveOAuthStatus) ||
			(provider === "databricks_devops" &&
				config.auth_config?.databricks_token &&
				config.auth_config?.devops_pat) ||
			(provider === "fabric" && fabricOAuthStatus) ||
			(!provider && config.connection_type),
	);

	// Handlers
	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleDeleteNode = useCallback(() => {
		onDeleteNode(node.id);
	}, [node.id, onDeleteNode]);

	const handleConfigChange = useCallback((newConfig: any) => {
		setCurrentConfig((prev) => ({ ...prev, ...newConfig }));
		setHasChanges(true);
	}, []);

	const handleGenericToolPermissionsChange = useCallback(
		(permissions: Record<string, boolean>) => {
			setGenericToolPermissions(permissions);
			handleConfigChange({ tool_permissions: permissions });
		},
		[handleConfigChange],
	);

	const handleGenericDiscoverTools = useCallback(async () => {
		setGenericTestStatus("testing");
		setGenericTestMessage("Discovering tools...");
		setGenericDiscoveredTools([]);

		try {
			const testConfig: Record<string, unknown> = {
				server_name: config.server_name || "MCP Server",
				connection_type: config.connection_type,
				server_url: config.server_url,
				command: config.command,
				args: config.args,
				auth_type: config.auth_type || "none",
				auth_config: config.auth_config,
				environment_variables: config.environment_variables,
				timeout_seconds: config.timeout_seconds || 30,
				max_retries: config.max_retries || 3,
			};

			const response = await fetch("/api/graph/test-mcp-server", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(testConfig),
			});

			const result = await response.json();

			if (response.ok && result.success) {
				setGenericTestStatus("success");
				const tools: McpToolInfo[] = (result.capabilities?.tools || []).map(
					(tool: { name?: string; description?: string; input_schema?: Record<string, unknown> }) => ({
						name: tool.name || "Unknown Tool",
						description: tool.description || "No description available",
						input_schema: tool.input_schema || undefined,
					}),
				);
				setGenericDiscoveredTools(tools);
				setGenericTestMessage(`Found ${tools.length} tool${tools.length !== 1 ? "s" : ""}.`);
			} else {
				setGenericTestStatus("error");
				setGenericTestMessage(result.error || "Failed to connect to MCP server");
			}
		} catch (error) {
			setGenericTestStatus("error");
			setGenericTestMessage(
				`Discovery failed: ${error instanceof Error ? error.message : "Unknown error"}`,
			);
		}
	}, [config]);

	const handleSave = useCallback(() => {
		const updateData: any = {
			mcp_server_config: {
				...config,
				...currentConfig,
				parent_agent_id: config.parent_agent_id,
			},
			isConfigured: true,
		};

		// Sync server_name to top-level name fields
		if (currentConfig.server_name) {
			updateData.name = currentConfig.server_name;
			updateData.server_name = currentConfig.server_name;
		}

		// Preserve the current position if it exists
		if (node.position) {
			updateData.position = node.position;
		}

		onUpdateNode(node.id, updateData);
		onClose();
	}, [config, currentConfig, node.id, node.position, onUpdateNode, onClose]);

	// Keyboard shortcut: Cmd/Ctrl+S to save
	const handleSaveRef = useRef(handleSave);
	handleSaveRef.current = handleSave;

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === "s") {
				e.preventDefault();
				handleSaveRef.current();
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, []);

	// Get provider-specific icon
	const ProviderIcon = providerVisuals.icon;

	const panelTabs = useMemo(
		() => [
			{
				id: "configuration" as const,
				label: "Configuration",
				description: "Connection settings",
				icon: <Settings className="h-4 w-4" />,
			},
			{
				id: "guardrails" as const,
				label: "Guardrails",
				description: "Safety policies",
				icon: <ShieldCheck className="h-4 w-4" />,
			},
		],
		[],
	);

	const isGuardrailsTab = activeTab === "guardrails";

	return (
		<div
			className="fixed inset-0 z-[110] flex animate-fadeIn items-start justify-center bg-black/50 px-4 pb-4 pt-[5vh] backdrop-blur-sm"
			onClick={onClose}
		>
			<div
				className="w-[85vw] max-w-[1800px]"
				onClick={handleStopPropagation}
			>
				<div
					className={cn(
						"flex min-h-[320px] flex-col rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]",
						isGuardrailsTab
							? "max-h-[90vh] overflow-visible"
							: "max-h-[80vh] overflow-hidden",
					)}
				>
					<div className="flex-none border-b border-gray-200 bg-white">
						<div className="flex items-center justify-between px-6 py-4">
							<div className="flex min-w-0 items-start gap-3">
								<div
									className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border bg-white shadow-sm"
									style={{
										borderColor: `rgba(${providerVisuals.colorRgb}, 0.35)`,
									}}
								>
									<ProviderIcon
										className="h-5 w-5"
										style={{ color: providerVisuals.color }}
									/>
								</div>
								<div className="min-w-0">
									<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
										Tool configuration
									</p>
									<h2 className="text-lg font-semibold text-gray-900">
										{providerVisuals.label}
									</h2>
									<p className="mt-0.5 text-sm text-gray-600">
										{isConfigured
											? "Configured"
											: "Configure your MCP connection"}
									</p>
								</div>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="shrink-0 rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								aria-label="Close"
							>
								<X className="h-5 w-5" />
							</button>
						</div>
					</div>

					<div
						ref={contentRef}
						className={cn(
							"flex min-h-0 flex-1",
							!isGuardrailsTab && "overflow-hidden",
						)}
					>
						<ConfigSidebar
							items={panelTabs}
							activeItem={activeTab}
							onChange={(id) =>
								setActiveTab(id as McpServerTabId)
							}
							collapsed={sidebarCollapsed}
							variant="light"
						/>

						<div
							className={cn(
								"custom-scrollbar min-h-0 flex-1 space-y-5 bg-slate-50 px-6 py-5",
								isGuardrailsTab ? "overflow-visible" : "overflow-y-auto",
							)}
						>
								{activeTab === "configuration" && (
									<>
										{/* Connection Status Badge */}
										<div
											className={`rounded-[4px] border bg-white p-4 shadow-sm ${
												isConfigured
													? "border-emerald-300"
													: "border-gray-200"
											}`}
										>
											<div className="flex items-center justify-between">
												<div className="flex items-center gap-3">
													{isConfigured ? (
														<div className="rounded-[4px] border border-emerald-200 bg-emerald-50 p-2">
															<CheckCircle className="h-5 w-5 text-emerald-700" />
														</div>
													) : (
														<div className="rounded-[4px] border border-gray-200 bg-white p-2">
															<Settings className="h-5 w-5 text-gray-500" />
														</div>
													)}
													<div>
														<p
															className={`text-sm font-medium ${isConfigured ? "text-emerald-900" : "text-gray-800"}`}
														>
															{isConfigured ? "Connected" : "Not Configured"}
														</p>
														<p className="text-[10px] text-gray-600">
															{isConfigured
																? "Ready to use in your workflows"
																: "Complete the configuration below"}
														</p>
													</div>
												</div>
												{isConfigured && (
													<span className="rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-[11px] font-medium text-emerald-900">
														Active
													</span>
												)}
											</div>
										</div>

										{/* Display Name field for official providers */}
										{provider && (
											<div>
												<label className="mb-2 block text-xs font-medium text-gray-800">
													Display Name
												</label>
												<input
													type="text"
													value={currentConfig.server_name || ""}
													onChange={(e) =>
														handleConfigChange({ server_name: e.target.value })
													}
													placeholder={providerVisuals.label}
													className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
												/>
											</div>
										)}
										{provider === "github" && (
											<GitHubMcpConfigSection
												config={currentConfig as any}
												onConfigChange={handleConfigChange}
												isConfigured={isConfigured}
											/>
										)}
										{provider === "notion" && (
											<NotionMcpConfigSection
												config={currentConfig as any}
												onConfigChange={handleConfigChange}
												isConfigured={isConfigured}
												onAuthStatusChange={setNotionOAuthStatus}
											/>
										)}
										{provider === "databricks" && (
											<DatabricksMcpConfigSection
												config={currentConfig as any}
												onConfigChange={handleConfigChange}
												isConfigured={isConfigured}
											/>
										)}
										{provider === "sharepoint" && (
											<SharePointMcpConfigSection
												config={currentConfig as any}
												onConfigChange={handleConfigChange}
												isConfigured={isConfigured}
												onAuthStatusChange={setSharepointOAuthStatus}
											/>
										)}
										{provider === "onedrive" && (
											<OneDriveMcpConfigSection
												config={currentConfig as any}
												onConfigChange={handleConfigChange}
												isConfigured={isConfigured}
												onAuthStatusChange={setOnedriveOAuthStatus}
											/>
										)}
										{provider === "atlassian" && (
											<AtlassianMcpConfigSection
												config={currentConfig as any}
												onConfigChange={handleConfigChange}
												isConfigured={isConfigured}
												onAuthStatusChange={setAtlassianOAuthStatus}
											/>
										)}
										{provider === "databricks_devops" && (
											<DatabricksDevOpsMcpConfigSection
												config={currentConfig as any}
												onConfigChange={handleConfigChange}
												isConfigured={isConfigured}
											/>
										)}
										{provider === "fabric" && (
											<FabricMcpConfigSection
												config={currentConfig as any}
												onConfigChange={handleConfigChange}
												isConfigured={isConfigured}
												onAuthStatusChange={setFabricOAuthStatus}
											/>
										)}
										{provider !== "github" && provider !== "notion" && provider !== "databricks" && provider !== "databricks_devops" && provider !== "sharepoint" && provider !== "onedrive" && provider !== "atlassian" && provider !== "fabric" && config.connection_type && (
											<div className="space-y-4">
												<div className="mb-4 text-sm font-medium text-gray-900">
													Custom MCP Server Configuration
												</div>

												<div className="space-y-3">
													{config.server_name && (
														<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
															<div className="mb-1 text-xs text-gray-600">
																Server Name
															</div>
															<div className="text-sm font-medium text-gray-900">
																{config.server_name}
															</div>
														</div>
													)}

													{config.description && (
														<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
															<div className="mb-1 text-xs text-gray-600">
																Description
															</div>
															<div className="text-sm text-gray-900">
																{config.description}
															</div>
														</div>
													)}

													<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
														<div className="mb-1 text-xs text-gray-600">
															Connection Type
														</div>
														<div className="text-sm font-medium capitalize text-gray-900">
															{config.connection_type}
														</div>
													</div>

													{config.connection_type === "stdio" && config.command && (
														<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
															<div className="mb-1 text-xs text-gray-600">
																Command
															</div>
															<div className="font-mono text-sm text-gray-900">
																{config.command}
															</div>
															{config.args &&
																Array.isArray(config.args) &&
																config.args.length > 0 && (
																	<div className="mt-2">
																		<div className="mb-1 text-xs text-gray-600">
																			Arguments
																		</div>
																		<div className="font-mono text-sm text-gray-900">
																			{config.args.join(" ")}
																		</div>
																	</div>
																)}
														</div>
													)}

													{config.connection_type === "http" && config.server_url && (
														<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
															<div className="mb-1 text-xs text-gray-600">
																Server URL
															</div>
															<div className="break-all font-mono text-sm text-gray-900">
																{config.server_url}
															</div>
														</div>
													)}

													<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
														<div className="mb-1 text-xs text-gray-600">
															Authentication
														</div>
														<div className="text-sm font-medium capitalize text-gray-900">
															{config.auth_type || "none"}
														</div>
													</div>

													{(config.timeout_seconds ||
														config.max_retries ||
														config.retry_delay) && (
														<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
															<div className="mb-2 text-xs text-gray-600">
																Connection Settings
															</div>
															<div className="grid grid-cols-3 gap-3 text-sm">
																{config.timeout_seconds && (
																	<div>
																		<div className="text-xs text-gray-600">
																			Timeout
																		</div>
																		<div className="text-gray-900">
																			{config.timeout_seconds}s
																		</div>
																	</div>
																)}
																{config.max_retries !== undefined && (
																	<div>
																		<div className="text-xs text-gray-600">
																			Max Retries
																		</div>
																		<div className="text-gray-900">
																			{config.max_retries}
																		</div>
																	</div>
																)}
																{config.retry_delay && (
																	<div>
																		<div className="text-xs text-gray-600">
																			Retry Delay
																		</div>
																		<div className="text-gray-900">
																			{config.retry_delay}s
																		</div>
																	</div>
																)}
															</div>
														</div>
													)}
												</div>

												<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
													<div className="mb-3 flex items-center justify-between">
														<div>
															<h4 className="text-sm font-medium text-gray-900">
																Tool Selection
															</h4>
															<p className="text-[10px] text-gray-600">
																Discover and manage available tools
															</p>
														</div>
														<Button
															onClick={handleGenericDiscoverTools}
															disabled={genericTestStatus === "testing"}
															variant={
																genericTestStatus === "success"
																	? "success"
																	: genericTestStatus === "error"
																		? "danger"
																		: "primary"
															}
															size="sm"
															icon={
																genericTestStatus === "testing" ? (
																	<Loader2 className="h-4 w-4 animate-spin text-orange-500" />
																) : genericTestStatus === "success" ? (
																	<CheckCircle className="h-4 w-4" />
																) : genericTestStatus === "error" ? (
																	<AlertCircle className="h-4 w-4" />
																) : undefined
															}
														>
															{genericTestStatus === "testing"
																? "Discovering..."
																: genericTestStatus === "success"
																	? "Discovered"
																	: genericTestStatus === "error"
																		? "Failed"
																		: "Discover Tools"}
														</Button>
													</div>

													{genericTestMessage && (
														<div
															className={`mb-3 rounded-[4px] border p-3 text-xs ${
																genericTestStatus === "success"
																	? "border-emerald-200 bg-emerald-50 text-emerald-900"
																	: genericTestStatus === "error"
																		? "border-red-200 bg-red-50 text-red-900"
																		: "border-gray-200 bg-white text-gray-700"
															}`}
														>
															{genericTestMessage}
														</div>
													)}

													{genericDiscoveredTools.length > 0 && (
														<McpToolSelectionCard
															tools={genericDiscoveredTools}
															toolPermissions={genericToolPermissions}
															onToolPermissionsChange={handleGenericToolPermissionsChange}
															providerColor={providerVisuals.color}
															providerColorRgb={providerVisuals.colorRgb}
															providerIcon={ProviderIcon}
															serverName={config.server_name || "MCP Server"}
														/>
													)}
												</div>
											</div>
										)}
										{provider !== "github" && provider !== "notion" && provider !== "databricks" && provider !== "databricks_devops" && provider !== "sharepoint" && provider !== "onedrive" && provider !== "atlassian" && provider !== "fabric" && !config.connection_type && (
											<div className="py-8 text-center">
												<div className="mb-4 inline-block rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
													<Settings className="h-8 w-8 text-gray-500" />
												</div>
												<h3 className="mb-2 text-lg font-medium text-gray-900">
													Generic MCP Server
												</h3>
												<p className="mx-auto max-w-sm text-sm text-gray-600">
													This is a generic MCP server node. For provider-specific
													features, create a new node using the MCP Server selection in
													Add Tool.
												</p>
											</div>
										)}
									</>
								)}

								{activeTab === "guardrails" && (
									<ToolGuardrailsSection toolNodeId={node.id} />
								)}
							</div>
						</div>

						<div className="border-t border-gray-200 bg-white px-6 py-3">
							<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
								<button
									type="button"
									onClick={handleDeleteNode}
									className="flex items-center gap-1.5 rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-xs text-red-700 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-800"
								>
									<Trash2 className="h-3.5 w-3.5" />
									Delete Node
								</button>

								<div className="flex items-center gap-3 sm:ml-auto">
									{hasChanges && (
										<span className="flex items-center gap-1.5 text-[11px] text-gray-600">
											<span className="h-1.5 w-1.5 animate-smoothPulse rounded-[4px] bg-orange-500" />
											Unsaved
										</span>
									)}
									<span className="hidden text-[11px] text-gray-400 sm:inline">
										{"\u2318"}S to save
									</span>
									<button
										type="button"
										onClick={onClose}
										className="rounded-[4px] border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
									>
										Cancel
									</button>
									<button
										type="button"
										onClick={handleSave}
										disabled={!hasChanges && isConfigured}
										className="rounded-[4px] bg-orange-600 px-5 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
									>
										<span className="inline-flex items-center gap-1.5">
											<Save className="h-3.5 w-3.5" />
											Save Changes
										</span>
									</button>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
	);
}
