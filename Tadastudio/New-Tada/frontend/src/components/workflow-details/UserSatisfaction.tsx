"use client";

import { useUserSatisfaction } from "@/hooks/workflow-metrics/useUserSatisfaction";
import ChartContainer from "./shared/ChartContainer";

const TONE_TEXT: Record<string, string> = {
	positive: "text-[#1B5E20]",
	negative: "text-[#B00020]",
	neutral: "text-[#F57C00]",
};

const PLACEHOLDER_METRICS = [
	{ id: "positive-ph", label: "Positive Feedback", tone: "positive", value: null as number | null },
	{ id: "negative-ph", label: "Negative Feedback", tone: "negative", value: null as number | null },
];

/** Shared metric card list — used by both full and contentOnly modes. */
function MetricCards({
	metrics,
	hasMetrics,
	summary,
}: {
	metrics: typeof PLACEHOLDER_METRICS;
	hasMetrics: boolean;
	summary?: string;
}) {
	return (
		<>
			<div className="space-y-3">
				{metrics.map((m) => {
					const colorClass = TONE_TEXT[m.tone] ?? TONE_TEXT.neutral;
					const isPlaceholder = m.value === null;
					return (
						<div
							key={m.id}
							className="flex min-h-[100px] flex-col justify-between rounded-xl border border-[#E0E0E0] bg-white p-5 shadow-[0px_4px_8px_rgba(0,0,0,0.06)]"
						>
							<p className="text-[11px] font-medium uppercase tracking-wide text-[#8A8A8A]">
								{m.label}
							</p>
							<div>
								<p
									className={`text-[32px] font-bold leading-none ${
										isPlaceholder ? "text-[#D0D0D0]" : colorClass
									}`}
								>
									{isPlaceholder ? "—" : `${m.value}%`}
								</p>
								{!isPlaceholder && (m as { description?: string }).description && (
									<p className="mt-1 text-[12px] text-[#8A8A8A]">{(m as { description?: string }).description}</p>
								)}
							</div>
						</div>
					);
				})}
			</div>
			{!hasMetrics && (
				<p className="mt-3 text-[12px] text-[#B0B0B0]">
					No satisfaction data yet — will populate once users interact with this workflow.
				</p>
			)}
			{hasMetrics && summary && (
				<p className="mt-3 text-[12px] leading-relaxed text-[#8A8A8A]">{summary}</p>
			)}
		</>
	);
}

export default function UserSatisfaction({
	workflowId,
	bare = false,
	contentOnly = false,
}: {
	workflowId: string;
	bare?: boolean;
	/** When true, renders only the metric cards with no header — use when the
	 *  parent is responsible for rendering the section title above both columns. */
	contentOnly?: boolean;
}) {
	const { data, loading, error, refetch } = useUserSatisfaction(workflowId);

	const hasMetrics = data && data.metrics.length > 0;
	const metrics = hasMetrics ? data.metrics : PLACEHOLDER_METRICS;

	// contentOnly: just the cards, no ChartContainer/header — caller owns the header.
	if (contentOnly) {
		if (loading) {
			return (
				<div className="space-y-3">
					{PLACEHOLDER_METRICS.map((_, i) => (
						// biome-ignore lint/suspicious/noArrayIndexKey: static placeholder
						<div key={i} className="h-[100px] animate-pulse rounded-xl border border-[#E0E0E0] bg-[#F5F5F5]" />
					))}
				</div>
			);
		}
		return <MetricCards metrics={metrics} hasMetrics={!!hasMetrics} summary={data?.summary} />;
	}

	return (
		<ChartContainer
			bare={bare}
			title="User Satisfaction"
			titleAccent
			subtitle="User experience and satisfaction across workflows"
			tooltip="Aggregated positive and negative feedback ratios."
			loading={loading}
			error={error}
			onRetry={refetch}
			skeletonHeight={200}
		>
			<MetricCards metrics={metrics} hasMetrics={!!hasMetrics} summary={data?.summary} />
		</ChartContainer>
	);
}
