"use client";

import {
	AlertCircle,
	CheckCircle,
	Eye,
	EyeOff,
	ExternalLink,
	Info,
	Loader2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import type { McpToolInfo } from "@/components/dialogs/McpToolsViewerModal";
import { AzureDevOpsIcon } from "@/components/icons/McpProviderIcons";
import McpToolSelectionCard from "./McpToolSelectionCard";

interface DatabricksDevOpsMcpConfig {
	server_name: string;
	connection_type: "stdio";
	command: string;
	args: string[];
	auth_type: "custom";
	auth_config: {
		databricks_token?: string;
		devops_pat?: string;
	};
	provider?: string;
	description?: string;
	metadata?: {
		databricks_host?: string;
		devops_org?: string;
		devops_project?: string;
		devops_repo?: string;
		git_folder_path?: string;
	};
	tool_permissions?: Record<string, boolean>;
}

type DiscoveredTool = McpToolInfo;

interface DatabricksDevOpsMcpConfigSectionProps {
	config: DatabricksDevOpsMcpConfig | null;
	onConfigChange: (config: DatabricksDevOpsMcpConfig) => void;
	isConfigured: boolean;
}

export default function DatabricksDevOpsMcpConfigSection({
	config,
	onConfigChange,
	isConfigured,
}: DatabricksDevOpsMcpConfigSectionProps) {
	// Databricks fields
	const [databricksHost, setDatabricksHost] = useState(
		config?.metadata?.databricks_host || "",
	);
	const [databricksToken, setDatabricksToken] = useState(
		config?.auth_config?.databricks_token || "",
	);
	const [showDatabricksToken, setShowDatabricksToken] = useState(false);

	// Azure DevOps fields
	const [devopsOrg, setDevopsOrg] = useState(
		config?.metadata?.devops_org || "",
	);
	const [devopsProject, setDevopsProject] = useState(
		config?.metadata?.devops_project || "",
	);
	const [devopsRepo, setDevopsRepo] = useState(
		config?.metadata?.devops_repo || "",
	);
	const [devopsPat, setDevopsPat] = useState(
		config?.auth_config?.devops_pat || "",
	);
	const [showDevopsPat, setShowDevopsPat] = useState(false);

	// Git folder path
	const [gitFolderPath, setGitFolderPath] = useState(
		config?.metadata?.git_folder_path || "",
	);

	// Test connection state
	const [testStatus, setTestStatus] = useState<
		"idle" | "testing" | "success" | "error"
	>(isConfigured ? "success" : "idle");
	const [testMessage, setTestMessage] = useState(
		isConfigured ? "Previously configured" : "",
	);
	const [discoveredTools, setDiscoveredTools] = useState<DiscoveredTool[]>([]);
	const [toolPermissions, setToolPermissions] = useState<Record<string, boolean>>(
		config?.tool_permissions || {},
	);

	// Sync from config on mount
	useEffect(() => {
		if (config?.auth_config?.databricks_token) {
			setDatabricksToken(config.auth_config.databricks_token);
		}
		if (config?.auth_config?.devops_pat) {
			setDevopsPat(config.auth_config.devops_pat);
		}
	}, [config]);

	// Check if all required fields are filled
	const hasAllFields =
		databricksHost.trim().length > 0 &&
		databricksToken.trim().length > 0 &&
		devopsOrg.trim().length > 0 &&
		devopsProject.trim().length > 0 &&
		devopsRepo.trim().length > 0 &&
		devopsPat.trim().length > 0 &&
		gitFolderPath.trim().length > 0;

	const buildConfig = useCallback((): DatabricksDevOpsMcpConfig => {
		return {
			server_name: "Databricks DevOps MCP Server",
			connection_type: "stdio",
			command: "python",
			args: ["-m", "backend.tools.databricks_devops_mcp"],
			auth_type: "custom",
			auth_config: {
				databricks_token: databricksToken.trim(),
				devops_pat: devopsPat.trim(),
			},
			provider: "databricks_devops",
			description:
				"Databricks workspace & Azure DevOps notebook management",
			metadata: {
				databricks_host: databricksHost.trim(),
				devops_org: devopsOrg.trim(),
				devops_project: devopsProject.trim(),
				devops_repo: devopsRepo.trim(),
				git_folder_path: gitFolderPath.trim(),
			},
		};
	}, [
		databricksHost,
		databricksToken,
		devopsOrg,
		devopsProject,
		devopsRepo,
		devopsPat,
		gitFolderPath,
	]);

	// Update parent config when fields change (only when all required fields are filled)
	useEffect(() => {
		if (hasAllFields) {
			onConfigChange(buildConfig());
		}
	}, [hasAllFields, buildConfig, onConfigChange]);

	const resetTestStatus = () => {
		if (testStatus === "success" || testStatus === "error") {
			setTestStatus("idle");
			setTestMessage("");
		}
	};

	const handleTestConnection = async () => {
		if (!hasAllFields) {
			setTestStatus("error");
			setTestMessage("Please fill in all required fields");
			return;
		}

		setTestStatus("testing");
		setTestMessage("Testing connection to Databricks DevOps MCP server...");
		setDiscoveredTools([]);

		try {
			const testConfig = buildConfig();

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
					const tools: DiscoveredTool[] =
						result.capabilities.tools.map(
							(tool: {
								name?: string;
								description?: string;
								input_schema?: Record<string, unknown>;
							}) => ({
								name: tool.name || "Unknown Tool",
								description:
									tool.description ||
									"No description available",
								input_schema: tool.input_schema || undefined,
							}),
						);
					setDiscoveredTools(tools);
				}

				onConfigChange(buildConfig());
			} else {
				setTestStatus("error");
				const errorMsg =
					result.error ||
					"Failed to connect to Databricks DevOps MCP server";
				setTestMessage(errorMsg);
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

	const inputClasses =
		"w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40";

	return (
		<div className="space-y-5">
			{/* Section Label */}
			<div className="text-[0.6rem] font-semibold capitalize text-gray-600">
				Databricks DevOps Configuration
			</div>

			{/* Info Card */}
			<div className="rounded-[4px] border border-blue-200 bg-white p-4 shadow-sm">
				<div className="flex items-start gap-3">
					<div className="rounded-[4px] border border-blue-200 bg-gray-50 p-2">
						<Info className="h-4 w-4 text-blue-800" />
					</div>
					<div className="flex-1">
						<h4 className="mb-1 text-sm font-medium text-blue-900">
							About Databricks DevOps
						</h4>
						<p className="mb-2 text-xs text-gray-600">
							Bridge Databricks workspace operations with Azure
							DevOps Git.{" "}
							<strong>Reads</strong> from Databricks Workspace
							API,{" "}
							<strong>writes</strong> to Azure DevOps, and{" "}
							<strong>syncs</strong> back via Databricks Repos.
						</p>
						<a
							href="https://learn.microsoft.com/en-us/azure/devops/repos/git/?view=azure-devops"
							target="_blank"
							rel="noopener noreferrer"
							className="flex items-center gap-1 text-xs text-blue-900 transition-colors hover:text-slate-900"
						>
							Learn more about Azure DevOps Repos
							<ExternalLink className="w-3 h-3" />
						</a>
					</div>
				</div>
			</div>

			{/* Databricks Configuration Card */}
			<div className="space-y-4 rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
				<label className="block text-xs font-medium text-gray-800">
					Databricks Workspace
				</label>

				<div>
					<label className="mb-1 block text-[10px] text-gray-600">
						Workspace URL
					</label>
					<input
						type="text"
						value={databricksHost}
						onChange={(e) => {
							setDatabricksHost(e.target.value);
							resetTestStatus();
						}}
						className={inputClasses}
						placeholder="https://adb-1234567890.3.azuredatabricks.net"
					/>
				</div>

				<div>
					<label className="mb-1 block text-[10px] text-gray-600">
						Personal Access Token
					</label>
					<div className="relative">
						<input
							type={showDatabricksToken ? "text" : "password"}
							value={databricksToken}
							onChange={(e) => {
								setDatabricksToken(e.target.value);
								resetTestStatus();
							}}
							className={`${inputClasses} pr-12`}
							placeholder="dapi..."
						/>
						<button
							type="button"
							onClick={() =>
								setShowDatabricksToken((prev) => !prev)
							}
							className="absolute right-3 top-1/2 -translate-y-1/2 transform text-gray-600 transition-colors hover:text-slate-900"
						>
							{showDatabricksToken ? (
								<EyeOff className="w-4 h-4" />
							) : (
								<Eye className="w-4 h-4" />
							)}
						</button>
					</div>
					<p className="mt-1 text-[10px] text-gray-600">
						Generate a PAT in Databricks under User Settings &gt;
						Developer &gt; Access tokens.
					</p>
				</div>

				<div>
					<label className="mb-1 block text-[10px] text-gray-600">
						Git Folder Path
					</label>
					<input
						type="text"
						value={gitFolderPath}
						onChange={(e) => {
							setGitFolderPath(e.target.value);
							resetTestStatus();
						}}
						className={inputClasses}
						placeholder="/Repos/user@company.com/repo-name"
					/>
					<p className="mt-1 text-[10px] text-gray-600">
						The workspace path to your Git folder in Databricks.
					</p>
				</div>
			</div>

			{/* Azure DevOps Configuration Card */}
			<div className="space-y-4 rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
				<label className="block text-xs font-medium text-gray-800">
					Azure DevOps Repository
				</label>

				<div className="grid grid-cols-2 gap-3">
					<div>
						<label className="mb-1 block text-[10px] text-gray-600">
							Organization
						</label>
						<input
							type="text"
							value={devopsOrg}
							onChange={(e) => {
								setDevopsOrg(e.target.value);
								resetTestStatus();
							}}
							className={inputClasses}
							placeholder="my-org"
						/>
					</div>
					<div>
						<label className="mb-1 block text-[10px] text-gray-600">
							Project
						</label>
						<input
							type="text"
							value={devopsProject}
							onChange={(e) => {
								setDevopsProject(e.target.value);
								resetTestStatus();
							}}
							className={inputClasses}
							placeholder="my-project"
						/>
					</div>
				</div>

				<div>
					<label className="mb-1 block text-[10px] text-gray-600">
						Repository
					</label>
					<input
						type="text"
						value={devopsRepo}
						onChange={(e) => {
							setDevopsRepo(e.target.value);
							resetTestStatus();
						}}
						className={inputClasses}
						placeholder="my-repo"
					/>
				</div>

				<div>
					<label className="mb-1 block text-[10px] text-gray-600">
						Personal Access Token
					</label>
					<div className="relative">
						<input
							type={showDevopsPat ? "text" : "password"}
							value={devopsPat}
							onChange={(e) => {
								setDevopsPat(e.target.value);
								resetTestStatus();
							}}
							className={`${inputClasses} pr-12`}
							placeholder="Azure DevOps PAT"
						/>
						<button
							type="button"
							onClick={() => setShowDevopsPat((prev) => !prev)}
							className="absolute right-3 top-1/2 -translate-y-1/2 transform text-gray-600 transition-colors hover:text-slate-900"
						>
							{showDevopsPat ? (
								<EyeOff className="w-4 h-4" />
							) : (
								<Eye className="w-4 h-4" />
							)}
						</button>
					</div>
					<p className="mt-1 text-[10px] text-gray-600">
						Needs Code (Read &amp; Write) scope. Generate in Azure
						DevOps under User Settings &gt; Personal access tokens.
					</p>
				</div>
			</div>

			{/* Test Connection Card */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
				<div className="mb-4 flex items-center justify-between">
					<div>
						<h4 className="text-sm font-medium text-gray-900">
							Connection Test
						</h4>
						<p className="text-[10px] text-gray-600">
							Verify credentials and discover available tools
						</p>
					</div>
					<Button
						onClick={handleTestConnection}
						disabled={
							testStatus === "testing" || !hasAllFields
						}
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

			{/* Discovered Tools */}
			{discoveredTools.length > 0 && (
				<McpToolSelectionCard
					tools={discoveredTools}
					toolPermissions={toolPermissions}
					onToolPermissionsChange={handleToolPermissionsChange}
					providerColor="#0078D4"
					providerColorRgb="0, 120, 212"
					providerIcon={AzureDevOpsIcon}
					serverName="Databricks DevOps"
				/>
			)}
		</div>
	);
}
