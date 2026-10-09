"use client";

import { useEffect, useState } from "react";
import { modelDeploymentAPI, type ModelDeploymentOption } from "@/lib/model-deployment-api";
import EvalGeneralSettings from "./EvalGeneralSettings";
import AutoEvalSettingsTab from "./AutoEvalSettingsTab";

type SubTab = "general" | "auto-eval";

export default function SettingsTab() {
	const [llmDeployments, setLlmDeployments] = useState<ModelDeploymentOption[]>([]);
	const [modelsLoading, setModelsLoading] = useState(true);
	const [subTab, setSubTab] = useState<SubTab>("general");

	useEffect(() => {
		let cancelled = false;
		modelDeploymentAPI
			.listSelectOptions()
			.then((deps) => {
				if (!cancelled) setLlmDeployments(deps);
			})
			.catch(() => {})
			.finally(() => {
				if (!cancelled) setModelsLoading(false);
			});
		return () => { cancelled = true; };
	}, []);

	// Tutorial: switch sub-tab on request
	useEffect(() => {
		const handler = (e: Event) => {
			const tab = (e as CustomEvent).detail?.tab as SubTab | undefined;
			if (tab) setSubTab(tab);
		};
		window.addEventListener("tutorialSwitchSettingsTab", handler);
		return () => window.removeEventListener("tutorialSwitchSettingsTab", handler);
	}, []);

	const tabs: { key: SubTab; label: string }[] = [
		{ key: "general", label: "General Defaults" },
		{ key: "auto-eval", label: "Auto-Evaluation" },
	];

	return (
		<div className="space-y-6">
			{/* Sub-tab bar */}
			<div className="rounded-2xl border border-slate-200 bg-white p-2 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
				<div className="flex space-x-2">
					{tabs.map((t) => (
						<button
							key={t.key}
							type="button"
							data-tutorial={`settings-${t.key}-tab`}
							onClick={() => setSubTab(t.key)}
							className={`flex items-center gap-2 px-4 py-3 rounded-lg font-medium transition-all duration-200 whitespace-nowrap min-w-fit ${
								subTab === t.key
									? "border border-orange-500 bg-orange-500 text-white"
									: "border border-transparent bg-white text-slate-700 hover:border-orange-400 hover:text-slate-900"
							}`}
						>
							{t.label}
						</button>
					))}
				</div>
			</div>

			{/* Tab content */}
			{subTab === "general" && (
				<EvalGeneralSettings llmDeployments={llmDeployments} modelsLoading={modelsLoading} />
			)}
			{subTab === "auto-eval" && (
				<AutoEvalSettingsTab llmDeployments={llmDeployments} modelsLoading={modelsLoading} />
			)}
		</div>
	);
}
