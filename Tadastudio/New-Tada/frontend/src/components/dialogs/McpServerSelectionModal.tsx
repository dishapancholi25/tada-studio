"use client";

import { Github, Loader2, Terminal, X } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";
import {
	type McpServerInfo,
	userSettingsAPI,
} from "@/lib/user-settings-api";
import { AzureDevOpsIcon, FabricIcon, OneDriveIcon, SharePointIcon } from "../icons/McpProviderIcons";

// Brand logo SVGs
const NotionLogo = ({ className }: { className?: string }) => (
	<svg className={className} viewBox="0 0 100 100" fill="currentColor">
		<path d="M6.017 4.313l55.333 -4.087c6.797 -0.583 8.543 -0.19 12.817 2.917l17.663 12.443c2.913 2.14 3.883 2.723 3.883 5.053v68.243c0 4.277 -1.553 6.807 -6.99 7.193L24.467 99.967c-4.08 0.193 -6.023 -0.39 -8.16 -3.113L3.3 79.94c-2.333 -3.113 -3.3 -5.443 -3.3 -8.167V11.113c0 -3.497 1.553 -6.413 6.017 -6.8z" />
		<path
			fill="white"
			d="M61.35 0.227l-55.333 4.087C1.553 4.7 0 7.617 0 11.113v60.66c0 2.723 0.967 5.053 3.3 8.167l13.007 16.913c2.137 2.723 4.08 3.307 8.16 3.113l64.257 -3.89c5.437 -0.387 6.99 -2.917 6.99 -7.193V20.64c0 -2.21 -0.873 -2.847 -3.443 -4.733L74.167 3.143c-4.273 -3.107 -6.02 -3.5 -12.817 -2.917zM25.92 19.523c-5.247 0.353 -6.437 0.433 -9.417 -1.99L8.927 11.507c-0.77 -0.78 -0.383 -1.753 1.557 -1.947l53.193 -3.887c4.467 -0.39 6.793 1.167 8.54 2.527l9.123 6.61c0.39 0.197 1.36 1.36 0.193 1.36l-54.933 3.307 -0.68 0.047zM19.803 88.3V30.367c0 -2.53 0.777 -3.697 3.103 -3.893L86 22.78c2.14 -0.193 3.107 1.167 3.107 3.693v57.547c0 2.53 -0.39 4.67 -3.883 4.863l-60.377 3.5c-3.493 0.193 -5.043 -0.97 -5.043 -4.083zm59.6 -54.827c0.387 1.75 0 3.5 -1.75 3.7l-2.91 0.577v42.773c-2.527 1.36 -4.853 2.137 -6.797 2.137 -3.107 0 -3.883 -0.973 -6.21 -3.887l-19.03 -29.94v28.967l6.02 1.363s0 3.5 -4.857 3.5l-13.39 0.777c-0.39 -0.78 0 -2.723 1.357 -3.11l3.497 -0.97v-38.3L30.48 40.667c-0.39 -1.75 0.58 -4.277 3.3 -4.473l14.367 -0.967 19.8 30.327v-26.83l-5.047 -0.58c-0.39 -2.143 1.163 -3.7 3.103 -3.89l13.4 -0.78z"
		/>
	</svg>
);

// MCP Logo Component - matches the one from ExternalToolsTab
const McpLogo = ({ className }: { className?: string }) => (
	<svg
		fill="currentColor"
		fillRule="evenodd"
		height="1em"
		style={{ flex: "none", lineHeight: 1 }}
		viewBox="0 0 24 24"
		width="1em"
		xmlns="http://www.w3.org/2000/svg"
		className={className}
	>
		<title>ModelContextProtocol</title>
		<path d="M15.688 2.343a2.588 2.588 0 00-3.61 0l-9.626 9.44a.863.863 0 01-1.203 0 .823.823 0 010-1.18l9.626-9.44a4.313 4.313 0 016.016 0 4.116 4.116 0 011.204 3.54 4.3 4.3 0 013.609 1.18l.05.05a4.115 4.115 0 010 5.9l-8.706 8.537a.274.274 0 000 .393l1.788 1.754a.823.823 0 010 1.18.863.863 0 01-1.203 0l-1.788-1.753a1.92 1.92 0 010-2.754l8.706-8.538a2.47 2.47 0 000-3.54l-.05-.049a2.588 2.588 0 00-3.607-.003l-7.172 7.034-.002.002-.098.097a.863.863 0 01-1.204 0 .823.823 0 010-1.18l7.273-7.133a2.47 2.47 0 00-.003-3.537z" />
		<path d="M14.485 4.703a.823.823 0 000-1.18.863.863 0 00-1.204 0l-7.119 6.982a4.115 4.115 0 000 5.9 4.314 4.314 0 006.016 0l7.12-6.982a.823.823 0 000-1.18.863.863 0 00-1.204 0l-7.119 6.982a2.588 2.588 0 01-3.61 0 2.47 2.47 0 010-3.54l7.12-6.982z" />
	</svg>
);

