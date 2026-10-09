"use client";

import { Clock, Filter, Globe, Shield } from "lucide-react";
import Dropdown from "@/components/ui/Dropdown";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";

interface WebSearchFiltersSectionProps {
	searchProvider: string;
	region: string;
	onRegionChange: (value: string) => void;
	timeRange: string;
	onTimeRangeChange: (value: string) => void;
	safeSearch: string;
	onSafeSearchChange: (value: string) => void;
}

export default function WebSearchFiltersSection({
	searchProvider,
	region,
	onRegionChange,
	timeRange,
	onTimeRangeChange,
	safeSearch,
	onSafeSearchChange,
}: WebSearchFiltersSectionProps) {
	const regionOptions = [
		{ value: "wt-wt", label: "No Region" },
		{ value: "us-en", label: "United States" },
		{ value: "uk-en", label: "United Kingdom" },
		{ value: "de-de", label: "Germany" },
		{ value: "fr-fr", label: "France" },
		{ value: "es-es", label: "Spain" },
		{ value: "it-it", label: "Italy" },
		{ value: "jp-jp", label: "Japan" },
		{ value: "cn-zh", label: "China" },
		{ value: "in-en", label: "India" },
		{ value: "br-pt", label: "Brazil" },
		{ value: "ca-en", label: "Canada" },
		{ value: "au-en", label: "Australia" },
	];

	const timeRangeOptions = [
		{ value: "", label: "Any Time" },
		{ value: "d", label: "Past Day" },
		{ value: "w", label: "Past Week" },
		{ value: "m", label: "Past Month" },
		{ value: "y", label: "Past Year" },
	];

	const safeSearchOptions = [
		{ value: "off", label: "Off" },
		{ value: "moderate", label: "Moderate" },
		{ value: "strict", label: "Strict" },
	];

	const isDuckDuckGo = searchProvider === "duckduckgo";

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex min-w-0 items-start gap-3">
						<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
							<Filter className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div className="min-w-0">
							<h3 className="text-lg font-semibold text-gray-900">
								Search Filters
							</h3>
							<p className="text-sm text-gray-600">
								Refine results by region, time, and content
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					{isDuckDuckGo ? (
						<>
							<div>
								<div className="mb-3 flex items-center gap-2">
									<label
										htmlFor="region-select"
										className="block text-sm font-semibold text-gray-900"
									>
										<Globe className="mr-1 inline-block h-4 w-4" />
										Region
									</label>
									<InfoTooltip text="Filter results by geographic region" />
								</div>
								<Dropdown
									value={region}
									onChange={onRegionChange}
									options={regionOptions}
									placeholder="Select region"
									menuAppearance="light"
								/>
							</div>

							<div>
								<div className="mb-3 flex items-center gap-2">
									<label
										htmlFor="time-range-select"
										className="block text-sm font-semibold text-gray-900"
									>
										<Clock className="mr-1 inline-block h-4 w-4" />
										Time Range
									</label>
									<InfoTooltip text="Filter results by publication date" />
								</div>
								<Dropdown
									value={timeRange}
									onChange={onTimeRangeChange}
									options={timeRangeOptions}
									placeholder="Select time range"
									menuAppearance="light"
								/>
							</div>
						</>
					) : (
						<div className="rounded-[4px] border border-gray-200 bg-slate-50 p-6 text-center">
							<p className="text-sm text-gray-600">
								Region and time range filters are only available for DuckDuckGo
								searches.
							</p>
						</div>
					)}

					<div>
						<div className="mb-3 flex items-center gap-2">
							<label
								id="safe-search-label"
								className="block text-sm font-semibold text-gray-900"
							>
								<Shield className="mr-1 inline-block h-4 w-4" />
								Safe Search
							</label>
							<InfoTooltip text="Filter explicit content from search results" />
						</div>
						<div
							className="grid grid-cols-3 gap-2.5"
							role="radiogroup"
							aria-labelledby="safe-search-label"
						>
							{safeSearchOptions.map((option) => (
								<button
									type="button"
									key={option.value}
									onClick={() => onSafeSearchChange(option.value)}
									className={`rounded-[4px] border-2 px-4 py-3 text-sm font-semibold transition-colors duration-200 ${
										safeSearch === option.value
											? "border-orange-500 bg-white text-gray-900 shadow-sm"
											: "border-transparent bg-white text-gray-600 hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
									}`}
								>
									{option.label}
								</button>
							))}
						</div>
					</div>

					{isDuckDuckGo && (region !== "wt-wt" || timeRange !== "") && (
						<div className="rounded-[4px] border border-orange-400 bg-white p-4 shadow-sm">
							<div className="mb-1 flex items-center gap-2">
								<Filter className="h-4 w-4 text-orange-600" />
								<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
									Active Filters
								</span>
							</div>
							<div className="mt-2 space-y-1 text-sm text-gray-800">
								{region !== "wt-wt" && (
									<div>
										Region:{" "}
										<span className="font-medium text-gray-900">
											{regionOptions.find((r) => r.value === region)?.label}
										</span>
									</div>
								)}
								{timeRange && (
									<div>
										Time:{" "}
										<span className="font-medium text-gray-900">
											{
												timeRangeOptions.find((t) => t.value === timeRange)
													?.label
											}
										</span>
									</div>
								)}
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
