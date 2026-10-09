"use client";

import {
	AlertCircle,
	CheckCircle,
	Clock,
	GitBranch,
	Loader2,
	Mail,
	PauseCircle,
	Play,
	Plus,
	Square,
	Trash2,
	XCircle,
} from "lucide-react";
import { memo, useCallback } from "react";
import { Handle, type NodeProps, Position } from "reactflow";
import { useNodeOutgoingEdges } from "@/hooks/useNodeOutgoingEdges";
import { useGraph } from "@/contexts/GraphContext";
import type { AgentNodeData } from "@/types/agent";
import EvalScoreBadge from "./shared/EvalScoreBadge";
import GuardrailIndicator from "./shared/GuardrailIndicator";
import InlineNameEditor from "./shared/InlineNameEditor";
import {
	createGradientFrame,
	handleStyles,
	nodeBodyGradient,
	nodeColors,
	nodeFrameRadius,
	nodeHeaderRadius,
	nodeRadius,
	nodeShadows,
	plusButtonBase,
	plusButtonPulse,
	plusButtonShadow,
} from "./shared/nodeStyles";

interface ExtendedFlowNodeData extends AgentNodeData {
	hasOutgoingConnections?: boolean;
	nexts?: string[];
	isReadOnly?: boolean;
	condition_config?: unknown;
	checkpoint_config?: unknown;
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
}

interface FlowNodeProps extends NodeProps {
	data: ExtendedFlowNodeData;
}

type ConditionBranch = { label?: string };
type ConditionConfig = {
	branch_mode?: "binary" | "multi";
	branches?: ConditionBranch[];
};

type CheckpointConfig = {
	await_mode?: string;
	email_config?: {
		enabled?: boolean;
		recipient_email?: string;
	};
};

