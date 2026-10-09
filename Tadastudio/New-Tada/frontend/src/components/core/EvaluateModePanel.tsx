"use client";

import { formatDistanceToNow } from "date-fns";
import { FlaskConical, Loader2, X } from "lucide-react";
import React, { useCallback, useEffect, useRef, useState } from "react";
import type { Node } from "reactflow";
import {
	createRun,
	getLatestRun,
	getRun,
	getRunRecommendations,
	listDatasets,
	type EvaluationDataset,
	type EvaluationRecommendation,
	type EvaluationRun,
} from "@/lib/evaluation-api";

function scoreColor(score: number) {
	if (score >= 80) return { text: "text-[#0DA931]", bg: "bg-[#0DA931]/15" };
	if (score >= 60) return { text: "text-amber-400", bg: "bg-amber-500/15" };
	return { text: "text-red-400", bg: "bg-red-500/15" };
}

function riskBadge(tier: string) {
	switch (tier) {
		case "low":
			return "bg-[#0DA931]/15 text-[#0DA931]";
		case "medium":
			return "bg-amber-500/15 text-amber-400";
		case "high":
			return "bg-red-500/15 text-red-400";
		default:
			return "bg-zinc-500/15 text-zinc-400";
	}
}

interface EvaluateModePanelProps {
	workflowId: string | null;
	nodes: Node[];
	onClose: () => void;
	onNodeScoresLoaded: (scores: Record<string, number>) => void;
}

