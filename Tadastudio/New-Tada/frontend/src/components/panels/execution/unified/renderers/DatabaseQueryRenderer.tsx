import {
	AlertCircle,
	ArrowUpDown,
	Check,
	CheckCircle,
	ChevronDown,
	ChevronUp,
	Clock,
	Code,
	Copy,
	Database,
	Maximize2,
	Table,
} from "lucide-react";
import React, { useMemo, useState } from "react";
import TablePreviewModal from "../../../../dialogs/TablePreviewModal";
import JsonViewerEnhanced from "../../../../JsonViewerEnhanced";
import TextModal from "../../../../ui/TextModal";
import type { DatabaseQueryExecution } from "../types/execution.types";
import { BaseRenderer, BaseRendererProps } from "./BaseRenderer";

type SortDirection = "asc" | "desc" | null;

export class DatabaseQueryRenderer extends BaseRenderer<DatabaseQueryExecution> {
	state = {
		queryModal: { open: false, text: "" },
		tableModal: {
			open: false,
			data: null as any[] | null,
			columns: null as string[] | null,
			rowCount: 0,
		},
		copiedQuery: false,
		sortColumn: null as string | null,
		sortDirection: null as SortDirection,
		showQuery: true,
	};

	getViewModes() {
		return [
			{
				key: "unified",
				label: "Query & Results",
				icon: <Database className="w-4 h-4" />,
			},
			{
				key: "results",
				label: "Results Only",
				icon: <Table className="w-4 h-4" />,
			},
			{ key: "query", label: "Query Only", icon: <Code className="w-4 h-4" /> },
			{ key: "raw", label: "Raw Data" },
		];
	}

	renderViewMode(mode: string, execution: DatabaseQueryExecution) {
		switch (mode) {
			case "unified":
				return this.renderUnifiedView(execution);
			case "results":
				return this.renderResults(execution);
			case "query":
				return this.renderQuery(execution);
			default:
				// Return raw JSON view
				return (
					<div className="bg-[color:var(--color-surface)] rounded-lg p-4">
						<JsonViewerEnhanced data={execution} />
					</div>
				);
		}
	}

	parseResults(results: any) {
		if (!results) return null;

		// If already parsed with data array, use it
		if (
			typeof results === "object" &&
			results.data &&
			Array.isArray(results.data)
		) {
			return results;
		}

		// If it has columns and data separately
		if (
			typeof results === "object" &&
			(results.columns || results.rowCount !== undefined)
		) {
			return results;
		}

		// Try to parse from string
		if (typeof results === "string") {
			try {
				const parsed = JSON.parse(results);
				if (Array.isArray(parsed)) {
					const columns = parsed.length > 0 ? Object.keys(parsed[0]) : [];
					return { rowCount: parsed.length, columns, data: parsed };
				}
				// If parsed object has data array, use it
				if (parsed.data && Array.isArray(parsed.data)) {
					return parsed;
				}
				return parsed;
			} catch {
				// If it's raw text, still try to extract structured data if available
				return { rawText: results };
			}
		}

		return results;
	}

	handleSort = (column: string) => {
		if (this.state.sortColumn === column) {
			// Cycle through: asc -> desc -> null
			const nextDirection =
				this.state.sortDirection === "asc"
					? "desc"
					: this.state.sortDirection === "desc"
						? null
						: "asc";
			this.setState({
				sortDirection: nextDirection,
				sortColumn: nextDirection ? column : null,
			});
		} else {
			this.setState({ sortColumn: column, sortDirection: "asc" });
		}
	};

	sortData(data: any[]) {
		if (!this.state.sortColumn || !this.state.sortDirection) {
			return data;
		}

		return [...data].sort((a, b) => {
			const aVal = a[this.state.sortColumn!];
			const bVal = b[this.state.sortColumn!];

			// Handle null/undefined values
			if (aVal === null || aVal === undefined) return 1;
			if (bVal === null || bVal === undefined) return -1;

			// Compare values
			let comparison = 0;
			if (typeof aVal === "number" && typeof bVal === "number") {
				comparison = aVal - bVal;
			} else {
				comparison = String(aVal).localeCompare(String(bVal));
			}

			return this.state.sortDirection === "asc" ? comparison : -comparison;
		});
	}

