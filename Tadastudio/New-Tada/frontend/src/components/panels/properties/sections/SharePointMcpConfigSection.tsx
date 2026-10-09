"use client";

import {
	AlertCircle,
	CheckCircle,
	ChevronDown,
	ChevronRight,
	ExternalLink,
	Info,
	Library,
	Link2,
	Loader2,
	MapPin,
	Plus,
	Trash2,
	Unlink,
	X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import type { McpToolInfo } from "@/components/dialogs/McpToolsViewerModal";
import { SharePointIcon } from "@/components/icons/McpProviderIcons";
import { runtimeConfig } from "@/lib/runtime-config";
import McpToolSelectionCard from "./McpToolSelectionCard";
import SearchablePicker from "./SearchablePicker";
import SharePointFolderTree from "./SharePointFolderTree";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface OAuthStatus {
	is_authenticated: boolean;
	has_token: boolean;
	has_client_registration: boolean;
	token_expired: boolean;
	expires_at: string | null;
	scope: string | null;
}

interface SharePointSite {
	id: string;
	name: string;
	url: string;
	description: string;
}

interface SharePointDrive {
	id: string;
	name: string;
	description: string;
	web_url: string;
	drive_type: string;
}

/** One selected document library with optional folder scoping. */
interface SelectedLibrary {
	driveId: string;
	driveName: string;
	folderIds: Set<string>;
	folderPaths: string[];
}

interface SharePointMcpConfig {
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
		site_id?: string;
		site_name?: string;
		// Multi-library: comma-separated IDs, ||| separated names
		drive_ids?: string;
		drive_names?: string;
		folder_paths?: string;
		// Backwards compat (single)
		drive_id?: string;
		drive_name?: string;
	};
	tool_permissions?: Record<string, boolean>;
}

