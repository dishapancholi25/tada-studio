import { AlertCircle, CheckCircle, Clock } from "lucide-react";
import type React from "react";
import { useCallback } from "react";
import type { NodeExecution } from "@/types/api";

interface ExecutionSelectorProps {
	executions: NodeExecution[];
	selectedIndex: number;
	onSelectExecution: (index: number) => void;
	currentExecution: NodeExecution;
}

const formatDuration = (seconds: number | null | undefined): string => {
	if (!seconds) return "N/A";
	if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
	if (seconds < 60) return `${seconds.toFixed(1)}s`;
	const minutes = Math.floor(seconds / 60);
	const remainingSeconds = seconds % 60;
	return `${minutes}m ${remainingSeconds.toFixed(1)}s`;
};

const STATUS_STYLES: Record<
	string,
	{ icon: React.ReactNode; textClass: string }
> = {
	completed: {
		icon: <CheckCircle className="h-3.5 w-3.5 text-emerald-600" />,
		textClass: "text-emerald-700",
	},
	failed: {
		icon: <AlertCircle className="h-3.5 w-3.5 text-red-600" />,
		textClass: "text-red-700",
	},
	running: {
		icon: (
			<Clock className="h-3.5 w-3.5 animate-spin text-orange-600" />
		),
		textClass: "text-orange-800",
	},
	default: {
		icon: <Clock className="h-3.5 w-3.5 text-slate-500" />,
		textClass: "text-slate-700",
	},
};

const ExecutionSelector: React.FC<ExecutionSelectorProps> = ({
	executions,
	selectedIndex,
	onSelectExecution,
	currentExecution,
}) => {
	const createSelectExecutionHandler = useCallback(
		(index: number) => () => {
			onSelectExecution(index);
		},
		[onSelectExecution],
	);

	if (executions.length <= 1) return null;

	const renderStatus = (status?: string) => {
		const statusKey = status ?? "default";
		const styles = STATUS_STYLES[statusKey] || STATUS_STYLES.default;
		return (
			<div
				className={`flex items-center gap-1.5 text-[11px] font-medium capitalize ${styles.textClass}`}
			>
				{styles.icon}
				{status || "pending"}
			</div>
		);
	};

	return (
		<section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
			<div className="mb-4 flex flex-wrap items-center justify-between gap-3">
				<div>
					<p className="text-[0.65rem] capitalize text-gray-500">
						Execution History
					</p>
					<p className="text-base font-semibold text-gray-900">
						Select a prior run
					</p>
				</div>
				<span className="inline-flex items-center gap-2 rounded-full border border-orange-300 bg-white px-3 py-1 text-xs font-medium text-orange-800">
					{executions.length} executions
				</span>
			</div>

			<div className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
				{executions.map((exec, index) => {
					const isActive = selectedIndex === index;
					return (
						<button
							key={exec.id || index}
							type="button"
							onClick={createSelectExecutionHandler(index)}
							className={`group rounded-2xl border px-4 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40 ${
								isActive
									? "border-orange-500 bg-white shadow-sm"
									: "border-gray-200 bg-white hover:border-orange-400 hover:bg-slate-50"
							}`}
						>
							<div className="flex items-center justify-between text-sm text-gray-900">
								<span className="font-semibold">Execution #{index + 1}</span>
								{exec.duration_seconds && (
									<span className="text-gray-500">
										{formatDuration(exec.duration_seconds)}
									</span>
								)}
							</div>
							<div className="mt-1 flex items-center justify-between text-xs text-gray-600">
								{exec.start_time ? (
									<span>{new Date(exec.start_time).toLocaleTimeString()}</span>
								) : (
									<span>Pending</span>
								)}
								{exec.execution_order !== undefined && (
									<span className="font-mono text-gray-500">
										Order #{exec.execution_order}
									</span>
								)}
							</div>
							<div className="mt-2">{renderStatus(exec.status)}</div>
						</button>
					);
				})}
			</div>

			{currentExecution && (
				<div className="mt-5 grid gap-3 rounded-2xl border border-gray-200 bg-slate-50 p-4 text-xs text-gray-700">
					<div className="flex flex-wrap items-center justify-between gap-2">
						<span className="text-[0.7rem] capitalize text-gray-500">
							Active Execution
						</span>
						{renderStatus(currentExecution.status)}
					</div>
					<div className="flex flex-wrap gap-4 text-sm text-gray-800">
						{currentExecution.duration_seconds && (
							<span className="text-gray-600">
								Duration:{" "}
								<span className="font-medium text-gray-900">
									{formatDuration(currentExecution.duration_seconds)}
								</span>
							</span>
						)}
						{currentExecution.input_tokens && (
							<span className="text-gray-600">
								Input tokens:{" "}
								<span className="font-medium text-gray-900">
									{currentExecution.input_tokens.toLocaleString()}
								</span>
							</span>
						)}
						{currentExecution.output_tokens && (
							<span className="text-gray-600">
								Output tokens:{" "}
								<span className="font-medium text-gray-900">
									{currentExecution.output_tokens.toLocaleString()}
								</span>
							</span>
						)}
					</div>
				</div>
			)}
		</section>
	);
};

export default ExecutionSelector;
