"use client";

import {
	AlertCircle,
	CheckCircle,
	ExternalLink,
	Eye,
	EyeOff,
	Info,
	Loader2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import type { McpToolInfo } from "@/components/dialogs/McpToolsViewerModal";
import { GithubIcon } from "@/components/icons/McpProviderIcons";
import McpToolSelectionCard from "./McpToolSelectionCard";

interface GitHubMcpConfig {
	server_name: string;
	connection_type: "http";
	server_url: string;
	auth_type: "bearer";
	auth_config: {
		access_token: string;
	};
	provider?: string;
	description?: string;
	tool_permissions?: Record<string, boolean>;
}

type GitHubTool = McpToolInfo;

interface GitHubMcpConfigSectionProps {
	config: GitHubMcpConfig | null;
	onConfigChange: (config: GitHubMcpConfig) => void;
	isConfigured: boolean;
}

export default function GitHubMcpConfigSection({
	config,
	onConfigChange,
	isConfigured,
}: GitHubMcpConfigSectionProps) {
	const [pat, setPat] = useState(config?.auth_config?.access_token || "");
	const [showPat, setShowPat] = useState(false);
	const [testStatus, setTestStatus] = useState<
		"idle" | "testing" | "success" | "error"
	>(isConfigured ? "success" : "idle");
	const [testMessage, setTestMessage] = useState(
		isConfigured ? "Previously configured" : "",
	);
	const [discoveredTools, setDiscoveredTools] = useState<GitHubTool[]>([]);
	const [toolPermissions, setToolPermissions] = useState<Record<string, boolean>>(
		config?.tool_permissions || {},
	);

	useEffect(() => {
		if (config?.auth_config?.access_token) {
			setPat(config.auth_config.access_token);
		}
	}, [config]);

	const handlePatChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setPat(e.target.value);
			// Reset test status when PAT changes
			if (testStatus === "success" || testStatus === "error") {
				setTestStatus("idle");
				setTestMessage("");
			}
		},
		[testStatus],
	);

	const handleTogglePatVisibility = useCallback(() => {
		setShowPat((prev) => !prev);
	}, []);

	const handleToolPermissionsChange = useCallback(
		(permissions: Record<string, boolean>) => {
			setToolPermissions(permissions);
			onConfigChange({ tool_permissions: permissions } as any);
		},
		[onConfigChange],
	);

	const handleTestConnection = async () => {
		if (!pat.trim()) {
			setTestStatus("error");
			setTestMessage("Please enter a GitHub Personal Access Token");
			return;
		}

		setTestStatus("testing");
		setTestMessage("Testing connection to GitHub Copilot MCP server...");
		setDiscoveredTools([]);

		try {
			const testConfig: GitHubMcpConfig = {
				server_name: "GitHub Copilot MCP",
				connection_type: "http",
				server_url: "https://api.githubcopilot.com/mcp",
				auth_type: "bearer",
				auth_config: {
					access_token: pat.trim(),
				},
			};

			const response = await fetch(`/api/graph/test-mcp-server`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(testConfig),
			});

			const result = await response.json();

			if (response.ok && result.success) {
				setTestStatus("success");
				setTestMessage(
					`Successfully connected! Found ${result.capabilities?.tools?.length || 0} GitHub tools.`,
				);

				// Extract tools from the response
				if (result.capabilities?.tools) {
					const tools: GitHubTool[] = result.capabilities.tools.map(
						(tool: { name?: string; description?: string; input_schema?: Record<string, unknown> }) => ({
							name: tool.name || "Unknown Tool",
							description: tool.description || "No description available",
							input_schema: tool.input_schema || undefined,
						}),
					);
					setDiscoveredTools(tools);
				}

				// Update parent with new config
				const newConfig: GitHubMcpConfig = {
					server_name: "GitHub Copilot MCP",
					connection_type: "http",
					server_url: "https://api.githubcopilot.com/mcp",
					auth_type: "bearer",
					auth_config: { access_token: pat.trim() },
					provider: "github",
					description: "GitHub Copilot MCP Server for repository access",
				};
				onConfigChange(newConfig);
			} else {
				setTestStatus("error");
				const errorMsg =
					result.error || "Failed to connect to GitHub Copilot MCP server";

				if (errorMsg.includes("401") || errorMsg.includes("unauthorized")) {
					setTestMessage(
						"Authentication failed. Please check that your GitHub PAT is valid and has the required scopes.",
					);
				} else if (errorMsg.includes("403") || errorMsg.includes("forbidden")) {
					setTestMessage(
						"Access denied. Please ensure your GitHub account has Copilot access.",
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

	return (
		<div className="space-y-5">
			{/* Section Label */}
			<div className="text-[0.6rem] font-semibold capitalize text-gray-600">
				GitHub Configuration
			</div>

			{/* Info Card */}
			<div className="rounded-[4px] border border-blue-200 bg-white p-4 shadow-sm">
				<div className="flex items-start gap-3">
					<div className="rounded-[4px] border border-blue-200 bg-blue-50 p-2">
						<Info className="h-4 w-4 text-blue-700" />
					</div>
					<div className="flex-1">
						<h4 className="mb-1 text-sm font-medium text-blue-900">
							About GitHub Copilot MCP
						</h4>
						<p className="mb-2 text-xs text-gray-600">
							Connect to GitHub&apos;s official MCP server to access
							repositories, issues, pull requests, and more.
						</p>
						<a
							href="https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/use-the-github-mcp-server"
							target="_blank"
							rel="noopener noreferrer"
							className="flex items-center gap-1 text-xs text-blue-800 transition-colors hover:text-slate-900"
						>
							Learn more about GitHub MCP
							<ExternalLink className="w-3 h-3" />
						</a>
					</div>
				</div>
			</div>

			{/* PAT Input */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
				<label className="mb-2 block text-xs font-medium text-gray-800">
					GitHub Personal Access Token
				</label>
				<div className="relative">
					<input
						type={showPat ? "text" : "password"}
						value={pat}
						onChange={handlePatChange}
						className="w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 pr-12 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
						placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
					/>
					<button
						type="button"
						onClick={handleTogglePatVisibility}
						className="absolute right-3 top-1/2 -translate-y-1/2 transform text-gray-600 transition-colors hover:text-slate-900"
					>
						{showPat ? (
							<EyeOff className="w-4 h-4" />
						) : (
							<Eye className="w-4 h-4" />
						)}
					</button>
				</div>
				<p className="mt-2 text-[10px] text-gray-600">
					Required scopes: repo, user:read, workflow for full functionality.
				</p>
			</div>

			{/* Test Connection Card */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
				<div className="mb-4 flex items-center justify-between">
					<div>
						<h4 className="text-sm font-medium text-gray-900">Connection Test</h4>
						<p className="text-[10px] text-gray-600">
							Verify your PAT and discover available tools
						</p>
					</div>
					<Button
						onClick={handleTestConnection}
						disabled={testStatus === "testing" || !pat.trim()}
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

			{/* Discovered Tools */}
			{discoveredTools.length > 0 && (
				<McpToolSelectionCard
					tools={discoveredTools}
					toolPermissions={toolPermissions}
					onToolPermissionsChange={handleToolPermissionsChange}
					providerColor="#f0883e"
					providerColorRgb="240, 136, 62"
					providerIcon={GithubIcon}
					serverName="GitHub Copilot"
				/>
			)}
			</div>
		</div>
	);
}
