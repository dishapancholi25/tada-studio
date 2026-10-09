"use client";

import {
	AlertCircle,
	CheckCircle,
	FileText,
	FolderOpen,
	Loader2,
	Trash2,
	XCircle,
} from "lucide-react";
import { memo, useCallback, useMemo } from "react";
import { Handle, type NodeProps, Position } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
import EvalScoreBadge from "../shared/EvalScoreBadge";
import InlineNameEditor from "../shared/InlineNameEditor";
import { getExecutionGradient } from "../shared/getExecutionGradient";
import {
	createGradientFrame,
	createSelectionGlow,
	nodeBodyGradient,
	nodeColors,
	nodeFrameRadius,
	nodeHeaderRadius,
	nodeRadius,
	nodeShadows,
} from "../shared/nodeStyles";

interface DocumentRetrieveConfig {
	collection_ids?: string[];
	max_document_size_tokens?: number;
	truncation_strategy?: string;
	output_format?: string;
	parent_agent_id?: string;
}

interface DocumentRetrieveNodeData {
	id: string;
	name: string;
	document_retrieve_config?: DocumentRetrieveConfig;
	parent_agent_id?: string;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
	toolCallCount?: number;
}

interface DocumentRetrieveNodeProps extends NodeProps {
	data: DocumentRetrieveNodeData;
}

function DocumentRetrieveNode({
	data,
	selected,
	id,
}: DocumentRetrieveNodeProps) {
	const { deleteNode } = useGraph();

	const collectionCount =
		data.document_retrieve_config?.collection_ids?.length || 0;
	const hasConfiguration = collectionCount > 0;

	const isExecuting = data.isExecuting || false;
	const executionStatus = data.executionStatus;
	const isReadOnlyPreview = Boolean(data.isReadOnlyPreview);
	const toolCallCount = data.toolCallCount || 0;

	const handleDeleteButtonClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			deleteNode(id).catch((err) => {
				console.error("Failed to delete node:", err);
			});
		},
		[deleteNode, id],
	);

	const gradientColors = useMemo(
		() => getExecutionGradient(executionStatus, "teal", hasConfiguration),
		[executionStatus, hasConfiguration],
	);

	const getStatusIcon = () => {
		if (isExecuting || executionStatus === "running") {
			return <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />;
		}
		switch (executionStatus) {
			case "completed":
				return (
					<div className="relative">
						<CheckCircle className="w-3.5 h-3.5 text-white" />
						{toolCallCount > 1 && (
							<span className="absolute -top-1.5 -right-2 min-w-[14px] h-[14px] flex items-center justify-center rounded-full bg-[#0DA931] text-[8px] font-bold text-white leading-none px-0.5">
								{toolCallCount}
							</span>
						)}
					</div>
				);
			case "failed":
				return <XCircle className="w-3.5 h-3.5 text-white" />;
			default:
				return null;
		}
	};

	return (
		<div className="relative group">
			<EvalScoreBadge score={data.evalScore} />
			{selected && (
				<div
					className={`pointer-events-none absolute -inset-[3px] ${nodeFrameRadius.compact} blur-xl opacity-60 transition-opacity`}
					style={createSelectionGlow(nodeColors.teal)}
				/>
			)}

			<div
				className={`p-[1px] ${nodeFrameRadius.compact} transition-all duration-200 ${
					selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
				}`}
				style={createGradientFrame(nodeColors.teal)}
			>
				<div
					className={`
            relative min-w-[160px] max-w-[200px] ${nodeRadius.compact}
            ${nodeShadows.default}
            ${selected ? nodeShadows.selected : ""}
            transition-all duration-200
          `}
				>
					<div
						className={`hidden absolute inset-0 bg-gradient-to-br ${gradientColors.from} ${gradientColors.to} ${nodeRadius.compact} blur-md ${
							isExecuting || executionStatus === "running"
								? "opacity-70 animate-pulse"
								: "opacity-35"
						}`}
					/>

					<div
						className={`relative ${nodeBodyGradient} border border-slate-200 ${nodeRadius.compact} ${
							isExecuting || executionStatus === "running"
								? "animate-pulse"
								: ""
						}`}
					>
						{/* Header */}
						<div
							className={`flex items-center justify-between px-3 py-2 ${nodeHeaderRadius.compact} border-b`}
							style={{
								backgroundColor: `rgb(${nodeColors.teal})`,
								borderColor: `rgba(${nodeColors.teal}, 0.3)`,
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
									<FileText className="w-3 h-3 text-white" />
								</div>
								<span className="text-[10px] font-semibold text-white capitalize">
									Doc Retrieve
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
							{!executionStatus && !hasConfiguration && (
								<div className="relative group/error">
									<AlertCircle className="w-4 h-4 text-white" />
									<div className="absolute right-0 top-6 opacity-0 group-hover/error:opacity-100 transition-opacity pointer-events-none z-50">
										<div className="bg-red-50 text-red-700 text-xs px-3 py-2 rounded-lg shadow-lg whitespace-nowrap border border-red-200">
											Collections required
										</div>
									</div>
								</div>
							)}
						</div>

						{/* Body */}
						<div className="px-3 py-2">
							<InlineNameEditor
								nodeId={id}
								initialName={data.name || "Document Retrieve"}
								placeholder="Document Retrieve"
								className="text-xs font-semibold text-slate-900 mb-1 truncate"
								readOnly={isReadOnlyPreview}
							/>

							{hasConfiguration ? (
								<div className="space-y-0.5">
									<div className="flex items-center gap-1 text-[10px]">
										<FolderOpen className="w-3 h-3 text-teal-400" />
										<span className="text-[color:var(--color-text-muted)]">
											{collectionCount} collection
											{collectionCount !== 1 ? "s" : ""}
										</span>
									</div>
								</div>
							) : (
								<p className="text-[10px] text-[color:var(--color-text-muted)] italic">
									Not configured
								</p>
							)}
						</div>
					</div>

					<Handle
						type="target"
						position={Position.Top}
						id="top"
						className="!w-3 !h-3 !bg-white !border-2 !border-[color:var(--color-border)]/80 hover:!border-teal-500 hover:!shadow-[0_0_8px_rgba(20,184,166,0.4)] transition-all"
						isConnectable={true}
					/>
				</div>
			</div>
		</div>
	);
}

export default memo(DocumentRetrieveNode);