	renderUnifiedView(execution: DatabaseQueryExecution) {
		const parsed =
			execution.parsed_results || this.parseResults(execution.results);
		const hasTableData = parsed && parsed.data && Array.isArray(parsed.data);

		return (
			<div className="space-y-4">
				{/* Query Section */}
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden">
					<div className="bg-gradient-to-r from-[color:var(--color-primary)]/20 to-[color:var(--color-accent)]/20 border-b border-[color:var(--color-border)]/30 px-6 py-4">
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-3">
								<div className="p-2 rounded-lg bg-[color:var(--color-accent)]/10">
									<Code className="w-5 h-5 text-[color:var(--color-accent)]" />
								</div>
								<h4 className="text-[color:var(--color-accent)] font-medium">
									SQL Query
								</h4>
							</div>
							<div className="flex items-center gap-2">
								<button
									onClick={() => this.handleCopyQuery(execution.query)}
									className="flex items-center gap-2 px-3 py-1.5 bg-[color:var(--color-surface)] hover:bg-[color:var(--color-border)] text-[color:var(--color-text-secondary)] rounded-lg transition-colors"
								>
									{this.state.copiedQuery ? (
										<>
											<Check className="w-4 h-4 text-[color:var(--color-accent)]" />
											<span className="text-sm">Copied!</span>
										</>
									) : (
										<>
											<Copy className="w-4 h-4" />
											<span className="text-sm">Copy</span>
										</>
									)}
								</button>
							</div>
						</div>
					</div>

					<div className="p-6">
						<pre className="bg-[color:var(--color-bg-secondary)] rounded-lg p-4 overflow-x-auto">
							<code className="text-sm text-[color:var(--color-accent)] font-mono leading-relaxed">
								{this.formatSQL(execution.query)}
							</code>
						</pre>

						{/* Execution metadata */}
						{(execution.duration || execution.timestamp) && (
							<div className="flex items-center gap-6 mt-4 pt-4 border-t border-[color:var(--color-border)] text-sm">
								{execution.duration && (
									<div className="flex items-center gap-2">
										<Clock className="w-4 h-4 text-[color:var(--color-text-muted)]" />
										<span className="text-[color:var(--color-text-muted)]">
											Duration:
										</span>
										<span className="text-[color:var(--color-accent)] font-mono">
											{typeof execution.duration === "number"
												? `${execution.duration.toFixed(2)}ms`
												: execution.duration}
										</span>
									</div>
								)}
								{execution.timestamp && (
									<div className="flex items-center gap-2">
										<Clock className="w-4 h-4 text-[color:var(--color-text-muted)]" />
										<span className="text-[color:var(--color-text-muted)]">
											Executed:
										</span>
										<span className="text-[color:var(--color-text-secondary)]">
											{new Date(execution.timestamp).toLocaleString()}
										</span>
									</div>
								)}
							</div>
						)}
					</div>
				</div>

				{/* Results Section */}
				<div className="space-y-4">
					<h3 className="text-sm font-medium text-[color:var(--color-text-muted)] capitalize tracking-wider flex items-center gap-2">
						<CheckCircle className="w-4 h-4 text-[color:var(--color-accent)]" />
						Query Results
					</h3>

					{parsed && parsed.error ? (
						<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-6 border border-red-500/20 bg-red-500/5">
							<div className="flex items-start gap-3">
								<div className="p-2 rounded-lg bg-red-500/10">
									<AlertCircle className="w-5 h-5 text-red-400" />
								</div>
								<div className="flex-1">
									<h4 className="text-red-400 font-medium mb-2">Query Error</h4>
									<pre className="text-red-300 text-sm whitespace-pre-wrap">
										{parsed.error}
									</pre>
								</div>
							</div>
						</div>
					) : hasTableData ? (
						this.renderEnhancedTable(parsed)
					) : parsed && parsed.rawText && !hasTableData ? (
						// Only show raw text if we don't have structured data
						<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
							<div className="flex items-center justify-between mb-3">
								<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)]">
									Raw Results
								</h4>
							</div>
							<pre className="bg-[color:var(--color-bg-secondary)] rounded-lg p-4 text-[color:var(--color-text-secondary)] whitespace-pre-wrap text-sm overflow-x-auto">
								{parsed.rawText}
							</pre>
						</div>
					) : (
						<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
							<JsonViewerEnhanced data={parsed || execution.results} />
						</div>
					)}
				</div>
			</div>
		);
	}

	renderResults(execution: DatabaseQueryExecution) {
		const parsed =
			execution.parsed_results || this.parseResults(execution.results);

		if (!parsed) {
			return (
				<div className="flex-1 flex items-center justify-center">
					<div className="text-center">
						<Database className="w-12 h-12 text-[color:var(--color-text-muted)] mx-auto mb-3" />
						<p className="text-[color:var(--color-text-muted)]">
							No results available
						</p>
					</div>
				</div>
			);
		}

		if (parsed.error) {
			return (
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-6 border border-red-500/20 bg-red-500/5">
					<div className="flex items-start gap-3">
						<div className="p-2 rounded-lg bg-red-500/10">
							<Database className="w-5 h-5 text-red-400" />
						</div>
						<div className="flex-1">
							<h4 className="text-red-400 font-medium mb-2">Query Error</h4>
							<pre className="text-red-300 text-sm whitespace-pre-wrap">
								{parsed.error}
							</pre>
						</div>
					</div>
				</div>
			);
		}

		// Prioritize structured data over raw text
		if (parsed.data && Array.isArray(parsed.data)) {
			return this.renderEnhancedTable(parsed);
		}

		// Only show raw text if we don't have structured data
		if (parsed.rawText) {
			return (
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
					<div className="flex items-center justify-between mb-3">
						<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)]">
							Raw Results
						</h4>
					</div>
					<pre className="bg-[color:var(--color-bg-secondary)] rounded-lg p-4 text-[color:var(--color-text-secondary)] whitespace-pre-wrap text-sm overflow-x-auto">
						{parsed.rawText}
					</pre>
				</div>
			);
		}

		return (
			<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
				<JsonViewerEnhanced data={parsed} />
			</div>
		);
	}

	renderEnhancedTable(parsed: any) {
		const { data, columns, rowCount } = parsed;

		// Ensure we have data to display
		if (!data || !Array.isArray(data) || data.length === 0) {
			return (
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-6 text-center">
					<Database className="w-12 h-12 text-[color:var(--color-text-muted)] mx-auto mb-3" />
					<p className="text-[color:var(--color-text-muted)]">
						No rows returned
					</p>
				</div>
			);
		}

		const displayColumns = columns || Object.keys(data[0]);
		const sortedData = this.sortData(data);
		const displayRows = sortedData.slice(0, 10);
		const hasMore = data.length > 10;

		return (
			<div className="space-y-4">
				{/* Header with stats */}
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4 bg-gradient-to-r from-[color:var(--color-primary)]/20 to-[color:var(--color-accent)]/20 border border-[color:var(--color-border)]/30">
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-4">
							<div className="p-2 rounded-lg bg-[color:var(--color-accent)]/10">
								<Database className="w-5 h-5 text-[color:var(--color-accent)]" />
							</div>
							<div>
								<div className="text-[color:var(--color-accent)] font-medium">
									{rowCount || data.length} row
									{(rowCount || data.length) !== 1 ? "s" : ""} returned
								</div>
								<div className="text-sm text-[color:var(--color-text-muted)]">
									{displayColumns.length} column
									{displayColumns.length !== 1 ? "s" : ""}
								</div>
							</div>
						</div>
						{hasMore && (
							<button
								onClick={() =>
									this.setState({
										tableModal: {
											open: true,
											data,
											columns: displayColumns,
											rowCount: rowCount || data.length,
										},
									})
								}
								className="flex items-center gap-2 px-4 py-2 bg-[color:var(--color-accent)]/10 hover:bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] rounded-lg transition-all hover:scale-105"
							>
								<Maximize2 className="w-4 h-4" />
								View All Rows
							</button>
						)}
					</div>
				</div>

				{/* Enhanced Table */}
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden">
					<div className="overflow-x-auto">
						<table className="w-full">
							<thead className="bg-[color:var(--color-surface)]/50 sticky top-0 z-10">
								<tr className="border-b border-[color:var(--color-border)]">
									{displayColumns.map((col: string, idx: number) => (
										<th
											key={col}
											className="text-left px-6 py-3 text-sm font-medium text-[color:var(--color-text-secondary)] cursor-pointer hover:bg-[color:var(--color-surface)]/70 transition-colors group"
											onClick={() => this.handleSort(col)}
										>
											<div className="flex items-center gap-2">
												<span>{col}</span>
												<div className="opacity-0 group-hover:opacity-100 transition-opacity">
													{this.state.sortColumn === col ? (
														this.state.sortDirection === "asc" ? (
															<ChevronUp className="w-3 h-3" />
														) : (
															<ChevronDown className="w-3 h-3" />
														)
													) : (
														<ArrowUpDown className="w-3 h-3 text-[color:var(--color-text-muted)]" />
													)}
												</div>
											</div>
										</th>
									))}
								</tr>
							</thead>
							<tbody className="divide-y divide-gray-800">
								{displayRows.map((row: any, idx: number) => (
									<tr
										key={`row-${JSON.stringify(row).substring(0, 50)}-${idx}`}
										className="hover:bg-[color:var(--color-surface)]/30 transition-colors group"
									>
										{displayColumns.map((col: string, colIdx: number) => (
											<td
												key={`${col}-${colIdx}`}
												className="px-6 py-3 text-sm text-[color:var(--color-text-muted)] group-hover:text-[color:var(--color-text-secondary)] transition-colors"
											>
												{this.renderCellValue(row[col])}
											</td>
										))}
									</tr>
								))}
							</tbody>
						</table>
					</div>

					{hasMore && (
						<div className="px-6 py-4 bg-[color:var(--color-surface)]/30 border-t border-[color:var(--color-border)]">
							<p className="text-center text-sm text-[color:var(--color-text-muted)]">
								Showing first 10 of {data.length} rows
								<button
									onClick={() =>
										this.setState({
											tableModal: {
												open: true,
												data,
												columns: displayColumns,
												rowCount: rowCount || data.length,
											},
										})
									}
									className="ml-2 text-[color:var(--color-accent)] hover:text-[color:var(--color-border)] underline"
								>
									View all
								</button>
							</p>
						</div>
					)}
				</div>

				{this.state.tableModal.open && (
					<TablePreviewModal
						isOpen={this.state.tableModal.open}
						onClose={() =>
							this.setState({
								tableModal: {
									open: false,
									data: null,
									columns: null,
									rowCount: 0,
								},
							})
						}
						tableName="Query Results"
						connectionName="Database Query"
						tableData={{
							success: true,
							data: this.state.tableModal.data || [],
							columns: this.state.tableModal.columns || [],
							row_count: this.state.tableModal.rowCount,
						}}
					/>
				)}
			</div>
		);
	}

	renderCellValue(value: any) {
		if (value === null) {
			return (
				<span className="text-[color:var(--color-text-muted)] italic">
					NULL
				</span>
			);
		}
		if (value === undefined) {
			return <span className="text-[color:var(--color-text-muted)]">-</span>;
		}
		if (typeof value === "boolean") {
			return (
				<span
					className={`px-2 py-0.5 rounded text-xs font-medium ${
						value
							? "bg-[color:var(--color-accent)]/10 text-[color:var(--color-accent)]"
							: "bg-red-500/10 text-red-400"
					}`}
				>
					{value ? "TRUE" : "FALSE"}
				</span>
			);
		}
		if (typeof value === "number") {
			return <span className="font-mono">{value.toLocaleString()}</span>;
		}
		if (typeof value === "object") {
			return (
				<span className="font-mono text-xs bg-[color:var(--color-surface)] px-2 py-1 rounded">
					{JSON.stringify(value, null, 2)}
				</span>
			);
		}

		const strValue = String(value);
		// Truncate long strings
		if (strValue.length > 100) {
			return <span title={strValue}>{strValue.substring(0, 100)}...</span>;
		}
		return strValue;
	}

	handleCopyQuery = async (query: string) => {
		try {
			await navigator.clipboard.writeText(query);
			this.setState({ copiedQuery: true });
			setTimeout(() => this.setState({ copiedQuery: false }), 2000);
		} catch (err) {
			console.error("Failed to copy query:", err);
		}
	};

	renderQuery(execution: DatabaseQueryExecution) {
		const query = execution.query;

		return (
			<div className="space-y-4">
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden">
					<div className="bg-gradient-to-r from-[color:var(--color-primary)]/20 to-[color:var(--color-accent)]/20 border-b border-[color:var(--color-border)]/30 px-6 py-4">
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-3">
								<div className="p-2 rounded-lg bg-[color:var(--color-accent)]/10">
									<Code className="w-5 h-5 text-[color:var(--color-accent)]" />
								</div>
								<h4 className="text-[color:var(--color-accent)] font-medium">
									SQL Query
								</h4>
							</div>
							<div className="flex items-center gap-2">
								<button
									onClick={() => this.handleCopyQuery(query)}
									className="flex items-center gap-2 px-3 py-1.5 bg-[color:var(--color-surface)] hover:bg-[color:var(--color-border)] text-[color:var(--color-text-secondary)] rounded-lg transition-colors"
								>
									{this.state.copiedQuery ? (
										<>
											<Check className="w-4 h-4 text-[color:var(--color-accent)]" />
											<span className="text-sm">Copied!</span>
										</>
									) : (
										<>
											<Copy className="w-4 h-4" />
											<span className="text-sm">Copy</span>
										</>
									)}
								</button>
								<button
									onClick={() =>
										this.setState({ queryModal: { open: true, text: query } })
									}
									className="flex items-center gap-2 px-3 py-1.5 bg-[color:var(--color-accent)]/10 hover:bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] rounded-lg transition-colors"
								>
									<Maximize2 className="w-4 h-4" />
									<span className="text-sm">Expand</span>
								</button>
							</div>
						</div>
					</div>

					<div className="p-6">
						<pre className="bg-[color:var(--color-bg-secondary)] rounded-lg p-4 overflow-x-auto">
							<code className="text-sm text-[color:var(--color-accent)] font-mono leading-relaxed">
								{this.formatSQL(query)}
							</code>
						</pre>
					</div>
				</div>

				{/* Execution Stats if available */}
				{(execution.duration || execution.timestamp) && (
					<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4 bg-[color:var(--color-surface)]/30">
						<div className="flex items-center justify-between text-sm">
							{execution.duration && (
								<>
									<span className="text-[color:var(--color-text-muted)]">
										Execution Time:
									</span>
									<span className="text-emerald-400 font-mono">
										{typeof execution.duration === "number"
											? `${execution.duration.toFixed(2)}ms`
											: execution.duration}
									</span>
								</>
							)}
						</div>
					</div>
				)}

				{this.state.queryModal.open && (
					<TextModal
						isOpen={this.state.queryModal.open}
						onClose={() =>
							this.setState({ queryModal: { open: false, text: "" } })
						}
						text={this.state.queryModal.text}
						title="SQL Query"
					/>
				)}
			</div>
		);
	}

	formatSQL(query: string) {
		// Basic SQL formatting for better readability
		return query
			.replace(
				/\b(SELECT|FROM|WHERE|JOIN|LEFT JOIN|RIGHT JOIN|INNER JOIN|GROUP BY|ORDER BY|HAVING|LIMIT|OFFSET|INSERT INTO|UPDATE|DELETE|CREATE|ALTER|DROP)\b/gi,
				(match) => "\n" + match.toUpperCase(),
			)
			.replace(/,\s*/g, ",\n  ")
			.trim();
	}

	renderEmptyState() {
		return (
			<div className="flex-1 flex items-center justify-center">
				<div className="text-center">
					<div className="p-4 rounded-full bg-[color:var(--color-accent)]/10 inline-block mb-4">
						<Database className="w-12 h-12 text-[color:var(--color-accent)]" />
					</div>
					<p className="text-[color:var(--color-text-secondary)] font-medium text-lg">
						No Query Executions
					</p>
					<p className="text-[color:var(--color-text-muted)] text-sm mt-2">
						This database query hasn&apos;t been executed yet
					</p>
				</div>
			</div>
		);
	}
}
