import { AlertCircle, CheckCircle, Clock, Play } from "lucide-react";
import type React from "react";
import { memo } from "react";
import NodeFeedbackButtons from "../shared/NodeFeedbackButtons";
import { formatDuration, getStatusStyle, type NodeExecution } from "./types";

interface NodeExecutionRowProps {
	nodeExecution: NodeExecution;
	executionId?: string;
}

const StatusIcon = ({ status }: { status: string }) => {
	const style = getStatusStyle(status);
	const iconClass = `w-4 h-4 ${style.iconClass}`;

	switch (status) {
		case "completed":
			return <CheckCircle className={iconClass} />;
		case "failed":
			return <AlertCircle className={iconClass} />;
		case "running":
			return <Play className={iconClass} />;
		default:
			return <Clock className={iconClass} />;
	}
};

const NodeExecutionRow = memo(function NodeExecutionRow({
	nodeExecution,
	executionId,
}: NodeExecutionRowProps) {
	const statusStyle = getStatusStyle(nodeExecution.status);

	return (
		<div
			className="rounded-xl border border-slate-200
				bg-white p-4
				flex items-center justify-between
				transition-all duration-200
				hover:border-orange-400
				hover:bg-white"
		>
			<div className="flex items-center gap-3">
				<StatusIcon status={nodeExecution.status} />
				<div>
					<div className="flex items-center gap-2">
						<span className="text-sm font-medium text-slate-900">
							{nodeExecution.node_name}
						</span>
						<span
							className="px-2 py-0.5 rounded-md text-[10px] font-mono
							bg-white text-orange-700 border border-slate-200"
						>
							{nodeExecution.node_type}
						</span>
					</div>
					<p className="text-xs font-mono text-slate-500 mt-0.5">
						Order: {nodeExecution.execution_order} • Duration:{" "}
						{formatDuration(nodeExecution.duration_seconds)}
					</p>
				</div>
			</div>

			<div className="flex items-center gap-2">
				{executionId &&
					nodeExecution.status !== "running" && (
						<NodeFeedbackButtons
							executionId={executionId}
							nodeExecutionId={nodeExecution.id}
						/>
					)}
				<span
					className={`px-3 py-1 rounded-full text-[11px] font-medium border ${statusStyle.badgeClass}`}
				>
					{nodeExecution.status}
				</span>
			</div>
		</div>
	);
});

export default NodeExecutionRow;
