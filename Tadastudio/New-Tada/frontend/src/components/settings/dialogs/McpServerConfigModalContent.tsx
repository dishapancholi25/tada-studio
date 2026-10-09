import {
	AlertCircle,
	CheckCircle,
	ChevronDown,
	ChevronRight,
	Info,
	Link2,
	Loader2,
	Plus,
	Trash2,
	Unlink,
	XCircle,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import Dropdown from "@/components/ui/Dropdown";
import FormInput from "@/components/ui/FormInput";
import FormTextarea from "@/components/ui/FormTextarea";
import {
	type TestMcpConnectionResponse,
	userSettingsAPI,
} from "@/lib/user-settings-api";

interface GroupInfo {
	id: string;
	name: string;
}

interface McpFormState {
	server_name: string;
	connection_type: "stdio" | "http";
	server_url: string;
	command: string;
	args: string; // Store as string to allow free typing
	working_directory: string;
	environment_variables: Record<string, string>;
	auth_type:
		| "none"
		| "api_key"
		| "bearer"
		| "oauth2"
		| "oauth_host_identity"
		| "mcp_oauth"
		| "custom";
	auth_credentials: Record<string, string>;
	timeout_seconds: number;
	max_retries: number;
	retry_delay: number;
	description: string;
	visibility: "private" | "shared";
	shared_with_group_ids: string[];
	ssl_config: {
		verify: boolean;
	};
}

interface FormErrors {
	server_name?: string;
	server_url?: string;
	command?: string;
	auth_credentials?: string;
}

interface McpServerConfigModalContentProps {
	formState: McpFormState;
	formErrors: FormErrors;
	isEditing: boolean;
	credentialsConfigured: boolean;
	testResult: TestMcpConnectionResponse | null;
	isTesting: boolean;
	cloudProvider: "aws" | "azure" | "none";
	availableGroups: GroupInfo[];
	onInputChange: (field: keyof McpFormState, value: any) => void;
	onTestConnection: () => void;
}

// Environment Variables Editor Component
interface EnvironmentVariablesEditorProps {
	variables: Record<string, string>;
	onChange: (variables: Record<string, string>) => void;
}

const EnvironmentVariablesEditor: React.FC<EnvironmentVariablesEditorProps> = ({
	variables,
	onChange,
}) => {
	const entries = Object.entries(variables);

	const handleAdd = () => {
		const newKey = `ENV_VAR_${entries.length + 1}`;
		onChange({ ...variables, [newKey]: "" });
	};

	const handleUpdate = (oldKey: string, newKey: string, value: string) => {
		const updated = { ...variables };
		if (oldKey !== newKey) {
			delete updated[oldKey];
		}
		updated[newKey] = value;
		onChange(updated);
	};

	const handleRemove = (key: string) => {
		const updated = { ...variables };
		delete updated[key];
		onChange(updated);
	};

	return (
		<div className="space-y-2">
			{entries.map(([key, value], index) => (
				<div key={index} className="flex items-start gap-2">
					<input
						type="text"
						value={key}
						onChange={(e) => handleUpdate(key, e.target.value, value)}
						placeholder="KEY"
						className="flex-1 px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-orange-500 transition-colors"
					/>
					<input
						type="text"
						value={value}
						onChange={(e) => handleUpdate(key, key, e.target.value)}
						placeholder="value or secret://SECRET_NAME"
						className="flex-[2] px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-orange-500 transition-colors"
					/>
					<button
						type="button"
						onClick={() => handleRemove(key)}
						className="p-2 rounded-lg text-red-500 hover:bg-red-500/10 transition-colors"
						title="Remove variable"
					>
						<Trash2 size={16} />
					</button>
				</div>
			))}

			<button
				type="button"
				onClick={handleAdd}
				className="flex items-center gap-2 px-3 py-2 text-sm text-orange-600 hover:bg-slate-100 rounded-lg transition-colors"
			>
				<Plus size={16} />
				Add Environment Variable
			</button>

			{entries.length === 0 && (
				<p className="text-xs text-slate-600 italic">
					No environment variables configured. Click the &quot;Add Environment Variable&quot; button above to add one.
				</p>
			)}
		</div>
	);
};

// --- MCP OAuth Status Section ---

interface McpOAuthStatusSectionProps {
	serverName: string;
	serverUrl: string;
}

interface McpOAuthStatus {
	is_authenticated: boolean;
	has_token: boolean;
	has_client_registration: boolean;
	token_expired: boolean;
	expires_at: string | null;
	scope: string | null;
}

const McpOAuthStatusSection: React.FC<McpOAuthStatusSectionProps> = ({
	serverName,
	serverUrl,
}) => {
	const [oauthStatus, setOauthStatus] = useState<McpOAuthStatus | null>(null);
	const [isConnecting, setIsConnecting] = useState(false);
	const [isDisconnecting, setIsDisconnecting] = useState(false);
	const [statusLoading, setStatusLoading] = useState(true);
	const [errorMessage, setErrorMessage] = useState("");

	const checkOAuthStatus = useCallback(async () => {
		if (!serverName) {
			setStatusLoading(false);
			return;
		}
		setStatusLoading(true);
		try {
			const data = await userSettingsAPI.getMcpOAuthStatus(serverName);
			setOauthStatus(data);
		} catch (error) {
			console.error("Error checking MCP OAuth status:", error);
			setOauthStatus(null);
		} finally {
			setStatusLoading(false);
		}
	}, [serverName]);

	useEffect(() => {
		checkOAuthStatus();
	}, [checkOAuthStatus]);

	const handleConnect = async () => {
		if (!serverUrl) {
			setErrorMessage("Server URL is required to connect");
			return;
		}
		if (!serverName) {
			setErrorMessage("Server name is required to connect");
			return;
		}

		setIsConnecting(true);
		setErrorMessage("");

		try {
			const data = await userSettingsAPI.initiateMcpOAuth(
				serverUrl,
				serverName,
			);
			const { authorization_url } = data;

			// Open popup window
			const popup = window.open(
				authorization_url,
				"mcp_oauth",
				"width=600,height=700,left=200,top=100",
			);

			// Listen for completion message from callback page
			const handleMessage = (event: MessageEvent) => {
				if (event.data?.type === "mcp_oauth_complete") {
					window.removeEventListener("message", handleMessage);
					popup?.close();
					setIsConnecting(false);

					if (event.data.success) {
						checkOAuthStatus();
						setErrorMessage("");
					} else {
						setErrorMessage(
							event.data.error || "OAuth authorization failed",
						);
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
			console.error("Error initiating MCP OAuth:", error);
			setIsConnecting(false);
			setErrorMessage(
				error instanceof Error
					? error.message
					: "Failed to connect to MCP server",
			);
		}
	};

	const handleDisconnect = async () => {
		setIsDisconnecting(true);
		try {
			await userSettingsAPI.revokeMcpOAuth(serverName);
			setOauthStatus(null);
			setErrorMessage("");
		} catch (error) {
			console.error("Error disconnecting:", error);
			setErrorMessage(
				error instanceof Error ? error.message : "Failed to disconnect",
			);
		} finally {
			setIsDisconnecting(false);
			checkOAuthStatus();
		}
	};

	const isAuthenticated = oauthStatus?.is_authenticated ?? false;

	return (
		<div className="space-y-3">
			{/* Info box */}
			<div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
				<div className="flex items-start gap-2">
					<Info className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
					<p className="text-sm text-slate-700">
						Authenticate via the MCP server&apos;s OAuth flow (PKCE). The server
						must support RFC 9728 (Protected Resource Metadata) and RFC 8414
						(OAuth discovery).
					</p>
				</div>
			</div>

			{/* OAuth Connection Status */}
			<div
				className={`rounded-lg border p-3 ${
					isAuthenticated
						? "border-emerald-500/30 bg-emerald-500/5"
						: "border-slate-200 bg-white"
				}`}
			>
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-2">
						{statusLoading ? (
							<Loader2 className="w-4 h-4 text-slate-600 animate-spin" />
						) : isAuthenticated ? (
							<CheckCircle className="w-4 h-4 text-emerald-400" />
						) : (
							<AlertCircle className="w-4 h-4 text-slate-600" />
						)}
						<div>
							<p
								className={`text-sm font-medium ${isAuthenticated ? "text-emerald-700" : "text-slate-700"}`}
							>
								{statusLoading
									? "Checking..."
									: isAuthenticated
										? "Connected"
										: "Not connected"}
							</p>
							{isAuthenticated && oauthStatus?.expires_at && (
								<p className="text-[10px] text-slate-600">
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
										<Loader2 className="w-3 h-3 animate-spin text-orange-500" />
									) : (
										<Unlink className="w-3 h-3" />
									)
								}
							>
								Disconnect
							</Button>
						) : (
							<Button
								onClick={handleConnect}
								disabled={isConnecting || !serverUrl || !serverName}
								size="sm"
								icon={
									isConnecting ? (
										<Loader2 className="w-3 h-3 animate-spin text-orange-500" />
									) : (
										<Link2 className="w-3 h-3" />
									)
								}
							>
								{isConnecting ? "Connecting..." : "Connect"}
							</Button>
						))}
				</div>
			</div>

			{/* Error message */}
			{errorMessage && (
				<div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
					<p className="text-xs text-red-300">{errorMessage}</p>
				</div>
			)}

			{/* Not connected hint */}
			{!isAuthenticated && !statusLoading && !serverUrl && (
				<p className="text-xs text-slate-600">
					Enter the Server URL above, then click Connect to authenticate.
				</p>
			)}
		</div>
	);
};

const McpServerConfigModalContent: React.FC<
	McpServerConfigModalContentProps
> = ({
	formState,
	formErrors,
	isEditing,
	credentialsConfigured,
	testResult,
	isTesting,
	cloudProvider,
	availableGroups,
	onInputChange,
	onTestConnection,
}) => {
	const [showAdvanced, setShowAdvanced] = useState(false);

	// Connection type options
	const connectionTypeOptions = [
		{
			value: "http",
			label: "HTTP Streamable",
			description: "Connect via HTTP protocol",
		},
		{
			value: "stdio",
			label: "Standard I/O (Coming Soon)",
			description: "Temporarily unavailable — use HTTP instead",
			disabled: true,
		},
	];

	// Auth type options (conditionally include OAuth Host Identity)
	const authTypeOptions = [
		{
			value: "none",
			label: "No Authentication",
			description: "No authentication required",
		},
		{
			value: "api_key",
			label: "API Key",
			description: "Authenticate with API key",
		},
		{
			value: "bearer",
			label: "Bearer Token",
			description: "Authenticate with bearer token",
		},
		{
			value: "oauth2",
			label: "OAuth (User Identity)",
			description: "Passes current user's JWT token as bearer token",
		},
		...(cloudProvider === "aws" || cloudProvider === "azure"
			? [
					{
						value: "oauth_host_identity",
						label: `OAuth (Host Identity - ${cloudProvider.toUpperCase()})`,
						description: `Uses ${cloudProvider === "aws" ? "AWS IAM" : "Azure Managed Identity"} for authentication`,
					},
				]
			: []),
		{
			value: "mcp_oauth",
			label: "MCP Server Login",
			description:
				"OAuth login via the MCP server's authorization flow (PKCE)",
		},
		{
			value: "custom",
			label: "Custom Headers",
			description: "Custom authentication headers",
		},
	];

	return (
		<div className="space-y-6">
			{/* Section 1: Basic Information */}
			<div>
				<h3 className="text-sm font-semibold text-slate-900 mb-3">
					Basic Information
				</h3>
				<div className="space-y-4">
					<FormInput
						label="Server Name"
						placeholder="My Custom MCP Server"
						value={formState.server_name}
						onChange={(e) => onInputChange("server_name", e.target.value)}
						error={formErrors.server_name}
					/>
					<FormTextarea
						label="Description (Optional)"
						placeholder="Brief description of this MCP server"
						value={formState.description}
						onChange={(e) => onInputChange("description", e.target.value)}
						rows={2}
					/>
					<div>
						<label className="block text-sm font-medium text-slate-700 mb-2">
							Sharing
						</label>
						<Dropdown
							menuAppearance="light"
							triggerClassName="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 hover:!border-orange-400"
							options={[
								{
									value: "private",
									label: "Private",
									description: "Only you can use this server",
								},
								{
									value: "shared",
									label: "Shared",
									description:
										"Share with others (your credentials stay hidden)",
								},
							]}
							value={formState.visibility}
							onChange={(value) => {
								onInputChange("visibility", value);
								if (value === "private") {
									onInputChange("shared_with_group_ids", []);
								}
							}}
						/>
						{formState.visibility === "shared" && (
							<div className="mt-3 space-y-3">
								<Dropdown
									menuAppearance="light"
									triggerClassName="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 hover:!border-orange-400"
									options={[
										{
											value: "everyone",
											label: "Everyone",
											description: "All users can discover and clone this server",
										},
										{
											value: "groups",
											label: "Specific Groups",
											description: "Only members of selected groups",
										},
									]}
									value={
										formState.shared_with_group_ids.length === 0 ||
										formState.shared_with_group_ids.includes("__all__")
											? "everyone"
											: "groups"
									}
									onChange={(value) => {
										if (value === "everyone") {
											onInputChange("shared_with_group_ids", ["__all__"]);
										} else {
											// Switch to groups mode - clear __all__
											onInputChange(
												"shared_with_group_ids",
												formState.shared_with_group_ids.filter(
													(id: string) => id !== "__all__",
												),
											);
										}
									}}
								/>

								{/* Group selection checkboxes */}
								{!formState.shared_with_group_ids.includes("__all__") &&
									formState.shared_with_group_ids.length === 0 &&
									false}
								{formState.visibility === "shared" &&
									!formState.shared_with_group_ids.includes("__all__") && (
										<div className="border border-slate-200 rounded-lg p-3 max-h-40 overflow-y-auto">
											{availableGroups.length === 0 ? (
												<p className="text-xs text-slate-600 italic">
													No groups available. Ask an admin to create groups
													first.
												</p>
											) : (
												<div className="space-y-2">
													{availableGroups.map((group) => (
														<label
															key={group.id}
															className="flex items-center gap-2 cursor-pointer hover:bg-slate-100 rounded px-2 py-1 transition-colors"
														>
															<input
																type="checkbox"
																checked={formState.shared_with_group_ids.includes(
																	group.id,
																)}
																onChange={(e) => {
																	const newIds = e.target.checked
																		? [
																				...formState.shared_with_group_ids,
																				group.id,
																			]
																		: formState.shared_with_group_ids.filter(
																				(id: string) => id !== group.id,
																			);
																	onInputChange(
																		"shared_with_group_ids",
																		newIds,
																	);
																}}
																className="rounded border-slate-200 text-orange-600"
															/>
															<span className="text-sm text-slate-900">
																{group.name}
															</span>
														</label>
													))}
												</div>
											)}
										</div>
									)}

								<div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
									<p className="text-xs text-slate-700">
										Your credentials stay private. Other users can discover and
										clone this server configuration but will need to provide
										their own credentials.
									</p>
								</div>
							</div>
						)}
					</div>
				</div>
			</div>

			{/* Section 2: Connection Configuration */}
			<div>
				<h3 className="text-sm font-semibold text-slate-900 mb-3">
					Connection Configuration
				</h3>
				<div className="space-y-4">
					<div>
						<label className="block text-sm font-medium text-slate-700 mb-2">
							Connection Type
						</label>
						<Dropdown
							menuAppearance="light"
							triggerClassName="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 hover:!border-orange-400"
							options={connectionTypeOptions}
							value={formState.connection_type}
							onChange={(value) => onInputChange("connection_type", value)}
						/>
					</div>

					{/* Conditional Fields - HTTP Connection */}
					{formState.connection_type === "http" && (
						<div className="animate-fadeIn">
							<FormInput
								label="Server URL"
								placeholder="http://mcp.example.com"
								value={formState.server_url}
								onChange={(e) => onInputChange("server_url", e.target.value)}
								error={formErrors.server_url}
								hint="Must start with http://"
							/>
						</div>
					)}

					{/* Conditional Fields - Stdio Connection */}
					{formState.connection_type === "stdio" && (
						<div className="space-y-4 animate-fadeIn">
							<FormInput
								label="Command"
								placeholder="npx"
								value={formState.command}
								onChange={(e) => onInputChange("command", e.target.value)}
								error={formErrors.command}
							/>
							<FormInput
								label="Arguments (comma-separated)"
								placeholder="-y, @modelcontextprotocol/server-github"
								value={formState.args}
								onChange={(e) => onInputChange("args", e.target.value)}
								hint="Separate multiple arguments with commas"
							/>
							<FormInput
								label="Working Directory (Optional)"
								placeholder="/path/to/directory"
								value={formState.working_directory}
								onChange={(e) =>
									onInputChange("working_directory", e.target.value)
								}
							/>
						</div>
					)}
				</div>
			</div>

			{/* Section 3: Authentication */}
			<div>
				<h3 className="text-sm font-semibold text-slate-900 mb-3">
					Authentication
				</h3>
				<div className="space-y-4">
					<div>
						<label className="block text-sm font-medium text-slate-700 mb-2">
							Authentication Type
						</label>
						<Dropdown
							menuAppearance="light"
							triggerClassName="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 hover:!border-orange-400"
							options={authTypeOptions}
							value={formState.auth_type}
							onChange={(value) => onInputChange("auth_type", value)}
						/>
					</div>

					{/* Conditional Fields - API Key Auth */}
					{formState.auth_type === "api_key" && (
						<div className="animate-fadeIn">
							<FormInput
								label="API Key"
								type="password"
								placeholder={
									credentialsConfigured ? "••••••••" : "your-api-key"
								}
								value={formState.auth_credentials.api_key || ""}
								onChange={(e) =>
									onInputChange("auth_credentials", {
										...formState.auth_credentials,
										api_key: e.target.value,
									})
								}
								error={formErrors.auth_credentials}
								hint={
									credentialsConfigured
										? "Leave blank to keep existing credentials"
										: ""
								}
							/>
						</div>
					)}

					{/* Conditional Fields - Bearer Token Auth */}
					{formState.auth_type === "bearer" && (
						<div className="animate-fadeIn">
							<FormInput
								label="Bearer Token"
								type="password"
								placeholder={
									credentialsConfigured ? "••••••••" : "your-bearer-token"
								}
								value={formState.auth_credentials.bearer_token || ""}
								onChange={(e) =>
									onInputChange("auth_credentials", {
										...formState.auth_credentials,
										bearer_token: e.target.value,
									})
								}
								error={formErrors.auth_credentials}
								hint={
									credentialsConfigured
										? "Leave blank to keep existing credentials"
										: ""
								}
							/>
						</div>
					)}

					{/* Conditional Fields - OAuth2 Auth */}
					{formState.auth_type === "oauth2" && (
						<div className="animate-fadeIn">
							<div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
								<p className="text-sm text-slate-700">
									Your current session JWT token will be automatically sent as a
									bearer token to authenticate with the MCP server.
								</p>
							</div>
						</div>
					)}

					{/* Conditional Fields - MCP OAuth Auth */}
					{formState.auth_type === "mcp_oauth" && (
						<div className="animate-fadeIn">
							<McpOAuthStatusSection
								serverName={formState.server_name}
								serverUrl={formState.server_url}
							/>
						</div>
					)}

					{/* Conditional Fields - OAuth Host Identity Auth */}
					{formState.auth_type === "oauth_host_identity" && (
						<div className="animate-fadeIn space-y-4">
							<div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4">
								<p className="text-sm text-slate-700">
									Authentication tokens will be generated automatically using{" "}
									<strong>
										{cloudProvider === "aws"
											? "AWS IAM"
											: "Azure Managed Identity"}
									</strong>
									.
									{cloudProvider === "aws"
										? " You can optionally specify an IAM role ARN to assume, or leave blank to use the default AWS credential chain."
										: " You can optionally specify a resource scope and client ID, or leave blank to use defaults."}
								</p>
							</div>

							{/* Azure-specific fields */}
							{cloudProvider === "azure" && (
								<>
									<FormInput
										label="Azure Resource Scope (Optional)"
										placeholder="https://database.windows.net/.default"
										value={formState.auth_credentials.resource || ""}
										onChange={(e) =>
											onInputChange("auth_credentials", {
												...formState.auth_credentials,
												resource: e.target.value,
											})
										}
										hint="Azure resource scope (defaults to database scope if not specified)"
									/>
									<FormInput
										label="Azure Client ID (Optional)"
										placeholder="00000000-0000-0000-0000-000000000000"
										value={formState.auth_credentials.client_id || ""}
										onChange={(e) =>
											onInputChange("auth_credentials", {
												...formState.auth_credentials,
												client_id: e.target.value,
											})
										}
										hint="Azure managed identity client ID (leave blank for system-assigned identity)"
									/>
								</>
							)}

							{/* AWS-specific fields */}
							{cloudProvider === "aws" && (
								<FormInput
									label="AWS Role ARN (Optional)"
									placeholder="arn:aws:iam::123456789012:role/MyRole"
									value={formState.auth_credentials.role_arn || ""}
									onChange={(e) =>
										onInputChange("auth_credentials", {
											...formState.auth_credentials,
											role_arn: e.target.value,
										})
									}
									hint="AWS IAM role ARN to assume (leave blank for default credentials)"
								/>
							)}
						</div>
					)}

					{/* Conditional Fields - Custom Auth */}
					{formState.auth_type === "custom" && (
						<div className="animate-fadeIn">
							<FormTextarea
								label="Custom Headers (JSON)"
								placeholder='{"X-Custom-Header": "value"}'
								value={formState.auth_credentials.custom_headers || ""}
								onChange={(e) =>
									onInputChange("auth_credentials", {
										...formState.auth_credentials,
										custom_headers: e.target.value,
									})
								}
								rows={3}
								error={formErrors.auth_credentials}
								hint="Enter custom headers as JSON object"
							/>
						</div>
					)}
				</div>
			</div>

			{/* Section 4: Advanced Settings (Collapsible) */}
			<div>
				<button
					onClick={() => setShowAdvanced(!showAdvanced)}
					className="flex items-center gap-2 text-sm font-semibold text-slate-900 hover:text-slate-900 transition-colors mb-3"
				>
					{showAdvanced ? (
						<ChevronDown size={16} />
					) : (
						<ChevronRight size={16} />
					)}
					Advanced Settings
				</button>

				{showAdvanced && (
					<div className="space-y-6 animate-fadeIn">
						{/* Timeout and Retry Settings */}
						<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
							<FormInput
								label="Timeout (seconds)"
								type="number"
								placeholder="30"
								value={formState.timeout_seconds.toString()}
								onChange={(e) =>
									onInputChange(
										"timeout_seconds",
										parseInt(e.target.value) || 30,
									)
								}
								hint="Connection timeout in seconds"
							/>
							<FormInput
								label="Max Retries"
								type="number"
								placeholder="3"
								value={formState.max_retries.toString()}
								onChange={(e) =>
									onInputChange("max_retries", parseInt(e.target.value) || 3)
								}
								hint="Maximum number of retry attempts"
							/>
							<FormInput
								label="Retry Delay (seconds)"
								type="number"
								step="0.1"
								placeholder="1.0"
								value={formState.retry_delay.toString()}
								onChange={(e) =>
									onInputChange(
										"retry_delay",
										parseFloat(e.target.value) || 1.0,
									)
								}
								hint="Delay between retries"
							/>
						</div>

						{/* Environment Variables - Only for STDIO connections */}
						{formState.connection_type === "stdio" && (
							<div>
								<label className="block text-sm font-medium text-slate-700 mb-2">
									Environment Variables
								</label>
								<p className="text-xs text-slate-600 mb-3">
									Configure environment variables for the STDIO MCP server
									process. Use{" "}
									<code className="px-1 py-0.5 bg-white rounded text-orange-600">
										secret://VARIABLE_NAME
									</code>{" "}
									to reference backend environment variables securely.
								</p>
								<EnvironmentVariablesEditor
									variables={formState.environment_variables}
									onChange={(envVars) =>
										onInputChange("environment_variables", envVars)
									}
								/>
							</div>
						)}

						{/* SSL/TLS Configuration - Only for HTTP connections */}
						{formState.connection_type === "http" && (
							<div className="border-t pt-4">
								<h4 className="text-sm font-medium text-slate-900 mb-3">
									SSL/TLS Configuration
								</h4>

								<div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
									<input
										type="checkbox"
										id="verify_ssl"
										checked={formState.ssl_config.verify}
										onChange={(e) =>
											onInputChange("ssl_config", {
												...formState.ssl_config,
												verify: e.target.checked,
											})
										}
										className="mt-1 w-4 h-4 rounded accent-orange-500 cursor-pointer"
									/>
									<div className="flex-1">
										<label
											htmlFor="verify_ssl"
											className="text-sm font-medium text-slate-900 cursor-pointer"
										>
											Verify SSL Certificates
										</label>
										<p className="text-xs text-slate-600 mt-1">
											{formState.ssl_config.verify
												? "Enabled: SSL certificates will be verified (recommended)"
												: "Disabled: SSL certificates will not be verified (development only)"}
										</p>
									</div>
								</div>

								{!formState.ssl_config.verify && (
									<div className="flex gap-2 p-3 mt-3 bg-red-500/10 border border-red-500/30 rounded-lg">
										<AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
										<p className="text-xs text-red-700">
											<strong>Security Warning:</strong> Disabling SSL verification is not
											recommended for production. Use only for testing with self-signed
											certificates.
										</p>
									</div>
								)}
							</div>
						)}
					</div>
				)}
			</div>

			{/* Section 5: Test Connection */}
			<div>
				<h3 className="text-sm font-semibold text-slate-900 mb-3">
					Test Connection
				</h3>
				<div className="space-y-3">
					<Button
						onClick={onTestConnection}
						variant="secondary"
						disabled={isTesting}
						loading={isTesting}
					>
						{isTesting ? "Testing..." : "Test Connection"}
					</Button>

					{/* Test Result Display */}
					{testResult && (
						<div className="animate-fadeIn">
							{testResult.success ? (
								<div className="bg-[#0DA931]/10 border border-[#0DA931]/30 rounded-lg p-4">
									<div className="flex items-start gap-3">
										<CheckCircle
											className="text-[#0DA931] mt-0.5 flex-shrink-0"
											size={20}
										/>
										<div className="flex-1">
											<p className="text-sm font-medium text-[#0DA931]">
												Connected successfully! Found{" "}
												{testResult.tool_count || 0} tools
											</p>

											{/* Tool List */}
											{testResult.tools && testResult.tools.length > 0 && (
												<div className="mt-3 max-h-48 overflow-y-auto space-y-2">
													{testResult.tools.map((tool, index) => (
														<div
															key={index}
															className="bg-white border border-slate-200 rounded-lg p-3"
														>
															<p className="text-sm font-medium text-slate-900">
																{tool.name}
															</p>
															{tool.description && (
																<p className="text-xs text-slate-700 mt-1">
																	{tool.description}
																</p>
															)}
														</div>
													))}
												</div>
											)}
										</div>
									</div>
								</div>
							) : (
								<div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
									<div className="flex items-start gap-3">
										<XCircle
											className="text-red-500 mt-0.5 flex-shrink-0"
											size={20}
										/>
										<div className="flex-1">
											<p className="text-sm font-medium text-red-500">
												Connection failed
											</p>
											<p className="text-xs text-red-400 mt-1">
												{testResult.error || "Unknown error occurred"}
											</p>
										</div>
									</div>
								</div>
							)}
						</div>
					)}
				</div>
			</div>
		</div>
	);
};

export default McpServerConfigModalContent;