interface SharePointMcpConfigSectionProps {
	config: SharePointMcpConfig | null;
	onConfigChange: (config: SharePointMcpConfig) => void;
	isConfigured: boolean;
	onAuthStatusChange?: (isAuthenticated: boolean) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Restore selectedLibraries from persisted config metadata. */
function restoreLibraries(config: SharePointMcpConfig | null): SelectedLibrary[] {
	if (!config?.metadata) return [];
	const m = config.metadata;
	const env = config.environment_variables || {};

	// Try multi-library first
	const ids = (m.drive_ids || env.SHAREPOINT_DRIVE_IDS || "").split(",").filter(Boolean);
	const names = (m.drive_names || "").split("|||");
	const allPaths = (m.folder_paths || env.SHAREPOINT_FOLDER_PATHS || "").split(",").filter(Boolean);

	if (ids.length > 0) {
		return ids.map((id: string, i: number) => ({
			driveId: id,
			driveName: names[i] || "",
			folderIds: new Set<string>(),
			folderPaths: i === 0 ? allPaths : [],
		}));
	}

	// Backwards compat: single drive_id
	const singleId = m.drive_id || env.SHAREPOINT_DRIVE_ID || "";
	if (singleId) {
		return [{
			driveId: singleId,
			driveName: m.drive_name || "",
			folderIds: new Set<string>(),
			folderPaths: allPaths,
		}];
	}

	return [];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SharePointMcpConfigSection({
	config,
	onConfigChange,
	isConfigured,
	onAuthStatusChange,
}: SharePointMcpConfigSectionProps) {
	// OAuth state
	const [oauthStatus, setOauthStatus] = useState<OAuthStatus | null>(null);
	const [isConnecting, setIsConnecting] = useState(false);
	const [isDisconnecting, setIsDisconnecting] = useState(false);
	const [statusLoading, setStatusLoading] = useState(true);

	// Site picker
	const [sites, setSites] = useState<SharePointSite[]>([]);
	const [sitesLoading, setSitesLoading] = useState(false);
	const [selectedSiteId, setSelectedSiteId] = useState(
		config?.metadata?.site_id || config?.environment_variables?.SHAREPOINT_SITE_ID || "",
	);
	const [selectedSiteName, setSelectedSiteName] = useState(
		config?.metadata?.site_name || "",
	);

	// Available libraries for the selected site
	const [drives, setDrives] = useState<SharePointDrive[]>([]);
	const [drivesLoading, setDrivesLoading] = useState(false);

	// Selected libraries (multi)
	const [selectedLibraries, setSelectedLibraries] = useState<SelectedLibrary[]>(
		() => restoreLibraries(config),
	);
	const [expandedLibIdx, setExpandedLibIdx] = useState<number | null>(null);

	// URL paste resolution
	const [pasteUrl, setPasteUrl] = useState("");
	const [resolving, setResolving] = useState(false);
	const [resolveError, setResolveError] = useState("");

	// Test & tools
	const [testStatus, setTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
	const [testMessage, setTestMessage] = useState("");
	const [discoveredTools, setDiscoveredTools] = useState<McpToolInfo[]>([]);
	const [toolPermissions, setToolPermissions] = useState<Record<string, boolean>>(
		config?.tool_permissions || {},
	);

	// -----------------------------------------------------------------------
	// OAuth lifecycle
	// -----------------------------------------------------------------------

	useEffect(() => { checkOAuthStatus(); }, []);

	useEffect(() => {
		if (!statusLoading && onAuthStatusChange) {
			onAuthStatusChange(oauthStatus?.is_authenticated ?? false);
		}
	}, [oauthStatus?.is_authenticated, statusLoading, onAuthStatusChange]);

	const checkOAuthStatus = async () => {
		setStatusLoading(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const resp = await fetch(`${apiBaseUrl}/api/microsoft-oauth/status`, { method: "GET", credentials: "include" });
			if (resp.ok) { setOauthStatus(await resp.json()); } else { setOauthStatus(null); }
		} catch { setOauthStatus(null); } finally { setStatusLoading(false); }
	};

	const handleConnect = async () => {
		setIsConnecting(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const resp = await fetch(`${apiBaseUrl}/api/microsoft-oauth/initiate`, { method: "POST", credentials: "include" });
			if (!resp.ok) { const e = await resp.json(); throw new Error(e.detail || "Failed to initiate OAuth"); }
			const data = await resp.json();
			const popup = window.open(data.authorization_url, "microsoft_oauth", "width=600,height=700,left=200,top=100");
			const handleMessage = (event: MessageEvent) => {
				if (event.data?.type === "microsoft_oauth_complete") {
					window.removeEventListener("message", handleMessage);
					popup?.close();
					setIsConnecting(false);
					if (event.data.success) { checkOAuthStatus(); setTestStatus("idle"); setTestMessage(""); }
					else { setTestStatus("error"); setTestMessage(event.data.error || "OAuth authorization failed"); }
				}
			};
			window.addEventListener("message", handleMessage);
			const checkClosed = setInterval(() => {
				if (popup?.closed) { clearInterval(checkClosed); window.removeEventListener("message", handleMessage); setIsConnecting(false); checkOAuthStatus(); }
			}, 500);
		} catch (error) {
			setIsConnecting(false);
			setTestStatus("error");
			setTestMessage(error instanceof Error ? error.message : "Failed to connect to Microsoft");
		}
	};

	const handleDisconnect = async () => {
		setIsDisconnecting(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const resp = await fetch(`${apiBaseUrl}/api/microsoft-oauth/revoke`, { method: "DELETE", credentials: "include" });
			if (resp.ok) { setOauthStatus(null); setTestStatus("idle"); setTestMessage(""); }
		} catch { /* silent */ } finally { setIsDisconnecting(false); checkOAuthStatus(); }
	};

	// -----------------------------------------------------------------------
	// Data loading
	// -----------------------------------------------------------------------

	useEffect(() => { if (oauthStatus?.is_authenticated) { loadSites(); } }, [oauthStatus?.is_authenticated]);
	useEffect(() => { if (selectedSiteId) { loadDrives(selectedSiteId); } }, [selectedSiteId]);

	const loadSites = async () => {
		setSitesLoading(true);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const resp = await fetch(`${apiBaseUrl}/api/microsoft-oauth/sharepoint/sites`, { credentials: "include" });
			if (resp.ok) { setSites((await resp.json()).sites || []); }
		} catch { /* silent */ } finally { setSitesLoading(false); }
	};

	const loadDrives = async (siteId: string) => {
		setDrivesLoading(true);
		setDrives([]);
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const resp = await fetch(`${apiBaseUrl}/api/microsoft-oauth/sharepoint/sites/${siteId}/drives`, { credentials: "include" });
			if (resp.ok) { setDrives((await resp.json()).drives || []); }
		} catch { /* silent */ } finally { setDrivesLoading(false); }
	};

	// -----------------------------------------------------------------------
	// URL resolution
	// -----------------------------------------------------------------------

	const handleResolveUrl = async (url: string) => {
		if (!url.trim()) return;
		setResolving(true);
		setResolveError("");
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const resp = await fetch(`${apiBaseUrl}/api/microsoft-oauth/sharepoint/resolve-url`, {
				method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
				body: JSON.stringify({ url: url.trim() }),
			});
			if (!resp.ok) { setResolveError((await resp.json()).detail || "Could not resolve URL"); return; }
			const data = await resp.json();
			if (data.site_id) {
				setSelectedSiteId(data.site_id);
				setSelectedSiteName(data.site_name || "");
				await loadDrives(data.site_id);
				if (data.drive_id) {
					addLibrary(data.drive_id, data.drive_name || "");
				}
			}
			setPasteUrl("");
		} catch { setResolveError("Failed to resolve URL"); } finally { setResolving(false); }
	};

