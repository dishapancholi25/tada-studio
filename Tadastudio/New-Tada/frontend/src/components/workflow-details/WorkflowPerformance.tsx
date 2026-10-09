"use client";

import { useWorkflowPerformance } from "@/hooks/workflow-metrics/useWorkflowPerformance";
import Card from "./shared/Card";
import { ErrorState } from "./shared/WidgetStates";
import SectionHeader from "./shared/SectionHeader";
import StatCard from "./shared/StatCard";

export default function WorkflowPerformance({ workflowId }: { workflowId: string }) {
	const { data, loading, error, refetch } = useWorkflowPerformance(workflowId);

	if (loading) {
		return (
			<div className="space-y-4">
				{/* Section header skeleton */}
				<div className="flex items-start justify-between gap-4">
					<div className="space-y-1.5">
						<div className="h-4 w-72 rounded bg-[#F0F0F0]" />
						<div className="h-3 w-96 rounded bg-[#F0F0F0]" />
					</div>
					<div className="h-8 w-32 rounded bg-[#F0F0F0]" />
				</div>
				<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
					{Array.from({ length: 4 }).map((_, i) => (
						<StatCard key={i} label="" value="" loading />
					))}
				</div>
			</div>
		);
	}

	if (error || !data) {
		return (
			<Card>
				<ErrorState message={error ?? "Failed to load performance"} onRetry={refetch} />
			</Card>
		);
	}

	return (
		<div className="space-y-4">
			{/* Section header: title on left, coverage on right — matches Figma */}
			<SectionHeader
				title="Workflow Performance & Response Time (Latency)"
				subtitle="Execution timing, latency percentiles, and data coverage for this workflow."
				action={
					data.slaTarget ? (
						<div className="flex flex-col items-end gap-0.5">
							<span className="flex items-center gap-1.5 text-[15px] font-bold text-[#16A34A]">
								<span className="h-2 w-2 rounded-full bg-[#16A34A]" />
								{data.slaTarget}
							</span>
							{data.highlights.map((h) => (
								<span key={h} className="text-[11px] text-[#8A8A8A]">{h}</span>
							))}
						</div>
					) : undefined
				}
			/>

			{/* Latency KPI cards — unchanged */}
			<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
				{data.kpis.map((kpi) => (
					<StatCard
						key={kpi.id}
						label={kpi.label}
						value={kpi.valueSeconds.toFixed(2)}
						unit="s"
						caption={kpi.caption}
						tone={kpi.tone}
						tinted
					/>
				))}
			</div>
		</div>
	);
}
