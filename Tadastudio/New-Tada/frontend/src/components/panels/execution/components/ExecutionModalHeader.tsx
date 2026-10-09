import {
	AlertCircle,
	CheckCircle,
	Clock,
	FileText,
	RefreshCw,
	X,
} from "lucide-react";
import type React from "react";
import type { NodeExecution } from "@/types/api";
import NodeFeedbackButtons from "../../../shared/NodeFeedbackButtons";

interface ExecutionModalHeaderProps {
	nodeExecution: NodeExecution | null;
	nodeName: string;
	nodeId: string;
	executionId?: string;
	onClose: () => void;
}

type StatusConfig = {
	label: string;
	Icon: typeof CheckCircle;
	iconClass: string;
	pillClass: string;
};

const STATUS_CONFIG: Record<string, StatusConfig> = {
	completed: {
		label: "Completed",
		Icon: CheckCircle,
		iconClass: "text-emerald-600",
		pillClass: "border-emerald-200 bg-white text-emerald-800",
	},
	failed: {
		label: "Failed",
		Icon: AlertCircle,
		iconClass: "text-red-600",
		pillClass: "border-red-200 bg-white text-red-800",
	},
	running: {
		label: "Running",
		Icon: RefreshCw,
		iconClass: "text-orange-600 animate-spin",
		pillClass: "border-orange-300 bg-white text-orange-800",
	},
	default: {
		label: "Queued",
		Icon: Clock,
		iconClass: "text-slate-600",
		pillClass: "border-gray-200 bg-white text-slate-800",
	},
};

const ExecutionModalHeader: React.FC<ExecutionModalHeaderProps> = ({
	nodeExecution,
	nodeName,
	nodeId,
	executionId,
	onClose,
}) => {
	const statusKey = nodeExecution?.status ?? "default";
	const status = STATUS_CONFIG[statusKey] || STATUS_CONFIG.default;
	const StatusIcon = status.Icon;

	return (
		<div className="flex-none border-b border-gray-200 bg-white">
			<div className="flex flex-wrap items-start justify-between gap-4 px-6 pt-5 pb-4">
				<div className="flex min-w-0 items-start gap-3">
					<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
						<FileText className="h-5 w-5 text-orange-600" aria-hidden />
					</div>
					<div className="min-w-0">
						<p className="text-xs font-semibold capitalize tracking-wide text-gray-500">
							Node Execution
						</p>
						<h2 className="text-lg font-semibold tracking-tight text-gray-900">
							{nodeName}
						</h2>
						<p className="text-xs text-gray-500">
							Node ID:{" "}
							<span className="font-mono text-gray-800">{nodeId}</span>
						</p>
						<div
							className={`mt-2 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${status.pillClass}`}
						>
							<StatusIcon className={`h-3.5 w-3.5 shrink-0 ${status.iconClass}`} />
							{status.label}
						</div>
					</div>
				</div>
				<div className="ml-auto flex shrink-0 items-center gap-2">
					{executionId &&
						nodeExecution?.id &&
						nodeExecution.status !== "running" && (
							<NodeFeedbackButtons
								executionId={executionId}
								nodeExecutionId={nodeExecution.id}
							/>
						)}
					<button
						type="button"
						onClick={onClose}
						className="rounded-lg border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
						aria-label="Close node execution panel"
					>
						<X className="h-4 w-4" />
					</button>
				</div>
			</div>
		</div>
	);
};

export default ExecutionModalHeader;
