"use client";

import type { PolicyMetricsResponse } from "@/types/guardrail-policies";
import * as guardrailsApi from "@/lib/guardrails-api";
import { useEffect, useState } from "react";

type TimeWindow = "7d" | "30d" | "all";

const WINDOW_LABELS: Record<TimeWindow, string> = {
	"7d": "Last 7 days",
	"30d": "Last 30 days",
	all: "All time",
};

interface PolicyMetricsProps {
	policyId: string;
}

export default function PolicyMetrics({ policyId }: PolicyMetricsProps) {
	const [window, setWindow] = useState<TimeWindow>("7d");
	const [metrics, setMetrics] = useState<PolicyMetricsResponse | null>(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		setLoading(true);
		guardrailsApi
			.getPolicyMetrics(policyId, window)
			.then((data) => setMetrics(data as PolicyMetricsResponse))
			.catch((err) => {
				console.error("Failed to load policy metrics:", err);
				setMetrics(null);
			})
			.finally(() => setLoading(false));
	}, [policyId, window]);

	if (loading) {
		return (
			<div className="flex items-center justify-center py-20">
				<div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-orange-500" />
			</div>
		);
	}

	if (!metrics || metrics.total_violations === 0) {
		return (
			<div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white py-20 text-slate-500">
				<p className="text-sm">
					No violation data yet. Deploy this policy to start collecting
					metrics.
				</p>
			</div>
		);
	}

	return (
		<div className="space-y-6">
			{/* Time window selector */}
			<div className="flex items-center gap-1">
				{(Object.keys(WINDOW_LABELS) as TimeWindow[]).map((w) => (
					<button
						key={w}
						type="button"
						onClick={() => setWindow(w)}
						className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
							window === w
								? "border border-orange-500 bg-orange-500 text-white"
								: "border border-slate-200 bg-white text-slate-700 hover:border-orange-400 hover:text-slate-900"
						}`}
					>
						{WINDOW_LABELS[w]}
					</button>
				))}
			</div>

			{/* Stats grid */}
			<div className="grid grid-cols-2 gap-3">
				<StatCard label="Total Violations" value={metrics.total_violations} />
				<StatCard label="Block Count" value={metrics.block_count} />
				<StatCard label="Warn Count" value={metrics.warn_count} />
				<StatCard
					label="Block Rate"
					value={`${(metrics.block_rate * 100).toFixed(1)}%`}
				/>
				<StatCard
					label="Warn Rate"
					value={`${(metrics.warn_rate * 100).toFixed(1)}%`}
				/>
				<StatCard
					label="False Positive Rate"
					value={`${(metrics.false_positive_rate * 100).toFixed(1)}%`}
				/>
			</div>

			{/* False positive signal */}
			{metrics.false_positive_count > 0 && (
				<p className="text-sm text-slate-600">
					{metrics.false_positive_count} violation
					{metrics.false_positive_count !== 1 ? "s" : ""} flagged as false
					positive{metrics.false_positive_count !== 1 ? "s" : ""} (
					{(metrics.false_positive_rate * 100).toFixed(1)}%)
				</p>
			)}

			{/* Top-5 rules */}
			{metrics.top_rules.length > 0 && (
				<div>
					<h4 className="mb-2 text-xs font-medium capitalize tracking-wider text-slate-500">
						Most Triggered Rules
					</h4>
					<ol className="space-y-1.5">
						{metrics.top_rules.map((rule, i) => (
							<li
								key={rule.rule_name}
								className="flex items-center justify-between text-sm"
							>
								<span className="text-slate-700">
									{i + 1}. {rule.rule_name}
								</span>
								<span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] text-orange-700">
									{rule.count}
								</span>
							</li>
						))}
					</ol>
				</div>
			)}

			{/* Per-rule feedback table */}
			{metrics.per_rule_feedback.length > 0 && (
				<div>
					<h4 className="mb-2 text-xs font-medium capitalize tracking-wider text-slate-500">
						Per-Rule Feedback
					</h4>
					<div className="overflow-hidden rounded-lg border border-slate-200">
						<table className="w-full text-xs">
							<thead>
								<tr className="border-b border-slate-200 text-slate-500">
									<th className="py-2 px-3 text-left font-medium">
										Rule
									</th>
									<th className="py-2 px-3 text-left font-medium">
										Confirmed
									</th>
									<th className="py-2 px-3 text-left font-medium">
										False Positive
									</th>
								</tr>
							</thead>
							<tbody>
								{metrics.per_rule_feedback.map((rf) => (
									<tr
										key={rf.rule_name}
										className="border-b border-slate-100"
									>
										<td className="py-2 px-3 text-slate-700">
											{rf.rule_name}
										</td>
										<td className="py-2 px-3 text-[#0DA931]">
											{rf.positive_count}
										</td>
										<td className="py-2 px-3 text-red-400">
											{rf.negative_count}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</div>
			)}
		</div>
	);
}

function StatCard({
	label,
	value,
}: {
	label: string;
	value: number | string;
}) {
	return (
		<div className="rounded-xl border border-slate-200 bg-white p-3 shadow-[0_10px_28px_rgba(15,23,42,0.06)]">
			<p className="mb-1 text-[10px] capitalize tracking-wider text-slate-500">
				{label}
			</p>
			<p className="text-lg font-semibold text-slate-900">{value}</p>
		</div>
	);
}
