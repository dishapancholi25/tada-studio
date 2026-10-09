"use client";

import { AlertCircle, CheckCircle, Clock } from "lucide-react";
import React, { useMemo, useState } from "react";
import { useGraphStore } from "@/stores/graphStore";
import type { NodeExecution } from "@/types/api";
import NodeFeedbackButtons from "../../../shared/NodeFeedbackButtons";
import { getProviderVisuals } from "../../../icons/McpProviderIcons";
import ExecutionHeader from "../../../ui/ExecutionHeader";
import ExecutionModal from "../../../ui/ExecutionModal";
import { useExecutionData } from "./hooks/useExecutionData";
import { useToolRegistry } from "./hooks/useToolRegistry";
import { DatabaseQueryRenderer } from "./renderers/DatabaseQueryRenderer";
import { DocumentRetrieveRenderer } from "./renderers/DocumentRetrieveRenderer";
import { DocumentSearchRenderer } from "./renderers/DocumentSearchRenderer";
import { EmailSendRenderer } from "./renderers/EmailSendRenderer";
import { FileWriteRenderer } from "./renderers/FileWriteRenderer";
import { HttpRequestRenderer } from "./renderers/HttpRequestRenderer";
import { McpServerRenderer } from "./renderers/McpServerRenderer";
// Import renderers
import { WebSearchRenderer } from "./renderers/WebSearchRenderer";
import type { McpServerExecution, ToolType } from "./types/execution.types";
import { formatToolName, getStatusIcon } from "./utils/formatters";

// Renderer mapping
const RENDERER_MAP = {
	web_search: WebSearchRenderer,
	http_request: HttpRequestRenderer,
	database_query: DatabaseQueryRenderer,
	document_search: DocumentSearchRenderer,
	document_retrieve: DocumentRetrieveRenderer,
	email_send: EmailSendRenderer,
	file_write: FileWriteRenderer,
	mcp_server: McpServerRenderer,
};

export interface UnifiedToolExecutionPanelProps {
	toolType: ToolType;
	nodeId: string;
	nodeName: string;
	executionId: string; // Can be WebSocket ID or Database UUID
	nodeExecution?: NodeExecution;
	parentAgentNodeId?: string; // For MCP nodes: the agent connected to this MCP node
	isExecuting?: boolean; // Whether the workflow is currently running
	onClose: () => void;
}

