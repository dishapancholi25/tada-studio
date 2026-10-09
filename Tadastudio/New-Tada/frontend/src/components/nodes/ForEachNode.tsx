"use client";

import {
	AlertCircle,
	CheckCircle,
	Clock,
	Layers,
	Loader2,
	Plus,
	Repeat,
	Settings,
	Trash2,
	XCircle,
	Zap,
} from "lucide-react";
import { memo, useCallback, useMemo } from "react";
import { Handle, type NodeProps, Position } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
import { useNodeOutgoingEdges } from "@/hooks/useNodeOutgoingEdges";
import EvalScoreBadge from "./shared/EvalScoreBadge";
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

interface ForEachNodeData {
	name: string;
	for_each_config?: {
		source_mode?: "previous" | "specific" | "start";
		source_node_id?: string;
		field_path?: string;
		concurrency_limit?: number;
		rate_limit_per_second?: number | null;
		max_iterations?: number;
		error_strategy?: "continue_on_error" | "fail_fast";
		max_retries_per_item?: number;
	};
	isExecuting?: boolean;
	executionStatus?: "pending" | "running" | "completed" | "failed" | "skipped";
	executionDuration?: number;
	hasOutgoingConnections?: boolean;
	nexts?: string[];
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
	// For Each progress during execution
	forEachProgress?: {
		completed: number;
		failed: number;
		total: number;
	};
}

interface ForEachNodeProps extends NodeProps {
	data: ForEachNodeData;
}

