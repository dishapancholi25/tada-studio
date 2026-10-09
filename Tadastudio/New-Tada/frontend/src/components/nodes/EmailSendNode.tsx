import {
	CheckCircle,
	Clock,
	Loader2,
	Mail,
	Plus,
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

interface EmailSendNodeData {
	name: string;
	email_send_config?: any;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	executionDuration?: number;
	nexts?: string[];
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
}

const EmailSendNode = memo(
	({ data, selected, id }: NodeProps<EmailSendNodeData>) => {
		const { deleteNode } = useGraph();
		const outgoingEdges = useNodeOutgoingEdges(id);
		const isExecuting = data.isExecuting || false;
		const executionStatus = data.executionStatus;
		const hasConfiguration =
			data.email_send_config &&
			(data.email_send_config.to_address ||
				data.email_send_config.to_source_mode !== "static");
		const isReadOnlyPreview = Boolean(data.isReadOnlyPreview);

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
					return null;
			}
		};

		// Get gradient colors based on execution status (memoized for performance)
		const gradientColors = useMemo(
			() => getExecutionGradient(executionStatus, "emerald"),
			[executionStatus],
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
            relative min-w-[200px] max-w-[250px] ${nodeRadius.standard}
            ${nodeShadows.default}
            ${selected ? nodeShadows.selected : ""}
            transition-all duration-200
          `}
					>
						{/* Background gradient effect */}
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
										<Mail className="w-4 h-4 text-white" />
									</div>
									<span className="text-xs font-semibold text-white capitalize">
										Email Send
									</span>
								</div>
								<GuardrailIndicator nodeId={id} />
								<div className="flex items-center gap-2">
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
									initialName={data.name || "Email Send"}
									placeholder="Email Send"
									className="text-sm font-semibold text-slate-900 mb-1 truncate"
									readOnly={isReadOnlyPreview}
								/>

								{hasConfiguration ? (
									<div className="space-y-1">
										{data.email_send_config.to_address &&
										data.email_send_config.to_source_mode === "static" ? (
											<p className="text-xs text-[color:var(--color-text-muted)] truncate">
												To: {data.email_send_config.to_address}
											</p>
										) : (
											<p className="text-xs text-emerald-400">
												Dynamic recipient
											</p>
										)}
										{data.email_send_config.subject &&
											data.email_send_config.subject_source_mode ===
												"static" && (
												<p className="text-xs text-[color:var(--color-text-muted)] truncate">
													{data.email_send_config.subject}
												</p>
											)}
									</div>
								) : (
									<p className="text-xs text-[color:var(--color-text-muted)] italic">
										Not configured
									</p>
								)}

								{/* Execution info */}
								{executionStatus === "completed" && data.executionDuration && (
									<div className="mt-2 pt-2 border-t border-emerald-500/20">
										<div className="flex items-center gap-1 text-xs text-white">
											<Clock className="w-3 h-3" />
											<span>
												Sent in {(data.executionDuration / 1000).toFixed(2)}s
											</span>
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

						{/* Add Node Button with connector path - only show if no outgoing connections */}
						{!isReadOnlyPreview &&
							outgoingEdges.length === 0 &&
							!isExecuting && (
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

EmailSendNode.displayName = "EmailSendNode";

export default EmailSendNode;
