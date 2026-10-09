"use client";

import type React from "react";
import { useCallback, useRef } from "react";
import { cn } from "@/lib/utils";

interface SidebarItem {
	id: string;
	label: string;
	icon?: React.ReactNode;
	description?: string;
	disabled?: boolean;
}

interface ConfigSidebarProps {
	items: SidebarItem[];
	activeItem: string;
	onChange: (id: string) => void;
	collapsed?: boolean;
	/** Light sidebar for orange/white modals (e.g. File Read). Default preserves legacy dark styling. */
	variant?: "default" | "light";
}

export default function ConfigSidebar({
	items,
	activeItem,
	onChange,
	collapsed = false,
	variant = "default",
}: ConfigSidebarProps) {
	const itemRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			const currentIndex = items.findIndex((item) => item.id === activeItem);
			let nextIndex = -1;

			if (e.key === "ArrowDown") {
				e.preventDefault();
				nextIndex = currentIndex + 1;
				while (nextIndex < items.length && items[nextIndex].disabled) {
					nextIndex++;
				}
				if (nextIndex >= items.length) return;
			} else if (e.key === "ArrowUp") {
				e.preventDefault();
				nextIndex = currentIndex - 1;
				while (nextIndex >= 0 && items[nextIndex].disabled) {
					nextIndex--;
				}
				if (nextIndex < 0) return;
			} else {
				return;
			}

			const nextItem = items[nextIndex];
			if (nextItem) {
				onChange(nextItem.id);
				itemRefs.current.get(nextItem.id)?.focus();
			}
		},
		[items, activeItem, onChange],
	);

	const isLight = variant === "light";

	return (
		<nav
			className={cn(
				"relative flex flex-none flex-col gap-1.5 overflow-hidden py-4 transition-all duration-200",
				isLight
					? "border-r border-slate-200 bg-white"
					: "bg-[rgba(0,0,0,0.15)]",
				collapsed ? "w-16 px-2" : "w-[200px] px-2",
			)}
			role="tablist"
			aria-orientation="vertical"
			onKeyDown={handleKeyDown}
		>
			{items.map((item) => {
				const isActive = item.id === activeItem;
				return (
					<button
						key={item.id}
						data-tutorial={`config-tab-${item.id}`}
						ref={(el) => {
							if (el) {
								itemRefs.current.set(item.id, el);
							} else {
								itemRefs.current.delete(item.id);
							}
						}}
						type="button"
						role="tab"
						aria-selected={isActive}
						aria-disabled={item.disabled}
						tabIndex={isActive ? 0 : -1}
						disabled={item.disabled}
						onClick={() => !item.disabled && onChange(item.id)}
						title={collapsed ? item.label : undefined}
						className={cn(
							"group relative flex items-center gap-2.5 rounded-[4px] text-xs font-medium transition-all duration-300 ease-out",
							collapsed ? "justify-center px-2 py-3" : "px-3.5 py-3",
							item.disabled && "cursor-not-allowed opacity-40",
							isLight
								? isActive
									? "border border-orange-500 bg-white text-slate-900 shadow-sm"
									: "border border-transparent text-slate-800 hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
								: isActive
									? "border-l-2 border-l-[color:var(--color-primary)] border-y border-y-transparent border-r border-r-transparent bg-gradient-to-r from-[rgba(var(--color-primary-rgb),0.12)] to-transparent text-[color:var(--color-primary)]"
									: "border border-transparent text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-hover)]/40 hover:text-slate-900",
							"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]",
						)}
					>
						{item.icon && (
							<span
								className={cn(
									"flex h-8 w-8 shrink-0 items-center justify-center rounded-[4px] transition-all [&>svg]:h-[18px] [&>svg]:w-[18px]",
									isLight
										? isActive
											? "border border-orange-200 bg-orange-100 text-orange-600"
											: "text-slate-600 group-hover:text-slate-900"
										: isActive
											? "bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)]"
											: "text-[color:var(--color-text-muted)]",
								)}
							>
								{item.icon}
							</span>
						)}
						{!collapsed && (
							<span className="min-w-0 truncate text-[13px] font-semibold tracking-wide">
								{item.label}
							</span>
						)}
					</button>
				);
			})}
		</nav>
	);
}
