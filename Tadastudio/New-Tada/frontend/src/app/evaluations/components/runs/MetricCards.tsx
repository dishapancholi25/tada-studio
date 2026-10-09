"use client";

export function PillarScoreCard({
	label,
	value,
	variant = "default",
}: {
	label: string;
	value?: number | null;
	variant?: "default" | "compact";
}) {
	const pct = value != null ? Math.round(value) : null;
	const barColor =
		pct !== null && pct >= 80
			? "bg-emerald-500"
			: pct !== null && pct >= 60
				? "bg-amber-500"
				: "bg-red-500";
	const textColor =
		pct !== null && pct >= 80
			? "text-emerald-600"
			: pct !== null && pct >= 60
				? "text-amber-600"
				: "text-red-600";

	if (variant === "compact") {
		return (
			<div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-[0_10px_28px_rgba(15,23,42,0.06)]">
				<p className="text-[11px] uppercase text-slate-500">{label}</p>
				{pct !== null ? (
					<div className="flex items-center gap-2">
						<span className={`text-sm font-semibold ${textColor}`}>{pct}%</span>
						<div className="h-1 w-16 overflow-hidden rounded-full bg-slate-100">
							<div
								className={`h-full rounded-full ${barColor}`}
								style={{ width: `${pct}%` }}
							/>
						</div>
					</div>
				) : (
					<span className="text-sm text-slate-400">—</span>
				)}
			</div>
		);
	}

	return (
		<div className="rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_82%,#f59e0b_180%)] p-4 shadow-[0_18px_50px_rgba(15,23,42,0.08)] transition-colors hover:border-orange-400">
			<p className="mb-1 text-xs uppercase text-slate-500">{label}</p>
			{pct !== null ? (
				<>
					<p className="text-2xl font-semibold text-slate-900">{pct}%</p>
					<div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
						<div
							className={`h-full rounded-full ${barColor}`}
							style={{ width: `${pct}%` }}
						/>
					</div>
				</>
			) : (
				<p className="text-2xl text-slate-400">—</p>
			)}
		</div>
	);
}

export function DiagnosticMetrics({ diagnostics }: { diagnostics?: Record<string, any> | null }) {
	if (!diagnostics) return null;
	const entries = Object.entries(diagnostics).filter(
		([, v]) => v != null && typeof v !== "object",
	);
	if (entries.length === 0) return null;

	const unitMap: Record<string, string> = {
		input_token_ratio: "%", output_token_ratio: "%", max_node_cost_share: "%",
		slowest_node_share: "%", max_ttft_ms: "ms", slowest_node_seconds: "s",
	};
	const formatVal = (key: string, val: any): string => {
		const suffix = unitMap[key] ?? "";
		if (typeof val === "number") {
			return Number.isInteger(val) ? `${val}${suffix}` : `${val.toFixed(1)}${suffix}`;
		}
		return `${val}${suffix}`;
	};

	return (
		<div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
			{entries.map(([key, val]) => (
				<div key={key} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
					<p className="mb-0.5 text-[10px] capitalize text-slate-500">{key.replace(/_/g, " ")}</p>
					<p className="text-sm font-semibold text-slate-900">{formatVal(key, val)}</p>
				</div>
			))}
		</div>
	);
}

export function MetricCard({ label, value, unit }: { label: string; value?: number | string | null; unit?: string }) {
	return (
		<div className="rounded-lg border border-slate-200 bg-white p-3">
			<p className="mb-0.5 text-[11px] uppercase text-slate-500">{label}</p>
			<p className="text-lg font-semibold text-slate-900">
				{value != null ? `${value}${unit ?? ""}` : "—"}
			</p>
		</div>
	);
}
