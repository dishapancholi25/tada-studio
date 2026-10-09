"use client";

import { Loader2, Save, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
	useFocusTrap,
	useEscapeKey,
} from "@/hooks/useAccessibility";
import { useToast } from "@/contexts/ToastContext";
import {
	type McpIntegrationConfig,
	type SaveMcpIntegrationRequest,
	userSettingsAPI,
} from "@/lib/user-settings-api";
import { systemMcpIntegrationsAPI } from "@/lib/admin-api";
import { getProviderVisuals } from "@/components/icons/McpProviderIcons";
import Button from "@/components/ui/Button";

// Provider config sections
import GitHubMcpConfigSection from "@/components/panels/properties/sections/GitHubMcpConfigSection";
import NotionMcpConfigSection from "@/components/panels/properties/sections/NotionMcpConfigSection";
import DatabricksMcpConfigSection from "@/components/panels/properties/sections/DatabricksMcpConfigSection";
import SharePointMcpConfigSection from "@/components/panels/properties/sections/SharePointMcpConfigSection";
import AtlassianMcpConfigSection from "@/components/panels/properties/sections/AtlassianMcpConfigSection";
import DatabricksDevOpsMcpConfigSection from "@/components/panels/properties/sections/DatabricksDevOpsMcpConfigSection";
import OneDriveMcpConfigSection from "@/components/panels/properties/sections/OneDriveMcpConfigSection";
import FabricMcpConfigSection from "@/components/panels/properties/sections/FabricMcpConfigSection";

interface McpIntegrationConfigModalProps {
	provider: string;
	scope: "personal" | "system";
	onClose: () => void;
	onSaved: () => void;
}

