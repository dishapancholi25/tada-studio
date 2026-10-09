"use client";

import {
	AlertCircle,
	Download,
	Loader,
	Maximize2,
	Minimize2,
	Table,
	X,
} from "lucide-react";
import { useEffect, useState } from "react";

interface TablePreviewData {
	success: boolean;
	data?: any[];
	columns?: string[];
	row_count?: number;
	error?: string;
}

interface TablePreviewModalProps {
	isOpen: boolean;
	onClose: () => void;
	tableName: string;
	connectionName: string;
	tableData: TablePreviewData | null;
	loading?: boolean;
}

export default function TablePreviewModal({
	isOpen,
	onClose,
	tableName,
	connectionName,
	tableData,
	loading = false,
}: TablePreviewModalProps) {
	const [isFullscreen, setIsFullscreen] = useState(false);

	// Close on escape key
	useEffect(() => {
		const handleEscape = (e: KeyboardEvent) => {
			if (e.key === "Escape" && isOpen) {
				onClose();
			}
		};
		window.addEventListener("keydown", handleEscape);
		return () => window.removeEventListener("keydown", handleEscape);
	}, [isOpen, onClose]);

	if (!isOpen) return null;

	const exportToCSV = () => {
		if (!tableData?.data || !tableData.columns) return;

		const csvContent = [
			// Header row
			tableData.columns.join(","),
			// Data rows
			...tableData.data.map((row) =>
				tableData
					.columns!.map((col) => {
						const value = row[col];
						// Escape values that contain commas or quotes
						if (value === null) return "NULL";
						const strValue = String(value);
						if (
							strValue.includes(",") ||
							strValue.includes('"') ||
							strValue.includes("\n")
						) {
							return `"${strValue.replace(/"/g, '""')}"`;
						}
						return strValue;
					})
					.join(","),
			),
		].join("\n");

		const blob = new Blob([csvContent], { type: "text/csv" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `${tableName}_preview.csv`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	};

	return (
		<div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
			<div
				className={`bg-[color:var(--color-bg-secondary)] rounded-xl shadow-2xl flex flex-col ${
					isFullscreen ? "w-full h-full m-0" : "w-full max-w-7xl max-h-[90vh]"
				} transition-all duration-300`}
			>
				{/* Header */}
				<div className="flex items-center justify-between p-6 border-b border-[color:var(--color-border)]">
					<div>
						<h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
							<Table className="w-5 h-5" />
							{tableName}
						</h2>
						<p className="text-sm text-[color:var(--color-text-muted)] mt-1">
							{connectionName}
						</p>
					</div>
					<div className="flex items-center gap-2">
						{tableData?.success && tableData.data && (
							<button
								onClick={exportToCSV}
								className="p-2 text-[color:var(--color-text-muted)] hover:text-slate-900 hover:bg-[color:var(--color-surface)] rounded-lg transition-colors"
								title="Export to CSV"
							>
								<Download className="w-5 h-5" />
							</button>
						)}
						<button
							onClick={() => setIsFullscreen(!isFullscreen)}
							className="p-2 text-[color:var(--color-text-muted)] hover:text-slate-900 hover:bg-[color:var(--color-surface)] rounded-lg transition-colors"
							title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
						>
							{isFullscreen ? (
								<Minimize2 className="w-5 h-5" />
							) : (
								<Maximize2 className="w-5 h-5" />
							)}
						</button>
						<button
							onClick={onClose}
							className="p-2 text-[color:var(--color-text-muted)] hover:text-slate-900 hover:bg-[color:var(--color-surface)] rounded-lg transition-colors"
						>
							<X className="w-5 h-5" />
						</button>
					</div>
				</div>

				{/* Content */}
				<div className="flex-1 overflow-hidden flex flex-col">
					{loading ? (
						<div className="flex-1 flex items-center justify-center">
							<div className="text-center">
								<Loader className="w-8 h-8 text-[color:var(--color-text-muted)] animate-spin mx-auto mb-2" />
								<p className="text-[color:var(--color-text-muted)]">
									Loading table data...
								</p>
							</div>
						</div>
					) : tableData?.success && tableData.data ? (
						<>
							{/* Stats Bar */}
							<div className="px-6 py-3 bg-[color:var(--color-surface)] border-b border-[color:var(--color-border)]">
								<div className="flex items-center justify-between text-sm">
									<div className="flex items-center gap-4">
										<span className="text-[color:var(--color-text-muted)]">
											Rows:{" "}
											<span className="text-slate-900 font-medium">
												{tableData.row_count || 0}
											</span>
										</span>
										<span className="text-[color:var(--color-text-muted)]">
											Columns:{" "}
											<span className="text-slate-900 font-medium">
												{tableData.columns?.length || 0}
											</span>
										</span>
										<span className="text-[color:var(--color-text-muted)]">
											Showing:{" "}
											<span className="text-slate-900 font-medium">
												{Math.min(100, tableData.data.length)}
											</span>
										</span>
									</div>
									{tableData.data.length < (tableData.row_count || 0) && (
										<span className="text-[color:var(--color-accent)] text-xs">
											Preview limited to first 100 rows
										</span>
									)}
								</div>
							</div>

							{/* Table Container */}
							<div className="flex-1 overflow-auto bg-[#0d0d0d]">
								<table className="w-full text-sm">
									<thead className="bg-[color:var(--color-surface)] sticky top-0 z-10">
										<tr>
											<th className="px-4 py-3 text-left text-[color:var(--color-text-muted)] font-medium border-b border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
												#
											</th>
											{tableData.columns?.map((col) => (
												<th
													key={col}
													className="px-4 py-3 text-left text-[color:var(--color-text-secondary)] font-medium whitespace-nowrap border-b border-[color:var(--color-border)] bg-[color:var(--color-surface)]"
												>
													{col}
												</th>
											))}
										</tr>
									</thead>
									<tbody>
										{tableData.data.map((row, idx) => (
											<tr
												key={`preview-row-${JSON.stringify(row).substring(0, 50)}-${idx}`}
												className="border-b border-[color:var(--color-surface)] hover:bg-[color:var(--color-surface)]/50"
											>
												<td className="px-4 py-2 text-[color:var(--color-text-muted)] font-mono text-xs">
													{idx + 1}
												</td>
												{tableData.columns?.map((col) => (
													<td
														key={col}
														className="px-4 py-2 text-[color:var(--color-text-secondary)]"
													>
														<div
															className="max-w-xs truncate"
															title={
																row[col] !== null ? String(row[col]) : "NULL"
															}
														>
															{row[col] !== null ? (
																String(row[col])
															) : (
																<span className="text-[color:var(--color-text-muted)] italic">
																	NULL
																</span>
															)}
														</div>
													</td>
												))}
											</tr>
										))}
									</tbody>
								</table>
							</div>
						</>
					) : (
						<div className="flex-1 flex items-center justify-center">
							<div className="text-center">
								<AlertCircle className="w-12 h-12 text-[color:var(--color-text-muted)] mx-auto mb-3" />
								<h3 className="text-lg font-medium text-[color:var(--color-text-muted)] mb-2">
									Failed to Load Table
								</h3>
								<p className="text-[color:var(--color-text-muted)] max-w-md">
									{tableData?.error ||
										"An error occurred while loading the table data"}
								</p>
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
