import {
	CheckCircle,
	Clock,
	Globe,
	Loader2,
	Lock,
	Plus,
	RefreshCw,
	Send,
	Trash2,
	XCircle,
} from "lucide-react";
import type React from "react";
import { memo, useCallback, useMemo } from "react";
import { Handle, type NodeProps, Position } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
import { useNodeOutgoingEdges } from "@/hooks/useNodeOutgoingEdges";
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

interface HttpRequestActionConfig {
	url_template?: string;
	method?: string;
	headers?: Record<string, string>;
	body_template?: string;
	auth_type?: string;
	auth_config?: Record<string, string>;
	timeout_seconds?: number;
	max_retries?: number;
	response_path?: string;
	success_status_codes?: number[];
}

interface HttpRequestActionNodeData {
	name: string;
	http_request_action_config?: HttpRequestActionConfig;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	executionDuration?: number;
	nexts?: string[];
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
}

const HttpRequestActionNode = memo(
	({ data, selected, id }: NodeProps<HttpRequestActionNodeData>) => {
		const { deleteNode } = useGraph();
		const outgoingEdges = useNodeOutgoingEdges(id);
		const hasConfiguration =
			data.http_request_action_config?.url_template &&
			data.http_request_action_config?.method;
		const isExecuting = data.isExecuting || false;
		const executionStatus = data.executionStatus;
		const executionDuration = data.executionDuration;
		const method = data.http_request_action_config?.method || "GET";
		const authType = data.http_request_action_config?.auth_type || "none";
		const maxRetries = data.http_request_action_config?.max_retries;
		const isReadOnlyPreview = Boolean(data.isReadOnlyPreview);

		const handleDeleteButtonClick = useCallback(
			(e: React.MouseEvent) => {
				e.stopPropagation();
				deleteNode(id).catch((err) => {
					console.error("Failed to delete node:", err);
				});
			},
			[deleteNode, id],
		);

		// Method color mapping
		const methodStyles = {
			GET: { text: "text-[#0DA931]", bg: "bg-[#0DA931]/20" },
			POST: {
				text: "text-[color:var(--color-text-muted)]",
				bg: "bg-[color:var(--color-text-muted)]/20",
			},
			PUT: {
				text: "text-[color:var(--color-accent)]",
				bg: "bg-[color:var(--color-accent)]/20",
			},
			DELETE: { text: "text-red-400", bg: "bg-red-500/20" },
			PATCH: { text: "text-purple-400", bg: "bg-purple-500/20" },
		};

		const methodStyle = methodStyles[method as keyof typeof methodStyles] || {
			text: "text-[color:var(--color-text-muted)]",
			bg: "bg-[color:var(--color-text-muted)]/20",
		};

		// Get status icon
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
					return <Send className="w-4 h-4 text-white" />;
			}
		};

		// Get gradient colors based on execution status (memoized for performance)
		const gradientColors = useMemo(
			() => getExecutionGradient(executionStatus, "emerald"),
			[executionStatus],
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
						style={createSelectionGlow(nodeColors.emerald)}
					/>
				)}

				{/* Outer gradient frame (glass halo) */}
				<div
					className={`p-[1px] ${nodeFrameRadius.standard} transition-all duration-200 ${
						selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
					}`}
					style={createGradientFrame(nodeColors.emerald)}
				>
					<div
						className={`
            relative min-w-[200px] max-w-[280px] ${nodeRadius.standard}
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
									backgroundColor: `rgb(${nodeColors.emerald})`,
									borderColor: `rgba(${nodeColors.emerald}, 0.35)`,
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
										<Globe className="w-4 h-4 text-white" />
									</div>
									<span className="text-xs font-semibold text-white capitalize">
										HTTP Request
									</span>
								</div>
								<GuardrailIndicator nodeId={id} />
								<div className="flex items-center gap-2 ml-3">
									{getStatusIcon()}
									{!isReadOnlyPreview && (
										<button
											onClick={handleDeleteButtonClick}
											className="p-1 rounded hover:bg-red-500/20 transition-colors"
											title="Delete"
										>
											<Trash2 className="w-3.5 h-3.5 text-white hover:text-slate-900" />
										</button>
									)}
								</div>
							</div>

							{/* Body */}
							<div className="px-4 py-3">
								<InlineNameEditor
									nodeId={id}
									initialName={data.name || "HTTP Request"}
									placeholder="HTTP Request"
									className="text-sm font-semibold text-slate-900 mb-2 truncate"
									readOnly={isReadOnlyPreview}
								/>

								{hasConfiguration ? (
									<div className="space-y-1.5">
										{/* Method Badge */}
										<div className="flex items-center gap-2">
											<div
												className={`px-2.5 py-1 rounded-full border text-[11px] font-medium ${methodStyle.bg} ${methodStyle.text}`}
												style={{ borderColor: "rgba(16, 185, 129, 0.35)" }}
											>
												{method}
											</div>
											{authType !== "none" && (
												<div className="flex items-center gap-1">
													<Lock className="w-3 h-3 text-emerald-400" />
													<span className="text-xs text-[color:var(--color-text-muted)]">
														{authType}
													</span>
												</div>
											)}
										</div>

										{/* URL */}
										{data.http_request_action_config?.url_template && (
											<div className="flex items-center gap-2 text-xs">
												<span className="text-[color:var(--color-text-muted)]">
													URL:
												</span>
												<span className="text-white font-mono truncate">
													{data.http_request_action_config.url_template
														.split("//")[1]
														?.split("/")[0] || "Configured"}
												</span>
											</div>
										)}

										{/* Retry config */}
										{maxRetries && maxRetries > 0 && (
											<div className="flex items-center gap-1 text-xs text-[color:var(--color-text-muted)]">
												<RefreshCw className="w-3 h-3 text-emerald-400" />
												<span>{maxRetries} retries</span>
											</div>
										)}
									</div>
								) : (
									<p className="text-xs text-[color:var(--color-text-muted)] italic">
										Not configured
									</p>
								)}

								{/* Execution duration */}
								{executionStatus === "completed" && executionDuration && (
									<div className="mt-2 pt-2 border-t border-emerald-500/20">
										<div className="flex items-center gap-1 text-xs text-white">
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
									<Plus className="w-4 h-4 text-[color:var(--color-text-muted)] group-hover:text-emerald-400 transition-colors" />
								</button>
							</>
						)}
					</div>
				</div>
			</div>
		);
	},
);

HttpRequestActionNode.displayName = "HttpRequestActionNode";

export default HttpRequestActionNode;
