"use client";

import {
	Bar,
	BarChart,
	CartesianGrid,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import { useAIApplicationInsights } from "@/hooks/workflow-metrics/useAIApplicationInsights";
import ChartContainer from "./shared/ChartContainer";

/** Static series definition — keeps the legend visible in the card header
 * even before data loads or when the empty state is shown. Colors match
 * the series returned by the service (Documents=orange, Queries=amber, Sessions=navy). */
const STATIC_SERIES = [
	{ key: "documents", label: "Documents", color: "#FF5E00" },
	{ key: "queries", label: "Queries", color: "#EF7413" },
	{ key: "sessions", label: "Sessions", color: "#1F2A44" },
];

export default function AIApplicationInsights({ workflowId }: { workflowId: string }) {
	const { data, loading, error, refetch } = useAIApplicationInsights(workflowId);

	// Always render the chart structure — empty data shows clean axes/grid.
	const points = data?.points ?? [];
	const series = data?.series ?? STATIC_SERIES;

	return (
		<ChartContainer
			title="AI Application Insights"
			subtitle="Total number of documents downloaded/viewed, along with the total queries raised and sessions."
			tooltip="Total number of documents downloaded/viewed, along with the total queries raised and sessions."
			loading={loading}
			error={error}
			onRetry={refetch}
			skeletonHeight={220}
			action={
				<div className="flex flex-wrap items-center gap-3">
					{series.map((s) => (
						<span key={s.key} className="flex items-center gap-1.5 text-[11px] text-[#8A8A8A]">
							<span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
							{s.label}
						</span>
					))}
				</div>
			}
		>
			<div className="h-[220px] w-full">
				{points.length === 0 ? (
					<div className="flex h-full flex-col items-center justify-center gap-2">
						<svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-[#CCCCCC]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
							<path strokeLinecap="round" strokeLinejoin="round" d="M3 8h18M3 12h18M3 16h18" />
						</svg>
						<p className="text-[12px] text-[#B0B0B0]">No data available</p>
					</div>
				) : (
					<ResponsiveContainer width="100%" height="100%">
						<BarChart data={points} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
							<CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" vertical={false} />
							<XAxis dataKey="label" tick={{ fontSize: 11, fill: "#8A8A8A" }} axisLine={false} tickLine={false} />
							<YAxis tick={{ fontSize: 11, fill: "#8A8A8A" }} axisLine={false} tickLine={false} />
							<Tooltip
								contentStyle={{ borderRadius: 8, border: "1px solid #EEE", fontSize: 12 }}
								cursor={{ fill: "rgba(255,94,0,0.05)" }}
							/>
							{series.map((s) => (
								<Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} radius={[3, 3, 0, 0]} maxBarSize={18} />
							))}
						</BarChart>
					</ResponsiveContainer>
				)}
			</div>
		</ChartContainer>
	);
}
