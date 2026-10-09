"use client";

import {
	AlertCircle,
	CheckCircle,
	Database,
	Loader2,
	Shield,
	Table,
	Trash2,
	XCircle,
} from "lucide-react";
import { memo, useCallback, useMemo } from "react";
import { Handle, type NodeProps, Position } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
import EvalScoreBadge from "./shared/EvalScoreBadge";
import GuardrailIndicator from "./shared/GuardrailIndicator";
import InlineNameEditor from "./shared/InlineNameEditor";
import { getExecutionGradient } from "./shared/getExecutionGradient";
import {
	createGradientFrame,
	createSelectionGlow,
	nodeBodyGradient,
	nodeColors,
	nodeFrameRadius,
	nodeHeaderRadius,
	nodeRadius,
	nodeShadows,
} from "./shared/nodeStyles";

interface DatabaseQueryActionConfig {
	connection_id?: string;
	table_name?: string;
	table_names?: string[];
	allowed_operations?: string[];
	max_rows?: number;
	timeout_seconds?: number;
	enable_read_only?: boolean;
	return_format?: string;
	include_schema?: boolean;
}

interface DatabaseQueryActionNodeData {
	id: string;
	name: string;
	database_query_action_config?: DatabaseQueryActionConfig;
	isExecuting?: boolean;
	executionStatus?: "running" | "completed" | "failed" | "pending" | "skipped";
	nexts?: string[];
	isReadOnlyPreview?: boolean;
	evalScore?: number | null;
}

interface DatabaseQueryActionNodeProps extends NodeProps {
	data: DatabaseQueryActionNodeData;
}

function DatabaseQueryActionNode({
	data,
	selected,
	id,
}: DatabaseQueryActionNodeProps) {
	const { deleteNode } = useGraph();

	const cfg = data.database_query_action_config;
	const hasConnection = Boolean(cfg?.connection_id);
	const tableName = cfg?.table_name || "";
	const tableNames = cfg?.table_names || [];
	const tableCount = tableNames.length;
	const displayTableInfo =
		tableCount > 1
			? `${tableCount} tables`
			: tableCount === 1
				? tableNames[0]
				: tableName;
	const isReadOnly = cfg?.enable_read_only || false;
	const maxRows = cfg?.max_rows;

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

	// Emerald theme for action node — distinct from purple tool node
	const gradientColors = useMemo(
		() => getExecutionGradient(executionStatus, "emerald", hasConnection),
		[executionStatus, hasConnection],
	);

	const getStatusIcon = () => {
		if (isExecuting || executionStatus === "running") {
			return <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />;
		}
		switch (executionStatus) {
			case "completed":
				return <CheckCircle className="w-3.5 h-3.5 text-white" />;
			case "failed":
				return <XCircle className="w-3.5 h-3.5 text-white" />;
			default:
				return null;
		}
	};

	return (
		<div className="relative group">
			<EvalScoreBadge score={data.evalScore} />

			{selected && (
				<div
					className={`pointer-events-none absolute -inset-[3px] ${nodeFrameRadius.compact} blur-xl opacity-60 transition-opacity`}
					style={createSelectionGlow(nodeColors.emerald)}
				/>
			)}

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
					<div
						className={`hidden absolute inset-0 bg-gradient-to-br ${gradientColors.from} ${gradientColors.to} ${nodeRadius.compact} blur-md ${
							isExecuting || executionStatus === "running"
								? "opacity-70 animate-pulse"
								: "opacity-35"
						}`}
					/>

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
									DB Action
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
								initialName={data.name || "DB Query Action"}
								placeholder="DB Query Action"
								className="text-xs font-semibold text-slate-900 mb-1 truncate"
								readOnly={isReadOnlyPreview}
							/>

							{hasConnection ? (
								<div className="space-y-0.5">
									{(tableName || tableNames.length > 0) && (
										<div className="flex items-center gap-1 text-[10px]">
											<Table className="w-3 h-3 text-emerald-400" />
											<span className="text-[color:var(--color-text-muted)] truncate">
												{displayTableInfo}
											</span>
										</div>
									)}
									{isReadOnly && (
										<div className="flex items-center gap-0.5 text-[10px]">
											<Shield className="w-3 h-3 text-emerald-400" />
											<span className="text-[color:var(--color-text-muted)]">
												Read-only
											</span>
										</div>
									)}
									{maxRows && (
										<div className="text-[10px] text-[color:var(--color-text-muted)]">
											Max: {maxRows} rows
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

					{/* Sequential node: left target + right source */}
					<Handle
						type="target"
						position={Position.Left}
						id="left"
						className="!w-3 !h-3 !bg-white !border-2 !border-[color:var(--color-border)]/80 hover:!border-emerald-500 transition-all"
						isConnectable={true}
					/>
					<Handle
						type="source"
						position={Position.Right}
						id="right"
						className="!w-3 !h-3 !bg-white !border-2 !border-[color:var(--color-border)]/80 hover:!border-emerald-500 transition-all"
						isConnectable={true}
					/>
				</div>
			</div>
		</div>
	);
}

export default memo(DatabaseQueryActionNode);
