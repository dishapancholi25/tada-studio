"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Database, ExternalLink, GitBranch, RotateCw } from "lucide-react";
import { api } from "@/lib/api";
import * as evalApi from "@/lib/evaluation-api";
import type { EvaluationRun } from "@/lib/evaluation-api";
import { getPhoenixUrl, sanitizeProjectName, usePhoenixConfig, usePhoenixProjectUrl } from "@/lib/phoenix-url";
import { StatusBadge } from "../shared/ScoreBadge";
import { nextRerunName } from "../shared/constants";
import { PillarScoreCard } from "./MetricCards";
import RunDetailsSubTab from "./RunDetailsSubTab";
import CompareSubTab from "./CompareSubTab";
import RecommendationsSubTab from "./RecommendationsSubTab";
import EvalHelpButton from "../shared/EvalHelpButton";
import type { EvalHelpTopic } from "../shared/EvalHelpButton";

type RunSubTab = "details" | "recommendations" | "compare";

export default function RunDetailView({ runId, onBack }: { runId: string; onBack: () => void }) {
	const [run, setRun] = useState<EvaluationRun | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [activeSubTab, setActiveSubTab] = useState<RunSubTab>("details");
	const [isBaseline, setIsBaseline] = useState(false);
	const [settingBaseline, setSettingBaseline] = useState(false);
	const [baselineSuccess, setBaselineSuccess] = useState(false);
	const [workflowInfo, setWorkflowInfo] = useState<{ id: string; name: string } | null>(null);
	const [datasetInfo, setDatasetInfo] = useState<{ id: string; name: string } | null>(null);
	const phoenixConfig = usePhoenixConfig();
	// Derive the eval Phoenix project name from the workflow name (mirrors backend logic).
	// The backend uses the graph's display name (not the UUID target_id) when routing
	// spans to Phoenix, so we must resolve the same name here.
	const evalProjectName = workflowInfo?.name ? sanitizeProjectName(workflowInfo.name) : null;
	const resolvedPhoenixUrl = usePhoenixProjectUrl(phoenixConfig, evalProjectName);

	useEffect(() => {
		setLoading(true);
		setError(null);
		setActiveSubTab("details");
		setIsBaseline(false);
		setBaselineSuccess(false);
		setWorkflowInfo(null);
		setDatasetInfo(null);
		evalApi
			.getRun(runId)
			.then(setRun)
			.catch((err: any) => setError(err.message ?? "Failed to load run"))
			.finally(() => setLoading(false));
	}, [runId]);

	// Resolve workflow name from workflow_id or target_id (when target is workflow)
	useEffect(() => {
		const wfId = run?.workflow_id || (run?.target_type === "workflow" ? run?.target_id : null);
		if (!wfId) return;
		// Use backend-resolved name if available
		if (run?.workflow_name) {
			setWorkflowInfo({ id: wfId, name: run.workflow_name });
			return;
		}
		api
			.listGraphs()
			.then((res) => {
				const match = (res.graphs ?? []).find(
					(g: { workflow_id: string; name: string }) => g.workflow_id === wfId,
				);
				if (match) setWorkflowInfo({ id: wfId, name: match.name });
				else setWorkflowInfo({ id: wfId, name: wfId.slice(0, 12) });
			})
			.catch(() => {
				setWorkflowInfo({ id: wfId, name: wfId.slice(0, 12) });
			});
	}, [run?.workflow_id, run?.workflow_name, run?.target_id, run?.target_type]);

	// Resolve dataset name
	useEffect(() => {
		if (!run?.dataset_id) return;
		if (run.dataset_name) {
			setDatasetInfo({ id: run.dataset_id, name: run.dataset_name });
			return;
		}
		evalApi
			.getDataset(run.dataset_id)
			.then((ds) => setDatasetInfo({ id: run.dataset_id!, name: ds.name }))
			.catch(() => setDatasetInfo({ id: run.dataset_id!, name: run.dataset_id!.slice(0, 12) }));
	}, [run?.dataset_id, run?.dataset_name]);

	// Check if this run is the baseline for its dataset
	useEffect(() => {
		if (!run?.dataset_id || !run?.id) return;
		evalApi
			.getDataset(run.dataset_id)
			.then((dataset) => setIsBaseline(dataset.baseline_run_id === run.id))
			.catch(() => {});
	}, [run?.dataset_id, run?.id]);

	const handleSetBaseline = async () => {
		if (!run?.dataset_id || !run?.id) return;
		setSettingBaseline(true);
		try {
			await evalApi.setBaselineRun(run.dataset_id, run.id);
			setIsBaseline(true);
			setBaselineSuccess(true);
			setTimeout(() => setBaselineSuccess(false), 3000);
		} catch {
			// silently fail
		} finally {
			setSettingBaseline(false);
		}
	};

	const [confirmRerun, setConfirmRerun] = useState(false);
	const [rerunning, setRerunning] = useState(false);
	const [rerunError, setRerunError] = useState<string | null>(null);

	// Tutorial: switch sub-tab on request
	useEffect(() => {
		const handler = (e: Event) => {
			const tab = (e as CustomEvent).detail?.tab as RunSubTab | undefined;
			if (tab) setActiveSubTab(tab);
		};
		window.addEventListener("tutorialSwitchRunSubTab", handler);
		return () => window.removeEventListener("tutorialSwitchRunSubTab", handler);
	}, []);

	const handleRerun = async () => {
		if (!run) return;
		setRerunning(true);
		setRerunError(null);
		try {
			const body: evalApi.CreateRunBody = {
				name: nextRerunName(run.name),
				dataset_id: run.dataset_id ?? "",
				target_type: run.target_type ?? "workflow",
				trigger: "manual",
				environment: run.environment ?? "dev",
				pillar_weights: run.pillar_weights ?? undefined,
				concurrency_limit: run.concurrency_limit ?? undefined,
				judge_model_config: run.judge_model_config ?? undefined,
				judge_output_policy: run.judge_output_policy as evalApi.CreateRunBody["judge_output_policy"],
				external_integration_config: run.external_integration_config ?? undefined,
			};
			if (run.workflow_id) body.workflow_id = run.workflow_id;
			if (run.target_id) body.target_id = run.target_id;
			const rerunResult = await evalApi.createRun(body);
			// Stash rerun ID for tutorial cleanup
			const evalData = (window as any).__tutorialEvalData;
			if (evalData && rerunResult?.id) {
				evalData.rerunId = rerunResult.id;
			}
			setConfirmRerun(false);
			onBack();
		} catch (err: any) {
			setRerunError(err.message ?? "Failed to rerun evaluation");
		} finally {
			setRerunning(false);
		}
	};

	// Tutorial: trigger rerun directly (skipping confirmation modal)
	const handleRerunRef = useRef(handleRerun);
	handleRerunRef.current = handleRerun;
	useEffect(() => {
		const handler = () => handleRerunRef.current();
		window.addEventListener("tutorialTriggerRerun", handler);
		return () => window.removeEventListener("tutorialTriggerRerun", handler);
	}, []);

	if (loading) return <p className="rounded-2xl border border-slate-200 bg-white py-10 text-center text-sm text-slate-500 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">Loading run details…</p>;
	if (error) return <p className="py-10 text-center text-sm text-red-400">{error}</p>;
	if (!run) return null;

	const SUB_TABS: { id: RunSubTab; label: string }[] = [
		{ id: "details", label: "Details" },
		{ id: "recommendations", label: "Recommendations" },
		{ id: "compare", label: "Compare" },
	];

	return (
		<div className="space-y-5">
			{/* Back + header */}
			<button
				type="button"
				onClick={onBack}
				className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 transition hover:border-orange-400 hover:text-slate-900"
			>
				<ArrowLeft size={14} /> Back to Runs
			</button>

			<div className="flex flex-wrap items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
				<h2 className="text-lg font-semibold text-slate-900">{run.name ?? run.id.slice(0, 8)}</h2>
				<EvalHelpButton topic="run-detail" />
				<StatusBadge status={run.status} />
				{run.regression_severity && (
					<span className="inline-flex items-center rounded-full border border-red-400/45 bg-red-400/12 px-2.5 py-0.5 text-[11px] font-medium text-red-300">
						Regression: {run.regression_severity}
					</span>
				)}
				{isBaseline && (
					<span className="inline-flex items-center rounded-full border border-emerald-400/45 bg-emerald-400/12 px-2.5 py-0.5 text-[11px] font-medium text-emerald-600">
						✓ Baseline
					</span>
				)}
				{!isBaseline && run.dataset_id && (
					<button
						type="button"
						onClick={handleSetBaseline}
						disabled={settingBaseline}
						title="Pin this run as the baseline for its dataset. Future runs will be compared against it to detect regressions and improvements."
						className="rounded-xl border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 disabled:opacity-40"
					>
						{settingBaseline ? "Setting…" : "Set as Baseline"}
					</button>
				)}
				{baselineSuccess && (
					<span className="text-xs text-emerald-400">Baseline pinned ✓</span>
				)}
				<button
					type="button"
					data-tutorial="eval-rerun-btn"
					onClick={() => setConfirmRerun(true)}
					title="Rerun this evaluation with the same configuration"
					className="rounded-xl border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 inline-flex items-center gap-1.5"
				>
					<RotateCw size={12} /> Rerun
				</button>
			</div>

			{/* Workflow & Dataset info */}
			{(workflowInfo || datasetInfo) && (
				<div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-2 text-sm flex-wrap shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
					{workflowInfo && (
						<div className="flex items-center gap-1.5">
							<GitBranch size={13} className="text-slate-400 shrink-0" />
							<span className="text-xs text-slate-500">Workflow</span>
							<a
								href={`/workflow/${encodeURIComponent(workflowInfo.id)}${run.graph_version != null && run.graph_definition_id ? `?version=${run.graph_version}&graph_definition_id=${run.graph_definition_id}` : ""}`}
								target="_blank"
								rel="noopener noreferrer"
								className="inline-flex items-center gap-1 font-medium text-[rgba(var(--color-primary-rgb),0.85)] transition hover:text-[rgba(var(--color-primary-rgb),1)] hover:underline"
								title={run.graph_version != null ? `Open version ${run.graph_version} in editor` : "Open in editor"}
							>
								{workflowInfo.name}
								<ExternalLink size={11} />
							</a>
							{run.graph_version != null && (
								<span className="rounded-full border border-slate-200 bg-white px-1.5 py-0.5 text-[11px] font-mono text-slate-600">
									v{run.graph_version}
								</span>
							)}
						</div>
					)}
					{workflowInfo && datasetInfo && (
						<span className="text-slate-300">|</span>
					)}
					{datasetInfo && (
						<div className="flex items-center gap-1.5">
							<Database size={13} className="text-slate-400 shrink-0" />
							<span className="text-xs text-slate-500">Dataset</span>
							<a
								href={`/evaluations?tab=datasets&dataset=${encodeURIComponent(datasetInfo.id)}`}
								className="inline-flex items-center gap-1 font-medium text-[rgba(var(--color-primary-rgb),0.85)] transition hover:text-[rgba(var(--color-primary-rgb),1)] hover:underline"
								title="Open dataset"
							>
								{datasetInfo.name}
								<ExternalLink size={11} />
							</a>
							{run.total_cases > 0 && (
								<span className="rounded-full border border-slate-200 bg-white px-1.5 py-0.5 text-[11px] text-slate-600">
									{run.completed_cases ?? 0}{run.failed_cases ? <span className="text-red-400/70">+{run.failed_cases}err</span> : ""}/{run.total_cases} cases
								</span>
							)}
						</div>
					)}
					{(() => {
						const runPhoenixUrl = getPhoenixUrl(phoenixConfig, run.external_eval_summary) ?? resolvedPhoenixUrl;
						if (!runPhoenixUrl) return null;
						return (
							<>
								{(workflowInfo || datasetInfo) && <span className="text-slate-300">|</span>}
								<div className="flex items-center gap-1.5">
									<a
										href={runPhoenixUrl}
										target="_blank"
										rel="noopener noreferrer"
										className="inline-flex items-center gap-1 font-medium text-[rgba(var(--color-primary-rgb),0.85)] transition hover:text-[rgba(var(--color-primary-rgb),1)] hover:underline"
										title="View in Phoenix"
									>
										Phoenix
										<ExternalLink size={11} />
									</a>
								</div>
							</>
						);
					})()}
				</div>
			)}

			{/* Pillar score cards — always visible */}
			<div data-tutorial="eval-score-cards" className="grid grid-cols-2 gap-4 px-4 sm:grid-cols-3 lg:grid-cols-5">
				<PillarScoreCard label="Composite" value={run.composite_score} />
				<PillarScoreCard label="Quality" value={run.quality_score} />
				<PillarScoreCard label="Reliability" value={run.reliability_score} />
				<PillarScoreCard label="Latency" value={run.latency_score} />
				<PillarScoreCard label="Cost" value={run.cost_score} />
			</div>

			{/* Sub-tab bar */}
			<div className="flex items-center gap-2 flex-wrap rounded-2xl border border-slate-200 bg-white p-3 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
				{SUB_TABS.map((tab) => (
					<button
						key={tab.id}
						type="button"
						data-tutorial={tab.id === "details" ? "eval-details-tab" : tab.id === "recommendations" ? "eval-recommendations-tab" : tab.id === "compare" ? "eval-compare-tab" : undefined}
						onClick={() => setActiveSubTab(tab.id)}
						className={`px-4 py-2 rounded-xl text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] ${
							activeSubTab === tab.id
								? "border border-orange-500 bg-orange-500 text-white"
								: "border border-slate-200 bg-white text-slate-600 hover:text-slate-900 hover:border-orange-400 hover:bg-white"
						}`}
					>
						{tab.label}
					</button>
				))}
				<div className="ml-auto">
					<EvalHelpButton topic={({ details: "run-details-tab", recommendations: "run-recommendations-tab", compare: "run-compare-tab" } as Record<RunSubTab, EvalHelpTopic>)[activeSubTab]} />
				</div>
			</div>

			{/* Sub-tab content */}
			<div data-tutorial="eval-details-section">{activeSubTab === "details" && <RunDetailsSubTab run={run} />}</div>
			<div data-tutorial="eval-recommendations-section">{activeSubTab === "recommendations" && <RecommendationsSubTab runId={run.id} workflowId={run.workflow_id} />}</div>
			<div data-tutorial="eval-compare-section">{activeSubTab === "compare" && <CompareSubTab run={run} />}</div>

			{confirmRerun && (
				<div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
					<div className="relative w-full max-w-sm overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
						<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
						<h3 className="mb-2 text-base font-semibold text-slate-900">Rerun Evaluation</h3>
						<p className="mb-6 text-sm text-slate-600">
							This will create a new evaluation run using the same dataset, workflow, and target configuration. Continue?
						</p>
						{rerunError && <p className="mb-4 text-sm text-red-400">{rerunError}</p>}
						<div className="flex justify-end gap-2">
							<button
								type="button"
								onClick={() => { setConfirmRerun(false); setRerunError(null); }}
								disabled={rerunning}
								className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 disabled:opacity-40"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={handleRerun}
								disabled={rerunning}
								className="rounded-xl border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-all hover:border-orange-600 hover:bg-orange-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 disabled:opacity-40"
							>
								{rerunning ? "Starting…" : "Rerun"}
							</button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}
