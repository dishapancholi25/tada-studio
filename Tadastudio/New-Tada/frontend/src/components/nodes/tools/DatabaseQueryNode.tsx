"use client";

import {
	AlertCircle,
	CheckCircle,
	Clock,
	Database,
	Loader2,
	Plus,
	Shield,
	Table,
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

interface DatabaseQueryConfig {
	connection_id?: string;
	table_name?: string;
	table_names?: string[];
	allowed_operations?: string[];
	max_rows?: number;
	timeout_seconds?: number;
	enable_read_only?: boolean;
	return_format?: string;
	include_schema?: boolean;
	parent_agent_id?: string;
}

interface DatabaseQueryNodeData {
	id: string;
	name: string;
	database_query_config?: DatabaseQueryConfig;
	parent_agent_id?: string;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	nexts?: string[];
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
	toolCallCount?: number;
}

interface DatabaseQueryNodeProps extends NodeProps {
	data: DatabaseQueryNodeData;
}

function DatabaseQueryNode({ data, selected, id }: DatabaseQueryNodeProps) {
	const { deleteNode } = useGraph();

	const hasConnection = data.database_query_config?.connection_id
		? true
		: false;
	const tableName = data.database_query_config?.table_name || "";
	const tableNames = data.database_query_config?.table_names || [];
	const tableCount = tableNames.length;
	const displayTableInfo =
		tableCount > 1
			? `${tableCount} tables`
			: tableCount === 1
				? tableNames[0]
				: tableName;
	const isReadOnly = data.database_query_config?.enable_read_only || false;
	const maxRows = data.database_query_config?.max_rows;
	const operations =
		data.database_query_config?.allowed_operations?.length || 0;

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

	// Purple theme for database (memoized for performance)
	const gradientColors = useMemo(
		() => getExecutionGradient(executionStatus, "purple", hasConnection),
		[executionStatus, hasConnection],
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
					style={createSelectionGlow(nodeColors.purple)}
				/>
			)}

			{/* Outer gradient frame (glass halo) */}
			<div
				className={`p-[1px] ${nodeFrameRadius.compact} transition-all duration-200 ${
					selected ? "scale-[1.01]" : "hover:-translate-y-0.5"
				}`}
				style={createGradientFrame(nodeColors.purple)}
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
								backgroundColor: `rgb(${nodeColors.purple})`,
								borderColor: `rgba(${nodeColors.purple}, 0.3)`,
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
									<Database className="w-3 h-3 text-white" />
								</div>
								<span className="text-[10px] font-semibold text-white capitalize">
									DB Query
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
							{/* Error indicator for missing connection (only show when no execution status) */}
							{!executionStatus && !isExecuting && !hasConnection && (
								<div className="relative group/error">
									<AlertCircle className="w-4 h-4 text-white" />
									<div className="absolute right-0 top-6 opacity-0 group-hover/error:opacity-100 transition-opacity pointer-events-none z-50">
										<div className="bg-red-50 text-red-700 text-xs px-3 py-2 rounded-lg shadow-lg whitespace-nowrap border border-red-200">
											Database connection required
										</div>
									</div>
								</div>
							)}
						</div>

						{/* Body */}
						<div className="px-3 py-2">
							<InlineNameEditor
								nodeId={id}
								initialName={data.name || "Database Query"}
								placeholder="Database Query"
								className="text-xs font-semibold text-slate-900 mb-1 truncate"
								readOnly={isReadOnlyPreview}
							/>

							{hasConnection ? (
								<div className="space-y-0.5">
									{(tableName || tableNames.length > 0) && (
										<div className="flex items-center gap-1 text-[10px]">
											<Table className="w-3 h-3 text-purple-400" />
											<span className="text-[color:var(--color-text-muted)] truncate">
												{displayTableInfo}
											</span>
										</div>
									)}
									<div className="flex items-center gap-2">
										{isReadOnly && (
											<div className="flex items-center gap-0.5 text-[10px]">
												<Shield className="w-3 h-3 text-purple-400" />
												<span className="text-[color:var(--color-text-muted)]">
													Read-only
												</span>
											</div>
										)}
										{maxRows && (
											<div className="flex items-center gap-0.5 text-[10px]">
												<span className="text-[color:var(--color-text-muted)]">
													Max: {maxRows}
												</span>
											</div>
										)}
									</div>
									{operations > 0 && (
										<div className="text-[10px] text-[color:var(--color-text-muted)]">
											{operations} operation{operations !== 1 ? "s" : ""}{" "}
											allowed
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
						className="!w-3 !h-3 !bg-white !border-2 !border-[color:var(--color-border)]/80 hover:!border-purple-500 hover:!shadow-[0_0_8px_rgba(168,85,247,0.4)] transition-all"
						isConnectable={true}
					/>
				</div>
			</div>
		</div>
	);
}

export default memo(DatabaseQueryNode);
