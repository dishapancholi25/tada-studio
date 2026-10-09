"use client";

import { Activity, FileText, MessageSquare } from "lucide-react";
import type { ReactNode } from "react";
import { useWorkflowSummary } from "@/hooks/workflow-metrics/useWorkflowSummary";
import { ErrorState } from "./shared/WidgetStates";
import StatCard from "./shared/StatCard";

const ICONS: Record<string, ReactNode> = {
	"active-sessions": <Activity className="h-4 w-4" />,
	"query-responses": <MessageSquare className="h-4 w-4" />,
	"documents-ingested": <FileText className="h-4 w-4" />,
};

export default function SummaryCards({ workflowId }: { workflowId: string }) {
	const { data, loading, error, refetch } = useWorkflowSummary(workflowId);

	if (loading) {
		return (
			<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
				{Array.from({ length: 3 }).map((_, i) => (
					<StatCard key={i} label="" value="" loading />
				))}
			</div>
		);
	}

	if (error || !data) {
		return <ErrorState message={error ?? "Failed to load summary"} onRetry={refetch} />;
	}

	return (
		<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{data.kpis.map((kpi) => (
				<StatCard
					key={kpi.id}
					label={kpi.label}
					value={kpi.value.toLocaleString()}
					unit={kpi.unit}
					delta={kpi.delta}
					icon={ICONS[kpi.id]}
				/>
			))}
		</div>
	);
}
