import type React from "react";
import { useEffect, useState } from "react";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import { configAPI } from "@/lib/config-api";
import {
	ApiError,
	type McpServerConfigRequest,
	type McpServerInfo,
	type TestMcpConnectionResponse,
	userSettingsAPI,
} from "@/lib/user-settings-api";
import McpServerConfigModalContent from "./McpServerConfigModalContent";
import McpServerConfigModalFooter from "./McpServerConfigModalFooter";
import McpServerConfigModalHeader from "./McpServerConfigModalHeader";

interface GroupInfo {
	id: string;
	name: string;
}

interface McpFormState {
	server_name: string;
	connection_type: "stdio" | "http";
	server_url: string;
	command: string;
	args: string; // Store as string to allow free typing, parse on submit
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

interface McpServerConfigModalProps {
	isOpen: boolean;
	selectedServer: McpServerInfo | null;
	onClose: () => void;
	onSaveComplete: () => void;
}

// Helper function to parse comma-separated args
const parseArgsString = (argsString: string): string[] => {
	if (!argsString || argsString.trim() === "") {
		return [];
	}
	return argsString
		.split(",")
		.map((arg) => {
			// Trim whitespace
			arg = arg.trim();
			// Remove surrounding quotes (single or double) if present
			if (
				(arg.startsWith('"') && arg.endsWith('"')) ||
				(arg.startsWith("'") && arg.endsWith("'"))
			) {
				arg = arg.slice(1, -1);
			}
			return arg;
		})
		.filter((arg) => arg !== "");
};

// Helper function to stringify args array
const stringifyArgs = (args: string[]): string => {
	return args.join(", ");
};

// Helper function to validate URL
const validateUrl = (url: string): boolean => {
	if (!url) return false;
	try {
		const parsedUrl = new URL(url);
		const validProtocols = ["http:", "https:", "ws:", "wss:"];
		return validProtocols.includes(parsedUrl.protocol);
	} catch {
		return false;
	}
};

const McpServerConfigModal: React.FC<McpServerConfigModalProps> = ({
	isOpen,
	selectedServer,
	onClose,
	onSaveComplete,
}) => {
	const isEditing = selectedServer !== null;
	const { showToast } = useToast();

	const [formState, setFormState] = useState<McpFormState>({
		server_name: "",
		connection_type: "http",
		server_url: "",
		command: "",
		args: "",
		working_directory: "",
		environment_variables: {},
		auth_type: "none",
		auth_credentials: {},
		timeout_seconds: 30,
		max_retries: 3,
		retry_delay: 1.0,
		description: "",
		visibility: "private",
		shared_with_group_ids: [],
		ssl_config: { verify: true },
	});

	const [formErrors, setFormErrors] = useState<FormErrors>({});
	const [isSaving, setIsSaving] = useState(false);
	const [isTesting, setIsTesting] = useState(false);
	const [testResult, setTestResult] =
		useState<TestMcpConnectionResponse | null>(null);
	const [credentialsConfigured, setCredentialsConfigured] = useState(false);
	const [isLoadingConfig, setIsLoadingConfig] = useState(false);
	const [credentialsDirty, setCredentialsDirty] = useState(false);
	const [formDirty, setFormDirty] = useState(false);
	const [showCloseConfirm, setShowCloseConfirm] = useState(false);
	const [originalServerName, setOriginalServerName] = useState<string | null>(
		null,
	);
	const [cloudProvider, setCloudProvider] = useState<"aws" | "azure" | "none">(
		"none",
	);
	const [availableGroups, setAvailableGroups] = useState<GroupInfo[]>([]);

	// Load cloud provider and groups on mount
	useEffect(() => {
		const fetchCloudProvider = async () => {
			try {
				const config = await configAPI.getEnvironmentConfig(true);
				setCloudProvider(config.system?.cloud_provider || "none");
			} catch (error) {
				console.error("Failed to fetch cloud provider config:", error);
			}
		};
		const fetchGroups = async () => {
			try {
				const response = await api.getGroups({ limit: 100 });
				const groups = response.groups || [];
				setAvailableGroups(
					groups.map((g: { id: string; name: string }) => ({
						id: g.id,
						name: g.name,
					})),
				);
			} catch (error) {
				console.error("Failed to fetch groups:", error);
			}
		};
		fetchCloudProvider();
		fetchGroups();
	}, []);

	// Load existing config in edit mode
	useEffect(() => {
		if (selectedServer) {
			setIsLoadingConfig(true);
			setOriginalServerName(selectedServer.server_name); // Store original name for rename detection
			userSettingsAPI
				.getMcpServer(selectedServer.server_name)
				.then((config) => {
					if (!config) {
						showToast("error", "Server configuration not found");
						return;
					}
					// Extract additional fields from config_summary
					const configSummary = config.config_summary || {};
					const argsArray = (configSummary.args as string[]) || [];
					setFormState({
						server_name: config.server_name,
						connection_type: config.connection_type as "stdio" | "http",
						server_url: config.server_url || "",
						command: config.command || "",
						args: stringifyArgs(argsArray),
						working_directory:
							(configSummary.working_directory as string) || "",
						environment_variables:
							(configSummary.environment_variables as Record<string, string>) ||
							{},
						auth_type: config.auth_type as
							| "none"
							| "api_key"
							| "bearer"
							| "oauth2"
							| "custom",
						auth_credentials:
							(configSummary.auth_credentials as Record<string, string>) || {},
						timeout_seconds: (configSummary.timeout_seconds as number) ?? 30,
						max_retries: (configSummary.max_retries as number) ?? 3,
						retry_delay: (configSummary.retry_delay as number) ?? 1.0,
						description: config.description || "",
						visibility: config.visibility === "shared" ? "shared" : "private",
						shared_with_group_ids: config.shared_with_group_ids || [],
						ssl_config: {
							verify:
								(configSummary.ssl_config as { verify?: boolean } | undefined)
									?.verify ?? true,
						},
					});
					setCredentialsConfigured(
						selectedServer?.credentials_configured ?? false,
					);
					setCredentialsDirty(false);
				})
				.catch((error) => {
					showToast(
						"error",
						`Failed to load server configuration: ${error.message}`,
					);
				})
				.finally(() => {
					setIsLoadingConfig(false);
				});
		} else {
			// Reset form for new server
			setOriginalServerName(null);
			setFormState({
				server_name: "",
				connection_type: "http",
				server_url: "",
				command: "",
				args: "",
				working_directory: "",
				environment_variables: {},
				auth_type: "none",
				auth_credentials: {},
				timeout_seconds: 30,
				max_retries: 3,
				retry_delay: 1.0,
				description: "",
				visibility: "private",
				shared_with_group_ids: [],
				ssl_config: { verify: true },
			});
			setCredentialsConfigured(false);
			setCredentialsDirty(false);
			setTestResult(null);
			setFormErrors({});
		}
		// Reset form dirty state when modal opens
		setFormDirty(false);
		setShowCloseConfirm(false);
	}, [selectedServer, isOpen]);

	// Validation function
	const validateForm = (): FormErrors | null => {
		const errors: FormErrors = {};

		if (!formState.server_name || formState.server_name.trim() === "") {
			errors.server_name = "Server name is required";
		}

		if (formState.connection_type === "stdio") {
			if (!formState.command || formState.command.trim() === "") {
				errors.command = "Command is required for stdio connection";
			}
		} else if (formState.connection_type === "http") {
			if (!formState.server_url || formState.server_url.trim() === "") {
				errors.server_url = "Server URL is required for HTTP connection";
			} else if (!validateUrl(formState.server_url)) {
				errors.server_url =
					"Invalid URL format. Must use http://, https://, ws://, or wss://";
			}
		}

		if (
			formState.auth_type !== "none" &&
			formState.auth_type !== "oauth2" &&
			formState.auth_type !== "oauth_host_identity" &&
			formState.auth_type !== "mcp_oauth"
		) {
			const requiredKeys: Record<string, string[]> = {
				api_key: ["api_key"],
				bearer: ["bearer_token"],
				custom: ["custom_headers"],
			};

			const required = requiredKeys[formState.auth_type];
			if (required) {
				const hasAllKeys = required.every(
					(key) =>
						formState.auth_credentials[key] &&
						formState.auth_credentials[key].trim() !== "",
				);

				// In edit mode with existing credentials, only require credentials if user is changing them
				const needsCredentials =
					isEditing && credentialsConfigured
						? credentialsDirty && !hasAllKeys // Only validate if user touched credentials
						: !hasAllKeys; // Always validate for new servers

				if (needsCredentials) {
					errors.auth_credentials = `${formState.auth_type} authentication requires credentials`;
				}
			}

			// Validate JSON for custom headers (only if provided)
			if (
				formState.auth_type === "custom" &&
				formState.auth_credentials.custom_headers
			) {
				try {
					JSON.parse(formState.auth_credentials.custom_headers);
				} catch (e) {
					errors.auth_credentials = `Invalid JSON: ${(e as Error).message}`;
				}
			}
		}

		return Object.keys(errors).length > 0 ? errors : null;
	};

	// Handle input changes
	const handleInputChange = (field: keyof McpFormState, value: any) => {
		setFormState((prev) => ({
			...prev,
			[field]: value,
		}));

		// Mark form as dirty when any field changes
		setFormDirty(true);

		// Mark credentials as dirty if auth credentials changed
		if (field === "auth_credentials") {
			setCredentialsDirty(true);
		}

		// Clear error for this field
		setFormErrors((prev) => {
			const newErrors = { ...prev };
			delete newErrors[field as keyof FormErrors];
			return newErrors;
		});
	};

	// Handle test connection
	const handleTestConnection = async () => {
		// Validate form before testing
		const errors = validateForm();
		if (errors) {
			setFormErrors(errors);
			showToast("error", "Please fix form errors before testing");
			return;
		}

		setIsTesting(true);
		setTestResult(null);

		try {
			// Build auth credentials with JSON parsing for custom headers
			let authCredentials;
			if (
				formState.auth_type !== "none" &&
				formState.auth_type !== "oauth2" &&
				formState.auth_type !== "oauth_host_identity" &&
				formState.auth_type !== "mcp_oauth"
			) {
				if (formState.auth_type === "custom") {
					const parsedHeaders = JSON.parse(
						formState.auth_credentials.custom_headers,
					);
					authCredentials = { custom_headers: parsedHeaders };
				} else {
					authCredentials = formState.auth_credentials;
				}
			}
			// For oauth2, oauth_host_identity, and mcp_oauth, credentials are injected by backend at runtime

			// Parse args string to array
			const argsArray = parseArgsString(formState.args);

			const config: McpServerConfigRequest = {
				server_name: formState.server_name,
				connection_type: formState.connection_type,
				server_url: formState.server_url || undefined,
				command: formState.command || undefined,
				args: argsArray.length > 0 ? argsArray : undefined,
				working_directory: formState.working_directory || undefined,
				environment_variables:
					Object.keys(formState.environment_variables).length > 0
						? formState.environment_variables
						: undefined,
				auth_type: formState.auth_type,
				auth_credentials: authCredentials,
				timeout_seconds: formState.timeout_seconds,
				max_retries: formState.max_retries,
				retry_delay: formState.retry_delay,
				description: formState.description || undefined,
				visibility: formState.visibility,
				shared_with_group_ids: formState.shared_with_group_ids,
				ssl_config: formState.ssl_config,
			};

			const result = await userSettingsAPI.testMcpConnection(config);
			setTestResult(result);

			if (result.success) {
				showToast(
					"success",
					`Connected successfully! Found ${result.tool_count || 0} tools`,
				);
			} else {
				showToast(
					"error",
					`Connection failed: ${result.error || "Unknown error"}`,
				);
			}
		} catch (error: unknown) {
			let errorMessage = "Network error occurred";
			if (error instanceof ApiError) {
				errorMessage = error.detail || error.message;
			} else if (error instanceof Error) {
				errorMessage = error.message;
			}
			const errorResult: TestMcpConnectionResponse = {
				success: false,
				server_name: formState.server_name,
				connection_type: formState.connection_type,
				error: errorMessage,
				tool_count: 0,
				tools: [],
			};
			setTestResult(errorResult);
			showToast("error", `Connection test failed: ${errorMessage}`);
		} finally {
			setIsTesting(false);
		}
	};

	// Handle form submission
	const handleSubmit = async () => {
		// Validate form
		const errors = validateForm();
		if (errors) {
			setFormErrors(errors);
			showToast("error", "Please fix the form errors before saving");
			return;
		}

		setIsSaving(true);

		try {
			// Build auth credentials with JSON parsing for custom headers
			let authCredentials;

			if (
				formState.auth_type === "none" ||
				formState.auth_type === "oauth2" ||
				formState.auth_type === "oauth_host_identity" ||
				formState.auth_type === "mcp_oauth"
			) {
				// No static credentials needed - these auth types use dynamic/runtime credentials
				authCredentials = undefined;
			} else if (isEditing && credentialsConfigured && !credentialsDirty) {
				// Editing with existing credentials and user didn't change them - omit to keep existing
				authCredentials = undefined;
			} else {
				// New server OR user is updating credentials
				if (formState.auth_type === "custom") {
					const parsedHeaders = JSON.parse(
						formState.auth_credentials.custom_headers || "{}",
					);
					authCredentials = { custom_headers: parsedHeaders };
				} else {
					authCredentials = formState.auth_credentials;
				}
			}

			// Parse args string to array
			const argsArray = parseArgsString(formState.args);

			const config: McpServerConfigRequest = {
				server_name: formState.server_name,
				connection_type: formState.connection_type,
				server_url: formState.server_url || undefined,
				command: formState.command || undefined,
				args: argsArray.length > 0 ? argsArray : undefined,
				working_directory: formState.working_directory || undefined,
				environment_variables:
					Object.keys(formState.environment_variables).length > 0
						? formState.environment_variables
						: undefined,
				auth_type: formState.auth_type,
				auth_credentials: authCredentials,
				timeout_seconds: formState.timeout_seconds,
				max_retries: formState.max_retries,
				retry_delay: formState.retry_delay,
				description: formState.description || undefined,
				visibility: formState.visibility,
				shared_with_group_ids: formState.shared_with_group_ids,
				ssl_config: formState.ssl_config,
			};

			// Debug logging
			console.log("[MCP Save]", {
				isEditing,
				credentialsConfigured,
				credentialsDirty,
				auth_type: formState.auth_type,
				sending_credentials: authCredentials !== undefined,
				auth_creds_keys: authCredentials ? Object.keys(authCredentials) : [],
			});

			// Handle server rename: delete old, create new
			const serverNameChanged =
				isEditing &&
				originalServerName &&
				originalServerName !== formState.server_name;

			if (serverNameChanged) {
				// Delete the old server first (by ID to ensure we delete the correct one)
				await userSettingsAPI.deleteMcpServer(selectedServer!.id!);
			}

			// Save the server (create new or update existing)
			await userSettingsAPI.saveMcpServer(formState.server_name, config);

			showToast(
				"success",
				serverNameChanged
					? `MCP server renamed from '${originalServerName}' to '${formState.server_name}'`
					: isEditing
						? "MCP server updated successfully"
						: "MCP server created successfully",
			);

			// Reset dirty flag on successful save
			setFormDirty(false);

			onSaveComplete();
			onClose();
		} catch (error: unknown) {
			if (error instanceof ApiError) {
				if (error.status === 400) {
					showToast("error", `Validation: ${error.detail || error.message}`);
				} else if (error.status === 409) {
					showToast("error", "A server with this name already exists");
					setFormErrors({ server_name: "Server name already exists" });
				} else if (error.status === 500) {
					showToast("error", "Server error occurred. Please try again later");
				} else {
					showToast(
						"error",
						`Failed to save server: ${error.detail || error.message}`,
					);
				}
			} else {
				const err = error as Error;
				showToast("error", `Failed to save server: ${err.message}`);
			}
		} finally {
			setIsSaving(false);
		}
	};

	// Handle close with confirmation if dirty
	const handleClose = () => {
		if (formDirty && !isSaving) {
			setShowCloseConfirm(true);
		} else {
			onClose();
		}
	};

	const handleConfirmClose = () => {
		setShowCloseConfirm(false);
		setFormDirty(false);
		onClose();
	};

	const handleCancelClose = () => {
		setShowCloseConfirm(false);
	};

	if (!isOpen) return null;

	return (
		<div
			className="fixed inset-0 z-[120] flex items-center justify-center bg-black/50 backdrop-blur-sm"
			onClick={(e) => {
				if (e.target === e.currentTarget && !isSaving) {
					handleClose();
				}
			}}
		>
			<div className="flex max-h-[80vh] w-full max-w-3xl flex-col overflow-hidden rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)]">
				<McpServerConfigModalHeader
					isEditing={isEditing}
					onClose={handleClose}
				/>

				<div className="flex-1 overflow-y-auto bg-white p-6">
					{isLoadingConfig ? (
						<div className="flex items-center justify-center py-12">
							<div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-orange-600"></div>
							<span className="ml-3 text-slate-600">Loading configuration...</span>
						</div>
					) : (
						<McpServerConfigModalContent
							formState={formState}
							formErrors={formErrors}
							isEditing={isEditing}
							credentialsConfigured={credentialsConfigured}
							testResult={testResult}
							isTesting={isTesting}
							cloudProvider={cloudProvider}
							availableGroups={availableGroups}
							onInputChange={handleInputChange}
							onTestConnection={handleTestConnection}
						/>
					)}
				</div>

				<McpServerConfigModalFooter
					isEditing={isEditing}
					isSaving={isSaving}
					onClose={handleClose}
					onSubmit={handleSubmit}
				/>
			</div>

			{/* Confirmation Dialog */}
			{showCloseConfirm && (
				<div className="fixed inset-0 z-[130] flex items-center justify-center bg-black/60 backdrop-blur-sm">
					<div className="mx-4 max-w-md rounded-[4px] border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.12)]">
						<h3 className="mb-2 text-lg font-semibold text-slate-900">Unsaved Changes</h3>
						<p className="mb-6 text-sm text-slate-600">
							You have unsaved changes. Are you sure you want to close? All changes will be lost.
						</p>
						<div className="flex justify-end gap-3">
							<button
								type="button"
								onClick={handleCancelClose}
								className="rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-800 transition-colors hover:border-orange-400 hover:text-slate-900"
							>
								Continue Editing
							</button>
							<button
								type="button"
								onClick={handleConfirmClose}
								className="rounded-[4px] bg-red-600 px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-red-700"
							>
								Discard Changes
							</button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
};

export default McpServerConfigModal;
