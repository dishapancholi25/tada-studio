"use client";

import {
	CheckCircle,
	Globe,
	Loader2,
	Terminal,
	Trash2,
	Wifi,
	XCircle,
} from "lucide-react";
import React, { memo, useCallback, useMemo } from "react";
import { Handle, type NodeProps, Position } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
import McpLogo from "../icons/McpLogo";
import { getProviderVisuals } from "../icons/McpProviderIcons";
import EvalScoreBadge from "./shared/EvalScoreBadge";
import GuardrailIndicator from "./shared/GuardrailIndicator";
import InlineNameEditor from "./shared/InlineNameEditor";
import { getExecutionGradient } from "./shared/getExecutionGradient";
import {
	badgeBase,
	createBadge,
	createGradientFrame,
	createSelectionGlow,
	nodeBodyGradient,
	nodeColors,
	nodeFrameRadius,
	nodeHeaderRadius,
	nodeRadius,
	nodeShadows,
} from "./shared/nodeStyles";

interface MCPServerConfig {
	provider?: string;
	server_name?: string;
	connection_type?: string;
	command?: string;
	args?: string[];
	timeout_seconds?: number;
	max_retries?: number;
	retry_delay?: number;
	parent_agent_id?: string;
}

interface McpServerNodeData {
	id: string;
	name: string;
	label?: string;
	server_name?: string;
	connection_type?: string;
	isConfigured?: boolean;
	mcp_server_config?: MCPServerConfig;
	parent_agent_id?: string;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
	toolCallCount?: number;
}

interface McpServerNodeProps extends NodeProps {
	data: McpServerNodeData;
}

