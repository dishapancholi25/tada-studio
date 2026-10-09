"use client";

import {
	CheckCircle,
	Clock,
	GitBranch,
	Layers,
	Loader2,
	// Plus, // Temporarily disabled — add-connection button commented out
	Settings,
	Trash2,
	XCircle,
} from "lucide-react";
import { memo, useCallback, useMemo } from "react";
import { Handle, type NodeProps, Position } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
// import { useNodeOutgoingEdges } from "@/hooks/useNodeOutgoingEdges"; // Temporarily disabled
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
	// plusButtonBase, // Temporarily disabled — add-connection button commented out
	// plusButtonShadow, // Temporarily disabled
} from "./shared/nodeStyles";

interface SubWorkflowNodeData {
	name: string;
	subworkflow_config?: {
		workflow_name?: string;
		target_workflow_id?: string;
		delegation_description?: string;
		input_schema?: Record<string, any>;
		output_schema?: Record<string, any>;
		timeout?: number;
		share_context?: boolean;
	};
	isExecuting?: boolean;
	executionStatus?: "pending" | "running" | "completed" | "failed" | "skipped";
	executionDuration?: number;
	hasOutgoingConnections?: boolean;
	nexts?: string[];
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
}

interface SubWorkflowNodeProps extends NodeProps {
	data: SubWorkflowNodeData;
}

