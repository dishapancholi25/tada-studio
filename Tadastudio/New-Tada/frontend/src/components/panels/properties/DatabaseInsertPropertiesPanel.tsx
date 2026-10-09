"use client";

import {
	AlertTriangle,
	ChevronDown,
	Database,
	Minus,
	Plus,
	Save,
	ShieldCheck,
	Table,
	Trash2,
	X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Node } from "reactflow";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import Dropdown from "../../ui/Dropdown";
import InfoTooltip from "../../ui/InfoTooltipPortal";
import StructuredFieldPicker from "../../ui/StructuredFieldPicker";
import ConfigSidebar from "./ConfigSidebar";
import InputSourceSelector from "./InputSourceSelector";
import ToolGuardrailsSection from "@/components/core/guardrails/ToolGuardrailsSection";

interface ColumnMapping {
	column_name: string;
	column_type: string;
	is_required: boolean;
	is_nullable: boolean;
	default_value?: any;
	is_primary_key: boolean;
	is_autoincrement: boolean;
	// Input source configuration
	source_mode: "static" | "previous" | "specific" | "start" | "field";
	static_value?: any;
	source_node_id?: string;
	source_field_path?: string;
	custom_template?: string;
}

interface DatabaseInsertConfig {
	connection_id?: string;
	table_name?: string;
	column_mappings?: ColumnMapping[];
	return_inserted_rows?: boolean;
	on_conflict_strategy?: "fail" | "ignore" | "update";
	conflict_columns?: string[];
	timeout_seconds?: number;
	batch_size?: number;
	transaction_mode?: "auto" | "manual";
}

interface DatabaseInsertNodeData {
	id: string;
	name: string;
	database_insert_config?: DatabaseInsertConfig;
}

interface DatabaseInsertPropertiesPanelProps {
	node: {
		id: string;
		data: DatabaseInsertNodeData;
		position?: { x: number; y: number };
	};
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
	availableNodes: Node[];
}

interface DatabaseConnection {
	id: string;
	name: string;
	database_type: string;
	host?: string;
	port?: number;
	database_name?: string;
	is_active: boolean;
}

interface DatabaseTable {
	name: string;
	schema?: string;
	type?: string;
}

interface TableColumn {
	column_name: string;
	column_type: string;
	is_nullable: boolean;
	is_required: boolean;
	default_value?: any;
	is_primary_key: boolean;
	is_autoincrement: boolean;
}

type DatabaseInsertTabId = "configuration" | "guardrails";

