"use client";

import {
	CheckSquare,
	Copy,
	Download,
	Edit,
	Globe,
	Loader2,
	Lock,
	Plus,
	Square,
	Trash2,
	Upload,
	Users,
	Wrench,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import Button from "@/components/ui/Button";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import Toggle from "@/components/ui/Toggle";
import { useToast } from "@/contexts/ToastContext";
import { type McpServerInfo, userSettingsAPI } from "@/lib/user-settings-api";
import McpServerConfigModal from "../dialogs/McpServerConfigModal";
import OfficialIntegrationsSection from "./OfficialIntegrationsSection";

// MCP Logo Component - inline SVG that respects theme colors
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

const ConnectionTypeBadge = ({ type }: { type: string }) => (
	<span
		className="px-2 py-1 text-xs font-medium rounded-md"
		style={{
			background:
				type === "stdio"
					? "rgba(59, 130, 246, 0.1)"
					: "rgba(16, 185, 129, 0.1)",
			color: type === "stdio" ? "rgb(59, 130, 246)" : "rgb(16, 185, 129)",
			border: `1px solid ${
				type === "stdio" ? "rgba(59, 130, 246, 0.3)" : "rgba(16, 185, 129, 0.3)"
			}`,
		}}
	>
		{type.toUpperCase()}
	</span>
);

const SharingBadge = ({
	visibility,
	sharedWithGroupIds,
	sharedWithGroupNames,
}: {
	visibility: "private" | "shared";
	sharedWithGroupIds: string[];
	sharedWithGroupNames: string[];
}) => {
	const isShared = visibility === "shared";
	const isEveryone =
		isShared &&
		(sharedWithGroupIds.length === 0 ||
			sharedWithGroupIds.includes("__all__"));
	const groupCount = sharedWithGroupIds.filter((id) => id !== "__all__").length;

	let label = "Private";
	let Icon = Lock;
	let bgColor = "rgba(107, 114, 128, 0.1)";
	let textColor = "rgb(156, 163, 175)";
	let borderColor = "rgba(107, 114, 128, 0.3)";

	if (isShared && isEveryone) {
		label = "Shared";
		Icon = Globe;
		bgColor = "rgba(16, 185, 129, 0.1)";
		textColor = "rgb(16, 185, 129)";
		borderColor = "rgba(16, 185, 129, 0.3)";
	} else if (isShared && groupCount > 0) {
		label =
			sharedWithGroupNames.length > 0
				? sharedWithGroupNames.join(", ")
				: `${groupCount} group${groupCount !== 1 ? "s" : ""}`;
		Icon = Users;
		bgColor = "rgba(59, 130, 246, 0.1)";
		textColor = "rgb(59, 130, 246)";
		borderColor = "rgba(59, 130, 246, 0.3)";
	}

	return (
		<span
			className="px-2 py-1 text-xs font-medium rounded-md flex items-center gap-1 max-w-[200px] truncate"
			style={{
				background: bgColor,
				color: textColor,
				border: `1px solid ${borderColor}`,
			}}
			title={isShared && groupCount > 0 ? `Shared with: ${sharedWithGroupNames.join(", ")}` : label}
		>
			<Icon className="w-3 h-3 flex-shrink-0" />
			{label}
		</span>
	);
};

export default function ExternalToolsTab() {
	const [mcpServers, setMcpServers] = useState<McpServerInfo[]>([]);
	const [loading, setLoading] = useState(true);
	const [loadError, setLoadError] = useState(false);
	const [selectedServer, setSelectedServer] = useState<McpServerInfo | null>(
		null,
	);
	const [showConfigModal, setShowConfigModal] = useState(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const [serverToDelete, setServerToDelete] = useState<string | null>(null);
	const [importing, setImporting] = useState(false);
	const [exporting, setExporting] = useState(false);
	const [selectedServerIds, setSelectedServerIds] = useState<Set<string>>(
		new Set(),
	);
	const [exportingIndividual, setExportingIndividual] = useState<string | null>(
		null,
	);
	const [cloningServerId, setCloningServerId] = useState<string | null>(null);
	const { showToast } = useToast();
	const fileInputRef = useRef<HTMLInputElement>(null);

	useEffect(() => {
		void loadMcpServers();
	}, []);

	const loadMcpServers = async () => {
		try {
			setLoading(true);
			setLoadError(false);
			const servers = await userSettingsAPI.listMcpServers();
			setMcpServers(servers);
		} catch (error) {
			console.error("Failed to load MCP servers:", error);
			setLoadError(true);
			showToast("error", "Failed to load MCP servers");
		} finally {
			setLoading(false);
		}
	};

	const handleAddServer = () => {
		setSelectedServer(null);
		setShowConfigModal(true);
	};

	const handleEditServer = (server: McpServerInfo) => {
		setSelectedServer(server);
		setShowConfigModal(true);
	};

	const handleToggleServer = async (
		serverName: string,
		currentStatus: boolean,
	) => {
		// Optimistic update - update UI immediately
		setMcpServers((prevServers) =>
			prevServers.map((server) =>
				server.server_name === serverName
					? { ...server, is_active: !currentStatus }
					: server,
			),
		);

		try {
			await userSettingsAPI.toggleMcpServer(serverName);
			showToast(
				"success",
				`MCP server ${!currentStatus ? "enabled" : "disabled"} successfully`,
			);
		} catch (error) {
			console.error("Failed to toggle MCP server:", error);
			showToast("error", "Failed to toggle server");
			// Revert optimistic update on error
			setMcpServers((prevServers) =>
				prevServers.map((server) =>
					server.server_name === serverName
						? { ...server, is_active: currentStatus }
						: server,
				),
			);
		}
	};

	const handleDeleteClick = (serverId: string) => {
		setServerToDelete(serverId);
		setShowDeleteConfirm(true);
	};

	const handleConfirmDelete = async () => {
		if (!serverToDelete) return;

		try {
			await userSettingsAPI.deleteMcpServer(serverToDelete);
			showToast("success", "MCP server deleted successfully");
			await loadMcpServers();
		} catch (error) {
			console.error("Failed to delete MCP server:", error);
			showToast("error", "Failed to delete server");
		} finally {
			setServerToDelete(null);
		}
	};

	const handleSaveComplete = async () => {
		await loadMcpServers();
	};

	const handleToggleSelectAll = () => {
		// Select all - only include servers with valid IDs
		const validIds = mcpServers
			.map((s) => s.id)
			.filter((id): id is string => id !== undefined && id !== null);

		if (selectedServerIds.size === validIds.length && validIds.length > 0) {
			// Deselect all
			setSelectedServerIds(new Set());
		} else {
			// Select all
			setSelectedServerIds(new Set(validIds));
		}
	};

	const handleToggleSelect = (serverId: string) => {
		setSelectedServerIds((prev) => {
			const next = new Set(prev);
			if (next.has(serverId)) {
				next.delete(serverId);
			} else {
				next.add(serverId);
			}
			return next;
		});
	};

	const handleExportSelected = async () => {
		try {
			setExporting(true);
			const serverIdsArray = Array.from(selectedServerIds);
			const response =
				await userSettingsAPI.exportSelectedMcpServers(serverIdsArray);

			// Create a downloadable JSON file
			const jsonStr = JSON.stringify(response, null, 2);
			const blob = new Blob([jsonStr], { type: "application/json" });
			const url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			link.download = `mcp-servers-${selectedServerIds.size}.json`;
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			URL.revokeObjectURL(url);

			const serverCount = Object.keys(response.mcpServers).length;
			showToast(
				"success",
				`Exported ${serverCount} selected MCP server(s) successfully`,
			);
		} catch (error) {
			console.error("Failed to export selected MCP servers:", error);
			showToast("error", "Failed to export selected MCP servers");
		} finally {
			setExporting(false);
		}
	};

	const handleExportIndividual = async (
		serverId: string,
		serverName: string,
	) => {
		try {
			setExportingIndividual(serverId);
			const response = await userSettingsAPI.exportSelectedMcpServers([
				serverId,
			]);

			// Create a downloadable JSON file
			const jsonStr = JSON.stringify(response, null, 2);
			const blob = new Blob([jsonStr], { type: "application/json" });
			const url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			// Use server name for the filename
			const safeName = serverName.replace(/[^a-z0-9_-]/gi, "_");
			link.download = `mcp-server-${safeName}.json`;
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			URL.revokeObjectURL(url);

			showToast("success", `Exported "${serverName}" successfully`);
		} catch (error) {
			console.error(`Failed to export MCP server "${serverName}":`, error);
			showToast("error", `Failed to export "${serverName}"`);
		} finally {
			setExportingIndividual(null);
		}
	};

	const handleCloneServer = async (server: McpServerInfo) => {
		if (!server.id) return;
		try {
			setCloningServerId(server.id);
			await userSettingsAPI.cloneMcpServer(server.id, server.server_name);
			showToast("success", `Cloned "${server.server_name}" to your servers`);
			await loadMcpServers();
		} catch (error) {
			console.error("Failed to clone server:", error);
			showToast("error", "Failed to clone server");
		} finally {
			setCloningServerId(null);
		}
	};

	const handleImportClick = () => {
		fileInputRef.current?.click();
	};

	const handleImportFileChange = async (
		event: React.ChangeEvent<HTMLInputElement>,
	) => {
		const file = event.target.files?.[0];
		if (!file) return;

		try {
			setImporting(true);

			// Read file content
			const fileContent = await file.text();
			let mcpServers: Record<string, any>;

			try {
				const parsed = JSON.parse(fileContent);
				// Support both formats: {mcpServers: {...}} and direct server object
				mcpServers = parsed.mcpServers || parsed;
			} catch (e) {
				showToast("error", "Invalid JSON file");
				return;
			}

			// Import the servers
			const response = await userSettingsAPI.importMcpServers({
				mcpServers,
				overwrite_existing: false, // Default: skip existing servers
			});

			// Build detailed message
			const messageParts = [];
			if (response.imported_count > 0) {
				messageParts.push(`${response.imported_count} server(s) imported`);
			}
			if (response.skipped_count > 0) {
				messageParts.push(`${response.skipped_count} skipped (already exist)`);
			}
			if (response.failed_count > 0) {
				messageParts.push(`${response.failed_count} failed`);
			}

			const message = messageParts.join(", ");

			if (response.success) {
				showToast("success", message || "Import completed");
			} else {
				showToast("warning", message || "Import completed with errors");
				// Log errors for debugging
				if (response.errors.length > 0) {
					console.error("Import errors:", response.errors);
				}
			}

			// Reload servers list
			await loadMcpServers();
		} catch (error) {
			console.error("Failed to import MCP servers:", error);
			showToast("error", "Failed to import MCP servers");
		} finally {
			setImporting(false);
			// Reset file input
			if (fileInputRef.current) {
				fileInputRef.current.value = "";
			}
		}
	};

	// Calculate the number of servers with valid IDs
	const validServersCount = mcpServers.filter((s) => s.id).length;
	const allSelected =
		validServersCount > 0 && selectedServerIds.size === validServersCount;

	return (
		<div className="p-6">
			{/* Header */}
			<div className="mb-6 flex items-center justify-between">
				<div className="flex items-center gap-3">
					<div className="flex items-center justify-center rounded-[4px] border border-orange-200 bg-white p-2">
						<Wrench className="h-6 w-6 text-orange-600" />
					</div>
					<div>
						<h2 className="text-xl font-semibold tracking-tight text-slate-900">External Tools</h2>
						<p className="mt-1 text-sm text-slate-600">
							Configure MCP servers and official integrations for agent tools
						</p>
					</div>
				</div>
			</div>

			{/* Official Integrations Section */}
			<OfficialIntegrationsSection />

			{/* Custom MCP Servers Header */}
			<div className="mb-4 flex items-center justify-between">
				<div>
					<h3 className="text-lg font-semibold text-slate-900">Custom MCP Servers</h3>
					<p className="mt-0.5 text-sm text-slate-600">Add your own MCP servers with custom configurations</p>
				</div>

				{/* Action Buttons */}
				{!loading && !loadError && (
					<div className="flex items-center gap-2">
						{/* Select/Deselect All Button - only show when there are servers */}
						{validServersCount > 0 && (
							<button
								type="button"
								onClick={handleToggleSelectAll}
								className="flex items-center gap-2 rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-800 transition-colors hover:border-orange-400 hover:text-slate-900"
								title={allSelected ? "Deselect all" : "Select all"}
							>
								{allSelected ? (
									<CheckSquare className="w-5 h-5" />
								) : (
									<Square className="w-5 h-5" />
								)}
								{allSelected ? "Deselect All" : "Select All"}
							</button>
						)}

						{/* Export Button - always visible, disabled when no selection */}
						<button
							type="button"
							onClick={handleExportSelected}
							disabled={exporting || selectedServerIds.size === 0}
							className="flex items-center gap-2 rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-800 transition-colors hover:border-orange-400 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
							title={
								selectedServerIds.size === 0
									? "Please select at least one server to export"
									: `Export ${selectedServerIds.size} selected server(s)`
							}
						>
							{exporting ? (
								<Loader2 className="w-5 h-5 animate-spin text-orange-500" />
							) : (
								<Download className="w-5 h-5" />
							)}
							Export
						</button>

						{/* Import Button */}
						<button
							type="button"
							onClick={handleImportClick}
							disabled={importing}
							className="flex items-center gap-2 rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-800 transition-colors hover:border-orange-400 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
							title="Import MCP servers from .mcp.json"
						>
							{importing ? (
								<Loader2 className="w-5 h-5 animate-spin text-orange-500" />
							) : (
								<Upload className="w-5 h-5" />
							)}
							Import
						</button>

						{/* Add Server Button */}
						<Button
							onClick={handleAddServer}
							icon={<Plus className="w-4 h-4" />}
						>
							Add MCP Server
						</Button>

						{/* Hidden File Input */}
						<input
							ref={fileInputRef}
							type="file"
							accept=".json,.mcp.json"
							onChange={handleImportFileChange}
							className="hidden"
						/>
					</div>
				)}
			</div>

			{/* Loading State */}
			{loading && (
				<div className="flex flex-col items-center justify-center py-16">
					<Loader2 className="mb-4 h-8 w-8 animate-spin text-orange-600" />
					<p className="text-slate-600">Loading MCP servers...</p>
				</div>
			)}

			{/* Error State */}
			{!loading && loadError && (
				<div className="flex flex-col items-center justify-center px-6 py-16">
					<div className="mb-4 rounded-full border border-red-200 bg-white p-4">
						<McpLogo className="h-12 w-12 text-red-600" />
					</div>
					<h3 className="mb-2 text-lg font-semibold text-slate-900">Failed to Load MCP Servers</h3>
					<p className="mb-6 max-w-md text-center text-slate-600">
						An error occurred while loading your MCP server configuration. Please try again.
					</p>
					<button
						type="button"
						onClick={() => void loadMcpServers()}
						className="flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-4 py-2 font-medium text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-colors hover:bg-orange-600"
					>
						Retry
					</button>
				</div>
			)}

			{/* Empty State */}
			{!loading && !loadError && mcpServers.length === 0 && (
				<div className="flex flex-col items-center justify-center px-6 py-16">
					<div className="mb-4 rounded-full border border-slate-200 bg-white p-4">
						<McpLogo className="h-12 w-12 text-slate-500" />
					</div>
					<h3 className="mb-2 text-lg font-semibold text-slate-900">No MCP Servers Configured</h3>
					<p className="mb-6 max-w-md text-center text-slate-600">
						Add custom MCP servers to extend your agents with external tools and capabilities
					</p>
					<button
						type="button"
						onClick={handleAddServer}
						className="flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-4 py-2 font-medium text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-colors hover:bg-orange-600"
					>
						<Plus className="h-5 w-5" />
						Add MCP Server
					</button>
				</div>
			)}

			{/* MCP Servers List */}
			{!loading && mcpServers.length > 0 && (
				<div className="space-y-4">
					{/* Server Cards */}
					{mcpServers
						.filter(
							(s): s is McpServerInfo & { id: string } =>
								s.id !== undefined && s.id !== null,
						)
						.map((server) => {
							const serverId = server.id; // Type-safe: server.id is guaranteed to be string
							const isOwned = server.is_owned_by_current_user !== false;
							return (
								<div
									key={`${server.server_name}-${server.creator_id || "self"}`}
									className="rounded-[4px] border border-slate-200 bg-white p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400"
								>
									<div className="flex items-start justify-between gap-4">
										{/* Left: Checkbox, Logo, Name, and Description */}
										<div className="flex min-w-0 flex-1 items-start gap-3">
											{/* Selection Checkbox - only for owned servers */}
											{isOwned && (
												<button
													type="button"
													onClick={() => handleToggleSelect(serverId)}
													className="mt-0.5 flex-shrink-0 rounded p-1 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
													title={
														selectedServerIds.has(serverId)
															? "Deselect server"
															: "Select server"
													}
												>
													{selectedServerIds.has(serverId) ? (
														<CheckSquare className="h-5 w-5 text-orange-600" />
													) : (
														<Square className="h-5 w-5 text-slate-400" />
													)}
												</button>
											)}
											<McpLogo className="mt-0.5 h-6 w-6 flex-shrink-0 text-orange-600" />
											<div className="min-w-0 flex-1">
												<div className="flex flex-wrap items-center gap-2">
													<h3 className="text-lg font-semibold text-slate-900">
														{server.server_name}
													</h3>
													<ConnectionTypeBadge type={server.connection_type} />
													<SharingBadge
														visibility={server.visibility}
														sharedWithGroupIds={server.shared_with_group_ids || []}
														sharedWithGroupNames={server.shared_with_group_names || []}
													/>
													{!isOwned && (
														<span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-800">
															Shared by {server.creator_name || "unknown"}
														</span>
													)}
													{server.clone_count > 0 && isOwned && (
														<span className="text-xs text-slate-600">
															{server.clone_count}{" "}
															{server.clone_count === 1 ? "clone" : "clones"}
														</span>
													)}
													{server.is_template && (
														<span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-800">
															Cloned
														</span>
													)}
												</div>
												{server.description && (
													<p className="mt-1 text-sm text-slate-600">
														{server.description}
													</p>
												)}
											</div>
										</div>

										{/* Right: Toggle and Action Buttons */}
										<div className="flex flex-shrink-0 items-center gap-3">
											{isOwned ? (
												<>
													<Toggle
														checked={server.is_active}
														onChange={() =>
															handleToggleServer(
																server.server_name,
																server.is_active,
															)
														}
														size="sm"
														label=""
														activeColor="#f97316"
													/>

													{/* Export Individual Button */}
													<button
														type="button"
														onClick={() =>
															handleExportIndividual(serverId, server.server_name)
														}
														disabled={exportingIndividual === serverId}
														className="rounded-[4px] border border-slate-200 bg-white p-2 text-sm font-medium text-slate-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
														title="Export this server"
													>
														{exportingIndividual === serverId ? (
															<Loader2 className="h-4 w-4 animate-spin text-orange-500" />
														) : (
															<Download className="h-4 w-4" />
														)}
													</button>

													<button
														type="button"
														onClick={() => handleEditServer(server)}
														className="rounded-[4px] border border-slate-200 bg-white p-2 text-sm font-medium text-slate-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
														title="Edit server"
													>
														<Edit className="h-4 w-4" />
													</button>

													<button
														type="button"
														onClick={() => handleDeleteClick(serverId)}
														className="rounded-[4px] border border-slate-200 bg-white p-2 text-sm font-medium text-red-600 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-700"
														title="Delete server"
													>
														<Trash2 className="h-4 w-4" />
													</button>
												</>
											) : (
												<button
													type="button"
													onClick={() => handleCloneServer(server)}
													disabled={cloningServerId === serverId}
													className="rounded-[4px] border border-violet-200 bg-white p-2 text-sm font-medium text-violet-800 transition-colors hover:border-violet-400 hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-50"
													title="Clone to my servers"
												>
													{cloningServerId === serverId ? (
														<Loader2 className="h-4 w-4 animate-spin text-orange-500" />
													) : (
														<Copy className="h-4 w-4" />
													)}
												</button>
											)}
										</div>
									</div>
								</div>
							);
						})}
				</div>
			)}

			{/* MCP Server Configuration Modal */}
			{showConfigModal && (
				<McpServerConfigModal
					isOpen={showConfigModal}
					selectedServer={selectedServer}
					onClose={() => {
						setShowConfigModal(false);
						setSelectedServer(null);
					}}
					onSaveComplete={handleSaveComplete}
				/>
			)}

			{/* Delete Confirmation Dialog */}
			<ConfirmDialog
				isOpen={showDeleteConfirm}
				onClose={() => {
					setShowDeleteConfirm(false);
					setServerToDelete(null);
				}}
				onConfirm={handleConfirmDelete}
				title="Delete MCP Server"
				message={`Are you sure you want to delete "${mcpServers.find((s) => s.id === serverToDelete)?.server_name || "this server"}"? This action cannot be undone and will remove all configuration for this server.`}
				confirmText="Delete"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>
		</div>
	);
}
