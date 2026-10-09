"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Copy, Download, ExternalLink, Globe, Lock, Loader2, Trash2, Upload, Users } from "lucide-react";
import * as evalApi from "@/lib/evaluation-api";
import type { DatasetExport, EvaluationDataset, EvaluationRun } from "@/lib/evaluation-api";
import Pagination from "@/components/ui/Pagination";
import Dropdown from "@/components/ui/Dropdown";
import DatasetEditorModal from "./DatasetEditorModal";
import Tooltip from "@/components/ui/Tooltip";

export default function DatasetsTab({ initialDatasetId, onInitialDatasetHandled, showAllUsers }: { initialDatasetId?: string | null; onInitialDatasetHandled?: () => void; showAllUsers?: boolean }) {
	const [datasets, setDatasets] = useState<EvaluationDataset[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	// User's own workflows — used to resolve links for shared datasets
	const [userWorkflows, setUserWorkflows] = useState<{ id: string; name: string }[]>([]);

	// Filter state
	const [filterType, setFilterType] = useState("");
	const [filterTarget, setFilterTarget] = useState("");
	const [filterDatePreset, setFilterDatePreset] = useState("");
	const [filterCustomFrom, setFilterCustomFrom] = useState("");
	const [filterCustomTo, setFilterCustomTo] = useState("");
	const [ownershipFilter, setOwnershipFilter] = useState<"all" | "my" | "shared">("all");
	const [sharingFilter, setSharingFilter] = useState("");

	// Modal state
	const [editingDataset, setEditingDataset] = useState<EvaluationDataset | null>(null);
	const [showCreateModal, setShowCreateModal] = useState(false);

	// Pagination state
	const [currentPage, setCurrentPage] = useState(1);
	const [pageSize, setPageSize] = useState(10);

	// Delete confirmation state
	const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
	const [deleteAssociatedRuns, setDeleteAssociatedRuns] = useState<EvaluationRun[]>([]);
	const [loadingDeleteRuns, setLoadingDeleteRuns] = useState(false);

	// Export / import state
	const [exportingId, setExportingId] = useState<string | null>(null);
	const [importing, setImporting] = useState(false);
	const [importPreview, setImportPreview] = useState<DatasetExport | null>(null);
	const [importName, setImportName] = useState("");

	const handleExport = async (datasetId: string, datasetName: string) => {
		setExportingId(datasetId);
		try {
			const data = await evalApi.exportDataset(datasetId);
			const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
			const url = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download = `${datasetName.replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		} catch (err: any) {
			setError(err.message ?? "Failed to export dataset");
		} finally {
			setExportingId(null);
		}
	};

	const handleImportFile = async (file: File) => {
		setError(null);
		try {
			const text = await file.text();
			const payload: DatasetExport = JSON.parse(text);
			if (payload.format !== "nexus-dataset-v1") {
				throw new Error("Invalid file format. Expected a Nexus dataset export (nexus-dataset-v1).");
			}
			setImportName(payload.dataset.name);
			setImportPreview(payload);
		} catch (err: any) {
			setError(err.message ?? "Failed to read import file");
		}
	};

	const handleConfirmImport = async () => {
		if (!importPreview || !importName.trim()) return;
		setImporting(true);
		setError(null);
		try {
			const payload = {
				...importPreview,
				dataset: { ...importPreview.dataset, name: importName.trim() },
			};
			const created = await evalApi.importDataset(payload);
			setImportPreview(null);
			setImportName("");
			await load();
			setEditingDataset(created);
		} catch (err: any) {
			setError(err.message ?? "Failed to import dataset");
		} finally {
			setImporting(false);
		}
	};

	const load = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const list = await evalApi.listDatasets(undefined, undefined, ownershipFilter, showAllUsers);
			setDatasets(list);
		} catch (err: any) {
			setError(err.message ?? "Failed to load datasets");
		} finally {
			setLoading(false);
		}
	}, [ownershipFilter, showAllUsers]);

	useEffect(() => {
		load();
	}, [load]);

	// Re-fetch when the evaluations tutorial finishes creating demo data
	useEffect(() => {
		const handler = () => load();
		window.addEventListener("tutorialEvalDataReady", handler);
		return () => window.removeEventListener("tutorialEvalDataReady", handler);
	}, [load]);

	// Tutorial: open the first dataset when requested
	useEffect(() => {
		const handler = () => {
			const first = datasets[0];
			if (first) setEditingDataset(first);
		};
		window.addEventListener("tutorialOpenDataset", handler);
		return () => window.removeEventListener("tutorialOpenDataset", handler);
	}, [datasets]);

	// Tutorial: close the dataset modal when requested
	useEffect(() => {
		const handler = () => setEditingDataset(null);
		window.addEventListener("tutorialCloseDatasetModal", handler);
		return () => window.removeEventListener("tutorialCloseDatasetModal", handler);
	}, []);

	useEffect(() => {
		evalApi.getWorkflows().then(setUserWorkflows).catch(() => {});
	}, []);

	// Map workflow name → current user's workflow id for resolving shared-dataset links
	const workflowIdByName = useMemo(() => {
		const m = new Map<string, string>();
		for (const wf of userWorkflows) m.set(wf.name, wf.id);
		return m;
	}, [userWorkflows]);

	// Auto-open dataset from URL param (e.g. linked from runs table)
	useEffect(() => {
		if (!initialDatasetId || loading) return;
		const match = datasets.find((d) => d.id === initialDatasetId);
		if (match) {
			setEditingDataset(match);
			onInitialDatasetHandled?.();
		} else if (!loading && datasets.length > 0) {
			// Dataset not found in current list — fetch it directly
			evalApi.getDataset(initialDatasetId)
				.then((ds) => setEditingDataset(ds))
				.catch(() => {})
				.finally(() => onInitialDatasetHandled?.());
		}
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [initialDatasetId, loading, datasets]);

	// Build unique target options from loaded datasets for the target filter dropdown
	const datasetTargetOptions = useMemo(() => {
		const seen = new Map<string, string>();
		for (const ds of datasets) {
			if (ds.target_id && (!filterType || ds.target_type === filterType) && !seen.has(ds.target_id)) {
				seen.set(ds.target_id, ds.target_name || ds.target_id.slice(0, 12));
			}
		}
		return Array.from(seen.entries()).map(([id, label]) => ({ id, label }));
	}, [datasets, filterType]);

	// Build unique group options from loaded datasets for the sharing filter
	const sharingFilterOptions = useMemo(() => {
		const groups = new Map<string, string>();
		for (const ds of datasets) {
			if (ds.visible_to_groups) {
				for (const g of ds.visible_to_groups) {
					if (!groups.has(g)) {
						groups.set(g, g === "__all__" ? "Everyone" : g);
					}
				}
			}
		}
		return Array.from(groups.entries())
			.map(([id, label]) => ({ id, label }))
			.sort((a, b) => a.label.localeCompare(b.label));
	}, [datasets]);

	// Compute the date cutoff from preset or custom range
	const datasetDateRange = useMemo(() => {
		if (filterDatePreset === "custom") {
			return {
				from: filterCustomFrom ? new Date(filterCustomFrom) : null,
				to: filterCustomTo ? new Date(`${filterCustomTo}T23:59:59`) : null,
			};
		}
		if (!filterDatePreset) return null;
		const now = new Date();
		const hours: Record<string, number> = { "24h": 24, "7d": 168, "30d": 720, "90d": 2160 };
		const h = hours[filterDatePreset];
		if (!h) return null;
		return { from: new Date(now.getTime() - h * 3600_000), to: null };
	}, [filterDatePreset, filterCustomFrom, filterCustomTo]);

	// Client-side filtering of datasets
	const filteredDatasets = useMemo(() => {
		let result = datasets;
		if (filterType) result = result.filter((ds) => ds.target_type === filterType);
		if (filterTarget) result = result.filter((ds) => ds.target_id === filterTarget);
		if (datasetDateRange) {
			result = result.filter((ds) => {
				if (!ds.created_at) return false;
				const d = new Date(ds.created_at);
				if (datasetDateRange.from && d < datasetDateRange.from) return false;
				if (datasetDateRange.to && d > datasetDateRange.to) return false;
				return true;
			});
		}
		if (sharingFilter === "private") {
			result = result.filter((ds) => !ds.visible_to_groups || ds.visible_to_groups.length === 0);
		} else if (sharingFilter) {
			result = result.filter((ds) => ds.visible_to_groups?.includes(sharingFilter));
		}
		return result;
	}, [datasets, filterType, filterTarget, datasetDateRange, sharingFilter]);

	// Reset to page 1 when filters or dataset list change
	useEffect(() => {
		setCurrentPage(1);
	}, [filterType, filterTarget, datasetDateRange, ownershipFilter, sharingFilter, datasets]);

	const paginatedDatasets = useMemo(() => {
		const start = (currentPage - 1) * pageSize;
		return filteredDatasets.slice(start, start + pageSize);
	}, [filteredDatasets, currentPage, pageSize]);

	const handleClone = async (id: string) => {
		try {
			const cloned = await evalApi.cloneDataset(id);
			await load();
			setEditingDataset(cloned);
		} catch (err: any) {
			setError(err.message ?? "Failed to clone dataset");
		}
	};

	const handleDelete = async (id: string) => {
		try {
			await evalApi.deleteDataset(id);
			if (editingDataset?.id === id) setEditingDataset(null);
			setConfirmDeleteId(null);
			setDeleteAssociatedRuns([]);
			await load();
		} catch (err: any) {
			setError(err.message ?? "Failed to delete dataset");
			setConfirmDeleteId(null);
			setDeleteAssociatedRuns([]);
		}
	};

	const initiateDelete = async (id: string) => {
		setConfirmDeleteId(id);
		setDeleteAssociatedRuns([]);
		setLoadingDeleteRuns(true);
		try {
			const runs = await evalApi.listRuns({ dataset_id: id, limit: 50 });
			setDeleteAssociatedRuns(runs);
		} catch {
			// Non-critical — proceed without showing runs
		} finally {
			setLoadingDeleteRuns(false);
		}
	};

	const selectClass = "max-w-[10rem] truncate rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15 hover:border-orange-400 hover:bg-white hover:text-slate-900 transition-all";
	const filterTriggerClass = "min-w-[7rem] max-w-[10rem] rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:border-orange-400 hover:bg-white hover:text-slate-900 transition-all";

	return (
		<div className="h-full flex flex-col">
			{error && <p className="mb-2 text-sm text-red-400 shrink-0">{error}</p>}

			{/* Unified container: Filters + Table + Pagination */}
			<div className="flex-1 flex flex-col rounded-2xl border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)] overflow-hidden min-h-0">
				{/* Filters + action buttons */}
				<div className="flex flex-wrap items-start gap-3 p-4 border-b border-slate-200 bg-white shrink-0">
					<div className="flex min-w-[8rem] flex-1 flex-wrap items-center gap-2">
						<Dropdown
							value={ownershipFilter}
							onChange={(v) => setOwnershipFilter(v as "all" | "my" | "shared")}
							options={[
								{ value: "all", label: "All Datasets" },
								{ value: "my", label: "My Datasets" },
								{ value: "shared", label: "Shared with Me" },
							]}
							width="trigger"
							triggerClassName={filterTriggerClass}
							menuAppearance="light"
						/>
						<Dropdown
							value={filterType}
							onChange={(v) => {
								setFilterType(v);
								setFilterTarget("");
							}}
							options={[
								{ value: "", label: "All types" },
								{ value: "workflow", label: "Workflow" },
								{ value: "agent", label: "Agent" },
								{ value: "model", label: "Model" },
								{ value: "tool", label: "Tool" },
							]}
							width="trigger"
							triggerClassName={filterTriggerClass}
							menuAppearance="light"
						/>
						{datasetTargetOptions.length > 0 && (
							<Dropdown
								value={filterTarget}
								onChange={setFilterTarget}
								options={[{ value: "", label: "All targets" }, ...datasetTargetOptions.map((opt) => ({ value: opt.id, label: opt.label }))]}
								width="trigger"
								triggerClassName={filterTriggerClass}
								menuAppearance="light"
							/>
						)}
						<Dropdown
							value={sharingFilter}
							onChange={setSharingFilter}
							options={[
								{ value: "", label: "All sharing" },
								{ value: "private", label: "Private" },
								...sharingFilterOptions.map((opt) => ({ value: opt.id, label: opt.label })),
							]}
							width="trigger"
							triggerClassName={filterTriggerClass}
							menuAppearance="light"
						/>
						<Dropdown
							value={filterDatePreset}
							onChange={(v) => {
								setFilterDatePreset(v);
								if (v !== "custom") {
									setFilterCustomFrom("");
									setFilterCustomTo("");
								}
							}}
							options={[
								{ value: "", label: "All dates" },
								{ value: "24h", label: "Last 24 hours" },
								{ value: "7d", label: "Last 7 days" },
								{ value: "30d", label: "Last 30 days" },
								{ value: "90d", label: "Last 90 days" },
								{ value: "custom", label: "Custom range" },
							]}
							width="trigger"
							triggerClassName={filterTriggerClass}
							menuAppearance="light"
						/>
						{filterDatePreset === "custom" && (
							<>
								<input
									type="date"
									value={filterCustomFrom}
									onChange={(e) => setFilterCustomFrom(e.target.value)}
									title={filterCustomFrom || "From"}
									className={selectClass}
								/>
								<span className="text-xs text-[color:var(--color-text-muted)]">to</span>
								<input
									type="date"
									value={filterCustomTo}
									onChange={(e) => setFilterCustomTo(e.target.value)}
									title={filterCustomTo || "To"}
									className={selectClass}
								/>
							</>
						)}
					</div>

				<div className="flex shrink-0 items-center gap-2">
					<button
						type="button"
						onClick={() => load()}
						className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
					>
						↻ Refresh
					</button>
					<label
						className={`rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-within:ring-2 focus-within:ring-orange-500/25 inline-flex items-center gap-1.5 cursor-pointer ${importing ? "opacity-50 pointer-events-none" : ""}`}
					>
						{importing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
						{importing ? "Importing…" : "Import Dataset"}
						<input
							type="file"
							accept=".json"
							className="sr-only"
							onChange={(e) => {
								const f = e.target.files?.[0];
								if (f) handleImportFile(f);
								e.target.value = "";
							}}
							disabled={importing}
						/>
					</label>
					<button
						type="button"
						data-tutorial="new-dataset-btn"
						onClick={() => setShowCreateModal(true)}
						className="rounded-xl border border-orange-500 bg-orange-500 px-4 py-1.5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-all hover:border-orange-600 hover:bg-orange-600 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
					>
						New Dataset
					</button>
				</div>
			</div>

			{/* Table content area - fills remaining space */}
			<div className="flex-1 overflow-auto min-h-0">
				{loading ? (
					<p className="py-10 text-center text-sm text-slate-500">Loading datasets...</p>
				) : filteredDatasets.length === 0 && datasets.length > 0 ? (
					<p className="py-10 text-center text-sm text-slate-500">No datasets match the current filters.</p>
				) : datasets.length === 0 ? (
					<p className="py-10 text-center text-sm text-slate-500">No datasets yet.</p>
				) : (
					<table className="w-full min-w-[880px] text-left text-sm table-fixed">
						<thead className="sticky top-0 bg-[#FBFBFB] z-10">
							<tr className="border-b border-slate-200 text-xs uppercase text-slate-500 whitespace-nowrap">
								<th className="px-4 py-3 w-[18%]">Name</th>
								<th className="px-4 py-3 w-[10%]">Type</th>
								<th className="px-4 py-3 w-[15%]">Target</th>
								<th className="px-4 py-3 w-[8%]">Cases</th>
								<th className="px-4 py-3 w-[8%]">Runs</th>
								<th className="px-4 py-3 w-[12%]">Created</th>
								{showAllUsers && <th className="px-4 py-3 w-[10%]">Owner</th>}
								<th className="px-4 py-3 w-[10%]">Sharing</th>
								<th className="px-4 py-3 w-[10%]" />
							</tr>
					</thead>
					<tbody>
						{paginatedDatasets.map((ds, dsIdx) => (
							<tr
								key={ds.id}
								data-tutorial={dsIdx === 0 ? "eval-dataset-first" : undefined}
								onClick={() => setEditingDataset(ds)}
								className="cursor-pointer border-b border-slate-100 transition-colors hover:bg-[#FFF1E8]"
							>
								<td className="px-4 py-3">
									<Tooltip content={ds.name} position="top" display="block">
										<div className="truncate text-slate-900">{ds.name}</div>
									</Tooltip>
									{ds.description && (
										<Tooltip content={ds.description} position="top" display="block">
											<p className="mt-0.5 text-xs text-slate-500 truncate">{ds.description}</p>
										</Tooltip>
									)}
								</td>
								<td className="px-4 py-3">
									<span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-[11px] font-medium text-orange-700 whitespace-nowrap">
										{ds.target_type}
									</span>
								</td>
								<td className="px-4 py-3 overflow-hidden">
									{ds.target_type === "workflow" && ds.target_id ? (
										<Tooltip content={ds.target_name ?? ds.target_id} position="top" display="block">
											<a
												href={`/workflow/${encodeURIComponent((ds.workflow_name && workflowIdByName.get(ds.workflow_name)) || ds.target_id)}`}
												target="_blank"
												rel="noopener noreferrer"
												onClick={(e) => e.stopPropagation()}
												className="flex w-full min-w-0 items-center gap-1 text-xs text-[rgba(var(--color-primary-rgb),0.75)] transition hover:text-[rgba(var(--color-primary-rgb),1)] hover:underline"
											>
												<span className="min-w-0 flex-1 truncate">{ds.target_name ?? ds.target_id.slice(0, 10)}</span>
												<ExternalLink size={10} className="shrink-0" />
											</a>
										</Tooltip>
									) : (ds.target_name || ds.target_id) ? (
										<Tooltip content={ds.target_name || ds.target_id || ""} position="top" display="block">
											<span className="text-slate-600 truncate block">
												{ds.target_name || ds.target_id!.slice(0, 12) + "\u2026"}
											</span>
										</Tooltip>
									) : (
										<span className="text-slate-400">\u2014</span>
									)}
								</td>
								<td className="px-4 py-3 text-slate-600 tabular-nums whitespace-nowrap">{ds.test_case_count}</td>
								<td className="px-4 py-3 text-slate-600 tabular-nums whitespace-nowrap">{ds.run_count ?? 0}</td>
								<td className="px-4 py-3 text-slate-500 whitespace-nowrap">
									{ds.created_at ? new Date(ds.created_at).toLocaleDateString() : "\u2014"}
								</td>
								{showAllUsers && (
									<td className="px-4 py-3 text-xs text-slate-500">
										<Tooltip content={ds.created_by_email ?? ds.created_by_name ?? ""} position="top" display="block">
											<div className="truncate">{ds.created_by_name ?? ds.created_by_email ?? ds.created_by_user_id?.slice(0, 8) ?? "\u2014"}</div>
										</Tooltip>
									</td>
								)}
								<td className="px-4 py-3 whitespace-nowrap">
									{ds.is_read_only ? (
										<span className="inline-flex items-center gap-1 text-xs text-slate-500" title={`Shared by ${ds.created_by_name || "another user"}`}>
											<Lock size={11} />
											Read-only
										</span>
									) : ds.visible_to_groups && ds.visible_to_groups.length > 0 ? (
										<span className="inline-flex items-center gap-1 text-xs text-[rgba(var(--color-primary-rgb),0.7)]">
											{ds.visible_to_groups.includes("__all__") ? (
												<><Globe size={11} /> Everyone</>
											) : (
												<><Users size={11} /> {ds.visible_to_groups.length} group{ds.visible_to_groups.length !== 1 ? "s" : ""}</>
											)}
										</span>
									) : (
										<span className="text-xs text-slate-400">Private</span>
									)}
								</td>
								<td className="px-4 py-3 text-right">
									<div className="inline-flex items-center gap-1">
										<button
											type="button"
											onClick={(e) => {
												e.stopPropagation();
												handleExport(ds.id, ds.name);
											}}
											disabled={exportingId === ds.id}
											className="rounded-xl p-2 text-[color:var(--color-text-muted)] transition-all hover:text-[rgba(var(--color-primary-rgb),1)] hover:bg-[rgba(var(--color-primary-rgb),0.10)] border border-transparent hover:border-[rgba(var(--color-primary-rgb),0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] disabled:opacity-30"
											title="Export dataset as JSON"
										>
											{exportingId === ds.id ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
										</button>
										<button
											type="button"
											onClick={(e) => {
												e.stopPropagation();
												handleClone(ds.id);
											}}
											className="rounded-xl p-2 text-[color:var(--color-text-muted)] transition-all hover:text-[rgba(var(--color-primary-rgb),1)] hover:bg-[rgba(var(--color-primary-rgb),0.10)] border border-transparent hover:border-[rgba(var(--color-primary-rgb),0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
											title="Clone dataset"
										>
											<Copy size={14} />
										</button>
										{!ds.is_read_only && (
										<button
											type="button"
											onClick={(e) => {
												e.stopPropagation();
												initiateDelete(ds.id);
											}}
											className="rounded-xl p-2 text-[color:var(--color-text-muted)] transition-all hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/45"
											title="Delete dataset"
										>
											<Trash2 size={14} />
										</button>
										)}
									</div>
								</td>
							</tr>
						))}
					</tbody>
				</table>
				)}
			</div>

			{/* Pagination - inside the unified box */}
			{!loading && filteredDatasets.length > 0 && (
				<div className="border-t border-slate-200 bg-white">
					<Pagination
						currentPage={currentPage}
						totalCount={filteredDatasets.length}
						pageSize={pageSize}
						onPageChange={setCurrentPage}
						onPageSizeChange={(size) => { setPageSize(size); setCurrentPage(1); }}
						pageSizeOptions={[10, 20, 50]}
						appearance="light"
					/>
				</div>
			)}
		</div>

			{/* Delete confirmation dialog */}
			{confirmDeleteId && (
				<div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
					<div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
						<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
						<h3 className="mb-2 text-base font-semibold text-slate-900">Delete Dataset</h3>
						<p className="mb-4 text-sm text-slate-600">
							Are you sure you want to delete this dataset? This action cannot be undone.
						</p>
						{loadingDeleteRuns ? (
							<div className="mb-4 flex items-center gap-2 text-xs text-slate-500">
								<Loader2 size={12} className="animate-spin" />
								Checking for associated runs…
							</div>
						) : deleteAssociatedRuns.length > 0 && (
							<div className="mb-4 rounded-xl border border-amber-400 bg-white p-3">
								<p className="mb-2 text-xs font-medium text-amber-700">
									{deleteAssociatedRuns.length} evaluation run{deleteAssociatedRuns.length !== 1 ? "s" : ""} use{deleteAssociatedRuns.length === 1 ? "s" : ""} this dataset and will no longer have access to its test cases:
								</p>
								<ul className="max-h-32 space-y-1 overflow-y-auto pr-1">
									{deleteAssociatedRuns.map((run) => (
										<li key={run.id} className="flex items-center justify-between text-xs text-slate-600">
											<span className="truncate mr-2">{run.name || `Run ${run.id.slice(0, 8)}`}</span>
											<span className="shrink-0 rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] text-slate-500">
												{run.status}
											</span>
										</li>
									))}
								</ul>
							</div>
						)}
						<div className="flex justify-end gap-2">
							<button
								type="button"
								onClick={() => { setConfirmDeleteId(null); setDeleteAssociatedRuns([]); }}
								className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={() => handleDelete(confirmDeleteId)}
								className="rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-400 transition-all hover:bg-red-500/20 hover:border-red-500/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/45"
							>
								Delete
							</button>
						</div>
					</div>
				</div>
			)}

			{/* Import preview dialog */}
			{importPreview && (
				<div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
					<div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
						<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
						<h3 className="mb-4 text-base font-semibold text-slate-900">Import Dataset</h3>
						<div className="space-y-4">
							<div>
								<label className="mb-1 block text-xs text-slate-500">Dataset Name</label>
								<input
									type="text"
									value={importName}
									onChange={(e) => setImportName(e.target.value)}
									onKeyDown={(e) => { if (e.key === "Enter" && importName.trim()) handleConfirmImport(); }}
									className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 hover:border-orange-400 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15 transition-all"
									autoFocus
								/>
							</div>
							<div className="space-y-1.5 text-xs text-slate-600">
								{importPreview.dataset.description && (
									<p><span className="text-slate-500">Description:</span> {importPreview.dataset.description}</p>
								)}
								<p><span className="text-slate-500">Target type:</span> <span className="text-slate-900">{importPreview.dataset.target_type}</span></p>
								{(importPreview.dataset.target_name || importPreview.dataset.workflow_name) && (
									<p>
										<span className="text-slate-500">Target:</span>{" "}
										<span className="text-slate-900">
											{importPreview.dataset.workflow_name}
											{importPreview.dataset.workflow_name && importPreview.dataset.target_name && importPreview.dataset.target_name !== importPreview.dataset.workflow_name ? " / " : ""}
											{importPreview.dataset.target_name && importPreview.dataset.target_name !== importPreview.dataset.workflow_name ? importPreview.dataset.target_name : ""}
										</span>
									</p>
								)}
								<p><span className="text-slate-500">Test cases:</span> <span className="text-slate-900">{importPreview.test_cases.length}</span></p>
								{importPreview.test_cases.filter((tc) => tc.file_info?.base64).length > 0 && (
									<p><span className="text-slate-500">File attachments:</span> <span className="text-slate-900">{importPreview.test_cases.filter((tc) => tc.file_info?.base64).length}</span></p>
								)}
							</div>
						</div>
						<div className="mt-6 flex justify-end gap-2">
							<button
								type="button"
								onClick={() => { setImportPreview(null); setImportName(""); }}
								className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={handleConfirmImport}
								disabled={importing || !importName.trim()}
								className="rounded-xl border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-all hover:border-orange-600 hover:bg-orange-600 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:shadow-none inline-flex items-center gap-1.5"
							>
								{importing ? <Loader2 size={14} className="animate-spin" /> : null}
								{importing ? "Importing…" : "Import"}
							</button>
						</div>
					</div>
				</div>
			)}

			{/* Dataset editor modal (edit existing) */}
			{editingDataset && (
				<DatasetEditorModal
					dataset={editingDataset}
					onClose={() => setEditingDataset(null)}
					onRefreshDatasets={load}
				/>
			)}

			{/* Dataset editor modal (create new) */}
			{showCreateModal && (
				<DatasetEditorModal
					dataset={null}
					onClose={() => setShowCreateModal(false)}
					onRefreshDatasets={load}
				/>
			)}
		</div>
	);
}
