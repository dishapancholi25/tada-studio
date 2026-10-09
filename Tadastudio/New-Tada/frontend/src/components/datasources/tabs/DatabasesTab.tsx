"use client";

import {
	AlertCircle,
	CheckCircle,
	ChevronDown,
	ChevronRight,
	Clock,
	Database,
	Eye,
	Globe,
	Key,
	Link2,
	Loader,
	Lock,
	Plus,
	RefreshCw,
	Search,
	Settings,
	Table,
	TestTube,
	Trash2,
	Users,
	XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import Button from "@/components/ui/Button";
import MetaChip from "@/components/ui/MetaChip";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import DatabaseConnectionForm, {
	type DatabaseConnectionData,
} from "../../database/DatabaseConnectionForm";
import ConfirmDialog from "../../dialogs/ConfirmDialog";
import TablePreviewModal from "../../dialogs/TablePreviewModal";
import DataSourceStatsBar from "../shared/DataSourceStatsBar";
import DataSourceFilterBar from "../shared/DataSourceFilterBar";
import SharingControls from "../shared/SharingControls";
import LoadingSkeleton from "../shared/LoadingSkeleton";
import EmptyState from "../shared/EmptyState";
import DatabaseTypeIcon, {
	getDatabaseTypeLabel,
} from "../shared/DatabaseTypeIcon";

type ConnectionFilterTab = "all" | "owned" | "shared";

const FILTER_TABS = [
	{ key: "all", label: "All" },
	{ key: "owned", label: "My Connections" },
	{ key: "shared", label: "Shared" },
];

interface DatabaseConnection {
	id: string;
	name: string;
	description?: string;
	database_type: string;
	host?: string;
	port?: number;
	database_name?: string;
	username?: string;
	use_ssl: boolean;
	is_active: boolean;
	read_only: boolean;
	last_connection_test?: string;
	last_connection_status?: string;
	last_error_message?: string;
	query_count: number;
	last_used?: string;
	created_at: string;
	updated_at?: string;
	visible_to_groups?: string[];
	user_id?: string;
	is_read_only?: boolean;
}

interface DatabaseSchema {
	tables: {
		[tableName: string]: {
			columns: Array<{
				name: string;
				type: string;
				nullable: boolean;
				default?: string;
				autoincrement?: boolean;
			}>;
			primary_keys: string[];
			foreign_keys: Array<{
				name?: string;
				columns: string[];
				referred_table: string;
				referred_columns: string[];
			}>;
			indexes: Array<{
				name?: string;
				columns: string[];
				unique: boolean;
			}>;
			loading?: boolean;
			error?: boolean;
		};
	};
	views: string[];
}

interface TablePreviewData {
	success: boolean;
	data?: any[];
	columns?: string[];
	row_count?: number;
	error?: string;
}

export default function DatabasesTab() {
	const { showSuccess, showError, showWarning } = useToast();
	const [connections, setConnections] = useState<DatabaseConnection[]>([]);
	const [selectedConnection, setSelectedConnection] =
		useState<DatabaseConnection | null>(null);
	const [loading, setLoading] = useState(true);
	const [searchTerm, setSearchTerm] = useState("");
	const [activeFilterTab, setActiveFilterTab] =
		useState<ConnectionFilterTab>("all");
	const [formModal, setFormModal] = useState<{
		isOpen: boolean;
		mode: "create" | "edit";
		data?: DatabaseConnectionData;
	}>({
		isOpen: false,
		mode: "create",
	});
	const [deleteDialog, setDeleteDialog] = useState<{
		isOpen: boolean;
		connectionId: string;
	}>({
		isOpen: false,
		connectionId: "",
	});

	// Sharing / visibility state
	const [isSharedVisibility, setIsSharedVisibility] = useState(false);
	const [visibilityGroups, setVisibilityGroups] = useState<string[]>([]);
	const [savingVisibility, setSavingVisibility] = useState(false);
	const [schema, setSchema] = useState<DatabaseSchema | null>(null);
	const [loadingSchema, setLoadingSchema] = useState(false);
	const [selectedTable, setSelectedTable] = useState<string>("");
	const [expandedTable, setExpandedTable] = useState<string | null>(null);
	const [schemaSearchTerm, setSchemaSearchTerm] = useState("");
	const [tablePreview, setTablePreview] = useState<TablePreviewData | null>(
		null,
	);
	const [loadingPreview, setLoadingPreview] = useState(false);
	const [testingConnection, setTestingConnection] = useState<string | null>(
		null,
	);
	const [previewModal, setPreviewModal] = useState<{
		isOpen: boolean;
		tableName: string;
	}>({
		isOpen: false,
		tableName: "",
	});

	useEffect(() => {
		void loadConnections();
	}, [activeFilterTab]); // eslint-disable-line react-hooks/exhaustive-deps

	const loadConnections = async () => {
		setLoading(true);
		try {
			const data = await api.getDatabaseConnections(
				true,
				0,
				100,
				activeFilterTab,
			);
			setConnections(data);
		} catch (error) {
			showError("Load Failed", "Failed to load database connections");
		} finally {
			setLoading(false);
		}
	};

	const loadSchema = async (connectionId: string, forceRefresh = false) => {
		setLoadingSchema(true);
		try {
			const tablesData = await api.getDatabaseTables(
				connectionId,
				forceRefresh,
			);
			const basicSchema = {
				tables: tablesData.tables.reduce((acc: any, tableName: string) => {
					acc[tableName] = {
						columns: [],
						primary_keys: [],
						foreign_keys: [],
						indexes: [],
						loading: true,
					};
					return acc;
				}, {}),
				views: [],
			};

			setSchema(basicSchema);

			if (
				tablesData.tables &&
				tablesData.tables.length > 0 &&
				!selectedTable
			) {
				const firstTable = tablesData.tables[0];
				setSelectedTable(firstTable);
			}

			showSuccess(
				"Schema Loaded",
				`Found ${tablesData.tables.length} tables`,
			);
		} catch (error) {
			setSchema(null);
			showWarning(
				"Schema Unavailable",
				"Could not load database schema",
			);
		} finally {
			setLoadingSchema(false);
		}
	};

	const loadTableDetails = async (connectionId: string, tableName: string) => {
		if (!connectionId || !tableName) return null;

		if (
			schema?.tables[tableName]?.columns &&
			schema.tables[tableName].columns.length > 0
		) {
			return schema.tables[tableName];
		}

		try {
			const details = await api.getTableDetails(connectionId, tableName);

			setSchema((prev) => {
				if (!prev) return prev;
				return {
					...prev,
					tables: {
						...prev.tables,
						[tableName]: {
							...details,
							loading: false,
						},
					},
				};
			});

			return details;
		} catch (error) {
			console.error(
				`Failed to load details for table ${tableName}:`,
				error,
			);
			setSchema((prev) => {
				if (!prev) return prev;
				return {
					...prev,
					tables: {
						...prev.tables,
						[tableName]: {
							...prev.tables[tableName],
							loading: false,
							error: true,
						},
					},
				};
			});
			return null;
		}
	};

	const loadTablePreview = async (connectionId: string, tableName: string) => {
		setLoadingPreview(true);
		try {
			const data = await api.previewDatabaseTable(
				connectionId,
				tableName,
				100,
			);
			setTablePreview(data);
		} catch (error) {
			setTablePreview({ success: false, error: "Failed to load preview" });
		} finally {
			setLoadingPreview(false);
		}
	};

	const handleCreateConnection = async (data: DatabaseConnectionData) => {
		try {
			await api.createDatabaseConnection(data);
			await loadConnections();
			showSuccess(
				"Connection Created",
				"Database connection has been created successfully",
			);
		} catch (error: any) {
			showError(
				"Creation Failed",
				error.message || "Failed to create database connection",
			);
			throw error;
		}
	};

	const handleUpdateConnection = async (data: DatabaseConnectionData) => {
		if (!data.id) return;

		try {
			await api.updateDatabaseConnection(data.id, data);
			await loadConnections();
			showSuccess(
				"Connection Updated",
				"Database connection has been updated successfully",
			);
		} catch (error: any) {
			showError(
				"Update Failed",
				error.message || "Failed to update database connection",
			);
			throw error;
		}
	};

	const handleDeleteConnection = async () => {
		const connectionId = deleteDialog.connectionId;

		try {
			await api.deleteDatabaseConnection(connectionId);
			await loadConnections();
			if (selectedConnection?.id === connectionId) {
				setSelectedConnection(null);
				setSchema(null);
				setTablePreview(null);
			}

			showSuccess(
				"Connection Deleted",
				"Database connection has been deleted successfully",
			);
		} catch (error) {
			showError("Delete Failed", "Failed to delete database connection");
		}
	};

	const handleTestConnection = async (connectionId: string) => {
		setTestingConnection(connectionId);

		try {
			const result = await api.testDatabaseConnection(connectionId);

			if (result.success) {
				showSuccess("Connection Test", "Connection successful!");
			} else {
				showError(
					"Connection Test",
					result.error_message || "Connection failed",
				);
			}

			await loadConnections();
		} catch (error) {
			showError("Test Failed", "Failed to test connection");
		} finally {
			setTestingConnection(null);
		}
	};

	const getStatusIcon = (status?: string) => {
		switch (status) {
			case "success":
				return <CheckCircle className="w-4 h-4 text-[#0DA931]" />;
			case "failed":
				return <XCircle className="w-4 h-4 text-red-400" />;
			default:
				return (
					<Clock className="w-4 h-4 text-[color:var(--color-text-muted)]" />
				);
		}
	};

	const handleSelectConnection = (conn: DatabaseConnection) => {
		setSelectedConnection(conn);
		const groups = conn.visible_to_groups ?? [];
		const shared = groups.length > 0;
		setIsSharedVisibility(shared);
		setVisibilityGroups(
			shared ? groups.filter((g) => g !== "__all__") : [],
		);
		setExpandedTable(null);
		setSchemaSearchTerm("");
		void loadSchema(conn.id);
	};

	const handleSaveVisibility = async () => {
		if (!selectedConnection) return;
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
			const updated = await api.updateDatabaseConnectionVisibility(
				selectedConnection.id,
				groups,
			);
			setSelectedConnection(updated);
			setConnections((prev) =>
				prev.map((c) => (c.id === updated.id ? updated : c)),
			);
			showSuccess(
				"Visibility Updated",
				"Connection sharing settings saved",
			);
		} catch {
			showError(
				"Update Failed",
				"Failed to update connection visibility",
			);
		} finally {
			setSavingVisibility(false);
		}
	};

	const openTablePreview = async (tableName: string) => {
		if (!selectedConnection) return;

		setPreviewModal({ isOpen: true, tableName });
		setSelectedTable(tableName);

		await loadTableDetails(selectedConnection.id, tableName);
		await loadTablePreview(selectedConnection.id, tableName);
	};

	const handleToggleTable = async (tableName: string) => {
		if (expandedTable === tableName) {
			setExpandedTable(null);
		} else {
			setExpandedTable(tableName);
			if (selectedConnection) {
				await loadTableDetails(selectedConnection.id, tableName);
			}
		}
	};

	const filteredConnections = connections.filter(
		(conn) =>
			conn.name.toLowerCase().includes(searchTerm.trim().toLowerCase()) ||
			conn.database_type.toLowerCase().includes(searchTerm.trim().toLowerCase()),
	);

	const filteredTables = useMemo(() => {
		if (!schema) return [];
		const tables = Object.keys(schema.tables);
		if (!schemaSearchTerm) return tables;
		return tables.filter((t) =>
			t.toLowerCase().includes(schemaSearchTerm.trim().toLowerCase()),
		);
	}, [schema, schemaSearchTerm]);

	const handleFilterChange = useCallback((filter: string) => {
		setActiveFilterTab(filter as ConnectionFilterTab);
		setSelectedConnection(null);
	}, []);

	return (
		<div className="p-6">
			{/* Stats Bar */}
			<DataSourceStatsBar
				title="Database Connections"
				titleIcon={
					<Database className="w-5 h-5 text-[color:var(--color-accent)]" />
				}
				actionSlot={
					<Button
						onClick={() =>
							setFormModal({ isOpen: true, mode: "create" })
						}
						variant="secondary"
						icon={<Plus className="w-4 h-4" />}
						data-tutorial="db-add-connection-btn"
					>
						Add Connection
					</Button>
				}
				stats={[
					{
						label: "Total Connections",
						value: connections.length,
						color: "primary",
						icon: <Database className="w-6 h-6" />,
					},
					{
						label: "Active",
						value: connections.filter((c) => c.is_active).length,
						color: "green",
						icon: <CheckCircle className="w-6 h-6" />,
					},
					{
						label: "Failed",
						value: connections.filter(
							(c) => c.last_connection_status === "failed",
						).length,
						color: "red",
						icon: <XCircle className="w-6 h-6" />,
					},
					{
						label: "Total Queries",
						value: connections.reduce(
							(sum, c) => sum + c.query_count,
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
				searchPlaceholder="Search connections..."
				className="mb-6"
			/>

			{/* Connections Grid */}
			<div
				className="rounded-xl p-6"
				style={{
					background: "var(--color-bg-secondary)",
					border: "1px solid var(--color-border)",
				}}
			>
				<div className="flex items-center justify-between mb-6">
					<h3 className="text-lg font-semibold text-slate-900">
						Connections
					</h3>
					<span className="text-sm text-[color:var(--color-text-muted)]">
						{filteredConnections.length} connections
					</span>
				</div>

				{loading ? (
					<LoadingSkeleton variant="card-grid" />
				) : filteredConnections.length === 0 ? (
					<EmptyState
						icon={<Database className="w-10 h-10" />}
						title="No Connections Found"
						description={
							searchTerm
								? "No connections match your search"
								: "Create your first database connection to get started"
						}
						primaryAction={
							!searchTerm
								? {
										label: "Add Connection",
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
					<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
						{filteredConnections.map((conn) => (
							<div
								key={conn.id}
								className="p-4 rounded-xl border transition-all duration-200 hover:shadow-lg cursor-pointer group"
								style={{
									background:
										selectedConnection?.id === conn.id
											? "rgba(var(--color-primary-rgb), 0.08)"
											: "var(--color-surface)",
									borderColor:
										selectedConnection?.id === conn.id
											? "var(--color-primary)"
											: "var(--color-border)",
								}}
								onClick={() => handleSelectConnection(conn)}
							>
								<div className="flex items-start gap-3 mb-3">
									<DatabaseTypeIcon
										type={conn.database_type}
										size="md"
									/>
									<div className="flex-1 min-w-0">
										<div className="flex items-center gap-2 mb-1">
											<h4 className="font-medium text-slate-900 truncate">
												{conn.name}
											</h4>
											{getStatusIcon(
												conn.last_connection_status,
											)}
										</div>
										<div className="text-xs text-[color:var(--color-text-muted)] mb-1 truncate font-mono">
											{conn.host}:{conn.port}/
											{conn.database_name}
										</div>
										{conn.description && (
											<p className="text-xs text-[color:var(--color-text-muted)] truncate">
												{conn.description}
											</p>
										)}
									</div>
									{/* Always-visible action buttons */}
									<div className="flex gap-1 flex-shrink-0">
										<button
											onClick={(e) => {
												e.stopPropagation();
												void handleTestConnection(
													conn.id,
												);
											}}
											disabled={
												testingConnection === conn.id ||
												savingVisibility
											}
											className="p-1.5 hover:bg-[color:var(--color-border)] rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed text-[color:var(--color-text-muted)] hover:text-slate-900"
											title="Test connection"
										>
											{testingConnection === conn.id ? (
												<Loader className="w-4 h-4 animate-spin text-orange-500" />
											) : (
												<TestTube className="w-4 h-4" />
											)}
										</button>
										<button
											onClick={(e) => {
												e.stopPropagation();
												setFormModal({
													isOpen: true,
													mode: "edit",
													data: conn as DatabaseConnectionData,
												});
											}}
											disabled={savingVisibility}
											className="p-1.5 hover:bg-[color:var(--color-border)] rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed text-[color:var(--color-text-muted)] hover:text-slate-900"
											title="Edit connection"
										>
											<Settings className="w-4 h-4" />
										</button>
										<button
											onClick={(e) => {
												e.stopPropagation();
												setDeleteDialog({
													isOpen: true,
													connectionId: conn.id,
												});
											}}
											disabled={savingVisibility}
											className="p-1.5 hover:bg-red-500/20 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed text-[color:var(--color-text-muted)] hover:text-red-400"
											title="Delete connection"
										>
											<Trash2 className="w-4 h-4" />
										</button>
									</div>
								</div>

								{/* Metadata chips */}
								<div className="flex flex-wrap items-center gap-1.5">
									<MetaChip
										label={getDatabaseTypeLabel(
											conn.database_type,
										)}
										color="plum"
									/>
									{conn.is_active ? (
										<MetaChip label="Active" color="green" />
									) : (
										<MetaChip label="Inactive" color="red" />
									)}
									{conn.read_only && (
										<MetaChip
											label="Read-only"
											color="gray"
										/>
									)}
									{conn.use_ssl && (
										<MetaChip label="SSL" color="gray" />
									)}
									{conn.visible_to_groups?.includes(
										"__all__",
									) ? (
										<MetaChip
											label="Shared"
											color="accent"
										/>
									) : (conn.visible_to_groups?.length ?? 0) >
									  0 ? (
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
									{conn.query_count > 0 && (
										<MetaChip
											label="Queries"
											value={conn.query_count}
											color="gray"
										/>
									)}
								</div>

								{conn.last_error_message && (
									<div className="mt-3 p-2 bg-red-900/30 border border-red-700 rounded-lg text-xs">
										<div className="flex items-start gap-2">
											<AlertCircle className="w-3 h-3 text-red-400 flex-shrink-0 mt-0.5" />
											<p className="text-red-400">
												{conn.last_error_message}
											</p>
										</div>
									</div>
								)}
							</div>
						))}
					</div>
				)}
			</div>

			{/* Sharing Controls for Selected Connection */}
			{selectedConnection && !selectedConnection.is_read_only && (
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

			{/* Selected Connection Schema Explorer */}
			{selectedConnection && (
				<div
					className="mt-6 rounded-xl p-6"
					style={{
						background: "var(--color-bg-secondary)",
						border: "1px solid var(--color-border)",
					}}
				>
					<div className="flex items-center justify-between mb-4">
						<h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
							<Table className="w-5 h-5 text-[color:var(--color-accent)]" />
							Schema Explorer: {selectedConnection.name}
						</h3>
						<Button
							onClick={() =>
								loadSchema(selectedConnection.id, true)
							}
							disabled={loadingSchema}
							variant="ghost"
							size="sm"
							icon={
								<RefreshCw
									className={`w-4 h-4 ${loadingSchema ? "animate-spin" : ""}`}
								/>
							}
						>
							Refresh
						</Button>
					</div>

					{loadingSchema ? (
						<LoadingSkeleton variant="card-grid" columns={2} />
					) : schema && Object.keys(schema.tables).length > 0 ? (
						<div className="space-y-3">
							{/* Schema search */}
							<div className="flex items-center gap-3">
								<div className="relative flex-1">
									<Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-[color:var(--color-text-muted)]" />
									<input
										type="text"
										className="w-full pl-10 pr-4 py-2 rounded-lg text-sm bg-[color:var(--color-surface)] border border-[color:var(--color-border)] text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-[color:var(--color-primary)]"
										placeholder="Filter tables..."
										value={schemaSearchTerm}
										onChange={(e) =>
											setSchemaSearchTerm(e.target.value)
										}
									/>
								</div>
								<span className="text-sm text-[color:var(--color-text-muted)]">
									{filteredTables.length} table
									{filteredTables.length !== 1 ? "s" : ""}
								</span>
							</div>

							{/* Table accordion list */}
							<div className="space-y-1">
								{filteredTables.map((tableName) => {
									const tableData = schema.tables[tableName];
									const isExpanded =
										expandedTable === tableName;
									const hasColumns =
										tableData?.columns?.length > 0;

									return (
										<div
											key={tableName}
											className="rounded-lg border overflow-hidden"
											style={{
												background:
													"var(--color-surface)",
												borderColor: isExpanded
													? "rgba(var(--color-primary-rgb), 0.3)"
													: "var(--color-border)",
											}}
										>
											{/* Table header row */}
											<div
												className="flex items-center justify-between px-3 py-2.5 cursor-pointer hover:bg-[color:var(--color-bg-secondary)] transition-colors"
												onClick={() =>
													handleToggleTable(tableName)
												}
											>
												<div className="flex items-center gap-2 min-w-0">
													{isExpanded ? (
														<ChevronDown className="w-4 h-4 text-[color:var(--color-accent)] flex-shrink-0" />
													) : (
														<ChevronRight className="w-4 h-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
													)}
													<Table className="w-4 h-4 text-[color:var(--color-accent)] flex-shrink-0" />
													<span className="text-sm text-slate-900 truncate font-medium">
														{tableName}
													</span>
													{hasColumns && (
														<span className="text-xs text-[color:var(--color-text-muted)]">
															(
															{
																tableData
																	.columns
																	.length
															}{" "}
															cols)
														</span>
													)}
												</div>
												<button
													onClick={(e) => {
														e.stopPropagation();
														openTablePreview(
															tableName,
														);
													}}
													className="p-1.5 hover:bg-[color:var(--color-border)] rounded-lg transition-all text-[color:var(--color-text-muted)] hover:text-slate-900 flex-shrink-0"
													title="Preview table data"
												>
													<Eye className="w-4 h-4" />
												</button>
											</div>

											{/* Expanded column details */}
											{isExpanded && (
												<div className="border-t border-[color:var(--color-border)] px-3 py-2 bg-[color:var(--color-bg-secondary)]">
													{tableData?.loading ? (
														<div className="flex items-center gap-2 py-2 text-sm text-[color:var(--color-text-muted)]">
															<Loader className="w-4 h-4 animate-spin text-orange-500" />
															Loading columns...
														</div>
													) : tableData?.error ? (
														<div className="text-sm text-red-400 py-2">
															Failed to load
															column details
														</div>
													) : hasColumns ? (
														<div className="space-y-1">
															{tableData.columns.map(
																(col) => (
																	<div
																		key={
																			col.name
																		}
																		className="flex items-center gap-2 py-1 text-xs"
																	>
																		{tableData.primary_keys?.includes(
																			col.name,
																		) ? (
																			<Key className="w-3 h-3 text-amber-400 flex-shrink-0" />
																		) : tableData.foreign_keys?.some(
																				(
																					fk,
																				) =>
																					fk.columns.includes(
																						col.name,
																					),
																			) ? (
																			<Link2 className="w-3 h-3 text-blue-400 flex-shrink-0" />
																		) : (
																			<span className="w-3 h-3 flex-shrink-0" />
																		)}
																		<span className="text-slate-900 font-medium min-w-[100px]">
																			{
																				col.name
																			}
																		</span>
																		<span className="text-[color:var(--color-text-muted)] font-mono">
																			{
																				col.type
																			}
																		</span>
																		{col.nullable && (
																			<span className="text-[color:var(--color-text-muted)]">
																				nullable
																			</span>
																		)}
																	</div>
																),
															)}
														</div>
													) : (
														<div className="text-sm text-[color:var(--color-text-muted)] py-2">
															No column details
															available
														</div>
													)}
												</div>
											)}
										</div>
									);
								})}
							</div>
						</div>
					) : (
						<EmptyState
							icon={<Database className="w-10 h-10" />}
							title="No Tables Found"
							description="This database connection has no accessible tables or the connection failed"
						/>
					)}
				</div>
			)}

			{/* Modals */}
			<DatabaseConnectionForm
				isOpen={formModal.isOpen}
				mode={formModal.mode}
				initialData={formModal.data}
				onClose={() => setFormModal({ isOpen: false, mode: "create" })}
				onSubmit={
					formModal.mode === "create"
						? handleCreateConnection
						: handleUpdateConnection
				}
			/>

			<ConfirmDialog
				isOpen={deleteDialog.isOpen}
				title="Delete Database Connection"
				message="Are you sure you want to delete this database connection? This action cannot be undone."
				confirmText="Delete"
				cancelText="Cancel"
				type="danger"
				onConfirm={handleDeleteConnection}
				onCancel={() =>
					setDeleteDialog({ isOpen: false, connectionId: "" })
				}
			/>

			<TablePreviewModal
				isOpen={previewModal.isOpen}
				onClose={() =>
					setPreviewModal({ isOpen: false, tableName: "" })
				}
				tableName={previewModal.tableName}
				connectionName={selectedConnection?.name || ""}
				tableData={tablePreview}
				loading={loadingPreview}
			/>
		</div>
	);
}
