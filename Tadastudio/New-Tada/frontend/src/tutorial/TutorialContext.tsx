"use client";

import {
	type ReactNode,
	createContext,
	useCallback,
	useContext,
	useEffect,
	useRef,
	useState,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import * as evalApi from "@/lib/evaluation-api";
import { modelDeploymentAPI } from "@/lib/model-deployment-api";
import {
	getTutorialState,
	hydrateTutorialState,
	markCompleted,
	saveProgress,
} from "./persistence";
import { TUTORIAL_DEFINITIONS } from "./steps";
import type { TutorialContextValue } from "./types";
import type {
	DestroyReason,
	TutorialEngine as TutorialEngineType,
} from "./TutorialEngine";

export const TutorialContext = createContext<TutorialContextValue | null>(null);

// ── Consistent tutorial resource names ──────────────────────────────
const TUTORIAL_WORKFLOW_NAME = "Tutorial Workflow";
/** @deprecated kept only for cleanup of legacy tutorial runs */
const TUTORIAL_PUBLISH_WORKFLOW_NAME_LEGACY = "Tutorial Published Workflow";
const TUTORIAL_DATASET_NAME = "Tutorial Dataset";
const TUTORIAL_COLLECTION_NAME = "Tutorial Collection";

/**
 * Delete any existing tutorial resources with the given name so the
 * tutorial starts from a clean slate each time.
 */
async function cleanExistingTutorialWorkflow(name: string): Promise<void> {
	await api.unpublishWorkflow(name).catch(() => {});
	await api.deleteGraph(name).catch(() => {});
}

async function cleanExistingTutorialCollection(): Promise<void> {
	const collections = await api.getCollections().catch(() => []);
	const match = (collections ?? []).find((c: any) => c.name === TUTORIAL_COLLECTION_NAME);
	if (match) {
		await api.deleteCollection(match.id).catch(() => {});
	}
}

async function cleanExistingTutorialEvalData(): Promise<void> {
	// Delete runs that belong to the tutorial dataset, then the dataset
	const datasets = await evalApi.listDatasets().catch(() => [] as any[]);
	const tutorialDs = (datasets ?? []).find((d: any) => d.name === TUTORIAL_DATASET_NAME);
	if (tutorialDs) {
		const runs = await evalApi.listRuns({ dataset_id: tutorialDs.id }).catch(() => [] as any[]);
		for (const run of runs ?? []) {
			await evalApi.deleteRun(run.id).catch(() => {});
		}
		await evalApi.deleteDataset(tutorialDs.id).catch(() => {});
	}
}

/**
 * Build a complete tutorial workflow (START → AGENT → END) with the first
 * available LLM so the graph passes publish validation.
 *
 * Uses importRawWorkflow to submit the entire graph definition (nodes +
 * connections) in a single API call, avoiding multi-step ID resolution issues.
 */
async function buildTutorialWorkflow(): Promise<string | undefined> {
	// Resolve a configured model deployment so the agent has a working LLM
	let deployment: { id: string; provider: string; model_name: string } | null = null;
	try {
		const deployments = await modelDeploymentAPI.listSelectOptions();
		// Prefer the default active LLM deployment, otherwise take the first active LLM
		const active = deployments.filter((d) => d.is_active && d.model_type === "llm");
		deployment = active.find((d) => d.is_default) ?? active[0] ?? null;
	} catch {
		// If the API is unreachable we cannot resolve a valid deployment
	}

	if (!deployment) {
		console.warn("No active LLM model deployments available — tutorial workflow will have no LLM configured");
	}

	const startId = "tutorial-start-node";
	const agentId = "tutorial-agent-node";
	const endId = "tutorial-end-node";

	const workflowJson = {
		name: TUTORIAL_WORKFLOW_NAME,
		description: "Created for the tutorial.",
		nodes: [
			{
				uniq_id: startId,
				name: "Start",
				type: "START",
				position: { x: 100, y: 200 },
				nexts: [agentId],
				inputs: [],
			},
			{
				uniq_id: agentId,
				name: "Assistant",
				type: "AGENT",
				position: { x: 400, y: 200 },
				nexts: [endId],
				inputs: [startId],
				agent_config: {
					...(deployment
						? {
								llm_config: {
									provider: deployment.provider,
									model_name: deployment.model_name,
									model_deployment_id: deployment.id,
									temperature: 1.2,
								},
							}
						: {}),
					system_prompt: "You are a creative storyteller. Always respond with long, imaginative narratives. Embellish your answers with fictional details and metaphors. Never give short or direct answers.",
				},
			},
			{
				uniq_id: endId,
				name: "End",
				type: "END",
				position: { x: 700, y: 200 },
				nexts: [],
				inputs: [agentId],
			},
		],
		connections: [
			{
				source_id: startId,
				target_id: agentId,
				connection_type: "workflow",
			},
			{
				source_id: agentId,
				target_id: endId,
				connection_type: "workflow",
			},
		],
	};

	const res = (await api.importRawWorkflow({
		name: TUTORIAL_WORKFLOW_NAME,
		description: "Created for the tutorial.",
		workflow_json: workflowJson,
	})) as any;

	return res?.success ? TUTORIAL_WORKFLOW_NAME : undefined;
}

/**
 * Ensure the "Tutorial Workflow" exists and return its graph data.
 * If it was already created by the canvas tutorial, reuse it.
 * Otherwise build a complete workflow (START → AGENT → END) with an LLM.
 */
async function ensureTutorialWorkflow(): Promise<{ name: string; workflowId: string }> {
	const existing = await api.getGraph(TUTORIAL_WORKFLOW_NAME).catch(() => null);
	if (existing?.success && existing.graph?.workflow_id) {
		return { name: existing.graph.name, workflowId: existing.graph.workflow_id };
	}
	// Workflow doesn't exist — build one from scratch
	const name = await buildTutorialWorkflow();
	if (!name) throw new Error("Failed to create Tutorial Workflow");
	// Re-fetch to get the workflow_id assigned by the backend
	const fresh = await api.getGraph(name);
	if (!(fresh as any)?.success || !(fresh as any)?.graph?.workflow_id) {
		throw new Error("Tutorial Workflow created but missing workflow_id");
	}
	return { name, workflowId: (fresh as any).graph.workflow_id };
}

/**
 * Run the Tutorial Workflow so the executions page has a completed execution
 * to demo. Triggers an async execution and polls until it finishes.
 */
async function runTutorialExecution(
	onProgress?: (msg: string) => void,
): Promise<void> {
	onProgress?.("Setting up Tutorial Workflow\u2026");
	const { name } = await ensureTutorialWorkflow();

	onProgress?.("Running Tutorial Workflow\u2026");
	// Trigger the workflow
	const res = await api.executeGraph({
		graph_name: name,
		initial_input: { message: "What is the capital of France?" },
		async_execution: true,
	});

	if (!res?.success || !res.execution_id) {
		console.warn("Tutorial execution trigger failed — executions tutorial will use any existing data");
		return;
	}

	// Poll until the execution finishes (completed or failed) — up to 60s
	onProgress?.("Waiting for execution to complete\u2026");
	const executionId = res.execution_id;
	const deadline = Date.now() + 60_000;
	while (Date.now() < deadline) {
		await new Promise((r) => setTimeout(r, 2000));
		try {
			const status = await api.getExecutionStatus(executionId);
			const s = status?.execution_status?.status;
			if (s === "completed" || s === "failed") {
				return;
			}
		} catch {
			// Ignore transient errors
		}
	}
}

/**
 * Set up dataset + test cases for the evaluations tutorial using the
 * "Tutorial Workflow" (auto-created if it doesn't exist).
 * Stores IDs on `window.__tutorialEvalData` for step references.
 */
async function setupEvaluationsTutorial(): Promise<void> {
	// Clean up any leftover eval resources from a previous tutorial run
	await cleanExistingTutorialEvalData();

	// 1. Delete and rebuild the Tutorial Workflow so it always starts with
	//    the deliberately poor prompt and a valid LLM deployment.
	await cleanExistingTutorialWorkflow(TUTORIAL_WORKFLOW_NAME);
	const name = await buildTutorialWorkflow();
	if (!name) throw new Error("Failed to create Tutorial Workflow");
	const fresh = await api.getGraph(name);
	const workflowId: string = (fresh as any)?.graph?.workflow_id;
	if (!workflowId) throw new Error("Tutorial Workflow created but missing workflow_id");

	// 2. Create a dataset targeting the workflow
	const dataset = await evalApi.createDataset({
		name: TUTORIAL_DATASET_NAME,
		description: "Demo dataset for the Evaluations tutorial.",
		target_type: "workflow",
		target_id: workflowId,
		workflow_id: workflowId,
	});

	// 3. Add test cases with judge criteria so the evaluator scores quality
	//    on explicit dimensions. The tutorial workflow uses a deliberately poor
	//    "creative storyteller" prompt, so responses will fail these criteria
	//    and drive the recommendation engine to suggest a prompt_edit.
	const sharedCriteria = {
		conciseness: "The response must be concise and directly answer the question without unnecessary elaboration, stories, or filler.",
		accuracy: "The response must be factually correct and match the expected output.",
		format_compliance: "The response must follow the requested format (e.g. a short answer, a two-sentence summary, a translation) without deviating into narratives or tangents.",
	};

	await evalApi.addTestCases(dataset.id, {
		manual: [
			{
				input_data: "What is the capital of France?",
				expected_output: "Paris",
				judge_criteria: sharedCriteria,
				tags: ["geography"],
			},
			{
				input_data: "Summarize the benefits of renewable energy in two sentences.",
				expected_output: "Renewable energy reduces greenhouse gas emissions and lowers dependency on finite fossil fuels. It also creates sustainable jobs and improves energy security.",
				judge_criteria: sharedCriteria,
				tags: ["summarization"],
			},
			{
				input_data: "Translate 'Hello, how are you?' to Spanish.",
				expected_output: "Hola, ¿cómo estás?",
				judge_criteria: sharedCriteria,
				tags: ["translation"],
			},
		],
	});

	// Stash IDs for tutorial steps to reference
	(window as any).__tutorialEvalData = {
		workflowName: TUTORIAL_WORKFLOW_NAME,
		datasetId: dataset.id,
		runId: null as string | null,
	};

	// Tell the already-mounted evaluations page to refresh its lists
	window.dispatchEvent(new CustomEvent("tutorialEvalDataReady"));
}

export function TutorialProvider({ children }: { children: ReactNode }) {
	const [isRunning, setIsRunning] = useState(false);
	const [activeTutorialId, setActiveTutorialId] = useState<string | null>(
		null,
	);
	const [setupProgress, setSetupProgress] = useState<string | null>(null);
	const [completedTutorials, setCompletedTutorials] = useState<
		Record<string, boolean>
	>({});
	const engineRef = useRef<TutorialEngineType | null>(null);
	const router = useRouter();
	const pathname = usePathname();
	const { showSuccess } = useToast();

	useEffect(() => {
		// Seed synchronously from cache, then hydrate from API
		setCompletedTutorials(getTutorialState().completedTutorials);
		hydrateTutorialState().then((state) => {
			setCompletedTutorials(state.completedTutorials);
		});
	}, []);

	const onComplete = useCallback(
		(completedId: string) => {
			markCompleted(completedId);
			saveProgress(completedId, 0);
			setCompletedTutorials((prev) => ({ ...prev, [completedId]: true }));
			showSuccess(
				"Tutorial complete!",
				`You've finished the ${TUTORIAL_DEFINITIONS[completedId]?.label ?? completedId} tutorial. You can replay it any time from the ? button.`,
			);
		},
		[showSuccess],
	);

	const onDestroy = useCallback(
		(id: string, reason: DestroyReason) => {
			setIsRunning(false);
			setActiveTutorialId(null);
			if (reason === "completed") {
				const state = getTutorialState();
				setCompletedTutorials(state.completedTutorials);
			}

			// Close the execution side panel after the home tutorial ends
			if (id === "home") {
				window.dispatchEvent(new CustomEvent("tutorialCloseExecutionPanel"));
			}

			// Clear stashed window refs (resources are intentionally retained
			// so the user can explore them after the tutorial)
			delete (window as any).__tutorialPublishWorkflowName;
			delete (window as any).__tutorialEvalData;
		},
		[],
	);

	const startTutorial = useCallback(
		(id: string) => {
			const definition = TUTORIAL_DEFINITIONS[id];
			if (!definition) {
				console.warn(`Tutorial definition not found: ${id}`);
				return;
			}

			const startEngine = () => {
				setSetupProgress(null);
				import("./TutorialEngine").then((m) => {
					if (!engineRef.current) {
						engineRef.current = new m.TutorialEngine();
					}
					const nextDef = definition.nextTutorialId
						? TUTORIAL_DEFINITIONS[definition.nextTutorialId]
						: undefined;
					const steps = definition.steps;

					engineRef.current.start(
						id,
						steps,
						0,
						onComplete,
						onDestroy,
						definition.nextTutorialId,
						nextDef?.label,
					);
					setActiveTutorialId(id);
					setIsRunning(true);
				});
			};

			const launch = () => {
				if (id === "home") {
					// Clean up any existing tutorial workflow before creating a fresh one
					setSetupProgress("Preparing tutorial workflow…");
					cleanExistingTutorialWorkflow(TUTORIAL_WORKFLOW_NAME).then(
						() => startEngine(),
						() => startEngine(),
					);
					return;
				}

				if (id === "publish") {
					setSetupProgress("Setting up publish tutorial…");
					// Clean up any legacy "Tutorial Published Workflow" from older runs
					cleanExistingTutorialWorkflow(TUTORIAL_PUBLISH_WORKFLOW_NAME_LEGACY).catch(() => {});
					// Make sure the workflow is unpublished so it shows in the "available" list
					api.unpublishWorkflow(TUTORIAL_WORKFLOW_NAME).catch(() => {});

					ensureTutorialWorkflow().then(
						({ name }) => {
							(window as any).__tutorialPublishWorkflowName = name;
							window.dispatchEvent(
								new CustomEvent("tutorialPublishWorkflowName", {
									detail: { name },
								}),
							);
							setTimeout(startEngine, 800);
						},
						() => setTimeout(startEngine, 800),
					);
					return;
				}

				if (id === "evaluations") {
					setSetupProgress("Setting up evaluations tutorial…");
					setupEvaluationsTutorial().then(
						() => setTimeout(startEngine, 800),
						() => setTimeout(startEngine, 800),
					);
					return;
				}

				if (id === "datasources") {
					// Delete any existing "Tutorial Collection" so the create demo works
					setSetupProgress("Preparing data sources…");
					cleanExistingTutorialCollection().then(
						() => setTimeout(startEngine, 400),
						() => setTimeout(startEngine, 400),
					);
					return;
				}

				if (id === "executions") {
					// Run the Tutorial Workflow so the executions page has a completed run to demo
					setSetupProgress("Creating and running Tutorial Workflow\u2026");
					runTutorialExecution((msg) => setSetupProgress(msg)).then(
						() => {
							// Dispatch a refresh event so the executions list picks up the new run
							window.dispatchEvent(new CustomEvent("tutorialRefreshExecutions"));
							setTimeout(startEngine, 800);
						},
						() => setTimeout(startEngine, 800),
					);
					return;
				}

				startEngine();
			};

			// Always navigate to the tutorial's starting route so the
			// correct screen is visible before step 0 renders.
			const alreadyOnRoute =
				definition.route === "/"
					? pathname === "/"
					: pathname.startsWith(definition.route);

			if (!alreadyOnRoute) {
				if (definition.route === "/workflow") {
					if (pathname.startsWith("/workflow/")) {
						launch();
					} else {
						api.listGraphs().then(
							(res: { graphs?: Array<{ name: string }> }) => {
								const first = res.graphs?.[0];
								if (first) {
									router.push(`/workflow/${encodeURIComponent(first.name)}`);
									setTimeout(launch, 800);
								} else {
									router.push("/");
									setTimeout(launch, 600);
								}
							},
							() => launch(),
						);
					}
				} else {
					router.push(definition.route);
					setTimeout(launch, 600);
				}
			} else {
				launch();
			}
		},
		[onComplete, onDestroy, router, pathname],
	);

	const stopTutorial = useCallback(() => {
		engineRef.current?.stop();
	}, []);

	useEffect(() => {
		return () => {
			engineRef.current?.stop();
		};
	}, []);

	// Listen for "Next Tutorial" requests from the engine
	useEffect(() => {
		const handler = (e: Event) => {
			const nextId = (e as CustomEvent).detail?.id;
			if (nextId) {
				// Small delay to let the current tutorial fully tear down
				setTimeout(() => startTutorial(nextId), 300);
			}
		};
		window.addEventListener("tutorialStartNext", handler);
		return () => window.removeEventListener("tutorialStartNext", handler);
	}, [startTutorial]);

	const refreshCompletionState = useCallback(() => {
		setCompletedTutorials(getTutorialState().completedTutorials);
		hydrateTutorialState().then((state) => {
			setCompletedTutorials(state.completedTutorials);
		});
	}, []);

	const value: TutorialContextValue = {
		startTutorial,
		stopTutorial,
		isRunning,
		activeTutorialId,
		completedTutorials,
		refreshCompletionState,
		setupProgress,
	};

	return (
		<TutorialContext.Provider value={value}>
			{children}
			{setupProgress && (
				<div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[10000] flex items-center gap-3 px-5 py-3 rounded-2xl bg-[color:var(--color-surface)]/95 border border-[color:var(--color-border)]/60 shadow-[0_20px_60px_rgba(0,0,0,0.5)] backdrop-blur-xl animate-fadeIn">
					<div className="h-4 w-4 rounded-full border-2 border-[rgba(var(--color-primary-rgb),0.25)] border-t-[color:var(--color-primary)] animate-spin" />
					<span className="text-sm text-[color:var(--color-text-secondary)]">
						{setupProgress}
					</span>
				</div>
			)}
		</TutorialContext.Provider>
	);
}

export function getTutorialIdForRoute(pathname: string): string | null {
	if (pathname === "/") return "home";
	if (pathname.startsWith("/workflow")) return "home";
	if (pathname.startsWith("/library")) return "library";
	if (pathname === "/publish" || pathname.startsWith("/publish/"))
		return "publish";
	if (pathname.startsWith("/datasources")) return "datasources";
	if (pathname.startsWith("/evaluations")) return "evaluations";
	if (pathname.startsWith("/executions")) return "executions";
	if (pathname.startsWith("/settings")) return "settings";
	return null;
}

export function useTutorial(): TutorialContextValue {
	const context = useContext(TutorialContext);
	if (!context) {
		throw new Error("useTutorial must be used within a TutorialProvider");
	}
	return context;
}
