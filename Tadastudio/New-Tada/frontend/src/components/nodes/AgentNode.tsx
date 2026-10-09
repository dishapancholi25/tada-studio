"use client";

import {
	AlertCircle,
	BookMarked,
	XCircle,
	Bot,
	Brain,
	CheckCircle,
	Clock,
	Database,
	Eye,
	Layers,
	Loader2,
	Plus,
	Settings,
	Shield,
	Trash2,
	Users,
	Zap,
} from "lucide-react";
import { memo, useCallback } from "react";
import { Handle, type NodeProps, Position } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
import { useNodeGuardrailStatus } from "@/hooks/useNodeGuardrailStatus";
import { useNodeOutgoingEdges } from "@/hooks/useNodeOutgoingEdges";
import { formatExecutionDuration } from "@/lib/executionGraphUtils";
import type { AgentNodeData } from "@/types/agent";
import EvalScoreBadge from "./shared/EvalScoreBadge";
import InlineNameEditor from "./shared/InlineNameEditor";
import {
	createGradientFrame,
	delegationTargetHandleStyles,
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

interface ExtendedAgentNodeData extends AgentNodeData {
	hasOutgoingConnections?: boolean;
	nexts?: string[];
	is_sub_agent?: boolean;
	parent_agent_id?: string;
	delegation_description?: string;
	is_orchestrator?: boolean;
	isReadOnlyPreview?: boolean;
	isAgentTemplatePreview?: boolean;
	evalScore?: number | null;
}

interface AgentNodeProps extends NodeProps {
	data: ExtendedAgentNodeData;
}

function AgentNode({ data, selected, id }: AgentNodeProps) {
	const { deleteNode, currentGraph } = useGraph();
	const isExecuting = data.isExecuting || false;
	const executionStatus = data.executionStatus;
	const executionDuration = data.executionDuration;
	const isSubAgent = data.isSubAgent || data.is_sub_agent || false;
	const isOrchestrator = data.isOrchestrator || data.is_orchestrator || data.agent_config?.is_orchestrator || false;
	const isReadOnlyPreview = Boolean(data.isReadOnlyPreview);
	const isAgentTemplatePreview = Boolean(data.isAgentTemplatePreview);

	// Subscribe to store edges so plus icon reacts to local optimistic updates
	const outgoingEdges = useNodeOutgoingEdges(id);
	const hasOutgoingWorkflowConnection = outgoingEdges.some(
		(edge) =>
			edge.source === id &&
			(!edge.sourceHandle || edge.sourceHandle === "workflow"),
	);

	// Keep bottom handle and plus icon positions in sync
	const bottomHandlePositions = {
		tools: "25%",
		delegation: "50%",
		workflow: "75%",
	} as const;
	// Spacing and curvature for the bottom connectors
	const connectorGap = 44; // px from node bottom to plus button center
	const connectorBend = 10; // px horizontal deviation of the curve
	const connectorWidth = connectorBend * 2 + 4; // svg width per connector

	// Agent features
	const memoryEnabled = data.agent_config?.memory_enabled || false;
	const hasStructuredOutput =
		(data.agent_config?.structured_outputs || []).length > 0;
	const tools = data.agent_config?.tools || [];
	const hasTools = tools.length > 0;
	const promptDisplay = data.agent_config?.system_prompt || data.description?.trim() || data.prompt || "";
	const hasLlmConfig = !!data.agent_config?.llm_config;
	const reviewEnabled = !!data.agent_config?.review_config?.review_enabled;
	const { hasGuardrails } = useNodeGuardrailStatus(currentGraph?.workflow_id, id);

	// Get model name and format it for display
	const modelName = data.agent_config?.llm_config?.model_name;
	const getModelDisplayName = (model: string) => {
		const modelMap: Record<string, string> = {
			"gpt-4o-latest": "GPT-4o",
			"gpt-4o": "GPT-4o",
			"gpt-4-turbo": "GPT-4 Turbo",
			"gpt-4": "GPT-4",
			"gpt-3.5-turbo": "GPT-3.5",
			"claude-3-opus": "Claude 3 Opus",
			"claude-3-sonnet": "Claude 3 Sonnet",
			"claude-3-haiku": "Claude 3 Haiku",
			"claude-2.1": "Claude 2.1",
			"claude-2": "Claude 2",
		};
		return modelMap[model] || model;
	};

	const getStatusIcon = () => {
		if (isExecuting || executionStatus === "running") {
			return (
				<Loader2 className="w-4 h-4 text-white animate-spin" />
			);
		}

		switch (executionStatus) {
			case "completed":
				return (
					<CheckCircle className="w-4 h-4 text-white" />
				);
			case "failed":
				return <XCircle className="w-4 h-4 text-white" />;
			case "pending":
				return <Clock className="w-4 h-4 text-white" />;
			case "skipped":
				return (
					<Clock className="w-4 h-4 text-slate-700" />
				);
			default:
				return null;
		}
	};

	const handleCreateSubAgentClick = useCallback(() => {
		const event = new CustomEvent("openCreateSubAgentDialog", {
			detail: { parentAgentId: id, parentAgentName: data.name },
		});
		window.dispatchEvent(event);
	}, [id, data.name]);

	const handleCreateSubWorkflowClick = useCallback(() => {
		const event = new CustomEvent("openCreateSubWorkflowDialog", {
			detail: { parentAgentId: id, parentAgentName: data.name },
		});
		window.dispatchEvent(event);
	}, [id, data.name]);

	const handlePublishAgentClick = useCallback(() => {
		const event = new CustomEvent("openPublishAgentDialog", {
			detail: { agentNodeId: id, agentName: data.name, agentDescription: data.description },
		});
		window.dispatchEvent(event);
	}, [id, data.name, data.description]);

	const handleSettingsClick = useCallback(() => {
		const event = new CustomEvent("openNodeSettings", {
			detail: { nodeId: id },
		});
		window.dispatchEvent(event);
	}, [id]);

	// Click handlers with stopPropagation
	const handleSettingsButtonClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			handleSettingsClick();
		},
		[handleSettingsClick],
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

	const handleCreateSubAgentButtonClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			handleCreateSubAgentClick();
		},
		[handleCreateSubAgentClick],
	);

	const handleCreateSubWorkflowButtonClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			handleCreateSubWorkflowClick();
		},
		[handleCreateSubWorkflowClick],
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

	const handleOpenToolSelectionClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			const event = new CustomEvent("openToolSelectionDialog", {
				detail: { parentAgentId: id, parentAgentName: data.name },
			});
			window.dispatchEvent(event);
		},
		[id, data.name],
	);

	const handlePublishAgentButtonClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			handlePublishAgentClick();
		},
		[handlePublishAgentClick],
	);

	// Get the appropriate color RGB for glow effects
	const glowColorRgb = isSubAgent
		? nodeColors.purple
		: "var(--color-primary-rgb)";

	// Match the “building block” card colors from design:
	// - Regular Agent: orange header
	// - Sub-Agent: purple header
	const headerRgb = isSubAgent ? nodeColors.purple : nodeColors.orange;

	return (
		<div
			data-tutorial="agent-node"
			className="relative group"
			style={{ marginBottom: (!isSubAgent || isOrchestrator) ? "50px" : "0", overflow: "visible" }}
		>
			<EvalScoreBadge score={data.evalScore} />

			{/* Outer frame (subtle) */}
			<div
				className={`p-[1px] ${nodeFrameRadius.standard} transition-all duration-200 ${
					selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
				}`}
				style={selected ? createGradientFrame(glowColorRgb) : undefined}
			>
				<div
					className={`
            relative min-w-[280px] max-w-[350px] ${nodeRadius.standard}
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
						}`}
					>
						{/* Header (solid) */}
						<div
							className={`flex items-center justify-between px-4 py-2.5 ${nodeHeaderRadius.standard} border-b border-black/10`}
							style={{ backgroundColor: `rgb(${headerRgb})` }}
						>
							<div className="flex items-center gap-2.5">
								<div className="h-7 w-7 rounded-lg flex items-center justify-center bg-white/20">
									{isSubAgent ? (
										<Layers className="w-4 h-4 text-white" />
									) : (
										<Bot className="w-4 h-4 text-white" />
									)}
								</div>
								<span className="text-xs font-semibold capitalize text-white">
									{isSubAgent ? "Sub-Agent" : "Agent"}
								</span>
							</div>

							<div className="flex items-center gap-2">
								{getStatusIcon()}

								{/* Error indicator for missing LLM config (not shown in preview mode) */}
								{!executionStatus && !hasLlmConfig && !isReadOnlyPreview && (
									<div className="relative group/error">
										<AlertCircle className="w-4 h-4 text-white" />
										<div className="absolute right-0 top-6 opacity-0 group-hover/error:opacity-100 transition-opacity pointer-events-none z-50">
											<div className="bg-white text-slate-900 text-xs px-3 py-2 rounded shadow-lg whitespace-nowrap border border-red-500/50">
												LLM configuration required
											</div>
										</div>
									</div>
								)}

								{/* Action buttons */}
								{!isReadOnlyPreview && (
									<>
										<button
											onClick={handlePublishAgentButtonClick}
											className="p-1 rounded hover:bg-slate-100 transition-colors"
											title="Publish to Library"
										>
											<BookMarked className="w-3.5 h-3.5 text-white hover:text-slate-900" />
										</button>
										<button
											data-tutorial="agent-settings-btn"
											onClick={handleSettingsButtonClick}
											className="p-1 rounded hover:bg-slate-100 transition-colors"
											title="Settings"
										>
											<Settings
												className="w-3.5 h-3.5 text-white hover:text-slate-900"
											/>
										</button>

										<button
											onClick={handleDeleteButtonClick}
											className="p-1 rounded hover:bg-slate-100 transition-colors"
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
								initialName={data.name || "Agent"}
								placeholder="Agent"
								className="text-sm font-semibold text-slate-900 mb-2 truncate"
								readOnly={isReadOnlyPreview}
							/>

							{/* Feature indicators */}
							<div className="flex flex-wrap items-center gap-1.5 mb-2">
								{/* Model indicator - only show when configured */}
								{modelName && (
									<div
										className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium"
										style={{
											backgroundColor: "rgba(249, 115, 22, 0.10)",
											borderColor: "rgba(249, 115, 22, 0.25)",
										}}
										title={`Model: ${modelName}`}
									>
										<Bot className="w-3 h-3 text-orange-700" />
										<span className="text-orange-800">
											{getModelDisplayName(modelName)}
										</span>
									</div>
								)}
								{isOrchestrator && (
									<div
										className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium"
										style={{
											backgroundColor: "rgba(168, 85, 247, 0.12)",
											borderColor: "rgba(168, 85, 247, 0.35)",
										}}
									>
										<Users className="w-3 h-3 text-purple-800" />
										<span className="text-purple-900">Orchestrator</span>
									</div>
								)}
								{memoryEnabled && (
									<div
										className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium"
										style={{
											backgroundColor: "rgba(139, 92, 246, 0.12)",
											borderColor: "rgba(139, 92, 246, 0.35)",
										}}
										title="Memory Enabled"
									>
										<Database className="w-3 h-3 text-violet-800" />
										<span className="text-violet-900">Memory</span>
									</div>
								)}
								{hasStructuredOutput && (
									<div
										className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium"
										style={{
											backgroundColor: "rgba(13, 169, 49, 0.12)",
											borderColor: "rgba(13, 169, 49, 0.35)",
										}}
										title="Structured Output"
									>
										<Brain className="w-3 h-3 text-[#0DA931]" />
										<span className="text-[#0DA931]">Structured</span>
									</div>
								)}
								{hasTools && (
									<div
										className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium"
										style={{
											backgroundColor: "rgba(249, 115, 22, 0.12)",
											borderColor: "rgba(249, 115, 22, 0.35)",
										}}
										title={`${tools.length} tool(s)`}
									>
										<Zap className="w-3 h-3 text-orange-800" />
										<span className="text-orange-900">{tools.length}</span>
									</div>
								)}
								{hasGuardrails && (
									<div
										className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium"
										style={{
											backgroundColor: "rgba(234, 179, 8, 0.12)",
											borderColor: "rgba(234, 179, 8, 0.35)",
										}}
										title="Guardrails active"
									>
										<Shield className="w-3 h-3 text-yellow-800" />
										<span className="text-yellow-900">Guardrails</span>
									</div>
								)}
								{reviewEnabled && (
									<div
										className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium"
										style={{
											backgroundColor: "rgba(56, 189, 248, 0.12)",
											borderColor: "rgba(56, 189, 248, 0.35)",
										}}
										title="Output review enabled"
									>
										<Eye className="w-3 h-3 text-sky-800" />
										<span className="text-sky-900">Review</span>
									</div>
								)}
							</div>

							{/* Prompt preview */}
							{promptDisplay && (
								<div className="mt-2 p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs">
									<div className="text-slate-600 font-mono line-clamp-3 leading-relaxed">
										{promptDisplay}
									</div>
								</div>
							)}

							{/* Execution duration */}
							{executionStatus === "completed" && executionDuration && (
								<div
									className={
										isSubAgent
											? "mt-2 pt-2 border-t border-[color:var(--color-secondary)]/20"
											: "mt-2 pt-2 border-t border-[color:var(--color-primary)]/20"
									}
								>
									<div className="flex items-center gap-1 text-xs text-slate-800">
										<Clock className="w-3 h-3" />
										<span>{formatExecutionDuration(executionDuration)}</span>
									</div>
								</div>
							)}
						</div>
					</div>

					{/* Handles */}
					{/* Left target handle — kept for all agents so React Flow can anchor
					    pre-existing workflow edges; invisible and non-interactive for sub-agents
					    to avoid showing a second connection point in the drag-connect UX. */}
					<Handle
						type="target"
						position={Position.Left}
						className={handleStyles}
						style={{
							pointerEvents: (isAgentTemplatePreview || isSubAgent) ? "none" : undefined,
							...(isSubAgent ? { opacity: 0 } : {}),
						}}
					/>
					{/* Top target handle — delegation connections for all agents.
					    Sub-agents: full-size visible handle; regular agents: smaller dashed handle that reveals on hover. */}
					<Handle
						type="target"
						position={Position.Top}
						id="top"
						className={isSubAgent ? handleStyles : delegationTargetHandleStyles}
						style={{
							pointerEvents: isAgentTemplatePreview ? "none" : undefined,
						}}
					/>
					<Handle
						type="source"
						position={Position.Right}
						className={handleStyles}
						style={{
							pointerEvents: isAgentTemplatePreview ? "none" : undefined,
						}}
					/>
					{/* Two separate bottom handles for tools and sub-agents */}
					<Handle
						type="source"
						position={Position.Bottom}
						id="tools"
						className={handleStyles}
						style={{ left: (isSubAgent && !isOrchestrator) ? "50%" : bottomHandlePositions.tools }}
					/>
					{(!isSubAgent || isOrchestrator) && (
						<>
							<Handle
								type="source"
								position={Position.Bottom}
								id="delegation"
								className={handleStyles}
								style={{ left: bottomHandlePositions.delegation }}
							/>
							<Handle
								type="source"
								position={Position.Bottom}
								id="workflow"
								className={handleStyles}
								style={{ left: bottomHandlePositions.workflow }}
							/>
						</>
					)}

					{/* (Connectors moved to the unified plus layer below for consistency) */}

					{/* Add Connection Plus Icon - only show if no outgoing workflow connections */}
					{!isReadOnlyPreview &&
						!hasOutgoingWorkflowConnection &&
						!isSubAgent && (
							<>
								<svg
									className="absolute pointer-events-none"
									style={{
										width: "100px",
										height: "40px",
										left: "calc(100% + 6px)",
										top: "50%",
										transform: "translateY(-50%)",
									}}
								>
									<path
										d="M 0 20 C 36 6, 60 34, 84 20"
										stroke="#0f172a"
										strokeWidth="1"
										fill="none"
										opacity="0.25"
									/>
								</svg>

								<button
									data-tutorial="agent-add-next-btn"
									onClick={handleOpenNodePaletteClick}
									className={`absolute ${plusButtonBase} ${plusButtonShadow} group`}
									style={{
										left: "calc(100% + 84px)",
										top: "50%",
										transform: "translateY(-50%)",
									}}
									title="Add next node"
								>
									<Plus className="w-5 h-5 text-slate-600 transition-all duration-200 group-hover:rotate-90 group-hover:text-slate-900" />
								</button>
							</>
						)}

					{/* Unified connector + plus layer (consistent geometry) */}
					{!isReadOnlyPreview && (
						<div
							className="absolute left-0 right-0 z-50 pointer-events-none"
							style={{ top: "100%", height: connectorGap + 28 }}
						>
							{/* Tools connector – straight vertical line */}
							<svg
								className="absolute -translate-x-1/2"
								style={{
									left: (isSubAgent && !isOrchestrator) ? "50%" : bottomHandlePositions.tools,
									top: 0,
									width: connectorWidth,
									height: connectorGap,
								}}
								viewBox={`0 0 ${connectorWidth} ${connectorGap}`}
							>
								{(() => {
									const cx = Math.floor(connectorWidth / 2);
									return (
										<path
											d={`M ${cx} 0 L ${cx} ${connectorGap}`}
											stroke="#0f172a"
											strokeWidth="1"
											fill="none"
											opacity="0.4"
										/>
									);
								})()}
							</svg>
							{/* Delegation connector – straight vertical line */}
							{(!isSubAgent || isOrchestrator) && (
								<svg
									className="absolute -translate-x-1/2"
									style={{
										left: bottomHandlePositions.delegation,
										top: 0,
										width: connectorWidth,
										height: connectorGap,
									}}
									viewBox={`0 0 ${connectorWidth} ${connectorGap}`}
								>
									{(() => {
										const cx = Math.floor(connectorWidth / 2);
										return (
											<path
												d={`M ${cx} 0 L ${cx} ${connectorGap}`}
												stroke="#0f172a"
												strokeWidth="1"
												fill="none"
												opacity="0.4"
											/>
										);
									})()}
								</svg>
							)}
							{/* Tools Plus Icon (centered at 30%) */}
							<div
								className="absolute -translate-x-1/2 pointer-events-auto group"
								style={{
									left: (isSubAgent && !isOrchestrator) ? "50%" : bottomHandlePositions.tools,
									top: connectorGap,
								}}
							>
								<button
									onClick={handleOpenToolSelectionClick}
									className={`${plusButtonBase} ${plusButtonShadow} group`}
									title="Add tools"
								>
									<Plus className="w-4 h-4 text-slate-600 transition-colors group-hover:text-slate-900" />
								</button>
								<div className="absolute left-1/2 -translate-x-1/2 -bottom-7 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
									<div className="bg-white text-slate-500 text-[10px] font-medium px-2.5 py-1 rounded-lg shadow-lg whitespace-nowrap border border-slate-200">
										Tools
									</div>
								</div>
							</div>

							{/* Sub-Agents Plus Icon (centered at 50%) - for regular agents and sub-agent orchestrators */}
							{(!isSubAgent || isOrchestrator) && (
								<>
									<div
										className="absolute -translate-x-1/2 pointer-events-auto group"
										style={{
											left: bottomHandlePositions.delegation,
											top: connectorGap,
										}}
									>
										<button
											onClick={handleCreateSubAgentButtonClick}
											className={`${plusButtonBase} ${plusButtonShadow} group`}
											title="Create sub-agent"
										>
											<Plus className="w-4 h-4 text-slate-600 transition-colors group-hover:text-slate-900" />
										</button>
										<div className="absolute left-1/2 -translate-x-1/2 -bottom-7 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
											<div className="bg-white text-slate-500 text-[10px] font-medium px-2.5 py-1 rounded-lg shadow-lg whitespace-nowrap border border-slate-200">
												Sub-Agents
											</div>
										</div>
									</div>

									{/* Workflow connector – straight vertical line */}
									<svg
										className="absolute -translate-x-1/2"
										style={{
											left: bottomHandlePositions.workflow,
											top: 0,
											width: connectorWidth,
											height: connectorGap,
										}}
										viewBox={`0 0 ${connectorWidth} ${connectorGap}`}
									>
										{(() => {
											const cx = Math.floor(connectorWidth / 2);
											return (
												<path
													d={`M ${cx} 0 L ${cx} ${connectorGap}`}
													stroke="#0f172a"
													strokeWidth="1"
													fill="none"
													opacity="0.4"
												/>
											);
										})()}
									</svg>

									{/* Sub-Workflows Plus Icon (centered at 75%) - only for regular agents */}
									<div
										className="absolute -translate-x-1/2 pointer-events-auto group"
										style={{
											left: bottomHandlePositions.workflow,
											top: connectorGap,
										}}
									>
										<button
											onClick={handleCreateSubWorkflowButtonClick}
											className={`${plusButtonBase} ${plusButtonShadow} group`}
											title="Create sub-workflow"
										>
											<Plus className="w-4 h-4 text-slate-600 transition-colors group-hover:text-slate-900" />
										</button>
										<div className="absolute left-1/2 -translate-x-1/2 -bottom-7 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
											<div className="bg-white text-slate-500 text-[10px] font-medium px-2.5 py-1 rounded-lg shadow-lg whitespace-nowrap border border-slate-200">
												Workflows
											</div>
										</div>
									</div>
								</>
							)}
						</div>
					)}
				</div>
			</div>
		</div>
	);
}

export default memo(AgentNode);
