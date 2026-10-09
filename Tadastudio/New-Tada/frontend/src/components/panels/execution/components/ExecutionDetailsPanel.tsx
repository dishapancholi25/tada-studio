import { Calendar, Clock, ExternalLink, Hash } from "lucide-react";
import type React from "react";
import type { NodeExecution } from "@/types/api";
import { usePhoenixConfig, usePhoenixProjectUrl } from "@/lib/phoenix-url";

interface ExecutionDetailsPanelProps {
	nodeExecution: NodeExecution;
}

const formatDuration = (seconds: number | null | undefined): string => {
	if (!seconds) return "N/A";
	if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
	if (seconds < 60) return `${seconds.toFixed(1)}s`;
	const minutes = Math.floor(seconds / 60);
	const remainingSeconds = seconds % 60;
	return `${minutes}m ${remainingSeconds.toFixed(1)}s`;
};

const formatDateTime = (dateString: string): { date: string; time: string } => {
	const date = new Date(dateString);
	const dateStr = date.toLocaleDateString("en-US", {
		month: "short",
		day: "numeric",
		year: "numeric",
	});
	const timeStr = date.toLocaleTimeString("en-US", {
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit",
		hour12: true,
	});
	return { date: dateStr, time: timeStr };
};

const STATUS_BADGE: Record<string, string> = {
	completed: "border-[#0DA931] bg-[#F1F8E9] text-[#0DA931]",
	failed: "border-red-400 bg-red-50 text-red-600",
	running: "border-orange-400 bg-orange-50 text-orange-600",
	default: "border-slate-300 bg-slate-50 text-slate-600",
};

const ExecutionDetailsPanel: React.FC<ExecutionDetailsPanelProps> = ({
	nodeExecution,
}) => {
	const badgeClass =
		STATUS_BADGE[nodeExecution.status ?? ""] || STATUS_BADGE.default;
	const phoenixConfig = usePhoenixConfig();
	const phoenixUrl = usePhoenixProjectUrl(
		phoenixConfig,
		phoenixConfig?.project_name ?? null,
	);

	return (
		<section className="h-full rounded-2xl border border-gray-200 bg-white shadow-sm">
			<div className="flex flex-wrap items-center gap-2 border-b border-gray-200 px-4 py-3">
				<div className="min-w-0 flex-1">
					<p className="text-[0.7rem] font-semibold capitalize text-gray-500">
						Execution Details
					</p>
					<p className="text-xs text-gray-600">
						{nodeExecution.node_type || "Node"}
					</p>
				</div>
				<span
					className={`rounded-full border px-3 py-1 text-[11px] font-medium capitalize ${badgeClass}`}
				>
					{nodeExecution.status || "pending"}
				</span>
				{phoenixUrl && (
					<a
						href={phoenixUrl}
						target="_blank"
						rel="noopener noreferrer"
						className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-white px-2.5 py-1 text-[11px] font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
						title="View in Phoenix"
					>
						Phoenix <ExternalLink className="h-3 w-3" />
					</a>
				)}
			</div>

			<div className="divide-y divide-gray-100">
				<div className="grid gap-3 px-4 py-5 text-sm text-gray-700">
					{nodeExecution.node_type !== "START" &&
						nodeExecution.node_type !== "END" && (
							<div>
								<p className="mb-2 text-[0.7rem] font-semibold capitalize text-gray-500">
									Duration
								</p>
								<div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-slate-50 px-3 py-2.5 shadow-sm">
									<Clock className="h-4 w-4 shrink-0 text-orange-600" />
									<p className="font-mono text-sm font-medium text-gray-900">
										{formatDuration(nodeExecution.duration_seconds)}
									</p>
								</div>
							</div>
						)}
					<div>
						<p className="mb-2 text-[0.7rem] font-semibold capitalize text-gray-500">
							Node Order
						</p>
						<div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-slate-50 px-3 py-2.5 shadow-sm">
							<Hash className="h-4 w-4 shrink-0 text-gray-500" />
							<p className="font-mono text-sm font-medium text-gray-900">
								{nodeExecution.execution_order ?? "—"}
							</p>
						</div>
					</div>
				</div>

				<div className="grid gap-3 px-4 py-5 text-xs text-gray-600">
					{nodeExecution.start_time && (
						<div>
							<p className="mb-2 text-[0.7rem] font-semibold capitalize text-gray-500">
								Start
							</p>
							<div className="flex items-center gap-2.5 rounded-xl border border-gray-200 bg-slate-50 px-3 py-2.5 shadow-sm">
								<Calendar className="h-4 w-4 shrink-0 text-gray-500" />
								<div className="flex flex-col gap-0.5">
									<p className="font-mono text-sm font-medium text-gray-900">
										{formatDateTime(nodeExecution.start_time).time}
									</p>
									<p className="font-mono text-xs text-gray-500">
										{formatDateTime(nodeExecution.start_time).date}
									</p>
								</div>
							</div>
						</div>
					)}
					{nodeExecution.end_time && (
						<div>
							<p className="mb-2 text-[0.7rem] font-semibold capitalize text-gray-500">
								End
							</p>
							<div className="flex items-center gap-2.5 rounded-xl border border-gray-200 bg-slate-50 px-3 py-2.5 shadow-sm">
								<Calendar className="h-4 w-4 shrink-0 text-gray-500" />
								<div className="flex flex-col gap-0.5">
									<p className="font-mono text-sm font-medium text-gray-900">
										{formatDateTime(nodeExecution.end_time).time}
									</p>
									<p className="font-mono text-xs text-gray-500">
										{formatDateTime(nodeExecution.end_time).date}
									</p>
								</div>
							</div>
						</div>
					)}
				</div>

				{(nodeExecution.input_tokens || nodeExecution.output_tokens) && (
					<div className="space-y-3 px-4 py-5">
						<p className="text-[0.7rem] font-semibold capitalize text-gray-500">
							Token Usage
						</p>
						<div className="grid gap-3">
							{nodeExecution.input_tokens && (
								<div className="rounded-xl border border-gray-200 bg-slate-50 px-3 py-2">
									<p className="text-[0.65rem] capitalize text-gray-500">
										Input
									</p>
									<p className="text-sm font-semibold text-gray-900">
										{nodeExecution.input_tokens.toLocaleString()}
									</p>
								</div>
							)}
							{nodeExecution.output_tokens && (
								<div className="rounded-xl border border-gray-200 bg-slate-50 px-3 py-2">
									<p className="text-[0.65rem] capitalize text-gray-500">
										Output
									</p>
									<p className="text-sm font-semibold text-gray-900">
										{nodeExecution.output_tokens.toLocaleString()}
									</p>
								</div>
							)}
							{nodeExecution.total_tokens && (
								<div className="rounded-xl border border-orange-300 bg-white px-3 py-2 text-gray-900">
									<p className="text-[0.65rem] capitalize text-gray-500">
										Total
									</p>
									<p className="text-base font-semibold text-gray-900">
										{nodeExecution.total_tokens.toLocaleString()}
									</p>
								</div>
							)}
						</div>
					</div>
				)}
			</div>
		</section>
	);
};

export default ExecutionDetailsPanel;
