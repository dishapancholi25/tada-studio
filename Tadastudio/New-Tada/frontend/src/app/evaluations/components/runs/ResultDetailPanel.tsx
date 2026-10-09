"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink } from "lucide-react";
import * as evalApi from "@/lib/evaluation-api";
import type { EvaluationResultDetail } from "@/lib/evaluation-api";
import { getPhoenixUrl, usePhoenixConfig } from "@/lib/phoenix-url";
import { ScoreBadge, StatusBadge } from "../shared/ScoreBadge";
import { PillarScoreCard, DiagnosticMetrics, MetricCard } from "./MetricCards";

export default function ResultDetailPanel({ resultId, onBack }: { resultId: string; onBack: () => void }) {
	const [detail, setDetail] = useState<EvaluationResultDetail | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const phoenixConfig = usePhoenixConfig();

	useEffect(() => {
		setLoading(true);
		setError(null);
		evalApi
			.getResultDetail(resultId)
			.then(setDetail)
			.catch((err: any) => setError(err.message ?? "Failed to load result detail"))
			.finally(() => setLoading(false));
	}, [resultId]);

	if (loading) return <p className="py-10 text-center text-sm text-slate-500">Loading result detail…</p>;
	if (error) return <p className="py-10 text-center text-sm text-red-400">{error}</p>;
	if (!detail) return null;

	const q = detail.quality_raw;
	const c = detail.cost_raw;
	const lat = detail.latency_raw;
	const rel = detail.reliability_raw;
	const gs = detail.guardrail_signals;
	const tc = detail.test_case;
	const exe = detail.execution_summary;

	return (
		<div className="space-y-6">
			{/* Back button */}
			<button
				type="button"
				onClick={onBack}
				className="flex items-center gap-1.5 text-sm text-slate-500 transition hover:text-slate-900"
			>
				<ArrowLeft size={14} /> Back to Results
			</button>

			{/* Score summary */}
			<div className="flex flex-wrap gap-2">
				<PillarScoreCard label="Composite" value={detail.composite_score} variant="compact" />
				<PillarScoreCard label="Quality" value={detail.quality_score} variant="compact" />
				<PillarScoreCard label="Reliability" value={detail.reliability_score} variant="compact" />
				<PillarScoreCard label="Latency" value={detail.latency_score} variant="compact" />
				<PillarScoreCard label="Cost" value={detail.cost_score} variant="compact" />
			</div>

			{/* Test Case */}
			{tc && (
				<div data-tutorial="result-test-case" className="rounded-xl border border-slate-200 bg-slate-50 p-4">
					<h3 className="mb-3 text-sm font-semibold text-slate-900">Test Case</h3>
					<div className="grid gap-4 md:grid-cols-2">
						<div>
							<p className="mb-1 text-xs text-slate-500">Input</p>
							<pre className="max-h-48 overflow-auto rounded-lg bg-slate-100 p-3 text-xs text-slate-700 whitespace-pre-wrap">
								{tc.input_data}
							</pre>
						</div>
						{tc.expected_output && (
							<div>
								<p className="mb-1 text-xs text-slate-500">Expected Output</p>
								<pre className="max-h-48 overflow-auto rounded-lg bg-slate-100 p-3 text-xs text-slate-700 whitespace-pre-wrap">
									{tc.expected_output}
								</pre>
							</div>
						)}
					</div>
				</div>
			)}

			{/* Execution Output */}
			{exe && (
				<div data-tutorial="result-execution-output" className="rounded-xl border border-slate-200 bg-slate-50 p-4">
					<div className="mb-3 flex items-center gap-3">
						<h3 className="text-sm font-semibold text-slate-900">Execution Output</h3>
						<StatusBadge status={exe.status} />
						{exe.duration_seconds != null && (
							<span className="text-xs text-slate-500">{exe.duration_seconds.toFixed(2)}s</span>
						)}
						{exe.id && (
							<a
								href={`/execution-viewer/${encodeURIComponent(exe.id)}`}
								target="_blank"
								rel="noopener noreferrer"
								className="ml-auto inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs text-slate-500 transition hover:border-slate-300 hover:text-slate-700"
							>
								View Trace <ExternalLink size={11} />
							</a>
						)}
						{(() => {
							const phoenixUrl = getPhoenixUrl(phoenixConfig, detail.trace_reference);
							return phoenixUrl ? (
								<a
									href={phoenixUrl}
									target="_blank"
									rel="noopener noreferrer"
									className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs text-slate-500 transition hover:border-slate-300 hover:text-slate-700"
								>
									View in Phoenix <ExternalLink size={11} />
								</a>
							) : null;
						})()}
					</div>
					{exe.output_data && (
						<div className="mb-3">
							<p className="mb-1 text-xs text-slate-500">Output (as seen by judge)</p>
							<pre className="max-h-64 overflow-auto rounded-lg bg-slate-100 p-3 text-xs text-slate-700 whitespace-pre-wrap">
								{typeof exe.output_data === "string" ? exe.output_data : JSON.stringify(exe.output_data, null, 2)}
							</pre>
						</div>
					)}
					{exe.error_message && (
						<div>
							<p className="mb-1 text-xs text-red-400/70">Error</p>
							<pre className="max-h-32 overflow-auto rounded-lg bg-red-500/5 p-3 text-xs text-red-400/80">
								{exe.error_message}
							</pre>
						</div>
					)}
				</div>
			)}

			{/* Quality Assessment */}
			{q && (
				<div data-tutorial="result-quality" className="rounded-xl border border-slate-200 bg-slate-50 p-4">
					<h3 className="mb-3 flex items-center gap-2.5 text-sm font-semibold text-slate-900">
						Quality <ScoreBadge value={detail.quality_score} showBar />
						{q.provider && (
							<span className={`ml-1 rounded-md px-1.5 py-0.5 text-[10px] font-medium ${
								q.provider === "phoenix"
									? "bg-violet-500/15 text-violet-400 border border-violet-500/30"
									: "bg-slate-50 text-slate-500 border border-slate-200"
							}`}>
								{q.provider === "phoenix" ? "Phoenix Judge" : "Built-in Judge"}
							</span>
						)}
						{q.fallback_reason && (
							<span className="text-[10px] text-amber-400/70">(fallback: {q.fallback_reason})</span>
						)}
					</h3>
					{q.judge_score != null && (
						<p className="mb-2 text-sm text-slate-700">
							Judge Score: <span className="font-semibold text-slate-900">{q.judge_score}</span>
						</p>
					)}
					{q.reasoning && (
						<div className="mb-3">
							<p className="mb-1 text-xs text-slate-500">Reasoning</p>
							<p className="rounded-lg bg-slate-100 p-3 text-sm leading-relaxed text-slate-600">{q.reasoning}</p>
						</div>
					)}
					{q.criteria_scores && Object.keys(q.criteria_scores).length > 0 && (
						<div className="space-y-2">
							<p className="text-xs text-slate-500">Per-Criterion Scores</p>
							{Object.entries(q.criteria_scores).map(([criterion, score]) => (
								<div key={criterion} className="flex items-center gap-3">
									<span className="w-44 truncate text-xs text-slate-600">{criterion}</span>
									<div className="flex-1 h-2 overflow-hidden rounded-full bg-slate-100">
										<div
											className={`h-full rounded-full ${(score ?? 0) >= 80 ? "bg-emerald-500" : (score ?? 0) >= 60 ? "bg-amber-500" : "bg-red-500"}`}
											style={{ width: `${Math.min(score ?? 0, 100)}%` }}
										/>
									</div>
									<span className="w-12 text-right text-xs font-medium text-slate-700">{score ?? "—"}</span>
								</div>
							))}
						</div>
					)}
					{q.diagnostics?.phoenix?.evaluations && (
						<div className="mt-3 space-y-2">
							<p className="text-xs text-slate-500">Phoenix Evaluations</p>
							{Object.entries(q.diagnostics.phoenix.evaluations as Record<string, any>).map(
								([name, ev]: [string, any]) => (
									<div key={name} className="rounded-lg border border-violet-500/20 bg-violet-500/5 p-3">
										<div className="flex items-center gap-2 mb-1">
											<span className="text-xs font-medium capitalize text-slate-700">
												{name.replace(/_/g, " ")}
											</span>
											{ev.score != null && <ScoreBadge value={Math.round(ev.score * 100)} />}
											{ev.label && (
												<span className="text-[10px] uppercase text-slate-500">{ev.label}</span>
											)}
										</div>
										{ev.explanation && (
											<p className="text-xs text-slate-500">{ev.explanation}</p>
										)}
									</div>
								),
							)}
						</div>
					)}
					<DiagnosticMetrics diagnostics={q.diagnostics} />
				</div>
			)}

			{/* Cost Assessment */}
			{c && (
				<div data-tutorial="result-cost" className="rounded-xl border border-slate-200 bg-slate-50 p-4">
					<h3 className="mb-3 flex items-center gap-2.5 text-sm font-semibold text-slate-900">Cost <ScoreBadge value={detail.cost_score} showBar /></h3>
					<div className="grid grid-cols-3 gap-3">
						<MetricCard label="Total Cost" value={c.total_cost != null ? `$${c.total_cost.toFixed(4)}` : null} />
						<MetricCard label="Input Tokens" value={c.input_tokens} />
						<MetricCard label="Output Tokens" value={c.output_tokens} />
					</div>
					<DiagnosticMetrics diagnostics={c.diagnostics} />
				</div>
			)}

			{/* Latency Assessment */}
			{lat && (
				<div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
					<h3 className="mb-3 flex items-center gap-2.5 text-sm font-semibold text-slate-900">Latency <ScoreBadge value={detail.latency_score} showBar /></h3>
					<div className="grid grid-cols-3 gap-3">
						<MetricCard label="Duration" value={lat.duration_seconds != null ? lat.duration_seconds.toFixed(2) : null} unit="s" />
						<MetricCard label="TTFT" value={lat.ttft_ms != null ? Math.round(lat.ttft_ms) : null} unit="ms" />
						<MetricCard label="Tokens/sec" value={lat.tokens_per_second != null ? lat.tokens_per_second.toFixed(1) : null} />
					</div>
					<DiagnosticMetrics diagnostics={lat.diagnostics} />
				</div>
			)}

			{/* Reliability Assessment */}
			{rel && (
				<div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
					<h3 className="mb-3 flex items-center gap-2.5 text-sm font-semibold text-slate-900">Reliability <ScoreBadge value={detail.reliability_score} showBar /></h3>
					<div className="grid grid-cols-3 gap-3">
						<MetricCard label="Success Rate" value={rel.success_rate != null ? `${Math.round(rel.success_rate * 100)}` : null} unit="%" />
						<MetricCard label="Nodes" value={rel.successful_nodes != null && rel.total_nodes != null ? `${rel.successful_nodes}/${rel.total_nodes}` : null} />
						<MetricCard label="Retries" value={rel.retry_count} />
					</div>
					<DiagnosticMetrics diagnostics={rel.diagnostics} />
				</div>
			)}

			{/* Guardrail Violations */}
			{gs?.signals && gs.signals.length > 0 && (
				<div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
					<h3 className="mb-3 text-sm font-semibold text-slate-900">
						Guardrail Violations
						{gs.total_violations != null && (
							<span className="ml-2 text-xs font-normal text-slate-500">({gs.total_violations} total)</span>
						)}
					</h3>
					<div className="space-y-2">
						{gs.signals.map((sig, i) => {
							const severityColors: Record<string, string> = {
								block: "border-red-500/30 bg-red-500/5",
								warn: "border-amber-500/30 bg-amber-500/5",
								info: "border-blue-500/30 bg-blue-500/5",
								low: "border-amber-500/30 bg-amber-500/5",
								medium: "border-orange-500/30 bg-orange-500/5",
								high: "border-red-500/30 bg-red-500/5",
								critical: "border-red-600/40 bg-red-600/10",
							};
							const severityLabels: Record<string, string> = {
								block: "Blocked",
								warn: "Warning",
								info: "Info",
							};
							return (
								<div
									key={`${sig.type}-${i}`}
									className={`rounded-lg border p-3 ${severityColors[sig.severity ?? ""] ?? "border-slate-200 bg-slate-50"}`}
								>
									<div className="flex items-center gap-2 mb-1">
										<span className="text-xs font-medium text-slate-700">{sig.type}</span>
										{sig.severity && (
											<span className="text-[10px] uppercase text-slate-500">
												{severityLabels[sig.severity] ?? sig.severity}
											</span>
										)}
										{sig.penalty != null && (
											<span className="text-[10px] text-slate-400">Quality impact: -{sig.penalty}</span>
										)}
									</div>
									{sig.message && <p className="text-xs text-slate-500">{sig.message}</p>}
								</div>
							);
						})}
					</div>
				</div>
			)}
		</div>
	);
}
