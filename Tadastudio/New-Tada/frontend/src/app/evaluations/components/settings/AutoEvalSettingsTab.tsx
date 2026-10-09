"use client";

import { useEffect, useMemo, useState } from "react";
import { FileText, Loader2, Settings } from "lucide-react";
import Dropdown from "@/components/ui/Dropdown";
import { api } from "@/lib/api";
import * as evalApi from "@/lib/evaluation-api";
import type { AutoEvalConfig, EvaluationDataset } from "@/lib/evaluation-api";
import type { ModelDeploymentOption } from "@/lib/model-deployment-api";
import { buildModelDropdownOptions, ENVIRONMENT_OPTIONS } from "../shared/constants";
import EvalHelpButton from "../shared/EvalHelpButton";

type ConfigTab = "general" | "scoring-judge";

export default function AutoEvalSettingsTab({
	llmDeployments,
	modelsLoading,
}: {
	llmDeployments: ModelDeploymentOption[];
	modelsLoading: boolean;
}) {
	const modelOptions = useMemo(
		() => buildModelDropdownOptions(llmDeployments),
		[llmDeployments],
	);
	const [workflows, setWorkflows] = useState<{ name: string; workflow_id: string }[]>([]);
	const [datasets, setDatasets] = useState<EvaluationDataset[]>([]);
	const [selectedWorkflowId, setSelectedWorkflowId] = useState("");

	const [enabled, setEnabled] = useState(false);
	const [triggerOnPublish, setTriggerOnPublish] = useState(false);
	const [triggerOnModify, setTriggerOnModify] = useState(false);
	const [datasetId, setDatasetId] = useState("");
	const [environment, setEnvironment] = useState("dev");
	const [debounceMinutes, setDebounceMinutes] = useState(1);
	const [costW, setCostW] = useState(0.25);
	const [qualityW, setQualityW] = useState(0.25);
	const [reliabilityW, setReliabilityW] = useState(0.25);
	const [latencyW, setLatencyW] = useState(0.25);
	const [judgeModelId, setJudgeModelId] = useState("");
	const [qualityJudgeProvider, setQualityJudgeProvider] = useState<"builtin" | "phoenix">("builtin");
	const [judgeOutputStrategy, setJudgeOutputStrategy] = useState<"final_node" | "specific_node" | "all_nodes">("final_node");
	const [judgeOutputNodeId, setJudgeOutputNodeId] = useState("");
	const [allGraphNodes, setAllGraphNodes] = useState<{ id: string; name: string }[]>([]);
	const [judgeMaxOutputChars, setJudgeMaxOutputChars] = useState(200000);

	const [loading, setLoading] = useState(true);
	const [saving, setSaving] = useState(false);
	const [successMsg, setSuccessMsg] = useState<string | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [activeTab, setActiveTab] = useState<ConfigTab>("general");

	const weightsSum = costW + qualityW + reliabilityW + latencyW;
	const weightsValid = Math.abs(weightsSum - 1.0) <= 0.01;

	const rangeOrange = "rgb(234 88 12)";
	const rangeTrackGrey = "rgb(226 232 240)";
	const rangeStyle = (pct: number) =>
		({
			background: `linear-gradient(to right, ${rangeOrange} 0%, ${rangeOrange} ${pct}%, ${rangeTrackGrey} ${pct}%, ${rangeTrackGrey} 100%)`,
			accentColor: rangeOrange,
		}) as const;

	const selectBase =
		"w-full rounded-[4px] border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 transition-all hover:border-orange-400 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15";

	// Tutorial: select the tutorial workflow in auto-eval settings
	useEffect(() => {
		const handler = () => {
			const evalData = (window as any).__tutorialEvalData as { workflowName?: string } | undefined;
			if (!evalData?.workflowName) return;
			const wf = workflows.find((w) => w.name === evalData.workflowName);
			if (wf) setSelectedWorkflowId(wf.workflow_id);
		};
		window.addEventListener("tutorialSelectAutoEvalWorkflow", handler);
		return () => window.removeEventListener("tutorialSelectAutoEvalWorkflow", handler);
	}, [workflows]);

	// Load workflows and datasets on mount
	useEffect(() => {
		let cancelled = false;
		const load = async () => {
			setLoading(true);
			try {
				const [graphsRes, datasetsRes] = await Promise.all([
					api.listGraphs(),
					evalApi.listDatasets(),
				]);
				if (!cancelled) {
					const wfList = (graphsRes.graphs ?? []).map((g: { name: string; workflow_id: string }) => ({
						name: g.name,
						workflow_id: g.workflow_id,
					}));
					setWorkflows(wfList);
					setDatasets(datasetsRes);
				}
			} catch (err) {
				console.error("Failed to load settings data:", err);
			} finally {
				if (!cancelled) setLoading(false);
			}
		};
		load();
		return () => { cancelled = true; };
	}, []);

	const getDefaultWeight = (key: string) => Number(localStorage.getItem(`eval_default_weight_${key}`)) || 0.25;
	const getDefaultJudgeModel = () => localStorage.getItem("eval_default_judge_model") ?? "";
	const getDefaultJudgeStrategy = () => (localStorage.getItem("eval_default_judge_strategy") as "final_node" | "specific_node" | "all_nodes") || "final_node";
	const getDefaultMaxOutputChars = () => Number(localStorage.getItem("eval_default_max_output_chars")) || 200000;
	const getDefaultEnvironment = () => localStorage.getItem("eval_default_environment") ?? "dev";

	const resetToDefaults = () => {
		setEnabled(false);
		setTriggerOnPublish(false);
		setTriggerOnModify(false);
		setDatasetId("");
		setEnvironment(getDefaultEnvironment());
		setDebounceMinutes(1);
		setCostW(getDefaultWeight("cost"));
		setQualityW(getDefaultWeight("quality"));
		setReliabilityW(getDefaultWeight("reliability"));
		setLatencyW(getDefaultWeight("latency"));
		setJudgeModelId(getDefaultJudgeModel());
		setQualityJudgeProvider("builtin");
		setJudgeOutputStrategy(getDefaultJudgeStrategy());
		setJudgeOutputNodeId("");
		setAllGraphNodes([]);
		setJudgeMaxOutputChars(getDefaultMaxOutputChars());
	};

	// Load config when workflow selection changes
	useEffect(() => {
		if (!selectedWorkflowId) return;
		let cancelled = false;
		const loadConfig = async () => {
			try {
				const cfg = await evalApi.getAutoEvalConfig(selectedWorkflowId);
				if (cancelled) return;
				setEnabled(cfg.enabled ?? false);
				setTriggerOnPublish(cfg.trigger_on_publish ?? false);
				setTriggerOnModify(cfg.trigger_on_modify ?? false);
				setDatasetId(cfg.dataset_id ?? "");
				setEnvironment(cfg.environment ?? getDefaultEnvironment());
				setDebounceMinutes(Math.max(1, Math.round((cfg.debounce_window_seconds ?? 60) / 60)));
				const pw = cfg.pillar_weights ?? {};
				setCostW(pw.cost ?? getDefaultWeight("cost"));
				setQualityW(pw.quality ?? getDefaultWeight("quality"));
				setReliabilityW(pw.reliability ?? getDefaultWeight("reliability"));
				setLatencyW(pw.latency ?? getDefaultWeight("latency"));
				setJudgeModelId(
					(cfg.judge_model_config as Record<string, string> | null)?.model_deployment_id
					?? (cfg.judge_model_config as Record<string, string> | null)?.deployment_id
					?? getDefaultJudgeModel(),
				);
				setQualityJudgeProvider(cfg.quality_judge_provider === "phoenix" ? "phoenix" : "builtin");
				const jop = cfg.judge_output_policy ?? {};
				setJudgeOutputStrategy(
					jop.strategy === "all_nodes" ? "all_nodes"
					: jop.strategy === "specific_node" ? "specific_node"
					: jop.strategy === "final_node" ? "final_node"
					: getDefaultJudgeStrategy(),
				);
				setJudgeOutputNodeId(jop.node_id ?? "");
				setJudgeMaxOutputChars(jop.max_output_chars ?? getDefaultMaxOutputChars());
				setError(null);
			} catch {
				if (cancelled) return;
				resetToDefaults();
			}
			if (!cancelled) setSuccessMsg(null);
		};
		loadConfig();
		return () => { cancelled = true; };
	}, [selectedWorkflowId]);

	// Load graph nodes for specific_node judge output
	useEffect(() => {
		if (!selectedWorkflowId) {
			setAllGraphNodes([]);
			return;
		}
		let cancelled = false;
		api.getGraphByWorkflowId(selectedWorkflowId)
			.then((res) => {
				if (cancelled || !res.success) return;
				const nodes = res.graph.nodes || [];
				const nodeId = (n: any) => n.uniq_id || n.id;
				const excludeTypes = new Set(["START", "END", "CONDITION"]);
				setAllGraphNodes(
					nodes
						.filter((n: any) => !excludeTypes.has(n.type))
						.map((n: any) => ({ id: nodeId(n), name: n.name || nodeId(n) })),
				);
			})
			.catch(() => { if (!cancelled) setAllGraphNodes([]); });
		return () => { cancelled = true; };
	}, [selectedWorkflowId]);

	const handleSave = async () => {
		if (!selectedWorkflowId || !weightsValid) return;
		setSaving(true);
		setError(null);
		setSuccessMsg(null);
		try {
			const config: AutoEvalConfig = {
				enabled,
				trigger_on_publish: triggerOnPublish,
				trigger_on_modify: triggerOnModify,
				debounce_window_seconds: debounceMinutes * 60,
				dataset_id: datasetId || null,
				environment,
				pillar_weights: {
					cost: costW,
					quality: qualityW,
					reliability: reliabilityW,
					latency: latencyW,
				},
				quality_judge_provider: qualityJudgeProvider,
				judge_model_config: judgeModelId ? { model_deployment_id: judgeModelId } : null,
				judge_output_policy: {
					strategy: judgeOutputStrategy,
					...(judgeOutputStrategy === "specific_node" && judgeOutputNodeId ? { node_id: judgeOutputNodeId } : {}),
					max_output_chars: judgeMaxOutputChars,
				},
			};
			await evalApi.updateAutoEvalConfig(selectedWorkflowId, config);
			setSuccessMsg("Auto-evaluation settings saved.");
			setTimeout(() => setSuccessMsg(null), 3000);
		} catch (err: unknown) {
			setError(err instanceof Error ? err.message : "Failed to save settings.");
		} finally {
			setSaving(false);
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center py-20">
				<div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-orange-500" />
			</div>
		);
	}

	return (
		<div className="space-y-6">
			{/* Workflow Selector */}
			<div
				data-tutorial="auto-eval-workflow-selector"
				className="rounded-[4px] border border-slate-200 bg-white p-5 shadow-[0_18px_50px_rgba(15,23,42,0.08)] transition-colors hover:border-orange-400"
			>
				<div className="mb-4 flex items-center gap-3">
					<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
						<FileText className="h-5 w-5 text-orange-600" />
					</div>
					<div className="flex min-w-0 flex-1 items-center gap-2">
						<h3 className="text-base font-semibold tracking-tight text-slate-900">Configure Auto-Evaluation</h3>
						<EvalHelpButton topic="auto-eval-settings" appearance="light" />
					</div>
				</div>
				<div>
					<label className="mb-1 block text-xs font-medium text-slate-600">Workflow</label>
					<Dropdown
						value={selectedWorkflowId}
						onChange={(v) => setSelectedWorkflowId(v)}
						options={[
							{ value: "", label: "Select a workflow to configure" },
							...workflows.map((wf) => ({ value: wf.workflow_id, label: wf.name })),
						]}
						triggerClassName="w-full !rounded-[4px] !border-slate-200 !bg-white !px-3 !py-2 !text-sm !text-slate-900 hover:!border-orange-400"
					/>
					<p className="mt-1 text-xs text-slate-500">
						Enter the Workflow ID from the browser URL when viewing the workflow canvas.
					</p>
				</div>
			</div>

			{/* Config Form */}
			{selectedWorkflowId && (
				<div
					data-tutorial="auto-eval-config"
					className="space-y-5 rounded-[4px] border border-slate-200 bg-white p-5 shadow-[0_18px_50px_rgba(15,23,42,0.08)] transition-colors hover:border-orange-400 sm:p-6"
				>
					<div className="flex items-center gap-3 border-b border-slate-200 pb-4">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
							<Settings className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<p className="text-sm font-semibold text-slate-900">Workflow auto-evaluation</p>
							<p className="text-xs text-slate-600">Triggers, dataset, scoring, and judge options for this workflow.</p>
						</div>
					</div>

					{/* Tab bar */}
					<div className="flex gap-1 rounded-[4px] border border-slate-200 bg-white p-1">
						{(["general", "scoring-judge"] as const).map((t) => (
							<button
								key={t}
								type="button"
								onClick={() => setActiveTab(t)}
								className={`flex-1 rounded-[4px] px-3 py-1.5 text-xs font-medium transition-all ${
									activeTab === t
										? "bg-orange-500 text-white"
										: "text-slate-600 hover:text-slate-900"
								}`}
							>
								{t === "general" ? "General" : "Evaluations"}
								{t === "scoring-judge" && !weightsValid && (
									<span className="ml-1.5 inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
								)}
							</button>
						))}
					</div>

					{/* General tab */}
					{activeTab === "general" && (
						<div className="space-y-5">
							{/* Enable toggle */}
							<div className="flex items-center justify-between gap-4 rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm">
								<div>
									<p className="text-sm font-medium text-slate-900">Enable auto-evaluation</p>
									<p className="mt-0.5 text-xs text-slate-600">Automatically run evaluations when triggered</p>
								</div>
								<button
									type="button"
									role="switch"
									aria-checked={enabled}
									onClick={() => setEnabled((v) => !v)}
									className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
										enabled ? "bg-orange-500" : "bg-slate-200"
									}`}
								>
									<span
										className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${
											enabled ? "translate-x-6" : "translate-x-1"
										}`}
									/>
								</button>
							</div>

							{/* Trigger checkboxes */}
							<div className="rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm">
								<p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-600">Trigger on</p>
								<div className="space-y-2">
									<label className="flex cursor-pointer items-center gap-2 text-sm text-slate-800">
										<input
											type="checkbox"
											checked={triggerOnPublish}
											onChange={(e) => setTriggerOnPublish(e.target.checked)}
											className="accent-orange-500"
										/>
										Publish
									</label>
									<label className="flex cursor-pointer items-center gap-2 text-sm text-slate-800">
										<input
											type="checkbox"
											checked={triggerOnModify}
											onChange={(e) => setTriggerOnModify(e.target.checked)}
											className="accent-orange-500"
										/>
										Modify &amp; Save
									</label>
								</div>
							</div>

							{/* Dataset dropdown */}
							<div>
								<label className="mb-1 block text-xs font-medium text-slate-600">Default Dataset</label>
								<select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className={selectBase}>
									<option value="">No default dataset</option>
									{datasets.map((ds) => (
										<option key={ds.id} value={ds.id}>
											{ds.name} ({ds.test_case_count} cases)
										</option>
									))}
								</select>
							</div>

							{/* Environment */}
							<div>
								<label className="mb-1 block text-xs font-medium text-slate-600">Default Environment</label>
								<select value={environment} onChange={(e) => setEnvironment(e.target.value)} className={selectBase}>
									{ENVIRONMENT_OPTIONS.map((o) => (
										<option key={o.value} value={o.value}>
											{o.label}
										</option>
									))}
								</select>
							</div>

							{/* Debounce window */}
							<div className="rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm">
								<label className="mb-1 block text-xs font-medium text-slate-600">
									Debounce Window:{" "}
									{debounceMinutes >= 60
										? `${Math.floor(debounceMinutes / 60)}h${debounceMinutes % 60 ? ` ${debounceMinutes % 60}m` : ""}`
										: `${debounceMinutes}m`}
								</label>
								<input
									type="range"
									min={1}
									max={1440}
									step={1}
									value={debounceMinutes}
									onChange={(e) => setDebounceMinutes(Number(e.target.value))}
									className="w-full transition-all duration-200"
									style={rangeStyle(((debounceMinutes - 1) / 1439) * 100)}
								/>
								<div className="flex justify-between text-xs text-slate-500">
									<span>1 min</span>
									<span>24 hours</span>
								</div>
							</div>
						</div>
					)}

					{/* Evaluations tab */}
					{activeTab === "scoring-judge" && (
						<div className="space-y-5">
							{/* Pillar weights */}
							<div className="rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm">
								<p className="mb-2 text-xs font-medium text-slate-600">Pillar Weights (must sum to 1.0)</p>
								{!weightsValid && (
									<p className="mb-2 text-xs text-amber-700">
										Weights currently sum to {weightsSum.toFixed(2)} — must equal 1.0
									</p>
								)}
								<div className="grid grid-cols-2 gap-3">
									{([
										["Cost", costW, setCostW],
										["Quality", qualityW, setQualityW],
										["Reliability", reliabilityW, setReliabilityW],
										["Latency", latencyW, setLatencyW],
									] as [string, number, (v: number) => void][]).map(([label, value, setter]) => (
										<div key={label}>
											<label className="flex justify-between text-xs text-slate-600">
												<span>{label}</span>
												<span className="font-mono text-slate-800">{value.toFixed(2)}</span>
											</label>
											<input
												type="range"
												min={0}
												max={1}
												step={0.05}
												value={value}
												onChange={(e) => setter(Number(e.target.value))}
												className="w-full transition-all duration-200"
												style={rangeStyle(value * 100)}
											/>
										</div>
									))}
								</div>
							</div>

							{/* Quality Judge Provider */}
							<div>
								<p className="mb-1.5 text-xs font-medium text-slate-600">Quality Judge Provider</p>
								<div className="flex gap-1 rounded-[4px] border border-slate-200 bg-white p-1">
									{(["builtin", "phoenix"] as const).map((p) => (
										<button
											key={p}
											type="button"
											onClick={() => setQualityJudgeProvider(p)}
											className={`flex-1 rounded-[4px] px-3 py-1.5 text-xs font-medium transition-all ${
												qualityJudgeProvider === p
													? "bg-orange-500 text-white"
													: "text-slate-600 hover:text-slate-900"
											}`}
										>
											{p === "builtin" ? "Built-in Judge" : "Phoenix LLM Judge"}
										</button>
									))}
								</div>
								<p className="mt-1 text-[11px] text-slate-600">
									{qualityJudgeProvider === "builtin"
										? "Uses the built-in LLM-as-a-judge for quality scoring. Runs via LangChain."
										: "Uses Phoenix LLMEvaluator for quality scoring. Requires Phoenix to be enabled."}
								</p>
							</div>

							{/* Evaluations model */}
							<div>
								<label className="mb-1.5 block text-xs font-medium text-slate-600">Evaluations Model</label>
								{modelsLoading ? (
									<div className="flex items-center gap-2 rounded-[4px] border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
										<Loader2 className="h-3.5 w-3.5 animate-spin text-orange-600" />
										Loading models...
									</div>
								) : modelOptions.length > 0 ? (
									<Dropdown
										value={judgeModelId}
										onChange={setJudgeModelId}
										options={[{ value: "", label: "System Default", description: "Use the platform default model" }, ...modelOptions]}
										placeholder="System Default"
										className="w-full"
										menuAppearance="light"
										triggerClassName="!rounded-[4px] border border-slate-200 !bg-white hover:!border-orange-400 hover:!bg-white !text-slate-900 [&_span]:!text-slate-900 [&_p]:!text-slate-500"
										dropdownClassName="!rounded-[4px] !border-slate-200 !bg-white"
										optionClassName="hover:!bg-slate-50 hover:!text-orange-700 aria-selected:!bg-slate-50 aria-selected:!text-slate-900 [&_.font-semibold]:!text-slate-900"
									/>
								) : (
									<p className="rounded-[4px] border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
										No model deployments configured.
									</p>
								)}
								<p className="mt-1 text-[11px] text-slate-600">
									LLM used for quality judging and Phoenix evaluations. Leave empty for system default.
								</p>
							</div>

							{/* Judge Output Policy */}
							<div className="rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm">
								<p className="mb-2 text-xs font-medium text-slate-600">Judge Output Policy</p>
								<div className="space-y-3">
									<div>
										<label className="mb-1.5 block text-xs font-medium text-slate-600">What to evaluate</label>
										<select
											value={judgeOutputStrategy}
											onChange={(e) => {
												setJudgeOutputStrategy(e.target.value as any);
												if (e.target.value !== "specific_node") setJudgeOutputNodeId("");
											}}
											className={selectBase}
										>
											<option value="final_node">Final node output (recommended)</option>
											<option value="specific_node">Specific node output</option>
											<option value="all_nodes">All node outputs</option>
										</select>
										<p className="mt-1 text-[11px] text-slate-600">
											{judgeOutputStrategy === "final_node" &&
												"Sends only the last node\u2019s response to the judge. Best for most workflows."}
											{judgeOutputStrategy === "specific_node" &&
												"Sends the output of a specific node. Useful when the answer comes from a mid-workflow node."}
											{judgeOutputStrategy === "all_nodes" &&
												"Sends all node outputs. Uses more tokens but gives the judge full context."}
										</p>
									</div>

									{judgeOutputStrategy === "specific_node" && (
										<div>
											<label className="mb-1.5 block text-xs font-medium text-slate-600">Node to evaluate</label>
											{allGraphNodes.length > 0 ? (
												<select value={judgeOutputNodeId} onChange={(e) => setJudgeOutputNodeId(e.target.value)} className={selectBase}>
													<option value="">Select a node…</option>
													{allGraphNodes.map((n) => (
														<option key={n.id} value={n.id}>
															{n.name}
														</option>
													))}
												</select>
											) : (
												<p className="rounded-[4px] border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
													No nodes found in workflow
												</p>
											)}
										</div>
									)}
								</div>
							</div>

							{/* Max Output Chars */}
							<div>
								<label className="mb-1 flex items-center justify-between text-xs font-medium text-slate-600">
									<span>Max Output Chars for Judge</span>
									<span className="tabular-nums text-slate-800">
										{judgeMaxOutputChars >= 1000 ? `${Math.round(judgeMaxOutputChars / 1000)}k` : judgeMaxOutputChars}
									</span>
								</label>
								<input
									type="range"
									min={10000}
									max={500000}
									step={10000}
									value={judgeMaxOutputChars}
									onChange={(e) => setJudgeMaxOutputChars(Number(e.target.value))}
									className="w-full transition-all duration-200"
									style={rangeStyle(((judgeMaxOutputChars - 10000) / 490000) * 100)}
								/>
								<div className="flex justify-between text-[10px] text-slate-500">
									<span>10k</span>
									<span>200k (default)</span>
									<span>500k</span>
								</div>
								<p className="mt-1 text-[11px] text-slate-600">
									Truncation limit for output sent to the judge LLM. Prevents context length errors.
								</p>
							</div>
						</div>
					)}

					{/* Feedback */}
					{successMsg && <p className="text-sm font-medium text-emerald-700">{successMsg}</p>}
					{error && <p className="text-sm font-medium text-red-700">{error}</p>}

					{/* Actions */}
					<div className="flex items-center justify-end gap-2 border-t border-slate-200 pt-4">
						<button
							type="button"
							onClick={() => setSelectedWorkflowId("")}
							disabled={saving}
							className="rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-800 transition-all hover:border-orange-500 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 disabled:opacity-40"
						>
							Cancel
						</button>
						<button
							type="button"
							onClick={handleSave}
							disabled={saving || !selectedWorkflowId || !weightsValid}
							className="rounded-[4px] border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-all hover:border-orange-600 hover:bg-orange-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-orange-500"
						>
							{saving ? "Saving\u2026" : "Save Settings"}
						</button>
					</div>
				</div>
			)}
		</div>
	);
}
