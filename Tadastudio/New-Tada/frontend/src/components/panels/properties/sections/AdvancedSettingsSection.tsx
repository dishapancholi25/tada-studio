"use client";

import { Sliders } from "lucide-react";
import InfoTooltip from "../../../ui/InfoTooltipPortal";
import NumberInput from "../../../ui/NumberInput";
import Toggle from "../../../ui/Toggle";

interface AdvancedSettingsSectionProps {
	similarityThreshold: number;
	onSimilarityThresholdChange: (v: number) => void;
	hybridSearchEnabled: boolean;
	searchMode: string;
	rrfK: number;
	onRrfKChange: (v: number) => void;
	includeMetadata: boolean;
	onIncludeMetadataChange: (v: boolean) => void;
	includeConfidenceScores: boolean;
	onIncludeConfidenceScoresChange: (v: boolean) => void;
	maxContextTokens: number;
	onMaxContextTokensChange: (v: number) => void;
}

export default function AdvancedSettingsSection({
	similarityThreshold,
	onSimilarityThresholdChange,
	hybridSearchEnabled,
	searchMode,
	rrfK,
	onRrfKChange,
	includeMetadata,
	onIncludeMetadataChange,
	includeConfidenceScores,
	onIncludeConfidenceScoresChange,
	maxContextTokens,
	onMaxContextTokensChange,
}: AdvancedSettingsSectionProps) {
	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100 text-orange-600">
							<Sliders className="h-6 w-6" aria-hidden />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Advanced Settings
							</h3>
							<p className="text-sm text-slate-600">
								Fine-tune relevance thresholds and output options
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div className="space-y-4">
						<h4 className="text-sm font-semibold capitalize tracking-wide text-slate-800">
							Relevance Settings
						</h4>

						<div>
							<div className="mb-3 flex items-center gap-2">
								<label className="text-sm font-semibold text-slate-800">
									Similarity Threshold
								</label>
								<InfoTooltip text="Minimum confidence score for results (0-1). Lower values return more results." />
							</div>
							<NumberInput
								value={similarityThreshold}
								onChange={onSimilarityThresholdChange}
								min={0}
								max={1}
								step={0.05}
								appearance="light"
							/>
						</div>

						{hybridSearchEnabled && searchMode === "hybrid" && (
							<div>
								<div className="mb-3 flex items-center gap-2">
									<label className="text-sm font-semibold text-slate-800">
										RRF K Parameter
									</label>
									<InfoTooltip text="Reciprocal Rank Fusion constant. Higher values give more weight to top results." />
								</div>
								<NumberInput
									value={rrfK}
									onChange={onRrfKChange}
									min={10}
									max={100}
									step={5}
									appearance="light"
								/>
							</div>
						)}
					</div>

					<div className="space-y-4 border-t border-slate-200 pt-4">
						<h4 className="text-sm font-semibold capitalize tracking-wide text-slate-800">
							Output Options
						</h4>

						<div className="flex items-center justify-between gap-4 rounded-[4px] border border-slate-200 bg-white p-4 transition-colors hover:border-orange-400">
							<div>
								<h5 className="text-sm font-semibold text-slate-900">
									Include Metadata
								</h5>
								<p className="mt-1 text-xs text-slate-600">
									Include document metadata in results
								</p>
							</div>
							<Toggle
								checked={includeMetadata}
								onChange={onIncludeMetadataChange}
								size="md"
								activeColor="#ea580c"
							/>
						</div>

						<div className="flex items-center justify-between gap-4 rounded-[4px] border border-slate-200 bg-white p-4 transition-colors hover:border-orange-400">
							<div>
								<h5 className="text-sm font-semibold text-slate-900">
									Include Confidence Scores
								</h5>
								<p className="mt-1 text-xs text-slate-600">
									Show relevance scores with search results
								</p>
							</div>
							<Toggle
								checked={includeConfidenceScores}
								onChange={onIncludeConfidenceScoresChange}
								size="md"
								activeColor="#ea580c"
							/>
						</div>

						<div>
							<div className="mb-3 flex items-center gap-2">
								<label className="text-sm font-semibold text-slate-800">
									Max Context Tokens
								</label>
								<InfoTooltip text="Maximum tokens to include in context for the agent" />
							</div>
							<NumberInput
								value={maxContextTokens}
								onChange={onMaxContextTokensChange}
								min={500}
								max={8000}
								step={500}
								appearance="light"
							/>
						</div>
					</div>
				</div>
			</div>

			<div className="rounded-[4px] border border-slate-200 bg-slate-50 p-4 shadow-sm">
				<div className="mb-2 flex items-center gap-2">
					<Sliders className="h-4 w-4 text-orange-600" aria-hidden />
					<span className="text-xs font-semibold capitalize tracking-wide text-slate-800">
						Current Advanced Settings
					</span>
				</div>
				<div className="space-y-1 text-sm text-slate-700">
					<div>
						Similarity Threshold:{" "}
						<span className="font-semibold text-slate-900">
							{similarityThreshold.toFixed(2)}
						</span>
					</div>
					{hybridSearchEnabled && searchMode === "hybrid" && (
						<div>
							RRF K:{" "}
							<span className="font-semibold text-slate-900">{rrfK}</span>
						</div>
					)}
					<div>
						Metadata:{" "}
						<span className="font-semibold text-slate-900">
							{includeMetadata ? "Enabled" : "Disabled"}
						</span>
					</div>
					<div>
						Confidence Scores:{" "}
						<span className="font-semibold text-slate-900">
							{includeConfidenceScores ? "Enabled" : "Disabled"}
						</span>
					</div>
					<div>
						Max Context:{" "}
						<span className="font-semibold text-slate-900">
							{maxContextTokens.toLocaleString()} tokens
						</span>
					</div>
				</div>
			</div>
		</div>
	);
}
