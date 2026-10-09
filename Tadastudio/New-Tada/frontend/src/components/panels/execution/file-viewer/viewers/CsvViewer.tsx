"use client";

import { Check, Code, Copy, Table } from "lucide-react";
import { useState, useCallback, useMemo } from "react";
import type { CsvViewerProps } from "../types/fileViewer.types";

interface ParsedCsv {
	headers: string[];
	rows: string[][];
}

function parseCsv(content: string): ParsedCsv {
	const lines = content.trim().split("\n");
	if (lines.length === 0) {
		return { headers: [], rows: [] };
	}

	// Simple CSV parser (handles basic cases)
	const parseRow = (line: string): string[] => {
		const result: string[] = [];
		let current = "";
		let inQuotes = false;

		for (let i = 0; i < line.length; i++) {
			const char = line[i];
			const nextChar = line[i + 1];

			if (char === '"' && !inQuotes) {
				inQuotes = true;
			} else if (char === '"' && inQuotes) {
				if (nextChar === '"') {
					current += '"';
					i++; // Skip next quote
				} else {
					inQuotes = false;
				}
			} else if (char === "," && !inQuotes) {
				result.push(current.trim());
				current = "";
			} else {
				current += char;
			}
		}
		result.push(current.trim());
		return result;
	};

	const headers = parseRow(lines[0]);
	const rows = lines.slice(1).map(parseRow);

	return { headers, rows };
}

export default function CsvViewer({ content, filename }: CsvViewerProps) {
	const [copied, setCopied] = useState(false);
	const [viewMode, setViewMode] = useState<"table" | "raw">("table");

	const parsedData = useMemo(() => parseCsv(content), [content]);

	const handleCopy = useCallback(async () => {
		try {
			await navigator.clipboard.writeText(content);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch (err) {
			console.error("Failed to copy:", err);
		}
	}, [content]);

	return (
		<div className="h-full flex flex-col">
			{/* Toolbar */}
			<div className="flex items-center justify-between px-4 py-2 border-b border-[color:var(--color-border)]/40 bg-[rgba(20,20,20,0.5)]">
				<div className="flex items-center gap-3">
					{/* View mode toggle */}
					<div className="flex rounded-lg border border-[color:var(--color-border)]/60 overflow-hidden">
						<button
							onClick={() => setViewMode("table")}
							className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all ${
								viewMode === "table"
									? "bg-[rgba(var(--color-primary-rgb),0.15)] text-[color:var(--color-primary)]"
									: "text-[color:var(--color-text-secondary)] hover:text-slate-900"
							}`}
						>
							<Table className="w-3.5 h-3.5" />
							Table
						</button>
						<button
							onClick={() => setViewMode("raw")}
							className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all border-l border-[color:var(--color-border)]/60 ${
								viewMode === "raw"
									? "bg-[rgba(var(--color-primary-rgb),0.15)] text-[color:var(--color-primary)]"
									: "text-[color:var(--color-text-secondary)] hover:text-slate-900"
							}`}
						>
							<Code className="w-3.5 h-3.5" />
							Raw
						</button>
					</div>

					{/* Row count */}
					<span className="text-xs text-[color:var(--color-text-muted)]">
						{parsedData.rows.length.toLocaleString()} rows ×{" "}
						{parsedData.headers.length} columns
					</span>
				</div>

				{/* Copy button */}
				<button
					onClick={handleCopy}
					className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
						border border-[color:var(--color-border)]/60 text-[color:var(--color-text-secondary)]
						hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-slate-900
						transition-all"
				>
					{copied ? (
						<>
							<Check className="w-3.5 h-3.5 text-emerald-400" />
							Copied!
						</>
					) : (
						<>
							<Copy className="w-3.5 h-3.5" />
							Copy
						</>
					)}
				</button>
			</div>

			{/* Content */}
			<div className="flex-1 overflow-auto custom-scrollbar">
				{viewMode === "table" ? (
					<div className="p-4">
						<div className="rounded-xl border border-[color:var(--color-border)]/70 overflow-hidden">
							<table className="min-w-full divide-y divide-[color:var(--color-border)]/40">
								<thead>
									<tr className="bg-[color:var(--color-surface)]/50">
										{parsedData.headers.map((header, i) => (
											<th
												key={i}
												className="px-4 py-3 text-left text-xs font-semibold capitalize tracking-wider text-[color:var(--color-text-secondary)] whitespace-nowrap"
											>
												{header}
											</th>
										))}
									</tr>
								</thead>
								<tbody className="divide-y divide-[color:var(--color-border)]/30">
									{parsedData.rows.map((row, rowIndex) => (
										<tr
											key={rowIndex}
											className="hover:bg-[color:var(--color-surface)]/30 transition-colors"
										>
											{row.map((cell, cellIndex) => (
												<td
													key={cellIndex}
													className="px-4 py-3 text-sm text-[color:var(--color-text-secondary)] whitespace-nowrap"
												>
													{cell || (
														<span className="text-[color:var(--color-text-muted)] italic">
															empty
														</span>
													)}
												</td>
											))}
										</tr>
									))}
								</tbody>
							</table>
						</div>
					</div>
				) : (
					<pre className="p-4 font-mono text-sm text-[color:var(--color-text-secondary)] whitespace-pre">
						{content}
					</pre>
				)}
			</div>
		</div>
	);
}
