"use client";

import { AlertCircle, Clock, Database } from "lucide-react";
import type React from "react";
import { useMemo } from "react";

interface DatabaseQueryResult {
	rowCount?: number;
	columns?: string[];
	data?: Record<string, any>[];
	error?: string;
	rawText?: string;
}

interface DatabaseQueryTraceRendererProps {
	input: any;
	output: any;
	metadata?: any;
}

/**
 * Parse formatted result string from database query tool
 * Format: "Found X rows\nColumns: col1, col2, ...\n\nData preview:\n  Row 1: col1: val1, col2: val2, ..."
 */
function parseFormattedResultString(text: string): DatabaseQueryResult | null {
	if (!text || typeof text !== "string") return null;

	// Check if this is the formatted result string
	if (
		!text.includes("Found") ||
		!text.includes("rows") ||
		!text.includes("Columns:")
	) {
		return null;
	}

	const lines = text.split("\n");
	let rowCount = 0;
	let columns: string[] = [];
	const data: Record<string, any>[] = [];

	for (let i = 0; i < lines.length; i++) {
		const line = lines[i].trim();

		// Parse row count: "Found 4 rows"
		const rowCountMatch = line.match(/^Found (\d+) rows?$/);
		if (rowCountMatch) {
			rowCount = parseInt(rowCountMatch[1]);
			continue;
		}

		// Parse columns: "Columns: column_name, data_type, is_nullable, ordinal_position"
		const columnsMatch = line.match(/^Columns:\s*(.+)$/);
		if (columnsMatch) {
			columns = columnsMatch[1].split(",").map((col) => col.trim());
			continue;
		}

		// Parse data rows: "Row 1: column_name: po_id, data_type: bigint, ..."
		const rowMatch = line.match(/^Row \d+:\s*(.+)$/);
		if (rowMatch) {
			const rowData: Record<string, any> = {};
			const pairs = rowMatch[1].split(/,\s*(?=[a-zA-Z_]+:)/); // Split on comma followed by key:

			for (const pair of pairs) {
				const colonIndex = pair.indexOf(":");
				if (colonIndex > -1) {
					const key = pair.substring(0, colonIndex).trim();
					let value: any = pair.substring(colonIndex + 1).trim();

					// Convert string values to appropriate types
					if (value === "NULL" || value === "null") {
						value = null;
					} else if (value === "true" || value === "TRUE") {
						value = true;
					} else if (value === "false" || value === "FALSE") {
						value = false;
					} else if (!isNaN(Number(value)) && value !== "") {
						// Only convert to number if it's a valid number and not empty
						const num = Number(value);
						if (Number.isFinite(num)) {
							value = num;
						}
					}

					rowData[key] = value;
				}
			}

			if (Object.keys(rowData).length > 0) {
				data.push(rowData);
			}
		}
	}

	if (columns.length > 0 && data.length > 0) {
		return { rowCount, columns, data };
	}

	return null;
}

/**
 * Parse database query results from various formats
 */
function parseQueryResults(output: any): DatabaseQueryResult | null {
	if (!output) return null;

	// Check if output has a 'result' field (common format from backend)
	let resultData = output;
	if (typeof output === "object" && output.result) {
		resultData = output.result;
	}

	// If already parsed with data array, use it
	if (
		typeof resultData === "object" &&
		resultData.data &&
		Array.isArray(resultData.data)
	) {
		return resultData;
	}

	// If it has columns and data separately
	if (
		typeof resultData === "object" &&
		(resultData.columns || resultData.rowCount !== undefined)
	) {
		return resultData;
	}

	// Try to parse formatted result string
	if (typeof resultData === "string") {
		const formatted = parseFormattedResultString(resultData);
		if (formatted) return formatted;

		// Try to parse as JSON
		try {
			const parsed = JSON.parse(resultData);
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
			// If it's raw text that couldn't be parsed, return it as rawText
			return { rawText: resultData };
		}
	}

	return resultData;
}

/**
 * Format SQL query for better readability
 */
function formatSQL(query: string): string {
	if (!query) return "";
	return query
		.replace(
			/\b(SELECT|FROM|WHERE|JOIN|LEFT JOIN|RIGHT JOIN|INNER JOIN|GROUP BY|ORDER BY|HAVING|LIMIT|OFFSET|INSERT INTO|UPDATE|DELETE|CREATE|ALTER|DROP)\b/gi,
			(match) => "\n" + match.toUpperCase(),
		)
		.replace(/,\s*/g, ",\n  ")
		.trim();
}

/**
 * Render a cell value with appropriate formatting
 */