function FlowNode({ data, selected, id }: FlowNodeProps) {
	const { deleteNode } = useGraph();
	const outgoingEdges = useNodeOutgoingEdges(id);
	const nodeType = data.type?.toUpperCase() || "AGENT";
	const isExecuting = data.isExecuting || false;
	const executionStatus = data.executionStatus;
	const executionDuration = data.executionDuration;
	const isReadOnlyPreview = Boolean(data.isReadOnlyPreview);
	const isDeletable = nodeType !== "START";

	const checkpointConfig = data.checkpoint_config as CheckpointConfig | undefined;
	const conditionConfig = data.condition_config as ConditionConfig | undefined;

	const handleDeleteButtonClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			deleteNode(id).catch((err) => {
				console.error("Failed to delete node:", err);
			});
		},
		[deleteNode, id],
	);

	// Check if checkpoint is in email mode
	const isEmailCheckpoint =
		nodeType === "CHECKPOINT" &&
		checkpointConfig?.await_mode === "email" &&
		checkpointConfig?.email_config?.enabled;

	// Define node configurations based on type
	const nodeConfigs = {
		START: {
			icon: Play,
			title: "START",
			subtitle: "",
			themeColor: "green",
			colorRgb: nodeColors.green,
			gradientFrom: "from-[#0DA931]/20",
			gradientTo: "to-[#0DA931]/20",
			borderColor: "border-[#0DA931]/40",
			iconBgColor: "bg-[#0DA931]/20",
			iconColor: "text-[#0DA931]",
			textColor: "text-[#0DA931]",
		},
		END: {
			icon: CheckCircle,
			title: "END",
			subtitle: "Workflow End",
			themeColor: "red",
			colorRgb: nodeColors.red,
			gradientFrom: "from-red-600/20",
			gradientTo: "to-rose-600/20",
			borderColor: "border-red-500/40",
			iconBgColor: "bg-red-500/20",
			iconColor: "text-white",
			textColor: "text-red-300",
		},
		CONDITION: {
			icon: GitBranch,
			title: "CONDITION",
			subtitle: "Branching Logic",
			themeColor: "orange",
			colorRgb: nodeColors.orange,
			gradientFrom: "from-orange-600/20",
			gradientTo: "to-amber-600/20",
			borderColor: "border-orange-500/40",
			iconBgColor: "bg-orange-500/20",
			iconColor: "text-orange-400",
			textColor: "text-orange-300",
		},
		CHECKPOINT: {
			icon: isEmailCheckpoint ? Mail : AlertCircle,
			title: "CHECKPOINT",
			subtitle: isEmailCheckpoint ? "Email Response" : "Human Review",
			themeColor: "purple",
			colorRgb: isEmailCheckpoint ? nodeColors.blue : nodeColors.purple,
			gradientFrom: isEmailCheckpoint
				? "from-blue-600/20"
				: "from-purple-600/20",
			gradientTo: isEmailCheckpoint ? "to-indigo-600/20" : "to-violet-600/20",
			borderColor: isEmailCheckpoint
				? "border-blue-500/40"
				: "border-purple-500/40",
			iconBgColor: isEmailCheckpoint ? "bg-blue-500/20" : "bg-purple-500/20",
			iconColor: isEmailCheckpoint ? "text-blue-400" : "text-purple-400",
			textColor: isEmailCheckpoint ? "text-blue-600" : "text-purple-600",
		},
	};

	const config =
		nodeConfigs[nodeType as keyof typeof nodeConfigs] || nodeConfigs.START;
	const Icon = config.icon;

	const getStatusIcon = () => {
		if (isExecuting || executionStatus === "running") {
			return <Loader2 className="w-4 h-4 text-white animate-spin" />;
		}

		switch (executionStatus) {
			case "completed":
				return <CheckCircle className="w-4 h-4 text-white" />;
			case "failed":
				return <XCircle className="w-4 h-4 text-white" />;
			case "paused":
				return (
					<PauseCircle className="w-4 h-4 text-white" />
				);
			case "pause_pending":
				return (
					<Loader2 className="w-4 h-4 text-white animate-spin" />
				);
			case "stop_requested":
			case "stopping":
				return <Loader2 className="w-4 h-4 text-white animate-spin" />;
			case "stopped":
				return <Square className="w-4 h-4 text-white" />;
			case "pending":
				return <Clock className="w-4 h-4 text-white" />;
			case "skipped":
				return <Clock className="w-4 h-4 text-slate-700" />;
			default:
				return null;
		}
	};

	// Note: Double-click is handled by ReactFlow's onNodeDoubleClick in ExecutionGraphViewer

	// Click handlers for node palette
	const handleOpenNodePaletteClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			const event = new CustomEvent("openNodePalette", {
				detail: { sourceNodeId: id },
			});
			window.dispatchEvent(event);
		},
		[id],
	);

	const createBranchPaletteClickHandler = useCallback(
		(branchIndex: number) => (e: React.MouseEvent) => {
			e.stopPropagation();
			const event = new CustomEvent("openNodePalette", {
				detail: {
					sourceNodeId: id,
					sourceBranchIndex: branchIndex,
				},
			});
			window.dispatchEvent(event);
		},
		[id],
	);

	return (
		<div className="relative group" data-tutorial={nodeType === "START" ? "start-node" : nodeType === "END" ? "end-node" : undefined}>
			<EvalScoreBadge score={data.evalScore} />

			{/* Outer frame (subtle) */}
			<div
				className={`p-[1px] ${nodeFrameRadius.standard} transition-all duration-200 ${
					selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
				}`}
				style={selected ? createGradientFrame(config.colorRgb) : undefined}
			>
				<div
					className={`
            relative min-w-[200px] max-w-[250px] ${nodeRadius.standard}
            ${nodeShadows.default}
            ${selected ? nodeShadows.selected : ""}
            transition-all duration-200
          `}
				>
					{/* Main node container */}
					<div
						className={`relative ${nodeBodyGradient} border border-slate-200 ${nodeRadius.standard} ${
							isExecuting || executionStatus === "running"
								? "opacity-90"
								: ""
						} ${executionStatus ? "cursor-pointer" : ""}`}
					>
						{/* Header (solid) */}
						<div
							className={`flex items-center justify-between px-4 py-2.5 ${nodeHeaderRadius.standard} border-b border-black/10`}
							style={{
								backgroundColor: `rgb(${config.colorRgb})`,
							}}
						>
							<div className="flex items-center gap-2.5">
								<div
									className="h-7 w-7 rounded-lg flex items-center justify-center bg-white/20"
								>
									<Icon className="w-4 h-4 text-white" />
								</div>
								<span className="text-xs font-semibold capitalize text-white">
									{config.title}
								</span>
							</div>
							<GuardrailIndicator nodeId={id} />
							<div className="flex items-center gap-2">
								{getStatusIcon()}
								{!isReadOnlyPreview && isDeletable && (
									<button
										onClick={handleDeleteButtonClick}
											className="p-1 rounded hover:bg-white/20 transition-colors"
										title="Delete"
									>
											<Trash2 className="w-3.5 h-3.5 text-white hover:text-slate-900" />
									</button>
								)}
							</div>
						</div>

						{/* Body (white) */}
						<div className="px-4 py-3">
							<InlineNameEditor
								nodeId={id}
								initialName={data.name || (nodeType === "START" ? "Start" : config.subtitle)}
								placeholder={nodeType === "START" ? "Start" : config.subtitle}
								className="text-sm font-semibold text-slate-900 mb-1 truncate"
								readOnly={isReadOnlyPreview}
							/>
							{nodeType === "START" ? (
								<p className="text-xs text-slate-500">Manual trigger</p>
							) : config.subtitle ? (
								<p className="text-xs text-slate-500">{config.subtitle}</p>
							) : null}
							{isEmailCheckpoint &&
								checkpointConfig?.email_config?.recipient_email && (
									<div className="mt-2 flex items-center gap-1">
										<Mail className="w-3 h-3 text-slate-700" />
										<span className="text-[11px] text-slate-700 truncate">
											{checkpointConfig.email_config?.recipient_email}
										</span>
									</div>
								)}

							{executionStatus === "completed" && executionDuration && (
								<div className="mt-2 pt-2 border-t border-slate-200">
									<div className="flex items-center gap-1 text-xs text-slate-700">
										<Clock className="w-3 h-3" />
										<span>{executionDuration.toFixed(2)}s</span>
									</div>
								</div>
							)}
						</div>
					</div>

					{/* Handles based on node type */}
					{nodeType === "START" && (
						<Handle
							type="source"
							position={Position.Right}
							className={handleStyles}
							data-tutorial="connection-handle"
						/>
					)}

					{nodeType === "END" && (
						<Handle
							type="target"
							position={Position.Left}
							className={handleStyles}
						/>
					)}

					{/* Checkpoint node handles */}
					{nodeType === "CHECKPOINT" && (
						<>
							<Handle
								type="target"
								position={Position.Left}
								className={handleStyles}
							/>
							<Handle
								type="source"
								position={Position.Right}
								className={handleStyles}
							/>
						</>
					)}

					{nodeType === "CONDITION" && (
						<>
							<Handle
								type="target"
								position={Position.Left}
								className={handleStyles}
							/>
							{/* Dynamic branch handles based on condition configuration */}
							{(() => {
								const branchMode = conditionConfig?.branch_mode || "binary";
								const branches = conditionConfig?.branches || [];

								if (branchMode === "multi" && branches.length > 0) {
									// Multi-branch mode with custom branches
									const branchCount = Math.min(branches.length, 4); // Limit to 4 branches
									return branches
										.slice(0, branchCount)
										.map((branch: ConditionBranch, index: number) => {
											const topPosition =
												25 + index * (50 / (branchCount - 1 || 1));

											return (
												<div key={`branch-${index}`}>
													<Handle
														type="source"
														position={Position.Right}
														id={`branch-${index}`}
														className={handleStyles}
														style={{
															top: `${topPosition}%`,
														}}
													/>
													{/* Branch label */}
													<div
														className="absolute text-[10px] font-medium text-[color:var(--color-text-muted)] pointer-events-none"
														style={{
															right: "20px",
															top: `${topPosition}%`,
															transform: "translateY(-50%)",
														}}
													>
														{branch.label || `Branch ${index + 1}`}
													</div>
												</div>
											);
										});
								} else {
									// Default binary mode (backward compatibility)
									return (
										<>
											<Handle
												type="source"
												position={Position.Right}
												id="true"
												style={{ top: "30%" }}
												className={handleStyles}
											/>
											<Handle
												type="source"
												position={Position.Right}
												id="false"
												style={{ top: "70%" }}
												className={handleStyles}
											/>
										</>
									);
								}
							})()}
						</>
					)}

					{/* Add Connection Plus Icons for multi-branch conditions */}
					{!isReadOnlyPreview &&
						nodeType === "CONDITION" &&
						conditionConfig?.branch_mode === "multi" &&
						(conditionConfig?.branches?.length || 0) > 0 && (
							<>
								{(conditionConfig?.branches || []).map(
									(branch: ConditionBranch, index: number) => {
										const branchCount = (conditionConfig?.branches || []).length;
										const topPosition =
											25 + index * (50 / (branchCount - 1 || 1));

										// Check if this specific branch handle has a connection
										const branchHandleId = `branch-${index}`;
										const hasConnection = outgoingEdges.some(
											(edge) => edge.sourceHandle === branchHandleId,
										);

										if (hasConnection) {
											return null; // Don't show plus icon if branch has connection
										}

										// Stagger the plus icons horizontally so they don't overlap
										const horizontalOffset = 90 + index * 15;

										return (
											<div key={`plus-${index}`}>
												<svg
													className="absolute pointer-events-none"
													style={{
														width: `${horizontalOffset + 10}px`,
														height: "40px",
														left: "100%",
														top: `${topPosition}%`,
														transform: "translateY(-50%)",
													}}
												>
													<path
														d={`M 0 20 C ${Math.round(horizontalOffset * 0.45)} 6, ${Math.round(horizontalOffset * 0.7)} 34, ${horizontalOffset} 20`}
														stroke="#ffffff"
														strokeWidth="1"
														fill="none"
														opacity="0.3"
													/>
												</svg>

												<button
													onClick={createBranchPaletteClickHandler(index)}
													className={`absolute ${plusButtonBase} ${plusButtonShadow}`}
													style={{
														left: `calc(100% + ${horizontalOffset}px)`,
														top: `${topPosition}%`,
														transform: "translateY(-50%)",
													}}
													title={`Add connection from ${branch.label}`}
												>
													<Plus className="w-5 h-5 text-[color:var(--color-text-muted)] hover:text-[color:var(--color-accent)] transition-colors" />
												</button>
											</div>
										);
									},
								)}
							</>
						)}

					{/* Add Connection Plus Icon for other nodes - only show if no outgoing connections and not END node */}
					{(() => {
						const hasOutgoingConnection = outgoingEdges.length > 0;
						return (
							!isReadOnlyPreview &&
							nodeType !== "END" &&
							nodeType !== "CONDITION" &&
							!hasOutgoingConnection && (
								<>
									<svg
										className="absolute pointer-events-none"
										style={{
											width: "100px",
											height: "40px",
											left: "100%",
											top: "50%",
											transform: "translateY(-50%)",
										}}
									>
										<path
											d="M 0 20 C 36 6, 60 34, 90 20"
											stroke="#0f172a"
											strokeWidth="1"
											fill="none"
											opacity="0.25"
										/>
									</svg>

									<button
										onClick={handleOpenNodePaletteClick}
										className={`absolute ${plusButtonBase} ${plusButtonShadow} ${nodeType === "START" ? plusButtonPulse : ""} group`}
										style={{
											left: "calc(100% + 90px)",
											top: "50%",
											transform: "translateY(-50%)",
										}}
										data-tutorial={nodeType === "START" ? "start-add-next-btn" : undefined}
										title="Add next node"
									>
										<Plus className="w-5 h-5 text-[color:var(--color-text-muted)] group-hover:text-[color:var(--color-accent)] transition-all duration-200 group-hover:rotate-90" />
									</button>
								</>
							)
						);
					})()}
				</div>
			</div>
		</div>
	);
}

export default memo(FlowNode);
