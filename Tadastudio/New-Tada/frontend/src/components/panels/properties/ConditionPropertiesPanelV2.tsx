"use client";

import {
	ArrowDownToLine,
	GitBranch,
	Save,
	Settings,
	Trash2,
	X,
	Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useGraph } from "@/contexts/GraphContext";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import ConfigSidebar from "./ConfigSidebar";
import DataSourceSection from "./sections/DataSourceSection";
import EvaluationRulesSection from "./sections/EvaluationRulesSection";
import SettingsSection from "./sections/SettingsSection";

interface SimpleCondition {
	input_source?: string;
	source_node_id?: string;
	field_path?: string;
	operator?: string;
	value?: any;
	value_type?: string;
	dynamic_source?: any;
	custom_template?: string;
}

interface BranchConfig {
	label: string;
	color: string;
	handle_id: string;
	condition: SimpleCondition;
}

interface PassthroughConfig {
	mode: "all" | "filter";
	fields?: string[];
}

interface ConditionConfig {
	branch_mode?: string;
	branches?: BranchConfig[];
	condition_type?: string;
	simple_conditions?: SimpleCondition[];
	expression?: string;
	llm_prompt?: string;
	logic_operator?: string;
	branch_count?: number;
	branch_labels?: string[];
	has_default_branch?: boolean;
	default_branch_label?: string;
	input_source?: string;
	source_node_id?: string;
	field_path?: string;
	passthrough_config?: PassthroughConfig;
}

type TabId = "rules" | "source" | "settings";

interface ConditionPropertiesPanelV2Props {
	nodeId: string;
	onClose: () => void;
}

