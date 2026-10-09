"use client";

import { ChevronDown, ChevronUp, Filter, Search } from "lucide-react";
import React, { useCallback, useMemo, useState } from "react";

interface JsonTreeTableViewProps {
	data: any[];
}

export default function JsonTreeTableView({ data }: JsonTreeTableViewProps) {
	const [sortColumn, setSortColumn] = useState<string | null>(null);
	const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
	const [searchTerm, setSearchTerm] = useState("");
	const [visibleColumns, setVisibleColumns] = useState<Set<string> | null>(
		null,
	);

	const { columns, rows } = useMemo(() => {
		if (!Array.isArray(data) || data.length === 0)
			return { columns: [], rows: [] };

		// Determine all unique keys across all rows
		const keySet = new Set<string>();
		const keyCounts = new Map<string, number>();

		data.forEach((row) => {
			if (row && typeof row === "object" && !Array.isArray(row)) {
				Object.keys(row).forEach((key) => {
					keySet.add(key);
					keyCounts.set(key, (keyCounts.get(key) || 0) + 1);
				});
			}
		});

		// Sort columns by frequency and name
		const sortedColumns = Array.from(keySet).sort((a, b) => {
			const countDiff = (keyCounts.get(b) || 0) - (keyCounts.get(a) || 0);
			if (countDiff !== 0) return countDiff;
			return a.localeCompare(b);
		});

		// Limit to most relevant columns if there are too many
		const finalColumns = sortedColumns.slice(0, 15);

		return { columns: finalColumns, rows: data };
	}, [data]);

	// Initialize visible columns on first render
	React.useEffect(() => {
		if (visibleColumns === null && columns.length > 0) {
			// Show first 7 columns by default
			setVisibleColumns(new Set(columns.slice(0, 7)));
		}
	}, [columns, visibleColumns]);

	const filteredRows = useMemo(() => {
		let filtered = rows;

		// Apply search filter
		if (searchTerm) {
			filtered = filtered.filter((row) => {
				if (!row) return false;
				return Object.values(row).some((value) =>
					String(value).toLowerCase().includes(searchTerm.trim().toLowerCase()),
				);
			});
		}

		// Apply sorting
		if (sortColumn) {
			filtered = [...filtered].sort((a, b) => {
				const aVal = a?.[sortColumn];
				const bVal = b?.[sortColumn];

				if (aVal === null || aVal === undefined) return 1;
				if (bVal === null || bVal === undefined) return -1;

				let comparison = 0;
				if (typeof aVal === "number" && typeof bVal === "number") {
					comparison = aVal - bVal;
				} else {
					comparison = String(aVal).localeCompare(String(bVal));
				}

				return sortDirection === "asc" ? comparison : -comparison;
			});
		}

		return filtered;
	}, [rows, searchTerm, sortColumn, sortDirection]);

	const handleSort = (column: string) => {
		if (sortColumn === column) {
			setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
		} else {
			setSortColumn(column);
			setSortDirection("asc");
		}
	};

	const toggleColumn = (column: string) => {
		setVisibleColumns((prev) => {
			const next = new Set(prev);
			if (next.has(column)) {
				next.delete(column);
			} else {
				next.add(column);
			}
			return next;
		});
	};

	const formatValue = (value: any): React.ReactNode => {
		if (value === null)
			return (
				<span className="text-[color:var(--color-text-muted)] italic">
					null
				</span>
			);
		if (value === undefined)
			return (
				<span className="text-[color:var(--color-text-muted)] italic">
					undefined
				</span>
			);
		if (typeof value === "boolean")
			return <span className="text-[#B00020]">{String(value)}</span>;
		if (typeof value === "number")
			return <span className="text-[color:var(--color-accent)]">{value}</span>;
		if (typeof value === "object") {
			if (Array.isArray(value)) {
				return <span className="text-[#B00020]">[{value.length}]</span>;
			}
			return (
				<span className="text-[color:var(--color-text-muted)]">{`{${Object.keys(value).length}}`}</span>
			);
		}

		const strValue = String(value);
		if (strValue.length > 50) {
			return (
				<span className="text-[#0DA931]" title={strValue}>
					{strValue.substring(0, 50)}...
				</span>
			);
		}
		return <span className="text-[#0DA931]">{strValue}</span>;
	};

	// Event handlers to replace arrow functions in JSX
	const handleSearchChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setSearchTerm(e.target.value);
		},
		[],
	);

	const createToggleColumnHandler = useCallback(
		(col: string) => () => {
			toggleColumn(col);
		},
		[],
	);

	const createSortHandler = useCallback(
		(col: string) => () => {
			handleSort(col);
		},
		[],
	);

	if (columns.length === 0) {
		return (
			<div className="bg-[color:var(--color-bg-secondary)]/50 rounded-lg border border-[color:var(--color-surface)] p-8 text-center">
				<p className="text-[color:var(--color-text-muted)] text-sm">
					No data to display in table format
				</p>
			</div>
		);
	}

	const displayColumns = columns.filter(
		(col) => visibleColumns?.has(col) ?? false,
	);

	return (
		<div className="bg-[color:var(--color-bg-secondary)]/50 rounded-lg border border-[color:var(--color-surface)]">
			{/* Controls */}
			<div className="p-3 border-b border-[color:var(--color-surface)]">
				<div className="flex items-center gap-3">
					{/* Search */}
					<div className="flex-1 relative">
						<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
						<input
							type="text"
							placeholder="Search table..."
							aria-label="Search table data"
							value={searchTerm}
							onChange={handleSearchChange}
							className="w-full pl-9 pr-3 py-1.5 bg-[color:var(--color-surface)]/50 border border-[color:var(--color-border)] rounded text-sm text-[color:var(--color-text-secondary)] placeholder-gray-500 focus:outline-none focus:border-[color:var(--color-border)]/50"
						/>
					</div>

					{/* Column Filter */}
					<div className="relative group">
						<button className="flex items-center gap-1.5 px-3 py-1.5 bg-[color:var(--color-surface)]/50 border border-[color:var(--color-border)] rounded text-sm text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-surface-hover)]">
							<Filter className="w-3 h-3" />
							Columns ({displayColumns.length}/{columns.length})
						</button>

						<div className="absolute right-0 top-full mt-1 w-64 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
							<div className="p-2 max-h-64 overflow-auto">
								{columns.map((col) => (
									<label
										key={col}
										className="flex items-center gap-2 px-2 py-1 hover:bg-[color:var(--color-surface)]/50 rounded cursor-pointer"
									>
										<input
											type="checkbox"
											checked={visibleColumns?.has(col) ?? false}
											onChange={createToggleColumnHandler(col)}
											className="w-3 h-3 rounded border-[color:var(--color-surface-hover)] text-[color:var(--color-accent)] focus:ring-0 focus:ring-offset-0"
										/>
										<span className="text-xs text-[color:var(--color-text-secondary)] truncate">
											{col}
										</span>
									</label>
								))}
							</div>
						</div>
					</div>
				</div>

				{/* Stats */}
				<div className="flex items-center gap-3 mt-2 text-xs text-[color:var(--color-text-muted)]">
					<span>
						Showing {filteredRows.length} of {rows.length} rows
					</span>
					{searchTerm && (
						<span className="text-[color:var(--color-accent)]">Filtered</span>
					)}
					{sortColumn && (
						<span className="text-[color:var(--color-accent)]">
							Sorted by {sortColumn}
						</span>
					)}
				</div>
			</div>

			{/* Table */}
			<div className="overflow-auto max-h-[400px]">
				<table className="w-full text-sm">
					<thead className="bg-[color:var(--color-surface)]/50 sticky top-0 z-10">
						<tr>
							<th className="px-3 py-2 text-left text-xs font-medium text-[color:var(--color-text-muted)] capitalize tracking-wider whitespace-nowrap">
								#
							</th>
							{displayColumns.map((col) => (
								<th
									key={col}
									className="px-3 py-2 text-left text-xs font-medium text-[color:var(--color-text-muted)] capitalize tracking-wider whitespace-nowrap cursor-pointer hover:text-[color:var(--color-text-secondary)] group"
									onClick={createSortHandler(col)}
								>
									<div className="flex items-center gap-1">
										<span className="truncate max-w-[150px]" title={col}>
											{col}
										</span>
										{sortColumn === col &&
											(sortDirection === "asc" ? (
												<ChevronUp className="w-3 h-3 text-[color:var(--color-accent)]" />
											) : (
												<ChevronDown className="w-3 h-3 text-[color:var(--color-accent)]" />
											))}
										{sortColumn !== col && (
											<ChevronUp className="w-3 h-3 text-[color:var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity" />
										)}
									</div>
								</th>
							))}
						</tr>
					</thead>
					<tbody className="divide-y divide-gray-800">
						{filteredRows.slice(0, 100).map((row, idx) => (
							<tr
								key={`json-row-${JSON.stringify(row).substring(0, 50)}-${idx}`}
								className="hover:bg-[color:var(--color-surface)]/30 transition-colors"
							>
								<td className="px-3 py-2 text-[color:var(--color-text-muted)] text-xs">
									{idx + 1}
								</td>
								{displayColumns.map((col) => (
									<td key={col} className="px-3 py-2 align-top">
										<div className="max-w-xs font-mono text-xs">
											{formatValue(row?.[col])}
										</div>
									</td>
								))}
							</tr>
						))}
					</tbody>
				</table>
			</div>

			{filteredRows.length > 100 && (
				<div className="p-2 text-center text-xs text-[color:var(--color-text-muted)] border-t border-[color:var(--color-surface)]">
					Showing first 100 rows. Use search to find specific data.
				</div>
			)}
		</div>
	);
}
