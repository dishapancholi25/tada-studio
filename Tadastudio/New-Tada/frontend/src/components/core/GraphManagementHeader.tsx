"use client";

import {
	ArrowUpDown,
	Calendar,
	FileText,
	Plus,
	SortAsc,
	Type,
	X,
} from "lucide-react";
import React, { useMemo } from "react";
import Dropdown, { type DropdownOption } from "@/components/ui/Dropdown";
import FormInput from "@/components/ui/FormInput";

interface GraphManagementHeaderProps {
	activeTab: "create" | "load";
	searchQuery: string;
	onSearchChange: (query: string) => void;
	sortOption: "created" | "updated" | "alphabetical";
	onSortOptionChange: (option: "created" | "updated" | "alphabetical") => void;
	sortDirection: "asc" | "desc";
	onSortDirectionToggle: () => void;
	onClose: () => void;
	mode?: "modal" | "page";
	onTabChange?: (tab: "create" | "load") => void;
}

const GraphManagementHeader = React.memo(function GraphManagementHeader({
	activeTab,
	searchQuery,
	onSearchChange,
	sortOption,
	onSortOptionChange,
	sortDirection,
	onSortDirectionToggle,
	onClose,
	mode = "modal",
	onTabChange,
}: GraphManagementHeaderProps) {
	// Define sort options for dropdown
	const sortOptions: DropdownOption[] = useMemo(
		() => [
			{
				value: "created",
				label: "Sort by Created Date",
				description: "Newest or oldest first",
				icon: <Calendar className="w-4 h-4" />,
			},
			{
				value: "updated",
				label: "Sort by Updated Date",
				description: "Recently modified",
				icon: <Calendar className="w-4 h-4" />,
			},
			{
				value: "alphabetical",
				label: "Sort Alphabetically",
				description: "A to Z or Z to A",
				icon: <Type className="w-4 h-4" />,
			},
		],
		[],
	);

	return (
		<div className="flex-none rounded-t-3xl border-b border-gray-200 bg-white">
			{/* Row 1: Title and Close Button */}
			<div className="flex items-center justify-between px-6 pt-5 pb-4">
				<div className="flex items-center gap-3">
					<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-orange-100 border border-orange-200">
						<FileText className="w-5 h-5 text-orange-600" />
					</div>
					<h2 className="text-lg font-semibold text-gray-900 tracking-tight">
						{mode === "page" ? "My Workflows" : "Workflow Management"}
					</h2>
				</div>

				{mode === "page" && activeTab === "load" && onTabChange && (
					<button
						onClick={() => onTabChange("create")}
						className="flex items-center gap-2 px-4 py-2 rounded-lg border border-orange-500 bg-orange-500 text-white hover:bg-orange-600 transition-all focus-visible:outline-none font-medium text-sm"
					>
						<Plus className="w-4 h-4" />
						<span>Create New</span>
					</button>
				)}
				{mode === "modal" && (
					<button
						onClick={onClose}
						className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
					>
						<X className="w-4 h-4" />
					</button>
				)}
			</div>

			{/* Row 2: Controls Bar (Only for Load Tab) */}
			{activeTab === "load" && (
				<div className="flex items-center gap-2 px-6 pb-4">
					{/* Sort Dropdown — orange trigger */}
					<div className="w-52">
						<Dropdown
							value={sortOption}
							onChange={(value) =>
								onSortOptionChange(
									value as "created" | "updated" | "alphabetical",
								)
							}
							options={sortOptions}
							showSelectedIndicator={true}
							align="start"
							width={240}
							menuAppearance="light"
							triggerClassName="!py-2 !px-3 !bg-white !border-orange-300 !text-slate-900 hover:!border-orange-400 hover:!bg-white focus:!border-orange-500 focus:!ring-orange-500/20 [&_svg]:!text-orange-600 [&_span]:!text-slate-900 [&_p]:!text-slate-500"
							dropdownClassName="!border-orange-300 !bg-white"
							optionClassName="hover:!bg-white hover:!text-orange-700 aria-selected:!bg-white aria-selected:!text-orange-700"
						/>
					</div>

					{/* Sort Direction Toggle — orange */}
					<button
						onClick={onSortDirectionToggle}
						className="p-2 rounded-lg bg-orange-500 border border-orange-500 text-white hover:bg-orange-600 transition-colors shrink-0"
						title={`Sort ${sortDirection === "asc" ? "ascending" : "descending"}`}
					>
						<ArrowUpDown
							className={`w-4 h-4 transition-transform duration-300 ${sortDirection === "asc" ? "" : "rotate-180"}`}
						/>
					</button>

					{/* Search Input — orange border */}
					<div className="flex-1">
						<FormInput
							value={searchQuery}
							onChange={(e) => onSearchChange(e.target.value)}
							placeholder="Search workflows..."
							className="!bg-white !border-orange-300 !text-slate-900 placeholder:!text-slate-400 hover:!border-orange-400 focus:!border-orange-500 focus:!ring-orange-500/20 !transition-all !duration-200"
						/>
					</div>
				</div>
			)}
		</div>
	);
});

export default GraphManagementHeader;
