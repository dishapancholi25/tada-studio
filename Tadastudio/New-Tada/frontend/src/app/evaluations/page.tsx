"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import * as evalApi from "@/lib/evaluation-api";
import type { TabId } from "./components/shared/constants";
import { TABS } from "./components/shared/constants";
import EvalHelpButton from "./components/shared/EvalHelpButton";
import type { EvalHelpTopic } from "./components/shared/EvalHelpButton";
import ShowAllUsersToggle from "./components/shared/ShowAllUsersToggle";
import DatasetsTab from "./components/datasets/DatasetsTab";
import RunsTab from "./components/runs/RunsTab";
import SettingsTab from "./components/settings/SettingsTab";

export default function EvaluationsPage() {
	const searchParams = useSearchParams();
	const router = useRouter();
	const pathname = usePathname();
	// Capture the cutoff before the nav bar's effect clears it (useState initializers run before effects)
	const [newRunCutoff] = useState(
		() => localStorage.getItem("eval_last_seen_at") || "1970-01-01T00:00:00.000Z",
	);
	const [activeTab, setActiveTab] = useState<TabId>(
		() => {
			const urlTab = searchParams.get("tab");
			if (urlTab === "datasets" || urlTab === "runs" || urlTab === "settings") return urlTab;
			return "datasets";
		},
	);
	const [initialDatasetId, setInitialDatasetId] = useState<string | null>(
		() => searchParams.get("dataset"),
	);
	const [showAllUsers, setShowAllUsers] = useState(false);

	// Clear URL search params without a full navigation
	const clearSearchParams = useCallback(() => {
		if (searchParams.toString()) {
			router.replace(pathname, { scroll: false });
		}
	}, [router, pathname, searchParams]);

	const handleTabChange = useCallback((tab: TabId) => {
		setActiveTab(tab);
		clearSearchParams();
	}, [clearSearchParams]);

	// Tutorial: switch main eval tab on request
	useEffect(() => {
		const handler = (e: Event) => {
			const tab = (e as CustomEvent).detail?.tab as TabId | undefined;
			if (tab) setActiveTab(tab);
		};
		window.addEventListener("tutorialSwitchEvalTab", handler);
		return () => window.removeEventListener("tutorialSwitchEvalTab", handler);
	}, []);

	// Auto-switch to Runs tab when arriving with unseen completed runs
	useEffect(() => {
		let cancelled = false;
		evalApi.listRuns({ status: "completed", limit: 5 }).then((runs) => {
			if (cancelled) return;
			const hasNew = runs.some((r) => r.completed_at && r.completed_at > newRunCutoff);
			if (hasNew) setActiveTab("runs");
		}).catch(() => {});
		return () => { cancelled = true; };
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	return (
		<AppShell>
		<div className="h-screen flex flex-col bg-white overflow-hidden">
			<div className="flex-1 flex flex-col overflow-hidden">
				<div className="flex-1 flex flex-col mx-auto w-full max-w-screen-2xl px-4 sm:px-6 lg:px-8 py-4 sm:py-6 overflow-hidden">
					{/* Tab bar */}
					<div className="mb-4 flex items-center gap-2 flex-wrap rounded-3xl border border-slate-200 bg-white p-4 shadow-[0_18px_50px_rgba(15,23,42,0.08)] shrink-0" data-tutorial="evaluations-header">
						{TABS.map((tab) => (
							<button
								key={tab.id}
								type="button"
								data-tutorial={tab.id === "datasets" ? "datasets-tab" : tab.id === "runs" ? "runs-tab" : tab.id === "settings" ? "eval-settings-tab" : undefined}
								onClick={() => handleTabChange(tab.id)}
								className={`px-4 py-2 rounded-xl text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] ${
									activeTab === tab.id
										? "border border-orange-500 bg-orange-500 text-white"
										: "border border-slate-200 bg-white text-slate-600 hover:text-slate-900 hover:border-orange-400 hover:bg-white"
								}`}
							>
								{tab.label}
							</button>
						))}
						<div className="ml-auto flex items-center gap-2">
							<ShowAllUsersToggle enabled={showAllUsers} onToggle={setShowAllUsers} />
							<EvalHelpButton topic={({ datasets: "datasets", runs: "runs", settings: "general-settings" } as Record<TabId, EvalHelpTopic>)[activeTab]} />
						</div>
					</div>

					{/* Tab content - fills remaining space */}
					<div className="flex-1 overflow-y-auto overflow-x-hidden">
						{activeTab === "datasets" && <DatasetsTab initialDatasetId={initialDatasetId} onInitialDatasetHandled={() => { setInitialDatasetId(null); clearSearchParams(); }} showAllUsers={showAllUsers} />}
						{activeTab === "runs" && <RunsTab newRunCutoff={newRunCutoff} showAllUsers={showAllUsers} />}
						{activeTab === "settings" && <SettingsTab />}
					</div>
				</div>
			</div>
		</div>
		</AppShell>
	);
}
