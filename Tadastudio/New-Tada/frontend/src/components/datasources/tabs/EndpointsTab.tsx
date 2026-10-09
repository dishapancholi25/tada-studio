"use client";

import {
	Globe,
	Link,
	Loader,
	Lock,
	Plus,
	Search,
	Settings,
	Trash2,
	Users,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Button from "@/components/ui/Button";
import MetaChip from "@/components/ui/MetaChip";
import Dropdown from "@/components/ui/Dropdown";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import ApiEndpointForm, {
	type ApiEndpointFormData,
} from "../ApiEndpointForm";
import ConfirmDialog from "../../dialogs/ConfirmDialog";
import DataSourceStatsBar from "../shared/DataSourceStatsBar";
import DataSourceFilterBar from "../shared/DataSourceFilterBar";
import SharingControls from "../shared/SharingControls";
import LoadingSkeleton from "../shared/LoadingSkeleton";
import EmptyState from "../shared/EmptyState";

type EndpointFilterTab = "all" | "owned" | "shared";

const FILTER_TABS = [
	{ key: "all", label: "All" },
	{ key: "owned", label: "My Endpoints" },
	{ key: "shared", label: "Shared" },
];

interface ServiceTemplate {
	id: string;
	name: string;
	service_type: string;
	description: string;
	url_template: string;
	method: string;
	headers?: Record<string, string>;
	auth_type: string;
	timeout_seconds?: number;
	max_retries?: number;
	response_format?: string;
	extract_path?: string;
	parameter_schema?: Record<string, unknown>;
}

interface ApiEndpointData {
	id: string;
	name: string;
	description?: string;
	service_type?: string;
	url_template: string;
	method: string;
	headers?: Record<string, string>;
	query_params?: Record<string, string>;
	request_body_template?: string;
	content_type?: string;
	parameter_schema?: Record<string, any>;
	auth_type: string;
	timeout_seconds: number;
	max_retries: number;
	retry_delay: number;
	retry_on_status?: number[];
	response_format: string;
	extract_path?: string;
	success_status_codes?: number[];
	verify_ssl: boolean;
	follow_redirects: boolean;
	max_redirects: number;
	is_active: boolean;
	usage_count: number;
	last_used?: string;
	created_at: string;
	updated_at?: string;
	visible_to_groups?: string[];
	user_id?: string;
	is_read_only?: boolean;
}

const METHOD_COLORS: Record<string, string> = {
	GET: "rgba(13, 169, 49, 0.15)",
	POST: "rgba(59, 130, 246, 0.15)",
	PUT: "rgba(245, 158, 11, 0.15)",
	PATCH: "rgba(168, 85, 247, 0.15)",
	DELETE: "rgba(239, 68, 68, 0.15)",
};

const METHOD_TEXT_COLORS: Record<string, string> = {
	GET: "rgb(74, 222, 128)",
	POST: "rgb(96, 165, 250)",
	PUT: "rgb(251, 191, 36)",
	PATCH: "rgb(192, 132, 252)",
	DELETE: "rgb(248, 113, 113)",
};

const METHOD_BORDERS: Record<string, string> = {
	GET: "rgba(13, 169, 49, 0.3)",
	POST: "rgba(59, 130, 246, 0.3)",
	PUT: "rgba(245, 158, 11, 0.3)",
	PATCH: "rgba(168, 85, 247, 0.3)",
	DELETE: "rgba(239, 68, 68, 0.3)",
};

export default function EndpointsTab() {
	const { showSuccess, showError } = useToast();
	const [endpoints, setEndpoints] = useState<ApiEndpointData[]>([]);
	const [selectedEndpoint, setSelectedEndpoint] =
		useState<ApiEndpointData | null>(null);
	const [loading, setLoading] = useState(true);
	const [searchTerm, setSearchTerm] = useState("");
	const [activeFilterTab, setActiveFilterTab] =
		useState<EndpointFilterTab>("all");
	const [formModal, setFormModal] = useState<{
		isOpen: boolean;
		mode: "create" | "edit";
		data?: Partial<ApiEndpointFormData>;
	}>({
		isOpen: false,
		mode: "create",
	});
	const [deleteDialog, setDeleteDialog] = useState<{
		isOpen: boolean;
		endpointId: string;
	}>({
		isOpen: false,
		endpointId: "",
	});

	// Templates
	const [templates, setTemplates] = useState<ServiceTemplate[]>([]);

	useEffect(() => {
		api
			.getApiEndpointTemplates()
			.then((t: ServiceTemplate[]) => setTemplates(t || []))
			.catch(() => {});
	}, []);

	const handleCreateFromTemplate = useCallback(
		(templateId: string) => {
			const template = templates.find((t) => t.id === templateId);
			if (!template) return;
			setFormModal({
				isOpen: true,
				mode: "create",
				data: {
					name: template.name || "",
					description: template.description || "",
					service_type: template.service_type || "generic",
					url_template: template.url_template || "",
					method: template.method || "GET",
					headers: template.headers || {},
					auth_type: template.auth_type || "none",
					timeout_seconds: template.timeout_seconds ?? 30,
					max_retries: template.max_retries ?? 3,
					response_format: template.response_format || "auto",
					extract_path: template.extract_path || "",
					parameter_schema: template.parameter_schema || {},
				},
			});
		},
		[templates],
	);

	// Connection test state
	const [testingEndpointId, setTestingEndpointId] = useState<string | null>(
		null,
	);

	// Sharing / visibility state
	const [isSharedVisibility, setIsSharedVisibility] = useState(false);
	const [visibilityGroups, setVisibilityGroups] = useState<string[]>([]);
	const [savingVisibility, setSavingVisibility] = useState(false);

	const loadEndpoints = useCallback(async () => {
		setLoading(true);
		try {
			const data = await api.getApiEndpoints(
				true,
				0,
				100,
				activeFilterTab,
			);
			setEndpoints(data);
		} catch {
			showError("Load Failed", "Failed to load API endpoints");
		} finally {
			setLoading(false);
		}
	}, [activeFilterTab, showError]);

	const handleTestEndpoint = useCallback(
		async (endpointId: string) => {
			setTestingEndpointId(endpointId);
			try {
				const result = (await api.testApiEndpoint(endpointId)) as any;
				if (result.success) {
					showSuccess(
						"Connection Successful",
						`Status ${result.status_code} in ${result.response_time_ms}ms`,
					);
				} else {
					showError(
						"Connection Failed",
						result.error ||
							"Could not connect to the endpoint",
					);
				}
				await loadEndpoints();
			} catch {
				showError(
					"Test Failed",
					"An error occurred while testing the endpoint",
				);
			} finally {
				setTestingEndpointId(null);
			}
		},
		[loadEndpoints, showSuccess, showError],
	);

	useEffect(() => {
		void loadEndpoints();
	}, [loadEndpoints]);

	const handleCreateEndpoint = async (data: ApiEndpointFormData) => {
		try {
			await api.createApiEndpoint(
				data as unknown as Record<string, unknown>,
			);
			await loadEndpoints();
			showSuccess(
				"Endpoint Created",
				"API endpoint has been created successfully",
			);
		} catch (error: any) {
			showError(
				"Creation Failed",
				error.message || "Failed to create API endpoint",
			);
			throw error;
		}
	};

	const handleUpdateEndpoint = async (data: ApiEndpointFormData) => {
		if (!data.id) return;

		try {
			await api.updateApiEndpoint(
				data.id,
				data as unknown as Record<string, unknown>,
			);
			await loadEndpoints();
			showSuccess(
				"Endpoint Updated",
				"API endpoint has been updated successfully",
			);
		} catch (error: any) {
			showError(
				"Update Failed",
				error.message || "Failed to update API endpoint",
			);
			throw error;
		}
	};

	const handleDeleteEndpoint = async () => {
		const endpointId = deleteDialog.endpointId;

		try {
			await api.deleteApiEndpoint(endpointId);
			await loadEndpoints();
			if (selectedEndpoint?.id === endpointId) {
				setSelectedEndpoint(null);
			}

			showSuccess(
				"Endpoint Deleted",
				"API endpoint has been deleted successfully",
			);
		} catch {
			showError("Delete Failed", "Failed to delete API endpoint");
		}
	};

	const handleSelectEndpoint = (ep: ApiEndpointData) => {
		setSelectedEndpoint(ep);
		const groups = ep.visible_to_groups ?? [];
		const shared = groups.length > 0;
		setIsSharedVisibility(shared);
		setVisibilityGroups(
			shared ? groups.filter((g) => g !== "__all__") : [],
		);
	};

	const handleSaveVisibility = async () => {
		if (!selectedEndpoint) return;
		setSavingVisibility(true);
		try {
			let groups: string[] = [];
			if (isSharedVisibility) {
				groups =
					visibilityGroups.length === 0 ||
					visibilityGroups.includes("__all__")
						? ["__all__"]
						: visibilityGroups;
			}
			const updated = await api.updateApiEndpointVisibility(
				selectedEndpoint.id,
				groups,
			);
			setSelectedEndpoint(updated);
			setEndpoints((prev) =>
				prev.map((e) => (e.id === updated.id ? updated : e)),
			);
			showSuccess(
				"Visibility Updated",
				"Endpoint sharing settings saved",
			);
		} catch {
			showError(
				"Update Failed",
				"Failed to update endpoint visibility",
			);
		} finally {
			setSavingVisibility(false);
		}
	};

	const handleFilterChange = useCallback((filter: string) => {
		setActiveFilterTab(filter as EndpointFilterTab);
		setSelectedEndpoint(null);
	}, []);

	const filteredEndpoints = endpoints.filter(
		(ep) =>
			ep.name.toLowerCase().includes(searchTerm.trim().toLowerCase()) ||
			ep.url_template.toLowerCase().includes(searchTerm.trim().toLowerCase()) ||
			ep.method.toLowerCase().includes(searchTerm.trim().toLowerCase()),
	);

	// Group endpoints by service type
	const groupedEndpoints = useMemo(() => {
		const groups: Record<string, ApiEndpointData[]> = {};
		for (const ep of filteredEndpoints) {
			const key =
				ep.service_type && ep.service_type !== "generic"
					? ep.service_type
					: "General";
			if (!groups[key]) groups[key] = [];
			groups[key].push(ep);
		}
		// Sort groups: "General" last
		const sortedKeys = Object.keys(groups).sort((a, b) => {
			if (a === "General") return 1;
			if (b === "General") return -1;
			return a.localeCompare(b);
		});
		return sortedKeys.map((key) => ({ group: key, endpoints: groups[key] }));
	}, [filteredEndpoints]);

	const methodCounts = endpoints.reduce(
		(acc, ep) => {
			acc[ep.method] = (acc[ep.method] || 0) + 1;
			return acc;
		},
		{} as Record<string, number>,
	);

	return (
		<div className="p-6">
			{/* Stats Bar */}
			<DataSourceStatsBar
				title="API Endpoints"
				titleIcon={
					<Link className="w-5 h-5 text-[color:var(--color-accent)]" />
				}
				actionSlot={
					<div className="flex gap-2">
						{templates.length > 0 && (
							<Dropdown
								options={templates.map((t) => ({
									value: t.id,
									label: t.name,
									description: t.description,
								}))}
								onChange={handleCreateFromTemplate}
								trigger={
									<Button
										variant="secondary"
										icon={
											<Globe className="w-4 h-4" />
										}
									>
										From Template
									</Button>
								}
								placeholder="Select a template"
								align="end"
							/>
						)}
						<Button
							onClick={() =>
								setFormModal({
									isOpen: true,
									mode: "create",
								})
							}
							variant="secondary"
							icon={<Plus className="w-4 h-4" />}
							data-tutorial="endpoint-add-btn"
						>
							Add Endpoint
						</Button>
					</div>
				}
				stats={[
					{
						label: "Total Endpoints",
						value: endpoints.length,
						color: "primary",
						icon: <Link className="w-6 h-6" />,
					},
					{
						label: "Active",
						value: endpoints.filter((e) => e.is_active).length,
						color: "green",
					},
					{
						label: "Methods",
						value:
							Object.entries(methodCounts)
								.map(([m, c]) => `${m}: ${c}`)
								.join(", ") || "None",
					},
					{
						label: "Total Usage",
						value: endpoints.reduce(
							(sum, e) => sum + e.usage_count,
							0,
						),
					},
				]}
				className="mb-6"
			/>

			{/* Filter + Search */}
			<DataSourceFilterBar
				filterTabs={FILTER_TABS}
				activeFilter={activeFilterTab}
				onFilterChange={handleFilterChange}
				searchTerm={searchTerm}
				onSearchChange={setSearchTerm}
				searchPlaceholder="Search endpoints..."
				className="mb-6"
			/>

			{/* Endpoints Grid (grouped by service type) */}
			<div
				className="rounded-xl p-6"
				style={{
					background: "var(--color-bg-secondary)",
					border: "1px solid var(--color-border)",
				}}
			>
				<div className="flex items-center justify-between mb-6">
					<h3 className="text-lg font-semibold text-slate-900">
						Endpoints
					</h3>
					<span className="text-sm text-[color:var(--color-text-muted)]">
						{filteredEndpoints.length} endpoints
					</span>
				</div>

				{loading ? (
					<LoadingSkeleton variant="card-grid" />
				) : filteredEndpoints.length === 0 ? (
					<EmptyState
						icon={<Link className="w-10 h-10" />}
						title="No Endpoints Found"
						description={
							searchTerm
								? "No endpoints match your search"
								: "Create your first API endpoint to get started"
						}
						primaryAction={
							!searchTerm
								? {
										label: "Add Endpoint",
										icon: <Plus className="w-4 h-4" />,
										onClick: () =>
											setFormModal({
												isOpen: true,
												mode: "create",
											}),
									}
								: undefined
						}
					/>
				) : (
					<div className="space-y-6">
						{groupedEndpoints.map(({ group, endpoints: eps }) => (
							<div key={group}>
								{/* Group header (only show if multiple groups) */}
								{groupedEndpoints.length > 1 && (
									<div className="flex items-center gap-2 mb-3">
										<span className="text-xs capitalize tracking-wider font-semibold text-[color:var(--color-text-muted)]">
											{group}
										</span>
										<div className="flex-1 h-px bg-[color:var(--color-border)]" />
										<span className="text-xs text-[color:var(--color-text-muted)]">
											{eps.length}
										</span>
									</div>
								)}
								<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
									{eps.map((ep) => (
										<div
											key={ep.id}
											className="p-4 rounded-xl border transition-all duration-200 hover:shadow-lg cursor-pointer group"
											style={{
												background:
													selectedEndpoint?.id ===
													ep.id
														? "rgba(var(--color-primary-rgb), 0.08)"
														: "var(--color-surface)",
												borderColor:
													selectedEndpoint?.id ===
													ep.id
														? "var(--color-primary)"
														: "var(--color-border)",
											}}
											onClick={() =>
												handleSelectEndpoint(ep)
											}
										>
											{/* Row 1: Method badge + Name + Actions */}
											<div className="flex items-center gap-2 mb-2">
												<span
													className="px-2 py-0.5 rounded text-xs font-bold flex-shrink-0 capitalize"
													style={{
														background:
															METHOD_COLORS[
																ep.method
															] ||
															"var(--color-surface)",
														color:
															METHOD_TEXT_COLORS[
																ep.method
															] ||
															"var(--color-text-primary)",
														border: `1px solid ${METHOD_BORDERS[ep.method] || "var(--color-border)"}`,
													}}
												>
													{ep.method}
												</span>
												{ep.service_type &&
													ep.service_type !==
														"generic" && (
														<span className="px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 bg-[color:var(--color-accent)]/15 text-[color:var(--color-accent)] border border-[color:var(--color-accent)]/30">
															{ep.service_type}
														</span>
													)}
												<h4 className="font-medium text-slate-900 truncate flex-1 min-w-0">
													{ep.name}
												</h4>
												{/* Always-visible actions */}
												<div className="flex gap-0.5 flex-shrink-0">
													<button
														onClick={(e) => {
															e.stopPropagation();
															handleTestEndpoint(
																ep.id,
															);
														}}
														disabled={
															testingEndpointId ===
															ep.id
														}
														className="p-1.5 hover:bg-[#0DA931]/20 rounded-lg transition-all duration-200 disabled:opacity-50 text-[color:var(--color-text-muted)] hover:text-[#0DA931]"
														title="Test connection"
													>
														{testingEndpointId ===
														ep.id ? (
															<Loader className="w-3.5 h-3.5 animate-spin text-orange-500" />
														) : (
															<Globe className="w-3.5 h-3.5" />
														)}
													</button>
													{!ep.is_read_only && (
														<>
															<button
																onClick={(
																	e,
																) => {
																	e.stopPropagation();
																	setFormModal(
																		{
																			isOpen: true,
																			mode: "edit",
																			data: ep as Partial<ApiEndpointFormData>,
																		},
																	);
																}}
																className="p-1.5 hover:bg-[color:var(--color-border)] rounded-lg transition-all duration-200 text-[color:var(--color-text-muted)] hover:text-slate-900"
																title="Edit endpoint"
															>
																<Settings className="w-3.5 h-3.5" />
															</button>
															<button
																onClick={(
																	e,
																) => {
																	e.stopPropagation();
																	setDeleteDialog(
																		{
																			isOpen: true,
																			endpointId:
																				ep.id,
																		},
																	);
																}}
																className="p-1.5 hover:bg-red-500/20 rounded-lg transition-all duration-200 text-[color:var(--color-text-muted)] hover:text-red-400"
																title="Delete endpoint"
															>
																<Trash2 className="w-3.5 h-3.5" />
															</button>
														</>
													)}
												</div>
											</div>

											{/* Row 2: URL (full width, wrappable) */}
											<div className="text-xs text-[color:var(--color-text-muted)] font-mono mb-2 line-clamp-2 break-all">
												{ep.url_template}
											</div>

											{/* Row 3: Description */}
											{ep.description && (
												<p className="text-xs text-[color:var(--color-text-muted)] mb-2 truncate">
													{ep.description}
												</p>
											)}

											{/* Row 4: Metadata chips */}
											<div className="flex flex-wrap items-center gap-1.5">
												{ep.auth_type !== "none" && (
													<MetaChip
														label={ep.auth_type}
														color="plum"
													/>
												)}
												{ep.visible_to_groups?.includes(
													"__all__",
												) ? (
													<MetaChip
														label="Shared"
														color="accent"
													/>
												) : (ep.visible_to_groups
														?.length ?? 0) > 0 ? (
													<MetaChip
														label="Groups"
														color="purpleDS"
													/>
												) : (
													<MetaChip
														label="Private"
														color="gray"
													/>
												)}
												{ep.usage_count > 0 && (
													<MetaChip
														label="Uses"
														value={ep.usage_count}
														color="gray"
													/>
												)}
											</div>
										</div>
									))}
								</div>
							</div>
						))}
					</div>
				)}
			</div>

			{/* Sharing Controls for Selected Endpoint */}
			{selectedEndpoint && !selectedEndpoint.is_read_only && (
				<SharingControls
					isShared={isSharedVisibility}
					onSharedChange={setIsSharedVisibility}
					groups={visibilityGroups}
					onGroupsChange={setVisibilityGroups}
					onSave={handleSaveVisibility}
					saving={savingVisibility}
					className="mt-6"
				/>
			)}

			{/* Modals */}
			<ApiEndpointForm
				isOpen={formModal.isOpen}
				mode={formModal.mode}
				initialData={formModal.data}
				onClose={() => setFormModal({ isOpen: false, mode: "create" })}
				onSubmit={
					formModal.mode === "create"
						? handleCreateEndpoint
						: handleUpdateEndpoint
				}
			/>

			<ConfirmDialog
				isOpen={deleteDialog.isOpen}
				title="Delete API Endpoint"
				message="Are you sure you want to delete this API endpoint? Any HTTP request nodes referencing it will fall back to their inline configuration."
				confirmText="Delete"
				cancelText="Cancel"
				type="danger"
				onConfirm={handleDeleteEndpoint}
				onCancel={() =>
					setDeleteDialog({ isOpen: false, endpointId: "" })
				}
			/>
		</div>
	);
}
