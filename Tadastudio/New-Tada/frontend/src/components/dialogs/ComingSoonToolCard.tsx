"use client";

import type { LucideIcon } from "lucide-react";
import type React from "react";
import { useCallback } from "react";

export interface ComingSoonTool {
	value: string;
	label: string;
	icon: LucideIcon;
	description: string;
	color: string;
	logo: string;
	fallbackEmoji: string;
}

interface ComingSoonToolCardProps {
	tool: ComingSoonTool;
}

export default function ComingSoonToolCard({ tool }: ComingSoonToolCardProps) {
	const handleImageError = useCallback(
		(e: React.SyntheticEvent<HTMLImageElement>) => {
			const target = e.target as HTMLImageElement;
			target.style.display = "none";
			target.parentElement!.innerHTML = `<span class="text-lg">${tool.fallbackEmoji}</span>`;
		},
		[tool.fallbackEmoji],
	);

	return (
		<div className="relative flex items-center gap-3 p-4 rounded-2xl border border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/20 cursor-not-allowed overflow-hidden">
			{/* Shimmer effect */}
			<div className="absolute inset-0 bg-gradient-to-r from-transparent via-[color:var(--color-surface)]/10 to-transparent animate-shimmer" />

			{/* Icon */}
			<div className="p-2.5 rounded-xl bg-[color:var(--color-surface)]/30 flex items-center justify-center w-[42px] h-[42px] flex-shrink-0">
				{tool.logo.startsWith("http") ? (
					<img
						src={tool.logo}
						alt={tool.label}
						className="w-5 h-5 opacity-50"
						onError={handleImageError}
					/>
				) : (
					<span className="text-lg opacity-50">{tool.fallbackEmoji}</span>
				)}
			</div>

			{/* Content */}
			<div className="flex-1 min-w-0">
				<div className="text-sm font-medium text-[color:var(--color-text-muted)]">
					{tool.label}
				</div>
				<div className="text-xs text-[color:var(--color-text-muted)]/70 mt-0.5 line-clamp-1">
					{tool.description}
				</div>
			</div>

			{/* Coming Soon Badge */}
			<span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-[color:var(--color-surface)]/50 text-[color:var(--color-text-muted)] border border-[color:var(--color-border)]/30 flex-shrink-0">
				Soon
			</span>
		</div>
	);
}
