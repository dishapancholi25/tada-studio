"use client";

import { Clock, Settings } from "lucide-react";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import Toggle from "@/components/ui/Toggle";

interface WebSearchAdvancedSectionProps {
	searchProvider: string;
	timeoutSeconds: number;
	onTimeoutSecondsChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
	includeRawContent: boolean;
	onIncludeRawContentToggle: () => void;
}

export default function WebSearchAdvancedSection({
	searchProvider,
	timeoutSeconds,
	onTimeoutSecondsChange,
	includeRawContent,
	onIncludeRawContentToggle,
}: WebSearchAdvancedSectionProps) {
	const isTavily = searchProvider === "tavily";

	const inputClass =
		"flex-1 rounded-[4px] border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-400/40";

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex min-w-0 items-start gap-3">
						<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
							<Settings className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div className="min-w-0">
							<h3 className="text-lg font-semibold text-gray-900">
								Advanced Settings
							</h3>
							<p className="text-sm text-gray-600">
								Performance and content options
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div className="space-y-4">
						<div className="flex items-center gap-2">
							<Clock className="h-4 w-4 text-orange-600" />
							<h4 className="text-sm font-semibold capitalize tracking-wide text-gray-900">
								Performance
							</h4>
						</div>

						<div className="rounded-[4px] border border-gray-200 bg-slate-50 p-4">
							<div className="mb-3 flex items-center gap-2">
								<label
									htmlFor="timeout-input"
									className="block text-sm font-semibold text-gray-900"
								>
									Request Timeout
								</label>
								<InfoTooltip text="Maximum time to wait for search results (1-60 seconds)" />
							</div>
							<div className="flex flex-wrap items-center gap-3">
								<input
									id="timeout-input"
									type="number"
									value={timeoutSeconds}
									onChange={onTimeoutSecondsChange}
									min="1"
									max="60"
									className={inputClass}
									placeholder="10"
								/>
								<span className="text-sm font-medium text-gray-600">
									seconds
								</span>
							</div>
						</div>
					</div>

					{isTavily && (
						<div className="space-y-4">
							<div className="flex items-center gap-2">
								<Settings className="h-4 w-4 text-orange-600" />
								<h4 className="text-sm font-semibold capitalize tracking-wide text-gray-900">
									Content Options
								</h4>
							</div>

							<div className="flex items-center justify-between rounded-[4px] border border-gray-200 bg-slate-50 p-3.5">
								<div className="flex items-center gap-2">
									<label
										htmlFor="include-raw-content-toggle"
										className="text-sm font-semibold text-gray-900"
									>
										Include Raw Content
									</label>
									<InfoTooltip text="Include raw page content in results. This provides more detail but increases response size significantly." />
								</div>
								<Toggle
									checked={includeRawContent}
									onChange={onIncludeRawContentToggle}
								/>
							</div>

							{includeRawContent && (
								<div className="rounded-[4px] border border-amber-300 bg-white p-3 shadow-sm">
									<p className="text-xs text-amber-950">
										Raw content will significantly increase response size and
										processing time.
									</p>
								</div>
							)}
						</div>
					)}

					<div className="rounded-[4px] border border-orange-400 bg-white p-4 shadow-sm">
						<div className="mb-1 flex items-center gap-2">
							<Settings className="h-4 w-4 text-orange-600" />
							<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
								Current Settings
							</span>
						</div>
						<div className="mt-2 space-y-1 text-sm text-gray-800">
							<div>
								Timeout:{" "}
								<span className="font-medium text-gray-900">
									{timeoutSeconds}s
								</span>
							</div>
							{isTavily && (
								<div>
									Raw Content:{" "}
									<span className="font-medium text-gray-900">
										{includeRawContent ? "Enabled" : "Disabled"}
									</span>
								</div>
							)}
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
