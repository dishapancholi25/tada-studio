"use client";

import { ChevronRight } from "lucide-react";
import type React from "react";
import { cn } from "@/lib/utils";

interface ConfigCardButtonProps {
	title: string;
	icon: React.ReactNode;
	description: string;
	borderColor: string;
	badge?: React.ReactNode;
	onClick: () => void;
	className?: string;
	preview?: React.ReactNode;
}

// Helper function to get color-specific hover effects
const getColorEffects = (borderColor: string) => {
	if (
		borderColor.includes("var(--color-primary)") ||
		borderColor.includes("primary")
	) {
		return "hover:shadow-[0_16px_45px_rgba(var(--color-primary-rgb),0.26)] hover:border-[color:var(--color-primary)]/70";
	} else if (borderColor.includes("blue")) {
		return "hover:shadow-[0_16px_45px_rgba(56,189,248,0.24)] hover:border-blue-400/70";
	} else if (borderColor.includes("green")) {
		return "hover:shadow-[0_16px_45px_rgba(74,222,128,0.26)] hover:border-[#0DA931]/70";
	} else if (borderColor.includes("orange")) {
		return "hover:shadow-[0_16px_45px_rgba(148,163,184,0.22)] hover:border-orange-400/70";
	} else if (borderColor.includes("red")) {
		return "hover:shadow-[0_16px_45px_rgba(248,113,113,0.24)] hover:border-red-400/70";
	}
	return "hover:shadow-[0_16px_45px_rgba(148,163,184,0.22)]";
};

const getAccentGradient = (borderColor: string) => {
	if (
		borderColor.includes("var(--color-primary)") ||
		borderColor.includes("primary")
	) {
		return "from-[rgba(var(--color-primary-rgb),0.14)] via-[rgba(var(--color-primary-rgb),0.06)] to-transparent";
	} else if (borderColor.includes("purple")) {
		return "from-fuchsia-500/14 via-violet-500/6 to-transparent";
	} else if (borderColor.includes("blue")) {
		return "from-sky-500/14 via-sky-500/6 to-transparent";
	} else if (borderColor.includes("green")) {
		return "from-emerald-500/14 via-emerald-500/6 to-transparent";
	} else if (borderColor.includes("orange")) {
		return "from-amber-500/14 via-amber-500/6 to-transparent";
	} else if (borderColor.includes("red")) {
		return "from-rose-500/14 via-rose-500/6 to-transparent";
	}
	return "from-white/12 via-white/5 to-transparent";
};

export default function ConfigCardButton({
	title,
	icon,
	description,
	borderColor,
	badge,
	onClick,
	className,
	preview,
}: ConfigCardButtonProps) {
	const accentGradient = getAccentGradient(borderColor);

	return (
		<button
			onClick={onClick}
			className={cn(
				"relative overflow-hidden",
				// Base card styling (replaces glass-card)
				"bg-[color:var(--color-surface)]/40 backdrop-blur",
				// Border and shape
				"rounded-2xl border",
				borderColor,
				// Hover and interaction states
				"group transition-all duration-300 cursor-pointer",
				"hover:scale-[1.02]",
				"active:scale-[0.98]",
				// Color-specific hover effects
				getColorEffects(borderColor),
				// Layout
				"w-full text-left min-h-[160px] shadow-[0_18px_55px_rgba(12,10,25,0.28)]",
				className,
			)}
		>
			<span
				className={cn(
					"pointer-events-none absolute inset-0 opacity-50 transition-opacity duration-500",
					"bg-gradient-to-br",
					accentGradient,
					"group-hover:opacity-75",
				)}
				aria-hidden="true"
			/>

			<span
				className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.05),transparent_55%)] opacity-40"
				aria-hidden="true"
			/>

			{/* Header */}
			<div className="relative z-[1] px-6 py-5 border-b border-[color:var(--color-border)]/25 bg-black/15 backdrop-blur-sm">
				<div className="flex items-start gap-3">
					<div className="p-3 rounded-xl bg-slate-100 flex-shrink-0 border border-slate-200 shadow-inner">
						{icon}
					</div>
					<div className="flex-1 min-w-0">
						<h3 className="text-base font-semibold text-slate-900 flex items-center gap-2 leading-tight">
							{title}
							{badge}
						</h3>
						<p className="text-sm text-[color:var(--color-text-muted)] mt-1 leading-tight">
							{description}
						</p>
					</div>
					<div className="flex-shrink-0 opacity-60 group-hover:opacity-100 transition-opacity">
						<ChevronRight className="w-4 h-4 text-[color:var(--color-text-muted)]" />
					</div>
				</div>
			</div>

			{/* Preview Content Area */}
			<div className="relative z-[1] p-6 flex-1 flex items-center justify-center min-h-[96px] bg-black/20">
				{preview ? (
					<div className="w-full">{preview}</div>
				) : (
					<div className="text-sm text-slate-600 text-center">
						Click to configure
					</div>
				)}
			</div>
		</button>
	);
}
