"use client";

import {
	AlertCircle,
	CheckCircle,
	Globe,
	Link,
	Loader2,
	Lock,
	RefreshCw,
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

interface HttpRequestConfig {
	url_template?: string;
	method?: string;
	headers?: Record<string, string>;
	auth_type?: string;
	auth_config?: Record<string, string>;
	request_body_template?: string;
	timeout_seconds?: number;
	max_retries?: number;
	retry_delay?: number;
	response_format?: string;
	error_handling?: string;
	follow_redirects?: boolean;
	verify_ssl?: boolean;
	extract_path?: string;
	success_status_codes?: number[];
	parent_agent_id?: string;
}

interface HttpRequestNodeData {
	id: string;
	name: string;
	http_request_config?: HttpRequestConfig;
	parent_agent_id?: string;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
	toolCallCount?: number;
}

interface HttpRequestNodeProps extends NodeProps {
	data: HttpRequestNodeData;
}

function HttpRequestNode({ data, selected, id }: HttpRequestNodeProps) {
	const { deleteNode } = useGraph();

	const hasUrl = data.http_request_config?.url_template ? true : false;
	const method = data.http_request_config?.method || "GET";
	const authType = data.http_request_config?.auth_type || "none";
	const maxRetries = data.http_request_config?.max_retries;
	const timeout = data.http_request_config?.timeout_seconds;

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

	// Method color mapping with backgrounds
	const methodStyles = {
		GET: {
			text: "text-[#0DA931]",
			bg: "bg-[#0DA931]/20",
			border: "border-[#0DA931]/30",
		},
		POST: {
			text: "text-[color:var(--color-accent)]",
			bg: "bg-[color:var(--color-accent)]/20",
			border: "border-[color:var(--color-border)]/30",
		},
		PUT: {
			text: "text-[color:var(--color-accent)]",
			bg: "bg-[color:var(--color-accent)]/20",
			border: "border-[color:var(--color-border)]/35",
		},
		DELETE: {
			text: "text-red-400",
			bg: "bg-red-500/20",
			border: "border-red-500/30",
		},
		PATCH: {
			text: "text-purple-400",
			bg: "bg-purple-500/20",
			border: "border-purple-500/30",
		},
	};

	const methodStyle = methodStyles[method as keyof typeof methodStyles] || {
		text: "text-[color:var(--color-text-muted)]",
		bg: "bg-[color:var(--color-text-muted)]/20",
		border: "border-[color:var(--color-text-muted)]/30",
	};

	// Green/emerald theme for HTTP requests (memoized for performance)
	const gradientColors = useMemo(
		() => getExecutionGradient(executionStatus, "emerald", hasUrl),
		[executionStatus, hasUrl],
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
									<Globe className="w-3 h-3 text-white" />
								</div>
								<span className="text-[10px] font-semibold text-white capitalize">
									HTTP Request
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
							{/* Error indicator for missing URL config (only show when no execution status) */}
							{!executionStatus && !isExecuting && !hasUrl && (
								<div className="relative group/error">
									<AlertCircle className="w-4 h-4 text-white" />
									<div className="absolute right-0 top-6 opacity-0 group-hover/error:opacity-100 transition-opacity pointer-events-none z-50">
										<div className="bg-red-50 text-red-700 text-xs px-3 py-2 rounded-lg shadow-lg whitespace-nowrap border border-red-200">
											URL configuration required
										</div>
									</div>
								</div>
							)}
						</div>

						{/* Body */}
						<div className="px-3 py-2">
							<InlineNameEditor
								nodeId={id}
								initialName={data.name || "HTTP Request"}
								placeholder="HTTP Request"
								className="text-xs font-semibold text-slate-900 mb-1 truncate"
								readOnly={isReadOnlyPreview}
							/>

							{hasUrl ? (
								<div className="space-y-0.5">
									<div className="flex items-center gap-1.5">
										<div
											className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${methodStyle.bg} ${methodStyle.border} border ${methodStyle.text}`}
										>
											{method}
										</div>
										{authType !== "none" && (
											<div className="flex items-center gap-0.5 text-[10px]">
												<Lock className="w-3 h-3 text-emerald-400" />
												<span className="text-[color:var(--color-text-muted)]">
													{authType}
												</span>
											</div>
										)}
									</div>
									<div className="flex items-center gap-2 text-[10px] text-[color:var(--color-text-muted)]">
										{maxRetries && maxRetries > 0 && (
											<div className="flex items-center gap-0.5">
												<RefreshCw className="w-3 h-3 text-emerald-400" />
												<span>{maxRetries} retries</span>
											</div>
										)}
										{timeout && <span>{timeout}s timeout</span>}
									</div>
									{data.http_request_config?.url_template && (
										<div className="flex items-center gap-0.5 text-[10px]">
											<Link className="w-3 h-3 text-emerald-400" />
											<span className="text-[color:var(--color-text-muted)] truncate max-w-[120px]">
												{data.http_request_config.url_template
													.split("//")[1]
													?.split("/")[0] || "URL configured"}
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
						className="!w-3 !h-3 !bg-white !border-2 !border-[color:var(--color-border)]/80 hover:!border-emerald-500 hover:!shadow-[0_0_8px_rgba(16,185,129,0.4)] transition-all"
						isConnectable={true}
					/>
				</div>
			</div>
		</div>
	);
}

export default memo(HttpRequestNode);
