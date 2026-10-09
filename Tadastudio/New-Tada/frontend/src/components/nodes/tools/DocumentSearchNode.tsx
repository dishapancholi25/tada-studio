"use client";

import {
	AlertCircle,
	CheckCircle,
	FileSearch,
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
import GuardrailIndicator from "../shared/GuardrailIndicator";
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

interface DocumentSearchConfig {
	document_collections?: string[];
	document_ids?: string[];
	search_k?: number;
	search_type?: string;
	similarity_threshold?: number;
	citation_format?: string;
	parent_agent_id?: string;
}

interface DocumentSearchNodeData {
	id: string;
	name: string;
	document_search_config?: DocumentSearchConfig;
	parent_agent_id?: string;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
	toolCallCount?: number;
}

interface DocumentSearchNodeProps extends NodeProps {
	data: DocumentSearchNodeData;
}

function DocumentSearchNode({ data, selected, id }: DocumentSearchNodeProps) {
	const { deleteNode } = useGraph();

	const collectionCount =
		data.document_search_config?.document_collections?.length || 0;
	const documentCount = data.document_search_config?.document_ids?.length || 0;
	const totalSources = collectionCount + documentCount;
	const hasConfiguration = totalSources > 0;

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

	// Blue/cyan theme for document search (memoized for performance)
	const gradientColors = useMemo(
		() => getExecutionGradient(executionStatus, "blue", hasConfiguration),
		[executionStatus, hasConfiguration],
	);

	// Status icon for execution feedback
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
			{/* Selection glow veneer */}
			{selected && (
				<div
					className={`pointer-events-none absolute -inset-[3px] ${nodeFrameRadius.compact} blur-xl opacity-60 transition-opacity`}
					style={createSelectionGlow(nodeColors.blue)}
				/>
			)}

			{/* Outer gradient frame (glass halo) */}
			<div
				className={`p-[1px] ${nodeFrameRadius.compact} transition-all duration-200 ${
					selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
				}`}
				style={createGradientFrame(nodeColors.blue)}
			>
				<div
					className={`
            relative min-w-[160px] max-w-[200px] ${nodeRadius.compact}
            ${nodeShadows.default}
            ${selected ? nodeShadows.selected : ""}
            transition-all duration-200
          `}
				>
					{/* Background gradient effect */}
					<div
						className={`hidden absolute inset-0 bg-gradient-to-br ${gradientColors.from} ${gradientColors.to} ${nodeRadius.compact} blur-md ${
							isExecuting || executionStatus === "running"
								? "opacity-70 animate-pulse"
								: "opacity-35"
						}`}
					/>

					{/* Main node container */}
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
								backgroundColor: `rgb(${nodeColors.blue})`,
								borderColor: `rgba(${nodeColors.blue}, 0.3)`,
							}}
						>
							<div className="flex items-center gap-1.5">
								{/* Icon capsule */}
								<div
									className="h-6 w-6 rounded-lg border flex items-center justify-center"
									style={{
										backgroundColor: "rgba(255, 255, 255, 0.2)",
										borderColor: "rgba(255, 255, 255, 0.28)",
									}}
								>
									<FileSearch className="w-3 h-3 text-white" />
								</div>
								<span className="text-[10px] font-semibold text-white capitalize">
									Doc Search
								</span>
							</div>
							<GuardrailIndicator nodeId={id} />
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
							{/* Error indicator for missing configuration (only show when no execution status) */}
							{!executionStatus && !hasConfiguration && (
								<div className="relative group/error">
									<AlertCircle className="w-4 h-4 text-white" />
									<div className="absolute right-0 top-6 opacity-0 group-hover/error:opacity-100 transition-opacity pointer-events-none z-50">
										<div className="bg-red-50 text-red-700 text-xs px-3 py-2 rounded-lg shadow-lg whitespace-nowrap border border-red-200">
											Document sources required
										</div>
									</div>
								</div>
							)}
						</div>

						{/* Body */}
						<div className="px-3 py-2">
							<InlineNameEditor
								nodeId={id}
								initialName={data.name || "Document Search"}
								placeholder="Document Search"
								className="text-xs font-semibold text-slate-900 mb-1 truncate"
								readOnly={isReadOnlyPreview}
							/>

							{hasConfiguration ? (
								<div className="space-y-0.5">
									{collectionCount > 0 && (
										<div className="flex items-center gap-1 text-[10px]">
											<FolderOpen className="w-3 h-3 text-blue-400" />
											<span className="text-[color:var(--color-text-muted)]">
												{collectionCount} collection
												{collectionCount !== 1 ? "s" : ""}
											</span>
										</div>
									)}
									{documentCount > 0 && (
										<div className="flex items-center gap-1 text-[10px]">
											<FileText className="w-3 h-3 text-blue-400" />
											<span className="text-[color:var(--color-text-muted)]">
												{documentCount} doc{documentCount !== 1 ? "s" : ""}
											</span>
										</div>
									)}
								</div>
							) : (
								<p className="text-[10px] text-[color:var(--color-text-muted)] italic">
									Not configured
								</p>
							)}
						</div>
					</div>

					{/* Handle - Only accepts connections from agents */}
					<Handle
						type="target"
						position={Position.Top}
						id="top"
						className="!w-3 !h-3 !bg-white !border-2 !border-[color:var(--color-border)]/80 hover:!border-blue-500 hover:!shadow-[0_0_8px_rgba(59,130,246,0.4)] transition-all"
						isConnectable={true}
					/>
				</div>
			</div>
		</div>
	);
}

export default memo(DocumentSearchNode);
