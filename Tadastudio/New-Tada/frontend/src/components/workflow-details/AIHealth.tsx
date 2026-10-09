"use client";

import { Info } from "lucide-react";
import { useAIHealth } from "@/hooks/workflow-metrics/useAIHealth";
import Card from "./shared/Card";
import SectionHeader from "./shared/SectionHeader";
import { ErrorState, SkeletonBlock } from "./shared/WidgetStates";

/** Qualitative band for the composite score. */
function scoreBand(score: number): string {
	if (score >= 90) return "Excellent";
	if (score >= 75) return "Good";
	if (score >= 60) return "Fair";
	return "Needs Attention";
}

/** Semantic text colour that matches the quality band. */
function scoreBandColor(score: number): string {
	if (score >= 75) return "text-[#16A34A]";
	if (score >= 60) return "text-[#B26A00]";
	return "text-[#FF5E00]";
}

export default function AIHealth({ workflowId }: { workflowId: string }) {
	const { data, loading, error, refetch } = useAIHealth(workflowId);
	// isEmpty only when the entire API call fails to return any metrics at all.
	const isEmpty = !loading && !error && !data;

	if (loading) {
		return (
			<div className="space-y-4">
				<div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
					{Array.from({ length: 4 }).map((_, i) => (
						<div key={i} className="rounded-xl border border-[#E0E0E0] bg-white p-6 shadow-sm">
							<div className="mb-4 h-4 w-24 rounded bg-[#F0F0F0]" />
							<div className="mb-3 h-8 w-16 rounded bg-[#F0F0F0]" />
							<div className="mb-3 h-2.5 w-full rounded-full bg-[#F0F0F0]" />
							<div className="h-3 w-32 rounded bg-[#F0F0F0]" />
						</div>
					))}
				</div>
			</div>
		);
	}

	if (error || isEmpty) {
		return (
			<Card>
				<ErrorState
					message={error ?? "No AI health data available"}
					onRetry={refetch}
				/>
			</Card>
		);
	}

	return (
		<div className="space-y-4">
			{/* Header with overall score */}
				<SectionHeader
					title="AI Health"
					subtitle="Composite quality signal across 4 evaluation dimensions"
				/>

			{/* Responsive grid of KPI cards */}
			{data && (
				<div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
					{data.metrics.map((m) => {
						const isPercentage = (m.unit ?? "%") === "%";
						const insufficient = m.status === "insufficient_data";
						return (
							<div
								key={m.id}
								className="flex flex-col rounded-xl border border-[#E0E0E0] bg-white p-6 shadow-sm"
							>
								{/* Card header: title + info icon */}
								<div className="mb-4 flex items-start justify-between gap-2">
									<span className="flex items-center gap-2 text-[13px] font-medium text-[#333333]">
										{m.label}
										<Info className="h-4 w-4 shrink-0 text-[#CCCCCC]" />
									</span>
								</div>

								{/* Large metric value */}
								<div className="mb-3 flex items-baseline gap-1">
									<span
										className="text-[32px] font-bold leading-none"
										style={{ color: insufficient ? "#D0D0D0" : m.color }}
									>
										{insufficient ? "—" : m.score}
									</span>
									{!insufficient && isPercentage && (
										<span className="text-[14px] font-semibold text-[#8A8A8A]">%</span>
									)}
									{!insufficient && !isPercentage && (
										<span className="text-[13px] font-medium text-[#8A8A8A]">{m.unit}</span>
									)}
								</div>

								{/* Progress bar */}
								<div className="mb-3 h-2 w-full overflow-hidden rounded-full bg-[#EDEDED]">
									<div
										className="h-full rounded-full transition-all duration-500"
										style={{
											width: insufficient
												? "0%"
												: `${Math.min(100, Math.max(0, isPercentage ? m.score : (m.score / 10) * 100))}%`,
											background: insufficient ? "#EDEDED" : m.color,
										}}
									/>
								</div>

								{/* Supporting text */}
								<div className="mt-auto space-y-0.5">
									{insufficient ? (
										<p className="text-[12px] font-medium text-[#B0B0B0]">
											Insufficient data
										</p>
									) : (
										m.threshold && (
											<p className="text-[12px] text-[#8A8A8A]">
												{m.threshold}
											</p>
										)
									)}
								</div>
							</div>
						);
					})}
				</div>
			)}
		</div>
	);
}