	// -----------------------------------------------------------------------
	// Library management (multi-select)
	// -----------------------------------------------------------------------

	const addLibrary = useCallback((driveId: string, driveName: string) => {
		setSelectedLibraries((prev) => {
			if (prev.some((l) => l.driveId === driveId)) return prev;
			return [...prev, { driveId, driveName, folderIds: new Set<string>(), folderPaths: [] }];
		});
	}, []);

	const removeLibrary = useCallback((index: number) => {
		setSelectedLibraries((prev) => prev.filter((_, i) => i !== index));
		setExpandedLibIdx((prev) => {
			if (prev === index) return null;
			if (prev !== null && prev > index) return prev - 1;
			return prev;
		});
	}, []);

	const updateLibraryFolders = useCallback((index: number, folderIds: Set<string>, folderPaths: string[]) => {
		setSelectedLibraries((prev) =>
			prev.map((lib, i) => (i === index ? { ...lib, folderIds, folderPaths } : lib)),
		);
	}, []);

	// Which drives are still available to add (not yet selected)
	const availableDrives = drives.filter((d) => !selectedLibraries.some((l) => l.driveId === d.id));

	// -----------------------------------------------------------------------
	// Config emission
	// -----------------------------------------------------------------------

	const buildEnvVars = useCallback(() => {
		const env: Record<string, string> = {};
		if (selectedSiteId) env.SHAREPOINT_SITE_ID = selectedSiteId;
		const driveIds = selectedLibraries.map((l) => l.driveId);
		if (driveIds.length > 0) env.SHAREPOINT_DRIVE_IDS = driveIds.join(",");
		const allPaths = selectedLibraries.flatMap((l) => l.folderPaths);
		if (allPaths.length > 0) env.SHAREPOINT_FOLDER_PATHS = allPaths.join(",");
		return env;
	}, [selectedSiteId, selectedLibraries]);

	const updateConfig = useCallback(() => {
		const envVars = buildEnvVars();
		const newConfig: SharePointMcpConfig = {
			server_name: "SharePoint MCP Server",
			connection_type: "stdio",
			command: "python",
			args: ["-m", "backend.tools.sharepoint_mcp"],
			auth_type: "oauth",
			auth_config: { provider: "microsoft" },
			provider: "sharepoint",
			description: "SharePoint integration for document libraries, sites, and file access",
			environment_variables: envVars,
			metadata: {
				site_id: selectedSiteId,
				site_name: selectedSiteName,
				drive_ids: selectedLibraries.map((l) => l.driveId).join(","),
				drive_names: selectedLibraries.map((l) => l.driveName).join("|||"),
				folder_paths: selectedLibraries.flatMap((l) => l.folderPaths).join(","),
			},
		};
		onConfigChange(newConfig);
	}, [buildEnvVars, onConfigChange, selectedSiteId, selectedSiteName, selectedLibraries]);

	useEffect(() => {
		if (oauthStatus?.is_authenticated) { updateConfig(); }
	}, [selectedSiteId, selectedLibraries, oauthStatus?.is_authenticated, updateConfig]);

	// -----------------------------------------------------------------------
	// Handlers
	// -----------------------------------------------------------------------

	const handleSiteChange = (siteId: string) => {
		const site = sites.find((s) => s.id === siteId);
		setSelectedSiteId(siteId);
		setSelectedSiteName(site?.name || "");
		setSelectedLibraries([]);
		setExpandedLibIdx(null);
	};

	const handleAddLibrary = (driveId: string) => {
		const drive = drives.find((d) => d.id === driveId);
		if (drive) addLibrary(drive.id, drive.name);
	};

