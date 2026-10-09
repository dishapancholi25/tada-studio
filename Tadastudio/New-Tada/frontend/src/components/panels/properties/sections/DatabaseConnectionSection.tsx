"use client";

import { Database, RefreshCw, Table } from "lucide-react";
import Checkbox from "@/components/ui/Checkbox";
import Dropdown from "@/components/ui/Dropdown";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";

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

interface DatabaseConnectionSectionProps {
	connectionId: string;
	onConnectionIdChange: (connectionId: string) => void;
	tableNames: string[];
	onTableNamesChange: (tableNames: string[]) => void;
	connections: DatabaseConnection[];
	tables: DatabaseTable[];
	loadingConnections: boolean;
	loadingTables: boolean;
	onRefreshTables: () => void;
}

export default function DatabaseConnectionSection({
	connectionId,
	onConnectionIdChange,
	tableNames,
	onTableNamesChange,
	connections,
	tables,
	loadingConnections,
	loadingTables,
	onRefreshTables,
}: DatabaseConnectionSectionProps) {
	const selectedConnection = connections.find((c) => c.id === connectionId);

	const handleCheckboxChange = (checked: boolean, tableName: string) => {
		if (checked) {
			onTableNamesChange([...tableNames, tableName]);
		} else {
			onTableNamesChange(tableNames.filter((t) => t !== tableName));
		}
	};

	const createConnectionOption = (conn: DatabaseConnection) => ({
		value: conn.id,
		label: conn.name,
		description: `${conn.database_type.toUpperCase()} - ${conn.host}:${conn.port}/${conn.database_name}`,
	});

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex min-w-0 items-start gap-3">
						<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
							<Database className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div className="min-w-0">
							<h3 className="text-lg font-semibold text-gray-900">
								Database Connection
							</h3>
							<p className="text-sm text-gray-600">
								Select database and tables to query
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div>
						<div className="mb-3 flex items-center gap-2">
							<label
								htmlFor="connection-select"
								className="block text-sm font-semibold text-gray-900"
							>
								Connection
							</label>
							<InfoTooltip text="Select the database connection to use for queries" />
						</div>

						{loadingConnections ? (
							<div className="rounded-[4px] border border-gray-200 bg-white p-4">
								<p className="text-sm text-gray-600">
									Loading connections...
								</p>
							</div>
						) : connections.length === 0 ? (
							<div className="rounded-[4px] border border-blue-200 bg-white p-4 shadow-sm">
								<p className="text-sm text-blue-900">
									No database connections found. Add connections in the Data
									Sources page.
								</p>
							</div>
						) : (
							<Dropdown
								value={connectionId}
								onChange={onConnectionIdChange}
								options={connections.map(createConnectionOption)}
								placeholder="Select a database connection"
								menuAppearance="light"
							/>
						)}
					</div>

					{selectedConnection && (
						<div className="rounded-[4px] border border-gray-200 bg-slate-50 p-4">
							<div className="mb-2 flex items-center gap-2">
								<Database className="h-4 w-4 text-orange-600" />
								<span className="text-sm font-semibold text-gray-900">
									Connection Details
								</span>
							</div>
							<div className="space-y-1 text-sm text-gray-600">
								<div>
									Type:{" "}
									<span className="font-medium text-gray-900">
										{selectedConnection.database_type.toUpperCase()}
									</span>
								</div>
								<div>
									Host:{" "}
									<span className="font-medium text-gray-900">
										{selectedConnection.host}:{selectedConnection.port}
									</span>
								</div>
								<div>
									Database:{" "}
									<span className="font-medium text-gray-900">
										{selectedConnection.database_name}
									</span>
								</div>
							</div>
						</div>
					)}

					{connectionId && (
						<div>
							<div className="mb-3 flex items-center justify-between">
								<div className="flex items-center gap-2">
									<label className="text-sm font-semibold text-gray-900">
										Tables
									</label>
									<InfoTooltip text="Select one or more tables for the agent to query" />
								</div>
								<button
									type="button"
									onClick={onRefreshTables}
									disabled={loadingTables}
									className="flex items-center gap-2 rounded-[4px] border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
									title="Refresh table list"
								>
									<RefreshCw
										className={`h-3.5 w-3.5 ${loadingTables ? "animate-spin" : ""}`}
									/>
									Refresh
								</button>
							</div>

							{loadingTables ? (
								<div className="rounded-[4px] border border-gray-200 bg-white p-6 text-center">
									<p className="text-sm text-gray-600">
										Loading tables...
									</p>
								</div>
							) : tables.length === 0 ? (
								<div className="rounded-[4px] border border-gray-200 bg-white p-6 text-center">
									<p className="text-sm text-gray-600">
										No tables found in selected database
									</p>
								</div>
							) : (
								<div className="space-y-4">
									<div className="custom-scrollbar max-h-80 overflow-y-auto rounded-[4px] border border-gray-200 bg-slate-50 p-4">
										<div className="grid grid-cols-1 gap-2.5">
											{tables.map((table) => {
												const isSelected = tableNames.includes(table.name);
												const typeLabel = (table.type || "Table").toUpperCase();
												return (
													<Checkbox
														key={table.name}
														checked={isSelected}
														onChange={(checked) =>
															handleCheckboxChange(checked, table.name)
														}
														variant="green"
														size="lg"
														className={`!items-center w-full rounded-[4px] border p-3.5 transition-colors duration-200 ${
															isSelected
																? "border-orange-500 bg-white shadow-sm"
																: "border-transparent bg-white hover:border-orange-400 hover:bg-slate-50"
														}`}
														label={
															<div className="flex w-full items-center gap-3">
																<div
																	className={`rounded-[4px] border p-2 ${isSelected ? "border-orange-400 bg-white text-orange-800" : "border-gray-200 bg-slate-100 text-gray-600"}`}
																>
																	<Table className="h-4 w-4" />
																</div>
																<div className="min-w-0 flex-1">
																	<div className="truncate text-sm font-semibold text-gray-900">
																		{table.name}
																	</div>
																	{table.schema && (
																		<div className="mt-0.5 truncate text-xs text-gray-600">
																			Schema: {table.schema}
																		</div>
																	)}
																</div>
																<span className="flex-shrink-0 text-xs font-semibold tracking-wide text-gray-600">
																	{typeLabel}
																</span>
															</div>
														}
													/>
												);
											})}
										</div>
									</div>

									{tableNames.length > 0 && (
										<div className="rounded-[4px] border border-orange-400 bg-white p-4 shadow-sm">
											<div className="mb-1 flex items-center gap-2">
												<Table className="h-4 w-4 text-orange-600" />
												<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
													{tableNames.length} Table
													{tableNames.length !== 1 ? "s" : ""} Selected
												</span>
											</div>
											<p className="mt-1 text-sm text-gray-800">
												{tableNames.join(", ")}
											</p>
										</div>
									)}
								</div>
							)}
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