function renderCellValue(value: any): React.ReactNode {
	if (value === null) {
		return (
			<span className="text-[color:var(--color-text-muted)] italic">NULL</span>
		);
	}
	if (value === undefined) {
		return <span className="text-[color:var(--color-text-muted)]">-</span>;
	}
	if (typeof value === "boolean") {
		return (
			<span
				className={`px-2 py-0.5 rounded-md text-xs font-medium ${
					value
						? "bg-[color:var(--color-success)]/15 text-[color:var(--color-success)] border border-[color:var(--color-success)]/30"
						: "bg-[color:var(--color-error)]/15 text-[color:var(--color-error)] border border-[color:var(--color-error)]/30"
				}`}
			>
				{value ? "TRUE" : "FALSE"}
			</span>
		);
	}
	if (typeof value === "number") {
		return (
			<span className="font-mono text-slate-900">{value.toLocaleString()}</span>
		);
	}
	if (typeof value === "object") {
		return (
			<span className="font-mono text-xs bg-[color:var(--color-surface)] border border-[color:var(--color-border)]/40 px-2 py-1 rounded-lg text-[color:var(--color-text-secondary)]">
				{JSON.stringify(value, null, 2)}
			</span>
		);
	}

	const strValue = String(value);
	// Truncate long strings
	if (strValue.length > 100) {
		return (
			<span
				title={strValue}
				className="text-[color:var(--color-text-secondary)]"
			>
				{strValue.substring(0, 100)}...
			</span>
		);
	}
	return (
		<span className="text-[color:var(--color-text-secondary)]">{strValue}</span>
	);
}

