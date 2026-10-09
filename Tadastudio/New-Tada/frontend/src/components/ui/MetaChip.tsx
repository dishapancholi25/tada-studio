"use client";

import React, { memo } from "react";

interface MetaChipProps {
	label: string;
	value?: string | number;
	title?: string;
	color?:
		| "plum"
		| "purple"
		| "purpleDS"
		| "gray"
		| "green"
		| "red"
		| "accent";
	wrap?: boolean;
}

const colorMap: Record<Required<MetaChipProps>["color"], string> = {
	plum: "bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] border-[color:var(--color-border)]/30",
	purple: "bg-purple-900/30 text-purple-600 border-purple-700/40",
	purpleDS: "bg-[#9636FF]/10 text-[#9636FF] border-purple-200",
	gray: "bg-[color:var(--color-surface)] text-[color:var(--color-text-secondary)] border-[color:var(--color-border)]",
	green: "bg-[#0DA931]/30 text-[#0DA931] border-[#0DA931]/40",
	red: "bg-red-900/30 text-red-300 border-red-700/40",
	accent:
		"bg-[color:var(--color-accent)]/10 text-[color:var(--color-accent)] border-[color:var(--color-border)]/20",
};

const MetaChip = memo(function MetaChip({
	label,
	value,
	title,
	color = "gray",
	wrap = false,
}: MetaChipProps) {
	return (
		<span
			className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs border ${colorMap[color]} ${wrap ? "whitespace-normal break-all leading-snug" : ""}`}
			title={title || String(value ?? label)}
		>
			<span className="opacity-80">{label}</span>
			{value !== undefined && (
				<strong className={`text-slate-800 ${wrap ? "font-medium" : ""}`}>
					{String(value)}
				</strong>
			)}
		</span>
	);
});

export default MetaChip;