function ColumnMappingRow({
	column,
	mapping,
	onUpdate,
	availableNodes,
}: {
	column: TableColumn;
	mapping: ColumnMapping;
	onUpdate: (mapping: ColumnMapping) => void;
	availableNodes: Node[];
}) {
	const [expanded, setExpanded] = useState(false);

	const getTypeColor = (type: string) => {
		const upperType = type.toUpperCase();
		if (
			upperType.includes("VARCHAR") ||
			upperType.includes("TEXT") ||
			upperType.includes("CHAR")
		) {
			return "bg-slate-100 text-gray-800 border-gray-200";
		} else if (
			upperType.includes("INT") ||
			upperType.includes("SERIAL") ||
			upperType.includes("NUMERIC")
		) {
			return "bg-purple-100 text-purple-900 border-purple-200";
		} else if (upperType.includes("BOOL")) {
			return "bg-[#F1F8E9] text-[#0DA931] border-[#0DA931]";
		} else if (upperType.includes("DATE") || upperType.includes("TIME")) {
			return "bg-amber-50 text-amber-900 border-amber-200";
		} else if (upperType.includes("JSON")) {
			return "bg-orange-50 text-orange-900 border-orange-200";
		}
		return "bg-slate-100 text-gray-800 border-gray-200";
	};

	const sourceModeOptions = [
		{
			value: "static",
			label: "Static Value",
			description: "Enter a fixed value",
		},
		{
			value: "previous",
			label: "Previous Node",
			description: "Output from previous node",
		},
		{
			value: "specific",
			label: "Specific Node",
			description: "Choose a specific node",
		},
		{
			value: "start",
			label: "Original Input",
			description: "Workflow starting input",
		},
		{
			value: "field",
			label: "Custom Template",
			description: "Advanced mapping",
		},
	];

	const handleToggleExpanded = useCallback(() => {
		setExpanded(!expanded);
	}, [expanded]);

	const handleMappingUpdate = useCallback(
		(mapping: ColumnMapping) => {
			onUpdate(mapping);
		},
		[onUpdate],
	);

	// Factory functions for form handlers
	const handleSourceModeChange = useCallback(
		(value: string) => {
			handleMappingUpdate({ ...mapping, source_mode: value as any });
		},
		[mapping, handleMappingUpdate],
	);

	const handleStaticValueChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			handleMappingUpdate({ ...mapping, static_value: e.target.value });
		},
		[mapping, handleMappingUpdate],
	);

	const handleSourceNodeChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			handleMappingUpdate({
				...mapping,
				source_node_id: e.target.value,
				source_field_path: "",
			});
		},
		[mapping, handleMappingUpdate],
	);

	const handleFieldPathChange = useCallback(
		(fieldPath: string) => {
			handleMappingUpdate({ ...mapping, source_field_path: fieldPath });
		},
		[mapping, handleMappingUpdate],
	);

	const handleManualFieldPathChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			handleMappingUpdate({ ...mapping, source_field_path: e.target.value });
		},
		[mapping, handleMappingUpdate],
	);

	const handleCustomTemplateChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			handleMappingUpdate({ ...mapping, custom_template: e.target.value });
		},
		[mapping, handleMappingUpdate],
	);

	return (
		<div className="overflow-hidden rounded-[4px] border border-gray-200 bg-white shadow-sm">
			<div
				className="flex cursor-pointer items-center gap-3 p-3 transition-colors hover:bg-slate-50"
				onClick={handleToggleExpanded}
			>
				<ChevronDown
					className={`h-4 w-4 text-gray-500 transition-transform ${expanded ? "rotate-180" : ""}`}
				/>

				<div className="flex flex-1 items-center gap-3">
					<div className="flex min-w-[200px] items-center gap-2">
						<span className="text-sm font-medium text-gray-900">
							{column.column_name}
							{column.is_required && !column.is_autoincrement && (
								<span className="ml-1 text-red-600">*</span>
							)}
						</span>
						{column.is_primary_key && (
							<span className="rounded-[4px] border border-blue-200 bg-blue-50 px-1.5 py-0.5 text-xs text-blue-900">
								PK
							</span>
						)}
						{column.is_autoincrement && (
							<span className="rounded-[4px] border border-[#0DA931] bg-[#F1F8E9] px-1.5 py-0.5 text-xs text-[#0DA931]">
								AUTO
							</span>
						)}
					</div>

					<span
						className={`text-xs px-2 py-0.5 rounded border ${getTypeColor(column.column_type)}`}
					>
						{column.column_type}
					</span>

					<div className="flex flex-1 items-center justify-end gap-2 text-right">
						<span className="text-xs text-gray-600">
							{mapping.source_mode === "static" && "Static Value"}
							{mapping.source_mode === "previous" && "Previous Node Output"}
							{mapping.source_mode === "specific" && mapping.source_node_id && (
								<>
									From:{" "}
									{availableNodes.find((n) => n.id === mapping.source_node_id)
										?.data.name || "Unknown"}
									{mapping.source_field_path && (
										<span className="ml-1 text-emerald-800">
											→ {mapping.source_field_path}
										</span>
									)}
								</>
							)}
							{mapping.source_mode === "start" && "Original Input"}
							{mapping.source_mode === "field" && "Custom Template"}
						</span>
						{mapping.source_mode === "specific" &&
							mapping.source_node_id &&
							availableNodes.find((n) => n.id === mapping.source_node_id)?.data
								.agent_config?.structured_outputs?.length > 0 && (
								<span className="rounded-[4px] border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-xs text-emerald-900">
									Structured
								</span>
							)}
					</div>
				</div>
			</div>

			{expanded && (
				<div className="space-y-4 border-t border-gray-200 bg-slate-50 p-4">
					<div>
						<label
							htmlFor="data-source-select"
							className="mb-2 block text-sm font-medium text-gray-800"
						>
							Data Source
						</label>
						<Dropdown
							value={mapping.source_mode}
							onChange={handleSourceModeChange}
							options={sourceModeOptions}
							placeholder="Select source"
							menuAppearance="light"
						/>
					</div>

					{mapping.source_mode === "static" && (
						<div>
							<label
								htmlFor="static-value-input"
								className="mb-2 block text-sm font-medium text-gray-800"
							>
								Static Value
							</label>
							<input
								id="static-value-input"
								type="text"
								value={mapping.static_value || ""}
								onChange={handleStaticValueChange}
								className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								placeholder={`Enter ${column.column_type.toLowerCase()} value`}
							/>
							{column.default_value && (
								<p className="mt-1 text-xs text-gray-600">
									Default: {column.default_value}
								</p>
							)}
						</div>
					)}

					{mapping.source_mode === "specific" && (
						<div>
							<label className="mb-2 block text-sm font-medium text-gray-800">
								Select Source Node
							</label>
							<select
								value={mapping.source_node_id || ""}
								onChange={handleSourceNodeChange}
								className="w-full appearance-none rounded-[4px] border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-900 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
							>
								<option value="">Choose a node...</option>
								{availableNodes.map((n) => (
									<option key={n.id} value={n.id}>
										{n.data.name}
										{n.data.agent_config?.structured_outputs?.length > 0 &&
											" (Structured)"}
									</option>
								))}
							</select>

							{mapping.source_node_id && (
								<div className="mt-2">
									<label className="mb-1 block text-xs font-medium text-gray-600">
										Field Path (optional - for structured outputs)
									</label>
									{(() => {
										const sourceNode = availableNodes.find(
											(n) => n.id === mapping.source_node_id,
										);
										const hasStructuredOutput =
											sourceNode?.data?.agent_config?.structured_outputs
												?.length > 0;
										const structuredFields = hasStructuredOutput
											? sourceNode?.data?.agent_config?.structured_outputs?.[0]
													?.fields || []
											: [];

										if (hasStructuredOutput && structuredFields.length > 0) {
											return (
												<StructuredFieldPicker
													fields={structuredFields}
													value={mapping.source_field_path || ""}
													onChange={handleFieldPathChange}
													placeholder="Select a field or enter path"
													allowManualInput={true}
													nodeName={sourceNode?.data?.name || ""}
												/>
											);
										} else {
											return (
												<input
													type="text"
													value={mapping.source_field_path || ""}
													onChange={handleManualFieldPathChange}
													className="w-full rounded-[4px] border border-gray-200 bg-white px-2 py-1 text-sm text-gray-900 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
													placeholder="e.g., customer.name or items[0].price"
												/>
											);
										}
									})()}
								</div>
							)}
						</div>
					)}

					{mapping.source_mode === "field" && (
						<div>
							<label className="mb-2 block text-sm font-medium text-gray-800">
								Custom Template
							</label>
							<textarea
								value={mapping.custom_template || ""}
								onChange={handleCustomTemplateChange}
								className="min-h-[80px] w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 font-mono text-sm text-gray-900 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								placeholder="e.g., {node_id.field_name} or custom expression"
							/>
							<p className="mt-1 text-xs text-gray-600">
								Use {"{node_id}"} or {"{node_id.field}"} for node outputs
							</p>
						</div>
					)}

					<div className="flex items-start gap-3 rounded-[4px] border border-gray-200 bg-white p-3 text-xs">
						<InfoTooltip text="Column metadata from database schema" />
						<div className="space-y-1 text-gray-600">
							<div>
								Type:{" "}
								<span className="text-gray-900">
									{column.column_type}
								</span>
							</div>
							<div>
								Nullable:{" "}
								<span className="text-gray-900">
									{column.is_nullable ? "Yes" : "No"}
								</span>
							</div>
							{column.default_value && (
								<div>
									Default:{" "}
									<span className="text-gray-900">
										{column.default_value}
									</span>
								</div>
							)}
							{column.is_primary_key && (
								<div className="text-blue-800">
									Primary Key
								</div>
							)}
							{column.is_autoincrement && (
								<div className="text-[#0DA931]">
									Auto-increment (will be generated)
								</div>
							)}
						</div>
					</div>
				</div>
			)}
		</div>
	);
}

