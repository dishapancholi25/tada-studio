"use client";

import { useEffect, useState } from "react";
import { ChevronRight, ExternalLink, ShieldAlert, ShieldCheck } from "lucide-react";
import type { EvaluationRun } from "@/lib/evaluation-api";
import { getPhoenixUrl, usePhoenixConfig } from "@/lib/phoenix-url";
import { ScoreBadge } from "../shared/ScoreBadge";
import ResultDetailPanel from "./ResultDetailPanel";

export default function RunDetailsSubTab({ run }: { run: EvaluationRun }) {
	const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
	const phoenixConfig = usePhoenixConfig();
	const showPhoenixColumn = !!phoenixConfig?.enabled;

	// Tutorial: click first result row to show detail panel
	useEffect(() => {
		const handler = () => {
			const firstResult = run.results?.[0];
			if (firstResult) setSelectedResultId(firstResult.id);
		};
		window.addEventListener("tutorialClickResultRow", handler);
		return () => window.removeEventListener("tutorialClickResultRow", handler);
	}, [run.results]);

	// If a result is selected, show its detail panel
	if (selectedResultId) {
		return <ResultDetailPanel resultId={selectedResultId} onBack={() => setSelectedResultId(null)} />;
	}

	return (
		<div className="space-y-6">
			{/* Per-case results — clickable */}
			{run.results && run.results.length > 0 ? (
				<div>
					<h3 className="mb-2 text-sm font-medium text-slate-600">Per-Case Results</h3>
					<table className="w-full text-left text-sm">
						<thead>
							<tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
								<th className="pb-2 pr-4">Case</th>
								<th className="pb-2 pr-4">Composite</th>
								<th className="pb-2 pr-4">Quality</th>
								<th className="pb-2 pr-4">Reliability</th>
								<th className="pb-2 pr-4">Latency</th>
								<th className="pb-2 pr-4">Cost</th>
								<th className="pb-2 pr-4">Guardrails</th>
								<th className="pb-2 pr-4">Trace</th>
								{showPhoenixColumn && <th className="pb-2 pr-4">Phoenix</th>}
								<th className="pb-2" />
							</tr>
						</thead>
						<tbody>
							{run.results.map((r) => (
								<tr
									key={r.id}
										data-tutorial={r.id === run.results?.[0]?.id ? "eval-result-first" : undefined}
									onClick={() => setSelectedResultId(r.id)}
									className="cursor-pointer border-b border-slate-100 transition hover:bg-slate-50"
								>
									<td className="py-2 pr-4 text-slate-600">{r.test_case_id?.slice(0, 8) ?? "—"}</td>
									<td className="py-2 pr-4">
										<ScoreBadge value={r.composite_score} label="C" />
									</td>
									<td className="py-2 pr-4">
										<ScoreBadge value={r.quality_score} label="Q" />
									</td>
									<td className="py-2 pr-4">
										<ScoreBadge value={r.reliability_score} label="R" />
									</td>
									<td className="py-2 pr-4">
										<ScoreBadge value={r.latency_score} label="L" />
									</td>
									<td className="py-2 pr-4">
										<ScoreBadge value={r.cost_score} label="$" />
									</td>
									<td className="py-2 pr-4">
										{r.guardrail_status === "blocked" ? (
											<span className="inline-flex items-center gap-1 rounded-md border border-red-500/30 bg-red-500/10 px-1.5 py-0.5 text-[10px] font-medium text-red-400" title={`${r.guardrail_violation_count} violation(s) blocked`}>
												<ShieldCheck size={11} />
												{r.guardrail_violation_count}
											</span>
										) : r.guardrail_status === "warned" ? (
											<span className="inline-flex items-center gap-1 rounded-md border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-400" title={`${r.guardrail_violation_count} violation(s) warned`}>
												<ShieldAlert size={11} />
												{r.guardrail_violation_count}
											</span>
										) : (
											<span className="text-xs text-slate-300">&mdash;</span>
										)}
									</td>
									<td className="py-2 pr-4">
										{r.graph_execution_id ? (
											<a
												href={`/execution-viewer/${encodeURIComponent(r.graph_execution_id)}`}
												target="_blank"
												rel="noopener noreferrer"
												onClick={(e) => e.stopPropagation()}
												className="inline-flex items-center gap-1 text-xs text-slate-500 transition hover:text-slate-700"
												title="View execution trace"
											>
												<ExternalLink size={12} />
											</a>
										) : (
											<span className="text-xs text-slate-300">—</span>
										)}
									</td>
									{showPhoenixColumn && (
									<td className="py-2 pr-4">
										{(() => {
											const phoenixUrl = getPhoenixUrl(phoenixConfig, r.trace_reference);
											return phoenixUrl ? (
												<a
													href={phoenixUrl}
													target="_blank"
													rel="noopener noreferrer"
													onClick={(e) => e.stopPropagation()}
													className="inline-flex items-center gap-1 text-xs text-slate-500 transition hover:text-slate-700"
													title="View in Phoenix"
												>
													<ExternalLink size={12} />
												</a>
											) : (
												<span className="text-xs text-slate-300">&mdash;</span>
											);
										})()}
									</td>
								)}
								<td className="py-2 text-right">
										<ChevronRight size={14} className="text-slate-300" />
									</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			) : (
				<p className="py-6 text-center text-sm text-slate-400">No per-case results available.</p>
			)}
		</div>
	);
}
