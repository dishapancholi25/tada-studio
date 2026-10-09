"use client";

import { Database, Save, Shield, ShieldCheck, Sliders, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import ConfigSidebar from "./ConfigSidebar";
import DatabaseAdvancedSection from "./sections/DatabaseAdvancedSection";
import DatabaseConnectionSection from "./sections/DatabaseConnectionSection";
import QueryConfigSection from "./sections/QueryConfigSection";
import ToolGuardrailsSection from "@/components/core/guardrails/ToolGuardrailsSection";
import { cn } from "@/lib/utils";

interface DatabaseQueryConfig {
	connection_id?: string;
	table_name?: string;
	table_names?: string[];
	allowed_operations?: string[];
	max_rows?: number;
	timeout_seconds?: number;
	enable_read_only?: boolean;
	return_format?: string;
	include_schema?: boolean;
	parent_agent_id?: string;
}

interface DatabaseQueryNodeData {
	id: string;
	name: string;
	database_query_config?: DatabaseQueryConfig;
}

interface DatabaseQueryPropertiesPanelProps {
	node: {
		id: string;
		data: DatabaseQueryNodeData;
		position?: { x: number; y: number };
	};
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
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

type DatabaseTabId = "connection" | "query" | "advanced" | "guardrails";

export default function DatabaseQueryPropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}: DatabaseQueryPropertiesPanelProps) {
	const config = node.data.database_query_config || {};

	// Database configuration
	const [connectionId, setConnectionId] = useState(config.connection_id || "");
	const [tableName, setTableName] = useState(config.table_name || "");
	const [tableNames, setTableNames] = useState<string[]>(
		config.table_names || (config.table_name ? [config.table_name] : []),
	);
	const [allowedOperations, setAllowedOperations] = useState<string[]>(
		config.allowed_operations || ["SELECT"],
	);
	const [maxRows, setMaxRows] = useState(config.max_rows || 100);
	const [timeoutSeconds, setTimeoutSeconds] = useState(
		config.timeout_seconds || 30,
	);
	const [enableReadOnly, setEnableReadOnly] = useState(
		config.enable_read_only || false,
	);
	const [returnFormat, setReturnFormat] = useState(
		config.return_format || "json",
	);
	const [includeSchema, setIncludeSchema] = useState(
		config.include_schema ?? true,
	);

	// Available connections and tables
	const [connections, setConnections] = useState<DatabaseConnection[]>([]);
	const [tables, setTables] = useState<DatabaseTable[]>([]);
	const [loadingConnections, setLoadingConnections] = useState(false);
	const [loadingTables, setLoadingTables] = useState(false);

	// Tab navigation
	const [activeTab, setActiveTab] = useState<DatabaseTabId>("connection");

	// Track initial values for unsaved changes detection
	const initialValues = useRef({
		connectionId: config.connection_id || "",
		tableNames:
			config.table_names || (config.table_name ? [config.table_name] : []),
		allowedOperations: config.allowed_operations || ["SELECT"],
		maxRows: config.max_rows || 100,
		timeoutSeconds: config.timeout_seconds || 30,
		enableReadOnly: config.enable_read_only || false,
		returnFormat: config.return_format || "json",
		includeSchema: config.include_schema ?? true,
	});

	// Unsaved changes detection
	const hasUnsavedChanges = useMemo(() => {
		const init = initialValues.current;
		return (
			connectionId !== init.connectionId ||
			JSON.stringify(tableNames) !== JSON.stringify(init.tableNames) ||
			JSON.stringify(allowedOperations) !==
				JSON.stringify(init.allowedOperations) ||
			maxRows !== init.maxRows ||
			timeoutSeconds !== init.timeoutSeconds ||
			enableReadOnly !== init.enableReadOnly ||
			returnFormat !== init.returnFormat ||
			includeSchema !== init.includeSchema
		);
	}, [
		connectionId,
		tableNames,
		allowedOperations,
		maxRows,
		timeoutSeconds,
		enableReadOnly,
		returnFormat,
		includeSchema,
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
			setTableNames([]);
		}
	}, [connectionId]);

	const loadConnections = async () => {
		setLoadingConnections(true);
		try {
			const conns = await api.getDatabaseConnections(true);
			setConnections(conns || []);
		} catch (error) {
			// Silent fail
		} finally {
			setLoadingConnections(false);
		}
	};

	const loadTables = async (connId: string, forceRefresh = true) => {
		setLoadingTables(true);
		try {
			const schema = await api.getDatabaseSchema(connId, forceRefresh);
			if (schema && schema.tables) {
				const tableList = Object.keys(schema.tables).map((name) => ({
					name,
					type: "table",
				}));
				setTables(tableList);
			}
		} catch (error) {
			setTables([]);
		} finally {
			setLoadingTables(false);
		}
	};

	const handleSave = useCallback(() => {
		const updatedConfig: DatabaseQueryConfig = {
			connection_id: connectionId,
			table_name: tableNames.length === 1 ? tableNames[0] : "",
			table_names: tableNames,
			allowed_operations: allowedOperations,
			max_rows: maxRows,
			timeout_seconds: timeoutSeconds,
			enable_read_only: enableReadOnly,
			return_format: returnFormat,
			include_schema: includeSchema,
			parent_agent_id: config.parent_agent_id,
		};

		const updateData: any = {
			database_query_config: updatedConfig,
		};

		if (node.position) {
			updateData.position = node.position;
		}

		onUpdateNode(node.id, updateData);
		onClose();
	}, [
		connectionId,
		tableNames,
		allowedOperations,
		maxRows,
		timeoutSeconds,
		enableReadOnly,
		returnFormat,
		includeSchema,
		config.parent_agent_id,
		node,
		onUpdateNode,
		onClose,
	]);

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

	const handleLoadTables = useCallback(() => {
		void loadTables(connectionId, true);
	}, [connectionId]);

	const handleReadOnlyToggle = useCallback((checked: boolean) => {
		setEnableReadOnly(checked);
		if (checked) {
			setAllowedOperations(["SELECT"]);
		}
	}, []);

	const handleDeleteAndClose = useCallback(() => {
		onDeleteNode(node.id);
		onClose();
	}, [onDeleteNode, node.id, onClose]);

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
				id: "connection" as const,
				label: "Connection",
				description: "Database & tables",
				icon: <Database className="h-4 w-4" />,
			},
			{
				id: "query" as const,
				label: "Query",
				description: "Operations & limits",
				icon: <Shield className="h-4 w-4" />,
			},
			{
				id: "advanced" as const,
				label: "Advanced",
				description: "Performance & format",
				icon: <Sliders className="h-4 w-4" />,
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
						<div className="flex flex-wrap items-start justify-between gap-4 px-6 pb-4 pt-5">
							<div className="flex min-w-0 items-start gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
									<Database className="h-5 w-5 text-orange-600" aria-hidden />
								</div>
								<div className="min-w-0">
									<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
										Tool configuration
									</p>
									<h2 className="text-lg font-semibold tracking-tight text-gray-900">
										Database Query Configuration
									</h2>
								</div>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="shrink-0 rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
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
								setActiveTab(id as DatabaseTabId)
							}
							collapsed={sidebarCollapsed}
							variant="light"
						/>

						<div
							className={cn(
								"flex-1 min-h-0 bg-slate-50 px-6 py-4",
								isGuardrailsTab ? "overflow-visible" : "overflow-y-auto",
							)}
						>
								{activeTab === "connection" && (
									<DatabaseConnectionSection
										connectionId={connectionId}
										onConnectionIdChange={setConnectionId}
										tableNames={tableNames}
										onTableNamesChange={setTableNames}
										connections={connections}
										tables={tables}
										loadingConnections={loadingConnections}
										loadingTables={loadingTables}
										onRefreshTables={handleLoadTables}
									/>
								)}

								{activeTab === "query" && (
									<QueryConfigSection
										enableReadOnly={enableReadOnly}
										onEnableReadOnlyChange={
											handleReadOnlyToggle
										}
										allowedOperations={allowedOperations}
										onAllowedOperationsChange={
											setAllowedOperations
										}
									/>
								)}

								{activeTab === "advanced" && (
									<DatabaseAdvancedSection
										maxRows={maxRows}
										onMaxRowsChange={setMaxRows}
										timeoutSeconds={timeoutSeconds}
										onTimeoutSecondsChange={
											setTimeoutSeconds
										}
										returnFormat={returnFormat}
										onReturnFormatChange={setReturnFormat}
										includeSchema={includeSchema}
										onIncludeSchemaChange={setIncludeSchema}
									/>
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
								<Trash2 className="w-3.5 h-3.5" />
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
									className="rounded-[4px] bg-orange-600 px-5 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								>
									<span className="inline-flex items-center gap-1.5">
										<Save className="w-3.5 h-3.5" />
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
