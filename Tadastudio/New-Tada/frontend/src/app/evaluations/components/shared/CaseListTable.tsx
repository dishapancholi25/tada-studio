"use client";

import React from "react";
import { Paperclip } from "lucide-react";

export interface CaseListFileInfo {
	id: string;
	filename: string;
	mime_type: string;
	file_size: number;
}

export interface CaseListItem {
	id: string;
	input_data: string | null;
	expected_output?: string | null;
	tags?: string[] | null;
	judge_criteria?: Record<string, any> | null;
	/** Optional badge text shown next to row index (e.g. "already imported"). */
	badge?: string | null;
	/** Attached files metadata. */
	files?: CaseListFileInfo[] | null;
}

export interface CaseListTableProps {
	items: CaseListItem[];
	/** When provided, renders a checkbox column and calls back on toggle. */
	selectedIds?: Set<string>;
	onToggleSelect?: (id: string) => void;
	/** Currently expanded row id. */
	expandedId: string | null;
	onToggleExpand: (id: string | null) => void;
	/** When true, uses compact sizing (smaller text, tighter spacing). */
	compact?: boolean;
	/** Render extra actions in the last column for a given item. */
	renderActions?: (item: CaseListItem, index: number) => React.ReactNode;
	/** Render a custom expanded panel (e.g. inline editing). Return null to fall back to the default detail view. */
	renderExpandedOverride?: (item: CaseListItem) => React.ReactNode | null;
	/** Hide the Expected Output and Tags columns (useful when items are execution previews). */
	hideOutputColumn?: boolean;
}

