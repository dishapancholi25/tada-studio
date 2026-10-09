"use client";

import {
	Area,
	AreaChart,
	CartesianGrid,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import { useState } from "react";
import type { ReactNode } from "react";
import { AlertCircle, Calendar, Percent } from "lucide-react";
import { useRunSummary } from "@/hooks/workflow-metrics/useRunSummary";
import Card from "./shared/Card";
import ChartContainer from "./shared/ChartContainer";
import { ErrorState } from "./shared/WidgetStates";
import StatCard from "./shared/StatCard";

const ICONS: Record<string, { icon: ReactNode; iconClassName: string }> = {
	"runs-today": {
		icon: <Calendar className="h-3.5 w-3.5" />,
		iconClassName:
			"flex h-6 w-6 shrink-0 items-center justify-center rounded bg-[rgba(6,182,212,0.1)] text-[#0891B2]",
	},
	"failed-runs": {
		icon: <AlertCircle className="h-3.5 w-3.5" />,
		iconClassName:
			"flex h-6 w-6 shrink-0 items-center justify-center rounded bg-[rgba(176,0,32,0.08)] text-[#B00020]",
	},
	"success-rate": {
		icon: <Percent className="h-3.5 w-3.5" />,
		iconClassName:
			"flex h-6 w-6 shrink-0 items-center justify-center rounded bg-[rgba(22,163,74,0.1)] text-[#16A34A]",
	},
};

const SUBCAPTIONS: Record<string, string> = {
	"runs-today": "Runs Today",
	"failed-runs": "Failed Runs",
	"success-rate": "Success Rate",
};

const CHART_SERIES = [
	{ key: "successful", label: "successful", color: "#22C55E", dashed: false },
	{ key: "failed", label: "failed", color: "#EF4444", dashed: false },
	{ key: "runs", label: "total", color: "#FF5E00", dashed: true },
];

export default function RunSummary({ workflowId }: { workflowId: string }) {
	const { data, loading, error, refetch } = useRunSummary(workflowId);
	const [period, setPeriod] = useState<"weekly" | "monthly">("weekly");

	const trend = data
		? period === "monthly"
			? (data.monthlyTrend ?? data.trend)
			: data.trend
		: undefined;
	const isEmpty = !loading && !error && (!trend || trend.length === 0);

	/** Renders one KPI StatCard with its icon, tone and subcaption. */
	function renderKpi(kpi: NonNullable<typeof data>["kpis"][number]) {
		const iconData = ICONS[kpi.id];
		return (
			<StatCard
				key={kpi.id}
				label={kpi.label}
				value={kpi.value.toLocaleString()}
				unit={kpi.unit}
				tone={kpi.tone}
				icon={iconData?.icon}
				iconClassName={iconData?.iconClassName}
				subcaption={SUBCAPTIONS[kpi.id]}
			/>
		);
	}

	return (
			<div className="grid grid-cols-1 items-stretch gap-6 lg:grid-cols-3">
				<ChartContainer
					title="Run Volume Trend"
					subtitle="Daily execution volume for this workflow — successful vs. failed"
					tooltip="Number of workflow runs per day across the selected window."
					loading={loading}
					error={error}
					isEmpty={isEmpty}
					onRetry={refetch}
					skeletonHeight={220}
					className="lg:col-span-2"
					action={
					<div className="flex items-center gap-1.5">
						{(["weekly", "monthly"] as const).map((p) => (
							<button
								key={p}
								type="button"
								onClick={() => setPeriod(p)}
								className={`rounded px-3 py-1 text-[11px] font-semibold capitalize transition-colors ${
									period === p
										? "bg-[#FF5E00] text-white"
										: "border border-[#E0E0E0] text-[#4C4C4C] hover:bg-[#F5F5F5]"
								}`}
							>
								{p.charAt(0).toUpperCase() + p.slice(1)}
							</button>
						))}
					</div>
				}
			>
				{trend && trend.length > 0 && (
					<>
						<div className="h-[220px] w-full">
							<ResponsiveContainer width="100%" height="100%">
								<AreaChart data={trend} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
									<defs>
										<linearGradient id="successFill" x1="0" y1="0" x2="0" y2="1">
											<stop offset="0%" stopColor="#22C55E" stopOpacity={0.3} />
											<stop offset="100%" stopColor="#22C55E" stopOpacity={0} />
										</linearGradient>
									</defs>
									<CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" vertical={false} />
									<XAxis
										dataKey="label"
										tick={{ fontSize: 10, fill: "#8A8A8A" }}
										axisLine={false}
										tickLine={false}
										interval="preserveStartEnd"
										minTickGap={24}
									/>
									<YAxis
										tick={{ fontSize: 11, fill: "#8A8A8A" }}
										axisLine={false}
										tickLine={false}
										width={36}
									/>
									<Tooltip
										contentStyle={{ borderRadius: 8, border: "1px solid #EEE", fontSize: 12 }}
									/>
									<Area
										type="monotone"
										dataKey="successful"
										name="successful"
										stroke="#22C55E"
										strokeWidth={2}
										fill="url(#successFill)"
										dot={false}
										activeDot={{ r: 3 }}
									/>
									<Area
										type="monotone"
										dataKey="failed"
										name="failed"
										stroke="#EF4444"
										strokeWidth={1.5}
										fill="none"
										dot={false}
										activeDot={{ r: 3 }}
									/>
									<Area
										type="monotone"
										dataKey="runs"
										name="total"
										stroke="#FF5E00"
										strokeWidth={1.5}
										strokeDasharray="5 4"
										fill="none"
										dot={false}
										activeDot={{ r: 3 }}
									/>
								</AreaChart>
							</ResponsiveContainer>
						</div>
						{/* Chart legend */}
						<div className="mt-2 flex items-center justify-center gap-5">
							{CHART_SERIES.map((s) => (
								<span key={s.key} className="flex items-center gap-1.5 text-[11px] text-[#8A8A8A]">
									<span
										className="inline-block h-[2px] w-4 shrink-0"
										style={{
											background: s.dashed
												? `repeating-linear-gradient(to right,${s.color} 0,${s.color} 4px,transparent 4px,transparent 8px)`
												: s.color,
										}}
									/>
									{s.label}
								</span>
							))}
						</div>
					</>
				)}
			</ChartContainer>

			{/* KPI panel: top row stretches, bottom row anchored — matches chart height */}
			<div className="grid h-full grid-rows-[1fr_auto] gap-6">
				{loading && (
					<>
						<StatCard label="" value="" loading />
						<div className="grid grid-cols-2 gap-4">
							{Array.from({ length: 2 }).map((_, i) => (
								<StatCard key={i} label="" value="" loading />
							))}
						</div>
					</>
				)}
				{!loading && (error || !data) && (
					<Card className="row-span-2">
						<ErrorState message={error ?? "Failed to load run summary"} onRetry={refetch} />
					</Card>
				)}
				{!loading && data && (
						<>
							{/* "Runs Today" occupies the upper section, top-aligned with the chart */}
							{data.kpis
								.filter((kpi) => kpi.id === "runs-today")
								.map((kpi) => renderKpi(kpi))}
							{/* "Failed Runs" and "Success Rate" anchored to the bottom row */}
							<div className="grid grid-cols-2 gap-4">
								{data.kpis
									.filter((kpi) => kpi.id !== "runs-today")
									.map((kpi) => renderKpi(kpi))}
							</div>
						</>
					)}
			</div>
		</div>
	);
}
