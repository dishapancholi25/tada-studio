"use client";

import { Info } from "lucide-react";
import { useQualityMetrics } from "@/hooks/workflow-metrics/useQualityMetrics";
import Tooltip from "@/components/ui/Tooltip";
import Card from "./shared/Card";
import { ErrorState } from "./shared/WidgetStates";

/** Three stacked quality cards — Groundedness, Hallucination Rate, Faithfulness.
 *
 * Replaces the former "Documents Ingested" chart. Cards stay rendered even when
 * a value is unavailable, showing "--" in place of the number. */
export default function QualityMetrics({ workflowId }: { workflowId: string }) {
	const { data, loading, error, refetch } = useQualityMetrics(workflowId);

	if (loading) {
		return (
			<div className="flex h-full flex-col gap-4">
				{Array.from({ length: 3 }).map((_, i) => (
					<Card key={i} className="flex flex-1 flex-col justify-center">
						<div className="mb-2 h-3 w-28 rounded bg-[#F0F0F0]" />
						<div className="h-3 w-40 rounded bg-[#F0F0F0]" />
					</Card>
				))}
			</div>
		);
	}

	if (error || !data) {
		return (
			<Card className="h-full">
				<ErrorState message={error ?? "Failed to load quality metrics"} onRetry={refetch} />
			</Card>
		);
	}

	return (
		<div className="flex h-full flex-col gap-4">
			{data.metrics.map((m) => {
				const hasValue = m.value !== null && m.value !== undefined;
				return (
					<Card key={m.id} className="flex flex-1 items-center justify-between gap-4">
						<div className="min-w-0">
							<span className="flex items-center gap-2 text-[14px] font-semibold text-[#333333]">
								{m.label}
								<Tooltip content={m.tooltip ?? m.description}>
									<span className="inline-flex">
										<Info className="h-3.5 w-3.5 shrink-0 text-[#CCCCCC]" />
									</span>
								</Tooltip>
							</span>
							<p className="mt-1 text-[12px] text-[#8A8A8A]">{m.description}</p>
						</div>
						<div className="flex shrink-0 flex-col items-end">
							<span
								className="text-[26px] font-bold leading-none"
								style={{ color: hasValue ? "#FF5E00" : "#D0D0D0" }}
							>
								{hasValue ? `${m.value}${m.unit ?? "%"}` : "--"}
							</span>
							{m.threshold && (
								<span className="mt-1.5 text-[11px] text-[#9A9A9A]">{m.threshold}</span>
							)}
						</div>
					</Card>
				);
			})}
		</div>
	);
}