import Button from "@/components/ui/Button";
import FormInput from "@/components/ui/FormInput";

interface McpServerSelectionModalProps {
	isOpen: boolean;
	onClose: () => void;
	onSelectProvider: (
		provider: string,
		toolName: string,
		customConfig?: McpServerInfo,
		shouldClone?: boolean,
	) => void;
}

interface McpProvider {
	id: string;
	name: string;
	description: string;
	icon: React.ReactNode;
	color: string;
	colorRgb: string;
	available: boolean;
	isCustom?: boolean;
	customConfig?: McpServerInfo;
	/** Override the auto-generated node name (prevents appending " MCP Server"). */
	defaultServerName?: string;
}

const mcpProviders: McpProvider[] = [
	{
		id: "github",
		name: "GitHub",
		description: "Access repositories, issues, PRs, and GitHub Actions",
		icon: <Github className="w-7 h-7" />,
		color: "#f0883e",
		colorRgb: "240, 136, 62",
		available: true,
	},
	{
		id: "atlassian",
		name: "Atlassian",
		description: "Jira issues, Confluence pages, and Bitbucket repos",
		icon: (
			<img
				src="/logos/atlassian-icon.svg"
				alt="Atlassian"
				className="w-7 h-7"
			/>
		),
		color: "#0052cc",
		colorRgb: "0, 82, 204",
		available: true,
		defaultServerName: "Atlassian",
	},
	{
		id: "databricks",
		name: "Databricks Catalog",
		description: "Access Unity Catalog functions and data via MCP",
		icon: <img src="/logos/databricks-icon.svg" alt="Databricks Catalog" className="w-7 h-7" />,
		color: "#FF3621",
		colorRgb: "255, 54, 33",
		available: true,
		defaultServerName: "Databricks Catalog MCP Server",
	},
	{
		id: "databricks_devops",
		name: "DevOps",
		description: "Manage Databricks notebooks via Azure DevOps Git",
		icon: <AzureDevOpsIcon className="w-7 h-7" />,
		color: "#0078D4",
		colorRgb: "0, 120, 212",
		available: true,
		defaultServerName: "Databricks DevOps MCP Server",
	},
	{
		id: "sharepoint",
		name: "SharePoint",
		description: "Access SharePoint sites, document libraries, and files",
		icon: <SharePointIcon className="w-7 h-7" />,
		color: "#0078D4",
		colorRgb: "0, 120, 212",
		available: true,
		defaultServerName: "SharePoint MCP Server",
	},
	{
		id: "onedrive",
		name: "OneDrive",
		description: "Access personal and shared files from OneDrive",
		icon: <OneDriveIcon className="w-7 h-7" />,
		color: "#0078D4",
		colorRgb: "0, 120, 212",
		available: true,
		defaultServerName: "OneDrive MCP Server",
	},
	{
		id: "fabric",
		name: "Microsoft Fabric",
		description: "Access Fabric workspaces, lakehouses, notebooks, and pipelines",
		icon: <FabricIcon className="w-7 h-7" />,
		color: "#2AAC94",
		colorRgb: "42, 172, 148",
		available: true,
		defaultServerName: "Microsoft Fabric MCP Server",
	},
	{
		id: "notion",
		name: "Notion",
		description: "Access databases, pages, and workspace content",
		icon: <NotionLogo className="w-7 h-7" />,
		color: "#000000",
		colorRgb: "255, 255, 255",
		available: true,
	},
];

