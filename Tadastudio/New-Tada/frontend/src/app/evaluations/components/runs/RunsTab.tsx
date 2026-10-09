"use client";

import { useCallback, useEffect, useState } from "react";
import { getAuthenticatedApiClientForMain } from "@/lib/api";
import { runtimeConfig } from "@/lib/runtime-config";
import RunsListView from "./RunsListView";
import RunDetailView from "./RunDetailView";

/** Ensure a prompt_edit recommendation exists for the tutorial run. */
async function seedTutorialRecommendation(runId: string) {
	const evalData = (window as any).__tutorialEvalData;
	if (!evalData) return;
	const body = {
		run_id: runId,
		target_node_id: "tutorial-agent-node",
		current_prompt: evalData.currentPrompt ?? "",
	};
	try {
		const client = getAuthenticatedApiClientForMain();
		if (client) {
			await client.post("/api/tutorial/seed-recommendation", body);
		} else {
			const base = await runtimeConfig.getApiBaseUrl();
			await fetch(`${base}/api/tutorial/seed-recommendation`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(body),
			});
		}
	} catch {
		// Non-fatal — the recommendation engine may have already generated one
	}
}

export default function RunsTab({ newRunCutoff, showAllUsers }: { newRunCutoff?: string; showAllUsers?: boolean }) {
	const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

	const handleBack = useCallback(() => setSelectedRunId(null), []);

	// Tutorial event: open a specific run's detail view
	useEffect(() => {
		const openHandler = (e: Event) => {
			const evalData = (window as any).__tutorialEvalData;
			const runId = (e as CustomEvent).detail?.runId
				|| evalData?.rerunId
				|| evalData?.runId;
			if (runId) {
				setSelectedRunId(runId);
				// Ensure a prompt_edit recommendation exists for the tutorial
				seedTutorialRecommendation(runId);
			}
		};
		const backHandler = () => setSelectedRunId(null);
		window.addEventListener("tutorialOpenEvalRun", openHandler);
		window.addEventListener("tutorialBackToRunsList", backHandler);
		return () => {
			window.removeEventListener("tutorialOpenEvalRun", openHandler);
			window.removeEventListener("tutorialBackToRunsList", backHandler);
		};
	}, []);

	if (selectedRunId) {
		return <RunDetailView runId={selectedRunId} onBack={handleBack} />;
	}

	return <RunsListView onSelectRun={setSelectedRunId} newRunCutoff={newRunCutoff} showAllUsers={showAllUsers} />;
}
