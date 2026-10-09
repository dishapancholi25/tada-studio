"use client";

import {
	CheckCircle,
	Clock,
	Code,
	GitBranch,
	Layers,
	Loader2,
	MessageSquare,
	Plus,
	Trash2,
	XCircle,
} from "lucide-react";
import type React from "react";
import { memo, useCallback, useMemo } from "react";
import { Handle, type NodeProps, Position } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
import { useNodeOutgoingEdges } from "@/hooks/useNodeOutgoingEdges";
import { formatExecutionDuration } from "@/lib/executionGraphUtils";
import EvalScoreBadge from "./shared/EvalScoreBadge";
import GuardrailIndicator from "./shared/GuardrailIndicator";
import { getExecutionGradient } from "./shared/getExecutionGradient";
import InlineNameEditor from "./shared/InlineNameEditor";
import {
	createGradientFrame,
	createSelectionGlow,
	handleStyles,
	nodeBodyGradient,
	nodeColors,
	nodeFrameRadius,
	nodeHeaderRadius,
	nodeRadius,
	nodeShadows,
	plusButtonBase,
	plusButtonShadow,
} from "./shared/nodeStyles";

interface ConditionConfig {
	condition_type?: string;
	simple_conditions?: Array<{
		input_source?: string;
		source_node_id?: string;
		field_path?: string;
		operator?: string;
		value?: any;
		value_type?: string;
	}>;
	expression?: string;
	llm_prompt?: string;
	logic_operator?: string;
	branch_count?: number;
	branch_labels?: string[];
	has_default_branch?: boolean;
	default_branch_label?: string;
	branches?: Array<{
		label: string;
		color?: string;
		handle_id?: string;
		condition?: any;
	}>;
	branch_mode?: string;
	// Passthrough mode fields (for binary mode without comparison operators)
	input_source?: string;
	source_node_id?: string;
	field_path?: string;
}

interface ConditionNodeData {
	name: string;
	condition_config?: ConditionConfig;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	executionDuration?: number;
	branchTaken?: number;
	nexts?: string[];
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
}