export default function DatabaseInsertPropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
	availableNodes,
}: DatabaseInsertPropertiesPanelProps) {
	const config = node.data.database_insert_config || {};

	// Database configuration
	const [connectionId, setConnectionId] = useState(config.connection_id || "");
	const [tableName, setTableName] = useState(config.table_name || "");
	const [columnMappings, setColumnMappings] = useState<ColumnMapping[]>(
		config.column_mappings || [],
	);
	const [returnInsertedRows, setReturnInsertedRows] = useState(
		config.return_inserted_rows ?? true,
	);
	const [onConflictStrategy, setOnConflictStrategy] = useState(
		config.on_conflict_strategy || "fail",
	);
	const [conflictColumns, setConflictColumns] = useState<string[]>(
		config.conflict_columns || [],
	);
	const [timeoutSeconds, setTimeoutSeconds] = useState(
		config.timeout_seconds || 30,
	);
	const [batchSize, setBatchSize] = useState(config.batch_size || 1);
	const [transactionMode, setTransactionMode] = useState(
		config.transaction_mode || "auto",
	);

	// Available connections and tables
	const [connections, setConnections] = useState<DatabaseConnection[]>([]);
	const [tables, setTables] = useState<DatabaseTable[]>([]);
	const [tableColumns, setTableColumns] = useState<TableColumn[]>([]);
	const [loadingConnections, setLoadingConnections] = useState(false);
	const [loadingTables, setLoadingTables] = useState(false);
	const [loadingColumns, setLoadingColumns] = useState(false);

	// Tab navigation
	const [activeTab, setActiveTab] = useState<DatabaseInsertTabId>("configuration");

	// Track initial values for unsaved changes detection
	const initialValues = useRef({
		connectionId: config.connection_id || "",
		tableName: config.table_name || "",
		columnMappings: JSON.stringify(config.column_mappings || []),
		returnInsertedRows: config.return_inserted_rows ?? true,
		onConflictStrategy: config.on_conflict_strategy || "fail",
		conflictColumns: JSON.stringify(config.conflict_columns || []),
		timeoutSeconds: config.timeout_seconds || 30,
		batchSize: config.batch_size || 1,
		transactionMode: config.transaction_mode || "auto",
	});

	// Unsaved changes detection
	const hasUnsavedChanges = useMemo(() => {
		const init = initialValues.current;
		return (
			connectionId !== init.connectionId ||
			tableName !== init.tableName ||
			JSON.stringify(columnMappings) !== init.columnMappings ||
			returnInsertedRows !== init.returnInsertedRows ||
			onConflictStrategy !== init.onConflictStrategy ||
			JSON.stringify(conflictColumns) !== init.conflictColumns ||
			timeoutSeconds !== init.timeoutSeconds ||
			batchSize !== init.batchSize ||
			transactionMode !== init.transactionMode
		);
	}, [
		connectionId,
		tableName,
		columnMappings,
		returnInsertedRows,
		onConflictStrategy,
		conflictColumns,
		timeoutSeconds,
		batchSize,
		transactionMode,
	]);

	// Load database connections on mount
	useEffect(() => {
		loadConnections().catch((error) => {
			console.error("Failed to load database connections:", error);
		});
	}, []);

	// Load tables when connection changes
	useEffect(() => {
		if (connectionId) {
			loadTables(connectionId).catch((error) => {
				console.error("Failed to load tables:", error);
			});
		} else {
			setTables([]);
			setTableName("");
			setTableColumns([]);
			setColumnMappings([]);
		}
	}, [connectionId]);

	// Load columns when table changes
	useEffect(() => {
		console.log("Table selection changed:", { connectionId, tableName });
		if (connectionId && tableName) {
			loadTableColumns(connectionId, tableName).catch((error) => {
				console.error("Failed to load table columns:", error);
			});
		} else {
			setTableColumns([]);
			setColumnMappings([]);
		}
	}, [connectionId, tableName]);

	const loadConnections = async () => {
		setLoadingConnections(true);
		try {
			const conns = await api.getDatabaseConnections(true);
			setConnections(conns || []);
		} catch (error) {
			console.error("Failed to load database connections:", error);
		} finally {
			setLoadingConnections(false);
		}
	};

	const loadTables = async (connId: string) => {
		setLoadingTables(true);
		try {
			const schema = await api.getDatabaseSchema(connId);
			if (schema && schema.tables) {
				const tableList = Object.keys(schema.tables).map((name) => ({
					name,
					type: "table",
				}));
				setTables(tableList);
			}
		} catch (error) {
			console.error("Failed to load tables:", error);
			setTables([]);
		} finally {
			setLoadingTables(false);
		}
	};

	const loadTableColumns = async (connId: string, table: string) => {
		console.log("Loading columns for table:", table, "connection:", connId);
		setLoadingColumns(true);
		try {
			// Encode the table name to handle special characters
			const encodedTable = encodeURIComponent(table);
			const url = `/api/datasources/connections/${connId}/tables/${encodedTable}/columns`;
			console.log("Fetching from URL:", url);

			const response = await fetch(url);

			if (response.ok) {
				const data = await response.json();
				setTableColumns(data.columns || []);

				// Initialize column mappings for non-autoincrement columns
				const mappings: ColumnMapping[] = (data.columns || [])
					.filter((col: TableColumn) => !col.is_autoincrement)
					.map((col: TableColumn) => ({
						...col,
						source_mode: "static" as const,
						static_value: col.default_value || null,
					}));
				setColumnMappings(mappings);
				console.log("Set column mappings:", mappings);
			} else {
				setTableColumns([]);
				setColumnMappings([]);
			}
		} catch (error) {
			console.error("Failed to load table columns:", error);
			setTableColumns([]);
			setColumnMappings([]);
		} finally {
			setLoadingColumns(false);
		}
	};

	const updateColumnMapping = (index: number, mapping: ColumnMapping) => {
		const newMappings = [...columnMappings];
		newMappings[index] = mapping;
		setColumnMappings(newMappings);
	};

	const handleSave = useCallback(() => {
		const updatedConfig: DatabaseInsertConfig = {
			connection_id: connectionId,
			table_name: tableName,
			column_mappings: columnMappings,
			return_inserted_rows: returnInsertedRows,
			on_conflict_strategy: onConflictStrategy,
			conflict_columns: conflictColumns,
			timeout_seconds: timeoutSeconds,
			batch_size: batchSize,
			transaction_mode: transactionMode,
		};

		const updateData: any = {
			database_insert_config: updatedConfig,
		};

		// Preserve the current position if it exists
		if (node.position) {
			updateData.position = node.position;
		}

		onUpdateNode(node.id, updateData);

		onClose();
	}, [
		connectionId,
		tableName,
		columnMappings,
		returnInsertedRows,
		onConflictStrategy,
		conflictColumns,
		timeoutSeconds,
		batchSize,
		transactionMode,
		node,
		onUpdateNode,
		onClose,
	]);

	const selectedConnection = connections.find((c) => c.id === connectionId);

	// Keyboard shortcut: Cmd/Ctrl+S to save
	const handleSaveRef = useRef(handleSave);
	handleSaveRef.current = handleSave;

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === "s") {
				e.preventDefault();
				handleSaveRef.current();
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, []);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleTimeoutChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setTimeoutSeconds(parseInt(e.target.value) || 30);
		},
		[],
	);

	const handleReturnInsertedRowsChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setReturnInsertedRows(e.target.checked);
		},
		[],
	);

	const handleUpdateColumnMapping = useCallback(
		(index: number, mapping: ColumnMapping) => {
			updateColumnMapping(index, mapping);
		},
		[],
	);

	const handleDeleteAndClose = useCallback(() => {
		onDeleteNode(node.id);
		onClose();
	}, [onDeleteNode, node.id, onClose]);

	// Factory functions for column mapping updates
	const createUpdateMappingHandler = useCallback(
		(index: number) => (updated: ColumnMapping) => {
			handleUpdateColumnMapping(index, updated);
		},
		[handleUpdateColumnMapping],
	);

	// Responsive sidebar collapse
	const contentRef = useRef<HTMLDivElement>(null);
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

	useEffect(() => {
		const el = contentRef.current;
		if (!el || typeof ResizeObserver === "undefined") return;
		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				setSidebarCollapsed(entry.contentRect.width < 400);
			}
		});
		observer.observe(el);
		return () => observer.disconnect();
	}, []);

	// Sidebar tab configuration
	const panelTabs = useMemo(
		() => [
			{
				id: "configuration" as const,
				label: "Configuration",
				description: "Database & mappings",
				icon: <Database className="h-4 w-4" />,
			},
			{
				id: "guardrails" as const,
				label: "Guardrails",
				description: "Safety policies",
				icon: <ShieldCheck className="h-4 w-4" />,
			},
		],
		[],
	);

	const isGuardrailsTab = activeTab === "guardrails";

	return (
		<div
			className="fixed inset-0 z-[110] flex animate-fadeIn items-start justify-center bg-black/50 px-4 pb-4 pt-[5vh] backdrop-blur-sm"
			onClick={handleBackdropClick}
		>
			<div
				className="w-[85vw] max-w-[1800px]"
				onClick={handleStopPropagation}
			>
				<div
					className={cn(
						"flex min-h-[320px] flex-col rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]",
						isGuardrailsTab
							? "max-h-[90vh] overflow-visible"
							: "max-h-[80vh] overflow-hidden",
					)}
				>
					<div className="flex-none border-b border-gray-200 bg-white">
						<div className="flex items-center justify-between px-6 py-4">
							<div className="flex items-start gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
									<Database className="h-5 w-5 text-orange-600" />
								</div>
								<div>
									<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
										Tool configuration
									</p>
									<h2 className="text-lg font-semibold text-gray-900">
										Database Insert Configuration
									</h2>
									<p className="mt-0.5 text-sm text-gray-600">
										Configure static database insertion
									</p>
								</div>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								aria-label="Close"
							>
								<X className="h-5 w-5" />
							</button>
						</div>
					</div>

					<div
						ref={contentRef}
						className={cn(
							"flex min-h-0 flex-1",
							!isGuardrailsTab && "overflow-hidden",
						)}
					>
						<ConfigSidebar
							items={panelTabs}
							activeItem={activeTab}
							onChange={(id) =>
								setActiveTab(id as DatabaseInsertTabId)
							}
							collapsed={sidebarCollapsed}
							variant="light"
						/>

						<div
							className={cn(
								"custom-scrollbar min-h-0 flex-1 space-y-6 bg-slate-50 px-6 py-5",
								isGuardrailsTab ? "overflow-visible" : "overflow-y-auto",
							)}
						>
								{activeTab === "configuration" && (
									<>
										<div className="rounded-[4px] border border-gray-200 bg-white p-5 shadow-sm">
											<div className="mb-4 flex items-center gap-2">
												<h3 className="text-sm font-semibold text-gray-900">
													Database Connection
												</h3>
												<InfoTooltip text="Select the database and table to insert into" />
											</div>

											<div className="space-y-4">
												<div>
													<label className="mb-2 block text-sm font-medium text-gray-800">
														Connection
													</label>
													{loadingConnections ? (
														<div className="text-sm text-gray-600">
															Loading connections...
														</div>
													) : connections.length === 0 ? (
														<div className="rounded-[4px] border border-orange-400 bg-white p-4 shadow-sm">
															<p className="text-sm text-gray-800">
																No database connections found. Add connections in the Data
																Sources page.
															</p>
														</div>
													) : (
														<Dropdown
															value={connectionId}
															onChange={setConnectionId}
															options={connections.map((conn) => ({
																value: conn.id,
																label: conn.name,
																description: `${conn.database_type.toUpperCase()} - ${conn.host}:${conn.port}/${conn.database_name}`,
															}))}
															placeholder="Select a database connection"
															menuAppearance="light"
														/>
													)}
												</div>

												{connectionId && (
													<div>
														<label className="mb-2 block text-sm font-medium text-gray-800">
															Table
														</label>
														{loadingTables ? (
															<div className="text-sm text-gray-600">
																Loading tables...
															</div>
														) : tables.length === 0 ? (
															<div className="rounded-[4px] border border-gray-200 bg-white p-4">
																<p className="text-sm text-gray-600">
																	No tables found in selected database
																</p>
															</div>
														) : (
															<Dropdown
																value={tableName}
																onChange={setTableName}
																options={tables.map((table) => ({
																	value: table.name,
																	label: table.name,
																	description: table.type || "table",
																}))}
																placeholder="Select a table"
																menuAppearance="light"
															/>
														)}
													</div>
												)}
											</div>
										</div>

										{tableName && (
											<div className="rounded-[4px] border border-gray-200 bg-white p-5 shadow-sm">
												<div className="mb-4 flex items-center gap-2">
													<h3 className="text-sm font-semibold text-gray-900">
														Column Mappings
													</h3>
													<InfoTooltip text="Map data sources to table columns" />
												</div>

												{loadingColumns ? (
													<div className="flex flex-col items-center justify-center py-8">
														<div className="mb-3 h-10 w-10 animate-spin rounded-full border-2 border-orange-600 border-b-transparent" />
														<p className="text-sm text-gray-600">
															Loading table columns...
														</p>
													</div>
												) : tableColumns.length > 0 ? (
													<div className="space-y-3">
														{columnMappings.map((mapping, index) => (
															<ColumnMappingRow
																key={mapping.column_name}
																column={
																	tableColumns.find(
																		(c) => c.column_name === mapping.column_name,
																	) || (mapping as any)
																}
																mapping={mapping}
																onUpdate={createUpdateMappingHandler(index)}
																availableNodes={availableNodes}
															/>
														))}

														<div className="mt-4 rounded-[4px] border border-gray-200 bg-slate-50 p-3 text-xs text-gray-700">
															<div className="flex flex-wrap items-center gap-4">
																<div className="flex items-center gap-1">
																	<span className="text-red-600">*</span> Required field
																</div>
																<div className="flex items-center gap-1">
																	<span className="rounded-[4px] border border-blue-200 bg-blue-50 px-1.5 py-0.5 text-blue-900">
																		PK
																	</span>{" "}
																	Primary Key
																</div>
																<div className="flex items-center gap-1">
																	<span className="rounded-[4px] border border-[#0DA931] bg-[#F1F8E9] px-1.5 py-0.5 text-[#0DA931]">
																		AUTO
																	</span>{" "}
																	Auto-generated
																</div>
															</div>
														</div>
													</div>
												) : (
													<div className="py-6 text-center">
														<p className="text-sm text-gray-600">
															No columns found for this table
														</p>
													</div>
												)}
											</div>
										)}

										<div className="rounded-[4px] border border-gray-200 bg-white p-5 shadow-sm">
											<div className="mb-4 flex items-center gap-2">
												<h3 className="text-sm font-semibold text-gray-900">Options</h3>
												<InfoTooltip text="Configure insert behavior" />
											</div>

											<div className="space-y-4">
												<div className="flex items-center justify-between rounded-[4px] border border-gray-200 bg-slate-50 p-4">
													<div>
														<h4 className="text-sm font-medium text-gray-900">
															Return Inserted Rows
														</h4>
														<p className="mt-0.5 text-xs text-gray-600">
															Include inserted data in node output
														</p>
													</div>
													<label className="relative inline-flex cursor-pointer items-center">
														<input
															type="checkbox"
															checked={returnInsertedRows}
															onChange={handleReturnInsertedRowsChange}
															className="peer sr-only"
														/>
														<div className="peer h-6 w-11 rounded-full bg-gray-300 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all peer-checked:bg-orange-600 peer-checked:after:translate-x-full" />
													</label>
												</div>

												<div>
													<label className="mb-2 block text-sm font-medium text-gray-800">
														Timeout (seconds)
													</label>
													<input
														type="number"
														min="5"
														max="300"
														value={timeoutSeconds}
														onChange={handleTimeoutChange}
														className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
													/>
												</div>
											</div>
										</div>

										{selectedConnection && (
											<div className="rounded-[4px] border border-gray-200 bg-white p-4 text-sm text-gray-700 shadow-sm">
												<div className="mb-1 flex items-center gap-2">
													<Database className="h-4 w-4 text-orange-600" />
													<span className="font-medium text-gray-900">
														Connection Details
													</span>
												</div>
												<div className="space-y-1">
													<div>
														Type: {selectedConnection.database_type.toUpperCase()}
													</div>
													<div>
														Host: {selectedConnection.host}:{selectedConnection.port}
													</div>
													<div>Database: {selectedConnection.database_name}</div>
												</div>
											</div>
										)}
									</>
								)}

								{activeTab === "guardrails" && (
									<ToolGuardrailsSection toolNodeId={node.id} />
								)}
						</div>
					</div>

					<div className="border-t border-gray-200 bg-white px-6 py-3">
						<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
							<button
								type="button"
								onClick={handleDeleteAndClose}
								className="flex items-center gap-1.5 rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-xs text-red-700 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-800"
							>
								<Trash2 className="h-3.5 w-3.5" />
								Delete Node
							</button>

							<div className="flex items-center gap-3 sm:ml-auto">
								{hasUnsavedChanges && (
									<span className="flex items-center gap-1.5 text-[11px] text-gray-600">
										<span className="h-1.5 w-1.5 animate-smoothPulse rounded-[4px] bg-orange-500" />
										Unsaved
									</span>
								)}
								<span className="hidden text-[11px] text-gray-400 sm:inline">
									{"\u2318"}S to save
								</span>
								<button
									type="button"
									onClick={onClose}
									className="rounded-[4px] border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								>
									Cancel
								</button>
								<button
									type="button"
									onClick={handleSave}
									disabled={
										!connectionId || !tableName || columnMappings.length === 0
									}
									className="rounded-[4px] bg-orange-600 px-5 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								>
									<span className="inline-flex items-center gap-1.5">
										<Save className="h-3.5 w-3.5" />
										Save Changes
									</span>
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