export default function EvaluateModePanel({
	workflowId,
	nodes,
	onClose,
	onNodeScoresLoaded,
}: EvaluateModePanelProps) {
	const [latestRun, setLatestRun] = useState<EvaluationRun | null>(null);
	const [datasets, setDatasets] = useState<EvaluationDataset[]>([]);
	const [recommendations, setRecommendations] = useState<
		EvaluationRecommendation[]
	>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [selectedDatasetId, setSelectedDatasetId] = useState("");
	const [concurrency, setConcurrency] = useState(1);
	const [runningState, setRunningState] = useState<{
		runId: string;
		completed: number;
		failed: number;
		total: number;
	} | null>(null);
	const [error, setError] = useState<string | null>(null);

	const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

	const fetchPanelData = useCallback(async () => {
		if (!workflowId) return;
		setIsLoading(true);
		setError(null);

		try {
			const [run, datasetList] = await Promise.all([
				getLatestRun(workflowId).catch(() => null),
				listDatasets("workflow").catch(() => []),
			]);

			setLatestRun(run);
			setDatasets(datasetList);

			if (datasetList.length > 0 && !selectedDatasetId) {
				setSelectedDatasetId(datasetList[0].id);
			}

			if (run?.id) {
				try {
					const recs = await getRunRecommendations(run.id);
					setRecommendations(recs);

					// Derive node scores from recommendations
					if (run.composite_score != null && recs.length > 0) {
						const nodeIds = new Set<string>();
						for (const rec of recs) {
							if (rec.target_node_id) {
								nodeIds.add(rec.target_node_id);
							}
						}
						if (nodeIds.size > 0) {
							const scores: Record<string, number> = {};
							for (const nid of nodeIds) {
								scores[nid] = run.composite_score;
							}
							onNodeScoresLoaded(scores);
						} else {
							onNodeScoresLoaded({});
						}
					} else {
						onNodeScoresLoaded({});
					}
				} catch {
					// recommendations endpoint may fail if no recs yet
					setRecommendations([]);
					onNodeScoresLoaded({});
				}
			} else {
				// No latest run — clear derived state
				setRecommendations([]);
				onNodeScoresLoaded({});
			}
		} catch (err: unknown) {
			setError(err instanceof Error ? err.message : "Failed to load evaluation data");
			setRecommendations([]);
			onNodeScoresLoaded({});
		} finally {
			setIsLoading(false);
		}
	}, [workflowId, selectedDatasetId, onNodeScoresLoaded]);

	useEffect(() => {
		fetchPanelData();
	}, [fetchPanelData]);

	// Reset derived state when workflowId changes
	useEffect(() => {
		setRecommendations([]);
		onNodeScoresLoaded({});
		setLatestRun(null);
	}, [workflowId, onNodeScoresLoaded]);

	// Cleanup polling on unmount
	useEffect(() => {
		return () => {
			if (pollIntervalRef.current) {
				clearInterval(pollIntervalRef.current);
			}
		};
	}, []);

	const handleQuickRun = useCallback(async () => {
		if (!workflowId || !selectedDatasetId) return;
		setError(null);

		try {
			const run = await createRun({
				workflow_id: workflowId,
				dataset_id: selectedDatasetId,
				trigger: "manual",
				target_type: "workflow",
				environment: "dev",
				concurrency_limit: concurrency,
			});

			setRunningState({
				runId: run.id,
				completed: 0,
				failed: 0,
				total: run.total_cases,
			});

			// Start polling
			pollIntervalRef.current = setInterval(async () => {
				try {
					const polled = await getRun(run.id);
					setRunningState((prev) =>
						prev
							? {
									...prev,
									completed: polled.completed_cases,
									failed: polled.failed_cases,
									total: polled.total_cases,
								}
							: null,
					);

					if (
						polled.status === "completed" ||
						polled.status === "completed_with_failures"
					) {
						if (pollIntervalRef.current) {
							clearInterval(pollIntervalRef.current);
							pollIntervalRef.current = null;
						}
						setRunningState(null);
						fetchPanelData();
					}
				} catch {
					// Ignore transient polling errors
				}
			}, 3000);
		} catch (err: unknown) {
			setError(err instanceof Error ? err.message : "Failed to start evaluation run");
		}
	}, [workflowId, selectedDatasetId, concurrency, fetchPanelData]);

	const pendingRecs = recommendations.filter((r) => r.status === "pending");

	// Pillar bar helper
	const PillarBar = ({
		label,
		value,
	}: { label: string; value: number | null | undefined }) => {
		const v = value ?? 0;
		const colors = scoreColor(v);
		return (
			<div className="flex items-center gap-2">
				<span className="w-20 text-xs text-slate-500 capitalize">
					{label}
				</span>
				<div className="flex-1 h-1.5 rounded-full bg-slate-200">
					<div
						className={`h-full rounded-full ${colors.bg}`}
						style={{
							width: `${Math.min(v, 100)}%`,
							backgroundColor:
								v >= 80
									? "rgb(13, 169, 49)"
									: v >= 60
										? "rgb(245, 158, 11)"
										: "rgb(239, 68, 68)",
						}}
					/>
				</div>
				<span className={`w-8 text-right text-xs font-medium ${colors.text}`}>
					{v > 0 ? Math.round(v) : "—"}
				</span>
			</div>
		);
	};

	return (
		<aside className="w-96 h-full flex flex-col border-l border-slate-200 bg-white overflow-y-auto">
			{/* Header */}
			<div className="flex items-center justify-between px-4 py-3 border-b border-black/10 bg-[rgb(249,115,22)]">
				<div className="flex items-center gap-2">
					<FlaskConical size={16} className="text-white" />
					<span className="text-sm font-semibold text-slate-900">Evaluate</span>
				</div>
				<div className="flex items-center gap-2">
					{workflowId && (
						<a
							href={`/evaluations?workflow_id=${workflowId}`}
							className="text-xs text-slate-800 hover:text-slate-900 transition-colors underline decoration-white/40 hover:decoration-white/70 underline-offset-2"
						>
							View full results &rarr;
						</a>
					)}
					<button
						onClick={onClose}
						className="p-1 rounded hover:bg-slate-100 transition-colors"
						aria-label="Close evaluate panel"
					>
						<X size={16} className="text-slate-800" />
					</button>
				</div>
			</div>

			{/* Loading skeleton */}
			{isLoading && (
				<div className="flex flex-col items-center justify-center py-12 gap-3">
					<Loader2 className="w-6 h-6 text-orange-600 animate-spin" />
					<span className="text-xs text-slate-500">
						Loading evaluation data...
					</span>
				</div>
			)}

			{/* Error */}
			{error && !isLoading && (
				<div className="px-4 py-3 border-b border-red-200 bg-red-50">
					<p className="text-xs text-red-700">{error}</p>
				</div>
			)}

			{/* Latest Score Card */}
			{latestRun && !isLoading && (
				<section className="px-4 py-4 border-b border-slate-200">
					<div className="flex items-start justify-between mb-3">
						<div>
							<div className="flex items-center gap-2">
								<span
									className={`text-3xl font-bold ${
										latestRun.composite_score != null
											? scoreColor(latestRun.composite_score).text
											: "text-slate-400"
									}`}
								>
									{latestRun.composite_score != null
										? Math.round(latestRun.composite_score)
										: "—"}
								</span>
								<span className="text-xs text-slate-500 mt-1">
									/ 100
								</span>
							</div>
							<p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1.5">
								<span>{latestRun.name || "Latest run"}</span>
								{latestRun.graph_version != null && (
									<span className="rounded border border-slate-200 bg-slate-50 px-1.5 py-px text-[10px] font-mono text-slate-500">
										v{latestRun.graph_version}
									</span>
								)}
							</p>
						</div>
						<div className="flex flex-col items-end gap-1">
							<span
								className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize tracking-wider ${
									latestRun.status === "completed"
										? "bg-[#0DA931]/15 text-[#0DA931]"
										: latestRun.status === "running"
											? "bg-blue-500/15 text-blue-400"
											: "bg-amber-500/15 text-amber-400"
								}`}
							>
								<span
									className={`h-1.5 w-1.5 rounded-full ${
										latestRun.status === "completed"
											? "bg-[#0DA931]"
											: latestRun.status === "running"
												? "bg-blue-400"
												: "bg-amber-400"
									}`}
								/>
								{latestRun.status}
							</span>
							{latestRun.created_at && (
								<span className="text-[10px] text-slate-500">
									{formatDistanceToNow(new Date(latestRun.created_at), {
										addSuffix: true,
									})}
								</span>
							)}
						</div>
					</div>

					<div className="flex flex-col gap-2">
						<PillarBar label="Quality" value={latestRun.quality_score} />
						<PillarBar label="Cost" value={latestRun.cost_score} />
						<PillarBar label="Reliability" value={latestRun.reliability_score} />
						<PillarBar label="Latency" value={latestRun.latency_score} />
					</div>
				</section>
			)}

			{/* Quick Run section */}
			{!isLoading && (
				<section className="px-4 py-4 border-b border-slate-200">
					<h3 className="text-xs font-semibold text-slate-700 capitalize tracking-wider mb-3">
						Run Evaluation
					</h3>

					<div className="flex flex-col gap-2 mb-3">
						<label className="text-xs text-slate-600">
							Dataset
						</label>
						<select
							value={selectedDatasetId}
							onChange={(e) => setSelectedDatasetId(e.target.value)}
							className="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
							disabled={!!runningState}
						>
							{datasets.length === 0 && (
								<option value="">No datasets available</option>
							)}
							{datasets.map((ds) => (
								<option key={ds.id} value={ds.id}>
									{ds.name} ({ds.test_case_count} cases)
								</option>
							))}
						</select>
					</div>

					<div className="flex flex-col gap-2 mb-3">
						<label className="text-xs text-slate-600">
							Concurrency
						</label>
						<select
							value={concurrency}
							onChange={(e) => setConcurrency(Number(e.target.value))}
							className="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
							disabled={!!runningState}
						>
							{[1, 2, 3, 4, 5].map((n) => (
								<option key={n} value={n}>
									{n}
								</option>
							))}
						</select>
					</div>

					{runningState && (
						<div className="mb-3 flex items-center gap-2">
							<Loader2
								size={14}
								className="text-orange-600 animate-spin flex-shrink-0"
							/>
							<span className="text-xs text-slate-700">
								Running... {runningState.completed}{runningState.failed ? `+${runningState.failed} failed` : ""}/{runningState.total} cases
							</span>
						</div>
					)}

					<button
						onClick={handleQuickRun}
						disabled={
							!selectedDatasetId || !!runningState || datasets.length === 0
						}
						className="w-full flex items-center justify-center gap-2 rounded-lg border border-orange-300 bg-orange-50 px-4 py-2 text-sm font-medium text-orange-800 transition-all hover:bg-orange-100 hover:border-orange-400 disabled:opacity-40 disabled:cursor-not-allowed"
					>
						<span>&#9889;</span> Quick Run
					</button>
				</section>
			)}

			{/* Top Recommendations */}
			{!isLoading && (
				<section className="px-4 py-4">
					<h3 className="text-xs font-semibold text-slate-700 capitalize tracking-wider mb-3">
						Recommendations
					</h3>

					{pendingRecs.length === 0 && (
						<p className="text-xs text-slate-500">
							{latestRun
								? "No pending recommendations."
								: "Run an evaluation to get recommendations."}
						</p>
					)}

					<div className="flex flex-col gap-2">
						{pendingRecs.slice(0, 3).map((rec) => (
							<div
								key={rec.id}
								className="rounded-lg border border-slate-200 bg-white p-3"
							>
								<div className="flex items-start justify-between gap-2 mb-1">
									<span className="text-xs font-medium text-slate-900 line-clamp-2">
										{rec.title}
									</span>
									<span
										className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize ${riskBadge(rec.risk_tier)}`}
									>
										{rec.risk_tier}
									</span>
								</div>
								{rec.expected_impact &&
									Object.keys(rec.expected_impact).length > 0 && (
										<p className="text-[10px] text-slate-500 mt-0.5">
											{[
												rec.expected_impact.quality_delta != null &&
													`Quality ${rec.expected_impact.quality_delta >= 0 ? "+" : ""}${Number(rec.expected_impact.quality_delta).toFixed(1)}`,
												rec.expected_impact.cost_delta != null &&
													`Cost ${rec.expected_impact.cost_delta >= 0 ? "+" : ""}${Number(rec.expected_impact.cost_delta).toFixed(1)}`,
												rec.expected_impact.latency_delta != null &&
													`Latency ${rec.expected_impact.latency_delta >= 0 ? "+" : ""}${Number(rec.expected_impact.latency_delta).toFixed(1)}`,
											]
												.filter(Boolean)
												.join(" · ")}
										</p>
									)}
								{rec.target_node_id && (
									<p className="text-[10px] text-slate-500">
										Node:{" "}
										{nodes.find((n) => n.id === rec.target_node_id)?.data
											?.name || rec.target_node_id}
									</p>
								)}
								{workflowId && latestRun && (
									<a
										href={`/evaluations?workflow_id=${workflowId}&run_id=${latestRun.id}`}
										className="text-[10px] text-orange-700 hover:text-slate-900 mt-1 inline-block"
									>
										View details &rarr;
									</a>
								)}
							</div>
						))}
					</div>
				</section>
			)}

			{/* Empty state */}
			{!latestRun && !isLoading && !error && (
				<div className="flex-1 flex flex-col items-center justify-center px-4 text-center">
					<FlaskConical
						size={32}
						className="text-orange-500/50 mb-3"
					/>
					<p className="text-sm text-slate-600">
						No evaluation runs yet.
					</p>
					<p className="text-xs text-slate-500 mt-1">
						Select a dataset and click Quick Run to get started.
					</p>
				</div>
			)}
		</aside>
	);
}