export default function McpIntegrationConfigModal({
	provider,
	scope,
	onClose,
	onSaved,
}: McpIntegrationConfigModalProps) {
	const { showToast } = useToast();
	const modalRef = useFocusTrap<HTMLDivElement>(true);
	useEscapeKey(onClose);

	const visuals = getProviderVisuals(provider);
	const IconComponent = visuals.icon;

	const [loading, setLoading] = useState(true);
	const [saving, setSaving] = useState(false);
	const [integration, setIntegration] =
		useState<McpIntegrationConfig | null>(null);
	const [currentConfig, setCurrentConfig] = useState<Record<string, any>>(
		{},
	);
	const [hasChanges, setHasChanges] = useState(false);

	// Load existing config
	useEffect(() => {
		const loadConfig = async () => {
			try {
				setLoading(true);
				if (scope === "personal") {
					const data =
						await userSettingsAPI.getMcpIntegration(provider);
					setIntegration(data);
					setCurrentConfig(data.settings || {});
				} else {
					// For system scope, load from admin API via the list
					const all = await systemMcpIntegrationsAPI.list();
					const match = all.find((i) => i.provider === provider);
					if (match) {
						// Build a config-like object from the summary
						setIntegration({
							provider: match.provider,
							display_name: match.display_name,
							is_configured: match.is_configured,
							is_active: match.is_active,
							has_system_default: false,
							has_group_default: false,
							group_names: [],
							credentials_configured: false,
							settings: {},
							tool_permissions: match.tool_permissions,
						});
					}
					setCurrentConfig({});
				}
			} catch (err) {
				console.error("Failed to load integration config:", err);
				showToast("error", "Failed to load integration configuration");
			} finally {
				setLoading(false);
			}
		};
		loadConfig();
	}, [provider, scope, showToast]);

	const handleConfigChange = useCallback(
		(newConfig: Record<string, any>) => {
			setCurrentConfig(newConfig);
			setHasChanges(true);
		},
		[],
	);

	const handleSave = useCallback(async () => {
		setSaving(true);
		try {
			// Extract credentials from config (sensitive fields)
			const credentials: Record<string, string> = {};
			const settings: Record<string, any> = { ...currentConfig };

			// Extract auth_config credentials
			if (settings.auth_config) {
				const authConfig = settings.auth_config;
				if (authConfig.access_token) {
					credentials.access_token = authConfig.access_token;
				}
				if (authConfig.databricks_token) {
					credentials.databricks_token =
						authConfig.databricks_token;
				}
				if (authConfig.devops_pat) {
					credentials.devops_pat = authConfig.devops_pat;
				}
				if (authConfig.client_secret) {
					credentials.client_secret = authConfig.client_secret;
				}
			}

			// Remove auth_config from settings (it contains sensitive data)
			// Keep non-sensitive parts
			if (settings.auth_config) {
				const { access_token, databricks_token, devops_pat, client_secret, ...safeAuthConfig } =
					settings.auth_config;
				settings.auth_config_metadata = safeAuthConfig;
				delete settings.auth_config;
			}

			const request: SaveMcpIntegrationRequest = {
				credentials:
					Object.keys(credentials).length > 0
						? credentials
						: undefined,
				settings,
				is_active: true,
			};

			if (scope === "personal") {
				await userSettingsAPI.saveMcpIntegration(provider, request);
			} else {
				await systemMcpIntegrationsAPI.save(provider, request);
			}

			showToast(
				"success",
				`${visuals.label} integration saved successfully`,
			);
			setHasChanges(false);
			onSaved();
		} catch (err) {
			console.error("Failed to save integration:", err);
			showToast("error", "Failed to save integration configuration");
		} finally {
			setSaving(false);
		}
	}, [currentConfig, provider, scope, visuals.label, showToast, onSaved]);

	const handleDelete = useCallback(async () => {
		try {
			if (scope === "personal") {
				await userSettingsAPI.deleteMcpIntegration(provider);
			} else {
				await systemMcpIntegrationsAPI.delete(provider);
			}
			showToast(
				"success",
				`${visuals.label} configuration removed`,
			);
			onSaved();
		} catch (err) {
			console.error("Failed to delete integration:", err);
			showToast("error", "Failed to remove configuration");
		}
	}, [provider, scope, visuals.label, showToast, onSaved]);

	const isConfigured = integration?.is_configured || false;

	const renderConfigSection = () => {
		switch (provider) {
			case "github":
				return (
					<GitHubMcpConfigSection
						config={currentConfig as any}
						onConfigChange={handleConfigChange}
						isConfigured={isConfigured}
					/>
				);
			case "notion":
				return (
					<NotionMcpConfigSection
						config={currentConfig as any}
						onConfigChange={handleConfigChange}
						isConfigured={isConfigured}
					/>
				);
			case "databricks":
				return (
					<DatabricksMcpConfigSection
						config={currentConfig as any}
						onConfigChange={handleConfigChange}
						isConfigured={isConfigured}
					/>
				);
			case "sharepoint":
				return (
					<SharePointMcpConfigSection
						config={currentConfig as any}
						onConfigChange={handleConfigChange}
						isConfigured={isConfigured}
					/>
				);
			case "onedrive":
				return (
					<OneDriveMcpConfigSection
						config={currentConfig as any}
						onConfigChange={handleConfigChange}
						isConfigured={isConfigured}
					/>
				);
			case "atlassian":
				return (
					<AtlassianMcpConfigSection
						config={currentConfig as any}
						onConfigChange={handleConfigChange}
						isConfigured={isConfigured}
					/>
				);
			case "databricks_devops":
				return (
					<DatabricksDevOpsMcpConfigSection
						config={currentConfig as any}
						onConfigChange={handleConfigChange}
						isConfigured={isConfigured}
					/>
				);
			case "fabric":
				return (
					<FabricMcpConfigSection
						config={currentConfig as any}
						onConfigChange={handleConfigChange}
						isConfigured={isConfigured}
					/>
				);
			default:
				return (
					<div className="text-sm text-slate-600">
						Configuration not available for this provider.
					</div>
				);
		}
	};

	return createPortal(
		<div
			className="fixed inset-0 z-[130] flex items-center justify-center"
			style={{ background: "rgba(0, 0, 0, 0.6)" }}
			onClick={(e) => {
				if (e.target === e.currentTarget) onClose();
			}}
		>
			<div
				ref={modalRef}
				className="flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)]"
				onClick={(e) => e.stopPropagation()}
			>
				{/* Header */}
				<div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-6 py-4">
					<div className="flex items-center gap-3">
						<div
							className="flex h-9 w-9 items-center justify-center rounded-[4px] border border-slate-200 bg-slate-50"
							style={{
								borderColor: `${visuals.color}40`,
								background: `rgba(${visuals.colorRgb}, 0.12)`,
							}}
						>
							<IconComponent
								size={22}
								style={{ color: visuals.color }}
							/>
						</div>
						<div>
							<h2 className="text-lg font-semibold tracking-tight text-slate-900">
								{visuals.label}
							</h2>
							<p className="text-xs text-slate-600">
								{scope === "system"
									? "System-wide configuration"
									: "Personal configuration"}
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-[4px] p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				{/* Content */}
				<div className="min-h-0 flex-1 overflow-y-auto bg-white px-6 py-5">
					{loading ? (
						<div className="flex items-center justify-center py-16">
							<Loader2 className="h-6 w-6 animate-spin text-orange-600" />
							<span className="ml-2 text-sm text-slate-600">
								Loading configuration...
							</span>
						</div>
					) : (
						<div className="space-y-4">
							{renderConfigSection()}
						</div>
					)}
				</div>

				{/* Footer */}
				<div className="flex shrink-0 items-center justify-between border-t border-slate-200 bg-white px-6 py-4">
					<div>
						{isConfigured && (
							<button
								type="button"
								onClick={handleDelete}
								className="text-sm text-red-600 transition-colors hover:text-red-800"
							>
								Remove Configuration
							</button>
						)}
					</div>
					<div className="flex items-center gap-3">
						<Button
							variant="secondary"
							onClick={onClose}
							className="!border-slate-200 !bg-white !text-slate-800 hover:!border-orange-500 hover:!text-orange-700"
						>
							Cancel
						</Button>
						<Button
							variant="primary"
							onClick={handleSave}
							disabled={saving || (!hasChanges && isConfigured)}
							className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
						>
							{saving ? (
								<>
									<Loader2 className="w-4 h-4 animate-spin text-orange-500 mr-1.5" />
									Saving...
								</>
							) : (
								<>
									<Save className="w-4 h-4 mr-1.5" />
									{isConfigured
										? "Update"
										: "Save Configuration"}
								</>
							)}
						</Button>
					</div>
				</div>
			</div>
		</div>,
		document.body,
	);
}
