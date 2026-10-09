"use client";

import type React from "react";
import { useCallback } from "react";

export interface Tab {
	id: string;
	label: string;
	content: React.ReactNode;
	icon?: React.ReactNode;
	disabled?: boolean;
}

interface TabContainerProps {
	tabs: Tab[];
	activeTab: string;
	onTabChange: (tabId: string) => void;
	className?: string;
	isDarkMode?: boolean;
}

export default function TabContainer({
	tabs,
	activeTab,
	onTabChange,
	className = "",
	isDarkMode = true,
}: TabContainerProps) {
	const activeTabContent = tabs.find((tab) => tab.id === activeTab)?.content;

	// Factory function for tab click handlers
	const createTabClickHandler = useCallback(
		(tab: Tab) => () => {
			if (!tab.disabled) {
				onTabChange(tab.id);
			}
		},
		[onTabChange],
	);

	return (
		<div className={`flex flex-col flex-1 min-h-0 ${className}`}>
			{/* Tab Navigation */}
			<div
				className={`flex gap-2 p-3 border-b-2 ${
					isDarkMode
						? "bg-[color:var(--color-surface)]/40 border-[color:var(--color-primary)]/25"
						: "bg-white border-slate-200"
				}`}
			>
				{tabs.map((tab) => (
					<button
						key={tab.id}
						onClick={createTabClickHandler(tab)}
						disabled={tab.disabled}
						className={`group relative flex-1 px-6 py-3.5 text-sm font-medium rounded-xl overflow-hidden transition-all duration-300 flex items-center justify-center gap-2 ${
							activeTab === tab.id
								? isDarkMode
									? "bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.2)] via-[rgba(var(--color-primary-rgb),0.1)] to-transparent border border-[rgba(var(--color-primary-rgb),0.5)] text-white shadow-[0_12px_30px_rgba(15,23,42,0.28)]"
									: "border border-orange-400 bg-white text-orange-700 shadow-sm"
								: isDarkMode
									? "border border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/25 text-[color:var(--color-text-muted)] hover:bg-gradient-to-br hover:from-white/10 hover:via-white/5 hover:to-transparent hover:border-[color:var(--color-border)]/70 hover:text-[color:var(--color-primary)] hover:-translate-y-0.5 hover:shadow-[0_10px_30px_rgba(22,31,55,0.35)]"
									: "border border-slate-200 bg-white text-slate-600 hover:border-orange-400 hover:bg-white hover:text-slate-900 hover:-translate-y-0.5 hover:shadow-sm"
						} ${tab.disabled ? "cursor-not-allowed opacity-50" : ""}`}
					>
						{/* Background gradient effect on hover (dark mode only — light mode stays solid white) */}
						{isDarkMode && activeTab !== tab.id && (
							<div className="absolute inset-0 bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.05)] via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
						)}

						{tab.icon && <span className="relative z-10">{tab.icon}</span>}
						<span className="relative z-10">{tab.label}</span>

						{/* Active indicator glow */}
						{activeTab === tab.id && isDarkMode && (
							<div className="absolute inset-0 bg-gradient-to-r from-[rgba(var(--color-primary-rgb),0.1)] via-[rgba(var(--color-primary-rgb),0.05)] to-[rgba(var(--color-primary-rgb),0.1)] animate-pulse" />
						)}
					</button>
				))}
			</div>

			{/* Tab Content */}
			<div
				className={`flex-1 overflow-y-auto p-6 min-h-0 ${
					isDarkMode ? "bg-[color:var(--color-surface)]/10" : "bg-white"
				}`}
			>
				<div className="animate-fadeIn">{activeTabContent}</div>
			</div>
		</div>
	);
}
