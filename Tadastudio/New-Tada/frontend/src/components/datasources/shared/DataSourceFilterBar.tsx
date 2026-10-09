"use client";

import { Search } from "lucide-react";
import type React from "react";
import FormInput from "@/components/ui/FormInput";

export interface FilterTab {
	key: string;
	label: string;
}

interface DataSourceFilterBarProps {
	filterTabs: FilterTab[];
	activeFilter: string;
	onFilterChange: (filter: string) => void;
	searchTerm: string;
	onSearchChange: (term: string) => void;
	searchPlaceholder?: string;
	rightSlot?: React.ReactNode;
	className?: string;
}

export default function DataSourceFilterBar({
	filterTabs,
	activeFilter,
	onFilterChange,
	searchTerm,
	onSearchChange,
	searchPlaceholder = "Search...",
	rightSlot,
	className = "",
}: DataSourceFilterBarProps) {
	return (
		<div className={`flex flex-col gap-3 ${className}`}>
			{/* Filter tabs + optional right slot */}
			<div className="flex items-center justify-between gap-3">
				<div className="flex gap-2">
					{filterTabs.map((tab) => (
						<button
							key={tab.key}
							type="button"
							onClick={() => onFilterChange(tab.key)}
							className="rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 hover:border-orange-400 hover:bg-white hover:text-slate-900"
							style={{
								color:
									activeFilter === tab.key
										? "#ffffff"
										: "var(--color-text-primary)",
								background:
									activeFilter === tab.key
										? "#f97316"
										: "#ffffff",
								border:
									activeFilter === tab.key
										? "1px solid rgba(249, 115, 22, 0.65)"
										: "1px solid rgba(249, 115, 22, 0.18)",
							}}
						>
							{tab.label}
						</button>
					))}
				</div>
				{rightSlot && <div className="flex items-center gap-2">{rightSlot}</div>}
			</div>

			{/* Search bar */}
			<div className="relative">
				<Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-[color:var(--color-text-muted)]" />
				<FormInput
					className="pl-10"
					placeholder={searchPlaceholder}
					value={searchTerm}
					onChange={(e) => onSearchChange(e.target.value)}
				/>
			</div>
		</div>
	);
}
