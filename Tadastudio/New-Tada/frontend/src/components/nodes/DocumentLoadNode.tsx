"use client";

import {
	AlertCircle,
	CheckCircle,
	Clock,
	Download,
	FileText,
	FolderOpen,
	Loader2,
	Plus,
	Trash2,
	XCircle,
} from "lucide-react";
import type React from "react";
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

interface DocumentLoadConfig {
	collection_id?: string;
	document_ids?: string[];
	output_mode?: string;
	chunk_output_mode?: string;
}

interface DocumentLoadNodeData {
	id: string;
	type: "DOCUMENT_LOAD";
	name: string;
	position?: { x: number; y: number };
	document_load_config?: DocumentLoadConfig;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	executionDuration?: number;
	nexts?: string[];
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
}

const DocumentLoadNode = memo(
	({ data, selected, id }: NodeProps<DocumentLoadNodeData>) => {
		const { deleteNode } = useGraph();
		const outgoingEdges = useNodeOutgoingEdges(id);
		const isExecuting = data.isExecuting || false;
		const executionStatus = data.executionStatus;
		const config = data.document_load_config || {};
		const hasConfiguration =
			config.collection_id || (config.document_ids && config.document_ids.length > 0);
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

		const gradientColors = useMemo(
			() =>
				getExecutionGradient(executionStatus, "indigo", !!hasConfiguration),
			[executionStatus, hasConfiguration],
		);

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

		const outputMode = config.output_mode || "batch";
		const chunkMode = config.chunk_output_mode || "full";
		const docCount = config.document_ids?.length || 0;

		return (
			<div className="relative group">
				<EvalScoreBadge score={data.evalScore} />
				{/* Selection glow */}
				{selected && (
					<div
						className={`pointer-events-none absolute -inset-[3px] ${nodeFrameRadius.standard} blur-xl opacity-60 transition-opacity`}
						style={createSelectionGlow(nodeColors.indigo)}
					/>
				)}

				{/* Outer gradient frame */}
				<div
					className={`p-[1px] ${nodeFrameRadius.standard} transition-all duration-200 ${
						selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
					}`}
					style={createGradientFrame(nodeColors.indigo)}
				>
					<div
						className={`
              relative min-w-[200px] max-w-[240px] ${nodeRadius.standard}
              ${nodeShadows.default}
              ${selected ? nodeShadows.selected : ""}
              transition-all duration-200
            `}
					>
						{/* Background gradient */}
						<div
							className={`hidden absolute inset-0 bg-gradient-to-br ${gradientColors.from} ${gradientColors.to} ${nodeRadius.standard} blur-md ${
								isExecuting || executionStatus === "running"
									? "opacity-70 animate-pulse"
									: "opacity-35"
							}`}
						/>

						{/* Main container */}
						<div
							className={`relative ${nodeBodyGradient} border border-slate-200 ${nodeRadius.standard} ${
								isExecuting || executionStatus === "running"
									? "animate-pulse"
									: ""
							}`}
						>
							{/* Header */}
							<div
								className={`flex items-center justify-between px-3 py-2 ${nodeHeaderRadius.standard} border-b`}
								style={{
									backgroundColor: `rgb(${nodeColors.indigo})`,
									borderColor: `rgba(${nodeColors.indigo}, 0.3)`,
								}}
							>
								<div className="flex items-center gap-1.5">
									<div
										className="h-6 w-6 rounded-lg border flex items-center justify-center"
										style={{
											backgroundColor: "rgba(255, 255, 255, 0.2)",
											borderColor: "rgba(255, 255, 255, 0.28)",
										}}
									>
										<Download className="w-3 h-3 text-white" />
									</div>
									<span className="text-[10px] font-semibold text-white capitalize">
										Doc Load
									</span>
								</div>
								<div className="flex items-center gap-1.5">
									{getStatusIcon()}
									{!isReadOnlyPreview && (
										<button
											onClick={handleDeleteButtonClick}
											className="p-0.5 rounded hover:bg-red-500/20 transition-colors"
											title="Delete"
										>
											<Trash2 className="w-3 h-3 text-white hover:text-slate-900" />
										</button>
									)}
								</div>
							</div>

							{/* Body */}
							<div className="px-3 py-2">
								<InlineNameEditor
									nodeId={id}
									initialName={data.name || "Document Load"}
									placeholder="Document Load"
									className="text-xs font-semibold text-slate-900 mb-1.5 truncate"
									readOnly={isReadOnlyPreview}
								/>

								{hasConfiguration ? (
									<div className="space-y-0.5">
										{config.collection_id && (
											<div className="flex items-center gap-1 text-[10px]">
												<FolderOpen className="w-3 h-3 text-indigo-400" />
												<span className="text-[color:var(--color-text-muted)]">
													Collection configured
												</span>
											</div>
										)}
										{docCount > 0 && (
											<div className="flex items-center gap-1 text-[10px]">
												<FileText className="w-3 h-3 text-indigo-400" />
												<span className="text-[color:var(--color-text-muted)]">
													{docCount} specific doc{docCount !== 1 ? "s" : ""}
												</span>
											</div>
										)}
										<div className="flex gap-1 mt-1">
											<span className="text-[9px] px-1.5 py-0.5 rounded-full bg-indigo-500/15 text-white border border-indigo-500/30">
												{outputMode}
											</span>
											{chunkMode !== "full" && (
												<span className="text-[9px] px-1.5 py-0.5 rounded-full bg-indigo-500/15 text-white border border-indigo-500/30">
													{chunkMode}
												</span>
											)}
										</div>
									</div>
								) : (
									<div className="flex items-center gap-1">
										<AlertCircle className="w-3 h-3 text-amber-400" />
										<p className="text-[10px] text-[color:var(--color-text-muted)] italic">
											Not configured
										</p>
									</div>
								)}
							</div>

							{/* Input handle */}
							<Handle
								type="target"
								position={Position.Top}
								id="top"
								className={`${handleStyles} hover:!border-indigo-500`}
								isConnectable={true}
							/>

							{/* Output handle */}
							<Handle
								type="source"
								position={Position.Bottom}
								id="bottom"
								className={`${handleStyles} hover:!border-indigo-500`}
								isConnectable={true}
							/>
						</div>

						{/* Add next node button */}
						{!isReadOnlyPreview && outgoingEdges.length === 0 && (
							<div className="absolute left-1/2 -translate-x-1/2 -bottom-8 opacity-0 group-hover:opacity-100 transition-opacity">
								<button
									className={`${plusButtonBase} ${plusButtonShadow} text-white hover:text-indigo-200`}
									onClick={handleOpenNodePaletteClick}
									title="Add next node"
								>
									<Plus className="w-3 h-3" />
								</button>
							</div>
						)}
					</div>
				</div>
			</div>
		);
	},
);

DocumentLoadNode.displayName = "DocumentLoadNode";

export default DocumentLoadNode;
