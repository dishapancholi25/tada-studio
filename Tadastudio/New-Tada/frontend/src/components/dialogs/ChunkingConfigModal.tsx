"use client";

import {
	BookOpen,
	ChevronDown,
	ChevronUp,
	Code,
	Eye,
	FileText,
	Hash,
	Info,
	Scale,
	Settings,
	Target,
	Type,
	X,
	Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import Dropdown from "../ui/Dropdown";

interface ChunkingConfig {
	strategy: "recursive" | "character" | "token" | "semantic" | "whole_page";
	chunkSize: number | null;
	chunkOverlap: number;
	loaderMode: "single" | "elements";
	preset: "fast" | "balanced" | "precise" | "whole_page" | "custom";
	separators?: string[];
	tokenizer?: string;
}

interface ChunkingConfigModalProps {
	isOpen: boolean;
	onClose: () => void;
	config: ChunkingConfig;
	onSave: (config: ChunkingConfig) => void;
	sampleText?: string;
}

const PRESET_CONFIGS = {
	fast: {
		strategy: "recursive" as const,
		chunkSize: 2000,
		chunkOverlap: 100,
		loaderMode: "single" as const,
		description: "Larger chunks for faster processing",
		icon: Zap,
		color: "text-[color:var(--color-text-muted)]",
		bgColor:
			"from-[color:var(--color-surface)] to-[color:var(--color-bg-secondary)]",
		borderColor: "border-[color:var(--color-text-muted)]/20",
	},
	balanced: {
		strategy: "recursive" as const,
		chunkSize: 1000,
		chunkOverlap: 200,
		loaderMode: "single" as const,
		description: "Optimal balance of speed and accuracy",
		icon: Scale,
		color: "text-[#0DA931]",
		bgColor: "from-[#0DA931]/10 to-[#0DA931]/5",
		borderColor: "border-[#0DA931]/20",
	},
	precise: {
		strategy: "semantic" as const,
		chunkSize: 500,
		chunkOverlap: 100,
		loaderMode: "elements" as const,
		description: "Smaller chunks for maximum precision",
		icon: Target,
		color: "text-purple-400",
		bgColor: "from-purple-500/10 to-purple-600/5",
		borderColor: "border-purple-500/20",
	},
	whole_page: {
		strategy: "whole_page" as const,
		chunkSize: null,
		chunkOverlap: 0,
		loaderMode: "single" as const,
		description: "Keep PDF pages intact as single chunks",
		icon: FileText,
		color: "text-blue-400",
		bgColor: "from-blue-500/10 to-blue-600/5",
		borderColor: "border-blue-500/20",
	},
};

const STRATEGY_INFO = {
	recursive: {
		name: "Recursive Character",
		icon: BookOpen,
		description:
			"Intelligently splits text at natural boundaries (paragraphs, sentences)",
		pros: ["Preserves context", "Respects document structure"],
		cons: ["May create variable chunk sizes"],
	},
	character: {
		name: "Fixed Character",
		icon: Type,
		description: "Splits text at fixed character intervals",
		pros: ["Consistent chunk sizes", "Predictable results"],
		cons: ["May split mid-sentence", "Less context-aware"],
	},
	token: {
		name: "Token-based",
		icon: Hash,
		description: "Splits based on language model tokens",
		pros: ["Optimized for LLMs", "Precise token counting"],
		cons: ["Slower processing", "Complex boundaries"],
	},
	semantic: {
		name: "Semantic",
		icon: Code,
		description: "Uses NLP to identify semantic boundaries",
		pros: ["Best context preservation", "Topic-aware splitting"],
		cons: ["Slowest processing", "Resource intensive"],
	},
	whole_page: {
		name: "Whole Page",
		icon: FileText,
		description: "Keeps each PDF page as a single chunk without splitting",
		pros: ["Preserves page context", "Best for page-based PDFs"],
		cons: ["May exceed LLM token limits", "Less granular search"],
	},
};

export default function ChunkingConfigModal({
	isOpen,
	onClose,
	config,
	onSave,
	sampleText = "This is a sample paragraph that demonstrates how text will be split into chunks. Each chunk maintains context while staying within the specified size limits. The overlap ensures continuity between chunks, which is crucial for accurate retrieval.",
}: ChunkingConfigModalProps) {
	const [localConfig, setLocalConfig] = useState<ChunkingConfig>(config);
	const [showAdvanced, setShowAdvanced] = useState(false);
	const [showPreview, setShowPreview] = useState(false);
	const [previewChunks, setPreviewChunks] = useState<any[]>([]);
	const [loadingPreview, setLoadingPreview] = useState(false);
	const [previewStats, setPreviewStats] = useState<any>(null);

	useEffect(() => {
		setLocalConfig(config);
	}, [config]);

	useEffect(() => {
		// Generate preview chunks based on current settings
		if (showPreview && sampleText) {
			generatePreviewChunks().catch((error) => {
				console.error("Failed to generate preview chunks:", error);
			});
		}
	}, [localConfig, showPreview, sampleText]);

	const generatePreviewChunks = async () => {
		setLoadingPreview(true);
		try {
			const result = await api.previewChunks(sampleText, {
				strategy: localConfig.strategy,
				chunkSize: localConfig.chunkSize ?? 1000,
				chunkOverlap: localConfig.chunkOverlap,
			});

			setPreviewChunks(result.chunks || []);
			setPreviewStats({
				totalChunks: result.total_chunks,
				avgChunkSize: Math.round(result.avg_chunk_size),
				recommendations: result.recommendations,
			});
		} catch (error) {
			console.error("Failed to generate preview:", error);
			// Fallback to simple preview
			const words = sampleText.split(" ");
			const wordsPerChunk = Math.floor((localConfig.chunkSize ?? 1000) / 5);
			const overlapWords = Math.floor(localConfig.chunkOverlap / 5);

			const chunks: any[] = [];
			for (let i = 0; i < words.length; i += wordsPerChunk - overlapWords) {
				const chunk = words.slice(i, i + wordsPerChunk).join(" ");
				if (chunk) {
					chunks.push({
						index: chunks.length,
						content: chunk,
						length: chunk.length,
					});
				}
			}
			setPreviewChunks(chunks);
		} finally {
			setLoadingPreview(false);
		}
	};

	const handlePresetSelect = (
		preset: "fast" | "balanced" | "precise" | "whole_page",
	) => {
		const presetConfig = PRESET_CONFIGS[preset];
		setLocalConfig({
			...localConfig,
			strategy: presetConfig.strategy,
			chunkSize: presetConfig.chunkSize,
			chunkOverlap: presetConfig.chunkOverlap,
			loaderMode: presetConfig.loaderMode,
			preset,
		});
	};

	const handleSave = () => {
		onSave(localConfig);
		onClose();
	};

	// Factory function for preset handlers
	const createPresetHandler = useCallback(
		(preset: "fast" | "balanced" | "precise" | "whole_page") => () => {
			handlePresetSelect(preset);
		},
		[],
	);

	// Check if whole_page mode is active (disables size/overlap controls)
	const isWholePageMode = localConfig.strategy === "whole_page";

	// Factory function for strategy handlers
	const createStrategyHandler = useCallback(
		(strategy: string) => () => {
			setLocalConfig({
				...localConfig,
				strategy: strategy as any,
				preset: "custom",
			});
		},
		[localConfig],
	);

	// Change handler for chunk size
	const handleChunkSizeChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setLocalConfig({
				...localConfig,
				chunkSize: parseInt(e.target.value),
				preset: "custom",
			});
		},
		[localConfig],
	);

	// Change handler for chunk overlap
	const handleChunkOverlapChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setLocalConfig({
				...localConfig,
				chunkOverlap: parseInt(e.target.value),
				preset: "custom",
			});
		},
		[localConfig],
	);

	// Change handler for loader mode
	const handleLoaderModeChange = useCallback(
		(value: string) => {
			setLocalConfig({
				...localConfig,
				loaderMode: value as any,
				preset: "custom",
			});
		},
		[localConfig],
	);

	// Click handler for preview toggle
	const handlePreviewToggle = useCallback(() => {
		setShowPreview(!showPreview);
	}, [showPreview]);

	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
			<div className="bg-[color:var(--color-surface)]/95 backdrop-blur-xl rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl border border-[color:var(--color-border)]/50">
				{/* Header */}
				<div className="bg-gradient-to-r from-[color:var(--color-surface)] to-[color:var(--color-bg-secondary)] p-6 border-b border-[color:var(--color-border)]/50">
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-3">
							<div className="p-2 bg-[color:var(--color-accent)]/15 rounded-lg">
								<Settings className="w-6 h-6 text-[color:var(--color-accent)]" />
							</div>
							<div>
								<h2 className="text-xl font-bold text-slate-900">
									Document Processing Configuration
								</h2>
								<p className="text-sm text-[color:var(--color-text-muted)] mt-1">
									Customize how documents are chunked and indexed
								</p>
							</div>
						</div>
						<button
							onClick={onClose}
							className="p-2 hover:bg-[color:var(--color-border)]/50 rounded-lg transition-colors"
						>
							<X className="w-5 h-5 text-[color:var(--color-text-muted)]" />
						</button>
					</div>
				</div>

				{/* Content */}
				<div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
					{/* Presets */}
					<div className="mb-6">
						<h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
							<Zap className="w-4 h-4 text-[color:var(--color-accent)]" />
							Quick Presets
						</h3>
						<div className="grid grid-cols-3 gap-3">
							{Object.entries(PRESET_CONFIGS).map(([key, preset]) => {
								const Icon = preset.icon;
								const isSelected = localConfig.preset === key;

								return (
									<button
										key={key}
										onClick={createPresetHandler(
											key as "fast" | "balanced" | "precise",
										)}
										className={`relative p-4 rounded-xl border transition-all duration-200 ${
											isSelected
												? `bg-gradient-to-br ${preset.bgColor} ${preset.borderColor} shadow-lg`
												: "bg-[color:var(--color-surface)]/50 border-[color:var(--color-border)]/50 hover:border-[color:var(--color-surface-hover)]"
										}`}
									>
										{isSelected && (
											<div className="absolute top-2 right-2 w-2 h-2 bg-[color:var(--color-primary)] rounded-full"></div>
										)}
										<Icon className={`w-5 h-5 ${preset.color} mb-2`} />
										<h4
											className={`font-medium text-sm ${isSelected ? "text-slate-900" : "text-[color:var(--color-text-secondary)]"}`}
										>
											{key.charAt(0).toUpperCase() + key.slice(1)}
										</h4>
										<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
											{preset.description}
										</p>
									</button>
								);
							})}
						</div>
					</div>

					{/* Chunking Strategy */}
					<div className="mb-6">
						<h3 className="text-sm font-semibold text-slate-700 mb-3">
							Chunking Strategy
						</h3>
						<div className="grid grid-cols-2 gap-3">
							{Object.entries(STRATEGY_INFO).map(([key, strategy]) => {
								const Icon = strategy.icon;
								const isSelected = localConfig.strategy === key;

								return (
									<button
										key={key}
										onClick={createStrategyHandler(key)}
										className={`p-4 rounded-xl border text-left transition-all duration-200 ${
											isSelected
												? "bg-gradient-to-br from-[color:var(--color-primary)]/15 to-[color:var(--color-accent)]/12 border-[color:var(--color-border)]/30"
												: "bg-[color:var(--color-surface)]/50 border-[color:var(--color-border)]/50 hover:border-[color:var(--color-surface-hover)]"
										}`}
									>
										<div className="flex items-start gap-3">
											<Icon
												className={`w-5 h-5 ${isSelected ? "text-[color:var(--color-accent)]" : "text-[color:var(--color-text-muted)]"}`}
											/>
											<div className="flex-1">
												<h4
													className={`font-medium text-sm ${isSelected ? "text-slate-900" : "text-[color:var(--color-text-secondary)]"}`}
												>
													{strategy.name}
												</h4>
												<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
													{strategy.description}
												</p>
											</div>
										</div>
									</button>
								);
							})}
						</div>
					</div>

					{/* Parameters */}
					<div className="mb-6 bg-[color:var(--color-bg-secondary)]/30 rounded-xl p-4 border border-[color:var(--color-border)]/30">
						<h3 className="text-sm font-semibold text-slate-700 mb-4">
							Parameters
						</h3>

						{isWholePageMode && (
							<div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
								<p className="text-xs text-blue-600">
									Whole Page mode keeps each PDF page as a single chunk. Chunk
									size and overlap settings are not applicable.
								</p>
							</div>
						)}

						<div className="space-y-4">
							<div className={isWholePageMode ? "opacity-50" : ""}>
								<div className="flex items-center justify-between mb-2">
									<label
										htmlFor="chunk-size-slider"
										className="text-sm text-[color:var(--color-text-secondary)]"
									>
										Chunk Size
									</label>
									<span className="text-sm font-mono text-[color:var(--color-accent)]">
										{isWholePageMode
											? "N/A"
											: `${localConfig.chunkSize} chars`}
									</span>
								</div>
								<input
									id="chunk-size-slider"
									type="range"
									min="200"
									max="4000"
									step="100"
									value={localConfig.chunkSize ?? 1000}
									onChange={handleChunkSizeChange}
									disabled={isWholePageMode}
									className="w-full accent-[#932A8F] disabled:cursor-not-allowed"
								/>
								<div className="flex justify-between text-xs text-[color:var(--color-text-muted)] mt-1">
									<span>200 (small)</span>
									<span>2000 (medium)</span>
									<span>4000 (large)</span>
								</div>
							</div>

							<div className={isWholePageMode ? "opacity-50" : ""}>
								<div className="flex items-center justify-between mb-2">
									<label
										htmlFor="chunk-overlap-slider"
										className="text-sm text-[color:var(--color-text-secondary)]"
									>
										Chunk Overlap
									</label>
									<span className="text-sm font-mono text-[color:var(--color-accent)]">
										{isWholePageMode
											? "N/A"
											: `${localConfig.chunkOverlap} chars`}
									</span>
								</div>
								<input
									id="chunk-overlap-slider"
									type="range"
									min="0"
									max="500"
									step="50"
									value={localConfig.chunkOverlap}
									onChange={handleChunkOverlapChange}
									disabled={isWholePageMode}
									className="w-full accent-[#932A8F] disabled:cursor-not-allowed"
								/>
								<div className="flex justify-between text-xs text-[color:var(--color-text-muted)] mt-1">
									<span>0 (none)</span>
									<span>250 (moderate)</span>
									<span>500 (high)</span>
								</div>
							</div>

							<div>
								<label
									htmlFor="loader-mode-select"
									className="text-sm text-[color:var(--color-text-secondary)] block mb-2"
								>
									Loader Mode
								</label>
								<Dropdown
									value={localConfig.loaderMode}
									onChange={handleLoaderModeChange}
									options={[
										{
											value: "single",
											label: "Single Mode",
											description: "Fast, simple text extraction",
										},
										{
											value: "elements",
											label: "Elements Mode",
											description:
												"Preserves document structure and formatting",
										},
									]}
									placeholder="Select loader mode"
								/>
							</div>
						</div>
					</div>

					{/* Preview */}
					<div className="mb-6">
						<button
							onClick={handlePreviewToggle}
							className="flex items-center gap-2 text-sm text-[color:var(--color-text-secondary)] hover:text-slate-900 transition-colors"
						>
							<Eye className="w-4 h-4" />
							Preview Chunking
							{showPreview ? (
								<ChevronUp className="w-4 h-4" />
							) : (
								<ChevronDown className="w-4 h-4" />
							)}
						</button>

						{showPreview && (
							<div className="mt-3 p-4 bg-[color:var(--color-bg-secondary)]/30 rounded-xl border border-[color:var(--color-border)]/30">
								{loadingPreview ? (
									<div className="text-center py-4">
										<div className="animate-spin rounded-full h-6 w-6 border-2 border-slate-200 border-t-orange-500 mx-auto"></div>
										<p className="text-xs text-[color:var(--color-text-muted)] mt-2">
											Generating preview...
										</p>
									</div>
								) : (
									<>
										<div className="flex items-center justify-between mb-3">
											<p className="text-xs text-[color:var(--color-text-muted)]">
												Sample text split into {previewChunks.length} chunks
											</p>
											{previewStats && (
												<span className="text-xs text-[color:var(--color-text-muted)]">
													Avg size: {previewStats.avgChunkSize} chars
												</span>
											)}
										</div>
										<div className="space-y-2 max-h-48 overflow-y-auto">
											{previewChunks.map((chunk) => (
												<div
													key={chunk.index}
													className="p-3 bg-[color:var(--color-surface)]/50 rounded-lg border border-[color:var(--color-border)]/30"
												>
													<div className="flex items-center justify-between mb-1">
														<span className="text-xs font-mono text-[color:var(--color-accent)]">
															Chunk {chunk.index + 1}
														</span>
														<div className="flex items-center gap-2">
															{chunk.has_overlap && (
																<span
																	className="text-xs text-[color:var(--color-text-muted)]"
																	title="Has overlap with previous chunk"
																>
																	↔
																</span>
															)}
															<span className="text-xs text-[color:var(--color-text-muted)]">
																{chunk.length} chars
															</span>
														</div>
													</div>
													<p className="text-xs text-[color:var(--color-text-secondary)] leading-relaxed">
														{chunk.content}
													</p>
												</div>
											))}
										</div>
										{previewStats?.recommendations && (
											<div className="mt-3 p-2 bg-[#F3F4F9] rounded-lg border border-[color:var(--color-text-muted)]/20">
												<p className="text-xs text-[color:var(--color-text-muted)] font-medium mb-1">
													Auto-detected Recommendations:
												</p>
												<p className="text-xs text-[color:var(--color-text-muted)]">
													Strategy: {previewStats.recommendations.strategy} •
													Size: {previewStats.recommendations.chunk_size} •
													Overlap: {previewStats.recommendations.chunk_overlap}
												</p>
											</div>
										)}
									</>
								)}
							</div>
						)}
					</div>

					{/* Info Box */}
					<div className="p-4 bg-gradient-to-r from-[color:var(--color-surface)] to-[color:var(--color-bg-secondary)] rounded-xl border border-[color:var(--color-border)]/20">
						<div className="flex items-start gap-3">
							<Info className="w-5 h-5 text-[color:var(--color-accent)] mt-0.5" />
							<div className="text-xs text-[color:var(--color-text-secondary)] space-y-1">
								<p className="font-medium text-[color:var(--color-accent)] mb-2">
									Configuration Tips
								</p>
								<p>
									• <strong>Chunk Size:</strong> Larger chunks preserve more
									context but may exceed LLM token limits
								</p>
								<p>
									• <strong>Overlap:</strong> Prevents loss of information at
									chunk boundaries
								</p>
								<p>
									• <strong>Strategy:</strong> Choose based on your document
									structure and retrieval needs
								</p>
								<div className="mt-2 pt-2 border-t border-[color:var(--color-border)]">
									<p className="font-medium text-[color:var(--color-accent)] mb-1">
										Loader Modes Explained:
									</p>
									<p>
										• <strong>Single Mode:</strong> Extracts plain text quickly.
										Best for simple documents without complex formatting
									</p>
									<p>
										• <strong>Elements Mode:</strong> Preserves tables, lists,
										headers, and layout. Use for technical docs, reports, or
										PDFs with complex structure
									</p>
								</div>
							</div>
						</div>
					</div>
				</div>

				{/* Footer */}
				<div className="bg-[color:var(--color-bg-secondary)]/50 p-6 border-t border-[color:var(--color-border)]/50">
					<div className="flex items-center justify-between">
						<div className="text-xs text-[color:var(--color-text-muted)]">
							Current: {localConfig.strategy}
							{localConfig.chunkSize !== null &&
								` • ${localConfig.chunkSize} chars`}
							{localConfig.chunkOverlap > 0 &&
								` • ${localConfig.chunkOverlap} overlap`}
						</div>
						<div className="flex gap-3">
							<button
								onClick={onClose}
								className="px-4 py-2 text-[color:var(--color-text-muted)] hover:text-slate-900 transition-colors"
							>
								Cancel
							</button>
							<button
								onClick={handleSave}
								className="px-6 py-2 bg-gradient-to-r from-[color:var(--color-primary)] to-[color:var(--color-accent)] btn-primary-text font-semibold rounded-lg hover:shadow-lg hover:shadow-[color:var(--color-primary)]/35 transition-all duration-200 hover:scale-105"
							>
								Save Configuration
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
