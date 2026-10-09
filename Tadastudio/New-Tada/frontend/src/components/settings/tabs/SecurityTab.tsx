"use client";

import {
	Activity,
	AlertTriangle,
	Clock,
	Copy,
	Download,
	Eye,
	EyeOff,
	Key,
	Lock,
	PlusCircle,
	RefreshCw,
	Shield,
	Upload,
	Users,
	Zap,
} from "lucide-react";
import { useCallback, useState } from "react";
import Button from "@/components/ui/Button";
import { useToast } from "@/contexts/ToastContext";
import { configAPI, type EnvironmentConfig } from "@/lib/config-api";

interface SecurityTabProps {
	config: EnvironmentConfig;
	onUpdate: (section: string, key: string, value: any) => Promise<void> | void;
}

export default function SecurityTab({ config, onUpdate }: SecurityTabProps) {
	const [generatingKey, setGeneratingKey] = useState(false);
	const [systemInfo, setSystemInfo] = useState<any>(null);
	const [loadingSystemInfo, setLoadingSystemInfo] = useState(false);
	const [newSecretName, setNewSecretName] = useState("");
	const [newSecretValue, setNewSecretValue] = useState("");
	const [savingSecret, setSavingSecret] = useState(false);
	const [showSecretValue, setShowSecretValue] = useState(false);
	const { showToast } = useToast();
	const secrets = config.mcp?.secrets || [];

	const handleGenerateEncryptionKey = async () => {
		setGeneratingKey(true);
		try {
			const result = await configAPI.generateEncryptionKey();
			showToast("success", "New encryption key generated");

			// Show the key in a modal or copy to clipboard
			navigator.clipboard.writeText(result.key).catch((error) => {
				console.error("Failed to copy encryption key:", error);
			});
			showToast("info", "Key copied to clipboard");
		} catch (error) {
			showToast("error", "Failed to generate encryption key");
		} finally {
			setGeneratingKey(false);
		}
	};

	const handleExportConfig = async () => {
		try {
			const result = await configAPI.exportConfiguration();
			showToast("success", `Configuration exported to ${result.backup_file}`);

			// Download the configuration
			const blob = new Blob([JSON.stringify(result.data, null, 2)], {
				type: "application/json",
			});
			const url = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download = `config_backup_${new Date().toISOString().split("T")[0]}.json`;
			a.click();
			URL.revokeObjectURL(url);
		} catch (error) {
			showToast("error", "Failed to export configuration");
		}
	};

	const handleImportConfig = async () => {
		const input = document.createElement("input");
		input.type = "file";
		input.accept = ".json";
		input.onchange = async (e: any) => {
			const file = e.target.files[0];
			if (file) {
				const reader = new FileReader();
				reader.onload = async (event) => {
					try {
						const configData = JSON.parse(event.target?.result as string);
						const result = await configAPI.importConfiguration(configData);
						if (result.success) {
							showToast("success", "Configuration imported successfully");
							window.location.reload();
						} else {
							showToast("error", `Import failed: ${result.error}`);
						}
					} catch (error) {
						showToast("error", "Invalid configuration file");
					}
				};
				reader.readAsText(file);
			}
		};
		input.click();
	};

	const loadSystemInfo = async () => {
		setLoadingSystemInfo(true);
		try {
			const info = await configAPI.getSystemInfo();
			setSystemInfo(info);
		} catch (error) {
			showToast("error", "Failed to load system information");
		} finally {
			setLoadingSystemInfo(false);
		}
	};

	const normalizeSecretName = (value: string) =>
		value
			.trim()
			.replace(/[^a-zA-Z0-9_]+/g, "_")
			.replace(/^_+|_+$/g, "")
			.toUpperCase();

	const handleCopy = async (value: string, label: string) => {
		try {
			await navigator.clipboard.writeText(value);
			showToast("success", `${label} copied`);
		} catch (error) {
			showToast("error", `Failed to copy ${label.toLowerCase()}`);
		}
	};

	const handleAddSecret = async () => {
		const normalized = normalizeSecretName(newSecretName);

		if (!normalized) {
			showToast(
				"error",
				"Enter a secret name (letters, numbers, underscores).",
			);
			return;
		}

		if (!newSecretValue) {
			showToast("error", "Enter a secret value.");
			return;
		}

		if (secrets.some((secret) => secret.name.toUpperCase() === normalized)) {
			showToast("error", "A secret with that name already exists.");
			return;
		}

		setSavingSecret(true);
		try {
			await Promise.resolve(
				onUpdate("mcp.secrets", normalized, newSecretValue),
			);
			setNewSecretName("");
			setNewSecretValue("");
			setShowSecretValue(false);
		} finally {
			setSavingSecret(false);
		}
	};

	const previewSecretName = newSecretName
		? normalizeSecretName(newSecretName)
		: "NAME";

	// Factory function for copy handlers
	const createCopyHandler = useCallback(
		(value: string, label: string) => () => {
			handleCopy(value, label);
		},
		[],
	);

	// Change handler for secret name input
	const handleSecretNameChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setNewSecretName(e.target.value);
		},
		[],
	);

	// Change handler for secret value input
	const handleSecretValueChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setNewSecretValue(e.target.value);
		},
		[],
	);

	// Click handler for show/hide secret value
	const handleToggleSecretValue = useCallback(() => {
		setShowSecretValue((prev) => !prev);
	}, []);

	return (
		<div className="p-6">
			{/* Header */}
			<div className="flex items-center gap-3 mb-6">
				<div className="p-2 bg-gradient-to-br from-red-500/20 to-pink-500/20 rounded-lg">
					<Shield className="w-6 h-6 text-red-400" />
				</div>
				<div>
					<h2 className="text-xl font-semibold text-slate-900">
						Security & Advanced Settings
					</h2>
					<p className="text-sm text-[color:var(--color-text-muted)] mt-1">
						Manage security settings and advanced configuration
					</p>
				</div>
			</div>

			{/* Encryption Settings */}
			<div className="bg-[color:var(--color-bg-secondary)]/60 backdrop-blur-sm border border-[color:var(--color-surface)] rounded-xl p-6 mb-6">
				<div className="flex items-center gap-3 mb-4">
					<Key className="w-5 h-5 text-[color:var(--color-accent)]" />
					<h3 className="text-lg font-semibold text-slate-900">
						Credential Encryption
					</h3>
				</div>

				<div className="space-y-4">
					<div className="flex items-center justify-between p-4 bg-[color:var(--color-surface)]/30 rounded-lg">
						<div>
							<p className="text-sm font-medium text-[color:var(--color-text-secondary)]">
								Encryption Status
							</p>
							<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
								Protects sensitive credentials in storage
							</p>
						</div>
						<div className="flex items-center gap-2">
							{config.security?.encryption?.enabled ? (
								<>
									<div className="w-2 h-2 rounded-full bg-[#0DA931] animate-pulse" />
									<span className="text-sm text-[#0DA931]">Enabled</span>
								</>
							) : (
								<>
									<div className="w-2 h-2 rounded-full bg-[color:var(--color-primary)]" />
									<span className="text-sm text-[color:var(--color-accent)]">
										Disabled
									</span>
								</>
							)}
						</div>
					</div>

					<button
						onClick={handleGenerateEncryptionKey}
						disabled={generatingKey}
						className="w-full px-4 py-2 bg-gradient-to-r from-[color:var(--color-primary)]/20 to-[color:var(--color-accent)]/18 
                     text-[color:var(--color-accent)] border border-[color:var(--color-border)]/35 rounded-lg font-medium
                     hover:shadow-lg hover:shadow-[#932A8F]/30 transition-all duration-300
                     disabled:opacity-50 disabled:cursor-not-allowed"
					>
						{generatingKey ? (
							<span className="flex items-center justify-center gap-2">
								<RefreshCw className="w-4 h-4 animate-spin text-orange-500" />
								Generating...
							</span>
						) : (
							<span className="flex items-center justify-center gap-2">
								<Key className="w-4 h-4" />
								Generate New Encryption Key
							</span>
						)}
					</button>

					<div className="p-3 bg-[color:var(--color-accent)]/15 border border-[color:var(--color-border)]/25 rounded-lg">
						<div className="flex items-start gap-2">
							<AlertTriangle className="w-4 h-4 text-[color:var(--color-accent)] mt-0.5" />
							<p className="text-xs text-[color:var(--color-text-muted)]">
								Generating a new key will require re-encrypting all stored
								credentials. Make sure to backup your configuration first.
							</p>
						</div>
					</div>
				</div>
			</div>

			{/* Backup & Restore */}
			<div className="bg-[color:var(--color-bg-secondary)]/60 backdrop-blur-sm border border-[color:var(--color-surface)] rounded-xl p-6 mb-6">
				<div className="flex items-center gap-3 mb-4">
					<Download className="w-5 h-5 text-[color:var(--color-accent)]" />
					<h3 className="text-lg font-semibold text-slate-900">Backup & Restore</h3>
				</div>

				<div className="grid gap-4 md:grid-cols-2">
					<button
						onClick={handleExportConfig}
						className="flex items-center justify-center gap-2 px-4 py-3 
                     bg-[color:var(--color-surface)]/50 hover:bg-[color:var(--color-surface)] border border-[color:var(--color-border)] 
                     rounded-lg text-[color:var(--color-text-secondary)] hover:text-slate-900 transition-all duration-300"
					>
						<Download className="w-5 h-5" />
						Export Configuration
					</button>

					<button
						onClick={handleImportConfig}
						className="flex items-center justify-center gap-2 px-4 py-3 
                     bg-[color:var(--color-surface)]/50 hover:bg-[color:var(--color-surface)] border border-[color:var(--color-border)] 
                     rounded-lg text-[color:var(--color-text-secondary)] hover:text-slate-900 transition-all duration-300"
					>
						<Upload className="w-5 h-5" />
						Import Configuration
					</button>
				</div>
			</div>

			{/* Future Features */}
			<div className="bg-[color:var(--color-bg-secondary)]/60 backdrop-blur-sm border border-[color:var(--color-surface)] rounded-xl p-6 mb-6">
				<h3 className="text-lg font-semibold text-slate-900 mb-4">
					Advanced Features
				</h3>

				<div className="grid gap-4 md:grid-cols-2">
					{/* API Key Rotation */}
					<div className="p-4 bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)] rounded-lg opacity-60">
						<div className="flex items-center gap-3 mb-2">
							<RefreshCw className="w-5 h-5 text-[color:var(--color-text-muted)]" />
							<h4 className="font-medium text-[color:var(--color-text-secondary)]">
								API Key Rotation
							</h4>
						</div>
						<p className="text-xs text-[color:var(--color-text-muted)] mb-3">
							Automatic key rotation for enhanced security
						</p>
						<div className="flex items-center gap-2">
							<Lock className="w-4 h-4 text-[color:var(--color-text-muted)]" />
							<span className="text-xs text-[color:var(--color-text-muted)]">
								Coming Soon
							</span>
						</div>
					</div>

					{/* Audit Logging */}
					<div className="p-4 bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)] rounded-lg opacity-60">
						<div className="flex items-center gap-3 mb-2">
							<Clock className="w-5 h-5 text-[color:var(--color-text-muted)]" />
							<h4 className="font-medium text-[color:var(--color-text-secondary)]">
								Audit Logging
							</h4>
						</div>
						<p className="text-xs text-[color:var(--color-text-muted)] mb-3">
							Track all configuration changes and access
						</p>
						<div className="flex items-center gap-2">
							<Lock className="w-4 h-4 text-[color:var(--color-text-muted)]" />
							<span className="text-xs text-[color:var(--color-text-muted)]">
								Coming Soon
							</span>
						</div>
					</div>

					{/* Rate Limiting */}
					<div className="p-4 bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)] rounded-lg opacity-60">
						<div className="flex items-center gap-3 mb-2">
							<Zap className="w-5 h-5 text-[color:var(--color-text-muted)]" />
							<h4 className="font-medium text-[color:var(--color-text-secondary)]">
								Rate Limiting
							</h4>
						</div>
						<p className="text-xs text-[color:var(--color-text-muted)] mb-3">
							Control API request rates and quotas
						</p>
						<div className="flex items-center gap-2">
							<Lock className="w-4 h-4 text-[color:var(--color-text-muted)]" />
							<span className="text-xs text-[color:var(--color-text-muted)]">
								Coming Soon
							</span>
						</div>
					</div>

					{/* Team Management */}
					<div className="p-4 bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)] rounded-lg opacity-60">
						<div className="flex items-center gap-3 mb-2">
							<Users className="w-5 h-5 text-[color:var(--color-text-muted)]" />
							<h4 className="font-medium text-[color:var(--color-text-secondary)]">
								Team Management
							</h4>
						</div>
						<p className="text-xs text-[color:var(--color-text-muted)] mb-3">
							User roles and permissions
						</p>
						<div className="flex items-center gap-2">
							<Lock className="w-4 h-4 text-[color:var(--color-text-muted)]" />
							<span className="text-xs text-[color:var(--color-text-muted)]">
								Coming Soon
							</span>
						</div>
					</div>
				</div>
			</div>

			{/* MCP Secrets */}
			<div className="bg-[color:var(--color-bg-secondary)]/60 backdrop-blur-sm border border-[color:var(--color-surface)] rounded-xl p-6 mb-6">
				<div className="flex items-center gap-3 mb-4">
					<Lock className="w-5 h-5 text-purple-600" />
					<div>
						<h3 className="text-lg font-semibold text-slate-900">MCP Secrets</h3>
						<p className="text-sm text-[color:var(--color-text-muted)]">
							Store credentials for MCP servers and reference them safely
						</p>
					</div>
				</div>

				<div className="space-y-6">
					<div>
						<div className="flex items-center justify-between mb-3">
							<h4 className="text-sm font-medium text-slate-900">Stored Secrets</h4>
							<span className="text-xs text-[color:var(--color-text-muted)]">
								{secrets.length} total
							</span>
						</div>
						{secrets.length > 0 ? (
							<div className="space-y-3">
								{secrets.map((secret) => {
									const secretRef = `secret://${secret.name}`;
									return (
										<div
											key={secret.env_key}
											className="p-4 bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)] rounded-lg flex flex-col gap-3 md:flex-row md:items-center md:justify-between"
										>
											<div>
												<p className="text-sm text-slate-900 font-medium">
													{secret.name}
												</p>
												<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
													{secret.env_key}
												</p>
												<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
													Value: {secret.value || "********"}
												</p>
											</div>
											<div className="flex items-center gap-2">
												<button
													type="button"
													onClick={createCopyHandler(
														secret.env_key,
														"Environment key",
													)}
													className="flex items-center gap-1 px-3 py-2 rounded-lg border border-[color:var(--color-border)] text-xs text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-border-hover)] transition-colors"
												>
													<Copy className="w-4 h-4" />
													Env
												</button>
												<button
													type="button"
													onClick={createCopyHandler(
														secretRef,
														"Secret reference",
													)}
													className="flex items-center gap-1 px-3 py-2 rounded-lg border border-[color:var(--color-border)] text-xs text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-border-hover)] transition-colors"
												>
													<Copy className="w-4 h-4" />
													Reference
												</button>
											</div>
										</div>
									);
								})}
							</div>
						) : (
							<div className="p-4 bg-[color:var(--color-surface)]/30 border border-dashed border-[color:var(--color-border)] rounded-lg text-xs text-[color:var(--color-text-muted)]">
								<p className="font-medium text-[color:var(--color-text-secondary)] mb-1">
									No secrets stored yet
								</p>
								<p>
									Use the form below to save API tokens or credentials for MCP
									servers.
								</p>
							</div>
						)}
					</div>

					<div className="border-t border-[color:var(--color-border)] pt-4">
						<h4 className="text-sm font-medium text-slate-900 mb-3 flex items-center gap-2">
							<PlusCircle className="w-4 h-4 text-[color:var(--color-accent)]" />
							Add Secret
						</h4>
						<div className="grid md:grid-cols-2 gap-4">
							<div>
								<label
									htmlFor="secret-name-input"
									className="block text-xs text-[color:var(--color-text-muted)] mb-2"
								>
									Secret Name
								</label>
								<input
									id="secret-name-input"
									type="text"
									value={newSecretName}
									onChange={handleSecretNameChange}
									placeholder="GITHUB_TOKEN"
									spellCheck={false}
									className="w-full px-4 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-[color:var(--color-text-muted)] focus:outline-none focus:border-[color:var(--color-border-hover)] transition-colors"
								/>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-2">
									Stored as{" "}
									<span className="font-mono text-[color:var(--color-text-secondary)]">
										MCP_SECRET_{previewSecretName}
									</span>{" "}
									in your environment.
								</p>
							</div>
							<div>
								<label
									htmlFor="secret-value-input"
									className="block text-xs text-[color:var(--color-text-muted)] mb-2"
								>
									Secret Value
								</label>
								<div className="relative">
									<input
										id="secret-value-input"
										type={showSecretValue ? "text" : "password"}
										value={newSecretValue}
										onChange={handleSecretValueChange}
										placeholder="Paste the token or credential"
										className="w-full px-4 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-[color:var(--color-text-muted)] focus:outline-none focus:border-[color:var(--color-border-hover)] transition-colors pr-12"
									/>
									<button
										type="button"
										onClick={handleToggleSecretValue}
										className="absolute inset-y-0 right-3 flex items-center text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)]"
										aria-label={
											showSecretValue
												? "Hide secret value"
												: "Show secret value"
										}
									>
										{showSecretValue ? (
											<EyeOff className="w-4 h-4" />
										) : (
											<Eye className="w-4 h-4" />
										)}
									</button>
								</div>
							</div>
						</div>
						<div className="mt-4 flex items-center justify-between flex-col md:flex-row gap-3">
							<p className="text-xs text-[color:var(--color-text-muted)] text-center md:text-left">
								Reference this secret from MCP tools with{" "}
								<span className="font-mono text-[color:var(--color-text-secondary)]">
									secret://{previewSecretName}
								</span>
							</p>
							<Button
								onClick={handleAddSecret}
								disabled={savingSecret}
								loading={savingSecret}
								icon={<PlusCircle className="w-4 h-4" />}
								size="sm"
							>
								Save Secret
							</Button>
						</div>
					</div>
				</div>
			</div>

			{/* System Diagnostics */}
			<div className="bg-[color:var(--color-bg-secondary)]/60 backdrop-blur-sm border border-[color:var(--color-surface)] rounded-xl p-6">
				<div className="flex items-center justify-between mb-4">
					<div className="flex items-center gap-3">
						<Activity className="w-5 h-5 text-[#0DA931]" />
						<h3 className="text-lg font-semibold text-slate-900">
							System Diagnostics
						</h3>
					</div>
					<Button
						onClick={loadSystemInfo}
						disabled={loadingSystemInfo}
						loading={loadingSystemInfo}
						size="sm"
					>
						{loadingSystemInfo ? "Loading..." : "Load Info"}
					</Button>
				</div>

				{systemInfo ? (
					<div className="grid gap-4 md:grid-cols-2">
						<div className="p-3 bg-[color:var(--color-surface)]/30 rounded-lg">
							<p className="text-xs text-[color:var(--color-text-muted)] mb-1">
								Platform
							</p>
							<p className="text-sm text-[color:var(--color-text-secondary)]">
								{systemInfo.platform?.system} {systemInfo.platform?.release}
							</p>
						</div>
						<div className="p-3 bg-[color:var(--color-surface)]/30 rounded-lg">
							<p className="text-xs text-[color:var(--color-text-muted)] mb-1">
								CPU Usage
							</p>
							<p className="text-sm text-[color:var(--color-text-secondary)]">
								{systemInfo.resources?.cpu_percent}%
							</p>
						</div>
						<div className="p-3 bg-[color:var(--color-surface)]/30 rounded-lg">
							<p className="text-xs text-[color:var(--color-text-muted)] mb-1">
								Memory
							</p>
							<p className="text-sm text-[color:var(--color-text-secondary)]">
								{systemInfo.resources?.memory_used_gb}GB /{" "}
								{systemInfo.resources?.memory_total_gb}GB
							</p>
						</div>
						<div className="p-3 bg-[color:var(--color-surface)]/30 rounded-lg">
							<p className="text-xs text-[color:var(--color-text-muted)] mb-1">
								Disk
							</p>
							<p className="text-sm text-[color:var(--color-text-secondary)]">
								{systemInfo.resources?.disk_used_gb}GB /{" "}
								{systemInfo.resources?.disk_total_gb}GB
							</p>
						</div>
					</div>
				) : (
					<div className="text-center py-8 text-[color:var(--color-text-muted)]">
						Click &quot;Load Info&quot; to view system diagnostics
					</div>
				)}
			</div>
		</div>
	);
}
