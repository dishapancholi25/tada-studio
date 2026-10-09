"use client";

import {
	CheckCircle,
	Clock,
	Filter,
	Globe,
	Key,
	Loader2,
	Search,
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

interface WebSearchConfig {
	search_provider?: string;
	api_key?: string;
	max_results?: number;
	search_depth?: string;
	include_answer?: boolean;
	include_raw_content?: boolean;
	include_images?: boolean;
	timeout_seconds?: number;
	region?: string;
	safe_search?: string;
	time_range?: string;
	parent_agent_id?: string;
}

interface WebSearchNodeData {
	id: string;
	name: string;
	web_search_config?: WebSearchConfig;
	parent_agent_id?: string;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
	toolCallCount?: number;
}

interface WebSearchNodeProps extends NodeProps {
	data: WebSearchNodeData;
}

function WebSearchNode({ data, selected, id }: WebSearchNodeProps) {
	const { deleteNode } = useGraph();

	const searchProvider =
		data.web_search_config?.search_provider || "duckduckgo";
	const hasApiKey = data.web_search_config?.api_key ? true : false;
	const maxResults = data.web_search_config?.max_results || 5;
	const searchDepth = data.web_search_config?.search_depth || "basic";
	const includeAnswer = data.web_search_config?.include_answer || false;
	const region = data.web_search_config?.region;
	const timeRange = data.web_search_config?.time_range;

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

	// Amber/yellow theme for web search (memoized for performance)
	const gradientColors = useMemo(
		() => getExecutionGradient(executionStatus, "amber"),
		[executionStatus],
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
					style={createSelectionGlow(nodeColors.amber)}
				/>
			)}

			{/* Outer gradient frame (glass halo) */}
			<div
				className={`p-[1px] ${nodeFrameRadius.compact} transition-all duration-200 ${
					selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
				}`}
				style={createGradientFrame(nodeColors.amber)}
			>
				<div
					className={`
            relative min-w-[140px] max-w-[180px] ${nodeRadius.compact}
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
								backgroundColor: `rgb(${nodeColors.amber})`,
								borderColor: `rgba(${nodeColors.amber}, 0.3)`,
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
									<Search className="w-3 h-3 text-white" />
								</div>
								<span className="text-[10px] font-semibold text-white capitalize">
									Web Search
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
							{/* Configuration indicator (only show when no execution status) */}
							{!executionStatus &&
								!isExecuting &&
								hasApiKey &&
								searchProvider === "tavily" && (
									<div
										className="w-2 h-2 rounded-full animate-pulse"
										style={{ backgroundColor: `rgb(${nodeColors.amber})` }}
									/>
								)}
						</div>

						{/* Body */}
						<div className="px-3 py-2">
							<InlineNameEditor
								nodeId={id}
								initialName={data.name || "Web Search"}
								placeholder="Web Search"
								className="text-xs font-semibold text-slate-900 mb-1 truncate"
								readOnly={isReadOnlyPreview}
							/>

							<div className="space-y-0.5">
								<div className="flex items-center gap-1.5">
									{searchProvider === "tavily" ? (
										<div className="px-1.5 py-0.5 bg-gray-500/20 border border-gray-500/30 rounded text-[10px] font-medium text-gray-300">
											Tavily
										</div>
									) : (
										<div className="px-1.5 py-0.5 bg-amber-500/20 border border-amber-500/30 rounded text-[10px] font-medium text-slate-900">
											DuckDuckGo
										</div>
									)}
									{hasApiKey && searchProvider === "tavily" && (
										<div className="flex items-center gap-0.5 text-[10px]">
											<Key className="w-3 h-3 text-amber-400" />
										</div>
									)}
								</div>

								<div className="flex items-center gap-2 text-[10px] text-[color:var(--color-text-muted)]">
									<div className="flex items-center gap-0.5">
										<span>Max: {maxResults}</span>
									</div>
									{searchDepth !== "basic" && (
										<div className="flex items-center gap-0.5">
											<Filter className="w-3 h-3 text-amber-400" />
											<span>{searchDepth}</span>
										</div>
									)}
									{includeAnswer && (
										<span className="text-amber-400">+Answer</span>
									)}
								</div>

								{(region || timeRange) && (
									<div className="flex items-center gap-2 text-[10px] text-[color:var(--color-text-muted)]">
										{region && (
											<div className="flex items-center gap-0.5">
												<Globe className="w-3 h-3 text-amber-400" />
												<span>{region}</span>
											</div>
										)}
										{timeRange && (
											<div className="flex items-center gap-0.5">
												<Clock className="w-3 h-3 text-amber-400" />
												<span>{timeRange}</span>
											</div>
										)}
									</div>
								)}
							</div>
						</div>
					</div>

					{/* Handle - Only accepts connections from agents */}
					<Handle
						type="target"
						position={Position.Top}
						id="top"
						className="!w-3 !h-3 !bg-white !border-2 !border-[color:var(--color-border)]/80 hover:!border-amber-500 hover:!shadow-[0_0_8px_rgba(245,158,11,0.4)] transition-all"
						isConnectable={true}
					/>
				</div>
			</div>
		</div>
	);
}

export default memo(WebSearchNode);