export default function CaseListTable({
	items,
	selectedIds,
	onToggleSelect,
	expandedId,
	onToggleExpand,
	compact = false,
	renderActions,
	renderExpandedOverride,
	hideOutputColumn = false,
}: CaseListTableProps) {
	const truncate = (text: string | null | undefined, maxLen: number) => {
		if (!text) return "—";
		return text.length > maxLen ? `${text.slice(0, maxLen)}...` : text;
	};

	const selectable = selectedIds != null && onToggleSelect != null;
	const textSize = compact ? "text-[11px]" : "text-xs";
	const cellPy = compact ? "py-2" : "py-2.5";

	return (
		<table className="w-full text-left text-sm">
			<thead className="sticky top-0 bg-white z-10">
				<tr className="border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500">
					{selectable && <th className="w-8 pb-2.5" />}
					<th className="w-8 pb-2.5" />
					<th className="pb-2.5 pr-3 font-medium">Input</th>
					{!hideOutputColumn && (
						<th className="pb-2.5 pr-3 font-medium">Expected Output</th>
					)}
					{!hideOutputColumn && (
						<th className="pb-2.5 pr-3 font-medium">Tags</th>
					)}
					{renderActions && <th className="pb-2.5 w-16" />}
				</tr>
			</thead>
			<tbody>
				{items.map((item, idx) => {
					const isExpanded = expandedId === item.id;
					const isSelected = selectable && selectedIds!.has(item.id);
					const colSpan =
						(selectable ? 1 : 0) + 2 + (hideOutputColumn ? 0 : 2) + (renderActions ? 1 : 0);

					const overrideContent = isExpanded && renderExpandedOverride
						? renderExpandedOverride(item)
						: null;

					return (
						<React.Fragment key={item.id}>
							<tr
								data-tutorial={idx === 0 ? "test-case-first-row" : undefined}
								onClick={() => onToggleExpand(isExpanded ? null : item.id)}
								className={`cursor-pointer border-b transition-colors ${
									isExpanded
										? "border-slate-200 bg-slate-100"
										: isSelected
											? "border-slate-100 bg-[rgba(var(--color-primary-rgb),0.06)]"
											: "border-slate-100 hover:bg-slate-50"
								}`}
							>
								{selectable && (
									<td className={`${cellPy} pl-3 pr-1`}>
										<input
											type="checkbox"
											checked={isSelected}
											onChange={(e) => {
												e.stopPropagation();
												onToggleSelect!(item.id);
											}}
											onClick={(e) => e.stopPropagation()}
											className={`${compact ? "h-3.5 w-3.5" : "h-4 w-4"} shrink-0 cursor-pointer rounded border-slate-300 accent-[rgba(var(--color-primary-rgb),0.8)]`}
										/>
									</td>
								)}
								<td className={`${cellPy} pr-1 text-center`}>
									<span className="text-[10px] tabular-nums text-slate-400">
										{idx + 1}
									</span>
								</td>
								<td className={`${cellPy} pr-3`}>
									<div className="flex items-center gap-2">
										{item.files && item.files.length > 0 && (
											<span title={item.files[0].filename}>
												<Paperclip className="h-3 w-3 shrink-0 text-[rgba(var(--color-primary-rgb),0.6)]" />
											</span>
										)}
										<span className={`font-mono ${textSize} text-slate-700`}>
											{truncate(item.input_data, compact ? 50 : 60)}
										</span>
										{item.badge && (
											<span className="shrink-0 rounded-full border border-amber-400/30 bg-amber-400/10 px-1.5 py-0.5 text-[10px] text-amber-400">
												{item.badge}
											</span>
										)}
									</div>
								</td>
								{!hideOutputColumn && (
									<td className={`${cellPy} pr-3`}>
										<span className={`font-mono ${textSize} text-slate-500`}>
											{truncate(item.expected_output, compact ? 40 : 50)}
										</span>
									</td>
								)}
								{!hideOutputColumn && (
									<td className={`${cellPy} pr-3`}>
										{item.tags && item.tags.length > 0 ? (
											<div className="flex gap-1 flex-wrap">
												{item.tags.map((tag) => (
													<span
														key={tag}
														className="rounded-full border border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/40 px-2 py-0.5 text-[10px] font-medium text-[color:var(--color-text-secondary)]"
													>
														{tag}
													</span>
												))}
											</div>
										) : (
											<span className="text-xs text-slate-300">—</span>
										)}
									</td>
								)}
								{renderActions && (
									<td className={`${cellPy} text-right`}>
										{renderActions(item, idx)}
									</td>
								)}
							</tr>
							{isExpanded && overrideContent != null ? (
								<tr key={`${item.id}-override`} className="border-b border-slate-200">
									<td colSpan={colSpan} className="px-3 py-3">
										{overrideContent}
									</td>
								</tr>
							) : isExpanded ? (
								<tr key={`${item.id}-expanded`} data-tutorial={idx === 0 ? "test-case-first-expanded" : undefined} className="border-b border-slate-200">
									<td colSpan={colSpan} className="px-3 py-3">
										<div className="grid grid-cols-2 gap-4">
											<div>
												<p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">
													Input Data
												</p>
												<pre className="max-h-52 overflow-auto rounded-lg border border-slate-200 bg-slate-100 p-3 text-xs leading-relaxed text-slate-700 whitespace-pre-wrap break-words">
													{item.input_data || "(none)"}
												</pre>
											</div>
											<div>
												<p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">
													Expected Output
												</p>
												<pre className="max-h-52 overflow-auto rounded-lg border border-slate-200 bg-slate-100 p-3 text-xs leading-relaxed text-slate-700 whitespace-pre-wrap break-words">
													{item.expected_output || "(none)"}
												</pre>
											</div>
										</div>
										{item.judge_criteria && Object.keys(item.judge_criteria).length > 0 && (
											<div className="mt-3">
												<p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">
													Judge Criteria
												</p>
												<div className="space-y-1">
													{Object.entries(item.judge_criteria).map(([k, v]) => (
														<div
															key={k}
															className="flex gap-2 rounded-lg border border-slate-200 bg-slate-100 px-3 py-2"
														>
															<span className="shrink-0 text-xs font-medium text-slate-500">
																{k}
															</span>
															<span className="text-xs text-slate-500">
																{String(v)}
															</span>
														</div>
													))}
												</div>
											</div>
										)}
										{item.tags && item.tags.length > 0 && (
											<div className="mt-3">
												<p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">
													Tags
												</p>
												<div className="flex gap-1.5 flex-wrap">
													{item.tags.map((tag) => (
														<span
															key={tag}
															className="rounded-full border border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/40 px-2.5 py-1 text-xs font-medium text-[color:var(--color-text-secondary)]"
														>
															{tag}
														</span>
													))}
												</div>
											</div>
										)}
										{item.files && item.files.length > 0 && (
											<div className="mt-3">
												<p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">
													Attached File
												</p>
												{item.files.map((f) => (
													<div
														key={f.id}
														className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-100 px-3 py-2"
													>
														<Paperclip className="h-3.5 w-3.5 shrink-0 text-[rgba(var(--color-primary-rgb),0.6)]" />
														<span className="min-w-0 flex-1 truncate text-xs text-slate-700">{f.filename}</span>
														<span className="shrink-0 text-[10px] text-slate-400">
															{f.file_size < 1024 ? `${f.file_size} B` : f.file_size < 1048576 ? `${(f.file_size / 1024).toFixed(1)} KB` : `${(f.file_size / 1048576).toFixed(1)} MB`}
														</span>
													</div>
												))}
											</div>
										)}
									</td>
								</tr>
							) : null}
						</React.Fragment>
					);
				})}
			</tbody>
		</table>
	);
}
