"use client";

import { useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import Dropdown, { type DropdownOption } from "@/components/ui/Dropdown";
import type { ModelDeploymentOption } from "@/lib/model-deployment-api";
import { buildModelDropdownOptions, ENVIRONMENT_OPTIONS } from "../shared/constants";
import EvalHelpButton from "../shared/EvalHelpButton";

type SettingsTab = "general" | "scoring-judge";

export default function EvalGeneralSettings({
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

	const [activeTab, setActiveTab] = useState<SettingsTab>("general");

	const [defaultJudgeModel, setDefaultJudgeModel] = useState(
		() => (typeof window !== "undefined" && localStorage.getItem("eval_default_judge_model")) || "",
	);
	const [defaultGenModel, setDefaultGenModel] = useState(
		() => (typeof window !== "undefined" && localStorage.getItem("eval_default_gen_model")) || "",
	);
	const [defaultConcurrency, setDefaultConcurrency] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_default_concurrency")) || 5,
	);
	const [defaultEnvironment, setDefaultEnvironment] = useState(
		() => (typeof window !== "undefined" && localStorage.getItem("eval_default_environment")) || "dev",
	);
	const [maxDatasetSize, setMaxDatasetSize] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_max_dataset_size")) || 200,
	);
	const [defaultJudgeStrategy, setDefaultJudgeStrategy] = useState(
		() => (typeof window !== "undefined" && localStorage.getItem("eval_default_judge_strategy")) || "final_node",
	);
	const [defaultMaxOutputChars, setDefaultMaxOutputChars] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_default_max_output_chars")) || 200000,
	);
	const [defaultQualityJudgeProvider, setDefaultQualityJudgeProvider] = useState<"builtin" | "phoenix">(
		() => ((typeof window !== "undefined" && localStorage.getItem("eval_default_quality_judge_provider")) === "phoenix" ? "phoenix" : "builtin"),
	);
	const [defaultCostW, setDefaultCostW] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_default_weight_cost")) || 0.25,
	);
	const [defaultQualityW, setDefaultQualityW] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_default_weight_quality")) || 0.25,
	);
	const [defaultReliabilityW, setDefaultReliabilityW] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_default_weight_reliability")) || 0.25,
	);
	const [defaultLatencyW, setDefaultLatencyW] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_default_weight_latency")) || 0.25,
	);
	const defaultWeightSum = defaultCostW + defaultQualityW + defaultReliabilityW + defaultLatencyW;
	const defaultWeightsValid = Math.abs(defaultWeightSum - 1.0) <= 0.01;
	const [saved, setSaved] = useState(false);

	const handleSave = () => {
		localStorage.setItem("eval_default_judge_model", defaultJudgeModel);
		localStorage.setItem("eval_default_gen_model", defaultGenModel);
		localStorage.setItem("eval_default_concurrency", String(defaultConcurrency));
		localStorage.setItem("eval_default_environment", defaultEnvironment);
		localStorage.setItem("eval_max_dataset_size", String(maxDatasetSize));
		localStorage.setItem("eval_default_judge_strategy", defaultJudgeStrategy);
		localStorage.setItem("eval_default_max_output_chars", String(defaultMaxOutputChars));
		localStorage.setItem("eval_default_weight_cost", String(defaultCostW));
		localStorage.setItem("eval_default_weight_quality", String(defaultQualityW));
		localStorage.setItem("eval_default_weight_reliability", String(defaultReliabilityW));
		localStorage.setItem("eval_default_weight_latency", String(defaultLatencyW));
		localStorage.setItem("eval_default_quality_judge_provider", defaultQualityJudgeProvider);
		setSaved(true);
		setTimeout(() => setSaved(false), 2500);
	};

	const envOptions: DropdownOption[] = ENVIRONMENT_OPTIONS.map((o) => ({ value: o.value, label: o.label }));

	const rangeOrange = "rgb(234 88 12)";
	const rangeTrackGrey = "rgb(226 232 240)";
	const rangeStyle = (pct: number) => ({
		background: `linear-gradient(to right, ${rangeOrange} 0%, ${rangeOrange} ${pct}%, ${rangeTrackGrey} ${pct}%, ${rangeTrackGrey} 100%)`,
		accentColor: rangeOrange,
	} as const);

	return (
		<div className="flex flex-col min-h-[calc(100dvh-14rem)] rounded-2xl border border-slate-200 bg-white p-6 pb-10 shadow-[0_18px_50px_rgba(15,23,42,0.08)] sm:p-8 sm:pb-10">
			<div className="space-y-5">
				<div>
					<div className="flex items-center gap-2">
						<h3 className="text-base font-semibold text-slate-900">General Defaults</h3>
						<EvalHelpButton topic="general-settings" />
					</div>
					<p className="mt-1 text-xs text-slate-500">
						These defaults pre-fill forms when creating runs or generating test cases. Per-workflow settings override these.
					</p>
				</div>

				{/* Tab bar */}
				<div className="flex gap-1 rounded-lg border border-slate-200 bg-white p-1">
					{(["general", "scoring-judge"] as const).map((t) => (
						<button
							key={t}
							type="button"
							onClick={() => setActiveTab(t)}
							className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
								activeTab === t
									? "bg-orange-500 text-white"
									: "text-slate-600 hover:text-slate-900"
							}`}
						>
							{t === "general" ? "General" : "Evaluations"}
							{t === "scoring-judge" && !defaultWeightsValid && (
								<span className="ml-1.5 inline-block h-1.5 w-1.5 rounded-full bg-amber-400" />
							)}
						</button>
					))}
				</div>

				{/* General tab */}
				{activeTab === "general" && (
					<div className="space-y-5">
					{/* Default Environment */}
					<div>
						<label className="mb-1.5 block text-xs text-slate-500">Default Environment</label>
						<Dropdown
							value={defaultEnvironment}
							onChange={setDefaultEnvironment}
							options={envOptions}
							placeholder="Select environment"
							className="w-full"
							triggerClassName="border border-slate-200 bg-white hover:bg-white hover:border-orange-400 text-slate-900"
						/>
					</div>

					{/* Default Concurrency */}
					<div>
						<label className="mb-1 flex items-center justify-between text-xs text-slate-500">
							<span>Default Concurrency Limit</span>
							<span className="tabular-nums text-slate-700">{defaultConcurrency}</span>
						</label>
						<input
							type="range"
							min={1}
							max={20}
							value={defaultConcurrency}
							onChange={(e) => setDefaultConcurrency(Number(e.target.value))}
							className="w-full transition-all duration-200"
							style={rangeStyle(((defaultConcurrency - 1) / 19) * 100)}
						/>
						<div className="flex justify-between text-[10px] text-slate-400">
							<span>1</span>
							<span>20</span>
						</div>
					</div>

					{/* Max Dataset Size */}
					<div>
						<label className="mb-1.5 block text-xs text-slate-500">Max Dataset Size</label>
						<input
							type="number"
							min={1}
							max={10000}
							value={maxDatasetSize}
							onChange={(e) => setMaxDatasetSize(Number(e.target.value) || 200)}
							className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 hover:border-orange-400 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15 transition-all"
						/>
						<p className="mt-1 text-[11px] text-slate-500">Maximum number of test cases per dataset.</p>
					</div>

					{/* Default Generator Model */}
					<div>
						<label className="mb-1.5 block text-xs text-slate-500">Default Generator Model</label>
						{modelsLoading ? (
							<div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
								<Loader2 className="h-3.5 w-3.5 animate-spin" />
								Loading models...
							</div>
						) : modelOptions.length > 0 ? (
							<Dropdown
								value={defaultGenModel}
								onChange={setDefaultGenModel}
								options={[{ value: "", label: "System Default", description: "Use the platform default generator model" }, ...modelOptions]}
								placeholder="System Default"
								className="w-full"
								triggerClassName="border border-slate-200 bg-white hover:bg-white hover:border-orange-400 text-slate-900"
							/>
						) : (
							<p className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
								No model deployments configured.
							</p>
						)}
						<p className="mt-1 text-[11px] text-slate-500">LLM used for AI test case generation.</p>
					</div>
					</div>
				)}

				{/* Evaluations tab */}
				{activeTab === "scoring-judge" && (
					<div className="space-y-5">
					{/* Pillar Weights */}
					<div>
						<p className="mb-2 text-xs text-slate-500">Default Pillar Weights</p>
						{!defaultWeightsValid && (
							<p className="mb-2 text-xs text-amber-400">
								Weights must sum to 1.0 (currently {defaultWeightSum.toFixed(2)})
							</p>
						)}
						<div className="grid grid-cols-2 gap-3">
							{([
								["Cost", defaultCostW, setDefaultCostW],
								["Quality", defaultQualityW, setDefaultQualityW],
								["Reliability", defaultReliabilityW, setDefaultReliabilityW],
								["Latency", defaultLatencyW, setDefaultLatencyW],
							] as [string, number, (v: number) => void][]).map(([label, value, setter]) => (
								<div key={label}>
									<label className="mb-0.5 flex items-center justify-between text-xs text-slate-500">
										<span>{label}</span>
										<span className="font-mono">{value.toFixed(2)}</span>
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
						<p className="mt-1 text-[11px] text-slate-500">Default scoring weights for evaluation pillars. Per-run settings override these.</p>
					</div>

					{/* Default Quality Judge Provider */}
					<div>
						<p className="mb-1.5 text-xs text-slate-500">Default Quality Judge Provider</p>
						<div className="flex gap-1 rounded-lg border border-slate-200 bg-white p-1">
							{(["builtin", "phoenix"] as const).map((p) => (
								<button
									key={p}
									type="button"
									onClick={() => setDefaultQualityJudgeProvider(p)}
									className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
										defaultQualityJudgeProvider === p
											? "bg-orange-500 text-white"
											: "text-slate-600 hover:text-slate-900"
									}`}
								>
									{p === "builtin" ? "Built-in Judge" : "Phoenix LLM Judge"}
								</button>
							))}
						</div>
						<p className="mt-1 text-[11px] text-slate-500">
							{defaultQualityJudgeProvider === "builtin"
								? "Uses the built-in LLM-as-a-judge for quality scoring. Runs via LangChain."
								: "Uses Phoenix LLMEvaluator for quality scoring. Requires Phoenix to be enabled."}
						</p>
					</div>

					{/* Default Evaluations Model */}
					<div>
						<label className="mb-1.5 block text-xs text-slate-500">Default Evaluations Model</label>
						{modelsLoading ? (
							<div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
								<Loader2 className="h-3.5 w-3.5 animate-spin" />
								Loading models...
							</div>
						) : modelOptions.length > 0 ? (
							<Dropdown
								value={defaultJudgeModel}
								onChange={setDefaultJudgeModel}
								options={[{ value: "", label: "System Default", description: "Use the platform default model" }, ...modelOptions]}
								placeholder="System Default"
								className="w-full"
								triggerClassName="border border-slate-200 bg-white hover:bg-white hover:border-orange-400 text-slate-900"
							/>
						) : (
							<p className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
								No model deployments configured.
							</p>
						)}
						<p className="mt-1 text-[11px] text-slate-500">LLM used for quality judging and Phoenix supplementary evaluations (hallucination, tool selection).</p>
					</div>

					{/* Default Judge Output Strategy */}
					<div>
						<label className="mb-1.5 block text-xs text-slate-500">Default Judge Output Policy</label>
						<Dropdown
							value={defaultJudgeStrategy}
							onChange={(v) => setDefaultJudgeStrategy(v)}
							options={[
								{ value: "final_node", label: "Final node output (recommended)" },
								{ value: "all_nodes", label: "All node outputs" },
							]}
							triggerClassName="w-full !rounded-xl !border-slate-200 !bg-white !px-3 !py-2 !text-sm !text-slate-900 hover:!border-orange-400"
						/>
						<p className="mt-1 text-[11px] text-slate-500">Controls which part of the workflow output the judge evaluates. Per-node selection is available per-run.</p>
					</div>

					{/* Default Max Output Chars */}
					<div>
						<label className="mb-1 flex items-center justify-between text-xs text-slate-500">
							<span>Default Max Output Chars for Judge</span>
							<span className="tabular-nums text-slate-700">{defaultMaxOutputChars >= 1000 ? `${Math.round(defaultMaxOutputChars / 1000)}k` : defaultMaxOutputChars}</span>
						</label>
						<input
							type="range"
							min={10000}
							max={500000}
							step={10000}
							value={defaultMaxOutputChars}
							onChange={(e) => setDefaultMaxOutputChars(Number(e.target.value))}
							className="w-full transition-all duration-200"
							style={rangeStyle(((defaultMaxOutputChars - 10000) / 490000) * 100)}
						/>
						<div className="flex justify-between text-[10px] text-slate-400">
							<span>10k</span>
							<span>200k (default)</span>
							<span>500k</span>
						</div>
						<p className="mt-1 text-[11px] text-slate-500">Truncation limit for output sent to the judge LLM. Prevents context length errors.</p>
					</div>
					</div>
				)}
			</div>

			{/* Save */}
			<div className="mt-auto flex flex-shrink-0 items-center justify-end gap-3 pt-6">
				{saved && (
					<span className="text-sm text-emerald-400">Defaults saved.</span>
				)}
				<button
					type="button"
					onClick={handleSave}
					className="rounded-xl border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-all hover:border-orange-600 hover:bg-orange-600 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
				>
					Save Defaults
				</button>
			</div>
		</div>
	);
}
