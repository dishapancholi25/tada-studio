"use client";

import { Columns, RefreshCw } from "lucide-react";
import Checkbox from "@/components/ui/Checkbox";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";

interface TableColumn {
	column_name: string;
	column_type: string;
	is_nullable?: boolean;
	is_primary_key?: boolean;
}

interface ColumnSelectionSectionProps {
	tableNames: string[];
	selectedColumns: string[];
	onSelectedColumnsChange: (columns: string[]) => void;
	columns: TableColumn[];
	loadingColumns: boolean;
	onRefreshColumns: () => void;
}

/**
 * Lets the user pick specific columns to include in the query output.
 * When no table (or more than one table) is selected, column selection is
 * disabled — selecting specific columns only makes sense for a single table.
 * Leaving all columns unchecked means "select all columns" (SELECT *).
 */
export default function ColumnSelectionSection({
	tableNames,
	selectedColumns,
	onSelectedColumnsChange,
	columns,
	loadingColumns,
	onRefreshColumns,
}: ColumnSelectionSectionProps) {
	const singleTable = tableNames.length === 1 ? tableNames[0] : null;

	const handleToggle = (checked: boolean, columnName: string) => {
		if (checked) {
			onSelectedColumnsChange([...selectedColumns, columnName]);
		} else {
			onSelectedColumnsChange(selectedColumns.filter((c) => c !== columnName));
		}
	};

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex min-w-0 items-start gap-3">
						<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
							<Columns className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div className="min-w-0">
							<div className="flex items-center gap-2">
								<h3 className="text-lg font-semibold text-gray-900">
									Column Selection
								</h3>
								<InfoTooltip text="Choose which columns to return. Leave all unchecked to return every column. Selected values are returned as an iterable JSON array for use by downstream nodes (e.g. For Each)." />
							</div>
							<p className="text-sm text-gray-600">
								Restrict the query output to specific columns
							</p>
						</div>
					</div>
					{singleTable && (
						<button
							type="button"
							onClick={onRefreshColumns}
							disabled={loadingColumns}
							className="flex items-center gap-2 rounded-[4px] border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
							title="Refresh column list"
						>
							<RefreshCw
								className={`h-3.5 w-3.5 ${loadingColumns ? "animate-spin" : ""}`}
							/>
							Refresh
						</button>
					)}
				</div>

				<div className="mt-6">
					{!singleTable ? (
						<div className="rounded-[4px] border border-gray-200 bg-white p-6 text-center">
							<p className="text-sm text-gray-600">
								{tableNames.length === 0
									? "Select a single table in the Connection tab to choose specific columns."
									: "Column selection is only available when exactly one table is selected."}
							</p>
						</div>
					) : loadingColumns ? (
						<div className="rounded-[4px] border border-gray-200 bg-white p-6 text-center">
							<p className="text-sm text-gray-600">Loading columns...</p>
						</div>
					) : columns.length === 0 ? (
						<div className="rounded-[4px] border border-gray-200 bg-white p-6 text-center">
							<p className="text-sm text-gray-600">
								No columns found for table &quot;{singleTable}&quot;
							</p>
						</div>
					) : (
						<div className="space-y-4">
							<div className="custom-scrollbar max-h-80 overflow-y-auto rounded-[4px] border border-gray-200 bg-slate-50 p-4">
								<div className="grid grid-cols-1 gap-2.5">
									{columns.map((col) => {
										const isSelected = selectedColumns.includes(
											col.column_name,
										);
										return (
											<Checkbox
												key={col.column_name}
												checked={isSelected}
												onChange={(checked) =>
													handleToggle(checked, col.column_name)
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
														<div className="min-w-0 flex-1">
															<div className="truncate text-sm font-semibold text-gray-900">
																{col.column_name}
																{col.is_primary_key && (
																	<span className="ml-2 rounded-full border border-orange-300 bg-orange-50 px-2 py-0.5 text-[10px] font-semibold text-orange-700">
																		PK
																	</span>
																)}
															</div>
															<div className="mt-0.5 truncate text-xs text-gray-600">
																{col.column_type}
																{col.is_nullable === false && " · NOT NULL"}
															</div>
														</div>
													</div>
												}
											/>
										);
									})}
								</div>
							</div>

							<div className="rounded-[4px] border border-orange-400 bg-white p-4 shadow-sm">
								<div className="mb-1 flex items-center gap-2">
									<Columns className="h-4 w-4 text-orange-600" />
									<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
										{selectedColumns.length === 0
											? "All Columns (SELECT *)"
											: `${selectedColumns.length} Column${selectedColumns.length !== 1 ? "s" : ""} Selected`}
									</span>
								</div>
								{selectedColumns.length > 0 && (
									<p className="mt-1 text-sm text-gray-800">
										{selectedColumns.join(", ")}
									</p>
								)}
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
