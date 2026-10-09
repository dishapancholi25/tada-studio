"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ExternalLink, Loader2, RotateCw, Trash2, Trophy } from "lucide-react";
import Dropdown from "@/components/ui/Dropdown";
import { api } from "@/lib/api";
import * as evalApi from "@/lib/evaluation-api";
import type { EvaluationDataset, EvaluationRun } from "@/lib/evaluation-api";
import { modelDeploymentAPI, type ModelDeploymentOption } from "@/lib/model-deployment-api";
import Pagination from "@/components/ui/Pagination";
import { ScoreBadge, StatusBadge } from "../shared/ScoreBadge";
import { buildModelDropdownOptions, ENVIRONMENT_OPTIONS, FORM_DROPDOWN_TRIGGER_CLASS, nextRerunName } from "../shared/constants";
import EvalHelpButton from "../shared/EvalHelpButton";

export default function RunsListView({ onSelectRun, newRunCutoff, showAllUsers }: { onSelectRun: (id: string) => void; newRunCutoff?: string; showAllUsers?: boolean }) {
	const [runs, setRuns] = useState<EvaluationRun[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [statusFilter, setStatusFilter] = useState("");
	const [triggerFilter, setTriggerFilter] = useState("");
	const [typeFilter, setTypeFilter] = useState("");
	const [workflowFilter, setWorkflowFilter] = useState("");
	const [datasetFilter, setDatasetFilter] = useState("");
	const [datePreset, setDatePreset] = useState("");
	const [customFrom, setCustomFrom] = useState("");
	const [customTo, setCustomTo] = useState("");

	// New Run Modal state
	const [showNewRunModal, setShowNewRunModal] = useState(false);
	const [modalDatasets, setModalDatasets] = useState<EvaluationDataset[]>([]);
	const [modalWorkflows, setModalWorkflows] = useState<{ name: string; workflow_id: string }[]>([]);
	const [runName, setRunName] = useState("");
	const [runDatasetId, setRunDatasetId] = useState("");
	const [runWorkflowId, setRunWorkflowId] = useState("");
	const [runTargetType, setRunTargetType] = useState("workflow");
	const [runEnvironment, setRunEnvironment] = useState("dev");
	const [costW, setCostW] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_default_weight_cost")) || 0.25,
	);
	const [qualityW, setQualityW] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_default_weight_quality")) || 0.25,
	);
	const [reliabilityW, setReliabilityW] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_default_weight_reliability")) || 0.25,
	);
	const [latencyW, setLatencyW] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_default_weight_latency")) || 0.25,
	);
	const [concurrencyLimit, setConcurrencyLimit] = useState(5);
	const [runJudgeModelId, setRunJudgeModelId] = useState(
		() => (typeof window !== "undefined" && localStorage.getItem("eval_default_judge_model")) || "",
	);
	const [runQualityJudgeProvider, setRunQualityJudgeProvider] = useState<"builtin" | "phoenix">(
		() => ((typeof window !== "undefined" && localStorage.getItem("eval_default_quality_judge_provider")) === "phoenix" ? "phoenix" : "builtin"),
	);
	const [submittingRun, setSubmittingRun] = useState(false);

	// Target-type-aware state
	const [runTargetId, setRunTargetId] = useState("");
	const [agentNodes, setAgentNodes] = useState<{ id: string; name: string }[]>([]);
	const [toolNodes, setToolNodes] = useState<{ id: string; name: string; type: string }[]>([]);
	const [nodesLoading, setNodesLoading] = useState(false);

	// Model deployments for judge dropdown
	const [runDeployments, setRunDeployments] = useState<ModelDeploymentOption[]>([]);
	const [runModelsLoading, setRunModelsLoading] = useState(true);

	// Pagination state
	const [currentPage, setCurrentPage] = useState(1);
	const [pageSize, setPageSize] = useState(10);

	// Delete confirmation state
	const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

	// Rerun confirmation state
	const [confirmRerunId, setConfirmRerunId] = useState<string | null>(null);
	const [rerunning, setRerunning] = useState(false);

	// Modal UI state
	const [showAdvanced, setShowAdvanced] = useState(false);
	const [modalTab, setModalTab] = useState<"general" | "scoring-judge">("general");
	const [phoenixEnabled, setPhoenixEnabled] = useState(false);
	const [phoenixEvalFaithfulness, setPhoenixEvalFaithfulness] = useState(true);
	const [phoenixEvalToolSelection, setPhoenixEvalToolSelection] = useState(true);
	const [phoenixEvalLlmJudge, setPhoenixEvalLlmJudge] = useState(false);
	const [phoenixEvalPenaltyEnabled, setPhoenixEvalPenaltyEnabled] = useState(false);
	const [giskardEnabled, setGiskardEnabled] = useState(false);

	// Judge output policy state
	const [judgeOutputStrategy, setJudgeOutputStrategy] = useState<"final_node" | "specific_node" | "all_nodes">(
		() => ((typeof window !== "undefined" && localStorage.getItem("eval_default_judge_strategy")) as any) || "final_node",
	);
	const [judgeOutputNodeId, setJudgeOutputNodeId] = useState("");
	const [judgeMaxOutputChars, setJudgeMaxOutputChars] = useState(
		() => Number(typeof window !== "undefined" && localStorage.getItem("eval_default_max_output_chars")) || 200000,
	);
	const [allGraphNodes, setAllGraphNodes] = useState<{ id: string; name: string }[]>([]);

	// Baseline tracking
	const [baselineRunIds, setBaselineRunIds] = useState<Set<string>>(new Set());

	// Workflow name lookup for the runs table
	const [workflowNameMap, setWorkflowNameMap] = useState<Map<string, string>>(new Map());
	const selectClass = "max-w-[10rem] truncate rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15 hover:border-orange-400 hover:bg-white hover:text-slate-900 transition-all";
	const filterTriggerClass = "min-w-[7rem] max-w-[10rem] rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:border-orange-400 hover:bg-white hover:text-slate-900 transition-all";

	const resetNewRunModalState = useCallback(() => {
		setShowNewRunModal(false);
		setRunName("");
		setRunDatasetId("");
		setRunWorkflowId("");
		setRunTargetId("");
		setAgentNodes([]);
		setToolNodes([]);
		setCostW(Number(localStorage.getItem("eval_default_weight_cost")) || 0.25);
		setQualityW(Number(localStorage.getItem("eval_default_weight_quality")) || 0.25);
		setReliabilityW(Number(localStorage.getItem("eval_default_weight_reliability")) || 0.25);
		setLatencyW(Number(localStorage.getItem("eval_default_weight_latency")) || 0.25);
		setConcurrencyLimit(5);
		setRunJudgeModelId(localStorage.getItem("eval_default_judge_model") || "");
		setShowAdvanced(false);
		setModalTab("general");
		setRunQualityJudgeProvider(
			localStorage.getItem("eval_default_quality_judge_provider") === "phoenix" ? "phoenix" : "builtin",
		);
		setPhoenixEnabled(false);
		setPhoenixEvalFaithfulness(true);
		setPhoenixEvalToolSelection(true);
		setPhoenixEvalLlmJudge(false);
		setPhoenixEvalPenaltyEnabled(false);
		setGiskardEnabled(false);
		setJudgeOutputStrategy(
			((localStorage.getItem("eval_default_judge_strategy")) as any) || "final_node",
		);
		setJudgeOutputNodeId("");
		setJudgeMaxOutputChars(
			Number(localStorage.getItem("eval_default_max_output_chars")) || 200000,
		);
		setAllGraphNodes([]);
	}, []);

	const load = useCallback(async (isPolling = false) => {
		if (!isPolling) {
			setLoading(true);
			setError(null);
		}
		try {
			const list = await evalApi.listRuns({
				status: statusFilter || undefined,
				trigger: triggerFilter || undefined,
				target_type: typeFilter || undefined,
				workflow_id: workflowFilter || undefined,
				show_all: showAllUsers || undefined,
			});
			setRuns(list);
			try {
				const [datasets, graphsRes] = await Promise.all([
					evalApi.listDatasets(),
					api.listGraphs(),
				]);
				setBaselineRunIds(new Set(datasets.flatMap((ds) => ds.baseline_run_id ? [ds.baseline_run_id] : [])));
				const nameMap = new Map<string, string>();
				for (const g of (graphsRes.graphs ?? []) as { workflow_id: string; name: string }[]) {
					nameMap.set(g.workflow_id, g.name);
				}
				setWorkflowNameMap(nameMap);
			} catch {
				setBaselineRunIds(new Set());
			}
		} catch (err: any) {
			if (!isPolling) setError(err.message ?? "Failed to load runs");
		} finally {
			if (!isPolling) setLoading(false);
		}
	}, [statusFilter, triggerFilter, typeFilter, workflowFilter, showAllUsers]);

	useEffect(() => {
		load();
	}, [load]);

	// Re-fetch when the evaluations tutorial finishes creating demo data
	useEffect(() => {
		const handler = () => load();
		window.addEventListener("tutorialEvalDataReady", handler);
		return () => window.removeEventListener("tutorialEvalDataReady", handler);
	}, [load]);

	// Tutorial: open the new run modal
	useEffect(() => {
		const handler = () => {
			handleOpenNewRunModal();
		};
		window.addEventListener("tutorialOpenNewRunModal", handler);
		return () => window.removeEventListener("tutorialOpenNewRunModal", handler);
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	// Build unique workflow options for filter
	const workflowFilterOptions = useMemo(() => {
		const opts: { id: string; label: string }[] = [];
		for (const [id, name] of workflowNameMap.entries()) {
			opts.push({ id, label: name });
		}
		return opts.sort((a, b) => a.label.localeCompare(b.label));
	}, [workflowNameMap]);

	// Fetch all datasets for filter dropdown (independent of filtered runs)
	const [allDatasets, setAllDatasets] = useState<EvaluationDataset[]>([]);
	useEffect(() => {
		evalApi.listDatasets()
			.then(setAllDatasets)
			.catch(() => {});
	}, []);

	const datasetFilterOptions = useMemo(() => {
		return allDatasets.map((d) => ({ id: d.id, label: d.name }));
	}, [allDatasets]);

	// Map dataset_id -> name for table display
	const dsNameMap = useMemo(() => {
		const m = new Map<string, string>();
		for (const d of allDatasets) m.set(d.id, d.name);
		return m;
	}, [allDatasets]);

	// Compute the date cutoff from preset or custom range
	const dateRange = useMemo(() => {
		if (datePreset === "custom") {
			return {
				from: customFrom ? new Date(customFrom) : null,
				to: customTo ? new Date(`${customTo}T23:59:59`) : null,
			};
		}
		if (!datePreset) return null;
		const now = new Date();
		const hours: Record<string, number> = { "24h": 24, "7d": 168, "30d": 720, "90d": 2160 };
		const h = hours[datePreset];
		if (!h) return null;
		return { from: new Date(now.getTime() - h * 3600_000), to: null };
	}, [datePreset, customFrom, customTo]);

	// Client-side filter by target_id and date range
	const filteredRuns = useMemo(() => {
		let result = runs;
		if (datasetFilter) result = result.filter((r) => r.dataset_id === datasetFilter);
		if (dateRange) {
			result = result.filter((r) => {
				if (!r.created_at) return false;
				const d = new Date(r.created_at);
				if (dateRange.from && d < dateRange.from) return false;
				if (dateRange.to && d > dateRange.to) return false;
				return true;
			});
		}
		return result;
	},
		[runs, datasetFilter, dateRange],
	);

	// Reset to page 1 when filters change
	useEffect(() => {
		setCurrentPage(1);
	}, [statusFilter, triggerFilter, typeFilter, workflowFilter, datasetFilter, dateRange]);

	const paginatedRuns = useMemo(() => {
		const start = (currentPage - 1) * pageSize;
		return filteredRuns.slice(start, start + pageSize);
	}, [filteredRuns, currentPage, pageSize]);

	// Fetch model deployments for judge model dropdown
	useEffect(() => {
		let cancelled = false;
		modelDeploymentAPI
			.listSelectOptions()
			.then((deps) => { if (!cancelled) setRunDeployments(deps); })
			.catch(() => {})
			.finally(() => { if (!cancelled) setRunModelsLoading(false); });
		return () => { cancelled = true; };
	}, []);

	const runModelOptions = useMemo(
		() => buildModelDropdownOptions(runDeployments),
		[runDeployments],
	);

	// Fetch agent/tool nodes when workflow + target type changes
	useEffect(() => {
		if (!runWorkflowId || (runTargetType !== "agent" && runTargetType !== "tool")) {
			setAgentNodes([]);
			setToolNodes([]);
			// Still load all nodes for judge output node selector
			if (runWorkflowId) {
				api.getGraphByWorkflowId(runWorkflowId)
					.then((res) => {
						if (!res.success) return;
						const nodes = res.graph.nodes || [];
						const nodeId = (n: any) => n.uniq_id || n.id;
						const excludeTypes = new Set(["START", "END", "CONDITION"]);
						setAllGraphNodes(
							nodes
								.filter((n: any) => !excludeTypes.has(n.type))
								.map((n: any) => ({ id: nodeId(n), name: n.name || nodeId(n) })),
						);
					})
					.catch(() => setAllGraphNodes([]));
			} else {
				setAllGraphNodes([]);
			}
			return;
		}
		let cancelled = false;
		setNodesLoading(true);
		setRunTargetId("");
		api.getGraphByWorkflowId(runWorkflowId)
			.then((res) => {
				if (cancelled || !res.success) return;
				const nodes = res.graph.nodes || [];
				// Backend serializes node ID as `uniq_id`, not `id`
				const nodeId = (n: any) => n.uniq_id || n.id;
				const excludeTypes = new Set(["START", "END", "CONDITION"]);
				setAllGraphNodes(
					nodes
						.filter((n: any) => !excludeTypes.has(n.type))
						.map((n: any) => ({ id: nodeId(n), name: n.name || nodeId(n) })),
				);
				if (runTargetType === "agent") {
					setAgentNodes(
						nodes
							.filter((n) => n.type === "AGENT")
							.map((n) => ({ id: nodeId(n), name: n.name || nodeId(n) })),
					);
				} else {
					const toolTypes = new Set([
						"DOCUMENT_SEARCH", "DATABASE_QUERY", "DATABASE_INSERT", "DATABASE_QUERY_ACTION",
						"HTTP_REQUEST", "HTTP_REQUEST_ACTION", "WEB_SEARCH",
						"MCP_SERVER", "EMAIL_SEND", "FILE_READ", "FILE_WRITE",
					]);
					setToolNodes(
						nodes
							.filter((n) => toolTypes.has(n.type))
							.map((n) => ({ id: nodeId(n), name: n.name || nodeId(n), type: n.type })),
					);
				}
			})
			.catch(() => {
				setAgentNodes([]);
				setToolNodes([]);
				setAllGraphNodes([]);
			})
			.finally(() => { if (!cancelled) setNodesLoading(false); });
		return () => { cancelled = true; };
	}, [runWorkflowId, runTargetType]);

	// Auto-polling for active runs
	useEffect(() => {
		const hasActiveRuns = runs.some(
			(r) => r.status === "pending" || r.status === "running",
		);
		if (!hasActiveRuns) return;

		const interval = setInterval(() => {
			load(true);
		}, 5000);

		return () => clearInterval(interval);
	}, [runs, load]);

	const handleOpenNewRunModal = async () => {
		setShowNewRunModal(true);
		try {
			const [ds, wfRes] = await Promise.all([
				evalApi.listDatasets(),
				api.listGraphs(),
			]);
			setModalDatasets(ds);
			if (wfRes.success && wfRes.graphs) {
				setModalWorkflows(wfRes.graphs);
			}
		} catch {
			// modal will show empty lists
		}
	};

	const handleSubmitRun = async () => {
		if (!runDatasetId) return;
		// Validate required fields per target type
		const needsWorkflow = runTargetType === "workflow" || runTargetType === "agent" || runTargetType === "tool";
		const needsTargetId = runTargetType === "agent" || runTargetType === "model" || runTargetType === "tool";
		if (needsWorkflow && !runWorkflowId.trim()) return;
		if (needsTargetId && !runTargetId) return;

		setSubmittingRun(true);
		setError(null);
		try {
			const body: evalApi.CreateRunBody = {
				name: runName.trim() || undefined,
				dataset_id: runDatasetId,
				target_type: runTargetType,
				trigger: "manual",
				environment: runEnvironment,
				pillar_weights: {
					cost: costW,
					quality: qualityW,
					reliability: reliabilityW,
					latency: latencyW,
				},
				concurrency_limit: concurrencyLimit,
				...(runJudgeModelId ? { judge_model_config: { model_deployment_id: runJudgeModelId } } : {}),
				judge_output_policy: {
					strategy: judgeOutputStrategy,
					...(judgeOutputStrategy === "specific_node" && judgeOutputNodeId ? { node_id: judgeOutputNodeId } : {}),
					...(judgeMaxOutputChars !== 200000 ? { max_output_chars: judgeMaxOutputChars } : {}),
				},
				quality_judge_provider: runQualityJudgeProvider,
				external_integration_config: {
					...(phoenixEnabled ? {
						phoenix: {
							enabled: true,
							eval_faithfulness_enabled: phoenixEvalFaithfulness,
							eval_tool_selection_enabled: phoenixEvalToolSelection,
							eval_llm_judge_enabled: phoenixEvalLlmJudge,
							eval_penalty_enabled: phoenixEvalPenaltyEnabled,
						},
					} : {}),
					giskard: { enabled: giskardEnabled && (runTargetType === "agent" || runTargetType === "model") },
				},
			};
			if (needsWorkflow) body.workflow_id = runWorkflowId.trim();
			if (needsTargetId) body.target_id = runTargetId;
			const createdRun = await evalApi.createRun(body);
			// If created during the tutorial, stash the run ID for cleanup and detail view
			const evalData = (window as any).__tutorialEvalData;
			if (evalData && createdRun?.id) {
				evalData.runId = createdRun.id;
			}
			resetNewRunModalState();
			await load();
		} catch (err: any) {
			setError(err.message ?? "Failed to create run");
		} finally {
			setSubmittingRun(false);
		}
	};

	// Tutorial: submit the new run
	const handleSubmitRunRef = useRef(handleSubmitRun);
	handleSubmitRunRef.current = handleSubmitRun;
	useEffect(() => {
		const handler = () => handleSubmitRunRef.current();
		window.addEventListener("tutorialSubmitNewRun", handler);
		return () => window.removeEventListener("tutorialSubmitNewRun", handler);
	}, []);

	// Tutorial: fill all new-run form fields at once
	useEffect(() => {
		const handler = (e: Event) => {
			const name = (e as CustomEvent).detail?.name ?? "Tutorial Baseline Run";
			setRunName(name);

			const evalData = (window as any).__tutorialEvalData as
				| { workflowName?: string; datasetId?: string }
				| undefined;
			if (evalData?.workflowName) {
				const wf = modalWorkflows.find((w) => w.name === evalData.workflowName);
				if (wf) {
					setRunWorkflowId(wf.workflow_id);
					if (evalData.datasetId) {
						// Small delay so dataset list reloads after workflow selection
						setTimeout(() => setRunDatasetId(evalData.datasetId!), 300);
					}
				}
			}
		};
		window.addEventListener("tutorialFillNewRunForm", handler);
		return () => window.removeEventListener("tutorialFillNewRunForm", handler);
	}, [modalWorkflows]);

	const handleDeleteRun = async (id: string) => {
		try {
			await evalApi.deleteRun(id);
			setConfirmDeleteId(null);
			await load();
		} catch (err: any) {
			setError(err.message ?? "Failed to delete run");
			setConfirmDeleteId(null);
		}
	};

	const handleRerun = async (id: string) => {
		const sourceRun = runs.find((r) => r.id === id);
		if (!sourceRun) return;
		setRerunning(true);
		setError(null);
		try {
			const body: evalApi.CreateRunBody = {
				name: nextRerunName(sourceRun.name),
				dataset_id: sourceRun.dataset_id ?? "",
				target_type: sourceRun.target_type ?? "workflow",
				trigger: "manual",
				environment: sourceRun.environment ?? "dev",
				pillar_weights: sourceRun.pillar_weights ?? undefined,
				concurrency_limit: sourceRun.concurrency_limit ?? undefined,
				judge_model_config: sourceRun.judge_model_config ?? undefined,
				judge_output_policy: sourceRun.judge_output_policy as evalApi.CreateRunBody["judge_output_policy"],
				external_integration_config: sourceRun.external_integration_config ?? undefined,
			};
			if (sourceRun.workflow_id) body.workflow_id = sourceRun.workflow_id;
			if (sourceRun.target_id) body.target_id = sourceRun.target_id;
			await evalApi.createRun(body);
			setConfirmRerunId(null);
			await load();
		} catch (err: any) {
			setError(err.message ?? "Failed to rerun evaluation");
		} finally {
			setRerunning(false);
		}
	};

	const weightSum = costW + qualityW + reliabilityW + latencyW;
	const weightsValid = Math.abs(weightSum - 1.0) <= 0.01;

	return (
		<div data-tutorial="eval-runs-list" className="h-full flex flex-col gap-4 min-h-0">
			{/* Filters + action buttons */}
			<div className="rounded-2xl border border-slate-200 bg-white p-4">
				<div className="flex min-w-[8rem] flex-1 flex-wrap items-center gap-2">
				<Dropdown
					value={statusFilter}
					onChange={setStatusFilter}
					options={[
						{ value: "", label: "All statuses" },
						{ value: "pending", label: "Pending" },
						{ value: "running", label: "Running" },
						{ value: "completed", label: "Completed" },
						{ value: "completed_with_failures", label: "Completed with failures" },
						{ value: "failed", label: "Failed" },
					]}
					width="trigger"
					triggerClassName={filterTriggerClass}
					menuAppearance="light"
				/>
				<Dropdown
					value={triggerFilter}
					onChange={setTriggerFilter}
					options={[
						{ value: "", label: "All triggers" },
						{ value: "manual", label: "Manual" },
						{ value: "on_publish", label: "On Publish" },
						{ value: "on_modify", label: "On Modify" },
						{ value: "scheduled", label: "Scheduled" },
					]}
					width="trigger"
					triggerClassName={filterTriggerClass}
					menuAppearance="light"
				/>
				<Dropdown
					value={typeFilter}
					onChange={setTypeFilter}
					options={[
						{ value: "", label: "All types" },
						{ value: "workflow", label: "Workflow" },
						{ value: "agent", label: "Agent" },
						{ value: "model", label: "Model" },
						{ value: "tool", label: "Tool" },
					]}
					width="trigger"
					triggerClassName={filterTriggerClass}
					menuAppearance="light"
				/>
				<Dropdown
					value={datePreset}
					onChange={(v) => {
						setDatePreset(v);
						if (v !== "custom") {
							setCustomFrom("");
							setCustomTo("");
						}
					}}
					options={[
						{ value: "", label: "All time" },
						{ value: "24h", label: "Last 24 hours" },
						{ value: "7d", label: "Last 7 days" },
						{ value: "30d", label: "Last 30 days" },
						{ value: "90d", label: "Last 90 days" },
						{ value: "custom", label: "Custom range" },
					]}
					width="trigger"
					triggerClassName={filterTriggerClass}
					menuAppearance="light"
				/>
				{datePreset === "custom" && (
					<>
						<input
							type="date"
							value={customFrom}
							onChange={(e) => setCustomFrom(e.target.value)}
							title={customFrom || "From"}
							className={selectClass}
							placeholder="From"
						/>
						<span className="text-xs text-slate-500">to</span>
						<input
							type="date"
							value={customTo}
							onChange={(e) => setCustomTo(e.target.value)}
							title={customTo || "To"}
							className={selectClass}
							placeholder="To"
						/>
					</>
				)}
				{workflowFilterOptions.length > 0 && (
					<Dropdown
						value={workflowFilter}
						onChange={setWorkflowFilter}
						options={[{ value: "", label: "All workflows" }, ...workflowFilterOptions.map((opt) => ({ value: opt.id, label: opt.label }))]}
						width="trigger"
						triggerClassName={filterTriggerClass}
						menuAppearance="light"
					/>
				)}
				{datasetFilterOptions.length > 0 && (
					<Dropdown
						value={datasetFilter}
						onChange={setDatasetFilter}
						options={[{ value: "", label: "All datasets" }, ...datasetFilterOptions.map((opt) => ({ value: opt.id, label: opt.label }))]}
						width="trigger"
						triggerClassName={filterTriggerClass}
						menuAppearance="light"
					/>
				)}
				</div>

				<div className="mt-3 flex flex-wrap items-center gap-3">
					<button
						type="button"
						onClick={() => load()}
						className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
					>
						↻ Refresh
					</button>
					<button
						type="button"
						data-tutorial="new-run-btn"
						onClick={handleOpenNewRunModal}
						className="rounded-xl border border-orange-500 bg-orange-500 px-4 py-1.5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-all hover:border-orange-600 hover:bg-orange-600 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
					>
						New Run
					</button>
				</div>
			</div>

			{error && <p className="text-sm text-red-400">{error}</p>}

			{loading ? (
				<p className="rounded-2xl border border-slate-200 bg-white py-10 text-center text-sm text-slate-500 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">Loading runs…</p>
			) : filteredRuns.length === 0 ? (
				<p className="rounded-2xl border border-slate-200 bg-white py-10 text-center text-sm text-slate-500 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">No evaluation runs found.</p>
			) : (
				<div className="flex-1 flex flex-col rounded-2xl border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)] overflow-hidden min-h-0">
					<div className="flex-1 overflow-auto min-h-0">
					<table className="w-full text-left text-sm">
						<thead className="sticky top-0 bg-white z-10">
							<tr className="border-b border-slate-200 bg-white text-xs uppercase text-slate-500">
								<th className="pb-2 pr-4 pt-3 pl-4 min-w-[220px]">Name</th>
								<th className="pb-2 pr-4 pt-3">Workflow</th>
								<th className="pb-2 pr-4 pt-3">Version</th>
								<th className="pb-2 pr-4 pt-3">Dataset</th>
								<th className="pb-2 pr-4 pt-3">Type</th>
								<th className="pb-2 pr-4 pt-3">Status</th>
								<th className="pb-2 pr-4 pt-3">Trigger</th>
								<th className="pb-2 pr-4 pt-3">Score</th>
								<th className="pb-2 pr-4 pt-3">Cases</th>
								<th className="pb-2 pr-4 pt-3">Created</th>
								{showAllUsers && <th className="pb-2 pr-4 pt-3">User</th>}
								<th className="pb-2 pt-3" />
							</tr>
						</thead>
						<tbody>
							{paginatedRuns.map((run, runIdx) => {
								const wfId = run.workflow_id || (run.target_type === "workflow" ? run.target_id : null);
								const wfName = run.workflow_name ?? (wfId ? workflowNameMap.get(wfId) : null);
								return (
								<tr
									key={run.id}
									data-tutorial={runIdx === 0 ? "eval-run-first" : undefined}
									data-tutorial-run-status={runIdx === 0 ? run.status : undefined}
									onClick={() => onSelectRun(run.id)}
									className="cursor-pointer border-b border-slate-100 hover:bg-white hover:text-slate-900"
								>
									<td className="py-2.5 pr-4 pl-4 text-slate-900 min-w-[220px]">
										<span className="inline-flex items-center gap-1.5">
											{newRunCutoff && run.completed_at && run.completed_at > newRunCutoff && (
												<span className="inline-block h-2 w-2 rounded-full bg-blue-400 shrink-0" title="New since your last visit" />
											)}
											{run.name ?? run.id.slice(0, 8)}
										</span>
										{baselineRunIds.has(run.id) && <span title="Baseline run"><Trophy size={12} className="inline ml-1.5 text-amber-400" /></span>}
									</td>
									<td className="py-2.5 pr-4">
										{wfId ? (
											<a
												href={`/workflow/${encodeURIComponent(wfId)}${run.graph_version != null && run.graph_definition_id ? `?version=${run.graph_version}&graph_definition_id=${run.graph_definition_id}` : ""}`}
												target="_blank"
												rel="noopener noreferrer"
												onClick={(e) => e.stopPropagation()}
												className="inline-flex items-center gap-1 text-xs text-[rgba(var(--color-primary-rgb),0.75)] transition hover:text-[rgba(var(--color-primary-rgb),1)] hover:underline"
												title={run.graph_version != null ? `Open version ${run.graph_version} in editor` : "Open in editor"}
											>
												{wfName ?? wfId.slice(0, 10)}
												<ExternalLink size={10} />
											</a>
										) : (
											<span className="text-slate-400">—</span>
										)}
									</td>
									<td className="py-2.5 pr-4">
										{run.graph_version != null ? (
											<span className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[11px] font-mono text-slate-600">
												v{run.graph_version}
											</span>
										) : (
											<span className="text-slate-400">—</span>
										)}
									</td>
									<td className="py-2.5 pr-4 text-xs">
										{run.dataset_id ? (
											<a
												href={`/evaluations?tab=datasets&dataset=${encodeURIComponent(run.dataset_id)}`}
												onClick={(e) => e.stopPropagation()}
												className="inline-flex items-center gap-1 text-[rgba(var(--color-primary-rgb),0.75)] transition hover:text-[rgba(var(--color-primary-rgb),1)] hover:underline"
												title="Open dataset"
											>
												{run.dataset_name ?? dsNameMap.get(run.dataset_id) ?? run.dataset_id.slice(0, 10)}
											</a>
										) : (
											<span className="text-slate-400">—</span>
										)}
									</td>
									<td className="py-2.5 pr-4">
										{run.target_type ? (
											<span className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[11px] capitalize text-slate-600">
												{run.target_type}
											</span>
										) : (
											<span className="text-slate-400">—</span>
										)}
									</td>
									<td className="py-2.5 pr-4">
										<StatusBadge status={run.status} />
									</td>
									<td className="py-2.5 pr-4 text-slate-600">{run.trigger ?? "—"}</td>
									<td className="py-2.5 pr-4">
										<ScoreBadge value={run.composite_score} />
									</td>
									<td className="py-2.5 pr-4 text-slate-600">
										{run.completed_cases ?? 0}{run.failed_cases ? <span className="text-red-400/70">+{run.failed_cases}</span> : ""}/{run.total_cases}
									</td>
									<td className="py-2.5 pr-4 text-slate-500">
										{run.created_at ? new Date(run.created_at).toLocaleDateString() : "—"}
									</td>
									{showAllUsers && (
										<td className="py-2.5 pr-4 text-xs text-slate-500" title={run.triggered_by_email ?? undefined}>
											{run.triggered_by_name ?? run.triggered_by_email ?? run.triggered_by_user_id?.slice(0, 8) ?? "—"}
										</td>
									)}
									<td className="py-2.5 text-right">
										<div className="inline-flex items-center gap-1">
											<button
												type="button"
												onClick={(e) => {
													e.stopPropagation();
													setConfirmRerunId(run.id);
												}}
												className="rounded-xl p-2 text-[color:var(--color-text-muted)] transition-all hover:text-[rgba(var(--color-primary-rgb),1)] hover:bg-[rgba(var(--color-primary-rgb),0.10)] border border-transparent hover:border-[rgba(var(--color-primary-rgb),0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
												title="Rerun evaluation"
											>
												<RotateCw size={14} />
											</button>
											<button
												type="button"
												onClick={(e) => {
													e.stopPropagation();
													setConfirmDeleteId(run.id);
												}}
												className="rounded-xl p-2 text-[color:var(--color-text-muted)] transition-all hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/45"
												title="Delete run"
											>
												<Trash2 size={14} />
											</button>
										</div>
									</td>
								</tr>
								);
							})}
						</tbody>
					</table>
					</div>

					<div className="border-t border-slate-200 bg-white">
						{!loading && filteredRuns.length > 0 && (
							<Pagination
								currentPage={currentPage}
								totalCount={filteredRuns.length}
								pageSize={pageSize}
								onPageChange={setCurrentPage}
								onPageSizeChange={(size) => { setPageSize(size); setCurrentPage(1); }}
								pageSizeOptions={[10, 20, 50]}
							/>
						)}
					</div>
				</div>
			)}

			{/* New Run Modal */}
			{showNewRunModal && (
				<div className="fixed inset-0 z-[100] flex items-start justify-center bg-black/60 backdrop-blur-sm pt-[5vh]">
					<div className="relative flex w-full max-w-lg flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(4,7,17,0.15)]" style={{ maxHeight: "90vh" }} data-tutorial="new-run-modal">
						<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
						<div className="flex items-center justify-between mb-4">
							<div className="flex items-center gap-2">
								<h3 className="text-base font-semibold text-slate-900">New Evaluation Run</h3>
								<EvalHelpButton topic="new-run" />
							</div>
							<button
								type="button"
								onClick={resetNewRunModalState}
								className="flex h-8 w-8 items-center justify-center rounded-xl text-slate-500 transition-all hover:text-slate-900 hover:bg-white border border-transparent hover:border-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
							>
								✕
							</button>
						</div>

						{/* Tab bar */}
						<div className="flex gap-1 rounded-lg border border-slate-200 bg-white p-1 mb-4 shrink-0" data-tutorial="new-run-modal-tabs">
								{(["general", "scoring-judge"] as const).map((t) => (
									<button
										key={t}
										type="button"
										data-tutorial={`new-run-tab-${t}`}
										onClick={() => setModalTab(t)}
										className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
											modalTab === t
												? "bg-orange-500 text-white"
												: "text-slate-600 hover:text-slate-900"
										}`}
									>
										{t === "general" ? "General" : "Evaluations"}
										{t === "scoring-judge" && !weightsValid && (
											<span className="ml-1.5 inline-block h-1.5 w-1.5 rounded-full bg-amber-400" />
										)}
									</button>
								))}
							</div>

						<div className="min-h-0 flex-1 overflow-y-auto space-y-4">
							{/* General tab */}
							{modalTab === "general" && (
								<div className="space-y-4" data-tutorial="new-run-general-content">
							<div>
								<label className="mb-1 block text-xs text-slate-500">Run Name (optional)</label>
								<input
									type="text"
									data-tutorial="run-name-input"
									value={runName}
									onChange={(e) => setRunName(e.target.value)}
									placeholder="e.g. Riddler Test — Initial Evaluation"
									className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 hover:border-orange-400 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15 transition-all"
								/>
							</div>

							<div className="flex gap-3">
								<div className="flex-1">
									<label className="mb-1 block text-xs text-slate-500">Target Type</label>
									<Dropdown
										value={runTargetType}
										onChange={(v) => {
											setRunTargetType(v);
											setRunTargetId("");
											setRunWorkflowId("");
											setRunDatasetId("");
											setAgentNodes([]);
											setToolNodes([]);
										}}
										options={[
											{ value: "workflow", label: "Workflow" },
											{ value: "agent", label: "Agent" },
											{ value: "model", label: "Model" },
											{ value: "tool", label: "Tool" },
										]}
										width="trigger"
										className="w-full"
										triggerClassName={FORM_DROPDOWN_TRIGGER_CLASS}
										menuAppearance="light"
									/>
								</div>
								<div className="flex-1">
									<label className="mb-1 block text-xs text-slate-500">Environment</label>
									<Dropdown
										value={runEnvironment}
										onChange={setRunEnvironment}
										options={ENVIRONMENT_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
										width="trigger"
										className="w-full"
										triggerClassName={FORM_DROPDOWN_TRIGGER_CLASS}
										menuAppearance="light"
									/>
								</div>
							</div>

							{/* Workflow selector — shown for workflow, agent, tool */}
							{(runTargetType === "workflow" || runTargetType === "agent" || runTargetType === "tool") && (
								<div data-tutorial="run-workflow-selector">
									<label className="mb-1 block text-xs text-slate-500">Workflow</label>
									<Dropdown
										value={runWorkflowId}
										onChange={(v) => {
											setRunWorkflowId(v);
											setRunDatasetId("");
										}}
										options={[{ value: "", label: "Select a workflow…" }, ...modalWorkflows.map((wf) => ({ value: wf.workflow_id, label: wf.name }))]}
										width="trigger"
										className="w-full"
										triggerClassName={FORM_DROPDOWN_TRIGGER_CLASS}
										menuAppearance="light"
									/>
								</div>
							)}

							{/* Agent node selector */}
							{runTargetType === "agent" && runWorkflowId && (
								<div>
									<label className="mb-1 block text-xs text-slate-500">Agent Node</label>
									{nodesLoading ? (
										<div className="flex items-center gap-2 rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
											<Loader2 className="h-3.5 w-3.5 animate-spin" />
											Loading agent nodes...
										</div>
									) : agentNodes.length > 0 ? (
										<Dropdown
											value={runTargetId}
											onChange={(v) => {
												setRunTargetId(v);
												setRunDatasetId("");
											}}
											options={[{ value: "", label: "Select an agent…" }, ...agentNodes.map((n) => ({ value: n.id, label: n.name }))]}
											width="trigger"
											className="w-full"
											triggerClassName="w-full border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 hover:bg-[color:var(--color-surface)]/80 hover:border-[rgba(var(--color-primary-rgb),0.4)] text-[color:var(--color-text-primary)]"
											menuAppearance="light"
										/>
									) : (
										<p className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
											No agent nodes found in this workflow.
										</p>
									)}
								</div>
							)}

							{/* Tool node selector */}
							{runTargetType === "tool" && runWorkflowId && (
								<div>
									<label className="mb-1 block text-xs text-slate-500">Tool Node</label>
									{nodesLoading ? (
										<div className="flex items-center gap-2 rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
											<Loader2 className="h-3.5 w-3.5 animate-spin" />
											Loading tool nodes...
										</div>
									) : toolNodes.length > 0 ? (
										<Dropdown
											value={runTargetId}
											onChange={(v) => {
												setRunTargetId(v);
												setRunDatasetId("");
											}}
											options={[{ value: "", label: "Select a tool…" }, ...toolNodes.map((n) => ({ value: n.id, label: `${n.name} (${n.type})` }))]}
											width="trigger"
											className="w-full"
											triggerClassName="w-full border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 hover:bg-[color:var(--color-surface)]/80 hover:border-[rgba(var(--color-primary-rgb),0.4)] text-[color:var(--color-text-primary)]"
											menuAppearance="light"
										/>
									) : (
										<p className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
											No tool nodes found in this workflow.
										</p>
									)}
								</div>
							)}

							{/* Model deployment selector */}
							{runTargetType === "model" && (
								<div>
									<label className="mb-1 block text-xs text-slate-500">Model Deployment</label>
									{runModelsLoading ? (
										<div className="flex items-center gap-2 rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
											<Loader2 className="h-3.5 w-3.5 animate-spin" />
											Loading models...
										</div>
									) : runModelOptions.length > 0 ? (
										<Dropdown
											value={runTargetId}
											onChange={(v) => {
												setRunTargetId(v);
												setRunDatasetId("");
											}}
											options={runModelOptions}
											placeholder="Select a model deployment…"
											className="w-full"
											triggerClassName="border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 hover:bg-[color:var(--color-surface)]/80 hover:border-[rgba(var(--color-primary-rgb),0.4)] text-[color:var(--color-text-primary)]"
										/>
									) : (
										<p className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
											No model deployments configured.
										</p>
									)}
								</div>
							)}

							<div data-tutorial="run-dataset-selector">
								<label className="mb-1 block text-xs text-slate-500">Dataset</label>
								{(() => {
									const effectiveTargetId =
										runTargetType === "workflow" ? runWorkflowId : runTargetId;
									const selectedWorkflowName =
										runTargetType === "workflow"
											? modalWorkflows.find((w) => w.workflow_id === runWorkflowId)?.name
											: undefined;
									const filtered = modalDatasets.filter(
										(ds) =>
											ds.target_type === runTargetType &&
											(!ds.target_id ||
												ds.target_id === effectiveTargetId ||
												(runTargetType === "workflow" &&
													selectedWorkflowName &&
													ds.workflow_name === selectedWorkflowName)),
									);
									return (
										<Dropdown
											value={runDatasetId}
											onChange={setRunDatasetId}
											options={[
												{ value: "", label: filtered.length === 0 ? "No datasets for this target" : "Select a dataset…" },
												...filtered.map((ds) => ({ value: ds.id, label: `${ds.name} (${ds.test_case_count} cases)` })),
											]}
											width="trigger"
											className="w-full"
											triggerClassName="w-full border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 hover:bg-[color:var(--color-surface)]/80 hover:border-[rgba(var(--color-primary-rgb),0.4)] text-[color:var(--color-text-primary)]"
											menuAppearance="light"
										/>
									);
								})()}
							</div>

							{/* External Integrations */}
							<div className="rounded-lg border border-slate-200 bg-slate-50">
								<button
									type="button"
									onClick={() => setShowAdvanced((v) => !v)}
									className="flex w-full items-center gap-2 px-4 py-3 text-sm text-slate-600 transition hover:text-slate-700"
								>
									<span className="text-xs">{showAdvanced ? "▼" : "▶"}</span>
									External Integrations
								</button>
								{showAdvanced && (
									<div className="space-y-3 px-4 pb-4">
										<div className="flex items-center justify-between">
											<div>
												<p className="text-sm text-slate-700">Phoenix supplementary evaluations</p>
												<p className="text-[10px] text-slate-400 mt-0.5">Run additional LLM-based evaluations via Phoenix (faithfulness, tool selection)</p>
											</div>
											<button
												type="button"
												role="switch"
												aria-checked={phoenixEnabled}
												onClick={() => setPhoenixEnabled((v) => !v)}
												className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
													phoenixEnabled ? "bg-violet-600" : "bg-slate-100"
												}`}
											>
												<span
													className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
														phoenixEnabled ? "translate-x-6" : "translate-x-1"
													}`}
												/>
											</button>
										</div>
										{phoenixEnabled && (
											<div className="ml-1 space-y-2 border-l-2 border-slate-200 pl-3">
												<label className="flex items-center gap-2 text-sm text-slate-700">
													<input
														type="checkbox"
														checked={phoenixEvalFaithfulness}
														onChange={(e) => setPhoenixEvalFaithfulness(e.target.checked)}
														className="accent-violet-500"
													/>
													Faithfulness
													<span className="text-[10px] text-slate-400">Checks output against retrieved context</span>
												</label>
												<label className="flex items-center gap-2 text-sm text-slate-700">
													<input
														type="checkbox"
														checked={phoenixEvalToolSelection}
														onChange={(e) => setPhoenixEvalToolSelection(e.target.checked)}
														className="accent-violet-500"
													/>
													Tool Selection
													<span className="text-[10px] text-slate-400">Evaluates tool choice quality</span>
												</label>
												<label className="flex items-center gap-2 text-sm text-slate-700">
													<input
														type="checkbox"
														checked={phoenixEvalLlmJudge}
														onChange={(e) => setPhoenixEvalLlmJudge(e.target.checked)}
														className="accent-violet-500"
													/>
													LLM Judge
													<span className="text-[10px] text-slate-400">Phoenix LLM judge for comparison with built-in judge</span>
												</label>
												<label className="flex items-center gap-2 text-sm text-slate-700">
													<input
														type="checkbox"
														checked={phoenixEvalPenaltyEnabled}
														onChange={(e) => setPhoenixEvalPenaltyEnabled(e.target.checked)}
														className="accent-violet-500"
													/>
													Eval Quality Penalty
													<span className="text-[10px] text-slate-400">Penalise quality score on low faithfulness</span>
												</label>
											</div>
										)}
										{(runTargetType === "agent" || runTargetType === "model") && (
											<div className="flex items-center justify-between">
												<p className="text-sm text-slate-700">Run Giskard safety scan</p>
												<button
													type="button"
													role="switch"
													aria-checked={giskardEnabled}
													onClick={() => setGiskardEnabled((v) => !v)}
													className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
														giskardEnabled ? "bg-violet-600" : "bg-slate-100"
													}`}
												>
													<span
														className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
															giskardEnabled ? "translate-x-6" : "translate-x-1"
														}`}
													/>
												</button>
											</div>
										)}
										<p className="text-[11px] text-slate-400">Requires Phoenix/Giskard to be installed and configured. OTel traces are sent to Phoenix automatically when tracing is enabled globally.</p>
									</div>
								)}
							</div>

							{/* Concurrency */}
							<div>
								<label className="mb-1 block text-xs text-slate-500">
									Concurrency Limit: {concurrencyLimit}
								</label>
								<input
									type="range"
									min={1}
									max={10}
									value={concurrencyLimit}
									onChange={(e) => setConcurrencyLimit(Number(e.target.value))}
									className="w-full accent-violet-500"
								/>
							</div>
								</div>
							)}

							{/* Evaluations tab */}
							{modalTab === "scoring-judge" && (
								<div className="space-y-4" data-tutorial="new-run-scoring-content">
							{/* Pillar weights */}
							<div>
								<p className="mb-2 text-xs text-slate-500">Pillar Weights</p>
								{!weightsValid && (
									<p className="mb-2 text-xs text-amber-400">
										Weights must sum to 1.0 (currently {weightSum.toFixed(2)})
									</p>
								)}
								<div className="grid grid-cols-2 gap-3">
									{[
										{ label: "Cost", value: costW, set: setCostW },
										{ label: "Quality", value: qualityW, set: setQualityW },
										{ label: "Reliability", value: reliabilityW, set: setReliabilityW },
										{ label: "Latency", value: latencyW, set: setLatencyW },
									].map(({ label, value, set }) => (
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
												onChange={(e) => set(Number(e.target.value))}
												className="w-full accent-violet-500"
											/>
										</div>
									))}
								</div>
							</div>

							{/* Quality Judge Provider */}
							<div>
								<p className="mb-1.5 text-xs text-slate-500">Quality Judge Provider</p>
								<div className="flex gap-1 rounded-lg bg-slate-100 p-1">
									{(["builtin", "phoenix"] as const).map((p) => (
										<button
											key={p}
											type="button"
											onClick={() => setRunQualityJudgeProvider(p)}
											className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
												runQualityJudgeProvider === p
													? "bg-slate-100 text-slate-900 shadow-sm"
													: "text-slate-500 hover:text-slate-600"
											}`}
										>
											{p === "builtin" ? "Built-in Judge" : "Phoenix LLM Judge"}
										</button>
									))}
								</div>
								<p className="mt-1 text-[11px] text-slate-400">
									{runQualityJudgeProvider === "builtin"
										? "Uses the built-in LLM-as-a-judge for quality scoring."
										: "Uses Phoenix LLMEvaluator for quality scoring. Requires Phoenix to be enabled."}
								</p>
							</div>

							{/* Evaluations Model */}
							<div>
								<label className="mb-1.5 block text-xs text-slate-500">Evaluations Model (optional)</label>
								{runModelsLoading ? (
									<div className="flex items-center gap-2 rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
										<Loader2 className="h-3.5 w-3.5 animate-spin" />
										Loading models...
									</div>
								) : runModelOptions.length > 0 ? (
									<Dropdown
										value={runJudgeModelId}
										onChange={setRunJudgeModelId}
										options={[{ value: "", label: "System Default", description: "Use the platform default model" }, ...runModelOptions]}
										placeholder="System Default"
										className="w-full"
										triggerClassName="border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 hover:bg-[color:var(--color-surface)]/80 hover:border-[rgba(var(--color-primary-rgb),0.4)] text-[color:var(--color-text-primary)]"
									/>
								) : (
									<p className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
										No model deployments configured.
									</p>
								)}
								<p className="mt-1 text-[11px] text-slate-400">LLM used for quality judging and Phoenix evaluations. Leave empty for system default.</p>
							</div>

							{/* Judge Output Policy */}
							<div>
								<p className="mb-2 text-xs text-slate-500">Judge Output Policy</p>
								<div className="space-y-3">
									<div>
										<label className="mb-1.5 block text-xs text-slate-500">What to evaluate</label>
										<Dropdown
											value={judgeOutputStrategy}
											onChange={(v) => {
												setJudgeOutputStrategy(v as any);
												if (v !== "specific_node") setJudgeOutputNodeId("");
											}}
											options={[
												{ value: "final_node", label: "Final node output (recommended)" },
												{ value: "specific_node", label: "Specific node output" },
												{ value: "all_nodes", label: "All node outputs" },
											]}
											width="trigger"
											className="w-full"
											triggerClassName="w-full border border-slate-200 bg-slate-100 hover:bg-slate-100 text-slate-900"
											menuAppearance="light"
										/>
										<p className="mt-1 text-[11px] text-slate-400">
											{judgeOutputStrategy === "final_node" && "Sends only the last node's response to the judge. Best for most workflows."}
											{judgeOutputStrategy === "specific_node" && "Sends the output of a specific node. Useful when the answer comes from a mid-workflow node."}
											{judgeOutputStrategy === "all_nodes" && "Sends all node outputs. Uses more tokens but gives the judge full context."}
										</p>
									</div>

									{judgeOutputStrategy === "specific_node" && (
										<div>
											<label className="mb-1.5 block text-xs text-slate-500">Node to evaluate</label>
											{allGraphNodes.length > 0 ? (
												<Dropdown
													value={judgeOutputNodeId}
													onChange={setJudgeOutputNodeId}
													options={[{ value: "", label: "Select a node…" }, ...allGraphNodes.map((n) => ({ value: n.id, label: n.name }))]}
													width="trigger"
													className="w-full"
													triggerClassName="w-full border border-slate-200 bg-slate-100 hover:bg-slate-100 text-slate-900"
													menuAppearance="light"
												/>
											) : (
												<p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-400">
													{runWorkflowId ? "No nodes found in workflow" : "Select a workflow first"}
												</p>
											)}
										</div>
									)}

									<div>
										<label className="mb-1 flex items-center justify-between text-xs text-slate-500">
											<span>Max output chars for judge</span>
											<span className="tabular-nums text-slate-700">{judgeMaxOutputChars >= 1000 ? `${Math.round(judgeMaxOutputChars / 1000)}k` : judgeMaxOutputChars}</span>
										</label>
										<input
											type="range"
											min={10000}
											max={500000}
											step={10000}
											value={judgeMaxOutputChars}
											onChange={(e) => setJudgeMaxOutputChars(Number(e.target.value))}
											className="w-full accent-violet-500"
										/>
										<div className="flex justify-between text-[10px] text-slate-300">
											<span>10k</span>
											<span>200k (default)</span>
											<span>500k</span>
										</div>
									</div>
								</div>
							</div>
								</div>
							)}
						</div>

						<div className="mt-6 flex shrink-0 justify-end gap-2">
							<button
								type="button"
								onClick={resetNewRunModalState}
								className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
							>
								Cancel
							</button>
							<button
								type="button"
								data-tutorial="new-run-submit-btn"
								onClick={handleSubmitRun}
								disabled={
									submittingRun ||
									!runDatasetId ||
									!weightsValid ||
									((runTargetType === "workflow" || runTargetType === "agent" || runTargetType === "tool") && !runWorkflowId.trim()) ||
									((runTargetType === "agent" || runTargetType === "model" || runTargetType === "tool") && !runTargetId)
								}
								className="rounded-xl border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-all hover:border-orange-600 hover:bg-orange-600 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:shadow-none"
							>
								{submittingRun ? "Starting…" : "Start Evaluation"}
							</button>
						</div>
					</div>
				</div>
			)}

			{/* Delete confirmation dialog */}
			{confirmDeleteId && (
				<div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
					<div className="relative w-full max-w-sm overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
						<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
						<h3 className="mb-2 text-base font-semibold text-slate-900">Delete Run</h3>
						<p className="mb-6 text-sm text-slate-600">
							Are you sure you want to delete this evaluation run? All results, recommendations, and associated executions will be permanently removed.
						</p>
						<div className="flex justify-end gap-2">
							<button
								type="button"
								onClick={() => setConfirmDeleteId(null)}
								className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={() => handleDeleteRun(confirmDeleteId)}
								className="rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-400 transition-all hover:bg-red-500/20 hover:border-red-500/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/45"
							>
								Delete
							</button>
						</div>
					</div>
				</div>
			)}

			{confirmRerunId && (
				<div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
					<div className="relative w-full max-w-sm overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
						<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
						<h3 className="mb-2 text-base font-semibold text-slate-900">Rerun Evaluation</h3>
						<p className="mb-6 text-sm text-slate-600">
							This will create a new evaluation run using the same dataset, workflow, and target configuration. Continue?
						</p>
						<div className="flex justify-end gap-2">
							<button
								type="button"
								onClick={() => setConfirmRerunId(null)}
								disabled={rerunning}
								className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 disabled:opacity-40"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={() => handleRerun(confirmRerunId)}
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