export default function DatabaseQueryTraceRenderer({
	input,
	output,
	metadata,
}: DatabaseQueryTraceRendererProps) {
	// Extract query from input
	const query = useMemo(() => {
		if (!input) return "";
		if (typeof input === "string") return input;
		if (input.query) return input.query;
		// Sometimes the query is in a nested structure
		if (input.item && input.item.query) return input.item.query;
		return "";
	}, [input]);

	// Extract and parse results from output
	const parsedResults = useMemo((): DatabaseQueryResult | null => {
		return parseQueryResults(output);
	}, [output]);

	// Extract metadata if available
	const duration = metadata?.duration || metadata?.elapsed;
	const timestamp = metadata?.timestamp;

	if (!query && !parsedResults) {
		return (
			<div className="text-[color:var(--color-text-muted)] text-sm">
				No database query data available
			</div>
		);
	}

	return (
		<div className="space-y-4">
			{/* Query Section */}
			{query && (
				<div className="bg-[rgba(var(--color-accent-rgb),0.08)] border border-[rgba(var(--color-accent-rgb),0.3)] rounded-xl overflow-hidden">
					<div className="px-4 py-3 bg-[rgba(var(--color-accent-rgb),0.15)] border-b border-[rgba(var(--color-accent-rgb),0.3)]">
						<div className="flex items-center gap-2.5">
							<div className="w-6 h-6 rounded-lg border border-[rgba(var(--color-accent-rgb),0.3)] bg-[rgba(var(--color-accent-rgb),0.08)] flex items-center justify-center">
								<Database className="w-3 h-3 text-[color:var(--color-accent)]" />
							</div>
							<span className="text-xs capitalize font-semibold text-[color:var(--color-accent)]">
								SQL Query
							</span>
						</div>
					</div>
					<div className="p-4">
						<pre className="bg-[rgba(0,0,0,0.2)] rounded-xl p-4 overflow-x-auto border border-[color:var(--color-border)]/30">
							<code className="text-sm text-[color:var(--color-accent)] font-mono leading-relaxed">
								{formatSQL(query)}
							</code>
						</pre>

						{/* Execution metadata */}
						{(duration || timestamp) && (
							<div className="flex items-center gap-6 mt-3 pt-3 border-t border-[rgba(var(--color-accent-rgb),0.2)] text-xs">
								{duration && (
									<div className="flex items-center gap-2">
										<Clock className="w-3 h-3 text-[color:var(--color-text-muted)]" />
										<span className="text-[color:var(--color-text-muted)]">
											Duration:
										</span>
										<span className="text-[color:var(--color-accent)] font-mono">
											{typeof duration === "number"
												? `${duration.toFixed(2)}ms`
												: duration}
										</span>
									</div>
								)}
								{timestamp && (
									<div className="flex items-center gap-2">
										<Clock className="w-3 h-3 text-[color:var(--color-text-muted)]" />
										<span className="text-[color:var(--color-text-muted)]">
											Executed:
										</span>
										<span className="text-[color:var(--color-text-secondary)] text-xs font-mono">
											{new Date(timestamp).toLocaleString()}
										</span>
									</div>
								)}
							</div>
						)}
					</div>
				</div>
			)}

			{/* Results Section */}
			{parsedResults && (
				<div className="space-y-3">
					{parsedResults.error ? (
						// Error Display
						<div className="bg-[color:var(--color-error)]/10 border border-[color:var(--color-error)]/30 rounded-xl p-4">
							<div className="flex items-start gap-3">
								<div className="w-8 h-8 rounded-lg border border-[color:var(--color-error)]/30 bg-[color:var(--color-error)]/10 flex items-center justify-center flex-shrink-0">
									<AlertCircle className="w-4 h-4 text-[color:var(--color-error)]" />
								</div>
								<div className="flex-1 min-w-0">
									<div className="text-xs capitalize font-semibold text-[color:var(--color-error)] mb-2">
										Query Error
									</div>
									<pre className="text-sm text-[color:var(--color-error)] whitespace-pre-wrap opacity-80">
										{parsedResults.error}
									</pre>
								</div>
							</div>
						</div>
					) : parsedResults.data &&
						Array.isArray(parsedResults.data) &&
						parsedResults.data.length > 0 ? (
						// Table Display
						<>
							{/* Results Header */}
							<div className="flex items-center justify-between px-4 py-3 bg-[color:var(--color-surface)]/40 border border-[color:var(--color-border)]/50 rounded-xl">
								<div className="flex items-center gap-2.5">
									<div className="w-6 h-6 rounded-lg border border-[color:var(--color-success)]/30 bg-[color:var(--color-success)]/10 flex items-center justify-center">
										<Database className="w-3 h-3 text-[color:var(--color-success)]" />
									</div>
									<span className="text-sm font-medium text-slate-900">
										{parsedResults.rowCount || parsedResults.data.length} row
										{(parsedResults.rowCount || parsedResults.data.length) !== 1
											? "s"
											: ""}{" "}
										returned
									</span>
								</div>
								{parsedResults.columns && (
									<span className="text-[0.65rem] capitalize text-[color:var(--color-text-muted)]">
										{parsedResults.columns.length} column
										{parsedResults.columns.length !== 1 ? "s" : ""}
									</span>
								)}
							</div>

							{/* Results Table */}
							<div className="bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)]/50 rounded-xl overflow-hidden">
								<div className="overflow-x-auto max-h-96 overflow-y-auto">
									<table className="w-full">
										<thead className="bg-[color:var(--color-surface)]/70 sticky top-0 z-10 backdrop-blur-sm">
											<tr className="border-b border-[color:var(--color-border)]/50">
												{(
													parsedResults.columns ||
													Object.keys(parsedResults.data[0])
												).map((col: string) => (
													<th
														key={col}
														className="text-left px-4 py-3 text-[0.65rem] font-semibold text-[color:var(--color-text-secondary)] capitalize"
													>
														{col}
													</th>
												))}
											</tr>
										</thead>
										<tbody className="divide-y divide-[color:var(--color-border)]/30">
											{parsedResults.data
												.slice(0, 50)
												.map((row: any, idx: number) => (
													<tr
														key={`row-${idx}`}
														className="hover:bg-[color:var(--color-surface-hover)]/50 transition-colors duration-150"
													>
														{(parsedResults.columns || Object.keys(row)).map(
															(col: string) => (
																<td
																	key={`${col}-${idx}`}
																	className="px-4 py-3 text-sm"
																>
																	{renderCellValue(row[col])}
																</td>
															),
														)}
													</tr>
												))}
										</tbody>
									</table>
								</div>

								{parsedResults.data.length > 50 && (
									<div className="px-4 py-3 bg-[color:var(--color-surface)]/50 border-t border-[color:var(--color-border)]/30 text-center">
										<p className="text-xs text-[color:var(--color-text-muted)]">
											Showing first 50 of {parsedResults.data.length} rows
										</p>
									</div>
								)}
							</div>
						</>
					) : parsedResults.data &&
						Array.isArray(parsedResults.data) &&
						parsedResults.data.length === 0 ? (
						// No Results
						<div className="bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)]/50 rounded-xl p-6 text-center">
							<Database className="w-10 h-10 text-[color:var(--color-text-muted)] mx-auto mb-2" />
							<p className="text-[color:var(--color-text-muted)] text-sm">
								Query executed successfully - no rows returned
							</p>
						</div>
					) : parsedResults.rawText ? (
						// Raw Text Display
						<div className="bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)]/50 rounded-xl p-4">
							<div className="text-[0.65rem] capitalize font-semibold text-[color:var(--color-text-muted)] mb-3">
								Raw Results
							</div>
							<pre className="text-sm text-[color:var(--color-text-secondary)] whitespace-pre-wrap overflow-x-auto">
								{parsedResults.rawText}
							</pre>
						</div>
					) : (
						// Fallback JSON Display
						<div className="bg-[color:var(--color-surface)]/30 border border-[color:var(--color-border)]/50 rounded-xl p-4">
							<div className="text-[0.65rem] capitalize font-semibold text-[color:var(--color-text-muted)] mb-3">
								Results
							</div>
							<pre className="text-sm text-[color:var(--color-text-secondary)] whitespace-pre-wrap overflow-x-auto">
								{JSON.stringify(parsedResults, null, 2)}
							</pre>
						</div>
					)}
				</div>
			)}

			{/* No Results Message */}
			{!parsedResults && query && (
				<div className="text-[color:var(--color-text-muted)] text-sm">
					Query executed - no results available
				</div>
			)}
		</div>
	);
}
