import {
	AlertCircle,
	CheckCircle,
	Clock,
	FileCode,
	FileImage,
	FileText,
	Loader2,
	Plus,
	Settings,
	Trash2,
	XCircle,
} from "lucide-react";
import type React from "react";
import { memo, useCallback, useMemo } from "react";
import { Handle, type NodeProps, Position } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
import { useNodeOutgoingEdges } from "@/hooks/useNodeOutgoingEdges";
import type { FileReadConfig } from "@/types/nodes";
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

interface FileReadNodeData {
	id: string;
	type: "FILE_READ";
	name: string;
	position?: { x: number; y: number };
	file_read_config?: FileReadConfig;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	executionDuration?: number;
	nexts?: string[];
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
}

const FileReadNode = memo(
	({ data, selected, id }: NodeProps<FileReadNodeData>) => {
		const { deleteNode } = useGraph();
		const outgoingEdges = useNodeOutgoingEdges(id);
		const isExecuting = data.isExecuting || false;
		const executionStatus = data.executionStatus;
		const executionDuration = data.executionDuration;
		const config = data.file_read_config || {};
		const hasConfiguration =
			config.extraction_mode || config.file_path || config.file_content;
		const isReadOnlyPreview = Boolean(data.isReadOnlyPreview);

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
			() => getExecutionGradient(executionStatus, "orange", !!hasConfiguration),
			[executionStatus, hasConfiguration],
		);

		const handleSettingsClick = () => {
			const event = new CustomEvent("openFileReadProperties", {
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

		// Click handler for node palette
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
            relative min-w-[240px] max-w-[300px] ${nodeRadius.standard}
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
										<FileText className="w-4 h-4 text-white" />
									</div>
									<span className="text-xs font-semibold text-white capitalize">
										File Read
									</span>
								</div>

								<div className="flex items-center gap-2">
									<GuardrailIndicator nodeId={id} />
									{getStatusIcon()}

									{/* Error indicator for missing configuration */}
									{!executionStatus && !hasConfiguration && (
										<div className="relative group/error">
											<AlertCircle className="w-4 h-4 text-white" />
											<div className="absolute right-0 top-6 opacity-0 group-hover/error:opacity-100 transition-opacity pointer-events-none z-50">
												<div className="bg-red-50 text-red-700 text-xs px-3 py-2 rounded-lg shadow-lg whitespace-nowrap border border-red-200">
													File read configuration required
												</div>
											</div>
										</div>
									)}

									{!isReadOnlyPreview && (
										<>
											<button
												onClick={handleSettingsButtonClick}
												className="p-1 rounded hover:bg-orange-500/20 transition-colors"
												title="Settings"
											>
												<Settings className="w-3.5 h-3.5 text-white" />
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
									initialName={data.name || "File Read"}
									placeholder="File Read"
									className="text-sm font-semibold text-slate-900 mb-2 truncate"
									readOnly={isReadOnlyPreview}
								/>

								{/* Configuration preview */}
								{hasConfiguration ? (
									<div className="space-y-2">
										{/* Mode and format badges */}
										<div className="flex items-center gap-2 flex-wrap">
											<div
												className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium"
												style={{
													backgroundColor: `rgba(${nodeColors.orange}, 0.12)`,
													borderColor: `rgba(${nodeColors.orange}, 0.35)`,
												}}
											>
												<FileCode className="w-3 h-3 text-orange-400" />
												<span className="text-slate-900">
													{config.extraction_mode === "text_only"
														? "Text Only"
														: config.extraction_mode === "raw"
															? "Disabled"
															: "AI OCR"}
												</span>
											</div>

											{config.doc_type && config.doc_type !== "auto" && (
												<div
													className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium"
													style={{
														backgroundColor: `rgba(${nodeColors.violet}, 0.12)`,
														borderColor: `rgba(${nodeColors.violet}, 0.35)`,
													}}
												>
													<FileImage className="w-3 h-3 text-violet-400" />
													<span className="text-slate-900 capitalize">
														{config.doc_type}
													</span>
												</div>
											)}

											{config.output_format &&
												config.output_format !== "markdown" && (
													<div
														className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium"
														style={{
															backgroundColor: `rgba(${nodeColors.blue}, 0.12)`,
															borderColor: `rgba(${nodeColors.blue}, 0.35)`,
														}}
													>
														<span className="text-slate-900">
															{config.output_format === "json"
																? "JSON"
																: config.output_format === "plain"
																	? "Plain"
																	: config.output_format === "raw"
																		? "Raw"
																		: "Markdown"}
														</span>
													</div>
												)}

											{config.extraction_mode === "raw" &&
												config.llm_safe_output && (
													<div
														className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium"
														style={{
															backgroundColor: `rgba(${nodeColors.blue}, 0.12)`,
															borderColor: `rgba(${nodeColors.blue}, 0.35)`,
														}}
													>
														<span className="text-slate-900">LLM-safe</span>
													</div>
												)}
										</div>

										{/* File path if configured */}
										{config.file_path && (
											<p className="text-xs text-[color:var(--color-text-muted)] truncate">
												{config.file_path.split("/").pop() ||
													config.file_path.split("\\").pop()}
											</p>
										)}

										{/* File size limit if configured */}
										{config.max_file_size_mb &&
											config.max_file_size_mb !== 10 && (
												<p className="text-xs text-[color:var(--color-text-muted)]">
													Max: {config.max_file_size_mb}MB
												</p>
											)}
									</div>
								) : (
									<p className="text-xs text-[color:var(--color-text-muted)] italic">
										Not configured
									</p>
								)}

								{/* Execution duration */}
								{executionStatus === "completed" && executionDuration && (
									<div className="mt-2 pt-2 border-t border-orange-500/20">
										<div className="flex items-center gap-1 text-xs text-slate-700">
											<Clock className="w-3 h-3" />
											<span>{executionDuration.toFixed(2)}s</span>
										</div>
									</div>
								)}
							</div>
						</div>

						{/* Handles */}
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
									title="Add next node"
								>
									<Plus className="w-4 h-4 text-[color:var(--color-text-muted)] group-hover:text-slate-700 transition-colors" />
								</button>
							</>
						)}
					</div>
				</div>
			</div>
		);
	},
);

FileReadNode.displayName = "FileReadNode";

export default FileReadNode;