export default function McpServerSelectionModal({
	isOpen,
	onClose,
	onSelectProvider,
}: McpServerSelectionModalProps) {
	const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
	const [selectedCustomConfig, setSelectedCustomConfig] = useState<
		McpServerInfo | undefined
	>(undefined);
	const [toolName, setToolName] = useState("");
	const [mounted, setMounted] = useState(false);
	const [customServers, setCustomServers] = useState<McpServerInfo[]>([]);
	const [loadingCustomServers, setLoadingCustomServers] = useState(true);
	const [shouldClone, setShouldClone] = useState(false);
	const [configuredProviders, setConfiguredProviders] = useState<Set<string>>(
		new Set(),
	);
	const dialogRef = useFocusTrap<HTMLDivElement>(isOpen);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	useEscapeKey(onClose, isOpen);

	// Fetch custom servers and configured integrations on mount
	useEffect(() => {
		const fetchCustomServers = async () => {
			try {
				// listMcpServers returns both own servers and servers shared with the user
				const allServers = await userSettingsAPI.listMcpServers();
				// Filter to only show active servers
				setCustomServers(allServers.filter((server) => server.is_active));
			} catch (error) {
				console.error("Failed to fetch MCP servers:", error);
			}
			setLoadingCustomServers(false);
		};

		const fetchConfiguredIntegrations = async () => {
			try {
				const integrations = await userSettingsAPI.listMcpIntegrations();
				const configured = new Set(
					integrations
						.filter((i) => i.is_configured && i.is_active)
						.map((i) => i.provider),
				);
				setConfiguredProviders(configured);
			} catch {
				// Non-critical, don't block UI
			}
		};

		fetchCustomServers();
		fetchConfiguredIntegrations();
	}, []);

	// Reset state when modal opens
	useEffect(() => {
		if (isOpen) {
			setSelectedProvider(null);
			setSelectedCustomConfig(undefined);
			setToolName("");
			setShouldClone(false);
		}
	}, [isOpen]);

	// Map custom server to provider format
	const mapCustomServerToProvider = useCallback(
		(server: McpServerInfo): McpProvider => {
			// Use server.id for unique identification to prevent duplicate selection issues
			return {
				id: `custom_${server.id}`,
				name: server.server_name,
				description: server.description || "Custom MCP Server",
				icon: <McpLogo className="w-7 h-7" />,
				color: "#6366f1",
				colorRgb: "99, 102, 241",
				available: true,
				isCustom: true,
				customConfig: server,
			};
		},
		[],
	);

	// Custom providers derived from fetched servers
	const customProviders = useMemo(() => {
		return customServers.map(mapCustomServerToProvider);
	}, [customServers, mapCustomServerToProvider]);

	// All providers combined (used for selection lookup)
	const allProviders = useMemo(() => {
		return [...mcpProviders, ...customProviders];
	}, [customProviders]);

	// Currently selected provider object (for right panel display)
	const selectedProviderObj = useMemo(() => {
		if (!selectedProvider) return null;
		return allProviders.find((p) => p.id === selectedProvider) ?? null;
	}, [selectedProvider, allProviders]);

	const handleProviderSelect = useCallback(
		(providerId: string) => {
			const provider = allProviders.find((p) => p.id === providerId);
			if (provider && provider.available) {
				setSelectedProvider(providerId);
				setSelectedCustomConfig(provider.customConfig);
				// For custom servers, use the name as-is; for built-in providers, use defaultServerName or append "MCP Server"
				const defaultName = provider.customConfig
					? provider.name
					: provider.defaultServerName || `${provider.name} MCP Server`;
				setToolName(defaultName);
			}
		},
		[allProviders],
	);

	const handleConfirm = useCallback(() => {
		if (selectedProvider && toolName.trim()) {
			onSelectProvider(
				selectedProvider,
				toolName.trim(),
				selectedCustomConfig,
				shouldClone,
			);
			onClose();
		}
	}, [
		selectedProvider,
		toolName,
		selectedCustomConfig,
		shouldClone,
		onSelectProvider,
		onClose,
	]);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleDialogClick = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleToolNameChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setToolName(e.target.value);
		},
		[],
	);

	// Renders a single provider row (shared between official and custom sections)
	const renderProviderRow = useCallback(
		(provider: McpProvider) => {
			const isSelected = selectedProvider === provider.id;
			const isDisabled = !provider.available;

			return (
				<button
					key={provider.id}
					type="button"
					onClick={() => handleProviderSelect(provider.id)}
					disabled={isDisabled}
					className={`
            group relative flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left transition-all duration-200
            ${
							isDisabled
								? "cursor-not-allowed border border-slate-200 bg-slate-100 opacity-60"
								: "cursor-pointer border border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
						}
            ${
							isSelected && !isDisabled
								? "!border-2 !border-orange-500 bg-white shadow-[0_4px_14px_rgba(15,23,42,0.08)]"
								: ""
						}
          `}
					title={provider.description}
				>
					{/* Icon */}
					<div
						className="p-2.5 rounded-xl border flex-shrink-0"
						style={{
							backgroundColor: `rgba(${provider.colorRgb}, 0.1)`,
							borderColor: `rgba(${provider.colorRgb}, 0.25)`,
							color: provider.color,
						}}
					>
						{provider.icon}
					</div>

					{/* Name + Description + Badges */}
					<div className="min-w-0 flex-1">
						<div className="flex items-center gap-2">
							<h3 className="truncate text-sm font-semibold text-slate-900 group-hover:text-slate-900">
								{provider.name}
							</h3>
							{isDisabled && (
								<span className="flex-shrink-0 rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
									Coming Soon
								</span>
							)}
							{!provider.isCustom &&
								configuredProviders.has(provider.id) && (
								<span className="flex-shrink-0 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-800">
									Configured
								</span>
							)}
							{provider.isCustom && (
								<span className="flex-shrink-0 rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[10px] font-medium text-indigo-800">
									Custom
								</span>
							)}
							{provider.isCustom &&
								provider.customConfig?.is_owned_by_current_user && (
									<span
										className={`flex-shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${
											provider.customConfig.visibility === "shared"
												? "border-emerald-200 bg-emerald-50 text-emerald-800"
												: "border-slate-200 bg-slate-100 text-slate-700"
										}`}
									>
										{provider.customConfig.visibility === "shared"
											? "Shared"
											: "Private"}
									</span>
								)}
							{provider.customConfig &&
								!provider.customConfig.is_owned_by_current_user && (
									<span className="flex-shrink-0 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-800">
										Shared
									</span>
								)}
							{provider.customConfig?.is_template && (
								<span className="flex-shrink-0 rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[10px] font-medium text-violet-800">
									Cloned
								</span>
							)}
							{provider.customConfig &&
								!provider.customConfig.is_owned_by_current_user &&
								provider.customConfig.creator_name && (
									<span className="flex-shrink-0 text-[10px] italic text-slate-500">
										by {provider.customConfig.creator_name}
									</span>
								)}
						</div>
						<p className="mt-0.5 truncate text-xs text-slate-600">
							{provider.description}
						</p>
					</div>

					{/* Selected indicator */}
					<div
						className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
							isSelected
								? "border-orange-500 bg-orange-500"
								: "border-slate-300 bg-white"
						}`}
					>
						{isSelected && (
							<svg
								className="h-3 w-3 text-white"
								viewBox="0 0 12 12"
								fill="none"
								stroke="currentColor"
								strokeWidth="2"
								strokeLinecap="round"
								strokeLinejoin="round"
							>
								<title>Selected</title>
								<polyline points="2.5 6 5 8.5 9.5 4" />
							</svg>
						)}
					</div>
				</button>
			);
		},
		[selectedProvider, handleProviderSelect, configuredProviders],
	);

	if (!isOpen || !mounted) {
		return null;
	}

	return createPortal(
		<div
			className="fixed inset-0 z-[130] flex animate-fadeIn items-center justify-center bg-black/60 backdrop-blur-sm"
			onClick={handleBackdropClick}
			role="presentation"
		>
			<div
				className="relative mx-4 flex max-h-[90vh] w-[90vw] max-w-4xl animate-scaleIn flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]"
				onClick={handleDialogClick}
			>
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />
				<div
					ref={dialogRef}
					className="flex max-h-[90vh] min-h-0 flex-1 flex-col overflow-hidden"
					role="dialog"
					aria-modal="true"
					aria-labelledby="mcp-selection-title"
				>
					{/* Header — Workflow Management style */}
					<div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
						<div className="flex items-center gap-3">
							<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
								<Terminal className="h-5 w-5 text-orange-600" aria-hidden />
							</div>
							<div>
								<h2
									id="mcp-selection-title"
									className="text-lg font-semibold tracking-tight text-slate-900"
								>
									Select MCP Provider
								</h2>
								<p className="mt-0.5 text-sm text-slate-500">
									Choose a provider to connect to
								</p>
							</div>
						</div>
						<button
							type="button"
							onClick={onClose}
							className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
							aria-label="Close"
						>
							<X className="h-5 w-5" />
						</button>
					</div>

					{/* Content — Split Panel */}
					<div className="flex min-h-0 flex-1 flex-row overflow-hidden">
						{/* Left Panel — Provider List */}
						<div className="custom-scrollbar w-[55%] shrink-0 space-y-4 overflow-y-auto border-r border-slate-200 bg-slate-50/50 p-6">
							<div className="text-[0.6rem] font-semibold capitalize text-slate-600">
								Official Integrations
							</div>
							<div className="space-y-1.5">
								{mcpProviders.map(renderProviderRow)}
							</div>

							{(loadingCustomServers || customProviders.length > 0) && (
								<>
									<div className="pt-2 text-[0.6rem] font-semibold capitalize text-slate-600">
										Custom Servers
									</div>
									{loadingCustomServers ? (
										<div className="flex items-center gap-2 text-sm text-slate-600">
											<Loader2 className="h-4 w-4 animate-spin text-orange-500" />
											<span>Loading custom servers...</span>
										</div>
									) : (
										<div className="space-y-1.5">
											{customProviders.map(renderProviderRow)}
										</div>
									)}
								</>
							)}
						</div>

						{/* Right Panel — Configuration */}
						<div className="custom-scrollbar flex flex-1 flex-col overflow-y-auto bg-white p-6">
							{!selectedProviderObj ? (
								<div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
									<div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50">
										<Terminal
											className="h-7 w-7 text-slate-500"
											strokeWidth={1.5}
										/>
									</div>
									<div>
										<p className="text-sm font-medium text-slate-900">
											Select a provider
										</p>
										<p className="mt-1 text-xs text-slate-600">
											Choose an integration from the list to configure it
										</p>
									</div>
								</div>
							) : (
								<div className="space-y-5">
									<div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
										<div
											className="flex-shrink-0 rounded-lg border p-2"
											style={{
												backgroundColor: `rgba(${selectedProviderObj.colorRgb}, 0.1)`,
												borderColor: `rgba(${selectedProviderObj.colorRgb}, 0.28)`,
												color: selectedProviderObj.color,
											}}
										>
											{selectedProviderObj.icon}
										</div>
										<div className="min-w-0">
											<p className="truncate text-sm font-semibold text-slate-900">
												{selectedProviderObj.name}
											</p>
											<p className="mt-0.5 truncate text-xs text-slate-600">
												{selectedProviderObj.description}
											</p>
										</div>
									</div>

									<FormInput
										label="Node Name"
										value={toolName}
										onChange={handleToolNameChange}
										placeholder="Enter a name for this MCP node"
										hint="You can customize the name or keep the default"
										className="!border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-slate-300 focus:!border-orange-500 focus:!ring-orange-500/20"
									/>

									{selectedCustomConfig &&
										!selectedCustomConfig.is_owned_by_current_user && (
											<div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 p-4">
												<div className="flex-1 pr-3">
													<label
														htmlFor="clone-toggle"
														className="cursor-pointer text-sm font-medium text-slate-900"
													>
														Clone to My Servers
													</label>
													<p className="mt-1 text-xs text-slate-600">
														Save this server configuration to your External Tools
														for reuse
													</p>
												</div>
												<button
													type="button"
													id="clone-toggle"
													role="switch"
													aria-checked={shouldClone}
													onClick={() => setShouldClone(!shouldClone)}
													className={`
													relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent
													transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-orange-500/40 focus:ring-offset-2 focus:ring-offset-white
													${shouldClone ? "bg-orange-500" : "bg-slate-400"}
												`}
												>
													<span
														aria-hidden="true"
														className={`
														pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0
														transition duration-200 ease-in-out
														${shouldClone ? "translate-x-5" : "translate-x-0"}
													`}
													/>
												</button>
											</div>
										)}
								</div>
							)}
						</div>
					</div>

					{/* Footer */}
					<div className="flex shrink-0 gap-3 border-t border-slate-200 bg-white px-6 py-4">
						<Button
							type="button"
							onClick={onClose}
							variant="ghost"
							className="flex-1 !rounded-xl !border !border-slate-200 !bg-white !text-slate-700 hover:!border-orange-400 hover:!text-orange-800"
						>
							Cancel
						</Button>
						<Button
							type="button"
							onClick={handleConfirm}
							disabled={!selectedProvider || !toolName.trim()}
							className="flex-1 !rounded-[4px] !border !border-orange-500 !bg-orange-500 !text-white hover:!border-orange-600 hover:!bg-orange-600 disabled:!opacity-50"
						>
							Add MCP Server
						</Button>
					</div>
				</div>
			</div>
		</div>,
		document.body,
	);
}
