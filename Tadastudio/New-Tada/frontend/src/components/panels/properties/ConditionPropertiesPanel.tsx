"use client";

import { GitBranch, Save, Zap } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useGraph } from "@/contexts/GraphContext";
import IconButton from "../../ui/IconButton";
import InfoTooltip from "../../ui/InfoTooltipPortal";
import TabBar from "../../ui/TabBar";
import ConditionBranchSection from "./sections/ConditionBranchSection";
import ConditionLogicSection from "./sections/ConditionLogicSection";

interface SimpleCondition {
	input_source?: string;
	source_node_id?: string;
	field_path?: string;
	operator?: string;
	value?: any;
	value_type?: string;
	dynamic_source?: any;
}

interface BranchConfig {
	label: string;
	color: string;
	handle_id: string;
	condition: SimpleCondition;
}

interface ConditionConfig {
	branch_mode?: string; // 'binary' | 'multi' | 'switch'
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
	// Passthrough mode fields (for binary mode direct boolean evaluation)
	input_source?: string;
	source_node_id?: string;
	field_path?: string;
}

interface ConditionPropertiesPanelProps {
	nodeId: string;
	onClose: () => void;
}

export default function ConditionPropertiesPanel({
	nodeId,
	onClose,
}: ConditionPropertiesPanelProps) {
	const { nodes, updateNode } = useGraph();
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
		// Passthrough mode defaults
		input_source: "previous",
		source_node_id: undefined,
		field_path: "",
	});

	const [saving, setSaving] = useState(false);

	// Tab navigation
	type ConditionTabId = "branch" | "logic";
	const [activeTab, setActiveTab] = useState<ConditionTabId>("branch");

	// Callbacks for handling config changes
	const handleBranchModeChange = useCallback(
		(mode: "binary" | "multi") => {
			if (mode === "binary") {
				setConfig({
					...config,
					branch_mode: "binary",
					branches: [],
					branch_labels: config.branch_labels || ["True", "False"],
				});
			} else {
				const defaultBranches = [
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
				setConfig({
					...config,
					branch_mode: "multi",
					branches:
						config.branches && config.branches.length > 0
							? config.branches
							: defaultBranches,
				});
			}
		},
		[config],
	);

	const handleBranchLabelsChange = useCallback(
		(labels: string[]) => {
			setConfig({ ...config, branch_labels: labels });
		},
		[config],
	);

	const handleBranchesChange = useCallback(
		(branches: BranchConfig[]) => {
			setConfig({ ...config, branches });
		},
		[config],
	);

	const handleConditionTypeChange = useCallback(
		(type: "simple" | "expression") => {
			setConfig({ ...config, condition_type: type });
		},
		[config],
	);

	const handleSimpleConditionsChange = useCallback(
		(conditions: SimpleCondition[]) => {
			setConfig({ ...config, simple_conditions: conditions });
		},
		[config],
	);

	const handleExpressionChange = useCallback(
		(expression: string) => {
			setConfig({ ...config, expression });
		},
		[config],
	);

	const handleLogicOperatorChange = useCallback(
		(operator: "AND" | "OR") => {
			setConfig({ ...config, logic_operator: operator });
		},
		[config],
	);

	// Passthrough mode handlers
	const handleInputSourceChange = useCallback(
		(source: string) => {
			setConfig({
				...config,
				input_source: source,
				source_node_id: undefined, // Clear when source changes
				field_path: "",
			});
		},
		[config],
	);

	const handleSourceNodeChange = useCallback(
		(nodeId?: string) => {
			setConfig({
				...config,
				source_node_id: nodeId,
				field_path: "", // Clear field path when node changes
			});
		},
		[config],
	);

	const handleFieldPathChange = useCallback(
		(path: string) => {
			setConfig({ ...config, field_path: path });
		},
		[config],
	);

	// Get all available nodes for input selection (excluding current node)
	const upstreamNodes = useMemo(() => {
		if (!node) return [];
		// Show all nodes except the current condition node itself
		return nodes.filter((n) => n.id !== nodeId && n.data?.type !== "END");
	}, [nodes, node, nodeId]);

	// Define tabs - hide Conditions tab for binary mode (uses passthrough evaluation)
	const conditionTabs = useMemo(() => {
		type TabAccent =
			| "core"
			| "input"
			| "memory"
			| "output"
			| "orchestration"
			| "advanced";
		const tabs: Array<{
			id: ConditionTabId;
			label: string;
			description: string;
			icon: React.ReactNode;
			accent: TabAccent;
		}> = [
			{
				id: "branch",
				label: "Branch Configuration",
				description: "Branching mode & paths",
				icon: <GitBranch className="h-4 w-4" />,
				accent: "core",
			},
		];

		// Only show Conditions tab for multi-branch mode
		if (config.branch_mode === "multi") {
			tabs.push({
				id: "logic",
				label: "Conditions",
				description: "Logic & rules",
				icon: <Zap className="h-4 w-4" />,
				accent: "input",
			});
		}

		return tabs;
	}, [config.branch_mode]);

	// Initialize with existing config
	useEffect(() => {
		if (node?.data) {
			setNodeName(node.data.name || "Condition");
			if (node.data.condition_config) {
				const existingConfig = node.data.condition_config;
				setConfig({
					...existingConfig,
					// Ensure branch_mode is set
					branch_mode: existingConfig.branch_mode || "binary",
					// Ensure branches array exists for multi-branch mode
					branches: existingConfig.branches || [],
					// Ensure branch_labels exist for binary mode
					branch_labels: existingConfig.branch_labels || ["True", "False"],
					// Passthrough mode fields
					input_source: existingConfig.input_source || "previous",
					source_node_id: existingConfig.source_node_id,
					field_path: existingConfig.field_path || "",
				});
			}
		}
	}, [node]);

	const handleSave = async () => {
		setSaving(true);
		try {
			// Ensure proper structure based on branch mode
			const saveConfig = {
				...config,
				branch_mode: config.branch_mode || "binary",
				// Ensure branches array is properly structured
				branches:
					config.branch_mode === "multi"
						? (config.branches || []).map((branch, index) => ({
								...branch,
								handle_id: branch.handle_id || `branch-${index}`,
								color: branch.color || "#8b5cf6",
								label: branch.label || `Branch ${index + 1}`,
								condition: branch.condition || {},
							}))
						: [],
				// Clear old branch_labels for multi-branch mode to avoid confusion
				branch_labels:
					config.branch_mode === "binary" ? config.branch_labels : undefined,
				// Include passthrough fields for binary mode, clear for multi-branch
				input_source:
					config.branch_mode === "binary" ? config.input_source : undefined,
				source_node_id:
					config.branch_mode === "binary" ? config.source_node_id : undefined,
				field_path:
					config.branch_mode === "binary" ? config.field_path : undefined,
				// Clear simple_conditions for binary mode (uses passthrough)
				simple_conditions:
					config.branch_mode === "multi" ? config.simple_conditions : [],
			};

			console.log("=== SAVING CONDITION CONFIG ===");
			console.log("Node ID:", nodeId);
			console.log("Node Name:", nodeName);
			console.log("Branch Mode:", saveConfig.branch_mode);
			console.log("Branches:", saveConfig.branches);
			console.log("Full Config:", saveConfig);

			const result = await updateNode(nodeId, {
				name: nodeName,
				condition_config: saveConfig,
			});

			console.log("Update result:", result);

			// Force a refresh of the graph to ensure the node updates
			setTimeout(() => {
				console.log("Config saved, closing panel");
				onClose();
			}, 100);
		} catch (error) {
			console.error("Failed to save condition config:", error);
		} finally {
			setSaving(false);
		}
	};

	return (
		<div
			className="fixed inset-0 bg-black/75 backdrop-blur-md flex items-center justify-center z-[100] animate-fadeIn"
			onClick={onClose}
		>
			<div
				className="bg-[color:var(--color-bg-secondary)] rounded-xl shadow-2xl max-w-5xl w-full mx-4 max-h-[90vh] overflow-hidden animate-scaleIn"
				onClick={(e) => e.stopPropagation()}
			>
				{/* Header */}
				<div className="flex items-center justify-between p-6 border-b border-[color:var(--color-surface)] bg-[color:var(--color-surface)]/50 rounded-t-xl">
					<div className="flex items-center gap-3">
						<div className="p-2 rounded-lg bg-[color:var(--color-surface)]">
							<GitBranch className="w-6 h-6 text-[color:var(--color-text-muted)]" />
						</div>
						<div>
							<h2 className="text-xl font-semibold text-slate-900">
								Condition Configuration
							</h2>
							<p className="text-sm text-[color:var(--color-text-muted)]">
								Configure branching logic and decision paths
							</p>
						</div>
					</div>
					<IconButton
						ariaLabel="Close"
						onClick={onClose}
						className="text-[color:var(--color-text-secondary)] hover:text-slate-900"
					/>
				</div>

				{/* Body */}
				<div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)] space-y-6">
					{/* Node Name Input */}
					<div className="rounded-xl border border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/30 p-4">
						<label
							htmlFor="node-name"
							className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-3 flex items-center gap-2"
						>
							Node Name
							<InfoTooltip text="A descriptive name for this condition node" />
						</label>
						<input
							id="node-name"
							type="text"
							value={nodeName}
							onChange={(e) => setNodeName(e.target.value)}
							placeholder="Enter node name..."
							className="w-full px-4 py-2.5 bg-[color:var(--color-surface)] border border-[color:var(--color-border)]/50 rounded-lg text-slate-900 placeholder-[color:var(--color-text-muted)] focus:border-[color:var(--color-primary)]/50 focus:ring-2 focus:ring-[color:var(--color-primary)]/20 focus:outline-none transition-all duration-200"
						/>
					</div>

					{/* Tab Navigation */}
					<TabBar
						tabs={conditionTabs}
						activeTab={activeTab}
						onChange={(tabId) => setActiveTab(tabId as ConditionTabId)}
						variant="subtle"
						size="md"
					/>

					{/* Tab Content */}
					{activeTab === "branch" && (
						<ConditionBranchSection
							branchMode={config.branch_mode || "binary"}
							onBranchModeChange={handleBranchModeChange}
							branchLabels={config.branch_labels || ["True", "False"]}
							onBranchLabelsChange={handleBranchLabelsChange}
							branches={config.branches || []}
							onBranchesChange={handleBranchesChange}
							// Passthrough mode props for binary
							inputSource={config.input_source || "previous"}
							sourceNodeId={config.source_node_id}
							fieldPath={config.field_path || ""}
							onInputSourceChange={handleInputSourceChange}
							onSourceNodeChange={handleSourceNodeChange}
							onFieldPathChange={handleFieldPathChange}
							availableNodes={upstreamNodes}
						/>
					)}

					{activeTab === "logic" && (
						<ConditionLogicSection
							branchMode={config.branch_mode || "binary"}
							conditionType={config.condition_type || "simple"}
							onConditionTypeChange={handleConditionTypeChange}
							simpleConditions={config.simple_conditions || []}
							onSimpleConditionsChange={handleSimpleConditionsChange}
							expression={config.expression || ""}
							onExpressionChange={handleExpressionChange}
							logicOperator={config.logic_operator || "AND"}
							onLogicOperatorChange={handleLogicOperatorChange}
							branches={config.branches || []}
							onBranchesChange={handleBranchesChange}
							availableNodes={upstreamNodes}
						/>
					)}
				</div>

				{/* Footer */}
				<div className="flex justify-end gap-3 px-6 py-4 bg-[color:var(--color-surface)]/30 border-t border-[color:var(--color-border)]/50 rounded-b-xl">
					<button
						onClick={onClose}
						className="px-5 py-2.5 border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/40 text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface)]/60 hover:text-slate-900 hover:border-[color:var(--color-border-hover)] rounded-lg transition-all duration-200 font-semibold"
					>
						Cancel
					</button>
					<button
						onClick={handleSave}
						disabled={saving}
						className="px-5 py-2.5 text-[color:var(--button-primary-text)] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] border border-[rgba(var(--color-primary-rgb),0.5)] rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-semibold shadow-[0_4px_12px_rgba(var(--color-primary-rgb),0.25)] hover:shadow-[0_8px_20px_rgba(var(--color-primary-rgb),0.35)] hover:scale-105 disabled:hover:scale-100"
					>
						<Save className="w-4 h-4" />
						{saving ? "Saving..." : "Save Configuration"}
					</button>
				</div>
			</div>
		</div>
	);
}