export default function UnifiedToolExecutionPanel({
	toolType,
	nodeId,
	nodeName,
	executionId,
	nodeExecution: preloadedData,
	parentAgentNodeId,
	isExecuting,
	onClose,
}: UnifiedToolExecutionPanelProps) {
	console.log("[DEBUG DB_QUERY Panel] UnifiedToolExecutionPanel mounted:", {
		toolType,
		nodeId,
		nodeName,
		executionId,
		hasPreloadedData: !!preloadedData,
	});

	const [selectedExecutionIndex, setSelectedExecutionIndex] = useState(0);

	// Get tool configuration
	const toolConfig = useToolRegistry(toolType);
	const Icon = toolConfig.icon;

	// Fetch execution data with dual ID support
	const { nodeExecution, toolExecutions, loading, error } = useExecutionData({
		executionId,
		nodeId,
		nodeName: nodeName || toolConfig.title,
		toolType,
		nodeExecution: preloadedData,
		parentAgentNodeId,
		isExecuting,
	});

	// Get the appropriate renderer class
	const RendererClass = RENDERER_MAP[toolType];

	// Determine status
	const status = useMemo(() => {
		if (loading) return "loading";
		if (error) return "error";
		if (!nodeExecution) {
			// No data yet — if workflow is running, show as in-progress
			return isExecuting ? "in_progress" : "error";
		}
		if (nodeExecution.status === "failed") return "error";
		if (nodeExecution.status === "completed") return "success";
		if (nodeExecution.status === "running") return "in_progress";
		return "pending";
	}, [loading, error, nodeExecution, isExecuting]);

	// Debug logging
	console.log(`[DEBUG DB_QUERY Panel] After useExecutionData:`, {
		hasNodeExecution: !!nodeExecution,
		toolExecutionsCount: toolExecutions.length,
		loading,
		error,
		toolExecutions: toolExecutions,
		// Show review_iteration for each execution
		toolExecutionsReviewIterations: toolExecutions.map((te, i) => ({
			idx: i,
			call_id: te.call_id,
			review_iteration: te.review_iteration,
		})),
	});

	console.log(`[UnifiedToolExecutionPanel] Rendering ${toolType} panel`, {
		executionId,
		nodeId,
		loading,
		error,
		hasNodeExecution: !!nodeExecution,
		nodeExecutionReviewIteration: nodeExecution?.review_iteration,
		toolExecutionsCount: toolExecutions.length,
		status,
	});

	// For MCP server, get provider from node config (authoritative) or execution detection (fallback)
	const nodes = useGraphStore((state) => state.nodes);
	const graphNode = nodes.find((n) => n.id === nodeId);
	const nodeConfigProvider =
		toolType === "mcp_server"
			? graphNode?.data?.mcp_server_config?.provider
			: undefined;

	const mcpExecution =
		toolType === "mcp_server" && toolExecutions.length > 0
			? (toolExecutions[0] as McpServerExecution)
			: null;

	// Node config provider takes precedence over execution-detected provider
	const effectiveProvider =
		toolType === "mcp_server"
			? nodeConfigProvider || mcpExecution?.provider || null
			: null;

	const providerVisuals = effectiveProvider
		? getProviderVisuals(effectiveProvider)
		: null;

	// Override provider on MCP executions so the renderer uses the correct visuals
	const effectiveToolExecutions = useMemo(() => {
		if (
			toolType !== "mcp_server" ||
			!nodeConfigProvider ||
			nodeConfigProvider === "generic"
		) {
			return toolExecutions;
		}
		return toolExecutions.map((exec) => ({
			...exec,
			provider:
				(exec as McpServerExecution).provider === "generic"
					? nodeConfigProvider
					: (exec as McpServerExecution).provider,
		}));
	}, [toolExecutions, toolType, nodeConfigProvider]);

	// For MCP, show the actual tool name; otherwise use node name
	const displayTitle = mcpExecution?.tool
		? `${formatToolName(mcpExecution.tool)} - Execution Details`
		: `${nodeName || toolConfig.title} - Execution Details`;

	// Get the appropriate icon
	const HeaderIcon = providerVisuals?.icon || Icon;

	// Create gradient style for provider-specific colors (inline styles work with dynamic colors)
	const headerGradientStyle = providerVisuals
		? {
				background: `linear-gradient(to right, ${providerVisuals.color}, rgba(${providerVisuals.colorRgb}, 0.6))`,
			}
		: undefined;

	// Override theme accent with provider color for the entire panel
	const accentOverrideStyle =
		providerVisuals && !providerVisuals.color.startsWith("var(")
			? ({
					"--color-primary": providerVisuals.color,
					"--color-primary-rgb": providerVisuals.colorRgb,
				} as React.CSSProperties)
			: undefined;

	return (
		<div style={accentOverrideStyle}>
		<ExecutionModal onBackdropClick={onClose}>
			<ExecutionHeader
				gradientFrom={providerVisuals ? undefined : toolConfig.gradientFrom}
				gradientTo={providerVisuals ? undefined : toolConfig.gradientTo}
				gradientStyle={headerGradientStyle}
				icon={<HeaderIcon className="w-6 h-6 text-white" />}
				title={displayTitle}
				onClose={onClose}
				statusBar={
					<>
						<div className="flex items-center gap-2">
							{status === "loading" && (
								<Clock className="w-4 h-4 animate-spin" />
							)}
							{status === "success" && (
								<CheckCircle className="w-4 h-4 text-[#0DA931]" />
							)}
							{status === "error" && (
								<AlertCircle className="w-4 h-4 text-red-300" />
							)}
							{status === "pending" && (
								<Clock className="w-4 h-4 text-[color:var(--color-accent-light)]" />
							)}
							{status === "in_progress" && (
								<Clock className="w-4 h-4 animate-spin text-[color:var(--color-accent-light)]" />
							)}
							<span className="capitalize">
								{status === "loading"
									? "Loading..."
									: status === "success"
										? "Completed"
										: status === "error"
											? "Failed"
											: status === "in_progress"
												? "In Progress"
												: "Pending"}
							</span>
						</div>
						{toolExecutions.length > 0 && (
							<div className="flex items-center gap-2">
								<span className="text-sm">
									{toolExecutions.length} execution
									{toolExecutions.length !== 1 ? "s" : ""}
								</span>
							</div>
						)}
						{nodeExecution?.id &&
							nodeExecution.status !== "running" && (
								<NodeFeedbackButtons
									executionId={executionId}
									nodeExecutionId={nodeExecution.id}
								/>
							)}
					</>
				}
			/>

			{/* Content */}
			<div className="flex flex-col h-[calc(90vh-120px)]">
				{loading ? (
					<div className="flex-1 flex items-center justify-center">
						<div className="text-[color:var(--color-text-muted)]">
							<Clock className="w-8 h-8 animate-spin mx-auto mb-3" />
							<p>Loading execution data...</p>
						</div>
					</div>
				) : error ? (
					<div className="flex-1 flex items-center justify-center">
						<div className="text-center">
							<AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
							<p className="text-red-400 font-medium">
								Error Loading Execution
							</p>
							<p className="text-[color:var(--color-text-muted)] text-sm mt-2">
								{error}
							</p>
						</div>
					</div>
				) : status === "in_progress" && toolExecutions.length === 0 ? (
					<div className="flex-1 flex items-center justify-center">
						<div className="text-center text-[color:var(--color-text-muted)]">
							<Clock className="w-8 h-8 animate-spin mx-auto mb-3" />
							<p className="font-medium">Execution in progress</p>
							<p className="text-sm mt-1">Results will appear when the tool completes</p>
						</div>
					</div>
				) : (
					React.createElement(RendererClass as any, {
						executions: effectiveToolExecutions,
						selectedIndex: selectedExecutionIndex,
						onSelectIndex: setSelectedExecutionIndex,
						nodeExecution: nodeExecution,
					})
				)}
			</div>
		</ExecutionModal>
		</div>
	);
}
