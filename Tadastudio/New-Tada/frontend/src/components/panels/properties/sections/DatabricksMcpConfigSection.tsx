"use client";

import {
	AlertCircle,
	CheckCircle,
	ExternalLink,
	Eye,
	EyeOff,
	Info,
	Key,
	Link,
	Loader2,
	Lock,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import Button from "@/components/ui/Button";
import type { McpToolInfo } from "@/components/dialogs/McpToolsViewerModal";
import { DatabricksIcon } from "@/components/icons/McpProviderIcons";
import McpToolSelectionCard from "./McpToolSelectionCard";

interface DatabricksMcpConfig {
	server_name: string;
	connection_type: "http";
	server_url: string;
	auth_type: "bearer" | "oauth";
	auth_config: Record<string, string>;
	provider?: string;
	description?: string;
	metadata?: {
		workspace_hostname?: string;
		catalog?: string;
		schema?: string;
	};
	tool_permissions?: Record<string, boolean>;
}

type DatabricksTool = McpToolInfo;

interface DatabricksMcpConfigSectionProps {
	config: DatabricksMcpConfig | null;
	onConfigChange: (config: DatabricksMcpConfig) => void;
	isConfigured: boolean;
}

export default function DatabricksMcpConfigSection({
	config,
	onConfigChange,
	isConfigured,
}: DatabricksMcpConfigSectionProps) {
	// URL mode: "parts" = workspace hostname + catalog + schema, "full" = single URL input
	const [urlMode, setUrlMode] = useState<"parts" | "full">(
		config?.metadata?.workspace_hostname ? "parts" : config?.server_url ? "full" : "parts",
	);

	// Endpoint type: "functions" = Unity Catalog functions, "sql" = SQL endpoint
	const [endpointType, setEndpointType] = useState<"functions" | "sql">(
		config?.server_url?.includes("/mcp/sql") ? "sql" : "functions",
	);

	// URL component parts
	const [workspaceHostname, setWorkspaceHostname] = useState(
		config?.metadata?.workspace_hostname || "",
	);
	const [catalog, setCatalog] = useState(config?.metadata?.catalog || "");
	const [schema, setSchema] = useState(config?.metadata?.schema || "");
	const [fullUrl, setFullUrl] = useState(config?.server_url || "");

	// Auth mode: "pat" = Personal Access Token, "oauth" = Service Principal M2M
	const [authMode, setAuthMode] = useState<"pat" | "oauth">(
		config?.auth_type === "oauth" ? "oauth" : "pat",
	);

	// PAT state
	const [pat, setPat] = useState(config?.auth_config?.access_token || "");
	const [showPat, setShowPat] = useState(false);

	// OAuth M2M state
	const [clientId, setClientId] = useState(config?.auth_config?.client_id || "");
	const [clientSecret, setClientSecret] = useState(config?.auth_config?.client_secret || "");
	const [showClientSecret, setShowClientSecret] = useState(false);

	// Test connection state
	const [testStatus, setTestStatus] = useState<"idle" | "testing" | "success" | "error">(
		isConfigured ? "success" : "idle",
	);
	const [testMessage, setTestMessage] = useState(isConfigured ? "Previously configured" : "");
	const [discoveredTools, setDiscoveredTools] = useState<DatabricksTool[]>([]);
	const [toolPermissions, setToolPermissions] = useState<Record<string, boolean>>(
		config?.tool_permissions || {},
	);

	// Sync from config on mount
	useEffect(() => {
		if (config?.auth_config?.access_token) {
			setPat(config.auth_config.access_token);
		}
		if (config?.auth_config?.client_id) {
			setClientId(config.auth_config.client_id);
		}
		if (config?.auth_config?.client_secret) {
			setClientSecret(config.auth_config.client_secret);
		}
	}, [config]);

	// Compute effective server URL
	const computedUrl = useMemo(() => {
		if (urlMode === "full") return fullUrl;
		if (!workspaceHostname) return "";
		const hostname = workspaceHostname
			.trim()
			.replace(/^https?:\/\//, "")
			.replace(/\/$/, "");
		if (endpointType === "sql") {
			return `https://${hostname}/api/2.0/mcp/sql`;
		}
		if (!catalog || !schema) return "";
		return `https://${hostname}/api/2.0/mcp/functions/${catalog.trim()}/${schema.trim()}`;
	}, [urlMode, fullUrl, workspaceHostname, catalog, schema, endpointType]);

	// Extract just the hostname (no path) for the OIDC token endpoint
	const effectiveHostname = useMemo(() => {
		if (urlMode === "parts" && workspaceHostname) {
			return workspaceHostname.trim().replace(/^https?:\/\//, "").replace(/\/.*$/, "");
		}
		// In full URL mode, extract hostname from the URL
		if (computedUrl) {
			try {
				return new URL(computedUrl).hostname;
			} catch {
				return "";
			}
		}
		return "";
	}, [urlMode, workspaceHostname, computedUrl]);

	// Check if auth credentials are filled
	const hasCredentials = authMode === "pat" ? pat.trim().length > 0 : clientId.trim().length > 0 && clientSecret.trim().length > 0;

	const handlePatChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setPat(e.target.value);
			if (testStatus === "success" || testStatus === "error") {
				setTestStatus("idle");
				setTestMessage("");
			}
		},
		[testStatus],
	);

	const handleTestConnection = async () => {
		if (!hasCredentials) {
			setTestStatus("error");
			setTestMessage(
				authMode === "pat"
					? "Please enter a Databricks Personal Access Token"
					: "Please enter Client ID and Client Secret",
			);
			return;
		}
		if (!computedUrl) {
			setTestStatus("error");
			setTestMessage("Please provide the workspace URL details");
			return;
		}

		setTestStatus("testing");
		setTestMessage("Testing connection to Databricks MCP server...");
		setDiscoveredTools([]);

		try {
			const testConfig: Record<string, unknown> =
				authMode === "pat"
					? {
							server_name: "Databricks MCP Server",
							connection_type: "http",
							server_url: computedUrl,
							auth_type: "bearer",
							auth_config: { access_token: pat.trim() },
						}
					: {
							server_name: "Databricks MCP Server",
							connection_type: "http",
							server_url: computedUrl,
							auth_type: "oauth",
							auth_config: {
								provider: "databricks",
								workspace_hostname: effectiveHostname,
								client_id: clientId.trim(),
								client_secret: clientSecret.trim(),
							},
						};

			const response = await fetch("/api/graph/test-mcp-server", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(testConfig),
			});

			const result = await response.json();

			if (response.ok && result.success) {
				setTestStatus("success");
				setTestMessage(
					`Successfully connected! Found ${result.capabilities?.tools?.length || 0} tools.`,
				);

				if (result.capabilities?.tools) {
					const tools: DatabricksTool[] = result.capabilities.tools.map(
						(tool: { name?: string; description?: string; input_schema?: Record<string, unknown> }) => ({
							name: tool.name || "Unknown Tool",
							description: tool.description || "No description available",
							input_schema: tool.input_schema || undefined,
						}),
					);
					setDiscoveredTools(tools);
				}

				// Build the final config and notify parent
				const newConfig: DatabricksMcpConfig =
					authMode === "pat"
						? {
								server_name: "Databricks MCP Server",
								connection_type: "http",
								server_url: computedUrl,
								auth_type: "bearer",
								auth_config: { access_token: pat.trim() },
								provider: "databricks",
								description: "Databricks Unity Catalog MCP Server",
								metadata: {
									workspace_hostname: effectiveHostname,
									catalog: catalog.trim(),
									schema: schema.trim(),
								},
							}
						: {
								server_name: "Databricks MCP Server",
								connection_type: "http",
								server_url: computedUrl,
								auth_type: "oauth",
								auth_config: {
									provider: "databricks",
									workspace_hostname: effectiveHostname,
									client_id: clientId.trim(),
									client_secret: clientSecret.trim(),
								},
								provider: "databricks",
								description: "Databricks Unity Catalog MCP Server",
								metadata: {
									workspace_hostname: effectiveHostname,
									catalog: catalog.trim(),
									schema: schema.trim(),
								},
							};
				onConfigChange(newConfig);
			} else {
				setTestStatus("error");
				const errorMsg = result.error || "Failed to connect to Databricks MCP server";

				if (errorMsg.includes("401") || errorMsg.includes("unauthorized")) {
					setTestMessage(
						"Authentication failed. Please check that your credentials are valid.",
					);
				} else if (errorMsg.includes("403") || errorMsg.includes("forbidden")) {
					setTestMessage(
						"Access denied. Please ensure the token/service principal has the required permissions.",
					);
				} else {
					setTestMessage(errorMsg);
				}
			}
		} catch (error) {
			setTestStatus("error");
			setTestMessage(
				`Connection test failed: ${error instanceof Error ? error.message : "Unknown error"}`,
			);
		}
	};

	const handleToolPermissionsChange = useCallback(
		(permissions: Record<string, boolean>) => {
			setToolPermissions(permissions);
			onConfigChange({ tool_permissions: permissions } as any);
		},
		[onConfigChange],
	);

	return (
		<div className="space-y-5">
			{/* Section Label */}
			<div className="text-[0.6rem] font-semibold capitalize text-gray-600">
				Databricks Configuration
			</div>

			{/* Info Card */}
			<div className="rounded-[4px] border border-orange-300 bg-white p-4 shadow-sm">
				<div className="flex items-start gap-3">
					<div className="rounded-[4px] border border-gray-200 bg-gray-50 p-2">
						<Info className="h-4 w-4 text-orange-800" />
					</div>
					<div className="flex-1">
						<h4 className="mb-1 text-sm font-medium text-orange-950">
							About Databricks MCP
						</h4>
						<p className="mb-2 text-xs text-gray-600">
							Connect to Databricks Unity Catalog functions exposed via MCP. Access
							data, run functions, and query vector search indexes.
						</p>
						<a
							href="https://docs.databricks.com/aws/en/generative-ai/mcp/"
							target="_blank"
							rel="noopener noreferrer"
							className="flex items-center gap-1 text-xs text-orange-950 transition-colors hover:text-slate-900"
						>
							Learn more about Databricks MCP
							<ExternalLink className="w-3 h-3" />
						</a>
					</div>
				</div>
			</div>

			{/* URL Configuration Card */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
				<div className="mb-3 flex items-center justify-between">
					<label className="text-xs font-medium text-gray-800">
						Server URL
					</label>
					<div className="flex overflow-hidden rounded-[4px] border border-gray-200">
						<button
							type="button"
							onClick={() => setUrlMode("parts")}
							className={`border-r border-gray-200 px-3 py-1 text-[10px] font-medium transition-colors ${
								urlMode === "parts"
									? "bg-gray-100 text-gray-900"
									: "bg-white text-gray-600 hover:text-slate-900"
							}`}
						>
							Build URL
						</button>
						<button
							type="button"
							onClick={() => setUrlMode("full")}
							className={`px-3 py-1 text-[10px] font-medium transition-colors ${
								urlMode === "full"
									? "bg-gray-100 text-gray-900"
									: "bg-white text-gray-600 hover:text-slate-900"
							}`}
						>
							Full URL
						</button>
					</div>
				</div>

				{urlMode === "parts" ? (
					<div className="space-y-3">
						{/* Endpoint Type Selector */}
						<div className="flex overflow-hidden rounded-[4px] border border-gray-200">
							<button
								type="button"
								onClick={() => setEndpointType("functions")}
								className={`flex-1 border-r border-gray-200 px-3 py-1.5 text-[10px] font-medium transition-colors ${
									endpointType === "functions"
										? "bg-gray-100 text-gray-900"
										: "bg-white text-gray-600 hover:text-slate-900"
								}`}
							>
								Unity Catalog Functions
							</button>
							<button
								type="button"
								onClick={() => setEndpointType("sql")}
								className={`flex-1 px-3 py-1.5 text-[10px] font-medium transition-colors ${
									endpointType === "sql"
										? "bg-gray-100 text-gray-900"
										: "bg-white text-gray-600 hover:text-slate-900"
								}`}
							>
								SQL
							</button>
						</div>

						<div>
							<label className="mb-1 block text-[10px] text-gray-600">
								Workspace Hostname
							</label>
							<input
								type="text"
								value={workspaceHostname}
								onChange={(e) => setWorkspaceHostname(e.target.value)}
								className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								placeholder="adb-1234567890.3.azuredatabricks.net"
							/>
						</div>
						{endpointType === "functions" && (
							<div className="grid grid-cols-2 gap-3">
								<div>
									<label className="mb-1 block text-[10px] text-gray-600">
										Catalog
									</label>
									<input
										type="text"
										value={catalog}
										onChange={(e) => setCatalog(e.target.value)}
										className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
										placeholder="my_catalog"
									/>
								</div>
								<div>
									<label className="mb-1 block text-[10px] text-gray-600">
										Schema
									</label>
									<input
										type="text"
										value={schema}
										onChange={(e) => setSchema(e.target.value)}
										className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
										placeholder="my_schema"
									/>
								</div>
							</div>
						)}
						{computedUrl && (
							<div className="flex items-start gap-2 rounded-[4px] border border-gray-200 bg-gray-50 p-2.5">
								<Link className="mt-0.5 h-3 w-3 flex-shrink-0 text-gray-600" />
								<p className="break-all font-mono text-[10px] text-gray-700">
									{computedUrl}
								</p>
							</div>
						)}
					</div>
				) : (
					<div>
						<input
							type="text"
							value={fullUrl}
							onChange={(e) => setFullUrl(e.target.value)}
							className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
							placeholder="https://adb-123.3.azuredatabricks.net/api/2.0/mcp/..."
						/>
						<p className="mt-1.5 text-[10px] text-gray-600">
							Full MCP server URL. Supports both /mcp/functions and /mcp/sql endpoints.
						</p>
					</div>
				)}
			</div>

			{/* Auth Type Selector */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
				<label className="mb-3 block text-xs font-medium text-gray-800">
					Authentication Method
				</label>
				<div className="mb-4 grid grid-cols-2 gap-2">
					<button
						type="button"
						onClick={() => setAuthMode("pat")}
						className={`flex items-center gap-2 rounded-[4px] border p-3 transition-colors ${
							authMode === "pat"
								? "border-orange-500 bg-white text-gray-900"
								: "border-gray-200 bg-white text-gray-600 hover:border-orange-300 hover:text-slate-900"
						}`}
					>
						<Key className="h-4 w-4" />
						<div className="text-left">
							<p className="text-xs font-medium">Personal Access Token</p>
							<p className="text-[10px] text-gray-600">For development</p>
						</div>
					</button>
					<button
						type="button"
						onClick={() => setAuthMode("oauth")}
						className={`flex items-center gap-2 rounded-[4px] border p-3 transition-colors ${
							authMode === "oauth"
								? "border-orange-500 bg-white text-gray-900"
								: "border-gray-200 bg-white text-gray-600 hover:border-orange-300 hover:text-slate-900"
						}`}
					>
						<Lock className="h-4 w-4" />
						<div className="text-left">
							<p className="text-xs font-medium">Service Principal</p>
							<p className="text-[10px] text-gray-600">OAuth M2M</p>
						</div>
					</button>
				</div>

				{authMode === "pat" ? (
					<div>
						<label className="mb-1 block text-[10px] text-gray-600">
							Databricks Personal Access Token
						</label>
						<div className="relative">
							<input
								type={showPat ? "text" : "password"}
								value={pat}
								onChange={handlePatChange}
								className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 pr-12 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								placeholder="dapi..."
							/>
							<button
								type="button"
								onClick={() => setShowPat((prev) => !prev)}
								className="absolute right-3 top-1/2 -translate-y-1/2 transform text-gray-600 transition-colors hover:text-slate-900"
							>
								{showPat ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
							</button>
						</div>
						<p className="mt-2 text-[10px] text-gray-600">
							Generate a PAT in your Databricks workspace under User Settings &gt;
							Developer &gt; Access tokens.
						</p>
					</div>
				) : (
					<div className="space-y-3">
						<div>
							<label className="mb-1 block text-[10px] text-gray-600">
								Client ID
							</label>
							<input
								type="text"
								value={clientId}
								onChange={(e) => setClientId(e.target.value)}
								className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								placeholder="Service principal client ID"
							/>
						</div>
						<div>
							<label className="mb-1 block text-[10px] text-gray-600">
								Client Secret
							</label>
							<div className="relative">
								<input
									type={showClientSecret ? "text" : "password"}
									value={clientSecret}
									onChange={(e) => setClientSecret(e.target.value)}
									className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 pr-12 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
									placeholder="Service principal client secret"
								/>
								<button
									type="button"
									onClick={() => setShowClientSecret((prev) => !prev)}
									className="absolute right-3 top-1/2 -translate-y-1/2 transform text-gray-600 transition-colors hover:text-slate-900"
								>
									{showClientSecret ? (
										<EyeOff className="w-4 h-4" />
									) : (
										<Eye className="w-4 h-4" />
									)}
								</button>
							</div>
						</div>
						<p className="text-[10px] text-gray-600">
							Uses OAuth2 client_credentials grant. Create a service principal in
							your Databricks workspace under Admin Settings.
						</p>
					</div>
				)}
			</div>

			{/* Test Connection Card */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
				<div className="mb-4 flex items-center justify-between">
					<div>
						<h4 className="text-sm font-medium text-gray-900">Connection Test</h4>
						<p className="text-[10px] text-gray-600">
							Verify credentials and discover available tools
						</p>
					</div>
					<Button
						onClick={handleTestConnection}
						disabled={testStatus === "testing" || !hasCredentials || !computedUrl}
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

			{/* Discovered Tools */}
			{discoveredTools.length > 0 && (
				<McpToolSelectionCard
					tools={discoveredTools}
					toolPermissions={toolPermissions}
					onToolPermissionsChange={handleToolPermissionsChange}
					providerColor="#FF3621"
					providerColorRgb="255, 54, 33"
					providerIcon={DatabricksIcon}
					serverName="Databricks Catalog"
				/>
			)}
		</div>
	);
}
