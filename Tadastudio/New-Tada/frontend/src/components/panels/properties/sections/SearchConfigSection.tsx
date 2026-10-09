"use client";

import { Search } from "lucide-react";
import Dropdown from "../../../ui/Dropdown";
import InfoTooltip from "../../../ui/InfoTooltipPortal";
import NumberInput from "../../../ui/NumberInput";
import Toggle from "../../../ui/Toggle";

interface SearchConfigSectionProps {
	searchK: number;
	onSearchKChange: (v: number) => void;
	hybridSearchEnabled: boolean;
	onHybridSearchEnabledChange: (v: boolean) => void;
	searchMode: string;
	onSearchModeChange: (v: string) => void;
	keywordWeight: number;
	onKeywordWeightChange: (v: number) => void;
	citationFormat: string;
	onCitationFormatChange: (v: string) => void;
}

const dropdownTriggerClass =
	"rounded-[4px] border border-slate-200 bg-white text-slate-900 hover:border-orange-400 hover:bg-slate-50";

export default function SearchConfigSection({
	searchK,
	onSearchKChange,
	hybridSearchEnabled,
	onHybridSearchEnabledChange,
	searchMode,
	onSearchModeChange,
	keywordWeight,
	onKeywordWeightChange,
	citationFormat,
	onCitationFormatChange,
}: SearchConfigSectionProps) {
	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100 text-orange-600">
							<Search className="h-6 w-6" aria-hidden />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Search Configuration
							</h3>
							<p className="text-sm text-slate-600">
								Configure search behavior and output format
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div>
						<div className="mb-3 flex items-center gap-2">
							<label className="text-sm font-semibold text-slate-800">
								Number of Results
							</label>
							<InfoTooltip text="Number of relevant chunks to retrieve (recommended: 3-10)" />
						</div>
						<NumberInput
							value={searchK}
							onChange={onSearchKChange}
							min={1}
							max={20}
							step={1}
							appearance="light"
						/>
					</div>

					<div className="flex items-center justify-between gap-4 rounded-[4px] border border-slate-200 bg-white p-4 transition-colors hover:border-orange-400">
						<div>
							<h4 className="text-sm font-semibold text-slate-900">
								Enable Hybrid Search
							</h4>
							<p className="mt-1 text-xs text-slate-600">
								Combine vector and keyword search for better results
							</p>
						</div>
						<Toggle
							checked={hybridSearchEnabled}
							onChange={onHybridSearchEnabledChange}
							size="md"
							activeColor="#ea580c"
						/>
					</div>

					{hybridSearchEnabled && (
						<div>
							<div className="mb-3 flex items-center gap-2">
								<label
									htmlFor="search-mode-select"
									className="text-sm font-semibold text-slate-800"
								>
									Search Mode
								</label>
								<InfoTooltip text="Choose between vector, keyword, or hybrid search" />
							</div>
							<Dropdown
								value={searchMode}
								onChange={onSearchModeChange}
								options={[
									{
										value: "vector",
										label: "Vector Only",
										description: "Semantic similarity search",
									},
									{
										value: "keyword",
										label: "Keyword Only",
										description: "Full-text keyword search",
									},
									{
										value: "hybrid",
										label: "Hybrid",
										description: "Combined vector and keyword search",
									},
								]}
								placeholder="Select search mode"
								menuAppearance="light"
								triggerClassName={dropdownTriggerClass}
							/>
						</div>
					)}

					{hybridSearchEnabled && searchMode === "hybrid" && (
						<div>
							<div className="mb-2 flex items-center gap-2">
								<label className="text-sm font-semibold text-slate-800">
									Search Weight Balance
								</label>
								<InfoTooltip text="Balance between vector (semantic) and keyword (exact match) search" />
							</div>
							<input
								type="range"
								min="0"
								max="1"
								step="0.1"
								value={keywordWeight}
								onChange={(e) =>
									onKeywordWeightChange(Number.parseFloat(e.target.value))
								}
								className="h-2 w-full cursor-pointer appearance-none rounded-[4px] bg-slate-200 accent-orange-600"
							/>
							<div className="mt-1 flex justify-between text-xs text-slate-600">
								<span>Vector: {Math.round((1 - keywordWeight) * 100)}%</span>
								<span>Keyword: {Math.round(keywordWeight * 100)}%</span>
							</div>
						</div>
					)}

					<div>
						<div className="mb-3 flex items-center gap-2">
							<label
								htmlFor="citation-format-select"
								className="text-sm font-semibold text-slate-800"
							>
								Citation Format
							</label>
							<InfoTooltip text="How citations should be formatted in the output" />
						</div>
						<Dropdown
							value={citationFormat}
							onChange={onCitationFormatChange}
							options={[
								{
									value: "structured",
									label: "Structured",
									description:
										"Full formatted output with sections and metrics",
								},
								{
									value: "inline",
									label: "Inline",
									description:
										"Text with [source, page] after each chunk",
								},
								{
									value: "footnote",
									label: "Footnote",
									description:
										"Text with [1] [2] and References section",
								},
								{
									value: "none",
									label: "None",
									description: "Raw text without any citations",
								},
							]}
							placeholder="Select citation format"
							menuAppearance="light"
							triggerClassName={dropdownTriggerClass}
						/>
					</div>
				</div>
			</div>

			<div className="rounded-[4px] border border-slate-200 bg-slate-50 p-4 shadow-sm">
				<div className="mb-2 flex items-center gap-2">
					<Search className="h-4 w-4 text-orange-600" aria-hidden />
					<span className="text-xs font-semibold capitalize tracking-wide text-slate-800">
						Current Search Settings
					</span>
				</div>
				<div className="space-y-1 text-sm text-slate-700">
					<div>
						Results:{" "}
						<span className="font-semibold text-slate-900">{searchK}</span>
					</div>
					<div>
						Mode:{" "}
						<span className="font-semibold text-slate-900">
							{searchMode === "hybrid"
								? "Hybrid"
								: searchMode === "vector"
									? "Vector Only"
									: "Keyword Only"}
						</span>
					</div>
					{hybridSearchEnabled && searchMode === "hybrid" && (
						<div>
							Balance:{" "}
							<span className="font-semibold text-slate-900">
								{Math.round((1 - keywordWeight) * 100)}% Vector /{" "}
								{Math.round(keywordWeight * 100)}% Keyword
							</span>
						</div>
					)}
					<div>
						Citations:{" "}
						<span className="font-semibold capitalize text-slate-900">
							{citationFormat}
						</span>
					</div>
				</div>
			</div>
		</div>
	);
}