function ForEachNode({ data, selected, id }: ForEachNodeProps) {
	const { deleteNode } = useGraph();
	const outgoingEdges = useNodeOutgoingEdges(id);
	const isExecuting = data.isExecuting || false;
	const executionStatus = data.executionStatus;
	const executionDuration = data.executionDuration;
	const isReadOnlyPreview = Boolean(data.isReadOnlyPreview);

	// Get For Each configuration
	const config = data.for_each_config || {};
	const fieldPath = config.field_path || "fields.rows";
	const concurrencyLimit = config.concurrency_limit || 5;
	const errorStrategy = config.error_strategy || "continue_on_error";
	const progress = data.forEachProgress;

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

	// Get gradient colors based on execution status
	const gradientColors = useMemo(
		() => getExecutionGradient(executionStatus, "amber"),
		[executionStatus],
	);

	const handleSettingsClick = () => {
		const event = new CustomEvent("openNodeSettings", {
			detail: { nodeId: id },
		});
		window.dispatchEvent(event);
	};

	const handleSettingsButtonClick = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
		handleSettingsClick();
	}, []);

	const handleDeleteButtonClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			deleteNode(id).catch((err) => {
				console.error("Failed to delete node:", err);
			});
		},
		[deleteNode, id],
	);

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

	return (
		<div className="relative group">
			<EvalScoreBadge score={data.evalScore} />
			{/* Selection glow veneer */}
			{selected && (
				<div
					className={`pointer-events-none absolute -inset-[3px] ${nodeFrameRadius.standard} blur-xl opacity-60 transition-opacity`}
					style={createSelectionGlow(nodeColors.amber)}
				/>
			)}

			{/* Outer gradient frame (glass halo) */}
			<div
				className={`p-[1px] ${nodeFrameRadius.standard} transition-all duration-200 ${
					selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
				}`}
				style={createGradientFrame(nodeColors.amber)}
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
								backgroundColor: `rgb(${nodeColors.amber})`,
								borderColor: `rgba(${nodeColors.amber}, 0.35)`,
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
									<Repeat className="w-4 h-4 text-white" />
								</div>
								<span className="text-xs font-semibold text-white capitalize">
									For Each
								</span>
							</div>

							<div className="flex items-center gap-2">
								{getStatusIcon()}
								{!isReadOnlyPreview && (
									<>
										<button
											onClick={handleSettingsButtonClick}
											className="p-1 rounded hover:bg-amber-500/20 transition-colors"
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
							{/* Node name */}
							<InlineNameEditor
								nodeId={id}
								initialName={data.name || "For Each"}
								placeholder="For Each"
								className="text-sm font-semibold text-slate-900 mb-2 truncate"
								readOnly={isReadOnlyPreview}
							/>

							{/* Feature indicators */}
							<div className="flex items-center gap-2 mb-2 flex-wrap">
								{/* Field path indicator */}
								<div
									className="flex items-center gap-1 px-2 py-0.5 bg-amber-500/20 rounded text-xs min-w-0"
									title={`Field path: ${fieldPath}`}
								>
									<Layers className="w-3 h-3 text-amber-400 flex-shrink-0" />
									<span className="text-slate-800 truncate">{fieldPath}</span>
								</div>

								{/* Concurrency indicator */}
								<div
									className="flex items-center gap-1 px-2 py-0.5 bg-orange-500/20 rounded text-xs flex-shrink-0"
									title={`Concurrency: ${concurrencyLimit}`}
								>
									<Zap className="w-3 h-3 text-orange-400 flex-shrink-0" />
									<span className="text-slate-800">x{concurrencyLimit}</span>
								</div>

								{/* Error strategy indicator */}
								{errorStrategy === "fail_fast" && (
									<div
										className="flex items-center gap-1 px-2 py-0.5 bg-red-500/20 rounded text-xs flex-shrink-0"
										title="Fail fast on error"
									>
										<AlertCircle className="w-3 h-3 text-red-400 flex-shrink-0" />
										<span className="text-red-800">Fail Fast</span>
									</div>
								)}
							</div>

							{/* Progress during execution */}
							{progress && (executionStatus === "running" || executionStatus === "completed") && (
								<div className="mt-2 p-2 bg-[color:var(--color-surface)]/50 rounded">
									<div className="flex items-center justify-between text-xs mb-1">
										<span className="text-slate-800">
											{progress.completed + progress.failed} / {progress.total}
										</span>
										<span className="text-slate-800">
											{progress.total > 0
												? Math.round(((progress.completed + progress.failed) / progress.total) * 100)
												: 0}%
										</span>
									</div>
									{/* Progress bar */}
									<div className="w-full h-1.5 bg-[color:var(--color-surface)] rounded-full overflow-hidden">
										<div
											className="h-full bg-amber-400 rounded-full transition-all duration-300"
											style={{
												width: `${progress.total > 0 ? ((progress.completed + progress.failed) / progress.total) * 100 : 0}%`,
											}}
										/>
									</div>
									{progress.failed > 0 && (
										<div className="mt-1 text-xs text-red-700">
											{progress.failed} failed
										</div>
									)}
								</div>
							)}

							{/* Execution duration */}
							{executionStatus === "completed" && executionDuration && (
								<div className="mt-2 pt-2 border-t border-amber-500/20">
									<div className="flex items-center gap-1 text-xs text-slate-800">
										<Clock className="w-3 h-3" />
										<span>{executionDuration.toFixed(2)}s</span>
									</div>
								</div>
							)}
						</div>
					</div>

					{/* Handles */}
					{/* Input handle */}
					<Handle
						type="target"
						position={Position.Top}
						id="input"
						className={handleStyles}
						title="Input"
					/>

					{/* Output handle - connects to body nodes or next nodes */}
					<Handle
						type="source"
						position={Position.Right}
						id="output"
						className={handleStyles}
						title="Connect to body nodes"
					/>

					{/* Add Connection Plus Icon - only show if no outgoing connections */}
					{!isReadOnlyPreview && outgoingEdges.length === 0 && (
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
								<Plus className="w-4 h-4 text-[color:var(--color-text-muted)] group-hover:text-amber-400 transition-colors" />
							</button>
						</>
					)}
				</div>
			</div>
		</div>
	);
}

export default memo(ForEachNode);