	const handleTestConnection = async () => {
		if (!oauthStatus?.is_authenticated) { setTestStatus("error"); setTestMessage("Please connect to Microsoft first"); return; }
		setTestStatus("testing"); setTestMessage("");
		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const resp = await fetch(`${apiBaseUrl}/api/microsoft-oauth/test`, { method: "POST", credentials: "include" });
			const data = await resp.json();
			if (data.status === "success") {
				setTestStatus("success"); setTestMessage(data.message);
				try {
					const envVars = buildEnvVars();
					const dr = await fetch(`${apiBaseUrl}/api/graph/test-mcp-server`, {
						method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
						body: JSON.stringify({ server_name: "SharePoint MCP Server", connection_type: "stdio", command: "python", args: ["-m", "backend.tools.sharepoint_mcp"], auth_type: "oauth", auth_config: { provider: "microsoft" }, environment_variables: envVars, timeout_seconds: 60 }),
					});
					const dd = await dr.json();
					if (dd.success && dd.capabilities?.tools) {
						const tools: McpToolInfo[] = dd.capabilities.tools.map(
							(t: { name?: string; description?: string; input_schema?: Record<string, unknown> }) => ({ name: t.name || "Unknown Tool", description: t.description || "No description available", input_schema: t.input_schema || undefined }),
						);
						setDiscoveredTools(tools);
						setTestMessage(`Connected successfully. Found ${tools.length} tools.`);
					}
				} catch { /* non-critical */ }
			} else { setTestStatus("error"); setTestMessage(data.message || "Connection test failed"); }
		} catch (error) { setTestStatus("error"); setTestMessage(error instanceof Error ? error.message : "Connection test failed"); }
	};

	const handleToolPermissionsChange = useCallback(
		(permissions: Record<string, boolean>) => { setToolPermissions(permissions); onConfigChange({ tool_permissions: permissions } as any); },
		[onConfigChange],
	);

	const isAuthenticated = oauthStatus?.is_authenticated ?? false;

	const scopeSummary = (() => {
		const parts: string[] = [];
		if (selectedSiteName) parts.push(selectedSiteName);
		if (selectedLibraries.length === 1) parts.push(selectedLibraries[0].driveName);
		else if (selectedLibraries.length > 1) parts.push(`${selectedLibraries.length} libraries`);
		const totalFolders = selectedLibraries.reduce((n, l) => n + l.folderPaths.length, 0);
		if (totalFolders > 0) parts.push(`${totalFolders} folder(s)`);
		return parts.length > 0 ? parts.join(" / ") : "All sites";
	})();

	// -----------------------------------------------------------------------
	// Render
	// -----------------------------------------------------------------------

	return (
		<div className="space-y-5">
			{/* Section Label */}
			<div className="text-[0.6rem] font-semibold capitalize text-gray-600">
				SharePoint Configuration
			</div>

			{/* Info Card */}
			<div className="rounded-[4px] border border-blue-200 bg-white p-4 shadow-sm">
				<div className="flex items-start gap-3">
					<div className="rounded-[4px] border border-blue-200 bg-blue-50 p-2">
						<Info className="h-4 w-4 text-blue-800" />
					</div>
					<div className="flex-1">
						<h4 className="mb-1 text-sm font-medium text-blue-900">About SharePoint MCP</h4>
						<p className="mb-2 text-xs text-gray-600">
							Connect to SharePoint using your Microsoft account.
							Select a site, one or more document libraries, and optional folders
							to scope what the agent can search and access.
						</p>
						<a href="https://learn.microsoft.com/en-us/graph/overview" target="_blank" rel="noopener noreferrer"
							className="flex items-center gap-1 text-xs text-blue-900 transition-colors hover:text-slate-900">
							Learn more about Microsoft Graph API <ExternalLink className="w-3 h-3" />
						</a>
					</div>
				</div>
			</div>

			{/* OAuth Connection Status */}
			<div className={`rounded-[4px] border bg-white p-4 shadow-sm ${isAuthenticated ? "border-emerald-300" : "border-amber-300"}`}>
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-3">
						{statusLoading ? (
							<div className="rounded-[4px] border border-gray-200 bg-gray-50 p-2"><Loader2 className="h-5 w-5 animate-spin text-gray-600" /></div>
						) : isAuthenticated ? (
							<div className="rounded-[4px] border border-emerald-200 bg-gray-50 p-2"><CheckCircle className="h-5 w-5 text-emerald-700" /></div>
						) : (
							<div className="rounded-[4px] border border-amber-200 bg-gray-50 p-2"><AlertCircle className="h-5 w-5 text-amber-800" /></div>
						)}
						<div>
							<p className={`text-sm font-medium ${isAuthenticated ? "text-emerald-900" : "text-amber-900"}`}>
								{statusLoading ? "Checking connection..." : isAuthenticated ? "Connected to Microsoft" : "Not connected"}
							</p>
							{isAuthenticated && oauthStatus?.expires_at && (
								<p className="mt-0.5 text-[10px] text-gray-600">Token expires: {new Date(oauthStatus.expires_at).toLocaleString()}</p>
							)}
						</div>
					</div>
					{!statusLoading && (isAuthenticated ? (
						<Button onClick={handleDisconnect} disabled={isDisconnecting} variant="danger" size="sm"
							icon={isDisconnecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Unlink className="w-4 h-4" />}>Disconnect</Button>
					) : (
						<Button onClick={handleConnect} disabled={isConnecting} size="sm"
							icon={isConnecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link2 className="w-4 h-4" />}>
							{isConnecting ? "Connecting..." : "Connect"}
						</Button>
					))}
				</div>
			</div>

			{/* Scope Configuration */}
			{isAuthenticated && (
				<div className="space-y-4 rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
					{/* Header */}
					<div className="flex items-center gap-2">
						<MapPin className="h-3.5 w-3.5 text-blue-800" />
						<span className="text-xs font-medium text-gray-800">Search Scope</span>
					</div>

					{/* Paste URL bar */}
					<div>
						<div className="flex gap-2">
							<input type="text" value={pasteUrl}
								onChange={(e) => { setPasteUrl(e.target.value); setResolveError(""); }}
								onKeyDown={(e) => { if (e.key === "Enter") handleResolveUrl(pasteUrl); }}
								placeholder="Paste a SharePoint URL to auto-select site & library"
								className="flex-1 rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-xs text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40" />
							<button type="button" disabled={!pasteUrl.trim() || resolving} onClick={() => handleResolveUrl(pasteUrl)}
								className="shrink-0 rounded-[4px] border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-medium text-blue-900 transition-colors hover:border-orange-300 hover:bg-white hover:text-slate-900 disabled:opacity-40">
								{resolving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Resolve"}
							</button>
						</div>
						{resolveError && <p className="mt-1 text-[10px] text-red-700">{resolveError}</p>}
					</div>

					{/* Separator */}
					<div className="flex items-center gap-3">
						<div className="flex-1 border-t border-gray-200" />
						<span className="text-[10px] text-gray-600">or browse</span>
						<div className="flex-1 border-t border-gray-200" />
					</div>

					{/* Site Picker */}
					<div>
						<label className="mb-2 flex items-center gap-1.5 text-xs font-medium text-gray-800">
							<MapPin className="w-3 h-3" /> SharePoint Site
						</label>
						<SearchablePicker value={selectedSiteId} onChange={handleSiteChange}
							options={sites.map((s) => ({ value: s.id, label: s.name, description: s.url }))}
							placeholder="All sites (no filter)" searchPlaceholder="Search sites..."
							emptyMessage="No sites match your search" loading={sitesLoading} loadingMessage="Loading sites..." />
					</div>

					{/* Document Libraries (multi-select) */}
					{selectedSiteId && (
						<div>
							<label className="mb-2 flex items-center gap-1.5 text-xs font-medium text-gray-800">
								<Library className="w-3 h-3" /> Document Libraries
							</label>

							{/* Selected libraries list */}
							{selectedLibraries.length > 0 && (
								<div className="space-y-2 mb-3">
									{selectedLibraries.map((lib, idx) => {
										const isExpanded = expandedLibIdx === idx;
										return (
											<div key={lib.driveId}
												className="overflow-hidden rounded-[4px] border border-gray-200 bg-white">
												{/* Library header */}
												<div className="flex items-center gap-2 px-3 py-2">
													<button type="button" onClick={() => setExpandedLibIdx(isExpanded ? null : idx)}
														className="text-gray-600 transition-colors hover:text-slate-900">
														{isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
													</button>
													<Library className="w-3.5 h-3.5 shrink-0 text-blue-800" />
													<span className="flex-1 truncate text-xs text-gray-900">{lib.driveName}</span>
													{lib.folderPaths.length > 0 && (
														<span className="text-[10px] text-gray-600">
															{lib.folderPaths.length} folder(s)
														</span>
													)}
													<button type="button" onClick={() => removeLibrary(idx)}
														className="rounded p-1 text-gray-600 transition-colors hover:bg-red-50 hover:text-red-800">
														<Trash2 className="w-3 h-3" />
													</button>
												</div>

												{/* Expanded: folder tree */}
												{isExpanded && (
													<div className="px-3 pb-3 space-y-2">
														<div className="overflow-hidden rounded-[4px] border border-gray-200 bg-gray-50">
															<SharePointFolderTree
																driveId={lib.driveId}
																selectedFolderIds={lib.folderIds}
																onSelectionChange={(ids, paths) => updateLibraryFolders(idx, ids, paths)}
															/>
														</div>
														{lib.folderPaths.length > 0 && (
															<div className="flex flex-wrap gap-1.5">
																{lib.folderPaths.map((path) => {
																	const name = path.split("/").filter(Boolean).pop() || path;
																	return (
																		<span key={path}
																			className="inline-flex items-center gap-1 rounded-[4px] border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] text-blue-900">
																			{name}
																			<button type="button"
																				onClick={() => {
																					const newPaths = lib.folderPaths.filter((p) => p !== path);
																					updateLibraryFolders(idx, new Set<string>(), newPaths);
																				}}
																				className="hover:text-slate-900 transition-colors">
																				<X className="w-2.5 h-2.5" />
																			</button>
																		</span>
																	);
																})}
															</div>
														)}
														<p className="text-[10px] text-gray-600">
															Select folders to narrow scope. Leave empty to search the entire library.
														</p>
													</div>
												)}
											</div>
										);
									})}
								</div>
							)}

							{/* Add library picker */}
							{!drivesLoading && availableDrives.length > 0 && (
								<div className="flex items-center gap-2">
									<Plus className="h-3.5 w-3.5 shrink-0 text-gray-600" />
									<div className="flex-1">
										<SearchablePicker value="" onChange={handleAddLibrary}
											options={availableDrives.map((d) => ({ value: d.id, label: d.name, description: d.description || d.drive_type }))}
											placeholder={selectedLibraries.length === 0 ? "Select a document library..." : "Add another library..."}
											searchPlaceholder="Search libraries..." emptyMessage="No more libraries available"
											loading={drivesLoading} loadingMessage="Loading libraries..." clearable={false} />
									</div>
								</div>
							)}
							{drivesLoading && (
								<div className="flex items-center gap-2 py-2 px-1">
									<Loader2 className="h-3.5 w-3.5 animate-spin text-gray-600" />
									<span className="text-xs text-gray-600">Loading libraries...</span>
								</div>
							)}
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

			{/* Test Connection */}
			{isAuthenticated && (
				<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
					<div className="mb-3 flex items-center justify-between">
						<div>
							<h4 className="text-sm font-medium text-gray-900">Test Connection</h4>
							<p className="text-[10px] text-gray-600">Verify Microsoft Graph API access</p>
						</div>
						<Button onClick={handleTestConnection} disabled={testStatus === "testing"}
							variant={testStatus === "success" ? "success" : testStatus === "error" ? "danger" : "primary"} size="sm"
							icon={testStatus === "testing" ? <Loader2 className="w-4 h-4 animate-spin" /> : testStatus === "success" ? <CheckCircle className="w-4 h-4" /> : testStatus === "error" ? <AlertCircle className="w-4 h-4" /> : undefined}>
							{testStatus === "testing" ? "Testing..." : testStatus === "success" ? "Success" : testStatus === "error" ? "Failed" : "Test"}
						</Button>
					</div>
					{testMessage && (
						<div className={`rounded-[4px] border p-3 text-xs ${testStatus === "success" ? "border-[#0DA931] bg-[#F1F8E9] text-[#0DA931]" : testStatus === "error" ? "border-red-400 bg-red-50 text-red-600" : "border-slate-200 bg-white text-slate-700"}`}>
							{testMessage}
						</div>
					)}
				</div>
			)}

			{/* Discovered Tools */}
			{discoveredTools.length > 0 && (
				<McpToolSelectionCard tools={discoveredTools} toolPermissions={toolPermissions}
					onToolPermissionsChange={handleToolPermissionsChange} providerColor="#0078D4"
					providerColorRgb="0, 120, 212" providerIcon={SharePointIcon} serverName="SharePoint" />
			)}

			{/* Not connected */}
			{!isAuthenticated && !statusLoading && (
				<div className="text-center py-4">
					<p className="text-xs text-gray-600">Connect to Microsoft to configure SharePoint access</p>
				</div>
			)}
		</div>
	);
}
