"use client";

import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";
import type { DeltaMetric } from "@/types/workflow-metrics";
import Card from "./Card";
import { Skeleton } from "./WidgetStates";

interface StatCardProps {
	label: string;
	value: string | number;
	unit?: string;
	delta?: DeltaMetric;
	icon?: ReactNode;
	/** Overrides the default orange icon container class. */
	iconClassName?: string;
	caption?: string;
	/** Rendered below the value row for all card types (non-tinted and tinted). */
	subcaption?: string;
	tone?: "good" | "warning" | "critical" | "neutral";
	loading?: boolean;
	/** When true, the card uses a tone-tinted background + border (used by the
	 *  latency cards). Off by default so other KPI cards stay neutral white. */
	tinted?: boolean;
}

const TONE_ACCENT: Record<NonNullable<StatCardProps["tone"]>, string> = {
	good: "text-[#16A34A]",
	warning: "text-[#F97316]",
	critical: "text-[#B00020]",
	neutral: "text-[#333333]",
};

/** Tone-tinted card surface (background + border) for the `tinted` variant,
 *  matched to the reference latency cards. */
const TONE_SURFACE: Record<NonNullable<StatCardProps["tone"]>, string> = {
	good: "bg-[#EEFBF2] border-[#CBEBD6]",
	warning: "bg-[#FFF4EE] border-[#FBDFCB]",
	critical: "bg-[#FDECEA] border-[#F5C6C0]",
	neutral: "bg-white border-[#F2F2F2]",
};

/** Reusable KPI card with optional delta indicator and tone-based value colour.
 *
 * Non-tinted (summary / run-summary) layout — matches the Figma reference:
 *   Row 1: LABEL  [▲ +X%?]  ·····  [icon]
 *   Row 2: caption (small, below label — if provided)
 *   Row 3: large VALUE  unit?
 *
 * Tinted (latency) layout:
 *   Row 1: LABEL
 *   Row 2: large VALUE  UNIT
 *   Row 3: caption (small, below value — if provided)
 */
export default function StatCard({
	label,
	value,
	unit,
	delta,
	icon,
	iconClassName,
	caption,
	subcaption,
	tone = "neutral",
	loading = false,
	tinted = false,
}: StatCardProps) {
	if (loading) {
		return (
			<Card>
				<Skeleton className="h-3 w-24" />
				<Skeleton className="mt-3 h-7 w-20" />
				<Skeleton className="mt-2 h-3 w-16" />
			</Card>
		);
	}

	const deltaUp = delta?.direction === "up";
	const deltaDown = delta?.direction === "down";

	return (
		<Card className={`flex flex-col${tinted ? ` border ${TONE_SURFACE[tone]}` : ""}`}>

			{/* ── Header row ──────────────────────────────────────── */}
			<div className="flex items-start justify-between gap-2">
				<div className="min-w-0">
					{/* Label + inline delta (non-tinted only) */}
					<div className="flex flex-wrap items-center gap-1.5">
						<span
							className={`text-[12px] font-medium leading-none ${
								tinted ? "font-mono text-[#4C4C4C]" : "uppercase tracking-wide text-[#8A8A8A]"
							}`}
						>
							{label}
						</span>

						{/* Delta: plain coloured text with arrow, inline with label */}
						{delta && !tinted && (
							<span
								className={`flex items-center gap-0.5 text-[11px] font-semibold ${
									deltaUp
										? "text-[#16A34A]"
										: deltaDown
											? "text-[#B00020]"
											: "text-[#666666]"
								}`}
							>
								{deltaUp ? (
									<ArrowUpRight className="h-3 w-3" />
								) : deltaDown ? (
									<ArrowDownRight className="h-3 w-3" />
								) : null}
								{deltaUp ? "+" : ""}
								{Math.abs(delta.changePct)}%
							</span>
						)}
					</div>

					{/* Caption below label for non-tinted cards */}
					{caption && !tinted && (
						<p className="mt-1 text-[11px] leading-tight text-[#9A9A9A]">{caption}</p>
					)}
				</div>

				{icon && (
					<span className={iconClassName ?? "flex h-6 w-6 shrink-0 items-center justify-center rounded bg-[rgba(255,94,0,0.08)] text-[#FF5E00]"}>
						{icon}
					</span>
				)}
			</div>

			{/* ── Value row ───────────────────────────────────────── */}
			<div className="mt-3 flex items-end gap-1">
				<span
					className={`text-[26px] font-bold leading-none ${tinted ? "font-mono" : ""} ${
						TONE_ACCENT[tone]
					}`}
				>
					{value}
				</span>
				{unit &&
					(tinted ? (
						<span
							className={`font-mono text-[26px] font-bold leading-none ${TONE_ACCENT[tone]}`}
						>
							{unit}
						</span>
					) : (
						<span className="mb-0.5 text-[13px] font-semibold text-[#8A8A8A]">{unit}</span>
					))}
			</div>

			{/* Tinted caption below value (latency cards) */}
			{tinted && caption && (
				<p className="mt-1.5 text-[11px] text-[#9A9A9A]">{caption}</p>
			)}
			{/* Subcaption below value for all card types (run-summary cards) */}
			{subcaption && (
				<p className="mt-1 text-[11px] text-[#9A9A9A]">{subcaption}</p>
			)}
		</Card>
	);
}
