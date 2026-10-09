"use client";

import { CheckCircle, Loader2, Mail, Trash2, XCircle } from "lucide-react";
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

interface EmailFieldConfig {
	mode: "ai" | "static";
	static_value?: string;
	ai_description?: string;
}

interface EmailSendToolConfig {
	to_address?: EmailFieldConfig;
	subject?: EmailFieldConfig;
	body?: EmailFieldConfig;
}

interface EmailSendToolNodeData {
	id: string;
	name: string;
	email_send_tool_config?: EmailSendToolConfig;
	parent_agent_id?: string;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	nexts?: string[];
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
	toolCallCount?: number;
}

interface EmailSendToolNodeProps extends NodeProps {
	data: EmailSendToolNodeData;
}

function EmailSendToolNode({ data, selected, id }: EmailSendToolNodeProps) {
	const { deleteNode } = useGraph();
	const config = data.email_send_tool_config;

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

	// Count static-mode fields (AI mode is default, so we count static overrides)
	const staticFieldCount = [
		config?.to_address?.mode === "static",
		config?.subject?.mode === "static",
		config?.body?.mode === "static",
	].filter(Boolean).length;

	// AI fields = 3 - static fields (defaults to AI mode)
	const aiFieldCount = 3 - staticFieldCount;

	// Emerald theme for email - tool nodes are always valid (memoized for performance)
	const gradientColors = useMemo(
		() => getExecutionGradient(executionStatus, "emerald"),
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
					style={createSelectionGlow(nodeColors.emerald)}
				/>
			)}

			{/* Outer gradient frame (glass halo) */}
			<div
				className={`p-[1px] ${nodeFrameRadius.compact} transition-all duration-200 ${
					selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
				}`}
				style={createGradientFrame(nodeColors.emerald)}
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
								backgroundColor: `rgb(${nodeColors.emerald})`,
								borderColor: `rgba(${nodeColors.emerald}, 0.3)`,
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
									<Mail className="w-3 h-3 text-white" />
								</div>
								<span className="text-[10px] font-semibold text-white capitalize">
									Email Send
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
						</div>

						{/* Body */}
						<div className="px-3 py-2">
							<InlineNameEditor
								nodeId={id}
								initialName={data.name || "Email Send"}
								placeholder="Email Send"
								className="text-xs font-semibold text-slate-900 mb-1 truncate"
								readOnly={isReadOnlyPreview}
							/>

							<div className="space-y-0.5">
								{/* Always show AI field count since AI mode is default */}
								{aiFieldCount > 0 && (
									<div className="text-[10px] text-emerald-400">
										{aiFieldCount} AI-populated field
										{aiFieldCount !== 1 ? "s" : ""}
									</div>
								)}
								{/* Show static overrides if any */}
								{config?.to_address?.mode === "static" &&
									config.to_address.static_value && (
										<div className="text-[10px] text-[color:var(--color-text-muted)] truncate">
											To: {config.to_address.static_value}
										</div>
									)}
								{config?.subject?.mode === "static" &&
									config.subject.static_value && (
										<div className="text-[10px] text-[color:var(--color-text-muted)] truncate">
											{config.subject.static_value}
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
						className="!w-3 !h-3 !bg-white !border-2 !border-[color:var(--color-border)]/80 hover:!border-emerald-500 hover:!shadow-[0_0_8px_rgba(16,185,129,0.4)] transition-all"
						isConnectable={true}
					/>
				</div>
			</div>
		</div>
	);
}

export default memo(EmailSendToolNode);
