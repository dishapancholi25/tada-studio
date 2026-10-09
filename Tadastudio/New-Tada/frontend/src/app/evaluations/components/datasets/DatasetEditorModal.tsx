"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Download, ExternalLink, FileText, Globe, Loader2, Lock, Pencil, ThumbsUp, Trash2, Upload, Users, X } from "lucide-react";
import Dropdown from "@/components/ui/Dropdown";
import { api } from "@/lib/api";
import * as evalApi from "@/lib/evaluation-api";
import type { DatasetExport, EvaluationDataset, TargetContextResponse, TestCase } from "@/lib/evaluation-api";
import { modelDeploymentAPI, type ModelDeploymentOption } from "@/lib/model-deployment-api";
import CaseListTable from "../shared/CaseListTable";
import type { CaseListItem } from "../shared/CaseListTable";
import type { CriterionRow, ModalTab } from "../shared/constants";
import { buildModelDropdownOptions, FORM_DROPDOWN_TRIGGER_CLASS, JUDGE_CRITERIA_PRESETS, MAX_CAP } from "../shared/constants";
import EvalHelpButton from "../shared/EvalHelpButton";
import GroupSelector from "@/components/settings/groups/GroupSelector";

export default function DatasetEditorModal({
	dataset: datasetProp,
	onClose,
	onRefreshDatasets,
}: {
	dataset: EvaluationDataset | null;
	onClose: () => void;
	onRefreshDatasets: () => void;
}) {
	// When opened in create mode (datasetProp=null), activeDataset is null until creation completes
	const [activeDataset, setActiveDataset] = useState<EvaluationDataset | null>(datasetProp);

	if (!activeDataset) {
		return (
			<DatasetMetadataModal
				onClose={onClose}
				onSaved={(ds) => {
					setActiveDataset(ds);
					onRefreshDatasets();
				}}
			/>
		);
	}

	return (
		<DatasetEditorModalInner
			dataset={activeDataset}
			onClose={onClose}
			onRefreshDatasets={onRefreshDatasets}
		/>
	);
}

/* ────────────────────────────────────────────────────────────────────────────
   Dataset metadata modal – used for both creating and editing datasets
   ──────────────────────────────────────────────────────────────────────────── */