function SubWorkflowNode({ data, selected, id }: SubWorkflowNodeProps) {
	const { deleteNode } = useGraph();
	// const outgoingEdges = useNodeOutgoingEdges(id); // Temporarily disabled — add-connection button commented out
	const isExecuting = data.isExecuting || false;
	const executionStatus = data.executionStatus;
	const executionDuration = data.executionDuration;
	const isReadOnlyPreview = Boolean(data.isReadOnlyPreview);

	// Get workflow configuration
	const config = data.subworkflow_config || {};
	const workflowName = config.workflow_name || data.name || "Sub-Workflow";
	const delegationDescription = config.delegation_description || "";

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
				return null;
		}
	};

	// Get gradient colors based on execution status (memoized for performance)
	const gradientColors = useMemo(
		() => getExecutionGradient(executionStatus, "teal"),
		[executionStatus],
	);

	const handleSettingsClick = () => {
		const event = new CustomEvent("openNodeSettings", {
			detail: { nodeId: id },
		});
		window.dispatchEvent(event);
	};

	// Click handler for settings button
	const handleSettingsButtonClick = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
		handleSettingsClick();
	}, []);

	// Click handler for delete button
	const handleDeleteButtonClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			deleteNode(id).catch((err) => {
				console.error("Failed to delete node:", err);
			});
		},
		[deleteNode, id],
	);

	// Click handler for node palette — temporarily disabled (add-connection button commented out)
	// const handleOpenNodePaletteClick = useCallback(
	// 	(e: React.MouseEvent) => {
	// 		e.stopPropagation();
	// 		const event = new CustomEvent("openNodePalette", {
	// 			detail: { sourceNodeId: id },
	// 		});
	// 		window.dispatchEvent(event);
	// 	},
	// 	[id],
	// );

	return (
		<div className="relative group">
			<EvalScoreBadge score={data.evalScore} />
			{/* Selection glow veneer */}
			{selected && (
				<div
					className={`pointer-events-none absolute -inset-[3px] ${nodeFrameRadius.standard} blur-xl opacity-60 transition-opacity`}
					style={createSelectionGlow(nodeColors.teal)}
				/>
			)}

			{/* Outer gradient frame (glass halo) */}
			<div
				className={`p-[1px] ${nodeFrameRadius.standard} transition-all duration-200 ${
					selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
				}`}
				style={createGradientFrame(nodeColors.teal)}
			>
				<div
					className={`
            relative min-w-[280px] max-w-[350px] ${nodeRadius.standard}
            ${nodeShadows.default}
            ${selected ? nodeShadows.selected : ""}
            transition-all duration-200
          `}
				>
					{/* Background gradient effect with status-based colors */}
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
					>
						{/* Header */}
						<div
							className={`flex items-center justify-between px-4 py-3 ${nodeHeaderRadius.standard} border-b`}
							style={{
								backgroundColor: `rgb(${nodeColors.teal})`,
								borderColor: `rgba(${nodeColors.teal}, 0.35)`,
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
									<Layers className="w-4 h-4 text-white" />
								</div>
								<span className="text-xs font-semibold text-white capitalize">
									Sub-Workflow
								</span>
							</div>

							<div className="flex items-center gap-2">
								<GuardrailIndicator nodeId={id} />
								{getStatusIcon()}
								{!isReadOnlyPreview && (
									<>
										{/* Action buttons */}
										<button
											onClick={handleSettingsButtonClick}
											className="p-1 rounded hover:bg-teal-500/20 transition-colors"
											title="Settings"
										>
											<Settings className="w-3.5 h-3.5 text-white hover:text-slate-900" />
										</button>

										<button
											onClick={handleDeleteButtonClick}
											className="p-1 rounded hover:bg-red-500/20 transition-colors"
											title="Delete"
										>
											<Trash2 className="w-3.5 h-3.5 text-white hover:text-slate-900" />
										</button>
									</>
								)}
							</div>
						</div>

						{/* Body */}
						<div className="px-4 py-3">
							{/* Workflow name */}
							<InlineNameEditor
								nodeId={id}
								initialName={workflowName}
								placeholder="Sub-Workflow"
								className="text-sm font-semibold text-slate-900 mb-2 truncate"
								readOnly={isReadOnlyPreview}
							/>

							{/* Feature indicators */}
							<div className="flex items-center gap-2 mb-2">
								{/* Workflow indicator */}
								<div
									className="flex items-center gap-1 px-2 py-0.5 bg-teal-100 border border-teal-200 rounded text-xs"
									title="Workflow Node"
								>
									<GitBranch className="w-3 h-3 text-teal-600" />
									<span className="text-teal-700 font-medium">Workflow</span>
								</div>

							</div>

							{/* Delegation description preview */}
							{delegationDescription && (
								<div className="mt-2 p-2 bg-[color:var(--color-surface)]/50 rounded text-xs">
									<div className="text-[color:var(--color-text-secondary)] font-mono line-clamp-3">
										{delegationDescription}
									</div>
								</div>
							)}

							{/* Execution duration */}
							{executionStatus === "completed" && executionDuration && (
								<div className="mt-2 pt-2 border-t border-teal-200">
									<div className="flex items-center gap-1 text-xs text-teal-600">
										<Clock className="w-3 h-3" />
										<span>{executionDuration.toFixed(2)}s</span>
									</div>
								</div>
							)}
						</div>
					</div>

					{/* Handles */}
					{/* Input handle - receives connection from agent's tool output */}
					<Handle
						type="target"
						position={Position.Top}
						id="input"
						className={handleStyles}
						title="Connect from Agent (as tool)"
					/>

						{/* Output handle — temporarily disabled; will enable in a later phase */}
						{/* <Handle
						type="source"
						position={Position.Right}
						id="output"
						className={handleStyles}
						title="Connect to workflow nodes"
						/> */}

					{/* Add Connection Plus Icon — temporarily disabled; will enable in a later phase */}
						{/* {!isReadOnlyPreview && outgoingEdges.length === 0 && (
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
									stroke="#ffffff"
									strokeWidth="1"
									fill="none"
									opacity="0.3"
								/>
							</svg>

							<button
								onClick={handleOpenNodePaletteClick}
								className={`absolute ${plusButtonBase} ${plusButtonShadow} group`}
								style={{
									left: "calc(100% + 90px)",
									top: "50%",
									transform: "translateY(-50%)",
								}}
								title="Add node"
							>
								<Plus className="w-4 h-4 text-[color:var(--color-text-muted)] group-hover:text-teal-400 transition-colors" />
							</button>
						</>
						)} */}
				</div>
			</div>
		</div>
	);
}

export default memo(SubWorkflowNode);