export default function ConditionPropertiesPanelV2({
	nodeId,
	onClose,
}: ConditionPropertiesPanelV2Props) {
	const { nodes, edges, updateNode, deleteNode } = useGraph();
	const node = nodes.find((n) => n.id === nodeId);

	const [nodeName, setNodeName] = useState(node?.data?.name || "Condition");
	const [config, setConfig] = useState<ConditionConfig>({
		branch_mode: "binary",
		branches: [],
		condition_type: "simple",
		simple_conditions: [],
		expression: "",
		llm_prompt: "",
		logic_operator: "AND",
		branch_count: 2,
		branch_labels: ["True", "False"],
		has_default_branch: false,
		default_branch_label: "Default",
		input_source: "previous",
		source_node_id: undefined,
		field_path: "",
		passthrough_config: { mode: "all" },
	});

	const [saving, setSaving] = useState(false);
	const [inputSourceConfig, setInputSourceConfig] = useState<any>(null);
	const [activeTab, setActiveTab] = useState<TabId>("rules");
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const contentRef = useRef<HTMLDivElement>(null);

	// Track initial values for unsaved changes
	const initialValues = useRef({
		name: node?.data?.name || "Condition",
		config: JSON.stringify(node?.data?.condition_config || {}),
	});

	// Initialize with existing config
	useEffect(() => {
		if (node?.data) {
			setNodeName(node.data.name || "Condition");
			if (node.data.condition_config) {
				const existingConfig = node.data.condition_config;

				const isc = node.data.input_source_config;
				const inputSource =
					isc?.source_mode || existingConfig.input_source || "previous";
				const sourceNodeId =
					isc?.source_mode === "specific"
						? (isc.source_node_id ?? existingConfig.source_node_id)
						: existingConfig.source_node_id;

				setConfig({
					...existingConfig,
					branch_mode: existingConfig.branch_mode || "binary",
					branches: existingConfig.branches || [],
					branch_labels: existingConfig.branch_labels || ["True", "False"],
					input_source: inputSource,
					source_node_id: sourceNodeId,
					field_path: existingConfig.field_path || "",
					condition_type: existingConfig.condition_type || "simple",
					simple_conditions: existingConfig.simple_conditions || [],
					expression: existingConfig.expression || "",
					logic_operator: existingConfig.logic_operator || "AND",
					has_default_branch: existingConfig.has_default_branch || false,
					default_branch_label:
						existingConfig.default_branch_label || "Default",
					passthrough_config: existingConfig.passthrough_config || {
						mode: "all",
					},
				});
			}
			setInputSourceConfig(node.data.input_source_config || null);
		}
	}, [node]);

	// Responsive sidebar collapse
	useEffect(() => {
		const el = contentRef.current;
		if (!el || typeof ResizeObserver === "undefined") return;
		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				setSidebarCollapsed(entry.contentRect.width < 400);
			}
		});
		observer.observe(el);
		return () => observer.disconnect();
	}, []);

	// Unsaved changes detection
	const hasUnsavedChanges = useMemo(() => {
		const init = initialValues.current;
		return nodeName !== init.name || JSON.stringify(config) !== init.config;
	}, [nodeName, config]);

	// Upstream nodes (excluding self and END nodes)
	const upstreamNodes = useMemo(() => {
		if (!node) return [];
		return nodes.filter((n) => n.id !== nodeId && n.data?.type !== "END");
	}, [nodes, node, nodeId]);

	// Resolve connected source node
	const connectedSourceNode = useMemo(() => {
		if (config.input_source === "specific" && config.source_node_id) {
			return nodes.find((n) => n.id === config.source_node_id);
		}
		// Default: find node connected via edges (previous node)
		const incomingEdge = edges.find((e) => e.target === nodeId);
		if (incomingEdge) {
			return nodes.find((n) => n.id === incomingEdge.source);
		}
		return undefined;
	}, [config.input_source, config.source_node_id, edges, nodeId, nodes]);

	// Sidebar items
	const sidebarItems = useMemo(
		() => [
			{
				id: "rules",
				label: "Rules",
				icon: <Zap className="h-4 w-4" />,
			},
			{
				id: "source",
				label: "Data Source",
				icon: <ArrowDownToLine className="h-4 w-4" />,
			},
			{
				id: "settings",
				label: "Settings",
				icon: <Settings className="h-4 w-4" />,
			},
		],
		[],
	);

	// --- Config update callbacks ---

	const handleInputSourceChange = useCallback((source: string) => {
		setConfig((prev) => ({
			...prev,
			input_source: source,
			source_node_id: source !== "specific" ? undefined : prev.source_node_id,
		}));
		setInputSourceConfig((prev: any) => ({
			...prev,
			source_mode: source,
			source_node_id: source !== "specific" ? null : prev?.source_node_id,
		}));
	}, []);

	const handleSourceNodeIdChange = useCallback((nodeId?: string) => {
		setConfig((prev) => ({ ...prev, source_node_id: nodeId }));
		setInputSourceConfig((prev: any) => ({
			...prev,
			source_mode: "specific",
			source_node_id: nodeId || null,
		}));
	}, []);

	const handleBranchModeChange = useCallback((mode: "binary" | "multi") => {
		if (mode === "binary") {
			setConfig((prev) => ({
				...prev,
				branch_mode: "binary",
				branches: [],
				branch_labels: prev.branch_labels || ["True", "False"],
			}));
		} else {
			setConfig((prev) => {
				const defaultBranches: BranchConfig[] = [
					{
						label: "Approve",
						color: "#0DA931",
						handle_id: "branch-0",
						condition: {},
					},
					{
						label: "Review",
						color: "#f59e0b",
						handle_id: "branch-1",
						condition: {},
					},
					{
						label: "Reject",
						color: "#ef4444",
						handle_id: "branch-2",
						condition: {},
					},
				];
				return {
					...prev,
					branch_mode: "multi",
					branches:
						prev.branches && prev.branches.length > 0
							? prev.branches
							: defaultBranches,
				};
			});
		}
	}, []);

	const handleBranchLabelsChange = useCallback((labels: string[]) => {
		setConfig((prev) => ({ ...prev, branch_labels: labels }));
	}, []);

	const handleBranchesChange = useCallback((branches: BranchConfig[]) => {
		setConfig((prev) => ({ ...prev, branches }));
	}, []);

	const handleFieldPathChange = useCallback((path: string) => {
		setConfig((prev) => ({ ...prev, field_path: path }));
	}, []);

	const handleConditionTypeChange = useCallback(
		(type: "simple" | "expression") => {
			setConfig((prev) => ({ ...prev, condition_type: type }));
		},
		[],
	);

	const handleExpressionChange = useCallback((expression: string) => {
		setConfig((prev) => ({ ...prev, expression }));
	}, []);

	const handleDefaultBranchChange = useCallback((has: boolean) => {
		setConfig((prev) => ({ ...prev, has_default_branch: has }));
	}, []);

	const handleDefaultBranchLabelChange = useCallback((label: string) => {
		setConfig((prev) => ({ ...prev, default_branch_label: label }));
	}, []);

	// Save handler
	const handleSave = useCallback(async () => {
		setSaving(true);
		try {
			const saveConfig: ConditionConfig = {
				...config,
				branch_mode: config.branch_mode || "binary",
				branches:
					config.branch_mode === "multi"
						? (config.branches || []).map((branch, index) => ({
								...branch,
								handle_id: branch.handle_id || `branch-${index}`,
								color: branch.color || "#8b5cf6",
								label: branch.label || `Branch ${index + 1}`,
								condition: {
									...(branch.condition || {}),
									input_source:
										branch.condition?.input_source ||
										config.input_source ||
										"previous",
									source_node_id:
										branch.condition?.source_node_id ||
										config.source_node_id ||
										undefined,
								},
							}))
						: [],
				branch_labels:
					config.branch_mode === "binary" ? config.branch_labels : undefined,
				input_source:
					config.branch_mode === "binary" ? config.input_source : undefined,
				source_node_id:
					config.branch_mode === "binary" ? config.source_node_id : undefined,
				field_path:
					config.branch_mode === "binary" ? config.field_path : undefined,
				simple_conditions:
					config.branch_mode === "multi" ? config.simple_conditions : [],
			};

			const updateData: any = {
				name: nodeName,
				condition_config: saveConfig,
			};

			if (inputSourceConfig) {
				updateData.input_source_config = inputSourceConfig;
			}

			await updateNode(nodeId, updateData);

			initialValues.current = {
				name: nodeName,
				config: JSON.stringify(saveConfig),
			};

			setTimeout(() => {
				onClose();
			}, 100);
		} catch (error) {
			console.error("Failed to save condition config:", error);
		} finally {
			setSaving(false);
		}
	}, [config, nodeName, nodeId, updateNode, onClose, inputSourceConfig]);

	// Delete handler
	const handleDelete = useCallback(async () => {
		setShowDeleteConfirm(true);
	}, []);

	const handleConfirmDelete = useCallback(async () => {
		await deleteNode(nodeId);
		onClose();
	}, [deleteNode, nodeId, onClose]);

	// Keyboard shortcut: Cmd/Ctrl+S
	const handleSaveRef = useRef(handleSave);
	handleSaveRef.current = handleSave;

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === "s") {
				e.preventDefault();
				handleSaveRef.current();
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, []);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	return (
		<div
			className="fixed inset-0 z-[110] flex animate-fadeIn items-start justify-center bg-black/50 px-4 pb-4 pt-[5vh] backdrop-blur-sm"
			onClick={handleBackdropClick}
		>
			<div className="w-[85vw] max-w-[1800px]" onClick={handleStopPropagation}>
				<div
					className="flex max-h-[80vh] min-h-[320px] flex-col overflow-hidden rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]"
				>
					<div className="flex-none border-b border-gray-200 bg-white">
						<div className="flex flex-wrap items-start justify-between gap-4 px-6 pb-4 pt-5">
							<div className="flex min-w-0 items-start gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
									<GitBranch className="h-5 w-5 text-orange-600" aria-hidden />
								</div>
								<div className="min-w-0">
									<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
										Tool configuration
									</p>
									<h2 className="text-lg font-semibold tracking-tight text-gray-900">
										Condition Configuration
									</h2>
									<p className="mt-0.5 text-sm text-gray-600">
										Configure branching logic and decision paths
									</p>
								</div>
							</div>
							<div className="flex flex-wrap items-center gap-3">
								<input
									type="text"
									value={nodeName}
									onChange={(e) => setNodeName(e.target.value)}
									placeholder="Node name..."
									className="w-[200px] rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								/>
								<button
									type="button"
									onClick={onClose}
									className="shrink-0 rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
									aria-label="Close"
								>
									<X className="h-5 w-5" />
								</button>
							</div>
						</div>
					</div>

					<div
						ref={contentRef}
						className="flex min-h-0 flex-1 overflow-hidden"
					>
						<ConfigSidebar
							items={sidebarItems}
							activeItem={activeTab}
							onChange={(id) => setActiveTab(id as TabId)}
							collapsed={sidebarCollapsed}
							variant="light"
						/>

						<div className="min-h-0 flex-1 overflow-y-auto bg-slate-50 px-6 py-4">
							<div className="space-y-6">
								{activeTab === "rules" && (
									<EvaluationRulesSection
										branchMode={config.branch_mode || "binary"}
										onBranchModeChange={handleBranchModeChange}
										branchLabels={config.branch_labels || ["True", "False"]}
										onBranchLabelsChange={handleBranchLabelsChange}
										fieldPath={config.field_path || ""}
										onFieldPathChange={handleFieldPathChange}
										connectedSourceNode={connectedSourceNode}
										branches={config.branches || []}
										onBranchesChange={handleBranchesChange}
									/>
								)}

								{activeTab === "source" && (
									<DataSourceSection
										inputSource={config.input_source || "previous"}
										sourceNodeId={config.source_node_id}
										availableNodes={upstreamNodes}
										connectedSourceNode={connectedSourceNode}
										onInputSourceChange={handleInputSourceChange}
										onSourceNodeIdChange={handleSourceNodeIdChange}
									/>
								)}

								{activeTab === "settings" && (
									<SettingsSection
										hasDefaultBranch={config.has_default_branch || false}
										onHasDefaultBranchChange={handleDefaultBranchChange}
										defaultBranchLabel={
											config.default_branch_label || "Default"
										}
										onDefaultBranchLabelChange={handleDefaultBranchLabelChange}
										conditionType={config.condition_type || "simple"}
										onConditionTypeChange={handleConditionTypeChange}
										expression={config.expression || ""}
										onExpressionChange={handleExpressionChange}
										branchMode={config.branch_mode || "binary"}
									/>
								)}
							</div>
						</div>
					</div>

					<div className="border-t border-gray-200 bg-white px-6 py-3">
						<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
							<button
								type="button"
								onClick={handleDelete}
								className="flex items-center gap-1.5 rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-xs text-red-700 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-800"
							>
								<Trash2 className="w-3.5 h-3.5" />
								Delete Node
							</button>

							<div className="flex items-center gap-3 sm:ml-auto">
								{hasUnsavedChanges && (
									<span className="flex items-center gap-1.5 text-[11px] text-gray-600">
										<span className="h-1.5 w-1.5 animate-smoothPulse rounded-[4px] bg-orange-500" />
										Unsaved
									</span>
								)}
								<span className="hidden text-[11px] text-gray-400 sm:inline">
									Ctrl/⌘ + S to save
								</span>
								<button
									type="button"
									onClick={onClose}
									className="rounded-[4px] border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								>
									Cancel
								</button>
								<button
									type="button"
									onClick={handleSave}
									disabled={saving}
									className="rounded-[4px] bg-orange-600 px-5 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								>
									{saving ? (
										<span className="inline-flex items-center gap-1.5">
											<span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
											Saving...
										</span>
									) : (
										<span className="inline-flex items-center gap-1.5">
											<Save className="w-3.5 h-3.5" />
											Save Changes
										</span>
									)}
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
			<ConfirmDialog
				isOpen={showDeleteConfirm}
				onClose={() => setShowDeleteConfirm(false)}
				onConfirm={handleConfirmDelete}
				title="Delete Node"
				message="Are you sure you want to delete this node? This action cannot be undone."
				confirmText="Delete"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>
		</div>
	);
}
