"use client";

import { AlertCircle, CheckCircle, Clock, Play } from "lucide-react";

export function ScoreBadge({ value, label, showBar }: { value?: number | null; label?: string; showBar?: boolean }) {
	if (value == null) return <span className="text-xs text-slate-500">{label ? `${label}: ` : ""}—</span>;
	const pct = Math.round(value);
	const color =
		pct >= 80
			? "text-emerald-400"
			: pct >= 60
				? "text-amber-400"
				: "text-red-400";
	const barBg =
		pct >= 80
			? "bg-emerald-500"
			: pct >= 60
				? "bg-amber-500"
				: "bg-red-500";
	return (
		<span className={`inline-flex items-center gap-2 text-xs font-medium ${color}`}>
			{label ? `${label}: ` : ""}{pct}%
			{showBar && (
				<span className="inline-block h-1 w-16 overflow-hidden rounded-full bg-slate-100">
					<span className={`block h-full rounded-full ${barBg}`} style={{ width: `${pct}%` }} />
				</span>
			)}
		</span>
	);
}

export function StatusBadge({ status }: { status: string }) {
	const styles: Record<string, { badgeClass: string; Icon: typeof CheckCircle }> = {
		pending: { badgeClass: "border-amber-400/45 bg-amber-400/12 text-amber-300", Icon: Clock },
		running: { badgeClass: "border-[rgba(var(--color-primary-rgb),0.45)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary-light)]", Icon: Play },
		completed: { badgeClass: "border-emerald-400/45 bg-emerald-400/12 text-emerald-600", Icon: CheckCircle },
		completed_with_failures: { badgeClass: "border-orange-400/45 bg-orange-400/12 text-orange-300", Icon: AlertCircle },
		failed: { badgeClass: "border-red-400/45 bg-red-400/12 text-red-300", Icon: AlertCircle },
	};
	const { badgeClass, Icon } = styles[status] ?? {
		badgeClass: "border-[color:var(--color-border)]/45 bg-[color:var(--color-surface)]/40 text-[color:var(--color-text-muted)]",
		Icon: Clock,
	};
	const displayLabel = status.replace(/_/g, " ");
	return (
		<span
			className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${badgeClass}`}
		>
			<Icon className="h-3 w-3" />
			{displayLabel}
		</span>
	);
}
