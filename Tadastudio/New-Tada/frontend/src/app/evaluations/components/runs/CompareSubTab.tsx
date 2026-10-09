"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Database, GitBranch } from "lucide-react";
import { api } from "@/lib/api";
import * as evalApi from "@/lib/evaluation-api";
import type { EvaluationRun, RunCompareResponse } from "@/lib/evaluation-api";
import { ScoreBadge } from "../shared/ScoreBadge";
import CompareRunPicker from "./CompareRunPicker";

export default function CompareSubTab({ run }: { run: EvaluationRun }) {
	const [peerRunId, setPeerRunId] = useState("");
	const [peerRunName, setPeerRunName] = useState("");
	const [compareResult, setCompareResult] = useState<RunCompareResponse | null>(null);
	const [comparing, setComparing] = useState(false);
	const [wfNames, setWfNames] = useState<Map<string, string>>(new Map());
	const [dsNames, setDsNames] = useState<Map<string, string>>(new Map());

	// Pre-fetch all workflow and dataset names on mount so they're ready when compare results arrive
	useEffect(() => {
		api.listGraphs().then((res: any) => {
			const m = new Map<string, string>();
			for (const g of (res.graphs ?? []) as { workflow_id: string; name: string }[]) {
				if (g.workflow_id) m.set(g.workflow_id, g.name);
			}
			setWfNames(m);
		}).catch(() => {});
		evalApi.listDatasets().then((datasets) => {
			const m = new Map<string, string>();
			for (const d of datasets) m.set(d.id, d.name);
			setDsNames(m);
		}).catch(() => {});
	}, []);

	const handleSelectPeer = (id: string, name: string) => {
		setPeerRunId(id);
		setPeerRunName(name);
		setCompareResult(null);
	};

	const handleCompare = async () => {
		if (!peerRunId) return;
		setComparing(true);
		try {
			const result = await evalApi.compareRuns(run.id, peerRunId);
			setCompareResult(result);
		} catch {
			// silently fail
		} finally {
			setComparing(false);
		}
	};

	// Tutorial: auto-select a peer run and trigger comparison
	useEffect(() => {
		const handler = (e: Event) => {
			const detail = (e as CustomEvent).detail ?? {};
			const peerId = detail.peerRunId ?? (window as any).__tutorialEvalData?.runId;
			if (peerId && peerId !== run.id) {
				setPeerRunId(peerId);
				setPeerRunName(detail.peerRunName ?? "Tutorial Baseline Run");
				// Auto-trigger compare after state settles
				setTimeout(async () => {
					setComparing(true);
					try {
						const result = await evalApi.compareRuns(run.id, peerId);
						setCompareResult(result);
					} catch {
						// silently fail
					} finally {
						setComparing(false);
					}
				}, 100);
			}
		};
		window.addEventListener("tutorialSelectComparePeer", handler);
		return () => window.removeEventListener("tutorialSelectComparePeer", handler);
	}, [run.id]);

	return (
		<div className="space-y-4 px-4">
			{!compareResult && (
				<>
					<h3 className="text-sm font-medium text-slate-600">Select a run to compare</h3>
					<div data-tutorial="compare-run-picker">
						<CompareRunPicker currentRun={run} selectedId={peerRunId} onSelect={handleSelectPeer} />
					</div>
					{peerRunId && (
						<div className="flex items-center gap-3">
							<span className="text-xs text-slate-500">
								Selected: <span className="text-slate-900">{peerRunName}</span>
							</span>
							<button
								type="button"
								data-tutorial="compare-btn"
								onClick={handleCompare}
								disabled={comparing}
								className="rounded-lg bg-[rgba(var(--color-primary-rgb),0.25)] px-4 py-1.5 text-sm font-medium text-slate-900 transition hover:bg-[rgba(var(--color-primary-rgb),0.35)] disabled:opacity-40"
							>
								{comparing ? "Comparing…" : "Compare"}
							</button>
						</div>
					)}
				</>
			)}
			{compareResult && (
				<button
					type="button"
					onClick={() => { setCompareResult(null); setPeerRunId(""); }}
					className="flex items-center gap-1.5 text-sm text-slate-500 transition hover:text-slate-900"
				>
					<ArrowLeft size={14} /> Pick a different run
				</button>
			)}

			{/* Comparison results table */}
			{compareResult && (
				<div data-tutorial="compare-results" className="rounded-xl border border-slate-200 bg-slate-50 p-4">
					<div className="mb-3 flex items-center gap-3">
						<h4 className="text-sm font-semibold text-slate-900">Comparison Results</h4>
						{compareResult.winner && (
							<span className="inline-flex items-center rounded-full border border-emerald-400/45 bg-emerald-400/12 px-2.5 py-0.5 text-[11px] font-medium text-emerald-600">
								Winner: {compareResult.winner === run.id ? "Run A" : "Run B"}
								{" "}({(() => {
									const w = compareResult.winner === run.id ? compareResult.run_a : compareResult.run_b;
									const wfId = w.workflow_id || (w.target_type === "workflow" ? w.target_id : null);
									return w.workflow_name ?? (wfId ? (wfNames.get(wfId) ?? null) : null) ?? w.name ?? wfId?.slice(0, 8) ?? w.id.slice(0, 8);
								})()})
							</span>
						)}
					</div>
					{/* Run metadata: workflow, dataset, version */}
					<div className="mb-3 grid grid-cols-2 gap-3 text-xs">
						{[
							{ label: "Run A", r: compareResult.run_a },
							{ label: "Run B", r: compareResult.run_b },
						].map(({ label, r }) => {
							const wfId = r.workflow_id || (r.target_type === "workflow" ? r.target_id : null);
							const wfName = r.workflow_name ?? (wfId ? (wfNames.get(wfId) ?? null) : null);
							const dsName = r.dataset_name ?? (r.dataset_id ? dsNames.get(r.dataset_id) : null) ?? null;
							return (
								<div key={label} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 space-y-1">
									<div>
										<span className="text-slate-500">{label}:</span>{" "}
										<span className="text-slate-900">{r.name ?? r.id.slice(0, 8)}</span>
									</div>
									{wfId && (
										<div className="flex items-center gap-1.5 text-slate-500">
											<GitBranch size={10} className="shrink-0" />
											<span>{wfName ?? wfId.slice(0, 12) + "…"}</span>
											{r.graph_version != null && (
												<span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-mono text-slate-500">v{r.graph_version}</span>
											)}
										</div>
									)}
									{!wfId && r.graph_version != null && (
										<div className="flex items-center gap-1.5 text-slate-500">
											<span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-mono text-slate-500">v{r.graph_version}</span>
										</div>
									)}
									{dsName && (
										<div className="flex items-center gap-1.5 text-slate-500">
											<Database size={10} className="shrink-0" />
											<span>{dsName}</span>
										</div>
									)}
								</div>
							);
						})}
					</div>
					{compareResult.winner_reason && (
						<p className="mb-3 text-xs text-slate-500">{compareResult.winner_reason}</p>
					)}
					<table className="w-full text-left text-sm">
						<thead>
							<tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
								<th className="pb-2 pr-4">Pillar</th>
								<th className="pb-2 pr-4">Run A</th>
								<th className="pb-2 pr-4">Run B</th>
								<th className="pb-2 pr-4">Delta</th>
								<th className="pb-2">Winner</th>
							</tr>
						</thead>
						<tbody>
							{(
								[
									{ key: "composite_score", label: "Composite", aVal: compareResult.run_a.composite_score, bVal: compareResult.run_b.composite_score },
									{ key: "quality_score", label: "Quality", aVal: compareResult.run_a.quality_score, bVal: compareResult.run_b.quality_score },
									{ key: "reliability_score", label: "Reliability", aVal: compareResult.run_a.reliability_score, bVal: compareResult.run_b.reliability_score },
									{ key: "latency_score", label: "Latency", aVal: compareResult.run_a.latency_score, bVal: compareResult.run_b.latency_score },
									{ key: "cost_score", label: "Cost", aVal: compareResult.run_a.cost_score, bVal: compareResult.run_b.cost_score },
								] as const
							).map(({ key, label, aVal, bVal }) => {
								const delta = compareResult.delta[key];
								const deltaStr =
									delta != null
										? delta > 0
											? `+${Math.round(delta)}%`
											: `${Math.round(delta)}%`
										: "—";
								const deltaColor =
									delta != null && delta > 0
										? "text-emerald-400"
										: delta != null && delta < 0
											? "text-red-400"
											: "text-slate-500";
								const arrow =
									delta != null && delta > 0
										? " ↑"
										: delta != null && delta < 0
											? " ↓"
											: "";
								const pillarWinner =
									aVal != null && bVal != null
										? aVal > bVal
											? "A"
											: bVal > aVal
												? "B"
												: "Tie"
										: "—";
								const winnerColor =
									pillarWinner === "A"
										? "text-blue-400"
										: pillarWinner === "B"
											? "text-emerald-400"
											: "text-slate-500";
								return (
									<tr key={key} className="border-b border-slate-100">
										<td className="py-2 pr-4 text-slate-700">{label}</td>
										<td className="py-2 pr-4">
											<ScoreBadge value={aVal} label="A" />
										</td>
										<td className="py-2 pr-4">
											<ScoreBadge value={bVal} label="B" />
										</td>
										<td className={`py-2 pr-4 text-xs font-medium ${deltaColor}`}>
											{deltaStr}{arrow}
										</td>
										<td className={`py-2 text-xs font-medium ${winnerColor}`}>
											{pillarWinner}
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
