"use client";

import {
	Activity,
	CheckCircle,
	Clock,
	DollarSign,
	TrendingDown,
	TrendingUp,
	XCircle,
	Zap,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import {
	Bar,
	BarChart,
	CartesianGrid,
	Cell,
	Legend,
	Line,
	LineChart,
	Pie,
	PieChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import { api } from "@/lib/api";
import SafeNumber from "./SafeNumber";
import { traceStyles } from "./styles/traceStyles";

interface TraceStatsProps {
	executionId: string;
	traceData: any;
}

interface ExecutionStats {
	totalNodes: number;
	completedNodes: number;
	failedNodes: number;
	runningNodes: number;
	totalTokens: number;
	totalCost: number;
	averageDuration: number;
	tokensByType: Record<string, number>;
	costByType: Record<string, number>;
	costByModel: Record<string, number>;
	performanceMetrics: {
		averageTokensPerSecond: number | null;
		averageTimeToFirstToken: number | null;
	};
}

export default function TraceStats({
	executionId,
	traceData,
}: TraceStatsProps) {
	const [stats, setStats] = useState<ExecutionStats | null>(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const loadStats = async () => {
			try {
				console.log("[TraceStats] Loading stats for execution:", executionId);
				const data = await api.get(
					`/api/trace/${encodeURIComponent(executionId)}/stats`,
				);
				console.log("[TraceStats] Raw stats data from API:", data);

				// Debug each field
				console.log("[TraceStats] Field values:", {
					totalNodes: data?.totalNodes,
					completedNodes: data?.completedNodes,
					failedNodes: data?.failedNodes,
					runningNodes: data?.runningNodes,
					totalTokens: data?.totalTokens,
					totalCost: data?.totalCost,
					averageDuration: data?.averageDuration,
					tokensByType: data?.tokensByType,
					costByType: data?.costByType,
					costByModel: data?.costByModel,
					performanceMetrics: data?.performanceMetrics,
				});

				// Ensure all required fields have default values
				const safeStats: ExecutionStats = {
					totalNodes: data?.totalNodes || 0,
					completedNodes: data?.completedNodes || 0,
					failedNodes: data?.failedNodes || 0,
					runningNodes: data?.runningNodes || 0,
					totalTokens: data?.totalTokens || 0,
					totalCost: data?.totalCost || 0,
					averageDuration: data?.averageDuration || 0,
					tokensByType: data?.tokensByType || {},
					costByType: data?.costByType || {},
					costByModel: data?.costByModel || {},
					performanceMetrics: {
						averageTokensPerSecond:
							data?.performanceMetrics?.averageTokensPerSecond || null,
						averageTimeToFirstToken:
							data?.performanceMetrics?.averageTimeToFirstToken || null,
					},
				};
				console.log("[TraceStats] Safe stats after processing:", safeStats);
				setStats(safeStats);
			} catch (error) {
				console.error("[TraceStats] Failed to load stats:", error);
			} finally {
				setLoading(false);
			}
		};

		loadStats().catch((error) => {
			console.error("Failed to load stats:", error);
		});
	}, [executionId]);

	if (loading) {
		return (
			<div
				className={`flex items-center justify-center h-full ${traceStyles.panelGradient}`}
			>
				<div className="text-[color:var(--color-text-muted)]">
					Loading statistics...
				</div>
			</div>
		);
	}

	if (!stats) {
		return (
			<div
				className={`flex items-center justify-center h-full ${traceStyles.panelGradient}`}
			>
				<div className="text-[color:var(--color-text-muted)]">
					No statistics available
				</div>
			</div>
		);
	}

	// Prepare data for charts
	console.log("[TraceStats] Preparing chart data with stats:", stats);

	const nodeStatusData = [
		{
			name: "Completed",
			value: stats.completedNodes || 0,
			color: "#F7971C",
		},
		{
			name: "Failed",
			value: stats.failedNodes || 0,
			color: "var(--color-error)",
		},
		{
			name: "Running",
			value: stats.runningNodes || 0,
			color: "var(--color-info)",
		},
		{
			name: "Pending",
			value: Math.max(
				0,
				(stats.totalNodes || 0) -
					(stats.completedNodes || 0) -
					(stats.failedNodes || 0) -
					(stats.runningNodes || 0),
			),
			color: "var(--color-text-muted)",
		},
	].filter((d) => d.value > 0);

	console.log("[TraceStats] nodeStatusData:", nodeStatusData);

	const tokensByTypeData = Object.entries(stats.tokensByType || {}).map(
		([type, count]) => ({
			type: type.replace("_", " ").replace(/\b\w/g, c => c.toUpperCase()),
			tokens: count,
		}),
	);

	console.log("[TraceStats] tokensByTypeData:", tokensByTypeData);

	const costByModelData = Object.entries(stats.costByModel || {}).map(
		([model, cost]) => {
			console.log(
				"[TraceStats] Processing cost for model:",
				model,
				"cost:",
				cost,
				"type:",
				typeof cost,
			);
			try {
				// Extra defensive: check if cost is actually a number or can be converted
				let safeCost = 0;
				if (cost !== null && cost !== undefined) {
					if (typeof cost === "number" && !isNaN(cost)) {
						safeCost = cost;
					} else if (typeof cost === "string") {
						const parsed = parseFloat(cost);
						safeCost = isNaN(parsed) ? 0 : parsed;
					}
				}
				return {
					model: model.split("-").slice(0, 2).join("-"),
					cost: Number(safeCost.toFixed(4)),
				};
			} catch (error) {
				console.error(
					"[TraceStats] Error processing cost for model:",
					model,
					"error:",
					error,
				);
				return {
					model: model.split("-").slice(0, 2).join("-"),
					cost: 0,
				};
			}
		},
	);

	console.log("[TraceStats] costByModelData:", costByModelData);

	const summaryCardClass =
		"group relative min-w-0 max-w-full overflow-hidden rounded-[4px] border border-slate-200 bg-white p-3 shadow-sm transition-colors duration-200 hover:border-orange-400 sm:p-4";

	return (
		<div
			className={`trace-stats h-full min-w-0 w-full max-w-full overflow-auto overflow-x-hidden p-3 custom-scrollbar sm:p-4 ${traceStyles.panelGradient}`}
		>
			<div className="mx-auto w-full max-w-full space-y-5 sm:space-y-6">
				{/* Summary Cards — single column in narrow trace panel avoids clipped values */}
				<div className="grid w-full min-w-0 grid-cols-1 gap-3 sm:gap-4 lg:grid-cols-2">
					<div className={summaryCardClass}>
						<div className="mb-2 flex min-w-0 items-start justify-between gap-2 sm:mb-3">
							<div className={traceStyles.iconCapsuleSm}>
								<Activity className="h-3 w-3 shrink-0 text-orange-600" />
							</div>
							<span
								className={`${traceStyles.inlineLabel} min-w-0 text-right leading-snug`}
							>
								Nodes
							</span>
						</div>
						<div className="break-words text-2xl font-bold tabular-nums tracking-tight text-slate-900 sm:text-3xl">
							{stats.totalNodes}
						</div>
						<div className="mt-1.5 break-words text-xs text-emerald-700 sm:mt-2">
							{stats.totalNodes > 0
								? ((stats.completedNodes / stats.totalNodes) * 100).toFixed(0)
								: "0"}
							% completed
						</div>
					</div>

					<div className={summaryCardClass}>
						<div className="mb-2 flex min-w-0 items-start justify-between gap-2 sm:mb-3">
							<div className={traceStyles.iconCapsuleSm}>
								<Zap className="h-3 w-3 shrink-0 text-orange-600" />
							</div>
							<span
								className={`${traceStyles.inlineLabel} min-w-0 text-right leading-snug`}
							>
								Tokens
							</span>
						</div>
						<div className="break-words text-2xl font-bold tabular-nums tracking-tight text-slate-900 sm:text-3xl">
							{stats.totalTokens.toLocaleString()}
						</div>
						{stats.performanceMetrics.averageTokensPerSecond && (
							<div className="mt-1.5 break-words text-xs text-slate-600 sm:mt-2">
								{(stats.performanceMetrics.averageTokensPerSecond || 0).toFixed(
									1,
								)}{" "}
								tokens/s
							</div>
						)}
					</div>

					<div className={summaryCardClass}>
						<div className="mb-2 flex min-w-0 items-start justify-between gap-2 sm:mb-3">
							<div className={traceStyles.iconCapsuleSm}>
								<DollarSign className="h-3 w-3 shrink-0 text-orange-600" />
							</div>
							<span
								className={`${traceStyles.inlineLabel} min-w-0 text-right leading-snug`}
							>
								Total Cost
							</span>
						</div>
						<div className="break-words text-2xl font-bold tabular-nums tracking-tight text-orange-800 sm:text-3xl">
							<SafeNumber
								value={stats.totalCost}
								decimals={4}
								prefix="$"
								fallback="$0.0000"
								label="totalCost"
							/>
						</div>
						<div className="mt-1.5 break-words text-xs text-slate-600 sm:mt-2">
							<SafeNumber
								value={
									stats.totalNodes > 0
										? (stats.totalCost || 0) / stats.totalNodes
										: 0
								}
								decimals={6}
								prefix="$"
								suffix="/node"
								fallback="$0.000000/node"
								label="costPerNode"
							/>
						</div>
					</div>

					<div className={summaryCardClass}>
						<div className="mb-2 flex min-w-0 items-start justify-between gap-2 sm:mb-3">
							<div className={traceStyles.iconCapsuleSm}>
								<Clock className="h-3 w-3 shrink-0 text-orange-600" />
							</div>
							<span
								className={`${traceStyles.inlineLabel} min-w-0 text-right leading-snug`}
							>
								Avg Duration
							</span>
						</div>
						<div className="break-words text-2xl font-bold tabular-nums tracking-tight text-slate-900 sm:text-3xl">
							<SafeNumber
								value={stats.averageDuration}
								decimals={2}
								suffix="s"
								fallback="0.00s"
								label="averageDuration"
							/>
						</div>
						{stats.performanceMetrics.averageTimeToFirstToken && (
							<div className="mt-1.5 break-words text-xs text-slate-600 sm:mt-2">
								TTFT:{" "}
								<SafeNumber
									value={stats.performanceMetrics.averageTimeToFirstToken}
									decimals={0}
									suffix="ms"
									fallback="0ms"
									label="TTFT"
								/>
							</div>
						)}
					</div>
				</div>

				{/* Node Status Distribution */}
				{nodeStatusData.length > 0 && (
					<div
						className={`${traceStyles.secondaryCard} min-w-0 max-w-full p-4 sm:p-5`}
					>
						<h3
							className={`${traceStyles.sectionHeader} mb-3 break-words sm:mb-4`}
						>
							Node Status Distribution
						</h3>
						<div className="h-[220px] w-full min-h-[200px] min-w-0 sm:h-[260px]">
							<ResponsiveContainer width="100%" height="100%">
								<PieChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
									<Pie
										data={nodeStatusData}
										cx="50%"
										cy="45%"
										labelLine={false}
										label={false}
										outerRadius="70%"
										fill="#8884d8"
										dataKey="value"
									>
										{nodeStatusData.map((entry, index) => (
											<Cell
												key={`cell-${entry.name || index}`}
												fill={entry.color}
											/>
										))}
									</Pie>
									<Legend
										verticalAlign="bottom"
										wrapperStyle={{
											fontSize: "11px",
											lineHeight: 1.45,
											color: "#0f172a",
											width: "100%",
											paddingTop: "4px",
										}}
										formatter={(value) => {
											const item = nodeStatusData.find((d) => d.name === value);
											const total = nodeStatusData.reduce((s, d) => s + d.value, 0);
											const v = item?.value ?? 0;
											const pct =
												total > 0 ? ((v / total) * 100).toFixed(0) : "0";
											return `${value} (${pct}%)`;
										}}
									/>
									<Tooltip
										contentStyle={{
											backgroundColor: "rgba(255, 255, 255, 0.98)",
											border: "1px solid #e2e8f0",
											borderRadius: "4px",
											color: "#0f172a",
											fontSize: "12px",
											maxWidth: "min(280px, 90vw)",
										}}
									/>
								</PieChart>
							</ResponsiveContainer>
						</div>
					</div>
				)}

				{/* Cost by Model */}
				{costByModelData.length > 0 && (
					<div className={`${traceStyles.secondaryCard} p-5`}>
						<h3 className={`${traceStyles.sectionHeader} mb-4`}>
							Cost by Model
						</h3>
						<ResponsiveContainer width="100%" height={200}>
							<BarChart data={costByModelData} layout="horizontal">
								<CartesianGrid
									strokeDasharray="3 3"
									stroke="rgba(234, 88, 12, 0.2)"
								/>
								<XAxis
									type="number"
									tick={{ fill: "#374151", fontSize: 12 }}
									tickFormatter={(value) => `$${value}`}
								/>
								<YAxis
									type="category"
									dataKey="model"
									tick={{ fill: "#374151", fontSize: 12 }}
									width={80}
								/>
								<Tooltip
									contentStyle={{
										backgroundColor: "rgba(255, 247, 237, 0.97)",
										border: "1px solid rgba(234, 88, 12, 0.3)",
										borderRadius: "12px",
										color: "#1f2937",
									}}
									formatter={(value: number) => `$${(value || 0).toFixed(4)}`}
								/>
								<Bar
									dataKey="cost"
									fill="#ea580c"
									radius={[4, 4, 4, 4]}
								/>
							</BarChart>
						</ResponsiveContainer>
					</div>
				)}

				{/* Performance Metrics */}
				<div
					className={`${traceStyles.secondaryCard} min-w-0 max-w-full p-4 sm:p-5`}
				>
					<h3
						className={`${traceStyles.sectionHeader} mb-3 break-words sm:mb-4`}
					>
						Performance Metrics
					</h3>
					<div className="space-y-4">
						<div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
							<span
								className={`${traceStyles.inlineLabel} shrink-0 sm:max-w-[45%]`}
							>
								Success Rate
							</span>
							<div className="flex min-w-0 flex-1 flex-wrap items-center gap-2 sm:justify-end">
								<div className="h-2 min-w-[4rem] flex-1 rounded-full bg-slate-200 sm:max-w-[10rem]">
									<div
										className="h-full bg-[#F7971C] transition-all duration-300"
										style={{
											width: `${stats.totalNodes > 0 ? (stats.completedNodes / stats.totalNodes) * 100 : 0}%`,
										}}
									/>
								</div>
								<span className="shrink-0 font-mono text-sm font-medium tabular-nums text-slate-900">
									{stats.totalNodes > 0
										? ((stats.completedNodes / stats.totalNodes) * 100).toFixed(
												1,
											)
										: "0.0"}
									%
								</span>
							</div>
						</div>

						{stats.performanceMetrics.averageTokensPerSecond && (
							<div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
								<span
									className={`${traceStyles.inlineLabel} shrink-0 sm:max-w-[55%]`}
								>
									Avg Tokens/Second
								</span>
								<span className="min-w-0 break-words font-mono text-sm font-medium text-slate-900">
									{(
										stats.performanceMetrics.averageTokensPerSecond || 0
									).toFixed(1)}
								</span>
							</div>
						)}

						{stats.performanceMetrics.averageTimeToFirstToken && (
							<div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
								<span
									className={`${traceStyles.inlineLabel} shrink-0 sm:max-w-[55%]`}
								>
									Avg Time to First Token
								</span>
								<span className="min-w-0 break-words font-mono text-sm font-medium text-slate-900">
									{(
										stats.performanceMetrics.averageTimeToFirstToken || 0
									).toFixed(0)}
									ms
								</span>
							</div>
						)}

						<div
							className={`${traceStyles.highlightRow} mt-4 flex min-w-0 flex-col gap-1 sm:flex-row sm:items-center sm:justify-between`}
						>
							<span className="break-words text-sm text-slate-700">
								Cost per Token
							</span>
							<span className="break-all font-mono text-sm font-medium text-orange-800">
								$
								{stats.totalTokens > 0
									? (
											((stats.totalCost || 0) / stats.totalTokens) *
											1000
										).toFixed(6)
									: "0.000000"}
								/1K
							</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