const ConditionNode = memo(
	({ data, selected, id }: NodeProps<ConditionNodeData>) => {
		const { deleteNode } = useGraph();
		const outgoingEdges = useNodeOutgoingEdges(id);
		const config = data.condition_config || {};
		// Check if passthrough mode is configured (binary mode with input_source but no simple_conditions)
		const isPassthroughMode =
			config.branch_mode === "binary" &&
			config.input_source &&
			config.input_source !== "" &&
			(config.simple_conditions?.length ?? 0) === 0;
		const hasConfiguration =
			(config.simple_conditions?.length ?? 0) > 0 ||
			config.expression ||
			config.llm_prompt ||
			(config.branches?.length ?? 0) > 0 ||
			isPassthroughMode;
		const isExecuting = data.isExecuting || false;
		const executionStatus = data.executionStatus;
		const executionDuration = data.executionDuration;
		const branchTaken = data.branchTaken;
		const isReadOnlyPreview = Boolean(data.isReadOnlyPreview);

		const handleDeleteButtonClick = useCallback(
			(e: React.MouseEvent) => {
				e.stopPropagation();
				deleteNode(id).catch((err) => {
					console.error("Failed to delete node:", err);
				});
			},
			[deleteNode, id],
		);

		const conditionType = config.condition_type || "simple";
		// Use branches array if available (for multi-branch), otherwise use branch_count
		const branchCount = config.branches?.length || config.branch_count || 2;
		// Get labels from branches array or use branch_labels
		const branchLabels = config.branches?.map((b: any) => b.label) ||
			config.branch_labels || ["True", "False"];
		const logicOperator = config.logic_operator || "AND";

		// Check which branches have connections
		const branchConnections = useMemo(() => {
			const connections: { [key: number]: boolean } = {};

			// Check each branch for connections
			for (let i = 0; i < branchCount; i++) {
				const branchHandle = `branch-${i}`;
				// Check if there's an edge from this node with this specific branch handle
				connections[i] = outgoingEdges.some(
					(edge) => edge.sourceHandle === branchHandle,
				);
			}

			return connections;
		}, [outgoingEdges, branchCount]);

		// Get condition type icon
		const getTypeIcon = () => {
			switch (conditionType) {
				case "expression":
					return <Code className="w-3 h-3 text-purple-400" />;
				case "llm":
					return (
						<MessageSquare className="w-3 h-3 text-[color:var(--color-text-muted)]" />
					);
				case "multiple":
					return <Layers className="w-3 h-3 text-orange-400" />;
				default:
					return <GitBranch className="w-3 h-3 text-purple-400" />;
			}
		};

		// Get status icon
		const getStatusIcon = () => {
			if (isExecuting || executionStatus === "running") {
				return <Loader2 className="w-4 h-4 text-white animate-spin" />;
			}

			switch (executionStatus) {
				case "completed":
					return <CheckCircle className="w-4 h-4 text-white" />;
				case "failed":
					return <XCircle className="w-4 h-4 text-white" />;
				case "pending":
					return <Clock className="w-4 h-4 text-white" />;
				case "skipped":
					return <Clock className="w-4 h-4 text-slate-700" />;
				default:
					return null; // Don't show branch icon as status
			}
		};

		// Get gradient colors based on execution status (memoized for performance)
		const gradientColors = useMemo(
			() => getExecutionGradient(executionStatus, "amber"),
			[executionStatus],
		);

		// Get condition summary for display
		const getConditionSummary = () => {
			// Check for multi-branch mode first
			if (
				config.branch_mode === "multi" &&
				config.branches &&
				config.branches.length > 0
			) {
				const branchCount = config.branches.length;
				return `Multi-branch (${branchCount})`;
			}

			if (conditionType === "expression" && config.expression) {
				return config.expression.length > 30
					? config.expression.substring(0, 30) + "..."
					: config.expression;
			}

			if (conditionType === "llm" && config.llm_prompt) {
				return config.llm_prompt.length > 30
					? config.llm_prompt.substring(0, 30) + "..."
					: config.llm_prompt;
			}

			if (config.simple_conditions && config.simple_conditions.length > 0) {
				const firstCondition = config.simple_conditions[0];
				const field = firstCondition.field_path || "field";
				const operator = firstCondition.operator || "==";
				const value = firstCondition.value || "value";

				if (config.simple_conditions.length > 1) {
					return `${field} ${operator} ${value} (${logicOperator} +${config.simple_conditions.length - 1})`;
				}
				return `${field} ${operator} ${value}`;
			}

			// Check for passthrough mode (direct boolean evaluation)
			if (isPassthroughMode) {
				const fieldPath = config.field_path;
				if (fieldPath) {
					return `${fieldPath} → boolean`;
				}
				// Show input source type
				const sourceLabel =
					config.input_source === "specific"
						? "Node output"
						: config.input_source === "previous"
							? "Previous output"
							: config.input_source === "start"
								? "Start input"
								: "Field value";
				return `${sourceLabel} → boolean`;
			}

			return "Not configured";
		};

		// Calculate dynamic node height based on branch count
		// Compact sizing for better visual balance
		const nodeHeight = 110 + Math.max(0, branchCount - 2) * 25;
		const headerHeight = 45; // Actual header height
		const topPadding = 15;
		const bottomPadding = 15;
		const availableHeight =
			nodeHeight - headerHeight - topPadding - bottomPadding;

		// Click handler for branch palette
		const createBranchPaletteClickHandler = useCallback(
			(branchIndex: number, branchLabel: string) => (e: React.MouseEvent) => {
				e.stopPropagation();
				const event = new CustomEvent("openNodePalette", {
					detail: {
						sourceNodeId: id,
						sourceBranchIndex: branchIndex,
						sourceBranchLabel: branchLabel,
					},
				});
				window.dispatchEvent(event);
			},
			[id],
		);

		return (
			<div className="relative group" style={{ minHeight: `${nodeHeight}px` }}>
				<EvalScoreBadge score={data.evalScore} />
				{/* Selection glow veneer */}
				{selected && (
					<div
						className={`pointer-events-none absolute -inset-[3px] ${nodeFrameRadius.standard} blur-xl opacity-60 transition-opacity`}
						style={createSelectionGlow(nodeColors.orange)}
					/>
				)}

				{/* Outer gradient frame (glass halo) */}
				<div
					className={`p-[1px] ${nodeFrameRadius.standard} transition-all duration-200 ${
						selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
					}`}
					style={createGradientFrame(nodeColors.orange)}
				>
					<div
						className={`
            relative min-w-[200px] max-w-[280px] ${nodeRadius.standard}
            ${nodeShadows.default}
            ${selected ? nodeShadows.selected : ""}
            transition-all duration-200
          `}
						style={{ minHeight: `${nodeHeight}px` }}
					>
						{/* Background gradient effect */}
						<div
							className={`hidden absolute inset-0 bg-gradient-to-br ${gradientColors.from} ${gradientColors.to} ${nodeRadius.standard} blur-xl ${
								isExecuting || executionStatus === "running"
									? "opacity-70 animate-pulse"
									: "opacity-40"
							}`}
						/>

						{/* Main node container */}
						<div
							className={`relative ${nodeBodyGradient} border border-slate-200 ${nodeRadius.standard} ${
								isExecuting || executionStatus === "running"
									? "animate-pulse"
									: ""
							}`}
							style={{ minHeight: `${nodeHeight}px` }}
						>
							{/* Header */}
							<div
								className={`flex items-center justify-between px-4 py-3 ${nodeHeaderRadius.standard} border-b`}
								style={{
									backgroundColor: `rgb(${nodeColors.orange})`,
									borderColor: `rgba(${nodeColors.orange}, 0.35)`,
								}}
							>
								<div className="flex items-center gap-2.5">
									{/* Icon capsule */}
									<div
										className="h-8 w-8 rounded-xl border flex items-center justify-center"
										style={{
											backgroundColor: "rgba(255, 255, 255, 0.2)",
											borderColor: "rgba(255, 255, 255, 0.28)",
										}}
									>
										<GitBranch className="w-4 h-4 text-white" />
									</div>
									<span className="text-xs font-semibold text-white capitalize">
										Condition
									</span>
								</div>
								<GuardrailIndicator nodeId={id} />
								<div className="flex items-center gap-2">
									{getStatusIcon()}
									{!isReadOnlyPreview && (
										<button
											onClick={handleDeleteButtonClick}
											className="p-1 rounded hover:bg-red-500/20 transition-colors"
											title="Delete"
										>
											<Trash2 className="w-3.5 h-3.5 text-white hover:text-slate-900" />
										</button>
									)}
								</div>
							</div>

							{/* Body */}
							<div className="px-4 py-3">
								<InlineNameEditor
									nodeId={id}
									initialName={data.name || "Condition"}
									placeholder="Condition"
									className="text-sm font-semibold text-slate-900 mb-2 truncate"
									readOnly={isReadOnlyPreview}
								/>

								{hasConfiguration ? (
									<div className="space-y-1.5">
										{/* Condition summary */}
										{config.branch_mode === "multi" ? (
											<div className="flex items-center gap-1 px-2 py-0.5 bg-orange-500/20 rounded text-xs inline-flex">
												<Layers className="w-3 h-3 text-orange-400" />
												<span className="text-white">
													{getConditionSummary()}
												</span>
											</div>
										) : (
											<div className="text-xs font-mono px-2 py-1 rounded bg-[color:var(--color-surface)]/50 text-[color:var(--color-text-secondary)]">
												{getConditionSummary()}
											</div>
										)}

										{/* Logic operator badge for multiple conditions */}
										{config.simple_conditions &&
											config.simple_conditions.length > 1 && (
												<div className="flex items-center gap-2">
													<span className="px-2 py-0.5 bg-orange-500/20 text-orange-400 text-xs rounded">
														{logicOperator}
													</span>
												</div>
											)}
									</div>
								) : (
									<p className="text-xs text-[color:var(--color-text-muted)] italic">
										Not configured
									</p>
								)}

								{/* Execution info */}
								{executionStatus === "completed" &&
									branchTaken !== undefined && (
										<div className="mt-2 pt-2 border-t border-orange-500/20">
											<div className="flex items-center gap-2 text-xs">
												<span className="text-[color:var(--color-text-muted)]">
													Branch taken:
												</span>
												<span className="text-white font-medium">
													{branchLabels[branchTaken] || `Branch ${branchTaken}`}
												</span>
											</div>
										</div>
									)}

								{/* Execution duration */}
								{executionStatus === "completed" && executionDuration && (
									<div className="flex items-center gap-1 text-xs text-white mt-2">
										<Clock className="w-3 h-3" />
										<span>{formatExecutionDuration(executionDuration)}</span>
									</div>
								)}
							</div>
						</div>

						{/* Input Handle */}
						<Handle
							type="target"
							position={Position.Left}
							className="!w-3 !h-3 !bg-orange-500 !border-2 !border-[color:var(--color-bg-secondary)] hover:!bg-orange-400 transition-colors"
						/>

						{/* Output Handles - Dynamic based on branch count */}
						{Array.from({ length: branchCount }, (_, index) => {
							// Calculate pixel-based vertical position for each handle
							// Distribute evenly across available height
							let pixelPosition;
							if (branchCount === 1) {
								// Single branch: center it
								pixelPosition = headerHeight + topPadding + availableHeight / 2;
							} else {
								// Multiple branches: distribute evenly from top to bottom
								const spacing = availableHeight / (branchCount - 1);
								pixelPosition = headerHeight + topPadding + spacing * index;
							}

							// Get the proper color for each branch
							// First check if branch has a defined color, otherwise use defaults
							const getBranchColor = () => {
								// Check if branches array exists and has color defined
								if (config.branches && config.branches[index]?.color) {
									return config.branches[index].color;
								}

								// Fallback to label-based colors for common patterns
								const label = branchLabels[index]?.toLowerCase() || "";
								if (
									label.includes("full") ||
									(label.includes("match") && label.includes("full"))
								) {
									return "#0DA931"; // Green for FULL_MATCH
								}
								if (label.includes("partial")) {
									return "#F68A40"; // Warm accent for PARTIAL_MATCH
								}
								if (label.includes("no") && label.includes("match")) {
									return "#ef4444"; // Red for NO_MATCH
								}
								if (label.includes("over") || label.includes("payment")) {
									return "#8b5cf6"; // Purple for OVERPAYMENT
								}

								// Default index-based colors as final fallback
								switch (index) {
									case 0:
										return "#0DA931"; // Green
									case 1:
										return "#ef4444"; // Red
									case 2:
										return "#f97316"; // Orange
									case 3:
										return "#a855f7"; // Purple
									default:
										return "#808080"; // Gray
								}
							};

							const branchColor = getBranchColor();

							return (
								<div key={`branch-${index}`}>
									{/* Branch Handle */}
									<Handle
										id={`branch-${index}`}
										type="source"
										position={Position.Right}
										style={{
											top: `${pixelPosition}px`,
											backgroundColor: branchColor,
											border: "2px solid #171717",
										}}
										className="!w-3 !h-3 hover:!opacity-80 transition-all"
									/>

									{/* Enhanced Branch Label Pill - Only show when no connection */}
									{!isReadOnlyPreview && !branchConnections[index] && (
										<div
											className="absolute pointer-events-none"
											style={{
												left: "calc(100% + 15px)",
												top: `${pixelPosition}px`,
												transform: "translateY(-50%)",
											}}
										>
											<div
												className="px-3 py-1.5 rounded-lg text-xs font-medium backdrop-blur-sm shadow-lg transition-all duration-200 whitespace-nowrap"
												style={{
													backgroundColor: `${branchColor}20`,
													color: branchColor,
													border: `1px solid ${branchColor}40`,
												}}
											>
												{branchLabels[index] || `Branch ${index + 1}`}
											</div>
										</div>
									)}

									{/* Add Connection Plus Icon - only show if this branch has no connection */}
									{!isReadOnlyPreview && !branchConnections[index] && (
										<>
											{/* Measure label width and position plus icon accordingly */}
											<div
												className="absolute"
												style={{
													left: "calc(100% + 15px)",
													top: `${pixelPosition}px`,
													transform: "translateY(-50%)",
													display: "flex",
													alignItems: "center",
													gap: "8px",
												}}
											>
												{/* Label (invisible duplicate for width measurement) */}
												<div className="invisible px-3 py-1.5 text-xs font-medium whitespace-nowrap">
													{branchLabels[index] || `Branch ${index + 1}`}
												</div>

												{/* Connecting line */}
												<svg
													className="pointer-events-none"
													style={{
														width: "20px",
														height: "2px",
													}}
												>
													<path
														d={`M 0 1 L 20 1`}
														stroke={branchColor}
														strokeWidth="1"
														fill="none"
														opacity="0.4"
														strokeDasharray="2,2"
													/>
												</svg>

												{/* Plus icon button */}
												<button
													onClick={createBranchPaletteClickHandler(
														index,
														branchLabels[index],
													)}
													className="p-1.5 rounded-full shadow-lg transition-all duration-200 hover:scale-110 group"
													style={{
														backgroundColor: `${branchColor}20`,
														border: `1px solid ${branchColor}40`,
													}}
													title={`Add node for ${branchLabels[index]} branch`}
												>
													<Plus
														className="w-3.5 h-3.5 transition-all duration-200 group-hover:rotate-90"
														style={{ color: branchColor }}
													/>
												</button>
											</div>
										</>
									)}
								</div>
							);
						})}
					</div>
				</div>
			</div>
		);
	},
);

ConditionNode.displayName = "ConditionNode";

export default ConditionNode;
