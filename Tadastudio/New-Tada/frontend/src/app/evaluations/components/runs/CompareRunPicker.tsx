"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { GitCompareArrows } from "lucide-react";
import { api } from "@/lib/api";
import * as evalApi from "@/lib/evaluation-api";
import type { EvaluationRun } from "@/lib/evaluation-api";
import { ScoreBadge, StatusBadge } from "../shared/ScoreBadge";
import Dropdown from "@/components/ui/Dropdown";

export default function CompareRunPicker({
	currentRun,
	selectedId,
	onSelect,
}: {
	currentRun: EvaluationRun;
	selectedId: string;
	onSelect: (id: string, name: string) => void;
}) {
	const [runs, setRuns] = useState<EvaluationRun[]>([]);
	const [loading, setLoading] = useState(true);
	const [statusFilter, setStatusFilter] = useState("");
	const [triggerFilter, setTriggerFilter] = useState("");
	const [typeFilter, setTypeFilter] = useState("");
	const [workflowFilter, setWorkflowFilter] = useState("");
	const [datasetFilter, setDatasetFilter] = useState("");
	const [datePreset, setDatePreset] = useState("");
	const [customFrom, setCustomFrom] = useState("");
	const [customTo, setCustomTo] = useState("");

	// Fetch workflow names for filter dropdown
	const [wfNameMap, setWfNameMap] = useState<Map<string, string>>(new Map());
	useEffect(() => {
		api.listGraphs()
			.then((res) => {
				const m = new Map<string, string>();
				for (const g of (res.graphs ?? []) as { workflow_id: string; name: string }[]) {
					m.set(g.workflow_id, g.name);
				}
				setWfNameMap(m);
			})
			.catch(() => {});
	}, []);

	const load = useCallback(async () => {
		setLoading(true);
		try {
			const list = await evalApi.listRuns({
				status: statusFilter || undefined,
				trigger: triggerFilter || undefined,
				target_type: typeFilter || undefined,
				workflow_id: workflowFilter || undefined,
			});
			setRuns(list.filter((r) => r.id !== currentRun.id));
		} catch {
			setRuns([]);
		} finally {
			setLoading(false);
		}
	}, [currentRun.id, statusFilter, triggerFilter, typeFilter, workflowFilter]);

	useEffect(() => {
		load();
	}, [load]);

	// Build workflow options from full graph list (not filtered runs)
	const workflowOptions = useMemo(() => {
		return Array.from(wfNameMap.entries())
			.map(([id, name]) => ({ id, label: name }))
			.sort((a, b) => a.label.localeCompare(b.label));
	}, [wfNameMap]);

	// Fetch all datasets for filter dropdown (independent of filtered runs)
	const [allDatasets, setAllDatasets] = useState<{ id: string; name: string }[]>([]);
	useEffect(() => {
		evalApi.listDatasets()
			.then((ds) => setAllDatasets(ds.map((d) => ({ id: d.id, name: d.name }))))
			.catch(() => {});
	}, []);

	const datasetOptions = useMemo(() => {
		return allDatasets.map((d) => ({ id: d.id, label: d.name }));
	}, [allDatasets]);

	// Map dataset_id -> name for table display (works even if backend doesn't return dataset_name)
	const dsNameMap = useMemo(() => {
		const m = new Map<string, string>();
		for (const d of allDatasets) m.set(d.id, d.name);
		return m;
	}, [allDatasets]);

	const dateRange = useMemo(() => {
		if (datePreset === "custom") {
			return {
				from: customFrom ? new Date(customFrom) : null,
				to: customTo ? new Date(`${customTo}T23:59:59`) : null,
			};
		}
		if (!datePreset) return null;
		const hours: Record<string, number> = { "24h": 24, "7d": 168, "30d": 720, "90d": 2160 };
		const h = hours[datePreset];
		if (!h) return null;
		return { from: new Date(Date.now() - h * 3600_000), to: null };
	}, [datePreset, customFrom, customTo]);

	const getRunWorkflowId = useCallback((r: EvaluationRun) => r.workflow_id || (r.target_type === "workflow" ? r.target_id : null), []);

	// Determine if a run is "similar" based on target_type of the current run
	const isSimilar = useCallback((r: EvaluationRun) => {
		if (r.target_type !== currentRun.target_type) return false;
		const curWfId = getRunWorkflowId(currentRun);
		switch (currentRun.target_type) {
			case "workflow":
				// Same workflow, dataset, type
				return getRunWorkflowId(r) === curWfId && r.dataset_id === currentRun.dataset_id;
			case "agent":
				// Same workflow, agent (target_id), dataset, type
				return getRunWorkflowId(r) === curWfId && r.target_id === currentRun.target_id && r.dataset_id === currentRun.dataset_id;
			case "tool":
				// Same tool (target_id), type
				return r.target_id === currentRun.target_id;
			case "model":
				// Same type only (already matched above)
				return true;
			default:
				return false;
		}
	}, [currentRun, getRunWorkflowId]);

	const filteredRuns = useMemo(() => {
		let result = runs;
		if (datasetFilter) result = result.filter((r) => r.dataset_id === datasetFilter);
		if (dateRange) {
			result = result.filter((r) => {
				if (!r.created_at) return false;
				const d = new Date(r.created_at);
				if (dateRange.from && d < dateRange.from) return false;
				if (dateRange.to && d > dateRange.to) return false;
				return true;
			});
		}
		// Sort similar runs first, then by date descending within each group
		result = [...result].sort((a, b) => {
			const aS = isSimilar(a) ? 1 : 0;
			const bS = isSimilar(b) ? 1 : 0;
			if (bS !== aS) return bS - aS;
			return new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime();
		});
		return result;
	}, [runs, datasetFilter, dateRange, isSimilar]);

	const selectCls = "rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-900 focus:border-slate-300 focus:outline-none";

	return (
		<div className="space-y-3">
			<div className="flex flex-wrap items-center gap-2">
				<Dropdown
					value={statusFilter}
					onChange={setStatusFilter}
					menuAppearance="light"
					width="trigger"
					triggerClassName={selectCls}
					options={[
						{ value: "", label: "All statuses" },
						{ value: "pending", label: "Pending" },
						{ value: "running", label: "Running" },
						{ value: "completed", label: "Completed" },
						{ value: "completed_with_failures", label: "Completed w/ failures" },
						{ value: "failed", label: "Failed" },
					]}
				/>
				<Dropdown
					value={triggerFilter}
					onChange={setTriggerFilter}
					menuAppearance="light"
					width="trigger"
					triggerClassName={selectCls}
					options={[
						{ value: "", label: "All triggers" },
						{ value: "manual", label: "Manual" },
						{ value: "on_publish", label: "On Publish" },
						{ value: "on_modify", label: "On Modify" },
						{ value: "scheduled", label: "Scheduled" },
					]}
				/>
				<Dropdown
					value={typeFilter}
					onChange={setTypeFilter}
					menuAppearance="light"
					width="trigger"
					triggerClassName={selectCls}
					options={[
						{ value: "", label: "All types" },
						{ value: "workflow", label: "Workflow" },
						{ value: "agent", label: "Agent" },
						{ value: "model", label: "Model" },
						{ value: "tool", label: "Tool" },
					]}
				/>
				<Dropdown
					value={datePreset}
					onChange={(value) => {
						setDatePreset(value);
						if (value !== "custom") {
							setCustomFrom("");
							setCustomTo("");
						}
					}}
					menuAppearance="light"
					width="trigger"
					triggerClassName={selectCls}
					options={[
						{ value: "", label: "All time" },
						{ value: "24h", label: "Last 24 hours" },
						{ value: "7d", label: "Last 7 days" },
						{ value: "30d", label: "Last 30 days" },
						{ value: "90d", label: "Last 90 days" },
						{ value: "custom", label: "Custom range" },
					]}
				/>
				{datePreset === "custom" && (
					<>
						<input type="date" value={customFrom} onChange={(e) => setCustomFrom(e.target.value)} className={selectCls} />
						<span className="text-[10px] text-slate-400">to</span>
						<input type="date" value={customTo} onChange={(e) => setCustomTo(e.target.value)} className={selectCls} />
					</>
				)}
				{workflowOptions.length > 0 && (
					<Dropdown
						value={workflowFilter}
						onChange={setWorkflowFilter}
						menuAppearance="light"
						width="trigger"
						triggerClassName={selectCls}
						options={[
							{ value: "", label: "All workflows" },
							...workflowOptions.map((opt) => ({
								value: opt.id,
								label: opt.label,
							})),
						]}
					/>
				)}
				{datasetOptions.length > 0 && (
					<Dropdown
						value={datasetFilter}
						onChange={setDatasetFilter}
						menuAppearance="light"
						width="trigger"
						triggerClassName={selectCls}
						options={[
							{ value: "", label: "All datasets" },
							...datasetOptions.map((opt) => ({
								value: opt.id,
								label: opt.label,
							})),
						]}
					/>
				)}
			</div>
			{loading ? (
				<p className="py-6 text-center text-xs text-slate-500">Loading runs…</p>
			) : filteredRuns.length === 0 ? (
				<p className="py-6 text-center text-xs text-slate-500">No other runs found.</p>
			) : (
				<div className="max-h-64 overflow-y-auto rounded-lg border border-slate-200">
					<table className="w-full text-left text-xs">
						<thead className="sticky top-0 bg-[var(--color-bg-secondary,#1a1a2e)]">
							<tr className="border-b border-slate-200 text-[10px] uppercase text-slate-500">
								<th className="pl-8 pr-3 py-1.5">Name</th>
								<th className="px-3 py-1.5">Workflow</th>
								<th className="px-3 py-1.5">Version</th>
								<th className="px-3 py-1.5">Dataset</th>
								<th className="px-3 py-1.5">Type</th>
								<th className="px-3 py-1.5">Status</th>
								<th className="px-3 py-1.5">Score</th>
								<th className="px-3 py-1.5">Created</th>
							</tr>
						</thead>
						<tbody>
							{filteredRuns.map((r) => {
								const rWfId = getRunWorkflowId(r);
								const similar = isSimilar(r);
								return (
								<tr
									key={r.id}
									onClick={() => onSelect(r.id, r.name ?? r.id.slice(0, 8))}
									className={`cursor-pointer border-b border-slate-100 transition ${
										r.id === selectedId
											? "bg-[rgba(var(--color-primary-rgb),0.12)] ring-1 ring-inset ring-[rgba(var(--color-primary-rgb),0.3)]"
											: similar
												? "bg-emerald-500/[0.06] hover:bg-emerald-500/[0.12]"
												: "hover:bg-slate-100"
									}`}
								>
									<td className="px-3 py-2 text-slate-900">
										<span className="flex items-center gap-1.5">
											{similar && <GitCompareArrows size={12} className="shrink-0 text-emerald-400/70" />}
											{r.name ?? r.id.slice(0, 8)}
										</span>
									</td>
									<td className="px-3 py-2 text-slate-500 text-[11px]">{r.workflow_name ?? (rWfId ? (wfNameMap.get(rWfId) ?? rWfId.slice(0, 10)) : "—")}</td>
									<td className="px-3 py-2">{r.graph_version != null ? (<span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-mono text-slate-500">v{r.graph_version}</span>) : <span className="text-slate-400">—</span>}</td>
									<td className="px-3 py-2 text-slate-500 text-[11px]">{r.dataset_name ?? (r.dataset_id ? dsNameMap.get(r.dataset_id) : null) ?? "—"}</td>
									<td className="px-3 py-2">
										{r.target_type ? (
											<span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] capitalize text-slate-500">
												{r.target_type}
											</span>
										) : <span className="text-slate-400">—</span>}
									</td>
									<td className="px-3 py-2"><StatusBadge status={r.status} /></td>
									<td className="px-3 py-2"><ScoreBadge value={r.composite_score} label="C" /></td>
									<td className="px-3 py-2 text-slate-500">
										{r.created_at ? new Date(r.created_at).toLocaleDateString() : "—"}
									</td>
								</tr>
								);
							})}
						</tbody>
					</table>
				</div>
			)}
		</div>
	);
}
