"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface ConfigBadgeProps {
	label: string;
	value: string;
	color: "plum" | "blue" | "purple" | "green" | "orange" | "gray";
	size?: "sm" | "md";
}

export default function ConfigBadge({
	label,
	value,
	color,
	size = "sm",
}: ConfigBadgeProps) {
	const colorClasses = {
		plum: "bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent-light)] border-[color:var(--color-border)]/30",
		blue: "bg-blue-400/20 text-blue-600 border-blue-400/30",
		purple: "bg-purple-400/20 text-purple-600 border-purple-400/30",
		green: "bg-[#0DA931]/20 text-[#0DA931] border-[#0DA931]/30",
		orange: "bg-orange-400/20 text-orange-300 border-orange-400/30",
		gray: "bg-gray-500/20 text-gray-400 border-gray-500/30",
	};

	const sizeClasses = {
		sm: "px-2 py-1 text-xs",
		md: "px-3 py-1.5 text-sm",
	};

	return (
		<div
			className={cn(
				"inline-flex items-center gap-1.5 rounded-md border",
				colorClasses[color],
				sizeClasses[size],
			)}
		>
			<span className="font-medium">{label}:</span>
			<span>{value}</span>
		</div>
	);
}
