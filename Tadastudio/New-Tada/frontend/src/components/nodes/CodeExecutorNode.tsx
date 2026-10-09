"use client";

import {
	CheckCircle,
	Clock,
	Code2,
	Loader2,
	Plus,
	Settings,
	Terminal,
	Trash2,
	XCircle,
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

interface CodeExecutorNodeData {
	name: string;
	code_executor_config?: {
		language?: "python" | "javascript";
		code?: string;
		timeout_seconds?: number;
		memory_limit_mb?: number;
		allow_network?: boolean;
		allow_filesystem?: boolean;
		input_variables?: Array<{
			variable_name: string;
			source_mode: string;
		}>;
		output_variable?: string;
	};
	isExecuting?: boolean;
	executionStatus?: "pending" | "running" | "completed" | "failed" | "skipped";
	executionDuration?: number;
	hasOutgoingConnections?: boolean;
	nexts?: string[];
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
}

interface CodeExecutorNodeProps extends NodeProps {
	data: CodeExecutorNodeData;
}

function CodeExecutorNode({ data, selected, id }: CodeExecutorNodeProps) {
	const { deleteNode } = useGraph();
	const outgoingEdges = useNodeOutgoingEdges(id);
	const isExecuting = data.isExecuting || false;
	const executionStatus = data.executionStatus;
	const executionDuration = data.executionDuration;
	const isReadOnlyPreview = Boolean(data.isReadOnlyPreview);

	const config = data.code_executor_config || {};
	const language = config.language || "python";
	const code = config.code || "";
	const timeoutSeconds = config.timeout_seconds || 30;
	const inputVars = config.input_variables || [];
	const outputVar = config.output_variable || "result";

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
				return <Clock className="w-4 h-4 text-white/70" />;
			default:
				return null;
		}
	};

	const gradientColors = useMemo(
		() => getExecutionGradient(executionStatus, "emerald"),
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

	const codePreview = useMemo(() => {
		if (!code) return "No code configured";
		const lines = code.split("\n");
		if (lines.length <= 2) return code.substring(0, 60);
		return `${lines[0].substring(0, 40)}... (${lines.length} lines)`;
	}, [code]);

	return (
		<div className="relative group">
			<EvalScoreBadge score={data.evalScore} />
			{selected && (
				<div
					className={`pointer-events-none absolute -inset-[3px] ${nodeFrameRadius.standard} blur-xl opacity-60 transition-opacity`}
					style={createSelectionGlow(nodeColors.emerald)}
				/>
			)}

			<div
				className={`p-[1px] ${nodeFrameRadius.standard} transition-all duration-200 ${
					selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
				}`}
				style={createGradientFrame(nodeColors.emerald)}
			>
				<div
					className={`
            relative min-w-[280px] max-w-[350px] ${nodeRadius.standard}
            ${nodeShadows.default}
            ${selected ? nodeShadows.selected : ""}
            transition-all duration-200
          `}
				>
					<div
						className={`hidden absolute inset-0 bg-gradient-to-br ${gradientColors.from} ${gradientColors.to} ${nodeRadius.standard} blur-xl ${
							isExecuting || executionStatus === "running"
								? "opacity-70 animate-pulse"
								: "opacity-40"
						}`}
					/>

					<div
						className={`relative ${nodeBodyGradient} border border-slate-200 ${nodeRadius.standard} ${
							isExecuting || executionStatus === "running"
								? "animate-pulse"
								: ""
						}`}
					>
						<div
							className={`flex items-center justify-between px-4 py-3 ${nodeHeaderRadius.standard} border-b`}
							style={{
								backgroundColor: `rgb(${nodeColors.emerald})`,
								borderColor: `rgba(${nodeColors.emerald}, 0.35)`,
							}}
						>
							<div className="flex items-center gap-2.5">
								<div
									className="h-8 w-8 rounded-xl border flex items-center justify-center"
									style={{
										backgroundColor: "rgba(255, 255, 255, 0.2)",
										borderColor: "rgba(255, 255, 255, 0.28)",
									}}
								>
									<Code2 className="w-4 h-4 text-white" />
								</div>
								<span className="text-xs font-semibold text-white uppercase tracking-[0.15em]">
									Code
								</span>
							</div>

							<div className="flex items-center gap-2">
								{getStatusIcon()}
								{!isReadOnlyPreview && (
									<>
										<button
											onClick={handleSettingsButtonClick}
											className="p-1 rounded hover:bg-emerald-500/20 transition-colors"
											title="Settings"
										>
											<Settings className="w-3.5 h-3.5 text-white hover:text-white" />
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

						<div className="px-4 py-3">
							<InlineNameEditor
								nodeId={id}
								initialName={data.name || "Code Executor"}
								placeholder="Code Executor"
								className="text-sm font-semibold text-slate-900 mb-2 truncate"
								readOnly={isReadOnlyPreview}
							/>

							<div className="flex items-center gap-2 mb-2 flex-wrap">
								<div
									className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
										language === "python"
											? "bg-blue-500/20"
											: "bg-yellow-500/20"
									}`}
									title={`Language: ${language}`}
								>
									<Terminal className="w-3 h-3 text-slate-600" />
									<span className="text-slate-800 capitalize">{language}</span>
								</div>

								<div
									className="flex items-center gap-1 px-2 py-0.5 bg-slate-500/20 rounded text-xs"
									title={`Timeout: ${timeoutSeconds}s`}
								>
									<Clock className="w-3 h-3 text-slate-500" />
									<span className="text-slate-800">{timeoutSeconds}s</span>
								</div>

								{inputVars.length > 0 && (
									<div
										className="flex items-center gap-1 px-2 py-0.5 bg-emerald-500/20 rounded text-xs"
										title={`${inputVars.length} input variable(s)`}
									>
										<span className="text-slate-800">
											{inputVars.length} input{inputVars.length !== 1 ? "s" : ""}
										</span>
									</div>
								)}
							</div>

							{code && (
								<div className="mt-2 p-2 bg-slate-100 rounded text-xs font-mono text-slate-700 overflow-hidden">
									<div className="truncate">{codePreview}</div>
								</div>
							)}

							{outputVar && outputVar !== "result" && (
								<div className="mt-2 text-xs text-slate-600">
									Output: <span className="font-mono">{outputVar}</span>
								</div>
							)}

							{executionStatus === "completed" && executionDuration && (
								<div className="mt-2 pt-2 border-t border-emerald-500/20">
									<div className="flex items-center gap-1 text-xs text-slate-800">
										<Clock className="w-3 h-3" />
										<span>{executionDuration.toFixed(2)}s</span>
									</div>
								</div>
							)}
						</div>
					</div>

					<Handle
						type="target"
						position={Position.Top}
						id="input"
						className={handleStyles}
						title="Input"
					/>

					<Handle
						type="source"
						position={Position.Right}
						id="output"
						className={handleStyles}
						title="Output"
					/>

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
								<Plus className="w-4 h-4 text-[color:var(--color-text-muted)] group-hover:text-emerald-400 transition-colors" />
							</button>
						</>
					)}
				</div>
			</div>
		</div>
	);
}

export default memo(CodeExecutorNode);
