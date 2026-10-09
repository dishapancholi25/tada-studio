"use client";

import { Key, Search } from "lucide-react";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import Toggle from "@/components/ui/Toggle";

interface WebSearchSearchSectionProps {
	searchProvider: string;
	onSearchProviderChange: (value: string) => void;
	apiKey: string;
	onApiKeyChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
	maxResults: number;
	onMaxResultsChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
	searchDepth: string;
	onSearchDepthChange: (value: string) => void;
	includeImages: boolean;
	onIncludeImagesToggle: () => void;
	includeAnswer: boolean;
	onIncludeAnswerToggle: () => void;
}

export default function WebSearchSearchSection({
	searchProvider,
	onSearchProviderChange,
	apiKey,
	onApiKeyChange,
	maxResults,
	onMaxResultsChange,
	searchDepth,
	onSearchDepthChange,
	includeImages,
	onIncludeImagesToggle,
	includeAnswer,
	onIncludeAnswerToggle,
}: WebSearchSearchSectionProps) {
	const providerOptions = [
		{
			value: "duckduckgo",
			label: "DuckDuckGo",
			description: "Free, No API needed",
		},
		{ value: "tavily", label: "Tavily", description: "Premium, AI-optimized" },
	];

	const searchDepthOptions = [
		{ value: "basic", label: "Basic", description: "Faster, standard results" },
		{
			value: "advanced",
			label: "Advanced",
			description: "Deeper, more comprehensive",
		},
	];

	const inputClass =
		"w-full rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-400/40";

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex min-w-0 items-start gap-3">
						<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
							<Search className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div className="min-w-0">
							<h3 className="text-lg font-semibold text-gray-900">
								Search Configuration
							</h3>
							<p className="text-sm text-gray-600">
								Configure provider and search settings
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div>
						<div className="mb-3 flex items-center gap-2">
							<label
								id="search-provider-label"
								className="block text-sm font-semibold text-gray-900"
							>
								Search Provider
							</label>
							<InfoTooltip text="Choose your search provider. DuckDuckGo is free, Tavily requires an API key but provides AI-optimized results." />
						</div>
						<div
							className="grid grid-cols-2 gap-3"
							role="radiogroup"
							aria-labelledby="search-provider-label"
						>
							{providerOptions.map((provider) => (
								<button
									type="button"
									key={provider.value}
									onClick={() => onSearchProviderChange(provider.value)}
									className={`rounded-[4px] border-2 p-4 text-left transition-colors duration-200 ${
										searchProvider === provider.value
											? "border-orange-500 bg-white shadow-sm"
											: "border-transparent bg-white hover:border-orange-400 hover:bg-slate-50"
									}`}
								>
									<div className="font-semibold text-gray-900">
										{provider.label}
									</div>
									<div className="mt-1 text-xs text-gray-600">
										{provider.description}
									</div>
								</button>
							))}
						</div>
					</div>

					{searchProvider === "tavily" && (
						<div>
							<div className="mb-3 flex items-center gap-2">
								<label
									htmlFor="tavily-api-key"
									className="block text-sm font-semibold text-gray-900"
								>
									<Key className="mr-1 inline-block h-4 w-4" />
									Tavily API Key
								</label>
								<InfoTooltip text="Get your API key from tavily.com. Required for Tavily search." />
							</div>
							<input
								id="tavily-api-key"
								type="password"
								value={apiKey}
								onChange={onApiKeyChange}
								className={inputClass}
								placeholder="Enter your Tavily API key"
							/>
							{!apiKey && (
								<div className="mt-2 rounded-[4px] border border-blue-200 bg-white p-3 shadow-sm">
									<p className="text-xs text-blue-900">
										API key required for Tavily. Get one at tavily.com
									</p>
								</div>
							)}
						</div>
					)}

					<div>
						<div className="mb-3 flex items-center gap-2">
							<label
								htmlFor="num-results-range"
								className="block text-sm font-semibold text-gray-900"
							>
								Maximum Results
							</label>
							<InfoTooltip text="Maximum number of search results to return (1-20)" />
						</div>
						<div className="flex items-center gap-4">
							<input
								id="num-results-range"
								type="range"
								min="1"
								max="20"
								value={maxResults}
								onChange={onMaxResultsChange}
								className="h-2 flex-1 cursor-pointer appearance-none rounded-lg bg-slate-200 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-orange-600 [&::-webkit-slider-thumb]:cursor-pointer"
							/>
							<span className="w-12 rounded-[4px] border border-gray-200 bg-white px-3 py-1 text-center font-semibold text-gray-900">
								{maxResults}
							</span>
						</div>
					</div>

					{searchProvider === "tavily" && (
						<div>
							<div className="mb-3 flex items-center gap-2">
								<label
									id="search-depth-label"
									className="block text-sm font-semibold text-gray-900"
								>
									Search Depth
								</label>
							</div>
							<div
								className="grid grid-cols-2 gap-3"
								role="radiogroup"
								aria-labelledby="search-depth-label"
							>
								{searchDepthOptions.map((depth) => (
									<button
										type="button"
										key={depth.value}
										onClick={() => onSearchDepthChange(depth.value)}
										className={`rounded-[4px] border-2 p-3.5 text-left transition-colors duration-200 ${
											searchDepth === depth.value
												? "border-orange-500 bg-white shadow-sm"
												: "border-transparent bg-white hover:border-orange-400 hover:bg-slate-50"
										}`}
									>
										<div className="text-sm font-semibold text-gray-900">
											{depth.label}
										</div>
										<div className="mt-1 text-xs text-gray-600">
											{depth.description}
										</div>
									</button>
								))}
							</div>
						</div>
					)}

					<div className="space-y-4">
						<div className="flex items-center justify-between rounded-[4px] border border-gray-200 bg-slate-50 p-3.5">
							<div className="flex items-center gap-2">
								<label
									htmlFor="include-images-toggle"
									className="text-sm font-semibold text-gray-900"
								>
									Include Images
								</label>
								<InfoTooltip text="Include image URLs in search results" />
							</div>
							<Toggle checked={includeImages} onChange={onIncludeImagesToggle} />
						</div>

						{searchProvider === "tavily" && (
							<div className="flex items-center justify-between rounded-[4px] border border-gray-200 bg-slate-50 p-3.5">
								<div className="flex items-center gap-2">
									<label
										htmlFor="include-answer-toggle"
										className="text-sm font-semibold text-gray-900"
									>
										Include AI Answer
									</label>
									<InfoTooltip text="Tavily can generate an AI-powered answer based on search results" />
								</div>
								<Toggle checked={includeAnswer} onChange={onIncludeAnswerToggle} />
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
