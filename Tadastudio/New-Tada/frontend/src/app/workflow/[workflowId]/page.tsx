"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { lazy, Suspense, useEffect, useState } from "react";
import AgentBuilder from "@/components/core/AgentBuilder";
import AddToLibraryDialog from "@/components/library/AddToLibraryDialog";
import { WorkflowLoading } from "@/components/utils/LazyLoad";
import { useLoadingOverlay } from "@/contexts/LoadingOverlayContext";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import { logLoading } from "@/lib/debug";
import { useGraphStore } from "@/stores/graphStore";

// Lazy load heavy components with preload hints
const GraphManagementDialog = lazy(() =>
	import("@/components/core/GraphManagementDialog").then((module) => ({
		default: module.default,
	})),
);

// Pre-load components that are likely to be used
const preloadComponents = () => {
	// Pre-load dialog since it's commonly used
	import("@/components/core/GraphManagementDialog");
};

import { useGraph } from "@/contexts/GraphContext";
import { HistoricalVersionBanner } from "@/components/shared/HistoricalVersionBanner";
import { VersionHistoryPanel } from "@/components/shared/VersionHistoryPanel";

export default function WorkflowPage() {
	const params = useParams();
	const router = useRouter();
	const searchParams = useSearchParams();
	const workflowParam = params.workflowId as string;
	const workflowId = decodeURIComponent(workflowParam);
	const [showGraphDialog, setShowGraphDialog] = useState(false);
	const [showAddToLibrary, setShowAddToLibrary] = useState(false);
	const [showVersionHistory, setShowVersionHistory] = useState(false);
	const { currentGraph, loadGraph, loadGraphByWorkflowId } = useGraph();
	const { showOverlay, hideOverlay } = useLoadingOverlay();
	const { showSuccess, showError } = useToast();
	const [showLoading, setShowLoading] = useState(true); // Start with loading visible
	const [loadingMessage, setLoadingMessage] = useState(
		`Loading workflow: ${workflowId}...`,
	);
	const [isReady, setIsReady] = useState(false); // Track when content can be shown
	const [loadedLoadKey, setLoadedLoadKey] = useState<string | null>(null); // Track which workflow+version is loaded

	// Track if this is the initial mount
	const [isInitialMount, setIsInitialMount] = useState(true);

	// Extract version params as stable primitives to avoid searchParams object reference in deps
	const versionParam = searchParams.get("version");
	const graphDefIdParam = searchParams.get("graph_definition_id");
	const searchParamsKey = `${versionParam || ""}:${graphDefIdParam || ""}`;

	// Composite load key: workflowId + version info
	const desiredLoadKey = `${workflowId}:${searchParamsKey}`;

	useEffect(() => {
		logLoading("Page loading state", {
			showLoading,
			isReady,
			currentGraphName: currentGraph?.name,
		});
	}, [showLoading, isReady, currentGraph]);

	useEffect(() => {
		if (searchParams.get("manage") === "1") {
			setShowGraphDialog(true);
			const paramsWithoutManage = new URLSearchParams(searchParams.toString());
			paramsWithoutManage.delete("manage");
			const nextSearch = paramsWithoutManage.toString();
			if (typeof window !== "undefined") {
				const nextUrl = nextSearch ? `?${nextSearch}` : "";
				router.replace(`${window.location.pathname}${nextUrl}`, {
					scroll: false,
				});
			}
		}
	}, [searchParams, router]);

	useEffect(() => {
		if (!workflowId) {
			router.push("/");
			return;
		}

		// Load the specific workflow
		const initWorkflow = async () => {
			// Check if this is a new workflow creation
			const isNewWorkflow =
				sessionStorage.getItem("newWorkflowCreation") === "true";
			if (isNewWorkflow) {
				sessionStorage.removeItem("newWorkflowCreation");
			}

			logLoading("WorkflowPage init", {
				workflowId,
				isNewWorkflow,
				when: "mount or param change",
			});

			// Build version options from stable extracted params
			const versionOptions:
				| { version?: number; graphDefinitionId?: string }
				| undefined =
				versionParam || graphDefIdParam
					? {
							version: versionParam ? Number(versionParam) : undefined,
							graphDefinitionId: graphDefIdParam || undefined,
						}
					: undefined;

			// Check if workflowId is a UUID (new format) or a name (legacy)
			const isUUID =
				/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
					workflowId,
				);

			// Check if we need to load — composite key includes version info
			const needsLoad = loadedLoadKey !== desiredLoadKey;
			logLoading("Needs load?", {
				needsLoad,
				isUUID,
				loadedLoadKey,
				desiredLoadKey,
				currentGraph: currentGraph?.name,
				workflowId,
			});

			if (needsLoad) {
				// Check if the store already has this graph (e.g., from localStorage rehydration
				// or a just-completed createGraph). If so, skip the loading overlay — the user
				// already sees nodes — but still fetch from the API to ensure correctness.
				const storeGraph = useGraphStore.getState().currentGraph;
				const storeHasGraph =
					storeGraph?.workflow_id === workflowId ||
					(!isUUID && storeGraph?.name === workflowId);

				if (storeHasGraph) {
					logLoading("Store has graph, fetching from API without loading overlay", {
						workflowId,
						storeName: storeGraph?.name,
					});
					// Show content immediately while API loads in the background
					setShowLoading(false);
					setIsReady(true);
					// Dismiss SSR overlay
					try {
						const el = document.getElementById("ssr-workflow-overlay");
						if (el) {
							el.classList.add("fade-out");
							setTimeout(() => {
								document.documentElement.classList.remove(
									"ssr-overlay-active",
								);
							}, 220);
						} else {
							document.documentElement.classList.remove("ssr-overlay-active");
						}
					} catch (e) {}
				}

				if (!storeHasGraph) {
					// Only show loading UI when store has no data
					setShowLoading(true);
					setIsReady(false);
					setLoadingMessage(`Loading workflow: ${workflowId}...`);
				}

				// Only show loading overlay when there's no cached graph data
				const minimumLoadTime = isNewWorkflow ? 1000 : 500;
				const minTimer = storeHasGraph
					? Promise.resolve()
					: new Promise<void>((resolve) =>
							setTimeout(resolve, minimumLoadTime),
						);
				if (!storeHasGraph) {
					showOverlay({
						message: `Loading workflow: ${workflowId}...`,
						minDurationMs: minimumLoadTime,
					});
					logLoading("Overlay shown from WorkflowPage", {
						minimumLoadTime,
						workflowId,
					});
					// Hide SSR overlay immediately once the client overlay is visible
					try {
						const el = document.getElementById("ssr-workflow-overlay");
						if (el) {
							el.classList.add("fade-out");
							setTimeout(() => {
								document.documentElement.classList.remove("ssr-overlay-active");
							}, 120);
						}
					} catch (e) {}
				}

				// Add retry logic for newly created workflows
				let retryCount = 0;
				const maxRetries = isNewWorkflow ? 3 : 1;
				const retryDelay = 1000;

				const tryLoadGraph = async (): Promise<boolean> => {
					try {
						if (isUUID) {
							logLoading("loadGraphByWorkflowId START", {
								workflowId,
								versionOptions,
							});
							await loadGraphByWorkflowId(workflowId, versionOptions);
							logLoading("loadGraphByWorkflowId SUCCESS", { workflowId });
						} else {
							const legacyName = workflowId;
							logLoading("loadGraph START (legacy name)", {
								workflowId: legacyName,
							});
							await loadGraph(legacyName);
							logLoading("loadGraph SUCCESS (legacy name)", {
								workflowId: legacyName,
							});
						}
						return true;
					} catch (err) {
						console.error(
							`Failed to load workflow (attempt ${retryCount + 1}):`,
							err,
						);

						if (retryCount < maxRetries) {
							retryCount++;
							setLoadingMessage(
								`Initializing workflow: ${workflowId}... (attempt ${retryCount + 1})`,
							);
							await new Promise((resolve) => setTimeout(resolve, retryDelay));
							return tryLoadGraph();
						}

						return false;
					}
				};

				const loadedPromise = tryLoadGraph();
				const [loaded] = await Promise.all([loadedPromise, minTimer]);

				if (!loaded) {
					// If all retries failed, show error and redirect
					setLoadingMessage("Workflow not found");
					setTimeout(() => {
						router.push("/");
						hideOverlay();
						try {
							const el = document.getElementById("ssr-workflow-overlay");
							if (el) {
								el.classList.add("fade-out");
								setTimeout(() => {
									document.documentElement.classList.remove(
										"ssr-overlay-active",
									);
								}, 220);
							} else {
								document.documentElement.classList.remove("ssr-overlay-active");
							}
						} catch (e) {}
					}, 1500);
					return;
				}
				// Loading successful and min time elapsed
				logLoading(
					"Workflow loaded and min time elapsed; hiding overlay + showing content",
					{ workflowId },
				);
				setLoadedLoadKey(desiredLoadKey); // Mark this workflow+version as loaded
				setShowLoading(false);
				setIsReady(true);
				if (!storeHasGraph) {
					hideOverlay();
				}
				// Gracefully dismiss SSR overlay (if present) without removing DOM node
				try {
					const el = document.getElementById("ssr-workflow-overlay");
					if (el) {
						el.classList.add("fade-out");
						setTimeout(() => {
							document.documentElement.classList.remove("ssr-overlay-active");
						}, 220);
					} else {
						document.documentElement.classList.remove("ssr-overlay-active");
					}
				} catch (e) {}
			} else {
				// Already loaded — just dismiss SSR overlay if present (F5/refresh case)
				try {
					const el = document.getElementById("ssr-workflow-overlay");
					if (el) {
						el.classList.add("fade-out");
						setTimeout(() => {
							document.documentElement.classList.remove("ssr-overlay-active");
						}, 220);
					} else {
						document.documentElement.classList.remove("ssr-overlay-active");
					}
				} catch (e) {}
				// Ensure content is visible
				setShowLoading(false);
				setIsReady(true);
			}

			setIsInitialMount(false);
		};

		void initWorkflow();
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [
		workflowId,
		loadGraph,
		loadGraphByWorkflowId,
		router,
		showOverlay,
		hideOverlay,
		loadedLoadKey,
		desiredLoadKey,
		versionParam,
		graphDefIdParam,
	]); // Include necessary dependencies

	// Pre-load components once the workflow is loaded
	useEffect(() => {
		if (!showLoading && currentGraph) {
			// Pre-load after a short delay to not impact initial render
			setTimeout(preloadComponents, 100);
		}
	}, [showLoading, currentGraph]);

	// Handle adding workflow to library
	const handleAddToLibrary = async (data: {
		name: string;
		description: string;
		category: string[];
		tags: string[];
		complexity?: string;
		iconColor?: string;
	}) => {
		if (!currentGraph?.workflow_id) {
			showError("No workflow loaded");
			return;
		}

		try {
			const response = await api.addToLibrary({
				workflow_id: currentGraph.workflow_id,
				name: data.name,
				description: data.description,
				category: data.category,
				tags: data.tags,
				complexity: data.complexity,
				icon_color: data.iconColor,
			});

			if (response.success) {
				showSuccess(`"${currentGraph.name}" has been added to the library!`);
				setShowAddToLibrary(false);
			} else {
				showError("Failed to add workflow to library");
			}
		} catch (error) {
			console.error("Failed to add workflow to library:", error);
			showError("Failed to add workflow to library");
		}
	};

	// Always show loading screen first to prevent flash of content
	if (showLoading || !isReady) {
		return (
			<div
				className="fixed inset-0 z-[9999]"
				style={{ background: "var(--color-bg-primary)" }}
			>
				<WorkflowLoading message={loadingMessage} />
			</div>
		);
	}

	// Show error if workflow failed to load (after loading completes)
	if (!currentGraph) {
		return (
			<div
				className="h-screen flex items-center justify-center"
				style={{ background: "var(--color-bg-primary)" }}
			>
				<div className="text-center">
					<h1 className="text-2xl font-bold mb-4" style={{ color: "#D32F2F" }}>
						Workflow Not Found
					</h1>
					<p className="mb-6" style={{ color: "var(--color-text-secondary)" }}>
						Could not load workflow: {workflowId}
					</p>
					<button
						onClick={() => router.push("/")}
						className="px-4 py-2 rounded-lg transition-colors"
						style={{
							background: "var(--color-primary)",
							color: "var(--color-text-primary)",
						}}
					>
						Back to Workflows
					</button>
				</div>
			</div>
		);
	}

	return (
		<main
			className="h-screen flex flex-col relative"
			style={{ background: "var(--color-bg-primary)" }}
		>
			{/* Historical Version Warning Banner */}
			<HistoricalVersionBanner
				workflowId={currentGraph?.workflow_id || workflowId}
			/>

			{/* Tab Content */}
			<div
				className="flex-1 overflow-hidden relative"
				style={{ background: "var(--color-bg-primary)" }}
			>
				<AgentBuilder
					onAddToLibrary={() => setShowAddToLibrary(true)}
					onVersionHistory={() => setShowVersionHistory(true)}
				/>
			</div>

			{/* Graph Management Dialog */}
			{showGraphDialog && (
				<Suspense fallback={null}>
					<GraphManagementDialog
						isOpen={showGraphDialog}
						onClose={() => setShowGraphDialog(false)}
					/>
				</Suspense>
			)}

			{/* Add to Library Dialog */}
			<AddToLibraryDialog
				isOpen={showAddToLibrary}
				workflowId={currentGraph?.workflow_id || null}
				workflowName={currentGraph?.name || null}
				onConfirm={handleAddToLibrary}
				onCancel={() => setShowAddToLibrary(false)}
			/>

			{/* Version History Panel */}
			{currentGraph?.workflow_id && (
				<VersionHistoryPanel
					workflowId={currentGraph.workflow_id}
					isOpen={showVersionHistory}
					onClose={() => setShowVersionHistory(false)}
				/>
			)}
		</main>
	);
}
