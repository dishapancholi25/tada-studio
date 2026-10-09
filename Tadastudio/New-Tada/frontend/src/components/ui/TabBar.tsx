"use client";

import clsx from "clsx";
import type React from "react";

type TabAccent =
	| "core"
	| "input"
	| "memory"
	| "output"
	| "orchestration"
	| "advanced";

export interface TabBarItem {
	id: string;
	label: string;
	icon?: React.ReactNode;
	description?: string;
	badge?: React.ReactNode;
	disabled?: boolean;
	accent?: TabAccent;
}

interface TabBarProps {
	tabs: TabBarItem[];
	activeTab: string;
	onChange: (tabId: string) => void;
	className?: string;
	equalWidth?: boolean;
	size?: "sm" | "md";
	variant?: "glass" | "subtle";
}

/**
 * TabBar renders a high-contrast, glassmorphism-inspired tab navigation row.
 * It supports optional icons, descriptions, and badges for each tab and exposes
 * sizing and layout controls for reuse across complex panels.
 */
export default function TabBar({
	tabs,
	activeTab,
	onChange,
	className = "",
	equalWidth = true,
	size = "md",
	variant = "glass",
}: TabBarProps) {
	const baseButton =
		"relative inline-flex flex-col items-center gap-1 rounded-xl border transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40";

	const sizeClasses = size === "sm" ? "px-4 py-2 text-xs" : "px-5 py-3 text-sm";

	const inactiveBase =
		"border-transparent bg-[rgba(17,24,39,0.55)] text-[color:var(--color-text-muted)] hover:-translate-y-[1px]";

	const containerClass =
		variant === "glass"
			? "relative overflow-hidden rounded-2xl border border-[rgba(var(--color-primary-rgb),0.3)] bg-[radial-gradient(circle_at_top,rgba(var(--color-primary-rgb),0.24),rgba(10,15,26,0.72)_55%)] p-1.5 shadow-[0_20px_55px_rgba(5,9,23,0.45)]"
			: "relative overflow-hidden rounded-2xl border-2 border-[color:var(--color-primary)]/30 bg-[color:var(--color-bg-secondary)] p-1.5 shadow-[0_12px_35px_rgba(0,0,0,0.55)]";

	const inactiveBaseSubtle =
		"border border-transparent bg-[color:var(--color-bg-secondary)] text-[color:var(--color-text-muted)]";

	const accentStylesGlass: Record<
		TabAccent | "coreDefault",
		{
			activeButton: string;
			inactiveButton: string;
			iconActive: string;
			iconInactive: string;
			glow: string;
			accentBar: string;
		}
	> = {
		coreDefault: {
			activeButton:
				"border-[rgba(var(--color-primary-rgb),0.55)] bg-[rgba(var(--color-primary-rgb),0.2)] text-white shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.28)]",
			inactiveButton:
				"hover:border-[rgba(var(--color-primary-rgb),0.3)] hover:bg-[rgba(var(--color-primary-rgb),0.12)] hover:text-slate-900 hover:shadow-[0_12px_28px_rgba(var(--color-primary-rgb),0.25)]",
			iconActive:
				"border-[rgba(var(--color-primary-rgb),0.4)] bg-[rgba(var(--color-primary-rgb),0.25)] text-white",
			iconInactive:
				"border-[rgba(var(--color-primary-rgb),0.15)] bg-[rgba(var(--color-primary-rgb),0.1)] text-[color:var(--color-text-secondary)]",
			glow: "bg-[radial-gradient(circle,_rgba(var(--color-primary-rgb),0.35),_transparent_70%)]",
			accentBar:
				"bg-[linear-gradient(90deg,transparent,rgba(var(--color-primary-rgb),0.32),transparent)]",
		},
		core: {
			activeButton:
				"border-[rgba(var(--color-primary-rgb),0.55)] bg-[rgba(var(--color-primary-rgb),0.2)] text-white shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.28)]",
			inactiveButton:
				"hover:border-[rgba(var(--color-primary-rgb),0.3)] hover:bg-[rgba(var(--color-primary-rgb),0.12)] hover:text-slate-900 hover:shadow-[0_12px_28px_rgba(var(--color-primary-rgb),0.25)]",
			iconActive:
				"border-[rgba(var(--color-primary-rgb),0.4)] bg-[rgba(var(--color-primary-rgb),0.25)] text-white",
			iconInactive:
				"border-[rgba(var(--color-primary-rgb),0.15)] bg-[rgba(var(--color-primary-rgb),0.1)] text-[color:var(--color-text-secondary)]",
			glow: "bg-[radial-gradient(circle,_rgba(var(--color-primary-rgb),0.35),_transparent_70%)]",
			accentBar:
				"bg-[linear-gradient(90deg,transparent,rgba(var(--color-primary-rgb),0.32),transparent)]",
		},
		input: {
			activeButton:
				"border-[rgba(56,189,248,0.6)] bg-[rgba(56,189,248,0.2)] text-white shadow-[0_15px_40px_rgba(56,189,248,0.28)]",
			inactiveButton:
				"hover:border-[rgba(56,189,248,0.35)] hover:bg-[rgba(56,189,248,0.12)] hover:text-slate-900 hover:shadow-[0_12px_26px_rgba(15,76,117,0.45)]",
			iconActive:
				"border-[rgba(56,189,248,0.45)] bg-[rgba(56,189,248,0.22)] text-white",
			iconInactive:
				"border-[rgba(56,189,248,0.18)] bg-[rgba(56,189,248,0.12)] text-sky-600",
			glow: "bg-[radial-gradient(circle,rgba(56,189,248,0.4),transparent_70%)]",
			accentBar:
				"bg-[linear-gradient(90deg,transparent,rgba(56,189,248,0.35),transparent)]",
		},
		memory: {
			activeButton:
				"border-[rgba(168,85,247,0.55)] bg-[rgba(168,85,247,0.2)] text-white shadow-[0_15px_40px_rgba(168,85,247,0.28)]",
			inactiveButton:
				"hover:border-[rgba(168,85,247,0.35)] hover:bg-[rgba(168,85,247,0.12)] hover:text-slate-900 hover:shadow-[0_12px_26px_rgba(92,52,157,0.45)]",
			iconActive:
				"border-[rgba(168,85,247,0.45)] bg-[rgba(168,85,247,0.22)] text-white",
			iconInactive:
				"border-[rgba(168,85,247,0.18)] bg-[rgba(168,85,247,0.12)] text-violet-600",
			glow: "bg-[radial-gradient(circle,rgba(168,85,247,0.38),transparent_70%)]",
			accentBar:
				"bg-[linear-gradient(90deg,transparent,rgba(168,85,247,0.35),transparent)]",
		},
		output: {
			activeButton:
				"border-[rgba(16,185,129,0.55)] bg-[rgba(16,185,129,0.18)] text-white shadow-[0_15px_40px_rgba(16,185,129,0.28)]",
			inactiveButton:
				"hover:border-[rgba(16,185,129,0.35)] hover:bg-[rgba(16,185,129,0.1)] hover:text-slate-900 hover:shadow-[0_12px_26px_rgba(4,94,71,0.45)]",
			iconActive:
				"border-[rgba(16,185,129,0.45)] bg-[rgba(16,185,129,0.22)] text-white",
			iconInactive:
				"border-[rgba(16,185,129,0.18)] bg-[rgba(16,185,129,0.12)] text-emerald-600",
			glow: "bg-[radial-gradient(circle,rgba(16,185,129,0.38),transparent_70%)]",
			accentBar:
				"bg-[linear-gradient(90deg,transparent,rgba(16,185,129,0.32),transparent)]",
		},
		orchestration: {
			activeButton:
				"border-[rgba(251,146,60,0.55)] bg-[rgba(251,146,60,0.2)] text-white shadow-[0_15px_40px_rgba(251,146,60,0.28)]",
			inactiveButton:
				"hover:border-[rgba(251,146,60,0.35)] hover:bg-[rgba(251,146,60,0.12)] hover:text-slate-900 hover:shadow-[0_12px_26px_rgba(120,53,15,0.45)]",
			iconActive:
				"border-[rgba(251,146,60,0.45)] bg-[rgba(251,146,60,0.22)] text-white",
			iconInactive:
				"border-[rgba(251,146,60,0.18)] bg-[rgba(251,146,60,0.12)] text-orange-200",
			glow: "bg-[radial-gradient(circle,rgba(251,146,60,0.4),transparent_70%)]",
			accentBar:
				"bg-[linear-gradient(90deg,transparent,rgba(251,146,60,0.35),transparent)]",
		},
		advanced: {
			activeButton:
				"border-[rgba(245,158,11,0.55)] bg-[rgba(245,158,11,0.2)] text-white shadow-[0_15px_40px_rgba(245,158,11,0.28)]",
			inactiveButton:
				"hover:border-[rgba(245,158,11,0.35)] hover:bg-[rgba(245,158,11,0.12)] hover:text-slate-900 hover:shadow-[0_12px_26px_rgba(120,69,5,0.45)]",
			iconActive:
				"border-[rgba(245,158,11,0.45)] bg-[rgba(245,158,11,0.22)] text-white",
			iconInactive:
				"border-[rgba(245,158,11,0.18)] bg-[rgba(245,158,11,0.12)] text-amber-700",
			glow: "bg-[radial-gradient(circle,rgba(245,158,11,0.4),transparent_70%)]",
			accentBar:
				"bg-[linear-gradient(90deg,transparent,rgba(245,158,11,0.35),transparent)]",
		},
	};

	const accentStylesSubtle: Record<
		TabAccent | "coreDefault",
		{
			activeButton: string;
			inactiveButton: string;
			iconActive: string;
			iconInactive: string;
			glow: string;
			accentBar: string;
		}
	> = {
		coreDefault: {
			activeButton:
				"border-[color:var(--color-primary)]/35 bg-[color:var(--color-surface)]/60 text-slate-900",
			inactiveButton: inactiveBaseSubtle,
			iconActive:
				"border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)]",
			iconInactive:
				"border-[color:var(--color-border)]/40 bg-[color:var(--color-bg-secondary)] text-[color:var(--color-text-secondary)]",
			glow: "bg-transparent",
			accentBar: "bg-transparent",
		},
		core: {
			activeButton:
				"border-[color:var(--color-primary)]/35 bg-[color:var(--color-surface)]/60 text-slate-900",
			inactiveButton: inactiveBaseSubtle,
			iconActive:
				"border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)]",
			iconInactive:
				"border-[color:var(--color-border)]/40 bg-[color:var(--color-bg-secondary)] text-[color:var(--color-text-secondary)]",
			glow: "bg-transparent",
			accentBar: "bg-transparent",
		},
		input: {
			activeButton:
				"border-[color:var(--color-primary)]/35 bg-[color:var(--color-surface)]/60 text-slate-900",
			inactiveButton: inactiveBaseSubtle,
			iconActive:
				"border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)]",
			iconInactive:
				"border-[color:var(--color-border)]/40 bg-[color:var(--color-bg-secondary)] text-[color:var(--color-text-secondary)]",
			glow: "bg-transparent",
			accentBar: "bg-transparent",
		},
		memory: {
			activeButton:
				"border-[color:var(--color-primary)]/35 bg-[color:var(--color-surface)]/60 text-slate-900",
			inactiveButton: inactiveBaseSubtle,
			iconActive:
				"border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)]",
			iconInactive:
				"border-[color:var(--color-border)]/40 bg-[color:var(--color-bg-secondary)] text-[color:var(--color-text-secondary)]",
			glow: "bg-transparent",
			accentBar: "bg-transparent",
		},
		output: {
			activeButton:
				"border-[color:var(--color-primary)]/35 bg-[color:var(--color-surface)]/60 text-slate-900",
			inactiveButton: inactiveBaseSubtle,
			iconActive:
				"border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)]",
			iconInactive:
				"border-[color:var(--color-border)]/40 bg-[color:var(--color-bg-secondary)] text-[color:var(--color-text-secondary)]",
			glow: "bg-transparent",
			accentBar: "bg-transparent",
		},
		orchestration: {
			activeButton:
				"border-[color:var(--color-primary)]/35 bg-[color:var(--color-surface)]/60 text-slate-900",
			inactiveButton: inactiveBaseSubtle,
			iconActive:
				"border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)]",
			iconInactive:
				"border-[color:var(--color-border)]/40 bg-[color:var(--color-bg-secondary)] text-[color:var(--color-text-secondary)]",
			glow: "bg-transparent",
			accentBar: "bg-transparent",
		},
		advanced: {
			activeButton:
				"border-[color:var(--color-primary)]/35 bg-[color:var(--color-surface)]/60 text-slate-900",
			inactiveButton: inactiveBaseSubtle,
			iconActive:
				"border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)]",
			iconInactive:
				"border-[color:var(--color-border)]/40 bg-[color:var(--color-bg-secondary)] text-[color:var(--color-text-secondary)]",
			glow: "bg-transparent",
			accentBar: "bg-transparent",
		},
	};

	const accentStyles =
		variant === "subtle" ? accentStylesSubtle : accentStylesGlass;
	const inactiveBaseApplied =
		variant === "subtle" ? inactiveBaseSubtle : inactiveBase;

	return (
		<div
			className={clsx(containerClass, className)}
		>
			{variant === "glass" && (
				<div className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.05),transparent_55%)]" />
			)}
			<div
				className={clsx(
					"relative z-10 flex flex-wrap gap-2",
					equalWidth ? "justify-between" : "justify-start",
				)}
				role="tablist"
			>
				{tabs.map((tab) => {
					const isActive = tab.id === activeTab;
					const accentKey = (tab.accent ?? "core") as TabAccent;
					const accent = accentStyles[accentKey] ?? accentStyles.coreDefault;

					return (
						<button
							key={tab.id}
							type="button"
							role="tab"
							aria-selected={isActive}
							aria-disabled={tab.disabled}
							disabled={tab.disabled}
							onClick={() => !tab.disabled && onChange(tab.id)}
							className={clsx(
								baseButton,
								sizeClasses,
								"group",
								equalWidth ? "flex-1 min-w-[120px]" : "min-w-[130px]",
								tab.disabled &&
									"opacity-50 cursor-not-allowed pointer-events-none",
								isActive
									? accent.activeButton
									: clsx(inactiveBaseApplied, accent.inactiveButton),
							)}
						>
							<span
								className={clsx(
									"absolute inset-x-2 bottom-1 h-px opacity-0 transition-opacity duration-200 group-hover:opacity-70",
									accent.accentBar,
								)}
							/>
							<span className="flex items-center gap-2">
								{tab.icon && (
									<span
										className={clsx(
											"flex h-7 w-7 items-center justify-center rounded-full border transition-colors duration-200",
											isActive ? accent.iconActive : accent.iconInactive,
										)}
									>
										{tab.icon}
									</span>
								)}
								<span className="text-sm font-semibold tracking-wide">
									{tab.label}
								</span>
								{tab.badge && (
									<span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-800 backdrop-blur">
										{tab.badge}
									</span>
								)}
							</span>
							{tab.description && (
								<span className="text-[11px] text-[color:var(--color-text-muted)]">
									{tab.description}
								</span>
							)}
							{isActive && (
								<span
									className={clsx(
										"absolute inset-x-3 -bottom-[6px] h-[10px] rounded-full blur-[6px]",
										accent.glow,
									)}
								/>
							)}
							<span
								className={clsx(
									"absolute inset-0 rounded-xl border border-white/0 transition-opacity duration-200 pointer-events-none",
									isActive
										? "opacity-70 border-slate-100"
										: "opacity-0 group-hover:opacity-20 border-slate-100",
								)}
							/>
						</button>
					);
				})}
			</div>
		</div>
	);
}