const McpServerNode = memo(({ data, selected, id }: McpServerNodeProps) => {
	const { deleteNode, updateNode } = useGraph();

	const serverName =
		data.mcp_server_config?.server_name ||
		data.server_name ||
		data.name ||
		data.label ||
		"MCP Server";
	const connectionType =
		data.mcp_server_config?.connection_type || data.connection_type || "stdio";
	const provider = data.mcp_server_config?.provider || "";
	const isOfficialProvider = provider !== "";
	const isConfigured = data.isConfigured !== false;

	const isExecuting = data.isExecuting || false;
	const executionStatus = data.executionStatus;
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
	const toolCallCount = data.toolCallCount || 0;

	// Get provider-specific visuals
	const providerVisuals = getProviderVisuals(provider);
	const ProviderIcon = providerVisuals.icon;

	// Teal theme for MCP nodes (memoized for performance)
	const gradientColors = useMemo(
		() => getExecutionGradient(executionStatus, "teal", isConfigured),
		[executionStatus, isConfigured],
	);

	// Connection type badge styles
	const getConnectionBadge = () => {
		if (connectionType.toLowerCase() === "http") {
			return {
				icon: Globe,
				badge: "HTTP",
				color: "text-[#0DA931]",
				bg: "bg-[#0DA931]/20",
				border: "border-[#0DA931]/30",
			};
		} else if (connectionType.toLowerCase() === "websocket") {
			return {
				icon: Wifi,
				badge: "WS",
				color: "text-purple-400",
				bg: "bg-purple-500/20",
				border: "border-purple-500/30",
			};
		}
		return {
			icon: Terminal,
			badge: "STDIO",
			color: "text-gray-400",
			bg: "bg-gray-500/20",
			border: "border-gray-500/30",
		};
	};

	const connBadge = getConnectionBadge();
	const ConnectionIcon = connBadge.icon;

	// Status icon for execution feedback
	const getStatusIcon = () => {
		if (isExecuting || executionStatus === "running") {
			return (
				<Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
			);
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

	// Custom save handler to update both name and mcp_server_config.server_name
	const handleNameSave = useCallback(
		async (nodeId: string, newName: string) => {
			// Update both the name field and mcp_server_config.server_name
			const updates: any = {
				name: newName,
				server_name: newName,
			};

			// Also update mcp_server_config if it exists
			if (data.mcp_server_config) {
				updates.mcp_server_config = {
					...data.mcp_server_config,
					server_name: newName,
				};
			}

			await updateNode(nodeId, updates);
		},
		[updateNode, data.mcp_server_config],
	);

	return (
		<div className="relative group">
			<EvalScoreBadge score={data.evalScore} />
			{/* Selection glow veneer */}
			{selected && (
				<div
					className={`pointer-events-none absolute -inset-[3px] ${nodeFrameRadius.standard} blur-xl opacity-60 transition-opacity`}
					style={createSelectionGlow(nodeColors.teal)}
				/>
			)}

			{/* Outer gradient frame (glass halo) */}
			<div
				className={`p-[1px] ${nodeFrameRadius.standard} transition-all duration-200 ${
					selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
				}`}
				style={createGradientFrame(nodeColors.teal)}
			>
				<div
					className={`
            relative min-w-[200px] max-w-[260px] ${nodeRadius.standard}
            ${nodeShadows.default}
            ${selected ? nodeShadows.selected : ""}
            transition-all duration-200
          `}
				>
					{/* Background gradient effect */}
					<div
						className={`hidden absolute inset-0 bg-gradient-to-br ${gradientColors.from} ${gradientColors.to} ${nodeRadius.standard} blur-md ${
							isExecuting || executionStatus === "running"
								? "opacity-70 animate-pulse"
								: "opacity-35"
						}`}
					/>

					{/* Main node container */}
					<div
						className={`relative overflow-hidden ${nodeBodyGradient} border border-slate-200 ${nodeRadius.standard} ${
							isExecuting || executionStatus === "running"
								? "animate-pulse"
								: ""
						}`}
					>
						{/* Header */}
						<div
							className={`relative z-10 flex items-center justify-between px-4 py-3 ${nodeHeaderRadius.standard} border-b`}
							style={{
								backgroundColor: `rgb(${provider ? providerVisuals.colorRgb : nodeColors.gray})`,
								borderColor: `rgba(${provider ? providerVisuals.colorRgb : nodeColors.gray}, 0.35)`,
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
									{provider ? (
										<ProviderIcon
											className="w-4 h-4 text-white"
										/>
									) : (
										<McpLogo
											className="text-white"
											size={16}
										/>
									)}
								</div>
								<span
									className="text-xs font-semibold capitalize text-white"
								>
									{provider ? providerVisuals.label : "MCP"}
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
						<div className="relative z-10 px-4 py-3">
							<InlineNameEditor
								nodeId={id}
								initialName={serverName}
								placeholder="MCP Server"
								className="text-sm font-semibold text-slate-900 mb-2 truncate"
								readOnly={isReadOnlyPreview}
								onSave={handleNameSave}
							/>

							{isConfigured ? (
								<div className="flex flex-wrap items-center gap-1.5">
									{isOfficialProvider ? (
										<div
											className={badgeBase}
											style={createBadge(providerVisuals.colorRgb)}
										>
											<ProviderIcon
												className="w-3 h-3"
												style={{ color: providerVisuals.color }}
											/>
											<span style={{ color: providerVisuals.color }}>
												{providerVisuals.label}
											</span>
										</div>
									) : (
										<div
											className={`${badgeBase} ${connBadge.bg} ${connBadge.border} ${connBadge.color}`}
										>
											<ConnectionIcon className="w-3 h-3" />
											<span>{connBadge.badge}</span>
										</div>
									)}
								</div>
							) : (
								<p className="text-xs text-amber-400/80 italic">
									Click to configure
								</p>
							)}
						</div>
					</div>

					{/* Handle - Only accepts connections from agents */}
					<Handle
						type="target"
						position={Position.Top}
						id="top"
						className="!w-3 !h-3 !border-2 !border-[color:var(--color-bg-secondary)] hover:!opacity-80 transition-all hover:!shadow-[0_0_8px_rgba(var(--color-primary-rgb),0.4)]"
						style={{
							backgroundColor: provider
								? providerVisuals.color
								: "var(--color-text-muted)",
						}}
						isConnectable={true}
					/>
				</div>
			</div>
		</div>
	);
});

McpServerNode.displayName = "McpServerNode";

export default McpServerNode;
