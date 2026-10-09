"use client";

import type React from "react";

export interface StatItem {
	label: string;
	value: string | number;
	color?: "primary" | "green" | "red" | "default";
	icon?: React.ReactNode;
	format?: "number" | "currency";
}

interface DataSourceStatsBarProps {
	stats: StatItem[];
	title: string;
	titleIcon: React.ReactNode;
	actionSlot?: React.ReactNode;
	className?: string;
}

const COLOR_STYLES: Record<
	NonNullable<StatItem["color"]>,
	{ bg: string; border: string; valueColor: string }
> = {
	primary: {
		bg: "#ffffff",
		border: "rgba(249, 115, 22, 0.45)",
		valueColor: "#c2410c",
	},
	green: {
		bg: "#ffffff",
		border: "rgba(249, 115, 22, 0.35)",
		valueColor: "#ea580c",
	},
	red: {
		bg: "rgba(239, 68, 68, 0.1)",
		border: "rgba(239, 68, 68, 0.2)",
		valueColor: "rgb(248, 113, 113)",
	},
	default: {
		bg: "#ffffff",
		border: "rgba(249, 115, 22, 0.28)",
		valueColor: "#0f172a",
	},
};

function formatValue(value: string | number, format?: StatItem["format"]): string {
	if (typeof value === "string") return value;
	if (format === "currency") return `$${value.toFixed(4)}`;
	if (format === "number") return value.toLocaleString();
	return typeof value === "number" ? value.toLocaleString() : String(value);
}

export default function DataSourceStatsBar({
	stats,
	title,
	titleIcon,
	actionSlot,
	className = "",
}: DataSourceStatsBarProps) {
	return (
		<div
			className={`rounded-xl p-6 shadow-md ${className}`}
			style={{
				background: "#ffffff",
				border: "1px solid rgba(249, 115, 22, 0.35)",
			}}
		>
			<div className="flex flex-wrap items-center justify-between gap-3 mb-4">
				<h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
					{titleIcon}
					{title}
				</h3>
				{actionSlot}
			</div>

			<div
				className="grid gap-4"
				style={{
					gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
				}}
			>
				{stats.map((stat) => {
					const colors = COLOR_STYLES[stat.color ?? "default"];
					return (
						<div
							key={stat.label}
							className="relative overflow-hidden rounded-lg p-4"
							style={{
								background: colors.bg,
								border: `1px solid ${colors.border}`,
							}}
						>
							{stat.icon && (
								<div className="absolute top-3 right-3 opacity-20">
									{stat.icon}
								</div>
							)}
							<div className="text-sm text-[color:var(--color-text-muted)]">
								{stat.label}
							</div>
							<div
								className="text-2xl font-semibold mt-0.5 flex items-center gap-1.5"
								style={{ color: colors.valueColor }}
							>
								{formatValue(stat.value, stat.format)}
							</div>
						</div>
					);
				})}
			</div>
		</div>
	);
}