function DatasetMetadataModal({
	onClose,
	onSaved,
	existingDataset,
}: {
	onClose: () => void;
	onSaved: (ds: EvaluationDataset) => void;
	existingDataset?: EvaluationDataset | null;
}) {
	const isEdit = !!existingDataset;
	const [name, setName] = useState(existingDataset?.name ?? "");
	const [description, setDescription] = useState(existingDataset?.description ?? "");
	const [targetType, setTargetType] = useState<"workflow" | "agent" | "model" | "tool">(
		(existingDataset?.target_type as "workflow" | "agent" | "model" | "tool") || "workflow",
	);
	const [targetId, setTargetId] = useState(existingDataset?.target_id ?? "");
	const [contextWorkflowId, setContextWorkflowId] = useState(existingDataset?.workflow_id ?? "");
	const [isSharedMode, setIsSharedMode] = useState(
		isEdit && (existingDataset?.visible_to_groups?.length ?? 0) > 0,
	);
	const [selectedVisibilityGroups, setSelectedVisibilityGroups] = useState<string[]>(
		(existingDataset?.visible_to_groups ?? []).filter((g) => g !== "__all__"),
	);
	const [saving, setSaving] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const [availableWorkflows, setAvailableWorkflows] = useState<{ id: string; name: string }[]>([]);
	const [agentNodes, setAgentNodes] = useState<{ id: string; name: string }[]>([]);
	const [toolNodes, setToolNodes] = useState<{ id: string; name: string; type: string }[]>([]);
	const [nodesLoading, setNodesLoading] = useState(false);
	const [modelDeployments, setModelDeployments] = useState<ModelDeploymentOption[]>([]);
	const [modelsLoading, setModelsLoading] = useState(true);

	useEffect(() => {
		evalApi.getWorkflows().then(setAvailableWorkflows).catch(() => {});
	}, []);

	useEffect(() => {
		let cancelled = false;
		modelDeploymentAPI
			.listSelectOptions()
			.then((deps) => { if (!cancelled) setModelDeployments(deps); })
			.catch(() => {})
			.finally(() => { if (!cancelled) setModelsLoading(false); });
		return () => { cancelled = true; };
	}, []);

	const modelOptions = useMemo(
		() => buildModelDropdownOptions(modelDeployments),
		[modelDeployments],
	);

	// Fetch agent/tool nodes when workflow + target type changes
	const initialNodeLoadDone = useRef(false);
	useEffect(() => {
		if (!contextWorkflowId || (targetType !== "agent" && targetType !== "tool")) {
			setAgentNodes([]);
			setToolNodes([]);
			return;
		}
		let cancelled = false;
		setNodesLoading(true);
		// Only clear targetId on user-driven changes, not the initial load
		if (initialNodeLoadDone.current) {
			setTargetId("");
		}
		api.getGraphByWorkflowId(contextWorkflowId)
			.then((res) => {
				if (cancelled || !res.success) return;
				const nodes = res.graph.nodes || [];
				const nodeId = (n: any) => n.uniq_id || n.id;
				if (targetType === "agent") {
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
			})
			.finally(() => {
				if (!cancelled) {
					setNodesLoading(false);
					initialNodeLoadDone.current = true;
				}
			});
		return () => { cancelled = true; };
	}, [contextWorkflowId, targetType]);

	const handleSave = async () => {
		if (!name.trim()) return;
		setSaving(true);
		setError(null);
		try {
			const workflowId = contextWorkflowId || (targetType === "workflow" ? targetId : undefined) || undefined;
			if (isEdit) {
				const updated = await evalApi.updateDataset(existingDataset!.id, {
					name: name.trim(),
					description: description.trim() || null,
					target_type: targetType,
					target_id: targetId || null,
					workflow_id: workflowId || null,
				});
				// Save visibility separately (uses its own endpoint)
				const groups = isSharedMode
					? (selectedVisibilityGroups.length > 0 ? selectedVisibilityGroups : ["__all__"])
					: [];
				const final = await evalApi.updateDatasetVisibility(existingDataset!.id, groups);
				onSaved(final);
			} else {
				const created = await evalApi.createDataset({
					name: name.trim(),
					description: description.trim() || undefined,
					target_type: targetType,
					target_id: targetId || undefined,
					workflow_id: workflowId,
				});
				onSaved(created);
			}
		} catch (err: any) {
			setError(err.message ?? `Failed to ${isEdit ? "update" : "create"} dataset`);
		} finally {
			setSaving(false);
		}
	};

	const inputClass = "w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 hover:border-orange-400 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15 transition-all";

	return (
		<div
			className="fixed inset-0 z-[110] flex items-center justify-center bg-black/70 backdrop-blur-sm"
			onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
		>
			<div className="relative w-full max-w-lg overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
				<div className="flex items-center justify-between mb-4">
					<h3 className="text-base font-semibold text-slate-900">{isEdit ? "Edit Dataset" : "New Dataset"}</h3>
					<button
						type="button"
						onClick={onClose}
						className="flex h-8 w-8 items-center justify-center rounded-xl text-slate-500 transition-all hover:text-slate-900 hover:bg-white border border-transparent hover:border-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
					>
						<X size={16} />
					</button>
				</div>

				<div className="space-y-4">
					<div>
						<label className="mb-1 block text-xs text-slate-500">Dataset Name</label>
						<input
							type="text"
							value={name}
							onChange={(e) => setName(e.target.value)}
							onKeyDown={(e) => { if (e.key === "Enter") handleSave(); }}
							placeholder="e.g. Regression Suite v1"
							className={inputClass}
							autoFocus
						/>
					</div>
					<div>
						<label className="mb-1 block text-xs text-slate-500">Description (optional)</label>
						<textarea
							value={description}
							onChange={(e) => setDescription(e.target.value)}
							placeholder="Dataset source, usage instructions, or other notes\u2026"
							rows={2}
							className={`${inputClass} resize-y`}
						/>
					</div>

					<div>
						<label className="mb-1 block text-xs text-slate-500">Target Type</label>
						<Dropdown
							value={targetType}
							onChange={(v) => {
								setTargetType(v as typeof targetType);
								setTargetId("");
								setContextWorkflowId("");
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

					{/* Workflow selector */}
					{targetType === "workflow" && availableWorkflows.length > 0 && (
						<div>
							<label className="mb-1 block text-xs text-slate-500">Target Workflow (optional)</label>
							<Dropdown
								value={targetId}
								onChange={setTargetId}
								options={[{ value: "", label: "None" }, ...availableWorkflows.map((wf) => ({ value: wf.id, label: wf.name }))]}
								width="trigger"
								className="w-full"
								triggerClassName={FORM_DROPDOWN_TRIGGER_CLASS}
								menuAppearance="light"
							/>
						</div>
					)}

					{/* Workflow selector for agent/tool */}
					{(targetType === "agent" || targetType === "tool") && availableWorkflows.length > 0 && (
						<div>
							<label className="mb-1 block text-xs text-slate-500">Workflow</label>
							<Dropdown
								value={contextWorkflowId}
								onChange={(v) => {
									setContextWorkflowId(v);
									setTargetId("");
								}}
								options={[{ value: "", label: "Select a workflow…" }, ...availableWorkflows.map((wf) => ({ value: wf.id, label: wf.name }))]}
								width="trigger"
								className="w-full"
								triggerClassName={FORM_DROPDOWN_TRIGGER_CLASS}
								menuAppearance="light"
							/>
						</div>
					)}

					{/* Agent node selector */}
					{targetType === "agent" && contextWorkflowId && (
						<div>
							<label className="mb-1 block text-xs text-slate-500">Agent Node (optional)</label>
							{nodesLoading ? (
								<div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
									<Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading agent nodes…
								</div>
							) : agentNodes.length > 0 ? (
								<Dropdown
									value={targetId}
									onChange={setTargetId}
									options={[{ value: "", label: "Select an agent…" }, ...agentNodes.map((n) => ({ value: n.id, label: n.name }))]}
									width="trigger"
									className="w-full"
									triggerClassName={FORM_DROPDOWN_TRIGGER_CLASS}
									menuAppearance="light"
								/>
							) : (
								<p className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
									No agent nodes found in this workflow.
								</p>
							)}
						</div>
					)}

					{/* Tool node selector */}
					{targetType === "tool" && contextWorkflowId && (
						<div>
							<label className="mb-1 block text-xs text-slate-500">Tool Node (optional)</label>
							{nodesLoading ? (
								<div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
									<Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading tool nodes…
								</div>
							) : toolNodes.length > 0 ? (
								<Dropdown
									value={targetId}
									onChange={setTargetId}
									options={[{ value: "", label: "Select a tool…" }, ...toolNodes.map((n) => ({ value: n.id, label: n.name }))]}
									width="trigger"
									className="w-full"
									triggerClassName={FORM_DROPDOWN_TRIGGER_CLASS}
									menuAppearance="light"
								/>
							) : (
								<p className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
									No tool nodes found in this workflow.
								</p>
							)}
						</div>
					)}

					{/* Model deployment selector */}
					{targetType === "model" && (
						<div>
							<label className="mb-1 block text-xs text-slate-500">Model Deployment (optional)</label>
							{modelsLoading ? (
								<div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
									<Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading models…
								</div>
							) : modelOptions.length > 0 ? (
								<Dropdown
									value={targetId}
									onChange={setTargetId}
									options={modelOptions}
									placeholder="Select a model deployment\u2026"
									className="w-full"
									triggerClassName={FORM_DROPDOWN_TRIGGER_CLASS}
								/>
							) : (
								<p className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
									No model deployments configured.
								</p>
							)}
						</div>
					)}

					{/* Sharing (edit mode only) */}
					{isEdit && (
						<div>
							<label className="mb-1 block text-xs text-slate-500">Sharing</label>
							<div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5">
								<div className="flex-1">
									<p className="text-sm text-slate-900">
										{isSharedMode ? "Shared" : "Private"}
									</p>
									<p className="text-[11px] text-slate-500">
										{isSharedMode
											? "Visible to selected groups or everyone"
											: "Only visible to you"}
									</p>
								</div>
								<button
									type="button"
									onClick={() => {
										setIsSharedMode(!isSharedMode);
										if (isSharedMode) setSelectedVisibilityGroups([]);
									}}
									className={`relative w-10 h-5 rounded-full transition-colors ${
										isSharedMode ? "bg-blue-500" : "bg-[color:var(--color-border)]"
									}`}
								>
									<span
										className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
											isSharedMode ? "left-[22px]" : "left-0.5"
										}`}
									/>
								</button>
							</div>
							{isSharedMode && (
								<div className="mt-2">
									<GroupSelector
										selectedGroups={selectedVisibilityGroups}
										onChange={setSelectedVisibilityGroups}
										placeholder="Select groups (optional, defaults to everyone)"
									/>
								</div>
							)}
						</div>
					)}

					{error && <p className="text-sm text-red-400">{error}</p>}
				</div>

				<div className="mt-6 flex justify-end gap-2">
					<button
						type="button"
						onClick={onClose}
						className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition-all hover:border-orange-400 hover:bg-white hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
					>
						Cancel
					</button>
					<button
						type="button"
						onClick={handleSave}
						disabled={saving || !name.trim()}
						className="rounded-xl border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-all hover:border-orange-600 hover:bg-orange-600 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:shadow-none"
					>
						{saving ? (isEdit ? "Saving\u2026" : "Creating\u2026") : (isEdit ? "Save Changes" : "Create Dataset")}
					</button>
				</div>
			</div>
		</div>
	);
}

/* ────────────────────────────────────────────────────────────────────────────
   Inner editor – the full dataset editor (existing logic, unchanged)
   ──────────────────────────────────────────────────────────────────────────── */

function DatasetEditorModalInner({
	dataset,
	onClose,
	onRefreshDatasets,
}: {
	dataset: EvaluationDataset;
	onClose: () => void;
	onRefreshDatasets: () => void;
}) {
	const [testCases, setTestCases] = useState<TestCase[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [activeTab, setActiveTab] = useState<ModalTab>("cases");
	const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);
	const [deletingId, setDeletingId] = useState<string | null>(null);

	// Tutorial: expand the first test case
	useEffect(() => {
		const handler = () => {
			if (testCases.length > 0) {
				setExpandedCaseId(testCases[0].id);
			}
		};
		window.addEventListener("tutorialExpandFirstTestCase", handler);
		return () => window.removeEventListener("tutorialExpandFirstTestCase", handler);
	}, [testCases]);

	// Mutable dataset state (updated when metadata is edited)
	const [currentDataset, setCurrentDataset] = useState(dataset);

	// User's own workflows — resolve links for shared datasets
	const [userWorkflows, setUserWorkflows] = useState<{ id: string; name: string }[]>([]);
	useEffect(() => {
		evalApi.getWorkflows().then(setUserWorkflows).catch(() => {});
	}, []);
	const resolvedWorkflowId = useMemo(() => {
		if (!currentDataset.workflow_name) return currentDataset.workflow_id;
		const match = userWorkflows.find((wf) => wf.name === currentDataset.workflow_name);
		return match ? match.id : currentDataset.workflow_id;
	}, [currentDataset.workflow_id, currentDataset.workflow_name, userWorkflows]);

	// Metadata edit modal
	const [editingMetadata, setEditingMetadata] = useState(false);

	// Inline edit state
	const [editingCaseId, setEditingCaseId] = useState<string | null>(null);
	const [editInputJson, setEditInputJson] = useState("");
	const [editExpectedJson, setEditExpectedJson] = useState("");
	const [editJudgeCriteria, setEditJudgeCriteria] = useState<CriterionRow[]>([]);
	const [editTagsInput, setEditTagsInput] = useState("");
	const [savingEdit, setSavingEdit] = useState(false);

	// Manual form state
	const [inputDataJson, setInputDataJson] = useState("");
	const [expectedOutputJson, setExpectedOutputJson] = useState("");
	const [judgeCriteria, setJudgeCriteria] = useState<CriterionRow[]>([]);
	const [tagsInput, setTagsInput] = useState("");
	const [addingManual, setAddingManual] = useState(false);

	// File attachment state (manual add form)
	const [pendingFile, setPendingFile] = useState<File | null>(null);
	const [uploadingFile, setUploadingFile] = useState(false);
	const [isDragging, setIsDragging] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);

	// AI gen form state
	const [seedPrompt, setSeedPrompt] = useState("");
	const [genCount, setGenCount] = useState(10);
	const [includeEdgeCases, setIncludeEdgeCases] = useState(false);
	const [includeAdversarial, setIncludeAdversarial] = useState(false);
	const [generating, setGenerating] = useState(false);
	const [genProgress, setGenProgress] = useState(0);
	const abortControllerRef = useRef<AbortController | null>(null);
	const [generatorModelId, setGeneratorModelId] = useState(
		() => (typeof window !== "undefined" && localStorage.getItem("eval_default_gen_model")) || "",
	);
	const [genDeployments, setGenDeployments] = useState<ModelDeploymentOption[]>([]);
	const [genModelsLoading, setGenModelsLoading] = useState(true);

	// Target context state
	const [drawerTargetContext, setDrawerTargetContext] = useState<TargetContextResponse | null>(null);
	const [drawerContextLoading, setDrawerContextLoading] = useState(false);

	// Import from executions state
	const [importExecutions, setImportExecutions] = useState<any[]>([]);
	const [importLoading, setImportLoading] = useState(false);
	const [importSelectedIds, setImportSelectedIds] = useState<Set<string>>(new Set());
	const [importIncludeExpected, setImportIncludeExpected] = useState(true);
	const [importTagsInput, setImportTagsInput] = useState("");
	const [importing, setImporting] = useState(false);
	const [importLoaded, setImportLoaded] = useState(false);
	const [importExpandedId, setImportExpandedId] = useState<string | null>(null);

	// Few-shot example picker state (AI tab)
	const [fewShotExpanded, setFewShotExpanded] = useState(false);
	const [fewShotExecutions, setFewShotExecutions] = useState<any[]>([]);
	const [fewShotLoading, setFewShotLoading] = useState(false);
	const [fewShotSelectedIds, setFewShotSelectedIds] = useState<Set<string>>(new Set());
	const [fewShotLoaded, setFewShotLoaded] = useState(false);
	const [fewShotExpandedId, setFewShotExpandedId] = useState<string | null>(null);

	const loadCases = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const cases = await evalApi.listTestCases(dataset.id);
			setTestCases(cases);
		} catch (err: any) {
			setError(err.message ?? "Failed to load test cases");
		} finally {
			setLoading(false);
		}
	}, [dataset.id]);

	useEffect(() => {
		loadCases();
	}, [loadCases]);

	// Abort streaming generation on unmount
	useEffect(() => {
		return () => {
			abortControllerRef.current?.abort();
		};
	}, []);

	// Fetch model deployments for generator dropdown
	useEffect(() => {
		let cancelled = false;
		modelDeploymentAPI
			.listSelectOptions()
			.then((deps) => { if (!cancelled) setGenDeployments(deps); })
			.catch(() => {})
			.finally(() => { if (!cancelled) setGenModelsLoading(false); });
		return () => { cancelled = true; };
	}, []);

	// Load target context when modal opens (non-blocking)
	useEffect(() => {
		if (!dataset.target_id || !dataset.target_type) return;
		let cancelled = false;
		setDrawerContextLoading(true);
		evalApi
			.getTargetContext(dataset.target_type, dataset.target_id, dataset.workflow_id || undefined)
			.then((ctx) => { if (!cancelled) setDrawerTargetContext(ctx); })
			.catch(() => {})
			.finally(() => { if (!cancelled) setDrawerContextLoading(false); });
		return () => { cancelled = true; };
	}, [dataset.id, dataset.target_id, dataset.target_type, dataset.workflow_id]);

	const genModelOptions = useMemo(
		() => buildModelDropdownOptions(genDeployments),
		[genDeployments],
	);

	const loadPositiveExecutions = useCallback(async (target: "import" | "fewshot") => {
		const setLoading_ = target === "import" ? setImportLoading : setFewShotLoading;
		const setExecs = target === "import" ? setImportExecutions : setFewShotExecutions;
		const setLoaded = target === "import" ? setImportLoaded : setFewShotLoaded;
		setLoading_(true);
		try {
			// Use workflow_id if available; for workflow-type datasets, fall back to target_id
			const workflowId = dataset.workflow_id || (dataset.target_type === "workflow" ? dataset.target_id : undefined) || undefined;
			const result = await api.getGraphExecutions(undefined, 50, 0, "positive", workflowId) as any;
			let execs = result?.executions ?? [];

			// For agent/tool targets, fetch node-level I/O and replace workflow-level data
			const useNodeIo = (dataset.target_type === "agent" || dataset.target_type === "tool") && dataset.target_id;
			if (useNodeIo && execs.length > 0) {
				const enriched = await Promise.allSettled(
					execs.map(async (exe: any) => {
						try {
							const nodeExe = await api.getNodeExecution(exe.id, dataset.target_id!) as any;
							if (nodeExe?.input_data) {
								return { ...exe, input_data: nodeExe.input_data, output_data: nodeExe.output_data ?? exe.output_data };
							}
						} catch { /* node not found in this execution */ }
						return null; // Mark for filtering
					}),
				);
				execs = enriched
					.filter((r): r is PromiseFulfilledResult<any> => r.status === "fulfilled" && r.value !== null)
					.map((r) => r.value);
			}

			setExecs(execs);
			setLoaded(true);
		} catch {
			setExecs([]);
			setLoaded(true);
		} finally {
			setLoading_(false);
		}
	}, [dataset.workflow_id, dataset.target_type, dataset.target_id]);

	// Load positive executions when switching to import tab
	useEffect(() => {
		if (activeTab === "import-executions" && !importLoaded) {
			loadPositiveExecutions("import");
		}
	}, [activeTab, importLoaded, loadPositiveExecutions]);

	// Load positive executions when expanding few-shot section
	useEffect(() => {
		if (fewShotExpanded && !fewShotLoaded) {
			loadPositiveExecutions("fewshot");
		}
	}, [fewShotExpanded, fewShotLoaded, loadPositiveExecutions]);

	/** Convert raw execution objects to CaseListItem for the shared table. */
	const executionToCaseItem = useCallback((exe: any): CaseListItem => {
		const extractText = (data: any, preferredKeys: string[]): string | null => {
			if (!data) return null;
			if (typeof data === "string") return data;
			if (typeof data === "object") {
				for (const key of preferredKeys) {
					if (data[key] && typeof data[key] === "string") return data[key];
				}
				// Exclude file_info (large base64) from fallback serialization
				const { file_info, ...rest } = data;
				if (Object.keys(rest).length === 0) {
					// File-only input
					if (file_info) {
						const name = file_info.name || file_info.filename || "uploaded file";
						return `[File: ${name}]`;
					}
					return null;
				}
				return JSON.stringify(rest);
			}
			return String(data);
		};
		const inputText = extractText(exe.input_data, ["message", "input", "prompt", "query"]);

		// For tool nodes, output_data is stored directly as the response dict,
		// e.g. {status_code, headers, data, error, elapsed}.
		// The agent LLM only receives the "data" portion via ToolMessage,
		// so extract just that to match what the wrapper agent will see.
		let outputText: string | null;
		const od = exe.output_data;
		if (dataset.target_type === "tool" && od && typeof od === "object" && "data" in od) {
			const bodyData = od.data;
			outputText = typeof bodyData === "object" ? JSON.stringify(bodyData, null, 2) : String(bodyData);
		} else {
			outputText = extractText(od, ["final_output", "message", "output", "response"]);
		}
		const meta: string[] = [];
		if (exe.graph_name || exe.workflow_name) meta.push(exe.graph_name || exe.workflow_name);
		if (exe.created_at) meta.push(new Date(exe.created_at).toLocaleString());
		const alreadyImported = testCases.some(
			(tc) => tc.judge_criteria?.execution_id === exe.id,
		);

		// Detect file_info from the execution's input_data
		const fi = typeof exe.input_data === "object" && exe.input_data?.file_info;
		const files = fi
			? [
					{
						id: `preview-${exe.id}`,
						filename: fi.name || fi.filename || "uploaded_file",
						mime_type: fi.type || "application/octet-stream",
						file_size: fi.size || 0,
					},
				]
			: undefined;

		return {
			id: exe.id,
			input_data: inputText,
			expected_output: outputText,
			tags: meta.length > 0 ? meta : null,
			judge_criteria: exe.duration_seconds != null
				? { duration: `${exe.duration_seconds.toFixed(1)}s` }
				: null,
			badge: alreadyImported ? "already imported" : null,
			files,
		};
	}, [testCases, dataset.target_type]);

	const importCaseItems = useMemo(
		() => importExecutions.map(executionToCaseItem),
		[importExecutions, executionToCaseItem],
	);

	const fewShotCaseItems = useMemo(
		() => fewShotExecutions.map(executionToCaseItem),
		[fewShotExecutions, executionToCaseItem],
	);

	const handleImportExecutions = async () => {
		if (importSelectedIds.size === 0) return;
		setImporting(true);
		setError(null);
		try {
			const tags = importTagsInput
				.split(",")
				.map((t) => t.trim())
				.filter(Boolean);
			const selectedCount = importSelectedIds.size;
			await evalApi.importFromExecutions(dataset.id, {
				execution_ids: Array.from(importSelectedIds),
				include_expected_output: importIncludeExpected,
				tags: tags.length > 0 ? tags : undefined,
			});
			await loadCases();
			onRefreshDatasets();
			setImportSelectedIds(new Set());
			setActiveTab("cases");

			// Auto-set description if the dataset doesn't have one yet
			if (!currentDataset.description) {
				const parts: string[] = [`Imported from executions (${selectedCount} case${selectedCount !== 1 ? "s" : ""})`];
				if (importIncludeExpected) parts.push("with expected outputs");
				const hasFiles = Array.from(importSelectedIds).some((id) => {
					const exe = importExecutions.find((e: any) => e.id === id);
					return exe && typeof exe.input_data === "object" && exe.input_data?.file_info;
				});
				if (hasFiles) parts.push("includes file attachments");
				if (tags.length > 0) parts.push(`tags: ${tags.join(", ")}`);
				const autoDesc = parts.join(" · ");
				try {
					await evalApi.updateDataset(dataset.id, { description: autoDesc });
					setCurrentDataset((prev) => ({ ...prev, description: autoDesc }));
				} catch {
					// Non-critical
				}
			}
		} catch (err: any) {
			setError(err.message ?? "Failed to import executions");
		} finally {
			setImporting(false);
		}
	};

	const toggleImportSelection = (id: string) => {
		setImportSelectedIds((prev) => {
			const next = new Set(prev);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return next;
		});
	};

	const toggleFewShotSelection = (id: string) => {
		setFewShotSelectedIds((prev) => {
			const next = new Set(prev);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return next;
		});
	};

	// Close on Escape
	useEffect(() => {
		const handleKey = (e: KeyboardEvent) => {
			if (e.key === "Escape") onClose();
		};
		document.addEventListener("keydown", handleKey);
		return () => document.removeEventListener("keydown", handleKey);
	}, [onClose]);

	const handleDeleteTestCase = async (tcId: string) => {
		setDeletingId(tcId);
		try {
			await evalApi.deleteTestCase(dataset.id, tcId);
			setTestCases((prev) => prev.filter((tc) => tc.id !== tcId));
			if (expandedCaseId === tcId) setExpandedCaseId(null);
			onRefreshDatasets();
		} catch (err: any) {
			setError(err.message ?? "Failed to delete test case");
		} finally {
			setDeletingId(null);
		}
	};

	const startEditing = (tc: TestCase) => {
		setEditingCaseId(tc.id);
		setEditInputJson(tc.input_data);
		setEditExpectedJson(tc.expected_output ?? "");
		setEditJudgeCriteria(
			tc.judge_criteria && Object.keys(tc.judge_criteria).length > 0
				? Object.entries(tc.judge_criteria).map(([key, value]) => ({ key, value: String(value) }))
				: [],
		);
		setEditTagsInput(tc.tags?.join(", ") ?? "");
		setExpandedCaseId(tc.id);
	};

	const cancelEditing = () => {
		setEditingCaseId(null);
	};

	const handleSaveEdit = async () => {
		if (!editingCaseId) return;
		const inputText = editInputJson.trim();
		if (!inputText) {
			setError("Input cannot be empty");
			return;
		}
		const expectedText = editExpectedJson.trim() || null;
		const filledCriteria = editJudgeCriteria.filter((r) => r.key.trim() && r.value.trim());
		const parsedJudge: Record<string, string> | null =
			filledCriteria.length > 0
				? Object.fromEntries(filledCriteria.map((r) => [r.key.trim(), r.value.trim()]))
				: null;
		const tags = editTagsInput
			.split(",")
			.map((t) => t.trim())
			.filter(Boolean);

		setSavingEdit(true);
		setError(null);
		try {
			const updated = await evalApi.updateTestCase(dataset.id, editingCaseId, {
				input_data: inputText,
				expected_output: expectedText,
				judge_criteria: parsedJudge,
				tags: tags.length > 0 ? tags : null,
			});
			setTestCases((prev) => prev.map((tc) => (tc.id === editingCaseId ? updated : tc)));
			setEditingCaseId(null);
		} catch (err: any) {
			setError(err.message ?? "Failed to update test case");
		} finally {
			setSavingEdit(false);
		}
	};

	const handleAddManual = async () => {
		const inputText = inputDataJson.trim();
		if (!inputText && !pendingFile) {
			setError("Input text or a file attachment is required");
			return;
		}
		const expectedText = expectedOutputJson.trim() || undefined;
		const filledCriteria = judgeCriteria.filter((r) => r.key.trim() && r.value.trim());
		const parsedJudgeCriteria: Record<string, string> | undefined =
			filledCriteria.length > 0
				? Object.fromEntries(filledCriteria.map((r) => [r.key.trim(), r.value.trim()]))
				: undefined;

		const tags = tagsInput
			.split(",")
			.map((t) => t.trim())
			.filter(Boolean);

		setAddingManual(true);
		setError(null);
		try {
			const added = await evalApi.addTestCases(dataset.id, {
				manual: [
					{
						input_data: inputText || `[File: ${pendingFile?.name}]`,
						expected_output: expectedText,
						judge_criteria: parsedJudgeCriteria,
						tags: tags.length > 0 ? tags : undefined,
					},
				],
			});

			// Upload file attachment if present
			if (pendingFile && added.length > 0) {
				setUploadingFile(true);
				try {
					await evalApi.uploadTestCaseFile(dataset.id, added[0].id, pendingFile);
				} catch (fileErr: any) {
					setError(`Test case added but file upload failed: ${fileErr.message}`);
				} finally {
					setUploadingFile(false);
				}
			}

			await loadCases();
			onRefreshDatasets();
			setInputDataJson("");
			setExpectedOutputJson("");
			setJudgeCriteria([]);
			setTagsInput("");
			setPendingFile(null);
			if (fileInputRef.current) fileInputRef.current.value = "";
			setActiveTab("cases");
		} catch (err: any) {
			setError(err.message ?? "Failed to add test case");
		} finally {
			setAddingManual(false);
		}
	};

	const handleDeleteFile = async (testCaseId: string, fileId: string) => {
		try {
			await evalApi.deleteTestCaseFile(dataset.id, testCaseId, fileId);
			await loadCases();
		} catch (err: any) {
			setError(err.message ?? "Failed to delete file");
		}
	};

	const formatFileSize = (bytes: number): string => {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	};

	const handleAiGenerate = async () => {
		const enrichment = drawerTargetContext?.ai_seed_enrichment || "";
		const userPrompt = seedPrompt.trim();
		if (!enrichment && !userPrompt) return;
		const finalSeedPrompt = enrichment
			? enrichment + (userPrompt ? "\n\n" + userPrompt : "")
			: userPrompt;
		setGenerating(true);
		setGenProgress(0);
		setError(null);

		const controller = new AbortController();
		abortControllerRef.current = controller;
		let lastSavedCount = 0;

		try {
			await evalApi.generateTestCasesStream(
				dataset.id,
				{
					seed_prompt: finalSeedPrompt,
					count: genCount,
					include_edge_cases: includeEdgeCases,
					include_adversarial: includeAdversarial,
					...(generatorModelId ? { generator_model: { model_deployment_id: generatorModelId } } : {}),
					...(fewShotSelectedIds.size > 0 ? { example_execution_ids: Array.from(fewShotSelectedIds) } : {}),
				},
				(event) => {
					if (event.event === "batch" && event.saved_count != null) {
						lastSavedCount = event.saved_count;
						setGenProgress(event.saved_count);
					} else if (event.event === "error") {
						setError(event.message ?? "Generation failed partway through");
						if (event.saved_count != null) {
							lastSavedCount = event.saved_count;
							setGenProgress(event.saved_count);
						}
					}
				},
				controller.signal,
			);

			// Reload to pick up all persisted cases
			await loadCases();
			onRefreshDatasets();
			if (lastSavedCount > 0) {
				setActiveTab("cases");

				// Auto-set description if the dataset doesn't have one yet
				if (!currentDataset.description) {
					const parts: string[] = [`AI-generated (${lastSavedCount} cases)`];
					if (generatorModelId) {
						const model = genDeployments.find((d) => d.id === generatorModelId);
						if (model) parts.push(`model: ${model.display_name || model.model_name || generatorModelId}`);
					}
					const opts: string[] = [];
					if (includeEdgeCases) opts.push("edge cases");
					if (includeAdversarial) opts.push("adversarial");
					if (opts.length) parts.push(`includes ${opts.join(" & ")}`);
					if (userPrompt) parts.push(`prompt: "${userPrompt.length > 120 ? userPrompt.slice(0, 120) + "…" : userPrompt}"`);
					const autoDesc = parts.join(" · ");
					try {
						await evalApi.updateDataset(dataset.id, { description: autoDesc });
						setCurrentDataset((prev) => ({ ...prev, description: autoDesc }));
					} catch {
						// Non-critical – don't surface this error
					}
				}
			}
		} catch (err: any) {
			if (err.name !== "AbortError") {
				setError(err.message ?? "Failed to generate test cases");
				// Reload in case some batches were saved before the error
				await loadCases();
				onRefreshDatasets();
			}
		} finally {
			abortControllerRef.current = null;
			setGenerating(false);
			setGenProgress(0);
		}
	};

	const atCapacity = testCases.length >= MAX_CAP;
	const tabs: { id: ModalTab; label: string }[] = [
		{ id: "cases", label: `Test Cases (${testCases.length})` },
		...(!dataset.is_read_only ? [
			{ id: "manual" as ModalTab, label: atCapacity ? "Add Manual (full)" : "Add Manual" },
			{ id: "ai" as ModalTab, label: atCapacity ? "AI Generate (full)" : "AI Generate" },
			{ id: "import-executions" as ModalTab, label: atCapacity ? "Import Executions (full)" : "Import Executions" },
		] : []),
		{ id: "export-import" as ModalTab, label: "Export / Import" },
	];

	return (
		<div
			className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm"
			onClick={(e) => {
				if (e.target === e.currentTarget) onClose();
			}}
		>
			<div className="flex w-full max-w-5xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]"
				style={{ height: "min(85vh, 800px)" }}
				data-tutorial="dataset-modal"
			>
				{/* Modal header */}
				<div className="pointer-events-none h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
				<div className="flex items-start gap-4 border-b border-slate-200 bg-white px-6 py-4" data-tutorial="dataset-modal-header">
					<div className="flex-1 min-w-0">
						<div className="flex items-center gap-2">
							<h2 className="text-base font-semibold text-slate-900 truncate">{currentDataset.name}</h2>
							{!dataset.is_read_only && (
								<button
									type="button"
									onClick={() => setEditingMetadata(true)}
									className="shrink-0 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-500 transition-all hover:text-slate-900 hover:border-orange-400 hover:bg-white"
									title="Edit dataset metadata"
								>
									<Pencil size={11} />
								</button>
							)}
							<EvalHelpButton topic="dataset-editor" />
						</div>
						<div className="mt-1 flex items-center gap-3 text-xs text-slate-500">
							<span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-[11px] font-medium text-orange-700">
								{currentDataset.target_type}
							</span>
							{currentDataset.target_type === "workflow" && currentDataset.target_id ? (
								<a
									href={`/workflow/${encodeURIComponent(resolvedWorkflowId || currentDataset.target_id)}`}
									target="_blank"
									rel="noopener noreferrer"
									className="inline-flex items-center gap-1 text-[rgba(var(--color-primary-rgb),0.75)] transition hover:text-[rgba(var(--color-primary-rgb),1)] hover:underline"
									title="Open in editor"
								>
									{currentDataset.target_name ?? currentDataset.target_id.slice(0, 10)}
									<ExternalLink size={10} />
								</a>
							) : (currentDataset.target_name || currentDataset.target_id) ? (
								<>
									{currentDataset.workflow_name && currentDataset.workflow_id && (
										<a
											href={`/workflow/${encodeURIComponent(resolvedWorkflowId || currentDataset.workflow_id)}`}
											target="_blank"
											rel="noopener noreferrer"
											className="inline-flex items-center gap-1 text-[rgba(var(--color-primary-rgb),0.75)] transition hover:text-[rgba(var(--color-primary-rgb),1)] hover:underline"
											title="Open in editor"
										>
											{currentDataset.workflow_name}
											<ExternalLink size={10} />
										</a>
									)}
									{currentDataset.workflow_name && currentDataset.workflow_id && <span className="text-slate-300">/</span>}
									<span className="text-slate-600" title={currentDataset.target_id || undefined}>
										{currentDataset.target_name || currentDataset.target_id}
									</span>
								</>
							) : (
								<span className="text-slate-400">No target</span>
							)}
							<span>{dataset.test_case_count} test case{dataset.test_case_count !== 1 ? "s" : ""}</span>
							{dataset.created_at && (
								<span>{new Date(dataset.created_at).toLocaleDateString()}</span>
							)}
						</div>
						{currentDataset.description && (
							<p className="mt-1.5 text-xs text-slate-500 line-clamp-2">{currentDataset.description}</p>
						)}
				{/* Sharing badge (read-only display) */}
				{dataset.is_read_only ? (
					<div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
						<Lock size={12} />
						<span>Shared by {dataset.created_by_name || dataset.created_by_email || "another user"} (read-only)</span>
						{dataset.visible_to_groups && dataset.visible_to_groups.length > 0 && (
							<>
								<span className="text-slate-300">·</span>
								{dataset.visible_to_groups.includes("__all__") ? (
									<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-500/15 text-blue-400 border border-blue-500/30">
										<Globe className="w-3 h-3" />
										Everyone
									</span>
								) : (
									dataset.visible_to_groups.map((g) => (
										<span key={g} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-500/15 text-purple-400 border border-purple-500/30">
											<Users className="w-3 h-3" />
											{g}
										</span>
									))
								)}
							</>
						)}
					</div>
				) : (currentDataset.visible_to_groups?.length ?? 0) > 0 ? (
					<div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
						{currentDataset.visible_to_groups?.includes("__all__") ? (
							<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-500/15 text-blue-400 border border-blue-500/30">
								<Globe className="w-3 h-3" />
								Shared with everyone
							</span>
						) : (
							<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-500/15 text-purple-400 border border-purple-500/30">
								<Users className="w-3 h-3" />
								Shared with {currentDataset.visible_to_groups!.length} group{currentDataset.visible_to_groups!.length !== 1 ? "s" : ""}
							</span>
						)}
					</div>
				) : null}
					</div>
					<button
						type="button"
						data-tutorial="dataset-modal-close-btn"
						onClick={onClose}
						className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-slate-500 transition-all hover:text-slate-900 hover:bg-white border border-transparent hover:border-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
					>
						<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
					</button>
				</div>

				{/* Tab bar */}
				<div className="flex gap-2 flex-wrap px-6 py-3 border-b border-slate-200 bg-white" data-tutorial="dataset-modal-tabs">
					{tabs.map((tab) => (
						<button
							key={tab.id}
							type="button"
							data-tutorial={`dataset-tab-${tab.id}`}
							onClick={() => setActiveTab(tab.id)}
							className={`px-4 py-2 rounded-xl text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] ${
								activeTab === tab.id
									? "border border-orange-500 bg-orange-500 text-white"
									: "border border-slate-200 bg-white text-slate-600 hover:text-slate-900 hover:border-orange-400 hover:bg-white"
							}`}
						>
							{tab.label}
						</button>
					))}
				</div>

				{/* Error banner */}
				{error && (
					<div className="mx-6 mt-3 flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">
						<span className="text-sm text-red-400">{error}</span>
						<button
							type="button"
							onClick={() => setError(null)}
							className="ml-auto text-xs text-red-400/60 hover:text-red-400"
						>
							Dismiss
						</button>
					</div>
				)}

				{/* Tab content */}
				<div className="flex-1 overflow-y-auto px-6 py-4" data-tutorial="dataset-modal-content">
					{/* ── Test Cases tab ── */}
					{activeTab === "cases" && (
						<>
							{!loading && (
								<div className="mb-4 space-y-2">
									<div className="flex items-center justify-between text-xs text-slate-500">
										<span>{testCases.length} / {MAX_CAP} test cases</span>
									</div>
									<div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
										<div
											className={`h-full rounded-full transition-all ${
												testCases.length >= MAX_CAP
													? "bg-red-500"
													: testCases.length >= 180
														? "bg-amber-500"
														: "bg-emerald-500"
											}`}
											style={{ width: `${Math.min((testCases.length / MAX_CAP) * 100, 100)}%` }}
										/>
									</div>
									{testCases.length >= MAX_CAP && (
										<p className="text-xs text-red-400">Dataset is at capacity. Delete cases to add more.</p>
									)}
									{testCases.length >= 180 && testCases.length < MAX_CAP && (
										<p className="text-xs text-amber-400">Approaching limit — {MAX_CAP - testCases.length} slots remaining.</p>
									)}
								</div>
							)}
							{loading ? (
								<p className="py-16 text-center text-sm text-slate-500">Loading test cases...</p>
							) : testCases.length === 0 ? (
								<div className="py-16 text-center">
									<p className="text-sm text-slate-500">No test cases yet.</p>
									{!dataset.is_read_only && (
									<>
									<p className="mt-1 text-xs text-slate-400">
										Add cases manually or use AI generation.
									</p>
									<div className="mt-4 flex justify-center gap-2">
										<button
											type="button"
											onClick={() => setActiveTab("manual")}
											className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 px-3 py-1.5 text-xs text-slate-700 transition-all hover:border-[rgba(var(--color-primary-rgb),0.50)] hover:bg-[color:var(--color-surface)]/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
										>
											Add Manual
										</button>
										<button
											type="button"
											onClick={() => setActiveTab("ai")}
											className="rounded-xl bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] px-3 py-1.5 text-xs font-medium text-[color:var(--button-primary-text)] shadow-[0_8px_20px_rgba(var(--color-primary-rgb),0.25)] transition-all hover:from-[rgba(var(--color-primary-rgb),0.9)] hover:to-[rgba(var(--color-primary-rgb),0.7)] hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
										>
											AI Generate
										</button>
										<button
											type="button"
											onClick={() => setActiveTab("import-executions")}
											className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs text-emerald-400 transition-all hover:border-emerald-500/50 hover:bg-emerald-500/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/45"
										>
											Import Executions
										</button>
									</div>
									</>
									)}
								</div>
							) : (
								<CaseListTable
									items={testCases}
									expandedId={expandedCaseId}
									onToggleExpand={setExpandedCaseId}
									renderActions={dataset.is_read_only ? undefined : (item) => (
										<div className="flex items-center justify-end gap-1">
											<button
												type="button"
												onClick={(e) => {
													e.stopPropagation();
													startEditing(item as TestCase);
												}}
												className="rounded-xl p-1.5 text-[color:var(--color-text-muted)] transition-all hover:text-slate-900 hover:bg-[rgba(var(--color-primary-rgb),0.12)] border border-transparent hover:border-[rgba(var(--color-primary-rgb),0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
												title="Edit test case"
											>
												<Pencil className="h-3.5 w-3.5" />
											</button>
											<button
												type="button"
												onClick={(e) => {
													e.stopPropagation();
													handleDeleteTestCase(item.id);
												}}
												disabled={deletingId === item.id}
												className="rounded-xl p-1.5 text-[color:var(--color-text-muted)] transition-all hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/45 disabled:opacity-30"
												title="Delete test case"
											>
												{deletingId === item.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
											</button>
										</div>
									)}
									renderExpandedOverride={(item) => {
										if (editingCaseId !== item.id) return null;
										return (
											<div>
												<div className="grid grid-cols-2 gap-4">
													<div>
														<p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">Input</p>
														<textarea
															value={editInputJson}
															onChange={(e) => setEditInputJson(e.target.value)}
															rows={5}
															spellCheck={false}
															placeholder="Enter the input text..."
															className="w-full rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs leading-relaxed text-[color:var(--color-text-secondary)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all resize-y"
														/>
													</div>
													<div>
														<p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">Expected Output</p>
														<textarea
															value={editExpectedJson}
															onChange={(e) => setEditExpectedJson(e.target.value)}
															rows={5}
															spellCheck={false}
															placeholder="Enter the expected output (optional)..."
															className="w-full rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs leading-relaxed text-[color:var(--color-text-secondary)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all resize-y"
														/>
													</div>
												</div>
												<div className="mt-3">
													<p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">Judge Criteria</p>
													{editJudgeCriteria.map((row, rIdx) => (
														<div key={rIdx} className="mb-2 flex items-start gap-2">
															<input
																type="text"
																value={row.key}
																onChange={(e) => {
																	const next = [...editJudgeCriteria];
																	next[rIdx] = { ...next[rIdx], key: e.target.value };
																	setEditJudgeCriteria(next);
																}}
																placeholder="Criterion"
																className="w-36 shrink-0 rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-2 py-1.5 text-xs text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all"
															/>
															<input
																type="text"
																value={row.value}
																onChange={(e) => {
																	const next = [...editJudgeCriteria];
																	next[rIdx] = { ...next[rIdx], value: e.target.value };
																	setEditJudgeCriteria(next);
																}}
																placeholder="Description"
																className="min-w-0 flex-1 rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-2 py-1.5 text-xs text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all"
															/>
															<button
																type="button"
																onClick={() => setEditJudgeCriteria(editJudgeCriteria.filter((_, i) => i !== rIdx))}
																className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-slate-300 transition hover:bg-red-500/10 hover:text-red-400/60"
															>
																<svg width="10" height="10" viewBox="0 0 12 12" fill="none"><path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
															</button>
														</div>
													))}
													<button
														type="button"
														onClick={() => setEditJudgeCriteria([...editJudgeCriteria, { key: "", value: "" }])}
														className="flex items-center gap-1 rounded-lg border border-dashed border-slate-200 px-2 py-1 text-[11px] text-slate-400 transition hover:border-slate-300 hover:text-slate-500"
													>
														<svg width="9" height="9" viewBox="0 0 10 10" fill="none"><path d="M5 1v8M1 5h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
														Add criterion
													</button>
												</div>
												<div className="mt-3">
													<p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">Tags (comma-separated)</p>
													<input
														type="text"
														value={editTagsInput}
														onChange={(e) => setEditTagsInput(e.target.value)}
														placeholder="e.g. happy-path, edge-case"
														className="w-full rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all"
													/>
												</div>
												{/* File attachment management */}
												<div className="mt-3">
													<p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-500">File Attachment</p>
													{(() => {
														const tc = testCases.find((c) => c.id === item.id);
														const files = tc?.files;
														const hasFile = files && files.length > 0;

														const handleEditFileDrop = async (e: React.DragEvent) => {
															e.preventDefault();
															setIsDragging(false);
															if (e.dataTransfer.files.length > 0) {
																try {
																	await evalApi.uploadTestCaseFile(dataset.id, item.id, e.dataTransfer.files[0]);
																	await loadCases();
																} catch (err: any) {
																	setError(err.message ?? "File upload failed");
																}
															}
														};

														if (hasFile) {
															return (
																<div className="space-y-1.5">
																	{files.map((f) => (
																		<div key={f.id} className="flex items-center gap-2 rounded-xl border-2 border-dashed border-[color:var(--color-accent)]/60 bg-[color:var(--color-surface)] px-3 py-2.5">
																			<FileText className="h-5 w-5 shrink-0 text-[color:var(--color-accent)]" />
																			<span className="min-w-0 flex-1 truncate text-xs font-medium text-slate-900">{f.filename}</span>
																			<span className="shrink-0 text-[10px] text-[color:var(--color-text-muted)]">{formatFileSize(f.file_size)}</span>
																			<button
																				type="button"
																				onClick={() => handleDeleteFile(item.id, f.id)}
																				className="shrink-0 p-1 rounded hover:bg-[color:var(--color-surface-hover)] text-[color:var(--color-text-muted)] hover:text-slate-900 transition-colors"
																				title="Remove file"
																			>
																				<X className="h-4 w-4" />
																			</button>
																		</div>
																	))}
																</div>
															);
														}
														return (
															<div
																className={`rounded-xl border-2 border-dashed p-4 text-center transition-all duration-200 cursor-pointer flex flex-col items-center justify-center gap-2 ${
																	isDragging
																		? "border-[color:var(--color-primary)] bg-[rgba(var(--color-primary-rgb),0.05)]"
																		: "border-[color:var(--color-border)] bg-[color:var(--color-surface)] hover:border-[color:var(--color-primary)]/50"
																}`}
																onDrop={handleEditFileDrop}
																onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
																onDragLeave={() => setIsDragging(false)}
																onClick={() => {
																	const input = document.createElement("input");
																	input.type = "file";
																	input.accept = ".pdf,.png,.jpg,.jpeg,.docx,.txt,.xlsx,.csv,.md,.json,.xml,.yaml,.yml";
																	input.onchange = async () => {
																		const f = input.files?.[0];
																		if (!f) return;
																		try {
																			await evalApi.uploadTestCaseFile(dataset.id, item.id, f);
																			await loadCases();
																		} catch (err: any) {
																			setError(err.message ?? "File upload failed");
																		}
																	};
																	input.click();
																}}
															>
																<Upload
																	className={`h-6 w-6 transition-all ${
																		isDragging
																			? "text-[color:var(--color-primary)] scale-110"
																			: "text-[color:var(--color-text-muted)]"
																	}`}
																/>
																<p className="text-xs font-medium text-slate-700">
																	Drop a file here or click to browse
																</p>
																<p className="text-[10px] text-[color:var(--color-text-muted)]">
																	PDF, DOCX, TXT, CSV, XLSX, images and more
																</p>
															</div>
														);
													})()}
												</div>
												<div className="mt-4 flex items-center justify-end gap-2">
													<button
														type="button"
														onClick={cancelEditing}
														className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 px-3 py-1.5 text-xs text-slate-700 transition-all hover:border-[rgba(var(--color-primary-rgb),0.50)] hover:bg-[color:var(--color-surface)]/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
													>
														Cancel
													</button>
													<button
														type="button"
														onClick={handleSaveEdit}
														disabled={savingEdit}
														className="rounded-xl bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] px-4 py-1.5 text-xs font-medium text-[color:var(--button-primary-text)] shadow-[0_8px_20px_rgba(var(--color-primary-rgb),0.25)] transition-all hover:from-[rgba(var(--color-primary-rgb),0.9)] hover:to-[rgba(var(--color-primary-rgb),0.7)] hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] disabled:opacity-40 disabled:hover:translate-y-0 disabled:shadow-none"
													>
														{savingEdit ? "Saving..." : "Save Changes"}
													</button>
												</div>
											</div>
										);
									}}
								/>
							)}
						</>
					)}

					{/* ── Add Manual tab ── */}
					{activeTab === "manual" && (
						<div className="space-y-5 py-2" data-tutorial="dataset-tab-manual-content">
							<div>
								<label className="mb-1.5 block text-xs font-medium text-slate-500">
									Input
								</label>
								<textarea
									value={inputDataJson}
									onChange={(e) => setInputDataJson(e.target.value)}
									rows={4}
									spellCheck={false}
									placeholder={drawerTargetContext?.input_schema || "Enter the input text to send to the workflow..."}
									className="w-full rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-4 py-3 text-sm leading-relaxed text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all resize-y"
								/>
							</div>
							<div>
								<label className="mb-1.5 block text-xs font-medium text-slate-500">
									File Attachment (optional)
								</label>
								<input
									ref={fileInputRef}
									type="file"
									accept=".pdf,.png,.jpg,.jpeg,.docx,.txt,.xlsx,.csv,.md,.json,.xml,.yaml,.yml,.doc,.rtf,.xls,.gif,.bmp,.svg,.py,.js,.html,.css,.zip,.tar,.gz"
									onChange={(e) => {
										const f = e.target.files?.[0];
										if (f) setPendingFile(f);
										e.target.value = "";
									}}
									style={{ display: "none" }}
								/>
								<div
									className={`rounded-xl border-2 border-dashed p-4 text-center transition-all duration-200 cursor-pointer flex flex-col items-center justify-center gap-2 ${
										isDragging
											? "border-[color:var(--color-primary)] bg-[rgba(var(--color-primary-rgb),0.05)]"
											: pendingFile
												? "border-[color:var(--color-accent)]/60 bg-[color:var(--color-surface)]"
												: "border-[color:var(--color-border)] bg-[color:var(--color-surface)] hover:border-[color:var(--color-primary)]/50"
									}`}
									onDrop={(e) => {
										e.preventDefault();
										setIsDragging(false);
										if (e.dataTransfer.files.length > 0) {
											setPendingFile(e.dataTransfer.files[0]);
										}
									}}
									onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
									onDragLeave={() => setIsDragging(false)}
									onClick={pendingFile ? undefined : () => fileInputRef.current?.click()}
								>
									{pendingFile ? (
										<>
											<FileText className="h-7 w-7 text-[color:var(--color-accent)]" />
											<div className="flex items-center gap-2">
												<span className="text-sm font-medium text-slate-900 truncate max-w-[200px]">
													{pendingFile.name}
												</span>
												<button
													type="button"
													onClick={(e) => { e.stopPropagation(); setPendingFile(null); }}
													className="p-1 rounded hover:bg-[color:var(--color-surface-hover)] text-[color:var(--color-text-muted)] hover:text-slate-900 transition-colors"
												>
													<X className="h-4 w-4" />
												</button>
											</div>
											<p className="text-xs text-[color:var(--color-text-muted)]">
												{formatFileSize(pendingFile.size)} · click the × to change
											</p>
										</>
									) : (
										<>
											<Upload
												className={`h-8 w-8 transition-all ${
													isDragging
														? "text-[color:var(--color-primary)] scale-110"
														: "text-[color:var(--color-text-muted)]"
												}`}
											/>
											<p className="text-sm font-medium text-slate-900">
												Drop a file here or click to browse
											</p>
											<p className="text-xs text-[color:var(--color-text-muted)]">
												PDF, DOCX, TXT, CSV, XLSX, images and more
											</p>
										</>
									)}
								</div>
							</div>
							<div>
								<label className="mb-1.5 block text-xs font-medium text-slate-500">
									Expected Output (optional)
								</label>
								<textarea
									value={expectedOutputJson}
									onChange={(e) => setExpectedOutputJson(e.target.value)}
									rows={3}
									spellCheck={false}
									placeholder="Enter the expected response (used for quality scoring)..."
									className="w-full rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-4 py-3 text-sm leading-relaxed text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all resize-y"
								/>
							</div>
							<div>
								<label className="mb-1.5 block text-xs font-medium text-slate-500">
									Judge Criteria (optional)
								</label>
								<p className="mb-2 text-xs text-slate-400">
									Define what the LLM judge should evaluate. Pick a preset to start, then edit freely.
								</p>
								{/* Preset selector */}
								<div className="mb-3 flex flex-wrap gap-1.5">
									{JUDGE_CRITERIA_PRESETS.map((preset) => (
										<button
											key={preset.label}
											type="button"
											onClick={() =>
												setJudgeCriteria(
													preset.criteria.map((c) => ({ ...c })),
												)
											}
											className="rounded-lg border border-white/[0.08] bg-slate-100 px-2.5 py-1 text-[11px] text-slate-500 transition hover:border-white/15 hover:bg-white/[0.07] hover:text-slate-700"
										>
											{preset.label}
										</button>
									))}
									{drawerTargetContext?.suggested_judge_criteria && judgeCriteria.length === 0 && (
										<button
											type="button"
											onClick={() =>
												setJudgeCriteria(
													Object.entries(drawerTargetContext.suggested_judge_criteria!).map(([key, value]) => ({ key, value: String(value) })),
												)
											}
											className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-2.5 py-1 text-[11px] text-emerald-400/70 transition hover:border-emerald-500/30 hover:bg-emerald-500/10 hover:text-emerald-400"
										>
											Load suggested criteria
										</button>
									)}
									{judgeCriteria.length > 0 && (
										<button
											type="button"
											onClick={() => setJudgeCriteria([])}
											className="rounded-lg border border-red-500/10 px-2.5 py-1 text-[11px] text-red-400/50 transition hover:border-red-500/20 hover:bg-red-500/5 hover:text-red-400/70"
										>
											Clear All
										</button>
									)}
								</div>
								{/* Key/value rows */}
								{judgeCriteria.map((row, idx) => (
									<div key={idx} className="mb-2 flex items-start gap-2">
										<input
											type="text"
											value={row.key}
											onChange={(e) => {
												const next = [...judgeCriteria];
												next[idx] = { ...next[idx], key: e.target.value };
												setJudgeCriteria(next);
											}}
											placeholder="Criterion name"
											className="w-40 shrink-0 rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-sm text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all"
										/>
										<input
											type="text"
											value={row.value}
											onChange={(e) => {
												const next = [...judgeCriteria];
												next[idx] = { ...next[idx], value: e.target.value };
												setJudgeCriteria(next);
											}}
											placeholder="Description of what to evaluate"
											className="min-w-0 flex-1 rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-sm text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all"
										/>
										<button
											type="button"
											onClick={() =>
												setJudgeCriteria(judgeCriteria.filter((_, i) => i !== idx))
											}
											className="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-lg text-slate-300 transition hover:bg-red-500/10 hover:text-red-400/60"
										>
											<svg width="12" height="12" viewBox="0 0 12 12" fill="none">
												<path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
											</svg>
										</button>
									</div>
								))}
								<button
									type="button"
									onClick={() =>
										setJudgeCriteria([...judgeCriteria, { key: "", value: "" }])
									}
									className="mt-1 flex items-center gap-1.5 rounded-lg border border-dashed border-slate-200 px-3 py-1.5 text-xs text-slate-400 transition hover:border-slate-300 hover:text-slate-500"
								>
									<svg width="10" height="10" viewBox="0 0 10 10" fill="none">
										<path d="M5 1v8M1 5h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
									</svg>
									Add criterion
								</button>
							</div>
							<div>
								<label className="mb-1.5 block text-xs font-medium text-slate-500">
									Tags (comma-separated, optional)
								</label>
								{drawerTargetContext?.suggested_tags && drawerTargetContext.suggested_tags.length > 0 && (
									<div className="mb-2 flex flex-wrap gap-1">
										{drawerTargetContext.suggested_tags.map((tag) => (
											<button
												key={tag}
												type="button"
												onClick={() => {
													const existing = tagsInput.split(",").map((t) => t.trim()).filter(Boolean);
													if (!existing.includes(tag)) {
														setTagsInput(existing.length > 0 ? `${tagsInput.trimEnd()}, ${tag}` : tag);
													}
												}}
												className="bg-slate-100 hover:bg-white/[0.10] rounded-full px-2 py-0.5 text-[10px] text-slate-500 transition"
											>
												+ {tag}
											</button>
										))}
									</div>
								)}
								<input
									type="text"
									value={tagsInput}
									onChange={(e) => setTagsInput(e.target.value)}
									placeholder="e.g. happy-path, edge-case, regression"
									className="w-full rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-4 py-2.5 text-sm text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all"
								/>
							</div>
							{testCases.length >= MAX_CAP && (
								<p className="text-xs text-red-400">Dataset full — delete cases to add more.</p>
							)}
							<button
								type="button"
								onClick={handleAddManual}
								disabled={addingManual || testCases.length >= MAX_CAP}
								className="w-full rounded-xl bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] px-4 py-3 text-sm font-semibold text-[color:var(--button-primary-text)] shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.35)] transition-all hover:from-[rgba(var(--color-primary-rgb),0.9)] hover:to-[rgba(var(--color-primary-rgb),0.7)] hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:shadow-none"
							>
								{uploadingFile ? "Uploading file..." : addingManual ? "Adding..." : "Add Test Case"}
							</button>
						</div>
					)}

					{/* ── AI Generate tab ── */}
					{activeTab === "ai" && (
						<div className="space-y-5 py-2" data-tutorial="dataset-tab-ai-content">
							{/* Context enrichment (auto) */}
							{drawerTargetContext?.ai_seed_enrichment && (
								<div>
									<div className="flex items-center justify-between">
										<span className="text-[11px] text-slate-400">Context (auto)</span>
										<button
											type="button"
											onClick={() => {
												if (!dataset.target_id || !dataset.target_type) return;
												setDrawerContextLoading(true);
												evalApi
													.getTargetContext(dataset.target_type, dataset.target_id, dataset.workflow_id || undefined)
													.then(setDrawerTargetContext)
													.catch(() => {})
													.finally(() => setDrawerContextLoading(false));
											}}
											className="rounded-full p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
											title="Refresh context"
										>
											{drawerContextLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <span className="text-xs">&#8634;</span>}
										</button>
									</div>
									<div className="mt-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-400 font-mono whitespace-pre-wrap">
										{drawerTargetContext.ai_seed_enrichment}
									</div>
								</div>
							)}

							<div>
								<label className="mb-1.5 block text-xs font-medium text-slate-500">
									{drawerTargetContext?.ai_seed_enrichment ? "Additional Guidance" : "Seed Prompt"}
								</label>
								<p className="mb-2 text-xs text-slate-400">
									Describe what kind of test cases to generate. Be specific about the inputs,
									expected behaviors, and scenarios you want to cover.
								</p>
								<textarea
									value={seedPrompt}
									onChange={(e) => setSeedPrompt(e.target.value)}
									rows={5}
									placeholder="e.g. Generate test cases for a customer support chatbot that handles billing inquiries, account changes, and technical troubleshooting..."
									className="w-full rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-4 py-3 text-sm leading-relaxed text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all resize-y"
								/>
							</div>
							<div>
								<label className="mb-1.5 flex items-center justify-between text-xs font-medium text-slate-500">
									<span>Number of test cases</span>
									<span className="tabular-nums text-slate-700">{genCount}</span>
								</label>
								<input
									type="range"
									min={1}
									max={20}
									value={genCount}
									onChange={(e) => setGenCount(Number(e.target.value))}
									className="w-full accent-[rgba(var(--color-primary-rgb),0.8)]"
								/>
								<div className="mt-1 flex justify-between text-[10px] text-slate-300">
									<span>1</span>
									<span>20</span>
								</div>
							</div>
							<div className="flex gap-6">
								<label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
									<input
										type="checkbox"
										checked={includeEdgeCases}
										onChange={(e) => setIncludeEdgeCases(e.target.checked)}
										className="h-4 w-4 rounded border-slate-300 accent-[rgba(var(--color-primary-rgb),0.8)]"
									/>
									Include edge cases
								</label>
								<label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
									<input
										type="checkbox"
										checked={includeAdversarial}
										onChange={(e) => setIncludeAdversarial(e.target.checked)}
										className="h-4 w-4 rounded border-slate-300 accent-[rgba(var(--color-primary-rgb),0.8)]"
									/>
									Include adversarial
								</label>
							</div>
							<div>
								<label className="mb-1.5 block text-xs font-medium text-slate-500">
									Generator Model (optional)
								</label>
								{genModelsLoading ? (
									<div className="flex items-center gap-2 rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
										<Loader2 className="h-3.5 w-3.5 animate-spin" />
										Loading models...
									</div>
								) : genModelOptions.length > 0 ? (
									<Dropdown
										value={generatorModelId}
										onChange={setGeneratorModelId}
										options={[{ value: "", label: "System Default", description: "Use the platform default model" }, ...genModelOptions]}
										placeholder="System Default"
										className="w-full"
										triggerClassName="border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 hover:bg-[color:var(--color-surface)]/80 hover:border-[rgba(var(--color-primary-rgb),0.4)] text-[color:var(--color-text-primary)]"
									/>
								) : (
									<p className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
										No model deployments configured.
									</p>
								)}
								<p className="mt-1 text-[11px] text-slate-400">LLM used to generate test cases. Leave empty for system default.</p>
							</div>
							{/* Few-shot examples from positive executions */}
							<div className="rounded-xl border border-slate-200 bg-slate-50">
								<button
									type="button"
									onClick={() => setFewShotExpanded(!fewShotExpanded)}
									className="flex w-full items-center justify-between px-4 py-3 text-left"
								>
									<div>
										<span className="text-xs font-medium text-slate-500">
											Examples from Runs
											{fewShotSelectedIds.size > 0 && (
												<span className="ml-1.5 rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[10px] text-emerald-400">
													{fewShotSelectedIds.size} selected
												</span>
											)}
										</span>
										<p className="mt-0.5 text-[11px] text-slate-400">
											Select positively-rated runs as few-shot examples to guide generation style and format.
										</p>
									</div>
									{fewShotExpanded ? (
										<ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
									) : (
										<ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
									)}
								</button>
								{fewShotExpanded && (
									<div className="border-t border-slate-100 px-4 pb-3 pt-2">
										{fewShotLoading ? (
											<div className="flex items-center gap-2 py-4 text-xs text-slate-400">
												<Loader2 className="h-3.5 w-3.5 animate-spin" />
												Loading positive executions...
											</div>
										) : fewShotExecutions.length === 0 ? (
											<div className="py-4 text-center">
												<p className="text-xs text-slate-400">No positively-rated executions found.</p>
												<p className="mt-0.5 text-[10px] text-slate-300">
													Rate runs with thumbs-up in Execution History to use them as examples.
												</p>
											</div>
										) : (
											<>
												<div className="max-h-[280px] overflow-y-auto">
													<CaseListTable
														items={fewShotCaseItems}
														selectedIds={fewShotSelectedIds}
														onToggleSelect={toggleFewShotSelection}
														expandedId={fewShotExpandedId}
														onToggleExpand={setFewShotExpandedId}
														compact
													/>
												</div>
												{fewShotSelectedIds.size > 0 && (
													<button
														type="button"
														onClick={() => setFewShotSelectedIds(new Set())}
														className="mt-2 text-[10px] text-slate-400 transition hover:text-slate-500"
													>
														Clear selection
													</button>
												)}
											</>
										)}
									</div>
								)}
							</div>
							{testCases.length >= MAX_CAP && (
								<p className="text-xs text-red-400">Dataset full — delete cases to add more.</p>
							)}
							{generating && (
								<div className="space-y-2">
									<div className="flex items-center justify-between text-xs">
										<span className="text-slate-500">Generating test cases...</span>
										<span className="tabular-nums font-medium text-slate-700">
											{genProgress} / {genCount}
										</span>
									</div>
									<div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
										<div
											className="h-full rounded-full bg-[rgba(var(--color-primary-rgb),0.6)] transition-all duration-500 ease-out"
											style={{ width: `${(genProgress / genCount) * 100}%` }}
										/>
									</div>
								</div>
							)}
							<button
								type="button"
								onClick={handleAiGenerate}
								disabled={generating || (!seedPrompt.trim() && !drawerTargetContext?.ai_seed_enrichment) || testCases.length >= MAX_CAP}
								className="w-full rounded-xl bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] px-4 py-3 text-sm font-semibold text-[color:var(--button-primary-text)] shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.35)] transition-all hover:from-[rgba(var(--color-primary-rgb),0.9)] hover:to-[rgba(var(--color-primary-rgb),0.7)] hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:shadow-none flex items-center justify-center gap-2"
							>
								{generating && <Loader2 className="h-4 w-4 animate-spin" />}
								{generating ? `Generating ${genProgress} of ${genCount}...` : `Generate ${genCount} Test Case${genCount !== 1 ? "s" : ""}`}
							</button>
						</div>
					)}

					{/* ── Import from Runs tab ── */}
					{/* ── Export / Import tab ── */}
					{activeTab === "export-import" && (
						<ExportImportTabContent
							dataset={dataset}
							testCases={testCases}
							onImported={async () => {
								await loadCases();
								onRefreshDatasets();
								setActiveTab("cases");
							}}
							onError={setError}
						/>
					)}

					{activeTab === "import-executions" && (
						<div className="space-y-5 py-2">
							<div>
								<p className="text-sm text-slate-500">
									Import positively-rated execution runs as test cases. Only runs you&apos;ve given a
									<ThumbsUp className="mx-1 inline h-3.5 w-3.5 text-emerald-400" />
									rating in Execution History are shown.
								</p>
							</div>

							{importLoading ? (
								<div className="flex items-center justify-center gap-2 py-16">
									<Loader2 className="h-5 w-5 animate-spin text-slate-500" />
									<span className="text-sm text-slate-500">Loading positive executions...</span>
								</div>
							) : importExecutions.length === 0 ? (
								<div className="py-16 text-center">
									<ThumbsUp className="mx-auto h-8 w-8 text-white/15" />
									<p className="mt-3 text-sm text-slate-500">No positively-rated executions found.</p>
									<p className="mt-1 text-xs text-slate-400">
										Rate executions with thumbs-up in Execution History to import them as test cases.
									</p>
									<button
										type="button"
										onClick={() => loadPositiveExecutions("import")}
										className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-500 transition hover:border-slate-300 hover:text-slate-700"
									>
										Refresh
									</button>
								</div>
							) : (
								<>
									{/* Selection controls */}
									<div className="flex items-center justify-between">
										<span className="text-xs text-slate-500">
											{importSelectedIds.size} of {importExecutions.length} selected
										</span>
										<div className="flex gap-2">
											<button
												type="button"
												onClick={() => setImportSelectedIds(new Set(importExecutions.map((e: any) => e.id)))}
												className="text-xs text-slate-500 transition hover:text-slate-700"
											>
												Select all
											</button>
											<span className="text-white/15">|</span>
											<button
												type="button"
												onClick={() => setImportSelectedIds(new Set())}
												className="text-xs text-slate-500 transition hover:text-slate-700"
											>
												Clear
											</button>
											<span className="text-white/15">|</span>
											<button
												type="button"
												onClick={() => loadPositiveExecutions("import")}
												className="text-xs text-slate-500 transition hover:text-slate-700"
											>
												Refresh
											</button>
										</div>
									</div>

									<CaseListTable
										items={importCaseItems}
										selectedIds={importSelectedIds}
										onToggleSelect={toggleImportSelection}
										expandedId={importExpandedId}
										onToggleExpand={setImportExpandedId}
									/>

									{/* Import options */}
									<div className="space-y-3">
										<label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
											<input
												type="checkbox"
												checked={importIncludeExpected}
												onChange={(e) => setImportIncludeExpected(e.target.checked)}
												className="h-4 w-4 rounded border-slate-300 accent-[rgba(var(--color-primary-rgb),0.8)]"
											/>
											Include execution output as expected output
										</label>
										<div>
											<label className="mb-1.5 block text-xs font-medium text-slate-500">
												Additional tags (comma-separated, optional)
											</label>
											<input
												type="text"
												value={importTagsInput}
												onChange={(e) => setImportTagsInput(e.target.value)}
												placeholder="e.g. exemplar, golden"
												className="w-full rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-4 py-2.5 text-sm text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.15)] transition-all"
											/>
										</div>
									</div>

									{atCapacity && (
										<p className="text-xs text-red-400">Dataset full — delete cases to add more.</p>
									)}

									{/* Import button */}
									<button
										type="button"
										onClick={handleImportExecutions}
										disabled={importing || importSelectedIds.size === 0 || atCapacity}
										className="w-full rounded-xl bg-gradient-to-br from-emerald-600 to-emerald-700 px-4 py-3 text-sm font-semibold text-slate-900 shadow-[0_15px_40px_rgba(16,185,129,0.25)] transition-all hover:from-emerald-500 hover:to-emerald-600 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/45 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:shadow-none flex items-center justify-center gap-2"
									>
										{importing && <Loader2 className="h-4 w-4 animate-spin" />}
										{importing
											? "Importing..."
											: `Import ${importSelectedIds.size} Execution${importSelectedIds.size !== 1 ? "s" : ""} as Test Cases`}
									</button>
								</>
							)}
						</div>
					)}
				</div>
			</div>

			{/* Edit metadata modal */}
			{editingMetadata && (
				<DatasetMetadataModal
					existingDataset={currentDataset}
					onClose={() => setEditingMetadata(false)}
					onSaved={(updated) => {
						setCurrentDataset(updated);
						setEditingMetadata(false);
						onRefreshDatasets();
					}}
				/>
			)}
		</div>
	);
}

/* ────────────────────────────────────────────────────────────────────────────
   Export / Import tab – export dataset as JSON, import test cases from JSON
   ──────────────────────────────────────────────────────────────────────────── */

function ExportImportTabContent({
	dataset,
	testCases,
	onImported,
	onError,
}: {
	dataset: EvaluationDataset;
	testCases: TestCase[];
	onImported: () => Promise<void>;
	onError: (msg: string) => void;
}) {
	const [exporting, setExporting] = useState(false);
	const [importing, setImporting] = useState(false);
	const [isDragging, setIsDragging] = useState(false);
	const [importPreview, setImportPreview] = useState<DatasetExport | null>(null);
	const fileInputRef = useRef<HTMLInputElement>(null);

	const handleExport = async () => {
		setExporting(true);
		try {
			const data = await evalApi.exportDataset(dataset.id);
			const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
			const url = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download = `${dataset.name.replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		} catch (err: any) {
			onError(err.message ?? "Failed to export dataset");
		} finally {
			setExporting(false);
		}
	};

	const loadFile = async (file: File) => {
		try {
			const text = await file.text();
			const payload: DatasetExport = JSON.parse(text);
			if (payload.format !== "nexus-dataset-v1") {
				onError("Invalid file format. Expected a Nexus dataset export (nexus-dataset-v1).");
				return;
			}
			if (!payload.test_cases || payload.test_cases.length === 0) {
				onError("The file contains no test cases to import.");
				return;
			}
			setImportPreview(payload);
		} catch {
			onError("Failed to read file. Ensure it is a valid JSON dataset export.");
		}
	};

	const handleImport = async () => {
		if (!importPreview) return;
		setImporting(true);
		try {
			const casesToAdd = importPreview.test_cases.map((tc) => ({
				input_data: tc.input_data,
				expected_output: tc.expected_output ?? undefined,
				judge_criteria: tc.judge_criteria ?? undefined,
				tags: tc.tags ?? undefined,
			}));
			const added = await evalApi.addTestCases(dataset.id, { manual: casesToAdd });

			// Upload file attachments for cases that had file_info
			for (let i = 0; i < importPreview.test_cases.length; i++) {
				const fi = importPreview.test_cases[i].file_info;
				if (!fi?.base64 || !added[i]) continue;
				try {
					const byteChars = atob(fi.base64);
					const bytes = new Uint8Array(byteChars.length);
					for (let j = 0; j < byteChars.length; j++) bytes[j] = byteChars.charCodeAt(j);
					const blob = new Blob([bytes], { type: fi.type || "application/octet-stream" });
					const file = new File([blob], fi.name || "uploaded_file", { type: fi.type || "application/octet-stream" });
					await evalApi.uploadTestCaseFile(dataset.id, added[i].id, file);
				} catch {
					// Skip files that fail to upload
				}
			}

			setImportPreview(null);
			await onImported();
		} catch (err: any) {
			onError(err.message ?? "Failed to import test cases");
		} finally {
			setImporting(false);
		}
	};

	const filesInPreview = importPreview?.test_cases.filter((tc) => tc.file_info?.base64).length ?? 0;

	return (
		<div className="space-y-6 py-2">
			{/* Export section */}
			<div>
				<h3 className="text-sm font-medium text-slate-900 mb-2">Export Dataset</h3>
				<p className="text-xs text-slate-500 mb-3">
					Download this dataset as a JSON file including all {testCases.length} test case{testCases.length !== 1 ? "s" : ""}
					{testCases.some((tc) => tc.files && tc.files.length > 0) ? " and file attachments" : ""}.
					The file can be shared and imported into any other dataset.
				</p>
				<button
					type="button"
					onClick={handleExport}
					disabled={exporting || testCases.length === 0}
					className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] px-4 py-2.5 text-sm font-semibold text-[color:var(--button-primary-text)] shadow-[0_8px_20px_rgba(var(--color-primary-rgb),0.25)] transition-all hover:from-[rgba(var(--color-primary-rgb),0.9)] hover:to-[rgba(var(--color-primary-rgb),0.7)] hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:shadow-none"
				>
					{exporting ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
					{exporting ? "Exporting…" : `Export ${testCases.length} Test Case${testCases.length !== 1 ? "s" : ""}`}
				</button>
			</div>

			<div className="border-t border-slate-200" />

			{/* Import section */}
			<div>
				<h3 className="text-sm font-medium text-slate-900 mb-2">Import Test Cases from File</h3>
				<p className="text-xs text-slate-500 mb-3">
					Import test cases from a previously exported JSON file into this dataset.
					File attachments in the export will be restored automatically.
				</p>

				{!importPreview ? (
					<>
						<input
							ref={fileInputRef}
							type="file"
							accept=".json"
							className="sr-only"
							onChange={(e) => {
								const f = e.target.files?.[0];
								if (f) loadFile(f);
								e.target.value = "";
							}}
						/>
						<div
							className={`rounded-xl border-2 border-dashed p-6 text-center transition-all duration-200 cursor-pointer flex flex-col items-center justify-center gap-2 ${
								isDragging
									? "border-[color:var(--color-primary)] bg-[rgba(var(--color-primary-rgb),0.05)]"
									: "border-[color:var(--color-border)] bg-[color:var(--color-surface)] hover:border-[color:var(--color-primary)]/50"
							}`}
							onDrop={(e) => {
								e.preventDefault();
								setIsDragging(false);
								if (e.dataTransfer.files.length > 0) loadFile(e.dataTransfer.files[0]);
							}}
							onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
							onDragLeave={() => setIsDragging(false)}
							onClick={() => fileInputRef.current?.click()}
						>
							<Upload
								className={`h-8 w-8 transition-all ${
									isDragging
										? "text-[color:var(--color-primary)] scale-110"
										: "text-[color:var(--color-text-muted)]"
								}`}
							/>
							<p className="text-sm font-medium text-slate-900">
								Drop a dataset JSON file here or click to browse
							</p>
							<p className="text-xs text-[color:var(--color-text-muted)]">
								Accepts .json files exported from Nexus
							</p>
						</div>
					</>
				) : (
					<div className="space-y-3">
						<div className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 p-4">
							<div className="flex items-center justify-between mb-2">
								<h4 className="text-sm font-medium text-slate-900">Import Preview</h4>
								<button
									type="button"
									onClick={() => setImportPreview(null)}
									className="text-xs text-slate-500 hover:text-slate-700 transition-colors"
								>
									Cancel
								</button>
							</div>
							<div className="space-y-1.5 text-xs text-slate-600">
								<p>
									<span className="text-slate-500">Source dataset:</span>{" "}
									<span className="text-slate-900">{importPreview.dataset.name}</span>
								</p>
								{importPreview.dataset.description && (
									<p>
										<span className="text-slate-500">Description:</span>{" "}
										{importPreview.dataset.description}
									</p>
								)}
								<p>
									<span className="text-slate-500">Target type:</span>{" "}
									<span className="text-slate-900">{importPreview.dataset.target_type}</span>
								</p>
								{(importPreview.dataset.target_name || importPreview.dataset.workflow_name) && (
									<p>
										<span className="text-slate-500">Target:</span>{" "}
										{importPreview.dataset.workflow_name && (
											<span className="text-slate-900">{importPreview.dataset.workflow_name}</span>
										)}
										{importPreview.dataset.workflow_name && importPreview.dataset.target_name && importPreview.dataset.target_name !== importPreview.dataset.workflow_name && (
											<span className="text-slate-500"> / </span>
										)}
										{importPreview.dataset.target_name && importPreview.dataset.target_name !== importPreview.dataset.workflow_name && (
											<span className="text-slate-900">{importPreview.dataset.target_name}</span>
										)}
									</p>
								)}
								<p>
									<span className="text-slate-500">Test cases:</span>{" "}
									<span className="text-slate-900">{importPreview.test_cases.length}</span>
								</p>
								{filesInPreview > 0 && (
									<p>
										<span className="text-slate-500">File attachments:</span>{" "}
										<span className="text-slate-900">{filesInPreview}</span>
									</p>
								)}
							</div>
						</div>

						<button
							type="button"
							onClick={handleImport}
							disabled={importing}
							className="w-full rounded-xl bg-gradient-to-br from-emerald-600 to-emerald-700 px-4 py-3 text-sm font-semibold text-slate-900 shadow-[0_15px_40px_rgba(16,185,129,0.25)] transition-all hover:from-emerald-500 hover:to-emerald-600 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/45 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:shadow-none flex items-center justify-center gap-2"
						>
							{importing && <Loader2 className="h-4 w-4 animate-spin" />}
							{importing
								? "Importing…"
								: `Import ${importPreview.test_cases.length} Test Case${importPreview.test_cases.length !== 1 ? "s" : ""}${filesInPreview > 0 ? ` with ${filesInPreview} file${filesInPreview !== 1 ? "s" : ""}` : ""}`}
						</button>
					</div>
				)}
			</div>
		</div>
	);
}
